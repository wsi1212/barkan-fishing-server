#!/usr/bin/env python3
"""Sprite -> voxel-extruded Minecraft model (like a dropped item, but placeable).

Turns a 16x16 (or 32x32) sprite into a model where every opaque pixel becomes a
1-px-deep box, merged into horizontal runs. Fruits/objects get real 3-D presence
instead of the paper-thin look a flat plane or cross model gives them.
Plants (mushrooms, flowers, grass) still look better as cross models — use this
for solid objects.

Faces are emitted only where the neighbor pixel is transparent (no z-fighting);
runs split when above/below transparency changes. Typical element count 20-60.

Usage:
  python sprite_to_voxel.py sprite.png out_model.json barkan:furniture/forage/z_fruit
Import:
  from sprite_to_voxel import voxelize; model = voxelize("s.png", "barkan:...")
"""
import sys, json
from PIL import Image

def voxelize(png, tex_ref, thick=1.0):
    im = Image.open(png).convert("RGBA")
    W, H = im.size
    px = im.load()
    op = lambda x, y: 0 <= x < W and 0 <= y < H and px[x, y][3] > 8
    z0, z1 = 8 - thick/2, 8 + thick/2
    u = 16.0 / W                                   # image px -> uv units
    els = []
    for y in range(H):
        x = 0
        while x < W:
            if not op(x, y): x += 1; continue
            sig = (op(x, y-1), op(x, y+1))
            x0 = x
            while x < W and op(x, y) and (op(x, y-1), op(x, y+1)) == sig:
                x += 1
            x1 = x                                  # exclusive
            fy0, fy1 = (H - 1 - y) * u, (H - y) * u   # model Y of this row
            faces = {
                "south": {"uv": [x0*u, y*u, x1*u, (y+1)*u], "texture": "#0"},
                "north": {"uv": [x1*u, y*u, x0*u, (y+1)*u], "texture": "#0"},
            }
            if not op(x0-1, y): faces["west"] = {"uv": [x0*u, y*u, (x0+1)*u, (y+1)*u], "texture": "#0"}
            if not op(x1, y):   faces["east"] = {"uv": [(x1-1)*u, y*u, x1*u, (y+1)*u], "texture": "#0"}
            if not sig[0]:      faces["up"]   = {"uv": [x0*u, y*u, x1*u, (y+1)*u], "texture": "#0"}
            if not sig[1]:      faces["down"] = {"uv": [x0*u, y*u, x1*u, (y+1)*u], "texture": "#0"}
            els.append({"from": [x0*u, fy0, z0], "to": [x1*u, fy1, z1], "faces": faces})
    return {"textures": {"0": tex_ref, "particle": tex_ref}, "elements": els,
            "display": {"fixed": {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [1, 1, 1]}}}

if __name__ == "__main__":
    m = voxelize(sys.argv[1], sys.argv[3])
    json.dump(m, open(sys.argv[2], "w"), indent=1)
    print(f"voxelized {sys.argv[1]} -> {sys.argv[2]} ({len(m['elements'])} elements)")
