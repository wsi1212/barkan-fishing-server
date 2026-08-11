#!/usr/bin/env python3
"""Xsens MVNX(.mvnx) 모캡 -> steve.bbmodel 리타게팅.

CMU(ASF/AMC)와 별개 경로다. MVNX는 XML이고 세그먼트 23개의 **글로벌 쿼터니언**을 프레임마다
담고 있어서, 부모 기준 로컬 회전 = inv(q_parent) * q_child 로 바로 뽑힌다(ASF처럼 축 정의를
따로 해석할 필요가 없어 오히려 단순하다).

    python3 mvnx_retarget.py scan  --mvnx "PSY Gangnam Style.mvnx"
    python3 mvnx_retarget.py preview --mvnx ... --start 1200 --out g.png
    python3 mvnx_retarget.py bake  --mvnx ... --start 1200 --target dance_gangnam

좌표계: MVN은 Z-up / X-forward / Y-left. 우리 리그는 Y-up이라 축을 갈아끼운다
(우리 X=굽힘 <- MVN Y축 회전, 우리 Y=비틀림 <- MVN Z축, 우리 Z=벌림 <- MVN X축).
부호는 --flip-* 로 뒤집어가며 렌더로 확인할 것 — 리그마다 한 번은 맞춰봐야 한다.

retarget.py의 후처리(스무딩·debias·발접지·루트 클램프·루프 클로징·cape 숨김)를 그대로 재사용한다.
"""
import argparse
import json
import math
import xml.etree.ElementTree as ET

import retarget as R

NS = {"m": "http://www.xsens.com/mvn/mvnx"}


def quat_mul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return (w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2)


def quat_conj(q):
    return (q[0], -q[1], -q[2], -q[3])


def quat_to_euler_zyx(q):
    """쿼터니언 -> (rx, ry, rz) 도. MVN 축 기준(X-forward, Y-left, Z-up)."""
    w, x, y, z = q
    n = math.sqrt(w * w + x * x + y * y + z * z) or 1.0
    w, x, y, z = w / n, x / n, y / n, z / n
    # roll(X)
    rx = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    # pitch(Y) — 짐벌 근처는 clamp
    s = 2 * (w * y - z * x)
    ry = math.asin(max(-1.0, min(1.0, s)))
    # yaw(Z)
    rz = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return math.degrees(rx), math.degrees(ry), math.degrees(rz)


class Mvnx:
    def __init__(self, path):
        tree = ET.parse(path)
        root = tree.getroot()
        subj = root.find("m:subject", NS)
        self.fps = float(subj.get("frameRate", "240"))
        self.labels = [s.get("label") for s in subj.find("m:segments", NS).findall("m:segment", NS)]
        self.idx = {lab: i for i, lab in enumerate(self.labels)}
        self.quats, self.pos, self.rest = [], [], None
        for fr in subj.find("m:frames", NS).findall("m:frame", NS):
            o = [float(v) for v in fr.find("m:orientation", NS).text.split()]
            q = [tuple(o[i * 4:i * 4 + 4]) for i in range(len(self.labels))]
            if fr.get("type") != "normal":
                # npose/tpose = 캘리브레이션 자세. 모션 프레임에선 빼되 ★기준자세로 보관한다.
                if self.rest is None:
                    self.rest = q
                continue
            p = [float(v) for v in fr.find("m:position", NS).text.split()]
            self.quats.append(q)
            self.pos.append([tuple(p[i * 3:i * 3 + 3]) for i in range(len(self.labels))])
        if self.rest is None:
            self.rest = self.quats[0]

    def local(self, f, child, parent):
        qc = self.quats[f][self.idx[child]]
        qp = self.quats[f][self.idx[parent]]
        return quat_mul(quat_conj(qp), qc)

    def local_rest(self, child, parent):
        qc = self.rest[self.idx[child]]
        qp = self.rest[self.idx[parent]]
        return quat_mul(quat_conj(qp), qc)

    def local_euler(self, f, child, parent):
        """★기준자세(npose) 대비 상대 회전의 오일러각.

        로컬 회전을 그대로 풀면 MVN 세그먼트 프레임끼리의 정렬 오프셋(어깨는 90도씩
        돌아가 있다)이 섞여서, 가만히 서 있어도 몸통이 45도 접힌 것처럼 나온다(실측).
        캘리브레이션 자세를 빼면 '쉬는 자세=0'인 해부학적 델타가 되어 부호·축이 명확해진다."""
        rel = quat_mul(quat_conj(self.local_rest(child, parent)), self.local(f, child, parent))
        return quat_to_euler_zyx(rel)


# 우리 리그 축 <- MVN 축. (굽힘, 비틀림, 벌림) = (MVN ry, MVN rz, MVN rx)
def map_axes(e, sx=1.0, sy=1.0, sz=1.0):
    rx, ry, rz = e
    return (ry * sx, rz * sy, rx * sz)


# ---------------------------------------------------------------------------
# ★위치 기반 리타게팅 (권장 경로)
#
# MVNX는 세그먼트 23개의 **월드 위치**도 프레임마다 준다. 관절 위치로 뼈의 방향벡터를
# 직접 만들면 쿼터니언 프레임 정렬 문제(어깨 세그먼트가 90도 돌아가 있는 등)를 아예
# 우회할 수 있다 — 오일러 방식은 기준자세를 빼도 몸통이 앞으로 접히는 걸 못 잡았다.
#
# 좌표계: MVN은 X=앞, Y=왼쪽, Z=위. 우리 모델은 X=오른쪽, Y=위, Z=앞.
#   (ours_x, ours_y, ours_z) = (-mvn_y, mvn_z, mvn_x)
# ---------------------------------------------------------------------------

def to_ours(v):
    return (-v[1], v[2], v[0])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def norm(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def dir_to_xz(v):
    """아래로 뻗은 기본자세(0,-1,0)를 방향 v로 보내는 (X각, Z각) 도.

    bbmodel 오일러 합성 순서가 Rz·Ry·Rx라, Rz·Rx·(0,-1,0) = (sz·cx, -cz·cx, -sx).
    Y(비틀림)는 방향을 안 바꾸므로 여기선 안 나온다(따로 처리)."""
    x, y, z = norm(v)
    ax = math.degrees(math.asin(max(-1.0, min(1.0, -z))))
    cx = math.cos(math.radians(ax))
    if abs(cx) < 1e-6:
        return ax, 0.0
    az = math.degrees(math.atan2(x / cx, -y / cx))
    return ax, az


def angle_between(a, b):
    a, b = norm(a), norm(b)
    d = max(-1.0, min(1.0, sum(a[i] * b[i] for i in range(3))))
    return math.degrees(math.acos(d))


def mat_t(m):
    return [[m[j][i] for j in range(3)] for i in range(3)]


ENERGY = [("RightUpperArm", "T8"), ("LeftUpperArm", "T8"),
          ("RightUpperLeg", "Pelvis"), ("LeftUpperLeg", "Pelvis")]


def find_window(mv, n, stride=40, loop_weight=1.5, neutral_weight=1.2):
    best, best_score = 0, -1e9
    for start in range(0, max(1, len(mv.quats) - n), stride):
        energy = seam = neutral = 0.0
        for child, parent in ENERGY:
            vals = [map_axes(mv.local_euler(f, child, parent))[0]
                    for f in range(start, start + n, max(1, n // 40))]
            energy += max(vals) - min(vals)
            seam += abs(vals[-1] - vals[0])
            neutral += abs(vals[0] - R.mean(vals))
        score = energy - loop_weight * seam - neutral_weight * neutral
        if score > best_score:
            best, best_score = start, score
    return best, best_score


def build_pos(mv, start, n, step, arm_ex=1.0, spine_ex=1.2, head_ex=1.5, hip_ex=1.0,
              twist_ex=1.5, root_xz_max=2.5, loop_frac=0.08):
    """위치(방향벡터) 기반 리타게팅. 각 뼈를 자식 관절 쪽으로 '겨냥'시킨다."""
    import pose_render as pr
    idxs = list(range(start, start + n, step))
    dt = step / mv.fps
    times = [i * dt for i in range(len(idxs))]
    L = times[-1]
    I = mv.idx

    def P(f, seg):
        return to_ours(mv.pos[f][I[seg]])

    ch = {k: [] for k in ("waist_x", "waist_z", "chest_x", "chest_z", "twist",
                           "pra_x", "pra_z", "pla_x", "pla_z", "prl_x", "prl_z", "pll_x", "pll_z",
                           "prfa", "plfa", "prfl", "plfl", "rx", "ry", "rz", "head_x", "head_y")}
    for f in idxs:
        pelvis, t8, neck = P(f, "Pelvis"), P(f, "T8"), P(f, "Neck")
        # 몸통: 골반->T8이 허리, T8->목이 가슴. 좌우 어깨선으로 몸 전체 비틀림.
        wx, wz = dir_to_xz([-c for c in sub(t8, pelvis)])   # 위로 뻗은 축이라 부호 반전
        cx, cz = dir_to_xz([-c for c in sub(neck, t8)])
        ch["waist_x"].append(wx); ch["waist_z"].append(wz)
        ch["chest_x"].append(cx - wx); ch["chest_z"].append(cz - wz)
        sh = sub(P(f, "LeftShoulder"), P(f, "RightShoulder"))
        ch["twist"].append(math.degrees(math.atan2(sh[2], sh[0])))
        hd = sub(P(f, "Head"), neck)
        ch["head_x"].append(dir_to_xz([-c for c in hd])[0])
        ch["head_y"].append(0.0)

        # 팔다리: 부모(가슴/골반) 회전을 걷어낸 뒤 겨냥각을 뽑는다.
        par = pr.euler_mat(cx, 0, cz)
        parT = mat_t(par)
        hip = pr.euler_mat(wx, 0, wz)
        hipT = mat_t(hip)
        for side, up, low, end, k in (("R", "RightUpperArm", "RightForeArm", "RightHand", "pra"),
                                       ("L", "LeftUpperArm", "LeftForeArm", "LeftHand", "pla")):
            d = pr.mat_vec(parT, list(sub(P(f, low), P(f, up))))
            ax, az = dir_to_xz(d)
            ch[k + "_x"].append(ax); ch[k + "_z"].append(az)
            bend = angle_between(sub(P(f, low), P(f, up)), sub(P(f, end), P(f, low)))
            ch["prfa" if side == "R" else "plfa"].append(bend)
        for side, up, low, end, k in (("R", "RightUpperLeg", "RightLowerLeg", "RightFoot", "prl"),
                                       ("L", "LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "pll")):
            d = pr.mat_vec(hipT, list(sub(P(f, low), P(f, up))))
            ax, az = dir_to_xz(d)
            ch[k + "_x"].append(ax); ch[k + "_z"].append(az)
            bend = angle_between(sub(P(f, low), P(f, up)), sub(P(f, end), P(f, low)))
            ch["prfl" if side == "R" else "plfl"].append(bend)
        p = P(f, "Pelvis")
        ch["rx"].append(p[0]); ch["ry"].append(p[1]); ch["rz"].append(p[2])

    m2u = 30.0 / 1.75
    win = max(3, (len(idxs) // 2) | 1)

    def C(key, ex, lo, hi, dead=2.0):
        sm = R.smooth(ch[key])
        m = R.mean(sm)
        d = R.deadzone([v - m for v in sm], dead)
        return R.clamp([v * ex for v in d], lo, hi)

    waist_x = C("waist_x", spine_ex, -30, 30); waist_z = C("waist_z", spine_ex, -25, 25)
    chest_x = C("chest_x", spine_ex, -30, 30); chest_z = C("chest_z", spine_ex, -25, 25)
    twist = C("twist", twist_ex, -35, 35, 1.5)
    pra_x = R.clamp([15 + v for v in C("pra_x", arm_ex, -180, 180, 3)], -60, 130)
    pla_x = R.clamp([15 + v for v in C("pla_x", arm_ex, -180, 180, 3)], -60, 130)
    pra_z = R.clamp([20 + v for v in C("pra_z", arm_ex, -180, 180, 3)], -25, 135)
    pla_z = R.clamp([-20 + v for v in C("pla_z", arm_ex, -180, 180, 3)], -135, 25)
    prl_x = R.clamp([8 + v for v in C("prl_x", hip_ex, -180, 180, 3)], -25, 90)
    pll_x = R.clamp([8 + v for v in C("pll_x", hip_ex, -180, 180, 3)], -25, 90)
    prl_z = C("prl_z", hip_ex, -22, 22, 3); pll_z = C("pll_z", hip_ex, -22, 22, 3)
    prfa = R.clamp([8 + v for v in R.debias(R.smooth(ch["prfa"]))], 0, 120)
    plfa = R.clamp([8 + v for v in R.debias(R.smooth(ch["plfa"]))], 0, 120)
    prfl = R.clamp(R.debias(R.smooth(ch["prfl"])), 0, 110)
    plfl = R.clamp(R.debias(R.smooth(ch["plfl"])), 0, 110)

    root_x = R.clamp(R.highpass([v * m2u for v in ch["rx"]], win), -root_xz_max, root_xz_max)
    root_z = R.clamp(R.highpass([v * m2u for v in ch["rz"]], win), -root_xz_max, root_xz_max)
    drops = [max(R.foot_drop(prl_x[i], prfl[i]), R.foot_drop(pll_x[i], plfl[i]))
             for i in range(len(idxs))]
    root_y = R.clamp([(d - R.LEG_REST) * 0.6 for d in drops], -4.0, 0.5)

    sm = {
        "pw_waist_x": waist_x, "pw_waist_y": [v * 0.4 for v in twist], "pw_waist_z": waist_z,
        "pc_chest_x": chest_x, "pc_chest_y": [v * 0.3 for v in twist], "pc_chest_z": chest_z,
        "h_ph_head_x": C("head_x", head_ex, -25, 25), "h_ph_head_y": [0.0] * len(idxs),
        "h_ph_head_z": [0.0] * len(idxs),
        "pra_x": pra_x, "pra_y": [0.0] * len(idxs), "pra_z": pra_z,
        "pla_x": pla_x, "pla_y": [0.0] * len(idxs), "pla_z": pla_z,
        "prfa_x": prfa, "plfa_x": plfa,
        "prl_x": prl_x, "prl_y": [0.0] * len(idxs), "prl_z": prl_z,
        "pll_x": pll_x, "pll_y": [0.0] * len(idxs), "pll_z": pll_z,
        "prfl_x": prfl, "plfl_x": plfl,
        "root_x": root_x, "root_y": root_y, "root_z": root_z, "root_twist_y": twist,
    }
    for k in sm:
        sm[k] = R.close_loop(sm[k], loop_frac)
    return sm, times, L


def build(mv, start, n, step, arm_ex=1.0, spine_ex=1.2, head_ex=1.5, hip_ex=1.0,
          twist_ex=1.5, root_xz_max=2.5, flip=(1, 1, 1), loop_frac=0.08):
    idxs = list(range(start, start + n, step))
    dt = step / mv.fps
    times = [i * dt for i in range(len(idxs))]
    L = times[-1]
    sx, sy, sz = flip

    # retarget.py의 centered()는 retarget_window 내부함수라 여기서 동등 구현
    # (스무딩 -> 평균중심화 -> 데드존 -> 과장 순서. 순서가 바뀌면 데드존이 무의미해진다)
    def centered(vals, ex, dead=2.0):
        sm = R.smooth(vals)
        m = R.mean(sm)
        d = R.deadzone([v - m for v in sm], dead)
        return [v * ex for v in d]

    def tri(child, parent, ex, dead=2.0):
        raw = [map_axes(mv.local_euler(f, child, parent), sx, sy, sz) for f in idxs]
        return [centered([r[k] for r in raw], ex, dead) for k in range(3)]

    waist = tri("L3", "Pelvis", spine_ex)
    chest = tri("T8", "L3", spine_ex)
    head = tri("Head", "Neck", head_ex)
    r_arm = tri("RightUpperArm", "T8", arm_ex, 3.0)
    l_arm = tri("LeftUpperArm", "T8", arm_ex, 3.0)
    r_leg = tri("RightUpperLeg", "Pelvis", hip_ex, 3.0)
    l_leg = tri("LeftUpperLeg", "Pelvis", hip_ex, 3.0)

    # 팔꿈치·무릎은 단일 굽힘축만(부호 섞이면 반대로 꺾임) — 절대값 + debias
    def bend(child, parent, lim):
        raw = [abs(map_axes(mv.local_euler(f, child, parent))[0]) for f in idxs]
        return R.clamp(R.debias(R.smooth(raw)), 0, lim)

    prfa = R.clamp([8 + v for v in bend("RightForeArm", "RightUpperArm", 120)], 0, 120)
    plfa = R.clamp([8 + v for v in bend("LeftForeArm", "LeftUpperArm", 120)], 0, 120)
    prfl = bend("RightLowerLeg", "RightUpperLeg", 110)
    plfl = bend("LeftLowerLeg", "LeftUpperLeg", 110)

    r_leg_x = R.clamp([8 + v for v in r_leg[0]], -20, 90)
    l_leg_x = R.clamp([8 + v for v in l_leg[0]], -20, 90)

    # 루트: 골반 위치(미터->유닛, Z가 위) + 골반 yaw에서 느린 성분 제거
    P = mv.idx["Pelvis"]
    win = max(3, (len(idxs) // 2) | 1)
    m2u = 30.0 / 1.75        # 사람키 ~1.75m를 모델 30유닛에 맞춘 환산
    px = [mv.pos[f][P][0] * m2u for f in idxs]
    py = [mv.pos[f][P][1] * m2u for f in idxs]
    root_x = R.clamp(R.highpass(px, win), -root_xz_max, root_xz_max)
    root_z = R.clamp(R.highpass(py, win), -root_xz_max, root_xz_max)

    drops = [max(R.foot_drop(r_leg_x[i], prfl[i]), R.foot_drop(l_leg_x[i], plfl[i]))
             for i in range(len(idxs))]
    root_y = R.clamp([(d - R.LEG_REST) * 0.6 for d in drops], -4.0, 0.5)

    pelvis_yaw = []
    for f in idxs:
        w, x, y, z = mv.quats[f][P]
        pelvis_yaw.append(math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))))
    root_twist = R.clamp([v * twist_ex for v in R.highpass(R.smooth(pelvis_yaw), win)], -35, 35)

    sm = {
        "pw_waist_x": R.clamp(waist[0], -30, 30), "pw_waist_y": R.clamp(waist[1], -30, 30),
        "pw_waist_z": R.clamp(waist[2], -25, 25),
        "pc_chest_x": R.clamp(chest[0], -30, 30), "pc_chest_y": R.clamp(chest[1], -30, 30),
        "pc_chest_z": R.clamp(chest[2], -25, 25),
        "h_ph_head_x": R.clamp(head[0], -25, 25), "h_ph_head_y": R.clamp(head[1], -35, 35),
        "h_ph_head_z": R.clamp(head[2], -18, 18),
        "pra_x": R.clamp([15 + v for v in r_arm[0]], -60, 130),
        "pra_y": R.clamp(r_arm[1], -30, 30),
        "pra_z": R.clamp([20 + v for v in r_arm[2]], -20, 135),
        "pla_x": R.clamp([15 + v for v in l_arm[0]], -60, 130),
        "pla_y": R.clamp(l_arm[1], -30, 30),
        "pla_z": R.clamp([-20 + v for v in l_arm[2]], -135, 20),
        "prfa_x": prfa, "plfa_x": plfa,
        "prl_x": r_leg_x, "prl_y": R.clamp(r_leg[1], -20, 20), "prl_z": R.clamp(r_leg[2], -22, 22),
        "pll_x": l_leg_x, "pll_y": R.clamp(l_leg[1], -20, 20), "pll_z": R.clamp(l_leg[2], -22, 22),
        "prfl_x": prfl, "plfl_x": plfl,
        "root_x": root_x, "root_y": root_y, "root_z": root_z, "root_twist_y": root_twist,
    }
    for k in sm:
        sm[k] = R.close_loop(sm[k], loop_frac)
    return sm, times, L


def common(p):
    p.add_argument("--mvnx", required=True)
    p.add_argument("--bbmodel", default=R.DEFAULT_BBMODEL)
    p.add_argument("--start", type=int, default=None)
    p.add_argument("--window-sec", type=float, default=4.0)
    p.add_argument("--step", type=int, default=12, help="240fps -> 12면 20fps")
    p.add_argument("--arm-ex", type=float, default=1.0)
    p.add_argument("--spine-ex", type=float, default=1.2)
    p.add_argument("--head-ex", type=float, default=1.5)
    p.add_argument("--hip-ex", type=float, default=1.0)
    p.add_argument("--twist-ex", type=float, default=1.5)
    p.add_argument("--flip", default="1,1,1", help="축 부호 sx,sy,sz (--euler 경로에서만)")
    p.add_argument("--euler", action="store_true",
                   help="구 오일러 경로 사용(기본은 위치 기반). 디버그용")


def prep(args):
    mv = Mvnx(args.mvnx)
    n = int(args.window_sec * mv.fps / args.step) * args.step
    start = args.start
    if start is None:
        start, sc = find_window(mv, n)
        print(f"자동 구간: start={start} score={sc:.1f} (총 {len(mv.quats)}프레임 @{mv.fps:.0f}fps)")
    if getattr(args, "euler", False):
        flip = tuple(float(v) for v in args.flip.split(","))
        sm, times, L = build(mv, start, n, args.step, arm_ex=args.arm_ex, spine_ex=args.spine_ex,
                              head_ex=args.head_ex, hip_ex=args.hip_ex, twist_ex=args.twist_ex,
                              flip=flip)
    else:
        sm, times, L = build_pos(mv, start, n, args.step, arm_ex=args.arm_ex,
                                  spine_ex=args.spine_ex, head_ex=args.head_ex,
                                  hip_ex=args.hip_ex, twist_ex=args.twist_ex)
    return sm, times, L


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(required=True)

    p = sub.add_parser("scan"); common(p)
    p.set_defaults(func=lambda a: print(find_window(Mvnx(a.mvnx),
                                                     int(a.window_sec * 240 / a.step) * a.step)))

    p = sub.add_parser("preview"); common(p)
    p.add_argument("--out", default="mvnx_preview.png")
    p.add_argument("--frames", type=int, default=12)

    def _prev(a):
        sm, times, L = prep(a)
        d = json.load(open(a.bbmodel))
        tmp = "__mvnx_preview__"
        d["animations"] = [x for x in d["animations"] if x["name"] != tmp]
        d["animations"].append({"name": tmp, "loop": "loop", "override": False, "length": round(L, 5),
                                 "snapping": 24, "selected": False, "anim_time_update": "",
                                 "blend_weight": "", "start_delay": "", "loop_delay": "",
                                 "animators": {}})
        R.bake_into(d, tmp, sm, times, L)
        import pose_render as pr
        pr.render_dual_view(d, pr.build_hierarchy(d), tmp, a.out, n_frames=a.frames)
        json.dump(d, open("__mvnx_preview.bbmodel", "w"), indent=1)
        print("렌더:", a.out, "/ 모델렌더용 임시 bbmodel: __mvnx_preview.bbmodel")
    p.set_defaults(func=_prev)

    p = sub.add_parser("bake"); common(p)
    p.add_argument("--target", required=True)

    def _bake(a):
        sm, times, L = prep(a)
        d = json.load(open(a.bbmodel))
        if a.target not in {x["name"] for x in d["animations"]}:
            d["animations"].append({"name": a.target, "loop": "loop", "override": False,
                                     "length": round(L, 5), "snapping": 24, "selected": False,
                                     "anim_time_update": "", "blend_weight": "", "start_delay": "",
                                     "loop_delay": "", "animators": {}})
        R.bake_into(d, a.target, sm, times, L)
        bad = R.check_integrity(d)
        json.dump(d, open(a.bbmodel, "w"), indent=1)
        print(f"'{a.target}' 구움 (length={L:.2f}s) 정합성:", "문제있음" if bad else "OK")
    p.set_defaults(func=_bake)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
