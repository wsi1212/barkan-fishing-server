#!/usr/bin/env python3
"""마을 주민 — &f마을 주민, 왕도, citizensId 68 (npc.json 키 '시민5').

CHARACTER BRIEF
  대사   ★"요즘 종탑에서 이상한 불빛이 보인다는 소문이 돌아요. …뭐, 헛소문이겠죠."
         → 종지기(48)의 목격담을 소문으로 나르는 평민. 왕성 안 배경 인물이지만
           스토리의 실마리를 흘리는 역할이다.
  구스킨 초록 후드티 같은 현대 캐주얼.

DESIGN SPEC
  나이/체격  30대, 평범한 체구
  실루엣     수수한 리넨 튜닉 + 가죽 벨트 + 헝겊 두건 + 어깨에 멘 자루
             (궁정 인물들과 달리 케이프·판금·금이 하나도 없어야 '평민'으로 읽힌다)
  팔레트     튜닉=오트밀 리넨 / 조끼=흙갈 / 두건=바랜 회갈 / ★악센트 없음
             왕도의 강철·진홍·잉크남보라 어느 계열도 아닌 '흙색'이 평민의 자리
  비대칭     자루 끈이 한쪽 어깨 + 오른 무릎 패치 + 왼소매만 걷음
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 짧은 스터블
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))
import garments as g                      # noqa: E402
from skinlib import Skin, ramp            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 68
P = dict(
    skin=ramp('c49a72'),
    hair=ramp('5a4a38'),
    tunic=ramp('b0a488'),
    vest=ramp('6e5a42'),
    hood=ramp('8a8072'),
    sack=ramp('9b8f74'),
    boot=ramp('4a3d2e'),
    iris=ramp('4a4034'),
)


def build():
    s = Skin()
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=6, seed=SEED)
    g.beard(s, P['hair'], style='stubble', y=5, seed=SEED)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, brow=P['hair'][2], brow_y=3)
    g.mouth(s, P['skin'], y=6, w=2)
    g.headscarf(s, P['hood'], rows=2, tail=False, seed=SEED)      # 헝겊 두건

    g.tunic(s, P['tunic'], y0=0, y1=11, collar=True, seed=SEED, grain=0.09, hem=False)
    g.sleeves(s, P['tunic'], y0=0, y1=9, rolled=('arm_l', 6), skin_r=P['skin'],
              seed=SEED, grain=0.09)
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['boot'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['boot'], rows=4, toe=True, cuff=True)

    g.vest(s, P['vest'], y0=1, hem=8, gap=0, seed=SEED, buttons=P['boot'])
    g.belt(s, P['boot'], y=9, accent=P['boot'], layer='outer')
    g.bandolier(s, P['sack'], front_x=2, layer='outer')           # 자루 끈
    f = s.f('body', 'back', 'outer')
    f.rect(1, 2, 6, 8, P['sack'][3])                              # 등에 멘 자루
    f.row(2, P['sack'][4], 1, 6); f.row(8, P['sack'][1], 1, 6)
    g.patch(s, 'leg_r', 'front', P['boot'], x=1, y=4, w=2, h=2)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'villager.png'))


if __name__ == '__main__':
    print(build())
