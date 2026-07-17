#!/usr/bin/env python3
"""Textured offline renderer — samples the model's real UVs per texel, applies
Minecraft's per-face light factors (up 1.0 / N-S 0.8 / E-W 0.6 / down 0.5).
Close enough to the in-game look to self-judge texture quality without a relog.

Usage: python render_textured.py <model.json> <texture.png> <out.png> [yaw] [pitch]
Default view: 3/4 (yaw 30, pitch 20).
"""
import json, math, sys
from PIL import Image, ImageDraw

FACE_LIGHT = {"up": 1.0, "down": 0.5, "north": 0.8, "south": 0.8, "west": 0.6, "east": 0.6}
CORNERS = lambda f, t: [(f[0],f[1],f[2]),(t[0],f[1],f[2]),(t[0],t[1],f[2]),(f[0],t[1],f[2]),
                        (f[0],f[1],t[2]),(t[0],f[1],t[2]),(t[0],t[1],t[2]),(f[0],t[1],t[2])]
FACE_IDX = {"down":[0,1,5,4],"up":[7,6,2,3],"north":[2,3,0,1],"south":[7,4,5,6],"west":[3,7,4,0],"east":[6,2,1,5]}

def viewrot(p, yaw, pitch):
    a=math.radians(yaw); c,s=math.cos(a),math.sin(a); x,y,z=p; x,z=x*c+z*s,-x*s+z*c
    a=math.radians(pitch); c,s=math.cos(a),math.sin(a); y,z=y*c-z*s,y*s+z*c
    return (x,y,z)

def lerp2(a,b,c,dd,fu,fv):
    top=[a[i]+(b[i]-a[i])*fu for i in range(3)]; bot=[dd[i]+(c[i]-dd[i])*fu for i in range(3)]
    return [top[i]+(bot[i]-top[i])*fv for i in range(3)]

def render(model_path, tex_path, out, yaw=30, pitch=20, size=640):
    m=json.load(open(model_path)); tex=Image.open(tex_path).convert("RGBA")
    W,H=tex.size; sx,sy=W/16.0,H/16.0
    quads=[]
    for e in m["elements"]:
        cs=CORNERS(e["from"],e["to"])
        for fn,fc in e.get("faces",{}).items():
            idx=FACE_IDX[fn]; poly=[cs[i] for i in idx]
            u0,v0,u1,v1=fc.get("uv",[0,0,16,16])
            pu0,pv0,pu1,pv1=int(round(u0*sx)),int(round(v0*sy)),int(round(u1*sx)),int(round(v1*sy))
            tw,th=max(1,abs(pu1-pu0)),max(1,abs(pv1-pv0))
            lt=FACE_LIGHT[fn]
            vp=[viewrot(p,yaw,pitch) for p in poly]
            depth=sum(p[2] for p in vp)/4
            for ty in range(th):
                for tx in range(tw):
                    su=pu0+tx if pu1>pu0 else pu0-tx-1
                    sv=pv0+ty if pv1>pv0 else pv0-ty-1
                    px=tex.getpixel((min(W-1,max(0,su)),min(H-1,max(0,sv))))
                    if px[3]<8: continue
                    col=(int(px[0]*lt),int(px[1]*lt),int(px[2]*lt),255)
                    q=[lerp2(poly[0],poly[1],poly[2],poly[3],fu,fv) for fu,fv in
                       ((tx/tw,ty/th),((tx+1)/tw,ty/th),((tx+1)/tw,(ty+1)/th),(tx/tw,(ty+1)/th))]
                    quads.append((depth,[viewrot(p,yaw,pitch) for p in q],col))
    quads.sort(key=lambda q:-q[0])
    pts=[v for _,vs,_ in quads for v in vs]; xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    mnx,mxx,mny,mxy=min(xs),max(xs),min(ys),max(ys)
    sc=size*0.85/max(mxx-mnx,mxy-mny,1); ox=size/2-(mnx+mxx)/2*sc; oy=size/2+(mny+mxy)/2*sc
    img=Image.new("RGBA",(size,size),(0,0,0,0)); dr=ImageDraw.Draw(img)
    for _,vs,col in quads:
        dr.polygon([(p[0]*sc+ox,-p[1]*sc+oy) for p in vs],fill=col)
    img.save(out); print("rendered",out)

if __name__=="__main__":
    a=sys.argv; render(a[1],a[2],a[3],float(a[4]) if len(a)>4 else 30,float(a[5]) if len(a)>5 else 20)
