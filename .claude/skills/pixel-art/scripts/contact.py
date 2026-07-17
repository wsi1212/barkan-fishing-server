import sys,os,math
from PIL import Image,ImageDraw
paths=sys.argv[1:-1]; out=sys.argv[-1]; scale=10; pad=12; cols=4
tiles=[]
for p in paths:
  if os.path.isfile(p):
    im=Image.open(p).convert("RGBA")
    if max(im.size)<=32:                      # 픽셀 스프라이트 -> nearest 확대
        im=im.resize((im.width*scale,im.height*scale),Image.NEAREST)
    else:                                     # 렌더/레퍼런스 같은 큰 이미지 -> 축소해서 타일로
        im.thumbnail((320,320),Image.LANCZOS)
    tiles.append((os.path.basename(p)[:16],im))
if not tiles: print("NO TILES"); sys.exit()
tw=max(t[1].width for t in tiles); th=max(t[1].height for t in tiles); rows=math.ceil(len(tiles)/cols)
sheet=Image.new("RGBA",(cols*(tw+pad)+pad,rows*(th+pad+18)+pad),(235,235,235,255)); dr=ImageDraw.Draw(sheet)
for i,(n,im) in enumerate(tiles):
  r,c=divmod(i,cols); x=pad+c*(tw+pad); y=pad+r*(th+pad+18); sheet.paste(im,(x,y),im); dr.text((x,y+th+4),n,fill=(0,0,0,255))
sheet.save(out); print("sheet",out,sheet.size,len(tiles),"tiles")
