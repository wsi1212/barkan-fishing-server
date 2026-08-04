#!/usr/bin/env python3
"""연결선(레일) 아이콘 — **처음 완성된 배경 아트에서 칸 단위로 추출**.

## 왜 이 방식인가
Codex의 elbow 조각을 겹쳐 tee/cross를 만드니 둥근 코너가 여러 겹 쌓여 **갈고리 사슬**처럼
됐다(버스 트렁크가 직선이 아니라 물결). 반면 `barkan_skilltree_gui_A_detailrestored5.png`
에는 근원→버스→계열 분기가 이미 제대로 그려져 있다.
→ 그 아트에서 **칸(36x36, 2배 좌표) 단위로 잘라내면 이어짐이 원본 그대로 보장**된다.
  같은 연속 그림에서 나온 타일이라 인접 타일이 자동으로 딱 맞는다. 정렬 계산이 필요 없다.

측정으로 확인: 버스 세로선이 col1 칸의 **정중앙 x68**(칸 x50~85, 중심 68)에 있다.

## 크기·배율
타일 = 칸 1개 = 36px(2배) = GUI 18px.
아이템은 기본 16px로 그려지므로 `display.gui.scale = 1.125` (16x1.125 = 18)를 주면
타일이 칸 피치와 **정확히** 일치 → 인접 레일 사이 빈틈 0.

## 소등본
점등본에서 탈채도·감광으로 파생 (따로 그려 받으면 실루엣이 어긋나 전환 시 움찔거린다).
"""
import json
import os

from PIL import Image, ImageEnhance

SRC_ART = os.path.expanduser("~/Downloads/barkan_skilltree_gui_A_detailrestored5.png")
RP = os.path.expanduser("~/development/barkan-resourcepack")
TEX = os.path.join(RP, "assets/minecraft/textures/item/barkan_icon")
ITEMS = os.path.join(RP, "assets/barkan/items/barkan_icon")

CELL = 36                     # 2배 좌표에서 칸 한 칸
CX0, CY0 = 14, 34             # 격자 원점 (2배)
# ★레일은 반드시 1.125 — 타일이 칸 1개(GUI 18px)를 담고 있으므로 16*1.125=18 이면 내용이
#   원본과 1:1로 맞는다. 1.45로 늘렸더니 선이 굵어지고 인접 타일과 간격이 안 맞아 끊겼다.
RAIL_SCALE = 1.125

# 역할 → (col, row).  A 아트(근원 + 4계열)에서 필요한 모양이 전부 나온다.
#   row1 = ┌(버스 시작)  row2 = ┼(근원이 왼쪽에서 진입)  row3 = ├  row4 = └(버스 끝)
#   3계열은 row1/row2/row4 를 쓰면 되고, 2페이지는 h 만 쓴다.
PIECES = {
    "h":          (3, 1),     # 노드 사이 가로
    "bus_top":    (1, 1),
    "bus_root":   (1, 2),
    "bus_mid":    (1, 3),
    "bus_bottom": (1, 4),
}

DIFF_GAIN = 9                 # 배경과의 차이를 알파로 환산할 때의 이득


def key_rail(tile, clean):
    """레일만 남긴다 — **배경 차분** 방식.

    ★밝기 임계값(lum>32)으로 자르던 방식은 실패했다: 선의 어두운 양끝(안티에일리어싱)이
      임계 아래라 날아가서 타일 경계마다 선이 끊겼다.
      대신 **같은 칸의 노드 없는 행(row0) 픽셀**을 배경 기준으로 삼아 차분한다.
      배경과 다른 만큼만 알파를 주니 선의 흐린 끝까지 온전히 남고, 벽면 노이즈는 0이 된다.
    """
    tile = tile.convert("RGBA")
    px, cp = tile.load(), clean.convert("RGB").load()
    for y in range(tile.height):
        for x in range(tile.width):
            r, g, b, _ = px[x, y]
            br, bg_, bb = cp[x, y]
            d = abs(r - br) + abs(g - bg_) + abs(b - bb)
            px[x, y] = (r, g, b, min(255, d * DIFF_GAIN))
    return tile


def dim(im):
    r, g, b, a = im.split()
    gray = ImageEnhance.Brightness(Image.merge("RGB", (r, g, b)).convert("L")).enhance(0.60)
    px, out = gray.load(), Image.new("RGBA", im.size)
    o, ap = out.load(), a.load()
    for y in range(im.height):
        for x in range(im.width):
            v = px[x, y]
            o[x, y] = (int(v * 0.94), int(v * 0.98), min(255, int(v * 1.10)), ap[x, y])
    return out


def write_item_json(icon_id, gui_scale):
    body = {"parent": "minecraft:item/generated",
            "textures": {"layer0": "minecraft:item/barkan_icon/" + icon_id},
            "display": {"gui": {"scale": [gui_scale] * 3}}}
    with open(os.path.join(ITEMS, icon_id + ".json"), "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False)


def main():
    art = Image.open(SRC_ART).convert("RGB")
    os.makedirs(ITEMS, exist_ok=True)
    for name, (col, row) in PIECES.items():
        x0, y0 = CX0 + CELL * col, CY0 + CELL * row
        clean = art.crop((x0, CY0, x0 + CELL, CY0 + CELL))     # 같은 열의 row0 = 배경 기준
        tile = key_rail(art.crop((x0, y0, x0 + CELL, y0 + CELL)), clean)
        for state, im in (("lit", tile), ("dim", dim(tile))):
            iid = f"tree_rail_{name}_{state}"
            im.save(os.path.join(TEX, iid + ".png"))
            write_item_json(iid, RAIL_SCALE)
    # 겹쳐 만들던 구버전 조각 정리
    for old in ("h", "v", "nw", "ne", "sw", "se", "tee", "cross"):
        for st in ("lit", "dim"):
            for p in (os.path.join(TEX, f"tree_rail_{old}_{st}.png"),
                      os.path.join(ITEMS, f"tree_rail_{old}_{st}.json")):
                if os.path.exists(p) and old != "h":
                    os.remove(p)
    print(f"레일 {len(PIECES)}종 × 점등/소등 = {len(PIECES)*2}개, {CELL}px, gui scale {RAIL_SCALE}")
    print("  " + ", ".join(PIECES))
    print("  (노드 아이콘 배율은 icon-forge/register_icons.py 담당)")


if __name__ == "__main__":
    main()
