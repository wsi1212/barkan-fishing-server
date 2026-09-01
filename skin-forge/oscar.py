#!/usr/bin/env python3
"""오스카 — &b[말 대여], 스폰마을(바르칸 항구), citizensId 43.

CHARACTER BRIEF  (npc_brief.py 마부 --village --radius 130 에서 뽑은 근거)
  역할   horseRental=true. 대사 없음(기능형) → 역할 + 지역이 컨셉의 전부.
  지역   바르칸 항구 < 탄광 < 바르칸 < 바르칸 연안 < 원양 — 유럽풍 스폰마을.
  이웃   반경 130 안: 할아버지(길잡이)·페리선장·헬가(물고기 판매)·클라우스(상점)·
         브루노(섬상점)·마르타(시장안내) 등. 전부 노인/제복/상인 실루엣이라
         "말을 직접 다루는 노동자" 실루엣은 이 마을에서 아직 안 쓰였다.
  ★사고 배경: 원래 텍스처가 Mojang 서버에서 blob 소실(404)되어 접속 클라이언트에
    기본 스티브로 보이던 것을 전면 재제작. 리컬러가 아니라 새 스킨.

DESIGN SPEC
  나이/체격  30대 후반, 다부지고 어깨가 넓다 — 종일 말을 다루는 노동
  실루엣     크림 리넨 셔츠(속옷) + 열린 가죽 조끼(짧은 밑단, 앞이 벌어져 셔츠가 보임)
             + 카키 캔버스 승마바지 + 무릎 위까지 오는 가죽 승마부츠 + 벨트(편자 버클)
  팔레트     셔츠=크림 리넨(matte) / 조끼=진갈색 가죽(leather) / 바지=올리브 카키(matte,
             조끼와 색상 자체를 갈라 하체가 한 덩어리로 안 뭉치게) / 부츠=제일 어두운
             가죽(leather) / 로프=삼끈색(matte) / 버클·리벳=놋쇠(ramp_lit, 유일한 진짜
             하이라이트)
  비대칭     오른쪽 소매만 걷어올림(맨 팔뚝 노출) · 왼쪽 허벅지에 고삐/로프 타래 파우치
  정체 모티프 왼쪽 허벅지의 로프 타래(고삐) — 가슴 로고 대신 소지품으로 직업을 말한다.
             ★편자 스탬프를 벨트 갭에 시도했다가 조끼 단추와 겹쳐 «세로로 늘어선 점»
             으로 뭉쳐 보여 폐기(1차 렌더 반려, 아래 REJECT 참고) — 벨트는 놋쇠 사각
             버클 하나로 단순하게 마감
  얼굴       그을린 피부 · 짧은 짙은 갈색 머리(가르마) · 턱수염 그루터기(stubble) ·
             호박빛 갈색(hazel) 눈, gaze=0(기본) · 코 생략(기본) · 표식 없음(마부는
             특별한 개성 표식이 필요 없다 — 실루엣과 소지품이 이미 직업을 말한다)
             ★흰자는 순백(ece8dd) 대신 otto 계열의 c9c4b8 — 그을린 피부 위에서
             순백은 도드라져 «흰 눈덩이» 두 개로 읽힌다(1차 렌더 반려)

REJECT LOG (1차 렌더 자기비평, 오너에게 보이기 전에 걸러낸 것)
  ① 벨트 갭에 4x4 편자 스탬프 + 조끼 단추 3점이 같은 x2~4 열에서 충돌 →
     세로로 늘어선 놋쇠 점 6~7개로 뭉쳐 «지퍼/단추줄»처럼 보임.
     → 조끼 단추 제거 + 편자 스탬프 폐기, 벨트는 buckle() 기본 사각 버클 하나로.
  ② 흰자 ece8dd가 그을린 피부(c9906a)와 대비가 너무 커 눈이 «하얀 덩어리»로 도드라짐.
     → c9c4b8로 낮춤(otto와 동일 처방 — 그을린 피부에는 이 톤이 자연스럽다).
  ③ 로프 파우치 2x2가 축소하면 «노란 배지»로만 보이고 «타래»로 안 읽힘.
     → 3x3으로 키움(lessons.md #9: 소품은 컴팩트한 덩어리라도 일정 크기 이상이어야
       형태로 읽힌다).
"""
import pathlib
import sys
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]
                       / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                                    # noqa: E402
from skinlib import Skin, ramp, ramp_lit                # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = zlib.crc32(b'oscar') % 100000                     # hash() 금지 — 빌드마다 달라진다


def matte(base, spread=0.22):
    """무광 직물(리넨·캔버스) — 색상 회전 0, 채도 거의 고정, 명도 폭 좁게."""
    return ramp(base, spread=spread, hue=0.0, sat=0.03)


def leather(base, spread=0.34):
    """가죽 — 무광보다 «완전 조금만» 반사한다."""
    return ramp(base, spread=spread, hue=0.02, sat=0.06)


P = dict(
    skin=ramp('c9906a'),
    hair=ramp('4a3826', spread=0.26),      # lessons.md 20장: 넓은 램프=머리 반반. 좁게.
    linen=matte('d9cfb4', 0.22),            # 셔츠 — 밝은 천은 여기 하나뿐
    vest=leather('5c3820', 0.32),           # 조끼 — 진갈색 가죽
    pants=matte('5c5c3e', 0.22),            # 캔버스 — 조끼와 색상(hue)까지 갈라 하체 분리
    boot=leather('2e2015', 0.30),           # 제일 어두운 가죽
    rope=matte('b8975c', 0.24),             # 고삐/로프 타래
    brass=ramp_lit('b08d3c'),               # 금속만 진짜 하이라이트
)


def build():
    s = Skin()
    skin, hair = P['skin'], P['hair']

    # ---- 머리 (그을린 피부 -> 머리 -> 수염 -> 이목구비, 순서대로 나중 것이 위에 남는다)
    g.head_base(s, skin, seed=SEED)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=3, back=6, seed=SEED, part_x=3)
    g.beard(s, hair, style='stubble', y=5, seed=SEED)
    g.face_shape(s, skin, jaw='square', temple=True)     # 다부진 인상
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['hazel']), y=4, gaze=0, iris_idx=1)
    g.brow(s, hair[1], y=3, weight=2)
    g.mouth(s, skin, y=6, w=2)

    # ---- torso: linen shirt (base), leather vest open at front (outer)
    g.tunic(s, P['linen'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07)
    g.vest(s, P['vest'], y0=0, hem=9, gap=2, seed=SEED)

    # ---- arms: right sleeve rolled up — the asymmetry
    g.sleeves(s, P['linen'], y0=0, y1=9, rolled=('arm_r', 6), skin_r=skin,
              seed=SEED, grain=0.07)
    g.hands(s, skin, rows=2)

    # ---- legs: canvas trousers, knee-high riding boots
    g.pants(s, P['pants'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['boot'], rows=5, toe=True, cuff=True)     # 5행 = 무릎 위까지 올라오는 부츠

    # ---- belt: plain brass buckle (a horseshoe stamp at this scale just read as
    # a column of loose dots once it sat next to the vest gap — dropped it;
    # lessons.md #9, compact blobs only)
    g.belt(s, P['boot'], y=7, accent=P['brass'], buckle=True)

    # ---- left thigh: coiled lead-rope — the identity motif + second asymmetry
    g.pouch(s, P['rope'], part='leg_l', face='front', x=1, y=1, w=3, h=3,
            metal=P['brass'])

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'oscar.png'))


if __name__ == '__main__':
    print(build())
