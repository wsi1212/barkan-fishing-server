#!/usr/bin/env python3
"""심해조사관 테클라 — 은빛 갈매기호 갑판 아래, citizensId 174.

CHARACTER BRIEF
  낚시사 길드가 파견한 젊은 심해 표본 조사관. 선원 제복과 겹치지 않게 관측자의
  긴 방수 외투, 표본 가방, 얼굴 앞에서 읽히는 묶은 머리를 중심으로 설계한다.

DESIGN SPEC
  나이/체격  20대 후반, 날렵한 체격
  실루엣     먹청 방수 코트 + 청록 안감 + 짧은 부츠 + 오른쪽 표본 가방
  팔레트     코트=깊은 바다 남청, 안감=해초 청록, 바지=젖은 회갈, 부츠=검은 갈색,
             악센트=황동 버클과 민트 표본병(두 곳)
  비대칭     오른쪽 허리 표본 가방, 왼쪽 소매의 접힌 지도 띠
  정체 모티프  가슴 로고 없이 허리의 작은 유리 표본병으로 조사관을 표현
  얼굴       붉은 갈색 앞머리와 어깨 길이 옆머리, 큰 청회색 눈, 코 생략, 입술은 옅게
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / '.codex/skills/npc-skin-style-mirror/scripts'))
import garments as g
from skinlib import Skin, ramp, ramp_lit

OUT = pathlib.Path(__file__).parent / 'out'
P = dict(skin=ramp('b77e61'), hair=ramp('70463c'), coat=ramp_lit('284958'),
         lining=ramp_lit('4d827f'), pants=ramp_lit('4f5552'), boot=ramp_lit('322d2c'),
         brass=ramp_lit('a47d3d'), glass=ramp_lit('6db6a2'), iris=ramp('5f8390'))

def build():
    s = Skin(); seed = 174
    g.head_base(s, P['skin'], seed=seed); g.ears(s, P['skin'], y=4)
    g.face_shape(s, P['skin'], jaw='narrow')
    g.hair(s, P['hair'], fringe=3, back=7, seed=seed, part_x=3)
    g.female_hair_length(s, P['hair'], seed=seed, drop=4, front=True, shoulders=True)
    g.female_eyes_big(s, 'd5d5c8', P['iris'], P['skin'], P['hair'], eye_y=5, gaze=0, iris_idx=2)
    g.brow(s, P['hair'][2], y=3); g.mouth(s, P['skin'], y=7, w=2, color=P['hair'][3])
    g.tunic(s, P['lining'], collar=True, seed=seed, grain=.08)
    g.sleeves(s, P['lining'], y0=0, y1=9, seed=seed, grain=.08); g.hands(s, P['skin'], rows=2)
    g.pants(s, P['pants'], y0=0, y1=7, seed=seed); g.boots(s, P['boot'], rows=4, toe=True, cuff=True)
    g.coat(s, P['coat'], y0=0, hem=10, tails=3, seed=seed, lapel=True)
    g.belt(s, P['boot'], y=7, accent=P['brass'], layer='outer')
    g.pouch(s, P['coat'], part='leg_r', face='front', x=1, y=2, w=2, h=3, metal=P['brass'])
    g.hair_ornament(s, P['glass'], kind='pin', side='left', seed=seed)
    s.f('body', 'front', 'outer').px(5, 4, P['glass'][4])
    s.f('arm_l', 'front', 'outer').px(2, 6, P['brass'][3])
    OUT.mkdir(exist_ok=True); return s.save(str(OUT / 'tecla.png'))

if __name__ == '__main__': print(build())
