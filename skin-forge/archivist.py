#!/usr/bin/env python3
"""왕립 대사서 — &a[Q] 왕립 대사서, 왕도 왕립 대도서관, citizensId 45.

CHARACTER BRIEF
  퀘스트 대사서의 부탁("학자들은 물고기가 품은 기억을 연구합니다, 표본을 가져다 주세요")
         지워진 낱장("물고기가 품은 기억만이 지워진 진실을 방증합니다")
         → 지워진 기록을 복원하려는 학자. 왕도 지식의 정점이면서 뭔가를 파헤치는 인물.
  구스킨 ★원색 파란 로브 + 분홍 얼굴에 큰 코 + 순백 수염 = '돼지 마법사'로 보임(유저 지적).
         만화 마법사이지 왕립 대사서가 아니다.

DESIGN SPEC
  나이/체격  70대, 등이 굽은 학자
  실루엣     학자 가운 + ★어깨 케이프(학위 복식) + 허리에 매단 두루마리 + 발등 덮는 긴 자락
             (왕도 인물들: 위병=판금, 전령=제복, 브란트=더블릿+가방 → 학자는 '가운+케이프')
  팔레트     가운=잉크 남보라(필사·기록의 색. 전령의 원색 파랑+금과 채도로 갈린다)
             / 케이프=더 짙은 잉크 / 안감·수염=회백 / ★악센트=놋쇠 한 곳(허리 인장)
             ★원색 금지 — 서버 팔레트는 전부 뮤트다
  비대칭     두루마리가 왼쪽 허리에만 + 케이프 자락이 한쪽으로 넘어감 + 오른소매 잉크 얼룩
  얼굴       눈동자 안쪽(기본) · ★코 없음(기본 — 구스킨의 큰 코가 돼지처럼 보인 원인)
             · 긴 회백 수염(순백 금지) · 이마·눈가 주름
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))
import garments as g                      # noqa: E402
from skinlib import Skin, ramp            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 45
# 값 뒤 인라인 주석은 쉼표를 삼켜 구문오류를 낸다 — 주석은 줄 위에
P = dict(
    skin=ramp('c2a184'),
    hair=ramp('a8a49c'),
    gown=ramp('3d3a5c'),
    cape=ramp('2a2841'),
    lining=ramp('9a9488'),
    scroll=ramp('bfb49a'),
    brass=ramp('a8863a'),
    iris=ramp('4a4a58'),
)


def build():
    s = Skin()
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=1, back=7, seed=SEED)
    g.beard(s, P['hair'], style='full', y=5, seed=SEED, ragged=False)
    g.wrinkles(s, P['skin'], brow_y=2, crow=True)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, brow=P['hair'][1], brow_y=3)
    g.mouth(s, P['skin'], y=6, w=2, color=P['hair'][1])

    for part in ('arm_r', 'arm_l'):
        s.form_fill(part, P['skin'], 0, 11, base_idx=3, top=True, bottom=True)
    g.tunic(s, P['gown'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07, hem=False)
    g.robe(s, P['gown'], y0=0, seed=SEED, hem_row=11, sleeve_to=9)
    g.hands(s, P['skin'], rows=2)
    # robe()는 다리 outer만 채운다 — base를 안 채우면 다리에 구멍이 뚫린다
    g.pants(s, P['gown'], y0=0, y1=11, seed=SEED)

    # 어깨 케이프: 학위 복식. 목~가슴 상단을 덮고 등으로 내려간다
    s.form_fill('body', P['cape'], 0, 4, layer='outer', base_idx=3, top=True)
    s.f('body', 'back', 'outer').rect(0, 0, 7, 7, P['cape'][2])
    s.f('body', 'back', 'outer').row(7, P['cape'][1])
    s.f('body', 'front', 'outer').row(4, P['cape'][1])
    s.f('body', 'front', 'outer').row(3, P['lining'][3], 2, 5)
    s.f('body', 'left', 'outer').rect(0, 0, 3, 7, P['cape'][2])
    s.f('body', 'left', 'outer').row(7, P['cape'][1])
    s.speckle('body', P['cape'], 0, 4, layer='outer', density=0.08, seed=SEED)
    for part in ('arm_r', 'arm_l'):
        s.form_fill(part, P['cape'], 0, 2, layer='outer', base_idx=3)
        s.hem(part, 2, P['cape'], layer='outer', base_idx=3)

    fr = s.f('body', 'front', 'outer')
    fr.rect(6, 6, 7, 9, P['scroll'][3])
    fr.row(6, P['scroll'][4], 6, 7)
    fr.row(9, P['scroll'][1], 6, 7)
    fr.px(6, 8, P['brass'][4])
    s.band('body', 5, 5, P['brass'][2], layer='outer')
    for y in (8, 9):
        s.f('arm_r', 'front', 'outer').px(1, y, P['cape'][1])
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'archivist.png'))


if __name__ == '__main__':
    print(build())
