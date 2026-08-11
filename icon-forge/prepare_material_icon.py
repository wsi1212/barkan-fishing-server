#!/usr/bin/env python3
"""Crop a chroma-keyed ImageGen material and normalize it to a 256px icon."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: prepare_material_icon.py <rgba-source> <out.png>")
    src, dst = map(Path, sys.argv[1:])
    im = Image.open(src).convert("RGBA")
    box = im.getchannel("A").getbbox()
    if not box:
        raise SystemExit(f"no opaque subject: {src}")
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    pad = max(8, round(max(w, h) * 0.10))
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(im.width, x1 + pad), min(im.height, y1 + pad)
    crop = im.crop((x0, y0, x1, y1))
    side = max(crop.width, crop.height)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(crop, ((side - crop.width) // 2, (side - crop.height) // 2))
    final = canvas.resize((256, 256), Image.Resampling.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    final.save(dst)
    print(f"{dst}: {final.size}, alpha_bbox={final.getchannel('A').getbbox()}")


if __name__ == "__main__":
    main()
