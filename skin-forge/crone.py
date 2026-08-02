#!/usr/bin/env python3
"""노파 — &a[Q] 노파, 사막마을, citizensId 77.

CHARACTER BRIEF  (npc_brief.py 노파 --village)
  대사   "모래바람이 부는 날엔 이상한 것이 낚인다우." / "늙은이 말 한번 들어보겠수?"
         "가시배가 좀 모였나? 가시가 있으니 조심하렴." / "고맙구나, 몸이 한결 나아질 것 같아."
  퀘스트 모래바람의 물고기(모래폭풍어) · 땡볕의 신기루(신기루어) · 제단의 분노(전기메기)
         → 날씨와 기이한 것을 읽는 사막 노파. 가시배를 모아 몸을 다스리는 민간 치료사.
  지역   사막마을 → 아라비안 테마가 맞는 자리.
  ★겹침 같은 사막에 이미: 유세프(모래색 토브+무늬없는 두건+청록 새시),
         현자(흰 토브+빨간 체크 케피예), 자말(길드)
  구스킨 ★불투명 384px = 머리만. 몸이 통째로 투명.

DESIGN SPEC
  나이/체격  80대 여성, 등이 굽고 작다
  실루엣     ★머리부터 어깨·가슴까지 덮는 긴 숄(멜라야) + 헐렁한 로브 + 굽은 자세
             (남자 둘은 두건+토브 = 어깨가 드러남. 숄로 어깨선을 덮어 실루엣을 가른다)
  팔레트     ★인디고 숄 — 사막 유목민 여성의 남색 염료. 마을의 모래색/흰색과 정면으로 갈림
             / 로브=짙은 흙갈 / ★악센트=가시배 열매의 붉은색(목의 부적) 한 곳
  비대칭     숄 자락이 한쪽 어깨로만 넘어감 + 왼쪽 허리에 약초 주머니
  정체 모티프 없음. 정체성은 인디고 숄 + 붉은 부적
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · ★수염 없음(여성) · 속눈썹 1px + 입술 톤으로
             성별을 읽히게 · 이마·눈가 주름을 마을에서 제일 깊게
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 77

P = dict(
    skin=ramp('a87b52'),                  # 사막 볕에 마른 노인 피부
    hair=ramp('a9a49a'),                  # 흰머리 (숄 아래 조금)
    shawl=ramp_lit('35406b'),                 # ★인디고 숄
    robe=ramp_lit('6b5a45'),                  # 짙은 흙갈 로브
    berry=ramp_lit('8f3a33'),                 # ★가시배 열매의 붉은색 — 유일한 악센트
    iris=ramp('4a3a2c'),
)


def build():
    s = Skin()

    # ---- head (숄 3행: 0-2 숄 / 3 눈썹 / 4 눈 / 5 볼 / 6 입 / 7 턱)
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=1, back=5, seed=SEED)
    g.wrinkles(s, P['skin'], brow_y=3, crow=True)            # 마을에서 제일 깊은 주름
    g.face_shape(s, P['skin'], jaw='long')
    g.face_marks(s, P['skin'], kind='sunken', seed=SEED)
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['grey']), y=4, gaze=0, iris_idx=1)
    g.brow(s, P['hair'][1], y=3)
    f = s.f('head', 'front')
    f.px(0, 4, P['skin'][1]); f.px(7, 4, P['skin'][1])       # 속눈썹/눈꼬리 1px
    f.rect(3, 6, 4, 6, P['berry'][1])                        # 입술 톤 = 여성으로 읽히는 최소 단서
    f.px(2, 5, P['skin'][1]); f.px(5, 5, P['skin'][1])       # 팔자주름
    g.headscarf(s, P['shawl'], rows=3, tail=True, seed=SEED)

    # ---- 몸: 헐렁한 로브 + 어깨를 덮는 숄
    for part in ('arm_r', 'arm_l'):
        s.form_fill(part, P['skin'], 0, 11, base_idx=3, top=True, bottom=True)
    g.tunic(s, P['robe'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07, hem=False)
    g.robe(s, P['robe'], y0=0, seed=SEED, hem_row=11, sleeve_to=9)

    # 숄: 머리에서 내려와 어깨·가슴 윗부분을 덮는다 (남자들의 토브와 갈리는 지점)
    sh = P['shawl']
    s.form_fill('body', sh, 0, 3, layer='outer', base_idx=3, top=True)
    s.f('body', 'front', 'outer').rect(2, 5, 5, 6, sh[2])    # 가슴 앞 자락
    s.f('body', 'front', 'outer').row(6, sh[1], 2, 5)
    s.f('body', 'left', 'outer').rect(0, 5, 3, 8, sh[2])     # ★한쪽 어깨로만 넘긴 자락
    s.f('body', 'left', 'outer').row(8, sh[1])
    s.speckle('body', sh, 0, 6, layer='outer', density=0.09, seed=SEED)
    # 숄이 어깨를 덮되 ★한쪽만 팔뚝까지 흘러내린다(좌우 동일 = 감사 경고 대상)
    s.form_fill('arm_r', sh, 0, 2, layer='outer', base_idx=3)
    s.hem('arm_r', 2, sh, layer='outer', base_idx=3)
    s.form_fill('arm_l', sh, 0, 6, layer='outer', base_idx=3)
    s.hem('arm_l', 6, sh, layer='outer', base_idx=3)
    s.folds('arm_l', 1, 5, sh, layer='outer', cols=(1,), seed=SEED)

    # 목의 붉은 부적 (유일한 악센트)
    fr = s.f('body', 'front', 'outer')
    fr.px(3, 4, P['berry'][3]); fr.px(4, 4, P['berry'][1])

    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['robe'], y0=0, y1=11, seed=SEED)
    for i, part in enumerate(('leg_r', 'leg_l')):            # 로브 자락 세로 주름
        s.folds(part, 1, 10, P['robe'], layer='outer', cols=(1 + i,), seed=SEED + i)
    s.folds('body', 7, 10, P['robe'], cols=(2, 5), seed=SEED)
    g.boots(s, P['robe'], rows=2, toe=True, cuff=False)
    g.pouch(s, P['robe'], part='leg_l', face='front', x=1, y=2, w=2, h=3,
            metal=P['berry'])

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'crone.png'))


if __name__ == '__main__':
    print(build())
