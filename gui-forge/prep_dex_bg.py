#!/usr/bin/env python3
"""도감 배경 손질 — 납품 넉 장 중 어긋난 것만 고쳐 bg_source.png 로 넘긴다.

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
SRC = os.path.expanduser("~/Downloads/dex-images")

S, GX, GY, CELL = 4, 7, 17, 18
X0, Y0, PITCH = GX * S, GY * S, CELL * S          # 28, 68, 72

# 이름: (납품 파일, 캔버스, 가로 구간, 세로 구간)
#   구간 = [(원본 a0, a1) → (목표 b0, b1)]. 빈 목록이면 손대지 않는다.
PLATES = {
    "dexmain":   ("dex-menu.png",        (704, 672), [], []),
    "dextab":    ("dex-book-tabs.png",   (704, 888), [], []),
    "dexisland": ("dex-book-island.png", (704, 744), [], []),
    "dexfish":   ("dex-book-fish.png",   (704, 888),
                  [((0, 45), (0, 28)),          # 왼쪽 테두리 — 눌러서 제자리
                   ((45, 656), (28, 676)),      # 격자 — 늘려서 72px 간격으로
                   ((656, 704), (676, 704))],   # 오른쪽 테두리 — 눌러서 제자리
                  [((0, 83), (0, 68)),          # 위 테두리 + 제목 띠
                   ((83, 501), (68, 500)),      # 격자
                   ((501, 888), (500, 888))]),  # 아래 판 + 인벤 영역 — 사실상 1:1
}

# 책등 열에 액자를 찍을 화면: (떠올 칸 col·row, 찍을 col, 찍을 row 목록)
SPINE_FILL = {"dexfish": ((3, 2), 4, [0, 1, 2, 3, 4])}


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


def cell_box(col, row):
    return (X0 + PITCH * col, Y0 + PITCH * row,
            X0 + PITCH * (col + 1), Y0 + PITCH * (row + 1))


def main():
    for name, (fname, size, xb, yb) in PLATES.items():
        im = Image.open(os.path.join(SRC, fname)).convert("RGBA")
        assert im.size == size, f"{name} 캔버스 {im.size} != {size}"
        im = remap(im, xb, yb)

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
              + (f" · 책등 액자 {len(fill[2])}개" if fill else ""))


if __name__ == "__main__":
    main()
