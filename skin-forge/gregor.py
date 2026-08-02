#!/usr/bin/env python3
"""왕실 요리장 그레고르 — &a[Q] 왕실 요리장 그레고르, 왕도 왕성 주방, citizensId 57.

CHARACTER BRIEF
  대사   "왕실 요리장 그레고르요. 연회 상을 채우려면 좋은 물고기가 끝없이 필요하지."
         "솜씨 좋은 어부라면 언제든 환영이네."
  기능   cooking(요리 GUI) · 퀘스트 연회 준비 → 귀빈의 입맛 → ★왕의 만찬
  구스킨 ★흰 셰프 재킷 + 빨간 나비넥타이 + 현대 토크 = 레스토랑 셰프.
         중세 왕실 주방장이 나비넥타이를 매지 않는다.

DESIGN SPEC
  나이/체격  60대, 왕성 주방을 수십 년 쥔 노장. 잘 먹은 체구
  실루엣     짙은 올리브 튜닉 + ★밝은 리넨 앞치마(무릎까지) + 리넨 코이프
             + 허리 칼집(주방칼) + 걷어붙인 소매
             ★같은 '앞치마 직군' 셋을 가르는 축:
               오토65(항구)=소금 절은 가죽 / 지크하르트117(대장간)=검댕 가죽·맨머리
               / 그레고르=밝은 리넨·코이프. 앞치마 재질과 머리로 직업이 갈린다
  팔레트     튜닉=짙은 올리브회 / 앞치마·코이프=밝은 리넨(순백 금지)
             / ★악센트=강철 1곳(칼집의 칼자루)+놋쇠 버클 1곳
             얼룩=기름·그을음(대장장이의 불똥 주황과 다른 재질)
  비대칭     오른 허리 칼집 + 왼쪽 앞치마 아래 기름 얼룩 + 오른 소매만 더 걷음
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 흰 콧수염 · 화덕에 그을린 붉은 얼굴
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, mix, ramp, ramp_lit       # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 57

P = dict(
    skin=ramp('c48f63'),
    # 백발은 램프를 좁히지 않으면 위가 클리핑돼 뒤통수가 형광 줄무늬가 된다
    hair=ramp('9a938a', spread=0.30),
    # ★요리사의 신호는 '어두운 몸통 위의 큰 밝은 앞치마'다. 튜닉과 앞치마가 한 단
    #   차이밖에 안 나면 전체가 올리브 한 덩어리 = 군복으로 읽힌다(실측 v2·v3).
    tunic=ramp_lit('3a4038'),
    # 리넨 램프는 기본 spread면 [4]가 fff7ec(거의 흰색)까지 올라간다
    linen=ramp_lit('b8ae98', spread=0.45),
    coif=ramp_lit('c4bca8', spread=0.40),
    steel=ramp_lit('8a8e93'),
    brass=ramp_lit('b08d3c', spread=0.45),
    grease=ramp_lit('6b5a3f'),
    # 어두운 가죽에 기본 spread를 쓰면 [0]이 0a0906 = 사실상 검정 외곽선이 된다
    boot=ramp_lit('4a3d2e', spread=0.42),
    pants=ramp_lit('3f3a33'),
    iris=ramp('4a5a4a'),
)


def build():
    s = Skin()

    # ---- 머리 (0-2 코이프 / 3 눈썹 / 4 눈 / 5 볼 / 6 콧수염 / 7 턱)
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=1, back=6, seed=SEED)
    g.wrinkles(s, P['skin'], brow_y=2, crow=True, forehead=False)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, brow=P['hair'][1], brow_y=3)
    fh = s.f('head', 'front')
    fh.rect(2, 6, 5, 6, P['hair'][3])                    # 흰 콧수염(수염은 없다)
    fh.px(3, 6, P['hair'][4]); fh.px(4, 6, P['hair'][2])
    g.mouth(s, P['skin'], y=7, w=2)
    for x, y in ((1, 5), (6, 5)):                        # 화덕에 익은 볼
        fh.px(x, y, mix(fh.get(x, y), (170, 96, 74, 255), 0.35))
    g.cap(s, P['coif'], crown=4, brim=False, seed=SEED)  # 리넨 코이프(현대 토크 아님)

    # ---- base: 올리브 튜닉 → 바지 → 장화
    g.tunic(s, P['tunic'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07, hem=False)
    g.sleeves(s, P['tunic'], y0=0, y1=7, seed=SEED, grain=0.07)
    for part in ('arm_r', 'arm_l'):                      # 걷어붙인 아래는 맨팔
        s.form_fill(part, P['skin'], 8, 11, base_idx=3)
        s.hem(part, 7, P['tunic'], base_idx=3)
    s.clear_rows('arm_r', 6, 7, layer='base')            # 오른쪽만 한 단 더 걷음
    s.form_fill('arm_r', P['skin'], 6, 7, base_idx=3)
    s.hem('arm_r', 5, P['tunic'], base_idx=3)
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['pants'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['boot'], rows=4, toe=True, cuff=True)

    # ---- 리넨 앞치마: 밝은 리넨이 이 인물의 직업 신호다
    g.apron(s, P['linen'], bib=(1, 6), bib_y=(1, 6), waist=7, hem=11,
            wrap=2, straps=True, tie=True, seed=SEED, accent=P['tunic'])
    fa = s.f('body', 'front', 'outer')
    for x in (0, 7):                                     # 양옆을 비워 튜닉이 보이게
        fa.rect(x, 8, x, 11, (0, 0, 0, 0), 0)
    for x, y in ((3, 9), (2, 4), (4, 10)):               # 기름·그을음 얼룩
        fa.px(x, y, mix(fa.get(x, y), P['grease'][2], 0.55))

    # ★오른 허리 칼집 — 주방칼. 금속은 칼자루 리벳과 벨트 버클 둘뿐
    fa.rect(6, 8, 7, 11, P['boot'][3])
    fa.col(6, P['boot'][4], 8, 11)
    fa.row(11, P['boot'][0], 6, 7)
    fa.px(6, 8, P['steel'][4]); fa.px(7, 8, P['steel'][2])
    g.belt(s, P['boot'], y=7, accent=P['brass'], layer='outer')

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'gregor.png'))


if __name__ == '__main__':
    print(build())
