#!/usr/bin/env python3
"""배 blueprint → 단일 선체 RP 모델 bake + 인라인 수치검증 (이무기 파이프라인의 배 버전).

소스: plugins/BlockShip/ships/<프리셋>.json (풀 blockstate 저장돼 있어 월드 스캔 불필요)
- animGroup 블록(돛/깃발)은 제외 — 계속 BlockDisplay로 빌로잉 애니 유지
- 면 텍스처/UV/회전/기하 전부 바닐라 클라 jar에서 직접 해석 (이무기식 수동 TEX 매핑 없음)
- ★렌더 레시피(이무기서 실측 확정): 스팬≤31유닛 bake(k=최대반경×16/15.5, 클라 자동축소 미발동 f=1),
  스폰 left_rotation = yaw회전 × Y180
- 회전 피벗 = 배 로컬 (0.5, ymid, 0.5) — Ship.rotateOffset+블록중심 보정과 동일한 강체 회전 중심.
  ymid는 스팬 최소화용(y는 yaw 회전에 무관).

사용: python3 bake_ship.py <프리셋이름> <영문모델명>   예) python3 bake_ship.py 범선 beomseon
출력: RP models/items + plugins/BlockShip/ship-models.json 갱신 + 검증 리포트
"""
import json, os, sys, zipfile, functools

SCRATCH = os.path.dirname(os.path.abspath(__file__))
JAR = os.path.expanduser("~/Library/Application Support/minecraft/versions/1.21.11/1.21.11.jar")
SHIPS = os.path.expanduser("~/Library/Application Support/feather/player-server/servers/"
                           "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip/ships")
BS_DATA = os.path.expanduser("~/Library/Application Support/feather/player-server/servers/"
                             "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
RP = os.path.expanduser("~/development/barkan-resourcepack")

preset = sys.argv[1] if len(sys.argv) > 1 else "범선"
mname = sys.argv[2] if len(sys.argv) > 2 else "ship0"
MODEL_DIR = os.path.join(RP, "assets/barkan/models/ship")
ITEM_DIR = os.path.join(RP, "assets/barkan/items/ship")
os.makedirs(MODEL_DIR, exist_ok=True); os.makedirs(ITEM_DIR, exist_ok=True)

# ---------- 바닐라 자산 해석 ----------
_zf = zipfile.ZipFile(JAR)

@functools.lru_cache(maxsize=None)
def _read(path):
    with _zf.open(path) as f:
        return json.load(f)

@functools.lru_cache(maxsize=None)
def _model_merged(model_id):
    """모델 id → parent 체인 병합: elements(자식 우선) + textures(자식 우선 병합)."""
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

# 90° 박스 회전 (vanilla_geom과 동일 수학) + 면 방향 리맵
def _rot90_box(fr, to, axis):
    if axis == "y":   # 위에서 볼 때 CW: (x,z) -> (16-z, x)
        nf = (16 - to[2], fr[1], fr[0]); nt = (16 - fr[2], to[1], to[0])
    else:             # x: (y,z) -> (z, 16-y)
        nf = (fr[0], fr[2], 16 - to[1]); nt = (to[0], to[2], 16 - fr[1])
    return list(nf), list(nt)

Y_MAP = {"north": "east", "east": "south", "south": "west", "west": "north", "up": "up", "down": "down"}
X_MAP = {"north": "down", "down": "south", "south": "up", "up": "north", "east": "east", "west": "west"}

warn = {"rot_elem_under_bsrot": 0, "tint": 0, "uvlock": 0}

def _apply_bs_rot(elements, xrot, yrot):
    """blockstate x/y 회전을 elements(박스+면방향+엘리먼트 회전 origin)에 적용."""
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
            # 엘리먼트 회전의 origin/axis도 리맵 필요 — 팔레트상 드묾, 발생 시 카운트만 (시각 미세 오차 감수)
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
    """blockstate 문자열 → [(elements, texmap)] 적용 목록 (variants/multipart, x/y 회전 반영)."""
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
            warn["uvlock"] += 1  # 균일 텍스처 위주라 무시 (시각 영향 미미)
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

# ---------- blueprint 로드 ----------
bp = json.load(open(os.path.join(SHIPS, preset + ".json")))
hull = [b for b in bp["blocks"] if not b.get("animGroup")]
sails = [b for b in bp["blocks"] if b.get("animGroup")]
print(f"{preset}: 전체 {len(bp['blocks'])} = 선체 {len(hull)} + 애니(돛) {len(sails)} (돛은 BlockDisplay 유지)")

cells = {}
for b in hull:
    cells[(b["x"], b["y"], b["z"])] = b["data"]

@functools.lru_cache(maxsize=None)
def state_parts_cached(data): return parts_for_state(data)

def is_full_opaque(data):
    """컬링용: 이 상태가 정확히 풀큐브 1개인가 (glass류 없음 — 팔레트가 목재/양털/석재라 불투명 전제)."""
    parts = state_parts_cached(data)
    boxes = [(tuple(e["from"]), tuple(e["to"])) for els, _ in parts for e in els]
    return boxes == [((0, 0, 0), (16, 16, 16))]

full_cells = {c for c, d in cells.items() if is_full_opaque(d)}

# ---------- 피벗/스케일 ----------
xs = [c[0] for c in cells]; ys = [c[1] for c in cells]; zs = [c[2] for c in cells]
pivot = (0.5, (min(ys) + max(ys) + 1) / 2, 0.5)  # XZ는 회전 중심 고정, Y는 스팬 최소화
lo = [min(xs) - pivot[0], min(ys) - pivot[1], min(zs) - pivot[2]]
hi = [max(xs) + 1 - pivot[0], max(ys) + 1 - pivot[1], max(zs) + 1 - pivot[2]]
k = max(max(-l, h) * 16 / 15.5 for l, h in zip(lo, hi))  # 스팬≤31유닛 → 클라 자동축소 미발동(f=1)
print(f"pivot={pivot} k={k:.4f} (스팬 {k*31/16:.1f}블록)")

# ---------- 엘리먼트 생성 ----------
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
                        continue  # 선체 내부 맞닿은 면 컬링
                resolved = _resolve_tex(texmap, fv.get("texture", "#missing"))
                nf = {"texture": "#" + tex_var(resolved),
                      "uv": [round(u, 4) for u in fv.get("uv", auto_uv(fn, fr, to))]}
                if fv.get("rotation"): nf["rotation"] = fv["rotation"]
                if "tintindex" in fv: warn["tint"] += 1
                faces[fn] = nf
            if not faces:
                continue
            ne = {"from": [round(8 + (c[a] - pivot[a]) * 16 / k + fr[a] / k, 4) for a in range(3)],
                  "to":   [round(8 + (c[a] - pivot[a]) * 16 / k + to[a] / k, 4) for a in range(3)],
                  "faces": faces}
            assert all(-16 <= v <= 32 for v in ne["from"] + ne["to"]), f"coord out of range @ {c}"
            if "rotation" in e and e["rotation"]:
                r = dict(e["rotation"])
                r["origin"] = [round(8 + (c[a] - pivot[a]) * 16 / k + r["origin"][a] / k, 4) for a in range(3)]
                ne["rotation"] = r
            elements.append(ne)

model = {"textures": {**tex_out, "particle": next(iter(tex_out.values()))}, "elements": elements}
json.dump(model, open(os.path.join(MODEL_DIR, mname + ".json"), "w"), separators=(",", ":"))
json.dump({"model": {"type": "minecraft:model", "model": f"barkan:ship/{mname}"}},
          open(os.path.join(ITEM_DIR, mname + ".json"), "w"), separators=(",", ":"))
print(f"model 저장: ship/{mname}.json — elements {len(elements)}, textures {len(tex_out)}")

# ---------- 인라인 검증: 모델 역변환 vs 기대 박스 ----------
der = [tuple(pivot[a] + (e["from"][a] / 16 - 0.5) * k for a in range(3)) +
       tuple(pivot[a] + (e["to"][a] / 16 - 0.5) * k for a in range(3)) for e in elements]
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

# ---------- 플러그인 디스크립터 ----------
desc_path = os.path.join(BS_DATA, "ship-models.json")
desc = json.load(open(desc_path)) if os.path.exists(desc_path) else {}
desc[preset] = {"item_model": f"barkan:ship/{mname}", "scale": round(k, 6), "pivot_y": pivot[1]}
json.dump(desc, open(desc_path, "w"), ensure_ascii=False, indent=1)
print("ship-models.json 갱신:", desc[preset])
print("VERIFY", "PASS" if fail == 0 else "FAIL")
