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
| [`quest-difficulty-bar.patch`](quest-difficulty-bar.patch) | **퀘스트 난이도 바** — `QuestManager.difficultyLore()` 신설 + 로어 렌더 5곳 | ⏸ 미적용 |

---

## `quest-difficulty-bar.patch` 상세

퀘스트 아이템 로어에 난이도를 **`\|` 바**로 그린다. 바의 **길이**가 곧 난이도다.

```
&7난이도 &a| &81/20                                        (최저)
&7난이도 &a||||&e|||&6||&c| &810/20
&7난이도 &a||||&e|||&6||&c|||&4||&d||&5||&8|&0| &820/20    (최고극악)
```

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
