# 섬·길드 제출형 랭킹 (Island/Guild Submission Ranking)

> 2026-06-16 설계. 기존 "설치 블럭 worth" 섬 랭킹(SuperiorSkyblock2)을 폐기하고,
> **아이템 제출형 점수 랭킹**을 BlockShip 안에 신설한다.

## 1. 배경 / 현황

- 개인섬은 SSB2 → BlockShip(`island/`, `island_world`)로 **100% 이관됨**. SSB2 islands = 0개(죽음).
- 따라서 SSB2 `/is top`(블럭 worth) 랭킹은 **빈 껍데기**. BlockShip `RankingManager`엔 섬 랭킹이 **없음**(개인/주간/길드만).
- → 블럭 worth 스캔을 고치는 게 아니라 **신규 제출형 랭킹을 BlockShip에 구축**. 완성 후 SSB2 제거 가능.

## 2. 핵심 규칙 (확정)

| 항목 | 결정 |
|------|------|
| 점수 획득 | **아이템 제출** → 소멸(sink) → `수량 × 품목점수` 가산 |
| 적립 대상 | **한 번 제출 = 내 섬 + 내 길드 동시 적립** |
| 점수 트랙 | **영구 누적(`submitTotal`) + 시즌(`submitSeason`)** 둘 다 |
| 랭킹 단위 | **섬 단위** + **길드 단위** (각각 시즌/통산 토글) |
| 시즌 | **월간** — 매월 1일 `submitSeason`만 0, `submitTotal` 보존 |
| 보상 | 시즌 상위 **3등**까지, **추천코인** (금액은 config, 지금은 소액) |
| 제출 품목 | **JSON 관리**(`submit-values.json`) — 광물블럭/뭉친 농산물(Material) + 물고기(등급별). 추후 요리 산출물 추가 |

## 3. 데이터 모델

**IslandData** (islands.json) 추가:
- `long submitTotal` — 영구 누적
- `long submitSeason` — 이번 시즌
- `Map<String,Long> submitLog` — uuid→누적 기여(전시/최고 기여자용)

**GuildData** (guilds.json) 추가:
- `long submitTotal`, `long submitSeason` + getter/setter/`addSubmit(n)`/`resetSubmitSeason()`

## 4. 제출 품목 config — `plugins/BlockShip/submit-values.json`

```json
{
  "items": {            // 바닐라 Material 이름 → 1개당 점수
    "DIAMOND_BLOCK": 500, "EMERALD_BLOCK": 450, "GOLD_BLOCK": 150,
    "IRON_BLOCK": 120, "COPPER_BLOCK": 40, "COAL_BLOCK": 30,
    "HAY_BLOCK": 25, "DRIED_KELP_BLOCK": 15, "MELON": 8, "PUMPKIN": 8
  },
  "fishByGrade": {      // 물고기는 등급(FishItem.grade)로 점수
    "E": 1, "D": 2, "C": 5, "B": 15, "A": 50, "S": 200, "M": 700, "L": 1800, "G": 5000
  },
  "rewards": {          // 시즌 1/2/3등 추천코인 (소액, 추후 수정)
    "island": [3, 2, 1],
    "guild":  [3, 2, 1]
  }
}
```
- 없으면 코드가 위 기본값으로 생성. 수정 후 **`/데이터리로드`** 로 반영(재시작 X).
- 물고기 식별: `FishItem.isFish(item)` → `FishItem.grade(item)` → `fishByGrade` 조회 (판매와 동일 로직 재사용).

## 5. 제출 흐름 (UI)

**제출소 NPC** (`NpcDef.submit` 플래그, NPC 중심 전환 방향) 우클릭 → 제출 GUI.

제출 GUI (`IslandSubmitManager.openSubmit`):
- 상단: config `items` 카탈로그 — 아이콘/이름/점수/"보유 N개". **클릭 = 인벤의 해당 Material 전부 제출**.
- 물고기 버튼(COD) — **인벤 물고기 전부 제출**(등급별 점수 합산).
- 하단 정보: 내 섬/길드의 시즌·통산 점수.
- 제출은 가상 슬롯에 아이템을 넣지 않고 **인벤에서 직접 차감**(분실 footgun 회피).

`award(p, pts)`:
- 섬 = `islandMgr.getIslandOf(uuid)`, 길드 = `guildMgr.getGuildByPlayer(uuid)`
- 둘 다 null → "섬이나 길드에 소속되어야 제출할 수 있습니다." (제출 취소)
- 있으면 각각 `submitTotal += pts`, `submitSeason += pts`; 섬 `submitLog[uuid] += pts`; save.

## 6. 랭킹 노출 — `/랭킹` 통합

- 메인 메뉴에 **슬롯 17 "섬·길드 기여 랭킹"** 추가 → `IslandSubmitManager.openRanking`.
- 랭킹 GUI: 탭 [섬]/[길드] + [시즌]/[통산] 토글, TOP 10, "내 기록" 패널.
- 섬 표기 = `ownerName 의 섬`, 길드 표기 = `displayName`.

## 7. 월간 리셋 + 보상 (`IslandSubmitManager`)

- `RankingManager.weeklyCheck` 패턴 미러: 1시간마다 `monthlyCheck()` → `YYYY-MM` 바뀌면 1회 실행.
- `submit-meta.json` 에 `lastResetYearMonth` 영속.
- 리셋: 섬 TOP3 / 길드 TOP3 (시즌 점수순) → **각 멤버에게** `rewards` 코인 지급(온라인 알림/오프라인 PlayerData) + 전체 공지 → 전 섬·길드 `submitSeason = 0`.

## 8. 변경 파일

| 파일 | 변경 |
|------|------|
| `island/IslandData.java` | +submitTotal/submitSeason/submitLog +getter/setter |
| `guild/GuildData.java` | +submitTotal/submitSeason +접근자 |
| `island/IslandSubmitConfig.java` | **신규** — submit-values.json 로드/기본생성/reload |
| `island/IslandSubmitManager.java` | **신규** — 제출 로직 + 제출GUI + 랭킹GUI + 월간리셋/보상 (Listener) |
| `npc/data/NpcDef.java` | +`boolean submit` |
| `npc/NpcInteractListener.java` | `d.submit` → openSubmit |
| `ranking/RankingManager.java` | 메인 슬롯17 + 클릭 → submitManager.openRanking (setter 주입) |
| `BlockShipPlugin.java` | 인스턴스화/이벤트등록/NPC·랭킹 주입/`/데이터리로드` 훅 |

## 9. v1 범위 / 후속

- v1: Material 키 + 물고기 등급. (광물블럭·뭉친 농산물·물고기 = 유저 예시 전부 커버)
- 후속: 요리 산출물 등 커스텀 아이템을 `items`에 식별키로 추가(요리 시스템 연동 시).
- 후속: SSB2 플러그인 제거(섬 0개라 안전).
