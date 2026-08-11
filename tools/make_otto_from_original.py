from PIL import Image, ImageDraw

src='/tmp/otto-skin/current.png'
out='/tmp/otto-skin/otto-original-fishmonger.png'
im=Image.open(src).convert('RGBA'); d=ImageDraw.Draw(im)
navy=(25,49,78,255); navy_hi=(49,82,121,255); navy_sh=(12,25,43,255)
cream=(226,215,177,255); cream_hi=(245,236,202,255); cream_sh=(184,169,135,255)
brown=(91,53,28,255); brown_hi=(139,84,38,255); gold=(226,177,72,255)
fish=(64,171,184,255); fish_hi=(124,220,212,255)

def r(box,c): d.rectangle(box,fill=c)

# Preserve the original face/head and base clothing. Add a bounded outer apron bib.
r((20,36,27,47),navy)
r((20,36,21,47),navy_hi); r((26,36,27,47),navy_sh)
r((22,36,25,37),navy_hi)
# apron neck straps and stitched edge
r((20,36,21,39),navy_hi); r((26,36,27,39),navy_sh)
r((22,46,25,47),navy_sh); r((22,45,25,45),navy_hi)
# readable fish emblem, centered and small
r((22,41,24,43),fish); r((21,42,21,42),fish_hi); r((25,42,26,42),fish_hi)
r((23,40,24,40),fish_hi); r((23,44,23,44),fish_hi)
# leather waist belt and buckle on base torso
r((20,30,27,31),brown); r((20,30,27,30),brown_hi)
r((23,30,24,31),gold)
# pouch on the apron outer layer
r((28,40,31,43),brown); r((28,40,31,40),brown_hi); r((29,41,30,41),gold)
# sleeve cuffs: preserve the original sleeve textures above, add dark cuff bands below
r((44,44,47,47),brown); r((44,44,47,44),brown_hi)
r((36,44,39,47),brown); r((36,44,39,44),brown_hi)

im.save(out)
print(out)
