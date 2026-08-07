#!/usr/bin/env python3
"""장터 여인 — &f장터 여인(시민6), 왕도 장터, citizensId 69.

CHARACTER BRIEF
  대사   "왕도 장터의 생선은 신선하기로 소문났답니다." / "한번 둘러보세요."
         → 기능 없는 &f 대화 NPC. 장터에서 ★생선을 파는 사람이다.
  구스킨 ★흰/분홍 머리 + 검정에 붉은 악센트 = 애니메이션 캐릭터. 66 아낙과 같은 계열의 오배치.

DESIGN SPEC
  나이/체격  40대, 하루 종일 서서 파는 사람. 팔뚝이 굵고 옷이 젖어 있다
  실루엣     소금기 밴 회청 커틀 + ★거친 삼베 앞치마(생선 손질용, 무릎까지)
             + 머릿수건 + 걷어붙인 소매
             ★66 마을 아낙과 가르는 축: 66=벽돌 커틀+리넨 앞치마+맨머리 땋음 /
             69=회청 커틀+삼베 앞치마+머릿수건. 색·재질·머리 셋 다 다르다
  팔레트     커틀=바랜 회청(물일하는 사람) / 앞치마=거친 삼베(누런 회갈)
             / 머릿수건=바랜 겨자 / ★악센트 금속 0곳 — 대신 앞치마에 은빛 비늘 2px
             (장터 생선장수의 서명. 금속 장신구보다 훨씬 직업을 잘 말한다)
  비대칭     오른 앞치마 아래 기운 자국 + 왼 소매만 더 걷어올림
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 속눈썹 + 입술 + 눈가 주름
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 69

P = dict(
    skin=ramp('c6996f'),
    hair=ramp('47372a'),
    kirtle=ramp_lit('55707a'),
    # 삼베는 커틀과 명도를 2단 이상 벌린다 — 붙으면 하체가 한 덩어리가 된다
    apron=ramp_lit('8a7f66'),
    scarf=ramp_lit('9a8446'),
    chemise=ramp_lit('aca699'),
    scale=ramp_lit('98a0a4'),
    lip=ramp('9b5a52'),
    iris=ramp('4a5a5f'),
)


def build():
    s = Skin()

    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=6, seed=SEED)
    g.wrinkles(s, P['skin'], crow=True, forehead=False)
    g.face_shape(s, P['skin'], jaw='oval')
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['hazel']), y=5, gaze=0, iris_idx=1)
    g.brow(s, P['hair'][1], y=4)
    f = s.f('head', 'front')
    f.px(0, 4, P['skin'][1]); f.px(7, 4, P['skin'][1])   # 속눈썹/눈꼬리
    f.rect(3, 6, 4, 6, P['lip'][2])                      # 입술
    g.headscarf(s, P['scarf'], rows=2, tail=True, seed=SEED)
    # ★두건이 머리카락을 전부 덮으면 여성으로 안 읽힌다(유저 지적: 남자처럼 보임).
    #   관자놀이에 앞머리를 드러내야 성별과 '천을 두른 것'이 동시에 읽힌다
    fo = s.f('head', 'front', 'outer')
    fo.rect(0, 2, 0, 4, P['hair'][3]); fo.rect(7, 2, 7, 4, P['hair'][3])
    fo.px(0, 5, P['hair'][2]); fo.px(7, 5, P['hair'][2])

    # ---- base: 슈미즈 → 커틀
    g.tunic(s, P['chemise'], y0=0, y1=11, collar=True, seed=SEED, grain=0.06, hem=False)
    g.sleeves(s, P['chemise'], y0=0, y1=11, seed=SEED, grain=0.06)
    g.pants(s, P['kirtle'], y0=0, y1=11, seed=SEED)
    g.hands(s, P['skin'], rows=2)

    # 커틀: 발목까지. 소매는 걷어올려 슈미즈를 드러낸다(물일하는 사람)
    g.robe(s, P['kirtle'], y0=0, seed=SEED, hem_row=11, sleeve_to=6,
           lining=P['chemise'])
    s.clear_rows('arm_l', 5, 11, layer='outer')          # 왼팔만 더 걷어올림
    s.hem('arm_l', 4, P['kirtle'], layer='outer', base_idx=3, lip=False)

    # ---- 삼베 앞치마: 생선 손질용. 66의 고운 리넨과 재질이 갈려야 한다
    g.apron(s, P['apron'], bib=(2, 5), bib_y=(2, 6), waist=7, hem=11,
            wrap=0, straps=True, tie=True, seed=SEED)
    fa = s.f('body', 'front', 'outer')
    for x in (0, 7):                                     # 양옆을 비워 커틀이 흐르게
        fa.rect(x, 7, x, 11, (0, 0, 0, 0), 0)
    s.speckle('body', P['apron'], 2, 11, layer='outer', density=0.16, seed=SEED,
              faces=('front',))                           # 삼베의 거친 결
    g.patch(s, 'leg_r', 'front', P['apron'], x=1, y=6, w=2, h=2, layer='outer')

    # ★앞치마에 달라붙은 생선 비늘 — 이 사람의 직업을 말하는 유일한 반짝임
    for x, y in ((3, 4), (2, 9), (5, 8)):
        fa.px(x, y, P['scale'][4])
        fa.px(min(7, x + 1), y, P['scale'][2])

    # ★긴 머리 — 반드시 <b>옷·머리쓰개를 다 그린 뒤</b>, 그리고 outer 레이어에.
    #   NPC는 lookclose로 늘 플레이어를 마주보므로 뒷머리는 볼 일이 없다 → 얼굴 옆과
    #   가슴 앞으로 내려와야 '길다'가 읽힌다. 머리쓰개는 함수가 알아서 비켜간다.
    g.female_hair_length(s, P['hair'], seed=SEED)
    # ★스펙에 '악센트 금속 0곳' — 네크라인만 주고 장신구는 넣지 않는다
    g.decollete(s, P['skin'], style='scoop')
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'fishwife.png'))


if __name__ == '__main__':
    print(build())
