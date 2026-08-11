#!/usr/bin/env python3
"""ImageGen badge master → grade variants → 64px harpoon recipe icons.

The badge is generated once as a pixel-art master and recolored deterministically
for E/D/C/B/A/S so every grade keeps the same silhouette and shading.
"""
from __future__ import annotations

import colorsys
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "recipe"
BADGES = OUT / "badges"
MASTER = BADGES / "badge_master.png"
BASE = OUT / "harpoon_base_balanced.png"

# Existing recipe icons use this lower-right seal center. The 13px overlay
# lands over the old 9px fill plus its dark stepped rim without moving the scroll.
BADGE_SIZE = 13
BADGE_POS = (40, 37)

# Two-tone ramps: primary material, secondary edge glow, and a small highlight
# tint. This keeps grade identity while avoiding six flat color circles.
GRADE_PALETTE = {
    "e": ("526577", "b9cbd8", "eef4f6"),  # steel / ice glint
    "d": ("23734f", "45bfa0", "c7f2d8"),  # emerald / jade glint
    "c": ("1f5794", "4fc8c6", "d8f4e8"),  # ocean / cyan glint
    "b": ("38245f", "8254aa", "d8c8e8"),  # restrained indigo / violet glint
    "a": ("a84f0c", "f2bd24", "fff6b8"),  # bright amber / gold glint
    "s": ("7f1730", "d94d35", "ffe0a0"),  # crimson / gold-ember glint
}


def crop_badge(master: Image.Image) -> Image.Image:
    alpha = master.getchannel("A")
    box = alpha.getbbox()
    if not box:
        raise RuntimeError("badge master has no opaque pixels")
    return master.crop(box).resize((BADGE_SIZE, BADGE_SIZE), Image.Resampling.LANCZOS)


def recolor(master: Image.Image, palette: tuple[str, str, str]) -> Image.Image:
    primary, secondary, highlight = palette
    ramps = [
        tuple(int(primary[i : i + 2], 16) for i in (0, 2, 4)),
        tuple(int(secondary[i : i + 2], 16) for i in (0, 2, 4)),
        tuple(int(highlight[i : i + 2], 16) for i in (0, 2, 4)),
    ]
    src = master.convert("RGBA")
    out = Image.new("RGBA", src.size, (0, 0, 0, 0))
    sp = src.load()
    dp = out.load()
    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = sp[x, y]
            if a == 0:
                continue
            _, source_lightness, _ = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            # Map the ImageGen bevel into visibly separate material bands:
            # dark primary rim → colored secondary bevel → pale highlight core.
            # This reads as a mixed material even at the final 13px size.
            if source_lightness < 0.32:
                depth = 0.62 + source_lightness * 0.9
                rgb = tuple(round(v * depth) for v in ramps[0])
            elif source_lightness < 0.58:
                u = (source_lightness - 0.32) / 0.26
                rgb = tuple(round(ramps[0][i] * (1 - u) + ramps[1][i] * u) for i in range(3))
            elif source_lightness < 0.80:
                u = (source_lightness - 0.58) / 0.22
                rgb = tuple(round(ramps[1][i] * (1 - u) + ramps[2][i] * u) for i in range(3))
            else:
                rgb = ramps[2]
            dp[x, y] = (*rgb, a)
    return out


def main() -> None:
    if not MASTER.exists() or not BASE.exists():
        raise SystemExit(f"missing input: {MASTER} or {BASE}")
    BADGES.mkdir(parents=True, exist_ok=True)
    master = crop_badge(Image.open(MASTER))
    base = Image.open(BASE).convert("RGBA")
    if base.size != (64, 64):
        raise SystemExit(f"harpoon base must be 64x64, got {base.size}")

    for grade, palette in GRADE_PALETTE.items():
        badge = recolor(master, palette)
        badge_path = BADGES / f"recipe_badge_{grade}.png"
        # Standalone 13px badge, useful for future recipe overlays.
        badge.save(badge_path)

        icon = base.copy()
        icon.alpha_composite(badge, BADGE_POS)
        icon.save(OUT / f"harpoon_{grade}.png")

    print(f"wrote {len(GRADE_PALETTE)} mixed-color badges and harpoon icons to {OUT}")


if __name__ == "__main__":
    main()
