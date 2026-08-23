#!/usr/bin/env python3
"""길가 대여소 NPC 11명 — 마부 5(말 대여, cid 178~182) · 뱃사공 6(배 대여, cid 183~188).

CHARACTER BRIEF
  마을 NPC가 아니다. 좌표를 실측하면 전부 마을에서 60~260칸 떨어진 **길목·물가**에
  혼자 서 있다(스폰마을~왕도 권역 = 바르칸 본섬). 그래서 «시내 상인» 이 아니라
  «역참에서 말을 돌보는 사람» 과 «선착장에서 배를 대는 사람» 이다. 대사는 없고
  역할 플래그(horseRental/boatRental)와 서 있는 자리가 컨셉 전부다.
  이름은 본섬 관례대로 독일계. 기존 NPC 170여명과 전부 다른 이름을 골랐다.

DESIGN SPEC — 왜 이 실루엣인가
  기존 남성 변형 80개의 garb 분포를 실측했다: tunic 16 · apron 16 · coat 13 ·
  jerkin 9 · robe 4 · thobe계 8 · smock 3 · wrap 3. **vest·suspenders·gloves 는
  아무도 안 쓴다.** 그래서 대여소는 그쪽으로 잡아 마을 사람들과 실루엣부터 갈린다.

  ┌ 마부 (5명) ─ 가죽 조끼 + 멜빵 + 장갑 + 승마 장화
  │  실루엣  속옷 셔츠 → outer 가죽 조끼 → 멜빵(허리 위로) → 무릎 위 장화 5행
  │          → 장갑 3행(고삐를 쥐는 손) → 허리에 굴레 파우치
  │  팔레트  ★«전부 가죽 갈색» 은 1차 시도에서 다양성 게이트 7건 실패했다
  │          (갈색·무채 100% / 유채 0% / 어두운옷 0% / 머리색 3종 / 피부 색상각 5°).
  │          통과 세트(tf_* 37명)의 기준선은 어두운옷 22% · 밝은옷 19% · 유채 41% ·
  │          갈색무채 35% · 머리색 5종이다. 그래서 가죽도 염색·풍화로 갈랐다:
  │          안장갈색 / **붉은 벽돌** / 거의 검정 / 밝은 아마셔츠 / **청회색**.
  │          악센트=놋쇠 버클 1곳뿐(ramp_lit).
  │  비대칭  한쪽 소매만 걷음 / 무릎 패치는 한쪽만 / 파우치는 오른허리
  │  얼굴    눈동자 안쪽(기본) · 코 없음(기본) · 수염은 사람마다 다르게
  └
  ┌ 뱃사공 (6명) ─ 기름옷 + 밧줄 허리 + 밧줄 코일
  │  실루엣  속옷 셔츠 → outer 교차 기름옷(wrap_tunic) → 허리 밧줄(sash)
  │          → 걷어올린 바지 + 짧은 장화 3행 → **가슴에 밧줄 코일(컴팩트 덩어리)**
  │  팔레트  기름옷은 방수 처리에 따라 색이 갈린다: **타르 검정** / **인디고** /
  │          **청록** / 캔버스 회갈 / 바랜 밝은 캔버스. 밧줄=마닐라 삼색.
  │  비대칭  밧줄을 한쪽 어깨로 넘김(bandolier) / 한쪽 바지만 더 걷음
  │  ★노(oar)를 대각으로 얹지 않는다 — lessons.md 9장: 대각선이 평평해져
  │    «베이지색 수직 띠» 로 읽혀 폐기된 전례가 있다. 덩어리(코일)만 읽힌다.
  └

  개인차는 «색만 교체» 가 아니라 다음 축으로 준다:
    나이(주름·수염) · 머리 스타일 5종 · 수염 4종 · 표식 5종 · 겉옷 색 · 표면 처리
    (seams/patchwork/trim/patch) · 모자 유무 · 소매 걷기 방향 · 홍채색

★결정성: seed 는 zlib.crc32(이름) — hash() 를 쓰면 프로세스마다 달라진다(lessons 12장).
"""
import pathlib
import sys
import zlib

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))
import garments as g                                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit                  # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'

BRASS = ramp_lit('9a7b3c')          # 유일한 금속 악센트 — ramp_lit 은 금속만(lessons 19장)

# ── 마부 5명 ────────────────────────────────────────────────────────────────
STABLE = {
    'ws_joachim': dict(
        file='ws_joachim', label='요아힘 — 왕도 서편 역참', cid=178,
        skin='c69874', hair='4a3a2c', hairstyle='crop', beard='mutton',
        leather='6f5136', shirt='b9b09a', pants='4f4a41', boot='3d3229',
        glove='5b4230', iris='brown', head=None, marks='ruddy',
        surface='seams', rolled=None, patch='leg_l', age=False, top='vest'),
    'ws_dietmar': dict(
        file='ws_dietmar', label='디트마르 — 왕도 남서 역참', cid=179,
        skin='9c7a52', hair='3f3831', hairstyle='sidepart', beard='stubble',
        leather='8a3f34', shirt='a85a48', pants='4a443c', boot='4a3c30',
        glove='6e5238', iris='hazel', head='cap', felt='4a443c', marks=None,
        surface=None, rolled='l', patch=None, age=True, top='sus'),
    'ws_bernd': dict(
        file='ws_bernd', label='베른트 — 북로 역참', cid=180,
        skin='e0a894', hair='8f4a2c', hairstyle='shaggy', beard='stubble',
        leather='33302b', shirt='4a4740', pants='565049', boot='47392f',
        glove='4d3a2b', iris='dark', head=None, marks='scar',
        surface='patchwork', rolled=None, patch='leg_r', age=False, top='vest'),
    'ws_jost': dict(
        file='ws_jost', label='요스트 — 북로 갈림길 역참', cid=181,
        skin='9d8a63', hair='d9bb63', hairstyle='slick', beard='goatee',
        leather='c9b48a', shirt='e6e0cc', pants='474139', boot='433629',
        glove='63492f', iris='amber', head='cap', felt='6b5f4a', marks='mole',
        surface='seams', rolled=None, patch='leg_l', age=False, top='sus'),
    'ws_kaspar': dict(
        file='ws_kaspar', label='카스파르 — 스폰마을 역참', cid=182,
        skin='c2926a', hair='9a938a', hairstyle='bald', beard='full',
        leather='3c5a6e', shirt='8a97a3', pants='4b453d', boot='47392f',
        glove='55402e', iris='grey', head=None, marks='sunken',
        surface=None, rolled='l', patch=None, age=True, top='vest'),
}

# ── 뱃사공 6명 ──────────────────────────────────────────────────────────────
BOAT = {
    'ws_matthis': dict(
        file='ws_matthis', label='마티스 — 왕도 서편 선착장', cid=183,
        skin='c08f66', hair='3a3228', hairstyle='crop', beard='stubble',
        oil='102133', shirt='183048', pants='514a40', boot='46392f',
        rope='9c8256', iris='blue', head=None, marks='ruddy',
        surface='seams', rolled='r', bare=False, age=False),
    'ws_thilo': dict(
        file='ws_thilo', label='틸로 — 왕도 남서 선착장', cid=184,
        skin='d5b596', hair='b5793a', hairstyle='shaggy', beard=None,
        oil='123a5c', shirt='1a5182', pants='585043', boot=None,
        rope='a88b5c', iris='green', head='cap', felt='6e6656', marks='freckles',
        surface=None, rolled='l', bare=True, age=False),
    'ws_jens': dict(
        file='ws_jens', label='옌스 — 북로 선착장', cid=185,
        skin='7a5230', hair='3d352c', hairstyle='sidepart', beard='goatee',
        oil='0a3d28', shirt='18563a', pants='463f38', boot='45392f',
        rope='94794f', iris='dark', head=None, marks=None,
        surface='trim', rolled='r', bare=False, age=False),
    'ws_gerold': dict(
        file='ws_gerold', label='게롤트 — 북로 갈림길 선착장', cid=186,
        skin='a97f5a', hair='7d6a4c', hairstyle='slick', beard='mutton',
        oil='10514c', shirt='1f6b64', pants='554d42', boot='40352c',
        rope='9f8455', iris='amber', head='cap', felt='5f5a4e', marks='mole',
        surface='seams', rolled=None, bare=False, age=True),
    'ws_arnd': dict(
        file='ws_arnd', label='아른트 — 스폰마을 선착장', cid=187,
        skin='c59468', hair='4f4034', hairstyle='crop', beard='full',
        oil='8a8470', shirt='c4bda8', pants='4e463c', boot='46392f',
        rope='a08453', iris='hazel', head=None, marks='scar',
        surface='patchwork', rolled='l', bare=False, age=False),
    'ws_hubert': dict(
        file='ws_hubert', label='후베르트 — 남안 선착장', cid=188,
        skin='c9ac9a', hair='a09789', hairstyle='bald', beard='full',
        oil='3d5a75', shirt='6b7d8e', pants='5a5147', boot='3d342c',
        rope='8f7549', iris='grey', head=None, marks='sunken',
        surface=None, rolled='r', bare=True, age=True),
}

VARIANTS = {}
for _k, _v in STABLE.items():
    _v['kind'] = 'stable'; VARIANTS[_k] = _v
for _k, _v in BOAT.items():
    _v['kind'] = 'boat'; VARIANTS[_k] = _v


def _face(s, v, seed, skin, hair):
    """얼굴 — 기본값(눈동자 안쪽 gaze=0 · 코 생략)을 지킨다."""
    g.head_base(s, skin, seed=seed)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=2 if v['hairstyle'] != 'bald' else 0, back=6, seed=seed)
    g.male_hair_style(s, hair, skin, style=v['hairstyle'], seed=seed, eye_y=4)
    g.face_shape(s, skin, jaw='square' if v['kind'] == 'stable' else 'long')
    g.eyes(s, 'c9c4b8', ramp(g.IRIS[v['iris']]), y=4, gaze=0, iris_idx=2)
    g.brow(s, hair[1], y=3)
    if v.get('beard'):
        g.beard(s, hair, style=v['beard'], y=5, seed=seed)
    g.mouth(s, skin, y=6, w=2)
    if v.get('age'):
        g.wrinkles(s, skin, brow_y=2, crow=True, forehead=True)
    if v.get('marks'):
        g.face_marks(s, skin, kind=v['marks'], seed=seed)


def build(v):
    seed = zlib.crc32(v['file'].encode()) % 100000
    skin = ramp(v['skin'])
    hair = ramp(v['hair'])
    s = Skin()
    _face(s, v, seed, skin, hair)
    if v.get('head') == 'cap':
        # ★모자 색을 겉옷 램프로 쓰면 안 된다 — 디트마르가 모자·멜빵·셔츠 전부
        #   꼭두서니 빨강이 되어 «빨간 운동복» 으로 읽혔다(렌더 실측). 중립 펠트로 뗀다.
        g.cap(s, ramp(v.get('felt', '5a5248')), crown=3, seed=seed)

    shirt = ramp(v['shirt'])
    pants = ramp(v['pants'])
    g.tunic(s, shirt, y0=0, y1=11, collar=True, seed=seed, grain=0.09)
    g.sleeves(s, shirt, y0=0, y1=11, seed=seed, grain=0.09,
              rolled=v.get('rolled'), skin_r=skin)

    if v['kind'] == 'stable':
        # ── 마부: 가죽 조끼 + 멜빵 + 장갑 + 승마 장화
        hide = ramp(v['leather'])
        g.pants(s, pants, y0=0, y1=11, seed=seed, grain=0.08)
        g.boots(s, ramp(v['boot']), rows=5, cuff=True)          # 무릎 위 승마 장화
        g.gloves(s, ramp(v['glove']), rows=3, cuff=True)        # 고삐 쥐는 손
        # ★조끼와 멜빵을 동시에 주면 안 된다 — 둘 다 같은 가죽 램프 outer 라
        #   멜빵 끈이 조끼에 묻혀 완전히 사라진다(아틀라스 실측: 놋쇠 버클만 보였다).
        #   사람마다 하나만 준다 → 5명 안에서 실루엣이 두 갈래로 갈리는 효과도 있다.
        if v.get('top') == 'vest':
            g.vest(s, hide, y0=0, hem=8, gap=2, seed=seed)
        else:
            g.suspenders(s, hide, cols=(1, 6), waist=8, dropped=None, buckle=BRASS)
        g.belt(s, hide, y=8, accent=BRASS, buckle=True)
        g.pouch(s, hide, part='leg_r', face='front', x=0, y=2, w=2, h=3,
                flap=True, metal=BRASS)                      # 굴레 주머니
        if v.get('patch'):
            g.patch(s, v['patch'], 'front', pants, 1, 4, w=2, h=2)
        if v.get('surface') == 'seams':
            g.seams(s, 'body', hide, y0=0, y1=8)
        elif v.get('surface') == 'patchwork':
            g.patchwork(s, 'body', hide, y0=0, y1=8, seed=seed)
    else:
        # ── 뱃사공: 기름옷 + 밧줄 허리 + 밧줄 코일
        oil = ramp(v['oil'])
        rope = ramp(v['rope'])
        # 걷어올린 바지 — 종아리를 비워 «물에 들어가는 사람» 으로 읽히게
        legrows = 7 if v.get('bare') else 9
        g.pants(s, pants, y0=0, y1=legrows, seed=seed, grain=0.08)
        for part in ('leg_r', 'leg_l'):
            s.form_fill(part, skin, legrows, 11, base_idx=3, bottom=True)
        if v.get('boot'):
            g.boots(s, ramp(v['boot']), rows=3, cuff=True)
        g.hands(s, skin, rows=2)
        g.wrap_tunic(s, oil, y0=0, hem=10, seed=seed, cross=4, lining=None)
        g.sash(s, rope, y=7, drop=2, layer='outer')                            # 허리 밧줄
        # ★bandolier(어깨끈)는 폐기했다 — 몸통 중앙에 «세로 한 줄» 이 생겨 지퍼로
        #   읽혔다(렌더 실측). lessons 9장의 «노가 수직 띠로 읽힌» 것과 같은 실패다.
        #   밧줄은 «한쪽으로 몰린 덩어리» 로만 읽힌다.
        fr = s.f('body', 'front', 'outer')
        cx = 5 if v.get('rolled') != 'l' else 1                  # 비대칭 — 좌우 반대편
        for _y in (4, 5, 6):
            fr.row(_y, rope[3], cx, cx + 2)
        fr.row(5, rope[4], cx, cx + 2)                           # 가운데 감긴 줄이 밝게
        fr.px(cx, 4, rope[1]); fr.px(cx + 2, 6, rope[1])         # 테두리 어둡게 = 덩어리감
        if v.get('surface') == 'seams':
            g.seams(s, 'body', oil, y0=0, y1=10)
        elif v.get('surface') == 'trim':
            # ★가로 줄무늬는 금지(오너 지시, 라이브러리가 ValueError 로 막는다).
            #   기름옷엔 «밑단 띠» 가 맞다 — 반복이 아니라 한 줄이므로 줄무늬로 안 읽힌다.
            g.trim(s, oil, part='body', rows=(9,), base_idx=1)
        elif v.get('surface') == 'patchwork':
            g.patchwork(s, 'body', oil, y0=0, y1=10, seed=seed)

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / (v['file'] + '.png')))


if __name__ == '__main__':
    for k in sys.argv[1:] or VARIANTS:
        print(build(VARIANTS[k]))
