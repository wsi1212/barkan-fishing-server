#!/usr/bin/env python3
"""섬상점 NPC 3명 — 사막(자이드) · 상단(레나토) · 왕도(볼커).

CHARACTER BRIEF
  섬상점(islandShop)은 지금까지 스폰마을 브루노 한 명뿐이었다(역할 행렬 실측).
  오너 지시로 마을마다 하나씩 둔다. 섬상점이 파는 것은 «섬 확장·가구·작물 한도·
  광산·워프» 이므로 이 사람은 **섬을 꾸며 주는 자재상**이다.

  브루노(스폰)와 안 겹치게: 브루노는 coat + lagoon + prop='rope' + buttons 로
  «섬으로 배를 대는 사람» 이다. 이 셋은 «자재와 도면을 다루는 사람» 으로 잡았다.

DESIGN SPEC
  공통 모티프  **가슴에 멘 도면통** — 3행×3폭 원통 덩어리(어깨끈 없음).
               ★긴 막대(자·측량봉)를 대각으로 얹지 않는다: lessons 9장의 «노가
               베이지 수직 띠로 읽혀 폐기» 와 같은 실패가 된다. 덩어리만 읽힌다.
               놋쇠 악센트는 도면통 마개 1곳뿐.
  ┌ 자이드 — &b[섬상점] 사막, 남성
  │  실루엣  로브 + 머리스카프 + 도면통. 현자(로브+후드)·바시르(로브+망토)와
  │          머리쓰개·소지품에서 갈린다
  │  팔레트  로브=테라코타(사막 세트가 모래톤 과다라 유채로) / 스카프=흰 아마
  ├ 레나토 — &b[섬상점] 상단, 남성
  │  실루엣  가죽 조끼 + 걷은 소매 + 도면통. 도시 상인이라 옷감이 좋다
  │  팔레트  조끼=짙은 청록 / 셔츠=크림. ★베르나르도가 올리브·마르첼로가 버건디라 피함
  └ 볼커 — &b[섬상점] 왕도, 남성
     실루엣  짧은 코트 + 도면통 + 놋쇠 버클. 왕실 인가를 받은 자재상의 관록
     팔레트  코트=짙은 남색 / 셔츠=회백

★얼굴 기본값: 눈동자 안쪽(gaze=0) · 코 생략.
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


def _face(s, skin, hair, iris, jaw, beard=None, marks=None, age=False,
          style='crop', seed=0):
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


def _plan_tube(s, tube, seed, side='r'):
    """도면통 — 어깨끈 + 원통 덩어리. 컴팩트해야 읽힌다(lessons 9장)."""
    # ★어깨끈(bandolier)은 안 쓴다 — 몸통 중앙에 «세로 한 줄» 을 만들어 지퍼로 읽힌다.
    #   뱃사공 6명에서 같은 이유로 뺐다(lessons 9장 계열). 통 덩어리만으로 읽힌다.
    fr = s.f('body', 'front', 'outer')
    x = 5 if side == 'r' else 0
    for y in (4, 5, 6):                          # 3행×3폭 — 세로로 길면 «띠» 가 된다
        fr.row(y, tube[3], x, x + 2)
    fr.row(4, tube[4], x, x + 2)                 # 마개가 밝게
    fr.px(x, 4, BRASS[4])                        # 놋쇠 마개 1점
    fr.px(x + 2, 6, tube[1]); fr.px(x, 6, tube[1])   # 테두리 어둡게 = 덩어리감


# ── 자이드 — 사막 ──────────────────────────────────────────────────────────
def build_zaid():
    sd = _seed('zaid')
    skin, hair = ramp('9c7047'), ramp('3d332b')
    terra, linen, tube = ramp('9c4a33'), ramp('d8d2c0'), ramp('6b5138')
    s = Skin()
    _face(s, skin, hair, 'dark', 'narrow', beard='goatee', marks='ruddy',
          style='crop', seed=sd)
    g.tunic(s, linen, y0=0, y1=11, collar=True, seed=sd, grain=0.09)    # ★base=아마
    g.sleeves(s, linen, y0=0, y1=11, seed=sd, grain=0.09)
    g.pants(s, ramp('7a6b52'), y0=0, y1=11, seed=sd, grain=0.08)
    g.robe(s, terra, y0=0, seed=sd, hem_row=7, sleeve_to=6, lining=None)
    g.hands(s, skin, rows=2)
    g.headscarf(s, linen, rows=3, tail=True, seed=sd, cord=tube)
    g.belt(s, tube, y=7, accent=BRASS, buckle=True, layer='outer')
    _plan_tube(s, tube, sd, side='r')
    g.boots(s, ramp('5a4436'), rows=3, cuff=True)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'is_zaid.png'))


# ── 레나토 — 상단 ──────────────────────────────────────────────────────────
def build_renato():
    sd = _seed('renato')
    skin, hair = ramp('c19a70'), ramp('4a3a2c')
    teal, cream, tube = ramp('1f5a55'), ramp('ddd4bc'), ramp('7a5c3a')
    s = Skin()
    _face(s, skin, hair, 'hazel', 'square', beard='mutton', style='sidepart', seed=sd)
    g.tunic(s, cream, y0=0, y1=11, collar=True, seed=sd, grain=0.09)
    g.sleeves(s, cream, y0=0, y1=11, seed=sd, grain=0.09, rolled='r', skin_r=skin)
    g.pants(s, ramp('4a443c'), y0=0, y1=11, seed=sd, grain=0.08)
    g.hands(s, skin, rows=2)
    g.vest(s, teal, y0=0, hem=8, gap=2, seed=sd)
    g.belt(s, tube, y=8, accent=BRASS, buckle=True)
    g.seams(s, 'body', teal, y0=0, y1=8)
    _plan_tube(s, tube, sd, side='l')
    g.boots(s, ramp('4f3f36'), rows=4, cuff=True)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'is_renato.png'))


# ── 볼커 — 왕도 ────────────────────────────────────────────────────────────
def build_volker():
    sd = _seed('volker')
    skin, hair = ramp('d5b08c'), ramp('8f8579')
    navy, grey, tube = ramp('26364f'), ramp('b5b0a4'), ramp('6b5440')
    s = Skin()
    _face(s, skin, hair, 'grey', 'long', beard='full', marks='sunken',
          age=True, style='slick', seed=sd)
    g.tunic(s, grey, y0=0, y1=11, collar=True, seed=sd, grain=0.09)
    g.sleeves(s, grey, y0=0, y1=11, seed=sd, grain=0.09)
    g.pants(s, ramp('3f3a34'), y0=0, y1=11, seed=sd, grain=0.08)
    g.hands(s, skin, rows=2)
    g.coat(s, navy, y0=0, hem=9, tails=2, seed=sd, lapel=True, center=True)
    g.belt(s, tube, y=8, accent=BRASS, buckle=True, layer='outer')
    # ★놋쇠 버튼(x=4, 행 2·4·6)은 뺐다 — 중앙에 «세로 점선» 이 생기고,
    #   하드룰 «악센트 최대 2곳» 도 깨진다(버튼3 + 버클 + 통 마개).
    #   지금 놋쇠는 버클 1 + 통 마개 1 로 정확히 2곳이다.
    _plan_tube(s, tube, sd, side='r')
    g.boots(s, ramp('433629'), rows=4, cuff=True)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'is_volker.png'))


BUILDS = {'is_zaid': build_zaid, 'is_renato': build_renato, 'is_volker': build_volker}

if __name__ == '__main__':
    for k in sys.argv[1:] or BUILDS:
        print(BUILDS[k]())
