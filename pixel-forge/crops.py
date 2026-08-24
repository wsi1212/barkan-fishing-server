#!/usr/bin/env python3
"""특수작물 성장 모델 v4.

7종 × 5단계(sprout/young/grown/tall/ripe)의 CraftEngine ItemDisplay 모델을
modelkit으로 생성한다. 단계가 올라갈수록 단순히 큐브를 키우지 않고, 줄기·잎·열매의
실루엣이 먼저 읽히도록 만든다. 모델 텍스처는 전부 오토 아틀라스이며, 원본 모델은
16×16 슬롯 아이콘이 아니라 월드용 3D 가구 모델이다.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".claude", "skills", "pixel-art", "scripts"))
from modelkit import Kit, Mat


CE = os.path.expanduser("~/Library/Application Support/feather/player-server/servers/"
                        "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/CraftEngine/resources/barkan_furniture")
MODELS = CE + "/resourcepack/assets/barkan/models/item/furniture/crop"
TEX = CE + "/resourcepack/assets/barkan/textures/furniture/crop"
CROPS_YML = CE + "/configuration/crops.yml"
os.makedirs(MODELS, exist_ok=True)
os.makedirs(TEX, exist_ok=True)


SOIL = "6b4a2a"
SPROUT = "6fae52"
LEAF = "4e8f3a"
STEM = "6f8e43"


def stem(k, x, z, h, mat=STEM, width=0.52):
    """밑동이 보이는 둥근 줄기."""
    k.rounded_box((x - width, 0, z - width), (x + width, h, z + width), mat, bevel=min(0.22, width * 0.4))


def leaf(k, x, z, y0, h, width, mat, angle=0, axis="z"):
    """밑동에서 바깥으로 펼쳐지는 얇은 잎. 회전으로 사각 기둥 느낌을 줄인다."""
    org = [x, y0, z]
    k.box((x - width, y0, z - 0.28), (x + width, y0 + h, z + 0.28), mat,
          rot=(axis, angle, org) if angle else None)


def sprout(k, angle=22.5, mat=None):
    mat = mat or Mat(SPROUT, var=0.85)
    stem(k, 8, 8, 2.3, mat, 0.32)
    leaf(k, 7.7, 8, 1.6, 3.3, 0.7, mat, angle)
    leaf(k, 8.3, 8, 1.7, 3.5, 0.7, mat, -angle)


def fan(k, positions, h, width, mat, axis="z"):
    for x, z, angle in positions:
        leaf(k, x, z, 0.4, h, width, mat, angle, axis)


def fruit(k, x, y, z, size, mat, bevel=None, rot=None):
    """5단 실루엣으로 만든 둥근 열매. 큰 단일 베벨 큐브가 되는 것을 막는다."""
    # y축으로 폭을 5번 바꿔 구형에 가깝게 만든다. 회전은 중심축 기준으로만 적용한다.
    spans = [(0.00, 0.16, 0.54), (0.16, 0.38, 0.82), (0.38, 0.72, 1.00),
             (0.72, 0.90, 0.82), (0.90, 1.00, 0.54)]
    total_h = size * 2.0
    org = [x, y + total_h * 0.5, z]
    for lo, hi, scale in spans:
        f = (x - size * scale, y + total_h * lo, z - size * scale)
        t = (x + size * scale, y + total_h * hi, z + size * scale)
        k.box(f, t, mat, rot=(rot[0], rot[1], org) if rot else None)


def _arc_stalk(k, x, z, total_h, stalk_mat, head_mat, axis, sgn):
    """밀 이삭을 3분절로 연결해 고개가 살짝 바깥으로 향하게 한다."""
    width = 0.42
    segs = [(total_h * 0.50, 0.0), (total_h * 0.30, 22.5 * sgn), (total_h * 0.20, 45.0 * sgn)]
    px, py, pz = float(x), 0.0, float(z)
    for length, angle in segs:
        rad = math.radians(angle)
        k.box((px - width, py, pz - width), (px + width, py + length, pz + width), stalk_mat,
              rot=(axis, angle, [px, py, pz]) if angle else None)
        if axis == "z":
            px -= math.sin(rad) * length
        else:
            pz += math.sin(rad) * length
        py += math.cos(rad) * length
    fruit(k, px, py - 0.55, pz, 1.05, head_mat, bevel=0.28, rot=(axis, 45.0 * sgn, [px, py, pz]))
    k.box((px - 0.55, py + 1.0, pz - 0.55), (px + 0.55, py + 2.0, pz + 0.55), head_mat,
          rot=(axis, 45.0 * sgn, [px, py, pz]))


# ── 각 작물: fn(stage 0~4) ──────────────────────────────────
def wheat(st, k):
    green = Mat("719a49", var=0.85, grain="v")
    gold = Mat("b8943f", var=0.78, grain="v")
    head_green = Mat("9cb45c", var=0.82)
    head_gold = Mat("d8ad43", var=0.88)
    pos = [(4.0, 6.0), (7.0, 9.7), (9.5, 5.6), (12.0, 9.0), (5.8, 4.0), (11.0, 12.0), (13.2, 6.3)]
    if st == 0:
        sprout(k, mat=Mat(SPROUT, var=0.8))
    elif st == 1:
        for i, (x, z) in enumerate(pos[:4]):
            stem(k, x, z, 4.8 + i * 0.35, green, 0.35)
            leaf(k, x, z, 2.2, 3.2, 0.6, green, 22.5 if i % 2 else -22.5)
    elif st == 2:
        for i, (x, z) in enumerate(pos[:5]):
            h = 7.0 + (i % 3) * 0.65
            stem(k, x, z, h, green, 0.38)
            leaf(k, x, z, 3.1, 3.4, 0.62, green, 22.5 if i % 2 else -22.5)
            fruit(k, x, h - 0.6, z, 0.82, head_green, bevel=0.25)
    elif st == 3:
        for i, (x, z) in enumerate(pos[:6]):
            h = 9.2 + (i % 3) * 0.8
            stem(k, x, z, h, gold if i % 2 == 0 else green, 0.4)
            leaf(k, x, z, 3.0, 4.0, 0.65, green, 22.5 if i % 2 else -22.5)
            fruit(k, x, h - 0.5, z, 0.95, head_gold if i % 2 == 0 else head_green, bevel=0.28)
    else:
        for i, (x, z) in enumerate(pos):
            h = 12.7 + (i % 3) * 1.25
            dx, dz = x - 8, z - 8
            if abs(dx) >= abs(dz):
                axis, sgn = "z", 1 if dx < 0 else -1
            else:
                axis, sgn = "x", 1 if dz > 0 else -1
            _arc_stalk(k, x, z, h, gold, head_gold, axis, sgn)


def carrot(st, k):
    leaf_mat = Mat("4f913c", var=0.9, grain="v")
    leaf_hi = Mat("6aa64a", var=0.78)
    orange = Mat("d47a2e", gloss=True)
    orange_hi = Mat("e89a36", gloss=True)
    if st == 0:
        sprout(k, mat=leaf_mat)
    elif st == 1:
        fan(k, [(6.8, 8, 22.5), (8, 8, 0), (9.2, 8, -22.5)], 4.7, 0.55, leaf_mat)
    elif st == 2:
        fan(k, [(5.1, 8, 45), (6.8, 8, 22.5), (8, 8, 0), (9.2, 8, -22.5), (10.9, 8, -45)], 7.0, 0.62, leaf_mat)
        fruit(k, 8, 0.3, 8, 1.5, Mat("a9672b", gloss=True), bevel=0.55)
    elif st == 3:
        fan(k, [(4.8, 8, 45), (6.4, 8, 22.5), (8, 8, 0), (9.6, 8, -22.5), (11.2, 8, -45)], 9.2, 0.7, leaf_mat)
        fruit(k, 6.2, 0.3, 7.3, 1.7, orange, bevel=0.62)
        fruit(k, 9.8, 0.3, 8.8, 1.65, orange_hi, bevel=0.62)
    else:
        fan(k, [(4.4, 8, 45), (5.8, 8, 22.5), (7.2, 8, 0), (8.8, 8, 0), (10.2, 8, -22.5), (11.6, 8, -45)], 11.6, 0.76, leaf_mat)
        leaf(k, 8, 8, 0.5, 10.5, 0.55, leaf_hi, 22.5, axis="x")
        fruit(k, 5.7, 0.25, 7.2, 1.75, orange, bevel=0.7)
        fruit(k, 9.9, 0.25, 8.8, 1.8, orange_hi, bevel=0.7)
        fruit(k, 8, 0.4, 5.3, 1.55, Mat("cb6b2b", gloss=True), bevel=0.62)


def potato(st, k):
    leaf_mat = Mat("477f3c", var=0.92)
    leaf_hi = Mat("639b4a", var=0.84)
    tuber = Mat("ad824b", var=0.88)
    tuber_hi = Mat("c99a5a", var=0.82)
    if st == 0:
        sprout(k, mat=leaf_mat)
    elif st == 1:
        fan(k, [(6.2, 8, 22.5), (8, 8, -22.5), (9.8, 8, 22.5)], 4.6, 0.8, leaf_mat)
    elif st == 2:
        fan(k, [(5.0, 8, 45), (6.7, 8, 22.5), (8.5, 8, -22.5), (10.8, 8, -45)], 6.5, 0.86, leaf_mat)
        fruit(k, 7.2, 0.2, 7.4, 1.2, tuber, bevel=0.45)
    elif st == 3:
        fan(k, [(4.4, 8, 45), (6.1, 8, 22.5), (8, 8, 0), (9.9, 8, -22.5), (11.6, 8, -45)], 8.4, 0.92, leaf_mat)
        fruit(k, 6.0, 0.2, 7.0, 1.45, tuber, bevel=0.55)
        fruit(k, 9.8, 0.2, 8.8, 1.4, tuber_hi, bevel=0.55)
    else:
        fan(k, [(4.0, 8, 45), (5.5, 8, 22.5), (7.2, 8, 0), (8.8, 8, 0), (10.5, 8, -22.5), (12, 8, -45)], 10.1, 0.98, leaf_mat)
        fruit(k, 5.5, 0.15, 7.1, 1.55, tuber, bevel=0.62)
        fruit(k, 9.8, 0.15, 8.7, 1.6, tuber_hi, bevel=0.62)
        fruit(k, 8.0, 0.2, 5.6, 1.35, Mat("9f713f", var=0.88), bevel=0.52)
        leaf(k, 8.0, 8.0, 5.0, 6.0, 0.55, leaf_hi, -22.5, axis="x")


def tomato(st, k):
    vine = Mat("5b7f3d", var=0.86, grain="v")
    leaf_mat = Mat("4f8f3f", var=0.9)
    green_fruit = Mat("8eae49", gloss=True)
    red = Mat("c94335", gloss=True)
    red_hi = Mat("e45a3d", gloss=True)
    if st == 0:
        sprout(k, mat=vine)
    elif st == 1:
        stem(k, 8, 8, 4.2, vine, 0.34)
        fan(k, [(6.2, 8, 22.5), (9.8, 8, -22.5)], 3.8, 0.7, leaf_mat)
    elif st == 2:
        stem(k, 8, 8, 8.0, vine, 0.38)
        fan(k, [(5.4, 8, 45), (6.8, 8, 22.5), (9.2, 8, -22.5), (10.6, 8, -45)], 4.6, 0.72, leaf_mat)
        fruit(k, 6.1, 3.7, 7.3, 1.15, green_fruit, bevel=0.38)
        fruit(k, 9.8, 5.7, 8.8, 1.1, green_fruit, bevel=0.38)
    elif st == 3:
        stem(k, 8, 8, 11.2, vine, 0.42)
        fan(k, [(4.8, 8, 45), (6.2, 8, 22.5), (9.8, 8, -22.5), (11.2, 8, -45)], 5.6, 0.78, leaf_mat)
        for x, y, z, size in [(5.8, 3.5, 7.1, 1.2), (10.2, 5.4, 8.7, 1.18), (6.2, 8.0, 8.6, 1.1), (9.9, 9.0, 7.0, 1.08)]:
            fruit(k, x, y, z, size, green_fruit if y < 7 else red, bevel=0.4)
    else:
        stem(k, 8, 8, 13.5, vine, 0.45)
        fan(k, [(4.4, 8, 45), (5.8, 8, 22.5), (10.2, 8, -22.5), (11.6, 8, -45)], 6.8, 0.84, leaf_mat)
        for x, y, z, size, mat in [(5.6, 3.2, 7.0, 1.35, red), (10.3, 4.8, 8.8, 1.34, red_hi),
                                    (6.2, 8.0, 8.8, 1.28, red), (10.0, 9.5, 6.9, 1.24, red_hi),
                                    (8.0, 12.0, 8.0, 1.15, red)]:
            fruit(k, x, y, z, size, mat, bevel=0.48)


def cabbage(st, k):
    outer = Mat("6d9d5e", var=0.83)
    mid = Mat("83b66c", var=0.82)
    core = Mat("a7d18c", var=0.77)
    if st == 0:
        sprout(k, mat=outer)
    elif st == 1:
        fruit(k, 8, 0.1, 8, 2.2, core, bevel=0.8)
        leaf(k, 6.0, 8, 0.5, 3.4, 1.0, outer, 22.5)
        leaf(k, 10.0, 8, 0.5, 3.4, 1.0, outer, -22.5)
    elif st == 2:
        fruit(k, 8, 0.1, 8, 2.7, mid, bevel=1.0)
        leaf(k, 5.0, 8, 0.5, 4.5, 1.25, outer, 22.5)
        leaf(k, 11.0, 8, 0.5, 4.5, 1.25, outer, -22.5)
        leaf(k, 8, 5.0, 0.5, 4.5, 1.25, outer, -22.5, axis="x")
    elif st == 3:
        fruit(k, 8, 0.15, 8, 3.2, mid, bevel=1.12)
        leaf(k, 4.4, 8, 0.4, 5.3, 1.45, outer, 22.5)
        leaf(k, 11.6, 8, 0.4, 5.3, 1.45, outer, -22.5)
        leaf(k, 8, 4.4, 0.4, 5.3, 1.45, outer, -22.5, axis="x")
        leaf(k, 8, 11.6, 0.4, 5.3, 1.45, outer, 22.5, axis="x")
    else:
        fruit(k, 8, 0.15, 8, 3.9, core, bevel=1.45)
        fruit(k, 8, 1.1, 8, 2.9, mid, bevel=1.05)
        leaf(k, 4.0, 8, 0.35, 6.2, 1.65, outer, 30)
        leaf(k, 12.0, 8, 0.35, 6.2, 1.65, outer, -30)
        leaf(k, 8, 4.0, 0.35, 6.2, 1.65, outer, -30, axis="x")
        leaf(k, 8, 12.0, 0.35, 6.2, 1.65, outer, 30, axis="x")


def mushroom(st, k):
    cap = Mat("8f6746", var=0.86, ao_top=True)
    cap_hi = Mat("b18354", var=0.82, ao_top=True)
    stem_mat = Mat("d4c39b", var=0.72, grain="v", ao_top=True)
    if st == 0:
        stem(k, 8, 8, 2.0, stem_mat, 0.6)
        k.dome(8, 1.5, 8, 4.8, 2.6, cap, layers=3)
    elif st == 1:
        stem(k, 8, 8, 3.1, stem_mat, 0.72)
        k.dome(8, 2.5, 8, 6.3, 3.0, cap_hi, layers=3)
    elif st == 2:
        for x, z, h, w, mat in [(5.5, 8, 3.3, 5.0, cap), (10.4, 8.4, 5.0, 6.5, cap_hi)]:
            stem(k, x, z, h, stem_mat, 0.7)
            k.dome(x, h - 0.5, z, w, 3.0, mat, layers=3)
    elif st == 3:
        for x, z, h, w, mat in [(4.7, 7.7, 3.7, 5.6, cap), (8.5, 8.3, 6.1, 7.6, cap_hi), (12.0, 7.0, 3.2, 4.8, cap)]:
            stem(k, x, z, h, stem_mat, 0.76)
            k.dome(x, h - 0.5, z, w, 3.2, mat, layers=3)
    else:
        for x, z, h, w, mat, rr in [(4.4, 7.5, 4.4, 6.0, cap, ("z", 22.5)),
                                     (8.5, 8.3, 7.4, 8.4, cap_hi, None),
                                     (12.1, 7.0, 4.0, 5.6, cap, ("z", -22.5))]:
            stem(k, x, z, h, stem_mat, 0.82)
            k.dome(x, h - 0.55, z, w, 3.6, mat, layers=3, rot=rr)


def melon(st, k):
    vine = Mat("4f8244", var=0.9, grain="v")
    leaf_mat = Mat("5c9849", var=0.85)
    rind = Mat("78a94f", var=0.72, stripe="245b31", stripe_w=2)
    rind_hi = Mat("93bb59", var=0.68, stripe="2c6c35", stripe_w=2)
    if st == 0:
        k.box((5.5, 0, 8), (10.5, 0.9, 8.8), vine, rot=("y", 22.5))
        sprout(k, angle=-22.5, mat=leaf_mat)
    elif st == 1:
        k.box((3.0, 0, 8), (11.0, 0.9, 8.8), vine, rot=("y", -22.5))
        leaf(k, 10.0, 8, 0.5, 3.4, 0.8, leaf_mat, -22.5)
        leaf(k, 11.8, 7.0, 0.5, 3.0, 0.75, leaf_mat, 22.5)
    elif st == 2:
        k.box((2.7, 0, 8), (8.5, 0.9, 8.8), vine, rot=("y", -22.5))
        leaf(k, 9.0, 8, 0.5, 4.2, 0.9, leaf_mat, -22.5)
        fruit(k, 10.2, 0.25, 8.0, 2.25, Mat("a4bd62", var=0.82, grain="v"), bevel=0.95)
    elif st == 3:
        k.box((2.0, 0, 7.5), (8.0, 0.9, 8.5), vine, rot=("y", -22.5))
        leaf(k, 8.5, 8, 0.5, 4.7, 0.92, leaf_mat, -22.5)
        fruit(k, 10.0, 0.25, 7.6, 3.0, rind_hi, bevel=1.2)
    else:
        k.box((1.4, 0, 7.0), (7.3, 0.95, 8.2), vine, rot=("y", 22.5))
        leaf(k, 7.2, 7.6, 0.5, 5.6, 1.0, leaf_mat, 22.5)
        fruit(k, 10.0, 0.25, 7.3, 3.8, rind, bevel=1.55)
        k.box((9.6, 7.0, 7.0), (10.5, 9.0, 8.0), Mat(SOIL, var=0.65, grain="v"), rot=("z", 22.5))


CROPS = {"wheat": wheat, "carrot": carrot, "potato": potato, "tomato": tomato,
         "cabbage": cabbage, "mushroom": mushroom, "melon": melon}
STAGES = ["sprout", "young", "grown", "tall", "ripe"]


def ensure_yml_items():
    """crops.yml에 신규 young/tall 단계 아이템을 멱등 추가."""
    txt = open(CROPS_YML, encoding="utf-8").read()
    add = []
    for eng in CROPS:
        for stage in ("young", "tall"):
            item_id = f"barkan:cropmodel_{eng}_{stage}"
            if item_id in txt:
                continue
            add.append(f"  {item_id}:\n    material: paper\n    model: barkan:item/furniture/crop/{eng}_{stage}\n")
    if add:
        with open(CROPS_YML, "a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(add))
    return len(add)


def main():
    for crop_index, (eng, fn) in enumerate(CROPS.items()):
        for stage_index, stage in enumerate(STAGES):
            k = Kit(seed=stage_index * 17 + crop_index * 31 + 7)
            fn(stage_index, k)
            ref = f"barkan:furniture/crop/{eng}_{stage}"
            im, model = k.build(ref)
            im.save(f"{TEX}/{eng}_{stage}.png")
            with open(f"{MODELS}/{eng}_{stage}.json", "w", encoding="utf-8") as f:
                json.dump(model, f, indent=1)
    added = ensure_yml_items()
    print(f"OK — 7작물 × 5단계 = 35모델, crops.yml 아이템 +{added}")


if __name__ == "__main__":
    main()
