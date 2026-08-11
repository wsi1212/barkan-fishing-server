from PIL import Image, ImageDraw

im = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
d = ImageDraw.Draw(im)

skin=(214,155,108,255); skin_hi=(235,183,132,255); skin_sh=(156,96,68,255)
hair=(63,38,26,255); hair_sh=(39,24,19,255)
cream=(226,215,177,255); cream_sh=(188,173,139,255)
navy=(28,48,78,255); navy_hi=(43,70,108,255)
teal=(35,91,111,255); teal_hi=(53,126,145,255); teal_sh=(22,65,80,255)
brown=(91,55,30,255); brown_hi=(125,76,37,255)
boot=(73,48,31,255); boot_hi=(111,72,40,255)
black=(25,22,20,255); white=(245,242,220,255)
fish=(78,174,184,255); fish_hi=(112,211,208,255)

def rect(box,c): d.rectangle(box,fill=c)
def panel(x,y,w,h,c,hi=None,sh=None):
    rect((x,y,x+w-1,y+h-1),c)
    if hi: rect((x,y,x+w-1,y),hi)
    if sh: rect((x,y+h-1,x+w-1,y+h-1),sh)

# Head: face and dark hair.
panel(8,8,8,8,skin,skin_hi,skin_sh); panel(24,8,8,8,hair,hair_sh,hair_sh)
panel(0,8,8,8,skin_sh,skin,skin_sh); panel(16,8,8,8,skin,skin_hi,skin_sh)
panel(8,0,8,8,hair,hair_sh,hair_sh); panel(16,0,8,8,skin_sh,skin,skin_sh)
rect((8,8,15,9),hair); rect((8,10,9,11),hair); rect((14,10,15,11),hair)
rect((10,12,10,12),white); rect((13,12,13,12),white)
rect((11,12,12,13),black); rect((14,12,14,13),black); rect((11,14,13,14),skin_sh)

# Torso: cream shirt and navy fish apron.
panel(20,20,8,12,cream,cream,cream_sh); panel(32,20,4,12,cream_sh,cream,cream_sh)
panel(16,20,4,12,cream_sh,cream,cream_sh); panel(20,16,8,4,cream,cream,cream_sh)
panel(28,16,8,4,cream_sh,cream,cream_sh)
rect((20,22,27,31),navy); rect((20,22,20,31),navy_hi); rect((27,22,27,31),(15,29,51,255))
rect((21,22,26,23),navy_hi)
# Fish emblem.
rect((22,26,24,28),fish); rect((25,27,26,27),fish_hi); rect((21,27,21,27),fish_hi)
rect((23,25,24,25),fish_hi); rect((23,29,23,29),fish_hi)
rect((20,30,27,31),brown); rect((23,30,24,31),brown_hi)

# Right arm.
panel(44,20,4,12,cream,cream,cream_sh); panel(52,20,4,12,cream_sh,cream,cream_sh)
panel(40,20,4,12,cream_sh,cream,cream_sh); panel(48,20,4,12,skin,skin_hi,skin_sh)
panel(44,16,4,4,cream,cream,cream_sh); panel(48,16,4,4,skin_sh,skin,skin_sh)
# Left arm.
panel(36,52,4,12,cream,cream,cream_sh); panel(44,52,4,12,cream_sh,cream,cream_sh)
panel(32,52,4,12,cream_sh,cream,cream_sh); panel(40,52,4,12,skin,skin_hi,skin_sh)
panel(36,48,4,4,cream,cream,cream_sh); panel(40,48,4,4,skin_sh,skin,skin_sh)

# Right leg.
panel(4,20,4,12,navy,navy_hi,navy); panel(12,20,4,12,navy,navy_hi,navy)
panel(0,20,4,12,navy_hi,navy,navy); panel(8,20,4,12,boot,boot_hi,boot)
panel(4,16,4,4,navy,navy_hi,navy); panel(8,16,4,4,boot,boot_hi,boot)
# Left leg.
panel(20,52,4,12,navy,navy_hi,navy); panel(28,52,4,12,navy,navy_hi,navy)
panel(16,52,4,12,navy_hi,navy,navy); panel(24,52,4,12,boot,boot_hi,boot)
panel(20,48,4,4,navy,navy_hi,navy); panel(24,48,4,4,boot,boot_hi,boot)

# First-pass headwear is painted on the base layer so no outer-layer UV can cover the face.
# A true 3D cap will be added only after this base skin is visually verified in-game.
rect((8,0,15,7),teal); rect((8,0,15,0),teal_hi); rect((8,7,15,7),teal_sh)
rect((8,8,15,9),teal_sh)
# Outer apron bib and belt pouch.
rect((20,36,21,47),navy_hi); rect((26,36,27,47),navy_hi); rect((22,38,25,47),navy)
rect((22,41,25,41),fish); rect((28,36,31,39),brown); rect((28,36,31,36),brown_hi)

im.save('/tmp/otto-skin/otto-fishmonger.png')
