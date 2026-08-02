#!/usr/bin/env python3
"""바르칸 국왕 — &a[Q] 바르칸 국왕, 왕도 알현실, citizensId 44.

CHARACTER BRIEF
  대사   "짐이 바르칸의 왕이다. 이름 없는 어부여, 그대의 명성이 이 왕성까지 닿았노라."
         ★"왕국의 바다가 어지럽다." / "안개 너머에서 검은 그림자가 스며들고 있다. …조심하라."
         → 위엄 + 근심. 승리한 왕이 아니라 무언가를 예감하고 있는 왕이다.
  퀘스트 왕도04 근위대장의 시험
  구스킨 ★★얼굴이 아예 없다(유저 지적). 머리 전체가 흰 왕관 덩어리 — 눈·눈썹·입이
         한 픽셀도 없고, 겉옷 레이어가 눈 구역을 덮고 있다. 순백 75px 클리핑.

DESIGN SPEC
  나이/체격  50대 후반. 위엄 있되 지쳐 있다(이마 주름·관자놀이 흰머리)
  실루엣     ★톱니 금관(이마 위 2행만 — 얼굴을 절대 덮지 않는다) + 어민 모피 칼라
             + 왕실 진홍 서코트(금실 앞섶) + 발목까지 내려오는 망토
  팔레트     진홍=위병 타바드(8f2b32)와 같은 계열이되 한 단 위 / 망토=더 짙은 진홍
             / ★어민(흰 바탕 검은 점)=왕족 전용 모피. 발렌틴58의 담비(갈회색)와
             재질이 명확히 갈린다 / 금=왕관·칼라 체인·앞섶·벨트
             ★"금은 권력자에게" — 왕은 그 규칙의 예외가 아니라 대상이다
  비대칭     왼 허리 인장 주머니 + 망토가 오른 어깨에서 더 길게 흐름
  얼굴       ★최우선 요구사항: 눈·눈썹·입이 반드시 보일 것
             눈동자 안쪽(기본) · 코 없음(기본) · 다듬은 수염 · 이마 주름
"""
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, mix, ramp, ramp_lit       # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 44

P = dict(
    skin=ramp('c9a077'),
    hair=ramp('6b5f52'),
    beard=ramp('7a6e5f'),
    royal=ramp_lit('9c2f38'),
    cloak=ramp_lit('6e1f2a'),
    # 어민은 흰 모피지만 순백(ffffff)으로 잡으면 램프 위가 클리핑돼 8x8에서 번진다
    ermine=ramp_lit('c2bcac'),
    fleck=ramp_lit('34302c'),
    gold=ramp_lit('c2a13f'),
    gem=ramp_lit('2f4a7a'),
    hose=ramp_lit('35313a'),
    boot=ramp_lit('3f332a'),
    iris=ramp('4a5a6b'),
)


def crown(s):
    """톱니 금관 — ★이마 위 2행까지만. 구스킨은 왕관이 머리 전체를 먹어 얼굴이 없었다.

    최상단 행(y0)을 금/투명 교대로 비워 위쪽 실루엣이 뾰족하게 읽히게 한다.
    (스킨 아틀라스에서 머리 위로 솟는 픽셀은 만들 수 없으므로, 톱니는 '비워서' 만든다)
    """
    gold = P['gold']
    for fname in ('front', 'right', 'left', 'back'):
        f = s.f('head', fname, 'outer')
        f.row(1, gold[3])
        f.row(2, gold[1])                                # 관테 아래 그림자
        for x in range(f.w):
            if x % 2 == 0:
                f.px(x, 0, gold[4])
    s.f('head', 'front', 'outer').px(3, 1, P['gem'][3])  # 정면 보석
    s.f('head', 'front', 'outer').px(4, 1, P['gem'][1])


def ermine_collar(s):
    """어민 칼라 — 흰 모피에 검은 점. 왕족만 쓰는 재질이라 그 자체가 계급 표시다."""
    er, fl = P['ermine'], P['fleck']
    for fname in ('right', 'left'):
        s.f('body', fname, 'outer').rect(0, 0, 3, 2, er[3])
    for fname in ('front', 'back'):
        s.f('body', fname, 'outer').rect(1, 0, 6, 2, er[3])
    s.f('body', 'top', 'outer').fill(er[4])
    f = s.f('body', 'front', 'outer')
    for x in (1, 6):                                     # 앞섶을 따라 내려오는 리버스
        f.rect(x, 3, x, 8, er[3])
        f.px(x, 8, er[1])
    rnd = random.Random(SEED)
    for fname in ('front', 'back', 'right', 'left'):     # 검은 점무늬
        fa = s.f('body', fname, 'outer')
        for y in range(0, 3):
            for x in range(fa.w):
                if fa.get(x, y)[3] and rnd.random() < 0.20:
                    fa.px(x, y, fl[2])
    for x in (1, 6):
        for y in range(3, 9):
            if rnd.random() < 0.25:
                f.px(x, y, fl[2])


def build():
    s = Skin()

    # ---- 머리 (0-2 왕관 / 3 눈썹 / 4 눈 / 5 볼 / 6-7 수염) — 얼굴이 최우선
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=3, back=8, seed=SEED)
    for y in (3, 4, 5):                                  # 관자놀이 흰머리
        for fname, x in (('right', 1), ('left', 2)):
            fa = s.f('head', fname)
            fa.px(x, y, mix(fa.get(x, y), P['beard'][4], 0.55))
    g.beard(s, P['beard'], style='full', y=5, seed=SEED, ragged=False)
    g.wrinkles(s, P['skin'], brow_y=2, crow=True, forehead=False)
    g.face_shape(s, P['skin'], jaw='long')
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['blue']), y=3, gaze=0, iris_idx=1, socket=P['skin'][1])
    g.brow(s, P['hair'][1], y=2)
    g.mouth(s, P['skin'], y=6, w=2)
    crown(s)

    # ---- base: 속옷 → 호스 → 장화 (base 6면 전부 불투명하게)
    g.tunic(s, P['royal'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07, hem=False)
    g.sleeves(s, P['royal'], y0=0, y1=11, seed=SEED, grain=0.07)
    g.hands(s, P['skin'], rows=1)
    g.pants(s, P['hose'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['boot'], rows=4, toe=True, cuff=True)

    # ---- 서코트: 발목까지. 왕은 짧은 옷을 입지 않는다
    g.robe(s, P['royal'], y0=0, seed=SEED, hem_row=9, sleeve_to=10)
    for part in ('leg_r', 'leg_l'):
        s.hem(part, 9, P['royal'], layer='outer', base_idx=3)

    # ---- 망토: 등에서 발목까지. 앞은 어깨 곡선으로 끝나 얼굴·가슴을 열어둔다
    g.mantle(s, P['cloak'], front=3, back=11, seed=SEED, lining=P['ermine'])
    for part in ('leg_r', 'leg_l'):                      # 망토 자락이 다리 뒤로 이어진다
        s.form_fill(part, P['cloak'], 0, 8, layer='outer', base_idx=2,
                    faces=('back',))
    ermine_collar(s)

    # ---- 금: 왕관 · 칼라 체인 · 앞섶 금실 · 벨트 버클
    f = s.f('body', 'front', 'outer')
    for y in range(3, 11, 2):
        f.px(3, y, P['gold'][4]); f.px(4, y, P['gold'][1])
    g.belt(s, P['boot'], y=9, accent=P['gold'], layer='outer')
    # 왼 허리 인장 주머니(비대칭)
    f.rect(6, 10, 7, 11, P['boot'][3]); f.px(6, 10, P['gold'][3])

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'king.png'))


if __name__ == '__main__':
    print(build())
