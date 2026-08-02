#!/usr/bin/env python3
"""알비스 — &a[Q] 알비스, 스폰 앞바다 외딴 첨탑의 은둔 마법사. (신규 NPC, citizensId 미정)

CHARACTER BRIEF  (quests.json 알비스01/02 + dialogue.json 알비스 대사에서 뽑은 근거)
  역할   퀘스트 NPC. 바르칸의 '조류'와 '잊힌 별빛'을 연구. 오로라를 소환해 전설
         성광어(星光魚)의 의식을 주관한다. 기능 GUI 없음 → 대사+서사가 컨셉 전부.
  대사   "…손님인가. 이 외딴 탑까지 오다니 별일이군."
         "나는 바르칸의 조류와 잊힌 별빛을 읽는 사람일세."
         "밤이 깊거든 밤바다에 낚싯대를 드리우게. 오로라가 답할 걸세."
         → 은둔·고령·초연한 학자 말투. 화려한 대마법사가 아니라 '읽는 사람'.
  지역   스폰 앞바다 외딴 첨탑 = 스폰도시 권역(유럽풍 중세). 사막/아라비안 요소 금지.
  차별화 세르간(같은 스폰권 은퇴 학자)이 이미 **보라 별무늬 로브**를 쓴다.
         → 색상(보라 금지, 심해 남색)과 실루엣(세르간=평평한 로브, 알비스=후드+숄더
           맨틀 2단 실루엣) 양쪽에서 갈라놓는다.

DESIGN SPEC  (그리기 전에 전부 선언)
  나이/체격  70대, 마른 장신. 등이 약간 굽은 노학자
  실루엣     [겉] 깊은 후드 → 어깨 맨틀(뒤로 길게 흐름) → [속] 발목까지 전신 로브
             → 맨발 아닌 낮은 가죽 신. 후드+맨틀 2단이 세르간과 갈리는 지점
  팔레트     로브=심해 남색(밤바다) / 맨틀=한 단계 더 어두운 남청(계급이 아니라 그림자)
             / 안감=오로라 청록(1px 숨구멍 — 칼라·소매끝에만) / 신=젖은 진갈
             / 악센트=별빛 은백 **2곳까지**(맨틀 잠금쇠 1 + 지팡이끈 파우치 금속 1)
  비대칭     왼쪽 허리에 관측 두루마리 파우치 · 오른 소매만 한 단 더 걷음(별을 가리키는 손)
             · 맨틀 왼쪽 어깨가 오른쪽보다 1px 낮게 흘러내림
  얼굴       창백한 피부(햇빛 안 봄), 백발 장발 + 긴 백색 수염, 흐린 청록 눈(gaze=0),
             이마 주름 + 눈가 주름, 코 없음(기본)
  정체 모티프 **가슴 엠블럼 없음** — 하드룰(엠블럼은 타바드/기사·왕실 전용). 정체성은
             후드+맨틀 재단, 오로라 안감 1px, 두루마리 파우치로만 표현
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 77

P = dict(
    skin=ramp('cfb6a4'),                  # 창백 — 첨탑에 갇혀 산다
    # ★백발은 base를 'a8a49a'쯤으로 잡아야 하이라이트에 여유가 생긴다 (audit: pure-white 클리핑)
    hair=ramp('a29e94', spread=0.50),
    beard=ramp('9d998f'),                 # 수염은 머리보다 반 단 어둡게 (같으면 얼굴이 뭉침)
    # ★2패스: 맨틀(2b3550)과 로브(2f3f63)가 값이 가까워 상체가 한 덩어리로 뭉쳤다.
    #   로브를 한 단 올려 후드·맨틀과 분리한다(하드룰: 인접 의복 값 분리).
    robe=ramp_lit('3b4d75'),                  # 심해 남색: 밤바다
    mantle=ramp_lit('232c45', spread=0.46),   # 후드/맨틀 = 그림자 쪽
    under=ramp_lit('4a5570'),                 # 속옷(base 레이어) — 로브가 outer라 base를 반드시 채운다
    # ★1패스 자기비평: '4fd0c0'은 채도가 너무 높아 안감이 아니라 네온 패치로 읽혔다.
    #   뮤트한 청록으로 낮춰야 '천 안감'이 된다.
    aurora=ramp_lit('3f8378', spread=0.44),   # 오로라 청록 = 안감 1px 숨구멍 전용
    shoe=ramp_lit('4a3b31', spread=0.42),     # 젖은 가죽 — spread 좁혀 near-black 클리핑 방지
    silver=ramp_lit('bfc6cf'),                # 별빛 은백 악센트(2곳까지)
    iris=ramp('5c7a80', spread=0.40),     # 흐린 청록 눈 — 노인이라 채도를 낮춘다(3패스)
)


def build():
    s = Skin()

    # ---- 얼굴: 피부 → 머리 → 수염 → 이목구비 (뒤 호출이 이김)
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=7, seed=SEED, part_x=4)   # 앞머리는 이마까지만
    g.beard(s, P['beard'], style='long', y=5, seed=SEED, ragged=True)
    g.wrinkles(s, P['skin'], crow=True, forehead=True)            # 노학자 = 주름 둘 다
    g.eyes(s, 'cdc8bd', P['iris'], y=4, gaze=0, brow=P['hair'][1], brow_y=3)
    g.mouth(s, P['skin'], y=6, w=2, color=P['beard'][1])

    # ---- ★base 레이어 속옷을 먼저 깐다.
    #      robe()는 몸통·팔·다리를 전부 outer에 그리므로, base를 비워두면 인게임에서
    #      투명 구멍이 뚫린다(하드룰 / audit ERROR 5건). 로브 밑에 받쳐 입은 속옷으로 채운다.
    g.tunic(s, P['under'], y0=0, y1=11, layer='base', collar=False, seed=SEED, grain=0.06)
    g.sleeves(s, P['under'], y0=0, y1=11, layer='base', seed=SEED)
    g.pants(s, P['under'], y0=0, y1=11, layer='base', seed=SEED)
    # 뒷면은 앞면과 다른 구성 — 등 중앙 이음선 (audit: front == back 경고 해소)
    s.f('body', 'back', 'base').col(4, P['under'][1], 0, 11)
    s.folds('body', 1, 10, P['under'], layer='base', cols=(2, 6), face='back', seed=SEED + 3)

    # ---- 전신 로브(outer) — robe()는 가로 요소를 하나도 안 그린다 → 흐름이 끊기지 않는다
    g.robe(s, P['robe'], y0=0, seed=SEED, hem_row=11, sleeve_to=10,
           lining=P['aurora'], placket=True)

    # 어깨 맨틀 — 앞은 곡선으로 짧게. ★1패스: back=9는 등을 전부 덮어 로브 세로 주름을
    #   가려 '평평한 판'이 됐다 → back=6으로 줄여 아래로 로브 흐름이 드러나게 한다.
    #   lining도 제거: 맨틀+로브 안감이 목에서 겹쳐 '청록 목걸이'가 됐다(악센트 예산 초과).
    #   ★2패스: clasp=은 silver 램프 최상단(거의 흰색)을 3px 써서 '흰 턱받이'가 됐다.
    #   → clasp 인자를 빼고, 아래에서 어두운 은색 2px만 직접 찍는다.
    g.mantle(s, P['mantle'], front=3, back=6, seed=SEED + 5)

    # 비대칭 ①: 맨틀 왼쪽 어깨만 1px 더 흘러내림
    s.f('body', 'left', 'outer').row(4, P['mantle'][1], 0, 3)

    # ---- 후드 (맨틀 다음 — 어깨 카울이 맨틀 위에 얹혀야 목이 안 뜬다)
    #      ★1패스: 후드 앞에 안감 줄을 넣으니 이마를 가로지르는 '바이저 띠'가 됐다 → 제거.
    #      후드의 내부 그림자는 hood()가 이미 그린다.
    g.hood(s, P['mantle'], opening=4, seed=SEED)
    # ★3패스: hood()는 flat fill이라 후드가 플라스틱 껍데기로 읽혔다. 천 결과 세로 주름을
    #   얹어 '천'으로 만든다(하드룰: flat fill 금지 정신).
    s.speckle('head', P['mantle'], 0, 7, layer='outer', density=0.10, seed=SEED,
              faces=('right', 'left', 'back'))
    s.folds('head', 1, 6, P['mantle'], layer='outer', cols=(2, 5), face='back', seed=SEED + 9)
    s.f('head', 'top', 'outer').row(0, P['mantle'][1], 1, 6)   # 정수리 접힘

    # 악센트 ①: 목 아래 잠금쇠 — 은백 램프 중간값 2px만 (하이라이트 쓰면 흰 얼룩이 된다)
    _b = s.f('body', 'front', 'outer')
    _b.px(3, 2, P['silver'][2]); _b.px(4, 2, P['silver'][1])

    # ★2패스: robe()가 양 소매 커프에 안감을 1px씩 넣는데, 왼쪽만 남으면 청록 사각으로
    #   튄다. 왼 소매는 로브색으로 덮어 깔끔히 두고, 비대칭은 '오른쪽 걷은 소매'로만 준다.
    _al = s.f('arm_l', 'front', 'outer')
    _al.px(1, 10, P['robe'][2]); _al.px(2, 10, P['robe'][1])

    # ---- 손: 소매가 손목(10)까지 오므로 손은 2행만
    g.hands(s, P['skin'], rows=2)
    # 비대칭 ②: 오른 소매만 한 단 더 걷음 → ★1패스: 청록을 칠하니 '발광 팔찌'가 됐다.
    #   걷은 소매는 안감색이 아니라 '드러난 맨살'로 표현해야 옷처럼 읽힌다.
    s.f('arm_r', 'front', 'outer').row(9, P['skin'][3], 1, 2)
    s.f('arm_r', 'right', 'outer').px(1, 9, P['skin'][2])

    # ---- 신발: 로브 자락 아래로 살짝
    g.boots(s, P['shoe'], rows=2, toe=True, cuff=False)

    # ---- 비대칭 ③: 왼쪽 허리 관측 두루마리 파우치 (악센트 ②: 파우치 금속)
    g.pouch(s, P['shoe'], part='leg_l', face='front', x=1, y=1, w=2, h=3,
            metal=P['silver'])

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'albis.png'))


if __name__ == '__main__':
    print(build())
