#!/usr/bin/env python3
"""힐데 — &b[회복] 힐데, 왕도 궁정 치료사, citizensId 122.

CHARACTER BRIEF
  대사   "궁정 치료사입니다. 다치신 곳 없나요?" / "회복이 필요하면 말씀하세요."
  구스킨 ★검은 정장 + 흰 셔츠 + 빨간 넥타이 = 현대 회사원. 중세 궁정 치료사와 정반대.

DESIGN SPEC
  나이/체격  30대 여성, 단정함
  실루엣     ★흰 두건(코이프) + 회청 로브 + 흰 앞치마 + 발목까지 오는 치마 + 약초 가방
             (베아트리체=마을 아낙의 머릿수건+보디스와 달리, 이쪽은 '단정한 궁정 복식')
  팔레트     로브=연한 회청 / 두건·앞치마=바랜 흰 / 가방=갈색 가죽 / ★악센트=약초의 세이지
             ★붉은 십자는 절대 금지 — 현대 적십자 기호다. 중세 치료사는 약초와 천으로 읽힌다
  비대칭     약초 가방이 한쪽 어깨 + 왼쪽 허리에 붕대 두루마리 + 앞치마 끈 매듭은 뒤
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · ★수염 없음(여성) · 속눈썹 1px + 입술 톤
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))
import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 122
P = dict(skin=ramp('d3a884'), hair=ramp('5f4636'), robe=ramp_lit('8794a3'),
         linen=ramp_lit('bfb9a8'), bag=ramp_lit('6b5440'), sage=ramp_lit('6f8a5c'),
         lip=ramp('9b5a52'), iris=ramp('4a5a6b'))


def build():
    s = Skin()
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=6, seed=SEED)
    g.face_shape(s, P['skin'], jaw='narrow')
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['grey']), y=4, gaze=0, iris_idx=1, socket=P['skin'][1])
    g.brow(s, P['hair'][1], y=3)
    f = s.f('head', 'front')
    f.px(0, 4, P['skin'][1]); f.px(7, 4, P['skin'][1])           # 속눈썹
    f.rect(3, 6, 4, 6, P['lip'][2])                               # 입술
    g.headscarf(s, P['linen'], rows=2, tail=False, seed=SEED)     # ★흰 코이프

    g.tunic(s, P['robe'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07, hem=False)
    g.sleeves(s, P['robe'], y0=0, y1=9, seed=SEED, grain=0.07)
    g.hands(s, P['skin'], rows=2)
    for part in ('leg_r', 'leg_l'):                               # ★긴 치마
        s.form_fill(part, P['robe'], 0, 11, base_idx=3, top=True, bottom=True)
        s.form_fill(part, P['robe'], 0, 10, layer='outer', base_idx=3)
        s.hem(part, 10, P['robe'], layer='outer', base_idx=3)
        s.folds(part, 1, 9, P['robe'], layer='outer', cols=(1,), seed=SEED)
    s.form_fill('body', P['robe'], 8, 11, layer='outer', base_idx=3)

    g.apron(s, P['linen'], bib=(2, 5), bib_y=(2, 6), waist=7, hem=11,
            wrap=1, straps=True, tie=True, seed=SEED)             # 흰 앞치마
    g.bandolier(s, P['bag'], front_x=1, layer='outer')            # 약초 가방 끈
    fr = s.f('body', 'front', 'outer')
    fr.rect(6, 6, 7, 9, P['bag'][3])                              # 가방
    fr.row(6, P['bag'][4], 6, 7); fr.row(9, P['bag'][1], 6, 7)
    fr.px(6, 7, P['sage'][3]); fr.px(7, 7, P['sage'][2])          # ★삐져나온 약초
    s.f('body', 'left', 'outer').rect(0, 8, 1, 10, P['linen'][4]) # 붕대 두루마리
    s.f('body', 'left', 'outer').row(10, P['linen'][1], 0, 1)
    # ★긴 머리 — 반드시 <b>옷·머리쓰개를 다 그린 뒤</b>, 그리고 outer 레이어에.
    #   NPC는 lookclose로 늘 플레이어를 마주보므로 뒷머리는 볼 일이 없다 → 얼굴 옆과
    #   가슴 앞으로 내려와야 '길다'가 읽힌다. 머리쓰개는 함수가 알아서 비켜간다.
    g.female_hair_length(s, P['hair'], seed=SEED)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'hilde.png'))


if __name__ == '__main__':
    print(build())
