#!/usr/bin/env python3
"""Emotecraft/PlayerAnimationLibrary 이모트(.json) -> steve.bbmodel 애니메이션 변환.

CMU 리타게팅(retarget.py)과 목적은 같지만 훨씬 싸고 안정적이다 — Emotecraft 이모트는
**이미 마인크래프트 플레이어 뼈대(머리/몸통/양팔/양다리 + bend)로 사람이 직접 만든 것**이라
리타게팅 수학(짐벌락·좌표계·비율·발 접지)이 아예 필요 없다. 뼈 이름과 축만 갈아끼우면 된다.
특히 mocap 리타게터가 통째로 잃어버렸던 **몸통 비틀림(torso.yaw / turn)** 이 소스에 그대로
들어 있다.

사용 예:
    # 미리보기 렌더만(파일 안 씀) — 굽기 전 필수
    python3 emote_import.py preview --emote club_penguin_dance.json --out prev.png

    # steve.bbmodel의 특정 애니에 굽기(없으면 새로 만듦)
    python3 emote_import.py bake --emote club_penguin_dance.json --target dance_penguin

라이선스 주의: KosmX/Emotecraft-emotes 저장소는 CC0(퍼블릭 도메인)이라 안전하다.
다른 커뮤니티 컬렉션은 개별 라이선스가 불명확하고, 유명 게임 안무 이름을 단 것들은
업로더가 CC0을 붙여도 원안무 권리까지 정리되는 게 아니다 — 일반 동작 위주로 고를 것.

포맷 요약(Emotecraft v2/v3):
    {"emote": {"isLoop": true, "beginTick": 0, "endTick": 142, "returnTick": 1,
               "degrees": false,            # false면 라디안
               "moves": [{"tick": 4, "easing": "EASEINOUTQUAD", "turn": 0,
                          "torso": {"yaw": 0.38}, "rightArm": {"pitch": -1.2, "bend": 0.5}}, ...]}}
    파트: head / torso / rightArm / leftArm / rightLeg / leftLeg
    값  : pitch(X) yaw(Y) roll(Z) / bend(팔꿈치·무릎) / x y z(픽셀 이동) / turn(몸 전체 yaw)
    ★tick 0의 키프레임은 무시된다(포맷 규약) — tick 1부터가 유효.
"""
import argparse
import json
import math
import uuid as uuidlib

from retarget import ZFIGHT

DEFAULT_BBMODEL = ("/Users/user/Library/Application Support/feather/player-server/servers/"
                    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BetterModel/players/steve.bbmodel")

TPS = 20.0          # 마인크래프트 틱
PX2UNIT = 0.9375    # 1픽셀 -> 우리 모델 유닛(몸 전체 30유닛 ≈ 32픽셀)

# Emotecraft 파트 -> (우리 본, 굽힘을 받을 자식 본). 몸통만 특수: 회전은 허리, 굽힘은 가슴.
PART_MAP = {
    "head":     ("h_ph_head", None),
    "torso":    ("pw_waist", "pc_chest"),
    "rightArm": ("pra_right_arm", "prfa_right_forearm"),
    "leftArm":  ("pla_left_arm", "plfa_left_forearm"),
    "rightLeg": ("prl_right_leg", "prfl_right_foreleg"),
    "leftLeg":  ("pll_left_leg", "plfl_left_foreleg"),
}

# ★부호 보정 없음. Emotecraft 소스는 이미 좌우가 미러링돼 있고(팔 벌리기 = rightArm.roll
# +135 / leftArm.roll −135), 그게 우리 리그 규약(오른팔 +Z=바깥, 왼팔 −Z=바깥)과 정확히
# 같은 방향이다. 처음엔 왼쪽 z를 뒤집었는데 그래서 왼팔만 몸을 가로질러 가다 clamp에
# 잘려 "한쪽 팔만 움직이는" 결과가 나왔다(jumping_jacks·floss에서 실측).
SIGN = {p: (1, 1, 1) for p in
        ("head", "torso", "rightArm", "leftArm", "rightLeg", "leftLeg")}

# 관통 방지 clamp. ★mocap 리타게터(rig-conventions.md)의 좁은 범위를 그대로 쓰면 안 된다 —
# 저건 모캡의 노이즈·과장이 리그를 뚫는 걸 막는 값이고, Emotecraft 이모트는 사람이 실제
# 플레이어 모델을 보면서 만든 것이라 팔이 몸을 가로지르는 게 의도(플로스가 대표적)다.
LIMITS = {
    "h_ph_head": ((-50, 50), (-70, 70), (-40, 40)),
    "pw_waist": ((-40, 40), (-40, 40), (-35, 35)),
    "pc_chest": ((-40, 40), (-40, 40), (-35, 35)),
    "pra_right_arm": ((-180, 180), (-90, 90), (-140, 140)),
    "pla_left_arm": ((-180, 180), (-90, 90), (-140, 140)),
    "prl_right_leg": ((-70, 100), (-45, 45), (-45, 45)),
    "pll_left_leg": ((-70, 100), (-45, 45), (-45, 45)),
}
# ★bend는 소스에서 좌우 부호가 갈린다(왼팔 −19 / 오른팔 +19가 같은 그림). 관절은 한쪽으로만
# 접히므로 절대값을 쓴다 — 부호를 살리면 한쪽 팔이 반대로 꺾여 부러진 것처럼 보인다.
BEND_ABS = True
BEND_LIMIT = {"prfa_right_forearm": (0, 130), "plfa_left_forearm": (0, 130),
              "prfl_right_foreleg": (0, 120), "plfl_left_foreleg": (0, 120),
              "pc_chest": (-40, 40)}


def ease(name, t):
    """Emotecraft easing -> 0~1 보간 계수. 미지원 이름은 선형으로 폴백."""
    n = (name or "LINEAR").upper()
    if n in ("CONSTANT", "STEP"):
        return 0.0
    if n.startswith("EASEINOUT"):
        return 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2
    if n.startswith("EASEIN"):
        return t * t
    if n.startswith("EASEOUT"):
        return 1 - (1 - t) ** 2
    return t


def load_emote(path):
    """이모트 JSON -> (채널 시계열, 길이틱, isLoop). 채널키 = (part, prop)."""
    raw = json.load(open(path, encoding="utf-8"))
    em = raw.get("emote", raw)
    to_deg = 1.0 if em.get("degrees") else 180.0 / math.pi
    chans = {}
    for mv in em.get("moves", []):
        tick = float(mv.get("tick", 0))
        if tick < 1:          # 포맷 규약: tick 0은 무시됨
            continue
        eas = mv.get("easing", "LINEAR")
        if "turn" in mv:
            chans.setdefault(("_root", "turn"), []).append((tick, float(mv["turn"]) * to_deg, eas))
        for part in PART_MAP:
            body = mv.get(part)
            if not isinstance(body, dict):
                continue
            for prop, val in body.items():
                if prop not in ("pitch", "yaw", "roll", "bend", "x", "y", "z"):
                    continue
                scale = to_deg if prop in ("pitch", "yaw", "roll", "bend") else 1.0
                chans.setdefault((part, prop), []).append((tick, float(val) * scale, eas))
    for k in chans:
        chans[k].sort(key=lambda e: e[0])
    end = float(em.get("endTick") or max((t for v in chans.values() for t, _, _ in v), default=20))
    return chans, end, bool(em.get("isLoop"))


def sample(series, tick):
    """easing을 반영해 임의 tick에서 값 추출. 키가 없으면 0(=기본자세)."""
    if not series:
        return 0.0
    if tick <= series[0][0]:
        return series[0][1]
    if tick >= series[-1][0]:
        return series[-1][1]
    for i in range(1, len(series)):
        t1, v1, _ = series[i - 1]
        t2, v2, e2 = series[i]
        if tick <= t2:
            f = ease(e2, (tick - t1) / max(1e-9, t2 - t1))
            return v1 + (v2 - v1) * f
    return series[-1][1]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def build_series(chans, end_tick, is_loop, step_tick=1.0):
    """우리 리그 본별 (x,y,z) 회전 시계열 + 루트 위치/회전을 만든다."""
    ticks = []
    t = 1.0
    while t <= end_tick:
        ticks.append(t)
        t += step_tick
    if ticks[-1] < end_tick:
        ticks.append(end_tick)
    times = [(tk - 1.0) / TPS for tk in ticks]

    rot = {}
    for part, (bone, child) in PART_MAP.items():
        sx, sy, sz = SIGN[part]
        xs = [sx * sample(chans.get((part, "pitch"), []), tk) for tk in ticks]
        ys = [sy * sample(chans.get((part, "yaw"), []), tk) for tk in ticks]
        zs = [sz * sample(chans.get((part, "roll"), []), tk) for tk in ticks]
        lim = LIMITS.get(bone)
        if lim:
            xs = [clamp(v, *lim[0]) for v in xs]
            ys = [clamp(v, *lim[1]) for v in ys]
            zs = [clamp(v, *lim[2]) for v in zs]
        rot[bone] = (xs, ys, zs)
        if child:
            bl = BEND_LIMIT[child if child in BEND_LIMIT else "pc_chest"]
            raw_bend = [sample(chans.get((part, "bend"), []), tk) for tk in ticks]
            if BEND_ABS and child != "pc_chest":
                raw_bend = [abs(v) for v in raw_bend]
            bend = [clamp(v, *bl) for v in raw_bend]
            # 몸통 bend는 가슴을 앞으로 접는 것(자체 회전 없음), 팔다리 bend는 관절 굽힘.
            rot[child] = (bend, [0.0] * len(ticks), [0.0] * len(ticks))

    root_pos = [[PX2UNIT * sample(chans.get(("torso", ax), []), tk) for ax in "xyz"] for tk in ticks]
    root_yaw = [sample(chans.get(("_root", "turn"), []), tk) for tk in ticks]

    if is_loop:
        # 루프면 첫/끝 값을 강제로 맞춘다(BetterModel은 값이 다르면 매 사이클 툭 끊긴다).
        for bone, (xs, ys, zs) in rot.items():
            for arr in (xs, ys, zs):
                arr[-1] = arr[0]
        root_pos[-1] = list(root_pos[0])
        root_yaw[-1] = root_yaw[0]
    return times, rot, root_pos, root_yaw


def bake(d, target, times, rot, root_pos, root_yaw, is_loop, hide_cape=True):
    bone_uuid = {g["name"]: g["uuid"] for g in d["groups"]}
    L = times[-1]

    def kf(t, ch, x, y, z, interp="catmullrom"):
        return {"channel": ch, "data_points": [{"x": str(round(x, 4)), "y": str(round(y, 4)),
                                                 "z": str(round(z, 4))}],
                "uuid": str(uuidlib.uuid4()), "time": round(t, 5), "color": -1,
                "interpolation": interp}

    animators = {}
    for bone, (xs, ys, zs) in rot.items():
        if bone not in bone_uuid:
            continue
        kfs = [kf(t, "rotation", xs[i], ys[i], zs[i]) for i, t in enumerate(times)]
        px, py, pz = ZFIGHT.get(bone, (0, 0, 0))
        kfs.append(kf(0.0, "position", px, py, pz, "linear"))
        kfs.append(kf(L, "position", px, py, pz, "linear"))
        animators[bone_uuid[bone]] = {"name": bone, "type": "bone", "rotation_global": False,
                                       "quaternion_interpolation": False, "keyframes": kfs}

    root_kfs = [kf(t, "position", *root_pos[i], interp="linear") for i, t in enumerate(times)]
    root_kfs += [kf(t, "rotation", 0, root_yaw[i], 0) for i, t in enumerate(times)]
    animators[bone_uuid["player_root"]] = {"name": "player_root", "type": "bone",
                                            "rotation_global": False,
                                            "quaternion_interpolation": False, "keyframes": root_kfs}
    if hide_cape and "cape_cape" in bone_uuid:
        animators[bone_uuid["cape_cape"]] = {
            "name": "cape_cape", "type": "bone", "rotation_global": False,
            "quaternion_interpolation": False,
            "keyframes": [kf(0.0, "scale", 0.001, 0.001, 0.001, "linear"),
                          kf(L, "scale", 0.001, 0.001, 0.001, "linear")]}

    by_name = {a["name"]: a for a in d["animations"]}
    if target not in by_name:
        d["animations"].append({"name": target, "loop": "loop" if is_loop else "once",
                                 "override": False, "length": round(L, 5), "snapping": 24,
                                 "selected": False, "anim_time_update": "", "blend_weight": "",
                                 "start_delay": "", "loop_delay": "", "animators": {}})
        by_name = {a["name"]: a for a in d["animations"]}
    tgt = by_name[target]
    tgt["animators"] = animators
    tgt["length"] = round(L, 5)
    tgt["loop"] = "loop" if is_loop else "once"
    return L


def prepare(args):
    chans, end, is_loop = load_emote(args.emote)
    if args.once:
        is_loop = False
    times, rot, root_pos, root_yaw = build_series(chans, end, is_loop, args.step_tick)
    print(f"소스 파트: {sorted({p for p, _ in chans if p != '_root'})}")
    print(f"길이 {end:.0f}틱 = {times[-1]:.2f}s, loop={is_loop}, 샘플 {len(times)}개")
    return times, rot, root_pos, root_yaw, is_loop


def cmd_preview(args):
    times, rot, root_pos, root_yaw, is_loop = prepare(args)
    d = json.load(open(args.bbmodel))
    tmp = "__emote_preview__"
    d["animations"] = [a for a in d["animations"] if a["name"] != tmp]
    bake(d, tmp, times, rot, root_pos, root_yaw, is_loop)
    import pose_render as pr
    hier = pr.build_hierarchy(d)
    out = pr.render_dual_view(d, hier, tmp, args.out, n_frames=args.frames)
    print("렌더 저장:", out, "-- 눈으로 확인 후 bake 할 것")


def cmd_bake(args):
    times, rot, root_pos, root_yaw, is_loop = prepare(args)
    d = json.load(open(args.bbmodel))
    L = bake(d, args.target, times, rot, root_pos, root_yaw, is_loop)
    json.dump(d, open(args.bbmodel, "w"), indent=1)
    print(f"'{args.target}' 애니에 구움 완료 (length={L:.2f}s, loop={is_loop})")
    print("-> 배포: dev는 파일이 곧 서버 파일이라 'bm reload'만, prod는 scp + bm reload")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(required=True)
    for name, fn in (("preview", cmd_preview), ("bake", cmd_bake)):
        p = sub.add_parser(name)
        p.add_argument("--emote", required=True, help="Emotecraft 이모트 json 경로")
        p.add_argument("--bbmodel", default=DEFAULT_BBMODEL)
        p.add_argument("--step-tick", type=float, default=1.0,
                       help="샘플 간격(틱). 1=20fps, 2=10fps로 키프레임 절반")
        p.add_argument("--once", action="store_true", help="루프 이모트를 1회 재생으로 강제")
        if name == "preview":
            p.add_argument("--out", default="emote_preview.png")
            p.add_argument("--frames", type=int, default=12)
        else:
            p.add_argument("--target", required=True, help="애니 이름(없으면 새로 만듦)")
        p.set_defaults(func=fn)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
