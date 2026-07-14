#!/usr/bin/env python3
"""슬롯 GUI 릴 심볼 아이콘 = 배당표 아트(ChatGPT, slot_paytable.png)에서 6종 크롭 (2026-07-14).

바닐라 Material(SWEET_BERRIES 등) 대신 배당표와 시각적으로 통일된 커스텀 아이콘을 쓴다.
좌표(BOXES)는 slot_paytable.png(1024×1536)를 격자 오버레이로 실측한 값 — 이미지가
바뀌면 재실측 필요. 배경 제거는 단순 색거리가 아니라 "테두리에서 시작하는 flood-fill"
(코너 4점이 아니라 전체 테두리 링을 시드로) — BAR처럼 안쪽이 어두운 도형은 금테에
막혀 안 지워지고, 바깥 펠트만 연결성 기준으로 제거된다.

출력: RP assets/{minecraft/textures/item,barkan/models,barkan/items}/slot/sym_*.
CasinoManager.slotSymbolItem()이 barkan:slot/sym_<symbol>로 참조.
"""

import os
from PIL import Image, ImageFilter
import numpy as np
from collections import deque

RP = os.path.expanduser("~/development/barkan-resourcepack")
SRC = os.path.join(RP, "assets/barkan/textures/painting/slot_paytable.png")
im = Image.open(SRC).convert("RGBA")
arr = np.array(im)

BOXES = {
    "cherry": (100, 250, 293, 395),
    "lemon":  (100, 250, 402, 490),
    "bell":   (100, 250, 508, 595),
    "bar":    (95, 255, 615, 700),
    "diamond":(100, 250, 695, 795),
    "seven":  (100, 250, 812, 895),
}

TEX_OUT = os.path.join(RP, "assets/minecraft/textures/item/slot")
MODEL_OUT = os.path.join(RP, "assets/barkan/models/slot")
ITEM_OUT = os.path.join(RP, "assets/barkan/items/slot")
for d in (TEX_OUT, MODEL_OUT, ITEM_OUT):
    os.makedirs(d, exist_ok=True)


def bg_mask_floodfill(rgb, thresh=48):
    h, w, _ = rgb.shape
    corners = np.concatenate([
        rgb[0:6, 0:6].reshape(-1, 3), rgb[0:6, -6:].reshape(-1, 3),
        rgb[-6:, 0:6].reshape(-1, 3), rgb[-6:, -6:].reshape(-1, 3),
    ], axis=0).astype(int)
    ref = corners.mean(axis=0)
    diff_full = np.abs(rgb.astype(int) - ref).sum(axis=2)
    close = diff_full <= thresh

    visited = np.zeros((h, w), dtype=bool)
    q = deque()
    # ★전체 테두리 링(코너 4점만이 아니라)에서 시드 — 노이즈로 특정 코너 픽셀 하나가
    #   임계 밖이어도 나머지 테두리 픽셀들이 시드 역할을 해 flood가 막히지 않는다.
    border_pixels = []
    border_pixels += [(0, x) for x in range(w)]
    border_pixels += [(h - 1, x) for x in range(w)]
    border_pixels += [(y, 0) for y in range(h)]
    border_pixels += [(y, w - 1) for y in range(h)]
    for y, x in border_pixels:
        if close[y, x] and not visited[y, x]:
            visited[y, x] = True
            q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and close[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))
    return visited


def write_rp_json(symbol):
    model = os.path.join(MODEL_OUT, f"sym_{symbol}.json")
    item = os.path.join(ITEM_OUT, f"sym_{symbol}.json")
    with open(model, "w") as f:
        f.write('{"parent":"minecraft:item/generated","textures":{"layer0":"minecraft:item/slot/sym_%s"}}' % symbol)
    with open(item, "w") as f:
        f.write('{"model":{"type":"minecraft:model","model":"barkan:slot/sym_%s"}}' % symbol)


for name, (x0, x1, y0, y1) in BOXES.items():
    crop = arr[y0:y1, x0:x1].copy()
    bg = bg_mask_floodfill(crop[:, :, :3])
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    mask_img = Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(1.0))
    crop[:, :, 3] = np.minimum(crop[:, :, 3], np.array(mask_img))
    out_img = Image.fromarray(crop, "RGBA")

    bbox = out_img.getbbox(alpha_only=True)
    if bbox:
        out_img = out_img.crop(bbox)
    side = max(out_img.size) + 16
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    ox = (side - out_img.width) // 2
    oy = (side - out_img.height) // 2
    canvas.paste(out_img, (ox, oy), out_img)
    canvas = canvas.resize((128, 128), Image.LANCZOS)
    canvas.save(os.path.join(TEX_OUT, f"sym_{name}.png"))
    write_rp_json(name)
    print(name, "bbox", bbox, "bg_pixels", int(bg.sum()), "/", bg.size)

print(f"완료: {len(BOXES)}종 → {TEX_OUT}")
