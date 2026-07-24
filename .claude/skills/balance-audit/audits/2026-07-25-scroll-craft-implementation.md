# 강화 주문서 + 이동 스크롤 대장간 조합 신설 (2026-07-25, 실제 구현)

## 배경
낚시 감사 조치권고 논의 중 발견: 강화 주문서(강화확률상승/하락확률감소/하락방지)는 **캐시상점
전용**이었다(`CashShopData.java`, "캐시"=`d.getCash()`, `/캐시지급`은 OP전용 → 게임 내 획득경로
전혀 없음 확인). 사용자 지시: "주문서를 그냥도 만들 수 있게 하자, 밸런스 맞는 적절한 재료로
대장간에서." 이후 **하급 1종씩만 남기라**는 조정 + **이동(마을)스크롤도 조합 가능하게** 추가 요청.

## A. 강화 주문서 — 하급 3종만 (2026-07-25 최종)
초안은 10종(전 티어) 만들었으나 사용자 지시로 **각 계열 최하급만** 남김. 고급(20/30%,
Lv11~20 방지권)은 캐시상점 전용 유지 — 캐시상점의 프리미엄 가치를 하급 접근성과 분리 보존하는
의도로 판단.

강화 기대비용 선형방정식(이미 이번 세션에서 확립)으로 "얼마를 아껴주는지" 먼저 계산(Lv10 단발
확률상승30%: 절감≈164,835원 ~ Lv15: 절감≈4,751,131원, 레벨 의존). 재료비를 이 절감액의 극히
일부(1~2%대)로 앵커링 — "확실히 이득이지만 공짜는 아닌" 지점. 절대값은
[cross-economy-values.md](../references/cross-economy-values.md) 골드가치로 산정.

| ID | 아이템 | 재료 | 목표/실제 원가 |
|---|---|---|---|
| SCR01 | 하락확률감소10 | 흑정석60+밀40+채집흔함10 | 3,000/2,920원 |
| SCR04 | 강화확률상승10 | 압축흑정석30+감자30+채집흔함30 | 10,000/9,645원 |
| SCR07 | 하락방지1(Lv6-10) | 압축흑정석30+채집흔함80 | 10,000/11,128원 |

★~~SCR02/03(하락확률감소20/30)·SCR05/06(강화확률상승20/30)·SCR08/09/10(하락방지2/3/4)~~는
추가했다가 **제거**(사용자 지시) — 캐시상점 전용으로 남음.

## B. 이동(마을) 스크롤 — 신규 조합 3종
사용자가 실제로 원했던 첫 요청. 강화 주문서와 달리 **PDC 태그**(`blockship:scroll`,
`ScrollManager.idOf`)로 식별돼 순수 JSON 레시피 추가만으론 작동 안 함 — Java 배선 필요했음
(아래 구현 상세). 저렴한 편의 아이템 성격에 맞춰 소액 재료로 설계.

| ID | 아이템 | 재료 | 재료비 |
|---|---|---|---|
| WARP01 | 스폰 도시 주문서 | 흑정석15+밀10 | ≈514원 |
| WARP02 | 사막마을 주문서 | 흑정석15+채집흔함5 | ≈666원 |
| WARP03 | 상단마을 주문서 | 흑정석15+밀5+채집흔함5 | ≈806원 |

## 구현 상세

### 강화 주문서 (lore 파싱, JSON만으로 충분)
`EnhanceManager`는 아이템 **lore 텍스트 파싱**으로만 식별(`hasTag`/`scrollBoostPercent`/
`downRedPercent`/`shieldTier` — PDC 아님). 조합대가 만든 `Material.PAPER`+동일 lore 포맷
(`"scroll:강화확률상승:10"` 등)이면 캐시상점 산출물과 완전히 동일하게 작동 — 강화 GUI가 둘을
구분 못 함(의도대로).

### 이동 스크롤 (PDC 필요, Java 코드 변경)
`ScrollManager.item(id,qty)`가 `PersistentDataContainer`(`blockship:scroll`=id)로 아이템을
만드는데, `CraftingManager.buildDirectResult()`는 lore/name만 부여하고 PDC를 안 붙임 — 순수
JSON으론 작동 안 하는 아이템이 만들어짐(우클릭해도 인식 안 됨). 해결:
- `CraftingManager`에 `ScrollManager` 세터 주입(`setScrollManager`) 추가.
- `buildDirectResult()` 최상단에서 `result.lore`의 `"warpscroll:<id>"` 마커를 감지하면 일반
  아이템 생성을 건너뛰고 `scrollManager.item(id,1)`로 위임(AfkShopGui 산출물과 완전 동일한
  PDC아이템 생성) — 기존 "mat:" 태그 관례와 같은 패턴의 새 마커.
- `BlockShipPlugin.java`에 `craftingManager.setScrollManager(scrollManager)` 배선 1줄 추가.
- 커밋: `3f23d06`.

### 공통
- `RecipeLoader.load()`가 `!file.exists()`일 때만 하드코딩 시드 사용 → 기존 recipes.json에 직접
  추가한 레시피는 서버 재시작해도 안 덮어써짐(안전 확인).
- `category="재료"` → 기존 `CraftingGui`의 5탭(낚싯대/부품/재료/드릴/통발) 중 "재료" 탭에 자동
  노출, 강화주문서 쪽은 신규 UI 코드 불필요.
- 재료 typeOrMatId/mcItem 전부 기존 라이브 레시피에서 실사용 확인된 값 그대로 재사용.

## 파일 변경
- `plugins/BlockShip/recipes.json` — SCR01/04/07(강화, 최종 3종) + WARP01~03(이동, 신규 3종).
  git 비추적 폴더라 백업 생성(`recipes.json.bak-20260725-scrollcraft-before/after`).
- `blockship-plugin` Java: `CraftingManager.java`(ScrollManager 세터+buildDirectResult 분기),
  `BlockShipPlugin.java`(배선 1줄). 커밋 `2025a10`(초안 SCR 10종, 이후 7종 JSON에서 직접 제거)
  → `3f23d06`(이동스크롤 Java 배선).

## 배포 필요
JSON 데이터는 재빌드 불필요, Java 변경(이동스크롤 배선)은 **빌드+배포+재시작 필요**. 둘 다 실행
중 서버가 캐시 중이므로 반영에는 재시작이 필요 — dev/prod 배포 규칙(재시작은 모아서+매번 허락)에
따라 사용자 승인 후 진행. 아직 미배포.

## 후속 검증 필요 (배포 후)
1. `/조합` GUI "재료" 탭에서 SCR01/04/07 + WARP01~03이 정상 표시되는지
2. 강화 주문서 조합결과를 강화 GUI 확률상승/하락방지/하락확률감소 칸에 넣었을 때 캐시상점
   산출물과 동일 인식되는지
3. 이동 스크롤 조합결과를 우클릭 시 실제로 워프되는지(PDC 배선 검증 핵심)
4. SCR02/03/05/06/08/09/10은 캐시상점에만 남아있는지 재확인(이미 JSON에서 제거함)
