#!/usr/bin/env python3
"""프리츠 — &b[퀘스트] 프리츠, 왕도 일감 게시판, citizensId 120.

CHARACTER BRIEF
  대사   "게시판 관리가 제 일입니다." / "오늘의 일감을 확인해보세요."
  기능   quest(일일/주간 게시판 GUI). ★[퀘스트] 태그는 게시판=기능형이지
         퀘스트를 주는 [Q]가 아니다 — 관청 서기로 그려야 한다
  구스킨 ★금발 장발 + 초록 엘프/레인저 복장. 판타지 궁수이지 서기가 아니다.

DESIGN SPEC
  나이/체격  20대 젊은 서기. 왕성 관청의 말단 — 화려할 이유가 없다
  실루엣     무릎 위 짧은 튜닉 + 가죽 벨트 + ★어깨에 두루마리 가방(반돌리에)
             + 팔토시(소매 보호대) + 짧은 갈색 머리
             왕도 인물 차별: 필경생67=잉크 남보라 로브(도서관) /
             프리츠=회청 짧은 튜닉+가방(관청 심부름꾼) — 길이와 실루엣이 다르다
  팔레트     튜닉=회청 / 호스=짙은 올리브회 / 가방·벨트=중간 가죽
             / ★악센트=놋쇠 1곳(가방 걸쇠). 말단 서기에게 금은 안 어울린다
  비대칭     반돌리에가 한쪽 어깨에만 + 오른쪽 허리 가방 + 왼팔만 팔토시
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 수염 없음(젊다) · 잉크 얼룩 1점
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 120

P = dict(
    skin=ramp('c9a077'),
    hair=ramp('5a4634'),
    tunic=ramp_lit('4a5a6b'),
    linen=ramp_lit('b8ae96'),
    hose=ramp_lit('4a4a3c'),
    leather=ramp_lit('6b5440'),
    boot=ramp_lit('3f342a'),
    brass=ramp_lit('b08d3c'),
    ink=ramp_lit('2b2f4a'),
    iris=ramp('4a4034'),
)


def build():
    s = Skin()

    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=3, back=6, seed=SEED, part_x=2)
    g.face_shape(s, P['skin'], jaw='narrow')
    g.face_marks(s, P['skin'], kind='mole', seed=SEED)
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['brown']), y=3, gaze=0, iris_idx=2)
    g.brow(s, P['hair'][1], y=2)
    g.mouth(s, P['skin'], y=6, w=2)

    # ---- base: 리넨 속옷 → 호스 → 장화
    g.tunic(s, P['linen'], y0=0, y1=11, collar=True, seed=SEED, grain=0.06, hem=False)
    g.sleeves(s, P['linen'], y0=0, y1=11, seed=SEED, grain=0.06)
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['hose'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['boot'], rows=4, toe=True, cuff=True)

    # ---- 짧은 튜닉: 허리 아래에서 끝난다(로브가 아니라는 신호)
    g.tunic(s, P['tunic'], y0=0, y1=10, layer='outer', collar=True, seed=SEED,
            grain=0.08)
    s.hem('body', 10, P['tunic'], layer='outer', base_idx=3)
    s.folds('body', 2, 9, P['tunic'], layer='outer', cols=(1, 6), seed=SEED)
    s.folds('body', 2, 9, P['tunic'], layer='outer', cols=(2, 5), face='back',
            seed=SEED + 3)
    for part in ('arm_r', 'arm_l'):
        s.form_fill(part, P['tunic'], 0, 7, layer='outer', base_idx=3)
        s.speckle(part, P['tunic'], 0, 7, layer='outer', density=0.07, seed=SEED)
        s.hem(part, 7, P['tunic'], layer='outer', base_idx=3)

    # 왼팔만 가죽 팔토시(비대칭) — 서기의 소매 보호대
    s.form_fill('arm_l', P['leather'], 8, 10, layer='outer', base_idx=3)
    s.hem('arm_l', 10, P['leather'], layer='outer', base_idx=3)

    # ★어깨 두루마리 가방: 앞 대각 → top면 → 등까지 이어져야 끈으로 읽힌다
    g.bandolier(s, P['leather'], front_x=2, layer='outer')
    fb = s.f('body', 'front', 'outer')
    fb.rect(5, 7, 7, 10, P['leather'][3])
    fb.row(7, P['leather'][4], 5, 7)
    fb.row(10, P['leather'][1], 5, 7)
    fb.px(6, 8, P['brass'][4])                           # 가방 걸쇠 — 유일한 금속
    fb.px(5, 8, P['linen'][4])                           # 삐져나온 두루마리 끝
    g.belt(s, P['boot'], y=9, accent=None, layer='outer')

    s.f('arm_r', 'front', 'outer').px(1, 6, P['ink'][1])  # 소매 잉크 얼룩

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'fritz.png'))


if __name__ == '__main__':
    print(build())
