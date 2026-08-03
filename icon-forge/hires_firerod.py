#!/usr/bin/env python3
"""고해상도 화염 낚싯대 — 16×16이 한계가 아님을 보이는 히어로 아이콘.
64×64, 광원 좌상단, 나뭇결+용암 균열 샤프트 + 감은 그립 + 팁 화염 + 매달린 불덩이 루어.
불꽃은 프레임 애니메이션(바닐라 .mcmeta). 출력: 큰 프리뷰 / GIF / 슬롯 실물 스케일 비교.
"""
import os, sys, math, random
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".claude", "skills", "pixel-art", "scripts"))
from palette import ramp

N = 64
WOOD = ramp("6a3d1f", 7)          # 어두운 갈색 → 따뜻한 나무
GRIP = ramp("3a2418", 7)          # 가죽 그립
METAL = ramp("8a8f96", 7)         # 금속 페룰
FIRE = ["4a0a05", "8f1d0a", "c8390f", "e8631c", "f59a2e", "ffcf5a", "fff2c0", "ffffff"]
EMBER = ["e8631c", "f59a2e", "ffcf5a"]


def hx(h):
    h = h.lstrip("#"); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def put(im, x, y, c, a=255):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < N and 0 <= y < N:
        r, g, b, _ = hx(c) if isinstance(c, str) else c
        im.putpixel((x, y), (r, g, b, a))


def bez(p0, cp, p1, steps=220):
    for i in range(steps + 1):
        t = i / steps; u = 1 - t
        yield (u*u*p0[0] + 2*u*t*cp[0] + t*t*p1[0],
               u*u*p0[1] + 2*u*t*cp[1] + t*t*p1[1], t)


def build_rod():
    """샤프트를 실루엣 마스크 → 형태 셰이딩 → 나뭇결 → 용암 균열 순으로 굽는다."""
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    center = list(bez((15, 52), (30, 26), (50, 13)))   # 손잡이(좌하) → 팁(우상)
    mask = {}                                           # (x,y) -> t
    for cx, cy, t in center:
        r = 4.2 - 2.4 * t                               # 손잡이 굵고 팁 얇게
        for dy in range(-5, 6):
            for dx in range(-5, 6):
                if dx*dx + dy*dy <= r*r:
                    x, y = int(round(cx+dx)), int(round(cy+dy))
                    if 0 <= x < N and 0 <= y < N:
                        mask[(x, y)] = min(mask.get((x, y), 1), t)
    # 구역: t=0 손잡이(좌하) → t=1 팁(우상).  그립=손잡이, 페룰=경계, 나머지=나무
    def region(t):
        if t < 0.26: return "grip"
        if t < 0.33: return "ferrule"
        return "wood"
    # 형태 셰이딩: 빈 이웃 방향으로 림 라이트(좌상)/코어 섀도(우하)
    for (x, y), t in mask.items():
        up = (x, y-1) not in mask; lf = (x-1, y) not in mask
        dn = (x, y+1) not in mask; rt = (x+1, y) not in mask
        ul = (x-1, y-1) not in mask; dr = (x+1, y+1) not in mask
        rg = region(t)
        pal = GRIP if rg == "grip" else (METAL if rg == "ferrule" else WOOD)
        if (up or lf or ul) and not (dn or rt):
            idx = 6 if rg == "wood" else 5              # 라이트
        elif dn or rt or dr:
            idx = 1                                     # 섀도 림
        else:
            idx = 3                                     # 미드
        put(im, x, y, pal[idx])
    # 나뭇결: 나무 구간 중심선 따라 어두운 파선
    rng = random.Random(7)
    for cx, cy, t in center[::9]:
        if region(t) != "wood":
            continue
        put(im, cx-0.5, cy-0.5, WOOD[2])
        if rng.random() < 0.5:
            put(im, cx+0.7, cy+0.3, WOOD[2])
    # 그립 밴드(감은 끈): 손잡이 구간에 3px 간격 링
    band = 0
    for cx, cy, t in center:
        if region(t) == "grip" and int(cx+cy) % 3 == 0:
            for dy in range(-5, 6):
                for dx in range(-5, 6):
                    if (int(round(cx+dx)), int(round(cy+dy))) in mask and dx*dx+dy*dy <= 20:
                        put(im, cx+dx, cy+dy, GRIP[5] if band % 2 == 0 else GRIP[1])
            band += 1
    # 손잡이 버트 캡(끝단 강조)
    hcx, hcy, _ = center[0]
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            if (int(round(hcx+dx)), int(round(hcy+dy))) in mask and dx*dx+dy*dy <= 16:
                put(im, hcx+dx, hcy+dy, GRIP[0] if dx*dx+dy*dy > 8 else GRIP[2])
    # 용암 균열: 나무 위를 흐르는 밝은 갈라짐 + 글로우
    crack_seed = [(0.42, 1), (0.55, -1), (0.68, 1), (0.8, -1)]
    for ct, side in crack_seed:
        pt = center[int(ct * (len(center)-1))]
        cx, cy = pt[0], pt[1]
        for k in range(4):
            gx, gy = cx + side*(k*0.7), cy - 1 + k*0.6
            if (int(round(gx)), int(round(gy))) in mask:
                put(im, gx, gy, FIRE[4] if k < 2 else FIRE[3])
                put(im, gx, gy-1, FIRE[6])              # 밝은 심
    return im, center, mask


def flame(im, cx, base_y, height, half_w, phase, up=True, seed=0):
    """물방울형 불꽃. up=True면 위로 타오름(팁), False면 아래로 매달림(루어)."""
    n = len(FIRE)
    for i in range(height):
        ft = i / height                                 # 0=뿌리, 1=끝
        y = base_y - i if up else base_y + i
        prof = math.sin(min(1.0, ft*1.12) * math.pi)    # 0..1..0 폭 프로파일
        w = half_w * (0.4 + 0.75 * prof)
        sway = math.sin(ft*5.5 + phase) * (half_w*0.35*ft)
        for dx in range(int(-w-1), int(w+2)):
            if abs(dx) > w:
                continue
            d = abs(dx) / max(1.0, w)
            heat = (1.0 - ft*0.72) - d*0.55             # 안쪽·뿌리가 가장 뜨겁다
            idx = max(1, min(n-1, int(round(heat * (n-1)))))
            put(im, cx+dx+sway, y, FIRE[idx])
    # 떠오르는 불티
    er = random.Random(seed*131 + int(phase*97))
    for _ in range(er.choice((2, 3))):
        ex = cx + er.choice((-half_w, -half_w+1, half_w-1, half_w))
        ey = (base_y - height - er.choice((1, 2, 3))) if up else (base_y + height + er.choice((1, 2)))
        put(im, ex, ey, er.choice(EMBER))


def build_frame(rod, center, phase, seed):
    im = rod.copy()
    tip = center[-1]
    tx, ty = tip[0], tip[1]
    # 팁 화염(위로)
    flame(im, tx+0.5, ty-1, 15, 5.5, phase, up=True, seed=seed)
    # 낚싯줄(팁 → 루어)
    lure_x, lure_y = tx-2, ty + 26
    for cx, cy, t in bez((tx+1, ty), (tx+3.5, ty+13), (lure_x, lure_y-9), 60):
        put(im, cx, cy, "b9b19c")
    # 매달린 불덩이 루어(아래로 타오르는 큰 불꽃 + 안쪽 갈고리)
    flame(im, lure_x, lure_y-9, 20, 8, phase*1.2 + 1.3, up=False, seed=seed+5)
    put(im, lure_x, lure_y-2, "2a1a12"); put(im, lure_x, lure_y-1, "2a1a12")
    put(im, lure_x-1, lure_y, "2a1a12")                 # 갈고리 J
    return im


def slot_mock(icon, scales, out):
    """바닐라 인벤 슬롯(18px, 회색 #8B8B8B) 위에 여러 스케일로 올려 '실물 크기'를 본다."""
    PANEL, SLOT, DK, LT = (198,198,198,255), (139,139,139,255), (55,55,55,255), (255,255,255,255)
    pad = 6; sc = 10
    W = pad*2 + len(scales)*(18*sc + 8) - 8
    H = pad*2 + 18*sc + 22
    board = Image.new("RGBA", (W, H), PANEL)
    for i, s in enumerate(scales):
        x0 = pad + i*(18*sc+8); y0 = pad
        for x in range(18*sc):
            for yy in (0, 18*sc-1): board.putpixel((x0+x, y0+yy), DK if yy==0 else LT)
        for y in range(18*sc):
            for xx in (0, 18*sc-1): board.putpixel((x0+xx, y0+y), DK if xx==0 else LT)
        for x in range(1, 18*sc-1):
            for y in range(1, 18*sc-1): board.putpixel((x0+x, y0+y), SLOT)
        small = icon.resize((s, s), Image.LANCZOS)      # 실제 렌더처럼 축소
        big = small.resize((16*sc, 16*sc), Image.NEAREST)
        board.alpha_composite(big, (x0 + sc, y0 + sc))
    board.save(out)


def main():
    out = os.path.join(HERE, "out", "hires"); os.makedirs(out, exist_ok=True)
    rod, center, mask = build_rod()
    frames = [build_frame(rod, center, ph, s) for s, ph in
              enumerate([0.0, 1.6, 3.1, 4.7, 6.0, 1.0])]
    # 애니 스트립 + mcmeta
    strip = Image.new("RGBA", (N, N*len(frames)), (0,0,0,0))
    for i, f in enumerate(frames): strip.paste(f, (0, i*N))
    strip.save(os.path.join(out, "firerod_anim.png"))
    open(os.path.join(out, "firerod_anim.png.mcmeta"), "w").write('{"animation":{"frametime":3}}')
    # 큰 프리뷰(정지, 8배)
    frames[0].resize((N*8, N*8), Image.NEAREST).save(os.path.join(out, "firerod_big.png"))
    # GIF(회색 슬롯 배경)
    gif = []
    for f in frames:
        b = Image.new("RGBA", (N, N), (139,139,139,255)); b.alpha_composite(f)
        gif.append(b.resize((N*6, N*6), Image.NEAREST).convert("P"))
    gif[0].save(os.path.join(out, "firerod.gif"), save_all=True, append_images=gif[1:],
                duration=150, loop=0)
    # 슬롯 실물 스케일 비교(16/32/64px로 축소해 슬롯에 올림)
    slot_mock(frames[0], [16, 32, 64], os.path.join(out, "firerod_slots.png"))
    print("done →", out)


if __name__ == "__main__":
    main()
