import sys; from PIL import Image
im=Image.open(sys.argv[1]).convert("RGBA")
s=int(sys.argv[3]) if len(sys.argv)>3 else 16
im.resize((im.width*s,im.height*s),Image.NEAREST).save(sys.argv[2]); print("shown",sys.argv[2],im.size)
