#!/usr/bin/env python3
"""후보 형태 × 스킨 × (확대/게임크기) 비교 시트."""
import sys, pathlib, json, io, base64
sys.path.insert(0, str(pathlib.Path.home()/'.claude/skills/npc-model-forge/scripts'))
import render_bbmodel as R
from PIL import Image, ImageDraw

def head_only(path, skin):
    m=json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
    gid=next(g['uuid'] for g in m['groups'] if g.get('name')=='h_ph_head')
    def find(ns):
        for n in ns:
            if isinstance(n,dict):
                if n.get('uuid')==gid: return n
                r=find(n.get('children',[]))
                if r: return r
    kids=[c for c in find(m['outliner'])['children'] if isinstance(c,str)]
    els=[e for e in m['elements'] if e['uuid'] in set(kids)]
    buf=io.BytesIO(); Image.open(skin).convert('RGBA').save(buf,'PNG')
    return {'resolution':{'width':64,'height':64},
            'textures':[{'source':'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()}],
            'elements':els,'groups':[],'outliner':kids}

def main():
    dst=sys.argv[1]; skins=sys.argv[2].split(','); srcs=sys.argv[3:]
    COLS=[]
    for sk in skins:
        nm=pathlib.Path(sk).stem
        COLS += [(nm+' 정면',sk,180,22),(nm+' 3/4',sk,215,22),(nm+' 게임크기',sk,215,7)]
    grid=[]
    for s in srcs:
        row=[]
        for _,sk,yaw,sc in COLS:
            im=R.render(head_only(s,sk),yaw,sc)
            if sc<10: im=im.resize((im.width*3,im.height*3),Image.NEAREST)
            row.append(im)
        grid.append((pathlib.Path(s).stem.replace('h_',''),row))
    Wc=max(i.width for _,r in grid for i in r); Hc=max(i.height for _,r in grid for i in r)
    lab,top=72,18
    out=Image.new('RGBA',(lab+len(COLS)*(Wc+10)+10, top+len(grid)*(Hc+12)+8),(28,28,34,255))
    d=ImageDraw.Draw(out)
    for j,(t,_,_,_) in enumerate(COLS): d.text((lab+j*(Wc+10)+2,4),t,fill=(185,185,195))
    for i,(nm,row) in enumerate(grid):
        y=top+i*(Hc+12)
        d.text((5,y+Hc//2),nm,fill=(240,225,140))
        for j,im in enumerate(row):
            out.paste(im,(lab+j*(Wc+10)+(Wc-im.width)//2, y+(Hc-im.height)),im)
    out.save(dst); print(dst,out.size)
main()
