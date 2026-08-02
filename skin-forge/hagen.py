#!/usr/bin/env python3
"""하겐 — &a[Q] 하겐, 스폰도시(스폰마을), citizensId 70.

CHARACTER BRIEF  (npc_brief.py 하겐 --village)
  대사   "낚시사 길드에서 잔뼈가 굵은 몸이지." / "자네 같은 신참에게 부탁할 일이…"
         → 길드 고참. 신참을 가르치는 위치. 자부심 있는 말투, 재촉하지 않음("천천히 해도 좋네").
  퀘스트 길드의 위엄(A등급 3마리) · 바르칸 대표어(붕어 50cm 대물) · 진정한 어부(50마리)
         → 등급·대물·숙련을 요구하는 사람. 장비를 갖춘 베테랑 낚시꾼이어야 설득력이 있다.
  지역   스폰도시. 유럽풍. 4m 반경에 NPC가 빽빽함 → 색·실루엣 충돌 회피가 최우선.
  이웃   할아버지(2.5m, 풀비어드+갈색조끼) · 하인리히(2.2m, 청록셔츠) ·
         브리기테(4m, 붉은 장발) · 촌장(3.5m, 갈색 로브)
         → 갈색(할아버지·촌장)과 청록(하인리히)은 이미 점유. 장발도 점유.

DESIGN SPEC
  나이/체격  50대, 어깨 넓은 현역. 노인(할아버지)과 구분되게 허리는 펴져 있어야 함
  실루엣     길드 조끼 위 반돌리에(도구 스트랩) + 벨트 + 무릎까지 오는 장화
             + 뒤로 묶은 반백 포니테일. 모자 없음(오토=캡이므로 의도적 대비)
  팔레트     조끼=딥 포레스트 그린(길드색, 마을에서 안 쓰는 유일한 방향) /
             셔츠=리넨 / 바지=차콜 캔버스 / 장화·스트랩=가죽 / 악센트=놋쇠 2곳뿐
             (길드 배지 + 벨트 버클). 반돌리에 리벳은 가죽톤으로 억제
  비대칭     반돌리에 자체 + 오른쪽 허벅지 루어 파우치 + 왼팔 가죽 팔보호대 + 왼무릎 패치
  정체 모티프 길드 배지 2x2 놋쇠, 조끼 왼가슴 1곳 — 가슴 로고 금지 규칙의 정당한 예외 폭
  얼굴       그을린 피부, 반백 머리, 머튼촙(할아버지의 풀비어드와 구분), 개암색 눈,
             이마 주름 + 눈꼬리 주름(나이), 모자 없으니 이마 행을 살릴 수 있음
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 70

P = dict(
    skin=ramp('c39a72'),                  # weathered fair
    hair=ramp('7d7468'),                  # salt-and-pepper
    beard=ramp('8f8578'),                 # 피부보다 어둡고 머리보다 밝게
    shirt=ramp_lit('8f8574'),                 # linen (조끼보다 눈에 덜 띄어야 한다)
    vest=ramp_lit('2f4a3a'),                  # 낚시사 길드 딥 포레스트 그린
    pants=ramp_lit('6b655a'),                 # charcoal canvas (장화와 2단 이상 벌린다)
    leather=ramp_lit('6b4f36'),               # bandolier / bracer
    boot=ramp_lit('3a2f26'),                  # 너무 어두우면 램프 하단이 순수검정처럼 된다
    brass=ramp_lit('b08d3c'),
    iris=ramp('5b4a33'),                  # hazel
)

BADGE = ['##',
         '#-']


def build():
    s = Skin()

    # ---- head (모자 없음 배치: 0-1 앞머리 / 2 주름 / 3 눈썹 / 4 눈 / 5 코 / 6 입 / 7 턱)
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=7, seed=SEED, part_x=2)
    g.hair_volume(s, P['hair'], fringe=1, back=8, tuft=True, seed=SEED, sideburn=2)
    g.beard(s, P['beard'], style='mutton', y=6, seed=SEED)   # 머튼촙: 입·턱이 보인다
    g.wrinkles(s, P['skin'], brow_y=2, crow=True)
    g.face_shape(s, P['skin'], jaw='long')
    g.face_marks(s, P['skin'], kind='sunken', seed=SEED)
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['dark']), y=4, gaze=0, iris_idx=2)
    g.brow(s, P['hair'][1], y=3)
    #   눈썹은 램프 최하단(hair[1])을 쓰면 눈 위에 검은 막대가 생긴다 → 중간톤
    g.nose(s, P['skin'], y=5, w=2)
    g.mouth(s, P['skin'], y=6, w=2)

    # ---- torso: 리넨 셔츠(base) → 길드 조끼(outer) → 반돌리에 → 벨트 → 포니테일
    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, fold_cols=(2, 5),
            grain=0.07, hem=False)   # 조끼가 허리를 덮으니 셔츠 헴은 생략
    g.vest(s, P['vest'], y0=0, hem=11, gap=0, seed=SEED, buttons=P['leather'])
    #   gap=0 = 여민 조끼. 8px에서 가운데를 벌리면 밝은 셔츠가 멜빵처럼 보인다
    s.motif('body', BADGE, 1, 2, P['brass'], layer='outer')  # 길드 배지, 왼가슴 1곳
    g.bandolier(s, P['leather'], front_x=2, layer='outer')
    g.belt(s, P['leather'], y=7, accent=P['brass'], layer='outer')
    g.ponytail(s, P['hair'], x0=3, w=2, y0=6, y1=11)

    # ---- arms: 리넨 소매 + 왼팔에만 가죽 팔보호대
    g.sleeves(s, P['shirt'], y0=0, y1=9, seed=SEED, grain=0.07)
    # 팔보호대는 벨트(몸통 7행)와 같은 높이·같은 가죽톤이면 팔-몸통-팔이 한 줄로 이어져
    # 보인다 → 어두운 가죽(boot 램프)으로 손목 쪽(7~9행)에만.
    s.form_fill('arm_l', P['boot'], 7, 9, base_idx=3)         # bracer (비대칭)
    s.band('arm_l', 7, 7, P['boot'][4])
    s.shade_ring('arm_l', 10, amount=0.28)                    # 손목 그림자
    g.hands(s, P['skin'], rows=2)

    # ---- legs: 차콜 바지 + 무릎 장화 + 루어 파우치 + 무릎 패치
    g.pants(s, P['pants'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['boot'], rows=5, toe=True, cuff=True)       # 무릎까지(오토는 4행)
    g.pouch(s, P['leather'], part='leg_r', face='front', x=1, y=2, w=2, h=3,
            metal=P['brass'])
    g.patch(s, 'leg_l', 'front', P['pants'], x=1, y=4, w=2, h=2)

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'hagen.png'))


if __name__ == '__main__':
    print(build())
