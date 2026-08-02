#!/usr/bin/env python3
"""군나르 — 항구 관리자, 스폰도시 항구, citizensId 132.

CHARACTER BRIEF  (npc_brief.py 군나르 --village)
  대사   "항구 관리가 제 일이오. 배들이 안전하게 드나들도록 하지." / "여긴 늘 바쁘답니다."
         → 항만장(harbormaster). 낚시꾼이 아니라 '관리직'이다 — 이 마을 노인 낚시꾼 4명과
           신분이 다르다는 게 실루엣에 드러나야 한다.
  역할   없음(대화 전용). 표시명에 색코드 없음 — 규칙상 &f여야 함(별건).
  지역   항구 < 스폰도시.
  이웃   30m+ 로 떨어져 있음(할아버지·프란츠·펠릭스·마르타). 같은 항구의 오토는 어물전.

DESIGN SPEC
  나이/체격  50대, 자세가 곧은 실무 관리자
  실루엣     ★방수 오일스킨 롱코트(무릎 덮음) + 항만장 캡 + 목수건 + 어깨에 감은 밧줄
             (마을의 낚시꾼들은 조끼·멜빵·망토 — 여밈 있는 '제복형 코트'는 이 사람뿐)
  팔레트     코트=짙은 네이비(마을 미사용: 오토=청록, 하겐=딥그린, 하인리히=청회,
             어부노인=올리브) / 셔츠=바랜 흰 / 밧줄=마 / ★악센트=놋쇠 호루라기 한 곳
  비대칭     밧줄 사리가 한쪽 어깨만 + 오른쪽 허리에 장부 주머니 + 왼쪽 소매만 접힘
  정체 모티프 놋쇠 호루라기(항만장의 상징) — 가슴 중앙 2px, 로고가 아니라 소지품
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · ★수염 없음(깔끔한 면도)
             — 이웃 넷이 full/mutton/goatee/stubble을 다 나눠 썼고, 면도가 관리직다움도 산다
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 132

P = dict(
    skin=ramp('c39a72'),
    hair=ramp('5a4636'),                  # 짧은 갈색
    # ★기본 spread(0.62)면 [3]~[4]가 밝은 파랑으로 튄다 — 마을은 전부 뮤트다
    coat=ramp_lit('2b3a52', spread=0.42),     # 짙은 네이비 오일스킨
    shirt=ramp_lit('a9a294'),                 # 바랜 흰 셔츠
    rope=ramp_lit('9b8355'),                  # 마 밧줄
    scarf=ramp_lit('6b4f4a'),                 # 목수건
    brass=ramp_lit('b08d3c'),                 # 호루라기
    capband=ramp_lit('6e5a25'),               # 캡 밴드는 놋쇠를 어둡게 — 밝게 두면 금관처럼 보인다
    boot=ramp_lit('3a2f26'),
    iris=ramp('3f5a6b'),                  # 바다빛 회청
)


def build():
    s = Skin()

    # ---- head (캡 2행 + 챙 1행: 0-1 캡 / 2 챙 / 3 눈썹 / 4 눈 / 5 볼 / 6 입 / 7 턱)
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=6, seed=SEED, part_x=2)
    g.wrinkles(s, P['skin'], crow=True, forehead=False)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, brow=P['hair'][2], brow_y=3)
    g.mouth(s, P['skin'], y=6, w=2)
    g.cap(s, P['coat'], crown=2, brim=True, band=P['capband'], seed=SEED)  # 항만장 캡

    # ---- 몸: 셔츠 → 네이비 롱코트(자락은 다리 outer로) → 목수건 → 밧줄 → 벨트
    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07, hem=False)
    g.sleeves(s, P['shirt'], y0=0, y1=9, seed=SEED, grain=0.07)
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['coat'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['boot'], rows=4, toe=True, cuff=True)

    g.coat(s, P['coat'], y0=0, hem=11, tails=3, layer='outer', lapel=True,
           center=True, seed=SEED)
    for part in ('arm_r', 'arm_l'):                       # 코트 소매
        s.form_fill(part, P['coat'], 0, 8, layer='outer', base_idx=3)
        s.hem(part, 8, P['coat'], layer='outer', base_idx=3)
    s.clear_rows('arm_l', 7, 11, layer='outer')           # 왼소매만 접어 셔츠가 보임
    s.hem('arm_l', 6, P['coat'], layer='outer', base_idx=3, lip=False)

    # 목수건: 칼라 위로 한 바퀴
    s.band('body', 0, 0, P['scarf'][3], layer='outer')
    s.f('body', 'front', 'outer').rect(3, 1, 4, 2, P['scarf'][2])   # 앞으로 늘어진 끝
    s.f('body', 'front', 'outer').px(4, 2, P['scarf'][1])

    # 호루라기: 목줄 V자 + 놋쇠 펜던트 (로고가 아니라 소지품)
    fr = s.f('body', 'front', 'outer')
    fr.px(2, 2, P['capband'][2]); fr.px(3, 3, P['capband'][2])      # 목줄(어둡게)
    fr.px(5, 2, P['capband'][2]); fr.px(4, 3, P['capband'][2])
    fr.px(3, 4, P['brass'][4]); fr.px(4, 4, P['brass'][2])          # 놋쇠 호루라기 2px

    g.bandolier(s, P['rope'], front_x=1, layer='outer')   # 어깨에 감은 밧줄(비대칭)
    g.belt(s, P['boot'], y=7, accent=P['brass'], layer='outer')
    g.pouch(s, P['boot'], part='leg_r', face='front', x=1, y=2, w=2, h=3,
            metal=P['brass'])                              # 장부 주머니

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'gunnar.png'))


if __name__ == '__main__':
    print(build())
