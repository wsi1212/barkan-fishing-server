#!/usr/bin/env python3
"""깨끗한 AI 도트 낚싯대의 '팁에만' 절차적 불꽃을 얹어 애니(로드는 완전 고정).

유저 지시(2026-07-20): 대가 통째로 타면 안 됨 → 베이스는 불 없는 깨끗한 대, 불은 팁에만
코드로 얹는다=위치·양 완전 통제. 불꽃 높이/흔들림이 위상 주기함수라 N프레임 매끄러운 루프.
출력: .mcmeta 세로스트립 + 리뷰 GIF + 프레임 비교.
사용: add_tip_fire.py <clean_dot.png> [frames] [frametime]
"""
import sys, math, random
from PIL import Image

RAMP = [(70, 15, 8), (150, 40, 12), (220, 80, 20), (245, 130, 35),
        (252, 175, 60), (255, 215, 110), (255, 240, 175), (255, 252, 225)]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def find_tip(im):
    """대 끝(팁)=우상단 극점. x-y 최대(오른쪽+위쪽)인 불투명 픽셀."""
    W, H = im.size
    px = im.load()
    best, bv = None, -1e9
    for y in range(H):
        for x in range(W):
            if px[x, y][3] > 0:
                v = x - y
                if v > bv:
                    bv, best = v, (x, y)
    return best


def main():
    path = sys.argv[1]
    argv = [a for a in sys.argv[2:] if not a.startswith("--")]
    flip = "--flip" in sys.argv                       # 좌우반전(왼쪽위 바라보게) — 불꽃 그린 뒤 적용
    N = int(argv[0]) if len(argv) > 0 else 8
    frametime = int(argv[1]) if len(argv) > 1 else 2
    base = Image.open(path).convert("RGBA")
    W, H = base.size
    tx, ty = find_tip(base)

    frames = []
    for f in range(N):
        p = 2 * math.pi * f / N
        im = base.copy()
        heat_at = {}
        # 팁 부근 3열에서 불꽃 솟구침(살짝 풍성하게) — 높이는 팁 위 여백 내로 제한(클리핑 방지)
        maxh = max(4, ty - 1)
        for col in (-1, 0, 1):
            ox = tx + col
            hh = min(maxh, 11 + 3 * math.sin(p + col * 0.6))      # 프레임마다 높이 오르내림
            for k in range(int(hh) + 1):
                ft = k / max(1.0, hh)
                prof = math.sin(min(1.0, ft * 1.15) * math.pi)    # 폭: 뿌리 좁고 중간 넓고 끝 뾰족
                halfw = 0.8 + 2.3 * prof
                sway = math.sin(p * 1.4 + ft * 4.2 + col) * (1.7 * ft)
                cy = ty - k - 1
                for dx in range(-int(halfw) - 1, int(halfw) + 2):
                    if abs(dx) > halfw:
                        continue
                    x = int(round(ox + dx + sway)); y = int(cy)
                    if 0 <= x < W and 0 <= y < H:
                        d = abs(dx) / max(0.6, halfw)
                        heat = (1.0 - ft * 0.72) - d * 0.5
                        if heat > heat_at.get((x, y), -1):
                            heat_at[(x, y)] = heat
        px = im.load()
        for (x, y), heat in heat_at.items():
            idx = clamp(int(round(heat * (len(RAMP) - 1))), 1, len(RAMP) - 1)
            px[x, y] = (*RAMP[idx], 255)
        # 떠오르는 불티
        er = random.Random(f * 131 + 5)
        for _ in range(er.choice((1, 2))):
            ex = tx + er.choice((-2, -1, 0, 1))
            ey = ty - int(12 + 3 * math.sin(p + ex))
            if 0 <= ex < W and 0 <= ey < H and base.load()[ex, ey][3] == 0:
                px[ex, ey] = (*RAMP[6], 255)
        frames.append(im)

    if flip:
        frames = [f.transpose(Image.FLIP_LEFT_RIGHT) for f in frames]

    strip = Image.new("RGBA", (W, H * N), (0, 0, 0, 0))
    for i, im in enumerate(frames):
        strip.paste(im, (0, i * H))
    strip.save(path.replace(".png", "_fire.png"))
    open(path.replace(".png", "_fire.png.mcmeta"), "w").write(
        '{"animation":{"frametime":%d}}' % frametime)
    # 프레임 비교(짝수 4개)
    idxs = list(range(0, N, max(1, N // 4)))[:4]
    sc = 5
    comp = Image.new("RGBA", (len(idxs) * (W * sc) + (len(idxs) - 1) * 6, H * sc), (139, 139, 139, 255))
    for i, fi in enumerate(idxs):
        comp.alpha_composite(frames[fi].resize((W * sc, H * sc), Image.NEAREST), (i * (W * sc + 6), 0))
    comp.convert("RGB").save(path.replace(".png", "_fire_frames.png"))
    # GIF(크롭 경량)
    bb = strip.getbbox()  # 대략
    gif = []
    for im in frames:
        b = Image.new("RGBA", (W, H), (139, 139, 139, 255)); b.alpha_composite(im)
        gif.append(b.resize((W * 5, H * 5), Image.NEAREST).convert("P", palette=Image.ADAPTIVE, colors=64))
    gif[0].save(path.replace(".png", "_fire.gif"), save_all=True, append_images=gif[1:],
                duration=frametime * 50, loop=0, optimize=True)
    print(f"tip=({tx},{ty}) frames={N} → {path.replace('.png','_fire_frames.png')}")


if __name__ == "__main__":
    main()
