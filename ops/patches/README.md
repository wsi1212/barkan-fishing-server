# 플러그인 패치 — BlockShip 자바 소스용

이 저장소(`barkan-fishing-server`)는 **문서·데이터**만 담는다. 자바 플러그인 소스는
별도 저장소(`wsi1212/blockship-plugin`, 작업본은 Mac `~/development/blockship-plugin/`)라
여기서 직접 커밋할 수 없다. 그래서 자바 변경은 **패치 파일**로 실어 둔다.

## 적용법

```bash
cd ~/development/blockship-plugin
git apply --check ~/barkan-fishing-server/ops/patches/<이름>.patch   # 먼저 확인
git apply         ~/barkan-fishing-server/ops/patches/<이름>.patch
./gradlew build
```

충돌하면 `git apply -3`(3-way)로 시도하고, 그래도 안 되면 패치 본문을 보고 손으로 옮긴다.
적용한 패치는 파일을 지우지 말고 **아래 표에 적용 완료로 표시**한다 — 같은 패치를 두 번
적용하는 사고를 막는다.

## 목록

| 패치 | 내용 | 적용 |
|---|---|---|
| [`quest-difficulty-and-tracking.patch`](quest-difficulty-and-tracking.patch) | **① 퀘스트 난이도 바** + **② 메인 퀘스트 추적/길잡이** | ⏸ 미적용 |

★옛 `quest-difficulty-bar.patch`는 이 파일에 **흡수됐다.** 둘 다 미적용 상태였고 같은
파일(`QuestManager`·`QuestGui`)을 건드려 따로 두면 적용 순서에 따라 충돌한다. **하나만 적용할 것.**

---

## ② 메인 퀘스트 추적 · 길잡이 (2026-08-15)

**증상** — 튜토를 졸업하면 메인 흐름이 끊기고, 사이드를 하나 밀거나 오랜만에 접속하면
메인 퀘스트를 찾을 수가 없다.

**원인 넷** (전부 실측으로 확인)

| | |
|---|---|
| **A** | `complete()`가 다음 퀘스트 안내를 **안 한다.** `completeTravel()`(visit 퀘)만 화살표를 이어 준다. 튜토는 `튜토_이동1~7` 같은 visit 퀘가 촘촘해 안 끊기지만, 졸업하면 낚기·조합 위주라 전부 `complete()`로 빠진다 — **정확히 「튜토 끝나면 끊긴다」의 원인** |
| **B** | 「대기」 상태 메인은 `activeQuests`에 없다. 사이드바(`getObjectiveActiveQuestId`)도 저널(슬롯13)도 `activeQuests`만 봐서 **둘 다 못 본다.** 저널은 심지어 *"진행 중인 메인 퀘스트가 없습니다"*라고 **거짓말**을 했다 |
| **C** | 사이드바는 `activeQuests`의 **첫** non-special, 저널은 **마지막** non-special을 집었다 — 서로 다른 걸 가리켰고, 카테고리를 안 봐서 사이드가 「메인 퀘스트」 자리를 차지했다 |
| **D** | `guideToQuestGiver`가 `npcNameOfQuest`(**표시이름**)를 `liveLocationOf`(**NPC 키**)에 넘기고 있었다. 키가 `하겐`인데 `길드장 하겐`으로 찾으니 항상 null → **실시간 위치 경로가 통째로 죽어 있었다**(2026-08-06에 고쳤다던 그 버그) |

**고친 것**

| 파일 | 내용 |
|---|---|
| `QuestManager` | `getTrackedMainQuest` / `getPendingMain` / `getLastClearedMain` / `questGiverName` / `startGuideTo` / `isMainLine` 신설 — 사이드바·저널·화살표가 **한 곳에서 같은 답**을 쓴다 |
| `QuestManager.complete()` | 다음 퀘스트가 열리면 채팅 안내 + `guideToQuestGiver()` (A 해결) |
| `QuestManager.greetOnJoin()` | 접속 80틱 뒤 「진행 중 / 반납 대상 / 다음 메인」 한 줄 + `/길잡이` 안내 |
| `NpcManager.npcIdOfQuest()` | 퀘스트 → NPC **키**. `guideToQuestGiver`가 이걸 쓰도록 교체 (D 해결) |
| `SidebarManager` | line 4~3에 **메인 이정표** 한 줄 (`다음 ▸ <퀘스트> / → <NPC>에게`, 레벨 미달이면 `Lv30 필요`). 트래커와 같은 퀘면 생략, 체인 완주면 `메인 완주 ▸ <마지막>` |
| `QuestGui` 슬롯13 | `getTrackedMainQuest` 사용. **대기 메인은 나침반 아이콘 + 수여 NPC + 「클릭 — 여기로 길안내」**. 일반 클릭 = 길안내, 쉬프트 = 포기(단 **대기 상태는 포기 불가** — 체인이 끊기면 복구 경로가 없다) |
| `QuestGui` 잠금 | *"다른 퀘스트를 먼저 완료해주세요"*에 **진행 중인 퀘스트 이름과 반납 NPC**를 로어로 |
| `BlockShipPlugin` | **`/길잡이`** 신설 (별칭 `rlfwkqdl` · `rwd` · `길안내` · `fnxm`) — 추적 중인 메인으로 화살표 재점화 |

★**진행도는 이정표에 안 붙인다.** 활성 퀘스트는 통틀어 **하나뿐**이고(`QuestGui`의
`hasOtherMain` 잠금) 대기 퀘는 수락 자체가 잠겨 있다. 진행도를 띄우면 「둘을 동시에 민다」로
읽혀 오해를 산다 — 이건 표지판이지 트래커가 아니다.

★**NPC 머리 위 `!` 마커는 이미 있다**(`QuestMarkerManager`, 2026-08-02). 근처까지 가면
찾을 수 있었고, 문제는 **어느 NPC로 가야 하는지 몰랐던 것**이다. 이 패치가 그걸 채운다.

---

## ① 퀘스트 난이도 바

퀘스트 아이템 로어에 난이도를 **`\|` 바**로 그린다. 바의 **길이**가 곧 난이도다.

```
&7난이도 &a|                                        (최저 1칸)
&7난이도 &a||||&e|||&6||&c|                          (10칸)
&7난이도 &a||||&e|||&6||&c|||&4||&d||&5||&8|&0|      (최고극악 20칸)
```

★**숫자(`7/20`)는 안 붙인다**(2026-08-15). 바의 **길이**가 곧 난이도다 — 숫자를 같이
띄우면 시선이 숫자로 가서 바가 장식이 되고, 로어 한 줄만 길어진다.

**색 램프** — 길어질수록 짙어진다.

| 칸 | 색 | | 칸 | 색 |
|---|---|---|---|---|
| 1–4 | `&a` 초록 | | 13–14 | `&4` 진빨강 |
| 5–7 | `&e` 노랑 | | 15–16 | `&d` 보라 |
| 8–9 | `&6` 주황 | | 17–18 | `&5` 진보라 |
| 10–12 | `&c` 빨강 | | 19 / 20 | `&8` 회색 / `&0` 검정 |

### 왜 레거시 색코드인가

로어 직렬화기가 **평범한 `legacySection()` / `legacyAmpersand()`** 빌드다
(`.hexColors()` 안 붙임) — **hex(`§x§R§R§G§G§B§B`)를 못 읽는다.** 그래서 램프를
레거시 9색으로 손수 짰다. `&`로 내보내면 세 GUI 모두에서 안전하다:

| GUI | 직렬화 | `&` 처리 |
|---|---|---|
| `QuestGui` | `legacySection()` | `&`→`§` 정규화 후 파싱 ✅ |
| `QuestCatalogGui` | `legacySection()` | `legacy()` 헬퍼가 정규화 ✅ |
| `VillageQuestGui` | `legacyAmpersand()` | `&`를 그대로 읽음 ✅ |

★`§`로 내보내면 `VillageQuestGui`에서 깨진다. 반드시 `&`를 쓸 것.

### 렌더 지점 5곳

| 파일 | 위치 | 언제 보이나 |
|---|---|---|
| `QuestGui` | `renderNpcIcon` | **NPC에게 수락할 때** · 진행 중 아이콘 |
| `QuestGui` | 활성 메인 슬롯 | 이미 수락한 메인을 볼 때 |
| `QuestGui` | 저널 | `/퀘스트` 목록 |
| `QuestCatalogGui` | 상세 | 도감 |
| `VillageQuestGui` | 마을 게시판 | 마을 퀘스트 목록 |

`난이도` 필드가 없는 퀘스트는 `difficultyLore()`가 `null`을 주고 **줄이 통째로 빠진다** —
필드 미기입 퀘스트가 있어도 로어가 깨지지 않는다.

### 데이터 쪽

숫자는 [`fish-tools/add_quest_difficulty.py`](../../fish-tools/add_quest_difficulty.py)가
`quests.json`의 각 퀘스트에 `난이도`(1~20)로 넣는다. **패치만 적용하고 데이터를 안 넣으면
아무것도 안 보인다** — 둘 다 필요하다.
