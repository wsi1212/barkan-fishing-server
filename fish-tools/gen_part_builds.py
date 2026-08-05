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

  ★★난이도 스탯 — 구 "낚싯대 전용" 원칙 폐기, 5부품에도 신설 분산(유저 지시: "최종 G를
    낚을 때는 온갖 할 수 있는 난이도감소를 다 써야 겨우 잡을만하게"). SUB_VAL "숙련형" 빌드로
    전 타입에 추가(E0 D1 C2 B3 A4 — 설계 원안). 근거(minigame_sim.py Monte Carlo, 반응250ms+핑40ms):
      로드 단독 최대(기존) rodBonus=12 → G등급 성공률 0.0%(사실상 불가)
      로드12 + 부품5종 전부 숙련형 = 총 rodBonus **37**(★A값4에 사막마을 극단형 shape배율1.15가
        곱해져 4×1.15=4.6→반올림5, 5×5=25+12=37 — 설계 원안 32보다 실제로 더 큼, 아래 수치가 진짜
        확정값) → G등급 성공률 **≈71%**(rb=36~37 구간, minigame_sim.py 실측)
    "온갖 걸 다 써야"는 만족(부품 5개 전부 다른 빌드 대신 숙련형을 골라야 함=다른 정체성 스탯을
    전부 포기하는 트레이드오프). "겨우"보다는 후하게 나왔지만(11%가 아니라 71%) G 자체가 피티 반영
    ~3,000+캐스트당 1마리라 이미 극히 희귀하므로 이정도 성공률이 과하다고 보진 않음 — 더 빡빡하게
    하려면 A값을 4→3으로(5×3+12=27, rb=27 구간 G≈1.7%) 낮추면 된다.
    ★부품엔 강화(EnhanceManager)가 없다(강화는 "낚싯대별"·부품엔 미적용) — 위 37이 진짜 최댓값.
    ★stat_value.py MAX_MAGNITUDE·gear_payback.py의 난이도 상한(12)은 이 변경으로 낡았다 —
    후속 감사에서 37로 갱신하고 E/H절을 재판정할 것(이번 턴 범위 밖으로 명시적으로 남김).
  §8.1 내구보존은 <b>낚싯대 전용</b>(변경 없음) — 부품엔 절대 넣지 않는다.

빌드 6종(그 부품이 무엇에 특화됐는지):
  특화형 = 타입 주스탯 최대치      행운형 = 행운 + 등급업
  크리형 = 크리확률 + 크기          상인형 = 판매보너스 + 더블찬스
  성장형 = 경험치 + 트리플찬스(★구 도망감소→트리플찬스로 교체, 트리플찬스 신설)
  숙련형 = 난이도(★신설, 전 타입 공통)

★기존 부품 이름은 바꾸지 않는다 — 장착 슬롯·부품 인벤·도감("type::name")·레시피·NPC 상점
  목록에 문자열로 박혀 있다. 스탯/레벨/가격만 재조정하고 빈 칸을 새 부품으로 채운다.
  (개발자 부품 8종은 삭제 — 유저 요청.)
"""
import json, shutil, sys, os

SRC = sys.argv[1]
WRITE_SHOPS = "--shops" in sys.argv

TYPES = ["릴", "줄", "바늘", "미끼", "찌"]
# ★2026-08-05 재배정 — 구 {릴:도망감소, 줄:크리배율, 바늘:등급업, 미끼:경험치, 찌:크기} 폐기.
TYPE_PRIMARY = {"릴": "경험치", "줄": "도망감소", "바늘": "크리확률", "미끼": "행운", "찌": "등급업"}

GRADE_LEVEL = {"E": 1, "D": 5, "C": 10, "B": 20, "A": 40}
LEVEL_BAND = {"D": (5, 9), "C": (10, 19), "B": (20, 34), "A": (40, 52)}
# ★2026-08-05 전면 리프라이싱 (price_ladder.py). 구 밴드는 수입 대비 2자리 낮았다.
PRICE_BAND = {"D": (4000, 11000), "C": (13000, 32000), "B": (40000, 100000),
              "A": (390000, 970000)}
SUB_BAND = {
    ("스폰마을", "B"): ((20, 27), (40000, 70000)),
    ("사막마을", "B"): ((28, 34), (70000, 100000)),
    ("사막마을", "A"): ((40, 44), (390000, 590000)),
    ("상단마을", "A"): ((44, 49), (590000, 850000)),
    ("왕도", "A"):     ((49, 52), (850000, 970000)),
}
# 미끼는 소모품이라 가격 단위가 다르다(개당). 위 밴드에 이 배수를 곱한다.
# ★미끼 1개 = 내구도만큼의 캐스트 → 유지비/h = (캐스트/h ÷ 내구) × 가격. A티어에서 그 유지비가
#   수입의 3%가 되도록 역산한 값(구 0.022는 새 밴드에 그대로 곱하면 유지비가 3배로 튄다).
BAIT_PRICE_MULT = 0.0165
DURAB = {"E": 40, "D": 70, "C": 130, "B": 220, "A": 340}

# 타입 주스탯 등급별 값 (§8.2~8.6 범위 상단 = 특화형, 하단 = 그 외 빌드의 기본치)
# ★2026-08-05: 크리확률(바늘)·행운(미끼)을 신규 TYPE_VAL로 승격(구엔 SUB_VAL에서만 존재).
TYPE_VAL = {
    "도망감소": {"E": 3, "D": 8,  "C": 15, "B": 22, "A": 30},
    "크리배율": {"E": 1, "D": 2,  "C": 3,  "B": 4,  "A": 5},    # 바늘 고정 부스탯(항상 동반)
    "등급업":   {"E": 0, "D": 3,  "C": 6,  "B": 10, "A": 15},
    "경험치":   {"E": 0, "D": 20, "C": 50, "B": 80, "A": 110},   # 미끼는 소모품이라 라이브값이 문서보다 높다
    "크기":     {"E": 0, "D": 3,  "C": 6,  "B": 10, "A": 15},
    "크리확률": {"E": 2, "D": 6,  "C": 12, "B": 20, "A": 30},   # ★바늘 주스탯 신설
    "행운":     {"E": 3, "D": 8,  "C": 14, "B": 22, "A": 32},   # ★미끼 주스탯 신설 — 공통 LUCK_CAP(A12)보다 훨씬 높다
}
TYPE_BASE = {   # 특화형이 아닌 빌드도 그 타입다움은 남긴다(주스탯 하한)
    "도망감소": {"E": 3, "D": 5,  "C": 10, "B": 13, "A": 16},
    "크리배율": {"E": 1, "D": 1,  "C": 2,  "B": 3,  "A": 4},
    "등급업":   {"E": 0, "D": 1,  "C": 3,  "B": 5,  "A": 8},
    "경험치":   {"E": 0, "D": 10, "C": 25, "B": 45, "A": 60},
    "크기":     {"E": 0, "D": 1,  "C": 3,  "B": 5,  "A": 8},
    "크리확률": {"E": 1, "D": 3,  "C": 6,  "B": 10, "A": 16},
    # ★행운은 TYPE_VAL/TYPE_CAP 대비 비율을 다른 스탯들(≈0.5~0.6)과 맞춘다. 처음에 15/22(B)로
    #   너무 높게 잡아서 행운형(비-특화형)이 특화형과 거의 동률이 되는 완전열등 버그가 났었다.
    "행운":     {"E": 2, "D": 4,  "C": 7,  "B": 12, "A": 17},
}
# 빌드 부스탯 (타입 무관)
SUB_VAL = {
    "행운":       {"E": 2, "D": 4, "C": 6,  "B": 9,  "A": 12},   # ★행운형 주력치 (미끼 아닌 타입용 — 미끼는 TYPE_VAL 행운 사용)
    "등급업":     {"E": 0, "D": 2, "C": 4,  "B": 6,  "A": 9},
    "크리확률":   {"E": 1, "D": 2, "C": 4,  "B": 8,  "A": 12},
    "크기":       {"E": 1, "D": 2, "C": 5,  "B": 7,  "A": 11},
    "판매보너스": {"E": 1, "D": 3, "C": 6,  "B": 10, "A": 16},
    "더블찬스":   {"E": 1, "D": 2, "C": 5,  "B": 7,  "A": 10},
    "경험치":     {"E": 0, "D": 8, "C": 18, "B": 30, "A": 45},
    "도망감소":   {"E": 2, "D": 4, "C": 8,  "B": 12, "A": 18},
    # ★2026-08-05 신설 — 트리플찬스(구 도망감소 자리 대체), 난이도(전 타입 공통 신설)
    "트리플찬스": {"E": 0, "D": 1, "C": 1,  "B": 2,  "A": 3},
    "난이도":     {"E": 0, "D": 1, "C": 2,  "B": 3,  "A": 4},
}
BUILDS = {
    "특화형": [],                       # 타입 주스탯 최대 + 행운
    "행운형": ["행운", "등급업"],
    "크리형": ["크리확률", "크기"],
    "상인형": ["판매보너스", "더블찬스"],
    "성장형": ["경험치", "트리플찬스"],  # ★구 도망감소 → 트리플찬스 (신규 스탯 도입)
    "숙련형": ["난이도"],                # ★신설 — 전 타입 공통, 단일축
}
SHAPE = {"기본형": (1.00, 1.00), "극단형": (1.15, 0.80), "균형형": (0.90, 1.25), "왕실형": (1.10, 1.10)}
HYBRID_SCALE = 0.8
# 마을 테마 (§17) — 낚싯대와 동일 규칙
VILLAGE_THEME = {"사막마을": ["등급업", "크기"], "상단마을": ["판매보너스", "크리확률"],
                 "왕도": ["행운", "더블찬스"]}
THEME_VAL = {"등급업": {"D": 1, "C": 2, "B": 3, "A": 5}, "크리확률": {"D": 1, "C": 2, "B": 3, "A": 5},
             "크기": {"D": 2, "C": 3, "B": 5, "A": 8}, "판매보너스": {"D": 2, "C": 3, "B": 5, "A": 8},
             "행운": {"D": 1, "C": 2, "B": 3, "A": 4}, "더블찬스": {"D": 1, "C": 2, "B": 3, "A": 4}}
# 상한 — 행운은 낚싯대와 같은 이유로 자른다(부품은 5개 겹쳐 끼므로 개당 상한이 더 중요)
LUCK_CAP = {"E": 2, "D": 4, "C": 6, "B": 9, "A": 12}
# ★행운형이 아닌 부품의 행운 기본치. 이걸 SUB_VAL과 같게 두면 모든 부품 행운이 같아져
#   행운형이라는 빌드 자체가 사라진다(바늘 D에서 특화형과 행운형이 완전 동일해졌다).
LUCK_BASE = {"E": 2, "D": 2, "C": 3, "B": 4, "A": 6}
# ★타입 주스탯 상한 (§8.2~8.6) — 마을 배수가 문서 범위를 밀어내지 못하게. 낚싯대 난이도와 같은 처리.
TYPE_CAP = {"도망감소": {"E": 3, "D": 8, "C": 15, "B": 22, "A": 30},
            "크리배율": {"E": 1, "D": 2, "C": 3, "B": 4, "A": 5},
            "등급업":   {"E": 0, "D": 3, "C": 6, "B": 10, "A": 15},
            "경험치":   {"E": 0, "D": 20, "C": 50, "B": 80, "A": 110},
            "크기":     {"E": 0, "D": 3, "C": 6, "B": 10, "A": 15},
            "크리확률": {"E": 2, "D": 6, "C": 12, "B": 20, "A": 30},   # ★신설(바늘)
            "행운":     {"E": 3, "D": 8, "C": 14, "B": 22, "A": 32}}   # ★신설(미끼, 공통상한보다 높음)
# ★교차 상한 — "남의 주스탯"은 그 타입 최대치의 절반 수준까지만. 안 걸면 릴이 크기 14를 주고
#   (찌 A 최대치가 15) 찌를 낄 이유가 사라진다. 각 부품이 자기 스탯을 소유해야 5슬롯이 의미 있다.
CROSS_CAP = {"도망감소": {"D": 4, "C": 8, "B": 12, "A": 16},
             "등급업":   {"D": 2, "C": 3, "B": 5, "A": 8},
             "크기":     {"D": 2, "C": 3, "B": 5, "A": 8},
             "경험치":   {"D": 8, "C": 18, "B": 30, "A": 50},
             "크리배율": {"D": 1, "C": 1, "B": 2, "A": 2},
             "크리확률": {"D": 3, "C": 6, "B": 10, "A": 15}}   # ★신설 — 바늘 아닌 타입이 크리형 빌드로 얻을 때

# ★2026-08-05 난이도 재교정 — 구 1.5는 stat_value.py 구공식 시절 값. 오늘 stat_value.py를
#   피티MC+실측220포획/h로 교체하며 난이도 정규화가 8.87로 폭증했다(H절: 숙련형 부품이 가격
#   대비 압도적으로 저평가돼 있었다 — 릴C 회수 0.52h vs 철제릴 19.83h 같은 왜곡). SV 정규화 열과 맞춤.
POWER_W = {"도망감소": 0.05, "크리배율": 2.5, "등급업": 1.0, "경험치": 0.45, "크기": 0.65,
           "행운": 0.65, "크리확률": 0.4, "판매보너스": 1.0, "더블찬스": 1.0, "난이도": 8.87,
           "트리플찬스": 0.6}

# ── 격자: (등급, 마을, 성격, [빌드...]) — 모든 타입이 같은 격자를 쓴다 ─────────
# ★2026-08-05 "숙련형"(난이도) 신설 — C/B/A에 걸쳐 두루 배치(유저 지시: 여러 부품에 두루두루).
#   A등급까지 쌓아야 종결 G등급 난이도감소 계산(gen_part_builds.py 상단 doc)이 맞는다.
GRID = [
    ("E", "스폰마을", "기본형", ["특화형"]),
    ("D", "스폰마을", "기본형", ["특화형", "행운형"]),
    ("C", "스폰마을", "기본형", ["특화형", "크리형", "상인형", "성장형", "숙련형"]),
    ("B", "스폰마을", "기본형", ["특화형", "행운형", "크리형", "숙련형"]),
    ("B", "사막마을", "극단형", ["특화형", "상인형"]),
    ("A", "사막마을", "극단형", ["특화형", "행운형", "숙련형"]),
    ("A", "상단마을", "균형형", ["특화형", "크리형", "상인형", "숙련형"]),
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
    "릴": {("D", "스폰마을", "행운형"): "행운 릴", ("C", "스폰마을", "상인형"): "황동 릴",
           ("C", "스폰마을", "성장형"): "수련용 릴", ("B", "스폰마을", "행운형"): "길조 릴",
           ("B", "사막마을", "상인형"): "행렬 릴", ("A", "사막마을", "행운형"): "신기루 릴",
           ("A", "사막마을", "특화형"): "열사 릴", ("A", "상단마을", "상인형"): "교역 릴",
           # ★2026-08-05 숙련형(난이도) 신설
           ("C", "스폰마을", "숙련형"): "숙련 릴", ("B", "스폰마을", "숙련형"): "노련한 릴",
           ("A", "사막마을", "숙련형"): "사막 노장 릴", ("A", "상단마을", "숙련형"): "정밀 감속 릴"},
    "줄": {("D", "스폰마을", "행운형"): "행운실", ("C", "스폰마을", "크리형2"): "",
           ("B", "스폰마을", "크리형"): "합사 카본줄", ("B", "사막마을", "특화형"): "사막 강선",
           ("B", "사막마을", "상인형"): "대상 밧줄", ("A", "사막마을", "행운형"): "신기루 줄",
           ("A", "상단마을", "상인형"): "교역 합사줄",
           ("C", "스폰마을", "숙련형"): "숙련줄", ("B", "스폰마을", "숙련형"): "노련한줄",
           ("A", "사막마을", "숙련형"): "사막 노장줄", ("A", "상단마을", "숙련형"): "정밀 감속줄"},
    "바늘": {("C", "스폰마을", "행운형2"): "", ("B", "스폰마을", "행운형"): "길조 바늘",
             ("B", "사막마을", "특화형"): "전갈 바늘", ("B", "사막마을", "상인형"): "행렬 바늘",
             ("A", "사막마을", "행운형"): "사구 바늘", ("A", "상단마을", "크리형"): "세공 바늘",
             ("A", "상단마을", "상인형"): "교역 바늘",
             ("C", "스폰마을", "숙련형"): "숙련 바늘", ("B", "스폰마을", "숙련형"): "노련한 바늘",
             ("A", "사막마을", "숙련형"): "사막 노장 바늘", ("A", "상단마을", "숙련형"): "정밀 감속 바늘"},
    "미끼": {("B", "스폰마을", "행운형"): "길조 미끼", ("B", "스폰마을", "크리형"): "번개 미끼",
             ("B", "사막마을", "상인형"): "행렬 미끼", ("A", "사막마을", "행운형"): "신기루 미끼",
             ("A", "사막마을", "특화형"): "오아시스 정수 미끼", ("A", "상단마을", "상인형"): "교역 미끼",
             ("C", "스폰마을", "숙련형"): "숙련 미끼", ("B", "스폰마을", "숙련형"): "노련한 미끼",
             ("A", "사막마을", "숙련형"): "사막 노장 미끼", ("A", "상단마을", "숙련형"): "정밀 감속 미끼"},
    "찌": {("D", "스폰마을", "행운형"): "행운 찌", ("C", "스폰마을", "상인형"): "황동 찌",
           ("C", "스폰마을", "성장형"): "수련용 찌", ("B", "사막마을", "특화형"): "모래 찌",
           ("B", "사막마을", "상인형"): "행렬 찌", ("A", "사막마을", "행운형"): "신기루 찌",
           ("A", "상단마을", "크리형"): "세공 찌", ("A", "상단마을", "상인형"): "교역 찌",
           ("C", "스폰마을", "숙련형"): "숙련 찌", ("B", "스폰마을", "숙련형"): "노련한 찌",
           ("A", "사막마을", "숙련형"): "사막 노장 찌", ("A", "상단마을", "숙련형"): "정밀 감속 찌"},
}
# 삭제 허용 (개발자 부품)
RETIRED_PREFIX = "개발자"

STAT_ORDER = ["도망감소", "크리배율", "등급업", "크리확률", "크기", "경험치",
              "판매보너스", "더블찬스", "트리플찬스", "행운", "난이도"]
# 등급별 제작 재료
COMMON = {
    "D": [("정제된갈고리", 4), ("강화실", 4), ("물고기비늘", 6)],
    "C": [("정제된갈고리", 8), ("강화철괴", 6), ("진주", 6), ("압축흑정석", 3)],
    "B": [("강철심", 14), ("강화철괴", 12), ("진주", 16), ("압축흑정석", 8)],
    "A": [("강철심", 26), ("진주", 30), ("압축흑정석", 22), ("별빛진주", 4)],
}
BUILD_MAT = {"특화형": "녹슨부품", "행운형": "행운의구슬", "크리형": "안개수정",
             "상인형": "보석", "성장형": "깃털찌조각", "숙련형": "낡은갈고리"}
BUILD_MAT_A = {"특화형": "강화철괴", "행운형": "행운의매듭", "크리형": "자수정",
               "상인형": "강화에메랄드", "성장형": "별빛진주", "숙련형": "진주조개"}
MAT_QTY = {"D": 4, "C": 8, "B": 14, "A": 24}


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
    return st


def power(st):
    return sum(POWER_W.get(k, 0) * v for k, v in st.items())


def stat_str(st):
    return ",".join(f"{k}:{st[k]}" for k in STAT_ORDER if st.get(k) is not None and st.get(k) != 0) \
           or f"{TYPE_PRIMARY_FALLBACK}:0"


TYPE_PRIMARY_FALLBACK = "행운"


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
    gorder = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4}
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
        luck_cap = TYPE_CAP["행운"][g] if c["type"] == "미끼" else LUCK_CAP[g]
        if c["st"].get("행운", 0) > luck_cap:
            errs.append(f"{c['name']}: 행운 {c['st']['행운']} > 상한 {luck_cap}")
        if "내구보존" in c["st"]:
            errs.append(f"{c['name']}: 내구보존은 낚싯대 전용(§8.1)")
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
    check(cat)
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
    removed = []
    for t in TYPES:
        for n in list(parts[t]):
            if (t, n) in owned:
                continue
            if not n.startswith(RETIRED_PREFIX):
                raise SystemExit(f"카탈로그에 없는 기존 부품(이름 유지 원칙 위반): {t}/{n}")
            del parts[t][n]
            removed.append(f"{t}/{n}")
    P["order"] = [e for e in order if not (e[0] in TYPES and (e[0], e[1]) not in owned)]
    order = P["order"]
    for c in cat:
        parts[c["type"]][c["name"]] = "|".join([
            c["name"], c["grade"], str(c["price"]), str(c["dur"]),
            stat_str(c["st"]), str(c["lv"]), c["village"]])
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
    for dead in [n for n in byname if not any(c["name"] == n for c in cat)]:
        rid = byname.pop(dead)
        recs.pop(rid, None)
        if rid in cats.get("부품", []):
            cats["부품"].remove(rid)
    nxt = 60
    for c in cat:
        if c["grade"] == "E":
            continue                                  # 시작 부품 — 레시피 없음
        rid = byname.get(c["name"])
        if rid is None:
            while f"P{nxt}" in recs:
                nxt += 1
            rid = f"P{nxt}"; nxt += 1
        mat = (BUILD_MAT_A if c["grade"] == "A" else BUILD_MAT)[
            "특화형" if c["build"] == "복합" else c["build"]]
        items = [ing(m, q) for m, q in COMMON[c["grade"]]]
        items.insert(1, ing(mat, MAT_QTY[c["grade"]]))
        recs[rid] = {"id": rid, "category": "부품", "displayName": c["name"],
                     "locked": c["village"] not in ("상단마을", "왕도"),
                     "resultMode": "part", "drillTier": 0, "village": {
                         "스폰마을": "스폰", "사막마을": "사막", "상단마을": "상단", "왕도": "왕도"}[c["village"]],
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
