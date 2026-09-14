#!/usr/bin/env python3
"""체사레 — &b[말 대여] 체사레, 상단마을 서쪽 마구간, citizensId 214.

CHARACTER BRIEF  (npc_brief.py 말대여_930_-36 --village 에서 뽑은 근거)
  역할   horseRental=true. 대사 없음(기능형) → 역할 + 지역이 컨셉의 전부.
  지역   상단마을(르네상스 이탈리아 무역항) < 깊은 숲 < 바르칸 < 바르칸 연안 < 원양.
         마을 색은 크림(sail)·버건디·황토금(ochre)·올리브 — tradetown.py 팔레트.
  자리   930/68/-36. 서쪽에 가문비 울타리 방목장(건초 223칸), 동쪽에 마을 진입로.
         반경 40블록 이웃은 베아트리체(93) 하나뿐 → 마을 중심의 앞치마 무리와 떨어져 있다.
  구스킨 NameMC farmer 태그 스킨(체크 플란넬 + 밀짚모자) = 20세기 미국 농부.
         ★오너 지적: 흰자 2px 위에 순검정 동공이 «바깥쪽»으로 붙어 사시로 보였다.

DESIGN SPEC
  나이/체격  40대. 마르고 힘줄진 체형 — 짐을 «드는» 사람(안토니오·마시모)이 아니라
             말을 «모는» 사람이다. 어깨보다 다리 실루엣에 정보를 싣는다.
  실루엣     교차 여밈(wrap) 올리브 튜닉 — 마을이 이미 쓰는 앞치마/열린 조끼/롱코트
             어휘와 겹치지 않는 유일한 여밈. 허리는 와인색 새시 2행.
             다리: 잉크 승마바지 + ★무릎 아래 가죽 각반 + 짧은 장화(3행).
             오른쪽 어깨엔 접어 걸친 안장담요(크림 바탕 + 버건디·황토 줄 2개).
             ★기존 말 대여 2명과 셋 다 달라야 한다:
               121 알브레히트 = 가죽 저킨 + 무릎 위 승마부츠 + 어깨 굴레 + 가죽 캡 + full 수염
               43  오스카     = 크림 셔츠 + 열린 가죽 조끼 + 무릎 부츠 + 왼허벅지 로프 타래
               214 체사레     = 교차여밈 튜닉 + 각반 + 짧은 장화 + 왼어깨 안장담요
  팔레트     튜닉=올리브 matte / 새시=와인 matte / 속옷·안감=크림 matte /
             바지=잉크 matte / 각반=엄버 가죽 / 장화=제일 어두운 가죽 /
             담요=크림 + 버건디·황토 줄 / 놋쇠는 ★2곳만(새시 버클·빗 주머니 걸쇠)
             값 분리: 튜닉(중간) → 새시(밝은 와인) → 바지(어두운 잉크) → 각반(중간 갈색)
             → 장화(최암) 로 인접끼리 두 단씩 벌린다.
  비대칭     ① 오른쪽 어깨 안장담요 ② ★왼 소매만 걷어 맨 팔뚝(오스카는 오른팔이다)
             ③ 오른 허벅지 말빗 주머니 ④ 왼 무릎 헝겊 패치
  정체 모티프 안장담요 + 말빗 — 가슴 로고 없이 소지품으로 직업을 말한다.
  얼굴       그을린 올리브 피부 · 다크브라운 머리(좁은 램프, lessons #20) ·
             ★콧수염 + 턱수염(오스카=stubble, 알브레히트=full 과 갈린다) ·
             ★눈동자 안쪽 gaze=0 · ★코 생략 · 흰자 c9c4b8(순백 금지) ·
             40대라 눈꼬리 주름만(이마 주름은 앞머리에 가려 안 보인다)

REJECT LOG (자기비평으로 걸러낸 것 — 오너에게 보이기 전)
  ① 머리 2f2418 = 8x8 에서 «검정 덩어리». 오스카(4a3826)와 나란히 놓으니 내 것만
     위 절반이 먹히고 흰자 2px 만 헤드라이트처럼 튀었다 → 453425 로 올림.
  ② 안장담요를 x6·x7 에 두니 wrap 여밈의 밝은 안감 대각선과 같은 쪽에서 뭉쳐
     «가슴 한복판 정체불명의 밝은 덩어리»가 됐다 → x0·x1(반대 어깨)로 이동 +
     안감을 한 단 낮춘 린넨(9c8f74)으로 교체.
  ③ 튜닉 hem=10 → 11행의 크림 속옷이 엉덩이를 감는 밝은 띠가 되어 새시와 경쟁 → hem=11.
  ④ 각반 상단 립을 gaiter[4](최명도)로 → 두 다리를 가로지르는 «밝은 가터»로 읽힘
     → 조임끈(gaiter[1], 어둡게)으로 교체.
  ⑤ goatee 단독은 턱 밑 얼룩으로만 읽혀 → 콧수염 1행을 손으로 얹고 입선을 그 안에 넣음.
"""
import pathlib
import sys
import zlib

_SKILL = pathlib.Path(__file__).resolve().parents[1] / '.claude/skills/npc-skin-forge/scripts'
if not _SKILL.exists():                       # lessons #23 — 레포 경로 우선, 없으면 홈
    _SKILL = pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'
sys.path.insert(0, str(_SKILL))

import garments as g                                    # noqa: E402
from skinlib import Skin, ramp, ramp_lit                # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = zlib.crc32(b'cesare') % 100000                    # hash() 금지 — 빌드마다 달라진다


def matte(base, spread=0.22):
    """무광 직물(리넨·모직·캔버스) — 색상 회전 0, 채도 거의 고정, 명도 폭 좁게."""
    return ramp(base, spread=spread, hue=0.0, sat=0.03)


def leather(base, spread=0.32):
    """가죽 — 무광보다 «완전 조금만» 반사한다."""
    return ramp(base, spread=spread, hue=0.02, sat=0.06)


P = dict(
    skin=ramp('b8895e'),                    # 지중해 그을림 (오스카 c9906a·알브레히트 bd9068 과 다름)
    # ★1차 반려: 2f2418 은 8x8 안에서 «거의 검정 덩어리»가 돼 흰자 2px만 헤드라이트처럼
    #   튄다(오스카 4a3826 과 나란히 놓고 확인). 값을 올리고 램프는 좁게 유지.
    hair=ramp('453425', spread=0.26),       # lessons #20: 넓은 램프 = 머리 반반
    # ★3차 반려: 수염을 hair 램프에서 뽑으니 머리와 같은 값이라 «입 주변 검은 바»가 됐다.
    #   skin-craft 규칙 = 피부보다 어둡고 «머리보다 밝게» → 중간 값으로 따로 뽑는다.
    beard=ramp('6a5240', spread=0.26),
    olive=matte('55603a', 0.24),            # 교차여밈 튜닉 — 마을 올리브
    cream=matte('c0b193', 0.22),            # 속셔츠 (상단 'sail')
    lin=matte('9c8f74', 0.20),              # 여밈 안감 — 담요와 밝기 경쟁을 피해 한 단 낮춘다
    wine=matte('7d3f42', 0.24),             # 허리 새시 — 튜닉보다 두 단 밝다
    ink=matte('3a3a4a', 0.22),              # 승마바지
    gaiter=leather('8a6a45', 0.30),         # 무릎 아래 각반 — 장화와 두 단 벌린 탠 가죽
    boot=leather('2b2018', 0.28),           # 짧은 장화
    blanket=matte('cbbb95', 0.20),          # 안장담요 바탕
    burg=matte('6e2f3a', 0.24),             # 담요 줄 1
    ochre=matte('a8813a', 0.24),            # 담요 줄 2
    brass=ramp_lit('b08d3c'),               # 금속만 진짜 하이라이트
)


def _rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _seal_fringe(s, skin_r, hair_r, rows=2):
    """앞머리(0~2행) 안에 남은 «고립된 피부 1px»을 머리색으로 막는다.

    lessons #22 — 머리 한가운데의 밝은 점은 8x8 에서 얼굴의 흠집으로 읽힌다.
    판정은 밝기가 아니라 «피부 램프와 머리 램프 중 어디에 더 가까운가»(RGB 거리)로
    한다 — 백발·반백이면 밝기 비교가 뒤집히기 때문.
    """
    f = s.f('head', 'front')
    skin_t = [_rgb(c) for c in skin_r]
    hair_t = [_rgb(c) for c in hair_r]

    def near(c, table):
        return min(sum((c[i] - t[i]) ** 2 for i in range(3)) for t in table)

    for y in range(0, rows):
        for x in range(8):
            c = f.get(x, y)[:3]
            if near(c, skin_t) < near(c, hair_t):
                f.px(x, y, g.hair_lit(hair_r, x, y))


def _moustache(s, beard_r):
    """콧수염 1행 + 그 안의 입선 — goatee 만 있으면 턱 밑 얼룩으로만 읽힌다.

    수염 값 규칙(skin-craft): 피부보다 어둡고 머리보다 밝게. 입은 콧수염 «안»에
    한 단 어두운 2px 선으로 (근검정 2px 는 구멍처럼 보인다).
    """
    b = g._beard_ramp(beard_r)
    f = s.f('head', 'front')
    f.row(6, b[3], 2, 5)                                 # 콧수염 — 한 단 밝게(skin-craft)
    f.px(3, 6, b[1]); f.px(4, 6, b[1])                   # 입선 — 콧수염 «안»의 한 단 어두운 2px


def build():
    s = Skin()
    skin, hair = P['skin'], P['hair']

    # ── 머리: 피부 → 머리카락 → 수염 → 얼굴 피처 (나중 것이 위에 남는다)
    g.head_base(s, skin, seed=SEED)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=2, back=6, seed=SEED, part_x=4)   # ★이마 한 행을 연다(2차)
    g.beard(s, P['beard'], style='goatee', y=5, seed=SEED)   # 턱 x3~4, 6~7행
    _moustache(s, P['beard'])                                  # ★콧수염 — 오스카·알브레히트와 갈리는 점
    g.face_shape(s, skin, jaw='long', temple=True)       # 마른 얼굴
    g.wrinkles(s, skin, crow=True, forehead=True)        # 40대 — 이마 주름 1px
    _seal_fringe(s, skin, hair, rows=2)                  # ★얼굴 피처 «뒤»에 (lessons #22)
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['brown']), y=4, gaze=0, iris_idx=1)
    g.brow(s, hair[1], y=3)

    # ── base: 크림 속셔츠 · 잉크 승마바지 · 짧은 장화
    g.tunic(s, P['cream'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07)
    g.sleeves(s, P['cream'], y0=0, y1=9, rolled=('arm_l', 6), skin_r=skin,
              seed=SEED, grain=0.07)                     # ★왼팔만 걷음 (7~9행 맨살)
    g.hands(s, skin, rows=2)
    g.pants(s, P['ink'], y0=0, y1=8, seed=SEED)
    g.boots(s, P['boot'], rows=3, toe=True, cuff=True)   # 9~11 = 발목 장화

    # ── outer: 교차 여밈 튜닉
    #   ★1차 반려: hem=10 이면 11행의 크림 속옷이 «엉덩이를 감는 밝은 띠»가 됐다(새시와
    #     경쟁). 11까지 덮고 크림은 칼라·소매단·여밈에서만 숨쉬게 한다.
    #   ★4차: 여밈 대각선을 x6→x3 으로 옮겨 담요(x0~x2)와 가슴 좌우를 나눈다.
    g.wrap_tunic(s, P['olive'], y0=0, hem=11, seed=SEED, cross=6,
                 lining=P['lin'], grain=0.08)
    s.form_fill('arm_r', P['olive'], 0, 8, layer='outer', base_idx=3, top=True)
    s.hem('arm_r', 8, P['olive'], layer='outer')         # 오른팔: 손목까지 긴 소매
    s.form_fill('arm_l', P['olive'], 0, 5, layer='outer', base_idx=3, top=True)
    s.hem('arm_l', 5, P['olive'], layer='outer')         # 왼팔: 걷어올린 소매단
    s.band('arm_l', 5, 5, P['olive'][4], layer='outer')  # 말린 천의 립

    # ── 허리 새시 2행 + 놋쇠 버클 (악센트 1/2)
    s.band('body', 6, 6, P['wine'][3], layer='outer')
    s.band('body', 7, 7, P['wine'][2], layer='outer')
    s.shade_ring('body', 8, layer='outer', amount=0.30)  # 새시가 튜닉에 드리우는 그림자
    s.buckle('body', 6, P['brass'], layer='outer')

    # ── 각반: 무릎 아래 6~8행을 가죽으로 감고 끈 자국, 장화(9~11) 바로 위에서 끝난다
    #   ★1차 반려: 상단 립을 gaiter[4](최명도)로 두니 두 다리를 가로지르는 «밝은 가터»가
    #     됐다. 각반의 위쪽은 조이는 «어두운 끈»이어야 무릎 아래로 읽힌다.
    for part in ('leg_r', 'leg_l'):
        s.form_fill(part, P['gaiter'], 6, 8, layer='outer', base_idx=3)
        s.band(part, 6, 6, P['gaiter'][1], layer='outer')            # 상단 조임끈
        s.f(part, 'front', 'outer').row(8, P['gaiter'][1])           # 아래는 그늘

    # ── 어깨에 접어 걸친 안장담요
    #   ★1차 반려: x6·x7 에 두니 wrap 여밈의 밝은 안감 대각선(x5→x3)과 같은 쪽에서
    #     겹쳐 «가슴 한복판의 정체불명 밝은 덩어리»가 됐다. 여밈이 비우는 x0·x1
    #     (캐릭터 오른쪽 어깨)로 옮긴다 — 걷어올린 왼소매와도 반대편이라 비대칭이 산다.
    bf = s.f('body', 'front', 'outer')
    bb = s.f('body', 'back', 'outer')
    bt = s.f('body', 'top', 'outer')
    br = s.f('body', 'right', 'outer')
    for y in range(0, 6):                                            # 어깨에서 허리까지
        for x in (0, 1, 2):
            bf.px(x, y, P['blanket'][3 if x == 1 else 2])
            bb.px(7 - x, y, P['blanket'][2])
        br.row(y, P['blanket'][2])
    for y, col in ((2, P['burg']), (4, P['ochre'])):                 # 접힌 줄무늬 2개
        bf.row(y, col[3], 0, 2)
        bb.row(y, col[2], 5, 7)
        br.row(y, col[2])
    bf.row(5, P['blanket'][1], 0, 2)                                 # 접힌 아랫단 두께
    bb.row(5, P['blanket'][1], 5, 7)
    br.row(5, P['blanket'][1])
    for x in (0, 1, 2):
        bt.col(x, P['blanket'][4], 0, 3)                             # 어깨를 실제로 넘는다

    # ── 소품: 오른 허벅지 말빗 주머니(악센트 2/2) + 왼 무릎 헝겊 패치
    g.pouch(s, P['gaiter'], part='leg_r', face='front', x=1, y=1, w=2, h=3,
            metal=P['brass'])
    g.patch(s, 'leg_l', 'front', P['gaiter'], x=1, y=3, w=2, h=2, layer='outer')

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'cesare.png'))


if __name__ == '__main__':
    print(build())
