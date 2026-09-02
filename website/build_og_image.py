#!/usr/bin/env python3
"""히어로 배너 -> 링크 미리보기(OG) 이미지 생성.

링크 프리뷰 크롤러(디스코드·카카오톡·트위터·슬랙)는 1200x630(1.91:1) JPEG 를
가장 안정적으로 처리한다. 히어로 원본은 1920x991 PNG 3.3MB 라 그대로 쓰면
크롤러가 받다 포기하거나(용량) 좌우가 잘려 배가 안 보인다.

재실행 가능한 생성기다 — 산출물(assets/og-image.jpg)을 손으로 고치지 말고
히어로가 바뀌면 이 스크립트를 다시 돌린다.
"""
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
SRC = HERE / "assets" / "barkan-harbor-banner.png"
OUT = HERE / "assets" / "og-image.jpg"
W, H = 1200, 630

im = Image.open(SRC).convert("RGB")
sw, sh = im.size
target = W / H
# 원본이 목표보다 넓으면 좌우를, 좁으면 위아래를 가운데 기준으로 잘라낸다.
if sw / sh > target:
    cw = round(sh * target)
    box = ((sw - cw) // 2, 0, (sw - cw) // 2 + cw, sh)
else:
    ch = round(sw / target)
    box = (0, (sh - ch) // 2, sw, (sh - ch) // 2 + ch)

im.crop(box).resize((W, H), Image.LANCZOS).save(
    OUT, "JPEG", quality=88, optimize=True, progressive=True
)
print(f"{OUT.name}: {W}x{H}  {OUT.stat().st_size // 1024} KB  (crop {box} of {sw}x{sh})")
