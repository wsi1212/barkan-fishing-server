#!/usr/bin/env python3
"""Prepare reviewed emotion variants for the BetterHUD dialogue atlas."""
from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "npc-profiles" / "imagegen-batch" / "revisions" / "emotions-from-headwear" / "transparent"
OUT = SOURCE / "deploy-ready-128x154"
CANVAS = (128, 154)
CONTENT_WIDTH = 118
CONTENT_X = 5
CONTENT_TOP = 19


def prepare(source: Path, target: Path) -> None:
    image = Image.open(source).convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"empty alpha: {source}")
    crop = image.crop(bbox)
    scaled_h = round(crop.height * CONTENT_WIDTH / crop.width)
    scaled = crop.resize((CONTENT_WIDTH, scaled_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    canvas.alpha_composite(scaled, (CONTENT_X, CONTENT_TOP))
    canvas.save(target)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sources = sorted(SOURCE.glob("*.png"))
    if len(sources) != 37:
        raise SystemExit(f"expected 37 reviewed emotion variants, found {len(sources)}")
    for source in sources:
        cid, _, state = source.stem.partition("_")
        # NPC names can contain underscores, so the state is always the suffix.
        state = source.stem.rsplit("_", 1)[-1]
        prepare(source, OUT / f"npc_{cid}_{state}.png")
    print(f"prepared {len(sources)} assets in {OUT}")


if __name__ == "__main__":
    main()
