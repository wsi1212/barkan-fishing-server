# 밸런스 감사 — 2026-08-27 요리 강화 농산물 재배분

## 요약

- `강화사과`(F10)는 요리 직접 사용처가 2개뿐이고 별도 활성 소비처가 없어 재료·조합 레시피에서 삭제했다.
- 남은 강화 농산물 9종의 **직접 사용 요리 종류 수**를 3~4개로 재배분했다.
- 총 소모 수량은 레시피 티어가 다르므로 완전 균등화하지 않았다. 특히 `대연회`의 강화 밀·강화 당근 각 96개는 최종 제작 난이도용으로 유지했다.

## 직접 사용처 델타

| 강화 농산물 | 변경 전 | 변경 후 | 총 소모량(후) |
|---|---:|---:|---:|
| 강화 밀 | 5 | 4 | 108 |
| 강화 감자 | 10 | 4 | 11 |
| 강화 당근 | 7 | 4 | 105 |
| 강화 비트루트 | 1 | 4 | 11 |
| 강화 멜론 | 2 | 3 | 10 |
| 강화 스위트베리 | 2 | 3 | 22 |
| 강화 호박 | 2 | 3 | 10 |
| 강화 사탕수수 | 0 | 3 | 8 |
| 강화 코코아 | 0 | 3 | 15 |
| 강화 사과 | 2 | 0 | 0 |

직접 사용 슬롯은 변경 전후 모두 31개다. 사과 파이는 강화 사탕수수, 왕실 케이크는 강화 코코아로 대체했고, 나머지는 비트루트·멜론·베리·호박·사탕수수·코코아에 분산했다.

## 검증

- `python3 .agents/skills/balance-audit/scripts/cooking_full_audit.py` 통과
  - 요리 58종 인식
  - 버프 24 / 제출 23 / 회복 2 / 판매 9
  - 강화 농산물 9종의 직접 사용처 범위 3~4개
- `jq empty ops/blockship-data/recipes.json` 통과
- `./gradlew build` 통과
  - 기존 Paper API deprecated 경고 35건만 발생

## 반영 범위

- BlockShip Java: `DishSpecs`, `RecipeLoader`, `MaterialLoader`, `CookingGui`, `PartFragmentManager`
- 런타임 데이터: `ops/blockship-data/materials.json`, `ops/blockship-data/recipes.json`
- 감사 기준: `.agents/skills/balance-audit/scripts/cooking_full_audit.py`

개발 파일과 데이터만 수정했으며 운영 서버에는 아직 배포하지 않았다.
