#!/usr/bin/env python3
"""납품본 손질 — 받은 그림을 정확한 캔버스에 맞춰 bg_source.png 로 넘긴다.

캔버스 맞추기(리사이즈)는 늘 하고, 어긋난 화면만 구간 보정·부분 도장을 더한다.

## 실측 결과 (check_align.py)
  표지(dexmain)      칸 오차 ≤2px  — 그대로 통과
  섬 목록(dexisland) 칸 오차 ≤3px  — 그대로 통과
  목록 속장(dextab)  칸 오차 ≤6px  — 1.5 GUI px, 아이콘이 액자 안에 있어 통과
  물고기(dexfish)    칸 간격 68.6/69.7px (72여야 함) → 양 끝이 17~20px 밀린다. 보정.

## dexfish 를 통짜로 확대하지 않는 이유
간격을 72로 맞추려면 1.05배 키워야 하는데, 그러면 바깥 장식 테두리가 17px씩 잘려나간다.
그래서 **구간별로 다시 배치**한다 — 테두리는 눌러서 제자리에 두고 격자만 늘린다
(fit_plate.py 와 같은 수법, 여기는 가로세로 둘 다).

## 책등 문제
물고기 판은 펼친 책이라 **가운데 열(col 4)이 책등 홈**이고 액자가 없다. 그런데 물고기는
9~44 를 연속으로 쓰므로 그 열에도 아이템이 올라간다. 옆 칸에서 액자를 떠다 5개 찍는다.

산출: src/<이름>/bg_source.png
"""
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DEX = os.path.expanduser("~/Downloads/dex-images")
CODEX = os.path.expanduser("~/.codex/generated_images")

S, GX, GY, CELL = 4, 7, 17, 18
X0, Y0, PITCH = GX * S, GY * S, CELL * S          # 28, 68, 72

# 이름: (납품 파일, 캔버스, 가로 구간, 세로 구간)
#   구간 = [(원본 a0, a1) → (목표 b0, b1)]. 빈 목록이면 손대지 않는다.
PLATES = {
    "dexmain":   (f"{DEX}/dex-menu.png",        (704, 672), [], []),
    "dextab":    (f"{DEX}/dex-book-tabs.png",   (704, 888), [], []),
    "dexisland": (f"{DEX}/dex-book-island.png", (704, 744), [], []),
    # 분해창 — 납품본(bg_source_rebuild)은 손댈 게 없고 「갈기」 버튼 위치만 옮긴다(SHIFTS).
    "disassemble": (f"{HERE}/src/disassemble/bg_source_rebuild.png", (704, 888), [], []),
    # NPC 대화 창 — 칸 오차 ≤3px 이라 캔버스만 맞추면 된다.
    "npcdialog": (f"{CODEX}/019fcffa-2416-7661-aab4-db32e8a6de57/"
                  "exec-e95e2996-94c5-43b7-a73c-8e36d792de6e.png", (704, 744), [], []),
    "dexfish":   (f"{DEX}/dex-book-fish.png",   (704, 888),
                  [((0, 45), (0, 28)),          # 왼쪽 테두리 — 눌러서 제자리
                   ((45, 656), (28, 676)),      # 격자 — 늘려서 72px 간격으로
                   ((656, 704), (676, 704))],   # 오른쪽 테두리 — 눌러서 제자리
                  [((0, 83), (0, 68)),          # 위 테두리 + 제목 띠
                   ((83, 501), (68, 500)),      # 격자
                   ((501, 888), (500, 888))]),  # 아래 판 + 인벤 영역 — 사실상 1:1
}

# 책등 열에 액자를 찍을 화면: (떠올 칸 col·row, 찍을 col, 찍을 row 목록)
SPINE_FILL = {"dexfish": ((3, 2), 4, [0, 1, 2, 3, 4])}

# 한 덩어리만 살짝 옮길 때: 이름 → [(상자, dx, dy)]
# ★2px(=0.5 GUI px) 라도 아이콘이 액자 구멍을 꽉 채우면 눈에 띈다. 구멍이 63px 인데
#   아이콘이 64px 이라 여유가 없어서, 2px 밀리면 위는 테두리에 걸치고 아래에 틈이 생긴다.
#   (2026-08-10 유저가 확대해서 잡아냄 — 겹쳐보기 그림으로는 안 보였다.)
SHIFTS = {   # (상자, dx, dy[, 메움 바닥을 뜰 절대 y])
    "npcdialog": [((160, 272, 546, 368), 0, -2)],   # 선택지 놋쇠 판이 2px 낮았다
    # 「갈기」 버튼이 셀49 중심보다 **24px** 아래였다(아이콘 위쪽 1/3 이 맨 바닥에 걸쳐 있었다).
    # ★상자 위끝은 450 — 초록 입력판 아래 테두리가 449 에서 끝나므로 1px 아래부터 잡는다.
    #   412 부터 잡았다가 그 테두리를 끌어올려 판 밑에 검은 홈을 파먹은 적이 있다.
    # ★메움은 버튼 **위쪽** 민무늬 바닥(y424~)에서 뜬다 — 아래쪽엔 밝은 이음선이 지나가 티가 난다.
    "disassemble": [((300, 450, 404, 542), 0, -24, 424)],
}

# 구멍 조이기: 액자 구멍이 아이콘(64px)보다 크면 그 틈만큼 액자 안쪽 테두리를 밀어 넣는다.
# ★2px 옮겨 중심을 맞춰도 구멍이 65px 이면 남는 1px 이 어느 한쪽에 몰린다 — 옮기기로는
#   절대 안 없어진다. 틈을 없애려면 구멍이 정확히 64px 이어야 한다(2026-08-10).
#   구멍이 이미 64 이하인 칸에는 아무 일도 안 일어난다(멱등).
SEAL = {"npcdialog": [29, 30, 31, 32, 33]}
DARK = 60          # 이보다 어두우면 구멍, 밝으면 액자


def remap(im, xb, yb):
    """구간별로 잘라 다시 붙인다. 구간이 없으면 그대로."""
    W, H = im.size
    if yb:
        out = Image.new("RGBA", (W, H))
        for (a0, a1), (b0, b1) in yb:
            out.paste(im.crop((0, a0, W, a1)).resize((W, b1 - b0), Image.LANCZOS), (0, b0))
        im = out
    if xb:
        out = Image.new("RGBA", (W, H))
        for (a0, a1), (b0, b1) in xb:
            out.paste(im.crop((a0, 0, a1, H)).resize((b1 - b0, H), Image.LANCZOS), (b0, 0))
        im = out
    return im


def seal_cell(im, slot):
    """칸 하나의 구멍을 아이콘 상자(64px)에 딱 맞춘다 — 넘치는 쪽 테두리를 안으로 민다."""
    px = im.load()
    col, row = slot % 9, slot // 9
    x0, y0 = cell_box(col, row)[:2]
    ix0, iy0 = x0 + 4, y0 + 4          # 아이콘 상자 (64px)
    ix1, iy1 = ix0 + 63, iy0 + 63
    def lum(x, y):
        r, g, b = px[x, y][:3]
        return (r * 299 + g * 587 + b * 114) // 1000
    my, mx = iy0 + 32, ix0 + 32
    # 아이콘 상자 바로 바깥이 아직 어두우면 **바깥 띠를 통째로 한 칸 안으로 민다.**
    # ★한 줄만 복사하면 안 된다 — 그 줄이 경계의 중간톤이면 복사해도 계속 어두워서 제자리걸음.
    for _ in range(4):
        if lum(ix0 - 1, my) >= DARK:
            break
        im.paste(im.crop((x0, y0, ix0 - 1, y0 + 72)), (x0 + 1, y0))
    for _ in range(4):
        if lum(ix1 + 1, my) >= DARK:
            break
        im.paste(im.crop((ix1 + 2, y0, x0 + 72, y0 + 72)), (ix1 + 1, y0))
    for _ in range(4):
        if lum(mx, iy0 - 1) >= DARK:
            break
        im.paste(im.crop((x0, y0, x0 + 72, iy0 - 1)), (x0, y0 + 1))
    for _ in range(4):
        if lum(mx, iy1 + 1) >= DARK:
            break
        im.paste(im.crop((x0, iy1 + 2, x0 + 72, y0 + 72)), (x0, iy1 + 1))


def cell_box(col, row):
    return (X0 + PITCH * col, Y0 + PITCH * row,
            X0 + PITCH * (col + 1), Y0 + PITCH * (row + 1))


def main():
    for name, (fname, size, xb, yb) in PLATES.items():
        im = Image.open(fname).convert("RGBA")
        if im.size != size:
            im = im.resize(size, Image.LANCZOS)      # 비율이 맞으면 통짜 리사이즈로 끝난다
        im = remap(im, xb, yb)

        for box, dx, dy, *rest in SHIFTS.get(name, []):
            heal_y = rest[0] if rest else None      # 메울 바닥을 뜰 절대 y (없으면 바로 옆)
            x0, y0, x1, y1 = box
            piece = im.crop(box)
            # 비는 자리는 옮긴 반대쪽 바로 옆에서 같은 두께로 떠다 메운다(뒤가 가로로 연속된 판).
            if dy:
                sy = heal_y if heal_y is not None else (y1 if dy < 0 else y0 + dy)
                im.paste(im.crop((x0, sy, x1, sy + abs(dy))),
                         (x0, y1 + dy if dy < 0 else y0))
            if dx:
                sx = x1 if dx < 0 else x0 + dx
                im.paste(im.crop((sx, y0, sx + abs(dx), y1)),
                         (x1 + dx if dx < 0 else x0, y0))
            im.paste(piece, (x0 + dx, y0 + dy))

        for slot in SEAL.get(name, []):
            seal_cell(im, slot)

        fill = SPINE_FILL.get(name)
        if fill:
            (sc, sr), dst_col, rows = fill
            sprite = im.crop(cell_box(sc, sr))
            for r in rows:
                x, y = cell_box(dst_col, r)[:2]
                im.paste(sprite, (x, y))

        out = os.path.join(HERE, "src", name)
        os.makedirs(out, exist_ok=True)
        im.convert("RGB").save(os.path.join(out, "bg_source.png"))
        print(f"  {name:10} {size[0]}x{size[1]}"
              + (f" · 구간보정 {len(xb)}x{len(yb)}" if xb or yb else " · 원본 그대로")
              + (f" · 책등 액자 {len(fill[2])}개" if fill else "")
              + (f" · 부분이동 {len(SHIFTS[name])}건" if name in SHIFTS else "")
              + (f" · 구멍조이기 {len(SEAL[name])}칸" if name in SEAL else ""))


if __name__ == "__main__":
    main()
