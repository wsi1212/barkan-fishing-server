#!/usr/bin/env python3
# CraftEngine/Blockbench 모델 오프라인 미리보기 — element+per-element rot+display.fixed.rotation 적용, 면=텍스처 평균색 painter's.
import json, math, sys
from PIL import Image, ImageDraw

def avg_color(tex, uv):
    w,h=tex.size
    x0=int(min(uv[0],uv[2])/16*w); x1=int(max(uv[0],uv[2])/16*w)
    y0=int(min(uv[1],uv[3])/16*h); y1=int(max(uv[1],uv[3])/16*h)
    x1=max(x1,x0+1); y1=max(y1,y0+1)
    pxs=[p for p in tex.crop((x0,y0,x1,y1)).getdata() if p[3]>10]
    if not pxs: return (150,150,150)
    n=len(pxs); return (sum(p[0] for p in pxs)//n, sum(p[1] for p in pxs)//n, sum(p[2] for p in pxs)//n)
def rot(p,axis,deg,o):
    a=math.radians(deg);c=math.cos(a);s=math.sin(a);x,y,z=p[0]-o[0],p[1]-o[1],p[2]-o[2]
    if axis=="x": y,z=y*c-z*s,y*s+z*c
    elif axis=="y": x,z=x*c+z*s,-x*s+z*c
    elif axis=="z": x,y=x*c-y*s,x*s+y*c
    return [x+o[0],y+o[1],z+o[2]]
def corners(f,t):
    return [(f[0],f[1],f[2]),(t[0],f[1],f[2]),(t[0],t[1],f[2]),(f[0],t[1],f[2]),
            (f[0],f[1],t[2]),(t[0],f[1],t[2]),(t[0],t[1],t[2]),(f[0],t[1],t[2])]
FACE_IDX={"down":[0,1,5,4],"up":[3,2,6,7],"north":[1,0,3,2],"south":[4,5,6,7],"west":[0,4,7,3],"east":[5,1,2,6]}
def viewrot(p,ry,rx):
    a=math.radians(ry);c,s=math.cos(a),math.sin(a);x,y,z=p;x,z=x*c+z*s,-x*s+z*c
    a=math.radians(rx);c,s=math.cos(a),math.sin(a);y,z=y*c-z*s,y*s+z*c
    return (x,y,z)
def render(model_path,tex_path,out_path,ry,rx,size=560):
    dd=json.load(open(model_path)); tex=Image.open(tex_path).convert("RGBA")
    drot=dd.get("display",{}).get("fixed",{}).get("rotation",[0,0,0])
    faces=[]
    for e in dd["elements"]:
        cs=corners(e["from"],e["to"])
        if e.get("rotation"):
            r=e["rotation"]; cs=[rot(c,r["axis"],r["angle"],r["origin"]) for c in cs]
        cs=[rot(rot(rot(c,"x",drot[0],[8,8,8]),"y",drot[1],[8,8,8]),"z",drot[2],[8,8,8]) for c in cs]
        for fn,idx in FACE_IDX.items():
            fc=e["faces"].get(fn)
            if not fc: continue
            vs=[viewrot(cs[i],ry,rx) for i in idx]
            faces.append((sum(v[2] for v in vs)/4, vs, avg_color(tex,fc.get("uv",[0,0,16,16]))))
    faces.sort(key=lambda x:-x[0])
    pts=[v for _,vs,_ in faces for v in vs]; xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    mnx,mxx,mny,mxy=min(xs),max(xs),min(ys),max(ys)
    sc=size*0.82/max(mxx-mnx,mxy-mny,1); ox=size/2-(mnx+mxx)/2*sc; oy=size/2+(mny+mxy)/2*sc
    img=Image.new("RGBA",(size,size),(244,246,248,255)); dr=ImageDraw.Draw(img)
    for _,vs,col in faces:
        dr.polygon([(p[0]*sc+ox,-p[1]*sc+oy) for p in vs], fill=col, outline=(50,50,50,140))
    img.save(out_path); print("saved",out_path)
if __name__=="__main__":
    mp,tp,ob=sys.argv[1],sys.argv[2],sys.argv[3]
    render(mp,tp,ob+"_34.png",30,14); render(mp,tp,ob+"_side.png",90,0)
