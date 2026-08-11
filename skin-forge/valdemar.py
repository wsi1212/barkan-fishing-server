#!/usr/bin/env python3
"""영주 발데마르 — 영주성 대전, citizensId 171.

CHARACTER BRIEF
  왕실보다 오래 강을 지켜 온 토착 영주. 중앙을 신뢰하지 않는 냉담한 50대 후반의 지방 권력자.
  영주성은 유럽풍 석재·짙은참나무 성이므로 사막/왕실 갑옷이 아닌 무거운 모직 코트가 맞다.

DESIGN SPEC
  나이/체격  50대 후반, 넓은 어깨의 노련한 영주
  실루엣     남청 모직 롱코트 + 짙은 포도주색 강변 새시 + 무릎까지 내려오는 자락
  팔레트     코트=강물 같은 남청 / 속옷=회갈 리넨 / 바지=짙은 숯색 / 장화=젖은 가죽
             악센트=낡은 은(새시 버클·한쪽 소매 단추, 두 곳만)
  비대칭     오른쪽 허벅지에 지도 주머니, 왼쪽 소매만 은 단추
  정체 모티프 가슴 로고 없이 코트 재단·지도 주머니로 '강을 읽는 지방 영주'를 표현
  얼굴       바랜 은회색 머리·짧은 각진 수염·눈가 주름·회청색 안쪽 응시, 코 생략
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / '.codex/skills/npc-skin-style-mirror/scripts'))
import garments as g
from skinlib import Skin, ramp, ramp_lit

OUT = pathlib.Path(__file__).parent / 'out'
P = dict(skin=ramp('ad7b59'), hair=ramp('777166'), coat=ramp_lit('35475b'),
         linen=ramp_lit('716b61'), pants=ramp_lit('3c3d42'), boot=ramp_lit('45382d'),
         sash=ramp_lit('6f3840'), silver=ramp_lit('9aa4aa'), iris=ramp('526b78'))

def build():
    s = Skin(); seed = 171
    g.head_base(s, P['skin'], seed=seed); g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=7, seed=seed, part_x=5)
    g.beard(s, P['hair'], style='mutton', y=6, seed=seed, ragged=False)
    g.face_shape(s, P['skin'], jaw='square'); g.wrinkles(s, P['skin'], crow=True, forehead=True)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, iris_idx=1); g.brow(s, P['hair'][1], y=3, weight=2)
    g.mouth(s, P['skin'], y=6, w=2, color=P['hair'][2])
    g.tunic(s, P['linen'], collar=True, seed=seed, grain=.07)
    g.sleeves(s, P['linen'], y0=0, y1=9, seed=seed, grain=.07); g.hands(s, P['skin'], rows=2)
    g.pants(s, P['pants'], y0=0, y1=7, seed=seed); g.boots(s, P['boot'], rows=4, toe=True, cuff=True)
    g.coat(s, P['coat'], y0=0, hem=11, tails=4, seed=seed, lapel=True)
    g.sash(s, P['sash'], y=7, drop=2, layer='outer'); s.buckle('body', 7, P['silver'], layer='outer')
    g.pouch(s, P['boot'], part='leg_r', face='front', x=1, y=2, w=2, h=3, metal=P['silver'])
    s.f('arm_l', 'front', 'outer').px(2, 5, P['silver'][3])
    OUT.mkdir(exist_ok=True); return s.save(str(OUT / 'valdemar.png'))
if __name__ == '__main__': print(build())
