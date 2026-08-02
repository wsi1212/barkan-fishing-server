#!/usr/bin/env python3
"""로테 — &b[유저마켓] 로테, 왕도 시장, citizensId 119.

CHARACTER BRIEF
  대사   "경매와 거래라면 저를 찾아오세요." / "좋은 물건 있으시면 내놓아보세요."
  기능   market(유저마켓·경매 GUI)
  구스킨 ★빨간 현대 블레이저 + 검정 스커트 + 노란 악센트 = 현대 커리어우먼.

DESIGN SPEC
  나이/체격  30대. 손을 더럽히지 않는 중개인 — 앞치마·패치·얼룩 금지
  실루엣     발목까지 오는 커틀 + ★가슴 앞 끈 조임(레이스) + 흰 리넨 소매·칼라
             + 허리 돈주머니 + 머리를 망(코이프)에 넣어 올림
             기존 여성 NPC 차별: 베아트리체=올리브 보디스+세이지 두건 /
             힐데=회청 로브+흰 코이프 / 66 아낙=벽돌 커틀+맨머리 땋음
             → 로테는 ★자주(plum)에 머리망
  팔레트     커틀=짙은 자주 / 소매·칼라=흰 리넨 / 벨트·주머니=검은 가죽
             / ★악센트=놋쇠 2곳(가슴 끈 아일릿 + 벨트 버클). 경매인의 금속은
             장신구가 아니라 저울추와 열쇠 쪽이다
  비대칭     오른 허리 돈주머니 + 왼손목만 소매를 접어 올림
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 속눈썹 + 입술
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 119

P = dict(
    skin=ramp('d0a57f'),
    hair=ramp('6b4a2f'),
    # 기본 spread면 [3]~[4]가 마젠타로 튄다 — 서버 팔레트는 전부 뮤트다
    kirtle=ramp_lit('4e2d47', spread=0.44),
    linen=ramp_lit('c4bcaa'),
    net=ramp_lit('8a8378'),
    leather=ramp_lit('3a3129'),
    brass=ramp_lit('b9973c'),
    lip=ramp('9b5a52'),
    iris=ramp('4a5a3f'),
)


def build():
    s = Skin()

    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=5, seed=SEED, part_x=3)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, brow=P['hair'][2], brow_y=3)
    f = s.f('head', 'front')
    f.px(0, 4, P['skin'][1]); f.px(7, 4, P['skin'][1])   # 속눈썹/눈꼬리
    f.rect(3, 6, 4, 6, P['lip'][2])                      # 입술
    # 머리망: 뒤통수만 덮는다. 얼굴 쪽으로 내려오면 코이프(힐데)와 겹친다
    g.cap(s, P['net'], crown=2, brim=False, seed=SEED)
    for fname in ('back', 'right', 'left'):              # 망 아래로 빠져나온 머리
        s.f('head', fname, 'outer').rect(0, 2, 3 if fname != 'back' else 7, 3,
                                         P['hair'][2])
    # ★망을 이마까지 끌고 오면 '회색 비니'가 된다 — 앞면은 관자놀이 양끝만 남긴다
    s.f('head', 'front', 'outer').clear()
    for x in (0, 7):
        s.f('head', 'front', 'outer').rect(x, 0, x, 2, P['net'][3])

    # ---- base: 리넨 슈미즈 → 커틀
    g.tunic(s, P['linen'], y0=0, y1=11, collar=True, seed=SEED, grain=0.06, hem=False)
    g.sleeves(s, P['linen'], y0=0, y1=11, seed=SEED, grain=0.06)
    g.pants(s, P['kirtle'], y0=0, y1=11, seed=SEED)
    g.hands(s, P['skin'], rows=2)

    # 커틀: 발목까지. 소매는 팔꿈치까지만 덮어 흰 리넨을 드러낸다
    g.robe(s, P['kirtle'], y0=0, seed=SEED, hem_row=11, sleeve_to=7,
           lining=P['linen'])
    s.clear_rows('arm_l', 6, 11, layer='outer')          # 왼소매만 더 접어 올림
    s.hem('arm_l', 5, P['kirtle'], layer='outer', base_idx=3, lip=False)

    # ★가슴 끈 조임(레이스) — 세로 중심축이자 커틀을 '재단된 옷'으로 만든다
    fb = s.f('body', 'front', 'outer')
    # ★2px 폭을 통째로 어둡게 칠하면 가슴에 검은 사각형이 붙는다(실측).
    #   여밈은 robe()가 이미 그린 세로 축(x3 밝음 / x4 어둠)에 맡기고,
    #   여기서는 그 양옆에 끈 구멍(아일릿)만 교대로 찍는다.
    for y in range(2, 7, 2):
        fb.px(2, y, P['linen'][3]); fb.px(5, y, P['linen'][2])
    fb.px(3, 1, P['brass'][4])

    g.belt(s, P['leather'], y=7, accent=P['brass'], layer='outer')
    g.pouch(s, P['leather'], part='leg_r', face='front', x=1, y=1, w=2, h=3,
            metal=P['brass'])

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'lotte.png'))


if __name__ == '__main__':
    print(build())
