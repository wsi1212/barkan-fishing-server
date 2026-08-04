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
RAIL_SCALE = 1.125            # 16 * 1.125 = 18 = 칸 피치
NODE_SCALE = 1.125            # 노드도 같은 배율 — 원반 18 + 레일 18 = 중심간격 36을
                              # 빈틈·겹침 없이 정확히 채운다. 1.25는 너무 커 보였다.

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

KEY_LO, KEY_HI = 32, 62       # 이 밝기 구간에서 알파를 0→255로 (패널 벽면은 lum~24)


def key_rail(tile):
    """패널 배경(어두운 벽면)을 빼고 레일만 남긴다. 금테·시안코어 둘 다 보존."""
    tile = tile.convert("RGBA")
    px = tile.load()
    for y in range(tile.height):
        for x in range(tile.width):
            r, g, b, _ = px[x, y]
            lum = (r * 2 + g * 5 + b) // 8
            if lum <= KEY_LO:
                px[x, y] = (0, 0, 0, 0)
            else:
                a = 255 if lum >= KEY_HI else int(255 * (lum - KEY_LO) / (KEY_HI - KEY_LO))
                px[x, y] = (r, g, b, a)
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


def scale_node_icons():
    """스킬 노드 아이콘도 칸 피치에 맞춰 확대.

    ★`skill_hub_*` 는 제외 — /레벨 허브 GUI 아트에 맞춰진 아이콘이라 키우면 링 밖으로
      삐져나온다(예전에 메달리온에서 같은 문제를 겪었다).
    """
    n = 0
    for f in sorted(os.listdir(TEX)):
        if not (f.startswith("skill_") and f.endswith(".png")) or f.startswith("skill_hub_"):
            continue
        write_item_json(f[:-4], NODE_SCALE)
        n += 1
    return n


def main():
    art = Image.open(SRC_ART).convert("RGB")
    os.makedirs(ITEMS, exist_ok=True)
    for name, (col, row) in PIECES.items():
        x0, y0 = CX0 + CELL * col, CY0 + CELL * row
        tile = key_rail(art.crop((x0, y0, x0 + CELL, y0 + CELL)))
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
    print(f"노드 아이콘 {scale_node_icons()}개 gui scale {NODE_SCALE} (skill_hub_* 제외)")


if __name__ == "__main__":
    main()
