#!/usr/bin/env python3
"""BetterModel 이 생성한 player_limb 머리를 «둥근 두개골» 로 변환한다.

왜 생성물을 고치나:
  머리 기하는 steve.bbmodel 이 아니라 BetterModel 내부의 바닐라 플레이어 림
  생성기에서 나온다(bbmodel 의 머리 큐브를 둥글게 바꿔도 생성 결과는 바이트
  동일 — dev 에서 실측 확인). 클라이언트가 실제로 읽는 것은 리소스팩에
  벤더링된 이 생성물이므로 여기서 쿼드를 옮기는 것이 유일한 경로다.
  ★그래서 이 스크립트는 «매번 생성물에 다시 적용» 하는 변환기다. 결과를
  사본으로 고정해 두면 BetterModel 갱신을 따라가지 못한다.

변환 규칙 (tint 인덱스를 절대 건드리지 않는다):
  base 머리는 head_0.json 의 384쿼드 통짜 모델이고 쿼드 i 의 색은
  custom_model_data colors[9+i] 다. 즉 쿼드를 «지우거나 순서를 바꾸면»
  전 픽셀 색이 밀린다. 대신 각 쿼드를 자기 법선 방향으로만 이동시킨다:
    면 F, 면내좌표 (a,b) 의 쿼드 → 둥근 형상에서 같은 (F,a,b) 의 표면 평면으로
  같은 면·같은 면내좌표이므로 텍스처 좌표가 보존된다. �록 형상에서는
  (F,a,b) 당 표면이 최대 1개라 1:1 대응이 성립한다.
  둥근 형상에 없는 쿼드는 머리 중심 평면으로 밀어 껍질 안에 숨긴다.

hat(겉레이어)은 픽셀마다 별도 모델(head_1..head_768)이고 floats[i] 로
표시 여부가 결정된다 → 같은 규칙으로 옮기되 평면을 0.5 만큼 바깥으로.
"""
import json, sys, pathlib, collections

# 생성물 실측 좌표계 (아이템 모델 16단위 공간)
B_ORG, B_PX, B_TOP = 4.25, 0.9375, 15.5      # base: x/z 시작, 픽셀크기, 머리 윗면 y
H_ORG, H_PX, H_TOP = 3.75, 1.0625, 16.0      # hat
CENTER = (8.0, 11.75, 8.0)
PLANE_AXIS = {'north':2, 'south':2, 'east':0, 'west':0, 'up':1, 'down':1}
INPLANE   = {'north':(0,1), 'south':(0,1), 'east':(2,1), 'west':(2,1),
             'up':(0,2), 'down':(0,2)}
OUTWARD   = {'north':-1, 'south':+1, 'east':+1, 'west':-1, 'up':+1, 'down':-1}
HAT_SCALE = 8.5 / 7.5        # hat 껍질 = base 껍질을 머리 중심 기준으로 확대한 것

def hat_plane(fname, base_val):
    """★hat 은 «법선방향 +0.5» 가 아니라 «중심 기준 확대» 다.
    정육면체에서는 두 값이 같아서(4.25→3.75, 15.5→16.0) 구별이 안 되지만,
    계단이 생기면 hat 픽셀 격자(중심기준 확대 격자)와 어긋나 틈이 벌어진다.
    실측: 0.5 오프셋으로 하면 정수리 계단에 밝은 실오라기가 새어 나온다."""
    ax = PLANE_AXIS[fname]
    return CENTER[ax] + (base_val - CENTER[ax]) * HAT_SCALE

PROFILES = {
    # rows[j]=Ytop j행의 사방 inset(px), cuts[j]=수직 모서리 컷 세기
    'e5': ([2,1,0,0,0,0,0,0], [3,2,1,0,0,0,0,0]),   # 두개골만 2단
    'e6': ([3,2,1,0,0,0,0,0], [4,3,2,1,0,0,0,0]),   # 두개골 3단(더 둥글게)
    'e8': ([3,2,1,0,0,0,0,0], [4,3,2,1,1,1,1,1]),   # 3단 + 수직모서리도 1px
    'e9': ([3,2,1,0,0,0,0,1], [4,3,2,1,1,1,1,2]),   # 3단 + 턱도 마감
}

def make(name):
    rows, cuts = PROFILES[name]
    def f(X,Y,Z):
        ins, c = rows[Y], cuts[Y]
        if X < ins or X > 7-ins or Z < ins or Z > 7-ins: return False
        u, w = abs(X+0.5-4.0), abs(Z+0.5-4.0)
        return (u+w) <= (3.5-ins)*2 - c + 0.001
    return f

def shape_e5():
    return make('e5')

def surface_planes(fn):
    """면 F, 면내좌표 → 표면 평면의 픽셀 인덱스."""
    occ = {(x,y,z) for x in range(8) for y in range(8) for z in range(8) if fn(x,y,z)}
    out = {}
    for X in range(8):
        for Y in range(8):
            zs = [z for z in range(8) if (X,Y,z) in occ]
            if zs:
                out[('north',X,Y)] = min(zs)
                out[('south',X,Y)] = max(zs)+1
    for Z in range(8):
        for Y in range(8):
            xs = [x for x in range(8) if (x,Y,Z) in occ]
            if xs:
                out[('east',Z,Y)]  = max(xs)+1
                out[('west',Z,Y)]  = min(xs)
    for X in range(8):
        for Z in range(8):
            ys = [y for y in range(8) if (X,y,Z) in occ]
            if ys:
                out[('up',X,Z)]   = min(ys)
                out[('down',X,Z)] = max(ys)+1
    return out, occ

def cell_of(el, org, px, top):
    """생성된 쿼드 → (면, 면내좌표 a, b) + 픽셀 격자 인덱스."""
    (fname,) = el['faces'].keys()
    a, b = el['from'], el['to']
    ix = lambda v: int(round((v - org) / px))
    iy = lambda v: int(round((top - v) / px))
    X, Z, Ytop = ix(a[0]), ix(a[2]), iy(b[1])
    ia, ib = {'north':(X,Ytop),'south':(X,Ytop),'east':(Z,Ytop),
              'west':(Z,Ytop),'up':(X,Z),'down':(X,Z)}[fname]
    return fname, ia, ib

def move_plane(el, fname, plane_val):
    ax = PLANE_AXIS[fname]
    el['from'] = list(el['from']); el['to'] = list(el['to'])
    el['from'][ax] = plane_val; el['to'][ax] = plane_val

def hide(el, fname):
    ax = PLANE_AXIS[fname]
    el['from'] = list(el['from']); el['to'] = list(el['to'])
    el['from'][ax] = CENTER[ax]; el['to'][ax] = CENTER[ax]

def plane_coord(fname, idx, org, px, top, extra=0.0):
    if PLANE_AXIS[fname] == 1:
        return top - idx*px + extra
    return org + idx*px + extra

def transform(root, profile=None, dry=False):
    fn = profile or shape_e5()
    planes, occ = surface_planes(fn)
    root = pathlib.Path(root)
    stats = collections.Counter()

    # ---- base: head_0.json (384쿼드 통짜)
    p0 = root/'models/player_limb/head_0.json'
    d0 = json.loads(p0.read_text())
    assert len(d0['elements']) == 384, '예상과 다른 base 쿼드 수: %d' % len(d0['elements'])
    for el in d0['elements']:
        fname, ia, ib = cell_of(el, B_ORG, B_PX, B_TOP)
        key = (fname, ia, ib)
        if key in planes:
            move_plane(el, fname, plane_coord(fname, planes[key], B_ORG, B_PX, B_TOP))
            stats['base_이동'] += 1
        else:
            hide(el, fname); stats['base_숨김'] += 1
    if not dry: p0.write_text(json.dumps(d0, separators=(',',':')))

    # ---- hat: head_1..head_768 (픽셀당 1모델)
    for i in range(1, 769):
        pi = root/('models/player_limb/head_%d.json' % i)
        if not pi.exists(): continue
        di = json.loads(pi.read_text())
        if len(di['elements']) != 1: continue
        el = di['elements'][0]
        fname, ia, ib = cell_of(el, H_ORG, H_PX, H_TOP)
        key = (fname, ia, ib)
        if key in planes:
            v = hat_plane(fname, plane_coord(fname, planes[key], B_ORG, B_PX, B_TOP))
            move_plane(el, fname, v); stats['hat_이동'] += 1
        else:
            hide(el, fname); stats['hat_숨김'] += 1
        if not dry: pi.write_text(json.dumps(di, separators=(',',':')))
    return stats, len(occ)

if __name__ == '__main__':
    root = sys.argv[1]
    dry = '--dry' in sys.argv
    prof = next((a.split('=')[1] for a in sys.argv if a.startswith('--profile=')), 'e5')
    st, nocc = transform(root, profile=make(prof), dry=dry)
    print('프로필', prof, end=' ')
    print('복셀 %d개' % nocc, dict(st), '(dry)' if dry else '')
