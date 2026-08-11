#!/usr/bin/env python3
"""근위병 라이너 — 영주성 성문, citizensId 172.

CHARACTER BRIEF
  성문에서 신참을 막고 수비대 식량을 받는 실무형 근위병. 왕실 위병과 다른 영주가 수비대라
  강철 갑옷 대신 짙은 녹색 타바드와 오래 쓴 가죽 장비를 쓴다.

DESIGN SPEC
  나이/체격  30대 초반, 단단한 체격
  실루엣     어두운 가죽 조끼 + 이끼색 타바드 + 무릎 장화 + 한쪽 팔 보호대
  팔레트     가죽=짙은 갈색 / 타바드=습지 이끼색 / 튜닉=무채색 리넨 / 악센트=무광 놋쇠 2곳
  비대칭     오른팔 가죽 보호대와 왼 무릎의 헝겊 패치
  정체 모티프 영주가의 작은 강물 문장(타바드 가슴 3x3, 근위병에게만 허용)
  얼굴       짧은 흑갈색 머리·옅은 수염·갈색 눈·흉터 한 점, 코 생략
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / '.codex/skills/npc-skin-style-mirror/scripts'))
import garments as g
from skinlib import Skin, ramp, ramp_lit

OUT = pathlib.Path(__file__).parent / 'out'
P = dict(skin=ramp('a87550'), hair=ramp('3f3328'), linen=ramp_lit('65655e'),
         leather=ramp_lit('453a2e'), tabard=ramp_lit('4e654e'), boot=ramp_lit('342c24'),
         brass=ramp_lit('a67c37'), iris=ramp('5b4430'))
CREST=['.#.','###','.#.']
def build():
    s = Skin(); seed = 172
    g.head_base(s, P['skin'], seed=seed); g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=5, seed=seed); g.beard(s, P['hair'], style='stubble', y=6, seed=seed)
    g.face_shape(s, P['skin'], jaw='square'); g.face_marks(s, P['skin'], kind='scar', seed=seed)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, iris_idx=1); g.brow(s, P['hair'][1], y=3)
    g.mouth(s, P['skin'], y=6, w=2, color=P['hair'][2])
    g.tunic(s, P['linen'], collar=True, seed=seed, grain=.07)
    g.sleeves(s, P['linen'], y0=0, y1=9, seed=seed, grain=.07); g.hands(s, P['skin'], rows=2)
    g.pants(s, P['leather'], y0=0, y1=7, seed=seed); g.boots(s, P['boot'], rows=4, toe=True, cuff=True)
    g.vest(s, P['leather'], y0=0, hem=8, layer='outer', seed=seed)
    g.tabard(s, P['tabard'], y0=1, hem=11, panel=(1,6), layer='outer', seed=seed, accent=P['brass'])
    s.motif('body', CREST, 3, 4, P['brass'], layer='outer', shade=False)
    g.belt(s, P['leather'], y=10, accent=P['brass'], layer='outer')
    s.form_fill('arm_r', P['leather'], 3, 8, layer='outer', base_idx=3); g.patch(s, 'leg_l', 'front', P['leather'], 1, 4, 2, 2)
    OUT.mkdir(exist_ok=True); return s.save(str(OUT / 'rainer.png'))
if __name__ == '__main__': print(build())
