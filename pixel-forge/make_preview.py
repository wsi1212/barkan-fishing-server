#!/usr/bin/env python3
# 상품 미리보기 합성 — MCModels 상품샷 스타일 (그라데이션 배경 + 라인업 + 타이틀)
import os, math
from PIL import Image, ImageDraw, ImageFont
RENDERS = ["tx_mushred","tx_mushblue","tx_mushorange","tx_mushtable","tx_mushshelf",
           "tx_mushcluster","tx_mushtall","tx_mushpink","tx_fruit","tx_berry","tx_herb"]
W, H = 1600, 1200
img = Image.new("RGB", (W, H)); px = img.load()
for y in range(H):                                    # 딥그린 세로 그라데이션 (채집 테마)
    t = y / H
    px_row = (int(24+18*t), int(48+30*t), int(34+22*t))
    for x in range(W): px[x, y] = px_row
d = ImageDraw.Draw(img)
tiles = []
for n in RENDERS:
    p = f"/tmp/{n}.png"
    if os.path.isfile(p):
        im = Image.open(p).convert("RGBA")
        bbox = im.getbbox(); im = im.crop(bbox) if bbox else im
        im.thumbnail((300, 300), Image.LANCZOS); tiles.append(im)
cols = 4; rows = math.ceil(len(tiles)/cols)
cw, ch = W//cols, (H-320)//rows
for i, im in enumerate(tiles):
    r, c = divmod(i, cols)
    x = c*cw + (cw-im.width)//2 + (cw//2 if r == rows-1 and len(tiles) % cols else 0)
    y = 140 + r*ch + (ch-im.height)//2
    sh = Image.new("RGBA", (im.width, 24), (0, 0, 0, 0))            # 바닥 그림자
    ImageDraw.Draw(sh).ellipse((6, 4, im.width-6, 20), fill=(0, 0, 0, 70))
    img.paste(sh, (x, y+im.height-10), sh)
    img.paste(im, (x, y), im)
try: f_big = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 64); f_s = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 30)
except: f_big = f_s = None
d.text((W//2, 58), "BARKAN FORAGE PACK", fill=(240, 234, 214), font=f_big, anchor="mm")
d.text((W//2, H-64), f"{len(tiles)} handcrafted 3D foraging props  ·  CraftEngine ready  ·  modelkit v3", fill=(190, 200, 185), font=f_s, anchor="mm")
img.save("/tmp/forage_product.png"); print("preview /tmp/forage_product.png", img.size)
