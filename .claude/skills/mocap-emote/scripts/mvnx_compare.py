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
