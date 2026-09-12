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
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Keeps the public client connection on Velocity while the main Paper backend restarts.
 *
 * <p>The local maintenance script writes either {@code drain} or {@code resume} to the
 * request file. In drain mode every current and new player is routed to the waiting
 * backend. In resume mode waiting players return only after the main backend answers a
 * Velocity ping. The status file is deliberately plain JSON so the shell orchestrator can
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
    private static final Component WAITING_MESSAGE = Component.text(
            "본 서버를 준비하는 동안 대기실로 이동했습니다.", NamedTextColor.YELLOW);

    private final ProxyServer proxy;
    private final Logger logger;
    private final Path controlDirectory;
    private final Path requestFile;
    private final Path statusFile;
    private final Path shipMarkerDirectory;
    private final String mainName;
    private final String waitingName;
    private final Map<UUID, Long> nextConnectAttempt = new ConcurrentHashMap<>();
    private final AtomicBoolean pingInFlight = new AtomicBoolean();

    private volatile DesiredMode desired = DesiredMode.RESUME;
    private volatile boolean mainReachable;
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
        this.shipMarkerDirectory = environmentPath("BARKAN_SHIP_MARKER_DIR",
                dataDirectory.resolve("ship-entities"));
        this.mainName = environmentText("BARKAN_MAIN_SERVER", "main");
        this.waitingName = environmentText("BARKAN_WAITING_SERVER", "waiting");
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
                .repeat(Duration.ofMillis(500))
                .schedule();

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

    @Subscribe
    public void onProxyShutdown(ProxyShutdownEvent ignored) {
        ProxyGeyserShipBridge bridge = geyserShipBridge;
        if (bridge != null) bridge.close();
    }

    @Subscribe
    public void onChooseInitialServer(PlayerChooseInitialServerEvent event) {
        if (desired != DesiredMode.DRAIN) return;
        waitingServer().ifPresent(event::setInitialServer);
    }

    @Subscribe
    public void onServerPreConnect(ServerPreConnectEvent event) {
        if (desired != DesiredMode.DRAIN || !isNamed(event.getOriginalServer(), mainName)) return;
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
    }

    private void tick() {
        readRequest();
        pingMain();

        RegisteredServer main = mainServer().orElse(null);
        RegisteredServer waiting = waitingServer().orElse(null);
        if (main == null || waiting == null) {
            writeStatus("MISCONFIGURED", 0, 0);
            return;
        }

        int mainPlayers = 0;
        int waitingPlayers = 0;
        for (Player player : proxy.getAllPlayers()) {
            String current = currentServerName(player);
            if (mainName.equals(current)) {
                mainPlayers++;
                if (desired == DesiredMode.DRAIN) connect(player, waiting);
            } else if (waitingName.equals(current)) {
                waitingPlayers++;
                if (desired == DesiredMode.RESUME && mainReachable) connect(player, main);
            }
        }

        String state;
        if (desired == DesiredMode.DRAIN) {
            state = mainPlayers == 0 ? "MAINTENANCE" : "DRAINING";
        } else {
            state = waitingPlayers == 0 ? "IDLE" : "RESUMING";
        }
        writeStatus(state, mainPlayers, waitingPlayers);
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
            logger.info("Maintenance request changed to {}", next);
        }
    }

    private void pingMain() {
        RegisteredServer main = mainServer().orElse(null);
        if (main == null || !pingInFlight.compareAndSet(false, true)) return;
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

        player.createConnectionRequest(destination).connect().whenComplete((result, failure) -> {
            if (failure != null) {
                logger.debug("Could not move {} to {}: {}", player.getUsername(),
                        destination.getServerInfo().getName(), failure.toString());
            }
        });
    }

    private void writeStatus(String state, int mainPlayers, int waitingPlayers) {
        String json = "{"
                + "\"state\":\"" + state + "\","
                + "\"desired\":\"" + desired + "\","
                + "\"mainPlayers\":" + mainPlayers + ","
                + "\"waitingPlayers\":" + waitingPlayers + ","
                + "\"proxyPlayers\":" + proxy.getPlayerCount() + ","
                + "\"mainReachable\":" + mainReachable + ","
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
