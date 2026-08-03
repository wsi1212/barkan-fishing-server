#!/usr/bin/env python3
"""하이브리드 애니 v2 — AI 로드는 고정, 불꽃은 '모양이 실제로 타오르며 움직임'(밝기변조 아님).

v1(밝기만 변조=반짝임)의 한계 해결. AI가 그린 불꽃 픽셀을 씨앗선으로 삼아, 프레임마다
위로 솟는 불꽃 혀(tongue)를 절차적으로 그린다. 혀의 높이·좌우 흔들림이 위상(phase)의
주기함수라 N프레임에서 매끄럽게 루프. → 불 실루엣이 프레임마다 실제로 바뀜=스프라이트 애니.

출력: 바닐라 .mcmeta 세로스트립 + 리뷰 GIF.
사용: animate_fire2.py <dot.png> [frames] [frametime]
"""
import sys, math, random
from PIL import Image

RAMP = [(70, 15, 8), (150, 40, 12), (220, 80, 20), (245, 130, 35),
        (252, 175, 60), (255, 215, 110), (255, 240, 175), (255, 252, 225)]


def is_fire(px):
    r, g, b, a = px
    if a == 0:
        return False
    return max(r, g, b) >= 185 and r >= 150 and g >= 95 and b <= g + 12


def main():
    path = sys.argv[1]
    N = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    frametime = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    base = Image.open(path).convert("RGBA")
    W, H = base.size
    src = base.load()
    seeds = [(x, y) for y in range(H) for x in range(W) if is_fire(src[x, y])]

    # 로드 본체(비-불꽃)만 남긴 정지 베이스 — 불꽃 자리는 은은한 잔불(ember)로 눌러둠
    body = base.copy()
    bp = body.load()
    for (x, y) in seeds:
        r, g, b, a = src[x, y]
        bp[x, y] = (int(r * 0.42), int(g * 0.32), int(b * 0.28), 255)   # 잔불 베이스

    frames = []
    for f in range(N):
        p = 2 * math.pi * f / N                      # 위상(주기 → 매끄러운 루프)
        im = body.copy()
        px = im.load()
        heat_at = {}                                 # (x,y) -> 최대 heat (겹치면 밝은 쪽)
        for (sx, sy) in seeds:
            # 이 씨앗의 이번 프레임 혀 높이(주기적으로 오르내림)
            hh = 2.5 + 4.5 * (0.5 + 0.5 * math.sin(p * 1.0 + sx * 0.7 + sy * 0.45))
            for k in range(int(hh) + 1):
                sway = math.sin(p * 1.5 + k * 0.7 + sx * 0.9) * (k * 0.22)  # 위로 갈수록 크게 흔들림
                x = int(round(sx + sway)); y = sy - k
                if 0 <= x < W and 0 <= y < H:
                    heat = 1.0 - k / max(1.0, hh)
                    if heat > heat_at.get((x, y), -1):
                        heat_at[(x, y)] = heat
        for (x, y), heat in heat_at.items():
            idx = max(1, min(len(RAMP) - 1, int(round(heat * (len(RAMP) - 1)))))
            px[x, y] = (*RAMP[idx], 255)
        # 튀는 불티(주기적 위치)
        er = random.Random(f * 131 + 3)
        for (sx, sy) in seeds:
            if er.random() < 0.06:
                ex = sx + er.choice((-1, 0, 1))
                ey = sy - int(6 + 3 * (0.5 + 0.5 * math.sin(p + sx)))
                if 0 <= ex < W and 0 <= ey < H and base.load()[ex, ey][3] == 0:
                    px[ex, ey] = (*RAMP[6], 255)
        frames.append(im)

    strip = Image.new("RGBA", (W, H * N), (0, 0, 0, 0))
    for i, im in enumerate(frames):
        strip.paste(im, (0, i * H))
    strip.save(path.replace(".png", "_anim2.png"))
    open(path.replace(".png", "_anim2.png.mcmeta"), "w").write(
        '{"animation":{"frametime":%d}}' % frametime)
    gif = []
    for im in frames:
        b = Image.new("RGBA", (W, H), (139, 139, 139, 255))
        b.alpha_composite(im)
        gif.append(b.resize((W * 6, H * 6), Image.NEAREST).convert("P"))
    gif[0].save(path.replace(".png", "_anim2.gif"), save_all=True,
                append_images=gif[1:], duration=frametime * 50, loop=0)
    print(f"seeds={len(seeds)} frames={N} → {path.replace('.png','_anim2.gif')}")


if __name__ == "__main__":
    main()
