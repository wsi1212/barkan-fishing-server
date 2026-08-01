# 밸런스 권위 소스 지도

각 수치가 **실제로 사는 위치**. pull.py가 이 위치들을 파싱한다. 코드 구조가 바뀌면 여기와
pull.py를 함께 갱신할 것. (검증 기준일: 2026-07-24)

**두 루트**
- `JAVA/` = `/Users/user/development/blockship-plugin/src/main/java/com/blockship/`
- `JSON/` = `…/plugins/BlockShip/`  (환경변수 `BLOCKSHIP_JAVA` / `BLOCKSHIP_JSON`로 오버라이드 가능)

**일반 패턴**: 공식·확률·비용 곡선 = **Java 하드코딩 상수** / 콘텐츠 표(부품·퀘스트·강화 스탯증가·상점가·제출값) = **JSON**.

---

## A. 레벨링 / 성장 곡선  (전부 Java 하드코딩)
| 수치 | 위치 | 비고 |
|---|---|---|
| `MAX_LV=100` | `JAVA/fishing/FishingLevelManager.java` | `addExp()`, `needForLevel()` |
| **레벨별 필요경험치 테이블 `NEED_TABLE`** (2026-08-01 개편) | 同 `NEED_TABLE` 상수 | 1~24 신설(L1=500→L24=692), **25+는 구 곡선과 동일** — `needForLevel()` 단일 lookup. 기존 addExp/needForLevel 이중 연쇄 제거 |
| (구) 구간별 벽 배수 1.04/1.08/1.05/1.09/1.06/1.10 — 25+에서만 유효 | 同 `NEED_TABLE[24+]` | 1~24는 테이블로 대체됨 |
| 레벨 마일스톤 스탯 보너스 | `JAVA/fishing/RewardMath.java` `levelBonus()` L18~41 | crit/critDmg/이탈감소 계단 |
| 등급 해금 마일스톤 (30→M,45→L,60→G) | `JAVA/fishing/GradeRoller.java` `maxGradeNum()` L74~78 | |
| 등급별 base XP | `JSON/fish.json` per-fish `baseExp` | RewardMath가 소비 |
| 장비 경험치 부스트 합산 | `JAVA/fishing/FishingBonuses.java` L101~197 | 하드코딩 아님 — parts.json/enhance.json/도핑/길드/캐시버프 합산 |

## B. 경제
**수입**
| 수치 | 위치 | 비고 |
|---|---|---|
| 등급 기본가 E100…G450000, 크기점수 배율 `0.5+sizeScore*0.5/100` | `JAVA/economy/FishItem.java` `fishPrice()` L105~114 | Java 하드코딩 |
| 신선도 감소 1.0/0.85/0.65/0.40/0.20 (15/40/90/180분) | 同 `freshnessMult()` L86~101 | |
| 최종 판매 체인 (×크리×판매보너스×신선도) | 同 `calcPrice()` L116~123 | |
| 퀘스트 보상 | `JSON/quests.json` (약 159항목) → `JAVA/quest/QuestManager.java` | 하드코딩 아님 |
| 제출 보상 (섬/길드), 보상 상한 1,000,000 clamp | `JSON/submit-values.json` + `JAVA/island/IslandSubmitConfig.java` L78 | |
| AFK 포인트 60초당 1 | `JAVA/afk/AfkManager.java` `SWEEP_SEC`/`DEFAULT_IDLE_SEC` L56~106 | |

**소모**
| 수치 | 위치 | 비고 |
|---|---|---|
| 상점 가격 | `JSON/shop-items.json` (`categories`) | |
| 캐시샵 가격 | `JAVA/economy/CashShopData.java` / `CashShopGui.java` | |
| 강화 비용 | `JAVA/enhance/EnhanceManager.java` `COST[]`/`PEARL[]` (D 참조) | |
| 돈 상한 `MAX_MONEY=10^15` | `JAVA/util/Num.java` L35 | clampMoney/mulMoney/addMoney |

## C. RNG / 등급  (전부 Java 하드코딩)
| 수치 | 위치 | 비고 |
|---|---|---|
| 등급 base 확률 G0.0000035…D21.12, 게이트 | `JAVA/fishing/GradeRoller.java` `ROLL_ORDER[]` L33~42 | PRD pity math `roll()` L102~165 |
| 등급업 총확률 (상한 없음, 2026-07-24 캡40 폐지) | `JAVA/fishing/RewardMath.java` `gradeUpChance()` L62~63 | roll()이 100%에서 자연 포화 |
| 콤보 보너스 step5 (상한 없음, 2026-07-24 캡20% 폐지) | 同 `comboBonusPct()` L94~95 | |
| 더블/트리플 캡 | 同 `extraFish()` L102~111 | 더블>100%는 트리플 0.5×로 스필 |
| 슬롯 RTP 93.92% (하우스엣지 6.08%), BET_UNIT 1000 | `JAVA/casino/slot/SlotRules.java` L10~15 | `THEORETICAL_RTP_BPS=9392` |
| 포커 레이크 5% | `JAVA/casino/table/PokerTableRuntime.java` `RAKE_BPS=500` L51 | |
| 섯다 배당 캡 20× | `JAVA/casino/seotda/SeotdaTableEngine.java` `CAP_MULTIPLIER=20` L27 | |
| 미니게임 난이도 파라미터 | `JAVA/fishing/MinigameTables.java` + `MinigameManager.java` | |

## D. 장비 / 강화 / 부품
| 수치 | 위치 | 비고 |
|---|---|---|
| 부품 스탯 표 **84종** (낚싯대20·릴12·줄14·바늘14·미끼13·찌11) | `JSON/parts.json` (`parts`) → `JAVA/parts/PartLoader.java` | ★CLAUDE.md "131"은 stale |
| 강화 성공률 `SUCCESS[]`, 비용 `COST[]`, 하락 `DOWN[]`, 체크포인트 {5,10,15}, 진주 `PEARL[]` | `JAVA/enhance/EnhanceManager.java` L45~57 | +16부터 성공률 급락(5→1)의 "벽" |
| 강화 성공 계산 `base*(1+boost/100)` | 同 L543~552 | |
| 레벨별 강화 스탯 증가표 | `JSON/enhance.json` (`order`,`table`) → `JAVA/enhance/EnhanceLoader.java` | 비용곡선과 별개 |
| 부품 조각 분해수율·합성비용 | `JAVA/parts/PartFragmentManager.java` L51~95 | |
| 내구도 감소·수리 | `JAVA/parts/EquipmentManager.java` `reduceDurability()`/`repairCost()` | 낚싯대만 내구無(`SLOTS`={릴,줄,바늘,미끼,찌}). 0=고장(수리대기), 2026-07-24 이전 버그로 파괴였음 |
| 스탯 합산 시 내구도 게이트 | `JAVA/fishing/FishingBonuses.java` L100~108 | durability>0 아니면 해당 부품 스탯 미적용 |
| 재료·드롭테이블 | `JSON/materials.json` (`materials`,`dropTables`) | |

---

## 드리프트 감시 목록 (코드 ↔ balance.md 중복 전사)
balance.md는 하드코딩 값의 거의 완전한 미러 → 축마다 이중화. 감사 때 아래를 대조:

| 수치 | 코드 권위 | balance.md 위치 |
|---|---|---|
| 등급 base 확률 | `GradeRoller.ROLL_ORDER[]` | §2.1 |
| 등급 기본가·판매공식 | `FishItem.fishPrice()` | §2.1/§2.2 |
| 신선도 버킷 | `FishItem.freshnessMult()` | §2.3 |
| need 테이블 (2026-08-01, 1~24 초반너프) | `FishingLevelManager.NEED_TABLE` (단일) | §3.1 |
| 등급 해금 30/45/60 | `RewardMath.levelBonus()` | §3.3/§7 |
| 강화 SUCCESS/COST/DOWN/PEARL | `EnhanceManager` | §10.3 |
| ~~등급업 캡~~ | 2026-07-24 코드+balance.md 동시 폐지로 **해소** | 크리배율 캡(8)·콤보캡(20%)도 함께 폐지 |
| 부품 수 | parts.json=**84** | §14="84종", CLAUDE.md="131" ← stale |

**★참고**: 기존 가드 `scripts/.claude/hooks/balance-check.sh`는 `*.sk`/`balance.md` 편집만 감시하고
**Java 소스는 감시 안 함**. 이 스킬이 그 공백을 메운다 — 반드시 Java 상수+JSON을 직접 읽는다.
