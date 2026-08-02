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
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 45
# 값 뒤 인라인 주석은 쉼표를 삼켜 구문오류를 낸다 — 주석은 줄 위에
# ★2026-08-01 리워크: 로브 4대 결함(짧은 소매·가로 띠·판때기 자락·침침한 단색) 제거.
#   가운을 한 단 밝게 올리고(3d3a5c→474468) 양피지 안감을 칼라·앞섶·커프에 노출한다.
P = dict(
    skin=ramp('c2a184'),
    # ★백발: 기본 spread로 램프를 뽑으면 위쪽이 클리핑돼 뒤통수가 형광 줄무늬가 된다.
    #   해법은 strands를 끄는 게 아니라(그러면 회색 돌덩이가 된다) 램프를 좁히는 것.
    hair=ramp('948f86', spread=0.30),
    gown=ramp_lit('474468'),
    cape=ramp_lit('2e2b47'),
    lining=ramp_lit('a8a08e'),
    scroll=ramp_lit('bfb49a'),
    brass=ramp_lit('a8863a'),
    iris=ramp('4a4a58'),
)


def build():
    s = Skin()
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    # ★백발에 strands=True를 쓰면 램프 상단이 클리핑돼 뒤통수가 형광 줄무늬가 된다.
    #   단일 톤으로 깔고 반스텝 그레인으로만 결을 준다.
    g.hair(s, P['hair'], fringe=1, back=7, seed=SEED)
    g.beard(s, P['hair'], style='full', y=5, seed=SEED, ragged=False)
    g.wrinkles(s, P['skin'], brow_y=2, crow=True)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, brow=P['hair'][1], brow_y=3)
    g.mouth(s, P['skin'], y=6, w=2, color=P['hair'][1])

    for part in ('arm_r', 'arm_l'):
        s.form_fill(part, P['skin'], 0, 11, base_idx=3, top=True, bottom=True)
    g.tunic(s, P['gown'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07, hem=False)
    # robe()는 다리 outer만 채운다 — base를 안 채우면 다리에 구멍이 뚫린다
    g.pants(s, P['gown'], y0=0, y1=11, seed=SEED)
    g.robe(s, P['gown'], y0=0, seed=SEED, hem_row=11, sleeve_to=10, lining=P['lining'])
    g.hands(s, P['skin'], rows=1)

    # 학위 케이프: 앞은 어깨 곡선으로 끝나고 뒤로 길게 흐른다(가로 직선 금지)
    g.mantle(s, P['cape'], front=4, back=10, seed=SEED, lining=P['lining'],
             clasp=P['brass'], sleeve=3)

    # 소지품은 전부 세로 요소로 — 허리를 두르는 놋쇠 띠(구버전)는 몸을 두 동강 냈다
    # 두루마리는 어두운 가운 위에서 쉽게 형광 막대가 된다 — 중간값으로 깔고
    # 빛나는 픽셀은 왼쪽 모서리 한 줄만
    fr = s.f('body', 'front', 'outer')
    fr.rect(6, 6, 7, 10, P['scroll'][1])
    fr.col(6, P['scroll'][2], 6, 10)
    fr.row(10, P['gown'][0], 6, 7)
    fr.px(6, 8, P['brass'][3])
    for y in (8, 9):                                     # 오른소매 잉크 얼룩(비대칭)
        s.f('arm_r', 'front', 'outer').px(1, y, P['cape'][1])
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'archivist.png'))


if __name__ == '__main__':
    print(build())
