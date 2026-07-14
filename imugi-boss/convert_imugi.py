#!/usr/bin/env python3
"""이무기 블록 빌드 → 마디별 RP 모델(ItemDisplay용) 변환기.

입력: imugi_scan.json (/get_region 결과), imugi_states.json (상태 블록 blockstate)
출력:
  - RP: assets/barkan/models/imugi/seg_XX.json + assets/barkan/items/imugi/seg_XX.json
  - imugi_rig.json  (마디별 pivot/scale/item_model — 스폰·애니메이션용 리그 데이터)
  - spawn_commands.txt (dev flatroom 정적 조립 테스트용 summon 커맨드)
  - preview_segments.png / preview_materials.png (검증 렌더)
"""
import json, math, os, re, sys
from collections import Counter, deque

SCRATCH = os.path.dirname(os.path.abspath(__file__))
RP = os.path.expanduser("~/development/barkan-resourcepack")
MODEL_DIR = os.path.join(RP, "assets/barkan/models/imugi")
ITEM_DIR = os.path.join(RP, "assets/barkan/items/imugi")

# ---------- 로드 ----------
scan = json.load(open(os.path.join(SCRATCH, "imugi_scan.json")))["blocks"]
states = json.load(open(os.path.join(SCRATCH, "imugi_states.json")))

def key(x, y, z): return (x, y, z)

blocks = {}  # (x,y,z) -> {"mat": short_name, "state": {..} or None}
for b in scan:
    mat = b["material"].removeprefix("minecraft:")
    st = None
    s = states.get(f"{b['x']},{b['y']},{b['z']}")
    if s and "[" in s:
        st = dict(kv.split("=") for kv in s[s.index("[")+1:-1].split(","))
    blocks[key(b["x"], b["y"], b["z"])] = {"mat": mat, "state": st}

# ---------- 연결 성분 (26-이웃) ----------
NB26 = [(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
        if not (dx == dy == dz == 0)]

def components(vox):
    seen, comps = set(), []
    for start in vox:
        if start in seen: continue
        comp, q = [], deque([start]); seen.add(start)
        while q:
            c = q.popleft(); comp.append(c)
            for d in NB26:
                n = (c[0]+d[0], c[1]+d[1], c[2]+d[2])
                if n in vox and n not in seen:
                    seen.add(n); q.append(n)
        comps.append(comp)
    return sorted(comps, key=len, reverse=True)

comps = components(set(blocks))
main = set(comps[0])
attached, dropped = [], []
for c in comps[1:]:
    # 본체에서 2블록 이내면 빌드 일부(떠 있는 수염 등)로 간주해 편입
    near = any(abs(a[0]-b[0]) <= 2 and abs(a[1]-b[1]) <= 2 and abs(a[2]-b[2]) <= 2
               for a in c for b in main)
    (attached if near else dropped).append(c)
for c in attached: main |= set(c)
print(f"components: {len(comps)} (main {len(comps[0])}, attached {sum(len(c) for c in attached)}, dropped {sum(len(c) for c in dropped)})")
for c in dropped:
    print("  dropped comp:", len(c), "at", c[0])

vox = main

# ---------- 측지 거리 (스파인 파라미터) ----------
def bfs(vox, start):
    dist = {start: 0}; q = deque([start])
    while q:
        c = q.popleft()
        for d in NB26:
            n = (c[0]+d[0], c[1]+d[1], c[2]+d[2])
            if n in vox and n not in dist:
                dist[n] = dist[c] + 1; q.append(n)
    return dist

seed = next(iter(vox))
d0 = bfs(vox, seed)
endA = max(d0, key=d0.get)          # 극단점 1
dA = bfs(vox, endA)
endB = max(dA, key=dA.get)          # 극단점 2 (지름의 양끝)
# 꼬리(낮은 y 극단)에서 0이 시작되게 정렬 → seg 0 = 꼬리, 마지막 = 머리
tail = endA if endA[1] <= endB[1] else endB
dist = bfs(vox, tail)
maxd = max(dist.values())
# 미도달(고립) 방어: 전부 도달함을 확인
assert len(dist) == len(vox), "unreachable voxels in main component"

N = max(10, min(18, round(maxd / 5)))
seg_of = {v: min(N-1, dist[v] * N // (maxd + 1)) for v in vox}
# 머리 병합: 뿔/수염 가지가 거리 밴드를 넘나들며 얼룩지는 걸 방지 — 마지막 HEAD_MERGE 밴드를 한 강체로
HEAD_MERGE = 2
head_idx = N - HEAD_MERGE
for v in vox:
    if seg_of[v] > head_idx: seg_of[v] = head_idx
N = head_idx + 1
print(f"geodesic max {maxd}, segments N={N} (head merged {HEAD_MERGE} bands), tail end at {tail} (head end {endB if tail==endA else endA})")

# ---------- 텍스처 매핑 ----------
TEX = {
    "stripped_warped_hyphae": "minecraft:block/stripped_warped_stem",
    "prismarine": "minecraft:block/prismarine",
    "prismarine_slab": "minecraft:block/prismarine",
    "prismarine_wall": "minecraft:block/prismarine",
    "dark_prismarine": "minecraft:block/dark_prismarine",
    "dark_prismarine_slab": "minecraft:block/dark_prismarine",
    "dark_prismarine_stairs": "minecraft:block/dark_prismarine",
    "polished_blackstone_brick_wall": "minecraft:block/polished_blackstone_bricks",
    "red_nether_brick_slab": "minecraft:block/red_nether_bricks",
    "red_nether_brick_stairs": "minecraft:block/red_nether_bricks",
    "smooth_quartz_stairs": "minecraft:block/quartz_block_bottom",
    "white_wool": "minecraft:block/white_wool",
    "lime_wool": "minecraft:block/lime_wool",
    "lime_stained_glass": "minecraft:block/lime_stained_glass",
}
FULL_OPAQUE = {"stripped_warped_hyphae", "prismarine", "dark_prismarine", "white_wool", "lime_wool"}

# ---------- 블록 → 로컬 박스(0..16 블록로컬) — 바닐라 jar에서 파생 (ground truth) ----------
import vanilla_geom

def boxes_for(mat, st):
    """(from,to) 박스 리스트, 블록 로컬 0..16 좌표. 바닐라 blockstate/model 파일 기반."""
    if mat == "ender_chest":
        return None  # 별도 스폰 (진짜 엔더체스트 아이템 모델 사용)
    state = f"minecraft:{mat}"
    if st:
        state += "[" + ",".join(f"{k}={v}" for k, v in sorted(st.items())) + "]"
    boxes = vanilla_geom.boxes_for_state(state)
    if not boxes:
        print("  ! vanilla boxes empty, full cube fallback:", state)
        return [((0, 0, 0), (16, 16, 16))]
    return [(tuple(fr), tuple(to)) for fr, to in boxes]

# hyphae 결(axis) 방향 → 면별 UV 회전 (원본 블록의 텍스처 방향 재현)
def hyphae_face_rotation(axis, face):
    if axis == "x":
        return 90 if face in ("up", "down", "north", "south") else 0
    if axis == "z":
        return 90 if face in ("east", "west") else 0
    return 0  # axis=y 기본

# ---------- 면 UV ----------
def face_uv(face, fr, to):
    x0, y0, z0 = fr; x1, y1, z1 = to
    if face in ("up", "down"): return [x0, z0, x1, z1]
    if face in ("north", "south"): return [x0, 16 - y1, x1, 16 - y0]
    return [z0, 16 - y1, z1, 16 - y0]  # east/west

DIRS = {"down": (0, -1, 0), "up": (0, 1, 0), "north": (0, 0, -1),
        "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}

# ---------- 마디별 모델 생성 ----------
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(ITEM_DIR, exist_ok=True)

segs = {i: [v for v in vox if seg_of[v] == i] for i in range(N)}
rig = {"world_origin_hint": "flatroom prod build",
       "left_rotation_fix": [0, 1, 0, 0],  # ItemDisplay 아이템모델 Y180° 렌더 관례 보정 — 모든 마디 필수
       "render_scale_multiplier": 1.5,  # 클라가 아이템 모델을 스팬48→2/3로 fit 렌더 → 스폰 scale = k×1.5 (실측 2026-07-06 정정: 0.5/×2는 오측)
       "segments": [], "extra_displays": []}
warn_scale = []

for i in range(N):
    sv = segs[i]
    if not sv:
        print(f"  ! segment {i} empty"); continue
    dmin = min(dist[v] for v in sv)
    band = [v for v in sv if dist[v] <= dmin + 1]  # 이전 마디와 맞닿는 관절 밴드
    pivot = tuple(sum(c[a] for c in band) / len(band) + 0.5 for a in range(3))  # 블록 중심 기준

    lo = [min(v[a] for v in sv) - pivot[a] for a in range(3)]
    hi = [max(v[a] for v in sv) + 1 - pivot[a] for a in range(3)]
    k = max(1.0, max(max(-l, h) * 2.0 / 3.0 for l, h in zip(lo, hi)))
    k = math.ceil(k * 100) / 100
    if k > 3.5: warn_scale.append((i, k))

    used_tex = {}
    elements = []
    for v in sv:
        info = blocks[v]; mat = info["mat"]
        bl = boxes_for(mat, info["state"])
        if bl is None:  # ender_chest → 별도 디스플레이
            st = info["state"] or {}
            facing = st.get("facing", "south")
            # ItemDisplay는 아이템 모델을 Y축 180° 돌려 렌더 → 180° 합성(N↔S, E↔W 스왑) 보정값
            YAW_Q = {"north": [0, 0, 0, 1], "south": [0, 1, 0, 0],
                     "west": [0, -0.70711, 0, 0.70711], "east": [0, 0.70711, 0, 0.70711]}
            rig["extra_displays"].append({
                "kind": "ender_chest_eye", "attach_seg": i,
                "pos": [v[0] + 0.5, v[1] + 0.5, v[2] + 0.5],
                "left_rotation": YAW_Q[facing],
                "scale": 2.0,  # 클라 0.5× 렌더 보정 (마디와 동일)
            })
            continue
        tkey = mat
        used_tex[tkey] = TEX[mat]
        full_opaque = mat in FULL_OPAQUE or (mat.endswith("_slab") and info["state"] and info["state"]["type"] == "double")
        for fr, to in bl:
            faces = {}
            for fname, d in DIRS.items():
                # 풀블록 면 컬링: 같은 마디의 불투명 풀블록이 면을 완전히 덮으면 생략
                if full_opaque and ((fr, to) == ((0, 0, 0), (16, 16, 16))):
                    n = (v[0]+d[0], v[1]+d[1], v[2]+d[2])
                    if n in vox and seg_of.get(n) == i:
                        nm = blocks[n]["mat"]
                        n_full = nm in FULL_OPAQUE or (nm.endswith("_slab") and blocks[n]["state"] and blocks[n]["state"]["type"] == "double")
                        if n_full: continue
                # 부분 박스: 박스가 블록 경계면에 안 닿는 방향의 면은 항상 그림
                face = {"texture": "#" + tkey, "uv": face_uv(fname, fr, to)}
                if mat == "stripped_warped_hyphae":
                    rot = hyphae_face_rotation((info["state"] or {}).get("axis", "y"), fname)
                    if rot: face["rotation"] = rot
                faces[fname] = face
            if not faces: continue
            e_from = [round(8 + (v[a] - pivot[a]) * 16 / k + fr[a] / k, 4) for a in range(3)]
            e_to = [round(8 + (v[a] - pivot[a]) * 16 / k + to[a] / k, 4) for a in range(3)]
            for c in e_from + e_to:
                assert -16 <= c <= 32, f"seg {i} coord {c} out of range (k={k})"
            elements.append({"from": e_from, "to": e_to, "faces": faces})

    model = {"textures": {**used_tex, "particle": next(iter(used_tex.values()))}, "elements": elements}
    name = f"seg_{i:02d}"
    json.dump(model, open(os.path.join(MODEL_DIR, name + ".json"), "w"), separators=(",", ":"))
    json.dump({"model": {"type": "minecraft:model", "model": f"barkan:imugi/{name}"}},
              open(os.path.join(ITEM_DIR, name + ".json"), "w"), separators=(",", ":"))
    rig["segments"].append({
        "seg": i, "item_model": f"barkan:imugi/{name}", "pivot": [round(p, 3) for p in pivot],
        "scale": k, "blocks": len(sv), "elements": len(elements),
        "dist_range": [dmin, max(dist[v] for v in sv)],
    })
    print(f"seg {i:02d}: blocks {len(sv):3d}  elements {len(elements):3d}  k={k:<5} pivot {tuple(round(p,1) for p in pivot)}")

if warn_scale: print("  ! large scale segs:", warn_scale)
json.dump(rig, open(os.path.join(SCRATCH, "imugi_rig.json"), "w"), indent=1)
json.dump({f"{v[0]},{v[1]},{v[2]}": seg_of[v] for v in vox},
          open(os.path.join(SCRATCH, "imugi_segmap.json"), "w"), separators=(",", ":"))

# ---------- 스폰 커맨드 (dev flatroom, 원좌표 그대로) ----------
lines = []
for s in rig["segments"]:
    px, py, pz = s["pivot"]; k = round(s["scale"] * rig["render_scale_multiplier"], 2)
    nbt = (f'{{item:{{id:"minecraft:paper",count:1,components:{{"minecraft:item_model":"{s["item_model"]}"}}}},'
           f'transformation:{{translation:[0f,0f,0f],left_rotation:[0f,1f,0f,0f],right_rotation:[0f,0f,0f,1f],'
           f'scale:[{k}f,{k}f,{k}f]}},Tags:["imugi_test","imugi_seg{s["seg"]}"]}}')
    lines.append(f'execute in minecraft:flatroom run summon minecraft:item_display {px} {py} {pz} {nbt}')
for e in rig["extra_displays"]:
    q = e["left_rotation"]; es = e.get("scale", 2.0)
    nbt = (f'{{item:{{id:"minecraft:ender_chest",count:1}},'
           f'transformation:{{translation:[0f,0f,0f],left_rotation:[{q[0]}f,{q[1]}f,{q[2]}f,{q[3]}f],'
           f'right_rotation:[0f,0f,0f,1f],scale:[{es}f,{es}f,{es}f]}},Tags:["imugi_test"]}}')
    lines.append(f'execute in minecraft:flatroom run summon minecraft:item_display {e["pos"][0]} {e["pos"][1]} {e["pos"][2]} {nbt}')
lines.append('# 정리: execute in minecraft:flatroom run kill @e[type=item_display,tag=imugi_test]')
open(os.path.join(SCRATCH, "spawn_commands.txt"), "w").write("\n".join(lines))
print(f"\nwrote {len(rig['segments'])} models -> {MODEL_DIR}")
print(f"spawn commands: {len(lines)-1} entities")
