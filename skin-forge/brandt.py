#!/usr/bin/env python3
"""브란트 — &b[길드] 브란트, 왕도 성 안 길드 연락 담당, citizensId 118.

CHARACTER BRIEF
  대사   "성 안 길드 연락 담당이오." / "길드에 볼 일이 있으면 말하시오."
  역할   길드 관리인 = 문서와 전달을 다루는 궁정 실무 문관. 병사도 상인도 아니다.
  구스킨 ★흰 토브 + 빨간 체크 케피예 = 사막 복장이 왕도 한복판에.
         지역-테마 규칙을 가장 크게 어기고 있던 스킨 중 하나.

DESIGN SPEC
  나이/체격  40대, 단정한 문관
  실루엣     무릎 위 더블릿 + ★어깨 서류가방(길드 문서) + 허리 인장주머니 + 챙 없는 모자
             (위병=판금, 전령=제복+금술, 알브레히트=승마가죽 → 문관은 '가방'으로 구분)
  팔레트     더블릿=짙은 녹청 / 셔츠=크림 / 가방·벨트=갈색 가죽
             ★왕도 소속 표시는 진홍 띠 한 줄만 — 전령(파랑+금)·국왕(진홍+금)과 겹치지 않게
             녹청을 주력으로. 악센트는 놋쇠 잠금 한 곳
  비대칭     서류가방이 한쪽 어깨 + 오른 허리 인장주머니 + 왼소매 커프만 접힘
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 짧게 다듬은 수염 · 검은 머리
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))
import garments as g                      # noqa: E402
from skinlib import Skin, ramp            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 118
P = dict(skin=ramp('c39a72'), hair=ramp('3f3128'), beard=ramp('55443a'),
         doublet=ramp('2f5a55'), shirt=ramp('c4b89c'), leather=ramp('5c4630'),
         crimson=ramp('8f2b32'), brass=ramp('b08d3c'), iris=ramp('3f4a52'))


def build():
    s = Skin()
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=6, seed=SEED, part_x=2)
    g.beard(s, P['beard'], style='goatee', y=5, seed=SEED)
    s.f('head', 'front').rect(2, 6, 5, 6, P['beard'][2])
    g.wrinkles(s, P['skin'], crow=True, forehead=False)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, brow=P['hair'][2], brow_y=3)
    g.cap(s, P['doublet'], crown=2, brim=False, seed=SEED)

    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, grain=0.06, hem=False)
    g.sleeves(s, P['shirt'], y0=0, y1=9, seed=SEED, grain=0.06)
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['leather'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['leather'], rows=4, toe=True, cuff=True)

    g.vest(s, P['doublet'], y0=0, hem=10, gap=0, seed=SEED, buttons=P['brass'])
    for part in ('arm_r', 'arm_l'):
        s.form_fill(part, P['doublet'], 0, 7, layer='outer', base_idx=3)
        s.hem(part, 7, P['doublet'], layer='outer', base_idx=3)
    s.clear_rows('arm_l', 7, 11, layer='outer')
    s.hem('arm_l', 6, P['doublet'], layer='outer', base_idx=3, lip=False)
    s.f('body', 'front', 'outer').row(0, P['crimson'][3], 2, 5)      # 왕도 소속 진홍 띠

    g.bandolier(s, P['leather'], front_x=2, layer='outer')            # 서류가방 끈
    f = s.f('body', 'front', 'outer')
    f.rect(5, 6, 7, 10, P['leather'][3])                              # ★서류가방
    f.row(6, P['leather'][4], 5, 7); f.row(10, P['leather'][1], 5, 7)
    f.px(6, 8, P['brass'][4])                                         # 놋쇠 잠금
    g.belt(s, P['leather'], y=10, accent=P['brass'], layer='outer')
    g.pouch(s, P['leather'], part='leg_r', face='front', x=1, y=2, w=2, h=3,
            metal=P['brass'])                                          # 인장주머니
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'brandt.png'))


if __name__ == '__main__':
    print(build())
