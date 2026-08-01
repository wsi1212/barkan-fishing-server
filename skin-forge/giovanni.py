#!/usr/bin/env python3
"""조반니 — &a[Q] 화물지기 조반니, 상단마을(은빛 갈매기호), citizensId 54.

CHARACTER BRIEF
  대사   "적재실 물건엔 손대지 마시오!" / "이 배의 짐은 전부 내 장부에 있소."
         ★"전부... 전부는 아니지만. 아니, 전부요. 전부."
  퀘스트 바다에 버린 열쇠(무서워서 열쇠를 바다에 던졌다는 실토) · 상자 속의 인장
         → 뭔가를 숨기고 있는 초조한 실무 관리인. 마르코(부유한 무역상)와 같은 마을이지만
           계층이 다르다 — 이쪽은 장부와 창고를 지키는 사람.
  구스킨 658/2048px 레거시 = 몸 대부분이 투명(A급).

DESIGN SPEC
  나이/체격  40대, 마르고 신경질적
  실루엣     소매 걷은 셔츠 + 가죽 조끼 + ★어깨 크로스백(장부) + 허리에 ★빈 열쇠고리
             (열쇠를 바다에 던졌다는 서사를 소품 하나로 박아둔다)
  팔레트     셔츠=회녹 / 조끼=갈색 가죽 / 가방=짙은 가죽. 같은 마을 마르코=버건디,
             알도=머스터드와 겹치지 않게 채도 낮은 쪽으로
  비대칭     크로스백이 한쪽 어깨 + 빈 열쇠고리는 오른 허리 + 왼소매만 걷음
  얼굴       ★gaze=-1 곁눈질 — 기본은 안쪽(gaze=0)이지만 "전부는 아니지만"이라고 말을
             흐리는 인물이라 시선을 피하는 게 캐릭터 그 자체다(규칙의 정당한 예외)
             · 코 없음(기본) · 짧은 스터블 · 눈밑 그늘
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))
import garments as g                      # noqa: E402
from skinlib import Skin, ramp            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 54
P = dict(skin=ramp('c09873'), hair=ramp('4a3f33'), shirt=ramp('96a094'),   # 조끼(갈색)와 값이 붙으면 조끼가 안 보인다
         vest=ramp('6b543a'), bag=ramp('44372a'), iron=ramp('8a8e93'), iris=ramp('4a4034'))


def build():
    s = Skin()
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=6, seed=SEED, part_x=1)
    g.beard(s, P['hair'], style='stubble', y=5, seed=SEED)
    g.wrinkles(s, P['skin'], crow=True, forehead=False)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=-1, brow=P['hair'][2], brow_y=3)  # 곁눈질
    s.f('head', 'front').px(1, 5, P['skin'][1]); s.f('head', 'front').px(6, 5, P['skin'][1])
    g.mouth(s, P['skin'], y=6, w=2)

    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, grain=0.08, hem=False)
    g.sleeves(s, P['shirt'], y0=0, y1=9, rolled=('arm_l', 6), skin_r=P['skin'],
              seed=SEED, grain=0.08)
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['bag'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['bag'], rows=4, toe=True, cuff=True)

    g.vest(s, P['vest'], y0=0, hem=9, gap=2, seed=SEED, buttons=P['iron'])
    g.belt(s, P['bag'], y=9, accent=P['iron'], layer='outer')
    g.bandolier(s, P['bag'], front_x=2, layer='outer')          # 장부 크로스백 끈
    f = s.f('body', 'front', 'outer')
    f.rect(0, 6, 2, 9, P['bag'][3])                              # 가방 몸체(한쪽 허리)
    f.row(6, P['bag'][4], 0, 2); f.row(9, P['bag'][1], 0, 2)
    f.px(1, 7, P['iron'][4])                                     # 걸쇠
    for x, y in ((6, 8), (7, 9), (6, 10)):                       # ★빈 열쇠고리
        f.px(x, y, P['iron'][3])
    f.px(7, 8, P['iron'][1])
    g.patch(s, 'leg_r', 'front', P['bag'], x=1, y=4, w=2, h=2)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'giovanni.png'))


if __name__ == '__main__':
    print(build())
