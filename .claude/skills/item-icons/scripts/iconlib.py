#!/usr/bin/env python3
"""아이템 아이콘 공용 브러시 — 16×16 인벤토리 아이콘 전용 저수준 도구.

색 근거는 pixel-art 스킬의 palette.ramp(휴시프트 램프)를 그대로 쓰고,
여기에는 '형태' 도구만 둔다: 베지어/폴리라인 경로, 테이퍼 스트로크(윗면 라이트·
아랫면 코어섀도 내장 = 원통 형태 셰이딩), 자동 셀아웃, 스파클, 디스크.
모든 그리기는 PIL RGBA 캔버스에 in-place. 좌표계 (0,0)=좌상단, 광원=좌상단 고정.
"""
from PIL import Image


def hx(h, a=255):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def _c(col, a=255):
    return hx(col, a) if isinstance(col, str) else col


def canvas(n=16):
    return Image.new("RGBA", (n, n), (0, 0, 0, 0))


def put(im, x, y, col):
    """경계 체크 픽셀 세트 — 아이콘 코드는 항상 이걸 쓴다(경로 계산이 캔버스를 벗어나기 쉬움)."""
    x, y = int(x), int(y)
    if 0 <= x < im.size[0] and 0 <= y < im.size[1]:
        im.putpixel((x, y), _c(col))


def qbez(p0, c, p1, steps=64):
    """2차 베지어 → (x,y,t) 실수 점 목록. 낚싯대 샤프트의 '휨(텐션)'이 여기서 나온다."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        pts.append((u*u*p0[0] + 2*u*t*c[0] + t*t*p1[0],
                    u*u*p0[1] + 2*u*t*c[1] + t*t*p1[1], t))
    return pts


def polyline(points, steps_per=12):
    """꺾인 폴리라인 → (x,y,t). 나뭇가지처럼 '삐뚤빼뚤'이 정체성일 때 베지어 대신 사용."""
    pts = []
    n = len(points) - 1
    for s in range(n):
        (x0, y0), (x1, y1) = points[s], points[s + 1]
        for i in range(steps_per + 1):
            k = i / steps_per
            pts.append((x0 + (x1-x0)*k, y0 + (y1-y0)*k, (s + k) / n))
    return pts


def cells(pts):
    """실수 경로 → 중복 제거된 정수 셀 목록(경로 순서 유지). 반환 [(cx,cy,t)...]"""
    out, seen = [], set()
    for x, y, t in pts:
        c = (int(round(x)), int(round(y)))
        if c not in seen:
            seen.add(c)
            out.append((c[0], c[1], t))
    return out


def shaft(im, cl, colfn, pair_until=0.62):
    """테이퍼 스트로크 — 낚싯대/지팡이/자루의 핵심 브러시.
    t<=pair_until 구간(굵은 쪽): 윗셀=라이트, 아랫셀=코어섀도(누운 원통을 좌상단에서
    비춘 형태 셰이딩이 브러시에 내장됨). 그 뒤(팁 쪽): 미드 톤 1px 테이퍼.
    colfn(t) -> (mid, light, dark) 헥스 3튜플 — t로 그라데이션 샤프트도 가능(여명 등).
    """
    for cx, cy, t in cl:
        mid, light, dark = colfn(t)
        if t <= pair_until:
            put(im, cx, cy, light)
            put(im, cx, cy + 1, dark)
        else:
            put(im, cx, cy, mid)


def flat_colfn(ramp5):
    """단색 재질 샤프트: mid=r2, light=r3, dark=r1."""
    return lambda t: (ramp5[2], ramp5[3], ramp5[1])


def blend_hex(h1, h2, k):
    a, b = hx(h1), hx(h2)
    return '%02x%02x%02x' % tuple(round(a[i] + (b[i]-a[i]) * k) for i in range(3))


def grade_colfn(ramp_a, ramp_b, bands=4):
    """t=0에서 ramp_a, t=1에서 ramp_b로 흐르는 그라데이션 샤프트(여명·천공용).
    bands 단계로 양자화 — 셀마다 새 색을 만들면 색 수가 폭발한다(램프 원칙 유지)."""
    def f(t):
        k = round(t * (bands - 1)) / (bands - 1)
        return (blend_hex(ramp_a[2], ramp_b[2], k),
                blend_hex(ramp_a[3], ramp_b[3], k),
                blend_hex(ramp_a[1], ramp_b[1], k))
    return f


def ring_at(im, cl, t_target, col_top, col_bot=None):
    """샤프트 위 마디/페룰 링(대나무 마디, 금테). 폭2 구간이면 위아래 둘 다 찍는다."""
    best = min(cl, key=lambda c: abs(c[2] - t_target))
    put(im, best[0], best[1], col_top)
    if col_bot:
        put(im, best[0], best[1] + 1, col_bot)


def grip(im, cl, ramp5, upto=0.16, cap=True):
    """손잡이 랩(감은 끈) — t<=upto 구간을 3px 두께 밴드 패턴으로 덮는다."""
    gcells = [c for c in cl if c[2] <= upto]
    for i, (cx, cy, t) in enumerate(gcells):
        band = ramp5[3] if i % 2 == 0 else ramp5[1]
        put(im, cx, cy - 1, ramp5[3] if i % 2 == 0 else ramp5[2])
        put(im, cx, cy, band)
        put(im, cx, cy + 1, ramp5[0])
    if cap and gcells:
        put(im, gcells[0][0] - 1, gcells[0][1] + 1, ramp5[0])  # 버트 캡


def hang_line(im, tip, drop=5, drift=1, col="c8c8c8", sag=0.45):
    """팁에서 낚싯줄을 아래로 늘어뜨린다. 반환: 줄 끝 좌표(루어/찌 부착점)."""
    tx, ty = tip
    p0 = (tx + 1, ty)
    p1 = (tx + 1 + drift, ty + drop)
    c = (tx + 1 + drift + 1, ty + drop * sag)
    end = None
    for cx, cy, t in cells(qbez(p0, c, p1, 32)):
        put(im, cx, cy, col)
        end = (cx, cy)
    return end


def disk(im, cx, cy, r, col):
    for y in range(int(cy - r), int(cy + r) + 1):
        for x in range(int(cx - r), int(cx + r) + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + 0.25:
                put(im, x, y, col)


def sparkle(im, x, y, col, arm=1):
    """+자 반짝이. arm=0이면 점 하나."""
    put(im, x, y, col)
    for d in range(1, arm + 1):
        for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d)):
            put(im, x + dx, y + dy, col)


def selout(im, dark, light=None):
    """자동 셀아웃(선택적 외곽선) — 덩어리 형태(찌·미끼·배지)용 마감 패스.
    아래/오른쪽이 빈 가장자리 픽셀 → 어두운 램프색(외곽선), 위/왼쪽이 빈 픽셀 → 라이트(림라이트).
    검정 대신 램프의 어두운 색을 쓰는 것이 바닐라급/아마추어를 가르는 지점."""
    src = im.copy()
    W, H = im.size
    for y in range(H):
        for x in range(W):
            if src.getpixel((x, y))[3] == 0:
                continue
            up = y == 0 or src.getpixel((x, y - 1))[3] == 0
            lf = x == 0 or src.getpixel((x - 1, y))[3] == 0
            dn = y == H - 1 or src.getpixel((x, y + 1))[3] == 0
            rt = x == W - 1 or src.getpixel((x + 1, y))[3] == 0
            if dn or rt:
                put(im, x, y, dark)
            elif (up or lf) and light:
                put(im, x, y, light)


def edge_cells(im):
    """실루엣 가장자리(불투명이면서 투명 이웃 보유) — fx 오오라 앵커 소스."""
    W, H = im.size
    out = []
    for y in range(H):
        for x in range(W):
            if im.getpixel((x, y))[3] == 0:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and im.getpixel((nx, ny))[3] == 0:
                    out.append((x, y))
                    break
    return out
