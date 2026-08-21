#!/usr/bin/env python3
"""머리 변형들을 같은 스킨으로 나란히 렌더해 컨택트시트를 만든다."""
import json, sys, io, base64, uuid, pathlib
sys.path.insert(0, str(pathlib.Path.home()/'.claude/skills/npc-model-forge/scripts'))
import render_bbmodel as R
from PIL import Image, ImageDraw

def head_only(path, skin_png, pitch=0.0):
    m = json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
    gid = next(g['uuid'] for g in m['groups'] if g.get('name')=='h_ph_head')
    def find(nodes):
        for n in nodes:
            if isinstance(n, dict):
                if n.get('uuid')==gid: return n
                r=find(n.get('children',[]))
                if r: return r
        return None
    node = find(m['outliner'])
    kids = [c for c in node['children'] if isinstance(c,str)]
    els = [e for e in m['elements'] if e['uuid'] in set(kids)]
    buf = io.BytesIO(); Image.open(skin_png).convert('RGBA').save(buf, 'PNG')
    b64 = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
    g = {'name':'pitch','uuid':str(uuid.uuid4()),'origin':[0,26.25,0],
         'rotation':[pitch,0,0],'children':kids}
    return {'resolution':{'width':64,'height':64},
            'textures':[{'source':b64}],
            'elements':els,
            'groups':[g],
            'outliner':[{'uuid':g['uuid'],'children':kids}]}

def main():
    skin = sys.argv[1]; dst = sys.argv[2]; srcs = sys.argv[3:]
    YAWS = [('정면',180,0),('3/4',215,0),('측면',270,0),('위에서 3/4',215,26),('아래에서',215,-34)]
    scale = 26
    rows=[]
    for s in srcs:
        name = pathlib.Path(s).stem.replace('steve_','')
        cells=[]
        for lab,yaw,pit in YAWS:
            mm = head_only(s, skin, pit)
            im = R.render(mm, yaw, scale)
            cells.append((lab, im))
        rows.append((name, cells))
    Wc = max(im.width for _,cs in rows for _,im in cs)
    Hc = max(im.height for _,cs in rows for _,im in cs)
    lab_w, top = 118, 20
    W = lab_w + len(YAWS)*(Wc+12) + 12
    H = top + len(rows)*(Hc+14) + 8
    out = Image.new('RGBA',(W,H),(30,30,36,255))
    d = ImageDraw.Draw(out)
    for j,(lab,_,_) in enumerate(YAWS):
        d.text((lab_w + j*(Wc+12) + 4, 5), lab, fill=(190,190,200))
    for i,(name,cs) in enumerate(rows):
        y = top + i*(Hc+14)
        d.text((6, y + Hc//2), name, fill=(235,225,150))
        for j,(_,im) in enumerate(cs):
            out.paste(im, (lab_w + j*(Wc+12) + (Wc-im.width)//2, y + (Hc-im.height)), im)
    out.save(dst); print(dst, out.size)

main()
