#!/usr/bin/env python3
"""오토 — &b[물고기 판매], 항구(스폰도시), citizensId 14.

CHARACTER BRIEF  (npc_brief.py 오토 --village 에서 뽑은 근거)
  역할   물고기 판매상 = 항구 어물전 주인. 대사 없음 → 역할+지역이 컨셉의 전부.
  지역   항구 < 스폰도시. 유럽풍 중세 항구. 사막/아라비안 요소 금지.
  이웃   프란츠(요리)·베티나·디르크·미아·랄프 — 같은 마을이므로 팔레트 계열은 맞추고
         실루엣은 겹치지 않게. 어물전 주인은 "젖은 가죽 + 걷어붙인 소매"가 전담 실루엣.

DESIGN SPEC  (그리기 전에 전부 선언 — 이 표가 품질의 근본 레버)
  나이/체격  40대 중반, 손이 억센 상인
  실루엣     걷어붙인 리넨 셔츠 + 무릎 덮는 방수 가죽 앞치마 + 젖은 장화 + 어부 캡
  팔레트     셔츠=바랜 청록(항구 물색) / 앞치마=소금기 낀 가죽 / 장화=젖은 진갈색
             / 바지=캔버스 회갈 / 악센트=놋쇠(버클 1곳 + 파우치 잠금 1곳, 그 이상 금지)
  비대칭     왼팔만 소매 걷음 · 오른 허벅지에 비늘칼 파우치 · 앞치마 왼쪽 아래 헝겊 패치
  얼굴       그을린 피부, 짧은 회갈 머리+구레나룻, 짧은 수염, 회청색 눈(안쪽 응시=기본),
             눈가 주름, 코 없음(기본)
  정체 모티프 가슴 로고 없음(장인은 로고를 안 붙인다) — 정체성은 앞치마 재단 + 파우치로
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 14

P = dict(
    skin=ramp('b9825e'),                  # tanned
    hair=ramp('6f6154'),                  # grey-brown
    beard=ramp('6d5c48'),                 # mid brown: darker than skin, lighter than hair
    shirt=ramp('4f6f6a'),                 # washed harbour teal
    apron=ramp('8d6c3e'),                 # salt-stained leather: must out-value the
    #                                       trousers or the whole lower body reads as one mass
    pants=ramp('5f574c'),                 # canvas
    boot=ramp('4a3a2e'),                  # wet leather
    brass=ramp('b08d3c'),
    iris=ramp('4a6070'),
)


def build():
    s = Skin()

    # ---- head: skin -> hair -> beard -> features (order matters, later wins)
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=6, seed=SEED, part_x=5)
    g.beard(s, P['beard'], style='full', y=5, seed=SEED, ragged=False)  # cheeks stay clear
    g.wrinkles(s, P['skin'], crow=True, forehead=False)   # cap covers the forehead
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, brow=P['hair'][1], brow_y=3)
    #   gaze=0 = 양쪽 홍채 안쪽(기본값). 코는 생략이 기본 — 오토는 캐릭터성이 없어 안 넣음
    g.mouth(s, P['skin'], y=6, w=2, color=P['beard'][1])  # mouth line inside the moustache
    g.cap(s, P['shirt'], crown=3, band=P['boot'], seed=SEED)  # knit fisherman's cap
    for x in (0, 7):                                        # sideburns under the cap
        s.f('head', 'front', 'outer').px(x, 4, P['hair'][2])

    # ---- torso: shirt (base) then leather apron (outer)
    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, fold_cols=(2, 5),
             grain=0.07)
    g.apron(s, P['apron'], bib=(2, 5), bib_y=(1, 5), waist=6, hem=11,
            wrap=2, straps=True, tie=True, seed=SEED)
    s.buckle('body', 6, P['brass'], layer='outer')           # brass buckle on the apron tie
    for x in (2, 5):                                         # bib rivets, not a chest logo
        s.f('body', 'front', 'outer').px(x, 1, P['brass'][4])
    g.patch(s, 'body', 'front', P['apron'], x=1, y=9, w=2, h=2, layer='outer')

    # ---- arms: left sleeve rolled up (the asymmetry)
    g.sleeves(s, P['shirt'], y0=0, y1=9, rolled=('arm_l', 6), skin_r=P['skin'],
               seed=SEED, grain=0.07)
    g.hands(s, P['skin'], rows=2)

    # ---- legs: canvas trousers, wet boots, gutting-knife pouch on one thigh
    g.pants(s, P['pants'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['boot'], rows=4, toe=True, cuff=True)
    g.pouch(s, P['boot'], part='leg_r', face='front', x=1, y=2, w=2, h=3,
            metal=P['brass'])

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'otto.png'))


if __name__ == '__main__':
    print(build())
