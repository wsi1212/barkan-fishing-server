#!/usr/bin/env python3
"""Install the selected imagegen icon sources at the pack's native sizes.

The generated source is intentionally kept in gui-forge/src/backpack so a
future asset pass can trace the final pixels back to the imagegen output.
This script only crops transparent margins and resizes; it does not redraw
the icon.
"""

from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "gui-forge" / "src" / "backpack"
PACK = Path("/Users/user/development/barkan-resourcepack")
PACK_ICONS = PACK / "assets/minecraft/textures/item/barkan_icon"
OUT = ROOT / "icon-forge" / "out"
NATIVE_SOURCES = ROOT / "icon-forge" / "imagegen-backpack"


def fit_transparent(source: Path, size: int, subject_box: int) -> Image.Image:
    image = Image.open(source).convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError(f"image has no opaque subject: {source}")
    subject = image.crop(bbox)
    subject = ImageOps.contain(subject, (subject_box, subject_box), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - subject.width) // 2
    y = (size - subject.height) // 2
    canvas.alpha_composite(subject, (x, y))
    return canvas


def harden_and_limit_bundle(image: Image.Image) -> Image.Image:
    """Keep imagegen's colors while making the 16px item texture hard-alpha."""
    alpha = image.getchannel("A").point(lambda value: 255 if value >= 64 else 0)
    rgb = image.convert("RGB").quantize(
        colors=14, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
    ).convert("RGB").convert("RGBA")
    pixels = []
    for red, green, blue, _ in rgb.get_flattened_data():
        if (red, green, blue) == (0, 0, 0):
            red, green, blue = 18, 12, 8
        pixels.append((red, green, blue, 255))
    rgb.putdata(pixels)
    rgb.putalpha(alpha)
    return rgb


def main() -> None:
    menu = fit_transparent(SOURCE / "imagegen_virtual_storage_raw.png", 128, 116)
    bundle = harden_and_limit_bundle(
        fit_transparent(SOURCE / "imagegen_portable_bundle_raw.png", 16, 14)
    )

    PACK_ICONS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    NATIVE_SOURCES.mkdir(parents=True, exist_ok=True)
    menu.save(PACK_ICONS / "ui_menu_backpack.png")
    bundle.save(PACK_ICONS / "portable_bundle.png")
    menu.save(NATIVE_SOURCES / "ui_menu_backpack_native.png")
    bundle.save(NATIVE_SOURCES / "portable_bundle_native.png")
    menu.save(OUT / "ui_menu_backpack.png")
    bundle.save(OUT / "portable_bundle.png")
    print("installed imagegen icons:")
    print(f"  ui_menu_backpack.png  {menu.size}")
    print(f"  portable_bundle.png    {bundle.size}")


if __name__ == "__main__":
    main()
