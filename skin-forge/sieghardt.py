#!/usr/bin/env python3
"""지크하르트 — &b[대장간] 지크하르트, 왕도 왕실 대장간, citizensId 117.

CHARACTER BRIEF
  대사   "왕실 대장간이오. 최고의 장비만 만들지." / "필요한 게 있으면 말해보시오."
  기능   smithy(강화·수리 GUI)
  구스킨 ★금발 + 현대 갈색 재킷 + 파란 청바지. 중세 대장장이가 청바지를 입는다.

DESIGN SPEC
  나이/체격  50대, 화덕 앞에서 늙은 사람. 팔뚝이 두꺼워야 한다
  실루엣     ★두꺼운 가죽 앞치마(무릎까지) + 소매를 걷어붙인 리넨 셔츠 + 가죽 팔토시
             + 짧게 민 머리 + 짙은 수염. 모자 없음(화덕 앞에서 모자는 안 쓴다)
  팔레트     앞치마=검댕 가죽(짙게) / 셔츠=오트밀 리넨 / 팔토시=중간 가죽
             / ★악센트=달군 쇠의 주황 1곳(앞치마 가슴의 불똥 자국)+놋쇠 버클 1곳
             오토(항구 어물전)의 소금 절은 밝은 가죽 앞치마와 명도로 갈린다
  비대칭     왼팔만 팔토시 + 오른쪽 앞치마 아래 기운 자국 + 오른팔 화상 흉터
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 그을음 얼룩 · 눈가 주름
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, mix, ramp, ramp_lit       # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 117

P = dict(
    skin=ramp('b07a52'),
    hair=ramp('3a2f28'),
    beard=ramp('4a3d33'),
    shirt=ramp_lit('a89880'),
    # 어두운 가죽에 기본 spread를 쓰면 [4](허리끈·옷단)가 밝은 황갈로 튀어
    # 앞치마 한가운데를 크림색 띠가 가로지른다
    apron=ramp_lit('45362a', spread=0.40),
    bracer=ramp_lit('6b4f36'),
    pants=ramp_lit('4f4a42'),
    boot=ramp_lit('352c24'),
    ember=ramp_lit('c4703a'),
    brass=ramp_lit('b08d3c'),
    soot=ramp_lit('3c3630'),
    iris=ramp('4a3a2c'),
)


def build():
    s = Skin()

    # ---- 머리 (0-1 짧게 민 머리 / 2 이마 / 3 눈썹 / 4 눈 / 5 볼 / 6-7 수염)
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=1, back=5, seed=SEED)    # 화덕 앞이라 짧게 민다
    g.beard(s, P['beard'], style='full', y=5, seed=SEED)
    g.wrinkles(s, P['skin'], crow=True, forehead=True)
    g.face_shape(s, P['skin'], jaw='square')
    g.face_marks(s, P['skin'], kind='scar', seed=SEED)
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['dark']), y=4, gaze=0, iris_idx=2)
    g.brow(s, P['hair'][1], y=3)
    g.mouth(s, P['skin'], y=6, w=2)
    fh = s.f('head', 'front')                            # 그을음 — 대장장이의 서명
    for x, y in ((1, 5), (6, 2), (5, 5)):
        fh.px(x, y, mix(fh.get(x, y), P['soot'][2], 0.5))

    # ---- base: 리넨 셔츠(소매는 팔꿈치까지) → 캔버스 바지 → 장화
    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07, hem=False)
    g.sleeves(s, P['shirt'], y0=0, y1=6, seed=SEED, grain=0.07)
    for part in ('arm_r', 'arm_l'):                      # 걷어붙인 아래는 맨팔
        s.form_fill(part, P['skin'], 7, 11, base_idx=3)
        s.hem(part, 6, P['shirt'], base_idx=3)
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['pants'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['boot'], rows=4, toe=True, cuff=True)

    # ---- 가죽 앞치마: 무릎까지 내려오는 두꺼운 한 장. 대장장이의 실루엣 전부
    g.apron(s, P['apron'], bib=(1, 6), bib_y=(1, 6), waist=7, hem=11,
            wrap=2, straps=True, tie=True, seed=SEED)
    for part in ('leg_r', 'leg_l'):                      # 앞치마 자락이 무릎을 덮는다
        s.form_fill(part, P['apron'], 0, 4, layer='outer', base_idx=3,
                    faces=('front', 'right', 'left'))
        s.hem(part, 4, P['apron'], layer='outer', base_idx=3)
    g.patch(s, 'leg_r', 'front', P['bracer'], x=1, y=2, w=2, h=2, layer='outer')

    # 왼팔만 가죽 팔토시(비대칭) + 오른팔 화상 흉터
    s.form_fill('arm_l', P['bracer'], 7, 9, layer='outer', base_idx=3)
    s.hem('arm_l', 9, P['bracer'], layer='outer', base_idx=3)
    s.f('arm_l', 'front', 'outer').px(1, 8, P['brass'][4])
    ar = s.f('arm_r', 'front')
    for y in (8, 9, 10):
        ar.px(2, y, mix(ar.get(2, y), P['ember'][1], 0.35))

    # ★악센트는 두 곳: 앞치마 가슴에 튄 불똥 자국 + 팔토시 놋쇠 리벳
    fb = s.f('body', 'front', 'outer')
    for x, y in ((2, 3), (3, 5), (5, 2)):
        fb.px(x, y, P['ember'][int(2 + (x + y) % 2)])

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'sieghardt.png'))


if __name__ == '__main__':
    print(build())
