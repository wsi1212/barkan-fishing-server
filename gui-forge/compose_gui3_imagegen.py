#!/usr/bin/env python3
"""Composite imagegen-rendered tile interiors into the exact GUI3 coordinates."""
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import build_gui3_bg
from build_gui3_bg import FONT, OUT, SRC, W, H, COLS, center_text

GEN = {
    "menu": Path("/Users/user/.codex/generated_images/019fcffa-2416-7661-aab4-db32e8a6de57/exec-d62989e1-9ceb-4acb-bff2-01f767fa16b9.png"),
    "myinfo": Path("/Users/user/.codex/generated_images/019fcffa-2416-7661-aab4-db32e8a6de57/exec-9d3964c5-081d-4aa6-83ed-30431e09d436.png"),
    "shop": Path("/Users/user/.codex/generated_images/019fcffa-2416-7661-aab4-db32e8a6de57/exec-e470abd4-2d07-4b47-83fc-2e2cbccb6a17.png"),
}
RECOMMEND_TILE = SRC / "shop" / "recommend_tile_imagegen.png"

# 타일 그림보다 메뉴 아이콘 쪽이 더 나은 경우가 있다. (화면, 타일번호) → 아이콘 텍스처.
# 도감이 그 경우였다(2026-08-08) — 생성물의 펼친 책보다 ui_menu_dex 가 또렷하다.
RP_ICONS = Path.home() / "development" / "barkan-resourcepack" / \
    "assets" / "minecraft" / "textures" / "item" / "barkan_icon"
TILE_ICON_OVERRIDE = {("myinfo", 5): "ui_menu_dex"}

# 2행 타일(메뉴·내 정보)은 세로 130px뿐이라 그림을 통째로 깔면 라벨이 아이콘 위에 얹힌다.
# 아래 LABEL_BAND 만큼은 글자 전용으로 비우고, 그림은 그 위 칸에 비율 유지로 넣는다.
# 상점은 4행이라 세로가 넉넉해서 예외(그림 그대로 + 아래쪽 여백에 글자).
LABEL_BAND = 40
# 사각형째로 붙이면 (a) 생성물이 들고 온 자기 몰딩이 겹쳐 액자가 두 겹이 되고
# (b) 판 색이 미세하게 달라 이음선이 보인다. 그래서 배경을 빼고 아이콘만 뽑아 얹는다.
MASK_LO, MASK_HI = 16, 52


# 생성물의 타일 격자는 우리 좌표와 세로로 어긋나 있다. 그래서 넉넉한 창을 잡고
# 그 안에서 아이콘 덩어리만 찾는다. 가로로 길게 이어진 줄은 몰딩이라 버린다.
WINDOW_PAD = 34
BAR_COVER = 0.92
BAR_THICK = 16
KEEP_RATIO = 0.04
NEAR = 28


def _components(flat, w, h):
    seen = bytearray(w * h)
    for start in range(w * h):
        if flat[start] and not seen[start]:
            seen[start] = 1
            stack, comp = [start], []
            while stack:
                i = stack.pop()
                comp.append(i)
                x, y = i % w, i // w
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1),
                               (x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1), (x + 1, y + 1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        j = ny * w + nx
                        if flat[j] and not seen[j]:
                            seen[j] = 1
                            stack.append(j)
            yield comp


def lift_icon(gen, box):
    """타일 창에서 어두운 판과 몰딩 줄을 지우고 아이콘 덩어리만 알파로 뽑아낸다."""
    x0, y0, x1, y1 = box
    win = gen.crop((x0, max(0, y0 - WINDOW_PAD), x1, min(H, y1 + WINDOW_PAD)))
    rgb = win.convert("RGB")
    w, h = rgb.size
    chans = rgb.split()
    bg = tuple(sorted(c.getdata())[w * h // 2] for c in chans)
    diff = ImageChops.difference(rgb, Image.new("RGB", (w, h), bg)).convert("L")
    soft = diff.point(lambda v: 0 if v <= MASK_LO else (255 if v >= MASK_HI else
                                                       int((v - MASK_LO) * 255 / (MASK_HI - MASK_LO))))
    hard = bytearray(1 if v > 110 else 0 for v in soft.getdata())

    def bounds(comp):
        xs = [i % w for i in comp]
        ys = [i // w for i in comp]
        return min(xs), min(ys), max(xs), max(ys)

    # 몰딩 줄 = 창을 가로지르면서 얇은 것. 리본·펼친 책처럼 넓기만 한 아이콘은
    # 폭만 보면 같이 지워지므로(2026-08-08 칭호·도감 소실) 두께까지 함께 본다.
    comps = []
    for comp in _components(hard, w, h):
        bx0, by0, bx1, by1 = bounds(comp)
        if bx1 - bx0 >= BAR_COVER * w and by1 - by0 <= BAR_THICK:
            continue
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    if not comps:
        return win.convert("RGBA")
    limit = len(comps[0]) * KEEP_RATIO
    keep = bytearray(w * h)
    ax0, ay0, ax1, ay1 = bounds(comps[0])
    for comp in comps:
        # 창 위아래 여백에 걸린 조각은 이웃 타일의 장식이다. 본체에서 멀면 버린다.
        if len(comp) < limit:
            continue
        bx0, by0, bx1, by1 = bounds(comp)
        if (bx0 - ax1 > NEAR or ax0 - bx1 > NEAR or by0 - ay1 > NEAR or ay0 - by1 > NEAR):
            continue
        ax0, ay0 = min(ax0, bx0), min(ay0, by0)
        ax1, ay1 = max(ax1, bx1), max(ay1, by1)
        for i in comp:
            keep[i] = 255
    keep_img = Image.frombytes("L", (w, h), bytes(keep)).filter(ImageFilter.MaxFilter(5))
    mask = ImageChops.multiply(soft, keep_img).filter(ImageFilter.GaussianBlur(0.6))
    out = win.convert("RGBA")
    out.putalpha(mask)
    bbox = mask.point(lambda v: 255 if v > 60 else 0).getbbox()
    return out.crop(bbox) if bbox else out

LABELS = {
    "menu": [(0, 140, 283, "내 정보"), (1, 140, 283, "레벨·특성"), (2, 140, 283, "장비"),
             (0, 284, 427, "퀘스트"), (1, 284, 427, "내 섬"), (2, 284, 427, "길드")],
    "myinfo": [(0, 140, 283, "프로필"), (1, 140, 283, "스탯"), (2, 140, 283, "칭호"),
               (0, 284, 427, "도전과제"), (1, 284, 427, "랭킹"), (2, 284, 427, "도감")],
    "shop": [(0, 140, 427, "캐시 상점"), (1, 140, 427, "잠수 상점"), (2, 140, 427, "추천상점")],
}


def main():
    # 빈 판(테두리·홈·제목만)을 여기서 다시 굽는다. 절차 아이콘이 남아 있으면
    # 뽑아낸 아이콘의 투명한 틈으로 비쳐 잡선이 보인다.
    build_gui3_bg.DRAW_ICONS = False
    build_gui3_bg.main()
    for name, source in GEN.items():
        if not source.exists():
            raise FileNotFoundError(source)
        base = Image.open(OUT / name / "bg_source.png").convert("RGBA")
        gen = Image.open(source).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)
        # Keep the exact slot-aligned molding from the deterministic base. The generated
        # art is used for the quiet interior only, so the imagegen model cannot move hitboxes.
        for tile, (col, y0, y1, _) in enumerate(LABELS[name]):
            x0, x1 = COLS[col]
            dst = (x0 + 7, y0 + 7, x1 - 6, y1 - 6)
            if name == "shop":
                base.paste(gen.crop(dst), (dst[0], dst[1]))
            else:
                iw, ih = dst[2] - dst[0], dst[3] - dst[1]
                swap = TILE_ICON_OVERRIDE.get((name, tile))
                icon = lift_icon(gen, (dst[0] + 10, dst[1], dst[2] - 10, dst[3]))
                if swap:
                    # 아이콘 원본은 사방에 투명 여백이 있다 — 그대로 맞추면 그림이 작아진다.
                    icon = Image.open(RP_ICONS / f"{swap}.png").convert("RGBA")
                    icon = icon.crop(icon.getbbox() or (0, 0, icon.width, icon.height))
                zw, zh = iw - 26, ih - LABEL_BAND - 8
                k = min(zw / icon.width, zh / icon.height)
                nw, nh = max(1, round(icon.width * k)), max(1, round(icon.height * k))
                base.alpha_composite(icon.resize((nw, nh), Image.Resampling.LANCZOS),
                                     (dst[0] + (iw - nw) // 2, dst[1] + 4 + (zh - nh) // 2))
        d = ImageDraw.Draw(base, "RGBA")
        for col, y0, y1, label in LABELS[name]:
            x0, x1 = COLS[col]
            box = (x0 + 4, y0 + 4, x1 - 4, y1 - 4)
            if name == "shop":
                center_text(d, box, label, size=30, y=378)
            else:
                center_text(d, box, label, size=28, y=y1 - 40)
        # The right shop tile is a high-resolution imagegen replacement. Apply only
        # its interior so the fixed GUI molding and hitbox coordinates stay exact.
        # Restore the deterministic label strip after the art paste.
        if name == "shop" and RECOMMEND_TILE.exists():
            tile_ref = Image.open(RECOMMEND_TILE).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)
            x0, x1 = COLS[2]
            inner = (x0 + 7, 140 + 7, x1 - 6, 427 - 6)
            label_strip = base.crop((inner[0], 374, inner[2], inner[3])).copy()
            base.paste(tile_ref.crop(inner), (inner[0], inner[1]))
            base.paste(label_strip, (inner[0], 374))
        base.putalpha(255)
        out = SRC / name / "bg_source.png"
        base.save(out)
        print(out)


if __name__ == "__main__":
    main()
