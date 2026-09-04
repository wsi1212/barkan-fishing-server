import sys, amulet_nbt as nbt
path, name, x, y, z = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
f = nbt.load(path + "/level.dat")
d = f.compound["Data"]
d["LevelName"] = nbt.StringTag(name)
sp = d["spawn"]
sp["dimension"] = nbt.StringTag("minecraft:" + name)
sp["pos"] = nbt.IntArrayTag([x, y, z])
for k in ("Player",):
    if k in d: del d[k]
f.save_to(path + "/level.dat")
print("level.dat 갱신:", name, (x, y, z))
