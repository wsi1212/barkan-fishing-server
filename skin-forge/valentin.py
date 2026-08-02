#!/usr/bin/env python3
"""궁정 상인 발렌틴 — &a[Q] 궁정 상인 발렌틴, 왕도, citizensId 58.

CHARACTER BRIEF
  대사   "궁정 상인 발렌틴입니다. 왕도의 상권, 함께 키워봅시다."
         "물건을 잘 파는 어부에겐 기회가 많지요."
  퀘스트 왕도의 상권(15) → 대량 거래(40) → ★왕실 납품상(70)
         → 왕실에 물건을 대는 조달상. 칼을 쥔 적이 없는 사람이다.
  구스킨 ★왕관형 금 투구 + 사슬갑옷 팔 + 금 트림 진홍 망토 + 판금 다리
         = 상인이 아니라 '왕' 또는 '기사'로 읽힘(유저 지적).

  ★교훈: 무장·금·문장은 그 인물의 '권한'을 뜻하는 기호다. 상인에게 사슬갑옷을
    입히면 직업이 지워진다. 갑옷은 병사에게, 금은 권력자에게, 문장은 소속이 있는
    자에게만. 부유함은 '갑옷의 양'이 아니라 '천의 질'로 보여야 한다.

DESIGN SPEC
  나이/체격  40대 후반, 잘 먹은 궁정 인물. 노동 흔적 없음(패치·잉크 얼룩 금지)
  실루엣     무릎까지 오는 궁정 가운 + ★담비 모피 숄칼라 + 벨벳 토크(챙 없는 모자)
             + 허리 벨트 + 겨드랑이 장부 + 한쪽 돈주머니
             왕도 인물 대비: 위병=판금 / 학자=잉크 남보라 로브 / 발렌틴=벨벳+모피
  팔레트     가운=짙은 청록 벨벳(왕도에서 안 쓰인 색. 위병 진홍·전령 파랑·학자 남보라와
             겹치지 않는다) / 모피=따뜻한 회백 / 셔츠=크림 / 호스=짙은 회갈
             ★악센트 금 2곳뿐 — 앞섶 금실 자수 + 벨트 버클. 투구·사슬·문장 전면 폐기
  비대칭     오른 허벅지 돈주머니 + 왼쪽 겨드랑이 장부 + 왼소매만 커프 접힘
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 다듬은 짧은 수염 + 희끗한 관자놀이
             (마르코82는 염소수염이라 겹치지 않는다)
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, mix, ramp, ramp_lit       # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 58

# 값 뒤 인라인 주석은 쉼표를 삼켜 구문오류를 낸다 — 주석은 줄 위에
P = dict(
    skin=ramp('c39a72'),
    hair=ramp('4a4034'),
    grey=ramp_lit('8a8378'),
    # ★기본 spread(0.62)로 초록을 뽑으면 [4]가 민트로 튀어 '벨벳'이 아니라
    #   '체육복'이 되고, 그레인 얼룩이 곰팡이처럼 보인다 — 램프를 좁힌다.
    velvet=ramp_lit('24483c', spread=0.44),
    toque=ramp_lit('1b3830', spread=0.44),
    # 담비 모피를 회백으로 잡으면 턱 밑에서 수염과 뭉쳐 '흰 수염'으로 읽힌다(실측)
    fur=ramp_lit('7a7166'),
    shirt=ramp_lit('c8bda4'),
    hose=ramp_lit('35323d'),
    boot=ramp_lit('4a3a2c'),
    gold=ramp_lit('b9973c'),
    ledger=ramp_lit('7d5f45'),
    iris=ramp('4a4033'),
)


def fur_collar(s):
    """담비 숄칼라 — 부유함을 '갑옷의 양'이 아니라 '천의 질'로 말하는 부품.

    목을 두르고 앞섶을 따라 가슴까지 내려온다(세로 요소). 어깨 바깥(x0·x7)은
    좁아져야 목도리가 아니라 칼라로 읽힌다.
    """
    fur = P['fur']
    for fname in ('right', 'left'):
        s.f('body', fname, 'outer').rect(0, 0, 3, 1, fur[3])
    for fname in ('front', 'back'):
        s.f('body', fname, 'outer').rect(1, 0, 6, 1, fur[3])
    s.f('body', 'top', 'outer').rect(0, 0, 7, 3, fur[4])
    f = s.f('body', 'front', 'outer')
    # ★리버스를 가슴 한가운데(x2·x5)에 세우면 금실 앞섶과 겹쳐 가슴이 통째로 밝아지고,
    #   턱 밑 모피와 수염이 뭉쳐 '흰 수염이 가슴까지 흘러내린' 꼴이 된다(실측 v2·v3).
    #   리버스는 바깥(x1·x6)으로 밀어 가슴을 V로 '테두리'만 잡는다.
    for x in (1, 6):
        f.rect(x, 2, x, 6, fur[3])
        f.px(x, 6, fur[1])
    # ★그레인 범위를 모피 밖으로 넓히면 벨벳 위에 회색 얼룩이 흩뿌려진다(실측 v4).
    #   칼라 행과 리버스 기둥에만 따로 건다.
    s.speckle('body', fur, 0, 1, layer='outer', density=0.16, seed=SEED,
              faces=('front',), strength=0.6)
    import random as _r
    rnd = _r.Random(SEED)
    for x in (1, 6):
        for y in range(2, 7):
            if rnd.random() < 0.35:
                f.px(x, y, fur[rnd.choice([2, 4])])
    s.speckle('body', fur, 0, 1, layer='outer', density=0.16, seed=SEED + 1,
              faces=('back', 'right', 'left'), strength=0.6)


def build():
    s = Skin()

    # ---- 머리 (0-2 모자 / 3 눈썹 / 4 눈 / 5 볼 / 6-7 수염)
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=6, seed=SEED, part_x=5)
    for y in (3, 4):                                     # 희끗한 관자놀이 = 연륜
        for fname, x in (('right', 1), ('left', 2)):
            fa = s.f('head', fname)
            fa.px(x, y, mix(fa.get(x, y), P['grey'][3], 0.6))
    g.beard(s, P['hair'], style='full', y=6, seed=SEED, ragged=False)
    g.wrinkles(s, P['skin'], crow=True, forehead=False)
    g.face_shape(s, P['skin'], jaw='narrow')
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['grey']), y=3, gaze=0, iris_idx=1, socket=P['skin'][1])
    g.brow(s, P['hair'][1], y=2)
    g.mouth(s, P['skin'], y=6, w=2)
    g.cap(s, P['toque'], crown=3, brim=False, seed=SEED)  # 궁정 벨벳 토크

    # ---- 속옷(base는 6면 전부 불투명하게 끝낸다)
    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, grain=0.06, hem=False)
    g.sleeves(s, P['shirt'], y0=0, y1=9, seed=SEED, grain=0.06)
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['hose'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['boot'], rows=4, toe=True, cuff=True)

    # ---- 궁정 가운: 무릎까지 내려오는 벨벳. 자락이 다리로 이어져야 코트가 된다
    g.coat(s, P['velvet'], y0=0, hem=11, tails=5, seed=SEED, lapel=False)
    for part in ('arm_r', 'arm_l'):                      # 넓은 벨벳 소매
        s.form_fill(part, P['velvet'], 0, 9, layer='outer', base_idx=3)
        s.speckle(part, P['velvet'], 0, 9, layer='outer', density=0.08, seed=SEED)
        s.hem(part, 9, P['velvet'], layer='outer', base_idx=3)
    s.clear_rows('arm_l', 8, 11, layer='outer')          # 왼소매만 커프 접힘(비대칭)
    s.hem('arm_l', 7, P['velvet'], layer='outer', base_idx=3, lip=False)
    s.band('arm_l', 8, 8, P['shirt'][3], layer='base')

    fur_collar(s)

    # ---- 금은 딱 두 곳: 앞섶 금실 자수(세로) + 벨트 버클. 그 이상은 상인이 아니다
    f = s.f('body', 'front', 'outer')
    for y in range(3, 10, 2):
        f.px(3, y, P['gold'][4]); f.px(4, y, P['gold'][1])
    g.belt(s, P['boot'], y=8, accent=P['gold'], layer='outer')

    # ---- 소지품(비대칭). 노동자가 아니므로 도구가 아니라 장부와 돈이다
    # 가슴은 모피 V + 금실만 남긴다. 상인의 기호는 벨트 아래에 매단 돈주머니 하나로
    # 충분하다 — 겨드랑이 장부는 옆면에 두면 팔에 가려 안 보이고(실측),
    # 앞면에 두면 가슴이 잡동사니가 된다
    f.rect(5, 9, 6, 11, P['boot'][3])
    f.col(5, P['boot'][4], 9, 11)
    f.row(11, P['boot'][1], 5, 6)
    f.px(6, 9, P['gold'][4])
    g.pouch(s, P['boot'], part='leg_r', face='front', x=1, y=1, w=2, h=3,
            metal=P['gold'])
    # 등판이 민무늬면 벨벳이 아니라 페인트다
    s.folds('body', 2, 10, P['velvet'], layer='outer', cols=(2, 5), face='back',
            seed=SEED + 9)

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'valentin.png'))


if __name__ == '__main__':
    print(build())
