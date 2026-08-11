#!/usr/bin/env python3
"""잠수장 하르트무트 — 은빛 갈매기호 갑판 아래, citizensId 175.

CHARACTER BRIEF
  수압과 잠수 장비를 책임지는 중년 잠수장. 갑판 선원들의 가벼운 제복과 달리
  무거운 방수 코트, 목 보호대, 공구 주머니가 먼저 읽혀야 한다.

DESIGN SPEC
  나이/체격  50대 초반, 넓고 단단한 체격
  실루엣     검은 해저 방수 코트 + 녹청 목 보호대 + 무거운 장화 + 양쪽 공구 주머니
  팔레트     코트=검푸른 기름천, 속옷=탁한 청록, 바지=숯 회색, 장화=젖은 가죽,
             악센트=황동 버클과 한쪽 압력계(두 곳)
  비대칭     왼쪽 가슴 압력계, 오른쪽 허벅지 렌치 주머니
  정체 모티프  작은 황동 압력계만 사용 — 로고나 왕실 문장은 없음
  얼굴       회갈색 짧은 머리, 넓은 사각 턱, 짧은 수염과 눈가 주름, 코 생략
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / '.codex/skills/npc-skin-style-mirror/scripts'))
import garments as g
from skinlib import Skin, ramp, ramp_lit

OUT = pathlib.Path(__file__).parent / 'out'
P = dict(skin=ramp('a87559'), hair=ramp('51453d'), coat=ramp_lit('293b46'),
         lining=ramp_lit('456d6b'), pants=ramp_lit('3d4142'), boot=ramp_lit('332d2a'),
         brass=ramp_lit('ae843e'), gauge=ramp_lit('7ea59b'), iris=ramp('5a7278'))

def build():
    s = Skin(); seed = 175
    g.head_base(s, P['skin'], seed=seed); g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=6, seed=seed, part_x=5)
    g.beard(s, P['hair'], style='short', y=6, seed=seed, ragged=False)
    g.face_shape(s, P['skin'], jaw='square'); g.wrinkles(s, P['skin'], crow=True, forehead=True)
    g.eyes(s, 'c8c2b5', P['iris'], y=4, gaze=0, iris_idx=1); g.brow(s, P['hair'][1], y=3, weight=2)
    g.mouth(s, P['skin'], y=6, w=2, color=P['hair'][2])
    g.tunic(s, P['lining'], collar=True, seed=seed, grain=.08)
    g.sleeves(s, P['lining'], y0=0, y1=9, seed=seed, grain=.08); g.hands(s, P['skin'], rows=2)
    g.pants(s, P['pants'], y0=0, y1=7, seed=seed); g.boots(s, P['boot'], rows=4, toe=True, cuff=True)
    g.coat(s, P['coat'], y0=0, hem=11, tails=3, seed=seed, lapel=True)
    g.belt(s, P['boot'], y=7, accent=P['brass'], layer='outer')
    g.pouch(s, P['coat'], part='leg_r', face='front', x=1, y=2, w=2, h=3, metal=P['brass'])
    s.f('body', 'front', 'outer').px(2, 3, P['gauge'][4]); s.f('body', 'front', 'outer').px(3, 3, P['brass'][3])
    s.f('arm_l', 'front', 'outer').px(1, 7, P['coat'][1]); s.f('arm_l', 'front', 'outer').px(2, 8, P['coat'][1])
    OUT.mkdir(exist_ok=True); return s.save(str(OUT / 'hartmut.png'))

if __name__ == '__main__': print(build())
