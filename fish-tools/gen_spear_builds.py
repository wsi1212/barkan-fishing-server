#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""창(작살) 빌드 카탈로그 생성기 — parts.json / recipes.json 재생성.

★수치를 바꿀 땐 이 파일을 고쳐 다시 돌린다. 손으로 JSON을 만지지 말 것.
   사용법: python3 gen_spear_builds.py <BlockShip 데이터 폴더> [--shops]
           --shops = npc.json 마을 상점(클라우스=스폰, 파리드=사막)에 작살 레시피 배분까지 갱신

────────────────────────────────────────────────────────────────────────────
설계 (balance.md 준수 — 2026-08-03 사다리 개편)
────────────────────────────────────────────────────────────────────────────
낚싯대와 같은 골격: **마을마다 / 빌드마다 여러 등급이 이어지는 사다리** + 복합형.

  §17 등급별 필요 레벨   E=1  D=5  C=10  B=20  A=40  S=60  ← ★고정값이 아니라 <b>하한</b>
  §7  등급별 가격대       ★2026-08-05 리프라이싱 (낚싯대와 동일 밴드 — 시리즈 짝 유지)
                          D 9,000~22,000 / C 26,000~65,000 / B 80,000~210,000
                          A 780,000~1,940,000 / S 3,400,000~3,620,000
                          근거 = balance-audit/scripts/price_ladder.py (구간 수입의 45%)
                          ※작살은 내구·미끼가 없어 한계비용 0 — 유지비 도입은 별건(08-03 권고 5)
  §17 마을 분포           스폰 E~B · 사막 B~A · 상단 A · 히든/전설 A~S
  §7  상점·대장간 천장 = A (S는 값이 아니라 전설 재료로 막는다)

★**레벨·가격은 같은 등급 안에서도 갈린다.** 등급이 바닥을 깔고, 그 위에서 실제 성능
  점수(POWER_W 가중합)로 등급 밴드 안 위치가 정해진다 — 같은 A라도 상단 균형형(약)과
  왕도 복합형(강)의 렙제가 다르다. 강한 물건일수록 늦게 열리고 비싸다.

빌드 5종(주력 + 전용 보상 스탯):
  행운형 = 행운 + 판매보너스   속도형 = 수영속도·돌진쿨감 + 경험치
  호흡형 = 수중호흡·호흡시간 + 더블찬스  크리형 = 크리확률·크리배율 + 크기
  공격형 = 공격력·공격속도 + 트리플찬스(A부터)

복합형(왕도·전설) = 두 계통을 각 80%씩. 순수형보다 정점은 낮고 범용은 높다.

마을 성격(같은 등급이라도 형태가 달라 서로 상위호환이 되지 않게):
  스폰 = 기본형 / 사막 = 극단형(주력↑ 보조↓) / 상단 = 균형형(주력↓ 보조↑) / 왕도 = 복합형

★수중호흡은 빌드와 무관하게 등급 하한 보장(BREATH_FLOOR). 물속 체류시간이 없으면
  어떤 빌드든 작살질 자체가 성립하지 않는다(유저 판단). 코드(HarpoonManager.breathFloor)가
  강제하지만 데이터도 하한 이상으로 적어 로어·표를 일치시킨다.
"""
import json, shutil, sys, os

SRC = sys.argv[1]
# --shops = npc.json 상점 NPC의 shopItems에 그 마을 작살 레시피를 배분(마을 상점에서 레시피 구매).
WRITE_SHOPS = "--shops" in sys.argv[2:]

# ── balance.md §17 등급 게이트 = 밴드 하한 ───────────────────────────────────
GRADE_LEVEL = {"E": 1, "D": 5, "C": 10, "B": 20, "A": 40, "S": 60}
# 같은 등급 안에서 성능에 따라 퍼지는 범위 (하한 = balance.md 필요레벨)
LEVEL_BAND = {"D": (5, 9), "C": (10, 18), "B": (20, 34), "A": (40, 55), "S": (60, 66)}
# balance.md §7 가격대 안에서 성능순으로 배치
# ★2026-08-05 전면 리프라이싱 — 낚싯대와 같은 밴드(price_ladder.py 산출).
PRICE_BAND = {"D": (9000, 22000), "C": (26000, 65000), "B": (80000, 210000),
              "A": (780000, 1940000), "S": (3400000, 3620000)}
# ★마을×등급 하위 밴드 — balance.md §17 성장경로(스폰 Lv1~20 → 사막 20~40 → 상단 40~ → 왕도 → 전설)를
#   지키려면 같은 B라도 스폰이 사막보다 먼저 열려야 한다. 없으면 위 등급 밴드 전체를 쓴다.
SUB_BAND = {
    ("스폰마을", "B"):  ((20, 27), (80000, 150000)),
    ("스폰마을", "C"):  ((10, 18), (26000, 65000)),
    ("사막마을", "B"):  ((26, 34), (140000, 210000)),
    ("사막마을", "A"):  ((40, 46), (780000, 1210000)),
    ("상단마을", "A"):  ((45, 52), (1210000, 1640000)),
    ("왕도", "A"):      ((50, 55), (1640000, 1940000)),
}
# 등급별 수중호흡 하한 — HarpoonManager.breathFloor와 반드시 같은 값.
BREATH_FLOOR = {"E": 5, "D": 8, "C": 10, "B": 13, "A": 15, "S": 18, "M": 20, "L": 22, "G": 25}
DURAB = {"D": 80, "C": 120, "B": 180, "A": 250, "S": 420}

# 성능 점수 가중치 — 서로 다른 단위를 한 눈금에 올려 "이게 저것보다 센가"를 판정한다.
# (balance-audit references/stat-values.md 상대가치를 창 기준으로 옮긴 값)
POWER_W = {
    "행운": 3.0, "크리확률": 1.6, "크리배율": 8.0, "공격력": 9.0, "공격속도": 1.0,
    "수영속도": 1.0, "돌진쿨감": 1.0, "수중호흡": 1.0,
    # ★호흡시간(2026-08-26 신설) — 잠수 1회당 실제 산소를 멈추는 초. 깊은물 타이머만 늘리는
    #   수중호흡보다 1초당 값이 나가서 1.5배로 센다. 코드=HarpoonManager.applyBreathOneShot.
    #   아직 어느 사다리·중립 라인에도 배정하지 않았다(배정은 별건 — 배정하면 같은 등급 밴드
    #   안 레벨·가격 순위가 같이 움직인다).
    "호흡시간": 1.5,
    "크기": 1.5, "판매보너스": 2.0, "경험치": 0.8, "더블찬스": 3.0, "트리플찬스": 4.0,
}

# ── 축별 주력 수치 (등급 사다리) ─────────────────────────────────────────────
#  ★S는 복합형(0.8배)으로만 존재한다 — 0.8을 곱해도 순수 A를 확실히 넘도록 A의 1.5배 안팎으로 잡는다.
PRIMARY = {
    "행운":     {"D": 3,  "C": 6,  "B": 10, "A": 16, "S": 30},
    "수영속도": {"D": 14, "C": 22, "B": 32, "A": 45, "S": 72},
    "돌진쿨감": {"D": 8,  "C": 12, "B": 20, "A": 30, "S": 52},
    "수중호흡": {"D": 16, "C": 26, "B": 38, "A": 55, "S": 95},
    # ★호흡시간 = 잠수 1회에 실제 산소를 멈추는 초(2026-08-26 신설). 수중호흡의 ~40%로 잡는다 —
    #   바닐라 산소가 15초라 «호흡시간+15초» 가 실제 잠수 한 번의 길이가 되는데, 이걸 수중호흡
    #   (강제이동 한도)까지 올리면 수면에 올라올 이유가 사라져 두 스탯 중 하나가 죽는다.
    "호흡시간": {"D": 6,  "C": 10, "B": 15, "A": 22, "S": 38},
    "크리확률": {"D": 5,  "C": 9,  "B": 14, "A": 22, "S": 36},
    "크리배율": {"D": 1,  "C": 1,  "B": 2,  "A": 4,  "S": 7},
    "공격력":   {"D": 2,  "C": 3,  "B": 4,  "A": 5,  "S": 7},   # 정점은 G(네더라이트 8)
    "공격속도": {"D": 10, "C": 18, "B": 24, "A": 34, "S": 62},
}
# 빌드별 전용 보상 스탯 (balance.md §8 부품 기준보다 한 급 아래 — 작살은 하나만 드는 단일 아이템)
REWARD = {
    "판매보너스": {"D": 2, "C": 4,  "B": 7,  "A": 12, "S": 22},
    "경험치":     {"D": 5, "C": 10, "B": 15, "A": 25, "S": 45},   # ★2026-08-26 ×2/3 (구 8/14/22/35/65)
    "더블찬스":   {"D": 1, "C": 2,  "B": 3,  "A": 5,  "S": 10},
    "크기":       {"D": 2, "C": 4,  "B": 6,  "A": 10, "S": 18},
    "트리플찬스": {"D": 0, "C": 0,  "B": 0,  "A": 2,  "S": 4},   # A부터만
}
# 주력이 아닌 축이 받는 기본치 (어떤 빌드든 최소한의 물속 활동은 된다)
BASE = {
    "수중호흡": {"D": 10, "C": 12, "B": 16, "A": 22, "S": 30},
    "수영속도": {"D": 5,  "C": 8,  "B": 12, "A": 18, "S": 24},
    "공격력":   {"D": 1,  "C": 2,  "B": 2,  "A": 3,  "S": 4},
}

# 빌드 정의 — 주력 축 + 보상 스탯 + 제작 재료(하위등급용, 상위등급용)
BUILDS = {
    "행운형": {"axes": ["행운"],               "reward": "판매보너스", "mat": ("행운의구슬", "행운의매듭")},
    "속도형": {"axes": ["수영속도", "돌진쿨감"], "reward": "경험치",     "mat": ("거대비늘", "거대비늘")},
    "호흡형": {"axes": ["수중호흡", "호흡시간"], "reward": "더블찬스",   "mat": ("산호조각", "진주코어")},
    "크리형": {"axes": ["크리확률", "크리배율"], "reward": "크기",       "mat": ("안개수정", "자수정")},
    "공격형": {"axes": ["공격력", "공격속도"],  "reward": "트리플찬스", "mat": ("강화철괴", "강화철괴")},
}
# 마을 성격 — (주력 배수, 보조·보상 배수)
SHAPE = {"기본형": (1.00, 1.00), "극단형": (1.20, 0.70), "균형형": (0.90, 1.30)}
# 복합형은 두 계통을 이 배수로 섞는다 — 순수형보다 정점은 낮고 범용은 높다.
HYBRID_SCALE = 0.8

# ── 사다리: (이름, 빌드, 등급, 마을(recipe village), 출처, 성격) ─────────────
LADDER = [
    # ═══ 스폰마을 — E~B 기본형. 빌드마다 D→C→B (balance.md 성장경로 Lv1~20) ═══
    ("물때 작살",   "행운형", "D", "스폰", "스폰마을", "기본형"),
    ("만조 작살",   "행운형", "C", "스폰", "스폰마을", "기본형"),
    ("조수의 작살", "행운형", "B", "스폰", "스폰마을", "기본형"),
    ("여울 작살",   "속도형", "D", "스폰", "스폰마을", "기본형"),
    ("급류 작살",   "속도형", "C", "스폰", "스폰마을", "기본형"),
    ("해류 작살",   "속도형", "B", "스폰", "스폰마을", "기본형"),
    ("갯벌 작살",   "호흡형", "D", "스폰", "스폰마을", "기본형"),
    ("해녀 작살",   "호흡형", "C", "스폰", "스폰마을", "기본형"),
    ("잠수부 작살", "호흡형", "B", "스폰", "스폰마을", "기본형"),
    ("벼린 작살",   "크리형", "D", "스폰", "스폰마을", "기본형"),
    ("예봉 작살",   "크리형", "C", "스폰", "스폰마을", "기본형"),
    ("섬광 작살",   "크리형", "B", "스폰", "스폰마을", "기본형"),
    ("쇠날 작살",   "공격형", "D", "스폰", "스폰마을", "기본형"),
    ("강철날 작살", "공격형", "C", "스폰", "스폰마을", "기본형"),
    ("파도날 작살", "공격형", "B", "스폰", "스폰마을", "기본형"),

    # ═══ 사막마을 — B~A 극단형. 주력이 튀고 보조가 얇다 ═══
    ("사구 작살",       "행운형", "B", "사막", "사막마을", "극단형"),
    ("신기루 작살",     "행운형", "A", "사막", "사막마을", "극단형"),
    ("열풍 작살",       "속도형", "B", "사막", "사막마을", "극단형"),
    ("모래바람 작살",   "속도형", "A", "사막", "사막마을", "극단형"),
    ("우물 작살",       "호흡형", "B", "사막", "사막마을", "극단형"),
    ("오아시스 작살",   "호흡형", "A", "사막", "사막마을", "극단형"),
    ("전갈 작살",       "크리형", "B", "사막", "사막마을", "극단형"),
    ("독전갈 작살",     "크리형", "A", "사막", "사막마을", "극단형"),
    ("사막칼날 작살",   "공격형", "B", "사막", "사막마을", "극단형"),
    ("사막군주의 작살", "공격형", "A", "사막", "사막마을", "극단형"),

    # ═══ 상단마을 — A 균형형(정밀·판매). 주력은 낮고 보조가 두껍다 ═══
    ("행상인의 작살", "행운형", "A", "상단", "상단마을", "균형형"),
    ("쾌속선 작살",   "속도형", "A", "상단", "상단마을", "균형형"),
    ("심해교역 작살", "호흡형", "A", "상단", "상단마을", "균형형"),
    ("세공사의 작살", "크리형", "A", "상단", "상단마을", "균형형"),
    ("호위대 작살",   "공격형", "A", "상단", "상단마을", "균형형"),
]

# ── 복합형: (이름, 빌드1, 빌드2, 등급, 마을, 출처) ───────────────────────────
#  ★이름은 낚싯대와 같은 <b>시리즈</b>로 맞춘다 — "◯◯ 작살"과 "◯◯ 낚싯대"가 한 세트로 읽히게
#    (gen_rod_builds.py의 HYBRIDS와 시리즈명이 1:1 대응. 한쪽만 고치지 말 것.)
#    빌드 조합은 무기별로 다르다 — 창과 낚싯대의 스탯 어휘 자체가 다르기 때문(같은 시리즈,
#    다른 특기). 시리즈명이 마을·티어를 알려주고 빌드는 로어의 "빌드" 줄이 알려준다.
HYBRIDS = [
    ("다목적 작살",    "호흡형", "공격형", "C", "스폰", "스폰마을"),
    ("겸업 작살",      "행운형", "크리형", "B", "스폰", "스폰마을"),
    ("만능 작살",      "호흡형", "행운형", "B", "스폰", "스폰마을"),
    ("유목상단 작살",  "행운형", "속도형", "B", "사막", "사막마을"),
    ("사막개척 작살",  "공격형", "호흡형", "B", "사막", "사막마을"),
    ("대상단 작살",    "행운형", "호흡형", "A", "사막", "사막마을"),
    ("사막탐사 작살",  "크리형", "공격형", "A", "사막", "사막마을"),
    ("정산가의 작살",  "크리형", "행운형", "A", "상단", "상단마을"),
    ("항해사의 작살",  "속도형", "행운형", "A", "상단", "상단마을"),
    ("중개인의 작살",  "크리형", "속도형", "A", "상단", "상단마을"),
    ("왕실 작살",      "행운형", "크리형", "A", "왕도", "왕도"),
    ("근위 작살",      "공격형", "크리형", "A", "왕도", "왕도"),
    ("왕도 상회 작살", "호흡형", "행운형", "A", "왕도", "왕도"),
    ("왕립 서고 작살", "크리형", "호흡형", "A", "왕도", "왕도"),
    ("왕립 순찰 작살", "속도형", "호흡형", "A", "왕도", "왕도"),
    # 전설 S — 대장간 천장(A)은 값이 아니라 재료(바르칸핵)로 지킨다. 낚싯대 전설 2종과 같은 시리즈.
    ("바르칸 작살",    "행운형", "크리형", "S", "왕도", "히든-전설"),
    ("천공의 작살",    "호흡형", "공격형", "S", "왕도", "히든-전설"),
]

# ── 기존 중립 라인 재조정 (balance.md 등급/레벨/가격대에 맞춤) ────────────────
#  ★철 작살은 튜토리얼 보상(튜토_작살2) — D등급이지만 레벨제한 1. 받자마자 못 쓰면 안 된다.
#  중립 라인은 "무난하지만 특화 없음" 자리라 각 등급 밴드의 <b>바닥 레벨·바닥 가격</b>에 둔다.
#  ★2026-08-05 리프라이싱 — 새 밴드의 바닥 가격으로 이동(D 9,000 / B 80,000 / A 780,000).
#  네더라이트 작살(G)은 밴드 밖 만렙 트로피 — 구 999,999가 S 상한의 11.1배였던 상대위치를 유지해
#  3,620,000 × 11.1 ≈ 40,000,000. (Lv70→100 구간 수입 약 1.7억의 23%.)
LEGACY = {
    "나무 작살":       ("E", 0,        60,  "수중호흡:5,수영속도:5,공격력:1",   1,   "튜토"),
    "철 작살":         ("D", 9000,     100, "수중호흡:10,수영속도:10,공격력:2", 1,   "튜토"),
    "강철 작살":       ("B", 80000,    160, "수중호흡:18,수영속도:23,공격력:3", 20,  "대장간"),
    "다이아 작살":     ("A", 780000,   260, "수중호흡:30,수영속도:26,공격력:4", 40,  "대장간"),
    "네더라이트 작살": ("G", 40000000, 320, "수중호흡:70,수영속도:45,공격력:8", 100, "대장간"),
}

# ── 심해 전용 심층 티어 ──────────────────────────────────────────────────────
# 7챕터 강하 준비의 권위 데이터. parts.json을 직접 고치지 않고 이 생성기에서만 산출한다.
# 야간투시는 심해에서만 의미가 있는 작살 전용 스탯이며, 1,000초 호흡은 최심부 통행권이다.
DEEP_SPEARS = [
    ("심해 잠수 작살", "S", 3480000, 520,
     "수중호흡:1000,야간투시:1,수영속도:55,공격력:8,돌진쿨감:18", 68, "심해", "왕도",
     ["진주코어", "안개수정"]),
    ("압력관통 작살", "S", 3550000, 560,
     "수중호흡:1000,야간투시:1,수영속도:48,공격력:12,공격속도:42", 69, "심해", "왕도",
     ["별빛진주", "압축흑정석"]),
    ("심연의 작살", "S", 3620000, 600,
     "수중호흡:1000,야간투시:2,수영속도:70,공격력:14,공격속도:50,돌진쿨감:28", 70, "심해", "왕도",
     ["바르칸핵", "별빛진주"]),
]
#  ★id는 HP90+ 예약대역을 쓴다 — 카탈로그가 HP02부터 순번을 먹으므로 낮은 번호를 쓰면 카탈로그
#    레시피를 덮어써 그 작살이 영구 미획득이 된다(2026-08-05 실제 사고: HP30/31/32가 모래바람·
#    독전갈·대상단 작살을 지워 사막 A 3종이 제작 불가였다). main()의 충돌 검사가 재발을 막는다.
LEGACY_RECIPES = [
    ("HP90", "강철 작살", "",       [("단단한자루", 10), ("강철심", 18), ("강화철괴", 18), ("진주", 12)]),
    ("HP91", "다이아 작살", "왕도", [("단단한자루", 20), ("강철심", 40), ("강화다이아몬드", 24),
                                     ("별빛진주", 8), ("압축흑정석", 30)]),
    ("HP92", "네더라이트 작살", "", [("단단한자루", 32), ("네더라이트주괴", 8), ("강화네더라이트파편", 24),
                                     ("바르칸핵", 2), ("용비늘", 4), ("별빛진주", 24)]),
]
# ── 레시피 해금 규약 ─────────────────────────────────────────────────────────
#  낚싯대·부품과 동일 모델(gen_rod_builds.py / gen_part_builds.py):
#    상점 NPC가 있는 마을(스폰=클라우스, 사막=파리드) → locked=true, 그 마을 상점에서 레시피 구매로 해금.
#    상점이 없는 마을(상단·왕도·전역) → locked=false, 그 마을 대장간에서 바로 제작(해금 경로가 없으니까).
SHOP_VILLAGES = ("스폰", "사막")

# ── 등급별 공통 제작 재료 ────────────────────────────────────────────────────
COMMON = {
    "D": [("단단한자루", 3), ("강철심", 2), ("물고기비늘", 6)],
    "C": [("단단한자루", 5), ("강철심", 6), ("물고기비늘", 12), ("진주", 4)],
    "B": [("단단한자루", 8), ("강철심", 14), ("진주", 12), ("압축흑정석", 5)],
    "A": [("단단한자루", 16), ("강철심", 26), ("진주", 26), ("압축흑정석", 18)],
    "S": [("단단한자루", 26), ("강철심", 50), ("별빛진주", 14), ("바르칸조각", 30),
          ("바르칸핵", 1), ("압축흑정석", 36)],
}
BUILD_MAT_QTY = {"D": 4, "C": 8, "B": 14, "A": 26, "S": 30}

# parts.json 스탯 표기 순서 (주력 → 기본 → 보상)
STAT_ORDER = ["행운", "크리확률", "크리배율", "공격력", "공격속도", "수영속도", "돌진쿨감",
              "수중호흡", "호흡시간", "크기", "판매보너스", "경험치", "더블찬스", "트리플찬스"]


def r(v):
    return max(1, int(round(v)))


def stats_for(build, grade, shape, hybrid_with=None):
    """빌드+등급+마을성격 → 스탯 dict. 복합형이면 두 빌드를 HYBRID_SCALE씩 섞는다."""
    pm, sm = SHAPE[shape]
    st = {}

    def apply(b, scale):
        spec = BUILDS[b]
        for ax in spec["axes"]:
            base = PRIMARY[ax][grade] * pm * scale
            if ax in ("공격력", "크리배율"):
                # ★정수 스탯은 반올림 때문에 등급 역전이 난다(A 극단형 5×1.2=6 vs S 복합형 7×0.8=6).
                #   전설(S)은 복합이어도 정수 주력만은 깎지 않아 "S가 A보다 약한" 상황을 막는다.
                if grade == "S":
                    base = PRIMARY[ax][grade] * pm
                # 복합형이라고 1 밑으로 깎지도 않는다(0이 되면 그 빌드가 사라진다).
                st[ax] = max(st.get(ax, 0), r(base))
            else:
                st[ax] = st.get(ax, 0) + r(base)
        rw = spec["reward"]
        val = REWARD[rw][grade] * sm * scale
        if val >= 1:
            st[rw] = st.get(rw, 0) + r(val)

    if hybrid_with:
        apply(build, HYBRID_SCALE)
        apply(hybrid_with, HYBRID_SCALE)
    else:
        apply(build, 1.0)

    for ax, table in BASE.items():
        st.setdefault(ax, r(table[grade] * (sm if ax != "공격력" else 1.0)))
    st["수중호흡"] = max(st["수중호흡"], BREATH_FLOOR[grade])
    # ★2026-08-26 — 2026-08-07 감사 ④ «장비 경험치 ×0.5» 는 생성기에만 들어가고 라이브엔
    #   끝내 반영되지 않았다(라이브 = 반값 전 값 그대로, C풀세팅 +154%). 유저 판단으로 강도를
    #   ×0.5 → ×2/3 로 완화하고, 나눗셈 대신 **표 자체를 손으로 떨어뜨린 정수**로 교체했다
    #   (15 이상은 5단위 — 기계식 ÷2 가 소수점 22.5 같은 값을 남겼던 문제도 같이 없앤다).
    return st


def power(st):
    """성능 점수 — 등급 밴드 안에서 레벨·가격 위치를 정하는 유일한 기준."""
    return sum(POWER_W.get(k, 0) * v for k, v in st.items())


def stat_str(st):
    return ",".join(f"{k}:{st[k]}" for k in STAT_ORDER if st.get(k))


def build_catalog():
    """(이름, 등급, 가격, 내구, 스탯, 레벨, 출처, 마을, 빌드재료들) — 레벨·가격은 점수 순으로 배치."""
    rows = []
    for (name, build, grade, village, origin, shape) in LADDER:
        st = stats_for(build, grade, shape)
        rows.append([name, grade, st, origin, village, [BUILDS[build]["mat"][0 if grade in "DCB" else 1]]])
    for (name, b1, b2, grade, village, origin) in HYBRIDS:
        st = stats_for(b1, grade, "기본형", hybrid_with=b2)
        idx = 0 if grade in "DCB" else 1
        mats = list(dict.fromkeys([BUILDS[b1]["mat"][idx], BUILDS[b2]["mat"][idx]]))
        rows.append([name, grade, st, origin, village, mats])

    # ★같은 등급 안에서 점수로 레벨·가격을 벌린다 (등급 = 하한, 성능 = 그 위 위치).
    out = []
    groups = {}
    for x in rows:
        # 하위 밴드가 있는 (마을, 등급)은 그 안에서, 없으면 등급 전체에서 성능순 배치.
        key = (x[3], x[1]) if (x[3], x[1]) in SUB_BAND else (None, x[1])
        groups.setdefault(key, []).append(x)
    for (vil, grade), band in groups.items():
        scores = [power(x[2]) for x in band]
        lo_s, hi_s = min(scores), max(scores)
        (lvl_lo, lvl_hi), (prc_lo, prc_hi) = SUB_BAND.get((vil, grade),
                                                          (LEVEL_BAND[grade], PRICE_BAND[grade]))
        for x, sc in zip(band, scores):
            t = 0.0 if hi_s == lo_s else (sc - lo_s) / (hi_s - lo_s)
            lv = int(round(lvl_lo + t * (lvl_hi - lvl_lo)))
            price = int(round((prc_lo + t * (prc_hi - prc_lo)) / 100.0) * 100)
            name, g, st, origin, village, mats = x
            out.append((name, g, price, DURAB[g], stat_str(st), lv, origin, village, mats, sc))
    # 심해 티어는 일반 S 밴드 점수 배치 대신 지정 레벨·호흡 1,000초를 보존한다.
    for name, grade, price, dur, stats, lv, origin, village, mats in DEEP_SPEARS:
        out.append((name, grade, price, dur, stats, lv, origin, village, mats,
                    sum(POWER_W.get(k, 0) * float(v) for k, v in
                        (x.split(":", 1) for x in stats.split(",")))))
    # 등급 → 레벨 순으로 정렬해 order/표가 사다리처럼 보이게
    gorder = {"D": 0, "C": 1, "B": 2, "A": 3, "S": 4}
    out.sort(key=lambda z: (gorder[z[1]], z[5]))
    return out


def check(catalog):
    """balance.md 대조 — 어긋나면 생성 자체를 막는다."""
    errs = []
    for (name, grade, price, dur, stats, lv, origin, village, mats, sc) in catalog:
        lo, hi = PRICE_BAND[grade]
        if not (lo <= price <= hi):
            errs.append(f"{name}: 가격 {price} 이 {grade} 대역 {lo}~{hi} 밖")
        if lv < GRADE_LEVEL[grade]:
            errs.append(f"{name}: 레벨 {lv} < {grade} 필요레벨 {GRADE_LEVEL[grade]}")
        got = dict(x.split(":", 1) for x in stats.split(","))
        if float(got.get("수중호흡", 0)) < BREATH_FLOOR[grade]:
            errs.append(f"{name}: 수중호흡 {got.get('수중호흡')} < 하한 {BREATH_FLOOR[grade]}")
    for name, (grade, price, dur, stats, lv, origin) in LEGACY.items():
        if grade in PRICE_BAND and price:
            lo, hi = PRICE_BAND[grade]
            if not (lo <= price <= hi):
                errs.append(f"{name}(중립): 가격 {price} 이 {grade} 대역 {lo}~{hi} 밖")
    if errs:
        raise SystemExit("balance.md 대조 실패:\n  - " + "\n  - ".join(errs))


def merge(items):
    """같은 재료가 두 번 나오면 수량 합산 — 조합대 재료 표시·소모 중복 방지."""
    out = []
    for it in items:
        for o in out:
            if o["typeOrMatId"] == it["typeOrMatId"]:
                o["qty"] += it["qty"]
                break
        else:
            out.append(it)
    return out


def main():
    catalog = build_catalog()
    check(catalog)

    parts_path = os.path.join(SRC, "parts.json")
    rec_path = os.path.join(SRC, "recipes.json")
    mats = json.load(open(os.path.join(SRC, "materials.json"), encoding="utf-8"))["materials"]

    def ing(mat_id, qty):
        m = mats.get(mat_id)
        if m is None:
            raise SystemExit(f"materials.json에 없는 재료: {mat_id}")
        return {"kind": "custom", "typeOrMatId": mat_id, "displayName": m["name"],
                "mcItem": m["mcItem"], "qty": int(qty)}

    # ── parts.json ──
    P = json.load(open(parts_path, encoding="utf-8"))
    shutil.copy(parts_path, parts_path + ".bak-spearladder")
    parts = P["parts"]

    owned = {c[0] for c in catalog} | set(LEGACY)
    stale = [n for n in parts["작살"] if n not in owned]   # 옛 세대(이름 바뀐 것) 정리
    for n in stale:
        del parts["작살"][n]
    P["order"] = [e for e in P["order"] if not (e[0] == "작살" and e[1] in stale)]
    order = P["order"]

    for name, (grade, price, dur, stats, lv, origin) in LEGACY.items():
        parts["작살"][name] = f"{name}|{grade}|{price}|{dur}|{stats}|{lv}|{origin}"
    for (name, grade, price, dur, stats, lv, origin, village, matlist, sc) in catalog:
        parts["작살"][name] = f"{name}|{grade}|{price}|{dur}|{stats}|{lv}|{origin}"

    have = {n for t, n in order if t == "작살"}
    for name in parts["작살"]:
        if name not in have:
            order.append(["작살", name])
    json.dump(P, open(parts_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"parts.json: 작살 {len(parts['작살'])}종 (카탈로그 {len(catalog)} + 중립 {len(LEGACY)}), 제거 {len(stale)}종")

    # ── recipes.json ──
    R = json.load(open(rec_path, encoding="utf-8"))
    shutil.copy(rec_path, rec_path + ".bak-spearladder")
    recs, cats = R["recipes"], R["categories"]

    cats.setdefault("작살", [])
    if "HP01" in cats.get("부품", []):
        cats["부품"].remove("HP01")
    if "HP01" in recs:
        recs["HP01"]["category"] = "작살"
    for rid in [k for k in list(recs) if k.startswith("HP") and k != "HP01"]:
        del recs[rid]                                   # 옛 세대 레시피 제거 후 재생성
    cats["작살"] = ["HP01"]

    def put(rid, name, village, ingredients):
        if rid in recs:
            raise SystemExit(f"레시피 id 충돌: {rid} ({name}) — 이미 {recs[rid]['resultPartName']}가 쓰고 있다")
        recs[rid] = {"id": rid, "category": "작살", "displayName": name,
                     "locked": village in SHOP_VILLAGES, "resultMode": "part", "drillTier": 0,
                     "village": village, "resultPartType": "작살", "resultPartName": name,
                     "ingredients": ingredients}
        cats["작살"].append(rid)

    for i, (name, grade, price, dur, stats, lv, origin, village, matlist, sc) in enumerate(catalog):
        items = [ing(m, q) for m, q in COMMON[grade]]
        qty = BUILD_MAT_QTY[grade]
        per = qty if len(matlist) == 1 else max(1, round(qty * 0.6))
        for j, m in enumerate(matlist):                 # 빌드 재료를 앞쪽에 — 무슨 창인지 재료로 읽히게
            items.insert(min(2 + j, len(items)), ing(m, per))
        put(f"HP{i + 2:02d}", name, village, merge(items))

    for rid, name, village, ings in LEGACY_RECIPES:
        put(rid, name, village, [ing(m, q) for m, q in ings])

    json.dump(R, open(rec_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    locked_n = sum(1 for v in recs.values() if v.get("resultPartType") == "작살" and v["locked"])
    print(f"recipes.json: 작살 레시피 {len(cats['작살'])}개 (해금필요 {locked_n}개 = 상점 판매분)")

    # ── NPC 상점 목록 (--shops) ──
    #   상점 NPC가 어느 마을 것인지는 <b>기존 shopItems의 출처</b>로 판정한다 — 작살이 아직
    #   안 들어간 상태에서도 붙일 수 있어야 하므로(부품 생성기처럼 자기 이름으로 매칭하면 첫 실행에 못 붙는다).
    if WRITE_SHOPS:
        npc_path = os.path.join(SRC, "npc.json")
        N = json.load(open(npc_path, encoding="utf-8"))
        shutil.copy(npc_path, npc_path + ".bak-spearshops")
        npcs = N["npcs"] if isinstance(N, dict) and "npcs" in N else N
        entries = npcs.items() if isinstance(npcs, dict) else [(x.get("id"), x) for x in npcs]

        origin_of = {}                     # 부품/낚싯대 이름 → 출처(마을)
        for cat_name, table in parts.items():
            for nm, spec in table.items():
                origin_of[nm] = spec.split("|")[6]
        all_spears = set(parts["작살"])
        want = {v: [c[0] for c in catalog if c[7] == v and c[1] != "S"
                    and not c[6].startswith("히든")] for v in SHOP_VILLAGES}
        vil_of_origin = {"스폰마을": "스폰", "사막마을": "사막"}

        hit = 0
        for _, v in entries:
            si = v.get("shopItems")
            if not si:
                continue
            # 기존 취급품의 출처 최다수 = 그 상점의 마을
            tally = {}
            for nm in si:
                vil = vil_of_origin.get(origin_of.get(nm, ""))
                if vil:
                    tally[vil] = tally.get(vil, 0) + 1
            if not tally:
                continue
            vil = max(tally, key=tally.get)
            v["shopItems"] = [x for x in si if x not in all_spears] + want[vil]
            hit += 1
            print(f"  {v.get('name', '?')} ← {vil} 작살 {len(want[vil])}종")
        json.dump(N, open(npc_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"npc.json: 상점 {hit}곳 작살 목록 갱신")

    # 감사용 표 — 등급 → 레벨 사다리로 출력
    print(f"\n{'등급':<3}{'Lv':>4}{'가격':>8}  {'출처':<10}{'이름':<16} 점수   스탯")
    for (name, grade, price, dur, stats, lv, origin, village, matlist, sc) in catalog:
        print(f"{grade:<3}{lv:>4}{price:>8}  {origin:<10}{name:<16}{sc:>6.0f}  {stats}")


if __name__ == "__main__":
    main()
