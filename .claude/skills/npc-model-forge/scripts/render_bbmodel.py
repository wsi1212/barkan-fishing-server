#!/usr/bin/env python3
"""`.bbmodel`을 오프라인에서 4면 렌더한다 — 텍스처 입힌 소프트웨어 래스터라이저.

왜 필요한가
  렌더를 안 보고 픽셀을 밀면 반드시 틀린다. 이번 세션에서만 스킨 작업이 4번 틀렸고
  (female_face 얼굴 파괴 · 앞머리 3회 · 세로주름=줄무늬 바지), 매번 <b>합성 렌더를
  눈으로 본 순간</b> 잡혔다. 3D 모델은 축이 하나 더 늘어나므로 더 위험하다.
  `render_skin.py`가 스킨 작업에서 했던 역할을 여기서 한다.

구현
  · 정사영(orthographic) + Z버퍼. 원근을 넣지 않는 이유는 <b>구조 검증용</b>이기 때문 —
    비율·정렬·겹침을 재려면 원근이 오히려 방해다(render_skin.py와 같은 사상).
  · 본 계층(groups.origin/rotation)과 요소 회전(element.origin/rotation)을 모두 적용한다.
    ★45° 판으로 모서리를 깎는 게 이 도메인의 1순위 기법이라(reference-study.md 2장),
    회전을 제대로 안 그리면 볼 이유가 없다.
  · 음영은 <b>변환 후 실제 법선</b>으로 계산한다. 면 이름(north/up…)으로 하면 회전된
    큐브가 전부 틀리게 칠해진다 — 바로 그 회전이 핵심인데.

사용
  render_bbmodel.py <model.bbmodel> <out.png> [--scale N] [--views front,left,back,right]
                    [--grid] [--wire]
"""
import base64
import io
import json
import math
import os
import sys

from PIL import Image

# ── 박스 6면 → 꼭짓점 4개 (바닐라 모델 규약: 바깥에서 봤을 때 uv 좌상→우상→우하→좌하) ──
def face_quad(a, b, name):
    x0, y0, z0 = a
    x1, y1, z1 = b
    return {
        'north': [(x1, y1, z0), (x0, y1, z0), (x0, y0, z0), (x1, y0, z0)],
        'south': [(x0, y1, z1), (x1, y1, z1), (x1, y0, z1), (x0, y0, z1)],
        'east':  [(x1, y1, z1), (x1, y1, z0), (x1, y0, z0), (x1, y0, z1)],
        'west':  [(x0, y1, z0), (x0, y1, z1), (x0, y0, z1), (x0, y0, z0)],
        'up':    [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
        'down':  [(x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0)],
    }[name]


def rot_mat(deg):
    """[rx,ry,rz]도 → 3x3. XYZ 순서(블록벤치 표기와 일치)."""
    rx, ry, rz = (math.radians(v) for v in deg)
    cx, sx, cy, sy, cz, sz = (math.cos(rx), math.sin(rx), math.cos(ry),
                              math.sin(ry), math.cos(rz), math.sin(rz))
    return (
        (cy * cz, -cy * sz, sy),
        (sx * sy * cz + cx * sz, -sx * sy * sz + cx * cz, -sx * cy),
        (-cx * sy * cz + sx * sz, cx * sy * sz + sx * cz, cx * cy),
    )


def mv(m, p):
    return (m[0][0] * p[0] + m[0][1] * p[1] + m[0][2] * p[2],
            m[1][0] * p[0] + m[1][1] * p[1] + m[1][2] * p[2],
            m[2][0] * p[0] + m[2][1] * p[1] + m[2][2] * p[2])


def apply_stack(p, stack):
    """(origin, rotmat) 스택을 안쪽→바깥쪽 순서로 적용."""
    for origin, m in stack:
        q = (p[0] - origin[0], p[1] - origin[1], p[2] - origin[2])
        q = mv(m, q)
        p = (q[0] + origin[0], q[1] + origin[1], q[2] + origin[2])
    return p


def load_textures(model):
    out = []
    for t in model.get('textures', []):
        src = t.get('source') or ''
        im = None
        if src.startswith('data:image'):
            try:
                im = Image.open(io.BytesIO(base64.b64decode(src.split(',', 1)[1]))).convert('RGBA')
            except Exception:
                im = None
        out.append(im)
    return out


def collect(model):
    """outliner를 걸어 (element, 변환스택)을 모은다. groups에 이름·피벗이 들어 있다."""
    gmeta = {g['uuid']: g for g in model.get('groups', [])}
    emap = {e['uuid']: e for e in model.get('elements', []) if e.get('type', 'cube') == 'cube'}
    out = []

    def walk(nodes, stack):
        for n in nodes:
            if isinstance(n, str):
                if n in emap:
                    out.append((emap[n], list(stack)))
                continue
            g = gmeta.get(n.get('uuid'), {})
            org = g.get('origin') or [0, 0, 0]
            rot = g.get('rotation') or [0, 0, 0]
            s = list(stack)
            if any(abs(v) > 1e-6 for v in rot):
                s.append((org, rot_mat(rot)))
            walk(n.get('children', []), s)

    walk(model.get('outliner', []), [])
    return out


def build_tris(model, view_deg):
    """모든 면을 (삼각형2개 + uv + 법선) 리스트로."""
    texes = load_textures(model)
    res = model.get('resolution', {'width': 16, 'height': 16})
    rw, rh = res.get('width', 16), res.get('height', 16)
    vm = rot_mat([0, view_deg, 0])
    tris = []
    for el, stack in collect(model):
        a, b = el['from'], el['to']
        eorg = el.get('origin') or [0, 0, 0]
        erot = el.get('rotation') or [0, 0, 0]
        estack = list(stack)
        if isinstance(erot, list) and any(abs(v) > 1e-6 for v in erot):
            estack = [(eorg, rot_mat(erot))] + estack
        infl = float(el.get('inflate', 0) or 0)
        if infl:
            a = [a[i] - infl for i in range(3)]
            b = [b[i] + infl for i in range(3)]
        for fname, f in (el.get('faces') or {}).items():
            if fname not in ('north', 'south', 'east', 'west', 'up', 'down'):
                continue
            uv = f.get('uv')
            ti = f.get('texture')
            if uv is None or ti is None or ti >= len(texes) or texes[ti] is None:
                continue
            tex = texes[ti]
            u1, v1, u2, v2 = uv
            sx, sy = tex.width / rw, tex.height / rh
            uvs = [(u1 * sx, v1 * sy), (u2 * sx, v1 * sy), (u2 * sx, v2 * sy), (u1 * sx, v2 * sy)]
            pts = [mv(vm, apply_stack(p, estack)) for p in face_quad(a, b, fname)]
            # 법선은 변환 <b>후</b> 좌표로 구한다 — 회전된 큐브를 면 이름으로 칠하면 다 틀린다
            e1 = [pts[1][i] - pts[0][i] for i in range(3)]
            e2 = [pts[2][i] - pts[0][i] for i in range(3)]
            nx = e1[1] * e2[2] - e1[2] * e2[1]
            ny = e1[2] * e2[0] - e1[0] * e2[2]
            nz = e1[0] * e2[1] - e1[1] * e2[0]
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            nrm = (nx / ln, ny / ln, nz / ln)
            tris.append((pts, uvs, tex, nrm))
    return tris


LIGHT = (-0.35, 0.72, -0.60)     # 좌상전방 광원 (render_skin.py의 면별 밝기와 같은 느낌)


def shade(nrm):
    d = sum(nrm[i] * LIGHT[i] for i in range(3))
    return max(0.52, min(1.12, 0.80 + 0.34 * d))


def render(model, view_deg, scale, pad=8):
    tris = build_tris(model, view_deg)
    if not tris:
        return None
    xs = [p[0] for t in tris for p in t[0]]
    ys = [p[1] for t in tris for p in t[0]]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    W = max(1, int((maxx - minx) * scale) + pad * 2)
    H = max(1, int((maxy - miny) * scale) + pad * 2)
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    px = img.load()
    zbuf = [[-1e9] * W for _ in range(H)]

    def to_screen(p):
        return ((p[0] - minx) * scale + pad, (maxy - p[1]) * scale + pad, p[2])

    for pts, uvs, tex, nrm in tris:
        sp = [to_screen(p) for p in pts]
        k = shade(nrm)
        tw, th = tex.width, tex.height
        tpx = tex.load()
        for i0, i1, i2 in ((0, 1, 2), (0, 2, 3)):
            (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = sp[i0], sp[i1], sp[i2]
            (a0, b0), (a1, b1), (a2, b2) = uvs[i0], uvs[i1], uvs[i2]
            den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(den) < 1e-9:
                continue
            xlo, xhi = int(min(x0, x1, x2)), int(max(x0, x1, x2)) + 1
            ylo, yhi = int(min(y0, y1, y2)), int(max(y0, y1, y2)) + 1
            for y in range(max(0, ylo), min(H, yhi)):
                for x in range(max(0, xlo), min(W, xhi)):
                    cx, cy = x + 0.5, y + 0.5
                    w0 = ((y1 - y2) * (cx - x2) + (x2 - x1) * (cy - y2)) / den
                    w1 = ((y2 - y0) * (cx - x2) + (x0 - x2) * (cy - y2)) / den
                    w2 = 1.0 - w0 - w1
                    if w0 < -1e-4 or w1 < -1e-4 or w2 < -1e-4:
                        continue
                    z = w0 * z0 + w1 * z1 + w2 * z2
                    if z <= zbuf[y][x]:
                        continue
                    u = w0 * a0 + w1 * a1 + w2 * a2
                    v = w0 * b0 + w1 * b1 + w2 * b2
                    tu = min(tw - 1, max(0, int(u)))
                    tv = min(th - 1, max(0, int(v)))
                    c = tpx[tu, tv]
                    if c[3] < 8:
                        continue           # 투명 픽셀은 Z도 안 쓴다(뒤가 비쳐야 한다)
                    zbuf[y][x] = z
                    px[x, y] = (min(255, int(c[0] * k)), min(255, int(c[1] * k)),
                                min(255, int(c[2] * k)), 255)
    return img


# ★카메라는 +Z에 있고 -Z를 본다. 플레이어 얼굴은 north(-Z)면에 있으므로 front=180이다.
#   (0으로 두면 얼굴이 back 패널에 나온다 — 첫 렌더에서 실측으로 확인)
#   -Z를 보는 캐릭터 기준 오른손은 +X쪽 → right=270.
VIEWS = {'front': 180, 'right': 270, 'back': 0, 'left': 90}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = {a.split('=')[0]: (a.split('=')[1] if '=' in a else True)
            for a in sys.argv[1:] if a.startswith('--')}
    if len(args) < 2:
        print(__doc__)
        return 1
    src, dst = args[0], args[1]
    scale = float(opts.get('--scale', 10))
    views = str(opts.get('--views', 'front,right,back,left')).split(',')
    model = json.load(open(src, encoding='utf-8'))
    panels = []
    for v in views:
        im = render(model, VIEWS.get(v, 0), scale)
        if im:
            panels.append((v, im))
    if not panels:
        print('렌더할 면이 없다 — 텍스처가 없거나 uv가 비었을 수 있다')
        return 1
    gap, top = 10, 16
    Wp = max(i.width for _, i in panels)
    Hp = max(i.height for _, i in panels)
    out = Image.new('RGBA', (len(panels) * (Wp + gap) + gap, Hp + top + gap), (32, 32, 38, 255))
    from PIL import ImageDraw
    d = ImageDraw.Draw(out)
    for i, (name, im) in enumerate(panels):
        x = gap + i * (Wp + gap)
        out.paste(im, (x + (Wp - im.width) // 2, top + (Hp - im.height)), im)
        d.text((x + 2, 3), name, fill=(200, 200, 208))
    out.save(dst)
    print('%s  (%dx%d, 면 %d)' % (dst, out.width, out.height, len(panels)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
