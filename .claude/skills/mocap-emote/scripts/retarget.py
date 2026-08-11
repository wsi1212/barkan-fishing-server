#!/usr/bin/env python3
"""CMU mocap(ASF/AMC) -> steve.bbmodel(BetterModel 13본 리그) 리타게팅 CLI.

사용 예:
    # 1) 클립 전체에서 가장 동적인 2초 구간 자동 탐색(정적 구간만 있는지도 확인)
    python3 retarget.py scan --asf 60.asf --amc 60_01.amc

    # 2) 미리보기 렌더만(파일에 안 씀) — 반드시 굽기 전에 눈으로 확인할 것
    python3 retarget.py preview --asf 60.asf --amc 60_01.amc --start 600 --out preview.png

    # 3) 확정본을 steve.bbmodel의 특정 애니(예: dance)에 굽기
    python3 retarget.py bake --asf 60.asf --amc 60_01.amc --start 600 --target dance

파이프라인 요약(왜 이렇게 하는지는 references/ 참고):
  다운로드(CMU, 라이선스 자유재배포) -> ASF/AMC 파싱 -> 각 본의 "부모 기준 로컬 회전"만
  추출(전체 FK 불필요, 조상 회전은 수학적으로 상쇄됨) -> 다관절 본은 Euler XYZ decompose,
  단일 DOF 본(팔꿈치·무릎)은 raw 채널 직접 사용(짐벌락 회피) -> window 평균으로 중심화 후
  과장 배율 적용 -> 우리 리그 축 규약으로 부호/오프셋 정렬 -> z-fight 오프셋 주입 ->
  루프 클로징(꼬리 15%를 시작값으로 크로스페이드) -> bbmodel에 굽기 -> 반드시 렌더 확인 후 배포.
"""
import argparse
import json
import math
import uuid as uuidlib

from asf_amc import Skeleton, parse_amc

DEFAULT_BBMODEL = ("/Users/user/Library/Application Support/feather/player-server/servers/"
                    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BetterModel/players/steve.bbmodel")
INCH2UNIT = 0.056444 * 32  # asf FAQ의 inch->meter 공식(0.056444)에 1블록=32유닛 근사 스케일

ENERGY_BONES = ["rhumerus", "lhumerus", "rfemur", "lfemur", "rtibia", "ltibia"]

# 다리 세그먼트 길이(steve.bbmodel 실측: 허벅지 큐브 y 5.625~11.25, 정강이 0~5.625).
# 발 접지(foot lock) 계산에 쓴다 — 무릎을 굽히면 골반이 그만큼 내려앉아야 발이 안 뜬다.
THIGH_LEN, SHIN_LEN = 5.625, 5.625
LEG_REST = THIGH_LEN + SHIN_LEN

# breathe 애니에서 추출한 z-fight baseline(본 이름 -> (x,y,z) position 상수).
# 회전이 들어가는 본(전완/무릎 포함)엔 x,y도 살짝 줘서 "어느 축도 완전히 안 겹치게" 한다
# (z만 다르면 되는 줄 알았는데, 축 하나라도 겹치면 여전히 z-fight 남는 케이스가 있었음).
ZFIGHT = {
    # 관절 두 큐브의 맞닿는 면 법선 방향으로 0.12u 겹친다. 접선(z)만 어긋나면
    # 면 자체는 여전히 같은 평면이라 몸통·어깨에서 z-fighting이 남는다.
    "pw_waist": (0, -0.12, 0.05), "pc_chest": (0, -0.12, -0.05), "h_ph_head": (0, -0.12, 0.05),
    "pra_right_arm": (-0.12, 0, -0.06), "pla_left_arm": (0.12, 0, -0.06),
    "prfa_right_forearm": (0.06, 0.12, -0.07), "plfa_left_forearm": (-0.06, 0.12, -0.07),
    "prl_right_leg": (0, 0.12, 0.05), "pll_left_leg": (0, 0.12, -0.05),
    "prfl_right_foreleg": (0.04, 0.12, 0.05), "plfl_left_foreleg": (-0.04, 0.12, -0.05),
}


def mean(vals):
    return sum(vals) / len(vals)


def smooth(vals, window=5):
    """단순 이동평균. 원본 mocap의 고주파 미세떨림(근육 트레머·센서 노이즈)이
    exaggeration 배율로 그대로 곱해지면 "부들부들" 떠는 것처럼 보인다(직접 겪은
    피드백) — 과장하기 전에 먼저 이걸로 죽인다. window는 홀수 권장."""
    n = len(vals)
    half = window // 2
    out = []
    for i in range(n):
        lo, hi = max(0, i - half), min(n, i + half + 1)
        out.append(sum(vals[lo:hi]) / (hi - lo))
    return out


def highpass(vals, window):
    """긴 이동평균(=저주파 성분)을 빼서 느린 표류만 제거하고 빠른 진동은 남긴다.
    detrend()는 첫/끝을 잇는 직선만 빼기 때문에, 캡처 볼륨을 크게 왕복하는 소스에선
    가운데가 여전히 크게 부풀어 모델이 몸(히트박스)에서 떨어져 나간다 —
    실제로 dance의 루트 X가 12유닛(≈0.8블록)까지 밀려 있었다."""
    if window < 3:
        return list(vals)
    base = smooth(vals, window if window % 2 else window + 1)
    return [v - b for v, b in zip(vals, base)]


def debias(vals, pct=10.0):
    """하위 pct% 값을 "완전히 편 상태"로 보고 그만큼 빼서 0에 붙인다(음수는 0으로).

    ★ASF 캘리브레이션 오프셋 때문에 팔꿈치·무릎의 raw 값은 가장 편 순간에도 20~60도
    굽어 있는 경우가 흔하다. 그대로 쓰면 어떤 소스를 넣어도 영구 스쿼트(무릎 25~87도)
    + T-rex 팔(팔꿈치 62~110도)이 된다 — 실제로 salsa 소스에서 그렇게 나왔다.
    굽힘의 상대 진폭은 그대로 보존되므로 동작 자체는 안 죽는다."""
    s = sorted(vals)
    base = s[min(len(s) - 1, int(len(s) * pct / 100.0))]
    return [max(0.0, v - base) for v in vals]


def foot_drop(hip_x, knee_x):
    """엉덩이 기준 발끝까지의 수직 낙차(유닛). 무릎이 굽을수록 작아진다(=발이 올라감).
    자식 본은 부모 기준이라 정강이의 절대 피치 = hip + knee."""
    a = math.radians(hip_x)
    return THIGH_LEN * math.cos(a) + SHIN_LEN * math.cos(a + math.radians(knee_x))


def deadzone(delta_vals, thresh):
    """센터링 후(exaggeration 전) range가 thresh 미만이면 사실상 "안 움직인 것"으로
    보고 전부 0으로 눕힌다 — 안 그러면 미세한 노이즈가 과장 배율만큼 커져서 잔떨림으로
    보인다. 진짜 움직이는 관절은 그대로 통과."""
    if max(delta_vals) - min(delta_vals) < thresh:
        return [0.0] * len(delta_vals)
    return delta_vals


def clamp(vals, lo, hi):
    return [max(lo, min(hi, v)) for v in vals]


def close_loop(vals, frac=0.08):
    """마지막 frac 구간을 시작값으로 선형 크로스페이드 -> 루프 이음매 제거.
    실제 모캡은 안 루프되므로 이게 없으면 재생마다 툭 끊기는 게 보인다.

    ★frac이 크면(옛 기본 0.15) 5초 루프의 끝 0.75초가 통째로 뭉개져 매 사이클마다
    동작이 죽는 구간이 생긴다. 대신 find_best_window가 시작/끝 자세가 비슷한 구간을
    고르게 해서(loop_weight) 짧은 크로스페이드로도 이음매가 안 보이게 한다."""
    n = len(vals)
    blend_start = int(n * (1 - frac))
    out = list(vals)
    for i in range(blend_start, n):
        f = (i - blend_start) / max(1, (n - 1 - blend_start))
        out[i] = vals[i] * (1 - f) + vals[0] * f
    out[-1] = vals[0]
    return out


NEUTRAL_BONES = ["rfemur", "lfemur", "lowerback"]


def find_best_window(sk, frames, n, stride=15, margin=0, loop_weight=1.5, neutral_weight=1.2):
    """rhumerus 등 주요 본 raw 1번축 값의 window 내 range 합이 최대인 시작 인덱스.
    ★첫 구간(프레임 0)을 그냥 쓰지 말 것 — 캡처 시작은 정지 자세인 경우가 흔하다.

    ★loop_weight: 시작 자세와 끝 자세의 차이(도)를 점수에서 뺀다. 둘이 비슷한 구간을
    고르면 루프 이음매가 애초에 거의 없어서 close_loop이 동작을 뭉갤 일이 없다.

    ★neutral_weight: 시작 자세가 그 구간의 평균 자세에서 얼마나 벗어났는지도 뺀다.
    이음매가 매끄러워도 그 자세가 깊은 런지면 루프마다 웅크리는 게 보인다(실제로
    salsa 630프레임 구간이 양다리 앞·허리 -30도로 시작해 매 사이클 0.6초씩 주저앉았다).
    애니메이션 관행대로 "지나가는 중립 자세"에서 끊는 것과 같은 효과.
    둘 다 0을 주면 옛 동작(에너지만 보기)."""
    best_start, best_score = margin, -1e9
    lo, hi = margin, len(frames) - n - margin
    for start in range(lo, max(lo + 1, hi), stride):
        window = frames[start:start + n]
        energy = 0.0
        seam = 0.0
        for bone in ENERGY_BONES:
            vals = [sk.raw_dof(f, bone, 0) for f in window]
            energy += max(vals) - min(vals)
            seam += abs(vals[-1] - vals[0])
        neutral = 0.0
        for bone in NEUTRAL_BONES:
            vals = [sk.raw_dof(f, bone, 0) for f in window]
            neutral += abs(vals[0] - mean(vals))
        score = energy - loop_weight * seam - neutral_weight * neutral
        if score > best_score:
            best_score, best_start = score, start
    return best_start, best_score


def retarget_window(sk, frames, start, n, step, arm_ex=1.3, spine_ex=2.5, head_ex=2.0, hip_ex=1.5,
                     use_real_root_y=False, root_y_scale=0.5, synth_spin=False,
                     fps=60.0, twist_ex=2.0, root_xz_max=2.5, footlock=True, bounce=0.0,
                     loop_frac=0.08, leg_spread=0.5, flip_leg_z=False):
    """지정 구간을 우리 리그 회전값 시계열로 변환.

    핵심 원리: local_rot(bone) = C@Rdof@Cinv 는 "부모 기준 로컬 회전 델타"라
    조상의 회전(루트 포함, 캡처 좌표계가 아무리 이상해도)이 수학적으로 상쇄되어
    안 들어간다 — 그래서 절대 world 자세가 이상해 보여도(루트가 -95/86/-103도처럼
    캘리브레이션 특이값을 가져도) 리타게팅 결과엔 영향 없다.

    다관절 본(어깨 rhumerus/lhumerus, 엉덩이 rfemur/lfemur, 척추 lowerback/upperback,
    머리 head)은 euler decompose가 안전(ry가 ±90 근처만 아니면). 단일 DOF 본(팔꿈치
    rradius/lradius, 무릎 rtibia/ltibia)은 반드시 raw dof 값을 직접 쓸 것 —
    decompose하면 그 축이 짐벌락(ry≈±90)에 자주 걸려 rx/rz가 -180~180으로
    요동치는 가짜 신호가 나온다(직접 겪은 버그).
    """
    idxs = list(range(start, start + n, step))
    sample_frames = [frames[i] for i in idxs]
    dt = step / fps  # CMU 대부분 60fps. subject 85 등 120fps 클립은 --fps 120 필수
    times = [i * dt for i in range(len(sample_frames))]
    L = times[-1]

    def series_decomp(bone):
        from asf_amc import decompose_xyz
        return [decompose_xyz(sk.local_rot(bone, f)) for f in sample_frames]

    def series_raw(bone, idx=0):
        return [sk.raw_dof(f, bone, idx) for f in sample_frames]

    lowerback = series_decomp("lowerback"); upperback = series_decomp("upperback"); head = series_decomp("head")
    rhumerus = series_decomp("rhumerus"); lhumerus = series_decomp("lhumerus")
    rfemur = series_decomp("rfemur"); lfemur = series_decomp("lfemur")
    rradius = series_raw("rradius"); lradius = series_raw("lradius")
    rtibia = series_raw("rtibia"); ltibia = series_raw("ltibia")
    root_tx = series_raw("root", 0); root_ty = series_raw("root", 1); root_tz = series_raw("root", 2)

    # ★옛 코드는 rescale(smooth(rradius), 12, 65)로 팔꿈치를 "무조건 12~65도를 꽉 채우도록"
    # 늘렸다. 그래서 팔꿈치가 거의 안 움직이는 구간에서도 강제로 53도를 휘두르고(노이즈 증폭),
    # 반대로 크게 굽히는 동작은 65도에 눌려서, 어떤 소스를 넣어도 똑같은 기계적 스윙이 됐다.
    # 실측 굽힘각을 그대로 쓰고 안전 범위로 clamp만 한다(8도는 완전히 편 팔이 뻣뻣해 보이지
    # 않게 주는 기본 굽힘).
    prfa_curl = clamp([8 + v for v in debias(smooth(rradius))], 0, 110)
    plfa_curl = clamp([8 + v for v in debias(smooth(lradius))], 0, 110)
    prfl_bend = clamp(debias(smooth(rtibia)), 0, 100)
    plfl_bend = clamp(debias(smooth(ltibia)), 0, 100)

    def centered(vals, ex, dead_thresh):
        """스무딩 -> 평균중심화 -> 데드존(원 진폭 기준) -> 과장 순서.
        데드존은 과장 *전* 진폭으로 판정해야 한다(과장 후 재면 이미 커져서 항상 통과함)."""
        sm = smooth(vals)
        m = mean(sm)
        d = [v - m for v in sm]
        d = deadzone(d, dead_thresh)
        return [v * ex for v in d]

    def shoulder_series(dec, ex):
        rx = centered([d[0] for d in dec], ex, dead_thresh=6.0)
        ry = centered([d[1] for d in dec], ex, dead_thresh=6.0)
        rz = centered([d[2] for d in dec], ex, dead_thresh=6.0)
        return rx, ry, rz

    r_arm_x, r_arm_y, r_arm_z = shoulder_series(rhumerus, arm_ex)
    l_arm_x, l_arm_y, l_arm_z = shoulder_series(lhumerus, arm_ex)
    # ★어깨 비틀림(Y). 박스 팔이라 축 회전이 그대로 보인다 — 팔을 휘두를 때 손등 방향이
    # 같이 도는 것만으로 "막대기 휘두르기"가 사람 동작으로 바뀐다.
    r_arm_y = clamp(r_arm_y, -25, 25)
    l_arm_y = clamp(l_arm_y, -25, 25)
    # 우리 리그 기본 오프셋(양팔이 완전히 처지지 않고 살짝 벌어진 기본자세) 위에 델타를 얹음.
    # 규약: 오른팔 +Z=바깥, 왼팔 -Z=바깥(나치경례처럼 보이는 단일팔 큰 각도 금지).
    # ★몸 관통 방지 clamp — exaggeration이 커도 이 범위를 못 넘는다(실제 겪은 clipping 버그).
    r_arm_z = clamp([20 + v for v in r_arm_z], -20, 130)
    l_arm_z = clamp([-20 + v for v in l_arm_z], -130, 20)
    r_arm_x = clamp([15 + v for v in r_arm_x], -50, 110)
    l_arm_x = clamp([15 + v for v in l_arm_x], -50, 110)

    def hip_series(dec, ex):
        rx = centered([d[0] for d in dec], ex, dead_thresh=5.0)
        ry = centered([d[1] for d in dec], ex, dead_thresh=5.0)
        rz = centered([d[2] for d in dec], ex, dead_thresh=5.0)
        return rx, ry, rz

    r_hip_x, r_hip_y, r_hip_z = hip_series(rfemur, hip_ex)
    l_hip_x, l_hip_y, l_hip_z = hip_series(lfemur, hip_ex)
    r_leg_x = clamp([8 + v for v in r_hip_x], -20, 90)
    l_leg_x = clamp([8 + v for v in l_hip_x], -20, 90)
    # ★다리 벌림(Z)과 회전(Y). 옛 코드는 X(앞뒤 킥)만 써서 두 발이 항상 정면 평행이었다 —
    # 그래서 어떤 춤을 넣어도 걷기 사이클처럼 보였다. 벌림이 있어야 스텝이 스텝으로 읽힌다.
    # 부호 규약은 팔과 동일(오른쪽 +Z=바깥). mocap의 좌우 부호가 우리 리그와 반대면
    # 두 다리가 같은 방향으로 쏠려 "기우뚱"하게 보이므로 preview에서 확인하고
    # --flip-leg-z로 뒤집을 것.
    r_leg_z = clamp([v * leg_spread for v in r_hip_z], -22, 22)
    l_leg_z = clamp([v * leg_spread for v in l_hip_z], -22, 22)
    if flip_leg_z:
        r_leg_z = [-v for v in r_leg_z]
        l_leg_z = [-v for v in l_leg_z]
    r_leg_y = clamp(r_hip_y, -20, 20)
    l_leg_y = clamp(l_hip_y, -20, 20)

    def spine_series(dec, ex, tex):
        rx = centered([d[0] for d in dec], ex, dead_thresh=3.0)
        ry = centered([d[1] for d in dec], tex, dead_thresh=2.0)
        rz = centered([d[2] for d in dec], ex, dead_thresh=3.0)
        return rx, ry, rz

    waist_x, waist_y, waist_z = spine_series(lowerback, spine_ex, twist_ex)
    chest_x, chest_y, chest_z = spine_series(upperback, spine_ex, twist_ex)
    waist_x, waist_z = clamp(waist_x, -30, 30), clamp(waist_z, -25, 25)
    chest_x, chest_z = clamp(chest_x, -30, 30), clamp(chest_z, -25, 25)
    # ★★몸통 비틀림(Y) — 이 리타게터의 가장 큰 구멍이었다. 9종 춤 전부 골반·척추·어깨의
    # Y가 정확히 0이라(머리만 예외) 키프레임을 1224개 박아도 앞뒤로만 흔드는 태엽인형이었다.
    # 골반과 어깨가 반대 위상으로 비틀리는 게 춤이 춤으로 보이는 핵심이다. 데드존도 낮게
    # (2도) 잡는다 — 비틀림은 진폭이 작아도 실루엣에 크게 보인다.
    waist_y = clamp(waist_y, -30, 30)
    chest_y = clamp(chest_y, -30, 30)

    def head_series(dec, ex):
        rx = centered([d[0] for d in dec], ex, dead_thresh=3.0)
        ry = centered([d[1] for d in dec], ex, dead_thresh=3.0)
        rz = centered([d[2] for d in dec], ex, dead_thresh=3.0)
        return rx, ry, rz

    head_x, head_y, head_z = head_series(head, head_ex)
    head_x, head_y = clamp(head_x, -25, 25), clamp(head_y, -35, 35)
    head_z = clamp(head_z, -18, 18)  # 갸웃(roll) — 리듬 타는 느낌이 여기서 나온다

    def detrend(vals):
        n2 = len(vals); v0, v1 = vals[0], vals[-1]
        return [vals[i] - (v0 + (v1 - v0) * i / (n2 - 1)) for i in range(n2)]

    # 루트 tx/tz는 실제 캡처 볼륨을 가로지르는 이동이 섞여있다. 선형 성분(detrend)만
    # 빼는 걸론 부족해서 — 가운데가 크게 부풀어 dance의 루트가 X로 12유닛(≈0.8블록)까지
    # 밀려 있었다. 모델만 옆으로 미끄러지고 히트박스·이름표는 제자리라 "몸에서 떨어져
    # 나간" 것처럼 보인다. 긴 이동평균까지 뺀 뒤(highpass) 하드 clamp로 제자리에 묶는다.
    win = max(3, (len(times) // 2) | 1)
    root_x = clamp([v * INCH2UNIT * 0.6 for v in highpass(detrend(root_tx), win)],
                    -root_xz_max, root_xz_max)
    root_z = clamp([v * INCH2UNIT * 0.6 for v in highpass(detrend(root_tz), win)],
                    -root_xz_max, root_xz_max)
    if use_real_root_y:
        # 진짜 점프처럼 수직 이동 자체가 핵심인 소스(Jump 등)는 실측 ty를 쓴다.
        root_y_raw = detrend(root_ty)
        base = min(root_y_raw)
        root_y = [(v - base) * INCH2UNIT * root_y_scale for v in root_y_raw]
    elif footlock:
        # ★★발 접지 — 옛 코드는 루트 Y가 고정(또는 인위적 코사인 바운스)인데 다리는
        # 65~90도까지 들어올려서, 발이 지면을 뚫거나 공중에서 미끄러졌다(스케이팅).
        # 매 프레임 두 발의 낙차를 계산해 "더 낮은 쪽 발"이 지면에 닿도록 골반 높이를
        # 역산한다. 무릎을 굽히면 몸이 내려앉고 펴면 올라오는 = 체중이 실린 움직임이 된다.
        # 지지발 = 낙차가 가장 큰(=가장 낮은) 발. 그 발이 지면에 닿으려면 골반이
        # 정확히 그 낙차만큼 높이 있어야 하므로, 기본 다리길이 대비 차이가 곧 오프셋이다.
        # ★부호 주의: 무릎을 굽히면 낙차가 줄고 골반은 *내려와야* 한다(음수).
        drops = [max(foot_drop(r_leg_x[i], prfl_bend[i]), foot_drop(l_leg_x[i], plfl_bend[i]))
                 for i in range(len(times))]
        # 다리 각도엔 이미 hip_ex 과장이 곱해져 있어 낙차를 100% 반영하면 실제보다 깊이
        # 주저앉는다(0.44블록까지 내려가 스쿼트처럼 보였다). 0.6배로 눌러 접지감만 남긴다.
        root_y = clamp([(dr - LEG_REST) * 0.6 for dr in drops], -4.0, 0.5)
        if bounce:
            root_y = [v - bounce * (1 - math.cos(2 * math.pi * t / L)) for v, t in zip(root_y, times)]
    else:
        # footlock을 끈 경우에만 옛 방식(인위적 코사인 바운스)으로 폴백.
        amp = bounce or 1.2
        root_y = [-amp * (1 - math.cos(2 * math.pi * t / L)) for t in times]

    # ★★몸 전체 비틀림은 척추가 아니라 root yaw에 들어 있다 — salsa 소스에서 실측하면
    # lowerback Y는 6도, thorax Y는 4도뿐인데 root yaw는 (방 안을 도는 느린 성분을 뺀 뒤에도)
    # 30도다. 즉 "골반이 좌우로 돌면서 스텝을 밟는" 게 춤의 골격인데 옛 파이프라인은
    # root 회전을 통째로 버려서(캘리브레이션 특이값 우려) 이걸 전부 잃었다.
    # 느린 회전(관객 기준 방향 전환)만 하이패스로 제거하고 빠른 비틀림만 가져온다.
    root_twist_y = clamp([v * twist_ex for v in highpass(detrend(series_raw("root", 4)), win)],
                          -35, 35)

    root_spin_y = None
    if synth_spin:
        # 루트 절대 회전은 캘리브레이션 특이값(짐벌락) 탓에 그대로 못 쓴다.
        # "빙글빙글" 계열은 정직하게 합성 360도 스핀을 얹는다(0->360은 루프에서 이미 이음매 없음).
        root_spin_y = [360.0 * t / L for t in times]

    series_map = {
        "pw_waist_x": waist_x, "pw_waist_y": waist_y, "pw_waist_z": waist_z,
        "pc_chest_x": chest_x, "pc_chest_y": chest_y, "pc_chest_z": chest_z,
        "h_ph_head_x": head_x, "h_ph_head_y": head_y, "h_ph_head_z": head_z,
        "pra_x": r_arm_x, "pra_y": r_arm_y, "pra_z": r_arm_z,
        "pla_x": l_arm_x, "pla_y": l_arm_y, "pla_z": l_arm_z,
        "prfa_x": prfa_curl, "plfa_x": plfa_curl,
        "prl_x": r_leg_x, "prl_y": r_leg_y, "prl_z": r_leg_z,
        "pll_x": l_leg_x, "pll_y": l_leg_y, "pll_z": l_leg_z,
        "prfl_x": prfl_bend, "plfl_x": plfl_bend,
        "root_x": root_x, "root_y": root_y, "root_z": root_z,
        "root_twist_y": root_twist_y,
    }
    for k in series_map:
        series_map[k] = close_loop(series_map[k], loop_frac)
    if root_spin_y is not None:
        series_map["root_spin_y"] = root_spin_y
    return series_map, times, L


def bake_into(d, target_name, series_map, times, L):
    """series_map을 steve.bbmodel의 애니메이션 dict(target_name)에 굽는다."""
    bone_uuid_of = {g["name"]: g["uuid"] for g in d["groups"]}

    def nu():
        return str(uuidlib.uuid4())

    def kf(t, ch, x=0.0, y=0.0, z=0.0, interp="catmullrom"):
        return {"channel": ch, "data_points": [{"x": str(x), "y": str(y), "z": str(z)}],
                "uuid": nu(), "time": round(t, 5), "color": -1, "interpolation": interp}

    animators = {}

    def add_rot(bone, xs=None, ys=None, zs=None):
        kfs = [kf(t, "rotation", xs[i] if xs else 0, ys[i] if ys else 0, zs[i] if zs else 0)
               for i, t in enumerate(times)]
        px, py, pz = ZFIGHT.get(bone, (0, 0, 0))
        kfs.append(kf(0.0, "position", px, py, pz, "linear"))
        kfs.append(kf(L, "position", px, py, pz, "linear"))
        animators[bone_uuid_of[bone]] = {"name": bone, "type": "bone", "rotation_global": False,
                                          "quaternion_interpolation": False, "keyframes": kfs}

    add_rot("pw_waist", xs=series_map["pw_waist_x"], ys=series_map["pw_waist_y"], zs=series_map["pw_waist_z"])
    add_rot("pc_chest", xs=series_map["pc_chest_x"], ys=series_map["pc_chest_y"], zs=series_map["pc_chest_z"])
    add_rot("h_ph_head", xs=series_map["h_ph_head_x"], ys=series_map["h_ph_head_y"], zs=series_map["h_ph_head_z"])
    add_rot("pra_right_arm", xs=series_map["pra_x"], ys=series_map["pra_y"], zs=series_map["pra_z"])
    add_rot("pla_left_arm", xs=series_map["pla_x"], ys=series_map["pla_y"], zs=series_map["pla_z"])
    add_rot("prfa_right_forearm", xs=series_map["prfa_x"])
    add_rot("plfa_left_forearm", xs=series_map["plfa_x"])
    add_rot("prl_right_leg", xs=series_map["prl_x"], ys=series_map["prl_y"], zs=series_map["prl_z"])
    add_rot("pll_left_leg", xs=series_map["pll_x"], ys=series_map["pll_y"], zs=series_map["pll_z"])
    add_rot("prfl_right_foreleg", xs=series_map["prfl_x"])
    add_rot("plfl_left_foreleg", xs=series_map["plfl_x"])

    # 망토는 애니메이터가 없어서 격렬한 척추/다리 동작 중에 몸을 그대로 뚫는다
    # (rig-conventions.md). 이 애니 재생 중에만 scale로 숨긴다 — 다른 애니로 넘어가면
    # cape 애니메이터가 없어 자동으로 원래 크기로 돌아오므로 복구 로직이 필요 없다.
    # ★옛 bake_into는 이걸 안 해서, 손으로 넣어둔 cape 숨김이 재굽기마다 날아갔다.
    if "cape_cape" in bone_uuid_of:
        animators[bone_uuid_of["cape_cape"]] = {
            "name": "cape_cape", "type": "bone", "rotation_global": False,
            "quaternion_interpolation": False,
            "keyframes": [kf(0.0, "scale", 0.001, 0.001, 0.001, "linear"),
                          kf(L, "scale", 0.001, 0.001, 0.001, "linear")]}

    root_kfs = [kf(t, "position", series_map["root_x"][i], series_map["root_y"][i], series_map["root_z"][i], "linear")
                for i, t in enumerate(times)]
    # 빙글빙글류는 합성 360도 스핀, 나머지는 실측에서 뽑은 몸통 비틀림.
    spin = series_map.get("root_spin_y") or series_map.get("root_twist_y")
    if spin is not None:
        root_kfs += [kf(t, "rotation", 0, spin[i], 0) for i, t in enumerate(times)]
    animators[bone_uuid_of["player_root"]] = {"name": "player_root", "type": "bone", "rotation_global": False,
                                               "quaternion_interpolation": False, "keyframes": root_kfs}

    by_name = {a["name"]: a for a in d["animations"]}
    if target_name not in by_name:
        raise SystemExit(f"target 애니 '{target_name}' 이 bbmodel에 없음 — 오타 확인 또는 신규 애니는 "
                          f"d['animations'].append(...)로 직접 추가 필요")
    target = by_name[target_name]
    target["animators"] = animators
    target["length"] = round(L, 5)
    target["loop"] = "loop"


def check_integrity(d):
    """루프 클로징(첫/끝 키프레임 값 일치) + NaN/이상치 검사. 문제 있으면 True."""
    bad = False
    for a in d["animations"]:
        L = float(a["length"])
        for u, banim in a["animators"].items():
            for ch in ("rotation", "position"):
                kfs = sorted([k for k in banim["keyframes"] if k["channel"] == ch], key=lambda k: float(k["time"]))
                for kf_ in kfs:
                    for ax in "xyz":
                        v = float(kf_["data_points"][0][ax])
                        if math.isnan(v) or abs(v) > 400:
                            print("EXTREME", a["name"], banim["name"], ch, kf_["time"], v); bad = True
                if len(kfs) >= 2 and a.get("loop") == "loop":
                    t1 = float(kfs[-1]["time"])
                    if abs(t1 - L) > 1e-4:
                        print("time!=L", a["name"], banim["name"], ch); bad = True
                    elif kfs[0]["data_points"][0] != kfs[-1]["data_points"][0]:
                        # 0<->360 회전 랩어라운드는 정상(같은 각도) — 안내만 하고 실패 처리 안 함
                        print("주의(회전 랩어라운드일 수 있음, 값 다름):", a["name"], banim["name"], ch,
                              kfs[0]["data_points"][0], kfs[-1]["data_points"][0])
    return bad


def cmd_scan(args):
    sk = Skeleton(args.asf)
    frames = parse_amc(args.amc, sk.bones)
    n = int(args.window_sec * args.fps / args.step) * args.step
    start, score = find_best_window(sk, frames, n, stride=args.stride)
    print(f"frames={len(frames)}  best_start={start}  score={score:.1f}  (len={n} step={args.step})")
    print(f"-> --start {start} 로 preview/bake 실행 권장")


def cmd_preview(args):
    sk = Skeleton(args.asf)
    frames = parse_amc(args.amc, sk.bones)
    n = int(args.window_sec * args.fps / args.step) * args.step
    start = args.start
    if start is None:
        start, score = find_best_window(sk, frames, n, stride=args.stride)
        print(f"자동 탐색된 구간: start={start} score={score:.1f}")
    series_map, times, L = retarget_window(
        sk, frames, start, n, args.step, arm_ex=args.arm_ex, spine_ex=args.spine_ex,
        head_ex=args.head_ex, hip_ex=args.hip_ex, use_real_root_y=args.real_root_y,
        root_y_scale=args.root_y_scale, synth_spin=args.synth_spin,
        fps=args.fps, twist_ex=args.twist_ex, root_xz_max=args.root_xz_max,
        footlock=not args.no_footlock, bounce=args.bounce, loop_frac=args.loop_frac,
        leg_spread=args.leg_spread, flip_leg_z=args.flip_leg_z)

    d = json.load(open(args.bbmodel))
    tmp_name = "__mocap_preview__"
    d["animations"] = [a for a in d["animations"] if a["name"] != tmp_name]
    d["animations"].append({"name": tmp_name, "loop": "loop", "override": False, "length": round(L, 5),
                             "snapping": 24, "selected": False, "anim_time_update": "", "blend_weight": "",
                             "start_delay": "", "loop_delay": "", "animators": {}})
    bake_into(d, tmp_name, series_map, times, L)

    import pose_render as pr
    hier = pr.build_hierarchy(d)
    out = pr.render_dual_view(d, hier, tmp_name, args.out, n_frames=args.frames)
    print("렌더 저장:", out, "-- 반드시 눈으로 확인 후 bake 진행할 것")


def cmd_bake(args):
    sk = Skeleton(args.asf)
    frames = parse_amc(args.amc, sk.bones)
    n = int(args.window_sec * args.fps / args.step) * args.step
    start = args.start
    if start is None:
        start, score = find_best_window(sk, frames, n, stride=args.stride)
        print(f"자동 탐색된 구간: start={start} score={score:.1f}")
    series_map, times, L = retarget_window(
        sk, frames, start, n, args.step, arm_ex=args.arm_ex, spine_ex=args.spine_ex,
        head_ex=args.head_ex, hip_ex=args.hip_ex, use_real_root_y=args.real_root_y,
        root_y_scale=args.root_y_scale, synth_spin=args.synth_spin,
        fps=args.fps, twist_ex=args.twist_ex, root_xz_max=args.root_xz_max,
        footlock=not args.no_footlock, bounce=args.bounce, loop_frac=args.loop_frac,
        leg_spread=args.leg_spread, flip_leg_z=args.flip_leg_z)

    d = json.load(open(args.bbmodel))
    bake_into(d, args.target, series_map, times, L)
    bad = check_integrity(d)
    json.dump(d, open(args.bbmodel, "w"), indent=1)
    print(f"'{args.target}' 애니에 구움 완료 (length={L:.2f}s). 정합성:", "문제있음(위 로그 확인)" if bad else "OK")
    print("-> 배포: dev는 파일 직접수정이라 /bm reload만, prod는 scp+/bm reload (재시작 불필요)")


def add_common_args(p):
    p.add_argument("--asf", required=True)
    p.add_argument("--amc", required=True)
    p.add_argument("--bbmodel", default=DEFAULT_BBMODEL)
    p.add_argument("--start", type=int, default=None, help="생략 시 자동 탐색")
    p.add_argument("--window-sec", type=float, default=4.0,
                   help="너무 짧으면(2~3초) 루프가 금방 반복돼 싸구려 느낌이 난다 — "
                        "실제 겪은 피드백. 4초 이상 권장, 소스 클립 길이가 허용하면 더 길게")
    p.add_argument("--step", type=int, default=3, help="프레임 서브샘플 간격(3=60fps->20fps)")
    p.add_argument("--stride", type=int, default=15, help="자동탐색 슬라이딩 보폭")
    p.add_argument("--arm-ex", type=float, default=1.3)
    p.add_argument("--spine-ex", type=float, default=1.6,
                   help="옛 기본값 2.5는 허리 X가 clamp(±30)에 상시 붙어 앞으로 접힌 것처럼 보였다")
    p.add_argument("--head-ex", type=float, default=2.0)
    p.add_argument("--hip-ex", type=float, default=1.5)
    p.add_argument("--real-root-y", action="store_true", help="점프처럼 실측 수직이동을 쓸 소스면 지정")
    p.add_argument("--root-y-scale", type=float, default=0.5)
    p.add_argument("--synth-spin", action="store_true", help="합성 360도 회전을 루트에 얹음(빙글빙글류)")
    p.add_argument("--fps", type=float, default=60.0,
                   help="소스 클립 프레임레이트. CMU 대부분 60이지만 subject 85 등은 120 — "
                        "틀리면 재생속도가 2배로 어긋난다")
    p.add_argument("--twist-ex", type=float, default=2.0,
                   help="몸통 비틀림(Y) 과장 배율. 0으로 주면 옛 동작(비틀림 없음)")
    p.add_argument("--root-xz-max", type=float, default=2.5,
                   help="루트 수평 이동 상한(유닛). 크면 모델이 히트박스에서 떨어져 미끄러진다")
    p.add_argument("--no-footlock", action="store_true",
                   help="발 접지 보정을 끄고 옛 인위적 바운스로 폴백")
    p.add_argument("--bounce", type=float, default=0.0,
                   help="접지 높이 위에 얹을 추가 통통거림 진폭(유닛)")
    p.add_argument("--loop-frac", type=float, default=0.08,
                   help="루프 크로스페이드 비율. 크면 꼬리 동작이 뭉개진다")
    p.add_argument("--leg-spread", type=float, default=1.0, help="다리 벌림(Z) 배율")
    p.add_argument("--flip-leg-z", action="store_true",
                   help="두 다리가 같은 방향으로 쏠려 보이면(부호 반대) 지정")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(required=True)

    p_scan = sub.add_parser("scan", help="가장 동적인 구간 자동 탐색만(파일 안 씀)")
    add_common_args(p_scan)
    p_scan.set_defaults(func=cmd_scan)

    p_prev = sub.add_parser("preview", help="렌더만 생성(파일 안 씀) — bake 전 필수")
    add_common_args(p_prev)
    p_prev.add_argument("--out", default="preview.png")
    p_prev.add_argument("--frames", type=int, default=10)
    p_prev.set_defaults(func=cmd_preview)

    p_bake = sub.add_parser("bake", help="steve.bbmodel의 --target 애니에 실제로 굽기")
    add_common_args(p_bake)
    p_bake.add_argument("--target", required=True, help="교체할 애니 이름(예: dance, dance_arms)")
    p_bake.set_defaults(func=cmd_bake)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
