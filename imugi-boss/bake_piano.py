#!/usr/bin/env python3
"""피아노 몸통 bake — 업스트림 mcfunction 의 block_display 패신저를 RP 모델로 굽는다.

왜: 피아노 1대가 block_display 523개다(2026-09-16 prod 실측). 건반 89개는 업스트림이
    Y오프셋+재질로 찾아 애니메이션하므로 «절대» 건드리면 안 되고, 나머지 430개가 대상.

어떻게: 430개를 회전으로 분류한다.
  - 90° 배수 / 단위행렬  → 박스 치수를 교환해 «본체 모델»에 정확히 구움 (손실 0)
  - ≤5° 기울기          → 0 으로 스냅해 본체에 포함 (육안 무시)
  - 그 외 회전          → 같은 회전끼리 묶어 그룹 모델 + 전용 ItemDisplay(임의 쿼터니언 가능)
  - 묶어도 3개 미만인 자투리 → 굽지 않고 block_display 로 남긴다(엔티티 수가 같아 이득 없음)

출력: RP assets/barkan/models/piano/*.json + items/piano/*.json
      plugins/BlockShip/piano-body.json (런타임 디스크립터: 본체 배치 + 보존할 패신저 좌표)

사용: python3 bake_piano.py [피아노jar경로]
"""
import json, os, re, sys, math, zipfile, subprocess
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vanilla_model import parts_for_state, _resolve_tex, auto_uv

PIANO_JAR = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BarkanPiano-1.21.11.jar")
RP  = os.path.expanduser("~/development/barkan-resourcepack")
BS  = os.path.expanduser("~/Library/Application Support/feather/player-server/servers/"
                         "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
MODEL_DIR = os.path.join(RP, "assets/barkan/models/piano")
ITEM_DIR  = os.path.join(RP, "assets/barkan/items/piano")
os.makedirs(MODEL_DIR, exist_ok=True); os.makedirs(ITEM_DIR, exist_ok=True)

WHITE_Y, BLACK_Y, Y_TOL = 1.0899, 1.1384, 0.08      # 업스트림 indexPianoKeys 와 동일해야 한다
SNAP_DEG = 0.0   # ★스냅 금지. 2026-09-16: 5° 스냅이 4블록 판의 꼭짓점을 0.25블록 밀어 «뚜껑 각짐»을 만들었다.
MIN_GROUP = 1                                        # 1 = 자투리 없이 전부 굽는다(누락 0). 2026-09-16 검증기가 뚜껑·뒷판·받침막대 누락을 잡아 3→1.

# ---------- 1) mcfunction 파싱 ----------
cubes = []
with zipfile.ZipFile(PIANO_JAR) as z:
    names = [n for n in z.namelist() if n.startswith("models/") and n.endswith(".mcfunction")]
    for idx, n in enumerate(sorted(names)):
        s = z.read(n).decode("utf-8", "replace")
        for m in re.finditer(r'block_state:\{Name:"minecraft:([a-z_]+)"(?:,Properties:\{([^}]*)\})?\},'
                             r'transformation:\[([^\]]+)\]', s):
            name, props, tr = m.group(1), m.group(2) or "", m.group(3)
            v = [float(x.rstrip('f')) for x in tr.split(',')]
            if len(v) < 16: continue
            ty = v[7]
            is_key = ((name == "quartz_block" and abs(ty - WHITE_Y) < Y_TOL) or
                      (name == "polished_blackstone_slab" and abs(ty - BLACK_Y) < Y_TOL))
            state = name if not props else name + "[" + props.replace('"', '').replace(":", "=") + "]"
            cubes.append(dict(root=idx, name=name, state=state, m=v, key=is_key,
                              t=(v[3], v[7], v[11])))
print(f"패신저 {len(cubes)}개 (건반 {sum(1 for c in cubes if c['key'])} / 몸통 {sum(1 for c in cubes if not c['key'])})")

# ---------- 2) 회전 분류 ----------
def linear(v):   # 3x3 선형부를 열벡터로
    return [(v[0], v[4], v[8]), (v[1], v[5], v[9]), (v[2], v[6], v[10])]

def decomp(v):
    """4x4 → (정규화 회전 3x3, 축별 스케일)."""
    cols = linear(v); R = []; S = []
    for c in cols:
        n = math.sqrt(sum(x*x for x in c)) or 1e-9
        S.append(n); R.append(tuple(x/n for x in c))
    return R, S

def is_axis90(R, tol=0.03):
    return all(abs(abs(x)) < tol or abs(abs(x)-1) < tol for col in R for x in col)

def tilt_deg(R):
    tr = R[0][0] + R[1][1] + R[2][2]
    return math.degrees(math.acos(max(-1.0, min(1.0, (tr - 1) / 2))))

main, groups, leftover = [], defaultdict(list), []
for c in cubes:
    if c["key"]: continue
    R, S = decomp(c["m"]); c["R"], c["S"] = R, S
    if is_axis90(R) or (SNAP_DEG > 0 and tilt_deg(R) <= SNAP_DEG):
        main.append(c)
    else:
        # 3자리 양자화가 최적 — 2자리는 서로 다른 회전이 뭉쳐 0.64블록 오차,
        # 4자리 이상은 오차가 같은데 그룹(=ItemDisplay) 수만 늘어난다 (2026-09-16 실측).
        groups[tuple(round(x, 3) for col in R for x in col)].append(c)

for k in list(groups):
    if len(groups[k]) < MIN_GROUP:
        leftover.extend(groups.pop(k))
print(f"본체 {len(main)} / 그룹 {len(groups)}종 {sum(len(v) for v in groups.values())}개 / 자투리 {len(leftover)}개")
print(f"→ 예상 엔티티: 건반 {sum(1 for c in cubes if c['key'])} + 본체 1 + 그룹 {len(groups)} + 자투리 {len(leftover)}"
      f" = {sum(1 for c in cubes if c['key']) + 1 + len(groups) + len(leftover)}  (현재 {len(cubes)+4})")
json.dump({"main": len(main), "groups": {str(k): len(v) for k, v in groups.items()},
           "leftover": len(leftover)}, open("/tmp/piano_buckets.json", "w"), indent=1)

# ---------- 3) 기하 방출 ----------
def mat_apply(v, p):
    """4x4(row-major) × (x,y,z,1) → (x,y,z)"""
    return (v[0]*p[0]+v[1]*p[1]+v[2]*p[2]+v[3],
            v[4]*p[0]+v[5]*p[1]+v[6]*p[2]+v[7],
            v[8]*p[0]+v[9]*p[1]+v[10]*p[2]+v[11])

def cube_boxes(c, inv_rot=None):
    """큐브 → [(lo, hi, faces, texmap)] 피아노 로컬(블록 단위) AABB.
    inv_rot 이 주어지면(그룹 모델) 그 회전의 역을 먼저 곱해 축정렬 프레임으로 되돌린다."""
    out = []
    for elements, texmap in parts_for_state(c["state"]):
        for e in elements:
            fr, to = e["from"], e["to"]
            pts = []
            for ix in (0, 1):
                for iy in (0, 1):
                    for iz in (0, 1):
                        p = ((fr[0] if ix == 0 else to[0]) / 16.0,
                             (fr[1] if iy == 0 else to[1]) / 16.0,
                             (fr[2] if iz == 0 else to[2]) / 16.0)
                        q = mat_apply(c["m"], p)
                        if inv_rot:
                            q = (inv_rot[0][0]*q[0]+inv_rot[0][1]*q[1]+inv_rot[0][2]*q[2],
                                 inv_rot[1][0]*q[0]+inv_rot[1][1]*q[1]+inv_rot[1][2]*q[2],
                                 inv_rot[2][0]*q[0]+inv_rot[2][1]*q[1]+inv_rot[2][2]*q[2])
                        pts.append(q)
            lo = [min(p[i] for p in pts) for i in range(3)]
            hi = [max(p[i] for p in pts) for i in range(3)]
            out.append((lo, hi, e.get("faces", {}), texmap))
    return out

def emit_model(cube_list, name, inv_rot=None):
    """모델 JSON 생성. 스팬≤31유닛이 되도록 k 로 줄이고, (k, pivot) 을 돌려준다."""
    boxes = []
    for c in cube_list: boxes += cube_boxes(c, inv_rot)
    if not boxes: return None
    lo = [min(b[0][i] for b in boxes) for i in range(3)]
    hi = [max(b[1][i] for b in boxes) for i in range(3)]
    ctr = [(lo[i] + hi[i]) / 2 for i in range(3)]
    span = max(hi[i] - lo[i] for i in range(3))
    k = max(1e-6, span * 16 / 31.0)          # 모델 좌표를 31유닛 안에 넣는다
    tex_ids, elements = {}, []
    for blo, bhi, faces, texmap in boxes:
        f = [(blo[i] - ctr[i]) / k * 16 + 8 for i in range(3)]
        t = [(bhi[i] - ctr[i]) / k * 16 + 8 for i in range(3)]
        for i in range(3):
            if t[i] - f[i] < 0.01: t[i] = f[i] + 0.01     # 0두께 방지
        ne = {"from": [round(x, 4) for x in f], "to": [round(x, 4) for x in t], "faces": {}}
        for face, fd in faces.items():
            res = _resolve_tex(texmap, fd.get("texture", "#all"))
            var = tex_ids.setdefault(res, "t%d" % len(tex_ids))
            ne["faces"][face] = {"uv": [round(u, 3) for u in (fd.get("uv") or auto_uv(face, ne["from"], ne["to"]))],
                                 "texture": "#" + var}
        if ne["faces"]: elements.append(ne)
    model = {"textures": {v: k2.removeprefix("minecraft:") for k2, v in tex_ids.items()},
             "elements": elements}
    json.dump(model, open(os.path.join(MODEL_DIR, name + ".json"), "w"), separators=(",", ":"))
    json.dump({"model": {"type": "minecraft:model", "model": f"barkan:piano/{name}"}},
              open(os.path.join(ITEM_DIR, name + ".json"), "w"), separators=(",", ":"))
    return {"model": f"barkan:piano/{name}", "k": round(k, 6),
            "center": [round(x, 6) for x in ctr], "elements": len(elements)}

def mat3_rows(R):
    """R 은 «열벡터» 3개. 회전행렬 M(row-major): M[r][c] = R[c][r]."""
    return [[R[0][0], R[1][0], R[2][0]], [R[0][1], R[1][1], R[2][1]], [R[0][2], R[1][2], R[2][2]]]

def mat3_inv(R):
    """정규직교이므로 역 = 전치. 전치의 row-major 는 R 을 그대로 행으로 읽은 것."""
    return [list(R[0]), list(R[1]), list(R[2])]

def quat_of(R):  # 열벡터 3x3 → (x,y,z,w)
    m = [[R[0][0], R[1][0], R[2][0]], [R[0][1], R[1][1], R[2][1]], [R[0][2], R[1][2], R[2][2]]]
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2; w = 0.25*s
        x = (m[2][1]-m[1][2])/s; y = (m[0][2]-m[2][0])/s; z = (m[1][0]-m[0][1])/s
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0+m[0][0]-m[1][1]-m[2][2])*2; w=(m[2][1]-m[1][2])/s
        x=0.25*s; y=(m[0][1]+m[1][0])/s; z=(m[0][2]+m[2][0])/s
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0+m[1][1]-m[0][0]-m[2][2])*2; w=(m[0][2]-m[2][0])/s
        x=(m[0][1]+m[1][0])/s; y=0.25*s; z=(m[1][2]+m[2][1])/s
    else:
        s = math.sqrt(1.0+m[2][2]-m[0][0]-m[1][1])*2; w=(m[1][0]-m[0][1])/s
        x=(m[0][2]+m[2][0])/s; y=(m[1][2]+m[2][1])/s; z=0.25*s
    return [round(v, 6) for v in (x, y, z, w)]

def mat3_mul_vec(M, v):
    return [M[0][0]*v[0]+M[0][1]*v[1]+M[0][2]*v[2],
            M[1][0]*v[0]+M[1][1]*v[1]+M[1][2]*v[2],
            M[2][0]*v[0]+M[2][1]*v[1]+M[2][2]*v[2]]

bodies = []
r = emit_model(main, "body_main")
if r: bodies.append({**r, "rot": [0.0, 0.0, 0.0, 1.0], "pos": r["center"]})
for gi, (key, cl) in enumerate(sorted(groups.items(), key=lambda kv: -len(kv[1]))):
    R = [tuple(key[0:3]), tuple(key[3:6]), tuple(key[6:9])]   # 열벡터
    rr = emit_model(cl, f"body_g{gi}", inv_rot=mat3_inv(R))
    if rr:
        # center 는 «회전된 프레임» 좌표라 R 로 되돌려야 월드(피아노 로컬) 위치가 된다
        Rrow = mat3_rows(R)
        bodies.append({**rr, "rot": quat_of(R),
                       "pos": [round(x, 6) for x in mat3_mul_vec(Rrow, rr["center"])]})

# yaw 해석용 기준: 검은건반 후보들의 XZ 중심(회전 0 기준). 런타임이 라이브 값과 대조해
# 피아노 설치 회전(0/90/180/270)을 «데이터에서» 알아낸다 — pianos.yml 파싱 의존을 피한다.
blk = [c["t"] for c in cubes if c["key"] and c["name"] == "polished_blackstone_slab"]
ref = [round(sum(t[i] for t in blk) / len(blk), 6) for i in (0, 2)] if blk else [0.0, 0.0]

desc = {"bodies": bodies, "ref_black_xz": ref,
        "keep": [[round(x, 5) for x in c["t"]] for c in leftover],
        "note": "pos/rot 은 회전 0 기준 피아노 로컬. 런타임이 ref_black_xz 로 설치 yaw 를 구해 덧씌운다."}
json.dump(desc, open(os.path.join(BS, "piano-body.json"), "w"), ensure_ascii=False, indent=1)
print(f"\n모델 {len(bodies)}개 생성 (요소 합계 {sum(b['elements'] for b in bodies)})")
for b in bodies: print(f"  {b['model']}  요소 {b['elements']:4d}  k={b['k']:.4f}")
print(f"디스크립터: {os.path.join(BS,'piano-body.json')}  (보존 {len(desc['keep'])}개)")
