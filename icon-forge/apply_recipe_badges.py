#!/usr/bin/env python3
"""Apply the shared mixed-color grade seals to every recipe scroll texture."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
BADGES = HERE / "out" / "recipe" / "badges"
RP = Path("/Users/user/development/barkan-resourcepack/assets/minecraft/textures/item/barkan_icon")
GRADES = "edcbas"
CATEGORIES = ("rod", "reel", "line", "hook", "bait", "bobber", "trap", "harpoon")
BADGE_POS = (40, 37)


def build_preview(output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for category in CATEGORIES:
        for grade in GRADES:
            src = RP / f"recipe_{category}_{grade}.png"
            badge = BADGES / f"recipe_badge_{grade}.png"
            if not src.exists() or not badge.exists():
                continue
            icon = Image.open(src).convert("RGBA")
            if icon.size != (64, 64):
                raise SystemExit(f"expected 64x64: {src} -> {icon.size}")
            icon.alpha_composite(Image.open(badge).convert("RGBA"), BADGE_POS)
            icon.save(output_dir / src.name)
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-dir", type=Path, default=None)
    parser.add_argument("--write", action="store_true", help="replace RP recipe textures")
    args = parser.parse_args()
    if not args.preview_dir and not args.write:
        raise SystemExit("choose --preview-dir or --write")

    destination = args.preview_dir or RP
    count = build_preview(destination)
    if args.write and destination != RP:
        raise SystemExit("refusing to write outside the resource pack")
    print(f"prepared {count} graded recipe icons in {destination}")


if __name__ == "__main__":
    main()
