#!/usr/bin/env python3
"""15x15 Minecraft-style stable sign: barn facade + horse-head silhouette.

The native PNG is transparent and intended as a construction reference. The guide
PNG is a nearest-neighbour enlargement with a subtle grid so each pixel maps to one
building block.
"""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

# Reuse the project's hue-shifted ramp generator rather than eyeballing flat colors.
SKILL_SCRIPTS = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "pixel-art" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))
from palette import ramp, rgba  # noqa: E402


OUT_DIR = Path(__file__).resolve().parent / "out"
NATIVE = OUT_DIR / "stable_sign_15x15.png"
GUIDE = OUT_DIR / "stable_sign_15x15_guide.png"


def c(hex_colour: str, step: int = 2):
    return rgba(ramp(hex_colour)[step])


# Three compact material ramps. The final image stays deliberately small in colour
# count so the build remains readable from a distance.
WOOD_SHADOW = c("7a5230", 0)
WOOD_DARK = c("7a5230", 1)
WOOD = c("7a5230", 2)
WOOD_LIGHT = c("7a5230", 3)
ROOF_DARK = c("c0392b", 1)
ROOF = c("c0392b", 2)
ROOF_LIGHT = c("c0392b", 3)
HAY_DARK = c("e0b53b", 1)
HAY = c("e0b53b", 2)
HAY_LIGHT = c("e0b53b", 3)
HORSE_SHADOW = c("e8dcc0", 1)
HORSE = c("e8dcc0", 2)
HORSE_LIGHT = c("e8dcc0", 3)


def rect(draw, box, colour):
    draw.rectangle(box, fill=colour)


def paint() -> Image.Image:
    im = Image.new("RGBA", (15, 15), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    # Barn outline / body. The one-pixel margin keeps the silhouette distinct.
    rect(d, (1, 6, 13, 13), WOOD_SHADOW)
    rect(d, (2, 7, 12, 13), WOOD)
    rect(d, (2, 7, 12, 7), WOOD_DARK)       # heavy lintel under the roof
    rect(d, (2, 8, 3, 13), WOOD_DARK)       # left post in shadow
    rect(d, (11, 8, 12, 13), WOOD_DARK)     # right post in shadow
    rect(d, (3, 8, 4, 12), WOOD_LIGHT)      # top-left light on the timber
    rect(d, (10, 8, 10, 12), WOOD_DARK)     # narrow board seam

    # Gabled roof, stepped to keep a clean 15x15 silhouette.
    for y, lo, hi in ((1, 6, 8), (2, 5, 9), (3, 4, 10), (4, 3, 11), (5, 2, 12), (6, 1, 13)):
        rect(d, (lo, y, hi, y), ROOF_DARK)
    rect(d, (6, 2, 8, 2), ROOF_LIGHT)
    rect(d, (5, 3, 8, 3), ROOF_LIGHT)
    rect(d, (4, 4, 8, 4), ROOF)
    rect(d, (3, 5, 10, 5), ROOF)
    rect(d, (2, 6, 12, 6), ROOF_DARK)        # cool underside / eave shadow
    rect(d, (9, 3, 9, 4), ROOF_DARK)
    rect(d, (10, 4, 10, 5), ROOF_DARK)

    # Deep arched doorway.
    rect(d, (6, 7, 8, 7), WOOD_SHADOW)
    rect(d, (5, 8, 9, 8), WOOD_SHADOW)
    rect(d, (4, 9, 10, 13), WOOD_SHADOW)
    rect(d, (5, 9, 9, 13), WOOD_DARK)

    # Hay blocks at the foot of the facade: a small warm cue that reads at distance.
    rect(d, (2, 11, 3, 13), HAY_DARK)
    rect(d, (2, 11, 3, 11), HAY_LIGHT)
    rect(d, (2, 12, 3, 13), HAY)
    rect(d, (11, 11, 12, 13), HAY_DARK)
    rect(d, (11, 11, 12, 11), HAY_LIGHT)
    rect(d, (11, 12, 12, 13), HAY)

    # Horse-head silhouette facing right. The long muzzle and two ears are the
    # highest-read feature; the mane stays in shadow so it remains legible in the door.
    horse_shadow = {
        (6, 7), (8, 7),
        (5, 8), (6, 8), (7, 8), (8, 8),
        (5, 9), (6, 9), (7, 9), (8, 9), (9, 9),
        (5, 10), (6, 10), (7, 10), (8, 10), (9, 10), (10, 10),
        (5, 11), (6, 11), (7, 11), (8, 11),
        (4, 12), (5, 12), (6, 12), (7, 12),
        (4, 13), (5, 13), (6, 13),
    }
    for x, y in horse_shadow:
        d.point((x, y), fill=HORSE_SHADOW)

    horse_base = {
        (6, 7), (8, 7),
        (6, 8), (7, 8), (8, 8),
        (6, 9), (7, 9), (8, 9), (9, 9),
        (6, 10), (7, 10), (8, 10), (9, 10),
        (6, 11), (7, 11),
        (5, 12), (6, 12),
        (5, 13),
    }
    for x, y in horse_base:
        d.point((x, y), fill=HORSE)

    # Top-left light on forehead and muzzle; dark eye/nostril preserve expression.
    for xy in ((7, 8), (8, 9), (9, 10)):
        d.point(xy, fill=HORSE_LIGHT)
    d.point((8, 9), fill=WOOD_SHADOW)          # eye
    d.point((10, 10), fill=WOOD_SHADOW)        # nostril
    d.point((5, 8), fill=HORSE_SHADOW)         # mane edge
    d.point((4, 12), fill=HORSE_SHADOW)        # neck edge

    return im


def make_guide(native: Image.Image) -> Image.Image:
    scale = 32
    enlarged = native.resize((native.width * scale, native.height * scale), Image.Resampling.NEAREST)
    bg = Image.new("RGBA", enlarged.size, (35, 39, 45, 255))
    bg.alpha_composite(enlarged)
    g = ImageDraw.Draw(bg)
    grid = (80, 86, 94, 130)
    for i in range(0, enlarged.width + 1, scale):
        g.line((i, 0, i, enlarged.height), fill=grid, width=1)
    for i in range(0, enlarged.height + 1, scale):
        g.line((0, i, enlarged.width, i), fill=grid, width=1)
    return bg


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    native = paint()
    native.save(NATIVE)
    make_guide(native).save(GUIDE)
    print(NATIVE)
    print(GUIDE)
