#!/usr/bin/env python3
"""특수작물 성장 모델 v5 — 실제 월드용 3D ItemDisplay 실루엣.

7종 × 5단계(sprout/young/grown/tall/ripe)의 CraftEngine 모델을 생성한다.
이번 버전은 아이콘용 2D 그림을 재사용하지 않고, 작물마다 줄기·잎·열매의
지면 접촉과 단계별 실루엣을 별도 3D 지오메트리로 설계한다.
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
    """지면에 끊김 없이 닿는 둥근 줄기."""
    k.rounded_box((x - width, 0, z - width), (x + width, h, z + width), mat,
                  bevel=min(0.22, width * 0.38))


def leaf(k, x, z, y0, h, width, mat, angle=0, axis="z", depth=0.5):
    """종잇장 대신 두께 있는 잎 칼날. 회전 피벗은 밑동이라 공중에 뜨지 않는다."""
    org = [x, y0, z]
    k.box((x - width, y0, z - depth), (x + width, y0 + h, z + depth), mat,
          rot=(axis, angle, org) if angle else None)


def sprout(k, mat=None, spread=0.72):
    """모든 작물 공통 새싹. 과장된 V자 판 대신 짧은 줄기+작은 잎 2장."""
    mat = mat or Mat(SPROUT, var=0.82)
    stem(k, 8, 8, 1.9, mat, 0.30)
    leaf(k, 8 - spread, 8, 1.25, 2.8, 0.55, mat, 22.5, depth=0.36)
    leaf(k, 8 + spread, 8, 1.25, 2.8, 0.55, mat, -22.5, depth=0.36)


def fan(k, points, h, width, mat, depth=0.5, axis="z"):
    for x, z, angle in points:
        leaf(k, x, z, 0.25, h, width, mat, angle, axis=axis, depth=depth)


def branch(k, x, z, y, length, mat, angle=0, depth=0.46):
    """토마토처럼 옆으로 뻗는 가지. 세로 잎판과 분리된 수평 3D 가지."""
    k.box((x - length, y - 0.32, z - depth), (x + length, y + 0.32, z + depth), mat,
          rot=("y", angle, [x, y, z]) if angle else None)


def bulb(k, x, y, z, width, height, mat, rot=None):
    """작은 열매/감자용 3단 구형 실루엣. 절대 베벨값을 쓰지 않아 판처럼 찢어지지 않는다."""
    # 층 사이를 살짝 겹쳐 수평 틈을 없애고, 폭은 중앙에서만 최대로 유지한다.
    layers = [(0.00, 0.29, 0.62), (0.25, 0.80, 1.00), (0.76, 1.00, 0.64)]
    org = [x, y + height * 0.5, z]
    for lo, hi, scale in layers:
        f = (x - width * scale * 0.5, y + height * lo, z - width * scale * 0.5)
        t = (x + width * scale * 0.5, y + height * hi, z + width * scale * 0.5)
        k.box(f, t, mat, rot=(rot[0], rot[1], org) if rot else None)


def carrot_root(k, x, z, height, top_width, mat):
    """당근 뿌리 — 아래가 좁고 잎 밑 어깨가 넓은 3D 테이퍼."""
    layers = [(0.00, 0.22, 0.30), (0.20, 0.58, 0.62), (0.55, 1.00, 1.00)]
    for lo, hi, scale in layers:
        w = top_width * scale
        y0, y1 = height * lo, height * hi
        # 날카로운 판 세 개 대신 작은 베벨을 겹쳐, 당근 어깨가 둥글게 보이게 한다.
        k.rounded_box((x - w * 0.5, y0, z - w * 0.5),
                      (x + w * 0.5, y1, z + w * 0.5), mat,
                      bevel=min(0.42, w * 0.28, max(0.08, (y1 - y0) * 0.36)))


def potato_tuber(k, x, y, z, width, height, mat):
    """흙 위로 드러난 감자. 둥근 단일 덩어리라 납작한 막대처럼 보이지 않는다."""
    depth = width * 0.82
    k.rounded_box((x - width * 0.5, y, z - depth * 0.5),
                  (x + width * 0.5, y + height, z + depth * 0.5), mat,
                  bevel=min(0.78, width * 0.28, height * 0.36))


def _arc_stalk(k, x, z, total_h, stalk_mat, head_mat, axis, sgn):
    """밀 성숙 줄기 — 기존에 가장 읽혔던 3분절 바깥쪽 아치 유지."""
    width = 0.46
    segs = [(total_h * 0.50, 0.0), (total_h * 0.30, 22.5 * sgn), (total_h * 0.20, 45.0 * sgn)]
    px, py, pz = float(x), 0.0, float(z)
    for length, angle in segs:
        rad = math.radians(angle)
        k.box((px - width, py - 0.20, pz - width), (px + width, py + length, pz + width), stalk_mat,
              rot=(axis, angle, [px, py, pz]) if angle else None)
        if axis == "z":
            px -= math.sin(rad) * length
        else:
            pz += math.sin(rad) * length
        py += math.cos(rad) * length
    # 이삭은 긴 큐브 하나가 아니라 굵은 중심 + 좌우 낟알 3쌍으로 읽히게 한다.
    for i, side in enumerate((-1, 1, -1, 1, -1, 1)):
        yy = py + 0.1 + i * 0.55
        xx = px + side * (0.72 if i < 4 else 0.48)
        zz = pz + (side * 0.28 if axis == "x" else 0)
        k.box((xx - 0.42, yy, zz - 0.42), (xx + 0.42, yy + 0.72, zz + 0.42), head_mat,
              rot=(axis, 45.0 * sgn, [px, py, pz]))


def wheat(st, k):
    stalk = Mat("7aa04e", var=0.82, grain="v")
    gold_st = Mat("b8a04e", var=0.76, grain="v")
    head_g = Mat("9ab86a", var=0.78)
    head_y = Mat("d8b23a", var=0.86)
    pos = [(3.5, 6.5), (6, 9.5), (8.5, 6), (11, 9), (13, 6.5), (5, 4.5), (10, 12), (12.5, 11.5)]
    if st == 0:
        sprout(k, Mat(SPROUT, var=0.8), 0.6)
    elif st == 1:
        for i, (x, z) in enumerate(pos[:4]):
            stem(k, x, z, 4.8 + i * 0.3, stalk, 0.36)
            leaf(k, x, z, 2.0, 2.8, 0.52, stalk, 22.5 if i % 2 else -22.5, depth=0.4)
    elif st == 2:
        for i, (x, z) in enumerate(pos[:6]):
            h = 7 + (i % 3)
            stem(k, x, z, h, stalk, 0.4)
            leaf(k, x, z, 3.0, 3.0, 0.55, stalk, 22.5 if i % 2 else -22.5, depth=0.42)
            k.dome(x, h - 0.45, z, 2.1, 2.0, head_g, layers=2)
    elif st == 3:
        for i, (x, z) in enumerate(pos):
            h = 9 + (i % 3)
            stem(k, x, z, h, gold_st if i % 2 == 0 else stalk, 0.42)
            leaf(k, x, z, 3.0, 3.6, 0.58, stalk, 22.5 if i % 2 else -22.5, depth=0.44)
            k.dome(x, h - 0.5, z, 2.4, 2.2, head_y if i % 2 == 0 else head_g, layers=2)
    else:
        for i, (x, z) in enumerate(pos):
            h = 13 + (i % 3) * 1.25
            dx, dz = x - 8, z - 8
            if abs(dx) >= abs(dz):
                axis, sgn = "z", 1 if dx < 0 else -1
            else:
                axis, sgn = "x", 1 if dz > 0 else -1
            _arc_stalk(k, x, z, h, gold_st, head_y, axis, sgn)


def carrot(st, k):
    leaf_mat = Mat("4f913c", var=0.88, grain="v")
    leaf_hi = Mat("6aa64a", var=0.82)
    orange = Mat("d97a2b", gloss=True)
    orange_hi = Mat("e79a35", gloss=True)
    if st == 0:
        sprout(k, leaf_mat, 0.58)
    elif st == 1:
        fan(k, [(6.8, 8, 22.5), (8, 8, 0), (9.2, 8, -22.5)], 4.2, 0.55, leaf_mat, 0.42)
    elif st == 2:
        fan(k, [(5.2, 8, 45), (6.8, 8, 22.5), (8, 8, 0), (9.2, 8, -22.5), (10.8, 8, -45)], 6.4, 0.66, leaf_mat, 0.48)
        carrot_root(k, 8, 7.0, 2.7, 2.6, Mat("b86a2a", gloss=True))
    elif st == 3:
        fan(k, [(4.8, 8, 45), (6.4, 8, 22.5), (8, 8, 0), (9.6, 8, -22.5), (11.2, 8, -45)], 8.0, 0.72, leaf_mat, 0.52)
        carrot_root(k, 6.0, 4.8, 3.3, 3.0, orange)
        carrot_root(k, 10.0, 6.4, 3.2, 2.9, orange_hi)
    else:
        fan(k, [(4.3, 8, 45), (5.7, 8, 22.5), (7.2, 8, 0), (8.8, 8, 0), (10.3, 8, -22.5), (11.7, 8, -45)], 9.2, 0.78, leaf_mat, 0.56)
        leaf(k, 8, 8, 0.2, 8.5, 0.54, leaf_hi, 22.5, axis="x", depth=0.42)
        carrot_root(k, 5.4, 3.9, 4.0, 3.3, orange)
        carrot_root(k, 10.5, 5.7, 4.0, 3.4, orange_hi)
        carrot_root(k, 8.0, 4.4, 3.6, 3.0, Mat("c96c2b", gloss=True))


def potato(st, k):
    bush = Mat("4f873f", var=0.9)
    bush2 = Mat("3f7438", var=0.86)
    soil = Mat(SOIL, var=0.86)
    tuber = Mat("c49a5c", var=0.8)
    tuber_dark = Mat("a97943", var=0.82)
    if st == 0:
        sprout(k, bush, 0.62)
    elif st == 1:
        fan(k, [(6.2, 8, 22.5), (8, 8, -22.5), (9.8, 8, 22.5)], 4.0, 0.8, bush, 0.56)
    elif st == 2:
        fan(k, [(5.0, 8, 45), (6.6, 8, 22.5), (8.4, 8, -22.5), (10.8, 8, -45)], 5.8, 0.9, bush, 0.6)
        bulb(k, 8, 0.1, 8, 5.2, 2.8, Mat("679348", var=0.82))
    elif st == 3:
        k.box((3.0, 0, 4.2), (13.0, 1.35, 11.8), soil)
        fan(k, [(4.8, 8, 45), (6.5, 8, 22.5), (8.0, 8, 0), (9.7, 8, -22.5), (11.3, 8, -45)], 7.1, 0.94, bush, 0.64)
        bulb(k, 7.0, 1.0, 7.0, 5.8, 3.6, bush2)
        bulb(k, 10.1, 1.0, 9.0, 4.8, 3.0, bush)
    else:
        k.box((2.4, 0, 3.5), (13.6, 1.45, 12.5), soil)
        fan(k, [(4.2, 8, 45), (5.7, 8, 22.5), (7.3, 8, 0), (8.8, 8, 0), (10.5, 8, -22.5), (12.0, 8, -45)], 8.2, 1.0, bush, 0.68)
        bulb(k, 6.7, 1.0, 6.8, 6.2, 4.0, bush2)
        bulb(k, 10.2, 1.0, 9.0, 5.6, 3.7, bush)
        # 수확 직전 흙 위로 일부 드러난 감자 — 앞줄을 따로 잡아 잎에 묻히지 않는다.
        potato_tuber(k, 4.5, 1.28, 1.7, 3.0, 2.15, tuber_dark)
        potato_tuber(k, 8.0, 1.18, 0.9, 2.65, 1.95, tuber)
        potato_tuber(k, 11.5, 1.30, 2.25, 3.1, 2.2, tuber)
        k.box((7.4, 6.4, 7.0), (8.6, 7.4, 8.2), Mat("ece6d5", var=0.55))


def tomato(st, k):
    stake = Mat("8a6a44", var=0.72, grain="v")
    vine = Mat("4f893d", var=0.9)
    green_fruit = Mat("8fae4c", gloss=True)
    red = Mat("d1372c", gloss=True)
    red_hi = Mat("e04a34", gloss=True)
    if st == 0:
        stem(k, 8, 8, 2.8, stake, 0.30)
        sprout(k, vine, 0.58)
    elif st == 1:
        stem(k, 8, 8, 6.5, stake, 0.34)
        branch(k, 8, 8, 2.4, 2.4, vine, 22.5)
        branch(k, 8, 8, 5.0, 2.5, vine, -22.5)
    elif st == 2:
        stem(k, 8, 8, 9.2, stake, 0.38)
        branch(k, 8, 8, 2.3, 2.7, vine, 22.5)
        branch(k, 8, 8, 5.2, 3.0, vine, -22.5)
        branch(k, 8, 8, 8.0, 2.7, vine, 22.5)
        bulb(k, 6.2, 3.1, 7.1, 2.2, 2.2, green_fruit)
    elif st == 3:
        stem(k, 8, 8, 11.4, stake, 0.4)
        branch(k, 8, 8, 2.3, 3.0, vine, 22.5)
        branch(k, 8, 8, 5.2, 3.3, vine, -22.5)
        branch(k, 8, 8, 8.1, 3.0, vine, 22.5)
        branch(k, 8, 8, 10.3, 2.6, vine, -22.5)
        bulb(k, 6.0, 3.2, 7.0, 2.5, 2.5, green_fruit)
        bulb(k, 10.1, 5.8, 8.8, 2.5, 2.5, green_fruit)
        bulb(k, 6.5, 7.8, 8.8, 2.2, 2.3, red)
    else:
        stem(k, 8, 8, 12.8, stake, 0.42)
        branch(k, 8, 8, 2.3, 3.2, vine, 22.5)
        branch(k, 8, 8, 5.2, 3.6, vine, -22.5)
        branch(k, 8, 8, 8.2, 3.3, vine, 22.5)
        branch(k, 8, 8, 10.6, 2.9, vine, -22.5)
        for x, y, z, w, h, mat in [(5.5, 2.8, 7.0, 2.8, 2.7, red), (10.4, 4.8, 8.8, 2.8, 2.8, red_hi),
                                    (6.3, 7.8, 8.9, 2.6, 2.6, red), (10.0, 9.5, 6.9, 2.5, 2.5, red_hi),
                                    (8.0, 11.6, 8.0, 2.3, 2.3, red)]:
            bulb(k, x, y, z, w, h, mat)
            k.box((x - 0.25, y + h, z - 0.25), (x + 0.25, y + h + 0.45, z + 0.25), vine)


def cabbage(st, k):
    outer = Mat("6d9d5e", var=0.84)
    mid = Mat("83b66c", var=0.82)
    core = Mat("a7d18c", var=0.78)
    if st == 0:
        sprout(k, outer, 0.58)
    elif st == 1:
        k.rounded_box((6.0, 0.05, 6.0), (10.0, 3.6, 10.0), core, bevel=0.72)
        leaf(k, 6.2, 8, 0.25, 2.7, 0.8, outer, 22.5, depth=0.58)
        leaf(k, 9.8, 8, 0.25, 2.7, 0.8, outer, -22.5, depth=0.58)
    elif st == 2:
        k.rounded_box((5.2, 0.05, 5.2), (10.8, 4.8, 10.8), mid, bevel=0.95)
        leaf(k, 5.2, 8, 0.2, 4.0, 1.1, outer, 22.5, depth=0.65)
        leaf(k, 10.8, 8, 0.2, 4.0, 1.1, outer, -22.5, depth=0.65)
    elif st == 3:
        k.rounded_box((4.6, 0.05, 4.6), (11.4, 5.8, 11.4), mid, bevel=1.18)
        leaf(k, 4.4, 8, 0.2, 5.0, 1.35, outer, 22.5, depth=0.72)
        leaf(k, 11.6, 8, 0.2, 5.0, 1.35, outer, -22.5, depth=0.72)
        leaf(k, 8, 4.4, 0.2, 4.7, 1.25, outer, -22.5, axis="x", depth=0.72)
        leaf(k, 8, 11.6, 0.2, 4.7, 1.25, outer, 22.5, axis="x", depth=0.72)
    else:
        # 중앙을 비우지 않는다. 단단한 구형 머리 + 바깥 잎 6장으로 양배추를 읽게 한다.
        k.rounded_box((4.0, 0.05, 4.0), (12.0, 7.0, 12.0), core, bevel=1.58)
        k.rounded_box((5.0, 0.8, 5.0), (11.0, 6.2, 11.0), mid, bevel=1.18)
        leaf(k, 3.8, 8, 0.15, 5.8, 1.5, outer, 30, depth=0.78)
        leaf(k, 12.2, 8, 0.15, 5.8, 1.5, outer, -30, depth=0.78)
        leaf(k, 8, 3.8, 0.15, 5.4, 1.4, outer, -30, axis="x", depth=0.78)
        leaf(k, 8, 12.2, 0.15, 5.4, 1.4, outer, 30, axis="x", depth=0.78)


def mushroom(st, k):
    cap = Mat("916846", var=0.84, ao_top=True)
    cap_hi = Mat("b18354", var=0.8, ao_top=True)
    stem_mat = Mat("d4c39b", var=0.72, grain="v", ao_top=True)
    if st == 0:
        stem(k, 8, 8, 2.0, stem_mat, 0.58)
        k.dome(8, 1.6, 8, 4.8, 2.5, cap, layers=3)
    elif st == 1:
        stem(k, 8, 8, 3.0, stem_mat, 0.68)
        k.dome(8, 2.4, 8, 6.2, 3.0, cap_hi, layers=3)
    elif st == 2:
        for x, z, h, w, mat in [(5.5, 8, 3.3, 5.4, cap), (10.4, 8.5, 4.8, 6.6, cap_hi)]:
            stem(k, x, z, h, stem_mat, 0.68)
            k.dome(x, h - 0.5, z, w, 3.0, mat, layers=3)
    elif st == 3:
        for x, z, h, w, mat in [(4.7, 7.7, 3.6, 5.6, cap), (8.5, 8.3, 6.0, 7.4, cap_hi), (12.0, 7.0, 3.1, 4.8, cap)]:
            stem(k, x, z, h, stem_mat, 0.74)
            k.dome(x, h - 0.5, z, w, 3.2, mat, layers=3)
    else:
        for x, z, h, w, mat, rr in [(4.5, 7.5, 4.3, 6.0, cap, ("z", 22.5)),
                                     (8.5, 8.3, 7.2, 8.2, cap_hi, None),
                                     (12.1, 7.0, 3.9, 5.6, cap, ("z", -22.5))]:
            stem(k, x, z, h, stem_mat, 0.8)
            k.dome(x, h - 0.55, z, w, 3.6, mat, layers=3, rot=rr)


def melon(st, k):
    vine = Mat("4f8244", var=0.88, grain="v")
    leaf_mat = Mat("5c9849", var=0.84)
    rind = Mat("78a94f", var=0.72, stripe="245b31", stripe_w=2)
    rind_hi = Mat("93bb59", var=0.7, stripe="2c6c35", stripe_w=2)
    if st == 0:
        k.box((5.5, 0, 8), (9.8, 0.8, 8.8), vine, rot=("y", 22.5))
        sprout(k, leaf_mat, 0.6)
    elif st == 1:
        k.box((3.0, 0, 8), (10.5, 0.8, 8.8), vine, rot=("y", -22.5))
        leaf(k, 10.0, 8, 0.25, 3.0, 0.75, leaf_mat, -22.5, depth=0.55)
    elif st == 2:
        k.box((2.5, 0, 8), (8.0, 0.85, 8.8), vine, rot=("y", -22.5))
        leaf(k, 6.8, 8.0, 0.25, 3.2, 0.72, leaf_mat, 22.5, depth=0.58)
        leaf(k, 8.6, 7.4, 0.25, 3.8, 0.78, leaf_mat, -22.5, depth=0.58)
        bulb(k, 10.6, 0.2, 5.9, 3.8, 3.6, Mat("a4bd62", var=0.82))
    elif st == 3:
        k.box((2.0, 0, 7.6), (7.7, 0.9, 8.6), vine, rot=("y", -22.5))
        leaf(k, 5.8, 8.0, 0.25, 3.8, 0.82, leaf_mat, 22.5, depth=0.62)
        leaf(k, 7.5, 7.0, 0.25, 4.5, 0.9, leaf_mat, -22.5, depth=0.62)
        leaf(k, 8.9, 8.3, 0.25, 3.4, 0.76, leaf_mat, 45, axis="x", depth=0.6)
        # 미성숙 열매는 낮은 3단 구형으로 두어 잎 사이에 묻힌 작은 멜론처럼 보이게 한다.
        bulb(k, 10.4, 0.25, 5.7, 5.2, 4.7, rind_hi)
    else:
        k.box((1.4, 0, 7.0), (7.0, 0.95, 8.2), vine, rot=("y", 22.5))
        leaf(k, 4.8, 8.0, 0.25, 4.2, 0.9, leaf_mat, 22.5, depth=0.68)
        leaf(k, 6.7, 7.0, 0.25, 5.0, 1.0, leaf_mat, -22.5, depth=0.7)
        leaf(k, 8.0, 8.6, 0.25, 3.6, 0.82, leaf_mat, 45, axis="x", depth=0.65)
        # 성숙 멜론은 잎보다 낮은 앞쪽에 둥근 줄무늬 열매 하나가 주인공이어야 한다.
        # 성숙 멜론은 돔형 3단 실루엣을 사용해 거대한 정육면체를 피한다.
        k.dome(10.4, 0.25, 5.6, 6.0, 5.4, rind, layers=3)
        k.box((10.0, 5.55, 5.2), (10.8, 6.8, 6.0), Mat(SOIL, var=0.65, grain="v"), rot=("z", 22.5))


CROPS = {"wheat": wheat, "carrot": carrot, "potato": potato, "tomato": tomato,
         "cabbage": cabbage, "mushroom": mushroom, "melon": melon}
STAGES = ["sprout", "young", "grown", "tall", "ripe"]


def ensure_yml_items():
    """crops.yml에 young/tall 단계 아이템 정의를 멱등 추가."""
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
