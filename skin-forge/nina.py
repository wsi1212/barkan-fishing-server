#!/usr/bin/env python3
"""견습 사서 니나 — &a[Q] 견습 사서 니나, 왕도 왕립 대도서관, citizensId 59.

CHARACTER BRIEF
  대사   "견습 사서 니나예요. 대사서님을 도와 물고기 표본을 정리하고 있어요."
         "손이 부족해서… 도와주실래요?"
  퀘스트 표본 수집 · 희귀종 연구 · ★금서의 재료(금서 복원)
  구스킨 ★붉은 장발 + 흰/연두 옷에 하반신이 거의 맨살. 도서관 5인 세트와 완전히 따로 논다.

SET ARCHITECTURE — 왕립 대도서관 6인의 마지막 한 명
  공통  잉크 남보라 가운(474468) + 양피지 안감 + 계급별 케이프 — 45·46·47·50·67과 한 팔레트
  계급  대사서45(긴 케이프+두루마리) > 차석50(짧은 케이프) > 금서고47(후드+열쇠)
        > 필경사46(앞치마+깃펜) > 필경생67(맨 가운, 소매 걷음) > ★니나59(견습, 최말단)
  ★니나를 필경생67과 가르는 축: 여성 · 표본 담당(깃펜이 아니라 표본 상자와 라벨끈)
    · 잉크 대신 소매 토시(견습은 옷을 아껴 입는다) · 땋아 묶은 머리

DESIGN SPEC
  나이/체격  10대 후반. 세트에서 가장 어리고 가장 수수하다 — 금속 악센트 0곳
  실루엣     케이프 없는 맨 가운 + 양팔 리넨 토시 + 허리에 표본 상자 + 뒤로 땋은 머리
  팔레트     가운=세트 공용 잉크 남보라 / 안감·토시=양피지 / 표본 상자=바랜 나무
  비대칭     표본 상자가 한쪽 허리에만 + 오른 토시만 잉크가 배어 있음
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 속눈썹 + 입술 · 주름 없음(어리다)
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 59

# ★도서관 세트 공용 팔레트 — library_staff.py / archivist.py와 값이 같아야 한 세트로 읽힌다
P = dict(
    skin=ramp('d2ab84'),
    hair=ramp('5a4230'),
    gown=ramp_lit('474468'),
    lining=ramp_lit('a8a08e'),
    crate=ramp_lit('8a7050'),
    ink=ramp_lit('2b2f4a'),
    lip=ramp('9b5a52'),
    iris=ramp('4a4a58'),
)


def build():
    s = Skin()

    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=6, seed=SEED, part_x=3)
    g.face_shape(s, P['skin'], jaw='narrow')
    g.face_marks(s, P['skin'], kind='freckles', seed=SEED)
    g.female_eyes_big(s, 'c9c4b8', ramp(g.IRIS['blue']), P['skin'], P['hair'], eye_y=5, gaze=0, iris_idx=2)
    g.brow(s, P['hair'][1], y=3)
    f = s.f('head', 'front')
    f.rect(3, 7, 4, 7, P['lip'][2])                      # 입술
    g.ponytail(s, P['hair'], x0=3, w=2, y0=0, y1=5)      # 뒤로 땋아 묶음

    # ---- base: 팔은 맨살로 깔고 가운이 덮는다(로브는 outer만 채운다)
    for part in ('arm_r', 'arm_l'):
        s.form_fill(part, P['skin'], 0, 11, base_idx=3, top=True, bottom=True)
    g.tunic(s, P['gown'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07, hem=False)
    g.pants(s, P['gown'], y0=0, y1=11, seed=SEED)
    g.robe(s, P['gown'], y0=0, seed=SEED, hem_row=11, sleeve_to=10, lining=P['lining'])
    g.hands(s, P['skin'], rows=1)

    # ★리넨 토시: 견습은 가운을 아껴 입는다. 필경생67의 '걷어올린 소매'와 대비되는 축
    for part in ('arm_r', 'arm_l'):
        s.form_fill(part, P['lining'], 6, 9, layer='outer', base_idx=3)
        s.hem(part, 9, P['lining'], layer='outer', base_idx=3)
        s.speckle(part, P['lining'], 6, 9, layer='outer', density=0.10, seed=SEED)
    for y in (7, 8):                                     # 오른 토시만 잉크가 배었다
        s.f('arm_r', 'front', 'outer').px(1, y, P['ink'][2])

    # 허리 표본 상자(비대칭) — 라벨끈이 위로 이어져야 '매단 것'으로 읽힌다
    fb = s.f('body', 'front', 'outer')
    fb.rect(5, 7, 7, 10, P['crate'][2])
    fb.row(7, P['crate'][4], 5, 7)
    fb.row(10, P['crate'][0], 5, 7)
    fb.col(5, P['crate'][1], 7, 10)
    fb.px(6, 9, P['lining'][4])                          # 상자에 붙인 라벨
    for y in (5, 6):
        fb.px(6, y, P['crate'][1])                       # 어깨끈

    # ★긴 머리 — 반드시 <b>옷·머리쓰개를 다 그린 뒤</b>, 그리고 outer 레이어에.
    #   NPC는 lookclose로 늘 플레이어를 마주보므로 뒷머리는 볼 일이 없다 → 얼굴 옆과
    #   가슴 앞으로 내려와야 '길다'가 읽힌다. 머리쓰개는 함수가 알아서 비켜간다.
    g.female_hair_length(s, P['hair'], seed=SEED)
    # 견습 사서 — 은은한 핀 하나
    g.decollete(s, P['skin'], style='scoop')
    g.hair_ornament(s, P['iris'], kind='pin', seed=SEED)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'nina.png'))


if __name__ == '__main__':
    print(build())
