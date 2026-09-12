package com.blockship.maintenance.waiting;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import net.kyori.adventure.title.Title;
import org.bukkit.Bukkit;
import org.bukkit.Difficulty;
import org.bukkit.GameMode;
import org.bukkit.GameRule;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.block.BlockPlaceEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.entity.FoodLevelChangeEvent;
import org.bukkit.event.player.PlayerCommandPreprocessEvent;
import org.bukkit.event.player.PlayerDropItemEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerMoveEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.generator.ChunkGenerator;
import org.bukkit.plugin.java.JavaPlugin;

import java.time.Duration;
import java.util.Random;

/** A deliberately empty, non-persistent holding world used during main-server maintenance. */
public final class BarkanWaitingRoom extends JavaPlugin implements Listener {

    private static final Component ACTION_BAR = Component.text(
            "본 서버가 준비되면 자동으로 돌아갑니다 · 접속을 끊지 마세요",
            NamedTextColor.AQUA);

    @Override
    public void onEnable() {
        Bukkit.getPluginManager().registerEvents(this, this);
        for (World world : Bukkit.getWorlds()) configureWorld(world);
        Bukkit.getScheduler().runTaskTimer(this, () -> {
            for (Player player : Bukkit.getOnlinePlayers()) {
                keepSafe(player);
                player.sendActionBar(ACTION_BAR);
            }
        }, 20L, 20L);
    }

    @Override
    public ChunkGenerator getDefaultWorldGenerator(String worldName, String id) {
        return new ChunkGenerator() {
            @Override
            public Location getFixedSpawnLocation(World world, Random random) {
                return waitingLocation(world);
            }
        };
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent event) {
        event.joinMessage(null);
        Player player = event.getPlayer();
        prepare(player);
        Bukkit.getScheduler().runTask(this, () -> {
            prepare(player);
            player.showTitle(Title.title(
                    Component.text("정기 점검 중", NamedTextColor.YELLOW),
                    Component.text("연결은 유지되고 있습니다", NamedTextColor.GRAY),
                    Title.Times.times(Duration.ofMillis(300), Duration.ofSeconds(4),
                            Duration.ofMillis(500))));
        });
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        event.quitMessage(null);
    }

    @EventHandler(ignoreCancelled = true)
    public void onMove(PlayerMoveEvent event) {
        Location to = event.getTo();
        if (to.getY() < 20 || Math.abs(to.getX()) > 40 || Math.abs(to.getZ()) > 40) {
            event.setTo(waitingLocation(to.getWorld()));
        }
    }

    @EventHandler public void onDamage(EntityDamageEvent event) { event.setCancelled(true); }
    @EventHandler public void onHunger(FoodLevelChangeEvent event) { event.setCancelled(true); }
    @EventHandler public void onBreak(BlockBreakEvent event) { event.setCancelled(true); }
    @EventHandler public void onPlace(BlockPlaceEvent event) { event.setCancelled(true); }
    @EventHandler public void onDrop(PlayerDropItemEvent event) { event.setCancelled(true); }
    @EventHandler public void onInteract(PlayerInteractEvent event) { event.setCancelled(true); }

    @EventHandler
    public void onCommand(PlayerCommandPreprocessEvent event) {
        // Velocity consumes its own commands before this backend sees them. Everything that
        // reaches the waiting Paper server is intentionally unavailable during maintenance.
        event.setCancelled(true);
        event.getPlayer().sendActionBar(ACTION_BAR);
    }

    private void prepare(Player player) {
        World world = player.getWorld();
        configureWorld(world);
        player.teleport(waitingLocation(world));
        player.setGameMode(GameMode.ADVENTURE);
        player.setInvulnerable(true);
        player.setAllowFlight(true);
        player.setFlying(true);
        player.setFoodLevel(20);
        player.setSaturation(20f);
        player.getInventory().clear();
    }

    private void keepSafe(Player player) {
        player.setInvulnerable(true);
        player.setAllowFlight(true);
        if (!player.isFlying()) player.setFlying(true);
        if (player.getLocation().getY() < 20) player.teleport(waitingLocation(player.getWorld()));
    }

    private static Location waitingLocation(World world) {
        return new Location(world, 0.5, 64.0, 0.5, 180f, 0f);
    }

    private static void configureWorld(World world) {
        world.setDifficulty(Difficulty.PEACEFUL);
        world.setTime(18000L);
        world.setStorm(false);
        world.setThundering(false);
        world.setSpawnLocation(waitingLocation(world));
        world.setGameRule(GameRule.DO_DAYLIGHT_CYCLE, false);
        world.setGameRule(GameRule.DO_WEATHER_CYCLE, false);
        world.setGameRule(GameRule.DO_MOB_SPAWNING, false);
        world.setGameRule(GameRule.DO_FIRE_TICK, false);
        world.setGameRule(GameRule.KEEP_INVENTORY, true);
        world.setGameRule(GameRule.SHOW_DEATH_MESSAGES, false);
    }
}
