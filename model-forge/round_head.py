#!/usr/bin/env python3
"""steve.bbmodel 의 머리를 복셀 기반 둥근 형태로 다시 만든다.

왜 복셀인가:
  BetterModel 은 bbmodel 큐브의 각 면을 픽셀 1개당 쿼드 1개로 펼친다
  (assets/bettermodel/models/player_limb/head_0.json = 6면×64px = 384쿼드).
  그래서 큐브를 여러 개로 쪼개면 안 보이는 내부 면까지 쿼드가 된다.
  대신 "표면 픽셀만" 두께 0 판으로 내보내면 원하는 어떤 형태든 만들면서
  쿼드 수는 노출 면적과 정확히 같아진다. 현재 384에는 목에 가려 안 보이는
  바닥면 64개가 들어 있으므로, 둥글게 깎으면서도 총량은 줄어든다.

좌표 규약 (파일 실측으로 검산됨):
  머리 base 큐브 = from[-3.75,22.5,-3.75] to[3.75,30,3.75]  → 8px, 1px=0.9375
  X: 0..8 (+x 방향)   Ytop: 0..8 (위에서 아래로)   Z: 0..8 (+z=뒤통수)
  면별 UV (base, hat 은 u+32) — 6면 모두 원본 파일과 일치 확인:
    north [16-xb, 8+ya, 16-xa, 8+yb]     south [24+xa, 8+ya, 24+xb, 8+yb]
    east  [8-zb, 8+ya, 8-za, 8+yb]       west  [16+za, 8+ya, 16+zb, 8+yb]
    up    [16-xa, 8-za, 16-xb, 8-zb]     down  [24-xa, za, 24-xb, zb]
"""
import json, sys, copy, uuid, pathlib

PX = 0.9375                      # 1 스킨픽셀의 모델 단위
ORIGIN = [-3.75, 22.5, -3.75]    # 머리 base 큐브의 from
CENTER = [0.0, 26.25, 0.0]       # 머리 중심
HAT_SCALE = 8.46875 / 7.5        # 원본 hat(inset+inflate0.5)의 실제 크기 비

def mx(X): return ORIGIN[0] + X * PX
def my(Ytop): return 30.0 - Ytop * PX
def mz(Z): return ORIGIN[2] + Z * PX

# ---------------------------------------------------------------- 형태 정의
def shape_full(X, Y, Z):
    return True

def make_shape(rows, cut):
    """rows[j] = Ytop j행의 사방 inset(px).
    cut = 수직 모서리 컷 세기. 스칼라 또는 행별 리스트.
    ★행별로 주는 이유: 모서리 컷은 «앞면 끝칼럼(뺨)»과 «측면 앞칼럼(머리카락)»을
      1px씩 교대로 노출시켜 줄무늬가 된다(실측). 정수리 쪽은 위·측면이 모두
      머리카락이라 안전하지만 얼굴 높이에서는 눈에 띈다 → 위는 강하게, 아래는 약하게."""
    def f(X, Y, Z):
        ins = rows[Y]
        c = cut[Y] if isinstance(cut, (list, tuple)) else cut
        if X < ins or X > 7 - ins or Z < ins or Z > 7 - ins:
            return False
        u, w = abs(X + 0.5 - 4.0), abs(Z + 0.5 - 4.0)
        lim = (3.5 - ins) * 2 - c + 0.001
        return (u + w) <= lim
    return f

# 프로필들 (Ytop 0=정수리 … 7=턱)
# rows[j] = Ytop j행의 사방 inset(px), cut = 수직 모서리 컷 세기
PROFILES = {
    'orig':    shape_full,
    'r1':      make_shape([2,1,0,0,0,0,0,0], 1.0),   # 관 2단 + 모서리 균일 1
    # 정수리는 강하게, 얼굴 높이로 내려오며 약해지는 테이퍼 (줄무늬 회피)
    'e1':      make_shape([2,1,0,0,0,0,0,0], [3,2.5,2,1.5,1,1,1,1]),
    'e2':      make_shape([2,1,0,0,0,0,0,0], [3,2,1,1,1,1,1,1]),
    'e3':      make_shape([3,2,1,0,0,0,0,0], [3,3,2.5,2,1.5,1,1,1]),
    'e4':      make_shape([2,1,0,0,0,0,0,0], [2,1.5,1,1,0,0,0,0]),
    # 얼굴 높이(Ytop3~)는 원본 그대로 두고 두개골만 둥글린다 — 줄무늬 원천 차단
    'e5':      make_shape([2,1,0,0,0,0,0,0], [3,2,1,0,0,0,0,0]),
    'e6':      make_shape([3,2,1,0,0,0,0,0], [4,3,2,1,0,0,0,0]),
    'e7':      make_shape([2,1,1,0,0,0,0,0], [3,2,1,0,0,0,0,0]),
}

# ---------------------------------------------------------------- 표면 추출
DIRS = [('north',(0,0,-1)), ('south',(0,0,1)), ('east',(1,0,0)),
        ('west',(-1,0,0)),  ('up',(0,-1,0)),   ('down',(0,1,0))]
# 주의: Ytop 은 아래로 증가하므로 up = Ytop-1 방향

def surface(fn, drop_bottom=True):
    occ = {(x,y,z) for x in range(8) for y in range(8) for z in range(8) if fn(x,y,z)}
    faces = {name: [] for name,_ in DIRS}
    for (x,y,z) in occ:
        for name,(dx,dy,dz) in DIRS:
            n = (x+dx, y+dy, z+dz)
            if n in occ:
                continue
            if name == 'down' and drop_bottom and y == 7 and 2 <= z <= 5:
                continue          # 가슴 큐브(z -1.875..1.875 = Z2..6)가 실제로 가리는 구간만 버린다
                                  # ★전부 버리면 아래에서 껍데기 내부가 뚫려 보인다(실측)
            faces[name].append((x,y,z))
    return occ, faces

def merge_rects(cells, name):
    """같은 평면의 노출 픽셀들을 최대 직사각형으로 합친다(탐욕)."""
    # 평면 상수축과 2D 축을 고른다
    if name in ('north','south'):   const, a, b = 2, 0, 1     # z 고정, (X,Ytop)
    elif name in ('east','west'):   const, a, b = 0, 2, 1     # x 고정, (Z,Ytop)
    else:                           const, a, b = 1, 0, 2     # y 고정, (X,Z)
    planes = {}
    for c in cells:
        planes.setdefault(c[const], set()).add((c[a], c[b]))
    out = []
    for k, pts in planes.items():
        pts = set(pts)
        while pts:
            u0, v0 = min(pts)
            w = 1
            while (u0+w, v0) in pts: w += 1
            h = 1
            while all((u0+i, v0+h) in pts for i in range(w)): h += 1
            for i in range(w):
                for j in range(h):
                    pts.discard((u0+i, v0+j))
            out.append((k, u0, v0, w, h))
    return out

# ---------------------------------------------------------------- UV
def uv_for(name, xa, xb, ya, yb, za, zb, hat):
    o = 32 if hat else 0
    if name == 'north': u = [16-xb+o, 8+ya, 16-xa+o, 8+yb]
    elif name == 'south': u = [24+xa+o, 8+ya, 24+xb+o, 8+yb]
    elif name == 'east':  u = [8-zb+o, 8+ya, 8-za+o, 8+yb]
    elif name == 'west':  u = [16+za+o, 8+ya, 16+zb+o, 8+yb]
    elif name == 'up':    u = [16-xa+o, 8-za, 16-xb+o, 8-zb]
    else:                 u = [24-xa+o, za, 24-xb+o, zb]
    return [float(v) for v in u]

def plate(name, rect, hat):
    """평면 사각형 → 두께 0 큐브 1개 (면 1개만)."""
    k, u0, v0, w, h = rect
    if name in ('north','south'):
        xa, xb = u0, u0+w; ya, yb = v0, v0+h
        za = zb = k + (0 if name=='north' else 1)
    elif name in ('east','west'):
        za, zb = u0, u0+w; ya, yb = v0, v0+h
        xa = xb = k + (0 if name=='west' else 1)
    else:
        xa, xb = u0, u0+w; za, zb = v0, v0+h
        ya = yb = k + (0 if name=='up' else 1)
    frm = [mx(xa), my(yb), mz(za)]
    to  = [mx(xb), my(ya), mz(zb)]
    if hat:
        frm = [CENTER[i] + (frm[i]-CENTER[i])*HAT_SCALE for i in range(3)]
        to  = [CENTER[i] + (to[i] -CENTER[i])*HAT_SCALE for i in range(3)]
    return {
        # ★이름은 원본과 똑같이 'skin'/'hat' — BetterModel 이 겉레이어를 이름으로
        #   가려낼 가능성이 있어 신호를 그대로 유지한다(dev 실측으로 확인)
        'name': 'hat' if hat else 'skin',
        'box_uv': False, 'render_order': 'default', 'locked': False,
        'allow_mirror_modeling': True,
        'from': [round(v,5) for v in frm], 'to': [round(v,5) for v in to],
        'autouv': 0, 'color': 4, 'origin': [0, 22.5, -1.875],
        'faces': {name: {'uv': uv_for(name, xa, xb, ya, yb, za, zb, hat), 'texture': 0}},
        'type': 'cube', 'uuid': str(uuid.uuid4()),
        **({'uv_offset': [32, 0]} if hat else {}),
    }

def build_head(fn, drop_bottom=True):
    occ, faces = surface(fn, drop_bottom)
    els, npx = [], 0
    for name, _ in DIRS:
        if not faces[name]: continue
        for r in merge_rects(faces[name], name):
            npx += r[3]*r[4]
            els.append(plate(name, r, False))
            els.append(plate(name, r, True))
    return els, npx, len(occ)

# ---------------------------------------------------------------- 적용
def rewrite(src, dst, prof, drop_bottom=True):
    m = json.loads(pathlib.Path(src).read_text(encoding='utf-8'))
    fn = PROFILES[prof]
    old = [e for e in m['elements']
           if e.get('from') == [-3.75,22.5,-3.75]
           or (e.get('inflate') == 0.5 and abs(e['from'][1]-22.51563) < 0.01)]
    assert len(old) == 2, '머리 큐브 2개를 못 찾았다: %d' % len(old)
    old_ids = {e['uuid'] for e in old}
    new, npx, nocc = build_head(fn, drop_bottom)
    m['elements'] = [e for e in m['elements'] if e['uuid'] not in old_ids] + new
    # outliner: h_ph_head 노드의 자식 교체
    gid = next(g['uuid'] for g in m['groups'] if g.get('name') == 'h_ph_head')
    def fix(nodes):
        for n in nodes:
            if isinstance(n, dict):
                if n.get('uuid') == gid:
                    n['children'] = [c for c in n.get('children',[])
                                     if not (isinstance(c,str) and c in old_ids)] \
                                    + [e['uuid'] for e in new]
                else:
                    fix(n.get('children', []))
    fix(m['outliner'])
    pathlib.Path(dst).write_text(json.dumps(m, ensure_ascii=False), encoding='utf-8')
    return npx, nocc, len(new)

if __name__ == '__main__':
    src, dst, prof = sys.argv[1], sys.argv[2], sys.argv[3]
    db = '--keep-bottom' not in sys.argv
    npx, nocc, nel = rewrite(src, dst, prof, db)
    print('%-12s 노출픽셀 %4d (한쪽) → 쿼드 %4d  판 %3d개  복셀 %3d'
          % (prof, npx, npx*2, nel, nocc))
