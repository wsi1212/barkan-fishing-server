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
        self.quats, self.pos, self.rest, self.rest_pos = [], [], None, None
        for fr in subj.find("m:frames", NS).findall("m:frame", NS):
            o = [float(v) for v in fr.find("m:orientation", NS).text.split()]
            q = [tuple(o[i * 4:i * 4 + 4]) for i in range(len(self.labels))]
            p = [float(v) for v in fr.find("m:position", NS).text.split()]
            pos = [tuple(p[i * 3:i * 3 + 3]) for i in range(len(self.labels))]
            if fr.get("type") != "normal":
                # npose/tpose = 캘리브레이션(차렷) 자세. 모션에선 빼되 ★기준자세로 보관한다.
                # 위치까지 보관하는 게 중요하다 — 사람 척추는 자연스레 굽어 있어서 절대
                # 겨냥각에 10~20도 상수 기울기가 섞이고, 우리 리그의 수직 박스 기준으로는
                # 그게 "계속 앞으로 접힌 자세"로 보인다. 이 기준자세 각을 빼야 0=차렷이 된다.
                if self.rest is None:
                    self.rest, self.rest_pos = q, pos
                continue
            self.quats.append(q)
            self.pos.append(pos)
        if self.rest is None:
            self.rest, self.rest_pos = self.quats[0], self.pos[0]

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
    """MVN(X=앞, Y=왼쪽, Z=위, 오른손) -> 우리 모델(X=오른쪽, Y=위, Z=뒤, 오른손).

    ★Z 부호가 핵심이다. 마인크래프트/블록벤치는 모델 정면이 -Z(북쪽)라서 우리 +Z는 '뒤'다.
    이걸 '앞'으로 잡으면 변환 행렬식이 -1(=거울)이 되어 애니메이션 전체가 앞뒤로
    뒤집힌다 — 뒤로 젖힌 자세가 앞으로 꺾인 자세로 들어가서, 강남스타일이 계속
    구부정하게 나왔던 진짜 원인이다. 각 관절 각도는 원본과 5~10도 내로 일치하는데도
    자세가 이상해 보이면 이 손잡이(handedness)부터 의심할 것."""
    return (-v[1], v[2], -v[0])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


SEG_LEN = 5.625          # 우리 리그의 상완/전완, 허벅지/정강이 한 마디 길이


def M_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dist3(v):
    return math.sqrt(sum(c * c for c in v))


def norm(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def dir_to_xz(v, prev_az=None, eps=0.30):
    """아래로 뻗은 기본자세(0,-1,0)를 방향 v로 보내는 (X각, Z각) 도.

    bbmodel 오일러 합성 순서가 Rz·Ry·Rx라, Rz·Rx·(0,-1,0) = (sz·cx, -cz·cx, -sx).
    Y(비틀림)는 방향을 안 바꾸므로 여기선 안 나온다(따로 처리).

    ★짐벌 특이점: cx=cos(ax)가 0에 가까울 때(=뼈가 정면/정후방을 가리킬 때) az는
    기하학적으로 의미가 없어지고 수치적으로 폭발한다. 강남스타일은 팔을 계속 앞으로
    뻗으므로 정확히 이 지점에 머문다 — 그대로 두면 팔이 매 프레임 튀어서 움직임량이
    원본의 4배가 됐다. 이럴 땐 az를 계산하지 말고 직전 프레임 값을 유지한다
    (어차피 팔 방향은 같으므로 그림은 안 바뀌고 연속성만 얻는다)."""
    x, y, z = norm(v)
    ax = math.degrees(math.asin(max(-1.0, min(1.0, -z))))
    cx = math.cos(math.radians(ax))
    if abs(cx) < eps:
        return ax, (prev_az if prev_az is not None else 0.0)
    az = math.degrees(math.atan2(x / cx, -y / cx))
    return ax, az


def angle_between(a, b):
    a, b = norm(a), norm(b)
    d = max(-1.0, min(1.0, sum(a[i] * b[i] for i in range(3))))
    return math.degrees(math.acos(d))


SHOULDER_X = 5.15625     # steve 어깨 관절의 좌우 위치(모델 유닛)
SHOULDER_Y = 21.5625


def _hand_local(pr, ax, ay, az, bend, side):
    """가슴 기준 손끝 위치(팔 회전만 반영). 보정용이라 가슴 회전은 무시해도 된다
    — 양팔에 똑같이 걸리므로 두 손 '간격'은 거의 안 변한다."""
    R1 = pr.euler_mat(ax, ay, az)
    v1 = pr.mat_vec(R1, [0, -SEG_LEN, 0])
    R2 = pr.mat_mul(R1, pr.euler_mat(bend, 0, 0))
    v2 = pr.mat_vec(R2, [0, -SEG_LEN, 0])
    return [SHOULDER_X * side + v1[0] + v2[0], SHOULDER_Y + v1[1] + v2[1], v1[2] + v2[2]]


def converge_hands(pr, pra_x, pra_z, pla_x, pla_z, prfa, plfa, gap_target, limit=55.0):
    """리그의 두 손 거리를 원본에 맞춘다. 조정 축은 **상완 비틀림(Y)**.

    ★왜 Y인가: 스티브는 양 어깨가 10.3유닛 벌어져 있는데 사람은 우리 스케일로 6유닛
    남짓이라, 원본 각도를 그대로 복사하면 손이 12유닛 떨어진다(원본 4.2). 말춤은 손이
    모여야 말춤이다. 그런데 팔이 앞으로 뻗은 상태(말춤의 기본자세)에서는 Z 회전이 손을
    좌우로 거의 못 옮긴다 — 실제로 Z로 보정했더니 12.3에서 10.6까지밖에 안 좁혀졌다.
    팔이 앞을 향할 때 상완을 비틀면 굽힌 전완이 안쪽으로 스윙한다. 사람이 실제로 손을
    모으는 방식과 같다."""
    ry = [0.0] * len(pra_x)
    ly = [0.0] * len(pra_x)
    for i in range(len(pra_x)):
        best, best_err = 0.0, None
        # 굵게 훑고 다시 미세하게 — 한 프레임당 수십 번 평가라 비용은 무시할 만하다.
        for coarse in range(-int(limit), int(limit) + 1, 5):
            rh = _hand_local(pr, pra_x[i], coarse, pra_z[i], prfa[i], +1)
            lh = _hand_local(pr, pla_x[i], -coarse, pla_z[i], plfa[i], -1)
            gap = math.sqrt(sum((rh[j] - lh[j]) ** 2 for j in range(3)))
            err = abs(gap - gap_target[i])
            if best_err is None or err < best_err:
                best, best_err = float(coarse), err
        ry[i], ly[i] = best, -best
    return R.smooth(R.smooth(ry, 7), 7), R.smooth(R.smooth(ly, 7), 7)


def unwrap(seq):
    """±180 경계에서 튀는 각도열을 연속으로 편다.

    ★IK/겨냥각은 팔이 수평 위로 올라가는 순간 az가 +179 -> -179로 점프한다. 그대로
    구우면 그 사이를 보간하느라 팔이 반대편으로 홱 돌아간다(상완 진폭이 원본 141도인데
    666도로 측정됐던 원인). 각도는 ±180을 넘어도 되므로 이어붙이는 게 맞다."""
    out = [seq[0]]
    for v in seq[1:]:
        dv = v - out[-1]
        while dv > 180:
            dv -= 360
        while dv < -180:
            dv += 360
        out.append(out[-1] + dv)
    return out


def two_bone_ik(target, L1, L2, prev_az=None):
    """어깨(엉덩이) 기준 목표 위치 -> (부모뼈 X각, 부모뼈 Z각, 자식뼈 굽힘각).

    ★각도 복사가 아니라 **위치를 맞추는** 이유: 스티브는 어깨 간격·팔 길이 비율이
    사람과 달라서, 원본과 똑같은 어깨/팔꿈치 각도를 줘도 손끝이 11유닛이나 벌어진다
    (강남스타일의 '두 손 모으기'가 전혀 안 나왔던 원인 — 원본 1.4유닛 vs 결과 12유닛).
    알파 부호는 FK로 되돌려 검증했다(+1이면 오차 10.6유닛, -1이면 0.64유닛)."""
    dist = math.sqrt(sum(c * c for c in target))
    dist = max(abs(L1 - L2) + 0.05, min(L1 + L2 - 0.05, dist))
    ci = (L1 * L1 + L2 * L2 - dist * dist) / (2 * L1 * L2)
    bend = 180.0 - math.degrees(math.acos(max(-1.0, min(1.0, ci))))
    cosa = (dist * dist + L1 * L1 - L2 * L2) / (2 * dist * L1)
    alpha = math.degrees(math.acos(max(-1.0, min(1.0, cosa))))
    ax, az = dir_to_xz(target, prev_az)
    return ax - alpha, az, bend


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

    # ★촬영장 기준 방향을 우리 모델의 정면(+Z)에 맞춘다.
    # MVN 전역 좌표계는 사람이 아니라 **방** 기준이라, 피험자가 어느 쪽을 보고 섰는지에 따라
    # "앞"이 우리 +Z와 어긋난다. 그대로 쓰면 좌우 다리가 벌어진 채 고정되고(우 -19도/좌 +29도)
    # 몸이 계속 기울어 보인다 — 실제로 강남스타일이 그렇게 나왔다. 구간 평균 어깨선 방향으로
    # 상수 yaw를 재서 모든 좌표를 미리 돌려 놓는다(프레임별 잔여 회전은 그대로 twist가 된다).
    def raw(f, seg):
        return to_ours(mv.rest_pos[I[seg]] if f == -1 else mv.pos[f][I[seg]])

    ys = []
    for f in idxs:
        sh = sub(raw(f, "LeftShoulder"), raw(f, "RightShoulder"))
        ys.append(math.atan2(sh[2], sh[0]))
    # 각도 평균은 원형이라 벡터 평균으로 낸다(179도와 -179도의 산술평균은 0이 되어버림)
    my = math.atan2(sum(math.sin(v) for v in ys), sum(math.cos(v) for v in ys))
    face = my - math.pi          # 정면 기준(어깨선이 -X를 향할 때가 정면)
    # ★부호 주의: Y축 회전 θ는 각도를 (my - θ)로 옮긴다. 어깨선을 -X(=모델 왼쪽)로
    # 보내려면 θ = my - π = face 여야 한다. -face로 돌리면 2my-π가 되어 정확히
    # 좌우가 뒤집힌 채 정렬된다(어깨선이 +X를 가리킴 = 거울상).
    ca, sa = math.cos(face), math.sin(face)

    def P(f, seg):
        x, y, z = raw(f, seg)
        return (x * ca + z * sa, y, -x * sa + z * ca)

    # ★루트 비틀림을 먼저 확정한다. player_root의 Y회전은 팔·다리에도 그대로 곱해지므로,
    # IK 목표를 이 회전이 걷힌 좌표계로 옮겨놓지 않으면 발의 앞뒤 성분(±1유닛)이 좌우
    # 성분(±4유닛)과 섞여 부호가 뒤집힌다 — "다리가 반대"로 보이던 원인.
    prev_az = {}          # 팔다리별 직전 Z각(특이점에서 유지용)
    # ★가슴 회전은 팔 목표를 걷어낼 때 쓰이는데, T8->목 마디가 14cm밖에 안 돼서 위치
    # 노이즈가 각도로 크게 증폭된다. 원시값을 쓰면 그 노이즈가 팔 목표에 곱해져 팔이
    # 매 프레임 떨린다(움직임량이 원본의 4배였던 원인). 미리 평활해 두고 쓴다.
    cx_raw, cz_raw = [], []
    for f in idxs:
        a_, b_ = dir_to_xz([-c for c in M_sub(P(f, "Neck"), P(f, "T8"))])
        cx_raw.append(a_); cz_raw.append(b_)
    CX = [0.0] + R.smooth(R.smooth(cx_raw, 9), 9)
    CZ = [0.0] + R.smooth(R.smooth(cz_raw, 9), 9)
    tw_raw = []
    for f in idxs:
        sh = M_sub(P(f, "LeftShoulder"), P(f, "RightShoulder"))
        tw_raw.append(math.degrees(math.atan2(sh[2], sh[0])))
    _sm = R.smooth(tw_raw)
    _m = R.mean(_sm)
    TW = R.clamp([(v - _m) * twist_ex for v in R.deadzone([v - _m for v in _sm], 1.5)], -35, 35)
    TW = [0.0] + TW          # 인덱스 0은 기준자세(f=-1)용

    KEYS = ("waist_x", "waist_z", "chest_x", "chest_z", "twist",
            "pra_x", "pra_z", "pla_x", "pla_z", "prl_x", "prl_z", "pll_x", "pll_z",
            "prfa", "plfa", "prfl", "plfl", "rx", "ry", "rz", "head_x", "head_y", "hgap")
    ch = {k: [] for k in KEYS}
    # ★기준자세(차렷)에서의 같은 각도 — 아래 루프가 끝난 뒤 전부 빼서 "0=차렷"으로 맞춘다.
    rest_ch = {k: [] for k in KEYS}
    base_spine = [0.0, 0.0, 0.0, 0.0]   # 기준자세의 (wx, wz, cx, cz)
    for _fi, f in enumerate([-1] + idxs):   # -1 = 기준자세
        into = rest_ch if f == -1 else ch
        untwist = mat_t(pr.euler_mat(0, TW[_fi], 0))   # 루트 Y회전 제거용
        pelvis, t8, neck = P(f, "Pelvis"), P(f, "T8"), P(f, "Neck")
        # 몸통: 골반->T8이 허리, T8->목이 가슴. 좌우 어깨선으로 몸 전체 비틀림.
        wx, wz = dir_to_xz([-c for c in sub(t8, pelvis)])   # 위로 뻗은 축이라 부호 반전
        cx, cz = dir_to_xz([-c for c in sub(neck, t8)])
        if f == -1:
            base_spine[:] = [wx, wz, cx, cz]
        else:
            # ★기준자세(차렷)의 척추 굽음을 여기서 바로 뺀다. 나중에 빼면 늦다 —
            # 아래에서 팔다리의 부모 회전을 걷어낼 때 이 각도를 쓰기 때문에, 보정 전
            # 값을 쓰면 척추의 자연 굽음이 팔다리 각도로 그대로 전가된다(다리가 계속
            # 19도 뒤로 가 있어서 몸이 앞으로 꺾여 보였다).
            wx -= base_spine[0]; wz -= base_spine[1]
            cx -= base_spine[2]; cz -= base_spine[3]
        into["waist_x"].append(wx); into["waist_z"].append(wz)
        into["chest_x"].append(cx - wx); into["chest_z"].append(cz - wz)
        sh = sub(P(f, "LeftShoulder"), P(f, "RightShoulder"))
        into["twist"].append(math.degrees(math.atan2(sh[2], sh[0])))
        hd = sub(P(f, "Head"), neck)
        into["head_x"].append(dir_to_xz([-c for c in hd])[0])
        into["head_y"].append(0.0)

        # 팔다리: 부모(가슴/골반) 회전을 걷어낸 뒤 겨냥각을 뽑는다.
        # 팔은 가슴의 자식이라 가슴의 절대 회전을 걷어내야 로컬 각이 된다(평활값 사용).
        parT = mat_t(pr.euler_mat(CX[_fi], 0, CZ[_fi]))
        # ★다리는 다르다 — rig-conventions.md대로 prl/pll은 허리가 아니라 player_root의
        # 직계 자식이라 몸통 회전을 물려받지 않는다. 그래서 걷어내면 안 되고 월드 방향을
        # 그대로 쓴다(걷어냈더니 척추 기울기가 다리로 전가돼 우/좌가 -19도/+25도로
        # 벌어진 채 고정됐다). 루트 비틀림(Y)은 방향의 X/Z 성분에 영향이 작아 무시.
        hipT = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        # ★팔다리는 각도 복사가 아니라 IK — 손끝/발끝이 원본과 같은 자리에 오도록 푼다.
        # 원본 팔다리 길이로 정규화한 뒤 우리 뼈 길이(5.625+5.625)에 맞춰 늘린다.
        # ★팔도 IK가 아니라 FK다. 2본 IK는 손이 가슴 근처(=목표 거리가 짧을 때) 알파가
        # 90도 부근이라 손이 조금만 움직여도 상완이 크게 휜다 — 실측 움직임량이 원본의
        # 4배(11073도 vs 2788도)로 팔이 떨었다. 상완 방향과 팔꿈치 굽힘을 그대로 복사하는
        # 쪽이 원본에 훨씬 충실하다. '두 손 모으기'는 아래 arm_converge 보정으로 따로 만든다.
        for side, up, low, end, k, seg in (
                ("R", "RightUpperArm", "RightForeArm", "RightHand", "pra", "prfa"),
                ("L", "LeftUpperArm", "LeftForeArm", "LeftHand", "pla", "plfa")):
            d_ = pr.mat_vec(parT, pr.mat_vec(untwist, list(sub(P(f, low), P(f, up)))))
            ax, az = dir_to_xz(d_, prev_az.get(k))
            prev_az[k] = az
            bend = angle_between(sub(P(f, low), P(f, up)), sub(P(f, end), P(f, low)))
            into[k + "_x"].append(ax); into[k + "_z"].append(az); into[seg].append(bend)
        # ★다리는 IK가 아니라 FK(허벅지 방향 + 무릎 굽힘 복사)다.
        # IK는 발 '위치'만 맞추는데, 무릎을 앞으로 크게 드는 동작(말춤의 핵심)은 발이
        # 몸 아래에 그대로 있어서 IK가 "다리 쭉 뻗고 발만 제자리"로 풀어버린다.
        # 실측: 원본 허벅지 진폭 56도인데 IK 결과는 19도(계속 -20도에 붙어 있었음).
        # 눈에 보이는 건 허벅지 각도지 발 좌표가 아니다.
        for side, up, low, end, k, seg in (
                ("R", "RightUpperLeg", "RightLowerLeg", "RightFoot", "prl", "prfl"),
                ("L", "LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "pll", "plfl")):
            thigh = pr.mat_vec(untwist, list(sub(P(f, low), P(f, up))))
            ax, az = dir_to_xz(thigh, prev_az.get(k))
            prev_az[k] = az
            bend = angle_between(sub(P(f, low), P(f, up)), sub(P(f, end), P(f, low)))
            into[k + "_x"].append(ax); into[k + "_z"].append(az); into[seg].append(bend)
        into["hgap"].append(dist3(sub(P(f, "RightHand"), P(f, "LeftHand"))) * (30.0 / 1.75))
        p = P(f, "Pelvis")
        into["rx"].append(p[0]); into["ry"].append(p[1]); into["rz"].append(p[2])

    # ★기준자세 빼기 = "0은 차렷 자세". 평균 빼기(옛 방식)와 결정적으로 다르다:
    # 강남스타일처럼 한 자세를 오래 유지하는 춤은 그 자세가 곧 평균이라, 평균을 빼면
    # 시그니처 포즈가 통째로 사라진다(실제로 '두 손 모아 앞으로'가 지워져서 팔 내리고
    # 흔드는 춤이 나왔다). 기준자세는 클립 내용과 무관한 상수라 그런 일이 없다.
    # ★척추·머리에만 적용한다. MVNX의 캘리브레이션 프레임은 이름이 npose라도 실제로는
    # **T포즈(팔 수평)** 라서, 팔다리에까지 빼면 차렷이 -90도로 읽혀 팔이 뒤틀린다(실측).
    # 팔다리는 애초에 보정이 필요 없다 — dir_to_xz의 0도가 "곧게 아래"이고 그게 우리 리그의
    # 쉬는 자세와 정확히 같다.
    for k in ("head_x",):        # 척추는 루프 안에서 이미 보정됨
        base = rest_ch[k][0]
        ch[k] = [v - base for v in ch[k]]

    m2u = 30.0 / 1.75
    win = max(3, (len(idxs) // 2) | 1)

    def C(key, ex, lo, hi, dead=2.0):
        """평균중심화 경로 — ★비틀림처럼 '전역 기준이 임의'인 채널에만 쓸 것."""
        sm = R.smooth(ch[key])
        m = R.mean(sm)
        d = R.deadzone([v - m for v in sm], dead)
        return R.clamp([v * ex for v in d], lo, hi)

    def A(key, ex, lo, hi):
        """★절대 각도 경로(기본). 방향벡터로 뽑은 겨냥각은 이미 '쉬는 자세=0'인
        해부학적 절대값이라 평균중심화하면 안 된다 — 유지되는 자세(강남스타일의
        '두 손 모아 앞으로' 같은)는 거의 상수라서 평균을 빼면 통째로 사라진다.
        실제로 그래서 말춤이 팔 내리고 흔드는 춤으로 나왔다(2026-08-12)."""
        return R.clamp([v * ex for v in R.smooth(ch[key])], lo, hi)

    waist_x = A("waist_x", spine_ex, -30, 30); waist_z = A("waist_z", spine_ex, -25, 25)
    chest_x = A("chest_x", spine_ex, -30, 30); chest_z = A("chest_z", spine_ex, -25, 25)
    # 비틀림만 중심화 — 촬영장에서 어느 방향을 보고 섰는지는 임의값이라 상수 성분에 의미가 없다.
    twist = TW[1:]          # 루프 전에 확정한 값(팔다리 IK와 동일한 값이어야 한다)
    # ★IK 결과라 clamp를 넉넉히 — 좁게 잡으면 손끝이 목표에서 밀려나 '손 모으기'가 깨진다.
    pra_x = A("pra_x", arm_ex, -170, 170); pla_x = A("pla_x", arm_ex, -170, 170)
    pra_z = A("pra_z", arm_ex, -140, 140); pla_z = A("pla_z", arm_ex, -140, 140)
    prl_x = A("prl_x", hip_ex, -80, 100); pll_x = A("pll_x", hip_ex, -80, 100)
    # ★다리 벌림(Z)만은 중심화한다. 사람 허벅지는 원래 안쪽으로 10~20도 기울어 있는데
    # (골반이 무릎보다 넓다) 우리 리그는 다리 박스 둘이 딱 붙어 있어서 그 상수를 그대로
    # 주면 두 다리가 30초 내내 교차한 채 꼬여 보인다. 흔들림(변화분)만 남긴다.
    # IK는 발 위치를 직접 맞추므로 중심화하면 안 된다(위치가 어긋남).
    prl_z = A("prl_z", hip_ex, -45, 45); pll_z = A("pll_z", hip_ex, -45, 45)
    # 굽힘은 두 세그먼트 사이의 기하학적 각도라 0=쭉 편 상태. debias 불필요.
    pra_y, pla_y = converge_hands(pr, pra_x, pra_z, pla_x, pla_z,
                                   R.smooth(ch["prfa"]), R.smooth(ch["plfa"]),
                                   R.smooth(ch["hgap"]))
    prfa = R.clamp(R.smooth(ch["prfa"]), 0, 120)
    plfa = R.clamp(R.smooth(ch["plfa"]), 0, 120)
    prfl = R.clamp(R.smooth(ch["prfl"]), 0, 110)
    plfl = R.clamp(R.smooth(ch["plfl"]), 0, 110)

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
        "pra_x": pra_x, "pra_y": pra_y, "pra_z": pra_z,
        "pla_x": pla_x, "pla_y": pla_y, "pla_z": pla_z,
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
    # ★각도 연속화는 스무딩·clamp보다 먼저. 순서가 바뀌면 점프 지점을 평균내 버린다.
    for k in ("pra_x", "pra_z", "pla_x", "pla_z", "prl_x", "prl_z", "pll_x", "pll_z"):
        ch[k] = unwrap(ch[k])

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
    p.add_argument("--loop-frac", type=float, default=0.08,
                   help="루프 크로스페이드 비율. 긴 클립(30초)엔 0.03 정도가 적당 — "
                        "0.08이면 2.4초가 뭉개진다")


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
                                  hip_ex=args.hip_ex, twist_ex=args.twist_ex,
                                  loop_frac=args.loop_frac)
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
