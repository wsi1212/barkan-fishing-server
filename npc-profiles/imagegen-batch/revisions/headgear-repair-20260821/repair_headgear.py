#!/usr/bin/env python3
"""요한(Citizens 162) 초상 «널빤지 헤드기어» 아티팩트 제거 — 재실행 가능한 생성기.

원인: 이미지 생성 단계에서 참조로 넣은 identity 보드/64x64 스킨 아틀라스(펼친 평면
텍스처)를 모델이 «머리에 쓴 물건»으로 읽어, 머리 위에 정육면체 + 좌우로 뻗은 빗살
널빤지를 그렸다. 아티팩트는 머리·머리카락 실루엣 «밖»에만 있고 그 아래 머리카락은
온전히 그려져 있다 → 재생성 없이 실루엣 밖을 지우는 것으로 복구된다.

절차
  1. 기준 곡선(CUT)을 base 투명 원본(1122x1402) 좌표계에서 1회 정의한다.
  2. 대상 이미지(1254x1254 3장)는 몸통 알파 윤곽으로 (s, tx, ty) 를 자동 정합해
     같은 곡선을 옮겨 쓴다. 손으로 3번 트레이스하지 않는다.
  3. 곡선 위쪽 픽셀을 지우고, 초록 스필 제거 + 미세 파편 제거를 한다.
  4. 결과를 transparent/ 에 쓰고, framed/ 에 128x154 미리보기를 낸다.
     실제 배포 애셋(+_sm/_md/_lg/_xl)은 deploy_assets.py 가 매니페스트 source 에서
     gen_npc_portrait_huds.frame() 으로 «다시 뽑는다» (사본 고정 금지).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
BATCH = HERE.parents[1]
REF = BATCH / "style-test" / "batch15-skin-confirmed" / "transparent" / "162_길드접수원.png"

TARGETS = {
    "base": BATCH / "style-test" / "batch15-skin-confirmed" / "framed" / "162_길드접수원.png",
    "progress": BATCH / "emotions" / "phase06" / "transparent" / "162_길드접수원_progress.png",
    "complete": BATCH / "emotions" / "phase06" / "transparent" / "162_길드접수원_complete.png",
}

# 기준 좌표계(REF, 1122x1402)에서 읽은 머리·머리카락 실루엣 상단.
# 이 선 «위»는 전부 아티팩트다. x<=277 은 좌측 널빤지만 있는 구간(아래 400 까지 비어 있다),
# x>=720 은 우측 널빤지만 있는 구간이라 열별 몸통 상단에서 자동 산출한다.
CUT = [
    (0, 400), (277, 400),
    # 왼쪽 널빤지가 머리카락과 섞이는 구간(가닥 끝은 아래에 남긴다)
    (278, 332), (280, 350), (285, 350), (288, 300),
    # 여기부터는 머리카락 «어두운 외곽선» 실측치(열별 최소 휘도)
    (290, 270), (295, 258), (300, 246), (305, 238), (310, 230), (320, 220),
    (330, 211), (340, 207), (350, 201), (360, 199), (370, 197), (380, 197),
    (390, 194), (400, 192), (410, 191), (420, 189), (430, 190), (440, 187),
    (450, 178), (460, 174), (470, 168), (480, 168), (490, 171), (500, 171),
    (510, 167), (520, 164), (530, 164), (540, 161), (550, 164), (560, 165),
    (570, 169), (580, 173), (590, 175), (600, 180), (610, 185), (620, 192),
    (630, 197), (640, 209), (660, 238), (680, 262), (700, 282), (710, 272),
    (715, 283), (719, 300),
]
AUTO_RIGHT_X = 720      # 이 x 이상은 열별 자동
AUTO_SCAN_FROM = 420    # 우측 널빤지 아래에서 시작해 몸통 상단을 찾는다
AUTO_CAP = 520          # 자동 구간 최대 절단선
RUN_SLACK = 10          # 절단선 바로 아래에서 시작하는 런은 통째로 남긴다(머리카락)
ALPHA_ON = 16
SPECK_MAX = 48          # 이보다 작은 고립 조각은 제거


def interp(table, x):
    if x <= table[0][0]:
        return table[0][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x0 <= x <= x1:
            return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return table[-1][1]


def profile(im: Image.Image):
    """행별 (불투명 픽셀 수, 가로 무게중심). 아티팩트의 빗살까지 담긴 서명이라
    머리 구간 정합에 쓰기 좋다(몸통 정합은 재생성마다 머리와 어긋난다)."""
    a = im.getchannel("A").load()
    w, h = im.size
    n, cx = [], []
    for y in range(h):
        c = s = 0
        for x in range(w):
            if a[x, y] > ALPHA_ON:
                c += 1
                s += x
        n.append(c)
        cx.append(s / c if c else None)
    return n, cx


def fit(src: Image.Image, dst: Image.Image, y0: int = 20, y1: int = 560):
    """dst ≈ s*src + t. 상단(아티팩트+머리) 알파 프로필을 1D 매칭한다."""
    sn, scx = profile(src)
    dn, dcx = profile(dst)
    h = dst.height
    best = None
    s = 0.88
    while s <= 1.12001:
        for ty in range(-80, 81):
            err = cnt = 0
            for y in range(y0, min(y1, src.height), 4):
                yy = int(round(s * y + ty))
                if 0 <= yy < h:
                    err += abs(dn[yy] - s * sn[y])
                    cnt += 1
            if cnt:
                e = err / cnt
                if best is None or e < best[0]:
                    best = (e, s, ty)
        s += 0.005
    e, s, ty = best
    num = cnt = 0
    for y in range(y0, min(y1, src.height), 2):
        yy = int(round(s * y + ty))
        if 0 <= yy < h and scx[y] is not None and dcx[yy] is not None:
            num += dcx[yy] - s * scx[y]
            cnt += 1
    return (e, s, num / cnt, float(ty))


def khaki_pixels(im: Image.Image):
    """정육면체 윗면의 카키색 화소 목록. 널빤지(r-b≈34)·피부(b≈111)와 구별되는
    r-b>=52 & b<=95 조건이다. 정합 미세보정과 잔여 검사의 지표로 쓴다."""
    px = im.load()
    w, h = im.size
    out = []
    for y in range(int(h * 0.18)):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > ALPHA_ON and r - b >= 52 and b <= 95:
                out.append((x, y))
    return out


REF_CUT = None


def ref_cut_table():
    """기준 좌표계 x -> 절단 y (1회 계산, refine 의 내부 루프를 정수 인덱싱으로 만든다)."""
    global REF_CUT
    if REF_CUT is None:
        REF_CUT = [interp(CUT, x) for x in range(1200)]
    return REF_CUT


def refine(im: Image.Image, s: float, tx: float, ty: float, span: int = 16):
    """카키 잔여를 최소화하도록 (tx, ty) 를 국소 보정한다.

    ★재생성된 표정 변형은 몸통·머리 정합이 서로 어긋난다(실측 progress 8.5px).
      정합을 눈으로 맞추는 대신 «지워야 할 것이 남았는가» 를 목적함수로 쓴다.
      같은 잔여량이면 덜 지우는 쪽(머리카락 보존)을 고른다.
    """
    table = ref_cut_table()
    kp = khaki_pixels(im)[::5]
    if not kp:
        return tx, ty, 0
    w = im.width
    best = None
    for dtx in range(-span, span + 1, 2):
        for dty in range(-span, span + 1, 2):
            cut = []
            for x in range(w):
                xr = int(round((x - (tx + dtx)) / s))
                cut.append(s * table[min(max(xr, 0), len(table) - 1)] + ty + dty)
            left = sum(1 for x, y in kp if y >= cut[x])
            # 동률이면 프로필 정합값에 가장 가까운 쪽(자의적 이동 방지)
            key = (left, abs(dtx) + abs(dty))
            if best is None or key < best[0]:
                best = (key, tx + dtx, ty + dty)
    (left, _), btx, bty = best
    return btx, bty, left * 5


def runs(alpha, x, h):
    out, start = [], None
    for y in range(h):
        on = alpha[x, y] > ALPHA_ON
        if on and start is None:
            start = y
        if not on and start is not None:
            out.append((start, y - 1))
            start = None
    if start is not None:
        out.append((start, h - 1))
    return out


def despeck(im: Image.Image, ylimit: int) -> int:
    """ylimit 위쪽의 작은 고립 조각(크로마 잔여물)을 지운다."""
    w, h = im.size
    a = im.getchannel("A").load()
    px = im.load()
    seen = [[False] * min(h, ylimit) for _ in range(w)]
    removed = 0
    for x in range(w):
        for y in range(min(h, ylimit)):
            if seen[x][y] or a[x, y] <= ALPHA_ON:
                continue
            stack, comp = [(x, y)], []
            seen[x][y] = True
            # ★조기 break 금지 — 큰 덩어리를 중간에 끊으면 seen 이 반쯤 칠해진 채 남아
            #   다음 시드가 그 덩어리의 «조각»을 작은 컴포넌트로 오인해 얼굴에 구멍을 낸다.
            while stack:
                cx, cy = stack.pop()
                comp.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < min(h, ylimit) and not seen[nx][ny] \
                            and a[nx, ny] > ALPHA_ON:
                        seen[nx][ny] = True
                        stack.append((nx, ny))
            if len(comp) <= SPECK_MAX:
                for cx, cy in comp:
                    px[cx, cy] = (0, 0, 0, 0)
                removed += len(comp)
    return removed


def drop_islands(im: Image.Image, min_size: int = 200):
    """알파>0 연결성으로 작은 섬을 전부 제거한다.

    ★알파 1~18 의 «보이지 않는» 크로마 잔여 1~2 픽셀이 화면 구석에 남으면 getbbox 가
      캔버스 전체를 잡고, 배포 프레이밍(알파 트림 후 visible_box 맞춤)이 통째로 어긋난다.
    """
    w, h = im.size
    a = im.getchannel("A").load()
    px = im.load()
    seen = bytearray(w * h)
    dropped = comps = 0
    for sy in range(h):
        for sx in range(w):
            if seen[sy * w + sx] or a[sx, sy] == 0:
                continue
            stack, comp = [(sx, sy)], []
            seen[sy * w + sx] = 1
            while stack:
                cx, cy = stack.pop()
                comp.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and a[nx, ny]:
                        seen[ny * w + nx] = 1
                        stack.append((nx, ny))
            if len(comp) < min_size:
                comps += 1
                dropped += len(comp)
                for cx, cy in comp:
                    px[cx, cy] = (0, 0, 0, 0)
    return comps, dropped


def despill(im: Image.Image, ylimit: int) -> int:
    """크로마 스필(초록 끼) 억제 — g 가 r·b 보다 튀는 픽셀만 되돌린다."""
    px = im.load()
    w, h = im.size
    fixed = 0
    for y in range(min(h, ylimit)):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a <= ALPHA_ON:
                continue
            if g - max(r, b) > 8:
                ng = max(r, b) + (g - max(r, b)) // 4
                px[x, y] = (r, ng, b, a)
                fixed += 1
    return fixed


def repair(target: Image.Image, s: float, tx: float, ty: float) -> dict:
    w, h = target.size
    a = target.getchannel("A").load()
    px = target.load()
    cleared = 0
    # 자동 구간에 쓸 열별 몸통 상단(기준 좌표계 -> 대상 좌표계로 환산해 스캔)
    scan_from = int(round(s * AUTO_SCAN_FROM + ty))
    cap = s * AUTO_CAP + ty
    auto_x0 = s * AUTO_RIGHT_X + tx
    for x in range(w):
        xr = (x - tx) / s                       # 기준 좌표계 x
        if x >= auto_x0:
            top = None
            for y in range(max(0, scan_from), h):
                if a[x, y] > ALPHA_ON:
                    top = y
                    break
            cut = min(cap, (top - 4) if top is not None else cap)
        else:
            cut = s * interp(CUT, xr) + ty
        cut = int(round(cut))
        if cut <= 0:
            continue
        for r0, r1 in runs(a, x, h):
            if r1 < cut:
                span = range(r0, r1 + 1)
            elif r0 >= cut - RUN_SLACK * s:
                continue
            else:
                span = range(r0, cut)
            for y in span:
                if px[x, y][3]:
                    px[x, y] = (0, 0, 0, 0)
                    cleared += 1
        # ★알파 1~16 의 «희미한» 크로마 잔여도 지운다. 눈에는 안 보이지만
        #   getbbox 는 잡아내므로 남겨두면 프레이밍(알파 트림)이 옛 아티팩트 크기로 잡힌다.
        for y in range(0, min(cut, h)):
            if 0 < px[x, y][3] <= ALPHA_ON:
                px[x, y] = (0, 0, 0, 0)
                cleared += 1
    khaki_before = len(khaki_pixels(target))
    speck = despeck(target, int(round(s * 700 + ty)))
    # ★스필 억제는 «머리 구간»만. 아래로 내리면 초록 저지(옷)를 탈색시킨다
    #   (실측: y 600~683 에서 5846 px 의 (41,59,46)->(41,49,46) 퇴색이 있었다).
    spill = despill(target, int(round(s * 430 + ty)))
    isl = drop_islands(target)
    return {"cleared": cleared, "speck": speck, "despill": spill,
            "islands": isl,
            "khaki_before": khaki_before, "khaki_left": len(khaki_pixels(target))}


def frame_preview(im: Image.Image, cw=128, ch=154) -> Image.Image:
    box = im.getchannel("A").getbbox() or (0, 0, im.width, im.height)
    c = im.crop(box)
    k = min(118 / 128 * cw / c.width, 138 / 154 * ch / c.height)
    w, h = max(1, round(c.width * k)), max(1, round(c.height * k))
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    out.alpha_composite(c.resize((w, h), Image.Resampling.LANCZOS), ((cw - w) // 2, ch - h))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--states", nargs="*", default=list(TARGETS))
    args = ap.parse_args()
    ref = Image.open(REF).convert("RGBA")
    (HERE / "transparent").mkdir(parents=True, exist_ok=True)
    (HERE / "framed").mkdir(parents=True, exist_ok=True)
    for state in args.states:
        src = TARGETS[state]
        im = Image.open(src).convert("RGBA")
        if src == REF:
            err, s, tx, ty = 0.0, 1.0, 0.0, 0.0
        else:
            err, s, tx, ty = fit(ref, im)
        print(f"[{state}] {src.name} fit s={s:.4f} tx={tx:.1f} ty={ty:.1f} err={err:.2f}px")
        tx, ty, left = refine(im, s, tx, ty)
        print(f"[{state}] refined s={s:.4f} tx={tx:.1f} ty={ty:.1f} khaki_predicted={left}")
        stats = repair(im, s, tx, ty)
        print(f"[{state}] {stats}  bbox={im.getchannel('A').getbbox()}")
        out = HERE / "transparent" / f"162_{state}_v1.png"
        im.save(out)
        # ★디스크에서 되읽는다 — 픽셀 직접 수정 후 같은 객체의 getbbox 가 캐시를 물 수 있다.
        reread = Image.open(out).convert("RGBA")
        print(f"[{state}] saved bbox={reread.getchannel('A').getbbox()}")
        frame_preview(reread).save(HERE / "framed" / f"162_{state}_v1.png")


if __name__ == "__main__":
    main()
