#!/usr/bin/env python3
"""Side-by-side: reference image vs your sprite, same visual height, one PNG.

Usage: python compare.py <ref.png> <sprite.png> <out.png> [ref2.png sprite2.png ...]
Pairs alternate ref,sprite. Look at the output and name what differs in words
(shape? palette? light direction?) before touching pixels again.
"""
import sys
from PIL import Image, ImageDraw

H = 320
def load(p, pixel):
    im = Image.open(p).convert("RGBA")
    if pixel:
        s = max(1, H // max(im.size))
        return im.resize((im.width*s, im.height*s), Image.NEAREST)
    im.thumbnail((H*2, H), Image.LANCZOS)
    return im

args = sys.argv[1:]; out = args.pop()
tiles = []
for i, p in enumerate(args):
    is_sprite = i % 2 == 1
    tiles.append((("REF", "MINE")[is_sprite], load(p, is_sprite)))
pad = 16
W = sum(t[1].width for t in tiles) + pad*(len(tiles)+1)
sheet = Image.new("RGBA", (W, H+pad*2+18), (238, 236, 230, 255))
d = ImageDraw.Draw(sheet); x = pad
for label, im in tiles:
    y = pad + (H - im.height)//2
    sheet.paste(im, (x, y), im)
    d.text((x, H+pad+4), label, fill=(60, 60, 60, 255))
    x += im.width + pad
sheet.save(out); print("compare ->", out, sheet.size)
