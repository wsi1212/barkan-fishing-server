#!/usr/bin/env python3
# 특수작물 모델 v3 — 5단계 성장(sprout/young/grown/tall/ripe) + 대형화(밀·당근·토마토) + 수박 4면 줄무늬.
# 계약: barkan:item/furniture/crop/<eng>_<stage>.json (기존 sprout/grown/ripe 이름 보존 → 데이터 마이그레이션 불요,
#       young/tall 신규). crops.yml에 cropmodel_<eng>_{young,tall} 아이템 자동 추가(멱등).
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".claude", "skills", "pixel-art", "scripts"))
from modelkit import Kit, Mat

CE = os.path.expanduser("~/Library/Application Support/feather/player-server/servers/"
                        "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/CraftEngine/resources/barkan_furniture")
MODELS = CE + "/resourcepack/assets/barkan/models/item/furniture/crop"
TEX = CE + "/resourcepack/assets/barkan/textures/furniture/crop"
CROPS_YML = CE + "/configuration/crops.yml"
os.makedirs(TEX, exist_ok=True)

G_SPROUT = "6fae52"; G_LEAF = "4e8f3a"; SOIL = "6b4a2a"

def sprout(k, leaves):
    k.box((7.4, 0, 7.4), (8.6, 3, 8.6), Mat(G_SPROUT, var=0.7, grain="v"))
    for f, t, rr in leaves:
        k.box(f, t, Mat(G_SPROUT, var=0.8), rot=rr)

def _arc_stalk(k, x, z, total_h, stalk_mat, head_mat, axis, sgn):
    """다 자란 밀 줄기 = 고사리식 3분절 아치 + 호를 따라 위로-바깥으로 살짝 끄덕이는 이삭.
    한 각도로 통째 기울이면 '삐딱한 막대'가 됨 — 분절마다 각을 키워야(0→22.5→45) 호가 생긴다.
    ★이삭은 줄기 호를 '이어서' 위로-바깥 방향(45°)으로 뻗는다 = 밀의 가벼운 끄덕임.
     (수직으로 툭 떨구면 벼/보리처럼 보임 — 유저 피드백 2026-07-18: '뭔가 쌀같냐')
    ★단일 축 회전만 가능 → axis로 방향 분배: axis="z"=좌우(±x), axis="x"=앞뒤(±z). 8대를
     중심 기준 바깥 4방향으로 배분해 사방 방사형(평면 부채살 아님).
    체인 끝점: z회전→(x−sinθ·L,cosθ·L) / x회전→(z+sinθ·L,cosθ·L). MC 허용각 {0,22.5,45}만."""
    W = 0.5
    segs = [(total_h * 0.50, 0.0), (total_h * 0.30, 22.5 * sgn), (total_h * 0.20, 45.0 * sgn)]
    px, py, pz = float(x), 0.0, float(z)
    for L, a in segs:
        r = math.radians(a)
        y0 = py - (0.5 if py > 0 else 0)                       # 관절 겹침 = 지터 틈 방지
        k.box((px - W, y0, pz - W), (px + W, py + L, pz + W), stalk_mat,
              rot=(axis, a, [px, py, pz]) if a else None)
        if axis == "z": px -= math.sin(r) * L; py += math.cos(r) * L
        else:           pz += math.sin(r) * L; py += math.cos(r) * L
    a = 45.0 * sgn; hl = total_h * 0.34; hw = 1.25             # 이삭: 호를 이어 위로-바깥 끄덕임(2단 테이퍼)
    k.box((px - hw, py - 0.4, pz - hw), (px + hw, py + hl * 0.62, pz + hw), head_mat, rot=(axis, a, [px, py, pz]))
    k.box((px - hw + 0.4, py + hl * 0.55, pz - hw + 0.4), (px + hw - 0.4, py + hl, pz + hw - 0.4),
          head_mat, rot=(axis, a, [px, py, pz]))          # 끝 테이퍼 = 이삭 꼭지

# ── 각 작물: fn(stage 0~4, kit) ──────────────────────────────
def wheat(st, k):
    stalk = Mat("7aa04e", var=0.8, grain="v"); gold_st = Mat("b8a04e", var=0.7, grain="v")
    head_g = Mat("9ab86a", var=0.7); head_y = Mat("d8b23a", var=0.8)
    POS = [(3.5, 6.5), (6, 9.5), (8.5, 6), (11, 9), (13, 6.5), (5, 4.5), (10, 12), (12.5, 11.5)]
    if st == 0:
        sprout(k, [((6, 2, 7.5), (7.6, 4.5, 8.5), ("z", 22.5)), ((8.4, 2.5, 7.5), (10, 5, 8.5), ("z", -22.5))])
    elif st == 1:   # 어린 줄기 4대
        for x, z in POS[:4]:
            k.box((x-0.5, 0, z-0.5), (x+0.5, 5, z+0.5), stalk)
    elif st == 2:   # 줄기 6대 + 풋이삭
        for i, (x, z) in enumerate(POS[:6]):
            h = 7 + (i % 3)
            k.box((x-0.5, 0, z-0.5), (x+0.5, h, z+0.5), stalk)
            k.box((x-1, h-0.5, z-1), (x+1, h+2, z+1), head_g)
    elif st == 3:   # 빽빽 8대, 노랗게 물들기 시작
        for i, (x, z) in enumerate(POS):
            h = 9 + (i % 3)
            k.box((x-0.5, 0, z-0.5), (x+0.5, h, z+0.5), stalk if i % 2 else gold_st)
            k.box((x-1.1, h-0.6, z-1.1), (x+1.1, h+2.2, z+1.1), head_g if i % 2 else head_y)
    else:           # 성숙 — 크고 빽빽한 황금밭, 사방으로 살짝 끄덕이는 아치(고사리식 3분절)
        for i, (x, z) in enumerate(POS):
            total_h = 13 + (i % 3) * 1.5                        # 13/14.5/16 = 크고 껑충
            dx, dz = x - 8, z - 8                               # 중심 기준 바깥 방향
            if abs(dx) >= abs(dz):
                axis, sgn = "z", (1 if dx < 0 else -1)         # 좌우로 휨(바깥쪽)
            else:
                axis, sgn = "x", (1 if dz > 0 else -1)         # 앞뒤로 휨(바깥쪽)
            _arc_stalk(k, x, z, total_h, gold_st, head_y, axis, sgn)

def carrot(st, k):
    leaf = Mat(G_LEAF, var=0.9)
    if st == 0:
        sprout(k, [((6.2, 2, 7.6), (7.8, 5, 8.4), ("z", 22.5)), ((8.2, 2, 7.6), (9.8, 5.2, 8.4), ("z", -22.5))])
    elif st == 1:   # 잎 3장
        for x, a in [(6, 30), (8, 0), (10, -30)]:
            k.box((x-0.6, 0, 7.5), (x+0.6, 5, 8.5), leaf, rot=("z", a, [x, 0, 8]))
    elif st == 2:   # 부채 5장
        for x, a in [(4.5, 45), (6.5, 22.5), (8.5, 0), (10.5, -22.5), (12, -45)]:
            k.box((x-0.7, 0, 7.4), (x+0.7, 7, 8.6), leaf, rot=("z", a, [x, 0, 8]))
    elif st == 3:   # 큰 부채 + 어깨 살짝
        for x, a in [(4, 45), (6.3, 22.5), (8.5, 0), (10.7, -22.5), (13, -45)]:
            k.box((x-0.8, 0, 7.3), (x+0.8, 9, 8.7), leaf, rot=("z", a, [x, 0, 8]))
        k.rounded_box((6.8, 0, 6.8), (9.4, 1.6, 9.4), Mat("d97a2b", gloss=True), bevel=0.5)
    else:           # 성숙 대형 — 잎 12높이 + 주황 어깨 3개 큼직
        for x, a in [(3.5, 45), (6, 22.5), (8.5, 0), (11, -22.5), (13.5, -45), (7, 30), (10, -30)]:
            k.box((x-0.9, 0, 7.2), (x+0.9, 12, 8.8), leaf, rot=("z", a, [x, 0, 8]))   # ★피벗=잎 밑동(공용피벗은 바닥 밑 스윙)
        for f, t in [((3.4, 0, 5.6), (6.8, 3, 9)), ((9, 0, 6.6), (12.6, 2.8, 10.2)), ((5.8, 0, 9.4), (9.2, 2.6, 12.8))]:
            k.rounded_box(f, t, Mat("d97a2b", gloss=True), bevel=0.7)

def potato(st, k):
    bush = Mat(G_LEAF, var=0.9); bush2 = Mat("3f7a37", var=0.9)
    if st == 0:
        sprout(k, [((6.4, 2.2, 7.5), (8, 4.4, 8.5), ("x", 22.5)), ((8, 2.6, 7.5), (9.6, 4.8, 8.5), ("x", -22.5))])
    elif st == 1:
        k.rounded_box((5, 0, 5.5), (10, 3.2, 10.5), bush)
    elif st == 2:
        k.rounded_box((3.5, 0, 4.5), (9.5, 4.5, 10.5), bush)
        k.rounded_box((8, 0, 6.5), (12.5, 3.8, 11.5), bush2)
    elif st == 3:   # 두둑 + 덤불
        k.box((3, 0, 4), (13, 1.4, 12), Mat(SOIL, var=0.9))
        k.rounded_box((4, 1, 5), (10, 5.5, 11), bush)
        k.rounded_box((8.5, 1, 6.5), (12.8, 4.6, 11.8), bush2)
    else:           # 성숙 — 흰꽃 + 캐낸 감자
        k.box((2.5, 0, 3.5), (13.5, 1.6, 12.5), Mat(SOIL, var=0.9))
        k.rounded_box((3.5, 1, 4.5), (10, 6.5, 11), bush)
        k.rounded_box((8.5, 1, 6), (13.3, 5.4, 12), bush2)
        for f, t in [((5.5, 6.5, 6.5), (7, 7.8, 8)), ((9.5, 5.4, 8.5), (11, 6.7, 10))]:
            k.box(f, t, Mat("eeeae0", var=0.5))
        for f, t in [((11.6, 0, 4), (13.8, 1.8, 6.2)), ((2.2, 0, 8.8), (4.2, 1.6, 10.8))]:
            k.rounded_box(f, t, Mat("c9a86a", var=0.7), bevel=0.5)

def tomato(st, k):
    stick = Mat("8a6a44", var=0.7, grain="v"); vine = Mat(G_LEAF, var=0.9)
    if st == 0:
        k.box((7.6, 0, 7.6), (8.4, 6, 8.4), stick)
        sprout(k, [((6.4, 1.5, 7.5), (8, 3.5, 8.5), ("z", 22.5))])
    elif st == 1:
        k.box((7.6, 0, 7.6), (8.4, 9, 8.4), stick)
        for y, a in [(2, 22.5), (5, -22.5)]:
            k.box((6.2, y, 7.3), (9.8, y+1.8, 8.7), vine, rot=("y", a))
    elif st == 2:
        k.box((7.6, 0, 7.6), (8.4, 12, 8.4), stick)
        for y, a in [(2, 22.5), (5.5, -22.5), (9, 22.5)]:
            k.box((5.8, y, 7.2), (10.2, y+2, 8.8), vine, rot=("y", a))
    elif st == 3:   # 풋토마토(연녹 알)
        k.box((7.6, 0, 7.6), (8.4, 14, 8.4), stick)
        for y, a in [(2.5, 22.5), (6, -22.5), (9.5, 22.5), (12, -22.5)]:
            k.box((5.6, y, 7.1), (10.4, y+2, 8.9), vine, rot=("y", a))
        for f, t in [((5, 3.5, 6.8), (7.2, 5.7, 9)), ((9.2, 7, 7.4), (11.2, 9, 9.4))]:
            k.rounded_box(f, t, Mat("9ab86a", gloss=True), bevel=0.5)
    else:           # 성숙 대형 — 지지대 15 + 빨간 알 5개 큼직
        k.box((7.6, 0, 7.6), (8.4, 15, 8.4), stick)
        for y, a in [(2.5, 22.5), (6, -22.5), (9.5, 22.5), (12.5, -22.5)]:
            k.box((5.4, y, 7,), (10.6, y+2.2, 9), vine, rot=("y", a))
        for f, t in [((4.2, 2.6, 6.2), (7.4, 5.8, 9.4)), ((8.8, 5.8, 7), (12, 9, 10.2)),
                     ((4.6, 8.4, 6.6), (7.4, 11.2, 9.4)), ((8.8, 11, 7.2), (11.4, 13.6, 9.8)),
                     ((6, 13, 6.8), (8.2, 15.2, 9))]:
            k.rounded_box(f, t, Mat("d1372c", gloss=True), bevel=0.6)

def cabbage(st, k):
    outer = Mat("7fae6e", var=0.8); core = Mat("9cc48a", var=0.7)
    if st == 0:
        sprout(k, [((5.8, 1.5, 7.4), (7.9, 3.8, 8.6), ("z", 30)), ((8.1, 1.5, 7.4), (10.2, 3.8, 8.6), ("z", -30))])
    elif st == 1:
        k.rounded_box((5.5, 0, 5.5), (10.5, 3, 10.5), core, bevel=0.8)
    elif st == 2:
        for f, t, rr in [((3.5, 0, 6), (7, 4, 10), ("z", 22.5)), ((9, 0, 6), (12.5, 4, 10), ("z", -22.5))]:
            k.box(f, t, outer, rot=(rr[0], rr[1], [(f[0]+t[0])/2, 0, (f[2]+t[2])/2]))
        k.rounded_box((5.5, 0, 5.5), (10.5, 4, 10.5), core, bevel=1)
    elif st == 3:
        for f, t, rr in [((2.8, 0, 5.5), (7, 5, 10.5), ("z", 22.5)), ((9, 0, 5.5), (13.2, 5, 10.5), ("z", -22.5)),
                         ((5.5, 0, 2.8), (10.5, 5, 7), ("x", -22.5)), ((5.5, 0, 9), (10.5, 5, 13.2), ("x", 22.5))]:
            k.box(f, t, outer, rot=(rr[0], rr[1], [(f[0]+t[0])/2, 0, (f[2]+t[2])/2]))
        k.rounded_box((5, 0, 5), (11, 5.5, 11), core, bevel=1.2)
    else:
        for f, t, rr in [((2.5, 0, 5.5), (6.5, 5.5, 10.5), ("z", 30)), ((9.5, 0, 5.5), (13.5, 5.5, 10.5), ("z", -30)),
                         ((5.5, 0, 2.5), (10.5, 5.5, 6.5), ("x", -30)), ((5.5, 0, 9.5), (10.5, 5.5, 13.5), ("x", 30))]:
            k.box(f, t, outer, rot=(rr[0], rr[1], [(f[0]+t[0])/2, 0, (f[2]+t[2])/2]))
        k.rounded_box((4.5, 0, 4.5), (11.5, 7.5, 11.5), core, bevel=1.4)

def mushroom(st, k):
    cap = Mat("9a6f46", var=0.8); stem = Mat("d9caa2", var=0.7, grain="v", ao_top=True)
    if st == 0:
        k.box((7, 0, 7), (9, 2.5, 9), stem)
        k.dome(8, 2, 8, 5, 2.8, cap, layers=2)
    elif st == 1:
        k.box((6.8, 0, 6.8), (9.2, 3.5, 9.2), stem)
        k.dome(8, 3, 8, 6.5, 3, cap, layers=2)
    elif st == 2:
        for x, z, h, w in [(5.5, 7, 3.5, 6), (10, 8.5, 5, 7)]:
            k.box((x-1, 0, z-1), (x+1, h, z+1), stem)
            k.dome(x, h-0.5, z, w, 3.2, cap)
    elif st == 3:
        for x, z, h, w in [(4.5, 7.5, 4, 6), (8.5, 8.5, 6.5, 7.5), (12, 6.5, 3, 5)]:
            k.box((x-1, 0, z-1), (x+1, h, z+1), stem)
            k.dome(x, h-0.5, z, w, 3.4, cap)
    else:
        for x, z, h, w, rr in [(4.5, 7.5, 4.5, 6.5, ("z", 22.5)), (8.5, 8.5, 7.5, 8.5, None), (12, 6.5, 4, 6, ("z", -22.5))]:
            k.box((x-1.1, 0, z-1.1), (x+1.1, h, z+1.1), stem)
            if rr: k.dome(x, h-0.5, z, w, 3.8, cap, rot=rr)
            else: k.dome(x, h-0.5, z, w, 3.8, cap)

def melon(st, k):
    vine = Mat("5c8a4a", var=0.9)
    striped = lambda: Mat("7fae52", var=0.6, grain="v", stripe="1e4020", stripe_w=2)   # 연녹 바탕 + 흑녹 줄(4면+윗면)
    if st == 0:
        k.box((6, 0, 7.5), (10, 1.2, 8.5), vine, rot=("y", 22.5))
        sprout(k, [((8.5, 1, 7.5), (10.3, 3.4, 8.5), ("z", -22.5))])
    elif st == 1:   # 덩굴 뻗음
        k.box((3.5, 0, 7.4), (9, 1.2, 8.6), vine, rot=("y", -22.5))
        k.box((7.5, 0, 6.4), (12.5, 1.2, 7.6), vine, rot=("y", 22.5))
        sprout(k, [((10.5, 1, 6.6), (12.2, 3.2, 7.6), ("z", -22.5))])
    elif st == 2:   # 어린 멜론(무늬 없음, 연녹)
        k.box((3.5, 0, 7.4), (8, 1.2, 8.6), vine, rot=("y", -22.5))
        k.rounded_box((7.5, 0, 6.5), (12.5, 4.5, 11.5), Mat("b8c86a", var=0.9, grain="v"), bevel=0.9)
    elif st == 3:   # 중멜론 — 줄무늬 시작
        k.box((2.8, 0, 7), (7.5, 1.2, 8.2), vine, rot=("y", -22.5))
        k.rounded_box((6, 0, 5.2), (13, 6.5, 12.2), striped(), bevel=1.2)
    else:           # 성숙 — 큰 수박, 4면+윗면 줄무늬 + 꼭지 덩굴
        k.box((2.2, 0, 6.4), (6.5, 1.2, 7.6), vine, rot=("y", 22.5))
        k.rounded_box((4.5, 0, 4), (14, 9.5, 13.5), striped(), bevel=1.6)
        k.box((8.6, 9.5, 8), (9.6, 11.2, 9), Mat("6b4a2a", var=0.7, grain="v"), rot=("z", 22.5))

CROPS = {"wheat": wheat, "carrot": carrot, "potato": potato, "tomato": tomato,
         "cabbage": cabbage, "mushroom": mushroom, "melon": melon}
STAGES = ["sprout", "young", "grown", "tall", "ripe"]   # ★기존 3이름 보존 + young/tall 신규

def ensure_yml_items():
    """crops.yml에 cropmodel_<eng>_{young,tall} 아이템 정의 멱등 추가."""
    txt = open(CROPS_YML, encoding="utf-8").read()
    add = []
    for eng in CROPS:
        for stg in ("young", "tall"):
            iid = f"barkan:cropmodel_{eng}_{stg}"
            if iid in txt: continue
            add.append(f"  {iid}:\n    material: paper\n    model: barkan:item/furniture/crop/{eng}_{stg}\n")
    if add:
        # items: 섹션 끝(파일 끝)에 덧붙임 — crops.yml은 items 트리 하나로 구성돼 있음
        open(CROPS_YML, "a", encoding="utf-8").write("\n" + "\n".join(add))
    return len(add)

def main():
    for eng, fn in CROPS.items():
        for si, stage in enumerate(STAGES):
            k = Kit(seed=si * 7 + hash(eng) % 97)
            fn(si, k)
            ref = f"barkan:furniture/crop/{eng}_{stage}"
            im, model = k.build(ref)
            im.save(f"{TEX}/{eng}_{stage}.png")
            json.dump(model, open(f"{MODELS}/{eng}_{stage}.json", "w"), indent=1)
    added = ensure_yml_items()
    print(f"OK — 7작물 × 5단계 = 35모델, crops.yml 아이템 +{added}")

if __name__ == "__main__":
    main()
