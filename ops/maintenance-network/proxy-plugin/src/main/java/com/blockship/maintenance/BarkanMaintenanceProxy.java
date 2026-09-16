package com.blockship.maintenance;

import com.google.inject.Inject;
import com.velocitypowered.api.event.Subscribe;
import com.velocitypowered.api.event.player.KickedFromServerEvent;
import com.velocitypowered.api.event.connection.DisconnectEvent;
import com.velocitypowered.api.event.player.PlayerChooseInitialServerEvent;
import com.velocitypowered.api.event.player.ServerPreConnectEvent;
import com.velocitypowered.api.event.proxy.ProxyInitializeEvent;
import com.velocitypowered.api.event.proxy.ProxyShutdownEvent;
import com.velocitypowered.api.plugin.Dependency;
import com.velocitypowered.api.plugin.Plugin;
import com.velocitypowered.api.plugin.annotation.DataDirectory;
import com.velocitypowered.api.command.CommandMeta;
import com.velocitypowered.api.command.SimpleCommand;
import com.velocitypowered.api.proxy.Player;
import com.velocitypowered.api.proxy.ProxyServer;
import com.velocitypowered.api.proxy.server.RegisteredServer;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import org.slf4j.Logger;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Duration;
import java.util.Locale;
import java.util.Map;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Keeps the public client connection on Velocity while the main Paper backend restarts.
 *
 * <p>The local maintenance script writes either {@code drain} or {@code resume} to the
 * request file. In drain mode every current and new player is routed to the waiting
 * backend. In resume mode waiting players return only after the main backend answers a
 * Velocity ping, and are paced one player every 200 ms instead of reconnecting as one burst.
 * The status file is deliberately plain JSON so the shell orchestrator can
 * wait for an acknowledged, empty main backend before stopping Paper.</p>
 */
@Plugin(
        id = "barkan-maintenance",
        name = "Barkan Maintenance",
        version = "1.0.0",
        description = "Seamless Barkan backend maintenance routing",
        authors = {"BlockShip"},
        dependencies = {@Dependency(id = "geyser", optional = true)}
)
public final class BarkanMaintenanceProxy {

    private enum DesiredMode { DRAIN, RESUME }

    private static final long CONNECT_RETRY_NANOS = Duration.ofSeconds(2).toNanos();
    private static final long MAIN_PING_INTERVAL_NANOS = Duration.ofSeconds(2).toNanos();
    private static final long READY_HEARTBEAT_MAX_AGE_MILLIS = Duration.ofSeconds(5).toMillis();
    private static final Pattern READY_TIMESTAMP = Pattern.compile(
            "\\\"completedAtEpochMs\\\"\\s*:\\s*(\\d+)");
    private static final Component WAITING_MESSAGE = Component.text(
            "본 서버를 준비하는 동안 대기실로 이동했습니다.", NamedTextColor.YELLOW);

    private final ProxyServer proxy;
    private final Logger logger;
    private final Path controlDirectory;
    private final Path requestFile;
    private final Path statusFile;
    /**
     * Geyser 팩/매핑은 Velocity를 재시작하지 않고 Geyser만 리로드한다. systemd Velocity는
     * stdin이 /dev/null이라, 로컬 유지보수 스크립트가 이 요청 파일을 만들어 프록시 JVM에
     * 안전하게 명령을 전달한다.
     */
    private final Path geyserReloadRequestFile;
    private final Path geyserReloadResultFile;
    private final Path mainReadyFile;
    private final Path shipMarkerDirectory;
    private final String mainName;
    private final String waitingName;
    private final boolean testCommandsEnabled;
    private final Map<UUID, Long> nextConnectAttempt = new ConcurrentHashMap<>();
    private final java.util.Set<UUID> resumePermits = ConcurrentHashMap.newKeySet();
    private final AtomicBoolean pingInFlight = new AtomicBoolean();
    private final AtomicBoolean geyserReloadInFlight = new AtomicBoolean();

    private volatile DesiredMode desired = DesiredMode.RESUME;
    private volatile boolean mainReachable;
    private volatile boolean mainReady;
    private volatile boolean resumeInProgress;
    private volatile boolean readinessGateArmed;
    private volatile long nextMainPingNanos;
    private volatile String lastBadRequest = "";
    private volatile ProxyGeyserShipBridge geyserShipBridge;

    @Inject
    public BarkanMaintenanceProxy(
            ProxyServer proxy,
            Logger logger,
            @DataDirectory Path dataDirectory
    ) {
        this.proxy = proxy;
        this.logger = logger;
        this.controlDirectory = environmentPath("BARKAN_MAINTENANCE_CONTROL_DIR",
                dataDirectory.resolve("control"));
        this.requestFile = controlDirectory.resolve("request");
        this.statusFile = controlDirectory.resolve("status.json");
        this.geyserReloadRequestFile = controlDirectory.resolve("geyser-reload.request");
        this.geyserReloadResultFile = controlDirectory.resolve("geyser-reload.result");
        this.mainReadyFile = environmentPath("BARKAN_MAIN_READY_FILE",
                Path.of("/home/ubuntu/mcserver/plugins/BlockShip/startup-ready.json"));
        this.shipMarkerDirectory = environmentPath("BARKAN_SHIP_MARKER_DIR",
                dataDirectory.resolve("ship-entities"));
        this.mainName = environmentText("BARKAN_MAIN_SERVER", "main");
        this.waitingName = environmentText("BARKAN_WAITING_SERVER", "waiting");
        this.testCommandsEnabled = Boolean.parseBoolean(
                environmentText("BARKAN_MAINTENANCE_TEST_COMMANDS", "false"));
    }

    @Subscribe
    public void onProxyInitialize(ProxyInitializeEvent ignored) {
        try {
            Files.createDirectories(controlDirectory);
            Files.createDirectories(shipMarkerDirectory);
            if (Files.notExists(requestFile)) atomicWrite(requestFile, "resume\n");
            readRequest();
        } catch (IOException e) {
            throw new IllegalStateException("maintenance control directory is unavailable", e);
        }

        proxy.getScheduler().buildTask(this, this::tick)
                // 복귀 처리량 2초당 10명. 한 번에 10명을 보내지 않고 200ms마다 1명씩 분산한다.
                .repeat(Duration.ofMillis(200))
                .schedule();

        if (testCommandsEnabled) registerTestCommand();

        try {
            geyserShipBridge = ProxyGeyserShipBridge.install(this, logger, shipMarkerDirectory);
        } catch (NoClassDefFoundError | ExceptionInInitializerError unavailable) {
            logger.info("Geyser API is unavailable; the Java maintenance router remains active");
        } catch (Throwable failure) {
            logger.warn("Could not install the proxy-side Bedrock ship bridge", failure);
        }

        logger.info("Barkan maintenance routing ready: {} -> {}, control={}",
                mainName, waitingName, controlDirectory);
    }

    private void registerTestCommand() {
        CommandMeta meta = proxy.getCommandManager().metaBuilder("점검테스트")
                .aliases("mainttest")
                .plugin(this)
                .build();
        proxy.getCommandManager().register(meta, new SimpleCommand() {
            private final List<String> choices = List.of("진입", "복귀", "재시작", "상태");

            @Override
            public void execute(Invocation invocation) {
                String[] arguments = invocation.arguments();
                if (arguments.length != 1) {
                    invocation.source().sendMessage(Component.text(
                            "사용법: /점검테스트 <진입|복귀|재시작|상태>", NamedTextColor.YELLOW));
                    return;
                }
                try {
                    switch (arguments[0].toLowerCase(Locale.ROOT)) {
                        case "진입", "drain" -> {
                            atomicWrite(requestFile, "drain\n");
                            invocation.source().sendMessage(Component.text(
                                    "공허 대기실 진입을 요청했습니다.", NamedTextColor.AQUA));
                        }
                        case "복귀", "resume" -> {
                            atomicWrite(requestFile, "resume\n");
                            invocation.source().sendMessage(Component.text(
                                    "본 서버 복귀를 요청했습니다.", NamedTextColor.GREEN));
                        }
                        case "재시작", "restart" -> {
                            atomicWrite(requestFile, "drain\n");
                            atomicWrite(controlDirectory.resolve("dev-action"), "restart\n");
                            invocation.source().sendMessage(Component.text(
                                    "대기실 이동 후 dev Paper를 재시작합니다. 접속을 유지하세요.",
                                    NamedTextColor.GOLD));
                        }
                        case "상태", "status" -> {
                            String status = Files.exists(statusFile)
                                    ? Files.readString(statusFile, StandardCharsets.UTF_8).trim()
                                    : "아직 상태 없음";
                            invocation.source().sendMessage(Component.text(status, NamedTextColor.GRAY));
                        }
                        default -> invocation.source().sendMessage(Component.text(
                                "사용법: /점검테스트 <진입|복귀|재시작|상태>", NamedTextColor.YELLOW));
                    }
                } catch (IOException failure) {
                    logger.warn("Could not handle dev maintenance test command", failure);
                    invocation.source().sendMessage(Component.text(
                            "점검 제어 파일을 쓰지 못했습니다.", NamedTextColor.RED));
                }
            }

            @Override
            public List<String> suggest(Invocation invocation) {
                String[] arguments = invocation.arguments();
                if (arguments.length > 1) return List.of();
                String prefix = arguments.length == 0 ? "" : arguments[0].toLowerCase(Locale.ROOT);
                return choices.stream().filter(choice -> choice.startsWith(prefix)).toList();
            }

            @Override
            public boolean hasPermission(Invocation invocation) {
                return testCommandsEnabled;
            }
        });
        logger.warn("DEV-ONLY maintenance test commands enabled: /점검테스트, /mainttest");
    }

    @Subscribe
    public void onProxyShutdown(ProxyShutdownEvent ignored) {
        ProxyGeyserShipBridge bridge = geyserShipBridge;
        if (bridge != null) bridge.close();
    }

    @Subscribe
    public void onChooseInitialServer(PlayerChooseInitialServerEvent event) {
        if (mainAdmissionOpen()) return;
        waitingServer().ifPresent(event::setInitialServer);
    }

    @Subscribe
    public void onServerPreConnect(ServerPreConnectEvent event) {
        if (!isNamed(event.getOriginalServer(), mainName)) return;
        UUID playerId = event.getPlayer().getUniqueId();
        if (resumePermits.remove(playerId)) return;
        if (mainAdmissionOpen()) return;
        waitingServer().ifPresent(waiting ->
                event.setResult(ServerPreConnectEvent.ServerResult.allowed(waiting)));
    }

    @Subscribe
    public void onKickedFromServer(KickedFromServerEvent event) {
        if (!isNamed(event.getServer(), mainName)) return;
        mainReachable = false;
        waitingServer().ifPresent(waiting -> event.setResult(
                KickedFromServerEvent.RedirectPlayer.create(waiting, WAITING_MESSAGE)));
    }

    @Subscribe
    public void onDisconnect(DisconnectEvent event) {
        nextConnectAttempt.remove(event.getPlayer().getUniqueId());
        resumePermits.remove(event.getPlayer().getUniqueId());
    }

    private void tick() {
        readRequest();
        processGeyserReloadRequest();
        pingMain();

        RegisteredServer main = mainServer().orElse(null);
        RegisteredServer waiting = waitingServer().orElse(null);
        if (main == null || waiting == null) {
            mainReady = false;
            resumeInProgress = false;
            writeStatus("MISCONFIGURED", 0, 0);
            return;
        }

        mainReady = mainReachable && readsFreshMainReady();

        int mainPlayers = 0;
        int waitingPlayers = 0;
        Player resumeCandidate = null;
        long now = System.nanoTime();
        for (Player player : proxy.getAllPlayers()) {
            String current = currentServerName(player);
            if (mainName.equals(current)) {
                mainPlayers++;
                if (desired == DesiredMode.DRAIN) connect(player, waiting);
            } else if (waitingName.equals(current)) {
                waitingPlayers++;
                if (desired == DesiredMode.RESUME && (!readinessGateArmed || mainReady)
                        && resumeCandidate == null) {
                    Long allowedAt = nextConnectAttempt.get(player.getUniqueId());
                    if (allowedAt == null || now >= allowedAt) resumeCandidate = player;
                }
            }
        }
        resumeInProgress = desired == DesiredMode.RESUME && waitingPlayers > 0;
        if (resumeCandidate != null) connect(resumeCandidate, main);

        String state;
        if (desired == DesiredMode.DRAIN) {
            state = mainPlayers == 0 ? "MAINTENANCE" : "DRAINING";
        } else {
            state = waitingPlayers == 0 ? "IDLE" : (mainReady ? "RESUMING" : "RESUME_PAUSED");
        }
        writeStatus(state, mainPlayers, waitingPlayers);
    }

    /**
     * Execute one Geyser-only reload requested by the local asset deployer.
     *
     * <p>The token prevents a stale result from being mistaken for a newer request. The command
     * runs through Velocity's command manager as its console source; this is deliberately not a
     * Velocity reload or service restart, so Java players remain connected through the proxy.</p>
     */
    private void processGeyserReloadRequest() {
        if (!Files.isRegularFile(geyserReloadRequestFile)) return;

        final String token;
        try {
            token = Files.readString(geyserReloadRequestFile, StandardCharsets.UTF_8).trim();
            Files.deleteIfExists(geyserReloadRequestFile);
        } catch (IOException failure) {
            logger.warn("Could not consume Geyser reload request {}", geyserReloadRequestFile, failure);
            return;
        }
        if (!token.matches("[A-Za-z0-9._-]{1,96}")) {
            writeGeyserReloadResult("invalid", "invalid-token");
            return;
        }
        if (!geyserReloadInFlight.compareAndSet(false, true)) {
            writeGeyserReloadResult(token, "busy");
            return;
        }
        if (!proxy.getCommandManager().hasCommand("geyser", proxy.getConsoleCommandSource())) {
            geyserReloadInFlight.set(false);
            writeGeyserReloadResult(token, "unavailable");
            logger.warn("Geyser reload requested but the Geyser command is unavailable");
            return;
        }

        logger.info("Running requested Geyser-only reload (token={})", token);
        proxy.getCommandManager().executeAsync(proxy.getConsoleCommandSource(), "geyser reload")
                .whenComplete((handled, failure) -> {
                    geyserReloadInFlight.set(false);
                    if (failure != null) {
                        logger.warn("Geyser-only reload failed", failure);
                        writeGeyserReloadResult(token, "failed");
                    } else if (Boolean.TRUE.equals(handled)) {
                        writeGeyserReloadResult(token, "ok");
                    } else {
                        logger.warn("Geyser reload command was not handled");
                        writeGeyserReloadResult(token, "unavailable");
                    }
                });
    }

    private void writeGeyserReloadResult(String token, String state) {
        try {
            atomicWrite(geyserReloadResultFile, token + " " + state + "\n");
        } catch (IOException failure) {
            logger.warn("Could not write Geyser reload result {}", geyserReloadResultFile, failure);
        }
    }

    private void readRequest() {
        final String request;
        try {
            request = Files.readString(requestFile, StandardCharsets.UTF_8)
                    .trim().toLowerCase(Locale.ROOT);
        } catch (IOException e) {
            logger.warn("Could not read maintenance request {}", requestFile, e);
            return;
        }

        DesiredMode next = switch (request) {
            case "drain" -> DesiredMode.DRAIN;
            case "resume" -> DesiredMode.RESUME;
            default -> null;
        };
        if (next == null) {
            if (!request.equals(lastBadRequest)) {
                lastBadRequest = request;
                logger.warn("Ignoring unknown maintenance request: '{}'", request);
            }
            return;
        }
        lastBadRequest = "";
        if (desired != next) {
            desired = next;
            nextConnectAttempt.clear();
            resumePermits.clear();
            if (next == DesiredMode.DRAIN) {
                // 새 프록시를 구 BlockShip보다 먼저 무접속 창에 배포할 수 있도록 평상시에는
                // 준비 마커를 요구하지 않는다. 실제 점검 주기를 본 뒤부터만 fail-closed 한다.
                readinessGateArmed = true;
                resumeInProgress = false;
            } else {
                resumeInProgress = readinessGateArmed;
            }
            logger.info("Maintenance request changed to {}", next);
        }
    }

    private boolean mainAdmissionOpen() {
        return desired != DesiredMode.DRAIN
                && (!readinessGateArmed || mainReady)
                && !resumeInProgress;
    }

    private void pingMain() {
        RegisteredServer main = mainServer().orElse(null);
        long now = System.nanoTime();
        if (main == null || now < nextMainPingNanos || !pingInFlight.compareAndSet(false, true)) return;
        nextMainPingNanos = now + MAIN_PING_INTERVAL_NANOS;
        main.ping().orTimeout(2, TimeUnit.SECONDS).whenComplete((ping, failure) -> {
            mainReachable = failure == null;
            pingInFlight.set(false);
        });
    }

    private void connect(Player player, RegisteredServer destination) {
        long now = System.nanoTime();
        Long allowedAt = nextConnectAttempt.get(player.getUniqueId());
        if (allowedAt != null && now < allowedAt) return;
        nextConnectAttempt.put(player.getUniqueId(), now + CONNECT_RETRY_NANOS);
        boolean returningToMain = destination.getServerInfo().getName().equalsIgnoreCase(mainName);
        if (returningToMain) resumePermits.add(player.getUniqueId());

        player.createConnectionRequest(destination).connect().whenComplete((result, failure) -> {
            if (returningToMain) resumePermits.remove(player.getUniqueId());
            if (failure != null) {
                logger.debug("Could not move {} to {}: {}", player.getUsername(),
                        destination.getServerInfo().getName(), failure.toString());
            }
        });
    }

    private boolean readsFreshMainReady() {
        try {
            String json = Files.readString(mainReadyFile, StandardCharsets.UTF_8);
            if (!json.matches("(?s).*\\\"ready\\\"\\s*:\\s*true.*")
                    || !json.matches("(?s).*\\\"acceptingPlayers\\\"\\s*:\\s*true.*")) return false;
            Matcher timestamp = READY_TIMESTAMP.matcher(json);
            if (!timestamp.find()) return false;
            long age = System.currentTimeMillis() - Long.parseLong(timestamp.group(1));
            return age >= 0 && age < READY_HEARTBEAT_MAX_AGE_MILLIS;
        } catch (IOException | NumberFormatException ignored) {
            return false;
        }
    }

    private void writeStatus(String state, int mainPlayers, int waitingPlayers) {
        String json = "{"
                + "\"state\":\"" + state + "\","
                + "\"desired\":\"" + desired + "\","
                + "\"mainPlayers\":" + mainPlayers + ","
                + "\"waitingPlayers\":" + waitingPlayers + ","
                + "\"proxyPlayers\":" + proxy.getPlayerCount() + ","
                + "\"mainReachable\":" + mainReachable + ","
                + "\"mainReady\":" + mainReady + ","
                + "\"readinessGateArmed\":" + readinessGateArmed + ","
                + "\"resumeRatePerSecond\":5,"
                + "\"updatedEpochMs\":" + System.currentTimeMillis()
                + "}\n";
        try {
            atomicWrite(statusFile, json);
        } catch (IOException e) {
            logger.warn("Could not write maintenance status {}", statusFile, e);
        }
    }

    private void atomicWrite(Path destination, String value) throws IOException {
        Files.createDirectories(destination.getParent());
        Path temporary = destination.resolveSibling(destination.getFileName() + ".tmp");
        Files.writeString(temporary, value, StandardCharsets.UTF_8);
        try {
            Files.move(temporary, destination, StandardCopyOption.ATOMIC_MOVE,
                    StandardCopyOption.REPLACE_EXISTING);
        } catch (AtomicMoveNotSupportedException unsupported) {
            Files.move(temporary, destination, StandardCopyOption.REPLACE_EXISTING);
        }
    }

    private Optional<RegisteredServer> mainServer() {
        return proxy.getServer(mainName);
    }

    private Optional<RegisteredServer> waitingServer() {
        return proxy.getServer(waitingName);
    }

    private static boolean isNamed(RegisteredServer server, String expected) {
        return expected.equals(server.getServerInfo().getName());
    }

    private static String currentServerName(Player player) {
        return player.getCurrentServer()
                .map(connection -> connection.getServerInfo().getName())
                .orElse("");
    }

    private static String environmentText(String name, String fallback) {
        String value = System.getenv(name);
        return value == null || value.isBlank() ? fallback : value.trim();
    }

    private static Path environmentPath(String name, Path fallback) {
        String value = System.getenv(name);
        return value == null || value.isBlank() ? fallback : Path.of(value.trim());
    }
}
