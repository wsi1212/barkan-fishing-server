#!/usr/bin/env python3
"""해부 스펙 기반 낚싯대 렌더러.

핵심 아이디어(유저 지시 2026-07-20): 물체의 '모든 지형적 특성'을 먼저 데이터로
선언하고, 렌더러는 그 스펙만 읽어 그린다. "불 달린 막대기"로 대충 넘어가지 못하게
해부학을 강제하는 것이 품질 레버.

낚싯대 해부(ANATOMY 스키마):
  blank   : 대(블랭크) — 베지어 곡선(butt→tip) + 테이퍼(굵기 butt→tip) + 재질 램프
  grip    : 손잡이 구간(t범위) + 재질 + 감은 밴드(wraps: t위치별 색)
  buttcap : 손잡이 끝단 캡
  ferrule : 릴시트/이음 금속 밴드(t범위)
  reel    : 릴 — 대 아래 스풀(원) + 크랭크 핸들
  guides  : 라인 가이드(관절 링) — t위치별로 대 법선방향 발+링, 팁으로 갈수록 작아짐
  tiptop  : 팁 가이드
  line    : 릴→가이드들 관통→팁→아래로 처지는 낚싯줄
  lure    : 줄 끝 루어(여기선 매달린 불덩이)
  cracks  : (선택) 용암 균열
  fx      : (선택) 오오라 — tip_flame / lure_flame / glow / embers
"""
import math, random
from PIL import Image
N = 64


def ramp(base, n=7, spread=0.72, hue=0.05, sat=0.16):
    import colorsys
    base = base.lstrip('#')
    r, g, b = [int(base[i:i+2], 16)/255 for i in (0, 2, 4)]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    out = []
    for i in range(n):
        t = (i/(n-1)) - 0.5
        vv = min(1, max(0.03, v + t*spread))
        hh = (h - t*hue) % 1.0
        ss = min(1, max(0, s - t*sat))
        rr, gg, bb = colorsys.hsv_to_rgb(hh, ss, vv)
        out.append('%02x%02x%02x' % (round(rr*255), round(gg*255), round(bb*255)))
    return out


def hx(h):
    h = h.lstrip('#'); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def put(im, x, y, c, a=255):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < N and 0 <= y < N:
        r, g, b = hx(c) if isinstance(c, str) else c[:3]
        im.putpixel((x, y), (r, g, b, a))


def bez(p0, cp, p1, t):
    u = 1 - t
    return (u*u*p0[0] + 2*u*t*cp[0] + t*t*p1[0],
            u*u*p0[1] + 2*u*t*cp[1] + t*t*p1[1])


def radius(A, t):
    """단차 있는 굵기 프로파일: 손잡이=굵게(rg) → 릴시트 어깨에서 뚝 떨어짐 → 얇은 대 테이퍼."""
    B = A["blank"]; ge = A["grip"]["t1"]
    rg, r0, r1 = B["r_grip"], B["r_blank0"], B["r_tip"]
    if t <= ge:
        return rg
    sh = 0.05                              # 어깨(단차) 폭
    if t <= ge + sh:
        return rg + (r0 - rg) * (t - ge) / sh
    return r0 + (r1 - r0) * (t - ge - sh) / (1 - ge - sh)


def bez_tan(p0, cp, p1, t):
    dx = 2*(1-t)*(cp[0]-p0[0]) + 2*t*(p1[0]-cp[0])
    dy = 2*(1-t)*(cp[1]-p0[1]) + 2*t*(p1[1]-cp[1])
    L = math.hypot(dx, dy) or 1
    return dx/L, dy/L


def normal(p0, cp, p1, t, side=1):
    tx, ty = bez_tan(p0, cp, p1, t)
    return (-ty*side, tx*side)          # 법선(대에서 수직으로 서는 방향)


def blank_mask(A):
    """블랭크 실루엣 마스크 (x,y)->t 와 중심선 샘플을 만든다."""
    p0, cp, p1 = A["blank"]["p0"], A["blank"]["cp"], A["blank"]["p1"]
    mask, centers = {}, []
    steps = 260
    for i in range(steps+1):
        t = i/steps
        cx, cy = bez(p0, cp, p1, t)
        centers.append((cx, cy, t))
        r = radius(A, t)
        rr = int(math.ceil(r))
        for dy in range(-rr-1, rr+2):
            for dx in range(-rr-1, rr+2):
                if dx*dx+dy*dy <= r*r:
                    x, y = int(round(cx+dx)), int(round(cy+dy))
                    if 0 <= x < N and 0 <= y < N:
                        mask[(x, y)] = min(mask.get((x, y), 1.0), t)
    return mask, centers


def shade_blank(im, A, mask):
    """실린더 셰이딩: 각 픽셀의 단면 오프셋을 광원(좌상)에 투영해 램프 인덱스를 정한다.
    얇은 구간도 '위=밝고 아래=어두운 원기둥'으로 일관되게 셰이딩됨(가장자리=전부밝음 버그 해소)."""
    WOOD = A["blank"]["ramp"]; GRIP = A["grip"]["ramp"]; METAL = A["ferrule"]["ramp"]
    g0, g1 = A["grip"]["t0"], A["grip"]["t1"]
    f0, f1 = A["ferrule"]["t0"], A["ferrule"]["t1"]
    p0, cp, p1 = A["blank"]["p0"], A["blank"]["cp"], A["blank"]["p1"]
    L = (-0.55, -0.84)                                   # 광원 방향(좌상, 위쪽 우세)

    def region(t):
        if g0 <= t < g1: return GRIP
        if f0 <= t < f1: return METAL
        return WOOD
    for (x, y), t in mask.items():
        pal = region(t); n = len(pal)
        cx, cy = bez(p0, cp, p1, t)
        r = max(0.9, radius(A, t))
        proj = ((x-cx)*L[0] + (y-cy)*L[1]) / r          # -1(그늘)..+1(광)
        idx = int(round(3 + proj*3.2))
        idx = max(1, min(n-1, idx))
        put(im, x, y, pal[idx])


def grain_and_cracks(im, A, mask, centers):
    rng = random.Random(A.get("seed", 7))
    g1 = A["grip"]["t1"]
    for cx, cy, t in centers[::7]:
        if t < g1:
            continue
        put(im, cx-0.4, cy-0.4, A["blank"]["ramp"][2])
        if rng.random() < 0.45:
            put(im, cx+0.6, cy+0.4, A["blank"]["ramp"][2])
    for c in A.get("cracks", []):
        pt = centers[int(c["t"]*(len(centers)-1))]
        cx, cy, _ = pt
        side = c.get("side", 1)
        for k in range(c.get("len", 4)):
            gx, gy = cx + side*k*0.7, cy - 1 + k*0.55
            if (int(round(gx)), int(round(gy))) in mask:
                put(im, gx, gy, A["fire"][4] if k < 2 else A["fire"][3])
                put(im, gx, gy-1, A["fire"][6])


def draw_wraps(im, A, mask, centers):
    """감은 밴드(빨간 가죽 등) — t위치에서 대 단면을 밴드 색으로 두른다."""
    for w in A["grip"].get("wraps", []) + A["blank"].get("wraps", []):
        t = w["t"]; col = w["ramp"]
        pt = centers[int(t*(len(centers)-1))]
        cx, cy, _ = pt
        r = radius(A, t)
        rr = int(math.ceil(r))+1
        width = w.get("w", 1)
        for cx2, cy2, tt in centers:
            if abs(tt-t) > width/ (len(centers)) :
                continue
            for dy in range(-rr, rr+1):
                for dx in range(-rr, rr+1):
                    if (int(round(cx2+dx)), int(round(cy2+dy))) in mask and dx*dx+dy*dy <= r*r+0.5:
                        top = dy < 0
                        put(im, cx2+dx, cy2+dy, col[4] if top else col[1])


def draw_buttcap(im, A, mask, centers):
    cap = A["buttcap"]["ramp"]
    cx, cy, _ = centers[0]
    r = A["blank"]["r_grip"]+1
    for dy in range(-int(r)-1, int(r)+2):
        for dx in range(-int(r)-1, int(r)+2):
            if (int(round(cx+dx)), int(round(cy+dy))) in mask and dx*dx+dy*dy <= r*r:
                edge = dx*dx+dy*dy > (r-1.3)**2
                put(im, cx+dx, cy+dy, cap[0] if edge else cap[2])


def draw_reel(im, A, centers):
    """스피닝 릴 — 얇은 발로 대와 분리해 매단 스풀 컵(림/면/허브 대비 명확) + 크랭크 팔+노브.
    은색으로 나무와 대비. 대에 붙은 덩어리로 보이지 않게 발로 띄운다."""
    R = A.get("reel")
    if not R:
        return
    cx, cy, _ = centers[int(R["t"]*(len(centers)-1))]
    nx, ny = normal(A["blank"]["p0"], A["blank"]["cp"], A["blank"]["p1"], R["t"], side=R.get("side", 1))
    tx_, ty_ = -ny, nx                            # 대 접선방향
    metal = A["reel"]["ramp"]
    stem = R.get("stem", 3)
    sx, sy = cx + nx*stem, cy + ny*stem           # 스풀 중심(대에서 stem만큼 아래)
    # 릴시트 발(가늘게 1px) — 대와 스풀을 분리
    for k in range(1, stem):
        put(im, cx+nx*k, cy+ny*k, metal[1])
    rr = R.get("r", 4)
    # 스풀 컵: 림(어두움) + 면(좌상 라이트→우하 섀도) — 얼굴이 살짝 보이는 개방형 스풀
    for dy in range(-rr, rr+1):
        for dx in range(-rr, rr+1):
            d = math.hypot(dx, dy)
            if d <= rr:
                if d >= rr-1.0:
                    put(im, sx+dx, sy+dy, metal[0])                 # 두꺼운 어두운 림
                else:
                    s = (dx*(-0.6)+dy*(-0.8))/rr                    # 좌상 광
                    put(im, sx+dx, sy+dy, metal[max(1, min(6, int(round(3+s*3))))])
    # 스풀 허브(중심 나사) + 반짝
    put(im, sx, sy, metal[0]); put(im, sx-1, sy-1, metal[6])
    # 크랭크: 스풀 옆(접선방향)으로 뻗은 팔 + 둥근 노브
    ar = rr+1
    axx, ayy = sx+tx_*ar, sy+ty_*ar
    for k in range(rr, ar+2):
        put(im, sx+tx_*k, sy+ty_*k, metal[2])
    kx, ky = sx+tx_*(ar+2), sy+ty_*(ar+2)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx*dx+dy*dy <= 2:
                put(im, kx+dx, ky+dy, metal[4] if (dx+dy) < 0 else metal[2])
    return (cx, cy)                               # 줄 시작(참고용)


def guide_ring(im, bx, by, nx, ny, size, metal):
    """대 표면에 밀착한 작은 라인 가이드: 1px 발 + 작은 속빈 링. (멀리 띄우면 색종이됨)"""
    put(im, bx, by, metal[2])                  # 발(대에 붙음)
    fx, fy = bx + nx*size, by + ny*size        # 링 중심(살짝만 띄움)
    ro = 1.5
    for a in range(0, 360, 45):
        rx = fx + math.cos(math.radians(a))*ro
        ry = fy + math.sin(math.radians(a))*ro
        put(im, rx, ry, metal[5] if math.sin(math.radians(a)) < 0 else metal[1])
    return (fx, fy, ro)


def draw_guides_and_line(im, A, mask, centers, reel_anchor):
    """가이드 링들 + 릴→가이드 관통→팁→처지는 줄."""
    p0, cp, p1 = A["blank"]["p0"], A["blank"]["cp"], A["blank"]["p1"]
    metal = A.get("guides_ramp") or A["ferrule"]["ramp"]
    line_col = A["line"]["col"]
    for g in A["guides"]:                        # 가이드 링만(대를 따라가는 줄은 안 그림)
        t = g["t"]
        cx, cy = bez(p0, cp, p1, t)
        nx, ny = normal(p0, cp, p1, t, side=A["guides_side"])
        r = radius(A, t)
        guide_ring(im, cx+nx*r, cy+ny*r, nx, ny, g["size"], metal)
    # 팁탑
    tx, ty = bez(p0, cp, p1, 1.0)
    nx, ny = normal(p0, cp, p1, 1.0, side=A["guides_side"])
    fx, fy, _ = guide_ring(im, tx, ty, nx, ny, A["tiptop"]["size"], metal)
    return (fx, fy)                               # 팁탑 = 처지는 줄의 출발점


def draw_hanging_line(im, A, tip_ring):
    """팁에서 아래로 처지는 줄 → 루어 부착점 반환."""
    tx, ty = tip_ring
    drop = A["line"]["drop"]
    lx, ly = tx + A["line"].get("drift", -2), ty + drop
    cpx, cpy = tx + 3, ty + drop*0.5           # 처짐(sag)
    end = None
    seg = 48
    for s in range(seg+1):
        t = s/seg; u = 1-t
        x = u*u*tx + 2*u*t*cpx + t*t*lx
        y = u*u*ty + 2*u*t*cpy + t*t*ly
        put(im, x, y, A["line"]["col"])
        end = (x, y)
    return end


def flame(im, cx, base_y, height, half_w, phase, fire, up=True, seed=0):
    n = len(fire)
    for i in range(height):
        ft = i/height
        y = base_y - i if up else base_y + i
        prof = math.sin(min(1.0, ft*1.12)*math.pi)
        w = half_w*(0.4+0.75*prof)
        sway = math.sin(ft*5.5+phase)*(half_w*0.35*ft)
        for dx in range(int(-w-1), int(w+2)):
            if abs(dx) > w: continue
            d = abs(dx)/max(1.0, w)
            heat = (1.0-ft*0.72)-d*0.55
            idx = max(1, min(n-1, int(round(heat*(n-1)))))
            put(im, cx+dx+sway, y, fire[idx])
    er = random.Random(seed*131+int(phase*97))
    for _ in range(er.choice((0, 1, 1))):
        ex = cx+er.choice((-half_w, half_w-1, half_w))
        ey = (base_y-height-er.choice((1, 2, 3))) if up else (base_y+height+er.choice((1, 2)))
        put(im, ex, ey, er.choice(fire[4:7]))


def apply_glow(im, A, mask):
    """불꽃 근처 나무를 살짝 데운다 — 마스크 픽셀당 정확히 1회 블렌드(중복적용 금지)."""
    if "glow" not in A["fx"]:
        return
    warm = hx(A["fire"][5])
    frm = A["fx"]["glow"].get("from_t", 0.8)
    for (x, y), t in mask.items():
        if t < frm:
            continue
        k = (t-frm)/max(0.01, 1-frm)
        m = 0.25*k
        px = im.getpixel((x, y))
        if px[3] > 0:
            im.putpixel((x, y), (min(255, int(px[0]*(1-m)+warm[0]*m)),
                                 min(255, int(px[1]*(1-m)+warm[1]*m)),
                                 min(255, int(px[2]*(1-m)+warm[2]*m)), 255))


def render(A, phase=0.0, seed=0):
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    mask, centers = blank_mask(A)
    shade_blank(im, A, mask)
    grain_and_cracks(im, A, mask, centers)
    draw_wraps(im, A, mask, centers)
    draw_buttcap(im, A, mask, centers)
    reel_anchor = draw_reel(im, A, centers) or centers[int(A["grip"]["t1"]*(len(centers)-1))][:2]
    apply_glow(im, A, mask)
    tip_ring = draw_guides_and_line(im, A, mask, centers, reel_anchor)
    lure_pt = draw_hanging_line(im, A, tip_ring)
    fx = A.get("fx", {})
    if "tip_flame" in fx:
        tx, ty = bez(A["blank"]["p0"], A["blank"]["cp"], A["blank"]["p1"], 1.0)
        flame(im, tx+0.5, ty-2, fx["tip_flame"]["h"], fx["tip_flame"]["w"], phase, A["fire"], up=True, seed=seed)
    if "lure_flame" in fx and lure_pt:
        flame(im, lure_pt[0], lure_pt[1]-fx["lure_flame"]["h"]//2, fx["lure_flame"]["h"],
              fx["lure_flame"]["w"], phase*1.2+1.3, A["fire"], up=False, seed=seed+5)
        put(im, lure_pt[0], lure_pt[1], "241610")   # 갈고리
    return im


# ───────── 불의 낚싯대 해부 스펙 ─────────
def fire_rod_anatomy():
    return {
        "seed": 7,
        "blank": {
            "p0": (13, 53), "cp": (30, 18), "p1": (53, 12),   # butt→tip, 위로 볼록한 자연스런 휨
            "r_grip": 4.6, "r_blank0": 2.4, "r_tip": 0.8,     # 손잡이 굵고 → 릴시트 단차 → 얇은 대
            "ramp": ramp("6a3d1f"),
            "wraps": [],   # 대 몸통엔 빨간밴드 없음(레퍼런스=빨강은 손잡이만, 몸통은 용암균열)
        },
        "grip": {"t0": 0.0, "t1": 0.26, "ramp": ramp("2f1d12"),
                 "wraps": [{"t": 0.09, "ramp": ramp("cc2b1e"), "w": 1.4},
                           {"t": 0.19, "ramp": ramp("cc2b1e"), "w": 1.4}]},  # 손잡이 빨간 가죽선 2개
        "buttcap": {"ramp": ramp("241610")},
        "ferrule": {"t0": 0.26, "t1": 0.32, "ramp": ramp("caa63a")},   # 릴시트=황동
        "reel": {"t": 0.32, "side": 1, "stem": 4, "r": 4, "ramp": ramp("9aa4ad")},  # 은색 릴
        "guides_ramp": ramp("6b7079"),   # 가이드=어두운 강철(황동보다 덜 튐)
        "guides": [{"t": 0.47, "size": 2}, {"t": 0.64, "size": 2}, {"t": 0.81, "size": 2}],
        "guides_side": -1,           # 대 위쪽(줄이 윗면으로 흐름 — 아래 루어 공간 안 침범)
        "tiptop": {"size": 2},
        "line": {"col": "d8d2c4", "drop": 26, "drift": -3},
        "fire": ["4a0a05", "8f1d0a", "c8390f", "e8631c", "f59a2e", "ffcf5a", "fff2c0"],
        "cracks": [{"t": 0.40, "side": 1, "len": 4}, {"t": 0.56, "side": -1, "len": 3},
                   {"t": 0.70, "side": 1, "len": 3}],
        "fx": {"tip_flame": {"h": 10, "w": 3}, "lure_flame": {"h": 13, "w": 5},
               "glow": {"from_t": 0.86}},
    }


if __name__ == "__main__":
    import os
    HERE = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(HERE, "out", "hires"); os.makedirs(out, exist_ok=True)
    A = fire_rod_anatomy()
    frames = [render(A, ph, s) for s, ph in enumerate([0.0, 1.6, 3.1, 4.7, 6.0, 1.0])]
    frames[0].resize((N*8, N*8), Image.NEAREST).save(os.path.join(out, "firerod2_big.png"))
    strip = Image.new("RGBA", (N, N*len(frames)), (0, 0, 0, 0))
    for i, f in enumerate(frames): strip.paste(f, (0, i*N))
    strip.save(os.path.join(out, "firerod2_anim.png"))
    open(os.path.join(out, "firerod2_anim.png.mcmeta"), "w").write('{"animation":{"frametime":3}}')
    gif = []
    for f in frames:
        b = Image.new("RGBA", (N, N), (139, 139, 139, 255)); b.alpha_composite(f)
        gif.append(b.resize((N*6, N*6), Image.NEAREST).convert("P"))
    gif[0].save(os.path.join(out, "firerod2.gif"), save_all=True, append_images=gif[1:], duration=150, loop=0)
    print("done")
