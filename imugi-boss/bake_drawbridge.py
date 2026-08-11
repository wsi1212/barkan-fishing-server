#!/usr/bin/env python3
"""도개교 발판(deckPos) → 단일 발판 RP 모델 bake + 인라인 수치검증 (이무기/배 파이프라인 재사용).

소스: drawbridges.json (deckPos/deckData/hingeSide/pivotA/pivotY — 실제 등록 데이터 그대로)
- 면 텍스처/UV/회전/기하 전부 바닐라 클라 jar에서 직접 해석 (bake_ship.py와 동일 로직 재사용)
- ★배와의 차이: 발판은 항상 Y가 pivotY로 고정된 평면 — pivot=(0,0,·) corner기준
  (배는 (0.5,ymid,0.5) 블록중심 보정 필요하지만, 도개교 런타임 rotatePoint는 이미 corner
  좌표(pivotA/pivotY)로 직접 회전하므로 bake도 동일 corner 기준이어야 일치)
- 회전축: WEST/EAST 경첩 → u=x-pivotA(회전축), n=z-zmin(비회전축) / NORTH/SOUTH → u=z-pivotA, n=x-xmin
  (Drawbridge.rotatePoint/swingsInXY와 정확히 동일 규약)
- 스폰 앵커 월드좌표 = (pivotA, pivotY, zmin) [WEST/EAST] 또는 (xmin, pivotY, pivotA) [NORTH/SOUTH]
  — 이 점이 정확히 회전축 위에 있어야 blockRotation(angleRad) 그대로 적용 가능.

사용: python3 bake_drawbridge.py <drawbridges.json경로> <다리id> <영문모델명>
  예) python3 bake_drawbridge.py /tmp/prod-drawbridges.json 성문다리 castle_gate_deck
출력: RP models/items + drawbridge-models.json(스크립트 옆) 갱신 + 검증 리포트
"""
import json, os, sys, zipfile, functools

SCRATCH = os.path.dirname(os.path.abspath(__file__))
JAR = os.path.expanduser("~/Library/Application Support/minecraft/versions/1.21.11/1.21.11.jar")
RP = os.path.expanduser("~/development/barkan-resourcepack")

src_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/prod-drawbridges.json"
bridge_id = sys.argv[2] if len(sys.argv) > 2 else "성문다리"
mname = sys.argv[3] if len(sys.argv) > 3 else "deck0"
MODEL_DIR = os.path.join(RP, "assets/barkan/models/drawbridge")
ITEM_DIR = os.path.join(RP, "assets/barkan/items/drawbridge")
os.makedirs(MODEL_DIR, exist_ok=True); os.makedirs(ITEM_DIR, exist_ok=True)

# ---------- 바닐라 자산 해석 (bake_ship.py와 동일) ----------
_zf = zipfile.ZipFile(JAR)

@functools.lru_cache(maxsize=None)
def _read(path):
    with _zf.open(path) as f:
        return json.load(f)

@functools.lru_cache(maxsize=None)
def _model_merged(model_id):
    mid = model_id.removeprefix("minecraft:")
    tex, elements = {}, None
    cur = mid
    while cur is not None:
        data = _read(f"assets/minecraft/models/{cur}.json")
        for k, v in data.get("textures", {}).items():
            tex.setdefault(k, v)
        if elements is None and "elements" in data:
            elements = data["elements"]
        cur = data.get("parent", None)
        if cur: cur = cur.removeprefix("minecraft:")
        if cur in ("block/block", "block/cube", None):
            if cur and elements is None:
                data2 = _read(f"assets/minecraft/models/{cur}.json")
                if "elements" in data2: elements = data2["elements"]
                for k, v in data2.get("textures", {}).items(): tex.setdefault(k, v)
            break
    return (elements or []), tex

def _resolve_tex(texmap, ref):
    seen = 0
    while isinstance(ref, str) and ref.startswith("#"):
        ref = texmap.get(ref[1:], "minecraft:block/missing")
        seen += 1
        if seen > 8: break
    if isinstance(ref, str) and ":" not in ref: ref = "minecraft:" + ref
    return ref

def _rot90_box(fr, to, axis):
    if axis == "y":
        nf = (16 - to[2], fr[1], fr[0]); nt = (16 - fr[2], to[1], to[0])
    else:
        nf = (fr[0], fr[2], 16 - to[1]); nt = (to[0], to[2], 16 - fr[1])
    return list(nf), list(nt)

Y_MAP = {"north": "east", "east": "south", "south": "west", "west": "north", "up": "up", "down": "down"}
X_MAP = {"north": "down", "down": "south", "south": "up", "up": "north", "east": "east", "west": "west"}

warn = {"rot_elem_under_bsrot": 0, "tint": 0, "uvlock": 0}

def _apply_bs_rot(elements, xrot, yrot):
    out = []
    for e in elements:
        fr, to = list(e["from"]), list(e["to"])
        faces = {f: dict(v) for f, v in e.get("faces", {}).items()}
        rot = e.get("rotation")
        for _ in range((xrot // 90) % 4):
            fr, to = _rot90_box(fr, to, "x")
            faces = {X_MAP[f]: v for f, v in faces.items()}
        for _ in range((yrot // 90) % 4):
            fr, to = _rot90_box(fr, to, "y")
            faces = {Y_MAP[f]: v for f, v in faces.items()}
        if rot and (xrot or yrot):
            warn["rot_elem_under_bsrot"] += 1
        out.append({"from": fr, "to": to, "faces": faces, **({"rotation": rot} if rot else {})})
    return out

def _match_when(when, props):
    if "OR" in when:
        return any(_match_when(w, props) for w in when["OR"])
    if "AND" in when:
        return all(_match_when(w, props) for w in when["AND"])
    for k, v in when.items():
        allowed = str(v).split("|")
        if props.get(k, "") not in allowed:
            return False
    return True

def parts_for_state(state_str):
    base = state_str.removeprefix("minecraft:")
    name = base.split("[")[0]
    props = {}
    if "[" in base:
        props = dict(kv.split("=") for kv in base[base.index("[") + 1:-1].split(","))
    bs = _read(f"assets/minecraft/blockstates/{name}.json")
    applies = []
    if "variants" in bs:
        for key, v in bs["variants"].items():
            kvs = dict(kv.split("=") for kv in key.split(",")) if key else {}
            if all(props.get(k, "") == val for k, val in kvs.items()):
                applies.append(v[0] if isinstance(v, list) else v)
                break
    else:
        for part in bs.get("multipart", []):
            when = part.get("when")
            if when is None or _match_when(when, props):
                a = part["apply"]
                applies.append(a[0] if isinstance(a, list) else a)
    out = []
    for a in applies:
        elements, texmap = _model_merged(a["model"])
        if a.get("uvlock") and (a.get("x") or a.get("y")):
            warn["uvlock"] += 1
        out.append((_apply_bs_rot(elements, a.get("x", 0), a.get("y", 0)), texmap))
    return out

def auto_uv(face, fr, to):
    x0, y0, z0 = fr; x1, y1, z1 = to
    if face == "down":  return [x0, 16 - z1, x1, 16 - z0]
    if face == "up":    return [x0, z0, x1, z1]
    if face == "north": return [16 - x1, 16 - y1, 16 - x0, 16 - y0]
    if face == "south": return [x0, 16 - y1, x1, 16 - y0]
    if face == "west":  return [z0, 16 - y1, z1, 16 - y0]
    return [16 - z1, 16 - y1, 16 - z0, 16 - y0]  # east

DIRS = {"down": (0, -1, 0), "up": (0, 1, 0), "north": (0, 0, -1),
        "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}

@functools.lru_cache(maxsize=None)
def state_parts_cached(data): return parts_for_state(data)

def is_full_opaque(data):
    parts = state_parts_cached(data)
    boxes = [(tuple(e["from"]), tuple(e["to"])) for els, _ in parts for e in els]
    return boxes == [((0, 0, 0), (16, 16, 16))]

# ---------- 도개교 데이터 로드 ----------
root = json.load(open(src_path))
b = next((x for x in root["list"] if x["id"] == bridge_id), None)
if b is None:
    print(f"'{bridge_id}' 없음. 목록: {[x['id'] for x in root['list']]}"); sys.exit(1)

hinge = b["hingeSide"]
pivotA, pivotY = b["pivotA"], b["pivotY"]
xy_swing = hinge in ("WEST", "EAST")
raw = list(zip(b["deckPos"], b["deckData"]))
print(f"{bridge_id}: 발판 {len(raw)}칸, 경첩={hinge}, pivotA={pivotA}, pivotY={pivotY}")

# 비회전축(n) 최소값 — 앵커 기준점. WEST/EAST면 z가 비회전축, NORTH/SOUTH면 x가 비회전축.
if xy_swing:
    n_min = min(p[2] for p, _ in raw)
else:
    n_min = min(p[0] for p, _ in raw)

# cells: (u, y, n) → blockdata (u=회전축, y=높이, n=비회전축, 전부 정수 코너좌표)
cells = {}
for p, data in raw:
    x, y, z = p
    u = (x - pivotA) if xy_swing else (z - pivotA)
    n = (z - n_min) if xy_swing else (x - n_min)
    yy = y - pivotY
    cells[(u, yy, n)] = data

full_cells = {c for c, d in cells.items() if is_full_opaque(d)}

# ---------- 피벗/스케일 — corner 기준(0,0,0), ship의 (0.5,·,0.5) 블록중심 보정 없음 ----------
us = [c[0] for c in cells]; ys = [c[1] for c in cells]; ns = [c[2] for c in cells]
pivot = (0, 0, 0)  # u=0,y=0 = 실제 회전축 그 자체(corner) — 앵커 스폰 위치와 정확히 일치해야 함
lo = [min(us) - pivot[0], min(ys) - pivot[1], min(ns) - pivot[2]]
hi = [max(us) + 1 - pivot[0], max(ys) + 1 - pivot[1], max(ns) + 1 - pivot[2]]
k = max(max(-l, h) * 16 / 15.5 for l, h in zip(lo, hi))
print(f"pivot={pivot} k={k:.4f} (스팬 {k*31/16:.2f}블록)")

# ---------- 엘리먼트 생성 (bake_ship.py와 동일 로직) ----------
elements, tex_out, exp_boxes = [], {}, []
def tex_var(resolved):
    var = resolved.split("/")[-1]
    while var in tex_out and tex_out[var] != resolved:
        var += "_"
    tex_out[var] = resolved
    return var

for c, data in sorted(cells.items()):
    full = c in full_cells
    for els, texmap in state_parts_cached(data):
        for e in els:
            fr, to = e["from"], e["to"]
            exp_boxes.append(tuple(c[a] + fr[a] / 16 for a in range(3)) +
                             tuple(c[a] + to[a] / 16 for a in range(3)))
            faces = {}
            for fn, fv in e.get("faces", {}).items():
                if full and (tuple(fr), tuple(to)) == ((0, 0, 0), (16, 16, 16)):
                    d = DIRS[fn]
                    if (c[0] + d[0], c[1] + d[1], c[2] + d[2]) in full_cells:
                        continue
                resolved = _resolve_tex(texmap, fv.get("texture", "#missing"))
                nf = {"texture": "#" + tex_var(resolved),
                      "uv": [round(u, 4) for u in fv.get("uv", auto_uv(fn, fr, to))]}
                if fv.get("rotation"): nf["rotation"] = fv["rotation"]
                if "tintindex" in fv: warn["tint"] += 1
                faces[fn] = nf
            if not faces:
                continue
            # ★디스플레이 엔티티 회전은 정규화 모델좌표 (0.5,0.5,0.5)=픽셀(8,8,8) 기준으로 피벗된다
            # (bake_ship.py와 동일 이유) — 우리 회전축(u=0,y=0)이 정확히 그 픽셀8 지점에 오도록 +8.
            ne = {"from": [round(8 + (c[a] - pivot[a]) * 16 / k + fr[a] / k, 4) for a in range(3)],
                  "to":   [round(8 + (c[a] - pivot[a]) * 16 / k + to[a] / k, 4) for a in range(3)],
                  "faces": faces}
            assert all(-16 <= v <= 32 for v in ne["from"] + ne["to"]), f"coord out of range @ {c}: {ne}"
            if "rotation" in e and e["rotation"]:
                r = dict(e["rotation"])
                r["origin"] = [round(8 + (c[a] - pivot[a]) * 16 / k + r["origin"][a] / k, 4) for a in range(3)]
                ne["rotation"] = r
            elements.append(ne)

# ★아이템 렌더 반전 보정(이무기/배와 동일 이유) — ItemDisplay 커스텀 모델은 X/Z가 뒤집혀 렌더된다.
# 배는 회전축이 Y라 렌더타임에 rotateY(180)만 얹으면 됐지만, 우리 회전축은 Z(가로눕기)라 그 방식은
# 스윙 회전과 꼬인다 — 대신 기하 자체를 픽셀8 기준으로 X/Z 미리 미러링(Y는 그대로, 높이축이라 무관).
FLIP_MAP = {"east": "west", "west": "east", "north": "south", "south": "north", "up": "up", "down": "down"}
for e in elements:
    e["from"][0], e["to"][0] = 16 - e["to"][0], 16 - e["from"][0]
    e["from"][2], e["to"][2] = 16 - e["to"][2], 16 - e["from"][2]
    e["faces"] = {FLIP_MAP[f]: v for f, v in e["faces"].items()}
    if "rotation" in e:
        e["rotation"]["origin"][0] = 16 - e["rotation"]["origin"][0]
        e["rotation"]["origin"][2] = 16 - e["rotation"]["origin"][2]

model = {"textures": {**tex_out, "particle": next(iter(tex_out.values()))}, "elements": elements}
json.dump(model, open(os.path.join(MODEL_DIR, mname + ".json"), "w"), separators=(",", ":"))
json.dump({"model": {"type": "minecraft:model", "model": f"barkan:drawbridge/{mname}"}},
          open(os.path.join(ITEM_DIR, mname + ".json"), "w"), separators=(",", ":"))
print(f"model 저장: drawbridge/{mname}.json — elements {len(elements)}, textures {len(tex_out)}")

# ---------- 인라인 검증 (+8 보정 역변환 + x/z 미러 되돌리기) ----------
der = []
for e in elements:
    ux_fr, ux_to = 16 - e["to"][0], 16 - e["from"][0]  # x축 미러 원복
    uz_fr, uz_to = 16 - e["to"][2], 16 - e["from"][2]  # z축 미러 원복
    fr = [pivot[0] + (ux_fr - 8) * k / 16, pivot[1] + (e["from"][1] - 8) * k / 16, pivot[2] + (uz_fr - 8) * k / 16]
    to = [pivot[0] + (ux_to - 8) * k / 16, pivot[1] + (e["to"][1] - 8) * k / 16, pivot[2] + (uz_to - 8) * k / 16]
    der.append(tuple(fr) + tuple(to))
der_left = list(der)
matched = interior = fail = 0
for eb in exp_boxes:
    hit = next((j for j, db in enumerate(der_left) if all(abs(x - y) <= 0.02 for x, y in zip(eb, db))), None)
    if hit is not None:
        der_left.pop(hit); matched += 1
    else:
        bx, by, bz = int(round(eb[0])), int(round(eb[1])), int(round(eb[2]))
        encl = ((bx, by, bz) in full_cells and
                (eb[3] - eb[0], eb[4] - eb[1], eb[5] - eb[2]) == (1.0, 1.0, 1.0) and
                all((bx + d[0], by + d[1], bz + d[2]) in full_cells for d in DIRS.values()))
        if encl: interior += 1
        else: fail += 1; print(f"  !! MISSING box @ {eb[:3]}")
if der_left:
    fail += len(der_left); print(f"  !! EXTRA {len(der_left)}")
print(f"expected {len(exp_boxes)} matched {matched} interior(밀폐컬링) {interior} FAIL {fail}")
print("warns:", warn)

# ---------- 앵커 월드좌표 + 플러그인 디스크립터 ----------
if xy_swing:
    anchor = [pivotA, pivotY, n_min]
else:
    anchor = [n_min, pivotY, pivotA]

desc_path = os.path.join(SCRATCH, "drawbridge-models.json")
desc = json.load(open(desc_path)) if os.path.exists(desc_path) else {}
desc[bridge_id] = {
    "item_model": f"barkan:drawbridge/{mname}",
    "scale": round(k, 6),
    "anchor": anchor,
    "hingeSide": hinge,
}
json.dump(desc, open(desc_path, "w"), ensure_ascii=False, indent=1)
print("drawbridge-models.json 갱신:", desc[bridge_id])
print("VERIFY", "PASS" if fail == 0 else "FAIL")
