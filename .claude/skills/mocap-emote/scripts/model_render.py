#!/usr/bin/env python3
"""steve.bbmodel 애니메이션을 **실제 큐브 모델**로 렌더해 GIF로 뽑는다.

pose_render.py(스틱피규어)는 각도·에너지 검수용이라 "사람처럼 보이는가"를 판단하기 어렵다.
이건 26개 큐브를 전부 그려서(페인터 알고리즘 + 면 방향 셰이딩) 인게임에 가까운 실루엣으로
보여준다. 텍스처는 안 입히고 파트별 단색(스티브 배색)이라 z-fight 같은 텍스처 레벨
아티팩트는 여전히 인게임에서만 확인 가능하다.

    python3 model_render.py --anim dance --out dance.gif
    python3 model_render.py --anim dance --compare-with old.bbmodel --out cmp.gif
    python3 model_render.py --all-dances --out dances.gif      # 춤 전체를 한 장에

PIL만 사용(이 환경엔 numpy 없음).
"""
import argparse
import json
import math

from PIL import Image, ImageDraw, ImageFont

import pose_render as pr

DEFAULT_BBMODEL = ("/Users/user/Library/Application Support/feather/player-server/servers/"
                    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BetterModel/players/steve.bbmodel")

# 파트별 배색(스티브 근사). skin=본체 레이어, hat=바깥(오버레이) 레이어.
BONE_COLOR = {
    "h_ph_head":          ((198, 152, 111), (60, 42, 25)),    # 얼굴 / 머리카락
    "pc_chest":           ((0, 168, 168), (0, 148, 148)),     # 상의
    "pw_waist":           ((0, 168, 168), (0, 148, 148)),
    "pra_right_arm":      ((0, 168, 168), (0, 148, 148)),     # 소매
    "pla_left_arm":       ((0, 168, 168), (0, 148, 148)),
    "prfa_right_forearm": ((198, 152, 111), (188, 142, 101)),  # 맨팔
    "plfa_left_forearm":  ((198, 152, 111), (188, 142, 101)),
    "prl_right_leg":      ((59, 59, 158), (52, 52, 140)),     # 바지
    "pll_left_leg":       ((59, 59, 158), (52, 52, 140)),
    "prfl_right_foreleg": ((59, 59, 158), (45, 45, 120)),
    "plfl_left_foreleg":  ((59, 59, 158), (45, 45, 120)),
}
SKIP_BONES = {"shadow", "tag_name", "cape_cape", "pri_right_item", "pli_left_item", "phip_hip"}

# 면 법선별 밝기(위=밝게, 아래=어둡게 — 마크 바닐라 조명 근사)
FACE_SHADE = {"up": 1.0, "down": 0.5, "north": 0.86, "south": 0.86, "east": 0.72, "west": 0.72}


def build_cube_map(d):
    """본 이름 -> [element dict]. outliner의 문자열 자식이 큐브 uuid다."""
    groups_by_uuid = {g["uuid"]: g for g in d["groups"]}
    el_by_uuid = {e["uuid"]: e for e in d["elements"]}
    out = {}

    def walk(node, cur_bone):
        if isinstance(node, str):
            if cur_bone and node in el_by_uuid:
                out.setdefault(cur_bone, []).append(el_by_uuid[node])
            return
        uuid = node.get("uuid")
        bone = groups_by_uuid[uuid]["name"] if uuid in groups_by_uuid else cur_bone
        for c in node.get("children", []):
            walk(c, bone)

    for top in d["outliner"]:
        walk(top, None)
    return out


def cube_faces(el):
    """큐브 -> [(4개 꼭짓점(모델좌표), 면이름)]."""
    x0, y0, z0 = el["from"]
    x1, y1, z1 = el["to"]
    v = {
        "up":    [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
        "down":  [(x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0)],
        "north": [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
        "south": [(x1, y0, z1), (x0, y0, z1), (x0, y1, z1), (x1, y1, z1)],
        "west":  [(x0, y0, z1), (x0, y0, z0), (x0, y1, z0), (x0, y1, z1)],
        "east":  [(x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)],
    }
    return [(pts, name) for name, pts in v.items()]


def collect_polys(d, hier, cubes, anim, t, yaw=32.0, pitch=10.0):
    """한 프레임의 모든 면을 카메라 좌표로 변환해 (깊이, 화면좌표, 색) 리스트로."""
    length = float(anim["length"])
    loop = anim.get("loop") == "loop"
    world = pr.pose_world(hier, anim, t, loop_length=length if loop else None)
    cam = pr.mat_mul(pr.rot_x(pitch), pr.rot_y(yaw))
    polys = []
    for bone, els in cubes.items():
        if bone in SKIP_BONES or bone not in world:
            continue
        colors = BONE_COLOR.get(bone)
        if colors is None:
            continue
        bpos, brot = world[bone]
        borigin = hier[bone]["origin"]
        for el in els:
            base = colors[1] if el.get("name") == "hat" else colors[0]
            for pts, face in cube_faces(el):
                cpts = []
                for p in pts:
                    local = [p[i] - borigin[i] for i in range(3)]
                    wv = pr.mat_vec(brot, local)
                    wp = [bpos[i] + wv[i] for i in range(3)]
                    cpts.append(pr.mat_vec(cam, wp))
                depth = sum(c[2] for c in cpts) / 4.0
                sh = FACE_SHADE[face]
                polys.append((depth, cpts, tuple(int(c * sh) for c in base)))
    polys.sort(key=lambda x: x[0])   # 먼 것부터(카메라는 +Z 쪽에서 본다)
    return polys


def draw_frame(draw, polys, cx, ground, scale):
    for _, cpts, col in polys:
        xy = [(cx + p[0] * scale, ground - p[1] * scale) for p in cpts]
        draw.polygon(xy, fill=col, outline=tuple(max(0, c - 28) for c in col))


def _font(size):
    # ★한글 라벨이 □□로 깨지지 않게 시스템 한글 폰트를 먼저 시도한다.
    for p in ("/System/Library/Fonts/AppleSDGothicNeo.ttc",
              "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
              "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_gif(entries, out_path, n_frames=48, scale=7.0, cell_w=300, cell_h=420, fps=20, cols=None):
    """entries = [(라벨, d, hier, cubes, anim)] — 격자로 배치해 한 GIF로."""
    n = len(entries)
    cols = cols or (n if n <= 3 else 3)
    rows = (n + cols - 1) // cols
    W, H = cell_w * cols, cell_h * rows
    L = max(float(e[4]["length"]) for e in entries)
    font = _font(15)

    frames = []
    for fi in range(n_frames):
        t = L * fi / n_frames
        img = Image.new("RGB", (W, H), (30, 31, 36))
        draw = ImageDraw.Draw(img)
        for i, (label, d, hier, cubes, anim) in enumerate(entries):
            cx = cell_w * (i % cols + 0.5)
            top = cell_h * (i // cols)
            ground = top + cell_h - 55
            al = float(anim["length"])
            tt = (t % al) if anim.get("loop") == "loop" else min(t, al)
            draw.line([(cx - 90, ground), (cx + 90, ground)], fill=(52, 54, 62), width=2)
            draw_frame(draw, collect_polys(d, hier, cubes, anim, tt), cx, ground, scale)
            w = draw.textlength(label, font=font)
            draw.text((cx - w / 2, top + 10), label, fill=(235, 235, 235), font=font)
        frames.append(img)

    frames[0].save(out_path, save_all=True, append_images=frames[1:],
                    duration=int(1000 / fps), loop=0, optimize=True)
    return out_path


def prep(path, anim_name):
    d = json.load(open(path))
    hier = pr.build_hierarchy(d)
    cubes = build_cube_map(d)
    anim = pr.build_anim_index(d)[anim_name]
    return d, hier, cubes, anim


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bbmodel", default=DEFAULT_BBMODEL)
    ap.add_argument("--anim", help="렌더할 애니 이름")
    ap.add_argument("--all-dances", action="store_true", help="dance* 애니 전부 나란히")
    ap.add_argument("--compare-with", help="비교 대상 bbmodel(같은 애니 이름을 나란히)")
    ap.add_argument("--label", default=None)
    ap.add_argument("--out", default="anim.gif")
    ap.add_argument("--frames", type=int, default=48)
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--scale", type=float, default=7.0)
    args = ap.parse_args()

    entries = []
    if args.all_dances:
        d = json.load(open(args.bbmodel))
        hier, cubes = pr.build_hierarchy(d), build_cube_map(d)
        for a in d["animations"]:
            if a["name"].startswith("dance"):
                entries.append((a["name"], d, hier, cubes, a))
    else:
        d, hier, cubes, anim = prep(args.bbmodel, args.anim)
        entries.append((args.label or args.anim, d, hier, cubes, anim))
        if args.compare_with:
            d2, h2, c2, a2 = prep(args.compare_with, args.anim)
            entries.insert(0, (f"{args.anim} (기존)", d2, h2, c2, a2))
            entries[1] = (f"{args.anim} (수정후)", d, hier, cubes, anim)

    out = render_gif(entries, args.out, n_frames=args.frames, fps=args.fps, scale=args.scale)
    print("GIF 저장:", out, f"({len(entries)}종, {args.frames}프레임)")


if __name__ == "__main__":
    main()
