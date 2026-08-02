#!/usr/bin/env python3
"""종지기 — &a[Q] 종지기, 왕도 북서 종탑, citizensId 48.

CHARACTER BRIEF
  대사   "북서 종탑의 종지기올시다. 매일 이 종을 울리지요."
         ★"헌데 밤마다… 누가 이 종탑에서 바다 너머로 불빛 신호를 보낸다오. 오싹한 일이야."
         → 높은 종탑에서 혼자 일하는 늙은이. 뭔가를 목격했고 겁먹어 있다.
  구스킨 ★보라+금 로브에 분홍빛 얼굴 = '돼지 마법사'로 보임(유저 지적). 종지기와 무관.

DESIGN SPEC
  나이/체격  60대, 종줄을 당겨 어깨가 굽음
  실루엣     ★귀덮개 달린 방한모 + 두꺼운 목도리 + 낡은 튜닉 + 장갑
             (종탑은 높고 바람이 세다 — 왕도에서 유일하게 '추워 보이는' 사람)
             + 어깨에 감은 종줄(마 밧줄)
  팔레트     튜닉=탁한 회갈 / 목도리=진회 / 밧줄=마. 왕도의 진홍·파랑·강철과 겹치지 않게
             채도를 최대한 낮춘다(그는 궁정 사람이 아니라 탑에 사는 일꾼)
             ★악센트 없음 — 가난한 종지기에게 금은 없다
  비대칭     종줄이 한쪽 어깨 + 오른손만 장갑(줄 당기는 손) + 왼무릎 패치
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 흰 콧수염 · 이마·눈가 주름
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))
import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 48
P = dict(skin=ramp('bd9068'), hair=ramp('a9a49a'), tunic=ramp_lit('7a6f61'),
         # 목도리는 튜닉(회갈)과 값·색상 둘 다 벌려야 보인다
         scarf=ramp_lit('3a4a52'), rope=ramp_lit('9b8355'), glove=ramp_lit('5c4a38'),
         cap=ramp_lit('5f5348'), iris=ramp('4a4a3f'))


def build():
    s = Skin()
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=1, back=6, seed=SEED)
    s.f('head', 'front').rect(2, 6, 5, 6, P['hair'][2])          # 흰 콧수염
    g.wrinkles(s, P['skin'], brow_y=3, crow=True, forehead=False)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, brow=P['hair'][1], brow_y=3)
    g.mouth(s, P['skin'], y=7, w=2)
    g.cap(s, P['cap'], crown=3, brim=False, seed=SEED)           # 방한모
    for side in ('right', 'left'):                                # ★귀덮개
        s.f('head', side, 'outer').rect(2, 3, 5, 5, P['cap'][2])
        s.f('head', side, 'outer').row(5, P['cap'][1], 2, 5)

    g.tunic(s, P['tunic'], y0=0, y1=11, collar=True, seed=SEED, grain=0.08)
    g.sleeves(s, P['tunic'], y0=0, y1=9, seed=SEED, grain=0.08)
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['glove'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['glove'], rows=4, toe=True, cuff=True)

    s.band('body', 0, 2, P['scarf'][3], layer='outer')            # ★두꺼운 목도리
    s.shade_ring('body', 3, layer='outer', amount=0.30)
    s.f('body', 'front', 'outer').rect(3, 3, 4, 5, P['scarf'][2])  # 늘어진 끝
    s.f('body', 'front', 'outer').px(4, 5, P['scarf'][1])
    g.bandolier(s, P['rope'], front_x=2, layer='outer')           # 종줄
    g.belt(s, P['glove'], y=8, accent=P['glove'], layer='outer')
    s.form_fill('arm_r', P['glove'], 8, 11, layer='outer', base_idx=3)   # ★오른손만 장갑
    s.band('arm_r', 8, 8, P['glove'][4], layer='outer')
    g.patch(s, 'leg_l', 'front', P['glove'], x=1, y=4, w=2, h=2)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'bellringer.png'))


if __name__ == '__main__':
    print(build())
