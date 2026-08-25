package com.barkan.worldwarp;

import java.util.Collections;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

import org.bukkit.Bukkit;
import org.bukkit.World;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerChangedWorldEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.plugin.java.JavaPlugin;

import net.kyori.adventure.resource.ResourcePackInfo;
import net.kyori.adventure.resource.ResourcePackRequest;
import net.kyori.adventure.text.Component;

/**
 * OP 전용 월드 워프 명령어 + 놀이월드 전용 리소스팩 배급.
 *
 * <p>메인 팩은 server.properties 가 전원에게 밀어준다. 여기서 다루는 건 <b>추가 팩</b>이다 —
 * 리듬게임 곡 18개가 87MB 라, 메인 팩에 합치면 놀이월드를 안 가는 사람까지 팩이 바뀔 때마다
 * 그걸 다 받는다. 그래서 <b>playworld 에 들어갈 때만</b> 밀고 나올 때 뗀다.
 */
public final class WorldWarp extends JavaPlugin implements org.bukkit.command.CommandExecutor, TabCompleter, Listener {

    private static final String NO_PERMISSION = "§c권한이 없습니다.";

    /** 추가 팩을 요구하는 월드. */
    private static final String PACK_WORLD = "playworld";
    /**
     * 팩의 고유 id — 클라이언트가 "이 팩"을 식별하는 열쇠다. <b>고정값이어야 한다.</b>
     * 매번 새로 만들면 클라가 다른 팩으로 보고 이미 받은 것을 또 받는다.
     */
    private static final UUID PACK_ID = UUID.fromString("b4a2c1d0-9e5f-4a31-8c76-0f1e2d3c4b5a");

    private String packUrl;
    private String packSha1;
    private boolean packRequired;
    private String packPrompt;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        reloadPackConfig();

        if (getCommand("월드") == null) {
            getLogger().severe("/월드 명령어가 plugin.yml에 등록되지 않았습니다.");
            return;
        }
        getCommand("월드").setExecutor(this);
        getCommand("월드").setTabCompleter(this);
        Bukkit.getPluginManager().registerEvents(this, this);
    }

    private void reloadPackConfig() {
        reloadConfig();
        packUrl = getConfig().getString("playworld-pack.url", "");
        packSha1 = getConfig().getString("playworld-pack.sha1", "");
        packRequired = getConfig().getBoolean("playworld-pack.required", true);
        packPrompt = getConfig().getString("playworld-pack.prompt", "&6놀이월드 &f추가 리소스팩을 받아주세요");
        if (packUrl.isBlank() || packSha1.isBlank()) {
            getLogger().warning("playworld-pack.url/sha1 이 비어 있습니다 — 추가 팩 배급을 건너뜁니다.");
        }
    }

    /** 팩이 설정돼 있고 URL·sha1 이 채워졌는가. */
    private boolean packReady() {
        return !packUrl.isBlank() && !packSha1.isBlank();
    }

    private void sendPack(Player player) {
        if (!packReady()) {
            return;
        }
        try {
            ResourcePackInfo info = ResourcePackInfo.resourcePackInfo(PACK_ID, java.net.URI.create(packUrl), packSha1);
            player.sendResourcePacks(ResourcePackRequest.resourcePackRequest()
                    .packs(info)
                    .required(packRequired)
                    .prompt(Component.text(packPrompt.replace('&', '§')))
                    // ★replace(false) — 메인 팩을 밀어내지 않고 위에 얹는다.
                    //   true 면 서버 기본 팩이 벗겨져 GUI·물고기 아이콘이 전부 깨진다.
                    .replace(false)
                    .build());
        } catch (Exception e) {
            getLogger().warning("놀이월드 팩 전송 실패(" + player.getName() + "): " + e.getMessage());
        }
    }

    private void removePack(Player player) {
        if (!packReady()) {
            return;
        }
        try {
            player.removeResourcePacks(PACK_ID);
        } catch (Exception e) {
            getLogger().warning("놀이월드 팩 해제 실패(" + player.getName() + "): " + e.getMessage());
        }
    }

    @EventHandler
    public void onWorldChange(PlayerChangedWorldEvent event) {
        Player p = event.getPlayer();
        boolean nowIn = PACK_WORLD.equals(p.getWorld().getName());
        boolean wasIn = PACK_WORLD.equals(event.getFrom().getName());
        if (nowIn && !wasIn) {
            sendPack(p);
        } else if (wasIn && !nowIn) {
            // 나가면 뗀다 — 87MB 를 계속 물고 있을 이유가 없고, 다음 진입 때 캐시로 즉시 붙는다.
            removePack(p);
        }
    }

    /** 놀이월드에서 로그아웃한 사람은 그 자리에서 다시 시작하므로, 접속 시에도 팩을 붙여준다. */
    @EventHandler
    public void onJoin(PlayerJoinEvent event) {
        if (PACK_WORLD.equals(event.getPlayer().getWorld().getName())) {
            Bukkit.getScheduler().runTaskLater(this, () -> sendPack(event.getPlayer()), 20L);
        }
    }

    private List<String> worldNames() {
        return Bukkit.getWorlds().stream()
                .map(World::getName)
                .sorted()
                .collect(Collectors.toList());
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!(sender instanceof Player player)) {
            sender.sendMessage("플레이어만 사용할 수 있습니다.");
            return true;
        }

        // plugin.yml 권한 설정과 별개로 실행부에서도 OP를 강제한다.
        // 권한 플러그인이나 명령어 충돌로 permission 체크가 우회되어도 워프할 수 없다.
        if (!player.isOp()) {
            player.sendMessage(NO_PERMISSION);
            return true;
        }

        if (args.length == 1 && args[0].equalsIgnoreCase("리로드")) {
            reloadPackConfig();
            player.sendMessage("§a놀이월드 팩 설정을 다시 읽었습니다. " + (packReady() ? "§7(url·sha1 설정됨)" : "§c(비어 있음)"));
            return true;
        }

        if (args.length == 0) {
            player.sendMessage("§6=== 월드 목록 === §f" + String.join(", ", worldNames()));
            player.sendMessage("§7사용법: /월드 <월드이름>");
            return true;
        }

        World world = Bukkit.getWorld(args[0]);
        if (world == null) {
            player.sendMessage("§c존재하지 않는 월드입니다: " + args[0]);
            return true;
        }

        var spawn = world.getSpawnLocation();
        // World#getKey() 가 곧 dimension key 다(world→minecraft:overworld). BlockShip 의
        // Worlds.dimKey() 도 내부적으로 이 호출이며, 이 플러그인은 BlockShip 을 참조하지 않는다.
        String commandText = "execute in " + world.getKey() + " run tp " + player.getName()
                + " " + spawn.getBlockX() + " " + spawn.getBlockY() + " " + spawn.getBlockZ();
        Bukkit.dispatchCommand(Bukkit.getConsoleSender(), commandText);
        player.sendMessage("§a" + world.getName() + " 월드로 이동했습니다.");
        return true;
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        if (!(sender instanceof Player player) || !player.isOp()) {
            return Collections.emptyList();
        }
        if (args.length != 1) {
            return Collections.emptyList();
        }
        String prefix = args[0].toLowerCase();
        return java.util.stream.Stream.concat(worldNames().stream(), java.util.stream.Stream.of("리로드"))
                .filter(name -> name.toLowerCase().startsWith(prefix))
                .collect(Collectors.toList());
    }
}
