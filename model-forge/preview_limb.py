#!/usr/bin/env python3
"""변환된 player_limb 머리를 «클라이언트가 보게 될 그대로» 렌더한다.

base 쿼드 i 의 색은 colors[9+i] = 그 쿼드가 원래 있던 위치의 스킨 픽셀이고,
hat 픽셀은 스킨 알파가 0 이면 아예 안 그려진다(range_dispatch fallback=empty).
그래서 «원본 팩에서 얻은 (면,면내좌표) → 스킨 UV» 를 색으로 쓰고,
기하는 변환된 팩에서 읽으면 실제 화면과 같아진다.
"""
import json, sys, pathlib, io, base64
sys.path.insert(0, str(pathlib.Path.home()/'.claude/skills/npc-model-forge/scripts'))
import render_bbmodel as R
from PIL import Image, ImageDraw
import round_limb_head as RL

def skin_uv(fname, ia, ib, hat):
    o = 32 if hat else 0
    X = Z = Ytop = None
    if fname in ('north','south'): X, Ytop = ia, ib
    elif fname in ('east','west'): Z, Ytop = ia, ib
    else: X, Z = ia, ib
    if fname=='north': return [15-X+o, 8+Ytop, 16-X+o, 9+Ytop]
    if fname=='south': return [24+X+o, 8+Ytop, 25+X+o, 9+Ytop]
    if fname=='east':  return [7-Z+o,  8+Ytop, 8-Z+o,  9+Ytop]
    if fname=='west':  return [16+Z+o, 8+Ytop, 17+Z+o, 9+Ytop]
    if fname=='up':    return [16-X+o, 8-Z, 15-X+o, 7-Z]
    return [24-X+o, Z, 23-X+o, Z+1]

def mk(new, uv, uid):
    """MC 아이템모델 요소 → 렌더러가 먹는 bbmodel 요소.
    ★MC 는 rotation 을 {angle,axis,origin} 으로 쓰고 렌더러는 [rx,ry,rz]+origin 을
      쓴다. 변환을 빼먹으면 45° 패싯이 축정렬로 그려져 «멀쩡해 보이는» 오진이 난다."""
    (fname,) = new['faces'].keys() if 'faces' in new else (None,)
    e = {'from':new['from'],'to':new['to'],'faces':{uv[1]:{'uv':uv[0],'texture':0}},
         'type':'cube','uuid':uid,'origin':[0,0,0]}
    r = new.get('rotation')
    if r:
        v = [0.0,0.0,0.0]; v[{'x':0,'y':1,'z':2}[r['axis']]] = r['angle']
        e['rotation'] = v; e['origin'] = r['origin']
    return e

def build(pristine, worked, skin_png):
    pris, work = pathlib.Path(pristine), pathlib.Path(worked)
    sk = Image.open(skin_png).convert('RGBA'); spx = sk.load()
    els = []
    # base
    p_old = json.loads((pris/'models/player_limb/head_0.json').read_text())['elements']
    p_new = json.loads((work/'models/player_limb/head_0.json').read_text())['elements']
    for old, new in zip(p_old, p_new):
        fname, ia, ib = RL.cell_of(old, RL.B_ORG, RL.B_PX, RL.B_TOP)
        uv = (skin_uv(fname, ia, ib, False), list(new['faces'].keys())[0])
        if new['from'][RL.PLANE_AXIS[fname]] == RL.CENTER[RL.PLANE_AXIS[fname]]:
            continue                                    # 숨긴 쿼드
        els.append(mk(new, uv, 'b%d'%len(els)))
    # hat — 스킨 알파가 있는 픽셀만 (짝수/홀수 중 하나만 쓰면 중복 없음)
    for i in range(1, 769, 2):
        fo = pris/('models/player_limb/head_%d.json'%i)
        fn_ = work/('models/player_limb/head_%d.json'%i)
        if not fo.exists(): continue
        old = json.loads(fo.read_text())['elements'][0]
        new = json.loads(fn_.read_text())['elements'][0]
        fname, ia, ib = RL.cell_of(old, RL.H_ORG, RL.H_PX, RL.H_TOP)
        uv = (skin_uv(fname, ia, ib, True), list(new['faces'].keys())[0])
        if spx[int(uv[0][0]), int(uv[0][1])][3] < 8: continue  # 투명 → 안 그려짐
        if new['from'][RL.PLANE_AXIS[fname]] == RL.CENTER[RL.PLANE_AXIS[fname]]:
            continue
        els.append(mk(new, uv, 'h%d'%i))
    buf=io.BytesIO(); sk.save(buf,'PNG')
    return {'resolution':{'width':64,'height':64},
            'textures':[{'source':'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()}],
            'elements':els,'groups':[],'outliner':[e['uuid'] for e in els]}

def main():
    pris, dst = sys.argv[1], sys.argv[2]
    pairs = [a.split('=', 1) for a in sys.argv[3:]]     # 라벨=팩경로
    skins = ['../skin-forge/out/tf_frieda.png','../skin-forge/out/ci_captain.png',
             '../skin-forge/out/archivist.png']
    VIEWS=[('정면',180,22),('3/4',215,22),('게임크기',215,7)]
    rows=[]
    for lab, pk in pairs:
        row=[]
        for sp in skins:
            m = build(pris, pk, sp)
            for _,yaw,sc in VIEWS:
                im = R.render(m, yaw, sc)
                if sc<10: im=im.resize((im.width*3,im.height*3),Image.NEAREST)
                row.append(im)
        rows.append((lab,row))
    Wc=max(i.width for _,r in rows for i in r); Hc=max(i.height for _,r in rows for i in r)
    LB,TP=76,18
    n=len(rows[0][1])
    out=Image.new('RGBA',(LB+n*(Wc+10)+10, TP+len(rows)*(Hc+12)+8),(28,28,34,255))
    d=ImageDraw.Draw(out)
    for j in range(n):
        sk=pathlib.Path(skins[j//len(VIEWS)]).stem; v=VIEWS[j%len(VIEWS)][0]
        d.text((LB+j*(Wc+10)+2,4), sk[:9]+' '+v, fill=(185,185,195))
    for i,(lab,row) in enumerate(rows):
        y=TP+i*(Hc+12); d.text((4,y+Hc//2),lab,fill=(240,225,140))
        for j,im in enumerate(row):
            out.paste(im,(LB+j*(Wc+10)+(Wc-im.width)//2, y+(Hc-im.height)),im)
    out.save(dst); print(dst,out.size)
main()
