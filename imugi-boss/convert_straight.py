#!/usr/bin/env python3
"""직선 이무기 → RP 마디 모델 변환 + 인라인 수치검증.
소스: straight_imugi_blocks.json (설치 기록 = 월드와 일치 검증됨, blockstate 포함)
마디: z밴드(직선이라 깔끔) — seg0=꼬리(verbatim), 중간=몸 밴드, last=머리(verbatim)
모델: barkan:imugi_s/seg_XX (기존 감긴 동상 barkan:imugi/* 유지)
"""
import json, math, os
import vanilla_geom

SCRATCH = os.path.dirname(os.path.abspath(__file__))
RP = os.path.expanduser("~/development/barkan-resourcepack")
MODEL_DIR = os.path.join(RP, "assets/barkan/models/imugi_s")
ITEM_DIR = os.path.join(RP, "assets/barkan/items/imugi_s")
os.makedirs(MODEL_DIR, exist_ok=True); os.makedirs(ITEM_DIR, exist_ok=True)

blocks = json.load(open(os.path.join(SCRATCH, "straight_imugi_blocks.json")))
segmap_orig = json.load(open(os.path.join(SCRATCH, "imugi_segmap.json")))
cells = {}
for b in blocks: cells[(b['x'], b['y'], b['z'])] = b['material']  # 중복은 자연 dedup
print('source cells:', len(cells))

# ---- 마디 배정 ----
DX = 73
head_cells = {(x+DX, y, z) for k, s in segmap_orig.items() if s == 8
              for x, y, z in [tuple(map(int, k.split(',')))]}
tail_orig = [tuple(map(int, k.split(','))) for k, s in segmap_orig.items() if s == 0]
# 꼬리 이동량은 브루트포스 탐색 (설치 시 반올림 값 재현 대신 실측)
best = (0, None)
for tx in range(69, 77):
    for ty in range(13, 21):
        for tz in range(-19, -11):
            hit = sum(1 for x, y, z in tail_orig if (x+tx, y+ty, z+tz) in cells)
            if hit > best[0]: best = (hit, (tx, ty, tz))
TT = best[1]
print('tail T found:', TT, 'match', best[0], '/', len(tail_orig))
tail_cells = {(x+TT[0], y+TT[1], z+TT[2]) for x, y, z in tail_orig}
head_cells &= set(cells); tail_cells &= set(cells)
# 유저 수동 편집분(시드에 없는 새 셀): 머리/꼬리 시드에 인접하면 그쪽으로, 아니면 몸통
def near_set(c, S, r=1):
    return any(abs(c[0]-s[0]) <= r and abs(c[1]-s[1]) <= r and abs(c[2]-s[2]) <= r for s in S)
unknown = [c for c in cells if c not in head_cells and c not in tail_cells]
for c in list(unknown):
    if c[2] >= -98 or (c[2] >= -104 and near_set(c, head_cells)):
        head_cells.add(c); unknown.remove(c)
    elif c[2] <= -131 and near_set(c, tail_cells):
        tail_cells.add(c); unknown.remove(c)
body_cells = unknown
print('head', len(head_cells), '/ tail', len(tail_cells), '/ body', len(body_cells))

# 몸: z −99(남,머리쪽)..−130(북) → 5블록 밴드, 남는 꼬랑지는 마지막 밴드에 병합
zmax_body = max(c[2] for c in body_cells)   # -99
zmin_body = min(c[2] for c in body_cells)
NB = (zmax_body - zmin_body + 1) // 3
def body_band(z):
    i = (zmax_body - z) // 3
    return min(i, NB - 1)
segments = []  # index 0=꼬리 → last=머리
segments.append(sorted(tail_cells))
for i in range(NB - 1, -1, -1):  # 북(꼬리쪽) 밴드부터
    segments.append(sorted(c for c in body_cells if body_band(c[2]) == i))
segments.append(sorted(head_cells))
N = len(segments)
print('segments:', N, 'sizes:', [len(s) for s in segments])

SPINE_X, SPINE_Y = 120.5, -31.0
def pivot_of(idx, seg):
    zc = (min(c[2] for c in seg) + max(c[2] for c in seg) + 1) / 2
    if idx == N - 1: zc = -98.0  # 머리 pivot=목 관절(리어) — 머리가 경로를 리드, 회전 시 목 이탈 방지
    return (SPINE_X, SPINE_Y, zc)

# ---- 텍스처 ----
TEX = {
    "stripped_warped_hyphae": "minecraft:block/stripped_warped_stem",
    "prismarine": "minecraft:block/prismarine", "prismarine_slab": "minecraft:block/prismarine",
    "prismarine_wall": "minecraft:block/prismarine",
    "dark_prismarine": "minecraft:block/dark_prismarine", "dark_prismarine_slab": "minecraft:block/dark_prismarine",
    "dark_prismarine_stairs": "minecraft:block/dark_prismarine",
    "polished_blackstone_brick_wall": "minecraft:block/polished_blackstone_bricks",
    "red_nether_brick_slab": "minecraft:block/red_nether_bricks", "red_nether_brick_stairs": "minecraft:block/red_nether_bricks",
    "smooth_quartz_stairs": "minecraft:block/quartz_block_bottom",
    "white_wool": "minecraft:block/white_wool", "lime_wool": "minecraft:block/lime_wool",
}
FULL_OPAQUE = {"stripped_warped_hyphae", "prismarine", "dark_prismarine", "white_wool", "lime_wool"}
def base_mat(m):
    m = m.removeprefix("minecraft:")
    return m[:m.index("[")] if "[" in m else m
def state_dict(m):
    if "[" not in m: return {}
    return dict(kv.split("=") for kv in m[m.index("[")+1:-1].split(","))
def face_uv(face, fr, to):
    x0,y0,z0 = fr; x1,y1,z1 = to
    if face in ("up","down"): return [x0,z0,x1,z1]
    if face in ("north","south"): return [x0,16-y1,x1,16-y0]
    return [z0,16-y1,z1,16-y0]
def hyphae_rot(axis, face):
    if axis == "x": return 90 if face in ("up","down","north","south") else 0
    if axis == "z": return 90 if face in ("east","west") else 0
    return 0
DIRS = {"down":(0,-1,0),"up":(0,1,0),"north":(0,0,-1),"south":(0,0,1),"west":(-1,0,0),"east":(1,0,0)}
YAW_Q = {"north":[0,0,0,1],"south":[0,1,0,0],"west":[0,-0.70711,0,0.70711],"east":[0,0.70711,0,0.70711]}

seg_of = {}
for i, seg in enumerate(segments):
    for c in seg: seg_of[c] = i

rig = {"world_origin_hint": "flatroom dev straight build",
       "left_rotation_fix": [0,1,0,0], "render_scale_multiplier": 1.0,
       "segments": [], "extra_displays": []}
expected_all, derived_all = 0, 0
fail = 0
for i, seg in enumerate(segments):
    pivot = pivot_of(i, seg)
    lo = [min(c[a] for c in seg) - pivot[a] for a in range(3)]
    hi = [max(c[a] for c in seg) + 1 - pivot[a] for a in range(3)]
    k = max(1.0, max(max(-l, h) * 16 / 15.5 for l, h in zip(lo, hi)))  # 스팬≤31유닛: 클라 자동축소(스팬>32 시 2/3) 미발동 → f=1
    k = k  # 정확값 유지 — 스팬을 정확히 48유닛으로(클라 fit 배율 결정론화)
    used_tex, elements, exp_boxes = {}, [], []
    for c in seg:
        m = cells[c]; bm = base_mat(m); st = state_dict(m)
        if bm == "ender_chest":
            rig["extra_displays"].append({"kind":"ender_chest_eye","attach_seg":i,
                "pos":[c[0]+.5, c[1]+.5, c[2]+.5], "left_rotation": YAW_Q[st.get("facing","south")], "scale": 1.15})  # 체스트 아이템은 자동축소 없음 — 1블록 눈
            continue
        boxes = vanilla_geom.boxes_for_state(m if "[" in m else f"minecraft:{bm}")
        if not boxes: boxes = [((0,0,0),(16,16,16))]
        used_tex[bm] = TEX[bm]
        full = bm in FULL_OPAQUE or (bm.endswith("_slab") and st.get("type") == "double")
        for fr, to in boxes:
            exp_boxes.append(tuple(c[a]+fr[a]/16 for a in range(3)) + tuple(c[a]+to[a]/16 for a in range(3)))
            faces = {}
            for fn, d in DIRS.items():
                if full and (tuple(fr), tuple(to)) == ((0,0,0),(16,16,16)):
                    n = (c[0]+d[0], c[1]+d[1], c[2]+d[2])
                    if seg_of.get(n) == i:
                        nm = base_mat(cells[n]); nst = state_dict(cells[n])
                        if nm in FULL_OPAQUE or (nm.endswith("_slab") and nst.get("type") == "double"):
                            continue
                face = {"texture": "#"+bm, "uv": face_uv(fn, fr, to)}
                if bm == "stripped_warped_hyphae":
                    r = hyphae_rot(st.get("axis","y"), fn)
                    if r: face["rotation"] = r
                faces[fn] = face
            if not faces: continue
            e_from = [round(8 + (c[a]-pivot[a])*16/k + fr[a]/k, 4) for a in range(3)]
            e_to   = [round(8 + (c[a]-pivot[a])*16/k + to[a]/k, 4) for a in range(3)]
            assert all(-16 <= v <= 32 for v in e_from+e_to), f"seg{i} out of range k={k}"
            elements.append({"from": e_from, "to": e_to, "faces": faces})
    name = f"seg_{i:02d}"
    model = {"textures": {**used_tex, "particle": next(iter(used_tex.values()))}, "elements": elements}
    json.dump(model, open(os.path.join(MODEL_DIR, name+".json"), "w"), separators=(",",":"))
    json.dump({"model": {"type":"minecraft:model","model": f"barkan:imugi_s/{name}"}},
              open(os.path.join(ITEM_DIR, name+".json"), "w"), separators=(",",":"))
    rig["segments"].append({"seg": i, "item_model": f"barkan:imugi_s/{name}",
                            "pivot": [round(p,3) for p in pivot], "scale": k,
                            "blocks": len(seg), "elements": len(elements)})
    # ---- 인라인 검증: 모델 역변환(world = pivot + (c/16-0.5)k) vs 기대 박스 ----
    der = []
    for e in elements:
        der.append(tuple(pivot[a]+(e["from"][a]/16-0.5)*k for a in range(3)) +
                   tuple(pivot[a]+(e["to"][a]/16-0.5)*k for a in range(3)))
    matched = 0
    der_left = list(der)
    interior = 0
    for eb in exp_boxes:
        hit = next((j for j, db in enumerate(der_left) if all(abs(x-y) <= .02 for x,y in zip(eb,db))), None)
        if hit is not None: der_left.pop(hit); matched += 1
        else:
            # 내부 밀폐 컬링 면제 검사 — 변환기와 동일 판정(double 슬랩도 불투명 취급)
            def is_full_cell(p):
                m2 = cells.get(p)
                if not m2 or seg_of.get(p) != i: return False
                b2 = base_mat(m2)
                return b2 in FULL_OPAQUE or (b2.endswith("_slab") and state_dict(m2).get("type") == "double")
            bx,by,bz = int(eb[0]), int(eb[1]), int(eb[2])
            encl = all(is_full_cell((bx+d[0],by+d[1],bz+d[2])) for d in DIRS.values()) \
                   and (eb[3]-eb[0], eb[4]-eb[1], eb[5]-eb[2]) == (1.,1.,1.)
            if encl: interior += 1
            else: fail += 1; print(f"  !! seg{i} MISSING box @ {eb[:3]}")
    if der_left: fail += len(der_left); print(f"  !! seg{i} EXTRA {len(der_left)}")
    expected_all += len(exp_boxes); derived_all += len(der)
    print(f"seg {i:02d}: blocks {len(seg):3d} elem {len(elements):3d} k={k:<5} pivot z={pivot[2]:<7} exp {len(exp_boxes)} matched {matched} interior {interior}")

# 눈 오프셋은 리그 로더가 머리 pivot 기준으로 계산하므로 pos 절대좌표 그대로 두면 됨
json.dump(rig, open(os.path.join(SCRATCH, "imugi_s_rig.json"), "w"), indent=1)
print("\nTOTAL expected", expected_all, "derived", derived_all, "FAIL", fail)
print("VERIFY", "PASS" if fail == 0 else "FAIL")
