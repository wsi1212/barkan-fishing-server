#!/usr/bin/env python3
"""왕도 물고기 판매 NPC — 틸만.

CHARACTER BRIEF
  물고기 판매는 스폰 3명(헬가·그레타·오토) · 사막 1(카심) · 상단 2(파올로·루카) 인데
  **왕도만 없었다**(실측: 왕도의 shop 플래그는 라인하르트=부품상점 16종, 궁정상인
  발렌틴=shopItems 0). 판별 기준은 shopItems 개수다 — 물고기 판매는 전부 0(판매 GUI를
  쓰고 품목 목록이 없다), 부품상점은 16~97종을 들고 있다.

  왕도는 «왕실에 납품하는 어물전» 이다. 항구에서 갓 올라온 물건을 다루는 오토와 달리
  성 안 시장에 대는 사람이라 차림이 더 정갈하다.

DESIGN SPEC
  기존 물고기 판매 6명과 실루엣이 겹치지 않게:
      오토            걷어붙인 셔츠 + 방수 가죽 앞치마 + 어부 캡   (남)
      헬가·미아       커틀 + 커치프 + 저울                      (여)
      그레타          오버드레스 + 커치프 + 저울                 (여)
      장터 여인       회청 커틀 + 삼베 앞치마                    (여)
    → 틸만은 **스목 + 코이프 + 가죽 토시**. smock+coif 조합은 아무도 안 쓴다.
  실루엣  속옷 셔츠(오트) → outer 스목(바랜 청회) → 코이프(본)
          → 팔 아래 가죽 토시 4행(생선 다루는 사람의 팔) → 허리 칼집
  팔레트  스목=바랜 청회 / 속=오트 / 토시·칼집=가죽 갈색 / 코이프=본
          ★인접 의복 값을 분리한다(스목과 속옷이 같은 값이면 전신 단색이 된다)
  비대칭  칼집은 오른 허벅지 한쪽만
  악센트  놋쇠 2곳 — 벨트 버클 1 + 칼집 리벳 1

★얼굴 기본값: 눈동자 안쪽(gaze=0) · 코 생략.
★소지품은 3×3 안쪽 덩어리로만 — 세로로 길면 «띠» 가 된다(lessons 9장).
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


def build_tilmann():
    sd = zlib.crc32(b'tilmann') % 100000
    skin, hair = ramp('c99a70'), ramp('5a4a38')
    smock, oat, hide, bone = ramp('62727e'), ramp('bfb39a'), ramp('6b5138'), ramp('d8d2c0')
    s = Skin()
    g.head_base(s, skin, seed=sd)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=2, back=6, seed=sd)
    g.male_hair_style(s, hair, skin, style='crop', seed=sd, eye_y=4)
    g.face_shape(s, skin, jaw='square')
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['blue']), y=4, gaze=0, iris_idx=2)
    g.brow(s, hair[1], y=3)
    g.beard(s, hair, style='stubble', y=5, seed=sd)
    g.mouth(s, skin, y=6, w=2)
    g.face_marks(s, skin, kind='ruddy', seed=sd)

    g.tunic(s, oat, y0=0, y1=11, collar=True, seed=sd, grain=0.09)      # base
    g.sleeves(s, oat, y0=0, y1=11, seed=sd, grain=0.09)
    g.pants(s, ramp('4a4740'), y0=0, y1=11, seed=sd, grain=0.08)
    g.hands(s, skin, rows=2)
    g.smock(s, smock, y0=0, hem=10, yoke=2, seed=sd, grain=0.10)        # outer
    g.gloves(s, hide, rows=4, cuff=True)                                # 가죽 토시
    g.cap(s, bone, crown=2, seed=sd)                                    # 코이프
    g.belt(s, hide, y=8, accent=BRASS, buckle=True, layer='outer')
    g.pouch(s, hide, part='leg_r', face='front', x=1, y=3, w=2, h=3,
            flap=True, metal=BRASS)                                     # 칼집(비대칭)
    g.seams(s, 'body', smock, y0=0, y1=10)
    g.boots(s, ramp('47392f'), rows=4, cuff=True)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'fm_tilmann.png'))


BUILDS = {'fm_tilmann': build_tilmann}

if __name__ == '__main__':
    for k in sys.argv[1:] or BUILDS:
        print(BUILDS[k]())
