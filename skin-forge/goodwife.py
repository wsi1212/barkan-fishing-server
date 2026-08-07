#!/usr/bin/env python3
"""마을 아낙 — &f마을 아낙(시민3), 왕도 성내, citizensId 66.

CHARACTER BRIEF
  대사   "어서 오세요. 왕성 안은 늘 사람이 북적여서 정신이 하나도 없다니까요."
         → 기능도 퀘스트도 없는 &f 대화 NPC. 왕성 안에 사는 평범한 살림꾼.
  구스킨 ★분홍 머리 + 군용 위장무늬 + 검은 코르셋에 맨어깨 = 애니메이션 캐릭터.
         왕도 평민과 아무 관계가 없다.

DESIGN SPEC
  나이/체격  30대 살림꾼. 화려할 이유가 하나도 없는 인물 — 악센트 금속 0곳
  실루엣     발목까지 오는 커틀(원피스) + 그 위 앞치마 + 걷어붙인 리넨 소매
             + ★땋아 내린 머리(맨머리)
             ★기존 여성 NPC 차별: 베아트리체=올리브 보디스+세이지 두건 /
             힐데=회청 로브+흰 코이프 → 66은 두건을 쓰지 않고 땋은 머리로 간다
  팔레트     커틀=벽돌 적갈(테라코타) / 소매·칼라=크림 리넨 / 앞치마=짙은 회갈
             (커틀과 2단 이상 벌려 하체가 한 덩어리로 뭉치지 않게)
  비대칭     오른 허리 열쇠고리 + 왼쪽 치마 아래 기운 자국(살림꾼의 낡음)
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 속눈썹 + 입술
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 66

P = dict(
    skin=ramp('cfa47e'),
    hair=ramp('4f3b2a'),
    kirtle=ramp_lit('8f5744'),
    # 슈미즈·앞치마·커틀 셋의 명도를 확실히 벌린다 — 첫 빌드에서 앞치마(5c5548)가
    # 커틀(8f5744)과 같은 명도라 상체가 통째로 벽돌 덩어리가 됐다
    linen=ramp_lit('a8aca6'),
    # c9bfa8은 램프 [4]가 fff5ea(거의 흰색)라 앞치마가 옷 전체를 삼킨다
    apron=ramp_lit('9a8f7c'),
    iron=ramp_lit('8a8e93'),
    lip=ramp('9b5a52'),
    iris=ramp('4a3a2c'),
)


def build():
    s = Skin()

    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=7, seed=SEED, part_x=4)
    g.face_shape(s, P['skin'], jaw='oval')
    g.face_marks(s, P['skin'], kind='freckles', seed=SEED)
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['green']), y=4, gaze=0, iris_idx=2)
    g.brow(s, P['hair'][1], y=3)
    f = s.f('head', 'front')
    f.px(0, 4, P['skin'][1]); f.px(7, 4, P['skin'][1])   # 속눈썹/눈꼬리
    f.rect(3, 6, 4, 6, P['lip'][2])                      # 입술
    g.ponytail(s, P['hair'], x0=3, w=2, y0=0, y1=6)      # 등으로 땋아 내린 머리

    # ---- base: 리넨 속옷 → 커틀
    g.tunic(s, P['linen'], y0=0, y1=11, collar=True, seed=SEED, grain=0.06, hem=False)
    g.sleeves(s, P['linen'], y0=0, y1=11, seed=SEED, grain=0.06)
    g.pants(s, P['kirtle'], y0=0, y1=11, seed=SEED)
    g.hands(s, P['skin'], rows=2)

    # 커틀은 발목까지 내려오는 한 벌 — 소매는 팔꿈치까지만 덮고 리넨을 드러낸다
    g.robe(s, P['kirtle'], y0=0, seed=SEED, hem_row=11, sleeve_to=6,
           lining=P['linen'])
    for part in ('arm_r', 'arm_l'):                      # 걷어붙인 리넨 소매
        s.band(part, 7, 7, P['linen'][4], layer='base')

    # 앞치마: 커틀과 2단 이상 벌어진 짙은 회갈 — 하체가 한 덩어리가 되지 않게
    g.apron(s, P['apron'], bib=(2, 5), bib_y=(1, 5), waist=6, hem=11,
            wrap=0, straps=True, tie=True, seed=SEED)
    # ★앞치마 자락이 앞면을 꽉 채우면 정작 커틀이 안 보인다 — 양 옆 1px씩 비워
    #   벽돌색이 실루엣 가장자리로 흐르게 한다
    fa = s.f('body', 'front', 'outer')
    for x in (0, 7):
        fa.rect(x, 6, x, 11, (0, 0, 0, 0), 0)
    g.patch(s, 'leg_l', 'front', P['apron'], x=1, y=6, w=2, h=2, layer='outer')

    # 살림꾼의 유일한 소지품 — 허리 열쇠고리(금속은 여기 1px뿐)
    fr = s.f('body', 'front', 'outer')
    fr.px(6, 7, P['iron'][4]); fr.px(6, 8, P['iron'][2]); fr.px(7, 8, P['iron'][1])

    # ★긴 머리 — 반드시 <b>옷·머리쓰개를 다 그린 뒤</b>, 그리고 outer 레이어에.
    #   NPC는 lookclose로 늘 플레이어를 마주보므로 뒷머리는 볼 일이 없다 → 얼굴 옆과
    #   가슴 앞으로 내려와야 '길다'가 읽힌다. 머리쓰개는 함수가 알아서 비켜간다.
    g.female_hair_length(s, P['hair'], seed=SEED)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'goodwife.png'))


if __name__ == '__main__':
    print(build())
