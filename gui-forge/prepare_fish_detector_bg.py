#!/usr/bin/env python3
"""Fit the ImageGen underwater detector art to a fixed 54-slot GUI plate."""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
RAW = HERE / "src" / "fish_detector_bg_imagegen.png"
OUT = HERE / "src" / "fish_detector" / "bg_source.png"
W, H = 704, 888


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"원화가 없습니다: {RAW}")
    raw = Image.open(RAW).convert("RGBA")
    fitted = raw.resize((W, W), Image.Resampling.LANCZOS)
    im = Image.new("RGBA", (W, H), (7, 17, 24, 255))
    im.paste(fitted, (0, 0))
    # The 6-row top inventory ends at art y=552.  Keep a dark underwater
    # continuation behind the deterministic player inventory grid.
    draw = ImageDraw.Draw(im)
    draw.rectangle((24, 548, 680, 887), fill=(7, 17, 24, 255))
    draw.line((28, 548, 676, 548), fill=(53, 103, 110, 255), width=4)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(OUT)
    print(f"초음파 탐지기 전용 판 → {OUT} (원화 {raw.size} → {W}x{H})")


if __name__ == "__main__":
    main()
