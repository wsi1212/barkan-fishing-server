#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""부품(릴·줄·바늘·미끼·찌) 빌드 카탈로그 생성기 — parts.json / recipes.json 재생성.

★수치를 바꿀 땐 이 파일을 고쳐 다시 돌린다. 손으로 JSON을 만지지 말 것.
   사용법: python3 gen_part_builds.py <BlockShip 데이터 폴더> [--shops]

────────────────────────────────────────────────────────────────────────────
설계 (balance.md 준수 — 낚싯대/작살 사다리와 같은 골격)
────────────────────────────────────────────────────────────────────────────
  §7  등급 가격대  ★2026-08-05 리프라이싱 — D 4,000~11,000 / C 13,000~32,000 /
                   B 40,000~100,000 / A 390,000~970,000 (구 200~25,000 폐기)
                   근거 = balance-audit/scripts/price_ladder.py — 풀세팅이 그 티어 구간
                   수입의 45%. 미끼는 소모품이라 BAIT_PRICE_MULT로 따로 축소(유지비 3%).
  §17 필요 레벨    E1 D5 C10 B20 A40 ← 하한. 같은 등급 안에서는 성능 점수로 갈린다.

  ★★2026-08-05 부품 정체성 전면 재배정(유저 지시) — 구 배정(릴=도망감소·줄=크리배율·
    바늘=등급업·미끼=경험치·찌=크기)을 폐기하고 아래로 교체. 스탯 자체는 이미 SUB_VAL로
    전 타입에 흩어져 있었으나(예: 미끼도 행운형 빌드로 행운을 얻을 수 있었다), 유저가 원한 건
    "이 타입의 정체성 = 이 스탯"이라는 <b>주스탯(TYPE_PRIMARY) 배정</b>이었다. 이름은
    안 바꾸지만(이름유지 원칙) 그 이름이 내는 스탯 조합은 이번에 전부 바뀐다.

  §8.2~8.6 타입별 <b>주스탯</b>과 범위 (신):
      미끼=행운(베이스, E3 D8 C14 B22 A32 — 부품 공통 행운 상한 A12보다 훨씬 높다,
             미끼가 "행운의 원천"이라는 정체성)
      바늘=크리확률(주, E2 D6 C12 B20 A30) + 크리배율(부, 모든 빌드에 항상 붙음 E1 D2 C3 B4 A5)
      줄=도망감소(E3 D8 C10~15 B18~22 A25~30, 구 릴 자리를 그대로 승계)
      찌=등급업(E0 D3 C5~6 B8~10 A12~15) — 더블찬스(상인형)·트리플찬스(성장형, ★신설)도
         찌 자신을 포함해 전 타입에서 얻을 수 있다
      릴=선택형 — 특화형은 경험치(E0 D10 C15~20 B25~35 A40~50), 크리형에서 크기,
         상인형에서 판매보너스를 골라 가져간다("경험치·판매·크기 중 택")

  ★★난이도 스탯 — **부품에 안 넣는다(2026-08-05 재검토·철회)**. 08-05 초반에 "숙련형" 빌드로
    5부품 전부에 분산시켰다가, 같은 날 완전점검에서 그 시도가 두 겹으로 어긋났음을 발견해
    철회했다: ①처음 계산한 목표(로드12+부품25=37→G 71%)가 로드 실측치(진짜 최대 5+강화1=6)를
    검증 없이 부풀린 값이었고 ②CROSS_CAP 버그로 바늘의 별개 스탯(크리배율)까지 오염됐다.
    유저 판단: "요리에서 난이도감소를 주면 된다(이미 요리 '노련한손맛' T4가 난이도+4 제공,
    2026-07-25 신설) — 부품/낚싯대는 지금 가격 재조정만으로 이미 밸런스가 맞다." 그래서
    난이도는 다시 **낚싯대 전용 + 요리 보조**로 되돌린다(원래 07-25 설계). 부품 5종 정체성
    재배정(위 §8.2~8.6)은 그대로 유지 — 이번에 되돌리는 건 "숙련형" 빌드 하나뿐이다.
  §8.1 «내구보존»은 2026-08-27 스탯 자체가 폐지됐다 — 부품이든 낚싯대든 넣지 않는다.

빌드 5종(그 부품이 무엇에 특화됐는지):
  특화형 = 타입 주스탯 최대치      행운형 = 행운 + 등급업
  크리형 = 크리확률 + 크기          상인형 = 판매보너스 + 더블찬스
  성장형 = 경험치 + 트리플찬스(★구 도망감소→트리플찬스로 교체, 트리플찬스 신설)

★기존 부품 이름은 바꾸지 않는다 — 장착 슬롯·부품 인벤·도감("type::name")·레시피·NPC 상점
  목록에 문자열로 박혀 있다. 스탯/레벨/가격만 재조정하고 빈 칸을 새 부품으로 채운다.
  (개발자 부품 8종은 삭제 — 유저 요청.)
"""
import json, shutil, sys, os

SRC = sys.argv[1]
WRITE_SHOPS = "--shops" in sys.argv
FORCE = "--force" in sys.argv       # 라이브 값 덮어쓰기 허용 (guard_drift 참조)
# ★추가 전용 — 카탈로그에 있고 라이브에 **없는** 종만 새로 쓴다. 기존 종은 값도 레시피도
#   손대지 않고 삭제 검사·드리프트 게이트도 건너뛴다.
#   왜: 레벨 재배분(patch_level_spread)·재료 적합(patch_cast_cost)이 라이브 값을 이미
#   조정해 놨다. 일반 모드로 돌리면 그 둘의 결과가 통째로 되돌아간다.
ADD_ONLY = "--add-only" in sys.argv

TYPES = ["릴", "줄", "바늘", "미끼", "찌"]
# ★2026-08-05 재배정 — 구 {릴:도망감소, 줄:크리배율, 바늘:등급업, 미끼:경험치, 찌:크기} 폐기.
TYPE_PRIMARY = {"릴": "경험치", "줄": "도망감소", "바늘": "크리확률", "미끼": "행운", "찌": "등급업"}

GRADE_LEVEL = {"E": 1, "D": 5, "C": 10, "B": 20, "A": 40, "S": 57}
LEVEL_BAND = {"D": (5, 9), "C": (10, 19), "B": (20, 34), "A": (40, 52), "S": (57, 70)}
# ★2026-08-05 전면 리프라이싱 (price_ladder.py). 구 밴드는 수입 대비 2자리 낮았다.
PRICE_BAND = {"D": (4000, 11000), "C": (13000, 32000), "B": (40000, 100000),
              "A": (390000, 970000), "S": (1000000, 2600000)}
SUB_BAND = {
    ("스폰마을", "B"): ((20, 27), (40000, 70000)),
    ("사막마을", "B"): ((28, 34), (70000, 100000)),
    ("사막마을", "A"): ((40, 44), (390000, 590000)),
    ("상단마을", "A"): ((44, 49), (590000, 850000)),
    ("왕도", "A"):     ((49, 52), (850000, 970000)),
    # ★2026-08-28 종결층 신설 — Lv58~70 은 부품이 한 종도 없어 «여정의 62%» 가 사막이었다.
    #   낚싯대는 히든 3마을이 Lv57~62 를 채우는데 부품은 그 마을에 계열이 통째로 빠져 있었다.
    ("히든-스폰마을", "S"): ((57, 59), (1000000, 1150000)),
    ("히든-사막마을", "S"): ((59, 61), (1150000, 1350000)),
    ("히든-상단마을", "S"): ((61, 63), (1350000, 1600000)),
    ("심해", "S"):         ((64, 66), (1700000, 2000000)),
    ("히든-전설", "S"):     ((67, 70), (2100000, 2600000)),
}
# 미끼는 소모품이라 가격 단위가 다르다(개당). 위 밴드에 이 배수를 곱한다.
# ★미끼 1개 = 내구도만큼의 캐스트 → 유지비/h = (캐스트/h ÷ 내구) × 가격. A티어에서 그 유지비가
#   수입의 3%가 되도록 역산한 값(구 0.022는 새 밴드에 그대로 곱하면 유지비가 3배로 튄다).
BAIT_PRICE_MULT = 0.0165
DURAB = {"E": 40, "D": 70, "C": 130, "B": 220, "A": 340, "S": 420}

# 타입 주스탯 등급별 값 (§8.2~8.6 범위 상단 = 특화형, 하단 = 그 외 빌드의 기본치)
# ★2026-08-05: 크리확률(바늘)·행운(미끼)을 신규 TYPE_VAL로 승격(구엔 SUB_VAL에서만 존재).
TYPE_VAL = {
    "도망감소": {"E": 3, "D": 8,  "C": 15, "B": 22, "A": 30, "S": 38},
    "크리배율": {"E": 1, "D": 2,  "C": 3,  "B": 4,  "A": 5, "S": 6},    # 바늘 고정 부스탯(항상 동반)
    "등급업":   {"E": 0, "D": 3,  "C": 6,  "B": 10, "A": 15, "S": 19},
    "경험치":   {"E": 0, "D": 15, "C": 35, "B": 55, "A": 75, "S": 95},    # ★2026-08-26 ×2/3 (구 20/50/80/110)
    "크기":     {"E": 0, "D": 3,  "C": 6,  "B": 10, "A": 15, "S": 19},
    "크리확률": {"E": 2, "D": 6,  "C": 12, "B": 20, "A": 30, "S": 38},   # ★바늘 주스탯 신설
    "행운":     {"E": 3, "D": 8,  "C": 14, "B": 22, "A": 32, "S": 40},   # ★미끼 주스탯 신설 — 공통 LUCK_CAP(A12)보다 훨씬 높다
}
TYPE_BASE = {   # 특화형이 아닌 빌드도 그 타입다움은 남긴다(주스탯 하한)
    "도망감소": {"E": 3, "D": 5,  "C": 10, "B": 13, "A": 16, "S": 21},
    "크리배율": {"E": 1, "D": 1,  "C": 2,  "B": 3,  "A": 4, "S": 5},
    "등급업":   {"E": 0, "D": 1,  "C": 3,  "B": 5,  "A": 8, "S": 10},
    "경험치":   {"E": 0, "D": 7,  "C": 15, "B": 30, "A": 40, "S": 50},   # ★2026-08-26 ×2/3 (구 10/25/45/60)
    "크기":     {"E": 0, "D": 1,  "C": 3,  "B": 5,  "A": 8, "S": 10},
    "크리확률": {"E": 1, "D": 3,  "C": 6,  "B": 10, "A": 16, "S": 20},
    # ★행운은 TYPE_VAL/TYPE_CAP 대비 비율을 다른 스탯들(≈0.5~0.6)과 맞춘다. 처음에 15/22(B)로
    #   너무 높게 잡아서 행운형(비-특화형)이 특화형과 거의 동률이 되는 완전열등 버그가 났었다.
    "행운":     {"E": 2, "D": 4,  "C": 7,  "B": 12, "A": 17, "S": 22},
}
# 빌드 부스탯 (타입 무관)
SUB_VAL = {
    "행운":       {"E": 2, "D": 4, "C": 6,  "B": 9,  "A": 12, "S": 15},   # ★행운형 주력치 (미끼 아닌 타입용 — 미끼는 TYPE_VAL 행운 사용)
    "등급업":     {"E": 0, "D": 2, "C": 4,  "B": 6,  "A": 9, "S": 11},
    "크리확률":   {"E": 1, "D": 2, "C": 4,  "B": 8,  "A": 12, "S": 15},
    "크기":       {"E": 1, "D": 2, "C": 5,  "B": 7,  "A": 11, "S": 14},
    "판매보너스": {"E": 1, "D": 3, "C": 6,  "B": 10, "A": 16, "S": 20},
    "더블찬스":   {"E": 1, "D": 2, "C": 5,  "B": 7,  "A": 10, "S": 13},
    "경험치":     {"E": 0, "D": 5, "C": 12, "B": 20, "A": 30, "S": 38},   # ★2026-08-26 ×2/3 (구 8/18/30/45)
    "도망감소":   {"E": 2, "D": 4, "C": 8,  "B": 12, "A": 18, "S": 23},
    # ★2026-08-05 신설 — 트리플찬스(구 도망감소 자리 대체)
    "트리플찬스": {"E": 0, "D": 1, "C": 1,  "B": 2,  "A": 3, "S": 4},
}
BUILDS = {
    "특화형": [],                       # 타입 주스탯 최대 + 행운
    "행운형": ["행운", "등급업"],
    "크리형": ["크리확률", "크기"],
    "상인형": ["판매보너스", "더블찬스"],
    "성장형": ["경험치", "트리플찬스"],  # ★구 도망감소 → 트리플찬스 (신규 스탯 도입)
}
SHAPE = {"기본형": (1.00, 1.00), "극단형": (1.15, 0.80), "균형형": (0.90, 1.25), "왕실형": (1.10, 1.10)}
HYBRID_SCALE = 0.8
# 마을 테마 (§17) — 낚싯대와 동일 규칙
VILLAGE_THEME = {"사막마을": ["등급업", "크기"], "상단마을": ["판매보너스", "크리확률"],
                 "왕도": ["행운", "더블찬스"],
                 # 히든은 본 마을 테마를 승계한다(같은 지역의 «깊은 곳»이라는 설정).
                 "히든-사막마을": ["등급업", "크기"],
                 "히든-상단마을": ["판매보너스", "크리확률"],
                 "히든-전설": ["행운", "더블찬스"]}
THEME_VAL = {"등급업": {"D": 1, "C": 2, "B": 3, "A": 5, "S": 6}, "크리확률": {"D": 1, "C": 2, "B": 3, "A": 5, "S": 6},
             "크기": {"D": 2, "C": 3, "B": 5, "A": 8, "S": 10}, "판매보너스": {"D": 2, "C": 3, "B": 5, "A": 8, "S": 10},
             "행운": {"D": 1, "C": 2, "B": 3, "A": 4, "S": 5}, "더블찬스": {"D": 1, "C": 2, "B": 3, "A": 4, "S": 5}}
# 상한 — 행운은 낚싯대와 같은 이유로 자른다(부품은 5개 겹쳐 끼므로 개당 상한이 더 중요)
# ★종결층 그룹 배수 — S 등급 안에서도 «어느 종결 구역인가» 로 계단을 만든다.
#   등급표가 하나뿐이라 이게 없으면 히든 5그룹이 스탯이 전부 같아지고, 레벨·가격만 높은
#   뒷 그룹이 앞 그룹에 완전열등으로 걸린다(2026-08-28 실측 30건).
#   캡을 적용한 «뒤에» 곱한다 — 종결층은 캡 위로 올라가라고 만든 층이다.
GROUP_MULT = {"히든-스폰마을": 0.90, "히든-사막마을": 0.97, "히든-상단마을": 1.05,
              "심해": 1.15, "히든-전설": 1.28}
LUCK_CAP = {"E": 2, "D": 4, "C": 6, "B": 9, "A": 12, "S": 20}
# ★행운형이 아닌 부품의 행운 기본치. 이걸 SUB_VAL과 같게 두면 모든 부품 행운이 같아져
#   행운형이라는 빌드 자체가 사라진다(바늘 D에서 특화형과 행운형이 완전 동일해졌다).
LUCK_BASE = {"E": 2, "D": 2, "C": 3, "B": 4, "A": 6, "S": 8}
# ★타입 주스탯 상한 (§8.2~8.6) — 마을 배수가 문서 범위를 밀어내지 못하게. 낚싯대 난이도와 같은 처리.
TYPE_CAP = {"도망감소": {"E": 3, "D": 8, "C": 15, "B": 22, "A": 30, "S": 38},
            "크리배율": {"E": 1, "D": 2, "C": 3, "B": 4, "A": 5, "S": 6},
            "등급업":   {"E": 0, "D": 3, "C": 6, "B": 10, "A": 15, "S": 19},
            "경험치":   {"E": 0, "D": 15, "C": 35, "B": 55, "A": 75, "S": 95},
            "크기":     {"E": 0, "D": 3, "C": 6, "B": 10, "A": 15, "S": 19},
            "크리확률": {"E": 2, "D": 6, "C": 12, "B": 20, "A": 30, "S": 38},   # ★신설(바늘)
            "행운":     {"E": 3, "D": 8, "C": 14, "B": 22, "A": 32, "S": 52}}   # ★신설(미끼, 공통상한보다 높음)
# ★교차 상한 — "남의 주스탯"은 그 타입 최대치의 절반 수준까지만. 안 걸면 릴이 크기 14를 주고
#   (찌 A 최대치가 15) 찌를 낄 이유가 사라진다. 각 부품이 자기 스탯을 소유해야 5슬롯이 의미 있다.
CROSS_CAP = {"도망감소": {"D": 4, "C": 8, "B": 12, "A": 16, "S": 20},
             "등급업":   {"D": 2, "C": 3, "B": 5, "A": 8, "S": 10},
             "크기":     {"D": 2, "C": 3, "B": 5, "A": 8, "S": 10},
             "경험치":   {"D": 5, "C": 12, "B": 20, "A": 35, "S": 44},
             "크리확률": {"D": 3, "C": 6, "B": 10, "A": 15, "S": 19}}   # ★신설 — 바늘 아닌 타입이 크리형 빌드로 얻을 때
             # ★2026-08-05 버그 수정: "크리배율" 항목을 여기서 뺐다 — 구 배정(줄=크리배율)
             #   시절 "남의 타입이 크리형 빌드로 얻는 소량"용 교차상한이었는데, 이제 크리배율은
             #   BUILDS의 어떤 pair에도 없고 오직 바늘의 항상동반 보조스탯(stats_for 특수분기)
             #   으로만 설정된다. 지웠어야 할 걸 안 지워서, 바늘 자신의 TYPE_VAL 크리배율
             #   (E1~A5)이 도로 D1/C1/B2/A2로 깎이고 있었다(A급 실측 5 아닌 2). "자기 스탯"인데
             #   "남의 스탯" 취급을 받은 것 — 발견: MAX_MAGNITUDE 재검산 중 실측 스캔으로 확인.

# ★난이도는 부품에 없다(위 doc 참조 — 낚싯대 전용+요리 보조로 되돌림) → POWER_W에 항목 없음.
POWER_W = {"도망감소": 0.05, "크리배율": 2.5, "등급업": 1.0, "경험치": 0.45, "크기": 0.65,
           "행운": 0.65, "크리확률": 0.4, "판매보너스": 1.0, "더블찬스": 1.0,
           "트리플찬스": 0.6}

# ── 격자: (등급, 마을, 성격, [빌드...]) — 모든 타입이 같은 격자를 쓴다 ─────────
GRID = [
    ("E", "스폰마을", "기본형", ["특화형"]),
    ("D", "스폰마을", "기본형", ["특화형", "행운형"]),
    ("C", "스폰마을", "기본형", ["특화형", "크리형", "상인형", "성장형"]),
    ("B", "스폰마을", "기본형", ["특화형", "행운형", "크리형"]),
    ("B", "사막마을", "극단형", ["특화형", "상인형"]),
    ("A", "사막마을", "극단형", ["특화형", "행운형"]),
    ("A", "상단마을", "균형형", ["특화형", "크리형", "상인형"]),
    # ★2026-08-28 종결층 — Lv57~70. 낚싯대는 히든 3마을이 이 구간을 채우는데 부품은
    #   한 종도 없었다(여정의 62%가 사막). 마을마다 2 빌드씩 = 타입당 10 종을 새로 깐다.
    ("S", "히든-스폰마을", "극단형", ["특화형", "성장형"]),
    ("S", "히든-사막마을", "극단형", ["특화형", "행운형"]),
    ("S", "히든-상단마을", "균형형", ["특화형", "상인형"]),
    ("S", "심해", "극단형", ["특화형", "크리형"]),
    ("S", "히든-전설", "왕실형", ["특화형", "상인형"]),
]
# 왕도 복합형 (타입마다 1종)
HYBRID = ("A", "왕도", "왕실형", ("행운형", "상인형"))

# ── 기존 이름 고정: (타입, 등급, 빌드) → 이름. 없는 칸은 NEW_NAME에서 새 이름을 쓴다 ──
#   ★기존 부품은 전부 여기 등장해야 한다(이름 유지 원칙). 빠지면 생성기가 실패한다.
PIN = {
    ("릴", "E", "스폰마을", "특화형"): "녹슨 릴",
    ("릴", "D", "스폰마을", "특화형"): "나무 릴",
    ("릴", "C", "스폰마을", "특화형"): "철제 릴",
    ("릴", "C", "스폰마을", "크리형"): "고속 릴",
    ("릴", "B", "스폰마을", "특화형"): "전술 릴",
    ("릴", "B", "스폰마을", "크리형"): "전기 릴",
    ("릴", "B", "사막마을", "특화형"): "사막 릴",
    ("릴", "A", "상단마을", "특화형"): "정밀 릴",
    ("릴", "A", "상단마을", "크리형"): "만능 릴",
    ("릴", "A", "왕도", "복합"):       "바르칸 릴",
    ("줄", "E", "스폰마을", "특화형"): "삼베줄",
    ("줄", "D", "스폰마을", "특화형"): "면줄",
    ("줄", "C", "스폰마을", "특화형"): "나일론줄",
    ("줄", "C", "스폰마을", "크리형"): "거미줄",
    ("줄", "C", "스폰마을", "상인형"): "쌍줄",
    ("줄", "C", "스폰마을", "성장형"): "강철 와이어",
    ("줄", "B", "스폰마을", "특화형"): "카본줄",
    ("줄", "B", "스폰마을", "행운형"): "티타늄줄",
    ("줄", "A", "사막마을", "특화형"): "모래바람 줄",
    ("줄", "A", "상단마을", "특화형"): "PE합사줄",
    ("줄", "A", "상단마을", "크리형"): "천공 와이어",
    ("줄", "A", "왕도", "복합"):       "바르칸 줄",
    ("바늘", "E", "스폰마을", "특화형"): "구부러진 바늘",
    ("바늘", "D", "스폰마을", "특화형"): "철 바늘",
    ("바늘", "D", "스폰마을", "행운형"): "대형 바늘",
    ("바늘", "C", "스폰마을", "특화형"): "날카로운 바늘",
    ("바늘", "C", "스폰마을", "크리형"): "예리한 바늘",
    ("바늘", "C", "스폰마을", "상인형"): "갈고리 바늘",
    ("바늘", "C", "스폰마을", "성장형"): "독침 바늘",
    ("바늘", "B", "스폰마을", "특화형"): "미늘 바늘",
    ("바늘", "B", "스폰마을", "크리형"): "정교한 바늘",
    ("바늘", "A", "사막마을", "특화형"): "신기루 바늘",
    ("바늘", "A", "상단마을", "특화형"): "용뼈 바늘",
    ("바늘", "A", "왕도", "복합"):       "바르칸 바늘",
    ("미끼", "E", "스폰마을", "특화형"): "지렁이",
    ("미끼", "D", "스폰마을", "특화형"): "떡밥",
    ("미끼", "D", "스폰마을", "행운형"): "향기나는 미끼",
    ("미끼", "C", "스폰마을", "특화형"): "새우",
    ("미끼", "C", "스폰마을", "크리형"): "거대 미끼",
    ("미끼", "C", "스폰마을", "상인형"): "빛나는 미끼",
    ("미끼", "C", "스폰마을", "성장형"): "살아있는 미끼",
    ("미끼", "B", "스폰마을", "특화형"): "반딧불이 미끼",
    ("미끼", "B", "사막마을", "특화형"): "오아시스 미끼",
    ("미끼", "A", "상단마을", "특화형"): "천공 미끼",
    ("미끼", "A", "상단마을", "크리형"): "프리미엄 미끼",
    ("미끼", "A", "왕도", "복합"):       "바르칸 미끼",
    ("찌", "E", "스폰마을", "특화형"): "나무 찌",
    ("찌", "D", "스폰마을", "특화형"): "코르크 찌",
    ("찌", "C", "스폰마을", "특화형"): "가벼운 찌",
    ("찌", "C", "스폰마을", "크리형"): "예민한 찌",
    ("찌", "B", "스폰마을", "특화형"): "전자 찌",
    ("찌", "B", "스폰마을", "행운형"): "행운 전자찌",
    ("찌", "B", "스폰마을", "크리형"): "초정밀 찌",
    ("찌", "A", "사막마을", "특화형"): "사구 찌",
    ("찌", "A", "상단마을", "특화형"): "수정 찌",
    ("찌", "A", "왕도", "복합"):       "바르칸 찌",
}
# 신규 이름 — 마을/등급 시리즈를 낚싯대·작살과 맞춘다(사막=사구/신기루/전갈/오아시스, 왕도=왕실 …)
NEW_NAME = {
    "릴": {
           ("S", "히든-스폰마을", "특화형"): "여명 릴", ("S", "히든-스폰마을", "성장형"): "등대 릴", ("S", "히든-사막마을", "특화형"): "모래폭풍 릴", ("S", "히든-사막마을", "행운형"): "전갈왕 릴", ("S", "히든-상단마을", "특화형"): "감정왕 릴", ("S", "히든-상단마을", "상인형"): "대상인 릴", ("S", "심해", "특화형"): "심연 릴", ("S", "심해", "크리형"): "심해수정 릴", ("S", "히든-전설", "특화형"): "용린 릴", ("S", "히든-전설", "상인형"): "성좌 릴",
           ("D", "스폰마을", "행운형"): "행운 릴", ("C", "스폰마을", "상인형"): "황동 릴",
           ("C", "스폰마을", "성장형"): "수련용 릴", ("B", "스폰마을", "행운형"): "길조 릴",
           ("B", "사막마을", "상인형"): "행렬 릴", ("A", "사막마을", "행운형"): "신기루 릴",
           ("A", "사막마을", "특화형"): "열사 릴", ("A", "상단마을", "상인형"): "교역 릴"},
    "줄": {
           ("S", "히든-스폰마을", "특화형"): "여명 줄", ("S", "히든-스폰마을", "성장형"): "등대 줄", ("S", "히든-사막마을", "특화형"): "모래폭풍 줄", ("S", "히든-사막마을", "행운형"): "전갈왕 줄", ("S", "히든-상단마을", "특화형"): "감정왕 줄", ("S", "히든-상단마을", "상인형"): "대상인 줄", ("S", "심해", "특화형"): "심연 줄", ("S", "심해", "크리형"): "심해수정 줄", ("S", "히든-전설", "특화형"): "용린 줄", ("S", "히든-전설", "상인형"): "성좌 줄",
           ("D", "스폰마을", "행운형"): "행운실", ("C", "스폰마을", "크리형2"): "",
           ("B", "스폰마을", "크리형"): "합사 카본줄", ("B", "사막마을", "특화형"): "사막 강선",
           ("B", "사막마을", "상인형"): "대상 밧줄", ("A", "사막마을", "행운형"): "신기루 줄",
           ("A", "상단마을", "상인형"): "교역 합사줄"},
    "바늘": {
           ("S", "히든-스폰마을", "특화형"): "여명 바늘", ("S", "히든-스폰마을", "성장형"): "등대 바늘", ("S", "히든-사막마을", "특화형"): "모래폭풍 바늘", ("S", "히든-사막마을", "행운형"): "전갈왕 바늘", ("S", "히든-상단마을", "특화형"): "감정왕 바늘", ("S", "히든-상단마을", "상인형"): "대상인 바늘", ("S", "심해", "특화형"): "심연 바늘", ("S", "심해", "크리형"): "심해수정 바늘", ("S", "히든-전설", "특화형"): "용린 바늘", ("S", "히든-전설", "상인형"): "성좌 바늘",
           ("C", "스폰마을", "행운형2"): "", ("B", "스폰마을", "행운형"): "길조 바늘",
             ("B", "사막마을", "특화형"): "전갈 바늘", ("B", "사막마을", "상인형"): "행렬 바늘",
             ("A", "사막마을", "행운형"): "사구 바늘", ("A", "상단마을", "크리형"): "세공 바늘",
             ("A", "상단마을", "상인형"): "교역 바늘"},
    "미끼": {
           ("S", "히든-스폰마을", "특화형"): "여명 미끼", ("S", "히든-스폰마을", "성장형"): "등대 미끼", ("S", "히든-사막마을", "특화형"): "모래폭풍 미끼", ("S", "히든-사막마을", "행운형"): "전갈왕 미끼", ("S", "히든-상단마을", "특화형"): "감정왕 미끼", ("S", "히든-상단마을", "상인형"): "대상인 미끼", ("S", "심해", "특화형"): "심연 미끼", ("S", "심해", "크리형"): "심해수정 미끼", ("S", "히든-전설", "특화형"): "용린 미끼", ("S", "히든-전설", "상인형"): "성좌 미끼",
           ("B", "스폰마을", "행운형"): "길조 미끼", ("B", "스폰마을", "크리형"): "번개 미끼",
             ("B", "사막마을", "상인형"): "행렬 미끼", ("A", "사막마을", "행운형"): "신기루 미끼",
             ("A", "사막마을", "특화형"): "오아시스 정수 미끼", ("A", "상단마을", "상인형"): "교역 미끼"},
    "찌": {
           ("S", "히든-스폰마을", "특화형"): "여명 찌", ("S", "히든-스폰마을", "성장형"): "등대 찌", ("S", "히든-사막마을", "특화형"): "모래폭풍 찌", ("S", "히든-사막마을", "행운형"): "전갈왕 찌", ("S", "히든-상단마을", "특화형"): "감정왕 찌", ("S", "히든-상단마을", "상인형"): "대상인 찌", ("S", "심해", "특화형"): "심연 찌", ("S", "심해", "크리형"): "심해수정 찌", ("S", "히든-전설", "특화형"): "용린 찌", ("S", "히든-전설", "상인형"): "성좌 찌",
           ("D", "스폰마을", "행운형"): "행운 찌", ("C", "스폰마을", "상인형"): "황동 찌",
           ("C", "스폰마을", "성장형"): "수련용 찌", ("B", "사막마을", "특화형"): "모래 찌",
           ("B", "사막마을", "상인형"): "행렬 찌", ("A", "사막마을", "행운형"): "신기루 찌",
           ("A", "상단마을", "크리형"): "세공 찌", ("A", "상단마을", "상인형"): "교역 찌"},
}
# 삭제 허용 (개발자 부품)
RETIRED_PREFIX = "개발자"
# Legacy dive-shop reels deliberately sit outside the normal village grid.  Keep their
# canonical source specs here so a regeneration preserves them while applying the
# global 2026-08-07 XP-stat half multiplier exactly once.
# ★«재료확률» 축 라인(채집·수집·유적 계열)은 이 사다리 소관이 아니다 — 빌드에 없는 축이고
#   스탯이 따로 조정된 값이라 이 공식으로 재생성하면 수치가 바뀐다. 이름 목록 대신
#   «스탯에 재료확률이 있으면 보존» 규칙으로 잡는다(항목이 늘어도 생성기가 안 깨지게).
EXTERNAL_AXIS = "재료확률"


def is_external(part_value):
    """parts.json 한 줄(이름|등급|가격|내구|스탯|레벨|출처)이 외부 라인인지."""
    f = part_value.split("|")
    return len(f) > 4 and EXTERNAL_AXIS in f[4]


PRESERVE_PARTS = {
    # ★격자 밖 잔존 1종 — 2026-08-28 실측으로 발견(생성기가 「이름 유지 원칙 위반」으로 멈춰 있었다).
    #   격자에 넣으면 스탯이 공식으로 재계산돼 라이브 값이 바뀐다. 재료 개편이 목적이므로
    #   스탯은 그대로 두고 «레시피 조성만» 뒤에서 따로 맞춘다(patch_line_signature.py).
    ("릴", "수습 릴"): "수습 릴|D|9000|70|경험치:11,트리플찬스:1,행운:2|4|스폰마을",
    # ★초보자 4종 — 조합대 R00b~e 가 주는 스폰마을 입문 부품. 사다리 격자(GRID) 밖이라
    #   여기 박아 둔다. 스탯은 레시피 로어에 적힌 값과 같아야 한다(로어=parts.json 관례).
    #   이게 없던 동안 네 개는 그냥 바닐라 아이템이라 **장비로 인식되지 않았다**(2026-08-11 제보).
    ("릴", "초보자 릴"): "초보자 릴|E|0|60|도망감소:5|1|스폰마을",
    ("줄", "초보자 줄"): "초보자 줄|E|0|60|크리배율:2|1|스폰마을",   # ★2 = «+20%» (표시는 raw x10). 20 을 적으면 표시 200% = 종결 크리빌드 전체와 동급이 된다.
    ("바늘", "초보자 바늘"): "초보자 바늘|E|0|60|등급업:1|1|스폰마을",
    ("찌", "초보자 찌"): "초보자 찌|E|0|60|크기:2|1|스폰마을",
    ("릴", "잠수부 릴"): "잠수부 릴|B|80000|220|경험치:30,행운:7|10|잠수상점",
    ("릴", "심해 잠수부 릴"): "심해 잠수부 릴|A|880000|340|등급업:7,경험치:45,판매보너스:12,더블찬스:6,행운:9|30|잠수상점",
    ("줄", "잠수부 줄"): "잠수부 줄|B|80000|220|도망감소:16,등급업:3,행운:7|10|잠수상점",
    ("줄", "심해 잠수부 줄"): "심해 잠수부 줄|A|935000|340|도망감소:24,등급업:7,판매보너스:12,더블찬스:6,행운:9|30|잠수상점",
    ("바늘", "잠수부 바늘"): "잠수부 바늘|B|80000|220|크리배율:4,크리확률:14,행운:7|10|잠수상점",
    ("바늘", "심해 잠수부 바늘"): "심해 잠수부 바늘|A|990000|340|크리배율:5,크리확률:24,판매보너스:12,더블찬스:6,행운:9|30|잠수상점",
    ("미끼", "잠수부 미끼"): "잠수부 미끼|B|1200|220|등급업:3,행운:22|10|잠수상점",
    ("미끼", "심해 잠수부 미끼"): "심해 잠수부 미끼|A|12000|340|등급업:7,판매보너스:12,더블찬스:6,행운:30|30|잠수상점",
    ("찌", "잠수부 찌"): "잠수부 찌|B|80000|220|등급업:8,행운:7|10|잠수상점",
    ("찌", "심해 잠수부 찌"): "심해 잠수부 찌|A|1090000|340|등급업:14,판매보너스:12,더블찬스:6,행운:9|30|잠수상점",
}

STAT_ORDER = ["도망감소", "크리배율", "등급업", "크리확률", "크기", "경험치",
              "판매보너스", "더블찬스", "트리플찬스", "행운"]
# 등급별 제작 재료
#
# ★2026-08-23 스폰마을 저티어 재료 루트 — 스폰마을의 E·D급 부품은 강/항구에서
#   바로 얻을 수 있는 재료만 사용한다. 항구는 스폰도시 드롭테이블을 상속하므로
#   두 지역의 공통 루트가 된다. 별빛진주는 D급 행운형에만 1개를 허용한다.
LOW_GRADE_COMMON = {
    "E": [("물고기비늘", 1)],
    "D": [("낡은갈고리", 2), ("녹슨부품", 2), ("강화실", 2), ("물고기비늘", 4)],
}
LOW_GRADE_TYPE_MAT = {
    "릴": "녹슨부품",
    "줄": "강화실",
    "바늘": "낡은갈고리",
    "미끼": "물고기비늘",
    "찌": "깃털찌조각",
}
LOW_GRADE_TYPE_QTY = {"E": 1, "D": 2}
LOW_GRADE_BUILD_EXTRA = {
    "E": {},
    "D": {
        "특화형": [],
        "행운형": [("진주", 2), ("별빛진주", 1)],
    },
}
# ══════════════════════════════════════════════════════════════════════════
#  계열 고유 재료 (2026-08-28) — «이 계열이면 반드시 들어가고, 다른 계열엔 안 들어간다»
#
#    낚싯대 = 정제된 갈고리   (낡은 갈고리×4 ← 부두)
#    작살   = 거대 비늘       (협곡)
#    부품   = 녹슨 부품       (강)
#    통발   = 끈 + 대나무     (바닐라 — TrapSpecs.java)
#
#  ★왜: 개편 전엔 세 계열이 «단단한 자루·강철 심·진주·압축 흑정석» 넉 장을 똑같이 쓰고 있었다.
#    재료만 보고는 무엇을 만드는지 알 수 없었고, 어느 어장을 가야 하는지도 계열로 갈리지 않았다.
#
#  ★광물 = 드릴 티어 사다리. 등급이 오르면 «더 좋은 드릴»을 요구한다.
#    B → 압축 흑정석(T1) · A → + 압축 적철석(T2) · S → + 압축 자수정(T3)
#    개편 전 압축 적철석은 쓰는 데가 드릴 T3 레시피 1건, 압축 자수정은 0건이었다
#    (T2 드릴로 캔 적철석이 갈 곳이 없어 T2 자체가 사문화돼 있었다).
# ══════════════════════════════════════════════════════════════════════════
COMMON = {
    "D": [("녹슨부품", 4), ("강화실", 4), ("물고기비늘", 6)],
    # ★C 이하는 압축 흑정석(=흑정석 계열 광물) 제외 — 광물은 사막마을부터 얻는다.
    "C": [("녹슨부품", 8), ("강화철괴", 6), ("진주", 6)],
    "B": [("녹슨부품", 12), ("강철심", 14), ("강화철괴", 12), ("진주", 16), ("압축흑정석", 8)],
    "A": [("녹슨부품", 20), ("강철심", 26), ("진주", 30), ("압축흑정석", 22),
          ("압축철광석", 5), ("별빛진주", 4)],
    # ★바르칸핵(=바르칸조각 8)을 공통에 넣는다. 이게 없으면 S 상인형이 싼 재료(강화에메랄드·
    #   진주)만으로 종결 목표에 닿아야 해서 여섯 재료를 전부 상한 48 로 채워도 −36% 가 남는다
    #   (2026-08-28 «성좌» 5종). 비싼 중간재 하나가 «캐스트 밀도» 를 만들어 준다.
    "S": [("녹슨부품", 30), ("강철심", 32), ("진주", 36), ("압축흑정석", 28), ("별빛진주", 8),
          ("바르칸조각", 12), ("바르칸핵", 6), ("압축철광석", 10), ("압축자수정", 2)],
}
# ★특화형 저티어가 녹슨부품이었는데 그건 이제 부품 COMMON(계열 고유)이라 중복이다.
BUILD_MAT = {"특화형": "강화철괴", "행운형": "행운의구슬", "크리형": "안개수정",
             "상인형": "보석", "성장형": "깃털찌조각"}
BUILD_MAT_A = {"특화형": "강화철괴", "행운형": "행운의매듭", "크리형": "자수정",
               "상인형": "강화에메랄드", "성장형": "별빛진주"}
# S 는 종결층이라 빌드 재료도 종결 재료로 간다. 특화형만 «바르칸핵»(중간재)이고 나머지는
# A 와 같은 축을 쓰되 수량이 오른다(MAT_QTY).
BUILD_MAT_S = {"특화형": "바르칸핵", "행운형": "행운의매듭", "크리형": "심해수정",
               "상인형": "강화에메랄드", "성장형": "별빛진주"}
MAT_QTY = {"D": 4, "C": 8, "B": 14, "A": 24, "S": 30}


def r(v):
    return max(1, int(round(v)))


def stats_for(ptype, grade, build, shape, hybrid=None, village=None):
    pm, sm = SHAPE[shape]
    prim = TYPE_PRIMARY[ptype]
    st = {}
    if build == "특화형":
        st[prim] = r(TYPE_VAL[prim][grade] * pm)
    else:
        base = TYPE_BASE[prim][grade]
        if base > 0:
            st[prim] = r(base)
        for pair in ([BUILDS[build]] if hybrid is None else [BUILDS[hybrid[0]], BUILDS[hybrid[1]]]):
            scale = 1.0 if hybrid is None else HYBRID_SCALE
            for i, ax in enumerate(pair):
                v = SUB_VAL[ax][grade] * (pm if i == 0 else sm) * scale
                if v >= 1:
                    st[ax] = st.get(ax, 0) + r(v)
    # ★2026-08-05 신설 — 바늘은 "크리확률+크리배율" 듀얼 정체성. 크리배율은 빌드와 무관하게
    #   항상 동반한다(크리형 빌드를 골랐는지와 무관 — 크리확률/크리배율은 별개 축이라 안 겹친다).
    if ptype == "바늘":
        v = TYPE_VAL["크리배율"][grade] * pm
        if v >= 1:
            st["크리배율"] = st.get("크리배율", 0) + r(v)
    # 마을 테마 (그 빌드가 안 쓰는 축에만)
    used = set(st) | {prim}
    for th in VILLAGE_THEME.get(village, []):
        if th in used or grade not in THEME_VAL.get(th, {}):
            continue
        st[th] = st.get(th, 0) + THEME_VAL[th][grade]
        break
    # 행운 — 부품 공통 부스탯. 행운형이 아니면 등급 기본치, 어떤 경우든 상한에서 자른다.
    # ★미끼는 예외 — 행운 자체가 미끼의 주스탯(TYPE_VAL/TYPE_BASE/TYPE_CAP)이라 공통상한(A12)을
    #   적용하면 위에서 준 특화치(A32)가 도로 깎인다. prim=="행운"(=미끼)일 때만 건너뛴다.
    if prim != "행운":
        st["행운"] = min(max(st.get("행운", 0), LUCK_BASE[grade]), LUCK_CAP[grade])
    # 상한: 자기 주스탯은 §8 범위까지, 남의 주스탯은 교차 상한까지.
    if prim in TYPE_CAP:
        st[prim] = min(st[prim], TYPE_CAP[prim][grade])
    for ax in list(st):
        if ax == prim or ax == "행운":
            continue
        cc = CROSS_CAP.get(ax)
        if cc and grade in cc:
            st[ax] = min(st[ax], cc[grade])
    # ★2026-08-26 — 2026-08-07 감사 ④ «장비 경험치 ×0.5» 는 생성기에만 들어가고 라이브엔
    #   끝내 반영되지 않았다(라이브 = 반값 전 값 그대로, C풀세팅 +154%). 유저 판단으로 강도를
    #   ×0.5 → ×2/3 로 완화하고, 나눗셈 대신 **표 자체를 손으로 떨어뜨린 정수**로 교체했다
    #   (15 이상은 5단위 — 기계식 ÷2 가 소수점 22.5 같은 값을 남겼던 문제도 같이 없앤다).
    # ★종결층 그룹 배수 — 캡 «뒤» 에 곱한다(위 GROUP_MULT 주석 참조).
    gm = GROUP_MULT.get(village)
    if gm:
        st = {k: r(v * gm) for k, v in st.items()}
    return st


def power(st):
    return sum(POWER_W.get(k, 0) * v for k, v in st.items())


def stat_str(st):
    return ",".join(f"{k}:{st[k]}" for k in STAT_ORDER if st.get(k) is not None and st.get(k) != 0) \
           or f"{TYPE_PRIMARY_FALLBACK}:0"


TYPE_PRIMARY_FALLBACK = "행운"


def guard_drift(what, drift):
    """라이브 값과 생성 결과가 다르면 **쓰기 전에 멈춘다** (--force 로만 통과).

    낚싯대 생성기(gen_rod_builds.py)와 같은 게이트. 이 표가 라이브와 어긋난 채로 돌면
    라이브에서 조정해 둔 수치를 조용히 되돌린다(2026-08-24 prod 실측 87종).
    """
    if not drift or FORCE:
        if drift:
            print(f"  ⚠ --force: {what} {len(drift)}종을 라이브 값에서 덮어쓴다")
        return
    print(f"\n❌ {what} {len(drift)}종이 라이브 값과 다르다 — 쓰지 않고 멈춘다.")
    print("   (표를 고쳐 의도한 변경이면 --force 를 붙여 다시 돌릴 것)")
    for name, live, gen in drift[:15]:
        print(f"   · {name}\n       라이브: {live}\n       생성기: {gen}")
    if len(drift) > 15:
        print(f"   … 외 {len(drift) - 15}종")
    raise SystemExit(2)


def build_catalog():
    rows = []
    for ptype in TYPES:
        cells = [(g, v, sh, b) for (g, v, sh, bs) in GRID for b in bs]
        cells.append((HYBRID[0], HYBRID[1], HYBRID[2], "복합"))
        for (grade, village, shape, build) in cells:
            name = PIN.get((ptype, grade, village, build)) or \
                   NEW_NAME.get(ptype, {}).get((grade, village, build))
            if not name:
                raise SystemExit(f"이름 미정: {ptype} {grade} {village} {build}")
            st = (stats_for(ptype, grade, "복합", shape, hybrid=HYBRID[3], village=village)
                  if build == "복합" else stats_for(ptype, grade, build, shape, village=village))
            new = (ptype, grade, village, build) not in PIN
            rows.append(dict(type=ptype, name=name, grade=grade, village=village,
                             build=build, st=st, new=new))
    out = []
    groups = {}
    for x in rows:
        key = (x["type"], x["village"] if (x["village"], x["grade"]) in SUB_BAND else None, x["grade"])
        groups.setdefault(key, []).append(x)
    for (ptype, vil, grade), band in groups.items():
        scores = [power(x["st"]) for x in band]
        lo, hi = min(scores), max(scores)
        (llo, lhi), (plo, phi) = SUB_BAND.get((vil, grade),
                                              (LEVEL_BAND.get(grade, (1, 1)), PRICE_BAND.get(grade, (0, 0))))
        for x, sc in zip(band, scores):
            t = 0.0 if hi == lo else (sc - lo) / (hi - lo)
            lv = 1 if grade == "E" else int(round(llo + t * (lhi - llo)))
            price = (plo + t * (phi - plo))
            if x["type"] == "미끼":
                blo, bhi = (max(5, int(plo * BAIT_PRICE_MULT)), int(phi * BAIT_PRICE_MULT) + 5)
                price = min(max(int(round(price * BAIT_PRICE_MULT / 5.0) * 5), blo), bhi)
            else:
                price = int(round(price / 50.0) * 50)
            if grade == "E":
                price = {"릴": 80, "줄": 60, "바늘": 50, "미끼": 5, "찌": 70}[x["type"]]
            x.update(lv=lv, price=price, score=sc, dur=DURAB[grade])
            out.append(x)
    gorder = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4, "S": 5}
    out.sort(key=lambda z: (TYPES.index(z["type"]), gorder[z["grade"]], z["lv"]))
    return out


def check(cat):
    errs = []
    for c in cat:
        g = c["grade"]
        if g != "E":
            lo, hi = PRICE_BAND[g]
            if c["type"] == "미끼":
                lo, hi = max(5, int(lo * BAIT_PRICE_MULT)), int(hi * BAIT_PRICE_MULT) + 5
            if not (lo <= c["price"] <= hi):
                errs.append(f"{c['name']}: 가격 {c['price']} 이 {g} 대역 {lo}~{hi} 밖")
            if c["lv"] < GRADE_LEVEL[g]:
                errs.append(f"{c['name']}: 레벨 {c['lv']} < {g} 필요레벨 {GRADE_LEVEL[g]}")
        # ★미끼는 행운이 주스탯이라 공통상한(LUCK_CAP)이 아니라 TYPE_CAP["행운"]을 쓴다.
        # ★그룹 배수가 캡 뒤에 곱해지므로 검사 상한도 같은 배수를 태운다 — 안 그러면
        #   «의도된 초과» 를 위반으로 잡는다(2026-08-28 심연·용린 미끼).
        luck_cap = r((TYPE_CAP["행운"][g] if c["type"] == "미끼" else LUCK_CAP[g])
                     * GROUP_MULT.get(c["village"], 1.0))
        if c["st"].get("행운", 0) > luck_cap:
            errs.append(f"{c['name']}: 행운 {c['st']['행운']} > 상한 {luck_cap}")
        if "내구보존" in c["st"]:
            errs.append(f"{c['name']}: 내구보존은 폐지된 스탯이다(2026-08-27, §8.1)")
        prim = TYPE_PRIMARY[c["type"]]
        if prim not in c["st"] and TYPE_VAL[prim][g] > 0:
            errs.append(f"{c['name']}: {c['type']} 주스탯({prim}) 없음")
    # 같은 타입·등급에서 완전열등
    for a in cat:
        for b in cat:
            if a is b or a["type"] != b["type"] or a["grade"] != b["grade"]:
                continue
            keys = set(a["st"]) | set(b["st"])
            if all(a["st"].get(k, 0) <= b["st"].get(k, 0) for k in keys) \
                    and a["price"] >= b["price"] and a["lv"] >= b["lv"]:
                errs.append(f"완전열등: {a['name']} ⊂ {b['name']}")
    if errs:
        raise SystemExit("검증 실패:\n  - " + "\n  - ".join(errs))


def merge(items):
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
    cat = build_catalog()
    check(cat)          # ★검증은 항상 카탈로그 «전체» 로 한다(완전열등은 기존과의 비교가 필요)
    parts_path = os.path.join(SRC, "parts.json")
    rec_path = os.path.join(SRC, "recipes.json")
    mats = json.load(open(os.path.join(SRC, "materials.json"), encoding="utf-8"))["materials"]

    def ing(mid, qty):
        m = mats[mid]
        return {"kind": "custom", "typeOrMatId": mid, "displayName": m["name"],
                "mcItem": m["mcItem"], "qty": int(qty)}

    P = json.load(open(parts_path, encoding="utf-8"))
    shutil.copy(parts_path, parts_path + ".bak-partladder")
    parts, order = P["parts"], P["order"]
    owned = {(c["type"], c["name"]) for c in cat}
    live_names = {(t, n) for t in TYPES for n in parts[t]}
    if ADD_ONLY:
        # ★«없다» 의 기준은 부품 **또는** 레시피다. 부품만 보면, 부품은 들어갔는데 레시피가
        #   빠진 중간 상태를 «전부 있음» 으로 읽고 아무것도 안 한다(2026-08-28 실측: 레시피만
        #   되돌린 뒤 재실행했더니 50종이 레시피 없는 채로 남았다).
        _R = json.load(open(rec_path, encoding="utf-8"))["recipes"]
        live_recipes = {rc.get("resultPartName") for rc in _R.values()
                        if rc.get("resultMode") == "part"}
        cat = [c for c in cat if (c["type"], c["name"]) not in live_names
               or c["name"] not in live_recipes]
        print(f"[add-only] 부품 또는 레시피가 없는 {len(cat)}종만 추가한다 "
              f"(나머지 {len(live_names)}종은 값·레시피 모두 손대지 않는다)")
    removed = []
    for t in ([] if ADD_ONLY else TYPES):
        for n in list(parts[t]):
            if (t, n) in owned:
                continue
            if (t, n) in PRESERVE_PARTS or is_external(parts[t][n]):
                continue
            if not n.startswith(RETIRED_PREFIX):
                raise SystemExit(f"카탈로그에 없는 기존 부품(이름 유지 원칙 위반): {t}/{n}")
            del parts[t][n]
            removed.append(f"{t}/{n}")
    # ★보존 부품(PRESERVE_PARTS)도 order 에 남겨야 한다 — owned 에만 없다고 걸러내면
    #   parts 에는 있는데 순서 목록에서 빠져 목록·상점에서 사라진다.
    external = {(t, n) for t in TYPES for n in parts[t] if is_external(parts[t][n])}
    P["order"] = [e for e in order
                  if not (e[0] in TYPES and (e[0], e[1]) not in owned
                          and (e[0], e[1]) not in PRESERVE_PARTS
                          and (e[0], e[1]) not in external)]
    order = P["order"]
    def line_for(c):
        return "|".join([c["name"], c["grade"], str(c["price"]), str(c["dur"]),
                         stat_str(c["st"]), str(c["lv"]), c["village"]])
    drift = [(f'{c["type"]}/{c["name"]}', parts[c["type"]][c["name"]], line_for(c)) for c in cat
             if c["name"] in parts[c["type"]] and parts[c["type"]][c["name"]] != line_for(c)]
    if not ADD_ONLY:
        guard_drift("부품", drift)
    for c in cat:
        parts[c["type"]][c["name"]] = line_for(c)
    for (ptype, name), value in ([] if ADD_ONLY else PRESERVE_PARTS.items()):
        parts[ptype][name] = value
        if [ptype, name] not in order:
            order.append([ptype, name])
    have = {(t, n) for t, n in order}
    for c in cat:
        if (c["type"], c["name"]) not in have:
            order.append([c["type"], c["name"]])
    json.dump(P, open(parts_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"parts.json: 부품 {sum(len(parts[t]) for t in TYPES)}종 "
          f"(신규 {sum(1 for c in cat if c['new'])}), 삭제 {len(removed)}종 {removed}")

    # ── recipes: 기존 P-id 유지, 신규는 P60+ ──
    R = json.load(open(rec_path, encoding="utf-8"))
    shutil.copy(rec_path, rec_path + ".bak-partladder")
    recs, cats = R["recipes"], R["categories"]
    byname = {rc.get("resultPartName"): rid for rid, rc in recs.items()
              if rc.get("resultMode") == "part" and rc.get("resultPartType") in TYPES}
    preserved_recipe_names = {name for _, name in PRESERVE_PARTS} | {n for _, n in external}
    for dead in ([] if ADD_ONLY else [n for n in byname
                 if not any(c["name"] == n for c in cat) and n not in preserved_recipe_names]):
        rid = byname.pop(dead)
        recs.pop(rid, None)
        if rid in cats.get("부품", []):
            cats["부품"].remove(rid)
    nxt = 60
    for c in cat:
        is_spawn_low = c["village"] == "스폰마을" and c["grade"] in LOW_GRADE_COMMON
        if c["grade"] == "E" and not is_spawn_low:
            continue                                  # 다른 마을의 E급은 시작 부품 규칙을 따른다.
        rid = byname.get(c["name"])
        if rid is None:
            while f"P{nxt}" in recs:
                nxt += 1
            rid = f"P{nxt}"; nxt += 1
        if is_spawn_low:
            # 저티어는 광산 압축재·타지역 특산재·중간재를 거치지 않는다.
            items = [ing(m, q) for m, q in LOW_GRADE_COMMON[c["grade"]]]
            items.append(ing(LOW_GRADE_TYPE_MAT[c["type"]], LOW_GRADE_TYPE_QTY[c["grade"]]))
            items.extend(ing(m, q) for m, q in LOW_GRADE_BUILD_EXTRA[c["grade"]].get(c["build"], []))
        else:
            mat = (BUILD_MAT_S if c["grade"] == "S" else
                   BUILD_MAT_A if c["grade"] == "A" else BUILD_MAT)[
                "특화형" if c["build"] == "복합" else c["build"]]
            items = [ing(m, q) for m, q in COMMON[c["grade"]]]
            items.insert(1, ing(mat, MAT_QTY[c["grade"]]))
        recs[rid] = {"id": rid, "category": "부품", "displayName": c["name"],
                     # ★출처가 히든-*/심해면 상점에 안 오르므로 locked 를 켜면 해금 경로가 없다.
                     "locked": not (c["village"] in ("상단마을", "왕도")
                                    or str(c.get("village", "")).startswith(("히든", "심해"))),
                     "resultMode": "part", "drillTier": 0, "village": {
                         "스폰마을": "스폰", "사막마을": "사막", "상단마을": "상단", "왕도": "왕도",
                         # 히든은 본 마을 조합대에서 만든다(레시피 해금이 히든 진입 보상).
                         "히든-스폰마을": "스폰", "히든-사막마을": "사막", "히든-상단마을": "상단",
                         "심해": "", "히든-전설": ""}[c["village"]],
                     "resultPartType": c["type"], "resultPartName": c["name"],
                     "ingredients": merge(items)}
        if rid not in cats["부품"]:
            cats["부품"].append(rid)
    json.dump(R, open(rec_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"recipes.json: 부품 레시피 {len(cats['부품'])}개")

    if WRITE_SHOPS:
        npc_path = os.path.join(SRC, "npc.json")
        N = json.load(open(npc_path, encoding="utf-8"))
        shutil.copy(npc_path, npc_path + ".bak-partladder")
        npcs = N["npcs"] if isinstance(N, dict) and "npcs" in N else N
        items = npcs.items() if isinstance(npcs, dict) else [(x.get("id"), x) for x in npcs]
        allparts = {c["name"] for c in cat}
        want = {v: [c["name"] for c in cat if c["village"] == v] for v in ("스폰마을", "사막마을")}
        hit = 0
        for k, v in items:
            si = v.get("shopItems")
            if not si:
                continue
            for vil, names in want.items():
                if any(n in si for n in names):
                    v["shopItems"] = [x for x in si if x not in allparts] + names
                    hit += 1
                    break
        json.dump(N, open(npc_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"npc.json: 상점 {hit}곳 부품 목록 갱신")

    print(f"\n{'타입':<4}{'등급':<3}{'Lv':>4}{'가격':>8}  {'마을':<7}{'빌드':<6}{'이름':<18}스탯")
    for c in cat:
        tag = "＋" if c["new"] else "  "
        print(f"{c['type']:<4}{c['grade']:<3}{c['lv']:>4}{c['price']:>8}  {c['village']:<7}"
              f"{c['build']:<6}{tag}{c['name']:<16}{stat_str(c['st'])}")


if __name__ == "__main__":
    main()
