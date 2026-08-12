#!/usr/bin/env python3
"""원본 모캡 골격 ↔ 리타게팅된 steve 모델을 **같은 카메라로 나란히** GIF로 뽑는다.

★이 도구가 왜 있는가: 결과물만 보면서 파라미터를 만지면 부호 하나(손잡이·축 반전)를
못 찾고 계속 헛돈다. 실제로 강남스타일에서 관절 각도는 원본과 5~10도 내로 맞는데도
자세가 구부정하게 나왔고, 원인은 좌표 변환이 회전이 아니라 거울(행렬식 -1)이었던 것.
원본을 옆에 그려놓고 나서야 30초 만에 잡혔다. **리타게팅 검수는 항상 이걸로 시작할 것.**

    python3 mvnx_compare.py --mvnx "PSY Gangnam Style.mvnx" --anim dance_gangnam \
        --out cmp.gif --seconds 30
"""
import argparse
import json
import math

from PIL import Image, ImageDraw

import model_render as mr
import mvnx_retarget as M
import pose_render as pr

# MVN 23세그먼트 골격 연결(그림용). 손가락·발가락은 생략.
BONES = [("Pelvis", "L5"), ("L5", "L3"), ("L3", "T12"), ("T12", "T8"), ("T8", "Neck"),
         ("Neck", "Head"),
         ("T8", "RightShoulder"), ("RightShoulder", "RightUpperArm"),
         ("RightUpperArm", "RightForeArm"), ("RightForeArm", "RightHand"),
         ("T8", "LeftShoulder"), ("LeftShoulder", "LeftUpperArm"),
         ("LeftUpperArm", "LeftForeArm"), ("LeftForeArm", "LeftHand"),
         ("Pelvis", "RightUpperLeg"), ("RightUpperLeg", "RightLowerLeg"),
         ("RightLowerLeg", "RightFoot"), ("RightFoot", "RightToe"),
         ("Pelvis", "LeftUpperLeg"), ("LeftUpperLeg", "LeftLowerLeg"),
         ("LeftLowerLeg", "LeftFoot"), ("LeftFoot", "LeftToe")]
C_RIGHT, C_LEFT, C_SPINE = (90, 200, 255), (255, 120, 120), (255, 210, 90)
M2U = 30.0 / 1.75      # 사람 키 1.75m -> 모델 30유닛


def facing_rotation(mv, idxs):
    """구간 평균 어깨선으로 정면 정렬 상수 yaw를 만든다(리타게터와 동일 로직)."""
    I = mv.idx
    ys = []
    for f in idxs:
        sh = M.sub(M.to_ours(mv.pos[f][I["LeftShoulder"]]),
                    M.to_ours(mv.pos[f][I["RightShoulder"]]))
        ys.append(math.atan2(sh[2], sh[0]))
    my = math.atan2(sum(math.sin(v) for v in ys), sum(math.cos(v) for v in ys))
    face = my - math.pi
    # 부호는 mvnx_retarget과 동일해야 한다(어깨선을 -X로 보내는 θ = face)
    return math.cos(face), math.sin(face)


def pitch_of(v):
    """뼈 방향의 앞뒤각(+=앞). 우리 좌표는 +Z=뒤라 부호를 뒤집어 잰다."""
    return math.degrees(math.atan2(-v[2], -v[1]))


# (라벨, 원본 부모, 원본 자식, 리그 부모본, 리그 자식본)
JOINTS = [("우허벅지", "RightUpperLeg", "RightLowerLeg", "prl_right_leg", "prfl_right_foreleg"),
          ("좌허벅지", "LeftUpperLeg", "LeftLowerLeg", "pll_left_leg", "plfl_left_foreleg"),
          ("우상완", "RightUpperArm", "RightForeArm", "pra_right_arm", "prfa_right_forearm"),
          ("좌상완", "LeftUpperArm", "LeftForeArm", "pla_left_arm", "plfa_left_forearm"),
          ("몸통", "Pelvis", "Neck", "pw_waist", "h_ph_head")]


def unwrap(seq):
    """±180 경계를 넘나들며 튀는 각도열을 연속으로 편다.
    ★안 하면 팔을 수평 위로 들 때마다 +179/-179를 오가서 진폭이 360도로 부풀려지고,
    멀쩡한 값이 '확인' 플래그를 받는다(실제로 겪음)."""
    out = [seq[0]]
    for v in seq[1:]:
        d = v - out[-1]
        while d > 180:
            d -= 360
        while d < -180:
            d += 360
        out.append(out[-1] + d)
    return out


def report(mv, P, idxs, hier, anim, L):
    """관절별로 원본과 대조. ★지표는 3D 벡터 사이각 — 평면 투영각은 팔이 옆으로 뻗는
    순간 요동쳐서(원본 141도인데 666도로 측정) 멀쩡한 결과에 오진 플래그를 단다."""
    print(f"{'관절':10s} {'방향오차 평균':>13s} {'최대':>7s} {'30도초과':>9s} {'원본 움직임':>11s} {'내 움직임':>10s}")
    for label, sp, sc, rp, rc in JOINTS:
        errs, sdir, mdir = [], [], []
        prev_s = prev_m = None
        s_move = m_move = 0.0
        for ti in range(len(idxs)):
            t = ti * (idxs[1] - idxs[0]) / mv.fps
            if t > L:
                break
            f = idxs[ti]
            sv = M.norm(M.sub(P(f, sc), P(f, sp)))
            w = pr.pose_world(hier, anim, t, loop_length=L)
            mvv = M.norm([w[rc][0][i] - w[rp][0][i] for i in range(3)])
            dot = max(-1.0, min(1.0, sum(sv[i] * mvv[i] for i in range(3))))
            errs.append(math.degrees(math.acos(dot)))
            if prev_s is not None:
                s_move += math.degrees(math.acos(max(-1.0, min(1.0,
                    sum(sv[i] * prev_s[i] for i in range(3))))))
                m_move += math.degrees(math.acos(max(-1.0, min(1.0,
                    sum(mvv[i] * prev_m[i] for i in range(3))))))
            prev_s, prev_m = sv, mvv
        n = len(errs)
        over = sum(1 for e in errs if e > 30)
        ratio = m_move / s_move if s_move else 0
        flag = "  <== 확인" if sum(errs) / n > 25 or over > n * 0.3 or not (0.5 < ratio < 1.8) else ""
        print(f"{label:10s} {sum(errs)/n:12.0f}도 {max(errs):6.0f}도 {100*over/n:8.0f}% "
              f"{s_move:10.0f}도 {m_move:9.0f}도{flag}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mvnx", required=True)
    ap.add_argument("--bbmodel", default=mr.DEFAULT_BBMODEL)
    ap.add_argument("--anim", required=True, help="비교할 애니 이름(리타게팅 결과)")
    ap.add_argument("--out", default="compare.gif")
    ap.add_argument("--seconds", type=float, default=30.0)
    ap.add_argument("--fps", type=int, default=12)
    ap.add_argument("--step", type=int, default=12, help="MVNX 프레임 서브샘플(240fps -> 12=20fps)")
    ap.add_argument("--scale", type=float, default=8.0)
    ap.add_argument("--report", action="store_true",
                    help="관절별로 원본 대비 진폭·일치율을 표로 출력(GIF는 안 만듦). "
                         "★눈으로 보고 넘기지 말고 이걸 먼저 볼 것 — 허벅지가 안 나오는 것 같은 "
                         "결함은 그림보다 숫자로 훨씬 빨리 잡힌다")
    args = ap.parse_args()

    mv = M.Mvnx(args.mvnx)
    I = mv.idx
    total = int(args.seconds * mv.fps)
    idxs = list(range(0, min(total, len(mv.pos)), args.step))
    ca, sa = facing_rotation(mv, idxs)

    def P(f, seg):
        x, y, z = M.to_ours(mv.pos[f][I[seg]])
        return (x * ca + z * sa, y, -x * sa + z * ca)

    d = json.load(open(args.bbmodel))
    hier, cubes = pr.build_hierarchy(d), mr.build_cube_map(d)
    anim = pr.build_anim_index(d)[args.anim]
    L = float(anim["length"])

    if args.report:
        report(mv, P, idxs, hier, anim, L)
        return

    cam = pr.mat_mul(pr.rot_x(10.0), pr.rot_y(32.0))   # model_render와 동일 카메라
    W, H = 340, 430
    font = mr._font(15)
    n_frames = int(args.seconds * args.fps)
    frames = []
    for i in range(n_frames):
        t = args.seconds * i / n_frames
        fi = min(len(idxs) - 1, int(t * mv.fps / args.step))
        f = idxs[fi]
        img = Image.new("RGB", (W * 2, H), (30, 31, 36))
        dr = ImageDraw.Draw(img)
        ground = H - 55

        # 왼쪽: 원본 골격 (가장 낮은 발을 지면에 붙여 세로 위치를 모델과 맞춘다)
        cx = W * 0.5
        foot = min(P(f, "RightToe")[1], P(f, "LeftToe")[1])
        dr.line([(cx - 95, ground), (cx + 95, ground)], fill=(52, 54, 62), width=2)
        for a, b in BONES:
            col = C_RIGHT if "Right" in a + b else (C_LEFT if "Left" in a + b else C_SPINE)
            pts = []
            for seg in (a, b):
                p = P(f, seg)
                q = pr.mat_vec(cam, [p[0] * M2U, (p[1] - foot) * M2U, p[2] * M2U])
                pts.append((cx + q[0] * args.scale, ground - q[1] * args.scale))
            dr.line(pts, fill=col, width=5)
        dr.text((cx - 55, 12), "원본 모캡", fill=(235, 235, 235), font=font)

        # 오른쪽: 리타게팅 결과
        cx2 = W * 1.5
        dr.line([(cx2 - 95, ground), (cx2 + 95, ground)], fill=(52, 54, 62), width=2)
        mr.draw_frame(dr, mr.collect_polys(d, hier, cubes, anim, t % L), cx2, ground, args.scale)
        dr.text((cx2 - 60, 12), f"{args.anim}", fill=(235, 235, 235), font=font)
        dr.text((W - 26, H - 24), f"{t:4.1f}s", fill=(150, 150, 150), font=font)
        frames.append(img)

    frames[0].save(args.out, save_all=True, append_images=frames[1:],
                    duration=int(1000 / args.fps), loop=0, optimize=True)
    print("GIF 저장:", args.out, f"({n_frames}프레임, {args.seconds:.0f}초)")


if __name__ == "__main__":
    main()
