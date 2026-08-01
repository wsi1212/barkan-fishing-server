#!/usr/bin/env python3
"""사막 도박장 딜러 12인 세트 — 룰렛·홀덤·섯다·블랙잭·쓰리카드·슬롯.

구스킨 실태
  ★12명 전원 현대 검정 턱시도 + 흰 셔츠 + 붉은 나비넥타이. 라스베가스 딜러다.
    게다가 실제로 3쌍이 완전 동일 텍스처였다(31=40, 32=36, 37=41).
  카지노는 사막마을 시설이므로 오아시스 도박장으로 읽혀야 한다.

SET ARCHITECTURE (위병·도서관 세트와 같은 원리)
  ★제복은 통일, 사람은 구분. 딜러 열둘이 각자 다른 옷이면 업장이 아니고,
    픽셀까지 같으면 복붙이다.
      공통(제복)  흰 리넨 셔츠 + 조끼 + 허리 새시 + 페즈(또는 터번) + 소매 걷음
      변주①테이블 ★조끼·새시 색 = 게임 종류. 손님이 색만 보고 테이블을 찾는다
        룰렛=진홍 / 홀덤=암청 / 섯다=녹 / 블랙잭=자주 / 쓰리카드=황토 / 슬롯=구리
      변주②사람  성별 · 수염 · 나이 · 머리쓰개(페즈/터번/맨머리) · 소품(카드/칩/주사위)

  같은 테이블 2~3인은 색이 같으므로 ②로만 갈린다 → audit는 --uniform-set으로 돈다.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'

U = dict(                                  # 제복 공통(전원 공유)
    shirt=ramp('bdb49c', spread=0.48),     # 흰 리넨 — 순백은 램프가 클리핑된다
    trouser=ramp('4a4238', spread=0.5),
    boot=ramp('3f342a', spread=0.45),
    brass=ramp('b08d3c', spread=0.5),
    ivory=ramp('c4bba4', spread=0.45),     # 상아 칩·주사위
)
# 테이블 색 — 이 세트의 1차 변주축
TABLE = dict(
    roulette=('8f2f38', 'crimson'), holdem=('2f3f5c', 'navy'),
    seotda=('35563f', 'green'), blackjack=('54304a', 'plum'),
    threecard=('8a6a2c', 'ochre'), slot=('96552f', 'copper'),
)

VARIANTS = {
    '31': dict(file='d_roulette1', cid=31, table='roulette', prop='ball',
               skin='a87a4e', hair='2f2721', beard='goatee', head='fez'),
    '40': dict(file='d_threecard2', cid=40, table='threecard', prop='cards',
               skin='9c7146', hair='3f3128', beard=None, head='turban'),
    '35': dict(file='d_threecard1', cid=35, table='threecard', prop='cards',
               skin='b98a5c', hair='2f2721', beard='stubble', head='fez'),
    '32': dict(file='d_holdem1', cid=32, table='holdem', prop='chips',
               skin='8f6339', hair='241d18', beard='full', head='fez'),
    '41': dict(file='d_holdem2', cid=41, table='holdem', prop='cards',
               female=True, skin='c09468', hair='3f2f24', beard=None, head='veilcap'),
    '33': dict(file='d_seotda1', cid=33, table='seotda', prop='cards',
               skin='9c7146', hair='4a3a2a', beard='mutton', head='turban', age=True),
    '42': dict(file='d_seotda2', cid=42, table='seotda', prop='dice',
               skin='a87a4e', hair='2f2721', beard='stubble', head=None),
    '34': dict(file='d_blackjack1', cid=34, table='blackjack', prop='cards',
               skin='b98a5c', hair='3f3128', beard='goatee', head='fez'),
    '38': dict(file='d_blackjack2', cid=38, table='blackjack', prop='chips',
               female=True, skin='b98a5c', hair='2f2721', beard=None, head='veilcap'),
    '39': dict(file='d_blackjack3', cid=39, table='blackjack', prop='dice',
               skin='8f6339', hair='9a938a', beard='full', head='turban', age=True),
    '36': dict(file='d_slot1', cid=36, table='slot', prop='chips',
               skin='c09468', hair='4a3a2a', beard=None, head='fez'),
    '37': dict(file='d_slot2', cid=37, table='slot', prop='ball',
               female=True, skin='a87a4e', hair='3f2f24', beard=None, head='veilcap'),
}


def fez(s, r, seed=0):
    """페즈 — 짧은 원통 모자. 술(tassel)이 뒤로 늘어진다.

    ★얼굴을 절대 침범하지 않는 3행짜리 모자라 딜러처럼 '얼굴이 보여야 하는'
      직군에 맞는다. 술은 뒤통수 outer로만 내려 정면 실루엣을 어지럽히지 않는다.
    """
    for fname in ('front', 'right', 'left', 'back'):
        f = s.f('head', fname, 'outer')
        f.rect(0, 0, 7, 2, r[3])
        f.row(0, r[4])
        f.row(2, r[1])                                   # 모자 아랫단 그림자
    s.f('head', 'top', 'outer').fill(r[4])
    bk = s.f('head', 'back', 'outer')                    # 술
    bk.rect(3, 3, 4, 5, r[2]); bk.row(5, r[1], 3, 4)


def veilcap(s, r, seed=0):
    """여성 딜러의 머릿수건 — 페즈와 같은 색이되 뒤통수와 목까지 감싼다."""
    for fname in ('right', 'left', 'back'):
        s.f('head', fname, 'outer').rect(0, 0, 7, 6, r[3])
    f = s.f('head', 'front', 'outer')
    f.rect(0, 0, 7, 1, r[3])
    for x in (0, 7):
        f.rect(x, 2, x, 6, r[2])
    f.row(1, r[1])
    s.f('head', 'top', 'outer').fill(r[4])


def turban(s, r, seed=0):
    for i in range(2):
        tone = r[4] if i % 2 == 0 else r[2]
        for fname in ('front', 'right', 'left', 'back'):
            s.f('head', fname, 'outer').row(i, tone)
    s.f('head', 'top', 'outer').fill(r[3])
    bk = s.f('head', 'back', 'outer')
    bk.rect(2, 2, 5, 3, r[3]); bk.row(3, r[1], 2, 5)


def build(v):
    s = Skin()
    seed = v['cid']
    skin, hair = ramp(v['skin']), ramp(v['hair'])
    tab = ramp(TABLE[v['table']][0], spread=0.46)

    # ---- 얼굴: 제복이 같으니 여기서 사람을 가른다
    g.head_base(s, skin, seed=seed)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=2, back=7 if v.get('female') else 6, seed=seed)
    if v.get('beard'):
        g.beard(s, hair, style=v['beard'], y=6 if v['beard'] == 'mutton' else 5,
                seed=seed, ragged=False)
    if v.get('age'):
        g.wrinkles(s, skin, crow=True, forehead=False)
    g.eyes(s, 'c9c4b8', ramp('3f3226'), y=4, gaze=0, brow=hair[1], brow_y=3)
    f = s.f('head', 'front')
    if v.get('female'):
        f.px(0, 4, skin[1]); f.px(7, 4, skin[1])
        f.rect(3, 6, 4, 6, ramp('8f5248')[2])
    else:
        g.mouth(s, skin, y=6, w=2)
    hd = v.get('head')
    if hd == 'fez':
        fez(s, tab, seed)
    elif hd == 'veilcap':
        veilcap(s, tab, seed)
    elif hd == 'turban':
        turban(s, U['ivory'], seed)

    # ---- 제복: 흰 리넨 셔츠(소매 걷음) → 조끼 → 새시 → 바지
    g.tunic(s, U['shirt'], y0=0, y1=11, collar=True, seed=seed, grain=0.06, hem=False)
    g.sleeves(s, U['shirt'], y0=0, y1=8, seed=seed, grain=0.06)
    for part in ('arm_r', 'arm_l'):                      # 걷어붙인 아래는 맨팔
        s.form_fill(part, skin, 9, 11, base_idx=3)
        s.hem(part, 8, U['shirt'], base_idx=3)
    s.clear_rows('arm_l', 7, 8, layer='base')            # 왼팔만 한 단 더(비대칭)
    s.form_fill('arm_l', skin, 7, 8, base_idx=3)
    s.hem('arm_l', 6, U['shirt'], base_idx=3)
    g.hands(s, skin, rows=2)
    g.pants(s, U['trouser'], y0=0, y1=7, seed=seed)
    g.boots(s, U['boot'], rows=4, toe=True, cuff=False)

    # ★조끼: 앞을 두 패널로 갈라 가운데로 흰 셔츠가 보여야 '조끼'다.
    #   통짜로 덮으면 셔츠가 사라져 그냥 색 튜닉이 된다.
    g.vest(s, tab, y0=0, hem=8, gap=1, seed=seed, buttons=U['brass'])
    s.hem('body', 8, tab, layer='outer', base_idx=3)
    s.folds('body', 2, 7, tab, layer='outer', cols=(1, 6), seed=seed)
    s.folds('body', 2, 7, tab, layer='outer', cols=(2, 5), face='back', seed=seed + 3)

    # 허리 새시 — 조끼와 같은 색 계열이되 한 단 짙게(가로 요소는 이것 하나뿐)
    s.band('body', 9, 9, tab[2], layer='outer')
    s.band('body', 10, 10, tab[1], layer='outer')
    s.f('body', 'front', 'outer').px(5, 11, tab[2])      # 늘어뜨린 끝(비대칭)

    # ---- 소품: 같은 테이블 2~3인을 가르는 마지막 축
    fb = s.f('body', 'front', 'outer')
    p = v['prop']
    if p == 'cards':                                     # 손에 쥔 카드 두 장
        fb.rect(6, 4, 7, 7, U['ivory'][4])
        fb.col(6, U['ivory'][2], 4, 7); fb.row(7, tab[1], 6, 7)
        fb.px(7, 5, tab[3])
    elif p == 'chips':                                   # 쌓인 칩
        for i, y in enumerate((4, 5, 6)):
            fb.rect(6, y, 7, y, U['ivory'][4] if i % 2 else tab[3])
        fb.row(7, tab[1], 6, 7)
    elif p == 'dice':                                    # 주사위 두 알
        fb.rect(6, 5, 7, 6, U['ivory'][4])
        fb.px(6, 5, U['ivory'][1]); fb.px(7, 6, U['ivory'][1])
    elif p == 'ball':                                    # 룰렛 구슬 / 슬롯 손잡이
        fb.px(6, 5, U['ivory'][4]); fb.px(7, 5, U['ivory'][2])
        fb.px(6, 6, U['brass'][3]); fb.px(6, 7, U['brass'][1])

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / f"{v['file']}.png"))


if __name__ == '__main__':
    for k in sys.argv[1:] or VARIANTS:
        print(build(VARIANTS[k]))
