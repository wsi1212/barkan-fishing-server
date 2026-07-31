#!/usr/bin/env python3
"""왕도 위병 4인 세트 — 로타르(60) · 쿠르트(61) · 디터(62) · 오스발트(63).

CHARACTER BRIEF
  전원 왕도 소속. 성문 위병 2명(로타르·쿠르트) + 거리 위병 2명(디터·오스발트).
  구스킨 상태가 제각각으로 망가져 있었다 — 위병으로 읽히는 게 하나도 없었음:
    60 로타르   검정+금 해적/귀족풍 화려한 옷
    61 쿠르트   빨간 후드 + 등에 다이아몬드 검 (게임 캐릭터 스킨)
    62 디터     초록 크리퍼 무늬 + 금 갑옷 (몹 스킨)
    63 오스발트 불투명 340px = 몸이 통째로 투명

SET ARCHITECTURE  (item-icons 스킬의 '한 스펙의 변주'와 같은 구조)
  ★제복은 통일, 사람은 구분. 병사 넷이 각자 다른 옷을 입으면 부대가 아니고,
    픽셀까지 같으면 복붙으로 보인다. 그래서:
      공통(제복) 강철 흉갑 + 진홍 타바드(왕실 문장) + 검은 가죽 벨트 + 강철 그리브
      변주(개인) ①머리 방어구 ②얼굴/나이/수염 ③망토 유무 ④비대칭 소품 ⑤계급 트림
  머리 방어구를 변주의 1축으로 쓰는 이유: 실루엣에서 가장 먼저 읽히는 부위라
  멀리서도 "누가 누구인지" 구분된다.

DESIGN SPEC (공통)
  팔레트   강철=차가운 회청 / 타바드=진홍(왕실) / 가죽=검정 / 금=계급 트림(고참만)
  악센트   금은 고참 2명에게만, 그것도 한 곳씩 — 넷 다 금을 두르면 계급이 안 보인다
  문장     ★엠블럼이 정당한 드문 경우(왕실 소속). 타바드 가슴에 3x3, 넷 모두 동일
  얼굴     눈동자 안쪽(기본) · 코 없음(기본)
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'

U = dict(                                  # 제복 팔레트(전원 공유)
    steel=ramp('7d8896'),                  # 차가운 회청 강철
    tabard=ramp('8f2b32'),                 # 진홍 왕실색
    leather=ramp('35302a'),                # 검은 가죽
    gold=ramp('c2a13f'),
    mail=ramp('5f6772'),                   # 사슬(강철보다 어둡게)
)

CREST = ['.#.',
         '###',
         '.#.']                            # 왕실 문장. 넷 모두 동일해야 '부대'가 된다.
#                                            타바드 폭(6px) 안에서 3x3이면 꽉 차 보이므로
#                                            그림자 없이 얇게만 찍는다

# 변주 표 — 그리기 전에 '누가 어떻게 다른가'를 먼저 선언한다
VARIANTS = {
    '60': dict(name='lothar', cid=60, label='성문 위병 로타르',
               helm='nasal', plume=True, cloak=True, rank=True,
               skin='b58a63', hair='6b6154', beard='mutton', age=True,
               extra='pauldron'),         # 고참 성문지기: 개방투구+붉은깃 + 망토 + 금 견장
    #                              ★면갑(closed)은 눈을 가려 대화 NPC엔 부적합 — 개방형으로
    '61': dict(name='kurt', cid=61, label='성문 위병 쿠르트',
               helm='coif', plume=False, cloak=True, rank=True,
               skin='c39a72', hair='4a3d2f', beard='full', age=False,
               extra='scabbard'),         # 성문지기: 사슬 두건 + 망토 + 허리 검집
    '62': dict(name='dieter', cid=62, label='거리 위병 디터',
               helm=None, plume=False, cloak=False, rank=False,
               skin='a8794f', hair='2f2721', beard='stubble', age=False,
               extra='armband'),          # 순찰: 맨머리(가벼운 복장) + 팔 완장
    '63': dict(name='oswald', cid=63, label='거리 위병 오스발트',
               helm='kettle', plume=False, cloak=False, rank=False,
               skin='cba585', hair='8a7a55', beard=None, age=False,
               extra='kneepatch'),        # 신참: 챙 넓은 철모 + 수염 없음 + 무릎 패치
}


def build(v):
    s = Skin()
    seed = v['cid']
    skin = ramp(v['skin'])
    hair = ramp(v['hair'])

    # ---- 얼굴: 제복이 같으니 여기서 사람을 가른다
    g.head_base(s, skin, seed=seed)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=2, back=6, seed=seed)
    if v['beard']:
        g.beard(s, ramp(v['hair']), style=v['beard'], y=5 if v['beard'] != 'mutton' else 6,
                seed=seed, ragged=False)
    g.wrinkles(s, skin, crow=True, forehead=v['age'] and v['helm'] is None)
    g.eyes(s, 'c9c4b8', ramp('3f4a52'), y=4, gaze=0, brow=hair[2], brow_y=3)
    g.mouth(s, skin, y=6, w=2)

    # ---- 제복(전원 동일)
    g.tunic(s, U['leather'], y0=0, y1=11, collar=True, seed=seed, grain=0.05, hem=False)
    g.sleeves(s, U['leather'], y0=0, y1=9, seed=seed, grain=0.05)
    g.hands(s, skin, rows=2)
    g.pants(s, U['leather'], y0=0, y1=7, seed=seed)
    g.boots(s, U['steel'], rows=4, toe=True, cuff=True)          # 강철 그리브
    for part in ('leg_r', 'leg_l'):
        g.scuff(s, part, U['steel'], 8, 11, layer='base', seed=seed, n=2)
    for i, part in enumerate(('arm_r', 'arm_l')):                # 강철 팔보호대
        end = 3 if (seed + i) % 2 == 0 else 2                    # 길이도 개인차
        s.form_fill(part, U['steel'], 0, end, layer='outer', base_idx=3)
        s.hem(part, end, U['steel'], layer='outer', base_idx=3)
        g.scuff(s, part, U['steel'], 0, end, seed=seed + i, n=2)

    g.cuirass(s, U['steel'], y0=0, y1=8, seed=seed)
    g.tabard(s, U['tabard'], y0=1, hem=11, panel=(1, 6), layer='outer', seed=seed)
    s.motif('body', CREST, 3, 3, U['gold'], layer='outer', shade=False)  # 왕실 문장
    g.belt(s, U['leather'], y=9, accent=U['steel'], layer='outer')

    # ---- 개인 변주
    g.helm(s, U['mail'] if v['helm'] == 'coif' else U['steel'], style=v['helm'],
           seed=seed, plume=U['tabard'] if v['plume'] else None)
    if v['cloak']:                                               # 망토는 성문지기만
        s.f('body', 'back', 'outer').rect(0, 0, 7, 11, U['tabard'][2])
        s.f('body', 'back', 'outer').col(0, U['tabard'][1], 0, 11)
        s.f('body', 'back', 'outer').row(11, U['tabard'][1])
        s.f('body', 'top', 'outer').rect(0, 3, 7, 3, U['tabard'][2])
        for part in ('leg_r', 'leg_l'):                          # 망토 자락
            s.form_fill(part, U['tabard'], 0, 2, layer='outer', base_idx=2)
    # ★금은 1인당 한 곳. 로타르는 견장, 쿠르트는 칼라 트림 — 계급줄까지 겹치면
    #   문장·견장·계급줄로 금이 3곳이 되어 규칙 위반이자 시각적으로 산만해진다.
    if v['rank'] and v['extra'] != 'pauldron':
        s.f('body', 'front', 'outer').row(1, U['gold'][3], 2, 5)
    if v['extra'] == 'pauldron':                                 # 금 견장(한쪽만)
        s.form_fill('arm_r', U['gold'], 0, 1, layer='outer', base_idx=3)
        s.hem('arm_r', 1, U['gold'], layer='outer', base_idx=3)
    elif v['extra'] == 'scabbard':                               # 허리 검집(한쪽)
        f = s.f('body', 'left', 'outer')
        f.rect(1, 6, 2, 11, U['leather'][3])
        f.px(1, 6, U['steel'][4]); f.px(2, 11, U['steel'][2])
    elif v['extra'] == 'armband':                                # 팔 완장(한쪽)
        s.form_fill('arm_l', U['tabard'], 5, 6, layer='outer', base_idx=3)
    elif v['extra'] == 'kneepatch':
        g.patch(s, 'leg_l', 'front', U['leather'], x=1, y=4, w=2, h=2)

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / f"guard_{v['name']}.png"))


if __name__ == '__main__':
    for key in sys.argv[1:] or VARIANTS:
        print(build(VARIANTS[key]))
