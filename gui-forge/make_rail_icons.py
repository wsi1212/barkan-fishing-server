#!/usr/bin/env python3
"""연결선(레일) 아이템 아이콘 — 가로/세로/모서리/분기 8종 × 점등·소등 + 아이콘 확대 설정.

## 왜 Codex가 준 모서리 조각을 안 쓰는가
받은 elbow 아트는 팔(arm)이 **칸 중심에 정렬돼 있지 않다**. 레일은 노드 칸 중심선
(cell center = 16+18*col, 26+18*row)에 정확히 맞아야 노드와 이어져 보인다. 그래서
직선 조각의 **단면(profile)** 만 뽑아 팔을 중심에서 각 변까지 그려 조립한다.
→ 모든 분기가 자동으로 중심 정렬되고, 점등/소등이 픽셀 단위로 일치한다.

## 소등본을 따로 안 받는 이유
따로 그려 받으면 실루엣이 미세하게 달라져 해금 순간 선이 움찔거린다.
점등본에서 탈채도·감광으로 파생시켜야 정확히 겹친다.

## 칸 밖으로 넘기는 이유
슬롯 간격 18px인데 아이템은 16px이라 칸마다 2px 빈틈이 생겨 선이 끊겨 보인다.
`display.gui.scale`로 아이템을 슬롯보다 크게 그려 메운다.
  · 레일 1.30 (16→20.8px)  · 노드 1.25 (16→20px)
  노드 원반 반지름 10 + 레일 반길이 10 → 노드 중심 간격 36을 정확히 덮어 맞물린다.
  transform이 무시되는 버전이면 16px로 그려질 뿐이라 안전하다(우아한 열화).

## 해상도
텍스처는 64px. 16으로 만들어 확대하면 실제로 16px 그림이 된다(1차 시도에서 그렇게 해서
뭉갰다). MC는 GUI 아이템을 화면 픽셀 단위로 nearest 샘플링하므로 64px이 그대로 살아난다.
"""
import json
import os

from PIL import Image, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "skilltree")
RP = os.path.expanduser("~/development/barkan-resourcepack")
TEX = os.path.join(RP, "assets/minecraft/textures/item/barkan_icon")
ITEMS = os.path.join(RP, "assets/barkan/items/barkan_icon")

ICON = 64                 # 텍스처 실해상도
THICK = 16                # 64 캔버스에서 파이프 두께 = GUI 4px
RAIL_SCALE = 1.30
NODE_SCALE = 1.25

# 분기 종류: 중심에서 어느 변으로 팔을 뻗는가
JUNCTIONS = {
    "h": "WE",            # 가로 (노드 사이)
    "v": "NS",            # 세로 (버스)
    "ne": "NE", "nw": "NW", "se": "SE", "sw": "SW",
    "tee": "NSE",         # 버스 중간에서 오른쪽 분기 (├)
    "cross": "NSEW",      # 근원이 왼쪽에서 들어오는 지점 (┼)
}


def dim(im):
    r, g, b, a = im.split()
    gray = ImageEnhance.Brightness(Image.merge("RGB", (r, g, b)).convert("L")).enhance(0.62)
    px, out = gray.load(), Image.new("RGBA", im.size)
    o, ap = out.load(), a.load()
    for y in range(im.height):
        for x in range(im.width):
            v = px[x, y]
            o[x, y] = (int(v * 0.94), int(v * 0.98), min(255, int(v * 1.10)), ap[x, y])
    return out


def pipe_profile(strip):
    """직선 레일에서 파이프 단면 1열을 뽑아 THICK 픽셀로 리샘플."""
    mid = strip.crop((strip.width // 2, 0, strip.width // 2 + 1, strip.height))
    return [mid.resize((1, THICK), Image.LANCZOS).getpixel((0, i)) for i in range(THICK)]


def junction(profile, arms):
    """중심 정렬된 분기 조각. arms 예: 'NSE'."""
    im = Image.new("RGBA", (ICON, ICON), (0, 0, 0, 0))
    px = im.load()
    lo = (ICON - THICK) // 2
    c = ICON // 2

    def h_run(x0, x1):
        for x in range(x0, x1):
            for i in range(THICK):
                px[x, lo + i] = profile[i]

    def v_run(y0, y1):
        for y in range(y0, y1):
            for i in range(THICK):
                px[lo + i, y] = profile[i]

    # 세로 먼저, 가로 나중 → 교차부에서 가로가 위로 와 노드로 이어지는 방향이 또렷하다
    if "N" in arms:
        v_run(0, c + THICK // 2)
    if "S" in arms:
        v_run(c - THICK // 2, ICON)
    if "W" in arms:
        h_run(0, c + THICK // 2)
    if "E" in arms:
        h_run(c - THICK // 2, ICON)
    return im


def write_item_json(icon_id, gui_scale=None):
    body = {"parent": "minecraft:item/generated",
            "textures": {"layer0": "minecraft:item/barkan_icon/" + icon_id}}
    if gui_scale:
        body["display"] = {"gui": {"scale": [gui_scale, gui_scale, gui_scale]}}
    with open(os.path.join(ITEMS, icon_id + ".json"), "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False)


def scale_node_icons():
    """스킬 노드 아이콘을 칸 밖으로 넘기도록 gui scale 부여.

    ★`skill_hub_*` 는 제외 — /레벨 허브 GUI에 쓰이고 그쪽 배경은 칸이 아니라 아트라
      키우면 아이콘 링 밖으로 삐져나온다(메달리온에서 같은 문제를 겪었다).
    """
    n = 0
    for f in sorted(os.listdir(TEX)):
        if not (f.startswith("skill_") and f.endswith(".png")) or f.startswith("skill_hub_"):
            continue
        write_item_json(f[:-4], gui_scale=NODE_SCALE)
        n += 1
    return n


def main():
    lit = Image.open(os.path.join(SRC, "rail_straight_lit.png")).convert("RGBA")
    prof_lit = pipe_profile(lit)
    prof_dim = pipe_profile(dim(lit))
    os.makedirs(ITEMS, exist_ok=True)

    n = 0
    for key, arms in JUNCTIONS.items():
        for state, prof in (("lit", prof_lit), ("dim", prof_dim)):
            name = f"tree_rail_{key}_{state}"
            junction(prof, arms).save(os.path.join(TEX, name + ".png"))
            write_item_json(name, gui_scale=RAIL_SCALE)
            n += 1
    # 구버전 이름 정리 (h 전용 2개)
    for old in ("tree_rail_lit", "tree_rail_dim"):
        for p in (os.path.join(TEX, old + ".png"), os.path.join(ITEMS, old + ".json")):
            if os.path.exists(p):
                os.remove(p)
    print(f"레일 조각 {n}개 ({', '.join(JUNCTIONS)}) × 점등/소등, {ICON}px, gui scale {RAIL_SCALE}")
    print(f"노드 아이콘 {scale_node_icons()}개에 gui scale {NODE_SCALE} 부여 (skill_hub_* 제외)")


if __name__ == "__main__":
    main()
