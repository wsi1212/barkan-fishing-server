#!/usr/bin/env python3
"""Compose a /수리 GUI mockup with the real resource-pack item icons.

This is a presentation/QA image only.  It does not change the transparent
runtime background tiles; the source background remains text-free.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "src" / "repair" / "bg_source.png"
OUTPUT = HERE / "src" / "repair" / "_preview_items.png"
RESOURCE_PACK = Path("/Users/user/development/barkan-resourcepack")
ICON_DIR = RESOURCE_PACK / "assets/minecraft/textures/item/barkan_icon"

SCALE = 4
GRID_X = 7
GRID_Y = 17
CELL = 18
ICON_SIZE = 64
ICON_PAD = 4


ICONS = {
    "repair": ICON_DIR / "ui_gui_repair.png",
    "reel": ICON_DIR / "catalog_reel_f3ef2508a3.png",
    "line": ICON_DIR / "catalog_line_53068ab98c.png",
    "hook": ICON_DIR / "catalog_hook_6b5402eaad.png",
    "bobber": ICON_DIR / "catalog_bobber_3a554886b3.png",
    "trap_aqua": ICON_DIR / "catalog_trap_4620a9e505.png",
}


def slot_box(slot: int) -> tuple[int, int, int, int]:
    row, col = divmod(slot, 9)
    x = (GRID_X + CELL * col) * SCALE + ICON_PAD
    y = (GRID_Y + CELL * row) * SCALE + ICON_PAD
    return x, y, x + ICON_SIZE, y + ICON_SIZE


def font(size: int):
    candidates = [
        RESOURCE_PACK / "assets/barkan/font/aggro_bold.ttf",
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/Library/Fonts/Arial Bold.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def icon_image(path: Path, max_subject: int = 56) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        image = image.crop(bbox)
    image.thumbnail((max_subject, max_subject), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    canvas.alpha_composite(
        image,
        ((ICON_SIZE - image.width) // 2, (ICON_SIZE - image.height) // 2),
    )
    return canvas


def paste_item(
    canvas: Image.Image,
    slot: int,
    path: Path,
    *,
    count: int | None = None,
    durability: float | None = None,
    max_subject: int = 56,
) -> None:
    x, y, _, _ = slot_box(slot)
    item = icon_image(path, max_subject)

    # A compact inventory-style shadow keeps bright icons readable over the
    # dark forge plate without altering the actual item texture.
    shadow = Image.new("RGBA", item.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 150), mask=item.getchannel("A"))
    canvas.alpha_composite(shadow, (x + 2, y + 3))
    canvas.alpha_composite(item, (x, y))

    draw = ImageDraw.Draw(canvas)
    if durability is not None:
        bar_x = x + 7
        bar_y = y + 59
        bar_w = 50
        draw.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + 3), fill=(24, 18, 18, 235))
        fill = max(1, int(bar_w * max(0.0, min(1.0, durability))))
        color = (185, 42, 36, 255) if durability < 0.35 else (218, 139, 39, 255)
        draw.rectangle((bar_x, bar_y, bar_x + fill, bar_y + 3), fill=color)

    if count is not None:
        label = str(count)
        text_font = font(17)
        bbox = draw.textbbox((0, 0), label, font=text_font, stroke_width=2)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            (x + ICON_SIZE - tw - 2, y + ICON_SIZE - th - 3),
            label,
            font=text_font,
            fill=(255, 255, 255, 255),
            stroke_width=2,
            stroke_fill=(12, 12, 12, 255),
        )


def main() -> None:
    missing = [str(path) for path in ICONS.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing resource-pack icons:\n" + "\n".join(missing))

    canvas = Image.open(SOURCE).convert("RGBA")

    # Screen slots 12–15 (Bukkit 0-based 11–14): four real equipped parts.
    for slot, key in zip((11, 12, 13, 14), ("reel", "line", "hook", "bobber")):
        paste_item(canvas, slot, ICONS[key], max_subject=55)

    # Screen slot 16 (Bukkit 0-based 15): one real trap stack in the input slot.
    paste_item(canvas, 15, ICONS["trap_aqua"], count=3, durability=0.29)

    # Slot 22: the same actual repair icon used for the action button.
    paste_item(canvas, 22, ICONS["repair"], max_subject=48)

    canvas.save(OUTPUT)
    print(f"wrote {OUTPUT}")
    print("real icons: slots 11-15,22; screen slots 12-16 are reel/line/hook/bobber/trap")


if __name__ == "__main__":
    main()
