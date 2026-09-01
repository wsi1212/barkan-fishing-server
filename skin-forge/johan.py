#!/usr/bin/env python3
"""요한 — &a[Q] 길드접수원, 스폰마을(바르칸 항구), citizensId 162.

CHARACTER BRIEF  (npc_brief.py 길드접수원 --village --radius 60 에서 뽑은 근거)
  역할   대화/퀘스트 전용. 튜토00(★게임 최초 퀘스트)을 지급 — 신규 유저가 접속 후
         가장 먼저 마주치는 NPC 중 하나. 대사: "낚시사 길드 접수창구", "명부·조업기록·
         등급심사·분쟁조정을 처리하는 서기", "이름을 함부로 안 적는다".
  ★사고   saves.yml 실측 결과 `traitnames`에 skintrait 이 나열돼 있는데 `traits:` 안에
         실제 데이터가 없었다(오스카는 blob 이 404 였지 데이터는 있었다 — 이쪽은 아예
         스킨 데이터가 없는 더 심한 케이스). 접속 클라이언트에는 처음부터 기본 스티브로
         보이고 있었을 것 — 신규 유저 온보딩 첫 화면이라 임팩트가 오스카보다 크다.
  지역   바르칸 항구(스폰마을). 이웃 반경 60: 군터(대장간)·잉그리드(길드)·라이문트
         (유저마켓)·디트리히(퀘스트)·펠릭스(대장간안내)·하겐(길드장)·세르간·힐데(회복)·
         루드비히(여관)·종지기·에르빈(랭킹). 전부 실외 노동/제복 계열 — «실내 서기»
         실루엣은 이 마을에 아직 없다.

DESIGN SPEC
  나이/체격  30대 초반, 마르고 자세가 곧다 — 종일 앉아 장부를 쓰는 사람. 오스카(마부,
             다부진 노동자)와 체형·실루엣 반대
  실루엣     크림 리넨 셔츠(속옷) + 짙은 남색 조끼(열린 형, 격식) + 양팔 가죽 서기 토시
             (잉크 안 묻게 소매를 조이는 밴드) + 짙은 회색 바지 + 낮은 단화
  팔레트     셔츠=크림 리넨(matte) / 조끼=짙은 남색(matte, 이웃 중 아무도 안 쓴 차가운
             색상 — 대장간=불그스름 가죽·철, 여관=따뜻한 갈색과 갈린다) / 바지=짙은
             회색(matte) / 토시·단화=진갈색 가죽(leather) / 악센트=철회색 단추 소량
  비대칭     오른팔에만 서기 토시(잉크 묻지 않게 조인 소매) · 왼쪽 벨트에 잉크병 파우치
  정체 모티프 벨트의 잉크병 파우치 — «명부에 이름을 올리는 사람»의 도구. 가슴 로고 없음
  얼굴       실내 근무라 갈색 피부보다 옅은 톤 · 짙은 갈색 단정한 머리(가르마) · 수염
             없음(말끔한 서기) · 회갈(hazel) 눈, gaze=0(기본) · 코 생략(기본) · 표식 없음
"""
import pathlib
import sys
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]
                       / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                                    # noqa: E402
from skinlib import Skin, ramp, ramp_lit                # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = zlib.crc32(b'johan') % 100000


def matte(base, spread=0.22):
    return ramp(base, spread=spread, hue=0.0, sat=0.03)


def leather(base, spread=0.34):
    return ramp(base, spread=spread, hue=0.02, sat=0.06)


P = dict(
    skin=ramp('d3a67e'),
    hair=ramp('3c2c1e', spread=0.24),
    linen=matte('d9cfb4', 0.22),
    vest=matte('2c3446', 0.24),             # 짙은 남색 — 마을에서 아무도 안 쓴 색상
    pants=matte('4a4a4a', 0.22),
    hide=leather('3a2c1e', 0.30),           # 토시·단화
    pewter=ramp_lit('8f8f8f'),              # 단추 — 차가운 회색 금속, 놋쇠 없음
)


def build():
    s = Skin()
    skin, hair = P['skin'], P['hair']

    g.head_base(s, skin, seed=SEED)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=3, back=5, seed=SEED, part_x=3)
    g.face_shape(s, skin, jaw='oval', temple=True)
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['hazel']), y=4, gaze=0, iris_idx=1)
    g.brow(s, hair[1], y=3)
    g.mouth(s, skin, y=6, w=2)

    # ---- torso: linen shirt (base) + dark navy vest, buttoned (outer)
    g.tunic(s, P['linen'], y0=0, y1=11, collar=True, seed=SEED, grain=0.06)
    g.vest(s, P['vest'], y0=0, hem=10, gap=2, seed=SEED, buttons=P['pewter'])

    # ---- arms: right forearm banded with a clerk's ink-guard cuff (asymmetry)
    g.sleeves(s, P['linen'], y0=0, y1=9, seed=SEED, grain=0.06)
    g.hands(s, skin, rows=2)
    s.band('arm_r', 5, 5, P['hide'][3], layer='outer')
    s.shade_ring('arm_r', 6, layer='outer', amount=0.28)

    # ---- legs: grey trousers, low shoes (not tall boots — a desk clerk, not a rider)
    g.pants(s, P['pants'], y0=0, y1=9, seed=SEED)
    g.boots(s, P['hide'], rows=2, toe=True, cuff=True)

    # ---- belt + inkwell pouch (identity motif, second asymmetry)
    g.belt(s, P['hide'], y=9, accent=P['pewter'], buckle=True)
    g.pouch(s, P['hide'], part='leg_l', face='front', x=1, y=1, w=2, h=2,
            metal=P['pewter'])

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'johan.png'))


if __name__ == '__main__':
    print(build())
