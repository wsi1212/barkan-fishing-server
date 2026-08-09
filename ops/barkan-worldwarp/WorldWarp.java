package com.barkan.worldwarp;

import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

import org.bukkit.Bukkit;
import org.bukkit.World;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;
import org.bukkit.plugin.java.JavaPlugin;

/** OP 전용 성 전시월드 워프 명령어. */
public final class WorldWarp extends JavaPlugin implements org.bukkit.command.CommandExecutor, TabCompleter {

    private static final String NO_PERMISSION = "§c권한이 없습니다.";

    @Override
    public void onEnable() {
        if (getCommand("월드") == null) {
            getLogger().severe("/월드 명령어가 plugin.yml에 등록되지 않았습니다.");
            return;
        }
        getCommand("월드").setExecutor(this);
        getCommand("월드").setTabCompleter(this);
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
        return worldNames().stream()
                .filter(name -> name.toLowerCase().startsWith(prefix))
                .collect(Collectors.toList());
    }
}
