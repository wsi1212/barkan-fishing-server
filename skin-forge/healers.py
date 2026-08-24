#!/usr/bin/env python3
"""회복 NPC 3명 — 사막(자흐라) · 상단(비앙카) · 왕도(오트마르).

CHARACTER BRIEF
  회복(heal)은 힐데 하나뿐이었다 — 스펙에는 «왕도 궁정 치료사» 로 적혀 있는데 실제로는
  스폰마을(432,826)에 서 있다. 오너 지시로 마을마다 하나씩 둔다.

  힐데와 안 겹치게: 힐데는 슬레이트 로브 + 흰 앞치마 + 두건 + 어깨 약초가방 + 붕대
  두루마리다. 이 셋은 «약을 짓는 사람» 을 각자 다른 매개로 표현한다.

DESIGN SPEC
  ┌ 자흐라 — &b[회복] 사막, 여성
  │  실루엣  하이웨이스트 + 베일 + **허리 약초 다발**. 사막 여성은 베일 근거가 있다
  │  팔레트  보디스=세이지 / 치마=모래 / 베일=본
  ├ 비앙카 — &b[회복] 상단, 여성
  │  실루엣  커틀 + 앞치마 + **허리 유리병 세 개**(컴팩트). 도시 약종상
  │  팔레트  커틀=황토 / 속=크림 / 앞치마=본. ★프리다 꼭두서니·엘레나 자두라 붉은계 피함
  └ 오트마르 — &b[회복] 왕도, 남성
     실루엣  긴 로브 + 코이프 + **가슴 약재 주머니**. 궁정 의관의 관록(백발·주름)
     팔레트  로브=목탄 / 속=본. 힐데의 슬레이트와 값으로 갈린다

★앞선 배치들에서 네 번 밟은 함정을 미리 피한다:
  ① kirtle/robe/high_waist 는 **outer 만** 채운다 → base tunic·sleeves 를 먼저 깔고
    치마는 다리 base 를 form_fill 로 직접 채운다(안 하면 인게임에 구멍).
  ② **인접 의복 값을 반드시 분리**한다(같은 램프로 겹치면 전신 단색이 된다).
  ③ **어깨끈(bandolier)·긴 막대 금지** — 몸통 중앙에 «세로 한 줄» 이 생겨 지퍼로
    읽힌다(lessons 9장). 소지품은 3×3 안쪽 덩어리로만.
  ④ **놋쇠 악센트는 2곳 이하** — 세로로 늘어놓으면 점선이 된다.
★얼굴 기본값: 눈동자 안쪽(gaze=0) · 코 생략 · 여성은 2행 눈 eye_y=5(잉가 기준).
★결정성: seed = zlib.crc32(이름).
"""
import pathlib
import sys
import zlib

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))
import garments as g                                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit                  # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
BRASS = ramp_lit('9a7b3c')


def _seed(n):
    return zlib.crc32(n.encode()) % 100000


def _skirt_legs(s, r):
    """치마 = 다리 base 를 직접 채운다(outer 만 칠하면 구멍이 뚫린다)."""
    for part in ('leg_r', 'leg_l'):
        s.form_fill(part, r, 0, 11, base_idx=3, top=True, bottom=True)
        s.form_fill(part, r, 0, 10, layer='outer', base_idx=3)
        s.hem(part, 10, r, layer='outer', base_idx=3)


def _female_face(s, skin, hair, iris, jaw, lip, marks=None, age=False, seed=0):
    g.head_base(s, skin, seed=seed)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=2, back=8, seed=seed)
    g.face_shape(s, skin, jaw=jaw)
    g.female_eyes_big(s, 'c9c4b8', ramp(g.IRIS[iris]), skin, hair,
                      eye_y=5, gaze=0, iris_idx=3)
    g.brow(s, hair[1], y=3)
    s.f('head', 'front').rect(3, 7, 4, 7, lip[2])
    if age:
        g.wrinkles(s, skin, brow_y=2, crow=True, forehead=True)
    if marks:
        g.face_marks(s, skin, kind=marks, seed=seed)


# ── 자흐라 — 사막 ──────────────────────────────────────────────────────────
def build_zahra():
    sd = _seed('zahra')
    skin, hair = ramp('a3764a'), ramp('42382e')
    sage, sand, bone = ramp('4f6b47'), ramp('c4b48e'), ramp('ddd6c4')
    s = Skin()
    _female_face(s, skin, hair, 'green', 'oval', ramp('8a4a4a'), seed=sd)
    g.tunic(s, sage, y0=0, y1=11, collar=True, seed=sd, grain=0.08)      # base=보디스
    g.sleeves(s, sage, y0=0, y1=11, seed=sd, grain=0.08)
    g.high_waist(s, sage, sand, band=4, embroider=True)
    _skirt_legs(s, sand)
    g.hands(s, skin, rows=2)
    g.headscarf(s, bone, rows=3, tail=True, seed=sd)
    # 허리 약초 다발 — 3×3 안쪽 덩어리
    fr = s.f('body', 'front', 'outer')
    for y in (6, 7, 8):
        fr.row(y, sage[1], 5, 6)
    fr.px(5, 6, sage[4]); fr.px(6, 8, sage[0])
    g.necklace(s, BRASS, style='pendant', y=0)
    g.boots(s, ramp('56463a'), rows=2, cuff=False)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'hl_zahra.png'))


# ── 비앙카 — 상단 ──────────────────────────────────────────────────────────
def build_bianca():
    sd = _seed('bianca')
    skin, hair = ramp('d3aa82'), ramp('6b4a30')
    ochre, cream, bone = ramp('9c7a2e'), ramp('ddd4bc'), ramp('e2ddce')
    s = Skin()
    _female_face(s, skin, hair, 'hazel', 'narrow', ramp('a05a52'), marks='freckles', seed=sd)
    g.tunic(s, cream, y0=0, y1=11, collar=True, seed=sd, grain=0.08)     # base
    g.sleeves(s, cream, y0=0, y1=11, seed=sd, grain=0.08)
    g.kirtle(s, ochre, cream, y0=0, hem_row=11, sleeve_to=9, seed=sd,
             neckline='scoop', waist=7)
    _skirt_legs(s, ochre)
    g.hands(s, skin, rows=2)
    g.apron(s, bone, bib=(2, 5), bib_y=(2, 6), waist=7, hem=11, straps=True,
            tie=True, seed=sd)
    # 허리 유리병 3개 — 가로로 붙인 컴팩트 덩어리(세로로 늘어놓으면 점선이 된다)
    fr = s.f('body', 'front', 'outer')
    for x in (1, 2, 3):
        fr.px(x, 8, ramp('5c7a6b')[3]); fr.px(x, 9, ramp('5c7a6b')[1])
    fr.px(2, 8, BRASS[4])                                   # 마개 1점
    g.decollete(s, skin, style='scoop')
    g.female_hair_length(s, hair, seed=sd, drop=4, front=True, shoulders=True)
    g.boots(s, ramp('4f3f36'), rows=3, cuff=True)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'hl_bianca.png'))


# ── 오트마르 — 왕도 ────────────────────────────────────────────────────────
def build_otmar():
    sd = _seed('otmar')
    skin, hair = ramp('d0ab86'), ramp('9a938a')
    coal, bone, pouch = ramp('2b2e35'), ramp('d0c9b8'), ramp('6b5440')
    s = Skin()
    g.head_base(s, skin, seed=sd)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=1, back=6, seed=sd)
    g.male_hair_style(s, hair, skin, style='bald', seed=sd, eye_y=4)
    g.face_shape(s, skin, jaw='long')
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['grey']), y=4, gaze=0, iris_idx=2)
    g.brow(s, hair[1], y=3)
    g.beard(s, hair, style='full', y=5, seed=sd)
    g.mouth(s, skin, y=6, w=2)
    g.wrinkles(s, skin, brow_y=2, crow=True, forehead=True)
    g.face_marks(s, skin, kind='sunken', seed=sd)
    g.tunic(s, bone, y0=0, y1=11, collar=True, seed=sd, grain=0.08)      # base
    g.sleeves(s, bone, y0=0, y1=11, seed=sd, grain=0.08)
    g.pants(s, ramp('4a4740'), y0=0, y1=11, seed=sd, grain=0.08)
    g.robe(s, coal, y0=0, seed=sd, hem_row=7, sleeve_to=7, lining=None)
    g.hands(s, skin, rows=2)
    g.cap(s, bone, crown=2, seed=sd)                          # 코이프
    g.belt(s, pouch, y=7, accent=BRASS, buckle=True, layer='outer')
    # 가슴 약재 주머니 — 3×3 덩어리
    fr = s.f('body', 'front', 'outer')
    for y in (3, 4, 5):
        fr.row(y, pouch[3], 5, 7)
    fr.row(3, pouch[4], 5, 7)
    fr.px(5, 5, pouch[1]); fr.px(7, 5, pouch[1])
    g.boots(s, ramp('433629'), rows=3, cuff=True)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'hl_otmar.png'))


BUILDS = {'hl_zahra': build_zahra, 'hl_bianca': build_bianca, 'hl_otmar': build_otmar}

if __name__ == '__main__':
    for k in sys.argv[1:] or BUILDS:
        print(BUILDS[k]())
