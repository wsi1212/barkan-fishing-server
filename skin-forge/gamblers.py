#!/usr/bin/env python3
"""사막 도박장 단골 4인 (신규 — 아직 서버에 없음, 스킨 선제작).

용도: 도박 관련 퀘스트를 주는 손님 NPC. 예) 슬롯 777 띄우기, 블랙잭 연승,
      하룻밤 수익 달성, 잃은 돈 되찾기.

★설계의 핵심: 딜러(31~42)와 손님이 옷만 보고 갈려야 한다.
  딜러 = 하우스 제복(검정 재킷 + 게임색 조끼 + 검정 나비타이 + 놋쇠 단추).
  ★손님에게는 이 조합을 하나도 주지 않는다 — 나비타이 금지, 검정 재킷 금지,
    게임색 조끼 금지. 대신 각자 '도박이 그 사람에게 무엇을 했는가'로 계층을 가른다.

4인 = 도박의 네 단계
    큰손   이기고 있는 사람      버건디 벨벳 + 금 조끼 + 시가        (부)
    타짜   업으로 하는 사람      차콜 조끼 + 챙모자 + 소매 속 카드   (기술)
    중독   못 끊는 사람          바랜 카디건 + 동전 컵 + 다크서클    (집착)
    폐인   다 잃은 사람          구겨진 회색 정장 + 풀린 넥타이      (파멸)
  넷을 나란히 세우면 그 자체로 도박장의 서사가 된다.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, mix, ramp       # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'

P = dict(
    burgundy=ramp('6b2b38', spread=0.46),
    gold=ramp('a8863a', spread=0.48),
    cream=ramp('c2b9a2', spread=0.44),
    charcoal=ramp('403e49', spread=0.38),
    # 6개 테이블 색(진홍·암청·녹·자주·황토·구리) 어디와도 안 겹치는 색이라야
    # 손님이 딜러로 오인되지 않는다
    sharpvest=ramp('4a3340', spread=0.44),
    ash=ramp('6b6870', spread=0.44),
    dingy=ramp('a89e88', spread=0.44),
    maroon=ramp('6e3038', spread=0.44),
    plum=ramp('5f4054', spread=0.44),
    oat=ramp('9a8f78', spread=0.48),
    leather=ramp('5a4433', spread=0.44),
    shoe=ramp('3a3641', spread=0.36),
    brass=ramp('b08d3c', spread=0.48),
    ivory=ramp('c4bba4', spread=0.45),
    ember=ramp('c4703a', spread=0.48),
)


def suit(s, jacket, shirt, y_hem=10, lapel=True, seed=0, sleeve_to=9,
         rumpled=False):
    """평범한 상하의 정장 — 딜러 제복과 달리 조끼도 나비타이도 없다.

    `rumpled`는 구김: 세로 주름을 촘촘히 넣고 옷단 라인을 흐트러뜨린다.
    """
    s.form_fill('body', jacket, 0, y_hem, layer='outer', base_idx=3, top=True)
    s.speckle('body', jacket, 0, y_hem, layer='outer',
              density=0.14 if rumpled else 0.06, seed=seed)
    f = s.f('body', 'front', 'outer')
    f.rect(3, 0, 4, 5, shirt[4])                         # 셔츠 앞섶(가슴판)
    f.px(3, 0, shirt[2]); f.px(4, 0, shirt[3])
    if lapel:
        for i in range(3):                               # 라펠이 V자로 벌어진다
            f.px(2 - i + 1, i, jacket[4]); f.px(5 + i - 1, i, jacket[4])
    s.folds('body', 2, y_hem - 1, jacket, layer='outer',
            cols=(1, 5) if rumpled else (1, 6), seed=seed)
    s.folds('body', 2, y_hem - 1, jacket, layer='outer', cols=(2, 5),
            face='back', seed=seed + 3)
    s.hem('body', y_hem, jacket, layer='outer', base_idx=3)
    for i, part in enumerate(('arm_r', 'arm_l')):
        s.form_fill(part, jacket, 0, sleeve_to, layer='outer', base_idx=3)
        s.speckle(part, jacket, 0, sleeve_to, layer='outer',
                  density=0.12 if rumpled else 0.06, seed=seed + i)
        s.hem(part, sleeve_to, jacket, layer='outer', base_idx=3)
        s.band(part, sleeve_to + 1, sleeve_to + 1, shirt[4], layer='outer')


# ─────────────────────────────────────────────────────────────────────────
def build_whale():
    """큰손 — 이기고 있는 사람. 퀘스트 예: 하룻밤에 얼마 따기.

    부는 '금의 양'이 아니라 '천의 질 + 금의 배치'로 말한다(발렌틴58에서 얻은 교훈).
    금은 조끼·반지·시곗줄 세 곳까지. 시가가 이 인물의 서명이다.
    """
    s = Skin(); SEED = 901
    skin, hair = ramp('c39a72'), ramp('3f332a')
    g.head_base(s, skin, seed=SEED)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=1, back=5, seed=SEED, part_x=5)   # 뒤로 넘긴 기름진 머리
    g.wrinkles(s, skin, crow=True, forehead=False)
    g.eyes(s, 'c9c4b8', ramp('4a3a2c'), y=4, gaze=0, brow=hair[1], brow_y=3)
    f = s.f('head', 'front')
    f.rect(2, 6, 5, 6, hair[2])                          # 다듬은 콧수염
    f.px(3, 6, hair[3])
    for x, y in ((1, 5), (6, 5)):                        # 잘 먹은 볼
        f.px(x, y, mix(f.get(x, y), (176, 108, 92, 255), 0.4))
    # ★시가 — 입 옆으로 물고 있다. 끝이 달아오른 1px가 전부지만 이게 캐릭터다
    f.px(6, 7, P['leather'][2]); f.px(7, 7, P['ember'][4])

    g.tunic(s, P['cream'], y0=0, y1=11, collar=True, seed=SEED, grain=0.05, hem=False)
    g.sleeves(s, P['cream'], y0=0, y1=11, seed=SEED, grain=0.05)
    g.hands(s, skin, rows=2)
    g.pants(s, P['charcoal'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['shoe'], rows=4, toe=True, cuff=False)

    suit(s, P['burgundy'], P['cream'], y_hem=10, seed=SEED, sleeve_to=9)
    fb = s.f('body', 'front', 'outer')
    fb.rect(3, 1, 4, 7, P['gold'][3])                    # 금실 조끼(딜러 조끼보다 좁다)
    fb.col(3, P['gold'][2], 1, 7); fb.row(7, P['gold'][1], 3, 4)
    for y in (2, 4, 6):
        fb.px(4, y, P['gold'][4])
    fb.px(2, 4, P['gold'][4]); fb.px(2, 5, P['gold'][2])  # 회중시계 줄
    fb.rect(6, 8, 7, 10, P['leather'][3])                # 두툼한 지갑
    fb.col(6, P['leather'][4], 8, 10); fb.px(7, 9, P['gold'][4])
    s.f('arm_l', 'front', 'base').px(1, 11, P['gold'][4])  # 금반지(한쪽 손만)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'gm_whale.png'))


def build_sharp():
    """타짜 — 업으로 하는 사람. 퀘스트 예: 블랙잭/섯다 연승.

    ★표정을 지운다: 볼 홍조도 주름도 없고 챙 그림자로 눈매를 덮는다.
      '읽히지 않는 얼굴'이 이 직업의 전부다.
    """
    s = Skin(); SEED = 902
    skin, hair = ramp('b98a5c'), ramp('241d18')
    g.head_base(s, skin, seed=SEED)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=2, back=5, seed=SEED)
    g.eyes(s, 'c9c4b8', ramp('35302a'), y=4, gaze=0, brow=hair[1], brow_y=3)
    g.mouth(s, skin, y=6, w=2)
    f = s.f('head', 'front')
    for x in range(1, 7):                                # 챙이 드리운 그늘
        f.px(x, 3, mix(f.get(x, 3), (0, 0, 0, 255), 0.30))
    # 챙모자: 크라운 2행 + 챙 1행. ★눈(y4)은 절대 침범하지 않는다
    hat = P['charcoal']
    for fname in ('front', 'right', 'left', 'back'):
        fo = s.f('head', fname, 'outer')
        fo.rect(0, 0, 7, 1, hat[3]); fo.row(1, hat[1])
    s.f('head', 'top', 'outer').fill(hat[4])
    fo = s.f('head', 'front', 'outer')
    fo.rect(0, 2, 7, 2, hat[2])                          # 챙
    fo.px(0, 2, hat[1]); fo.px(7, 2, hat[1])
    s.f('head', 'right', 'outer').px(0, 2, hat[2])
    s.f('head', 'left', 'outer').px(3, 2, hat[2])
    s.f('head', 'front', 'outer').px(2, 1, P['maroon'][3])   # 모자 밴드 한 점

    g.tunic(s, P['cream'], y0=0, y1=11, collar=True, seed=SEED, grain=0.05, hem=False)
    g.sleeves(s, P['cream'], y0=0, y1=11, seed=SEED, grain=0.05)
    g.hands(s, skin, rows=2)
    g.pants(s, P['charcoal'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['shoe'], rows=4, toe=True, cuff=False)

    # 재킷 없이 조끼만 — 딜러와 갈리는 지점(딜러는 재킷 + 게임색 조끼 + 나비타이)
    vs = P['sharpvest']
    s.form_fill('body', vs, 0, 8, layer='outer', base_idx=3, top=True)
    s.speckle('body', vs, 0, 8, layer='outer', density=0.07, seed=SEED)
    fv = s.f('body', 'front', 'outer')
    fv.rect(3, 0, 4, 4, P['cream'][4])                   # 열린 깃 사이로 셔츠
    fv.px(3, 0, P['cream'][2]); fv.px(2, 1, vs[4]); fv.px(5, 1, vs[1])
    for y in (5, 7):                                     # 놋쇠 단추
        fv.px(4, y, P['brass'][4])
    s.hem('body', 8, vs, layer='outer', base_idx=3)
    s.folds('body', 2, 7, vs, layer='outer', cols=(1, 6), seed=SEED)
    s.folds('body', 2, 7, vs, layer='outer', cols=(2, 5), face='back', seed=SEED + 3)
    for i, part in enumerate(('arm_r', 'arm_l')):        # 셔츠 소매 걷음
        s.band(part, 6 + i, 6 + i, P['cream'][2], layer='base')
        s.band(part, 7 + i, 7 + i, P['cream'][4], layer='base')
    # ★소매 속에 숨긴 카드 — 왼팔 안쪽에 상아색 2px
    ac = s.f('arm_l', 'front', 'base')
    ac.px(0, 8, P['ivory'][4]); ac.px(0, 9, P['ivory'][2])
    fb = s.f('body', 'front', 'outer')
    fb.rect(6, 9, 7, 11, P['leather'][3])                # 허리 카드 케이스
    fb.col(6, P['leather'][4], 9, 11); fb.px(7, 10, P['brass'][3])
    return s.save(str(OUT / 'gm_sharp.png'))


def build_addict():
    """슬롯 중독 — 못 끊는 사람. ★퀘스트 예: 슬롯머신 777 띄우기.

    이 인물의 서명은 '동전 컵'이다. 옷은 한때 괜찮았지만 지금은 바랜 카디건이고,
    눈 밑 다크서클과 헝클어진 머리가 몇 시간째 앉아 있었다는 걸 말한다.
    """
    s = Skin(); SEED = 903
    skin, hair = ramp('cfa47e'), ramp('6b5540')
    g.head_base(s, skin, seed=SEED)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=3, back=7, seed=SEED, part_x=2)
    g.eyes(s, 'c9c4b8', ramp('4a4a58'), y=4, gaze=0, brow=hair[2], brow_y=3)
    f = s.f('head', 'front')
    f.px(0, 4, skin[1]); f.px(7, 4, skin[1])             # 속눈썹
    f.rect(3, 6, 4, 6, ramp('9b5a52')[2])                # 입술
    for x in (1, 2, 5, 6):                               # ★다크서클
        f.px(x, 5, mix(f.get(x, 5), (86, 70, 78, 255), 0.45))
    for x in (0, 7):                                     # 헝클어져 삐친 머리
        s.f('head', fname := 'front', 'outer').px(x, 3, hair[2])

    g.tunic(s, P['dingy'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07, hem=False)
    g.sleeves(s, P['dingy'], y0=0, y1=11, seed=SEED, grain=0.07)
    g.hands(s, skin, rows=2)
    g.pants(s, P['oat'], y0=0, y1=11, seed=SEED)
    g.boots(s, P['leather'], rows=3, toe=True, cuff=False)

    # 바랜 카디건: 앞이 활짝 열려 속 셔츠가 넓게 보인다(단추를 안 잠근 지 오래)
    car = P['plum']
    s.form_fill('body', car, 0, 10, layer='outer', base_idx=3, top=True)
    s.speckle('body', car, 0, 10, layer='outer', density=0.13, seed=SEED)
    fb = s.f('body', 'front', 'outer')
    fb.rect(2, 0, 5, 10, (0, 0, 0, 0), 0)                # 앞이 열림
    fb.col(1, car[4], 0, 10); fb.col(6, car[2], 0, 10)   # 여밈 두께
    s.folds('body', 2, 9, car, layer='outer', cols=(2, 5), face='back', seed=SEED)
    s.hem('body', 10, car, layer='outer', base_idx=3)
    for i, part in enumerate(('arm_r', 'arm_l')):
        s.form_fill(part, car, 0, 8 + i, layer='outer', base_idx=3)
        s.hem(part, 8 + i, car, layer='outer', base_idx=3)
    g.patch(s, 'leg_l', 'front', P['oat'], x=1, y=5, w=2, h=2, layer='outer')

    # ★동전 컵 — 이 인물의 전부. 컵 + 넘칠 듯한 놋쇠 동전
    fb.rect(2, 7, 5, 10, P['dingy'][3])
    fb.col(2, P['dingy'][4], 7, 10); fb.row(10, P['dingy'][1], 2, 5)
    for x, y in ((2, 6), (4, 6), (3, 7), (5, 7)):
        fb.px(x, y, P['brass'][4])
    fb.px(3, 6, P['brass'][2]); fb.px(5, 6, P['brass'][3])
    return s.save(str(OUT / 'gm_addict.png'))


def build_ruined():
    """폐인 — 다 잃은 사람. 퀘스트 예: 잃은 돈 되찾아 주기 / 빚 갚기.

    ★한때 좋은 옷이었다는 게 보여야 슬프다. 그래서 정장은 정장인데
      넥타이가 풀려 늘어지고, 주머니가 뒤집혀 나와 있고, 소매가 구겨져 있다.
    """
    s = Skin(); SEED = 904
    skin, hair = ramp('c09468'), ramp('4a4038')
    g.head_base(s, skin, seed=SEED)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=3, back=6, seed=SEED)
    g.eyes(s, 'c9c4b8', ramp('4a4a4a'), y=4, gaze=0, brow=hair[1], brow_y=3)
    g.beard(s, hair, style='stubble', y=5, seed=SEED)    # 며칠 안 깎은 수염
    g.mouth(s, skin, y=6, w=2)
    f = s.f('head', 'front')
    for x in (1, 2, 5, 6):                               # 다크서클
        f.px(x, 5, mix(f.get(x, 5), (80, 68, 68, 255), 0.40))
    for x in (2, 5):                                     # 이마에 흘러내린 머리
        s.f('head', 'front', 'outer').px(x, 3, hair[2])

    g.tunic(s, P['dingy'], y0=0, y1=11, collar=True, seed=SEED, grain=0.08, hem=False)
    g.sleeves(s, P['dingy'], y0=0, y1=11, seed=SEED, grain=0.08)
    g.hands(s, skin, rows=2)
    g.pants(s, P['charcoal'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['shoe'], rows=4, toe=True, cuff=False)

    suit(s, P['ash'], P['dingy'], y_hem=10, seed=SEED, sleeve_to=7, rumpled=True)
    fb = s.f('body', 'front', 'outer')
    # ★풀려서 늘어진 넥타이 — 매듭이 가슴까지 내려와 있다
    fb.px(4, 1, P['maroon'][2]); fb.px(4, 2, P['maroon'][4])
    fb.rect(4, 3, 4, 6, P['maroon'][3]); fb.px(4, 6, P['maroon'][1])
    fb.px(3, 1, P['dingy'][4])                           # 풀린 셔츠 단추
    # ★뒤집혀 나온 빈 주머니 — 빈털터리의 관용 기호
    for part, x in (('leg_r', 2), ('leg_l', 1)):
        pf = s.f(part, 'front', 'outer')
        pf.rect(x, 1, x + 1, 2, P['dingy'][4]); pf.px(x, 2, P['dingy'][2])
    g.patch(s, 'arm_r', 'front', P['dingy'], x=1, y=9, w=2, h=2, layer='outer')
    return s.save(str(OUT / 'gm_ruined.png'))


BUILDERS = dict(whale=build_whale, sharp=build_sharp,
                addict=build_addict, ruined=build_ruined)

if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    for k in sys.argv[1:] or BUILDERS:
        print(BUILDERS[k]())
