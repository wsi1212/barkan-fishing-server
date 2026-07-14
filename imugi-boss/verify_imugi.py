#!/usr/bin/env python3
"""독립 검증기: 생성된 모델 JSON을 렌더 수식으로 월드 AABB 역변환해
원본 스캔+바닐라 blockstate 기하와 블록 단위 대조. diff=0이면 100% 일치.

렌더 수식(실측 검증된 net): world = pivot + (c/16 - 0.5) * k_rig
(스폰 scale 2k × 클라 0.5 = k, 클라 180Y × left_rotation 180Y = identity)
"""
import json, os, sys
import vanilla_geom

SCRATCH = os.path.dirname(os.path.abspath(__file__))
RP = os.path.expanduser("~/development/barkan-resourcepack/assets/barkan/models/imugi")

scan = json.load(open(os.path.join(SCRATCH, "imugi_scan.json")))["blocks"]
states = json.load(open(os.path.join(SCRATCH, "imugi_states.json")))
segmap = json.load(open(os.path.join(SCRATCH, "imugi_segmap.json")))
rig = json.load(open(os.path.join(SCRATCH, "imugi_rig.json")))
bymat = {(b["x"], b["y"], b["z"]): b["material"].removeprefix("minecraft:") for b in scan}

TOL = 0.02

def expected_boxes(seg_i):
    """세그먼트의 기대 월드 AABB 집합 (바닐라 기하 기반)."""
    out = []
    for kk, v in segmap.items():
        if v != seg_i: continue
        x, y, z = map(int, kk.split(","))
        mat = bymat[(x, y, z)]
        if mat == "ender_chest": continue  # 별도 디스플레이
        st = states.get(kk)
        state = st if st else f"minecraft:{mat}"
        boxes = vanilla_geom.boxes_for_state(state)
        if not boxes:
            boxes = [((0, 0, 0), (16, 16, 16))]
        for fr, to in boxes:
            out.append(tuple(round(c + l / 16, 4) for c, l in zip((x, y, z), fr)) +
                       tuple(round(c + l / 16, 4) for c, l in zip((x, y, z), to)))
    return out

def derived_boxes(seg):
    """모델 JSON → 렌더 수식으로 월드 AABB."""
    m = json.load(open(os.path.join(RP, f"seg_{seg['seg']:02d}.json")))
    p = seg["pivot"]; k = seg["scale"]
    out = []
    for e in m["elements"]:
        fr = [p[a] + (e["from"][a] / 16 - 0.5) * k for a in range(3)]
        to = [p[a] + (e["to"][a] / 16 - 0.5) * k for a in range(3)]
        out.append(tuple(round(v, 4) for v in fr) + tuple(round(v, 4) for v in to))
    return out

def match_sets(exp, der):
    """탐욕 매칭: 각 기대 박스에 tol 내 유도 박스가 1:1로 있는가."""
    der_left = list(der)
    missing = []
    for eb in exp:
        hit = None
        for i, db in enumerate(der_left):
            if all(abs(a - b) <= TOL for a, b in zip(eb, db)):
                hit = i; break
        if hit is None: missing.append(eb)
        else: der_left.pop(hit)
    return missing, der_left  # (기대인데 없음, 유도인데 남음)

FULLCUBE_MATS = {"stripped_warped_hyphae", "prismarine", "dark_prismarine", "white_wool", "lime_wool"}

def is_interior_enclosed(box, seg_i):
    """기대 박스가 풀큐브이고 같은 마디의 풀큐브 6이웃에 완전 밀폐 → 렌더상 비가시(컬링 정당)."""
    fx, fy, fz, tx, ty, tz = box
    if (tx - fx, ty - fy, tz - fz) != (1.0, 1.0, 1.0): return False
    bx, by, bz = int(fx), int(fy), int(fz)
    for d in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
        n = (bx+d[0], by+d[1], bz+d[2])
        nk = f"{n[0]},{n[1]},{n[2]}"
        if segmap.get(nk) != seg_i: return False
        nm = bymat.get(n)
        if nm not in FULLCUBE_MATS:
            nst = states.get(nk, "")
            if not (nm and nm.endswith("_slab") and "type=double" in nst): return False
    return True

total_missing = total_extra = total_exp = 0
for seg in rig["segments"]:
    exp = expected_boxes(seg["seg"])
    der = derived_boxes(seg)
    missing, extra = match_sets(exp, der)
    interior = [b for b in missing if is_interior_enclosed(b, seg["seg"])]
    missing = [b for b in missing if b not in interior]
    total_exp += len(exp); total_missing += len(missing); total_extra += len(extra)
    status = "OK " if not missing and not extra else "DIFF"
    print(f"seg {seg['seg']:02d} [{status}] expected {len(exp):4d} boxes / derived {len(der):4d} / missing {len(missing)} / extra {len(extra)} / interior-culled {len(interior)}")
    for mb in missing[:4]:
        bx = tuple(int(v // 1) for v in mb[:3])
        print(f"    - missing @~{bx}: {mb[:3]} -> {mb[3:]}  ({bymat.get(bx, '?')})")
    for xb in extra[:4]:
        print(f"    - extra   : {xb[:3]} -> {xb[3:]}")

# 엔더체스트 눈 검증
eyes_expect = sorted([(x + 0.5, y + 0.5, z + 0.5) for (x, y, z), m in bymat.items() if m == "ender_chest"])
eyes_rig = sorted([tuple(e["pos"]) for e in rig["extra_displays"]])
eyes_ok = eyes_expect == eyes_rig and all(e.get("scale") == 2.0 for e in rig["extra_displays"])
print(f"eyes: expect {len(eyes_expect)} / rig {len(eyes_rig)} / pos&scale {'OK' if eyes_ok else 'DIFF'}")

print(f"\nTOTAL: expected {total_exp} boxes, missing {total_missing}, extra {total_extra}")
sys.exit(0 if (total_missing == 0 and total_extra == 0 and eyes_ok) else 1)
