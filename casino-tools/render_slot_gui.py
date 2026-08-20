#!/usr/bin/env python3
"""Render the current CasinoManager slot GUI at the project's exact GUI scale.

Sources of truth:
  - BlockShip CasinoManager.java (slot assignments and screens)
  - gui-forge/make_inventory_layout.py (18px slot pitch / 4x art scale)
  - Minecraft 1.21.11 generic_54.png (vanilla container background)

The output is a visual preview, not a replacement for an in-game screenshot.
The canvas uses the same 4x convention as the rest of gui-forge:
  176 x 222 GUI px -> 704 x 888 art px for a 54-slot inventory.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
RP = Path.home() / "development" / "barkan-resourcepack"
GUI_FORGE = HERE.parent / "gui-forge"
CLIENT_JAR = (
    Path.home()
    / "Library/Application Support/minecraft/versions/1.21.11/1.21.11.jar"
)
OUT = HERE / "rendered"

SCALE = 4
GUI_W = 176
GRID_X = 7
GRID_Y = 17
CELL = 18
COLS = 9


def font(size: int):
    path = RP / "assets/barkan/font/aggro_medium.ttf"
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def vanilla_texture(path: str) -> Image.Image:
    with ZipFile(CLIENT_JAR) as jar:
        return Image.open(BytesIO(jar.read(path))).convert("RGBA")


def custom_texture(name: str) -> Image.Image:
    return Image.open(RP / "assets/minecraft/textures/item" / name).convert("RGBA")


def custom_slot_texture(symbol: str) -> Image.Image:
    return Image.open(
        RP / "assets/minecraft/textures/item/slot" / f"sym_{symbol}.png"
    ).convert("RGBA")


def custom_chip_texture(chip: str) -> Image.Image:
    return Image.open(
        RP / "assets/minecraft/textures/item/chip" / f"chip_{chip}.png"
    ).convert("RGBA")


def item_texture(kind: str) -> Image.Image:
    """Use the exact client texture where it exists, including block-backed items."""
    paths = {
        "book": "assets/minecraft/textures/item/book.png",
        "arrow": "assets/minecraft/textures/item/arrow.png",
        "nether_star": "assets/minecraft/textures/item/nether_star.png",
        "lime_dye": "assets/minecraft/textures/item/lime_dye.png",
        "iron_nugget": "assets/minecraft/textures/item/iron_nugget.png",
        "gold_nugget": "assets/minecraft/textures/item/gold_nugget.png",
        "emerald": "assets/minecraft/textures/item/emerald.png",
        "diamond": "assets/minecraft/textures/item/diamond.png",
        "clock": "assets/minecraft/textures/item/clock_00.png",
        "note_block": "assets/minecraft/textures/block/note_block.png",
        "lever": "assets/minecraft/textures/block/lever.png",
        "redstone_torch": "assets/minecraft/textures/block/redstone_torch.png",
        "black_pane": "assets/minecraft/textures/block/black_stained_glass.png",
        "gray_pane": "assets/minecraft/textures/block/gray_stained_glass.png",
        "orange_pane": "assets/minecraft/textures/block/orange_stained_glass.png",
    }
    return vanilla_texture(paths[kind])


def canvas(rows: int, background: Path | None = None) -> Image.Image:
    """Use a custom exact-size plate, or fall back to the real vanilla GUI texture."""
    height = 114 + rows * CELL
    if background is not None:
        plate = Image.open(background).convert("RGBA")
        expected = (GUI_W * SCALE, height * SCALE)
        if plate.size != expected:
            raise ValueError(f"custom background {plate.size} != {expected}: {background}")
        return plate.copy()
    base = vanilla_texture("assets/minecraft/textures/gui/container/generic_54.png")
    base = base.crop((0, 0, GUI_W, height))
    return base.resize((GUI_W * SCALE, height * SCALE), Image.Resampling.NEAREST)


def slot_xy(slot: int) -> tuple[int, int]:
    row, col = divmod(slot, COLS)
    return GRID_X + CELL * col, GRID_Y + CELL * row


def paste_item(im: Image.Image, slot: int, texture: Image.Image) -> None:
    """Paste a 16x16 in-game item sprite into the exact 18px slot."""
    x, y = slot_xy(slot)
    sprite = texture.resize((16 * SCALE, 16 * SCALE), Image.Resampling.NEAREST)
    im.alpha_composite(sprite, ((x + 1) * SCALE, (y + 1) * SCALE))


def title(im: Image.Image, text: str, custom: bool = False) -> None:
    d = ImageDraw.Draw(im)
    f = font(8 * SCALE)
    if custom:
        # Plates.title/GuiTitle centers the title over the art-deco plate and uses
        # a warm ink instead of vanilla black, which disappears on the emerald panel.
        bbox = d.textbbox((0, 0), text, font=f)
        x = (GUI_W * SCALE - (bbox[2] - bbox[0])) // 2
        y = 5 * SCALE
        d.text((x + SCALE, y + SCALE), text, font=f, fill=(72, 30, 10, 255))
        d.text((x, y), text, font=f, fill=(255, 240, 210, 255))
        return
    # Vanilla container title starts at GUI (8, 6), with a one-pixel shadow.
    x, y = 8 * SCALE, 6 * SCALE
    d.text((x + SCALE, y + SCALE), text, font=f, fill=(255, 255, 255, 255))
    d.text((x, y), text, font=f, fill=(64, 64, 64, 255))


def pane_fill(im: Image.Image, rows: int, custom: bool = False) -> None:
    # Java now uses Plates.paint(): paper + ui_blank on Java clients, so the
    # art-deco plate remains visible. Bedrock keeps the legacy glass fallback.
    if custom:
        return
    pane = item_texture("black_pane")
    for slot in range(rows * COLS):
        paste_item(im, slot, pane)


def render_reels(im: Image.Image, state: str) -> None:
    # Exact CasinoManager.renderSlot() placements.
    frame_black = (9, 10, 12, 14, 16, 17, 27, 28, 30, 32, 34, 35)
    black = item_texture("black_pane")
    gray = item_texture("gray_pane")
    for slot in frame_black:
        paste_item(im, slot, black)

    if state == "pre_spin":
        for slot in (11, 13, 15, 20, 22, 24, 29, 31, 33):
            paste_item(im, slot, gray)
        return

    # A representative visible reel window. The real result is fixed at SPIN;
    # this only chooses which already-existing item textures to show in the mock.
    symbols = [
        ["lemon", "cherry", "bell"],
        ["cherry", "diamond", "bar"],
        ["bell", "seven", "cherry"],
    ]
    if state == "result_777":
        symbols = [["seven", "seven", "seven"]] * 3
    for reel, column in enumerate(symbols):
        slots = (11 + reel * 2, 20 + reel * 2, 29 + reel * 2)
        for slot, symbol in zip(slots, column):
            paste_item(im, slot, custom_slot_texture(symbol))


def render_game(state: str) -> Image.Image:
    im = canvas(6, GUI_FORGE / "src" / "slot_casino" / "_preview_full.png")
    title(im, "슬롯머신", custom=True)
    pane_fill(im, 6, custom=True)

    # render() overwrites slot 4's note block with the paytable book.
    paste_item(im, 4, item_texture("book"))
    render_reels(im, state)

    if state == "pre_spin":
        for slot in (47, 49, 51):
            paste_item(im, slot, custom_texture("slot/ui_lever_up.png"))
        paste_item(im, 53, item_texture("arrow"))
    elif state == "spinning":
        for slot in (47, 49, 51):
            paste_item(im, slot, custom_texture("slot/ui_lever_up.png"))
    elif state == "spinning_one_stop":
        for slot in (47, 49, 51):
            icon = "ui_lever_down.png" if slot == 47 else "ui_lever_up.png"
            paste_item(im, slot, custom_texture(f"slot/{icon}"))
    elif state == "result_777":
        paste_item(im, 49, item_texture("nether_star"))
        paste_item(im, 51, item_texture("lime_dye"))
    return im


def render_bet() -> Image.Image:
    im = canvas(4, GUI_FORGE / "src" / "slot_bet" / "_preview_full.png")
    title(im, "슬롯머신 · 베팅", custom=True)
    pane_fill(im, 4, custom=True)
    paste_item(im, 4, item_texture("note_block"))
    # Same barkan:chip/* assets used by CasinoManager on Java clients.
    for slot, material in zip(
        (10, 12, 14, 16), ("1k", "10k", "100k", "1m")
    ):
        paste_item(im, slot, custom_chip_texture(material))
    return im


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    outputs = {
        "slot_bet_gui.png": render_bet(),
        "slot_game_pre_spin.png": render_game("pre_spin"),
        "slot_game_spinning.png": render_game("spinning"),
        "slot_game_one_lever_down.png": render_game("spinning_one_stop"),
        "slot_game_result_777.png": render_game("result_777"),
    }
    for name, im in outputs.items():
        im.save(OUT / name)
        print(f"{name}: {im.width}x{im.height}")


if __name__ == "__main__":
    main()
