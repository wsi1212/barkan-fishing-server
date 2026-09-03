#!/usr/bin/env python3
"""직선 레스트 포즈 보스 빌드 → 마디별 RP 모델(ItemDisplay) + 리그 + 인라인 수치검증.

convert_straight.py(이무기 전용, 좌표·시드 하드코딩)를 이름·bbox 파라미터로 일반화한 것.
소스는 scan_boss.py 산출 `<name>_scan.json` (blockstate 포함) — 손편집 금지, 매번 다시 뽑는다.

마디 = z밴드(직선이라 깔끔). seg0=꼬리(verbatim) → 중간=몸 밴드 → last=머리(verbatim).
스팬을 31유닛 이하로 유지해 클라 대형모델 2/3 자동축소를 원천 회피 → render_scale_multiplier=1.0.

사용: python3 bake_boss.py <name>
"""
import json, os, sys
import vanilla_geom

HERE = os.path.dirname(os.path.abspath(__file__))
RP = os.path.expanduser("~/development/barkan-resourcepack")

# ---------------------------------------------------------------- 보스별 설정
BOSSES = {
    # 자수정 결정 뱀 — prod flatroom 직선 레스트 포즈 (2026-09-03 유저 빌드)
    "crystal": {
        "band": 3,          # 몸 마디 z밴드 두께(블록) — 3 = 관절각 검증된 값
        "head_z_min": -119, # 이 z 이상 = 머리 한 마디(강체)
        "tail_z_max": -145, # 이 z 이하 = 꼬리 한 마디(강체)
    },
}

# ---------------------------------------------------------------- 텍스처/불투명
TEX = {
    "amethyst_block": "minecraft:block/amethyst_block",
    "amethyst_cluster": "minecraft:block/amethyst_block",   # ★크로스평면 금지 → 부피 스파이크로 대체
    "purpur_block": "minecraft:block/purpur_block",
    "white_concrete": "minecraft:block/white_concrete",
    "black_concrete": "minecraft:block/black_concrete",
    "black_wool": "minecraft:block/black_wool",
    "pale_moss_block": "minecraft:block/pale_moss_block",
    "oak_leaves": "minecraft:block/moss_block",             # ★잎 텍스처는 바이옴 틴트 의존 → 초록 고정
    "magenta_stained_glass": "minecraft:block/magenta_stained_glass",
    "magenta_stained_glass_pane": "minecraft:block/magenta_stained_glass",
    "sea_lantern": "minecraft:block/sea_lantern",
    "smooth_quartz_stairs": "minecraft:block/quartz_block_bottom",
    "polished_blackstone_stairs": "minecraft:block/polished_blackstone",
}
FULL_OPAQUE = {"amethyst_block", "purpur_block", "white_concrete", "black_concrete",
               "black_wool", "pale_moss_block", "sea_lantern", "oak_leaves"}
EXTRA_DISPLAY = {"ender_chest"}

# 군집(크리스탈 싹) 대체 부피 — facing=up 로컬 프레임 3단 테이퍼. 실제 부피라 옆에서도 보인다.
# 밑면 폭 10 은 바닐라 군집 크로스(폭 14.4, 두께 0)의 시각 질량에 맞춘 값 — 더 얇게 하면
# 뿔이 바늘처럼 가늘어져 원본 실루엣이 죽는다.
SPIKE_UP = [((3, 0, 3), (13, 5, 13)), ((4.5, 5, 4.5), (11.5, 11, 11.5)),
            ((6, 11, 6), (10, 16, 10))]

DIRS = {"down": (0, -1, 0), "up": (0, 1, 0), "north": (0, 0, -1),
        "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}
YAW_Q = {"north": [0, 0, 0, 1], "south": [0, 1, 0, 0],
         "west": [0, -0.70711, 0, 0.70711], "east": [0, 0.70711, 0, 0.70711]}


def base_mat(m):
    m = m.removeprefix("minecraft:")
    return m[:m.index("[")] if "[" in m else m


def state_dict(m):
    if "[" not in m:
        return {}
    return dict(kv.split("=") for kv in m[m.index("[") + 1:-1].split(","))


def face_uv(face, fr, to):
    x0, y0, z0 = fr
    x1, y1, z1 = to
    if face in ("up", "down"):
        return [x0, z0, x1, z1]
    if face in ("north", "south"):
        return [x0, 16 - y1, x1, 16 - y0]
    return [z0, 16 - y1, z1, 16 - y0]


def variant_rotation(state_str):
    """blockstate 파일의 variant 회전(x, y)을 그대로 읽어온다 — 6방향 손코딩 금지."""
    block = base_mat(state_str)
    props = state_dict(state_str)
    bs = vanilla_geom._read(f"assets/minecraft/blockstates/{block}.json")
    for key, val in bs.get("variants", {}).items():
        kv = dict(p.split("=") for p in key.split(",")) if key else {}
        if all(props.get(k) == v for k, v in kv.items()):
            v = val[0] if isinstance(val, list) else val
            return v.get("x", 0), v.get("y", 0)
    return 0, 0


def boxes_of(state_str):
    """셀 → 로컬 AABB 리스트. 군집은 부피 대체, 미지 블록은 풀큐브 폴백, 중복 박스 제거."""
    bm = base_mat(state_str)
    if bm == "amethyst_cluster" or bm.endswith("_amethyst_bud"):
        xr, yr = variant_rotation(state_str)
        els = [{"from": list(fr), "to": list(to)} for fr, to in SPIKE_UP]
        boxes = vanilla_geom._apply_variant(els, xr, yr)
    else:
        try:
            boxes = vanilla_geom.boxes_for_state(state_str if "[" in state_str
                                                 else f"minecraft:{bm}")
        except KeyError:
            boxes = []          # 1.20.1 jar 에 없는 신규 블록(pale_moss 등) → 풀큐브
    boxes = [b for b in boxes if all(b[1][a] > b[0][a] for a in range(3))]  # 0두께 제거
    if not boxes:
        boxes = [((0, 0, 0), (16, 16, 16))]
    seen, out = set(), []
    for fr, to in boxes:                      # 판유리 multipart 는 중심기둥을 중복 산출
        key = (tuple(fr), tuple(to))
        if key in seen:
            continue
        seen.add(key)
        out.append((fr, to))
    return out


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__)
    cfg = BOSSES[name]
    scan = json.load(open(os.path.join(HERE, f"{name}_scan.json")))
    cells = {tuple(map(int, k.split(","))): v for k, v in scan["cells"].items()}
    print(f"source cells: {len(cells)}  world={scan['world']} bbox={scan['bbox']}")

    model_dir = os.path.join(RP, f"assets/barkan/models/{name}")
    item_dir = os.path.join(RP, f"assets/barkan/items/{name}")
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(item_dir, exist_ok=True)

    # ---- 마디 배정 (z밴드) ----
    head = sorted(c for c in cells if c[2] >= cfg["head_z_min"])
    tail = sorted(c for c in cells if c[2] <= cfg["tail_z_max"])
    body = [c for c in cells if c not in set(head) | set(tail)]
    assert head and tail and body, "머리/꼬리/몸 중 빈 그룹"
    zmax_b, zmin_b = max(c[2] for c in body), min(c[2] for c in body)
    band = cfg["band"]
    NB = max(1, (zmax_b - zmin_b + 1) // band)          # 남는 꼬랑지는 마지막(꼬리쪽) 밴드에 병합

    def band_of(z):
        return min((zmax_b - z) // band, NB - 1)        # 0 = 머리쪽

    segments = [tail]
    for i in range(NB - 1, -1, -1):                     # 꼬리쪽 밴드부터
        segments.append(sorted(c for c in body if band_of(c[2]) == i))
    segments.append(head)
    segments = [s for s in segments if s]
    N = len(segments)
    print(f"segments: {N} sizes: {[len(s) for s in segments]}")

    # ---- 척추축: 몸통 코어(불투명 살) 무게중심. 스파이크·잎 장식은 축을 끌면 안 된다 ----
    # 직선 리그는 축이 하나뿐이라 마디마다 다른 축을 쓸 수 없다 → 튜브 전체가 가장 잘 중심에
    # 오는 값을 쓰고, 머리는 pivot(목 관절)으로 따로 잡는다.
    core = [c for c in cells if base_mat(cells[c]) in FULL_OPAQUE and c not in set(tail)]
    half = lambda v: round(v * 2) / 2
    SPINE_X = half(sum(c[0] for c in core) / len(core) + 0.5)
    SPINE_Y = half(sum(c[1] for c in core) / len(core) + 0.5)
    print(f"spine: x={SPINE_X} y={SPINE_Y}  (core cells {len(core)})")

    def pivot_of(idx, seg):
        zc = (min(c[2] for c in seg) + max(c[2] for c in seg) + 1) / 2
        if idx == N - 1:
            zc = float(min(c[2] for c in seg))          # 머리 pivot = 목 관절(리어)
        return (SPINE_X, SPINE_Y, zc)

    seg_of = {}
    for i, seg in enumerate(segments):
        for c in seg:
            seg_of[c] = i

    rig = {"world_origin_hint": f"{scan['world']} straight rest pose {scan['bbox']}",
           "left_rotation_fix": [0, 1, 0, 0], "render_scale_multiplier": 1.0,
           "segments": [], "extra_displays": []}
    expected_all = derived_all = fail = 0

    for i, seg in enumerate(segments):
        pivot = pivot_of(i, seg)
        lo = [min(c[a] for c in seg) - pivot[a] for a in range(3)]
        hi = [max(c[a] for c in seg) + 1 - pivot[a] for a in range(3)]
        k = max(1.0, max(max(-l, h) * 16 / 15.5 for l, h in zip(lo, hi)))  # 스팬≤31유닛
        used_tex, elements, exp_boxes = {}, [], []
        for c in seg:
            m = cells[c]
            bm, st = base_mat(m), state_dict(m)
            if bm in EXTRA_DISPLAY:
                rig["extra_displays"].append(
                    {"kind": "ender_chest_eye", "attach_seg": i,
                     "pos": [c[0] + .5, c[1] + .5, c[2] + .5],
                     "left_rotation": YAW_Q[st.get("facing", "south")], "scale": 1.15})
                continue
            used_tex[bm] = TEX[bm]
            full = bm in FULL_OPAQUE
            for fr, to in boxes_of(m):
                exp_boxes.append(tuple(c[a] + fr[a] / 16 for a in range(3))
                                 + tuple(c[a] + to[a] / 16 for a in range(3)))
                faces = {}
                for fn, d in DIRS.items():
                    if full and (tuple(fr), tuple(to)) == ((0, 0, 0), (16, 16, 16)):
                        n = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
                        if seg_of.get(n) == i and base_mat(cells[n]) in FULL_OPAQUE:
                            continue                    # 같은 마디 내부 밀폐면 컬링
                    faces[fn] = {"texture": "#" + bm, "uv": face_uv(fn, fr, to)}
                if not faces:
                    continue
                e_from = [round(8 + (c[a] - pivot[a]) * 16 / k + fr[a] / k, 4) for a in range(3)]
                e_to = [round(8 + (c[a] - pivot[a]) * 16 / k + to[a] / k, 4) for a in range(3)]
                assert all(-16 <= v <= 32 for v in e_from + e_to), f"seg{i} out of range k={k}"
                elements.append({"from": e_from, "to": e_to, "faces": faces})

        sname = f"seg_{i:02d}"
        model = {"textures": {**used_tex, "particle": next(iter(used_tex.values()))},
                 "elements": elements}
        json.dump(model, open(os.path.join(model_dir, sname + ".json"), "w"),
                  separators=(",", ":"))
        json.dump({"model": {"type": "minecraft:model", "model": f"barkan:{name}/{sname}"}},
                  open(os.path.join(item_dir, sname + ".json"), "w"), separators=(",", ":"))
        rig["segments"].append({"seg": i, "item_model": f"barkan:{name}/{sname}",
                                "pivot": [round(p, 3) for p in pivot], "scale": k,
                                "blocks": len(seg), "elements": len(elements)})

        # ---- 인라인 검증: 모델 역변환(world = pivot + (c/16-0.5)k) vs 기대 박스 ----
        der = [tuple(pivot[a] + (e["from"][a] / 16 - 0.5) * k for a in range(3))
               + tuple(pivot[a] + (e["to"][a] / 16 - 0.5) * k for a in range(3))
               for e in elements]
        der_left, matched, interior = list(der), 0, 0
        for eb in exp_boxes:
            hit = next((j for j, db in enumerate(der_left)
                        if all(abs(x - y) <= .02 for x, y in zip(eb, db))), None)
            if hit is not None:
                der_left.pop(hit)
                matched += 1
                continue

            def is_full_cell(p):
                m2 = cells.get(p)
                return bool(m2) and seg_of.get(p) == i and base_mat(m2) in FULL_OPAQUE
            bx, by, bz = int(eb[0]), int(eb[1]), int(eb[2])
            encl = all(is_full_cell((bx + d[0], by + d[1], bz + d[2])) for d in DIRS.values()) \
                and (eb[3] - eb[0], eb[4] - eb[1], eb[5] - eb[2]) == (1., 1., 1.)
            if encl:
                interior += 1
            else:
                fail += 1
                print(f"  !! seg{i} MISSING box @ {eb[:3]}")
        if der_left:
            fail += len(der_left)
            print(f"  !! seg{i} EXTRA {len(der_left)}")
        expected_all += len(exp_boxes)
        derived_all += len(der)
        print(f"seg {i:02d}: blocks {len(seg):3d} elem {len(elements):3d} k={k:<8.4f} "
              f"pivot z={pivot[2]:<8} exp {len(exp_boxes)} matched {matched} interior {interior}")

    out = os.path.join(HERE, f"{name}_rig.json")
    json.dump(rig, open(out, "w"), indent=1)
    print(f"\nwrote {out} + {model_dir}")
    print("TOTAL expected", expected_all, "derived", derived_all, "FAIL", fail)
    print("VERIFY", "PASS" if fail == 0 else "FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
