from PIL import Image, ImageDraw

W = 64
im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
d = ImageDraw.Draw(im)

def px(x, y, c): d.point((x, y), fill=c)
def box(x, y, w, h, c): d.rectangle((x, y, x+w-1, y+h-1), fill=c)
def row(x, y, values):
    for i, c in enumerate(values): px(x+i, y, c)

# Deliberately restrained, high-contrast palette: rugged guildmaster, not a recolor of another NPC.
skin0=(176,104,62,255); skin1=(205,132,78,255); skin2=(231,163,96,255); skin3=(120,64,43,255)
hair0=(43,29,26,255); hair1=(68,40,30,255); hair2=(93,53,35,255)
navy0=(18,35,50,255); navy1=(24,52,71,255); navy2=(38,77,94,255); navy3=(59,105,115,255)
leather0=(54,32,23,255); leather1=(91,52,28,255); leather2=(133,76,34,255); metal=(170,139,76,255)
cream0=(185,166,128,255); cream1=(219,199,157,255); cream2=(238,219,173,255)
eye=(224,232,218,255); iris=(38,105,121,255); ink=(24,23,22,255)
fish0=(34,128,145,255); fish1=(70,177,181,255); fish2=(117,207,196,255)
boot0=(34,27,25,255); boot1=(71,43,29,255); boot2=(108,63,34,255)

# Head base: small 2x2 eyes, one-pixel nose bridge, compact mouth and stubble.
box(8,8,8,8,skin1); box(0,8,8,8,skin0); box(16,8,8,8,skin1); box(24,8,8,8,skin0)
box(8,0,8,8,hair1); box(16,0,8,8,hair0)
box(8,8,8,2,hair0); box(8,10,2,2,hair1); box(14,10,2,2,hair1)
box(10,12,2,2,eye); box(14,12,2,2,eye)
px(11,13,iris); px(14,13,iris); px(12,14,skin3); px(13,14,skin3)
row(11,15,[skin3,skin3,skin3,skin3]); px(10,15,skin0); px(15,15,skin0)
# Side/top/bottom head surfaces with hair volume and ear details.
box(8,0,8,8,hair1); box(16,0,8,8,hair0); box(0,8,8,8,skin0); box(24,8,8,8,skin0)
box(2,11,3,3,skin1); px(2,12,skin2); box(26,11,3,3,skin1); px(27,12,skin2)
box(8,16,8,4,hair0); box(16,16,8,4,hair0); box(8,4,8,4,hair2); box(16,4,8,4,hair1)

# Torso base: heavy guild coat, pale shirt, collar, and a central fish-hook insignia.
box(20,20,8,12,navy1); box(16,20,4,12,navy0); box(28,20,4,12,navy0)
box(20,16,8,4,cream1); box(28,16,4,4,cream0)
box(21,20,6,3,cream2); box(23,23,2,2,leather1)
box(20,24,8,8,navy1); row(20,24,[navy2,navy2,navy1,navy1,navy1,navy1,navy2,navy2])
# layered lapels and guild fish mark
box(20,21,2,9,navy2); box(26,21,2,9,navy0)
box(22,26,4,4,fish0); row(22,27,[fish1,fish1,fish2,fish1]); px(26,27,fish1); px(21,27,fish1); px(23,26,fish2); px(23,29,fish0)
# belt across waist, buckle and hanging strap
box(20,30,8,2,leather1); box(21,30,2,2,leather2); box(24,30,3,2,leather0); box(23,30,2,2,metal); px(24,31,leather1)

# Torso side/back faces: seams, shoulder panels, and rear coat split.
box(32,20,4,12,navy0); box(36,20,8,12,navy1); box(36,21,8,2,navy2); box(40,24,4,8,navy0)
box(20,36,8,12,navy1); box(28,36,8,12,navy0); box(36,36,8,12,navy1); box(44,36,4,12,navy0)
box(21,36,2,10,navy2); box(34,36,2,10,navy2); box(37,36,2,10,navy2)
box(20,44,8,4,leather0); box(28,44,8,4,leather0); box(36,44,8,4,leather0)

# Right arm: top 44,16; left/front/right/back 40/44/48/52,20.
box(44,16,4,4,navy2); box(48,16,4,4,navy0)
box(40,20,4,8,navy1); box(40,28,4,4,cream1)
box(44,20,4,8,navy2); box(44,28,4,4,cream2)
box(48,20,4,8,navy0); box(48,28,4,4,skin2)
box(52,20,4,8,navy1); box(52,28,4,4,skin1)
box(44,24,1,4,navy3); box(44,28,1,4,cream1)
# Left arm: top 36,48; left/front/right/back 32/36/40/44,52.
box(36,48,4,4,navy2); box(40,48,4,4,navy0)
box(32,52,4,8,navy1); box(32,60,4,4,skin1)
box(36,52,4,8,navy2); box(36,60,4,4,skin2)
box(40,52,4,8,navy0); box(40,60,4,4,skin0)
box(44,52,4,8,navy1); box(44,60,4,4,skin1)
box(36,56,1,4,navy3); box(36,60,1,4,skin2)

# Right leg: top 4,16; left/front/right/back 0/4/8/12,20.
box(4,16,4,4,navy2); box(8,16,4,4,navy0)
box(0,20,4,8,navy1); box(0,28,4,4,boot1)
box(4,20,4,8,navy2); box(4,28,4,4,boot2)
box(8,20,4,8,navy0); box(8,28,4,4,boot0)
box(12,20,4,8,navy1); box(12,28,4,4,boot1)
box(4,24,1,4,navy3)
# Left leg: top 20,48; left/front/right/back 16/20/24/28,52.
box(20,48,4,4,navy2); box(24,48,4,4,navy0)
box(16,52,4,8,navy1); box(16,60,4,4,boot1)
box(20,52,4,8,navy2); box(20,60,4,4,boot2)
box(24,52,4,8,navy0); box(24,60,4,4,boot0)
box(28,52,4,8,navy1); box(28,60,4,4,boot1)
box(20,56,1,4,navy3)
# Rear apron/trouser panels and boot cuffs (unused faces are intentionally not transparent).
box(4,52,4,8,navy1); box(8,52,4,8,navy0); box(12,52,4,8,navy2)
box(4,60,4,4,boot1); box(8,60,4,4,boot2); box(12,60,4,4,boot1)
box(20,52,4,8,navy1); box(24,52,4,8,navy0); box(28,52,4,8,navy2)
box(20,60,4,4,boot1); box(24,60,4,4,boot2); box(28,60,4,4,boot1)

# Outer layer: fisherman cap, beard edge, coat lapels, belt pouches and boot cuffs.
box(40,0,8,8,navy1); box(48,0,8,8,navy0); box(56,0,8,8,navy1)
box(40,0,16,2,navy2); box(40,6,24,2,navy0); box(48,2,8,4,navy2)
# Front cap brim and side cloth: keeps the eyes exposed while making the headwear read in-game.
box(40,8,8,2,navy0); box(40,8,8,1,navy3); box(40,10,2,3,navy1); box(46,10,2,3,navy0)
box(32,8,8,8,hair0); box(48,8,8,8,hair0); box(56,8,8,8,hair1)
box(8,32,8,8,hair0); box(16,32,8,8,hair1); box(8,32,16,2,hair2)
# Bib/apron outer layer: shoulder straps, stitched front, fish badge, and lower hem.
box(20,36,8,12,navy0); box(20,36,2,12,navy2); box(26,36,2,12,navy2)
box(22,38,4,8,navy1); box(22,38,4,1,navy3); box(22,46,4,2,navy0)
box(22,41,4,4,fish0); row(22,42,[fish1,fish1,fish2,fish1]); px(21,42,fish1); px(26,42,fish1); px(23,41,fish2); px(23,44,fish0)
box(20,47,8,1,leather0)
box(20,40,2,8,navy2); box(26,40,2,8,navy0); box(28,40,4,4,leather1)
box(28,40,4,4,leather2); box(29,41,2,2,leather0); px(30,41,metal)
box(32,40,4,8,leather1); box(32,40,4,1,leather2); box(32,46,4,2,leather0)
box(4,48,4,4,boot1); box(8,48,4,4,boot2); box(12,48,4,4,boot1); box(16,48,4,4,boot0)
box(20,48,4,4,boot1); box(24,48,4,4,boot2); box(28,48,4,4,boot1); box(32,48,4,4,boot0)

im.save('/tmp/hagen-skin/hagen-guildmaster.png')
