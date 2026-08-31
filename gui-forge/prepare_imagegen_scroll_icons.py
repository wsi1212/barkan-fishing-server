#!/usr/bin/env python3
"""Install the imagegen travel-scroll sources at the native 16x16 item size.

The large transparent sources stay under gui-forge/src/scroll for traceability;
this script only crops transparent margins, downsizes, and applies the same
hard-alpha/limited-palette treatment used by the portable bundle icon.
"""

from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "gui-forge" / "src" / "scroll"
OUT = ROOT / "icon-forge" / "imagegen-warp"


def fit_icon(source: Path, size: int = 16, subject_box: int = 14) -> Image.Image:
    image = Image.open(source).convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"image has no opaque subject: {source}")
    subject = image.crop(bbox)
    subject = ImageOps.contain(subject, (subject_box, subject_box), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - subject.width) // 2
    y = (size - subject.height) // 2
    canvas.alpha_composite(subject, (x, y))

    # Keep the generated palette readable at 16px and remove fringe alpha.
    alpha = canvas.getchannel("A").point(lambda value: 255 if value >= 64 else 0)
    rgb = canvas.convert("RGB").quantize(
        colors=24, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
    ).convert("RGB").convert("RGBA")
    rgb.putalpha(alpha)
    return rgb


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for ident in ("spawn", "desert", "merchant", "royal"):
        src = SOURCE / f"imagegen_warp_{ident}_raw.png"
        dst = OUT / f"ui_scroll_warp_{ident}_native.png"
        fit_icon(src).save(dst)
        print(f"  {dst.name}: {Image.open(dst).size}")


if __name__ == "__main__":
    main()
