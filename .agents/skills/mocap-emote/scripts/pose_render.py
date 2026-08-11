#!/usr/bin/env python3
"""steve.bbmodel(BetterModel 13본 리그) 애니메이션 오프라인 프리뷰 렌더러.

matplotlib/numpy 없이 PIL + 순수 python 벡터연산만 사용(이 환경엔 numpy가 없음).
Blockbench catmullrom 보간은 선형으로 근사(진폭·타이밍·에너지 검수용이지 바이트
단위 재현 목적 아님 — 실제 z-fight/메시 이음새 같은 텍스처 레벨 아티팩트는 이 렌더러로
못 봄, 그건 인게임에서만 확인 가능).

단독 실행:
    python3 pose_render.py <bbmodel경로> <애니이름> [--out out.png] [--frames 10]

라이브러리로 임포트해서 쓰는 함수: build_hierarchy, pose_world, get_pt, SEGMENTS,
render_dual_view (retarget.py의 preview 커맨드가 이걸 호출한다).
"""
import argparse
import json
import math

from PIL import Image, ImageDraw, ImageFont


def load(path):
    return json.load(open(path))


def build_hierarchy(d):
    groups_by_uuid = {g["uuid"]: g for g in d["groups"]}
    parent_of = {}

    def walk(node, parent_uuid):
        if isinstance(node, str):
            return
        uuid = node["uuid"]
        if uuid in groups_by_uuid:
            parent_of[uuid] = parent_uuid
            for c in node.get("children", []):
                walk(c, uuid)
        else:
            for c in node.get("children", []):
                walk(c, parent_uuid)

    for top in d["outliner"]:
        walk(top, None)

    name_of_uuid = {u: g["name"] for u, g in groups_by_uuid.items()}
    hier = {}
    for u, g in groups_by_uuid.items():
        pu = parent_of.get(u)
        hier[g["name"]] = {"origin": g["origin"], "parent": name_of_uuid.get(pu) if pu else None}
    return hier


def build_anim_index(d):
    return {a["name"]: a for a in d["animations"]}


def channel_series(anim, bone_name, channel):
    for bkey, banim in anim["animators"].items():
        if banim.get("name") != bone_name:
            continue
        kfs = [kf for kf in banim["keyframes"] if kf["channel"] == channel]
        if not kfs:
            return None
        kfs.sort(key=lambda k: float(k["time"]))
        out = []
        for kf in kfs:
            dp = kf["data_points"][0]
            vals = [float(dp.get(ax, "0") or 0) for ax in ("x", "y", "z")]
            out.append((float(kf["time"]), vals))
        return out
    return None


def sample_series(series, t, loop_length=None):
    if series is None:
        return [0.0, 0.0, 0.0]
    if len(series) == 1:
        return series[0][1]
    times = [s[0] for s in series]
    if loop_length is not None and t > times[-1]:
        t = t % loop_length
    if t <= times[0]:
        return series[0][1]
    if t >= times[-1]:
        return series[-1][1]
    for i in range(len(series) - 1):
        t0, v0 = series[i]; t1, v1 = series[i + 1]
        if t0 <= t <= t1:
            f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return [v0[k] + (v1[k] - v0[k]) * f for k in range(3)]
    return series[-1][1]


def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mat_vec(m, v):
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


def rot_x(deg):
    r = math.radians(deg); c, s = math.cos(r), math.sin(r)
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def rot_y(deg):
    r = math.radians(deg); c, s = math.cos(r), math.sin(r)
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def rot_z(deg):
    r = math.radians(deg); c, s = math.cos(r), math.sin(r)
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def euler_mat(rx, ry, rz):
    return mat_mul(mat_mul(rot_z(rz), rot_y(ry)), rot_x(rx))


CHAIN_ORDER = [
    "player_root", "phip_hip", "pw_waist", "pc_chest", "h_ph_head",
    "pra_right_arm", "prfa_right_forearm", "pla_left_arm", "plfa_left_forearm",
    "prl_right_leg", "prfl_right_foreleg", "pll_left_leg", "plfl_left_foreleg",
]

END_EXTENSION = {
    "prfa_right_forearm": (0.625, -5.625, 0), "plfa_left_forearm": (-0.625, -5.625, 0),
    "prfl_right_foreleg": (0, -5.625, 0), "plfl_left_foreleg": (0, -5.625, 0),
    "h_ph_head": (0, 0, 3.2),
}


def pose_world(hier, anim, t, loop_length=None):
    world = {}
    for bone in CHAIN_ORDER:
        info = hier[bone]
        origin = info["origin"]; parent = info["parent"]
        anim_rot = sample_series(channel_series(anim, bone, "rotation"), t, loop_length)
        anim_pos = sample_series(channel_series(anim, bone, "position"), t, loop_length)
        local_rot = euler_mat(*anim_rot)
        if parent is None:
            base = [origin[i] + anim_pos[i] for i in range(3)]
            world[bone] = (base, local_rot)
        else:
            p_pos, p_rot = world[parent]
            p_origin = hier[parent]["origin"]
            offset = [origin[i] - p_origin[i] + anim_pos[i] for i in range(3)]
            offset_rotated = mat_vec(p_rot, offset)
            w_pos = [p_pos[i] + offset_rotated[i] for i in range(3)]
            w_rot = mat_mul(p_rot, local_rot)
            world[bone] = (w_pos, w_rot)
    return world


def end_point(bone, world):
    pos, rot = world[bone]
    ext = END_EXTENSION.get(bone)
    if ext is None:
        return pos
    v = mat_vec(rot, list(ext))
    return [pos[i] + v[i] for i in range(3)]


def get_pt(name, world):
    if name.startswith("*"):
        return end_point(name[1:], world)
    return world[name][0]


COLORS = {"spine": (255, 210, 90), "arm_r": (90, 200, 255), "arm_l": (255, 120, 120),
          "leg_r": (120, 255, 150), "leg_l": (200, 150, 255)}
SEGMENTS_COLORED = [
    ("phip_hip", "pw_waist", "spine"), ("pw_waist", "pc_chest", "spine"),
    ("pc_chest", "h_ph_head", "spine"), ("h_ph_head", "*h_ph_head", "spine"),
    ("pc_chest", "pra_right_arm", "arm_r"), ("pra_right_arm", "prfa_right_forearm", "arm_r"),
    ("prfa_right_forearm", "*prfa_right_forearm", "arm_r"),
    ("pc_chest", "pla_left_arm", "arm_l"), ("pla_left_arm", "plfa_left_forearm", "arm_l"),
    ("plfa_left_forearm", "*plfa_left_forearm", "arm_l"),
    ("player_root", "prl_right_leg", "leg_r"), ("prl_right_leg", "prfl_right_foreleg", "leg_r"),
    ("prfl_right_foreleg", "*prfl_right_foreleg", "leg_r"),
    ("player_root", "pll_left_leg", "leg_l"), ("pll_left_leg", "plfl_left_foreleg", "leg_l"),
    ("plfl_left_foreleg", "*plfl_left_foreleg", "leg_l"),
]


def render_dual_view(d, hier, anim_name, out_path, n_frames=10, scale=6.5):
    """front(X-Y)+side(Z-Y) 2행 그리드, 팔다리 색상 구분(자기비평용 — 척추가 진짜
    굽었는지, 팔 스윙이 흉내내는 각도인지 헷갈리지 않게)."""
    anim = build_anim_index(d)[anim_name]
    length = float(anim["length"]); loop = anim.get("loop") == "loop"
    times = [length * i / n_frames for i in range(n_frames)] if loop else \
            [length * i / (n_frames - 1) for i in range(n_frames)]

    cell_w = 1700 / n_frames
    img = Image.new("RGB", (1700, 1000), (24, 24, 28))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
    except Exception:
        font = ImageFont.load_default()

    for row, view in enumerate(("front", "side")):
        ground = 460 + row * 480
        for i, t in enumerate(times):
            world = pose_world(hier, anim, t, loop_length=length if loop else None)
            cx = cell_w * (i + 0.5)
            if view == "front":
                def proj(p, cx=cx):
                    return (cx + p[0] * scale, ground - p[1] * scale)
            else:
                def proj(p, cx=cx):
                    return (cx + p[2] * scale, ground - p[1] * scale)
            for a, b, col in SEGMENTS_COLORED:
                pa, pb = get_pt(a, world), get_pt(b, world)
                draw.line([proj(pa), proj(pb)], fill=COLORS[col], width=3)
            draw.text((cx - 18, ground + 15), f"t={t:.2f}", fill=(200, 200, 200), font=font)
        draw.text((6, row * 480 + 4), f"{anim_name} ({view}, len={length:.2f}s loop={loop})",
                  fill=(255, 255, 255), font=font)

    img.save(out_path)
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bbmodel")
    ap.add_argument("anim_name")
    ap.add_argument("--out", default=None)
    ap.add_argument("--frames", type=int, default=10)
    args = ap.parse_args()
    d = load(args.bbmodel)
    hier = build_hierarchy(d)
    out = args.out or f"pose_{args.anim_name}.png"
    render_dual_view(d, hier, args.anim_name, out, n_frames=args.frames)
    print("저장:", out)
