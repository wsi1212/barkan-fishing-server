#!/usr/bin/env python3
"""Build the two 3-row specialty GUI plates.

Both pages keep the tested 704x672 workbench frame and inventory region, but
replace the forge wall with a distinct top scene.  Runtime item sockets are
stamped from already-tested socket cells so the Java slot coordinates remain
the single source of truth.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps


HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
BASE_PATH = SRC / "workbench" / "bg_source.png"
ENHANCE_PATH = SRC / "enhance" / "bg_source.png"
PLATE = (704, 672)
SCALE = 4
GRID_X, GRID_Y, CELL = 7, 17, 18
PITCH = CELL * SCALE
# The GUI's inner art runs from GRID_X=7, not from screen slot column 1.
# Keeping that distinction is what makes the scene line up with the 72px sockets.
TOP = (7 * SCALE, 17 * SCALE, (7 + CELL * 9) * SCALE, 81 * SCALE)


def cell_box(slot: int) -> tuple[int, int, int, int]:
    row, col = divmod(slot, 9)
    x0 = (GRID_X + CELL * col) * SCALE
    y0 = (GRID_Y + CELL * row) * SCALE
    return x0, y0, x0 + PITCH, y0 + PITCH


def copy_cell(src: Image.Image, slot: int) -> Image.Image:
    return src.crop(cell_box(slot)).copy()


def paste_cell(dst: Image.Image, src: Image.Image, slot: int) -> None:
    x0, y0, _, _ = cell_box(slot)
    dst.alpha_composite(src, (x0, y0))


def textured_panel(size: tuple[int, int], base: tuple[int, int, int], seed: int) -> Image.Image:
    """Make a dense, quiet material texture that still reads after 4x scaling."""
    noise = Image.effect_noise(size, 30 + seed % 9).convert("L")
    ramp = ImageOps.colorize(noise, black=tuple(max(0, c - 26) for c in base), white=tuple(min(255, c + 30) for c in base))
    ramp = ramp.filter(ImageFilter.GaussianBlur(0.7))
    return ramp.convert("RGBA")


def replace_scene(im: Image.Image, panel: Image.Image) -> Image.Image:
    out = im.copy()
    out.alpha_composite(panel, (TOP[0], TOP[1]))
    return out


def artifact_scene(base: Image.Image) -> Image.Image:
    full_size = (TOP[2] - TOP[0], TOP[3] - TOP[1])
    # Draw the motif at the old 564px composition width, then center it on the
    # full 648px grid panel. This keeps the central socket visually centered.
    motif = textured_panel((564, full_size[1]), (116, 78, 43), 17)
    d = ImageDraw.Draw(motif, "RGBA")
    w, h = motif.size

    # Sun-baked sandstone courses, kept behind all item sockets.
    for y in range(18, h, 42):
        d.line((0, y, w, y), fill=(48, 28, 16, 130), width=3)
        d.line((0, y + 3, w, y + 3), fill=(214, 155, 82, 55), width=2)
    for x in range(-38, w + 40, 92):
        for y in range(18, h, 42):
            offset = 46 if (y // 42) % 2 else 0
            d.line((x + offset, y, x + offset, min(h, y + 42)), fill=(54, 31, 17, 105), width=3)

    # Central archaeologist's slab: the one input slot is the artifact cradle.
    d.rounded_rectangle((250, 72, 314, 223), radius=7, fill=(49, 29, 18, 185), outline=(231, 174, 94, 180), width=3)
    d.rectangle((238, 213, 327, 236), fill=(70, 39, 20, 220), outline=(222, 154, 75, 150), width=3)
    d.line((245, 218, 322, 218), fill=(255, 208, 122, 120), width=2)

    # Left: brush, scroll and specimen jar. Right: oil lamp and folded map.
    d.rectangle((29, 102, 43, 226), fill=(49, 27, 17, 220), outline=(202, 135, 62, 180), width=3)
    d.line((36, 108, 62, 83), fill=(211, 147, 69, 220), width=5)
    d.line((39, 113, 66, 90), fill=(246, 204, 125, 130), width=2)
    d.ellipse((62, 184, 105, 230), fill=(54, 39, 28, 235), outline=(224, 165, 92, 160), width=3)
    d.ellipse((70, 191, 97, 220), fill=(180, 111, 44, 110))
    d.polygon([(473, 179), (534, 163), (554, 203), (489, 219)], fill=(197, 145, 76, 180), outline=(55, 31, 17, 210))
    for y in (180, 190, 200):
        d.line((487, y, 530, y - 11), fill=(255, 220, 148, 110), width=2)
    d.rectangle((583, 176, 612, 228), fill=(49, 27, 16, 235), outline=(226, 165, 78, 180), width=3)
    d.ellipse((588, 157, 607, 181), fill=(255, 180, 55, 210), outline=(255, 228, 138, 150), width=2)
    d.line((598, 156, 598, 143), fill=(235, 180, 88, 180), width=3)

    # Small brass corner studs make the panel feel like a dedicated station.
    for x, y in ((12, 11), (w - 12, 11), (12, h - 12), (w - 12, h - 12)):
        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(238, 182, 88, 200), outline=(70, 39, 20, 230), width=2)

    panel = textured_panel(full_size, (116, 78, 43), 19)
    panel.alpha_composite(motif, ((full_size[0] - motif.width) // 2, 0))
    out = replace_scene(base, panel)
    socket = copy_cell(base, 11)
    paste_cell(out, socket, 13)  # SLOT_INPUT
    paste_cell(out, copy_cell(Image.open(ENHANCE_PATH).convert("RGBA"), 40), 26)  # SLOT_CLOSE
    out.putalpha(255)
    return out


def horseshoe(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple[int, int, int, int]) -> None:
    # A thick open horseshoe, drawn as concentric arcs with square-ish nails.
    d.arc((cx - r, cy - r, cx + r, cy + r), 210, 510, fill=color, width=7)
    d.arc((cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8), 210, 510, fill=(35, 23, 18, 220), width=3)
    for angle in (225, 270, 315):
        import math
        rad = math.radians(angle)
        x = int(cx + (r - 3) * math.cos(rad))
        y = int(cy + (r - 3) * math.sin(rad))
        d.rectangle((x - 3, y - 3, x + 3, y + 3), fill=(221, 159, 74, 210))


def horse_scene(base: Image.Image) -> Image.Image:
    full_size = (TOP[2] - TOP[0], TOP[3] - TOP[1])
    motif = textured_panel((564, full_size[1]), (81, 48, 29), 31)
    d = ImageDraw.Draw(motif, "RGBA")
    w, h = motif.size

    # Stable planks and a darker lower kickboard.
    for y in range(8, h, 38):
        d.line((0, y, w, y), fill=(27, 16, 12, 210), width=4)
        d.line((0, y + 4, w, y + 4), fill=(176, 108, 53, 95), width=2)
    for x in range(30, w, 108):
        d.line((x, 0, x, h), fill=(35, 21, 15, 150), width=4)
    d.rectangle((0, 226, w, h), fill=(34, 22, 17, 180))
    d.line((0, 226, w, 226), fill=(218, 145, 70, 170), width=4)

    # Horizontal stall rails behind the four evenly spaced tier cards.
    for y in (78, 214):
        d.rectangle((18, y, w - 18, y + 10), fill=(43, 26, 18, 235), outline=(198, 119, 57, 190), width=3)
        d.line((22, y + 3, w - 22, y + 3), fill=(241, 176, 91, 120), width=2)
    for x in (52, 154, 256, 358, 460, 562):
        d.rectangle((x, 70, x + 9, 232), fill=(45, 27, 18, 230), outline=(192, 113, 53, 160), width=2)

    # Tack room details on both sides leave the center readable.
    horseshoe(d, 69, 118, 31, (188, 126, 58, 230))
    horseshoe(d, w - 68, 119, 31, (188, 126, 58, 230))
    d.line((86, 35, 111, 95), fill=(214, 151, 74, 210), width=5)
    d.line((102, 35, 125, 95), fill=(138, 78, 39, 220), width=7)
    d.line((w - 111, 35, w - 86, 95), fill=(214, 151, 74, 210), width=5)
    d.line((w - 125, 35, w - 102, 95), fill=(138, 78, 39, 220), width=7)

    # A warm lantern and hay-colored ground accent the stable without text.
    d.rectangle((24, 238, 75, 258), fill=(200, 145, 67, 170), outline=(55, 31, 20, 220), width=3)
    for x in range(30, 72, 9):
        d.line((x, 242, x + 12, 256), fill=(247, 197, 112, 100), width=3)
    d.rectangle((w - 75, 238, w - 24, 258), fill=(200, 145, 67, 170), outline=(55, 31, 20, 220), width=3)
    d.ellipse((w // 2 - 12, 8, w // 2 + 12, 32), fill=(244, 176, 76, 180), outline=(255, 220, 130, 130), width=2)

    panel = textured_panel(full_size, (81, 48, 29), 37)
    panel.alpha_composite(motif, ((full_size[0] - motif.width) // 2, 0))
    out = replace_scene(base, panel)
    paste_cell(out, copy_cell(base, 4), 4)  # balance/info
    tier_socket = copy_cell(base, 11)
    for slot in (10, 12, 14, 16):
        paste_cell(out, tier_socket, slot)
    paste_cell(out, copy_cell(Image.open(ENHANCE_PATH).convert("RGBA"), 40), 22)  # optional summon
    out.putalpha(255)
    return out


def main() -> None:
    base = Image.open(BASE_PATH).convert("RGBA")
    if base.size != PLATE:
        raise SystemExit(f"base size {base.size} != {PLATE}")
    artifact = SRC / "artifact"
    horse = SRC / "horse"
    artifact.mkdir(parents=True, exist_ok=True)
    horse.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact / "bg_source.png"
    horse_path = horse / "bg_source.png"

    # Once imagegen scenes have been adopted, keep this historical one-command
    # entrypoint from silently replacing them with the procedural fallback.
    if (artifact / "bg_imagegen.png").exists() and (horse / "bg_imagegen.png").exists():
        from adopt_imagegen_bg import adopt
        adopt("artifact", (13, 26))
        adopt("horse", (10, 12, 14, 16))
        return

    artifact_scene(base).save(artifact_path)
    horse_scene(base).save(horse_path)
    print(f"artifact plate -> {artifact_path} (704x672, opaque)")
    print(f"horse plate    -> {horse_path} (704x672, opaque)")


if __name__ == "__main__":
    main()
