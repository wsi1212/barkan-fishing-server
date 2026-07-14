#!/usr/bin/env python3
"""아우라 셀(aura_straight.json) → 세그먼트별 RP 모델 bake + 인라인 검증 + 리그 갱신.

세그 배정/피벗/스케일은 convert_straight.py와 동일 규약(z밴드, imugi_s_rig.json의 pivot·k 재사용)
— 아우라 디스플레이가 본체 세그와 같은 변환을 공유하므로 체인 애니를 그대로 따라간다.
색: green=라임 유리 / red=빨간 유리 / purple=투톤(초록 유래→마젠타, 빨강 유래→퍼플).
출력: models/items barkan:imugi_s/aura_XX_<color> + imugi_s_rig.json에 aura_models 추가.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
RP = os.path.expanduser("~/development/barkan-resourcepack")
MODEL_DIR = os.path.join(RP, "assets/barkan/models/imugi_s")
ITEM_DIR = os.path.join(RP, "assets/barkan/items/imugi_s")

aura = json.load(open(os.path.join(HERE, "aura_straight.json")))
rig = json.load(open(os.path.join(HERE, "imugi_s_rig.json")))
body = {(b["x"], b["y"], b["z"]) for b in json.load(open(os.path.join(HERE, "straight_imugi_blocks.json")))}

# convert_straight.py와 동일한 z밴드 세그 배정 재현
body_zs = sorted({c[2] for c in body})
# 머리/꼬리 verbatim 구간: rig 세그 0=꼬리, last=머리 — 밴드 경계는 몸통 z범위에서만.
# convert_straight: 몸통 z −99(남)..−130(북), 밴드3. 리그 피벗 z들로 세그 중심 복원해 최근접 배정이 가장 견고.
seg_pivots = [(s["seg"], s["pivot"]) for s in rig["segments"]]

def seg_of_z(z):
    return min(seg_pivots, key=lambda sp: abs(sp[1][2] - (z + 0.5)))[0]

TEX = {"green": "minecraft:block/lime_stained_glass",
       "red": "minecraft:block/red_stained_glass",
       "purple": "minecraft:block/purple_stained_glass",
       "magenta": "minecraft:block/magenta_stained_glass"}
DIRS = {"down": (0, -1, 0), "up": (0, 1, 0), "north": (0, 0, -1),
        "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}
def face_uv(face, fr, to):
    x0, y0, z0 = fr; x1, y1, z1 = to
    if face in ("up", "down"): return [x0, z0, x1, z1]
    if face in ("north", "south"): return [x0, 16 - y1, x1, 16 - y0]
    return [z0, 16 - y1, z1, 16 - y0]

green_set = {tuple(c) for c in aura["green"]}
colors = {
    "green": {tuple(c): "green" for c in aura["green"]},
    "red": {tuple(c): "red" for c in aura["red"]},
    # 보라(3페, 자체 디자인): 초록 유래 다발=마젠타, 빨강 유래=퍼플 투톤
    "purple": {tuple(c): ("magenta" if tuple(c) in green_set else "purple") for c in aura["purple"]},
}

aura_models = {}
fail = 0
for cname, cellmap in colors.items():
    by_seg = {}
    for c in cellmap:
        by_seg.setdefault(seg_of_z(c[2]), []).append(c)
    aura_models[cname] = {}
    for segIdx, cs in sorted(by_seg.items()):
        seg = next(s for s in rig["segments"] if s["seg"] == segIdx)
        pivot = seg["pivot"]
        # 아우라 자체 k — 불꽃이 몸 위로 솟아 세그 k 범위를 넘으므로 (별도 디스플레이라 독립 스케일 가능)
        lo = [min(c[a] for c in cs) - pivot[a] for a in range(3)]
        hi = [max(c[a] + 1 for c in cs) - pivot[a] for a in range(3)]
        k = max(seg["scale"], max(max(-l, h) * 16 / 15.5 for l, h in zip(lo, hi)))
        used, elements, exp = {}, [], []
        cset = set(cs)
        for c in cs:
            tex = TEX[cellmap[c]]
            var = tex.split("/")[-1]
            used[var] = tex
            faces = {}
            for fn, d in DIRS.items():
                if (c[0] + d[0], c[1] + d[1], c[2] + d[2]) in cset:
                    continue  # 같은 아우라끼리 맞닿은 면 컬링
                faces[fn] = {"texture": "#" + var, "uv": face_uv(fn, (0, 0, 0), (16, 16, 16))}
            e_from = [round(8 + (c[a] - pivot[a]) * 16 / k, 4) for a in range(3)]
            e_to = [round(8 + (c[a] - pivot[a]) * 16 / k + 16 / k, 4) for a in range(3)]
            assert all(-16 <= v <= 32 for v in e_from + e_to), f"aura {cname} seg{segIdx} out of range"
            elements.append({"from": e_from, "to": e_to, "faces": faces})
            exp.append(tuple(c) + tuple(v + 1 for v in c))
        name = f"aura_{segIdx:02d}_{cname}"
        model = {"textures": {**used, "particle": next(iter(used.values()))}, "elements": elements}
        json.dump(model, open(os.path.join(MODEL_DIR, name + ".json"), "w"), separators=(",", ":"))
        json.dump({"model": {"type": "minecraft:model", "model": f"barkan:imugi_s/{name}"}},
                  open(os.path.join(ITEM_DIR, name + ".json"), "w"), separators=(",", ":"))
        aura_models[cname][str(segIdx)] = {"item_model": f"barkan:imugi_s/{name}", "scale": k}
        # 인라인 검증 (역변환)
        for e, x in zip(elements, exp):
            der = tuple(pivot[a] + (e["from"][a] / 16 - 0.5) * k for a in range(3)) \
                + tuple(pivot[a] + (e["to"][a] / 16 - 0.5) * k for a in range(3))
            if not all(abs(p - q) <= 0.02 for p, q in zip(der, x)):
                fail += 1
                print(f"  !! {name} mismatch @ {x[:3]}")
        print(f"{name}: cells {len(cs)}")

rig["aura_models"] = aura_models
json.dump(rig, open(os.path.join(HERE, "imugi_s_rig.json"), "w"), indent=1)
print("rig aura_models 추가:", {c: len(m) for c, m in aura_models.items()})
print("VERIFY", "PASS" if fail == 0 else f"FAIL({fail})")
