#!/usr/bin/env python3
"""껍질에 구멍이 있는지 검출한다 — base 레이어만 불투명 단색으로 렌더하고,
실루엣 «안쪽» 의 배경 픽셀을 센다(테두리에서 flood fill 해서 바깥을 지운 뒤 남은 것).
45° 패싯은 축 하나 회전으로만 만들 수 있어 위쪽 모서리에서 삼각 구멍이 나기 쉽다."""
import sys, json, pathlib, io, base64
sys.path.insert(0, str(pathlib.Path.home()/'.claude/skills/npc-model-forge/scripts'))
import render_bbmodel as R
import round_limb_head as RL
from PIL import Image
from collections import deque

def base_model(work):
    d = json.loads((pathlib.Path(work)/'models/player_limb/head_0.json').read_text())
    els = []
    for e in d['elements']:
        (f,) = e['faces'].keys()
        ax = RL.PLANE_AXIS[f]
        if e['from'][ax] == RL.CENTER[ax] and e['to'][ax] == RL.CENTER[ax]:
            continue                                   # 숨긴 쿼드
        el = {'from': e['from'], 'to': e['to'], 'origin': [0,0,0],
              'faces': {f: {'uv': [0,0,1,1], 'texture': 0}}, 'type': 'cube',
              'uuid': 'e%d' % len(els)}
        r = e.get('rotation')
        if r:
            v = [0.0,0.0,0.0]; v[{'x':0,'y':1,'z':2}[r['axis']]] = r['angle']
            el['rotation'] = v; el['origin'] = r['origin']
        els.append(el)
    im = Image.new('RGBA', (2,2), (255,80,80,255))
    buf = io.BytesIO(); im.save(buf, 'PNG')
    return {'resolution': {'width':1,'height':1},
            'textures':[{'source':'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()}],
            'elements': els, 'groups': [], 'outliner': [e['uuid'] for e in els]}

def holes(im):
    W,H = im.size; px = im.load()
    solid = lambda x,y: px[x,y][3] >= 8
    seen = [[False]*W for _ in range(H)]
    q = deque()
    for x in range(W):
        for y in (0, H-1):
            if not solid(x,y) and not seen[y][x]: seen[y][x]=True; q.append((x,y))
    for y in range(H):
        for x in (0, W-1):
            if not solid(x,y) and not seen[y][x]: seen[y][x]=True; q.append((x,y))
    while q:
        x,y = q.popleft()
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx,ny = x+dx, y+dy
            if 0<=nx<W and 0<=ny<H and not seen[ny][nx] and not solid(nx,ny):
                seen[ny][nx]=True; q.append((nx,ny))
    return sum(1 for y in range(H) for x in range(W) if not solid(x,y) and not seen[y][x])

def main():
    for arg in sys.argv[1:]:
        lab, pk = arg.split('=',1)
        base = base_model(pk); tot=0; worst=(0,None); n=0
        # ★피치를 안 보면 위쪽 모서리 삼각구멍을 놓친다 — 그룹 회전으로 기울인다
        for pitch in (-60, -30, 0, 30, 60):
            m = dict(base)
            g = {'name':'p','uuid':'PITCH','origin':[8,11.75,8],
                 'rotation':[pitch,0,0],'children':[e['uuid'] for e in base['elements']]}
            m['groups'] = [g]; m['outliner'] = [{'uuid':'PITCH','children':g['children']}]
            for yaw in range(0, 360, 15):
                im = R.render(m, yaw, 30)
                if im is None: continue
                h = holes(im); tot += h; n += 1
                if h > worst[0]: worst = (h, (pitch, yaw))
        print('%-16s %d방향 구멍픽셀 합계 %5d   최악(pitch,yaw)=%s (%d)'
              % (lab, n, tot, worst[1], worst[0]))
main()
