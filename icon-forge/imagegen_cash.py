"""ImageGen cash-art normalizer for 32x32 GUI reward textures.

The source art stays high-resolution for future edits. This module turns each
transparent source into a hard-alpha, palette-limited 32x32 item texture so the
resource pack gets a real high-resolution icon instead of the old 16x16 painter.
"""
from PIL import Image


def prepare(path, size=32, margin=2, colors=14):
    source = Image.open(path).convert("RGBA")
    alpha = source.getchannel("A")
    visible = alpha.point(lambda value: 255 if value >= 8 else 0)
    bbox = visible.getbbox()
    if bbox is None:
        raise ValueError(f"ImageGen source has no visible pixels: {path}")
    source = source.crop(bbox)
    alpha = source.getchannel("A")

    limit = size - margin * 2
    scale = min(limit / source.width, limit / source.height)
    dims = (max(1, round(source.width * scale)), max(1, round(source.height * scale)))
    rgb = source.convert("RGB").resize(dims, Image.Resampling.LANCZOS)
    # ImageGen shading is rich; cap the final icon at a compact palette while
    # retaining its generated pixel-art character.
    rgb = rgb.quantize(colors=colors, method=Image.Quantize.MEDIANCUT,
                       dither=Image.Dither.NONE).convert("RGBA")
    alpha = alpha.resize(dims, Image.Resampling.LANCZOS)
    alpha = alpha.point(lambda value: 255 if value >= 96 else 0)
    rgb.putalpha(alpha)
    # Replace ImageGen's occasional pure-black outline with a warm dark-ramp
    # color; item-icons forbids a dead #000 border on inventory backgrounds.
    pixels = rgb.load()
    for y in range(rgb.height):
        for x in range(rgb.width):
            r, g, b, a = pixels[x, y]
            if a and r == 0 and g == 0 and b == 0:
                pixels[x, y] = (38, 22, 27, a)

    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.alpha_composite(rgb, ((size - dims[0]) // 2, (size - dims[1]) // 2))
    return out
