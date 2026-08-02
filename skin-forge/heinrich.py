#!/usr/bin/env python3
"""하인리히 — 스폰마을 강가 노인, citizensId 102.

CHARACTER BRIEF  (npc_brief.py 하인리히 --village)
  대사   "나이는 먹었어도 손맛은 여전하지." / "여기 강가에서 40년째 낚싯대를 던지고 있다네."
         → 격식 없는 강가 토박이 노인. 길드도 직책도 없고, 그냥 평생 낚은 사람.
  역할   없음(대화 전용). 표시명에 색코드가 없다 — 규칙상 대화만 하는 NPC는 &f여야 함(별건).
  지역   스폰도시. 유럽풍.
  ★문제 4m 안에 노인 낚시꾼이 셋이다:
         할아버지(4.3m) 회청 머리 + 풀비어드 + 갈색 조끼
         하겐(2.2m)     반백 포니테일 + 딥그린 길드 조끼 + 반돌리에 + 무릎장화
         촌장(1.6m)     갈색 로브 / 브리기테(6.1m) 붉은 장발
         → 갈색·딥그린·장발은 점유됨. 실루엣과 색을 둘 다 비켜야 한다.
  구스킨 head.outer 384px 전체가 불투명 순수검정 = 머리에 검은 상자. 팔·다리 단색.

DESIGN SPEC
  나이/체격  70대, 등이 살짝 굽은 마른 체구
  실루엣     ★밀짚모자(마을 유일) + 낡은 리넨 셔츠 + 멜빵 + 걷어올린 바짓단 + ★맨발
             (마을 전원이 장화라 맨발 자체가 실루엣 차별화)
  팔레트     밀짚=따뜻한 straw / 셔츠=바랜 누런 리넨 / 바지=흐린 청회(강물, 마을 미사용)
             / 멜빵=낡은 가죽. ★금속 악센트 없음 — 가난한 시골 노인이라 놋쇠가 없는 게 맞다
             (하겐의 놋쇠 배지·버클과도 자동으로 갈라짐)
  비대칭     ★멜빵 한쪽이 어깨에서 흘러내림 + 오른쪽 바짓단만 걷어올림 + 왼무릎 헝겊 패치
  정체 모티프 없음. 로고 붙일 사람이 아니다 — 정체성은 밀짚모자+맨발+흘러내린 멜빵
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 흰 염소수염(할아버지=풀비어드, 하겐=머튼촙과
             구분) · 눈꼬리 주름 · 모자가 이마를 덮으므로 이마 주름은 생략
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 102

P = dict(
    skin=ramp('b58a63'),                  # 40년 강가 = 볕에 그은 가죽 같은 피부
    hair=ramp('a8a49a'),                  # 흰머리. ★베이스를 너무 밝게(dedbd2) 잡으면
    #                                       램프 위쪽이 ffffff로 클리핑돼 번진다
    straw=ramp_lit('c2a34e'),                 # 밀짚
    shirt=ramp_lit('a3977a'),                 # 바랜 누런 리넨 (피부·흰머리와 값 분리)
    pants=ramp_lit('5c6b72'),                 # 흐린 청회 (강물색, 마을에서 아무도 안 씀)
    leather=ramp_lit('5f4530'),               # 낡은 멜빵 (셔츠 위에서 읽히게 진하게)
    iris=ramp('4f5d4a'),                  # 흐린 녹갈
)


def build():
    s = Skin()

    # ---- head (모자 2행 + 챙 1행 배치: 0-1 모자 / 2 챙 / 3 눈썹 / 4 눈 / 5 볼 / 6 입 / 7 턱)
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=1, back=5, seed=SEED)      # 모자 밑 옆머리만
    g.beard(s, P['hair'], style='goatee', y=5, seed=SEED)  # 흰 염소수염
    g.wrinkles(s, P['skin'], crow=True, forehead=False)    # 모자가 이마를 덮음
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, brow=P['hair'][1], brow_y=3)
    g.mouth(s, P['skin'], y=6, w=2)                        # 코는 기본대로 생략
    g.cap(s, P['straw'], crown=2, brim='round', seed=SEED)  # 밀짚모자: 챙은 한 바퀴 (밴드 없음:
    #   2행짜리 crown에 가죽밴드를 넣으면 모자가 아니라 머리띠로 읽힌다)

    # ---- torso: 리넨 셔츠 + 한쪽 흘러내린 멜빵
    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, fold_cols=(2, 5),
            grain=0.08)
    g.suspenders(s, P['leather'], cols=(1, 6), waist=7, dropped='left', cross=True)
    g.patch(s, 'body', 'front', P['shirt'], x=5, y=8, w=2, h=2)   # 셔츠 기운 자국

    # ---- arms: 소매를 팔꿈치까지 걷음(둘 다) — 40년 강가
    g.sleeves(s, P['shirt'], y0=0, y1=6, seed=SEED, grain=0.08)
    s.form_fill('arm_r', P['skin'], 7, 11, base_idx=3, bottom=True)
    s.form_fill('arm_l', P['skin'], 7, 11, base_idx=3, bottom=True)
    for part in ('arm_r', 'arm_l'):
        s.hem(part, 6, P['shirt'], base_idx=3)             # 걷어올린 소매단

    # ---- legs: 바지 + 오른쪽만 걷어올림 + 맨발
    g.pants(s, P['pants'], y0=0, y1=8, seed=SEED)
    s.form_fill('leg_r', P['pants'], 0, 6, base_idx=3)     # 오른쪽은 더 짧게
    s.hem('leg_r', 6, P['pants'], base_idx=3)              # 걷어올린 단
    s.form_fill('leg_r', P['skin'], 7, 11, base_idx=3, bottom=True)   # 맨 정강이+발
    s.form_fill('leg_l', P['skin'], 9, 11, base_idx=3, bottom=True)   # 맨발
    s.hem('leg_l', 8, P['pants'], base_idx=3)
    for part in ('leg_r', 'leg_l'):                        # 발등 그림자 = 발로 읽히게
        s.shade_ring(part, 11, amount=0.25)
        s.f(part, 'bottom').fill(P['skin'][1])             # 발바닥
    g.patch(s, 'leg_l', 'front', P['pants'], x=1, y=4, w=2, h=2)      # 무릎 패치

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'heinrich.png'))


if __name__ == '__main__':
    print(build())
