#!/usr/bin/env python3
"""알도 — &a[Q] 알도, 상단마을, citizensId 95.

CHARACTER BRIEF
  대사   ★"낚시라면 나만큼 잘 아는 사람 없지!" / "물 반, 고기 반이라는 말, 내가 증명해 보이겠소."
         "천천히 하시오, 물고기는 도망 안 가니까."
  퀘스트 낚시광의 부탁(8마리) · 귀한 손님(B등급 2마리)
         → ★허풍 센 낚시광. 스폰마을의 진짜 어부들(수수한 노인들)과 정반대 인물 —
           실력보다 장비와 차림새가 화려한 쪽으로 그려야 캐릭터가 산다.
  구스킨 빨간 체크 플란넬 + 청바지 = 현대 캐주얼(B급 테마 파괴).

DESIGN SPEC
  나이/체격  40대, 배가 좀 나온 자신만만한 체구
  실루엣     ★깃털 꽂은 모자 + 화려한 조끼 + 벨트에 루어를 주렁주렁 + 걷어올린 소매
             (스폰마을 어부들의 앞치마·멜빵·망토와 정반대: '과하게 차려입은' 실루엣)
  팔레트     조끼=머스터드 황토(상단마을 미사용. 마르코=버건디, 조반니=회녹와 분리)
             / 셔츠=크림 / ★악센트=깃털의 청록 + 놋쇠 루어, 두 곳
  비대칭     모자 깃털이 한쪽 + 벨트 왼쪽에만 루어 3개 + 오른소매만 걷음
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 손질된 콧수염(허세) · 혈색 좋은 볼
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))
import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 95
P = dict(skin=ramp('cf9d78'), hair=ramp('4f3a2a'), vest=ramp_lit('b08a34'),
         shirt=ramp_lit('c9bda1'), hat=ramp_lit('6b5433'), teal=ramp_lit('2f7d78'),
         brass=ramp_lit('b08d3c'), boot=ramp_lit('4a3a2b'), iris=ramp('4a3a2c'))


def build():
    s = Skin()
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=6, seed=SEED)
    s.f('head', 'front').rect(2, 6, 5, 6, P['hair'][2])          # 손질된 콧수염
    s.f('head', 'front').px(3, 6, P['hair'][3])
    s.f('head', 'front').px(1, 5, P['skin'][4]); s.f('head', 'front').px(6, 5, P['skin'][4])
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, brow=P['hair'][2], brow_y=3)
    g.cap(s, P['hat'], crown=2, brim=True, band=P['teal'], seed=SEED)
    s.f('head', 'right', 'outer').rect(5, 0, 6, 1, P['teal'][4])  # ★깃털(한쪽만)
    s.f('head', 'right', 'outer').px(6, 0, P['teal'][2])

    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07, hem=False)
    g.sleeves(s, P['shirt'], y0=0, y1=9, rolled=('arm_r', 6), skin_r=P['skin'],
              seed=SEED, grain=0.07)
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['boot'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['boot'], rows=4, toe=True, cuff=True)

    g.vest(s, P['vest'], y0=0, hem=9, gap=0, seed=SEED, buttons=P['brass'])
    g.belt(s, P['boot'], y=9, accent=P['brass'], layer='outer')
    f = s.f('body', 'front', 'outer')
    for i, x in enumerate((1, 2, 3)):                             # ★벨트에 매단 루어 3개
        f.px(x, 10, P['brass'][4] if i != 1 else P['teal'][4])
        f.px(x, 11, P['brass'][1])
    g.pouch(s, P['boot'], part='leg_l', face='front', x=1, y=2, w=2, h=3,
            metal=P['brass'])
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'aldo.png'))


if __name__ == '__main__':
    print(build())
