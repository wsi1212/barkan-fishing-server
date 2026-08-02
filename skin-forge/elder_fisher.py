#!/usr/bin/env python3
"""어부 노인 — &a[Q] 어부 노인 (npc.json 키는 '노인'), 스폰도시, citizensId 74.

CHARACTER BRIEF  (npc_brief.py 노인 --village)
  대사   "평생을 이 물가에서 낚시했다네." / "늙은이의 부탁 하나 들어주겠나?"
         "늪가는 발이 푹푹 빠지니 조심해서 다니거라."
         "허허, 색이 참 곱구먼. 이걸 말려두면 겨우내 요긴하게 쓴단다."
         → 아주 늙은 어부이면서 늪·폭포를 아는 사람. 약초를 말려 겨울을 나는 생활자.
           말투가 손자에게 이르는 투("거라", "허허") = 마을에서 제일 나이 많은 축.
  퀘스트 옛날 물고기(메기 3마리) · 폭포의 비밀 · 노인03(늪지, 고운 색의 것을 말림)
  지역   스폰도시.
  ★문제 스폰마을 노인 낚시꾼 4번째다:
         할아버지 회청머리+풀비어드+갈색조끼 / 하겐 반백포니테일+딥그린조끼+반돌리에
         하인리히 밀짚모자+리넨+멜빵+맨발  → 갈색·딥그린·밀짚·장발이 전부 점유됨

DESIGN SPEC
  나이/체격  80대, 등이 굽고 마름. 마을에서 가장 늙음
  실루엣     ★후드 달린 낡은 망토(마을 유일 — 하겐=니트캡, 하인리히=밀짚모자, 나머지 무모)
             + 안에 낡은 튜닉 + 허리에 말린 약초 다발 + 낡은 신
  팔레트     망토=탁한 올리브카키(늪 이끼. 하겐의 딥포레스트그린과 명도·채도 모두 반대쪽)
             / 튜닉=바랜 갈회 / ★악센트=말린 약초의 적자색 한 곳뿐
             ("색이 참 곱구먼" — 이 사람의 정체를 한 색으로 압축)
  비대칭     약초 다발이 왼쪽 허리에만 + 망태기 끈이 한쪽 어깨 + 오른 무릎 패치
  정체 모티프 없음. 정체성은 후드 실루엣 + 적자색 약초 다발
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 성긴 흰 수염(stubble — full/mutton/goatee는
             이미 이웃 셋이 나눠 씀) · 이마·눈가 주름 · 후드 그늘
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 74

P = dict(
    skin=ramp('bd9068'),                  # 늙고 볕에 그은 피부
    hair=ramp('b0aca0'),                  # 흰머리 (클리핑 안 되게 밝은 회색 베이스)
    cloak=ramp_lit('6b6b45'),                 # 탁한 올리브카키 = 늪 이끼
    tunic=ramp_lit('968a78'),                 # 바랜 갈회 (망토보다 밝아야 앞섶이 열린 게 보임)
    herb=ramp_lit('5c2f40'),                  # ★말린 약초의 적자색. 밝은 단계를 쓰면
    #                                       가슴에 분홍 리본을 단 꼴이 된다 — 어두운 단계만
    shoe=ramp_lit('4a3f33'),
    iris=ramp('5a6b5f'),                  # 흐린 회녹
)


def build():
    s = Skin()

    # ---- head (후드 안: 0-1 후드챙 / 2 그늘 / 3 눈썹 / 4 눈 / 5 볼 / 6 입 / 7 턱)
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=1, back=6, seed=SEED)
    g.beard(s, P['hair'], style='stubble', y=4, seed=SEED)   # 성긴 흰 수염
    g.wrinkles(s, P['skin'], brow_y=2, crow=True)            # 후드는 이마를 덜 가림
    g.face_shape(s, P['skin'], jaw='long')
    g.face_marks(s, P['skin'], kind='ruddy', seed=SEED)
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['blue']), y=4, gaze=0, iris_idx=1)
    g.brow(s, P['hair'][1], y=3)
    g.mouth(s, P['skin'], y=6, w=2)

    # ---- 몸: 낡은 튜닉 → 후드 망토
    g.tunic(s, P['tunic'], y0=0, y1=11, collar=True, seed=SEED, grain=0.08, hem=False)
    g.sleeves(s, P['tunic'], y0=0, y1=9, seed=SEED, grain=0.08)
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['tunic'], y0=0, y1=8, seed=SEED)
    g.boots(s, P['shoe'], rows=3, toe=True, cuff=True)

    # 망토는 몸통 outer + 다리 outer 윗부분(자락)까지 이어야 재킷이 아닌 망토로 읽힌다
    # center=True: 망토는 앞이 열려 안의 튜닉이 보여야 한다. 닫으면 올리브 판때기.
    g.coat(s, P['cloak'], y0=0, hem=11, tails=3, layer='outer', lapel=False,
           center=True, seed=SEED)
    s.clear_rows('body', 2, 9, layer='outer', faces=('front',))   # 앞섶을 연다
    fr = s.f('body', 'front', 'outer')
    for y in range(2, 10):                        # 좌우 자락 2열씩만 = 가운데로 튜닉이 보인다
        for x in (0, 1, 6, 7):
            fr.px(x, y, P['cloak'][3] if x < 4 else P['cloak'][2])
        fr.px(1, y, P['cloak'][1]); fr.px(6, y, P['cloak'][1])    # 자락 안쪽 두께
    g.hood(s, P['cloak'], opening=5, seed=SEED)
    s.band('body', 7, 7, P['cloak'][2], layer='outer')       # 허리끈
    s.shade_ring('body', 8, layer='outer', amount=0.30)

    # ---- 왼쪽 허리춤에 말린 약초 다발 (비대칭 + 유일한 악센트, 작게)
    f = s.f('body', 'front', 'outer')
    f.rect(6, 8, 7, 10, P['herb'][2])
    f.px(6, 8, P['herb'][3]); f.px(7, 10, P['herb'][1])
    s.f('body', 'left', 'outer').rect(1, 8, 2, 10, P['herb'][2])  # 옆구리로 이어짐
    g.pouch(s, P['shoe'], part='leg_l', face='front', x=1, y=2, w=2, h=3,
            metal=P['herb'])
    g.patch(s, 'leg_r', 'front', P['tunic'], x=1, y=4, w=2, h=2)

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'elder_fisher.png'))


if __name__ == '__main__':
    print(build())
