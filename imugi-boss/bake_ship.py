#!/usr/bin/env python3
"""배 blueprint → 단일 선체 RP 모델 bake + 인라인 수치검증 (이무기 파이프라인의 배 버전).

소스: plugins/BlockShip/ships/<프리셋>.json (풀 blockstate 저장돼 있어 월드 스캔 불필요)
- 돛/깃발(animGroup)도 함께 bake — BlockDisplay 0개 (2026-09-05: 돛 엔티티 제거, 빌로잉 애니 포기)
- blueprint 의 per-block scale(얇은 돛 [1,1,0.15] 등)은 셀 원점 기준으로 기하에 곱해 재현
  (BlockDisplay Transformation 의 scale 이 원점 코너 기준이라 동일)
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

from vanilla_model import (_read, _model_merged, _resolve_tex, _rot90_box,
                           Y_MAP, X_MAP, warn, _apply_bs_rot, _match_when,
                           parts_for_state, auto_uv, DIRS)

# ---------- blueprint 로드 ----------
bp = json.load(open(os.path.join(SHIPS, preset + ".json")))
anim = [b for b in bp["blocks"] if b.get("animGroup")]
print(f"{preset}: 전체 {len(bp['blocks'])} 블록 전부 bake (애니 블록 {len(anim)}개 포함 — BlockDisplay 0개)")

cells, scales = {}, {}
for b in bp["blocks"]:
    c = (b["x"], b["y"], b["z"])
    cells[c] = b["data"]
    sc = b.get("scale")
    if sc and tuple(float(v) for v in sc) != (1.0, 1.0, 1.0):
        scales[c] = [float(v) for v in sc]

@functools.lru_cache(maxsize=None)
def state_parts_cached(data): return parts_for_state(data)

def is_full_opaque(data):
    """컬링용: 이 상태가 정확히 풀큐브 1개인가 (glass류 없음 — 팔레트가 목재/양털/석재라 불투명 전제)."""
    parts = state_parts_cached(data)
    boxes = [(tuple(e["from"]), tuple(e["to"])) for els, _ in parts for e in els]
    return boxes == [((0, 0, 0), (16, 16, 16))]

# 축소된 셀(얇은 돛)은 풀큐브가 아니므로 컬링 대상에서 제외
full_cells = {c for c, d in cells.items() if c not in scales and is_full_opaque(d)}

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
    sc = scales.get(c)
    for els, texmap in state_parts_cached(data):
        for e in els:
            fr0, to0 = e["from"], e["to"]
            fr = [fr0[a] * sc[a] for a in range(3)] if sc else fr0
            to = [to0[a] * sc[a] for a in range(3)] if sc else to0
            exp_boxes.append(tuple(c[a] + fr[a] / 16 for a in range(3)) +
                             tuple(c[a] + to[a] / 16 for a in range(3)))
            faces = {}
            for fn, fv in e.get("faces", {}).items():
                if full and (tuple(fr), tuple(to)) == ((0, 0, 0), (16, 16, 16)):
                    d = DIRS[fn]
                    if (c[0] + d[0], c[1] + d[1], c[2] + d[2]) in full_cells:
                        continue  # 선체 내부 맞닿은 면 컬링
                resolved = _resolve_tex(texmap, fv.get("texture", "#missing"))
                # UV 는 축소 전 기하 기준 (돛 텍스처가 눌리지 않게)
                nf = {"texture": "#" + tex_var(resolved),
                      "uv": [round(u, 4) for u in fv.get("uv", auto_uv(fn, fr0, to0))]}
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
                r["origin"] = [round(8 + (c[a] - pivot[a]) * 16 / k
                                     + r["origin"][a] * (sc[a] if sc else 1.0) / k, 4) for a in range(3)]
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
