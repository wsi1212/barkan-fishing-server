#!/usr/bin/env python3
"""사관 게르하르트 — 영주성 서고, citizensId 173.

CHARACTER BRIEF
  영주성의 오래된 사본을 지키는 건조한 기록자. 왕도 대도서관 사제와 다르게 지방 서고의
  실무자이므로 낡은 잉크색 로브와 기록 주머니가 읽혀야 한다.

DESIGN SPEC
  나이/체격  40대 중반, 마른 체격
  실루엣     먼지 낀 잉크색 로브 + 회갈 리넨 안감 + 길게 내려온 소매와 양피지 주머니
  팔레트     로브=먹청 / 안감=회갈 / 바지=짙은 갈색 / 장화=낡은 가죽 / 악센트=황동 2곳
  비대칭     오른 허벅지 양피지 주머니와 왼 소매의 잉크 얼룩
  정체 모티프 가슴 로고 없음 — 사제 아닌 기록관은 로브 흐름·주머니로만 표현
  얼굴       짙은 갈색 단발·좁은 염소수염·피곤한 청회색 눈·얕은 주름, 코 생략
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / '.codex/skills/npc-skin-style-mirror/scripts'))
import garments as g
from skinlib import Skin, ramp, ramp_lit

OUT = pathlib.Path(__file__).parent / 'out'
P = dict(skin=ramp('b28765'), hair=ramp('4a4034'), robe=ramp_lit('3d4d63'),
         lining=ramp_lit('766e61'), pants=ramp_lit('403a35'), boot=ramp_lit('382f28'),
         brass=ramp_lit('a4803d'), iris=ramp('587080'))
def build():
    s = Skin(); seed = 173
    g.head_base(s, P['skin'], seed=seed); g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=7, seed=seed, part_x=2); g.beard(s, P['hair'], style='goatee', y=6, seed=seed, ragged=False)
    g.face_shape(s, P['skin'], jaw='narrow'); g.wrinkles(s, P['skin'], crow=True, forehead=True)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, iris_idx=1); g.brow(s, P['hair'][1], y=3)
    g.mouth(s, P['skin'], y=6, w=2, color=P['hair'][2])
    g.tunic(s, P['lining'], collar=True, seed=seed, grain=.07)
    g.sleeves(s, P['lining'], y0=0, y1=9, seed=seed, grain=.07); g.hands(s, P['skin'], rows=2)
    g.pants(s, P['pants'], y0=0, y1=7, seed=seed); g.boots(s, P['boot'], rows=4, toe=True, cuff=True)
    g.robe(s, P['robe'], y0=0, seed=seed, hem_row=11, sleeve_to=10, lining=P['lining'])
    g.belt(s, P['boot'], y=7, accent=P['brass'], layer='outer'); g.pouch(s, P['lining'], part='leg_r', face='front', x=1, y=2, w=2, h=3, metal=P['brass'])
    s.f('arm_l', 'front', 'outer').px(1, 7, P['robe'][1]); s.f('arm_l', 'front', 'outer').px(2, 8, P['robe'][1])
    OUT.mkdir(exist_ok=True); return s.save(str(OUT / 'gerhardt.png'))
if __name__ == '__main__': print(build())
