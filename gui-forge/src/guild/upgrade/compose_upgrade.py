from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent
CANVAS = (704, 888)


def resized_background() -> Image.Image:
    image = Image.open(ROOT / "sources" / "background_imagegen.png").convert("RGBA")
    return image.resize(CANVAS, Image.Resampling.LANCZOS)


def socket_centers() -> list[tuple[int, int]]:
    # 64px holes, 72px pitch. This is the locked guild-upgrade layout.
    centers = [(64, 104), (208, 176)]
    centers += [(x, y) for y in (248, 320, 392) for x in (136, 208, 280)]
    centers += [(496, 176)]
    centers += [(x, y) for y in (248, 320, 392) for x in (424, 496, 568)]
    return centers


def glow_line(layer: Image.Image, points: list[tuple[int, int]], width: int = 2) -> None:
    scale = 4
    glow = Image.new("RGBA", (CANVAS[0] * scale, CANVAS[1] * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    scaled = [(x * scale, y * scale) for x, y in points]
    draw.line(scaled, fill=(0, 180, 220, 125), width=(width + 7) * scale, joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(5 * scale))
    glow = glow.resize(CANVAS, Image.Resampling.LANCZOS)
    layer.alpha_composite(glow)

    draw = ImageDraw.Draw(layer)
    draw.line(points, fill=(31, 166, 184, 150), width=width, joint="curve")
    draw.line(points, fill=(205, 119, 43, 160), width=1, joint="curve")


def add_connection_effects(base: Image.Image, centers: list[tuple[int, int]]) -> Image.Image:
    effects = Image.new("RGBA", CANVAS, (0, 0, 0, 0))

    # Subtle cyan/gold conduits behind each 3x3 upgrade block.
    for x0, x1 in ((136, 280), (424, 568)):
        mid = (x0 + x1) // 2
        glow_line(effects, [(mid, 176), (mid, 208), (mid, 248), (mid, 392)], width=2)
        for y in (248, 320, 392):
            glow_line(effects, [(x0, y), (x1, y)], width=2)

        # Decorative outer arcs reinforce the original guild-workbench feel.
        draw = ImageDraw.Draw(effects)
        box = (x0 - 48, 148, x1 + 48, 440)
        draw.arc(box, 190, 350, fill=(193, 112, 36, 180), width=2)
        draw.arc(box, 10, 170, fill=(28, 148, 174, 140), width=2)

        # Small brass/cyan connection nodes outside the socket holes.
        for x in (x0 - 20, x1 + 20):
            for y in (224, 296, 368, 416):
                draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(207, 129, 43, 210), outline=(48, 192, 204, 190))

    # Mask all socket rectangles so no effect can paint over a hole or frame.
    mask = Image.new("L", CANVAS, 0)
    mask_draw = ImageDraw.Draw(mask)
    for cx, cy in centers:
        mask_draw.rectangle((cx - 36, cy - 36, cx + 36, cy + 36), fill=255)
    effects.putalpha(Image.composite(Image.new("L", CANVAS, 0), effects.getchannel("A"), mask))

    base.alpha_composite(effects)
    effects.convert("RGBA").save(ROOT / "connection_effects.png")
    return base


def add_slots(base: Image.Image, centers: list[tuple[int, int]]) -> Image.Image:
    source = Image.open(ROOT / "cutouts" / "socket_frame.png").convert("RGBA")
    bbox = source.getchannel("A").getbbox()
    if bbox is None:
        raise RuntimeError("socket frame has no alpha")
    source = source.crop(bbox).resize((72, 72), Image.Resampling.LANCZOS)
    for cx, cy in centers:
        base.alpha_composite(source, (cx - 36, cy - 36))
    source.save(ROOT / "socket_frame_72x72.png")
    return base


def add_central_conduit(base: Image.Image) -> Image.Image:
    source = Image.open(ROOT / "cutouts" / "central_conduit.png").convert("RGBA")
    bbox = source.getchannel("A").getbbox()
    if bbox is None:
        raise RuntimeError("central conduit has no alpha")
    source = source.crop(bbox)
    source.thumbnail((52, 204), Image.Resampling.LANCZOS)
    x = round(352 - source.width / 2)
    y = round(320 - source.height / 2)
    base.alpha_composite(source, (x, y))
    source.save(ROOT / "central_conduit_placed.png")
    return base


def make_verification(image: Image.Image, centers: list[tuple[int, int]]) -> None:
    guide = image.convert("RGBA").copy()
    draw = ImageDraw.Draw(guide)
    draw.rectangle((28, 25, 676, 64), outline=(70, 180, 255, 255), width=2)
    draw.rectangle((28, 553, 676, 856), outline=(0, 255, 100, 255), width=2)
    for index, (cx, cy) in enumerate(centers):
        draw.rectangle((cx - 32, cy - 32, cx + 32, cy + 32), outline=(255, 30, 40, 255), width=2)
        draw.text((cx - 29, cy - 29), str(index), fill=(255, 245, 0, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))
    draw.rectangle((320, 216, 384, 424), outline=(50, 220, 255, 255), width=2)
    draw.text((322, 426), "1칸 공백", fill=(50, 220, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))
    guide.convert("RGB").save(ROOT / "verification" / "guild_upgrade_guide_overlay.png")


def main() -> None:
    centers = socket_centers()
    if len(centers) != 21:
        raise RuntimeError(f"expected 21 sockets, got {len(centers)}")
    image = resized_background()
    image = add_connection_effects(image, centers)
    image = add_slots(image, centers)
    image = add_central_conduit(image)
    image.convert("RGB").save(ROOT / "guild_upgrade_final_704x888.png")
    make_verification(image, centers)
    print(f"saved {ROOT / 'guild_upgrade_final_704x888.png'}")
    print(f"socket_count={len(centers)} canvas={image.size}")


if __name__ == "__main__":
    main()
