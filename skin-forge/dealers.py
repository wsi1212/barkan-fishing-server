#!/usr/bin/env python3
"""사막 도박장 딜러 12인 세트 — 룰렛·홀덤·섯다·블랙잭·쓰리카드·슬롯.

★설계 판단 정정 (2026-08-02)
  1차에서 "카지노가 사막마을에 있으니 사막 팔레트"라며 페즈+조끼로 갈아입혔는데,
  유저 지적으로 되돌린다. 원칙을 잘못 적용했다 —
      **지역이 아니라 업장이 톤을 정한다.**
  그레고르57(중세 왕성 주방)에게서 현대 셰프복을 벗긴 건 장소와 충돌해서였지만,
  카지노는 룰렛·홀덤·슬롯머신이 있는 '의도적으로 현대 장르인 시설'이다.
  그 안의 정장 딜러는 충돌이 아니라 정합이고, 무엇보다 ★턱시도는 '딜러'를
  즉시 읽히게 하는 가장 강한 기호다. 옷은 그 사람의 직업을 말해야 한다.

SET ARCHITECTURE
  공통(하우스 제복)  흰 드레스 셔츠 + 검정 재킷 + 검정 나비타이 + ★소매 가터(크루피어의
                     상징) + 검정 바지. 옆·뒤는 통째로 검정이라 실루엣은 완전한 정장
  변주①테이블  ★정면 조끼 색 = 게임 종류. 검정 재킷 라펠이 액자처럼 감싸므로
               멀리서도 색이 또렷하고, 옆에서 보면 그냥 정장이다
                 룰렛=진홍 / 홀덤=암청 / 섯다=녹 / 블랙잭=자주 / 쓰리카드=황토 / 슬롯=구리
  변주②사람    성별 · 수염 · 나이 · 딜러 바이저(초록 챙) 유무 · 소품(카드/칩/주사위/구슬)
  같은 테이블 2~3인은 ②로만 갈린다 → audit는 --uniform-set으로 돈다.

구스킨 문제였던 것: 12명이 텍스처 9개뿐(31=40, 32=36, 37=41 완전 동일).
  정장 느낌은 되살리되 그 중복만 제거한다.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'

U = dict(
    # 순백 셔츠는 램프 위가 클리핑돼 8x8에서 번진다 — 한 단 내린 흰색
    shirt=ramp_lit('c6bfae', spread=0.42),
    jacket=ramp_lit('26242a', spread=0.38),    # 검정 재킷. [0]이 사실상 검정이 되지 않게 좁힌다
    trouser=ramp_lit('2b2930', spread=0.38),
    shoe=ramp_lit('221f24', spread=0.34),
    brass=ramp_lit('b08d3c', spread=0.48),
    ivory=ramp_lit('c4bba4', spread=0.45),     # 상아 칩·주사위·카드
    visor=ramp_lit('2f6b4a', spread=0.44),     # 딜러 바이저(초록 셀룰로이드 챙)
)
TABLE = dict(
    roulette='8f2f38', holdem='2f3f5c', seotda='35563f',
    blackjack='54304a', threecard='8a6a2c', slot='96552f',
)

VARIANTS = {
    '31': dict(file='d_roulette1', cid=31, table='roulette', prop='ball',
               skin='c98a72', hair='241f1c', beard='goatee', visor=True,
               eye_y=4, iris='dark', jaw='narrow', brow_a=1),
    '35': dict(file='d_threecard1', cid=35, table='threecard', prop='cards',
               skin='b98a5c', hair='a89a6f', beard='stubble', visor=False,
               eye_y=5, iris='grey', jaw='square', marks='scar'),
    '40': dict(file='d_threecard2', cid=40, table='threecard', prop='chips',
               female=True, skin='e0bcae', hair='1b1a24', backhair=8, beard=None, visor=False,
               eye_y=4, iris='green', jaw='oval', cheek=True),
    '32': dict(file='d_holdem1', cid=32, table='holdem', prop='chips',
               skin='946642', hair='241d18', beard='full', visor=True,
               eye_y=3, iris='amber', jaw='narrow', brow_a=1),
    '41': dict(file='d_holdem2', cid=41, table='holdem', prop='cards',
               female=True, skin='cfa47e', hair='c2a052', backhair=8, beard=None, visor=False,
               eye_y=4, iris='hazel', jaw='oval', marks='mole'),
    '33': dict(file='d_seotda1', cid=33, table='seotda', prop='cards',
               skin='9c7146', hair='9a938a', beard='mutton', visor=True, age=True,
               eye_y=4, iris='grey', jaw='long', socket=True),
    '42': dict(file='d_seotda2', cid=42, table='seotda', prop='dice',
               skin='a89055', hair='2f2721', beard='stubble', visor=False,
               eye_y=5, iris='brown', jaw='square', brow_w=2),
    '34': dict(file='d_blackjack1', cid=34, table='blackjack', prop='cards',
               skin='b98a5c', hair='3f3128', beard='goatee', visor=False,
               eye_y=4, iris='blue', jaw='narrow'),
    '38': dict(file='d_blackjack2', cid=38, table='blackjack', prop='chips',
               female=True, skin='b98a5c', hair='8f4a24', backhair=8, beard=None, visor=True,
               eye_y=5, iris='dark', jaw='square', marks='ruddy'),
    '39': dict(file='d_blackjack3', cid=39, table='blackjack', prop='dice',
               skin='9c6b3f', hair='6b6154', beard='full', visor=False, age=True,
               eye_y=3, iris='hazel', jaw='oval', brow_a=-1),
    '36': dict(file='d_slot1', cid=36, table='slot', prop='chips',
               skin='c09468', hair='a05a2a', beard=None, visor=False,
               eye_y=4, iris='green', jaw='narrow', marks='freckles'),
    '37': dict(file='d_slot2', cid=37, table='slot', prop='ball',
               female=True, skin='a87a4e', hair='b8b2a6', backhair=8, beard=None, visor=True,
               eye_y=5, iris='amber', jaw='long', socket=True),
}


def visor(s, r, seed=0):
    """딜러 바이저 — 초록 셀룰로이드 챙 + 이마 밴드.

    ★모자가 아니라 '챙'이라 머리 위(top면)를 덮지 않는다. 이마 1행 밴드 + 그 아래
      1행이 챙이며, 눈(y4)은 절대 침범하지 않는다.
    """
    for fname in ('front', 'right', 'left', 'back'):
        s.f('head', fname, 'outer').row(2, r[2])         # 이마 밴드
    f = s.f('head', 'front', 'outer')
    f.row(3, r[3])                                       # 챙(반투명 초록)
    f.px(0, 3, r[1]); f.px(7, 3, r[1])
    f.px(3, 2, r[4]); f.px(4, 2, r[1])                   # 밴드 조임쇠


def tuxedo(s, v, seed):
    """하우스 제복 — 옆·뒤는 통째로 검정 재킷, 앞만 흰 셔츠 + 게임색 조끼.

    ★이 재단이 요점이다: 실루엣은 완전한 정장인데 정면에서만 테이블 색이 읽힌다.
      조끼를 몸통 전체에 두르면 '색 튜닉'이 되고, 색을 아예 빼면 테이블 구분이 죽는다.
    """
    jk, sh = U['jacket'], U['shirt']
    vest = ramp_lit(TABLE[v['table']], spread=0.46)

    # 재킷: 4면 + 어깨. 뒤는 무늬 없이 통짜(정장의 등판은 매끈하다)
    s.form_fill('body', jk, 0, 11, layer='outer', base_idx=3, top=True)
    s.speckle('body', jk, 0, 11, layer='outer', density=0.06, seed=seed)
    s.folds('body', 2, 10, jk, layer='outer', cols=(2, 5), face='back', seed=seed)

    f = s.f('body', 'front', 'outer')
    # 흰 셔츠 가슴판 + 게임색 조끼 (x2~5). 라펠(x1·x6)은 검정으로 남겨 액자를 만든다
    f.rect(2, 0, 5, 0, sh[4])                            # 칼라
    f.rect(2, 1, 5, 8, vest[3])                          # 조끼
    f.col(2, vest[2], 1, 8); f.col(5, vest[4], 1, 8)     # 조끼 앞단 두께
    f.row(8, vest[1], 2, 5)                              # 조끼 밑단
    for y in (3, 5, 7):                                  # 놋쇠 단추
        f.px(4, y, U['brass'][4]); f.px(4, y + 1, vest[1])
    f.px(2, 1, sh[3]); f.px(5, 1, sh[3])                 # 칼라 끝
    f.rect(3, 1, 4, 1, jk[1])                            # ★검정 나비타이
    f.px(3, 2, jk[0]); f.px(4, 2, jk[2])
    for x in (1, 6):                                     # 라펠 실크(한 단 밝게)
        f.col(x, jk[4], 0, 5)

    # 소매: ★검정 재킷 소매 + 손목에 흰 셔츠 커프 1행.
    #   몸통은 재킷인데 팔만 흰 셔츠면 '재킷 입은 몸 + 셔츠 팔'로 어긋난다(실측 v1).
    #   정장은 어깨부터 손목까지 한 벌로 이어져야 한다.
    for i, part in enumerate(('arm_r', 'arm_l')):
        # ★top=True 필수 — 어깨 윗면(어깨 캡)까지 재킷을 덮는다. 빼먹으면 그 면만 투명해
        #   위에서 내려다볼 때 검정 소매에 구멍이 뚫려 밝은 셔츠가 드러난다(2026-08-04 지적).
        #   딜러는 테이블 뒤에 서서 플레이어가 항상 내려다보는 각도라 가장 잘 보이는 면이다.
        s.form_fill(part, jk, 0, 9, layer='outer', base_idx=3, top=True)
        s.speckle(part, jk, 0, 9, layer='outer', density=0.05, seed=seed + i)
        s.folds(part, 2, 8, jk, layer='outer', cols=(1,), seed=seed + i * 3)
        s.hem(part, 9, jk, layer='outer', base_idx=3)
        s.band(part, 10, 10, sh[4], layer='outer')                # 드러난 셔츠 커프
        s.band(part, 9 + i, 9 + i, jk[1], layer='outer')          # 커프 접힘(좌우 비대칭)



def feminize(s, v, seed):
    """여성 실루엣·옆머리 패스 — townsfolk.feminize와 같은 처방(이 모듈은 townsfolk를
    import하지 않아 중복 정의한다).

    ★2026-08-05 오너 지적("근본적인 원인 중 하나가 여자스킨이 없어"): 그때까지 female=True가
      하던 일은 속눈썹 2px + 입술색뿐이라 여성 NPC가 남성 몸에 옷만 갈아입은 꼴이었다.
      바닐라 모델은 남녀 지오메트리가 같으므로 성별은 '칠해서' 만들어야 한다.
    ★반드시 옷을 다 그린 뒤 호출 — 먼저 부르면 옷이 덮어 무효다.
    """
    if not v.get('female') or v.get('child'):
        return
    g.female_form(s, seed=seed)
    # ★긴 머리 — 얼굴 앞면은 절대 안 건드린다(1차 실패 교훈: female_face가 앞면 x0·x7을
    #   머리로 덮어 얼굴이 6px로 좁아지고 눈이 검은 덩어리가 됐다. garments.female_hair_length
    #   주석 참고). 머리를 통째로 감싸는 머리쓰개면 건너뛴다.
    # ★머리 볼륨(옆·뒤·정수리)은 머리에 아무것도 안 쓴 사람만 — 이 패스는 모자를 그린
    #   뒤에 돌기 때문에 켜면 두건·모자·바이저 crown을 머리카락이 덮어쓴다.
    #   등으로 흘러내리는 길이(shoulders)는 머리쓰개와 무관하므로 항상 준다.
    g.female_hair_length(s, ramp(v['hair']), seed=seed,
                         head_volume=(v.get('head') is None and not v.get('visor')),
                         shoulders=v.get('head') not in ('hood', 'coif', 'veil'))

def build(v):
    s = Skin()
    seed = v['cid']
    skin, hair = ramp(v['skin']), ramp(v['hair'])

    g.head_base(s, skin, seed=seed)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=2, back=7 if v.get('female') else 5, seed=seed,
           part_x=3 if v.get('female') else None)
    if v.get('beard'):
        g.beard(s, hair, style=v['beard'], y=max(v.get('eye_y', 4) + 1, 6 if v['beard'] == 'mutton' else 5),
                seed=seed, ragged=False)
    if v.get('age'):
        g.wrinkles(s, skin, crow=True, forehead=False)
    # ★얼굴 개인차 (2026-08-03) — 전 마을 공통 처방. 눈높이·눈동자색·턱선·눈썹·표식을
    #   사람마다 달리한다. 이걸 안 하면 옷을 아무리 갈라도 '다 비슷하다'가 남는다.
    eye_y = v.get('eye_y', 4)
    g.face_shape(s, skin, jaw=v.get('jaw', 'oval'), cheek=v.get('cheek', False))
    g.face_marks(s, skin, kind=v.get('marks'), seed=seed)
    g.eyes(s, 'c9c4b8', ramp(g.IRIS[v.get('iris', 'brown')]), y=eye_y,
           gaze=v.get('gaze', 0), socket=skin[1] if v.get('socket') else None,
           iris_idx=1 if v.get('iris', 'brown') in ('blue', 'amber', 'hazel', 'grey') else 2)
    g.brow(s, hair[1], y=eye_y - 1, weight=v.get('brow_w', 1), angle=v.get('brow_a', 0))
    if sum(1 for x in (1, 2, 5, 6)
           if max(s.f('head', 'front').get(x, eye_y)[:3]) > 150) < 2:
        raise ValueError(f"{v.get('file', v.get('name'))}: 눈이 지워졌다 (eye_y={eye_y})")
    f = s.f('head', 'front')
    if v.get('female'):
        f.px(0, 4, skin[1]); f.px(7, 4, skin[1])
        f.rect(3, 6, 4, 6, ramp('8f5248')[2])
    else:
        g.mouth(s, skin, y=6, w=2)
    if v.get('visor'):
        visor(s, U['visor'], seed)

    # base: 셔츠 → 바지 → 구두 (base 6면 전부 불투명하게)
    g.tunic(s, U['shirt'], y0=0, y1=11, collar=True, seed=seed, grain=0.05, hem=False)
    g.sleeves(s, U['shirt'], y0=0, y1=11, seed=seed, grain=0.05)
    g.hands(s, skin, rows=1)
    g.pants(s, U['trouser'], y0=0, y1=7, seed=seed)
    g.boots(s, U['shoe'], rows=4, toe=True, cuff=False)

    tuxedo(s, v, seed)
    feminize(s, v, seed)     # ★여성 패스 — 정장 다음, 소품 앞

    # 소품 — 같은 테이블 2~3인을 가르는 마지막 축
    fb = s.f('body', 'front', 'outer')
    tab = ramp_lit(TABLE[v['table']], spread=0.46)
    p = v['prop']
    if p == 'cards':                                     # 부채꼴로 쥔 카드
        fb.rect(6, 4, 7, 7, U['ivory'][4])
        fb.col(6, U['ivory'][2], 4, 7); fb.row(7, tab[1], 6, 7)
        fb.px(7, 5, tab[3])
    elif p == 'chips':                                   # 쌓인 칩
        for i, y in enumerate((4, 5, 6)):
            fb.rect(6, y, 7, y, U['ivory'][4] if i % 2 else tab[3])
        fb.row(7, U['jacket'][1], 6, 7)
    elif p == 'dice':
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
