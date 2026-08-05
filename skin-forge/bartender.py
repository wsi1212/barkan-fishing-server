#!/usr/bin/env python3
"""바텐더 — 사막 도박장 바(bar) 담당. 딜러 12인·식당 주인과 실루엣부터 갈린다.

DESIGN SPEC
  근거   카지노(dealers.py)가 확립한 원칙: **지역이 아니라 업장이 톤을 정한다.**
         룰렛·슬롯이 있는 의도적 현대 장르 시설이므로 바텐더도 현대 바 복장이 정합이다.

  차별화 (같은 방에 서는 딜러 12명 + 이미 있는 식당 주인 153과 겹치면 안 된다)
         딜러      = 검정 재킷(긴소매) + 게임별 색 조끼 + 나비타이 + 초록 바이저
         식당 주인 = 여성 · 앞치마 + 두건 + 국자 (요리하는 사람)
         ★바텐더  = **재킷 없음** — 흰 셔츠 소매를 팔꿈치까지 걷고, 검정 조끼 + 나비타이,
                    허리 아래로 긴 **검정 바 앞치마**, 그리고 어깨에 걸친 **린넨 수건**.
         → 멀리서 읽히는 순서: (1) 팔이 밝다=재킷 없음 → 딜러 아님
                              (2) 허리 아래가 검다=긴 앞치마 → 바 뒤에 선 사람
                              (3) 어깨 한쪽에 흰 천=수건 → 바텐더 확정
         소매 걷기는 좌우 비대칭(오른팔만 더 높이) — 대칭은 마네킹이 된다.

  팔레트 딜러와 같은 하우스 제복 계열(셔츠 c6bfae · 검정 26242a)을 공유해 '같은 업장'
         으로 묶고, 유일한 유채색은 나비타이가 아니라 **조끼 안감의 놋쇠 단추**로 준다.
         ★순백/순검정 금지 — 8x8에서 램프가 클리핑돼 번진다. 셔츠는 한 단 내린 흰색.

  얼굴   남성 · 짧은 콧수염(딜러 중 mutton/goatee/full과 겹치지 않는 유일한 수염 형태)
         눈은 2x2(눈꺼풀 1행 + 눈 1행). 눈동자 회색.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                                  # noqa: E402
from skinlib import Skin, ramp, ramp_lit              # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
CID = 161                                            # prod 실측 cid (초기 추정 158은 알비스였다)
SEED = 158

P = dict(
    skin=ramp_lit('c39468', spread=0.40),
    hair=ramp_lit('3a2c22', spread=0.38),
    shirt=ramp_lit('c6bfae', spread=0.42),            # 딜러와 공유 = 같은 업장
    vest=ramp_lit('26242a', spread=0.38),
    # ★검정 앞치마는 실패했다(1차 렌더): 검정 조끼 + 검정 앞치마 + 검정 바지가
    #   하나의 어두운 덩어리로 뭉쳐 앞치마가 아예 안 읽혔다. 값(밝기)이 위아래와
    #   갈려야 3겹으로 보인다 → 따뜻한 가죽 갈색. 유채색 예산은 놋쇠와 같은 계열이라 안 튄다.
    apron=ramp_lit('6b4a2e', spread=0.42),
    trouser=ramp_lit('2b2930', spread=0.38),
    shoe=ramp_lit('221f24', spread=0.34),
    brass=ramp_lit('b08d3c', spread=0.48),
    # ★수건은 '밝은 색'으로는 절대 안 읽힌다(2차 렌더 실패): 셔츠 c6bfae 위에
    #   cfc7b4을 얹으니 같은 색 덩어리였다. 밝은 팔 위에서 천을 분리하는 건 색이
    #   아니라 **무늬**다 → 표백 린넨 + 짙은 줄무늬 2줄(전형적인 바 타월).
    towel=ramp_lit('ded8c8', spread=0.40),
    towel_stripe=ramp_lit('4b4740', spread=0.34),
)


def head(s):
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=6, seed=SEED)
    g.face_shape(s, P['skin'], jaw='square')
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['grey']), y=4, gaze=0,
           socket=P['skin'][1], iris_idx=1)
    # 눈썹은 눈꺼풀(socket)과 안 겹치게 1행 위, 두께 1 → 눈이 2x2로 읽힌다
    g.brow(s, P['hair'][2], y=3, weight=1)
    g.mouth(s, P['skin'], y=6, w=2)
    # ★콧수염 — 딜러들의 goatee/full/stubble/mutton과 겹치지 않는 유일한 수염 형태.
    #   beard()엔 콧수염이 없어 직접 찍는다. ★반드시 맨 마지막에 — 1차 렌더에서
    #   nose(y=5)를 뒤에 그려 콧수염 가운데 2px이 지워지고 좌우 점 2개만 남았다.
    #   코는 생략한다(이 프로젝트 얼굴 기본값 — 8x8에서 코까지 넣으면 얼굴이 붐빈다).
    f = s.f('head', 'front')
    f.rect(2, 5, 5, 5, P['hair'][1])
    f.px(2, 5, P['hair'][0]); f.px(5, 5, P['hair'][0])
    g.neck_shadow(s, P['skin'])


def body(s):
    # ---- 기본: 흰 셔츠 한 벌(몸통 + 양팔). 겉옷이 얇으니 base가 실루엣을 진다
    g.tunic(s, P['shirt'], 0, 11, layer='base', collar=True, seed=SEED)
    # ★소매 걷기 비대칭 — 오른팔은 팔꿈치(5)까지, 왼팔은 한 단 낮게(7). 맨팔은 skin_r로.
    g.sleeves(s, P['shirt'], 0, 11, layer='base', rolled=('arm_r', 5),
              skin_r=P['skin'], seed=SEED)
    g.sleeves(s, P['shirt'], 0, 7, layer='base', seed=SEED + 1)
    s.form_fill('arm_l', P['skin'], 8, 11, layer='base', base_idx=3, bottom=True)
    g.hands(s, P['skin'], rows=2, y1=11)
    g.pants(s, P['trouser'], 0, 11, layer='base', seed=SEED)
    g.boots(s, P['shoe'], rows=4, y1=11, layer='base')

    # ---- 겉옷: 검정 조끼(가슴~허리) + 놋쇠 단추
    g.vest(s, P['vest'], y0=0, hem=8, gap=2, layer='outer', seed=SEED,
           buttons=P['brass'])
    # 나비타이 — ★0행이 아니라 1행. 0행은 셔츠 칼라가 점유해서 1차 렌더에선 아예 안 보였다.
    #   조끼 트임(gap) 사이로 드러난 밝은 셔츠 위에 어두운 매듭을 놓아야 대비가 생긴다.
    fo = s.f('body', 'front', 'outer')
    fo.rect(2, 1, 5, 1, P['vest'][1])
    fo.px(3, 1, P['vest'][0]); fo.px(4, 1, P['vest'][0])       # 매듭 가운데가 가장 어둡다

    # ---- 긴 바 앞치마: 허리(7)부터 다리 자락까지. 조끼보다 어두워 두 겹이 갈린다
    g.apron(s, P['apron'], bib=(2, 5), bib_y=(7, 7), waist=7, hem=11,
            straps=False, layer='outer', seed=SEED)
    for part in ('leg_r', 'leg_l'):
        s.form_fill(part, P['apron'], 0, 6, layer='outer', base_idx=3, top=True)
        s.hem(part, 6, P['apron'], layer='outer')
    fa = s.f('body', 'front', 'outer')
    fa.px(3, 7, P['brass'][3]); fa.px(4, 7, P['brass'][2])     # 허리 버클 = 유일한 금속

    # ---- ★어깨 수건: 바텐더 확정 기호. 왼쪽 어깨에서 등으로 넘어간다.
    #   줄무늬가 실루엣을 만든다 — 무늬 없이는 밝은 셔츠와 뭉친다(2차 렌더 교훈).
    tw, st = P['towel'], P['towel_stripe']

    def cloth(face, x0, y0, x1, y1, stripes=()):
        face.rect(x0, y0, x1, y1, tw[3])
        for sy in stripes:
            if y0 <= sy <= y1:
                face.rect(x0, sy, x1, sy, st[2])

    cloth(s.f('arm_l', 'top', 'outer'), 0, 0, 3, 3, stripes=(1,))
    cloth(s.f('arm_l', 'front', 'outer'), 0, 0, 3, 3, stripes=(1, 3))
    s.f('arm_l', 'front', 'outer').row(4, st[1])       # 천 끝 접힘(가장 어두운 줄)
    cloth(s.f('arm_l', 'left', 'outer'), 0, 0, 3, 3, stripes=(1, 3))
    cloth(s.f('body', 'back', 'outer'), 0, 0, 2, 4, stripes=(1, 3))
    cloth(s.f('body', 'top', 'outer'), 0, 0, 2, 3, stripes=(1,))


def build():
    s = Skin()
    head(s)
    body(s)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'bartender.png'))


if __name__ == '__main__':
    print(build())
