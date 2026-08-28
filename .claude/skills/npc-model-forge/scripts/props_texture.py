#!/usr/bin/env python3
"""소품 텍스처(64x64 props 아틀라스) 생성 — 밀짚·등나무·천.

★스킨 팔레트 규칙을 그대로 따른다: 순수 검정 금지, 램프 5단, 뮤트.
  중세 마을에 채도 높은 원색은 없다.
★<b>타일 가능한 재질</b>로 만든다. 부품 6면이 같은 UV 사각형을 공유하므로,
  이음매가 눈에 띄면 큐브마다 무늬가 튄다.
"""
import random
import sys

from PIL import Image


def ramp(hex6, n=5, spread=0.5):
    r, g, b = (int(hex6[i:i + 2], 16) for i in (0, 2, 4))
    out = []
    for i in range(n):
        t = (i / (n - 1) - 0.5) * spread
        out.append(tuple(max(6, min(249, int(c * (1 + t)))) for c in (r, g, b)))
    return out


def weave(im, box, base, seed, horiz=3, vert=0):
    """가로(세로) 결이 보이는 짜임. 반스텝 명암만 써서 '천'으로 읽히게 한다."""
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    px = im.load()
    for y in range(y0, y1):
        for x in range(x0, x1):
            i = 2
            if horiz and (y - y0) % horiz == 0:
                i = 1
            if vert and (x - x0) % vert == 0:
                i = 1 if i == 2 else 0
            if rnd.random() < 0.16:
                i = min(4, i + 1)
            px[x, y] = base[i] + (255,)


def main(out='/tmp/props.png'):
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    # 밀짚 — 바랜 노랑갈색. 가로 결이 촘촘하다
    weave(im, (0, 0, 32, 32), ramp('c8a35c'), 11, horiz=3)
    # 등나무(바구니) — 밀짚보다 붉고 어둡게, 격자로 짜인 결
    weave(im, (32, 0, 64, 32), ramp('9a6b3c'), 23, horiz=4, vert=4)
    # 천(리본) — 짙은 적갈. 결 없이 은은하게
    weave(im, (0, 32, 32, 64), ramp('8a4a3a'), 37, horiz=6)
    # 내용물(농산물) — ★바구니와 명도·색상을 확실히 벌린다. 같은 갈색이면
    #   바구니가 '속이 꽉 찬 갈색 덩어리'로 읽힌다(1차 실패)
    weave(im, (32, 32, 48, 48), ramp('7a9a45'), 51, horiz=3)      # 채소
    weave(im, (48, 32, 64, 48), ramp('c46a3a'), 53, horiz=3)      # 과일
    im.save(out)
    print('%s  (밀짚 / 등나무 / 천)' % out)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '/tmp/props.png')
