"""전시월드를 위에서 내려다본 컬러 지도 PNG 로 뽑는다(음영 = 높이)."""
import sys, json, numpy as np, amulet, logging
from PIL import Image, ImageDraw
logging.disable(logging.ERROR)

COL = {
 "air":None,"prismarine":(90,150,140),"prismarine_bricks":(99,171,158),"dark_prismarine":(48,88,76),
 "sea_lantern":(230,245,235),"quartz_block":(235,232,226),"quartz_pillar":(235,232,226),
 "stone":(125,125,125),"cobblestone":(122,122,122),"stone_bricks":(122,122,122),"andesite":(136,136,136),
 "sand":(219,207,163),"sandstone":(216,203,155),"gravel":(136,126,124),"dirt":(134,96,67),
 "grass_block":(106,140,68),"planks":(162,130,78),"log":(102,81,50),"leaves":(70,110,50),
 "wool":(200,200,200),"stained_glass":(150,190,220),"glass":(190,215,230),"stained_glass_pane":(150,190,220),
 "water":(60,90,180),"ice":(160,200,230),"snow":(240,240,245),"clay":(160,166,179),
 "obsidian":(20,18,30),"end_stone_bricks":(220,220,160),"purpur_block":(170,126,170),
 "gold_block":(240,200,80),"diamond_block":(110,220,215),"iron_block":(220,220,220),
 "concrete":(120,120,160),"terracotta":(150,92,66),"bricks":(150,97,83),"slab":(140,140,140),
 "stairs":(140,140,140),"wall":(130,130,130),"fence":(150,120,70),"lantern":(240,220,150),
 "glowstone":(250,230,150),"deepslate":(80,80,84),"bedrock":(60,60,60),"magma_block":(140,60,30),
}
def bn(n): return n.split(":")[-1]
def color_for(name):
    b = bn(name)
    if b in COL: return COL[b]
    for k in ("prismarine","quartz","sand","stone","glass","wool","concrete","planks","log","leaves",
              "terracotta","brick","slab","stairs","wall","copper","purpur","coral"):
        if k in b: return COL.get(k, None) or COL.get(k+"_block") or (150,150,150)
    return (168,150,140)

def main(world, out, scale=1):
    lv = amulet.load_level(world); D="minecraft:overworld"; pal=lv.block_palette
    coords=list(lv.all_chunk_coords(D))
    cxs=[c[0] for c in coords]; czs=[c[1] for c in coords]
    x0,x1,z0,z1 = min(cxs)*16, max(cxs)*16+15, min(czs)*16, max(czs)*16+15
    W,L = x1-x0+1, z1-z0+1
    img = np.zeros((L,W,3), np.uint8)
    hmap = np.full((L,W), -999, np.int32)
    palcol = None
    for cx,cz in coords:
        try: ch=lv.get_chunk(cx,cz,D)
        except Exception: continue
        if palcol is None or len(palcol)<len(pal):
            palcol=[color_for(pal[i].namespaced_name) for i in range(len(pal))]
            colarr=np.array([c or (0,0,0) for c in palcol], np.uint8)
            isair=np.array([bn(pal[i].namespaced_name) in ("air","cave_air","void_air") for i in range(len(pal))],bool)
        for cy in sorted(ch.blocks.sub_chunks):
            a=ch.blocks.get_sub_chunk(cy)
            if a.max()>=len(isair): continue
            solid=~isair[a]
            if not solid.any(): continue
            any_=solid.any(axis=1)
            top=15-np.argmax(solid[:, ::-1, :], axis=1)          # (16,16) x,z
            yw=cy*16+top
            xs,zs=np.nonzero(any_)
            gx=cx*16+xs-x0; gz=cz*16+zs-z0
            yy=yw[xs,zs]; idx=a[xs,top[xs,zs],zs]
            better=yy>hmap[gz,gx]
            gx,gz,yy,idx=gx[better],gz[better],yy[better],idx[better]
            hmap[gz,gx]=yy
            img[gz,gx]=colarr[idx]
    lv.close()
    # 높이 음영
    h=hmap.astype(np.float32); mask=hmap>-999
    if mask.any():
        lo,hi=np.percentile(h[mask],[5,95]); hi=max(hi,lo+1)
        sh=np.clip((h-lo)/(hi-lo),0,1)*0.5+0.65
        img=np.clip(img*sh[...,None],0,255).astype(np.uint8)
    im=Image.fromarray(img)
    if scale!=1: im=im.resize((W*scale,L*scale), Image.NEAREST)
    plots=json.load(open("plots.json"))
    d=ImageDraw.Draw(im)
    for p in plots:
        px,pz=(p["x"]-x0)*scale,(p["z"]-z0)*scale
        d.rectangle([px,pz,px+p["w"]*scale,pz+p["l"]*scale], outline=(255,80,80), width=2)
        d.text((px+4,pz+4), p["id"], fill=(255,255,0))
    im.save(out); print("saved", out, im.size)

main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv)>3 else 1)
