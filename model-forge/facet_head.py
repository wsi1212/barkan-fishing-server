#!/usr/bin/env python3
"""머리를 «45° 패싯» 으로 깎는다 — 서드파티 모델(demon_knight/blue_wizard)이 쓰는 기법.

왜 계단이 아니라 패싯인가:
  로컬 서드파티 휴머노이드 모델을 해부하니 머리가 큐브 46~85개로 되어 있고
  ±22.5/±45° 회전 큐브로 «경사면» 을 만든다(demon_knight: 앞면 판 + rot[0,±45,0]
  측면 패싯). 축정렬 계단으로 깎으면 둥근 게 아니라 톱니로 보인다.

가능한 이유:
  BetterModel 이 만든 쿼드는 전부 1×1 `normal_pixel` + tintindex 단색이다.
  즉 쿼드의 UV 방향·미러링이 무의미하므로, 어떤 쿼드를 어느 위치·어느 방향에
  놓아도 «그 tintindex 의 스킨 픽셀 색» 이 그대로 칠해진다. MC 아이템 모델은
  축 하나당 ±22.5/±45 회전을 허용하므로 수직 모서리 45° 패싯이 만들어진다.

배치(수직 모서리 4개를 45° 패싯으로):
  앞/뒤면은 X 1..6 만 남기고, 각 면의 끝칼럼(X0·X7)과 측면의 끝칼럼(Z0·Z7)을
  모서리 패싯 위에 반씩 올린다 — 해제 64칸 = 패싯 64칸으로 정확히 맞는다.
"""
import math, json, pathlib, collections
import round_limb_head as RL

PXB, ORGB, TOPB = RL.B_PX, RL.B_ORG, RL.B_TOP
C = RL.CENTER
S = RL.HAT_SCALE
HALF = math.sqrt(2) / 2.0          # 패싯 반폭 (px)

def mx(X): return ORGB + X * PXB
def my(Y): return TOPB - Y * PXB
def mz(Z): return ORGB + Z * PXB

def flat(face, plane_idx, a, b):
    """축정렬 평면 쿼드. a,b = 면내 격자좌표."""
    if face in ('north', 'south'):
        X, Y = a, b
        return dict(frm=[mx(X), my(Y+1), mz(plane_idx)],
                    to =[mx(X+1), my(Y), mz(plane_idx)], face=face, rot=None)
    if face in ('east', 'west'):
        Z, Y = a, b
        return dict(frm=[mx(plane_idx), my(Y+1), mz(Z)],
                    to =[mx(plane_idx), my(Y), mz(Z+1)], face=face, rot=None)
    X, Z = a, b
    return dict(frm=[mx(X), my(plane_idx), mz(Z)],
                to =[mx(X+1), my(plane_idx), mz(Z+1)], face=face, rot=None)

def facet(sx, sz, row, slot):
    """모서리 (sx,sz) 의 row 행 패싯. slot='face'(앞/뒤면쪽) 또는 'side'(측면쪽)."""
    cx = 7.5 if sx > 0 else 0.5
    cz = 0.5 if sz < 0 else 7.5
    # +local x 가 측면쪽을 향하는 부호 = sx (유도 후 미리보기로 검증)
    lo, hi = (0.0, HALF) if sx > 0 else (-HALF, 0.0)
    if slot == 'face':
        lo, hi = (-HALF, 0.0) if sx > 0 else (0.0, HALF)
    face = 'north' if sz < 0 else 'south'
    ang = (-45 if sz < 0 else 45) * (1 if sx > 0 else -1)
    return dict(frm=[mx(cx+lo), my(row+1), mz(cz)],
                to =[mx(cx+hi), my(row),   mz(cz)],
                face=face,
                rot=dict(angle=ang, axis='y', origin=[mx(cx), my(row)-PXB/2, mz(cz)]))

def crown_facet(edge, i, slot):
    """정수리 4개 «변» 패싯. edge in front/back/right/left, i = 변 방향 격자좌표.
    slot='side'(측면쪽) / 'top'(정수리쪽). 축 하나 회전으로 만들 수 있는 경사면."""
    if edge in ('front', 'back'):
        cz = 0.5 if edge == 'front' else 7.5
        cy = 0.5
        face = 'north' if edge == 'front' else 'south'
        ang  = 45 if edge == 'front' else -45
        lo, hi = (0.0, HALF) if slot == 'top' else (-HALF, 0.0)
        if edge == 'back': lo, hi = (-hi, -lo)
        return dict(frm=[mx(i),   my(cy-lo), mz(cz)],
                    to =[mx(i+1), my(cy-hi), mz(cz)], face=face,
                    rot=dict(angle=ang, axis='x',
                             origin=[mx(i+0.5), my(cy), mz(cz)]))
    cx = 7.5 if edge == 'right' else 0.5
    cy = 0.5
    face = 'east' if edge == 'right' else 'west'
    ang  = 45 if edge == 'right' else -45
    lo, hi = (0.0, HALF) if slot == 'top' else (-HALF, 0.0)
    if edge == 'left': lo, hi = (-hi, -lo)
    return dict(frm=[mx(cx), my(cy-lo), mz(i)],
                to =[mx(cx), my(cy-hi), mz(i+1)], face=face,
                rot=dict(angle=ang, axis='z',
                         origin=[mx(cx), my(cy), mz(i+0.5)]))

def build_assign(crown=True):
    """(면, 면내a, 면내b) → 목표 기하. 없으면 숨김."""
    A = {}
    KEEP = range(1, 7)                     # 평면으로 남기는 면내 6칸
    R0 = 1 if crown else 0                 # crown 이면 0행은 정수리 패싯이 쓴다
    for r in range(R0, 8):
        for X in KEEP: A[('north', X, r)] = flat('north', 0, X, r)
        for X in KEEP: A[('south', X, r)] = flat('south', 8, X, r)
        for Z in KEEP: A[('east',  Z, r)] = flat('east',  8, Z, r)
        for Z in KEEP: A[('west',  Z, r)] = flat('west',  0, Z, r)
        # 모서리 패싯 — 앞/뒤면 끝칼럼 + 측면 끝칼럼을 반씩
        A[('north', 7, r)] = facet(+1, -1, r, 'face')
        A[('east',  0, r)] = facet(+1, -1, r, 'side')
        A[('north', 0, r)] = facet(-1, -1, r, 'face')
        A[('west',  0, r)] = facet(-1, -1, r, 'side')
        A[('south', 7, r)] = facet(+1, +1, r, 'face')
        A[('east',  7, r)] = facet(+1, +1, r, 'side')
        A[('south', 0, r)] = facet(-1, +1, r, 'face')
        A[('west',  7, r)] = facet(-1, +1, r, 'side')
    if crown:
        # 정수리 4개 변 = 45° 패싯. 측면 0행 + up 테두리 직선부를 반씩 올린다
        for i in KEEP:
            A[('north', i, 0)] = crown_facet('front', i, 'side')
            A[('up',    i, 0)] = crown_facet('front', i, 'top')
            A[('south', i, 0)] = crown_facet('back',  i, 'side')
            A[('up',    i, 7)] = crown_facet('back',  i, 'top')
            A[('east',  i, 0)] = crown_facet('right', i, 'side')
            A[('up',    7, i)] = crown_facet('right', i, 'top')
            A[('west',  i, 0)] = crown_facet('left',  i, 'side')
            A[('up',    0, i)] = crown_facet('left',  i, 'top')
        # 위쪽 4모서리: 축 하나 회전으로 삼각 패싯을 못 만든다 →
        # 수직 패싯을 0행까지 올려 «작은 귀» 로 막는다(구멍 방지, 검출기로 확인)
        A[('north', 7, 0)] = facet(+1, -1, 0, 'face')
        A[('east',  0, 0)] = facet(+1, -1, 0, 'side')
        A[('north', 0, 0)] = facet(-1, -1, 0, 'face')
        A[('west',  0, 0)] = facet(-1, -1, 0, 'side')
        A[('south', 7, 0)] = facet(+1, +1, 0, 'face')
        A[('east',  7, 0)] = facet(+1, +1, 0, 'side')
        A[('south', 0, 0)] = facet(-1, +1, 0, 'face')
        A[('west',  7, 0)] = facet(-1, +1, 0, 'side')
    # ★모서리 칸도 정수리/바닥을 덮어야 한다. 패싯이 그 칸을 «대각선» 으로 자르므로
    #   칸을 통째로 빼면 안쪽 삼각형이 뚫린다(구멍검출기: 피치 -60 에서 4176픽셀 누출).
    #   칸 전체를 평면으로 덮으면 바깥 삼각형이 패싯 밖으로 살짝 나오지만
    #   정수리라 눈높이에서 안 보이고, 코플래너 겹침(z-fighting)이 없다.
    for X in range(8):
        for Z in range(8):
            if ('up', X, Z) not in A:
                A[('up', X, Z)] = flat('up', 0, X, Z)
            if not (2 <= Z <= 5):                      # 가슴이 가리는 칸은 생략
                A[('down', X, Z)] = flat('down', 8, X, Z)
    return A

def scale_geom(g):
    """hat 껍질 = base 목표 기하를 머리 중심 기준 확대."""
    f = lambda p: [C[i] + (p[i]-C[i])*S for i in range(3)]
    out = dict(frm=f(g['frm']), to=f(g['to']), face=g['face'], rot=None)
    if g['rot']:
        out['rot'] = dict(angle=g['rot']['angle'], axis=g['rot']['axis'],
                          origin=f(g['rot']['origin']))
    return out

def put(el, g):
    el['from'] = [round(v, 5) for v in g['frm']]
    el['to']   = [round(v, 5) for v in g['to']]
    (old,) = el['faces'].keys()
    if old != g['face']:
        el['faces'] = {g['face']: el['faces'][old]}
    if g['rot']:
        el['rotation'] = {'angle': g['rot']['angle'], 'axis': g['rot']['axis'],
                          'origin': [round(v, 5) for v in g['rot']['origin']]}
    else:
        el.pop('rotation', None)

def hide(el):
    (f,) = el['faces'].keys()
    ax = RL.PLANE_AXIS[f]
    el['from'] = list(el['from']); el['to'] = list(el['to'])
    el['from'][ax] = C[ax]; el['to'][ax] = C[ax]
    el.pop('rotation', None)

def transform(root, crown=True):
    A = build_assign(crown)
    root = pathlib.Path(root); st = collections.Counter()
    p0 = root/'models/player_limb/head_0.json'
    d0 = json.loads(p0.read_text())
    for el in d0['elements']:
        key = RL.cell_of(el, RL.B_ORG, RL.B_PX, RL.B_TOP)
        if key in A: put(el, A[key]); st['base_배치'] += 1
        else:        hide(el);        st['base_숨김'] += 1
    p0.write_text(json.dumps(d0, separators=(',', ':')))
    for i in range(1, 769):
        pi = root/('models/player_limb/head_%d.json' % i)
        if not pi.exists(): continue
        di = json.loads(pi.read_text()); el = di['elements'][0]
        key = RL.cell_of(el, RL.H_ORG, RL.H_PX, RL.H_TOP)
        if key in A: put(el, scale_geom(A[key])); st['hat_배치'] += 1
        else:        hide(el);                    st['hat_숨김'] += 1
        pi.write_text(json.dumps(di, separators=(',', ':')))
    return st

if __name__ == '__main__':
    import sys
    print(dict(transform(sys.argv[1], crown='--no-crown' not in sys.argv)))
