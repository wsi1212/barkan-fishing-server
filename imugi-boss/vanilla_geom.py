#!/usr/bin/env python3
"""바닐라 클라 jar에서 blockstate→모델 박스(AABB) 기하를 추출하는 ground-truth 모듈.
convert_imugi.py의 손코딩 기하와 독립적으로, 실제 바닐라 파일에서 파생한다.
"""
import json, zipfile, functools, os

JAR = os.path.expanduser("~/Library/Application Support/minecraft/versions/1.20.1/1.20.1.jar")
_zf = zipfile.ZipFile(JAR)

@functools.lru_cache(maxsize=None)
def _read(path):
    with _zf.open(path) as f:
        return json.load(f)

def _model_elements(model_id):
    """모델 id (minecraft:block/xxx) → parent 체인 병합 elements (없으면 [])."""
    mid = model_id.removeprefix("minecraft:")
    data = _read(f"assets/minecraft/models/{mid}.json")
    if "elements" in data:
        return data["elements"]
    if "parent" in data:
        return _model_elements(data["parent"])
    return []

def _rot90_box(fr, to, axis, times, ):
    """블록 중심(8,8,8) 기준 90°×times 회전. 바닐라 blockstate 회전은 시계방향(위에서 봤을 때 y+는 CW)."""
    fr, to = list(fr), list(to)
    for _ in range(times % 4):
        if axis == "y":
            # 바닐라 y회전(양수)=위에서 볼 때 시계방향: (x,z) -> (16-z, x)
            nf = (16 - to[2], fr[1], fr[0]); nt = (16 - fr[2], to[1], to[0])
        elif axis == "x":
            # x회전(양수): (y,z) -> (z, 16-y)  [동쪽에서 본 시계방향]
            nf = (fr[0], fr[2], 16 - to[1]); nt = (to[0], to[2], 16 - fr[1])
        else:
            raise ValueError(axis)
        fr, to = list(nf), list(nt)
    return tuple(fr), tuple(to)

def _apply_variant(elements, xrot, yrot):
    out = []
    for e in elements:
        fr, to = tuple(e["from"]), tuple(e["to"])
        fr, to = _rot90_box(fr, to, "x", xrot // 90)
        fr, to = _rot90_box(fr, to, "y", yrot // 90)
        out.append((tuple(round(v, 4) for v in fr), tuple(round(v, 4) for v in to)))
    return out

def _match_when(when, props):
    if "OR" in when:
        return any(_match_when(w, props) for w in when["OR"])
    for k, v in when.items():
        pv = props.get(k)
        if pv is None: return False
        if pv not in str(v).split("|"): return False
    return True

def boxes_for_state(state_str):
    """'minecraft:xxx[a=b,c=d]' → 로컬(0..16) AABB 리스트. 풀블록 인식 포함."""
    if "[" in state_str:
        block = state_str[:state_str.index("[")].removeprefix("minecraft:")
        props = dict(kv.split("=") for kv in state_str[state_str.index("[")+1:-1].split(","))
    else:
        block, props = state_str.removeprefix("minecraft:"), {}
    bs = _read(f"assets/minecraft/blockstates/{block}.json")
    picked = []  # (model, x, y)
    if "variants" in bs:
        for key, val in bs["variants"].items():
            kv = dict(p.split("=") for p in key.split(",")) if key else {}
            if all(props.get(k) == v for k, v in kv.items()):
                v = val[0] if isinstance(val, list) else val
                picked.append((v["model"], v.get("x", 0), v.get("y", 0)))
                break
    else:  # multipart
        for part in bs["multipart"]:
            if "when" not in part or _match_when(part["when"], props):
                v = part["apply"]
                v = v[0] if isinstance(v, list) else v
                picked.append((v["model"], v.get("x", 0), v.get("y", 0)))
    boxes = []
    for model, x, y in picked:
        boxes.extend(_apply_variant(_model_elements(model), x, y))
    return boxes

if __name__ == "__main__":
    # 스모크 테스트: 이무기 팔레트의 상태 대표들
    tests = [
        "minecraft:prismarine_slab[type=bottom,waterlogged=false]",
        "minecraft:prismarine_slab[type=top,waterlogged=false]",
        "minecraft:prismarine_slab[type=double,waterlogged=false]",
        "minecraft:red_nether_brick_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]",
        "minecraft:dark_prismarine_stairs[facing=east,half=top,shape=straight,waterlogged=false]",
        "minecraft:polished_blackstone_brick_wall[east=none,north=low,south=none,up=true,waterlogged=false,west=tall]",
    ]
    for t in tests:
        print(t.split(":")[1][:60])
        for fr, to in boxes_for_state(t):
            print("   ", fr, "->", to)
