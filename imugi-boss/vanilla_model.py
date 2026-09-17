#!/usr/bin/env python3
"""바닐라 클라 jar(1.21.11) → blockstate 별 «텍스처까지 붙은» 모델 기하 해석.

bake_ship.py 안에 있던 것을 공용으로 뺐다(2026-09-16) — 피아노 베이커가 같은 해석을
써야 하는데, 사본을 만들면 두 베이커가 서로 다른 규칙으로 갈라진다.
AABB 만 필요하면 vanilla_geom.py(1.20.1) 쪽이고, 이건 면/UV/텍스처가 필요한 경우다.
"""
import json, os, zipfile, functools

JAR = os.path.expanduser("~/Library/Application Support/minecraft/versions/1.21.11/1.21.11.jar")

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
