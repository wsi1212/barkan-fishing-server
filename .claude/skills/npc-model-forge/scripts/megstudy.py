#!/usr/bin/env python3
"""잘 만든 3D NPC 모델이 <b>기하학적으로</b> 뭘 하고 있는지 계량한다.

스킨 때와 같은 사상: "왜 좋아 보이지?"를 감으로 흉내내면 헛다리를 짚는다(female_face·
세로주름 사고). 실제 파일을 열어 <b>숫자로</b> 재고, 우리 것과 같은 잣대로 비교해
격차가 있는 항목만 처방한다.

무엇을 재나 — 박스 모델링에서 '사람이 만든 티'를 만드는 후보들
  cube_n      본당 큐브 수. 1본 1큐브면 레고, 여러 개면 형태를 깎았다는 뜻
  rot_pct     <b>회전된 큐브 비율</b>. 축 정렬만 쓰면 딱딱하다 — 유기적 형태의 1순위 신호
  rot_vals    실제로 쓰인 회전각 (바닐라 JSON은 ±22.5/±45만 허용)
  size_var    큐브 크기의 다양성(작은 디테일 큐브를 섞는가)
  thin_pct    한 축이 ≤2px인 <b>얇은 판</b> 비율 — 천·머리카락·챙은 판으로 만든다
  overlap     같은 본 안에서 큐브가 겹치는가(부피를 겹쳐 쌓는 기법)
  bone_depth  이름으로 추정한 계층 깊이(hair→hair_mid→hair_end 같은 사슬)
"""
import collections
import glob
import json
import os
import sys


def load_bones(root, name):
    out = {}
    for f in sorted(glob.glob(os.path.join(root, name, '*.json'))):
        try:
            out[os.path.basename(f)[:-5]] = json.load(open(f))
        except Exception:
            pass
    return out


def cube_metrics(el):
    """큐브 하나의 크기·회전·판 여부."""
    a, b = el.get('from', [0, 0, 0]), el.get('to', [0, 0, 0])
    dims = sorted(abs(b[i] - a[i]) for i in range(3))
    rot = el.get('rotation')
    ang = 0.0
    if isinstance(rot, dict):
        ang = abs(float(rot.get('angle', 0) or 0))
    elif isinstance(rot, list):
        ang = max(abs(float(v)) for v in rot) if rot else 0.0
    return dims, ang


def analyse(root, name):
    bones = load_bones(root, name)
    cubes = []
    for bn, d in bones.items():
        for el in d.get('elements', []):
            cubes.append((bn,) + cube_metrics(el))
    if not cubes:
        return None
    n = len(cubes)
    rot = [c for c in cubes if c[2] > 0.01]
    thin = [c for c in cubes if c[1][0] <= 2.0]          # 최소축 ≤2px = 판
    vols = [c[1][0] * c[1][1] * c[1][2] for c in cubes]
    per_bone = collections.Counter(c[0] for c in cubes)
    # 계층 깊이: 이름에 _mid/_end/_2 같은 사슬 표시가 있는 본 수
    chain = sum(1 for b in bones if any(k in b for k in ('_mid', '_end', '2', '3')))
    return dict(
        name=name, bones=len(bones), cubes=n,
        cubes_per_bone=round(n / len(bones), 2),
        rot_pct=round(100 * len(rot) / n, 1),
        rot_vals=sorted({round(c[2], 1) for c in rot})[:6],
        thin_pct=round(100 * len(thin) / n, 1),
        # 크기 다양성: 부피의 변동계수(표준편차/평균). 클수록 큰것+작은것을 섞었다
        size_cv=round((sum((v - sum(vols) / n) ** 2 for v in vols) / n) ** 0.5
                      / max(1e-6, sum(vols) / n), 2),
        max_cubes_in_bone=max(per_bone.values()),
        chain_bones=chain,
    )


def main():
    root, names = sys.argv[1], sys.argv[2].split(',')
    rows = [r for r in (analyse(root, n) for n in names) if r]
    hdr = ('모델', '본', '큐브', '큐브/본', '회전%', '판%', '크기변동', '최대큐브/본', '사슬본')
    print('%-12s %4s %5s %7s %6s %6s %8s %10s %6s' % hdr)
    for r in rows:
        print('%-12s %4d %5d %7.2f %6.1f %6.1f %8.2f %10d %6d' % (
            r['name'], r['bones'], r['cubes'], r['cubes_per_bone'], r['rot_pct'],
            r['thin_pct'], r['size_cv'], r['max_cubes_in_bone'], r['chain_bones']))
    if rows:
        def avg(k):
            return sum(r[k] for r in rows) / len(rows)
        print('%-12s %4.0f %5.0f %7.2f %6.1f %6.1f %8.2f %10.1f %6.1f  ← 평균' % (
            '', avg('bones'), avg('cubes'), avg('cubes_per_bone'), avg('rot_pct'),
            avg('thin_pct'), avg('size_cv'), avg('max_cubes_in_bone'), avg('chain_bones')))
        used = sorted({v for r in rows for v in r['rot_vals']})
        print('\n쓰인 회전각:', used)


if __name__ == '__main__':
    main()
