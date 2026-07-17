#!/usr/bin/env python3
"""Textured offline renderer — samples the model's real UVs per texel, applies
Minecraft's per-face light factors (up 1.0 / N-S 0.8 / E-W 0.6 / down 0.5).
Close enough to the in-game look to self-judge texture quality without a relog.

Usage: python render_textured.py <model.json> <texture.png> <out.png> [yaw] [pitch]
Default view: 3/4 (yaw 30, pitch 20).

★카메라 규약(2026-07-18 고정): pitch = 카메라 고도각(도), **양수 = 지평선 위에서 내려다봄(조감)**.
  과거엔 양수가 벌레시점이라 아이콘 31종이 전부 밑면부터 보이는 사고가 남 — 수식을 만지면
  assert_camera_convention()(빨강 윗면/파랑 밑면 판자 셀프테스트)이 빌드에서 즉시 잡는다.
render()는 가시면 픽셀 통계 {"up","down","side"}를 반환 — 최종 이미지에서 실제로 보이는
면의 비율이므로 "밑면이 지배하는 아이콘"을 호출자가 정량 감사할 수 있다.
auto_camera(elements) = 형태(납작/기본/길쭉 + 상부질량) → (yaw, pitch) 자동 판정.
"""
import json, math, sys
from PIL import Image, ImageDraw

FACE_LIGHT = {"up": 1.0, "down": 0.5, "north": 0.8, "south": 0.8, "west": 0.6, "east": 0.6}
CORNERS = lambda f, t: [(f[0],f[1],f[2]),(t[0],f[1],f[2]),(t[0],t[1],f[2]),(f[0],t[1],f[2]),
                        (f[0],f[1],t[2]),(t[0],f[1],t[2]),(t[0],t[1],t[2]),(f[0],t[1],t[2])]
FACE_IDX = {"down":[0,1,5,4],"up":[7,6,2,3],"north":[2,3,0,1],"south":[7,4,5,6],"west":[3,7,4,0],"east":[6,2,1,5]}

def viewrot(p, yaw, pitch):
    a=math.radians(yaw); c,s=math.cos(a),math.sin(a); x,y,z=p; x,z=x*c+z*s,-x*s+z*c
    a=math.radians(-pitch); c,s=math.cos(a),math.sin(a); y,z=y*c-z*s,y*s+z*c   # 부호 반전: pitch 양수=조감
    return (x,y,z)

def lerp2(a,b,c,dd,fu,fv):
    top=[a[i]+(b[i]-a[i])*fu for i in range(3)]; bot=[dd[i]+(c[i]-dd[i])*fu for i in range(3)]
    return [top[i]+(bot[i]-top[i])*fv for i in range(3)]

def rot_pt(p, axis, ang, org):
    a=math.radians(ang); c,s=math.cos(a),math.sin(a)
    x,y,z=p[0]-org[0],p[1]-org[1],p[2]-org[2]
    if axis=="x": y,z=y*c-z*s,y*s+z*c
    elif axis=="y": x,z=x*c+z*s,-x*s+z*c
    else: x,y=x*c-y*s,x*s+y*c
    return (x+org[0],y+org[1],z+org[2])

def render(model_path, tex_path, out, yaw=30, pitch=20, size=640):
    m=json.load(open(model_path)); tex=Image.open(tex_path).convert("RGBA")
    W,H=tex.size; sx,sy=W/16.0,H/16.0
    quads=[]
    for e in m["elements"]:
        cs=CORNERS(e["from"],e["to"])
        if e.get("rotation"):
            r=e["rotation"]; cs=[rot_pt(c,r["axis"],r["angle"],r["origin"]) for c in cs]
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
                    quads.append((depth,[viewrot(p,yaw,pitch) for p in q],col,
                                  fn if fn in ("up","down") else "side"))
    quads.sort(key=lambda q:-q[0])
    pts=[v for _,vs,_,_ in quads for v in vs]; xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    mnx,mxx,mny,mxy=min(xs),max(xs),min(ys),max(ys)
    sc=size*0.85/max(mxx-mnx,mxy-mny,1); ox=size/2-(mnx+mxx)/2*sc; oy=size/2+(mny+mxy)/2*sc
    img=Image.new("RGBA",(size,size),(0,0,0,0)); dr=ImageDraw.Draw(img)
    IDCOL={"up":(255,0,0),"down":(0,0,255),"side":(0,255,0)}
    idimg=Image.new("RGB",(size,size),(0,0,0)); idr=ImageDraw.Draw(idimg)   # 가시면 ID 패스(같은 페인터 순서)
    for _,vs,col,fc in quads:
        poly=[(p[0]*sc+ox,-p[1]*sc+oy) for p in vs]
        dr.polygon(poly,fill=col); idr.polygon(poly,fill=IDCOL[fc])
    img.save(out); print("rendered",out)
    stats={"up":0,"down":0,"side":0}
    ap,ip=img.load(),idimg.load()
    for yy in range(size):
        for xx in range(size):
            if ap[xx,yy][3]>0:
                r,g,b=ip[xx,yy]
                stats["up" if r else ("down" if b else "side")]+=1
    return stats

def auto_camera(elements):
    """형태 → 아이콘 카메라 (yaw, pitch, 판정라벨) 자동 결정. 근거:
    바닐라 GUI 3/4뷰 = display rotation [30,225,0] → 기본 고도 30°(플레이어가 아는 표준 앵글).
    · 납작(h < 0.45×발자국): 위 패턴이 정체성(이끼·반쯤 묻힌 트러플) → 55°
    · 길쭉(h > 1.7×발자국): 옆 실루엣이 정체성(줄기 꽃·스파이어) → 22° (급하면 키가 뭉개짐)
    · 상부질량(면적가중 무게중심 상위 60%+: 갓·꽃머리)은 +8° 더 내려다봐 윗면을 보여줌, 하부질량은 −5°
    yaw 35 = 45° 꼭짓점 대칭을 피한 프론트 바이어스(유기물용 하우스 스타일). 예외는 manifest icon_pitch/icon_yaw."""
    pts=[]; wsum=0.0; wy=0.0
    for e in elements:
        f,t=e["from"],e["to"]; cs=CORNERS(f,t)
        if e.get("rotation"):
            r=e["rotation"]; cs=[rot_pt(c,r["axis"],r["angle"],r["origin"]) for c in cs]
        pts+=cs
        w,h,d=abs(t[0]-f[0]),abs(t[1]-f[1]),abs(t[2]-f[2])
        area=2*(w*d+w*h+d*h) or 0.001
        wsum+=area; wy+=area*(sum(c[1] for c in cs)/8)
    ys=[p[1] for p in pts]; h=max(ys)-min(ys)
    fp=max(max(p[0] for p in pts)-min(p[0] for p in pts),
           max(p[2] for p in pts)-min(p[2] for p in pts)) or 0.001
    slender=h/fp
    if slender<0.45: base,klass=55,"납작"
    elif slender>1.7: base,klass=22,"길쭉"
    else: base,klass=30,"기본"
    topmass=((wy/wsum)-min(ys))/h if h>0.001 else 0.5
    if topmass>0.60: base+=8
    elif topmass<0.38: base-=5
    return 35, max(18,min(58,base)), f"{klass}·상부질량{topmass:.2f}"

def assert_camera_convention():
    """pitch 부호 회귀 방지 셀프테스트 — 윗면=빨강/밑면=파랑 판자를 pitch=+30으로 렌더해
    빨강이 압도해야 통과(양수=조감). 2026-07-18 벌레시점 아이콘 사고의 재발 방지 안전망."""
    import tempfile, os
    with tempfile.TemporaryDirectory() as td:
        tex=Image.new("RGBA",(16,16))
        for y in range(16):
            for x in range(16):
                tex.putpixel((x,y),(255,0,0,255) if x<8 else (0,0,255,255))
        tp=os.path.join(td,"t.png"); tex.save(tp)
        mdl={"elements":[{"from":[0,7,0],"to":[16,9,16],"faces":{
            "up":{"uv":[0,0,8,16]},"down":{"uv":[8,0,16,16]},
            "north":{"uv":[0,0,1,16]},"south":{"uv":[0,0,1,16]},
            "west":{"uv":[0,0,1,16]},"east":{"uv":[0,0,1,16]}}}]}
        mp=os.path.join(td,"m.json"); json.dump(mdl,open(mp,"w"))
        op=os.path.join(td,"o.png"); st=render(mp,tp,op,yaw=35,pitch=30,size=96)
        if st["up"] < st["down"]*3:
            raise SystemExit(f"✗ 카메라 규약 위반: pitch=+30에서 윗면 {st['up']}px < 밑면 {st['down']}px×3 "
                             "— pitch 양수=조감이어야 함 (render_textured.viewrot 확인)")

if __name__=="__main__":
    a=sys.argv; render(a[1],a[2],a[3],float(a[4]) if len(a)>4 else 30,float(a[5]) if len(a)>5 else 20)
