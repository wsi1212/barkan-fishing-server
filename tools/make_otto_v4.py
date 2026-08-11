from PIL import Image, ImageDraw

im=Image.new('RGBA',(64,64),(0,0,0,0)); d=ImageDraw.Draw(im)
skin=(214,155,108,255); skin_l=(235,183,132,255); skin_d=(157,94,67,255)
hair=(61,36,25,255); hair_l=(87,53,34,255); hair_d=(36,22,17,255)
shirt=(226,215,177,255); shirt_l=(245,236,202,255); shirt_d=(184,169,135,255)
apron=(25,49,78,255); apron_l=(43,73,111,255); apron_d=(15,29,51,255)
teal=(35,91,111,255); teal_l=(58,133,148,255); teal_d=(20,61,76,255)
belt=(94,56,29,255); belt_l=(135,82,37,255); boot=(70,45,29,255); boot_l=(112,70,39,255)
white=(248,244,219,255); eye=(25,30,30,255); fish=(70,177,186,255); fish_l=(118,219,211,255)
def r(x1,y1,x2,y2,c): d.rectangle((x1,y1,x2,y2),fill=c)
def face(x,y,w,h,c,hi,lo):
    r(x,y,x+w-1,y+h-1,c); r(x,y,x+w-1,y,hi); r(x,y+h-1,x+w-1,y+h-1,lo)
def matrix(x,y,rows,pal):
    for yy,row in enumerate(rows):
        for xx,key in enumerate(row): r(x+xx,y+yy,x+xx,y+yy,pal[key])

# HEAD surfaces (classic layout)
face(8,8,8,8,skin,skin_l,skin_d); face(0,8,8,8,skin_d,skin,skin_d)
face(16,8,8,8,skin,skin_l,skin_d); face(24,8,8,8,hair,hair_l,hair_d)
face(8,0,8,8,teal,teal_l,teal_d); face(16,0,8,8,skin_d,skin,skin_d)
# cap brim / hairline and face details
# Larger readable eyes and a cleaner face; cap brim only occupies one row.
r(8,8,15,8,teal_d); r(8,9,9,10,hair); r(14,9,15,10,hair)
r(9,11,10,12,white); r(13,11,14,12,white)
r(10,12,10,13,(35,169,185,255)); r(13,12,13,13,(35,169,185,255))
r(10,13,10,13,eye); r(13,13,13,13,eye)
r(11,13,12,14,skin_d); r(11,15,14,15,hair_d)
# Original Otto face, using the reference's small-nose / 2x2-eye language.
matrix(8,8,[
 ['h','h','h','h','h','h','h','h'],
 ['h','h','s','s','s','s','h','h'],
 ['h','s','s','s','s','s','s','h'],
 ['s','w','w','s','s','w','w','s'],
 ['s','w','c','s','s','c','w','s'],
 ['s','s','s','d','d','s','s','s'],
 ['s','s','s','d','d','s','s','s'],
 ['d','d','d','d','d','d','d','d']],
 {'h':hair,'s':skin,'w':white,'c':(35,169,185,255),'d':skin_d})

# TORSO surfaces
face(20,20,8,12,shirt,shirt_l,shirt_d); face(16,20,4,12,shirt_d,shirt,shirt_d)
face(28,20,4,12,shirt_d,shirt,shirt_d); face(32,20,4,12,shirt,shirt_l,shirt_d)
face(20,16,8,4,shirt,shirt_l,shirt_d); face(28,16,8,4,shirt_d,shirt,shirt_d)
# apron on front and straps on back
r(20,22,27,31,apron); r(20,22,20,31,apron_l); r(27,22,27,31,apron_d)
r(21,22,22,31,apron_l); r(25,22,26,31,apron_d)
r(22,25,24,27,fish); r(21,26,21,26,fish_l); r(25,26,26,26,fish_l); r(23,24,23,24,fish_l); r(23,28,23,28,fish_l)
r(20,30,27,31,belt_l); r(20,30,27,30,belt); r(23,30,24,31,(226,177,72,255))
r(32,20,33,31,apron); r(35,20,35,31,apron_d)
# Original Otto apron front: layered collar, straps, stitching, fish emblem, and waist.
matrix(20,20,[
 ['q','q','q','q','q','q','q','q'],
 ['q','q','n','n','n','n','q','q'],
 ['q','n','n','n','n','n','n','q'],
 ['n','n','n','n','n','n','n','n'],
 ['n','n','n','f','f','n','n','n'],
 ['n','n','f','f','f','f','n','n'],
 ['n','n','n','f','f','n','n','n'],
 ['n','n','n','n','n','n','n','n'],
 ['n','n','n','n','n','n','n','n'],
 ['b','b','b','g','g','b','b','b'],
 ['n','n','n','n','n','n','n','n'],
 ['d','d','d','d','d','d','d','d']],
 {'q':shirt,'n':apron,'f':fish,'b':belt_l,'g':(226,177,72,255),'d':apron_d})

def arm(x,classic=True):
    # x is left edge of the six classic arm faces: left, front, right, back at y20; top/bottom at y16
    face(x+4,20,4,12,shirt,shirt_l,shirt_d); face(x,20,4,12,shirt_d,shirt,shirt_d)
    face(x+8,20,4,12,shirt_d,shirt,shirt_d); face(x+12,20,4,12,shirt_d,shirt,shirt_d)
    for xx in (x,x+4,x+8,x+12): r(xx,28,xx+3,31,skin)
    for xx in (x,x+4,x+8,x+12): r(xx,28,xx+3,28,skin_l)
    face(x+4,16,4,4,shirt,shirt_l,shirt_d); face(x+8,16,4,4,skin_d,skin,skin_d)
arm(40)
# left arm (same layout in lower half)
face(36,52,4,12,shirt,shirt_l,shirt_d); face(32,52,4,12,shirt_d,shirt,shirt_d)
face(40,52,4,12,shirt_d,shirt,shirt_d); face(44,52,4,12,shirt_d,shirt,shirt_d)
for xx in (32,36,40,44): r(xx,60,xx+3,63,skin)
for xx in (32,36,40,44): r(xx,60,xx+3,60,skin_l)
face(36,48,4,4,shirt,shirt_l,shirt_d); face(40,48,4,4,skin_d,skin,skin_d)

def leg(x,y):
    face(x+4,y+4,4,12,apron,apron_l,apron_d); face(x,y+4,4,12,apron_d,apron,apron_d)
    face(x+8,y+4,4,12,apron_d,apron,apron_d); face(x+12,y+4,4,12,apron_d,apron,apron_d)
    for xx in (x,x+4,x+8,x+12): r(xx,y+12,xx+3,y+15,boot)
    for xx in (x,x+4,x+8,x+12): r(xx,y+12,xx+3,y+12,boot_l)
    face(x+4,y,4,4,apron,apron_l,apron_d); face(x+8,y,4,4,boot,boot_l,boot)
leg(0,16); leg(16,48)

# OUTER LAYER: small, bounded details only. Never cover the full face.
# Fisher cap crown and brim.
r(40,0,47,5,teal); r(40,0,47,0,teal_l); r(40,5,47,5,teal_d)
r(32,8,39,10,teal); r(32,8,39,8,teal_l); r(32,10,39,10,teal_d)
r(40,8,47,10,teal); r(40,8,47,8,teal_l); r(40,10,47,10,teal_d)
r(48,8,55,10,teal_d); r(48,8,55,8,teal); r(48,10,55,10,teal_d)
r(56,8,63,10,teal); r(56,8,63,8,teal_l); r(56,10,63,10,teal_d)
# Apron bib, straps, and pouch.
r(20,36,27,47,apron); r(20,36,21,47,apron_l); r(26,36,27,47,apron_d)
r(22,38,25,38,fish); r(22,42,25,42,apron_l)
r(28,36,31,39,belt); r(28,36,31,36,belt_l)
# Rolled sleeve cuffs and trouser cuffs.
r(44,36,47,39,shirt_d); r(36,36,39,39,shirt_d)
r(4,36,7,39,apron_l); r(20,36,23,39,apron_l)

im.save('/tmp/otto-skin/otto-v4.png')
