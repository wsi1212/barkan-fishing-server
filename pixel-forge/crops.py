#!/usr/bin/env python3
# 특수작물 모델 v2 — X자 십자평면 전면 폐지(유저 지시 2026-07-17) → modelkit 박스 3D.
# 계약 유지: barkan:item/furniture/crop/<eng>_<stage>.json 경로 그대로 덮어씀 (Java/crops.yml 무변경).
# 7작물 × 3단계(sprout/grown/ripe), 작물·단계별 고유 실루엣 + 존 셰이딩 텍스처.
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".claude", "skills", "pixel-art", "scripts"))
from modelkit import Kit, Mat

CE = os.path.expanduser("~/Library/Application Support/feather/player-server/servers/"
                        "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/CraftEngine/resources/barkan_furniture")
MODELS = CE + "/resourcepack/assets/barkan/models/item/furniture/crop"
TEX = CE + "/resourcepack/assets/barkan/textures/furniture/crop"
os.makedirs(TEX, exist_ok=True)

G_SPROUT = "6fae52"   # 새싹 연두
G_LEAF = "4e8f3a"     # 잎 초록
SOIL = "6b4a2a"

def sprout(k, leaves):
    """공용 새싹 골격 — 작물별 잎 배치(leaves=[(f,t,rot)])가 실루엣을 가름."""
    k.box((7.4, 0, 7.4), (8.6, 3, 8.6), Mat(G_SPROUT, var=0.7, grain="v"))
    for f, t, rr in leaves:
        k.box(f, t, Mat(G_SPROUT, var=0.8), rot=rr)

def wheat(stage, k):
    if stage == 0:
        sprout(k, [((6, 2, 7.5), (7.6, 4.5, 8.5), ("z", 22.5)), ((8.4, 2.5, 7.5), (10, 5, 8.5), ("z", -22.5))])
    elif stage == 1:  # 녹색 이삭대 4줄기
        st = Mat("7aa04e", var=0.8, grain="v")
        for x, z, h, a in [(5, 7, 7, 22.5), (8, 8.5, 9, 0), (10.5, 6.5, 8, -22.5), (7, 6, 6, 0)]:
            k.box((x-0.5, 0, z-0.5), (x+0.5, h, z+0.5), st, rot=("z", a) if a else None)
            k.box((x-1, h-0.5, z-1), (x+1, h+2, z+1), Mat("9ab86a", var=0.7))
    else:             # 황금 이삭 — 고개 숙임
        st = Mat("b8a04e", var=0.7, grain="v"); hd = Mat("d8b23a", var=0.8)
        for x, z, h, a in [(4.5, 7, 8, 22.5), (8, 8.5, 10, 0), (11.5, 6.5, 9, -22.5), (6.5, 5.5, 7, 0), (9.5, 10, 8, 22.5)]:
            k.box((x-0.5, 0, z-0.5), (x+0.5, h, z+0.5), st, rot=("z", a) if a else None)
            k.box((x-1.2, h-0.8, z-1.2), (x+1.2, h+2.6, z+1.2), hd, rot=("z", 22.5))   # 숙인 이삭
def carrot(stage, k):
    if stage == 0:
        sprout(k, [((6.2, 2, 7.6), (7.8, 5, 8.4), ("z", 22.5)), ((8.2, 2, 7.6), (9.8, 5.2, 8.4), ("z", -22.5))])
    elif stage == 1:  # 깃잎 부채
        for x, a in [(4.5, 45), (6.5, 22.5), (8.5, 0), (10.5, -22.5), (12, -45)]:
            k.box((x-0.7, 0, 7.4), (x+0.7, 7, 8.6), Mat(G_LEAF, var=0.9), rot=("z", a, [8, 0.5, 8]))
    else:             # 깃잎 + 주황 어깨
        for x, a in [(5, 30), (8, 0), (11, -30)]:
            k.box((x-0.8, 0, 7.3), (x+0.8, 8, 8.7), Mat(G_LEAF, var=0.9), rot=("z", a, [8, 0.5, 8]))
        for f, t in [((4.2, 0, 6.2), (6.8, 2.2, 8.8)), ((9.2, 0, 7.2), (11.8, 2, 9.8)), ((6.5, 0, 9), (9, 1.8, 11.5))]:
            k.rounded_box(f, t, Mat("d97a2b", gloss=True), bevel=0.6)
def potato(stage, k):
    if stage == 0:
        sprout(k, [((6.4, 2.2, 7.5), (8, 4.4, 8.5), ("x", 22.5)), ((8, 2.6, 7.5), (9.6, 4.8, 8.5), ("x", -22.5))])
    elif stage == 1:  # 낮은 잎덤불
        k.rounded_box((3.5, 0, 4.5), (9.5, 4.5, 10.5), Mat(G_LEAF, var=0.9))
        k.rounded_box((8, 0, 6.5), (12.5, 3.8, 11.5), Mat("3f7a37", var=0.9))
    else:             # 덤불 + 흰꽃 + 흙두둑 감자
        k.box((3, 0, 4), (13, 1.4, 12), Mat(SOIL, var=0.9))                           # 두둑
        k.rounded_box((4, 1, 5), (10, 5.5, 11), Mat(G_LEAF, var=0.9))
        k.rounded_box((8.5, 1, 6.5), (12.8, 4.6, 11.8), Mat("3f7a37", var=0.9))
        for f, t in [((5.5, 5.5, 6.5), (7, 6.8, 8)), ((9.5, 4.6, 8.5), (11, 5.9, 10))]:
            k.box(f, t, Mat("eeeae0", var=0.5))                                        # 흰꽃
        k.box((11.4, 0, 4.8), (13.4, 1.6, 6.8), Mat("c9a86a", var=0.7))                # 삐져나온 감자
def tomato(stage, k):
    stick = Mat("8a6a44", var=0.7, grain="v")
    if stage == 0:
        k.box((7.6, 0, 7.6), (8.4, 6, 8.4), stick)
        sprout(k, [((6.4, 1.5, 7.5), (8, 3.5, 8.5), ("z", 22.5))])
    elif stage == 1:  # 지지대 + 덩굴
        k.box((7.6, 0, 7.6), (8.4, 12, 8.4), stick)
        for y, a in [(2, 22.5), (5.5, -22.5), (9, 22.5)]:
            k.box((5.8, y, 7.2), (10.2, y+2, 8.8), Mat(G_LEAF, var=0.9), rot=("y", a))
    else:             # + 빨간 알 3
        k.box((7.6, 0, 7.6), (8.4, 12, 8.4), stick)
        for y, a in [(2.5, 22.5), (6, -22.5), (9.5, 22.5)]:
            k.box((5.8, y, 7.2), (10.2, y+2, 8.8), Mat(G_LEAF, var=0.9), rot=("y", a))
        for f, t in [((4.8, 3, 6.6), (7.4, 5.6, 9.2)), ((9, 6.5, 7.4), (11.4, 8.9, 9.8)), ((5.6, 8.6, 6.4), (7.8, 10.8, 8.6))]:
            k.rounded_box(f, t, Mat("d1372c", gloss=True), bevel=0.6)
def cabbage(stage, k):
    if stage == 0:
        sprout(k, [((5.8, 1.5, 7.4), (7.9, 3.8, 8.6), ("z", 30)), ((8.1, 1.5, 7.4), (10.2, 3.8, 8.6), ("z", -30))])
    elif stage == 1:  # 벌어진 잎 4방
        c = Mat("7fae6e", var=0.8)
        for f, t, rr in [((2.8, 0, 5.5), (7, 5, 10.5), ("z", 22.5)), ((9, 0, 5.5), (13.2, 5, 10.5), ("z", -22.5)),
                         ((5.5, 0, 2.8), (10.5, 5, 7), ("x", -22.5)), ((5.5, 0, 9), (10.5, 5, 13.2), ("x", 22.5))]:
            k.box(f, t, c, rot=rr)
        k.rounded_box((6, 0, 6), (10, 3.5, 10), Mat("9cc48a", var=0.7))
    else:             # 꽉 찬 구
        c = Mat("7fae6e", var=0.8)
        for f, t, rr in [((2.5, 0, 5.5), (6.5, 5.5, 10.5), ("z", 30)), ((9.5, 0, 5.5), (13.5, 5.5, 10.5), ("z", -30)),
                         ((5.5, 0, 2.5), (10.5, 5.5, 6.5), ("x", -30)), ((5.5, 0, 9.5), (10.5, 5.5, 13.5), ("x", 30))]:
            k.box(f, t, c, rot=rr)
        k.rounded_box((4.5, 0, 4.5), (11.5, 7.5, 11.5), Mat("9cc48a", var=0.7), bevel=1.4)
def mushroom(stage, k):
    cap = Mat("9a6f46", var=0.8); st = Mat("d9caa2", var=0.7, grain="v", ao_top=True)
    if stage == 0:
        k.box((7, 0, 7), (9, 2.5, 9), st)
        k.dome(8, 2, 8, 5, 2.8, cap, layers=2)
    elif stage == 1:
        for x, z, h, w in [(5.5, 7, 3.5, 6), (10, 8.5, 5, 7)]:
            k.box((x-1, 0, z-1), (x+1, h, z+1), st)
            k.dome(x, h-0.5, z, w, 3.2, cap)
    else:
        for x, z, h, w, rr in [(4.5, 7.5, 4, 6, ("z", 22.5)), (8.5, 8.5, 7, 8, None), (12, 6.5, 3.5, 5.5, ("z", -22.5))]:
            k.box((x-1, 0, z-1), (x+1, h, z+1), st)
            k.dome(x, h-0.5, z, w, 3.6, cap, rot=rr) if rr else k.dome(x, h-0.5, z, w, 3.6, cap)
def melon(stage, k):
    vine = Mat("5c8a4a", var=0.9)
    if stage == 0:
        k.box((6, 0, 7.5), (10, 1.2, 8.5), vine, rot=("y", 22.5))
        sprout(k, [((8.5, 1, 7.5), (10.3, 3.4, 8.5), ("z", -22.5))])
    elif stage == 1:  # 덩굴 + 어린 멜론
        k.box((3.5, 0, 7.4), (9, 1.2, 8.6), vine, rot=("y", -22.5))
        k.rounded_box((7.5, 0, 6), (13, 5, 11.5), Mat("b8c86a", var=0.9, grain="v"), bevel=1)
    else:             # 큰 수박 — 진녹/연녹 교대 세로 슬랩 = 진짜 줄무늬 (양배추와 혼동 방지)
        k.box((2.5, 0, 6.4), (7, 1.2, 7.6), vine, rot=("y", 22.5))
        dark = Mat("2e6b34", var=0.6, grain="v"); light = Mat("7fae52", var=0.6, grain="v")
        x0 = 4.5
        for i, w in enumerate([2.2, 1.6, 2.2, 1.6, 2.2]):                              # 줄무늬 5칸
            k.box((x0, 0.8, 4.5), (x0 + w, 8.2, 13), dark if i % 2 == 0 else light)
            x0 += w
        k.box((5.2, 0, 5.2), (13.1, 0.8, 12.3), dark)                                  # 아랫굽
        k.box((5.2, 8.2, 5.2), (13.1, 9.2, 12.3), dark)                                # 윗굽
        k.box((8.4, 9.2, 8), (9.4, 10.8, 9), Mat("6b4a2a", var=0.7, grain="v"), rot=("z", 22.5))  # 꼭지 덩굴
CROPS = {"wheat": wheat, "carrot": carrot, "potato": potato, "tomato": tomato,
         "cabbage": cabbage, "mushroom": mushroom, "melon": melon}
STAGES = ["sprout", "grown", "ripe"]

def main():
    for eng, fn in CROPS.items():
        for si, stage in enumerate(STAGES):
            k = Kit(seed=si * 7 + hash(eng) % 97)
            fn(si, k)
            ref = f"barkan:furniture/crop/{eng}_{stage}"
            im, model = k.build(ref)
            im.save(f"{TEX}/{eng}_{stage}.png")
            json.dump(model, open(f"{MODELS}/{eng}_{stage}.json", "w"), indent=1)
            print(f"  ✔ {eng}_{stage} ({len(model['elements'])} elem)")
    print(f"OK — {len(CROPS)}작물 × 3단계 = {len(CROPS)*3}모델 (X자 폐지)")

if __name__ == "__main__":
    main()
