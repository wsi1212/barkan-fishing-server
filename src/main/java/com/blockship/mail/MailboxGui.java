package com.blockship.mail;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.serializer.legacy.LegacyComponentSerializer;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.inventory.InventoryDragEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.InventoryHolder;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.plugin.java.JavaPlugin;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** 6줄 수령 전용 우편함. 마지막 줄 중앙(49번)은 항상 모두 수령이다. */
public final class MailboxGui implements Listener {
    private static final LegacyComponentSerializer LEG = LegacyComponentSerializer.legacySection();
    private final JavaPlugin plugin;
    private final MailboxManager mailbox;
    private final com.blockship.playerdata.PlayerDataManager playerData;

    public MailboxGui(JavaPlugin plugin, MailboxManager mailbox, com.blockship.playerdata.PlayerDataManager playerData) {
        this.plugin = plugin; this.mailbox = mailbox; this.playerData = playerData;
    }

    public void open(Player player, int requestedPage) {
        var data = playerData.getOrCreate(player.getUniqueId(), player.getName());
        MailboxManager.MailboxSnapshot snapshot = mailbox.snapshot(player.getUniqueId(), data);
        List<MailboxManager.MailEntry> entries = snapshot.entries();
        int pages = Math.max(1, (entries.size() + 44) / 45);
        int page = Math.max(1, Math.min(requestedPage, pages));
        Holder holder = new Holder(player.getUniqueId(), page);
        Inventory inv = Bukkit.createInventory(holder, 54, LEG.deserialize("§6우편함 §8| §7수령 전용"));
        holder.inventory = inv;
        int start = (page - 1) * 45;
        for (int slot = 0; slot < 45 && start + slot < entries.size(); slot++) {
            MailboxManager.MailEntry entry = entries.get(start + slot);
            inv.setItem(slot, display(entry));
            holder.entries.put(slot, entry.serialize());
        }
        for (int i = 45; i <= 53; i++) inv.setItem(i, pane(Material.GRAY_STAINED_GLASS_PANE, "§8"));
        inv.setItem(45, page > 1 ? named(Material.ARROW, "§7◀ 이전 페이지") : pane(Material.GRAY_STAINED_GLASS_PANE, "§8◀ 이전 없음"));
        inv.setItem(48, named(Material.BOOK, "§e수령 대기: §f" + entries.size() + "개", "§7우편은 도착 후 7일간 보관됩니다.", "§8인벤이 가득 차면 아이템 우편은 남아 있습니다."));
        inv.setItem(49, named(Material.HOPPER, "§a§l모두 수령", "§7받을 수 있는 보상을 전부 수령합니다.", "§8인벤 공간이 부족한 우편은 그대로 남습니다."));
        inv.setItem(53, page < pages ? named(Material.ARROW, "§7다음 페이지 ▶") : pane(Material.GRAY_STAINED_GLASS_PANE, "§8다음 없음"));
        player.openInventory(inv);
        if (snapshot.expired() > 0) player.sendMessage("§8[§6 우편함 §8] §7유효기간이 지난 우편 §c" + snapshot.expired() + "개§7가 만료되었습니다.");
    }

    @EventHandler
    public void onClick(InventoryClickEvent event) {
        if (!(event.getInventory().getHolder() instanceof Holder holder)) return;
        event.setCancelled(true);
        if (!(event.getWhoClicked() instanceof Player player) || !holder.owner.equals(player.getUniqueId())) return;
        int slot = event.getRawSlot();
        if (slot < 0 || slot >= 54) return;
        if (slot == 45 && holder.page > 1) { open(player, holder.page - 1); return; }
        if (slot == 53) { open(player, holder.page + 1); return; }
        MailboxManager.ClaimResult result;
        if (slot == 49) result = mailbox.claimAll(player);
        else {
            String raw = holder.entries.get(slot);
            if (raw == null) return;
            result = mailbox.claimOne(player, raw);
        }
        sendResult(player, result);
        Bukkit.getScheduler().runTask(plugin, () -> open(player, holder.page));
    }

    @EventHandler
    public void onDrag(InventoryDragEvent event) {
        if (event.getInventory().getHolder() instanceof Holder) event.setCancelled(true);
    }

    private static void sendResult(Player p, MailboxManager.ClaimResult r) {
        if (r.claimed() > 0) {
            String coin = r.recommendCoins() > 0 ? " §a추천 코인 " + r.recommendCoins() + "개" : "";
            p.sendMessage("§8[§6 우편함 §8] §a" + r.claimed() + "개§7 보상을 수령했습니다." + coin);
        } else if (r.inventoryFull() > 0) p.sendMessage("§8[§6 우편함 §8] §e인벤토리 공간이 부족합니다. §7우편은 그대로 보관됩니다.");
        else p.sendMessage("§8[§6 우편함 §8] §7수령할 수 있는 우편이 없습니다.");
        if (r.inventoryFull() > 0 && r.claimed() > 0) p.sendMessage("§8[§6 우편함 §8] §e" + r.inventoryFull() + "개§7는 인벤 공간 부족으로 남겨두었습니다.");
    }

    private static ItemStack display(MailboxManager.MailEntry entry) {
        ItemStack out;
        if (entry.isRecommendCoins()) out = named(Material.EMERALD, "§a마인리스트 추천 보상");
        else {
            ItemStack item = entry.item();
            out = item == null ? named(Material.BARRIER, "§c손상된 우편") : item.clone();
        }
        ItemMeta meta = out.getItemMeta();
        List<Component> lore = meta.lore() == null ? new ArrayList<>() : new ArrayList<>(meta.lore());
        lore.add(LEG.deserialize(""));
        lore.add(LEG.deserialize("§7보낸 곳: §f" + entry.source()));
        if (entry.isRecommendCoins()) lore.add(LEG.deserialize("§7보상: §a추천 코인 " + entry.payload() + "개"));
        lore.add(LEG.deserialize("§7남은 시간: §f" + remaining(entry.expiresAt())));
        lore.add(LEG.deserialize("")); lore.add(LEG.deserialize("§a클릭하여 수령"));
        meta.lore(lore); out.setItemMeta(meta); return out;
    }

    private static String remaining(long expiresAt) {
        long millis = Math.max(0, expiresAt - System.currentTimeMillis());
        long hours = Math.max(1, Duration.ofMillis(millis).toHours());
        return hours >= 48 ? (hours / 24) + "일" : hours + "시간";
    }
    private static ItemStack pane(Material type, String name) { return named(type, name); }
    private static ItemStack named(Material type, String name, String... lore) {
        ItemStack item = new ItemStack(type); ItemMeta meta = item.getItemMeta(); meta.displayName(LEG.deserialize(name));
        if (lore.length > 0) { List<Component> list = new ArrayList<>(); for (String line : lore) list.add(LEG.deserialize(line)); meta.lore(list); }
        item.setItemMeta(meta); return item;
    }

    private static final class Holder implements InventoryHolder {
        final UUID owner; final int page; final Map<Integer, String> entries = new HashMap<>(); Inventory inventory;
        Holder(UUID owner, int page) { this.owner = owner; this.page = page; }
        @Override public Inventory getInventory() { return inventory; }
    }
}
