#!/usr/bin/env python3
"""스킬 허브 배경 손질 — 액자 다섯을 정확한 격자에 다시 박는다.

## 왜 손으로 박나
발주로 두 번 받았는데 액자 간격이 76px, 80px 로 왔다. 필요한 건 **72px**(게임이
아이템을 그리는 간격)이고, 그림 생성은 픽셀 단위 기하를 못 맞춘다. 재질과 구도는
받은 그림이 좋으니 **텍스처는 발주, 좌표는 코드**로 나눈다. 강화창 화살표 옮기기
(prep_enhance_bg.py)·아이스박스 상점 버튼 이식(prep_icebox_bg.py)과 같은 수법이다.

## 하는 일
1. 받은 원본(1283x1226)을 704x672로 줄인다.
2. 가운데 액자(이미 x=352에 정확히 앉아 있다)를 스프라이트로 뜬다.
3. 9-슬라이스로 늘려 **테두리 두께는 그대로 두고 구멍만 64px**로 키운다.
   받은 액자는 구멍이 48px라 64px짜리 아이콘이 테두리를 통째로 덮었다.
4. 슬롯 11~15의 셀 중심(x = 208·280·352·424·496, y = 176)에 다시 찍는다.
   72px 간격에 78px 액자라 6px씩 겹치는데, 겹치는 폭이 테두리 두께와 비슷해
   칸을 나눈 하나의 진열대처럼 읽힌다.
5. 옛 액자가 새 액자 바깥으로 삐져나온 좌우 자투리는 아래쪽 벽을 떠다 덮는다.

산출: src/skillhub/bg_source.png  (build_plate.py skillhub 가 먹는 파일)
"""
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "skillhub")
RAW = os.path.expanduser(
    "~/.codex/generated_images/019fcffa-2416-7661-aab4-db32e8a6de57/"
    "exec-6a6d0d38-9ba2-44e2-8aff-8d59e9c1f8c9.png")

W, H = 704, 672
# 가운데 액자 실측 바깥 상자(704x672 기준). 구멍은 329~377 x 150~206.
SPRITE = (321, 142, 386, 214)
CORNER = 18          # 9-슬라이스 모서리 — 액자 장식이 다 들어가는 크기
OUT = 78             # 새 액자 바깥 한 변 (테두리 7 x2 + 구멍 64)
CENTERS = [208, 280, 352, 424, 496]   # 슬롯 11~15 셀 중심
ROW_Y = 176                            # 1행 셀 중심
OLD = (158, 133, 542, 220)             # 옛 액자 다섯이 차지하던 범위(그림자까지 넉넉히)
END_L, END_R = (112, 158), (542, 590)  # 좌우 끝 장식(다이아+연결선) 블록


def nine_slice(sp, out_w, out_h, c):
    """모서리 c x c 는 그대로, 변과 가운데만 늘린다 — 테두리 두께가 안 변한다."""
    w, h = sp.size
    im = Image.new("RGBA", (out_w, out_h))
    xs_src = [(0, c), (c, w - c), (w - c, w)]
    ys_src = [(0, c), (c, h - c), (h - c, h)]
    xs_dst = [(0, c), (c, out_w - c), (out_w - c, out_w)]
    ys_dst = [(0, c), (c, out_h - c), (out_h - c, out_h)]
    for (sy0, sy1), (dy0, dy1) in zip(ys_src, ys_dst):
        for (sx0, sx1), (dx0, dx1) in zip(xs_src, xs_dst):
            piece = sp.crop((sx0, sy0, sx1, sy1))
            im.paste(piece.resize((dx1 - dx0, dy1 - dy0), Image.LANCZOS), (dx0, dy0))
    return im


def main():
    im = Image.open(RAW).convert("RGBA").resize((W, H), Image.LANCZOS)
    frame = nine_slice(im.crop(SPRITE), OUT, OUT, CORNER)

    # 새 액자 줄이 옛 줄보다 좁아져서 양 끝에 옛 액자 자투리가 남는다. 그 자리를 벽으로
    # 메우려 해 봤지만(아래·옆에서 떠오기) 옛 액자의 그림자가 남아 티가 났다. 대신
    # **끝 장식(다이아+연결선)을 통째로 안쪽으로 밀어** 자투리를 덮는다. 장식이 비운
    # 자리는 그 바깥 민무늬 벽에서 떠오면 되고, 거긴 진짜로 아무것도 없다.
    y0, y1 = OLD[1], OLD[3]
    half = OUT // 2
    new_x0, new_x1 = CENTERS[0] - half, CENTERS[-1] + half
    for (bx0, bx1), dx in ((END_L, new_x0 - OLD[0]), (END_R, new_x1 - OLD[2])):
        im.paste(im.crop((bx0, y0, bx1, y1)), (bx0 + dx, y0))
        gap = (bx0, bx0 + dx) if dx > 0 else (bx1 + dx, bx1)   # 장식이 비운 자리
        w = gap[1] - gap[0]
        sx = gap[0] - w if dx > 0 else gap[1]                  # 바깥쪽 민무늬 벽
        im.paste(im.crop((sx, y0, sx + w, y1)), (gap[0], y0))

    for cx in CENTERS:
        im.alpha_composite(frame, (cx - half, ROW_Y - half))

    im.save(os.path.join(SRC, "bg_source.png"))
    print(f"  skillhub 액자 5개 재배치 · 간격 72px · 바깥 {OUT}px · 구멍 {OUT - 2 * 7}px")


if __name__ == "__main__":
    main()
