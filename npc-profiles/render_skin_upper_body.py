#!/usr/bin/env python3
"""Render a transparent Minecraft skin head-and-torso portrait.

The result deliberately uses the exact pixels from the signed Citizens skin.  It
is intended for staff or player statues where an illustrated NPC portrait would
misrepresent the in-world skin.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def layer(dst: Image.Image, skin: Image.Image, base: tuple[int, int, int, int],
          overlay: tuple[int, int, int, int], at: tuple[int, int]) -> None:
    """Place a base body part and its outer clothing layer at *at*."""
    dst.alpha_composite(skin.crop(base), at)
    dst.alpha_composite(skin.crop(overlay), at)


def render(skin_path: Path, output_path: Path, scale: int) -> None:
    skin = Image.open(skin_path).convert("RGBA")
    if skin.size != (64, 64):
        raise ValueError(f"Expected a modern 64x64 Minecraft skin, got {skin.size}: {skin_path}")

    # 16x20 logical pixels: an eight-pixel head, 12-pixel torso, and both arms.
    portrait = Image.new("RGBA", (16, 20), (0, 0, 0, 0))
    layer(portrait, skin, (8, 8, 16, 16), (40, 8, 48, 16), (4, 0))       # head + hat
    layer(portrait, skin, (44, 20, 48, 32), (44, 36, 48, 48), (0, 8))    # right arm
    layer(portrait, skin, (20, 20, 28, 32), (20, 36, 28, 48), (4, 8))    # torso + jacket
    layer(portrait, skin, (36, 52, 40, 64), (52, 52, 56, 64), (12, 8))  # left arm

    output_path.parent.mkdir(parents=True, exist_ok=True)
    portrait.resize((portrait.width * scale, portrait.height * scale), Image.Resampling.NEAREST).save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skin", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scale", type=int, default=16)
    args = parser.parse_args()
    render(args.skin, args.output, args.scale)


if __name__ == "__main__":
    main()
