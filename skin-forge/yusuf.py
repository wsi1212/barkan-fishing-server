#!/usr/bin/env python3
"""유세프 — &a[Q] 유세프, 사막마을 오아시스 어장 관리인, citizensId 79.

CHARACTER BRIEF  (npc_brief.py 유세프 --village)
  대사   "오아시스 어장을 관리하고 있소." / "일손이 필요하던 참이오."
  퀘스트 오아시스의 주인(B등급 3마리) · 사막 도감(15마리) · 더위를 이겨라(20마리 판매)
  지역   사막마을 < 사막 → 아라비안 테마가 '맞는' 몇 안 되는 자리(지역-테마 일치 규칙).
  이웃   자말(4.5m, 길드) · 유누스(6.5m) · 사피르 · 파티마
         같은 사막의 현자(147)가 이미 흰 토브 + 빨간 체크 케피예 → 그 조합은 피한다.
  구스킨 ★불투명 384px = 머리만 있고 몸·팔·다리가 통째로 투명. 인게임에서 몸이 안 보임.

DESIGN SPEC
  나이/체격  40대, 볕에 그을린 어장 관리인
  실루엣     두건 + 발목까지 오는 토브(로브) + 허리 새시 + 어깨에 걸친 물주머니 끈
             (현자=흰 토브/빨간 체크와 갈리도록 모래색 토브 + 무늬 없는 두건)
  팔레트     토브=모래 / 두건=밝은 모래 / ★새시=오아시스 청록(이 사람의 정체: 물)
             / 가죽=물주머니 끈. 악센트는 청록 한 곳뿐
  비대칭     물주머니 끈이 한쪽 어깨만 가로지름 + 오른쪽 허리 파우치 + 왼소매만 걷음
  정체 모티프 없음(문장 붙일 사람 아님). 정체성은 청록 새시 + 물주머니
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 짧은 검은 수염 · 눈꼬리 주름
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 79

P = dict(
    skin=ramp('9b6f45'),                  # 사막 볕에 그은 피부
    hair=ramp('3d3229'),                  # 검은 갈색 (순수검정 금지)
    beard=ramp('55483a'),                 # 수염은 머리보다 한 단 밝게 (턱이 검은 막대가 됨)
    robe=ramp('b8ae95'),                  # 모래빛 토브 (현자의 흰 토브와 구분)
    scarf=ramp('c9b98f'),                 # 밝은 모래 두건 (무늬 없음)
    sash=ramp('3f7a74'),                  # ★오아시스 청록 — 유일한 악센트
    leather=ramp('6b4f36'),               # 물주머니 끈
    iris=ramp('4a3524'),                  # 짙은 갈색
)


def build():
    s = Skin()

    # ---- head (두건 3행: 0-2 두건 / 3 눈썹 / 4 눈 / 5 볼 / 6 입 / 7 턱)
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=1, back=6, seed=SEED)
    g.beard(s, P['beard'], style='full', y=5, seed=SEED, ragged=False)
    g.wrinkles(s, P['skin'], crow=True, forehead=False)      # 두건이 이마를 덮음
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, brow=P['hair'][2], brow_y=3)
    g.mouth(s, P['skin'], y=6, w=2, color=P['hair'][1])
    g.headscarf(s, P['scarf'], rows=3, tail=True, seed=SEED, cord=P['leather'])

    # ---- 맨몸(base)을 먼저 다 채운다. 로브는 outer라 base가 비면 팔에 구멍이 뚫린다
    for part in ('arm_r', 'arm_l'):
        s.form_fill(part, P['skin'], 0, 11, base_idx=3, top=True, bottom=True)

    # ---- 토브: 몸통+다리 전체를 덮는 로브 + 허리 새시
    g.tunic(s, P['robe'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07, hem=False)
    g.robe(s, P['robe'], y0=0, seed=SEED, hem_row=11, sleeve_to=8)
    for part in ('arm_r', 'arm_l'):      # 소매를 한 단 어둡게 = 몸통과 팔이 분리돼 보인다
        s.form_fill(part, P['robe'], 0, 8, layer='outer', base_idx=2)
        s.hem(part, 8, P['robe'], layer='outer', base_idx=2)
    # 아라비안 새시는 허리를 '감는' 띠다. sash()는 대각선이라 물주머니 어깨끈과
    # 방향이 겹쳐 산만해졌다 → 링으로 두르고 앞에 매듭만.
    s.band('body', 7, 8, P['sash'][3], layer='outer')
    s.shade_ring('body', 9, layer='outer', amount=0.28)
    s.f('body', 'front', 'outer').rect(3, 7, 4, 8, P['sash'][4])   # 매듭
    s.f('body', 'front', 'outer').px(4, 8, P['sash'][1])
    g.bandolier(s, P['leather'], front_x=2, layer='outer')   # 물주머니 어깨끈(비대칭)
    g.headscarf(s, P['scarf'], rows=3, tail=True, seed=SEED, cord=P['leather'])

    # ---- 팔: 왼소매만 걷어 맨팔 (겉옷 행 구간만 지운다)
    # 6행부터 걷으면 팔 절반이 맨살이라 '한쪽만 옷을 안 입은' 꼴이 된다 → 팔뚝만.
    s.clear_rows('arm_l', 8, 11, layer='outer')
    s.hem('arm_l', 7, P['robe'], layer='outer', base_idx=2, lip=False)   # 걷어올린 소매단
    g.hands(s, P['skin'], rows=2)

    # ---- 다리: 로브 아래 샌들 신은 발
    g.pants(s, P['robe'], y0=0, y1=11, seed=SEED)            # 로브 안쪽(base)도 채운다
    g.boots(s, P['leather'], rows=2, toe=True, cuff=False)   # 샌들
    g.pouch(s, P['leather'], part='leg_r', face='front', x=1, y=2, w=2, h=3,
            metal=P['sash'])

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'yusuf.png'))


if __name__ == '__main__':
    print(build())
