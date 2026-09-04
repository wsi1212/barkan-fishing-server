"""소스 월드를 위에서 내려다본 지도 + 128블록 좌표격자. 가짜 바닷물은 투명 처리."""
import sys, re, numpy as np, amulet, logging
from PIL import Image, ImageDraw
from render_map import color_for, bn
logging.disable(logging.ERROR)
FAKE = re.compile(r'(stained_glass|wool|concrete)\[color="(blue|cyan|light_blue)"\]')
HIDE = re.compile(r'^(air|cave_air|void_air|water|flowing_water)$')

def main(world, out, x0,z0,x1,z1, ytop=320):
    lv=amulet.load_level(world); D="minecraft:overworld"; pal=lv.block_palette
    W,L=x1-x0+1, z1-z0+1
    img=np.zeros((L,W,3),np.uint8); hmap=np.full((L,W),-999,np.int32)
    isair=colarr=None
    for cx in range(x0//16,x1//16+1):
        for cz in range(z0//16,z1//16+1):
            try: ch=lv.get_chunk(cx,cz,D)
            except Exception: continue
            if isair is None or len(isair)<len(pal):
                names=[pal[i].full_blockstate for i in range(len(pal))]
                isair=np.array([bool(HIDE.match(bn(n.split('[')[0]))) or bool(FAKE.search(n)) for n in names],bool)
                colarr=np.array([color_for(n.split('[')[0]) or (0,0,0) for n in names],np.uint8)
            for cy in sorted(ch.blocks.sub_chunks):
                if cy*16>ytop: continue
                a=ch.blocks.get_sub_chunk(cy)
                if a.max()>=len(isair): continue
                solid=~isair[a]
                if not solid.any(): continue
                any_=solid.any(axis=1); top=15-np.argmax(solid[:,::-1,:],axis=1)
                xs,zs=np.nonzero(any_)
                gx=cx*16+xs-x0; gz=cz*16+zs-z0
                keep=(gx>=0)&(gx<W)&(gz>=0)&(gz<L)
                xs,zs,gx,gz=xs[keep],zs[keep],gx[keep],gz[keep]
                yy=(cy*16+top)[xs,zs]; idx=a[xs,top[xs,zs],zs]
                b=yy>hmap[gz,gx]
                hmap[gz,gx[0:0]] if False else None
                gx,gz,yy,idx=gx[b],gz[b],yy[b],idx[b]
                hmap[gz,gx]=yy; img[gz,gx]=colarr[idx]
    lv.close()
    h=hmap.astype(np.float32); m=hmap>-999
    if m.any():
        lo,hi=np.percentile(h[m],[5,95]); hi=max(hi,lo+1)
        sh=np.clip((h-lo)/(hi-lo),0,1)*0.55+0.6
        img=np.clip(img*sh[...,None],0,255).astype(np.uint8)
    im=Image.fromarray(img); d=ImageDraw.Draw(im)
    for gx in range(0,W,128):
        d.line([(gx,0),(gx,L)],fill=(255,60,60),width=1); d.text((gx+2,2),str(x0+gx),fill=(255,255,0))
    for gz in range(0,L,128):
        d.line([(0,gz),(W,gz)],fill=(255,60,60),width=1); d.text((2,gz+2),str(z0+gz),fill=(255,255,0))
    im.save(out); print("saved",out,im.size)
a=sys.argv
main(a[1],a[2],int(a[3]),int(a[4]),int(a[5]),int(a[6]))
