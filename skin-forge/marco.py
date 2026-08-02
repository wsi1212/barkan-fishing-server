#!/usr/bin/env python3
"""마르코 — &a[Q] 상인 마르코, 상단마을, citizensId 82.

CHARACTER BRIEF  (npc_brief.py 마르코 --village)
  대사   "사막 상단의 마르코올시다." / "거래는 신뢰가 전부지요."
  퀘스트 사막 특산품 · 대량 수출(40마리 판매) · 황금 거래(60cm 2마리)
         · 프리미엄 수출(품질 80%+ B등급 3마리, "VIP 고객용")
         → 규모와 품질을 따지는 부유한 무역상. 사막과 '거래'하는 사람이지 사막 사람이 아니다.
  지역   상단마을(이탈리아풍 이름들: 안토니오·줄리아·마시모·도메니코) → 유럽풍이 맞다.
         ★사막 요소를 입히면 지역-테마 규칙 위반. 사막은 그가 '가는 곳'이지 사는 곳이 아니다.
  구스킨 ★불투명 384px = 머리만. 몸이 통째로 투명.

DESIGN SPEC
  나이/체격  40대, 잘 먹은 체구. 노동자가 아니라 장부를 쥔 사람
  실루엣     르네상스 무역상: 무릎 위 더블릿 + ★한쪽 어깨에만 걸친 짧은 망토(이탈리아 상인의
             전형) + 챙 없는 모자 + 허리 돈주머니. 스폰마을 노동자들(조끼·멜빵·앞치마)과
             완전히 다른 계층으로 읽혀야 한다
  팔레트     더블릿=버건디 벨벳(부유함) / 셔츠=크림 / 모자·망토=더 짙은 와인
             / ★악센트=금 2곳(가슴 브로치 + 벨트 버클). 상인에게 금은 로고가 아니라 신분
  비대칭     ★어깨 망토가 왼쪽에만 + 오른쪽 허리 돈주머니 + 왼손목 소매 커프만 접힘
  정체 모티프 금 브로치 3x2 — 문장 성격(상단 소속)이라 엠블럼이 정당한 드문 경우
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 다듬은 콧수염+염소수염(장인의 덥수룩함과
             반대되는 '손질된' 수염) · 검은 머리
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 82

P = dict(
    skin=ramp('c99a70'),
    hair=ramp('3f3128'),                  # 검은 갈색
    beard=ramp('55443a'),                 # 손질된 수염(머리보다 한 단 밝게)
    doublet=ramp_lit('6e2f3a'),               # 버건디 벨벳
    cloak=ramp_lit('4a1f2a'),                 # 더 짙은 와인 = 어깨 망토·모자
    shirt=ramp_lit('c4b89c'),                 # 크림 셔츠
    gold=ramp_lit('c2a13f'),
    hose=ramp_lit('4a4238'),                  # 짙은 회갈 호스(다리)
    boot=ramp_lit('3c2f26'),
    iris=ramp('4a3a2c'),
)

BROOCH = ['##',
          '#-']        # 2x2. 3x3 + 그림자는 가슴에서 '로고'처럼 번쩍인다(실측)


def build():
    s = Skin()

    # ---- head (모자 2행: 0-1 모자 / 2 이마 / 3 눈썹 / 4 눈 / 5 볼 / 6 콧수염 / 7 염소수염)
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=6, seed=SEED, part_x=5)
    g.beard(s, P['beard'], style='goatee', y=5, seed=SEED)
    s.f('head', 'front').rect(2, 6, 5, 6, P['beard'][2])     # 다듬은 콧수염
    s.f('head', 'front').px(3, 6, P['beard'][3])
    g.wrinkles(s, P['skin'], crow=True, forehead=False)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, brow=P['hair'][2], brow_y=3)
    g.cap(s, P['cloak'], crown=2, brim=False, seed=SEED)     # 챙 없는 벨벳 모자

    # ---- 몸: 크림 셔츠 → 버건디 더블릿 → 한쪽 어깨 망토
    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, grain=0.06, hem=False)
    g.sleeves(s, P['shirt'], y0=0, y1=9, seed=SEED, grain=0.06)
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['hose'], y0=0, y1=7, seed=SEED)   # 바지까지 와인이면 하체가 한 덩어리
    g.boots(s, P['boot'], rows=4, toe=True, cuff=True)

    # 단추까지 금이면 악센트가 3곳(브로치·단추·버클) — 규칙상 2곳까지라 단추는 어둡게
    g.vest(s, P['doublet'], y0=0, hem=9, gap=0, seed=SEED, buttons=P['boot'])
    for part in ('arm_r', 'arm_l'):                          # 더블릿 소매
        s.form_fill(part, P['doublet'], 0, 7, layer='outer', base_idx=3)
        s.hem(part, 7, P['doublet'], layer='outer', base_idx=3)
    s.clear_rows('arm_l', 7, 11, layer='outer')              # 왼쪽만 커프 접힘
    s.hem('arm_l', 6, P['doublet'], layer='outer', base_idx=3, lip=False)

    # ★한쪽 어깨 망토: 왼 어깨~가슴 일부 + top면 + 등 절반
    cl = P['cloak']
    s.f('body', 'top', 'outer').rect(4, 0, 7, 3, cl[3])
    s.f('body', 'front', 'outer').rect(5, 0, 7, 6, cl[3])
    s.f('body', 'front', 'outer').col(5, cl[1], 0, 6)        # 망토 가장자리 두께
    s.f('body', 'front', 'outer').row(6, cl[1], 5, 7)
    s.f('body', 'left', 'outer').rect(0, 0, 3, 8, cl[2])
    s.f('body', 'left', 'outer').row(8, cl[1])
    s.f('body', 'back', 'outer').rect(0, 0, 3, 7, cl[2])
    s.f('body', 'back', 'outer').row(7, cl[1], 0, 3)
    s.speckle('body', cl, 0, 6, layer='outer', density=0.08, seed=SEED, faces=('front',))

    # 금 브로치(상단 소속) + 금 버클 — 악센트는 이 둘뿐
    s.motif('body', BROOCH, 1, 3, P['gold'], layer='outer', shade=False)
    g.belt(s, P['boot'], y=8, accent=P['gold'], layer='outer')
    g.pouch(s, P['boot'], part='leg_r', face='front', x=1, y=2, w=2, h=3,
            metal=P['gold'])                                  # 돈주머니

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'marco.png'))


if __name__ == '__main__':
    print(build())
