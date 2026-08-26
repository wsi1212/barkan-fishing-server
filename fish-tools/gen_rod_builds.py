#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""낚싯대 빌드 카탈로그 생성기 — parts.json / recipes.json / enhance.json 재생성.

★수치를 바꿀 땐 이 파일을 고쳐 다시 돌린다. 손으로 JSON을 만지지 말 것.
   사용법: python3 gen_rod_builds.py <BlockShip 데이터 폴더> [--shops]

────────────────────────────────────────────────────────────────────────────
설계 (balance.md 준수 — 2026-08-03, 작살 사다리(gen_spear_builds.py)와 같은 골격)
────────────────────────────────────────────────────────────────────────────
  §17 등급별 필요 레벨  E=1 D=5 C=10 B=20 A=40 S=60  ← ★고정값이 아니라 <b>하한</b>
  §7  등급별 가격대      ★2026-08-05 리프라이싱 (구 D 200~600 … S 85,000~90,000 폐기)
                         D 9,000~22,000 / C 26,000~65,000 / B 80,000~210,000
                         A 780,000~1,940,000 / S 3,400,000~3,620,000
                         근거 = 풀세팅이 그 티어 구간 수입의 45% (price_ladder.py)
  §17 마을 분포          스폰 E~B · 사막 B~A · 상단 A · 히든 A~S
  §8.1 낚싯대 주스탯 = 난이도(E0 D1 C1~2 B2~3 A3~5 S5~8) — 낚싯대 전용
       ★2026-08-27 «내구보존» 스탯 전면 폐지(정규화 0.08~0.27 = 있으나 없으나).
       행운 = 전 등급 보편 부스탯(일반 E1 D2 C2~4 B3~6 A5~10 S8~14 / 히든 A14~18 S20~22)

★**기존 22종은 이름을 바꾸지 않는다.** 낚싯대 이름은 플레이어 장착 아이템·강화 기록
  (enhance.json table)·NPC 상점 목록·퀘스트 보상·레시피 id(rodNameToId)에 전부 문자열로
  박혀 있다. 이름을 바꾸면 그 연결이 통째로 끊긴다 → 스탯/등급/레벨/가격만 재조정하고,
  빈 칸(마을×빌드×등급)은 새 낚싯대로 채운다.

빌드 5종(주력 쌍 = 그 낚싯대의 정체성):
  숙련형 = 난이도 + 도망감소   행운형 = 행운 + 등급업
  크리형 = 크리확률 + 크기      상인형 = 판매보너스 + 더블찬스
  성장형 = 경험치 + 트리플찬스

★난이도·행운은 빌드와 무관하게 등급 하한이 깔린다(§8.1 보편 부스탯). 난이도가 0이면
  미니게임 자체가 안 되고, 행운 0이면 등급 롤이 죽는다.

마을 성격(같은 등급이라도 형태가 달라 상위호환이 되지 않게):
  스폰 = 기본형 / 사막 = 극단형(주력↑ 보조↓) / 상단 = 균형형(주력↓ 보조↑)
  왕도 = 복합형(두 계통 80%씩) / 히든 = 전설형(주력↑ + 행운 상단)
"""
import json, shutil, sys, os

SRC = sys.argv[1]
WRITE_SHOPS = "--shops" in sys.argv
FORCE = "--force" in sys.argv       # 라이브 값 덮어쓰기 허용 (guard_drift 참조)

#: 등급 진입 레벨. ★D 5 → 3 (2026-08-27) — 튜토 종료 시점이 Lv3 인데 D 하한이 5 라
#  Lv3~4 가 죽은 구간이었다. 티어 내부 계단을 보존한 −2 시프트(D 밴드 5~9 → 3~7).
GRADE_LEVEL = {"E": 1, "D": 3, "C": 10, "B": 20, "A": 40, "S": 60}
LEVEL_BAND = {"D": (3, 7), "C": (10, 18), "B": (20, 34), "A": (40, 58), "S": (60, 66)}
# ★2026-08-05 전면 리프라이싱 — 근거·재현: balance-audit/scripts/price_ladder.py
#   구 밴드(D 280~600 … S 85,000~90,000)는 수입 대비 2자리 낮았다. 티어 구간을 다 플레이해서 버는
#   돈 대비 그 티어 풀세팅 값이 0.8~3.7%뿐 → "종결 장비 풀세팅 1시간 43분", 레벨축(Lv70=46h)보다
#   장비축이 27배 빨리 끝났다. 새 기준 = **풀세팅(낚싯대2 + 부품5 가중) = 그 티어 구간 수입의 45%**.
#   구간 수입은 실측 처리량(220 포획/h, 크기점수 65.6)과 피티 반영 몬테카를로로 산출.
PRICE_BAND = {"D": (9000, 22000), "C": (26000, 65000), "B": (80000, 210000),
              "A": (780000, 1940000), "S": (3400000, 3620000)}
# 마을×등급 하위 밴드 — §17 성장경로(스폰 1~20 → 사막 20~40 → 상단 40~ → 왕도 → 히든/전설)
#   ★구 밴드 내 상대위치를 그대로 새 밴드에 사상했다(성장경로 순서 보존).
SUB_BAND = {
    ("스폰마을", "B"): ((20, 27), (80000, 150000)),
    ("사막마을", "B"): ((26, 34), (140000, 210000)),
    ("사막마을", "A"): ((40, 45), (780000, 1140000)),
    ("상단마을", "A"): ((44, 50), (1140000, 1520000)),
    ("왕도", "A"):     ((50, 54), (1520000, 1770000)),
    ("히든", "A"):     ((52, 58), (1640000, 1940000)),
}
DURAB = {"E": 60, "D": 110, "C": 200, "B": 320, "A": 480, "S": 800}
# 등급 하한 — 어떤 빌드든 이 아래로는 안 내려간다(§8.1 보편 부스탯)
FLOOR = {
    "난이도": {"E": 0, "D": 1, "C": 1, "B": 2, "A": 3, "S": 5},
    "행운":   {"E": 1, "D": 2, "C": 3, "B": 4, "A": 6, "S": 9},
}
# 히든(마을 전설)은 행운 상단 — §8.1 "히든 A=14~18, S=20~22"
HIDDEN_LUCK = {"A": 16, "S": 20}
# ★상한 — 난이도와 행운은 balance.md가 범위를 못박은 스탯이라 마을 배수를 적용하지 않고 여기서 자른다.
#   (난이도는 2026-07-25 반응속도+핑 Monte Carlo로 목표치를 정한 값이라 임의로 넘기면 미니게임이 무너진다.)
CAP = {
    "난이도": {"E": 0, "D": 1, "C": 2, "B": 3, "A": 5, "S": 8},
    "행운":   {"E": 2, "D": 4, "C": 6, "B": 9, "A": 14, "S": 22},
}
CAP_HIDDEN_LUCK = {"A": 18, "S": 22}

# 성능 점수 가중치 — balance-audit references/stat-values.md **최대기여 정규화** 열 기준.
#  ★per-단위 정규화(경험치 1.0·트리플 2.0)를 쓰면 성장형이 모든 밴드 최상위를 독점하고
#    S가 A보다 낮게 나온다 — 경험치는 "레벨링 국면 한정"(만렙 후 0), 트리플은 실현가능치가
#    낮아서 per-단위가 실제 기여를 과대평가한다. 최대기여 쪽이 등급 서열과 맞다.
POWER_W = {
    # ★2026-08-05 재교정 — 구 1.5는 stat_value.py 구공식(flat확률+150캐스트) 시절 최대기여(0.27)
    #   기준. 오늘 stat_value.py를 피티MC+실측220포획/h로 전면 교체하며 난이도 정규화가 8.87로
    #   폭증(피티 반영 시 고등급 비중이 커져 "실제로 잡히느냐"의 가치가 커짐) — 구 가중치를 그대로
    #   두면 난이도 보유 아이템(전승자/여명 등 A급 특화)이 가격 대비 실제가치를 계속 못 반영해
    #   회수시간 역전이 난다(H절 감사에서 열사 3.80h ↔ 전승자 12.35h로 확인). SV 정규화 열과 맞춤.
    "난이도": 8.87,
    "도망감소": 0.36,     # 2026-08-27 내구보존 폐지 → 숙련형 부스탯이 여기로
    "행운": 0.65, "등급업": 1.0, "크리확률": 0.4, "크기": 0.65,
    "판매보너스": 1.0, "더블찬스": 1.0,
    "경험치": 0.45,       # 레벨링 국면 한정 가치 → 절반만 인정
    "트리플찬스": 0.6,
}

PRIMARY = {
    "난이도":     {"D": 1,  "C": 2,  "B": 3,  "A": 5,  "S": 8},
    "도망감소":   {"E": 1, "D": 3,  "C": 6,  "B": 10, "A": 18, "S": 26},
    "행운":       {"D": 4,  "C": 6,  "B": 9,  "A": 14, "S": 20},
    "등급업":     {"E": 1, "D": 1,  "C": 2,  "B": 4,  "A": 8,  "S": 14},
    "크리확률":   {"E": 1, "D": 2,  "C": 4,  "B": 6,  "A": 10, "S": 15},
    "크기":       {"E": 1, "D": 2,  "C": 4,  "B": 6,  "A": 10, "S": 14},
    "판매보너스": {"E": 1, "D": 3,  "C": 6,  "B": 10, "A": 18, "S": 24},
    "더블찬스":   {"E": 1, "D": 1,  "C": 2,  "B": 4,  "A": 7,  "S": 10},
    "경험치":     {"E": 3, "D": 7, "C": 12, "B": 20, "A": 30, "S": 45},   # ★2026-08-26 ×2/3 (구 5/10/18/28/45/65)
    "트리플찬스": {"D": 0,  "C": 0,  "B": 1,  "A": 3,  "S": 5},
}
BUILDS = {
    "숙련형": ["난이도", "도망감소"],
    "행운형": ["행운", "등급업"],
    "크리형": ["크리확률", "크기"],
    "상인형": ["판매보너스", "더블찬스"],
    "성장형": ["경험치", "트리플찬스"],
}
SHAPE = {"기본형": (1.00, 1.00), "극단형": (1.00, 0.85), "균형형": (0.95, 1.25),
         "왕실형": (1.10, 1.10), "전설형": (1.10, 1.10)}
# ★마을 성격은 배수가 아니라 <b>테마 스탯</b>으로 낸다. 난이도·행운이 상한에 걸려 배수로는
#   차별화가 안 되고(사막 숙련형이 스폰 숙련형의 완전열등이 됐다), balance.md §17이 이미
#   마을 테마를 정해 뒀다 — 사막=등급업·크기(사막 특수), 상단=판매·정밀, 왕도=견고.
VILLAGE_THEME = {"사막마을": ["등급업", "크기"], "상단마을": ["판매보너스", "크리확률"],
                 "왕도": ["도망감소", "행운"]}
THEME_VAL = {
    "등급업":     {"D": 1, "C": 2, "B": 3, "A": 5,  "S": 7},
    "크리확률":   {"D": 1, "C": 2, "B": 3, "A": 5,  "S": 7},
    "크기":       {"D": 2, "C": 3, "B": 5, "A": 8,  "S": 12},
    "판매보너스": {"D": 2, "C": 3, "B": 5, "A": 8,  "S": 12},
    "도망감소":   {"D": 2, "C": 4, "B": 6, "A": 10, "S": 14},
}
HYBRID_SCALE = 0.8

# ── 사다리: (이름, 빌드, 등급, 마을(recipe village), 출처, 성격, 신규?) ─────────
#  기존 22종은 new=False — 이름 유지, 스탯만 재조정.
LADDER = [
    # ═══ 스폰마을 E (튜토/시작) ═══
    ("나뭇가지",           "숙련형", "E", "스폰", "스폰마을", "기본형", False),
    ("초보 낚싯대",        "크리형", "E", "스폰", "스폰마을", "기본형", False),
    # ═══ 스폰마을 D (Lv5~9) — 5빌드 ═══
    ("튼튼한 막대기",      "숙련형", "D", "스폰", "스폰마을", "기본형", True),
    ("대나무 막대기",      "행운형", "D", "스폰", "스폰마을", "기본형", False),
    ("낚시견습생의 낚싯대", "크리형", "D", "스폰", "스폰마을", "기본형", False),
    ("장터 낚싯대",        "상인형", "D", "스폰", "스폰마을", "기본형", True),
    ("수련생 낚싯대",      "성장형", "D", "스폰", "스폰마을", "기본형", True),
    # ═══ 스폰마을 C (Lv10~18) — 5빌드 ═══
    ("참나무 낚싯대",      "숙련형", "C", "스폰", "스폰마을", "기본형", False),
    ("잉어꾼의 낚싯대",    "행운형", "C", "스폰", "스폰마을", "기본형", False),
    ("낚시꾼의 낚싯대",    "크리형", "C", "스폰", "스폰마을", "기본형", False),
    ("장사꾼의 낚싯대",    "상인형", "C", "스폰", "스폰마을", "기본형", True),
    ("경험의 낚싯대",      "성장형", "C", "스폰", "스폰마을", "기본형", False),
    # ═══ 스폰마을 B (Lv20~27) — 5빌드 ═══
    ("전문가 낚싯대",      "숙련형", "B", "스폰", "스폰마을", "기본형", False),
    ("숙련자의 낚싯대",    "행운형", "B", "스폰", "스폰마을", "기본형", False),
    ("예리한 낚싯대",      "크리형", "B", "스폰", "스폰마을", "기본형", True),
    ("거래상의 낚싯대",    "상인형", "B", "스폰", "스폰마을", "기본형", True),
    ("학도의 낚싯대",      "성장형", "B", "스폰", "스폰마을", "기본형", True),
    # ═══ 사막마을 B (Lv26~34) — 극단형 5빌드 ═══
    ("모래 낚싯대",        "숙련형", "B", "사막", "사막마을", "극단형", True),
    ("사구의 낚싯대",      "행운형", "B", "사막", "사막마을", "극단형", True),
    ("전갈 낚싯대",        "크리형", "B", "사막", "사막마을", "극단형", True),
    ("행렬의 낚싯대",      "상인형", "B", "사막", "사막마을", "극단형", True),
    ("유목민 낚싯대",      "성장형", "B", "사막", "사막마을", "극단형", True),
    # ═══ 사막마을 A (Lv40~45) — 극단형 5빌드 ═══
    ("열사의 낚싯대",      "숙련형", "A", "사막", "사막마을", "극단형", True),
    ("오아시스 낚싯대",    "행운형", "A", "사막", "사막마을", "극단형", True),
    ("사막 낚싯대",        "크리형", "A", "사막", "사막마을", "극단형", False),
    ("교역로 낚싯대",      "상인형", "A", "사막", "사막마을", "극단형", True),
    ("고고학자의 낚싯대",  "성장형", "A", "사막", "사막마을", "극단형", True),
    # ═══ 상단마을 A (Lv44~50) — 균형형 5빌드 ═══
    ("흑단목 낚싯대",      "숙련형", "A", "상단", "상단마을", "균형형", False),
    ("감별사의 낚싯대",    "행운형", "A", "상단", "상단마을", "균형형", True),
    ("정밀 낚싯대",        "크리형", "A", "상단", "상단마을", "균형형", True),
    ("무역상의 낚싯대",    "상인형", "A", "상단", "상단마을", "균형형", True),
    ("회계사의 낚싯대",    "성장형", "A", "상단", "상단마을", "균형형", True),
    # ═══ 히든 (마을 전설 A) — 마을×빌드 전체(3마을 × 5빌드). 기존 6종 + 신규 9종 ═══
    ("수호자의 낚싯대",    "숙련형", "A", "",     "히든-스폰마을", "전설형", False),
    ("등대지기의 낚싯대",  "행운형", "A", "",     "히든-스폰마을", "전설형", True),
    ("여명의 낚싯대",      "크리형", "A", "",     "히든-스폰마을", "전설형", False),
    ("파수꾼의 낚싯대",    "상인형", "A", "",     "히든-스폰마을", "전설형", True),
    ("전승자의 낚싯대",    "성장형", "A", "",     "히든-스폰마을", "전설형", True),
    ("모래폭풍의 낚싯대",  "숙련형", "A", "",     "히든-사막마을", "전설형", True),
    ("신기루 낚싯대",      "행운형", "A", "",     "히든-사막마을", "전설형", False),
    ("전갈왕의 낚싯대",    "크리형", "A", "",     "히든-사막마을", "전설형", True),
    ("사막군주의 낚싯대",  "상인형", "A", "",     "히든-사막마을", "전설형", False),
    ("유적탐사자의 낚싯대", "성장형", "A", "",    "히든-사막마을", "전설형", True),
    ("선단장의 낚싯대",    "숙련형", "A", "",     "히든-상단마을", "전설형", True),
    ("감정왕의 낚싯대",    "행운형", "A", "",     "히든-상단마을", "전설형", True),
    ("세공장의 낚싯대",    "크리형", "A", "",     "히든-상단마을", "전설형", True),
    ("행상인의 낚싯대",    "상인형", "A", "",     "히든-상단마을", "전설형", False),
    ("대상인의 낚싯대",    "성장형", "A", "",     "히든-상단마을", "전설형", False),
]

# ── 복합형: (이름, 빌드1, 빌드2, 등급, 마을, 출처, 신규?) ────────────────────
HYBRIDS = [
    # 마을별 복합형 — "한 계통만 파지 않는" 선택지를 각 마을에도 둔다(왕도만의 특권이 아니게)
    # ★이름은 작살과 같은 <b>시리즈</b>로 맞춘다 — "◯◯ 낚싯대"와 "◯◯ 작살"이 한 세트로 읽히게
    #   (gen_spear_builds.py의 HYBRIDS와 시리즈명이 1:1 대응. 한쪽만 고치지 말 것.)
    ("다목적 낚싯대",      "숙련형", "상인형", "C", "스폰", "스폰마을", True),
    ("겸업 낚싯대",        "행운형", "크리형", "B", "스폰", "스폰마을", True),
    ("만능 낚싯대",        "숙련형", "상인형", "B", "스폰", "스폰마을", True),
    ("유목상단 낚싯대",    "상인형", "행운형", "B", "사막", "사막마을", True),
    ("사막개척 낚싯대",    "숙련형", "성장형", "B", "사막", "사막마을", True),
    ("대상단 낚싯대",      "행운형", "성장형", "A", "사막", "사막마을", True),
    ("사막탐사 낚싯대",    "크리형", "상인형", "A", "사막", "사막마을", True),
    ("정산가의 낚싯대",    "숙련형", "성장형", "A", "상단", "상단마을", True),
    ("항해사의 낚싯대",    "행운형", "상인형", "A", "상단", "상단마을", True),
    ("중개인의 낚싯대",    "크리형", "성장형", "A", "상단", "상단마을", True),
    ("왕실 낚싯대",        "숙련형", "행운형", "A", "왕도", "왕도", True),
    ("근위 낚싯대",        "숙련형", "크리형", "A", "왕도", "왕도", True),
    ("왕도 상회 낚싯대",   "상인형", "성장형", "A", "왕도", "왕도", True),
    ("왕립 서고 낚싯대",   "크리형", "성장형", "A", "왕도", "왕도", True),
    ("왕립 순찰 낚싯대",   "상인형", "숙련형", "A", "왕도", "왕도", True),
    # 전설 S 2종 (기존) — 이름·정체성 유지, 복합형으로 재조정
    ("바르칸 낚싯대",      "상인형", "성장형", "S", "",   "히든-전설", False),
    ("천공의 낚싯대",      "크리형", "상인형", "S", "",   "히든-전설", False),
]

# 개별 정체성 추가 스탯 (프레임워크 밖) — 잉어꾼의 등급특화는 이 낚싯대만의 특징이라 유지
EXTRA = {"잉어꾼의 낚싯대": "등급특화:C:50"}

# ★개발자 낚싯대(개발자 낚싯대·개발자 크리확률)는 2026-08-03 삭제 — 유저 요청.
#   빈 리스트로 두면 build_catalog에 없는 기존 항목이 stale로 잡혀 제거된다.
KEEP_AS_IS = ["잠수부의 낚싯대", "심해 잠수부의 낚싯대", "초보자 낚싯대"]
# ★«재료확률» 축 라인(채집·수집·탐사·발굴·유물 계열)은 이 사다리 소관이 아니다.
#   빌드 5종에 없는 축이고 스탯이 따로 조정된 값이라 이 공식으로 재생성하면 수치가 바뀐다.
#   이름을 일일이 적는 대신 «스탯에 재료확률이 있으면 보존» 규칙으로 잡는다 — 그 라인에
#   항목이 더 늘어도 생성기가 깨지지 않는다(2026-08-24 기준 낚싯대 9종·부품 20종).
#   정식 6번째 빌드로 승격하려면 PRIMARY·POWER_W·BUILDS·LADDER 를 같이 손봐야 한다.
EXTERNAL_AXIS = "재료확률"


def is_external(part_value):
    """parts.json 한 줄(이름|등급|가격|내구|스탯|레벨|출처)이 외부 라인인지."""
    f = part_value.split("|")
    return len(f) > 4 and EXTERNAL_AXIS in f[4]
PRESERVE_RODS = {
    "잠수부의 낚싯대": "잠수부의 낚싯대|B|160000|320|난이도:2,행운:7,등급업:3,판매보너스:8,더블찬스:3|10|잠수상점",
    "심해 잠수부의 낚싯대": "심해 잠수부의 낚싯대|A|2100000|480|난이도:4,행운:17,판매보너스:15,더블찬스:8,트리플찬스:3,경험치:22.5|30|잠수상점",
    # ★초보자 낚싯대 — 조합대 R00(스폰마을 입문)이 주는 낚싯대. 사다리 격자 밖이라 여기 박아 둔다.
    #   부품 4종은 gen_part_builds.py 의 PRESERVE_PARTS 에 들어갔는데 낚싯대만 빠져 있었다
    #   (2026-08-11 발견). 그대로 두면 이 생성기가 stale 로 보고
    #   "카탈로그에 없는 기존 낚싯대(이름 유지 원칙 위반): 초보자 낚싯대" 로 **중단**된다.
    #   값은 parts.json 과 반드시 같아야 한다(로어=parts.json 관례).
    "초보자 낚싯대": "초보자 낚싯대|E|0|60|경험치:3|1|스폰마을",
}
# ★초보 낚싯대 2종은 일반 등급 상한(E=1)을 그대로 쓰지 않는다.
#   입문 장비도 3강까지 열되, 풀강 난이도 보정은 -1로만 제한한다.
#   기존 초보 낚싯대의 +1 효과는 유지해 이미 강화한 아이템의 체감을 보존한다.
ENHANCE_OVERRIDES = {
    "초보자 낚싯대": {
        "max": 3,
        "levels": {
            "1": "경험치:3",
            "2": "경험치:3",
            "3": "난이도:1",
        },
    },
    "초보 낚싯대": {
        "max": 3,
        "levels": {
            "1": "크기:1",
            "2": "크리확률:1",
            "3": "난이도:1",
        },
    },
}
# ★삭제 허용 목록 — 이 생성기가 직접 만들었다가 시리즈명 통일 과정에서 이름이 바뀐 항목들.
#   기존 22종(플레이어 데이터가 걸린 이름)은 절대 여기 넣지 말 것. 넣으면 그 연결이 끊긴다.
RETIRED = {"개발자 낚싯대", "개발자 크리확률",
           "왕실 어사 낚싯대", "근위 어부 낚싯대", "왕실 연회 낚싯대"}

# 등급별 제작 재료 (기존 R12/R24 규모 참고)
COMMON = {
    "E": [("나뭇가지", 4), ("강화실", 2)],
    "D": [("단단한자루", 4), ("정제된갈고리", 4), ("강화실", 6), ("물고기비늘", 8)],
    # ★C 이하는 압축 흑정석(=흑정석 계열 광물) 제외 — 광물은 사막마을부터 얻는다.
    "C": [("단단한자루", 6), ("정제된갈고리", 8), ("강화석탄", 12), ("진주", 8)],
    "B": [("단단한자루", 12), ("정제된갈고리", 14), ("강철심", 18), ("진주", 20), ("압축흑정석", 10)],
    "A": [("단단한자루", 18), ("강철심", 36), ("진주", 45), ("압축흑정석", 36)],
    "S": [("단단한자루", 26), ("강철심", 60), ("별빛진주", 18), ("바르칸조각", 36),
          ("바르칸핵", 2), ("압축흑정석", 48)],
}
BUILD_MAT = {
    "숙련형": ("녹슨부품", "강화철괴"),
    "행운형": ("행운의구슬", "행운의매듭"),
    "크리형": ("안개수정", "자수정"),
    "상인형": ("보석", "강화에메랄드"),
    "성장형": ("깃털찌조각", "별빛진주"),
}
BUILD_MAT_QTY = {"E": 2, "D": 5, "C": 10, "B": 16, "A": 28, "S": 34}
# 강화 최대치 — 기존 관행(E1 D8 C10 B13 A15 S18)
ENH_MAX = {"E": 1, "D": 8, "C": 10, "B": 13, "A": 15, "S": 18}

STAT_ORDER = ["난이도", "행운", "등급업", "크리확률", "크기", "판매보너스",
              "더블찬스", "트리플찬스", "경험치", "도망감소", "등급특화"]


def r(v):
    return max(1, int(round(v)))


def stats_for(build, grade, shape, hybrid_with=None, hidden=False, theme_village=None):
    pm, sm = SHAPE[shape]
    st = {}
    used = set(BUILDS[build]) | (set(BUILDS[hybrid_with]) if hybrid_with else set())

    def apply(b, scale):
        axes = BUILDS[b]
        for i, ax in enumerate(axes):
            mult = pm if i == 0 else sm          # 첫 축=주력, 둘째 축=보조
            tbl = PRIMARY[ax]
            if grade not in tbl:                 # E(시작 낚싯대)는 하한만 — 빌드 스탯 없음
                continue
            base = tbl[grade] * mult * scale
            if base < 1:
                continue
            st[ax] = st.get(ax, 0) + r(base)

    if hybrid_with:
        apply(build, HYBRID_SCALE)
        apply(hybrid_with, HYBRID_SCALE)
    else:
        apply(build, 1.0)

    # 마을 테마 — 그 빌드가 안 쓰는 축 중 첫 번째에 얹는다(겹치면 두 배 강해지므로 회피).
    for th in VILLAGE_THEME.get(theme_village, []):
        if th in used or grade not in THEME_VAL.get(th, {}):
            continue
        st[th] = st.get(th, 0) + THEME_VAL[th][grade]
        break

    # 등급 하한 — 난이도·행운은 어떤 빌드든 최소치가 깔린다
    for ax, table in FLOOR.items():
        st[ax] = max(st.get(ax, 0), table[grade])
    if hidden and grade in HIDDEN_LUCK:
        st["행운"] = max(st["행운"], HIDDEN_LUCK[grade])
    # 상한 클램프 — 마을 배수가 문서 범위를 밀어내지 못하게(난이도·행운 전용)
    for ax, table in CAP.items():
        cap = table[grade]
        if ax == "행운" and hidden and grade in CAP_HIDDEN_LUCK:
            cap = CAP_HIDDEN_LUCK[grade]
        st[ax] = min(st[ax], cap)
    # ★2026-08-26 — 2026-08-07 감사 ④ «장비 경험치 ×0.5» 는 생성기에만 들어가고 라이브엔
    #   끝내 반영되지 않았다(라이브 = 반값 전 값 그대로, C풀세팅 +154%). 유저 판단으로 강도를
    #   ×0.5 → ×2/3 로 완화하고, 나눗셈 대신 **표 자체를 손으로 떨어뜨린 정수**로 교체했다
    #   (15 이상은 5단위 — 기계식 ÷2 가 소수점 22.5 같은 값을 남겼던 문제도 같이 없앤다).
    return st


def power(st):
    return sum(POWER_W.get(k, 0) * v for k, v in st.items() if isinstance(v, (int, float)))


def stat_str(st, extra=None):
    s = ",".join(f"{k}:{st[k]}" for k in STAT_ORDER if st.get(k))
    if extra:
        s += "," + extra
    return s


def guard_drift(what, drift):
    """라이브 값과 생성 결과가 다르면 **쓰기 전에 멈춘다** (--force 로만 통과).

    이 생성기의 표(PRICE_BAND·PRIMARY·LADDER…)가 라이브 데이터와 어긋난 채로 돌면,
    누군가 라이브에서 조정해 둔 수치를 조용히 되돌린다. 2026-08-24 실측: prod 라이브가
    낚싯대·부품 87종에서 이 표와 달랐고(가격·레벨·스탯), 카탈로그 항목 14종에는
    프레임워크 밖 축 «재료확률» 이 얹혀 있었다 — 그대로 돌리면 전부 사라진다.
    의도한 재조정이면 차이 목록을 확인하고 --force 를 붙여 돌릴 것.
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
    for (name, build, grade, village, origin, shape, new) in LADDER:
        hidden = origin.startswith("히든")
        tv = origin.replace("히든-", "")      # 히든-사막마을 → 사막마을 테마 계승
        st = stats_for(build, grade, shape, hidden=hidden, theme_village=tv)
        mat = BUILD_MAT[build][0 if grade in "EDCB" else 1]
        rows.append([name, grade, st, ("히든" if hidden else origin), village, [mat], build, new, origin])
    for (name, b1, b2, grade, village, origin, new) in HYBRIDS:
        hidden = origin.startswith("히든")
        shape = "전설형" if hidden else ("왕실형" if origin == "왕도" else "기본형")
        st = stats_for(b1, grade, shape, hybrid_with=b2,
                       hidden=hidden, theme_village=origin.replace("히든-", ""))
        idx = 0 if grade in "EDCB" else 1
        mats = list(dict.fromkeys([BUILD_MAT[b1][idx], BUILD_MAT[b2][idx]]))
        rows.append([name, grade, st, ("히든" if hidden else origin), village, mats,
                     f"{b1[:-1]}·{b2[:-1]}", new, origin])

    out = []
    groups = {}
    for x in rows:
        key = (x[3], x[1]) if (x[3], x[1]) in SUB_BAND else (None, x[1])
        groups.setdefault(key, []).append(x)
    for (vil, grade), band in groups.items():
        scores = [power(x[2]) for x in band]
        lo_s, hi_s = min(scores), max(scores)
        (llo, lhi), (plo, phi) = SUB_BAND.get((vil, grade), (LEVEL_BAND.get(grade, (1, 1)),
                                                             PRICE_BAND.get(grade, (0, 0))))
        for x, sc in zip(band, scores):
            t = 0.0 if hi_s == lo_s else (sc - lo_s) / (hi_s - lo_s)
            lv = int(round(llo + t * (lhi - llo)))
            price = int(round((plo + t * (phi - plo)) / 100.0) * 100)
            name, g, st, vgroup, village, mats, build, new, origin = x
            if g == "E":                                  # 시작 낚싯대는 무료·Lv1
                lv, price = 1, 0 if name == "나뭇가지" else 50
            out.append(dict(name=name, grade=g, price=price, dur=DURAB[g], st=st, lv=lv,
                            origin=origin, village=village, mats=mats, build=build,
                            new=new, score=sc))
    gorder = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4, "S": 5}
    out.sort(key=lambda z: (gorder[z["grade"]], z["lv"]))
    return out


def check(cat):
    errs = []
    for c in cat:
        g = c["grade"]
        if g in PRICE_BAND and c["price"]:
            lo, hi = PRICE_BAND[g]
            if not (lo <= c["price"] <= hi):
                errs.append(f"{c['name']}: 가격 {c['price']} 이 {g} 대역 {lo}~{hi} 밖")
        if c["lv"] < GRADE_LEVEL[g]:
            errs.append(f"{c['name']}: 레벨 {c['lv']} < {g} 필요레벨 {GRADE_LEVEL[g]}")
        if "내구보존" in c["st"]:
            errs.append(f"{c['name']}: 내구보존은 폐지된 스탯이다(2026-08-27)")
        # ★2026-08-27 난이도 상한 재설정 — «숙련형이 난이도 라인»으로 바뀌었다.
        #   S(16) 급 존 순간이동(zoneWidth<1)을 넘으려면 rodBonus ≥ 2+sizeDiff 가 필요하고
        #   S 어종 기대 sizeDiff 가 3.23 이라 문턱이 9 다. 강화 증설분을 합쳐 도달하도록
        #   숙련형 기본을 D3/C5/B7 로 올렸다 → 구 밴드 (D1,C1~2,B2~3) 로는 전부 실패한다.
        #   하한은 0 (채집형은 난이도 0 이 설계다).
        nan = c["st"].get("난이도", 0)
        cap = {"E": 0, "D": 3, "C": 5, "B": 7, "A": 10, "S": 12}[g]
        if not (0 <= nan <= cap):
            errs.append(f"{c['name']}: 난이도 {nan} 이 {g} 상한 {cap} 밖")
        lk = c["st"].get("행운", 0)
        hid = c["origin"].startswith("히든")
        cap = {"E": 2, "D": 4, "C": 6, "B": 9, "A": 18 if hid else 14, "S": 22}[g]
        if lk > cap:
            errs.append(f"{c['name']}: 행운 {lk} > {g}{'(히든)' if hid else ''} 상한 {cap}")
    if errs:
        raise SystemExit("balance.md 대조 실패:\n  - " + "\n  - ".join(errs))
    # 완전열등 검사 — 같은 등급에서 모든 스탯이 ≤이고 더 비싸고 렙제도 높으면 살 이유가 없다
    keys = set()
    for c in cat:
        keys |= set(k for k in c["st"] if isinstance(c["st"][k], (int, float)))
    dom = []
    for a in cat:
        for b in cat:
            if a is b or a["grade"] != b["grade"]:
                continue
            if (all(a["st"].get(k, 0) <= b["st"].get(k, 0) for k in keys)
                    and a["price"] >= b["price"] and a["lv"] >= b["lv"]):
                dom.append(f"{a['name']} ⊂ {b['name']}")
    if dom:
        raise SystemExit("완전열등(살 이유 없는 낚싯대):\n  - " + "\n  - ".join(dom))


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
    enh_path = os.path.join(SRC, "enhance.json")
    mats = json.load(open(os.path.join(SRC, "materials.json"), encoding="utf-8"))["materials"]

    def ing(mid, qty):
        m = mats.get(mid)
        if m is None:
            raise SystemExit(f"materials.json에 없는 재료: {mid}")
        return {"kind": "custom", "typeOrMatId": mid, "displayName": m["name"],
                "mcItem": m["mcItem"], "qty": int(qty)}

    # ── parts.json ──
    P = json.load(open(parts_path, encoding="utf-8"))
    shutil.copy(parts_path, parts_path + ".bak-rodladder")
    parts, order = P["parts"], P["order"]
    owned = {c["name"] for c in cat} | set(KEEP_AS_IS)
    stale = [n for n in parts["낚싯대"] if n not in owned
             and not is_external(parts["낚싯대"][n])]
    # 삭제 허용 목록 — 여기 없는 이름이 stale로 잡히면 이름 유지 원칙 위반이므로 즉시 실패.
    for n in stale:
        if n not in RETIRED:
            raise SystemExit(f"카탈로그에 없는 기존 낚싯대(이름 유지 원칙 위반): {n}")
    for n in stale:
        del parts["낚싯대"][n]
    P["order"] = [e for e in P["order"] if not (e[0] == "낚싯대" and e[1] in stale)]
    if stale:
        print(f"  삭제: {stale}")
    def line_for(c):
        return "|".join([c["name"], c["grade"], str(c["price"]), str(c["dur"]),
                         stat_str(c["st"], EXTRA.get(c["name"])), str(c["lv"]), c["origin"]])
    drift = [(c["name"], parts["낚싯대"][c["name"]], line_for(c)) for c in cat
             if c["name"] in parts["낚싯대"] and parts["낚싯대"][c["name"]] != line_for(c)]
    guard_drift("낚싯대", drift)
    for c in cat:
        parts["낚싯대"][c["name"]] = line_for(c)
    for name, value in PRESERVE_RODS.items():
        parts["낚싯대"][name] = value
    have = {n for t, n in order if t == "낚싯대"}
    for c in cat:
        if c["name"] not in have:
            order.append(["낚싯대", c["name"]])
    json.dump(P, open(parts_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"parts.json: 낚싯대 {len(parts['낚싯대'])}종 (카탈로그 {len(cat)} + 개발자 {len(KEEP_AS_IS)}), "
          f"신규 {sum(1 for c in cat if c['new'])}종")

    # ── recipes.json (기존 R-id 유지, 신규는 R60+) ──
    R = json.load(open(rec_path, encoding="utf-8"))
    shutil.copy(rec_path, rec_path + ".bak-rodladder")
    recs, cats, n2i = R["recipes"], R["categories"], R.setdefault("rodNameToId", {})
    # 은퇴한 이름(개발자·개명 전)의 레시피·이름매핑 정리 — 안 지우면 조합대에 유령 레시피가 남는다.
    for dead in [n for n in n2i if n in RETIRED]:
        rid = n2i.pop(dead)
        recs.pop(rid, None)
        if rid in cats.get("낚싯대", []):
            cats["낚싯대"].remove(rid)
    nxt = 60
    for c in cat:
        if c["grade"] == "E" and c["name"] == "나뭇가지":
            continue                                        # 기본 지급품 — 레시피 없음
        rid = n2i.get(c["name"])
        if rid is None:
            while f"R{nxt}" in recs:
                nxt += 1
            rid = f"R{nxt}"
            nxt += 1
        items = [ing(m, q) for m, q in COMMON[c["grade"]]]
        qty = BUILD_MAT_QTY[c["grade"]]
        per = qty if len(c["mats"]) == 1 else max(1, round(qty * 0.6))
        for j, m in enumerate(c["mats"]):
            items.insert(min(1 + j, len(items)), ing(m, per))
        # ★해금 규약: 낚싯대 레시피는 원래 "마을 상점 NPC에서 레시피 구매 → 해금"이다(§18.2).
        #   그런데 상점 NPC가 있는 마을은 스폰(클라우스)·사막(파리드)뿐이고 /부품상점은 NPC 안내로
        #   바뀌었다 → 상점이 없는 상단·왕도 레시피를 locked로 두면 해금 경로가 아예 없어 영구
        #   미획득이 된다. 그 두 마을만 locked=false(그 마을 대장간에서 바로 제작, 작살과 동일 모델).
        locked = c["village"] not in ("상단", "왕도")
        recs[rid] = {"id": rid, "category": "낚싯대", "displayName": c["name"],
                     "locked": locked, "resultMode": "rod", "drillTier": 0,
                     "village": c["village"], "rodPartName": c["name"],
                     "ingredients": merge(items)}
        n2i[c["name"]] = rid
        if rid not in cats["낚싯대"]:
            cats["낚싯대"].append(rid)
    json.dump(R, open(rec_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"recipes.json: 낚싯대 레시피 {len(cats['낚싯대'])}개")

    # ── enhance.json (없는 낚싯대만 추가 — 기존 표는 손대지 않는다) ──
    #   기존 표를 바꾸면 이미 강화해 둔 플레이어의 누적 스탯이 소급 변경된다(getCumulativeStats).
    E = json.load(open(enh_path, encoding="utf-8"))
    shutil.copy(enh_path, enh_path + ".bak-rodladder")
    tbl, eorder = E["table"], E.setdefault("order", [])
    added = 0
    for c in cat:
        if c["name"] in tbl:
            continue
        mx = ENH_MAX[c["grade"]]
        axes = [k for k in STAT_ORDER if c["st"].get(k) and k in PRIMARY]
        main_ax = axes[0] if axes else "난이도"
        levels = {}
        for n in range(1, mx + 1):
            parts_ = [f"{main_ax}:{1 if main_ax not in ('경험치',) else 4}"]
            if n % 2 == 0 and len(axes) > 1:
                parts_.append(f"{axes[1]}:1")
            if n % 5 == 0:
                parts_.append("행운:1")
            if n == mx:
                parts_.append("난이도:1")
            levels[str(n)] = ",".join(parts_)
        tbl[c["name"]] = {"max": mx, "levels": levels}
        if c["name"] not in eorder:
            eorder.append(c["name"])
        added += 1
    # 일반 E급 상한보다 입문 낚싯대 2종의 예외 규칙을 우선 적용한다.
    for name, profile in ENHANCE_OVERRIDES.items():
        tbl[name] = profile
        if name not in eorder:
            eorder.append(name)
    json.dump(E, open(enh_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"enhance.json: 강화표 {added}종 추가 (총 {len(tbl)}종)")

    # ── NPC 상점 목록 (--shops) ──
    if WRITE_SHOPS:
        npc_path = os.path.join(SRC, "npc.json")
        N = json.load(open(npc_path, encoding="utf-8"))
        shutil.copy(npc_path, npc_path + ".bak-rodladder")
        npcs = N["npcs"] if isinstance(N, dict) and "npcs" in N else N
        items = npcs.items() if isinstance(npcs, dict) else [(x.get("id"), x) for x in npcs]
        want = {"스폰": [], "사막": [], "상단": [], "왕도": []}
        for c in cat:
            if c["origin"].startswith("히든") or c["grade"] == "S":
                continue                                    # 히든/전설은 상점 비노출(§7 천장 A)
            if c["village"] in want:
                want[c["village"]].append(c["name"])
        hit = 0
        for k, v in items:
            for vil, names in want.items():
                if v.get("shopItems") and any(n in v["shopItems"] for n in
                                              [c["name"] for c in cat if c["village"] == vil]):
                    # ★카탈로그 이름만 걷어낸다. parts["낚싯대"] 전체로 걸러내면 보존 낚싯대
                    #   (초보자·잠수부·수집 계열)가 상점에서 조용히 사라진다.
                    catalog_names = {c["name"] for c in cat}
                    keep = [x for x in v["shopItems"] if x not in catalog_names]
                    v["shopItems"] = names + keep
                    hit += 1
                    break
        json.dump(N, open(npc_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"npc.json: 상점 {hit}곳 낚싯대 목록 갱신")

    print(f"\n{'등급':<3}{'Lv':>4}{'가격':>7}  {'출처':<14}{'빌드':<10}{'이름':<18}{'점수':>6}  스탯")
    for c in cat:
        tag = "＋" if c["new"] else "  "
        print(f"{c['grade']:<3}{c['lv']:>4}{c['price']:>7}  {c['origin']:<14}{c['build']:<10}"
              f"{tag}{c['name']:<16}{c['score']:>6.0f}  {stat_str(c['st'], EXTRA.get(c['name']))}")


if __name__ == "__main__":
    main()
