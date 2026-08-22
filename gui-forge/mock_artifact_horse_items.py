#!/usr/bin/env python3
"""Compose presentation previews with the actual Java GUI item materials.

This script only writes QA images. It reads vanilla 1.21.3 item textures
from the installed client jar and the ImageGen-backed horse item textures
from the resource pack; no runtime texture is invented here.
"""
from io import BytesIO
from pathlib import Path
import zipfile

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
RESOURCE_PACK = Path("/Users/user/development/barkan-resourcepack")
ICON_DIR = RESOURCE_PACK / "assets/minecraft/textures/item/barkan_icon"
JAR_CANDIDATES = [
    Path.home() / "Library/Application Support/minecraft/versions/1.21.3/1.21.3.jar",
    Path.home() / "Library/Application Support/minecraft/versions/1.21.10/1.21.10.jar",
]

SCALE = 4
GRID_X, GRID_Y, CELL = 7, 17, 18
ICON_SIZE = 64
ICON_PAD = 4


def slot_box(slot: int) -> tuple[int, int, int, int]:
    row, col = divmod(slot, 9)
    x = (GRID_X + CELL * col) * SCALE + ICON_PAD
    y = (GRID_Y + CELL * row) * SCALE + ICON_PAD
    return x, y, x + ICON_SIZE, y + ICON_SIZE


def jar_path() -> Path:
    for path in JAR_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("Minecraft 1.21.x client jar not found")


def vanilla_icon(name: str) -> Image.Image:
    path = f"assets/minecraft/textures/item/{name}.png"
    with zipfile.ZipFile(jar_path()) as jar:
        image = Image.open(BytesIO(jar.read(path))).convert("RGBA")
    return image


def custom_icon(name: str) -> Image.Image:
    return Image.open(ICON_DIR / f"{name}.png").convert("RGBA")


def icon_image(image: Image.Image, max_subject: int = 56) -> Image.Image:
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        image = image.crop(bbox)
    image.thumbnail((max_subject, max_subject), Image.Resampling.NEAREST)
    canvas = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    canvas.alpha_composite(image, ((ICON_SIZE - image.width) // 2, (ICON_SIZE - image.height) // 2))
    return canvas


def paste_item(canvas: Image.Image, slot: int, icon: Image.Image, *, max_subject: int = 56) -> None:
    x, y, _, _ = slot_box(slot)
    item = icon_image(icon, max_subject)
    shadow = Image.new("RGBA", item.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 155), mask=item.getchannel("A"))
    canvas.alpha_composite(shadow, (x + 2, y + 3))
    canvas.alpha_composite(item, (x, y))


def save_artifact() -> None:
    canvas = Image.open(SRC / "artifact" / "bg_source.png").convert("RGBA")
    paste_item(canvas, 13, vanilla_icon("clay_ball"), max_subject=54)
    paste_item(canvas, 26, vanilla_icon("barrier"), max_subject=48)
    out = SRC / "artifact" / "_preview_items.png"
    canvas.save(out)
    print(f"artifact preview -> {out}")


def save_horse() -> None:
    canvas = Image.open(SRC / "horse" / "bg_source.png").convert("RGBA")
    for slot, tier in zip((10, 12, 14, 16), ("pony", "brown", "white", "black")):
        paste_item(canvas, slot, custom_icon(f"horse_{tier}"), max_subject=56)
    paste_item(canvas, 22, custom_icon("ui_gui_horse"), max_subject=48)
    out = SRC / "horse" / "_preview_items.png"
    canvas.save(out)
    print(f"horse preview    -> {out}")


if __name__ == "__main__":
    save_artifact()
    save_horse()
