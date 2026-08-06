#!/usr/bin/env python3
"""GUI 배경 아트용 **가이드 판** 생성 — 그림 그리는 쪽에 좌표를 글이 아니라 그림으로 준다.

왜 필요한가 (2026-08-06):
  낚시 성공 창 배경을 좌표 표(글)로만 발주했더니 4장 전부 슬롯 격자를 벗어났다.
  소켓 링이 제멋대로 놓여 실제 슬롯(18px 피치, 원점 7,17)과 안 맞았고, 한 장은
  캔버스 비율부터 틀어졌다. 그림 작업자에게 좌표는 **레이어로 깔아줘야** 지켜진다.

산출: src/<gui>/_guide.png — 캔버스 크기가 곧 정답이고, 그 위에 칸이 표시돼 있다.

사용: python3 make_guide.py <gui이름> <컨테이너행수> [--hero 11-15] [--btn 4,8]
      예) python3 make_guide.py fishing_success 3 --hero 11-15
          python3 make_guide.py fish_shop 3 --hero 9-26 --btn 4,8
  --hero : 아이템이 실제로 놓이는 칸(노란 상자로 강조)
  --btn  : 버튼 칸(주황 채움) — 배경에 버튼 자리를 파둘 위치
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

SCALE = 4                      # 아트 = GUI × 4 (정수배 무손실)
GW = 176                       # 마크 상자 GUI 가로 — 고정
GRID_X, GRID_Y = 7, 17         # 컨테이너 슬롯 격자 원점
CELL = 18                      # 칸 크기
COLS = 9

BG        = (44, 44, 52, 255)
SLOT_FILL = (0, 190, 190, 70)
SLOT_LINE = (0, 255, 255, 255)
INV_FILL  = (120, 60, 60, 70)
INV_LINE  = (255, 90, 90, 255)
HERO_LINE = (255, 220, 0, 255)
TITLE_FILL= (60, 60, 110, 90)
WARN_LINE = (255, 0, 255, 255)


def geometry(rows):
    """행 수 → 창 크기와 각 영역 좌표(GUI px). 전부 유도식 — 하드코딩 금지."""
    gh = 114 + rows * CELL
    inv_y0 = 31 + rows * CELL            # 플레이어 인벤 첫 행 top
    return {
        "gh": gh,
        "slot_rows": [GRID_Y + CELL * r for r in range(rows)],
        "inv_rows": [inv_y0, inv_y0 + CELL, inv_y0 + 2 * CELL],
        "hotbar": inv_y0 + 58,
        "inv_label": (8, gh - 94),       # 바닐라가 "인벤토리" 라벨을 그리는 자리
        "title_label": (8, 6),
    }


def font(px):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(p, px)
        except Exception:
            pass
    return ImageFont.load_default()


def parse_slots(spec):
    """'9-26' / '4,8' / '2-6,11-15' → 슬롯 집합."""
    out = set()
    for part in (spec or "").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    name, rows = sys.argv[1], int(sys.argv[2])
    argv = sys.argv[3:]
    hero_spec = btn_spec = ""
    for i, a in enumerate(argv):
        if a == "--hero" and i + 1 < len(argv): hero_spec = argv[i + 1]
        if a == "--btn" and i + 1 < len(argv): btn_spec = argv[i + 1]
    globals()["HERO_SLOTS"] = parse_slots(hero_spec)
    globals()["BTN_SLOTS"] = parse_slots(btn_spec)
    g = geometry(rows)
    W, H = GW * SCALE, g["gh"] * SCALE
    im = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(im, "RGBA")
    f_big, f_sm = font(28), font(18)

    def cell(x, y, fill, line, w=3):
        d.rectangle([x * SCALE, y * SCALE,
                     (x + CELL) * SCALE - 1, (y + CELL) * SCALE - 1],
                    fill=fill, outline=line, width=w)

    # 컨테이너 슬롯 — 여기에 아이템이 올라간다. 소켓/홈은 정확히 이 칸에 맞춰야 한다.
    # ★주인공 칸은 **5칸**(2026-08-06). 낚시 결과는 물고기 1마리가 아니라 더블/트리플 +
    #   낚시 재료 + 보물상자까지 한 번에 3~4개가 쏟아지므로 한 칸짜리 제단으론 못 담는다.
    heroes = globals().get("HERO_SLOTS") or set()
    btns = globals().get("BTN_SLOTS") or set()
    hero_cells = []
    for r, y in enumerate(g["slot_rows"]):
        for c in range(COLS):
            x = GRID_X + CELL * c
            idx = r * COLS + c
            is_hero, is_btn = idx in heroes, idx in btns
            fill = (255, 150, 0, 90) if is_btn else SLOT_FILL
            line = (255, 150, 0, 255) if is_btn else (HERO_LINE if is_hero else SLOT_LINE)
            cell(x, y, fill, line, 4 if (is_hero or is_btn) else 3)
            if is_hero:
                hero_cells.append((x, y))
            d.text(((x + 4) * SCALE, (y + 5) * SCALE), ("BTN" if is_btn else str(idx)),
                   font=f_sm, fill=(255, 255, 255, 230))

    # 플레이어 인벤 — 격자는 빌더가 덧그린다. 아트에선 민무늬로 둘 것.
    for y in g["inv_rows"] + [g["hotbar"]]:
        for c in range(COLS):
            cell(GRID_X + CELL * c, y, INV_FILL, INV_LINE, 2)
    iy = g["inv_rows"][0]
    d.text((GRID_X * SCALE + 8, (iy - 12) * SCALE),
           "PLAYER INVENTORY - leave FLAT, do not draw grid",
           font=f_sm, fill=INV_LINE)

    # 제목 글자 자리 — 마크가 제목을 안 그리므로 아트에 직접 그려야 한다.
    d.rectangle([0, 0, W - 1, (GRID_Y - 1) * SCALE], fill=TITLE_FILL, outline=(140, 140, 255, 255), width=3)
    d.text((12, 10), "TITLE TEXT GOES HERE (painted into the art)", font=f_sm, fill=(200, 200, 255, 255))

    # 바닐라 "인벤토리" 라벨이 덧그려질 수 있는 줄
    lx, ly = g["inv_label"]
    d.line([(lx * SCALE, ly * SCALE), (W - 8, ly * SCALE)], fill=WARN_LINE, width=3)
    d.text((lx * SCALE + 6, ly * SCALE + 4), "vanilla may draw a label on this line",
           font=f_sm, fill=WARN_LINE)

    # ★프레임 침범 금지 영역 — 2026-08-06 실패: 좌우 나무 프레임을 44px로 그려서
    #   맨 바깥 슬롯 열이 프레임 위에 올라탔다. 마크 슬롯 격자는 art x=28에서 시작하고
    #   소켓(96px)은 x=16까지 뻗으므로, 프레임이 들어올 수 있는 폭은 한쪽 16px뿐이다.
    #   이건 바닐라 상자 GUI 규격이라 협상 불가 — 그림으로 못박아 둔다.
    def nogo(x0, y0, x1, y1, label):
        d.rectangle([x0, y0, x1, y1], outline=(255, 140, 0, 255), width=5)
        d.text((x0 + 8, y0 + 6), label, font=f_sm, fill=(255, 140, 0, 255))

    sock = 96 // 2 - CELL * SCALE // 2      # 소켓이 칸 밖으로 뻗는 여유(art px)
    sx0 = GRID_X * SCALE - sock
    sx1 = (GRID_X + CELL * COLS) * SCALE - 1 + sock
    sy0 = g["slot_rows"][0] * SCALE - sock
    sy1 = (g["slot_rows"][-1] + CELL) * SCALE - 1 + sock
    nogo(sx0, sy0, sx1, sy1, "FRAME MUST NOT ENTER (sockets reach here)")

    iy0, iy1 = g["inv_rows"][0], g["hotbar"] + CELL
    nogo(GRID_X * SCALE, iy0 * SCALE, (GRID_X + CELL * COLS) * SCALE - 1, iy1 * SCALE - 1,
         "FRAME MUST NOT ENTER")

    if hero_cells:
        hx0 = min(x for x, _ in hero_cells) * SCALE
        hx1 = (max(x for x, _ in hero_cells) + CELL) * SCALE - 1
        hy0 = min(y for _, y in hero_cells) * SCALE
        hy1 = (max(y for _, y in hero_cells) + CELL) * SCALE - 1
        d.rectangle([hx0, hy0, hx1, hy1], outline=HERO_LINE, width=5)
        d.text((6, H - 30),
               f"ITEM AREA (yellow): x {hx0}~{hx1}, y {hy0}~{hy1}  center x={(hx0 + hx1) // 2}",
               font=f_sm, fill=HERO_LINE)

    d.text((12, H - 60), f"CANVAS MUST BE EXACTLY {W} x {H}", font=f_big, fill=(255, 255, 0, 255))

    out = os.path.join(HERE, "src", name)
    os.makedirs(out, exist_ok=True)
    p = os.path.join(out, "_guide.png")
    im.save(p)
    print(f"가이드 저장: {p}  ({W}x{H}, 컨테이너 {rows}행)")
    print(f"  컨테이너 슬롯 행 top(GUI y): {g['slot_rows']}")
    print(f"  플레이어 인벤 행 top:        {g['inv_rows']}  핫바 {g['hotbar']}")
    print(f"  바닐라 인벤 라벨 줄:         {g['inv_label']}")


if __name__ == "__main__":
    main()
