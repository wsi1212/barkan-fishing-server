#!/usr/bin/env python3
"""역할 공백을 메우는 NPC 6명 — ops/audit-npc-roles.py 가 찾아낸 마을×역할 구멍.

CHARACTER BRIEF
  마을 4곳의 역할 행렬을 실측해 나온 확실한 공백만 메운다:
      여관    스폰✓ 사막✓ 상단✓ 왕도✗  → 아그네스 (왕도)
      퀘스트  스폰✓ 사막✗ 상단✓ 왕도✓  → 바시르   (사막)
      유저마켓 스폰✓ 사막✗ 상단✗ 왕도✓  → 살리마(사막) · 엘레나(상단)
      말 대여  스폰✓ 사막✗ 상단✗ 왕도✓  → 타미르(사막) · 베르나르도(상단)
  회복(힐데)·섬상점(브루노)·페리(페리선장)·감정(사피르)·카지노는 단독 배치가
  설계로 보여 건드리지 않았다.
  이름은 마을 관례대로 — 사막=아랍계, 상단=이탈리아계, 왕도=독일계. 기존 180여명과
  전부 다른 이름.

DESIGN SPEC
  ┌ 아그네스 — &b[여관] 왕도, 여성
  │  기존 여관 주인 3명(루드비히·라시드·지오반니)이 **전부 남성**이라 여성으로 변주.
  │  실루엣  커틀 + 앞치마 + 허리 열쇠 꾸러미. 두건은 «여관=부엌 인접» 근거가 있어 허용
  │          (머리쓰개는 역할 근거 있는 사람만 — lessons 5-2)
  │  팔레트  커틀=이끼 / 앞치마=표백 아마 / 속=오트 / 열쇠=놋쇠 1곳
  ├ 바시르 — &b[퀘스트] 사막, 남성
  │  실루엣  로브 + 머리스카프(끈) + 허리 두루마리 파우치. 현자(로브+후드)·촌장과 갈린다
  │  팔레트  로브=모래 회갈 / 스카프=흰 아마 / 띠=대추야자
  ├ 살리마 — &b[유저마켓] 사막, 여성
  │  실루엣  하이웨이스트 + 베일 + 목걸이. 사막 여성은 베일 근거가 있다
  │  팔레트  상의=인디고 / 치마=모래 / 베일=흰
  ├ 엘레나 — &b[유저마켓] 상단, 여성
  │  실루엣  커틀 + 목걸이 + 팔찌 + **긴 머리(머리쓰개 없음)** — 상단은 도시라 맨머리
  │  팔레트  커틀=자두 / 속=크림. ★프리다가 꼭두서니라 붉은계는 피했다
  ├ 타미르 — &b[말 대여] 사막, 남성
  │  실루엣  짧은 로브 + 스카프 + **장갑**(고삐) + 굴레 파우치
  │  팔레트  로브=낙타 / 스카프=적갈
  └ 베르나르도 — &b[말 대여] 상단, 남성
     실루엣  가죽 조끼 + 장갑 + 승마 장화. 길가 마부(wayside)와 같은 계열이되
             상단 도시풍이라 옷감이 좋다(셔츠 밝음·조끼 올리브)
     팔레트  조끼=올리브 가죽 / 셔츠=크림

★얼굴 기본값 준수: 눈동자 안쪽(gaze=0) · 코 생략 · 여성은 2행 눈 eye_y=5(잉가 기준).
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


def _seed(name):
    return zlib.crc32(name.encode()) % 100000


def _male_face(s, skin, hair, iris, jaw, beard=None, marks=None, age=False, seed=0,
               style='crop'):
    g.head_base(s, skin, seed=seed)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=2, back=6, seed=seed)
    g.male_hair_style(s, hair, skin, style=style, seed=seed, eye_y=4)
    g.face_shape(s, skin, jaw=jaw)
    g.eyes(s, 'c9c4b8', ramp(g.IRIS[iris]), y=4, gaze=0, iris_idx=2)
    g.brow(s, hair[1], y=3)
    if beard:
        g.beard(s, hair, style=beard, y=5, seed=seed)
    g.mouth(s, skin, y=6, w=2)
    if age:
        g.wrinkles(s, skin, brow_y=2, crow=True, forehead=True)
    if marks:
        g.face_marks(s, skin, kind=marks, seed=seed)


def _female_face(s, skin, hair, iris, jaw, lip, marks=None, age=False, seed=0):
    g.head_base(s, skin, seed=seed)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=2, back=8, seed=seed)
    g.face_shape(s, skin, jaw=jaw)
    # ★여성 눈높이는 잉가 기준 eye_y=5 (오너 지시 2026-08-22)
    g.female_eyes_big(s, 'c9c4b8', ramp(g.IRIS[iris]), skin, hair,
                      eye_y=5, gaze=0, iris_idx=3)
    g.brow(s, hair[1], y=3)
    s.f('head', 'front').rect(3, 7, 4, 7, lip[2])          # 입술은 눈(5·6) 아래
    if age:
        g.wrinkles(s, skin, brow_y=2, crow=True, forehead=True)
    if marks:
        g.face_marks(s, skin, kind=marks, seed=seed)


# ── 1. 아그네스 — 왕도 여관 ────────────────────────────────────────────────
def build_agnes():
    sd = _seed('agnes')
    skin, hair = ramp('d9b492'), ramp('7a6a58')
    moss, linen, oat = ramp('5c6b4a'), ramp('cfc8b4'), ramp('a89878')
    s = Skin()
    _female_face(s, skin, hair, 'green', 'oval', ramp('9b5a52'), marks='ruddy',
                 age=True, seed=sd)
    g.headscarf(s, linen, rows=2, tail=False, seed=sd)     # 여관=부엌 인접 근거
    g.tunic(s, oat, y0=0, y1=11, collar=True, seed=sd, grain=0.08)      # ★base
    g.sleeves(s, oat, y0=0, y1=11, seed=sd, grain=0.08)
    g.kirtle(s, moss, oat, y0=0, hem_row=11, sleeve_to=9, seed=sd,
             neckline='square', waist=7)
    for part in ('leg_r', 'leg_l'):        # ★치마 = 다리 base 를 직접 채운다
        s.form_fill(part, moss, 0, 11, base_idx=3, top=True, bottom=True)
        s.form_fill(part, moss, 0, 10, layer='outer', base_idx=3)
        s.hem(part, 10, moss, layer='outer', base_idx=3)
    g.hands(s, skin, rows=2)
    g.apron(s, linen, bib=(2, 5), bib_y=(2, 6), waist=7, hem=11, straps=True,
            tie=True, seed=sd)
    fr = s.f('leg_r', 'front', 'outer')                    # 열쇠 꾸러미(비대칭)
    fr.rect(1, 2, 2, 3, BRASS[2]); fr.px(1, 4, BRASS[4]); fr.px(2, 4, BRASS[1])
    g.boots(s, ramp('4a3f34'), rows=3, cuff=True)
    g.decollete(s, skin, style='square')
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'gf_agnes.png'))


# ── 2. 바시르 — 사막 퀘스트 게시판 ──────────────────────────────────────────
def build_bashir():
    sd = _seed('bashir')
    skin, hair = ramp('a8794f'), ramp('3d352c')
    robe, scarf, date = ramp('9c8f74'), ramp('d5cfbc'), ramp('6b4a32')
    s = Skin()
    _male_face(s, skin, hair, 'dark', 'narrow', beard='goatee', seed=sd, style='crop')
    g.tunic(s, date, y0=0, y1=11, collar=True, seed=sd, grain=0.08)     # ★base=짙은 속옷
    g.sleeves(s, date, y0=0, y1=11, seed=sd, grain=0.08)
    g.pants(s, robe, y0=0, y1=11, seed=sd, grain=0.08)
    g.robe(s, robe, y0=0, seed=sd, hem_row=11, sleeve_to=10, lining=None)
    g.hands(s, skin, rows=2)
    g.headscarf(s, scarf, rows=3, tail=True, seed=sd, cord=date)
    g.mantle(s, date, front=3, back=8, seed=sd, clasp=BRASS)   # 어깨 망토
    g.belt(s, date, y=7, accent=BRASS, buckle=True, layer='outer')
    g.pouch(s, date, part='leg_l', face='front', x=1, y=2, w=2, h=3,
            flap=True, metal=BRASS)                         # 두루마리 파우치(비대칭)
    g.boots(s, ramp('5a4436'), rows=3, cuff=True)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'gf_bashir.png'))


# ── 3. 살리마 — 사막 유저마켓 ───────────────────────────────────────────────
def build_salima():
    sd = _seed('salima')
    skin, hair = ramp('8f6640'), ramp('443c33')
    indigo, sand, veil = ramp('3a557d'), ramp('bfae8c'), ramp('ddd6c4')
    s = Skin()
    _female_face(s, skin, hair, 'dark', 'narrow', ramp('8a4a4a'), seed=sd)
    g.tunic(s, indigo, y0=0, y1=11, collar=True, seed=sd, grain=0.08)   # ★base=보디스
    g.sleeves(s, indigo, y0=0, y1=11, seed=sd, grain=0.08)
    g.high_waist(s, indigo, sand, band=4, embroider=True)
    for part in ('leg_r', 'leg_l'):        # ★치마 = 다리 base 를 직접 채운다
        s.form_fill(part, sand, 0, 11, base_idx=3, top=True, bottom=True)
        s.form_fill(part, sand, 0, 10, layer='outer', base_idx=3)
        s.hem(part, 10, sand, layer='outer', base_idx=3)
    g.hands(s, skin, rows=2)
    g.headscarf(s, veil, rows=3, tail=True, seed=sd)        # 사막 여성 = 베일 근거
    g.necklace(s, BRASS, style='pendant', y=0)
    g.bracelet(s, BRASS, y=9)
    g.boots(s, ramp('56463a'), rows=2, cuff=False)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'gf_salima.png'))


# ── 4. 엘레나 — 상단 유저마켓 ───────────────────────────────────────────────
def build_elena():
    sd = _seed('elena')
    skin, hair = ramp('c9a077'), ramp('8f4a2c')
    plum, cream = ramp('50354a'), ramp('ddd4bc')
    s = Skin()
    _female_face(s, skin, hair, 'hazel', 'oval', ramp('a05a52'), marks='mole', seed=sd)
    g.tunic(s, cream, y0=0, y1=11, collar=True, seed=sd, grain=0.08)    # ★base
    g.sleeves(s, cream, y0=0, y1=11, seed=sd, grain=0.08)
    g.kirtle(s, plum, cream, y0=0, hem_row=11, sleeve_to=9, seed=sd,
             neckline='scoop', waist=7)
    for part in ('leg_r', 'leg_l'):        # ★치마 = 다리 base 를 직접 채운다
        s.form_fill(part, plum, 0, 11, base_idx=3, top=True, bottom=True)
        s.form_fill(part, plum, 0, 10, layer='outer', base_idx=3)
        s.hem(part, 10, plum, layer='outer', base_idx=3)
    g.hands(s, skin, rows=2)
    g.necklace(s, BRASS, style='beads', y=0)
    g.bracelet(s, BRASS, y=9)
    g.boots(s, ramp('4f3f36'), rows=3, cuff=True)
    g.decollete(s, skin, style='scoop')
    # ★긴 머리는 옷을 다 그린 뒤 outer 로 — 앞에서 보여야 «길다» 가 읽힌다
    g.female_hair_length(s, hair, seed=sd, drop=5, front=True, shoulders=True)
    g.hair_ornament(s, BRASS, kind='pin', seed=sd)          # 머리쓰개 없음 → 장신구로
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'gf_elena.png'))


# ── 5. 타미르 — 사막 말 대여 ────────────────────────────────────────────────
def build_tamir():
    sd = _seed('tamir')
    skin, hair = ramp('b9895c'), ramp('41372c')
    camel, rust, hide = ramp('bfa87e'), ramp('8a4f36'), ramp('6b5136')
    s = Skin()
    _male_face(s, skin, hair, 'amber', 'square', beard='stubble', marks='ruddy',
               seed=sd, style='shaggy')
    g.tunic(s, rust, y0=0, y1=11, collar=True, seed=sd, grain=0.08)     # ★base=적갈
    g.sleeves(s, rust, y0=0, y1=11, seed=sd, grain=0.08)
    g.robe(s, camel, y0=0, seed=sd, hem_row=6, sleeve_to=6, lining=None)  # 짧은 로브
    g.pants(s, ramp('6b6350'), y0=0, y1=11, seed=sd, grain=0.08)
    g.headscarf(s, rust, rows=3, tail=True, seed=sd, cord=hide)
    g.gloves(s, hide, rows=3, cuff=True)                    # 고삐 쥐는 손
    g.belt(s, hide, y=8, accent=BRASS, buckle=True, layer='outer')
    g.pouch(s, hide, part='leg_r', face='front', x=0, y=2, w=2, h=3,
            flap=True, metal=BRASS)                         # 굴레 주머니
    g.boots(s, ramp('56412e'), rows=4, cuff=True)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'gf_tamir.png'))


# ── 6. 베르나르도 — 상단 말 대여 ────────────────────────────────────────────
def build_bernardo():
    sd = _seed('bernardo')
    skin, hair = ramp('a37a52'), ramp('5f4a34')
    olive, cream, boot = ramp('5f6340'), ramp('d5cdb4'), ramp('47382c')
    s = Skin()
    _male_face(s, skin, hair, 'brown', 'long', beard='mutton', seed=sd, style='sidepart')
    g.tunic(s, cream, y0=0, y1=11, collar=True, seed=sd, grain=0.09)
    g.sleeves(s, cream, y0=0, y1=11, seed=sd, grain=0.09)
    g.pants(s, ramp('4f4a3e'), y0=0, y1=11, seed=sd, grain=0.08)
    g.boots(s, boot, rows=5, cuff=True)                     # 승마 장화
    g.gloves(s, ramp('6b4f34'), rows=3, cuff=True)
    g.vest(s, olive, y0=0, hem=8, gap=2, seed=sd)
    g.belt(s, olive, y=8, accent=BRASS, buckle=True)
    g.seams(s, 'body', olive, y0=0, y1=8)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'gf_bernardo.png'))


BUILDS = {
    'gf_agnes': build_agnes, 'gf_bashir': build_bashir, 'gf_salima': build_salima,
    'gf_elena': build_elena, 'gf_tamir': build_tamir, 'gf_bernardo': build_bernardo,
}

if __name__ == '__main__':
    for k in sys.argv[1:] or BUILDS:
        print(BUILDS[k]())
