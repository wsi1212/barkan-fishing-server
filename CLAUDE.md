# Fish - 바르칸 열도 낚시 서버

## 프로젝트 개요
마크 서버용 종합 낚시 게임. **Paper 1.21.11 + Java 21 툴체인(런타임 JVM 은 Java 25).** 모든 게임 로직은 BlockShip 자바 플러그인(`/Users/user/development/blockship-plugin/src/main/java/com/blockship/`)에 기능별 패키지(`fishing/` `enhance/` `parts/` `quest/` `npc/` `ferry/` `region/` `market/` `economy/` `profile/` `ranking/` `mining/` `guild/` `inn/` `portal/` `island/` 등)로 구현돼 있다.
상세 설계: [design.md](design.md) | 수치 밸런스: [balance.md](balance.md) | 스토리: [story.md](story.md)

## 🚫 절대 운영 안전 규칙 — 모든 에이전트 세션 공통 (2026-09-02)

- Codex·Claude를 포함한 **모든 에이전트는 prod 서버를 재시작하지 않는다.** `sudo systemctl restart mcserver`, `systemctl restart mcserver`, `ops/rp-deploy.sh prod --restart`, `~/deploy-blockship.sh`, `ops/deploy-all-prod.sh`, `nightly-restart.sh --now` 및 이와 동등한 재시작 경로를 실행 금지한다.
- 리소스팩 prod 배포는 `ops/rp-deploy.sh prod`를 **`--restart` 없이** 실행해 새 Release와 URL/SHA1만 반영한다. 접속자 확인·공지·승인 없는 운영 중단을 에이전트가 만들지 않는다.
- **매일 06:00 KST 정기 재시작은 켜져 있다 (2026-09-02 복구 → 09-03 17:14 커밋 `f34bd1a9` 로 차단 → 09-03 20:45 유저 지시로 재복구).** ★이 항목은 하루에 두 번 뒤집혔다 — 문서를 믿지 말고 `crontab -l | grep nightly` 와 `head -35 ~/mcserver/scripts/nightly-restart.sh`(상단 `exit 2` 가드 유무)로 실측할 것. cron `0 21 * * * nightly-restart.sh` 가 staging 적용 + 재시작을 하고, 30/10/5/1분 전 `restart-warning.sh` 가 예고한다. 이건 «예약된» 재시작이라 위 금지의 예외다 — 에이전트가 임의 시각에 때리는 것만 금지다. 오늘 밤만 건너뛰려면 `touch ~/mcserver/scripts/.skip-nightly-once` (1회 자동 소모). 재시작 없는 점검용 `nightly-maintenance.sh` 는 파일만 남아 있고 cron 에서 빠져 있다(09-03 낮 동안 이게 06:00 자리를 차지해 스테이징이 하루 종일 적용되지 않았다 — 증상은 «staging 대기 N개» 리포트만 반복).
- **이 금지는 훅으로 강제된다** — `ops/hooks/guard-prod-restart.py` (Claude `settings.json` + Codex `hooks.json` 양쪽 PreToolUse). 문서만으로 막던 2026-09-02 에 에이전트가 하루 6번 prod 를 재시작했다. 검산 `ops/hooks/guard-prod-restart-selftest.py`. 통과시키는 것: 조회·grep·히어독 본문·`crontab` 편집·`PREVIEW=1`·`systemctl start`(inactive 복구)·dev.
- **자동복구 가드는 지금 꺼져 있다 (2026-09-03 `f34bd1a9` 로 차단, 06:00 재복구 때 같이 살리지 않았다 — 성격이 달라 유저가 따로 정할 몫).** 두 스크립트 상단에 `exit 2` 가드가 박혀 있다 → 프리즈·jar 교체를 감지해도 **아무도 재시작하지 않는다.** 원래 설계는: `watchdog.sh`(cron `*/2`, RCON 4회 연속 무응답≈8분이면 프리즈로 보고 재시작) · `jar-guard.sh`(cron `*/2`, 라이브 jar mtime > 서버 시작시각이면 알림+재시작, 30분 쿨다운). 둘은 «사람이 정한 자가복구»라 위 금지의 예외다. 백업·디스크가드·하트비트·crash-watch·fetch-staging 은 애초에 꺼진 적 없고 06:00 작업과 무관한 별도 cron이다 — 06:00 리포트는 `.backup-status` 를 읽어 «보고만» 한다. 막아 둔 것(의도): APPLY_NOW 즉시적용 — 폰에서 승격해도 staging 까지만, 즉시배포는 dev 전용. `resourcepack-restart.sh`(호출자 없는 스텁)·`oneshot-guild-rename-gm.sh` 도 그대로 차단.
- Java/JSON 코드는 반드시 `~/stage-blockship.sh`로 `~/mcserver/staging/`에만 올린다. 운영 `plugins/` 승격은 하지 않는다.
- prod 상태가 `inactive`로 확인된 경우에만 복구 목적으로 `systemctl start mcserver`를 검토할 수 있다. `active`, `activating`, `deactivating` 상태에서는 start/restart를 추가로 호출하지 않는다.
- 이 항목은 아래의 기존 배포 설명보다 우선한다. 사용자가 이 안전 규칙을 명시적으로 변경하기 전까지 계속 적용한다.

## 기술 스택
- **Paper 1.21.11 + Java 21 툴체인 — BlockShip 자바 플러그인이 모든 게임 시스템** (빌드: `cd /Users/user/development/blockship-plugin && ./gradlew build`, 상세는 아래 「BlockShip Java 플러그인」 섹션)

## 핵심 시스템 요약
> 각 시스템은 `com/blockship/` 아래 자바 패키지에 구현. 표의 패키지는 대략 위치이니 정확한 클래스는 해당 패키지에서 확인.

| 시스템 | 위치 (com/blockship/) | 핵심 |
|--------|------|------|
| **낚시** | `fishing/` (FishingListener·GradeRoller·MinigameManager) | PRD 등급 결정, 미니게임, 크리티컬(캡8), 등급업(캡30%), 더블/트리플(독립) |
| **레벨** | `fishing/FishingLevelManager` | 만렙100, 구간별 벽(1.04/1.08/1.05/1.09/1.06/1.10), 로드맵 GUI |
| **장비/부품** | `parts/` (EquipmentManager·PartLoader·FragmentForgeGui) | 131종, 분해·조각 합성, 포맷:`이름\|등급\|가격\|내구\|스탯\|레벨제한\|출처` |
| **강화** | `enhance/EnhanceManager` (EnhanceLoader) | 강화=낚싯대별(`/강화`) — 축복 시스템은 2026-06-13 전면 폐지 |
| **버프(구 도핑)** | `playerdata/DopingManager`·`DopingTable` | 일시 낚시버프 1종 활성. `/도핑상점` 폐지 → **요리 먹기로 전환**(`cooking/`). apply 엔진·보너스표를 요리(DishSpecs)가 위임 재사용, `/도핑`=활성버프 확인 |
| **판매** | `economy/SellCommand`·`SellGuiListener` | 등급기본가×(0.5+크기점수×0.5/100), 판매보너스·신선도 반영 |
| **칭호** | `title/` (TitleManager·TitleLogic·FishDisplayManager) | TextDisplay(addPassenger), 채팅 포맷 |
| **퀘스트** | `quest/` (QuestManager·QuestGui·QuestCatalogGui) | 일일/주간/메인, 쉬운건 타이틀 표시 |
| **NPC/대화** | `npc/` (NpcManager·NpcDialogueManager, data/) | NPC 우클릭 대화, 퀘스트 수락/완료 |
| **아이스박스** | `economy/IceboxGui` | 물고기 보관함 (9단계, 신선도 보존) |
| **페리** | `ferry/` (FerryManager·FerryVoyage) | 지역간 정기선 (노선, 요금, 보스바). ★**항로(웨이포인트) 2개 이상이면 «배가 실제로 간다»** — `FerryVoyage` 가 선체 ItemDisplay 1 + 승객 좌석 ArmorStand N 으로 바다 항로를 항해(승객 시야 자유). 항로가 비면 옛 TP 방식 폴백. 항로 등록은 `/페리설정 <노선> 경유지추가` 를 **수면 위를 지나가며 순서대로**(좌표 상상 금지 — 육지 통과함) |
| **지역** | `region/RegionManager` (RegionData·RegionTracker·RegionCommand) | Java 데이터(regions.json) |
| **날씨** | `region/WeatherManager` (WeatherCommand·WeatherInfoCommand) | 지역별 독립 날씨, 파티클, 사운드, 시야 제한 |
| **사이드바** | `sidebar/SidebarManager` | 스코어보드 HUD (레벨, 돈, 위치, 환경, 콤보) |
| **배** | `ship/` (ShipManager·ShipFactory·ShipMover) + `model/` + `command/ShipCommandManager` + `editor/ShipEditor` | 프리셋 **1종 `돛단배`**(2026-09-05 `범선` 폐지·교체, 소유는 PlayerShipData 가 읽을 때 자동 이관). 선체=구운 ItemDisplay 1개(`ship-models.json`)+돛만 BlockDisplay, 충돌=발밑 카펫. ★블루프린트는 손편집 금지 — `imugi-boss/scan_ship_world.py <프리셋>`(월드에서 재추출) → `bake_ship.py <프리셋> <영문명>` |
| **길드 디스코드** | `guild/GuildDiscordBridge` → vip-billing → `discord-bot/` | 길드별 전용 채널·역할 자동 생성. 훅은 `GuildManager.save()` 하나. 상세·상한·배포절차는 [discord-bot/README.md](discord-bot/README.md) |

**기타 시스템 위치**: 도감 `dex/`·`collectible/` · 마켓/거래 `market/`·`trade/`(SalePostManager·TradeManager) · 길드 `guild/`(GuildManager·IslandBuilder) · 섬 `island/`(IslandManager·IslandProtectionListener) · 프로필 `profile/`(ProfileGui·SkinRenderer) · 랭킹 `ranking/RankingManager` · 통발 `trap/`(TrapManager·TrapSpecs) · 특수작물 `crop/`(CropManager·CropSpecs, 요리재료·섬한도·BlockShip네이티브 ItemDisplay) · 요리 `cooking/`(DishSpecs·CookingManager·CookingGui, 먹기버프+제출+판매 3용도, 요리사NPC 주방=대장간분리) · 짚라인 `zipline/` · 스킬 `skill/SkillManager` · 제작 `crafting/`(RecipeLoader·MaterialLoader) · 광질모자 `mining/` · 여관 `inn/` · 포탈 `portal/` · 물텔포 `water/` · 캐시샵 `economy/CashShopGui`·`CashEffectManager` · 돈·수표·송금 `economy/`(MoneyCommand·CheckCommand·TransferCommand)·`playerdata/MoneyBridge` · 스크롤 `scroll/` · 잠긴문/열쇠 `door/`(LockedDoorManager — 아래 「잠긴문/열쇠 규약」 필독) · 상자잠금 `lock/`(ChestLockManager·ChestLockListener — 아래 「상자 잠금 규약」) · **조선소 시승** `ship/ShipPreviewManager`(좌클릭 미리보기 — 전용 바다 월드 `ship_preview` 로 TP 후 그 배 무료 소환·조종, `/미리보기종료` 복귀. 월드=슈퍼플랫 «공기96+기반암1+물30» 이라 **수면 y=62**, 월드보더 1000, 깊은물 강제이동 면제. 복귀좌표=extraStrs[시승복귀] 영속) · 잠수(AFK) `afk/`(AfkManager — 방치 10분→잠수대 월드 afk_world 자동이동, `/잠수`(wkatn·ㅈㅅ) 토글, 복귀위치=extraStrs[잠수복귀], `/잠수 설정 <초>` OP) · **데이터 영속** `playerdata/`(PlayerData·PlayerDataManager, 단일 권위) · 유틸 `util/`(Num 숫자포맷·Worlds.dimKey·ItemCodec)

## 코드 컨벤션
- 명령어·UI 텍스트는 한글
- **명령어 별칭 규칙 → 전역 훅이 강제** (`~/.claude/hooks/guard-security.py`, 두벌식 변환·초성 검출 내장): 한글 플레이어 명령엔 영타 별칭(두벌식) 부여, 자주 쓰는 건 초성도(선택). **초성 별칭을 달면 그 초성의 영타(영키보드 로마자)도 함께** 부여(예 ㅅㅍ→tv·ㅅㅈ→tw·ㅅ→t, 한/영 안 바꿔도 먹히게 — 단 1~3자라 충돌 주의). **OP 전용 명령(setPermission blockship.admin)엔 영타·초성 별칭 금지** — 위반 시 훅이 경고. (구 CLAUDE.md의 매핑표·초성 예시는 훅으로 이관됨)
- **탭 자동완성 필수** (OP 전용 명령어는 제외): 인자가 있는 모든 명령어에 TabCompleter 구현
  - 인자가 **플레이어 닉네임**이면: 접속 중인 플레이어 이름 목록
  - 인자가 **숫자 (금액/수량/레벨 등)**이면: 자동완성 목록 **넣지 않음**. 대신 `<금액>`, `<수량>` 같은 도움말 텍스트만 표시
  - 인자가 **고정 선택지** (등급, 타입 등)이면: 가능한 값을 모두 나열
  - 자동완성 없이 명령어만 만드는 것은 금지

### 아이템 지급 규약 (mail/ItemDelivery — 2026-08-26 신설, 위반 시 훅이 경고)
- 플레이어에게 아이템을 주는 **모든** 경로는 `com.blockship.mail.ItemDelivery.give(p, "출처", item)` 하나만 쓴다.
  `p.getInventory().addItem(...)` 을 직접 부르고 잔량을 `dropItemNaturally` 하거나 반환값을 버리는 것은 금지.
- 인벤 우선 → 초과분은 **우편함(7일 보관, `/우편함`)**. 저장은 플레이어별 코얼레싱(다음 틱 1회)이라
  채굴처럼 초당 여러 번 불려도 디스크 쓰기가 폭주하지 않는다. 실패해도 dirty 로 남아 주기·퇴장 저장이 재시도.
- 자기 안내 문구가 이미 있는 곳(작살·수표)은 `giveReporting` — 공용 안내 없이 boolean 만 반환.
- 우편 300통을 넘으면 `stashOverflow` 가 잔량을 돌려주고 그때만 바닥 폴백(복제 없음).
- ★**왜**: 바닥 아이템은 5분이면 디스폰 — 인벤이 꽉 찬 줄 모르고 계속 플레이하면 보상이 조용히 증발했다.
- 예외(그대로 둠): 바닐라 작물 보너스 수확(`SkillManager`)·주인 오프라인 작물 회수(`CropManager`)·
  우편 저장 실패 시 바닥 반환(`TradeManager`). **바닐라 블록/몹 드롭은 건드리지 않는다**(2026-08-26 유저 결정).

### NPC 닉네임 색 규칙 (2026-07-08 신설, 위반 금지)
NPC 머리 위 표시 이름의 **색코드**는 역할별로 통일한다. ★표시 이름 = **Citizens `saves.yml`의 `name` 필드**(BetterModel/BlockShip 아님) → 색 바꾸려면 saves.yml 편집(stop→편집→start). BlockShip 클릭 매칭은 **uncolored 이름 비교**라 색만 바꾸면 매칭 안 깨짐(이름 텍스트를 바꾸면 npc.json name도 같이 바꿔야 함).
- **하늘색 `&b`** = 기능형 NPC (길드·상점·물고기판매·섬상점·대장간·요리사·유저마켓·드릴상점·페리·**일퀘/주간 게시판([퀘스트] 태그)**·여관·회복·말대여 등 GUI/기능 제공).
- **초록색 `&a`** = 퀘스트(스토리·메인·튜토) 주는 NPC (태그 `[Q]` 또는 `[길잡이]`, 예: 할아버지·펠릭스·마르타·베티나·낚시꾼할아버지·동굴탐험가).
- **하얀색 `&f`** = 대화만 하는 NPC (기능도 퀘스트도 없음).
- ★함정: `[퀘스트]` 태그(디트리히·엔초)는 **일퀘 게시판=기능형(하늘)**, 퀘스트를 대화로 주는 건 `[Q]`(초록). 헷갈리지 말 것.

### 월드 이동 규칙
- **`player.teleport()` (Java Bukkit API)로 cross-world(다른 월드로) 이동 불가** — Paper에서 작동 안 함. 같은 월드 내 이동은 가능.
- 반드시 `execute in <dimension> run tp <플레이어> <x> <y> <z>` 명령어 사용
- **⚠️ `<dimension>`은 월드(level) 이름이 아니라 dimension key다!** 메인 월드를 `minecraft:world`로 쓰면 `Unknown dimension 'minecraft:world'`로 텔레포트가 **조용히 무시됨**(에러는 콘솔에만, 플레이어에겐 안 보임). 2026-06-06 섬상점/페리/포탈/여관 등 워프 전반에서 이 버그 발견·수정.
  - 바닐라: `world`→`minecraft:overworld`, `world_nether`→`minecraft:the_nether`, `world_the_end`→`minecraft:the_end`
  - 커스텀 월드(guild_world 등): `minecraft:<월드이름>` 그대로
- **`com.blockship.util.Worlds.dimKey(worldName)` 헬퍼로 변환** — 월드이름→정확한 dimension key:
  `Bukkit.dispatchCommand(consoleSender, "execute in " + Worlds.dimKey(world) + " run tp player x y z")`

### 잠긴문/열쇠 규약 (door/LockedDoorManager — 2026-07-04 신설, 위반 금지)
- **열쇠는 실물 아이템이 아니다** — `PlayerData.extraFlags["열쇠"]` 리스트의 keyId 문자열이 유일한 저장소. 아이템/PDC 기반 열쇠를 새로 만들지 말 것 (분실·거래·복제 사고 방지가 설계 의도).
- **문은 절대 물리적으로 열지 않는다** — 클릭 이벤트 취소 + 열쇠 보유자만 개별 TP. 문을 실제로 열면 다른 유저가 따라 들어가므로 금지.
- 지급 경로는 두 가지뿐: 퀘스트 보상 필드 `"보상열쇠": "키id:표시이름"` (QuestManager.rewardKey) / OP `/잠긴문 키부여 <플레이어> <키id>`.
- **`마스터키`는 예약 keyId** — 모든 잠긴문 통과, OP 수동 지급 전용. 퀘스트 보상으로는 지급 불가(rewardKey가 차단·경고 로그). 일반 열쇠 keyId로 "마스터키" 사용 금지.
- 문 설정: OP `/잠긴문 pos1/pos2 → 생성 <문id> <키id> <키표시이름...> → 도착점 <문id>`. 영속 `locked-doors.json`. 왕복은 안쪽에 같은 키의 문을 하나 더.
- keyId는 한글 무공백(예: `여관지하실`), 표시이름은 자유(예: `여관 지하실 열쇠`).

### 상자 잠금 규약 (lock/ChestLockManager — 2026-08-07 신설)
- **잠긴문(door/)과 별개 시스템** — 이쪽은 유저가 스스로 거는 컨테이너 자물쇠(LWC/Lockette 계열), 저쪽은 OP가 배치하는 퀘스트 열쇠 문. 서로 참조하지 않는다.
- **대상 월드는 `island_world` / `guild_world`뿐** (`ChestLockManager.LOCK_WORLDS`). 일반 월드는 MapProtectionListener가 이미 막으므로 중복 보호 금지.
- **권위 데이터는 `chest-locks.json`** — 표지판은 UI일 뿐이다. 소유자 UUID를 별도로 들고 있어서 표지판 글자를 고쳐 남의 잠금을 뺏을 수 없다. 대신 **지연 검증**: 표지판이 사라지거나 `[lock]` 태그가 지워지면 다음 접근 때 잠금도 자동 소멸(`signStillValid`).
- 잠그는 법(2026-09-05 변경): **표지판을 들고 상자·통·화로·마법부여대 등을 그냥 우클릭** → 옆면에 `[lock]` + 본인 이름 표지판이 자동으로 붙는다(`ChestLockListener.quickLock`). **웅크린 채 우클릭하면 바닐라 그대로 장식 표지판**이 붙는다 — 자동잠금 없음.
  - ★**빈 표지판 자동잠금은 폐지됐다** — 손으로 붙인 표지판은 첫 줄에 `[lock]`(·`잠금`·`private`·`비공개`)을 **직접 적었을 때만** 잠긴다. 되살리면 장식 표지판이 다시 전부 잠금이 된다.
  - quickLock 은 옆면을 실제로 설치하고 **`BlockPlaceEvent` 를 흘려 보낸다** — 섬 권한 판정을 복제하지 않으려는 것(거부되면 되돌림). 걸린 표지판(hanging)은 대상 아님.
  - 잠긴 컨테이너는 표지판을 들고 우클릭해도 잠기지 않는다(기존 잠금 판정으로 빠짐) → 주인은 그냥 열린다.
- 명단은 표지판 2~4줄 — `wsi1212, calan123`처럼 콤마/공백 구분. 소유자는 항상 명단 맨 앞에 강제 유지. 3줄을 넘치면 `외 N명`으로 접히고 그 상태로 표지판을 재편집하면 접힌 이름은 사라진다(권위는 JSON이지만 재편집은 WYSIWYG) — 인원이 많으면 `/상자잠금 추가·제거`를 쓸 것.
- 이름은 저장 시 UUID로도 해석해 둔다(온라인→캐시된 오프라인 순, **네트워크 조회 금지**). 그래서 닉 변경에도 유지되고 닉 재사용으로는 못 들어온다.
- 막는 경로: 우클릭 사용 / 파괴 / 표지판 파괴 / 잠긴 상자 옆 상자 붙이기(더블상자 강탈) / 호퍼 반출(같은 주인 잠금끼리만 허용) / 폭발 / 피스톤. **호퍼로 넣는 건 자유**(자동 분류기가 깨지므로).
- OP는 전부 통과. 섬장·길드장은 **`/상자잠금 해제`로 남의 잠금을 풀 수만** 있다(주인이 떠난 죽은 잠금 정리용, 열지는 못함).

### 메시지 전송 필터 패턴
- 전체 broadcast 전송 시 차단 플래그 체크 필수: 전체채팅 / 길드채팅 / 길드홍보 / 서버팁 / S등급+ 낚시공지
- guild_world에 있는 플레이어에게는 날씨 알림 보내지 않음

### guild_world 규칙
- guild_world는 길드 전용 공허 월드
- 날씨 시스템 적용 안 됨 (항상 맑음)
- 날씨 알림 메시지 보내지 않음 (Java WeatherManager에서 `guild_world` 체크)
- 사이드바에 "☀ 맑음" 고정 표시
- 길드 미가입자가 guild_world에 있으면 자동 스폰 이동

## 스탯 용어 표준
모든 UI(상점/장비/스탯/도핑/강화)에서 동일 용어 사용. 상세: balance.md 6장 참조.

## 주요 명령어
- `/레벨` `/장비` `/강화` `/칭호` `/부품상점` `/판매` `/작물`
- `/도감` `/마켓` `/마켓등록 <가격>` `/수표 <금액>` `/잠수` (잠수대 토글 — 10분 방치 시 자동) `/미리보기종료` (조선소 시승 종료)
- `/상자잠금` (섬/길드섬 컨테이너 자물쇠 — 잠그는 건 표지판, 이 명령은 정보·명단수정·해제)
- `/콤보` (조회=일반, `/콤보 <n>` 설정만 op) · `/낚시테스트 [등급]` `/카메라툴` (op)
- `/ship create/destroy/save/spawn/edit` (배)
- `/지역 생성/삭제/목록/정보/설정/바이옴/파티클/리로드` (Java, op)
- `/날씨설정 <지역|전역> <날씨|해제>` (Java, op) — **날씨 목록을 여기 적지 않는다**(드리프트). `/날씨설정` 을 인자 없이 치면 WeatherManager 가 정의한 전체 목록 + 각각의 전역/지역·시간 조건을 출력한다. 지역전용 날씨는 지역 `allowedWeathers` 화이트리스트에 이름이 있어야 자동 발동한다 — 비어 있으면 OP 수동 발동만 되고 자동으로는 영원히 안 뜬다(2026-08-27 태풍·눈보라가 그 상태였다).
- **중요**: 서버 최초 설정 시 `/gamerule advance_weather false` 필수 (MC 자체 날씨 비활성화, 우리 WeatherManager가 제어)
- **`send_command_feedback=false` 는 의도된 설정이다 (2026-09-06, prod·dev 양쪽).** 우리 워프(페리·포탈·섬·여관·잠수·지역이동)가 전부 콘솔 `execute in <dim> run tp` 라 바닐라가 «…을(를) …(으)로 순간이동시켰습니다» 를 접속 중인 **모든 OP** 에게 뿌렸다(`CommandSourceStack#broadcastToAdmins` — 유일한 게이트가 이 게임룰). 부작용으로 OP 가 직접 친 바닐라 명령의 **성공** 메시지도 안 뜬다(실패 메시지는 그대로) — 유저가 그래도 좋다고 결정했다. 디스패치 순간에만 껐다 되돌리는 코드(util/Tp)는 «부하만 는다» 는 이유로 폐기됐으니 되살리지 말 것. `true` 로 되돌리면 도배가 그대로 재발한다.
- **⚠️ 1.21.11 게임룰 개명 — 옛 camelCase 이름은 전부 없는 이름이다.** 콘솔/RCON 에서 `gamerule doWeatherCycle` 같은 걸 치면 `Incorrect argument for command` 만 나오고 **에러 원인이 안 보인다**(룰이 없다는 말을 안 해 준다). 이름은 level.dat `game_rules` 가 권위 — snake_case 인데다 **뜻까지 바뀐 게 있다**:
  - `doDaylightCycle` → **`advance_time`** · `doWeatherCycle` → **`advance_weather`**
  - `doMobGriefing` → `mob_griefing` · `keepInventory` → `keep_inventory` · `commandBlockOutput` → `command_block_output` 등 나머지는 단순 snake_case
  - 목록 확인: `python3 -c "import gzip,re;print(sorted(set(x.decode() for x in re.findall(rb'[a-z_]{4,30}', gzip.open('world/level.dat','rb').read()))))"`
  - Bukkit API 쪽 `GameRule.DO_DAYLIGHT_CYCLE` 상수는 그대로 동작한다(deprecated 경고만) — 깨지는 건 명령어 문자열뿐.
- **시간 흐름**: prod 메인월드는 2026-08-18 부터 `advance_time=true` (그 전까지는 `false` 로 daytime 1000 에 얼어 있었다 — 밤/새벽 전용 어종과 심야 날씨(오로라·유성우·열대야)가 전부 발동 불가였던 원인). 시간대 구간표는 **`com.blockship.util.DayPeriod` 단일 권위**(새벽 22000~999 / 낮 1000~10999 / 저녁 11000~14999 / 밤 15000~21999) — 복제 금지.

## 밸런스 핵심 수치
- **등급업 캡 30%**, 크리배율 캡 80%, 슈퍼크리 2%
- **장비 경험치 보너스**: S풀세팅 +330% (장비가 성장 속도 좌우)
- **Lv.60**: G등급+S장비 해금 | **Lv.70**: 엔드게임 진입 (~46시간)
- **Lv.100**: 하드코어 (~517시간)
- 상세: balance.md 참조

## BlockShip Java 플러그인 (배 + 칭호)
- 소스: `/Users/user/development/blockship-plugin/`
- 빌드: `cd /Users/user/development/blockship-plugin && ./gradlew build`
- 배포: `cp build/libs/BlockShip-1.0.0-SNAPSHOT.jar /Users/user/Library/Application\ Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/`
- **⚠️ 배포 후 서버 풀 재시작 필수** — `/plugman reload`나 실행 중 jar 덮어쓰기는 lazy-load CNFE로 부분 고장 유발(금지). jar 변경은 모아서 한 번에 재시작.
  - **★jar만 올리고 재시작을 미루는 것도 금지** — 중간 상태 자체가 고장이다. 2026-08-03 prod 사고: jar 교체 후 재시작 없이 방치 → `NoClassDefFoundError: WeatherManager$WeatherChoice`로 `/칭호`·계단앉기 등 전방위 고장(3시간 뒤 인지).
  - 3중 방어가 걸려 있다: ① 에이전트 훅 `ops/hooks/guard-live-jar.py` (Claude Code+Codex 양쪽, plugins/ **루트**에 jar 쓰기 차단 — `plugins/<플러그인폴더>/` 데이터는 허용) ② `deploy-blockship.sh`가 JSON 검증 통과 **후**에만 jar 업로드 + dev도 자동 재시작 ③ prod `~/mcserver/scripts/jar-guard.sh` (cron 2분, jar mtime > 서버 시작시각이면 Discord 알림 + 자동 재시작, 30분 쿨다운).
  - 우회하지 말고 `~/deploy-blockship.sh`(즉시) / `~/stage-blockship.sh`(지연, staging/)를 쓸 것. **넷 다 `ops/` 의 실체를 가리키는 심볼릭링크**이고, 어긋나면 `ops/audit-copies.py` 가 배포를 멈춘다. **클라우드 세션(폰·웹)은 이 둘을 못 쓴다**(22번 포트 차단) → Actions 승격 경로, 아래 「자동 sync」 참조.
- 빌드+배포 한줄: `cd /Users/user/development/blockship-plugin && ./gradlew build && cp build/libs/BlockShip-1.0.0-SNAPSHOT.jar "/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/"`
- 이후 **서버 풀 재시작** (dev=`~/dev-mc.sh restart` — RCON 25575, **feather 미사용** / prod=`sudo systemctl restart mcserver`)

### /textride 서브커맨드 (기존 명령어에 통합, 새 명령어 등록 불필요)
- `/textride <player> <tag>` — Paper addPassenger (기존)
- `/textride update <player> <titleTag> <nameTag> <titleText>` — 칭호 업데이트 (HEX 지원)
- `/textride combo <player> <titleTag> <nameTag> <combo>` — 콤보 파스텔 그라데이션
- `/textride remove <player> <titleTag> <nameTag>` — 칭호 제거

## 운영 서버 (Oracle Cloud)

### 서버 정보
- **Provider**: Oracle Cloud Infrastructure (Always Free)
- **계정**: 가족 명의 (rhfipkk tenancy, ap-chuncheon-1)
- **리전**: South Korea North (Chuncheon) — 한국 핑 5~10ms
- **인스턴스**: `minecraft-server` — OCID `ocid1.instance.oc1.ap-chuncheon-1.an4w4ljripxk3pacvlzpjj2sojj6c57romwttueidpff7jcyyvp7v6bwbvmq` (★인스턴스 재생성 시 OCID 바뀜 → 워치독 동적그룹 `mc-instance-dg` 매칭룰도 갱신 필요)
- **현재 사양**: VM.Standard.A1.Flex 4 OCPU / 24 GB RAM (목표 달성, Java 힙 16G — 2026-07-07 12G→16G, Aikar ≥12G 대용량 힙 플래그. start.sh). 디스크 48GB(2026-08-13 여유 23GB).
- **🚨 이 인스턴스는 재발급되지 않는다 (2026-08-13 확인)**
  - 오라클 공식 문서: A1은 **South Korea North (Chuncheon) 제외** 모든 AD에서 생성 가능 → **춘천에 A1을 새로 만들 수 없다.** 무료 가입 드롭다운에 한국이 없는 이유이고, 새 계정을 만들어도 해결되지 않는다.
  - Always Free A1 한도가 **4 OCPU/24GB → 2 OCPU/12GB**(1,500 OCPU-h / 9,000 GB-h)로 축소됨. 현재 인스턴스는 **한도의 2배**이고, 한도 초과 shape는 재생성이 막힌다. (시행 시점은 1차 출처 확인 실패 — 날짜를 사실로 취급하지 말 것.)
  - **⇒ `terminate` 절대 금지.** `stop`(정지)은 되돌릴 수 있지만 종료는 영구다. 이전·정리 작업 중 실수로 날리면 춘천 4/24를 영구히 잃는다.
  - 강제 리사이즈 대비: 힙을 **7G**로 내리고 Aikar 플래그 5개를 소용량 변형으로 되돌려야 한다 → **[ops/oracle/HEAP-DOWNSIZE.md](ops/oracle/HEAP-DOWNSIZE.md)** (실측 수치 포함). 이전 검토와 대안은 [ops/oracle/MIGRATION.md](ops/oracle/MIGRATION.md) (전제 붕괴 표시됨).
- **OS**: Ubuntu 24.04 ARM64
- **MC/Paper 버전**: prod·dev 구동 = **Paper 1.21.11** (prod version_history.json / dev `~/dev-mc.sh` 의 paper-1.21.11-132.jar). BlockShip 빌드 타겟도 **1.21.11** 로 맞췄다(2026-08-14, build.gradle.kts paperDevBundle·paper-api 1.21.11, api-version '1.21') — **드리프트 없음**.
  - ★드리프트를 방치하면 "컴파일은 되는데 런타임에 없는 상수"가 그대로 나간다. 1.21.4 로 빌드하던 동안 **`Material.CHAIN`** 참조 4곳이 지뢰로 남아 있었다(1.21.9 에서 구리 사슬이 들어오며 chain → **iron_chain** 개명. 1.21.11 API 에 CHAIN 없음). 짚라인 케이블·배 블록 판정·스킬 노드 아이콘이 실행되는 순간 NoSuchFieldError 가 되는 상태였다. **MC 를 올리면 빌드 타깃도 같이 올릴 것.**
  - 상향에 딸려 오는 것: paperweight **2.0.0-beta.21**(1.21.11 번들은 data version 7 이라 beta.16 이하 거부) + **Gradle 9.0**(beta.17+ 요구) + `test { failOnNoDiscoveredTests = false }`(Gradle 9 는 테스트 소스만 있고 발견 0이면 빌드를 깬다 — src/test 의 *SelfTest 는 JUnit 이 아니라 main() 검산 스크립트다).
  - ★이제 이 jar 은 1.21.9 미만에서 안 돈다(IRON_CHAIN 부재).
- **ProtocolLib 5.4.0**: 지원 명시 범위는 1.21.4–1.21.8 → prod(1.21.11)에서 부팅 시 "not yet been tested" 경고 뜸(로드·리스너 등록은 정상). dev(Mac) 버전은 별도 확인 필요 — 패킷 작업 전 양쪽 버전 대조할 것.
- **plugin.yml 의존성 실측**: `api-version: '1.21'` · **`softdepend: [ BetterHud, BetterModel, ProtocolLib, Citizens, VotifierPlus ]`** — ★**hard `depend`가 하나도 없다.** 그래서 그 플러그인들이 없어도 BlockShip은 로드·enable 된다. 대신 softdepend를 가드 없이 참조하는 코드(예: `diagnostics/PacketBlackbox`의 ProtocolLib)는 그 플러그인이 로드 실패하면 CNFE로 죽는다 — **새 softdepend 사용 시 `getPluginManager().getPlugin(...) != null` 확인 필수.**
- **ViaVersion/ViaBackwards 5.11.0**(정식, 2026-07-27 교체 — 이전 5.11.1-SNAPSHOT 개발버전이 최신 클라(26.2) 미지원해 접속끊김 유발했음, 상세는 「클라이언트 크래시 자동감지」 참조). Hangar 다운로드: `https://hangar.papermc.io/api/v1/projects/<ViaVersion|ViaBackwards>/versions/<버전>/PAPER/download`.
- **공인 IP**: `168.107.8.107` (Reserved 예약 IP — 인스턴스 재생성에도 불변. 2026-07-24 임시 IP 134.185.113.25에서 교체. 예약IP OCID: `ocid1.publicip.oc1.ap-chuncheon-1.amaaaaaaipxk3paarwjmvgd5ii3js5qes7jmsbyh5sy2holja6x4vhdust7a`)
- **도메인**: `barkan.kro.kr` (내도메인.한국 무료 서브도메인, A레코드 → 168.107.8.107 — **2026-08-14 dig 실측 해석됨**). ★무료 도메인이라 **갱신 주기 확인 필요** — 놓치면 서버는 멀쩡한데 이름만 안 풀린다.
- **SSH 키**: `~/.ssh/oracle-mc.key` (Mac 로컬)
- **SSH 접속**: `ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107`
- **OCI CLI 설정**: `~/.oci-family/config` (가족 계정용, OCI_CLI_CONFIG_FILE 환경변수로 지정)
- **서버 경로**: `~/mcserver/` (인스턴스 안)
- **Java**: Azul Zulu JDK **25** ARM (`/usr/lib/jvm/zulu25-ca-arm64`, start.sh 가 이 경로를 쓴다). 플러그인 바이트코드는 Java 21 툴체인 산출이라 그대로 돈다.
- **방화벽 (2계층 — 외부 접근은 둘 다 통과해야 함)**: OCI Security List(외부 관문) + iptables(박스 내부)
  - **외부 열림 포트**: `22`(SSH) · `25565`(마크) · `80`·`443`·`3000`(다른 서비스용, 예: LH cron) · icmp — OCI SL·iptables 양쪽에 존재
  - **RCON `25575`**: enabled지만 **localhost 전용** — OCI SL에 없고 iptables 기본 REJECT라 외부에서 이중 차단

### Dev / Prod 분리 (옵션 C - 하이브리드)
- **Mac** = dev: 본인이 개발/테스트하는 곳 (★**feather 미사용** — `~/dev-mc.sh start/stop/restart/cmd <명령>/log [N]`로 관리, RCON 25575 pw devtest2026. 서버파일은 옛 feather 폴더 경로에 있지만 실행/재시작은 dev-mc.sh)
- **Oracle (춘천)** = prod: 베타 유저 접속하는 운영 서버
- **prod 가 데이터 권위, dev 는 그 미러** (2026-08-27 유저 결정). 출시 후에도 사람들은 prod 에서 놀고 dev 는 극히 일부 상황에서만 쓴다 → **prod→dev 전체 클론이 정상 작업**이다(`~/mc-sync/mc-sync.sh`). 반대 방향(dev→prod)은 진짜 유저 진행도를 지우므로 여전히 금지에 가깝다 — 코드·콘텐츠를 prod 로 보내는 건 `~/deploy-blockship.sh` 이지 데이터 클론이 아니다.
  - ★작업 원본은 **dev 라이브 폴더가 아니라 git 레포 `ops/blockship-data/`** 다. dev 의 `plugins/BlockShip/` 은 굴려보는 런타임 사본이라 덮여도 레포에서 다시 나온다. 이 구조라서 prod→dev 미러가 안전하다 — 구조가 바뀌면 이 전제부터 다시 볼 것.
- 코드(jar, 설정)만 dev → prod 동기화
- **dev 코드 배포 한 줄**: `~/deploy-dev.sh` (BlockShip 빌드 → dev plugins/ 복사 → dev-mc.sh restart 자동)
- **⚠️ dev 기동 느림(~83s, 타임아웃 90s 아슬아슬)**: 타임아웃 떠도 실패 아님(그냥 느림), 몇 초 더 기다리면 뜸. 곧바로 재시작하면 뜨는 중인 인스턴스가 `world/session.lock`을 잡은 채라 새 인스턴스가 죽고 **좀비 java 누적**(락만 잡고 25565 미리슨) — 감지: `ps aux|grep paper-1.21.11.jar` 2개 이상. 해결: `pkill -9 -f paper-1.21.11.jar` → 락 해제 확인 → `dev-mc.sh start` 1회.
- **prod↔dev 데이터 동기화(수동 실행)**: `~/mc-sync/mc-sync.sh`. launchd 자동 sync 는 2026-07-05 해제(dev 플러그인 편집이 매일 덮여 유실된 사고) — **수동 실행만**. 방향은 `config.env` 의 `DIRECTION`(기본 `prod_to_dev`), dev→prod 는 `CONFIRM_OVERWRITE_PROD=yes` 인터록이 걸려 있다. 목적지를 정지시키고 목적지 게임데이터를 백업(`~/mc-sync/backups/gamedata-dev-<TS>/`)한 뒤 미러한다. 월드는 **소스에서 자동 발견**되므로 목적지 고유 월드(dev 의 `SuperiorWorld` 등)는 안 지워진다.
  - ★`DATA_PATHS` 는 **비어 있지 않다**(2026-08-27 실측 — 옛 문서는 「비어있어 플러그인 데이터 sync 안 됨」이라 적혀 있었으나 값이 되채워져 있었고 주석만 옛 상태였다). 현재 `plugins/BlockShip` · Citizens `saves.yml`/`shops.yml`/`skins` · `Multiverse-Core/worlds.yml` 이 **전부 덮인다**. 「안 덮인다」고 믿고 dev 에서 작업하면 그대로 잃는다.
  - ★**`--dry-run` 은 이 맥에서 무용지물이다.** macOS 는 rsync 가 아니라 **openrsync**(protocol 29, "2.6.9 compatible") 라 `--dry-run --stats` 가 항상 `Number of files transferred: 0` 을 낸다. 미리보기는 `rsync -an --itemize-changes` 로 직접 볼 것.
  - 2026-08-27 스크립트 결함 2개 수정: ① `${DRY_RUN:+[dry] }` 가 `DRY_RUN=0` 에서도 확장돼 **진짜 실행이 로그에 `[dry]` 로 찍혔다** ② `rsync | grep … || true` 가 rsync 종료코드를 삼켜 **깨진 전송도 exit 0** 이었다(실제로 `world` 가 14 region 부족한 채 「성공」으로 끝났다). 이제 실패를 모아 비영점 종료한다.

### 자동 sync (옵션 C)
**BlockShip Java plugin** — 빌드 후 배포 스크립트
- **배포 전 점검은 `ops/preflight.sh`** — 게이트 10종을 **배포·재시작 없이** 돈다(prod 는 읽기만). `--local` 은 prod 접속도 없이 로컬만. 게이트를 확인하려고 prod 를 재시작하지 말 것.
- **게이트 10종을 순서대로 돈다** — 인스턴스데이터 제외목록 · 목표id대조 · **사본드리프트(`audit-copies.py`)** · 퀘스트감사(ERROR 0 기준) · 굵은포맷 · 타임존 · NPC대사 · **빌드출처(`guard-build-source.sh`)** · staged JSON 검증 · **배포후 커밋 대조**. 통과 못 하면 배포가 멈춘다. `SKIP_QUEST_AUDIT` 우회구는 폐지됐다.
  - ★**미커밋이 있으면 게이트가 HEAD 워크트리를 자동으로 떠서 빌드한다** — 손으로 `git worktree add` 할 필요 없다. 제외된 파일은 화면에 찍힌다. 나가야 하는 파일이면 커밋하고 다시 돌릴 것.
  - ★**HEAD 가 upstream 보다 뒤처지면 거부한다** — 남이 푸시한 커밋이 prod 에서 되돌아가기 때문. `git pull` 후 다시.
  - ★**prod 가 어느 커밋을 돌고 있나는 로그로 확인한다**: `grep '\[Build\]' ~/mcserver/logs/latest.log` → `[Build] commit=<sha12> clean`. jar mtime·sha1 로는 판별 불가(낡은 체크아웃 빌드는 mtime 이 최신이다). `dirty` 가 보이면 미커밋이 실린 jar 이다.
- 위치: `ops/deploy-blockship.sh` (`~/deploy-blockship.sh` 는 여기로 가는 심볼릭링크 — **홈 사본을 따로 만들지 말 것**, 2026-08-31 에 두 벌이 240줄 갈라진 채 서로 다른 게이트를 돌고 있었다)
- 한 줄 실행: `~/deploy-blockship.sh`
- 동작: 로컬 빌드 → SCP로 오라클 plugins/ 업로드 → SSH로 **`systemctl restart mcserver` (전체 재시작)**. ★plugman reload 아님(위 라인 100 규칙대로 금지 — 클래스로더 손상). 접속자 없을 때 실행 권장. = **즉시 배포**.
- **지연 배포(스테이징)**: `~/stage-blockship.sh` — 빌드 후 오라클 `~/mcserver/staging/`에 jar만 올리고 재시작 안 함 → **매일 06:00 KST 데일리 유지보수 때 자동 적용**(Mac 꺼져있어도 미리 올려두면 됨). 설정 JSON은 `staging/BlockShip/`에 두면 같이 반영. 무인기간 배포에 적합. 적용 시 구 jar는 `backups/deployed-jars/`에 자동 백업(롤백용). ★자동배포=미검증 jar도 그대로 적용되니 dev 테스트 후 스테이징할 것.
- **클라우드 세션(폰·웹 Claude Code)에서 배포** — 위 두 스크립트는 **맥 전용**이다(SSH 키가 맥에만 있고, 클라우드 컨테이너는 **22번 포트 egress가 원천 차단**이라 키를 넣어도 SSH가 안 된다. 하네스가 git SSH URL도 HTTPS로 재작성한다). 대신 **당겨오는 경로**를 쓴다 — GitHub Actions `blockship-smoke.yml`을 수동 실행:
  - `promote=true` → **콘텐츠 게이트 3종**(퀘스트감사·굵은포맷·타임존) + 빌드 + 부팅스모크 통과 시 Release 발행 → prod가 당겨 `staging/` → **06:00 적용**. 게이트는 빌드보다 «먼저» 돈다.
    - 이 3종은 플러그인 소스·데이터만 보므로 CI 에서 돌 수 있다. 스크립트는 `blockship-plugin/tools/` 에 **한 벌만** 둔다(scripts 레포에 사본을 만들면 CI 와 맥이 다른 규칙을 돈다 — `ops/audit-copies.py` 검사 ⑤ 가 잡는다).
    - 라이브 인스턴스 데이터가 필요한 게이트(사본드리프트·목표id대조·NPC대사·staged JSON)는 맥 경로가 맡는다.
  - `apply_now=true` → Release 본문에 `APPLY_NOW` 마커 → prod가 당겨오는 **즉시 적용+재시작**(최대 지연 = cron `*/5`). promote도 켜진 것으로 본다.
  - GitHub은 **MCP 도구로만** 다룬다(셸에서 `api.github.com` 직접 호출은 403). 절차·함정은 스킬 `deploy-prod` 참조.

**전체 변경** — Git 백업
- 이 폴더(설계 문서 + 설정)가 git repo
- 의미 있는 변경마다 commit
- 오라클은 git pull 하지 않음 (rsync로 이미 sync됨). Git은 백업/롤백용

### 운영 명령어
```bash
# 오라클 SSH 접속
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107

# 마크 서버 콘솔 (tmux 세션)
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 -t 'tmux attach -t mc'
# 분리: Ctrl+B, D

# 마크 서버 재시작 (systemd)
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 'sudo systemctl restart mcserver'

# 로그 확인
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 'tail -f ~/mcserver/logs/latest.log'

# 플레이어 데이터 백업 (진행도 = 레벨/돈/장비/강화)
scp -i ~/.ssh/oracle-mc.key -r ubuntu@168.107.8.107:~/mcserver/plugins/BlockShip/playerdata ~/Desktop/prod-playerdata-$(date +%Y%m%d)
```

### 자동 백업 — 05:50 KST 선행 월드 tar + 06:00 KST 유지보수
**2겹 백업**: 로컬(빠른 되돌리기) + 오프사이트(인스턴스 사망 대비 DR). 스크립트는 박스 `~/mcserver/scripts/`.
★월드 tar만 `pre-restart-backup.sh`(cron `50 20 * * *` UTC = **05:50 KST**)로 분리했다. 오늘 날짜 마커가 있어야 06:00이 이를 재사용하며, 실패·미완료·마커 부재에는 안전하게 기존 정지 중 백업으로 폴백한다. 유지보수는 선행 백업 락이 잡힌 동안 월드를 종료하지 않는다.
- **[05:50 KST · 서버 실행 중]** — `save-all flush` 후 gzip 검증을 통과한 로컬 월드 tar를 순차 생성한다. 오늘 실측 본월드 112초 + 섬 23초이므로, 06:00 재시작의 접속 불가 창에서 약 139초를 뺐다.
  1. `local-backup.sh main` — world계열+flatroom+mine → `backups/localmain-*`, 로컬 3개
  2. `local-backup.sh islands` — guild_world+island_world → `backups/localislands-*`, 로컬 7개
  - 라이브 tar도 `tar`의 읽는 중 변경 경고(rc=1)는 무결성 검증된 아카이브로 취급한다. rc≥2 또는 `gzip -t` 실패만 실패다.
- **[06:00 KST · 서버 정지 중]** — `playerdata`만 종료 저장 직후 tar한다(약 4초). 정상 시 월드 tar를 다시 만들지 않아, 순수 부팅 시간에 가까워진다.
  3. `offsite-backup.sh --tar-only` — BlockShip 폴더(playerdata+라이브 JSON) **tar 만**. playerdata 는
     종료 저장 직후가 가장 정확하다.
- **[기동 + RCON 부팅확인 후]** — 업로드는 네트워크에 묶여 있어 정지 창에 넣지 않는다.
  → Oracle Object Storage 버킷 `mc-backups`(instance principal 인증=박스에 OCI키 없음, 버전관리 ON)
  4. `offsite-backup.sh --upload-only <tar>` → `blockship/`, 원격 30개
  5. `offsite-worlds.sh islands --upload-only <localislands tar>` → `islands/`, 원격 5개
  6. **KST 1·15일만** `offsite-worlds.sh main --upload-only <localmain tar>` → `world/`, 원격 2개(격주)
  7. 레거시 `playerdata-*.tar.gz` prune(신규 생성 없음)
- ★**오프사이트는 tar 를 다시 뜨지 않는다.** `offsite-worlds.sh` 의 월드 목록이 `local-backup.sh` 와
  글자까지 같아서 예전엔 **같은 내용을 하루 두 번 압축**했다(본월드 1.4GB×2회). 이제 05:50에 뜬
  로컬 tar 를 `--upload-only` 로 그대로 올린다 → 중복 압축 제거. playerdata는 종료 직후 tar를 그대로 올린다.
  두 스크립트를 **인자 없이** 부르면 예전처럼 tar+업로드를 혼자 다 한다(수동 실행·복구용).
- ★**낡은 tar 가 오늘 이름으로 올라가지 않는다** — `fresh_tar` 가 60분 이내 파일만 고른다. 로컬 백업이
  실패한 날엔 오프사이트도 로그에 «건너뜀» 으로 남지, 어제 것이 오늘 백업으로 둔갑하지 않는다.
- ★**옛 cron 줄(`0 19`/`30 20`/`45 20 1,15`/`0 20`/`10 20`)을 되살리지 말 것** — 지금은 이들을
  `05:50 pre-restart-backup.sh` 하나로 조정했으며, 되살리면 같은 백업이 하루 두 번 돈다.
- **백업이 아닌 cron 은 그대로 둔다**: 디스크가드(매시 :15)·하트비트(5분)·crash-watch(2분)·
  fetch-staging/fetch-resourcepack(5분)·재시작 예고(05:30/50/55/59). 상시 감시라 하루 1회로 몰면 의미가 없다.
- 선행 tar는 `save-all flush` 뒤에 돈다. **알림**: 실패=즉시 개별 🔴, 성공=상태파일(`.backup-status`)에 누적 → `nightly-restart.sh`(cron 21:00 UTC=06:00 KST, "데일리 유지보수")가 **①staging 자동배포 ②무조건 재시작(05:50 월드 tar 재사용+정지 중 playerdata tar) ③RCON 부팅확인(최대 3분) ④오프사이트 업로드 ⑤데일리 리포트** 🌅(배포결과+백업 성공목록+부팅확인+헬스)로 하루 1회 통합 발송(노이즈 최소화). 재시작 사전예고는 `restart-warning.sh <30|10|5|1>`(각각 05:30/05:50/05:55/05:59 KST 별도 cron, 접속자 0명이면 조용히 스킵)이 담당 — nightly-restart.sh 자체는 재시작 직전 즉시 알림 1회만. PREVIEW=1로 발송·재시작·배포 없이 리포트 미리보기 가능. webhook=`~/mcserver/scripts/discord-webhook.url`. ★리포트는 백업 결과를 담아야 하므로 **기동 후**에 나간다(그래서 `.backup-status` 도 그때 비운다). 스킵 마커·리소스팩 가드 실패로 재시작을 취소하는 날엔 선행 백업을 재사용하고, 없으면 라이브로 폴백한다. ★같은 스크립트에 **즉시 모드(`--now`/`NOW=1`)** 가 있다 — `fetch-staging.sh`가 APPLY_NOW 마커를 보면 부른다(아래 무인운영 절).
- tar는 라이브 서버 파일이 읽는중 바뀌면 exit 1(경고, 아카이브 유효)을 냄 → `tar||fail` 금지, `--warning=no-file-changed`+rc≥2만 치명+`gzip -t` 무결성검증으로 성공판정(2026-07-24 본월드 백업 오탐 사고 후 수정).
- ★staging은 `~/mcserver/backups/offsite-stage/`로 격리(로컬 백업과 glob 충돌 방지 필수).
- 상세·복원법: memory `project_offsite_backup_dr`. 복원 = Object Storage에서 `oci os object get`→tar 해제.

### 프리즈 워치독 (2026-07-24 신설, 무인운영 자가복구)
- systemd `mcserver`는 프로세스 death만 잡음(`Restart=always`). **메인스레드 프리즈(데드락/GC지옥)는 못잡아서** 외부 워치독 추가.
- `~/mcserver/scripts/watchdog.sh` (cron `*/2`, flock): `rcon.py list` 2분간격 헬스체크 → **4회 연속 무응답(≈8분)=프리즈 판정→`systemctl restart mcserver`+Discord 알림**. 순간렉/저장/GC는 다음 체크 회복→카운터 리셋. 부팅유예 5분, 1시간 3회초과=크래시루프로 보고 재시작중단+🆘.
- **★prod RCON 켜짐**: `enable-rcon=true`, 포트 25575, 비번=랜덤(server.properties). 외부는 iptables 기본 REJECT 차단, localhost만. `~/mcserver/scripts/rcon.py list`로 수동 확인/명령 가능. (dev RCON은 별개 pw devtest2026)
- 상세: memory `project_offsite_backup_dr`.

### 클라이언트 크래시 자동감지 (2026-07-27 신설)
- 서버는 클라 크래시 진짜 원인(DecoderException 등)을 모름 — 그건 유저 로컬 `disconnect-*.txt`에만 있음. 대신 **"접속 후 15초 이내 끊김"**을 크래시 의심 신호로 자동 포착 → 유저 수동제보 없이도 먼저 인지.
- `~/mcserver/scripts/crash-watch.py` (cron `*/2`, flock, 상태 `.crash-watch-state.json`에 오프셋/최근접속시각 영속): 로그에서 접속↔`lost connection`을 페어링하지만, **빠른 끊김 Discord 알림은 2026-08-22부터 비활성화**했다. 일반 운영 알림은 그대로 유지한다.
- 실전검증(2026-07-27 마리/잉그리드 오진 사고): 과거 7건의 lost connection 중 실제 급끊김(크래시성) 6건을 정확히 잡아냄, 정상 3분 세션 뒤 끊긴 1건은 올바르게 제외.
- ★진짜 원인은 ViaVersion/ViaBackwards가 최신 클라(26.2) 미지원 낡은 스냅샷(5.11.1-SNAPSHOT)이었던 것으로 판명 — 정식 5.11.0(1.8~26.2 지원)로 교체 후 해결. NPC 모델부착(NpcAnimator)은 무관했음(오진, 원복 완료). 향후 이런 "클라 최신버전 vs Via 구버전" 드리프트가 재발 원인 1순위. 수정 전/후 로그 대조로 해결 검증 완료(수정후 정상 5분+ 세션 확인).
- **패킷 블랙박스**(`com.blockship.diagnostics.PacketBlackbox`, ProtocolLib): 급끊김(15초 이내)이면 직전 엔티티 패킷(ENTITY_METADATA·EQUIPMENT·SPAWN_ENTITY·ENTITY_DESTROY) 40개를 `plugins/BlockShip/packet-blackbox/`에 덤프한다. 다만 crash-watch.py는 이 덤프를 Discord로 첨부 전송하지 않는다.

### 무인운영 자동화 추가분 (2026-07-24, 군입대 대비 자가복구 시리즈)
- `~/mcserver/scripts/nightly-restart.sh` (cron 21:00 UTC=06:00 KST): staging 자동배포+**무조건** `systemctl restart`(누수 정리, 접속자 있어도 실행)+디스코드 데일리 리포트. 사전예고(30/10/5/1분 전 인게임 방송)는 `restart-warning.sh`가 별도 cron으로 담당(2026-07-27 신설).
  - **즉시 모드 `--now`(=`NOW=1`)**: 06:00을 안 기다리고 지금 적용. `fetch-staging.sh`가 APPLY_NOW 마커를 보면 `exec`으로 넘긴다(cron의 flock이 재시작·부팅확인 끝까지 유지 → 다음 주기 안 겹침). ★**적용 로직을 복제하지 않으려고** 같은 스크립트에 모드를 붙였다 — validate-staged 게이트·리소스팩 교차검증·구 jar 백업이 전부 여기 있다. 정기와 다른 점 4개: ①staging 비면 **재시작 안 함**(정기는 누수정리라 무조건) ②예고가 없었으므로 `GRACE`초(기본 60) 방송 후 재시작 ③데일리 리포트가 아니라 배포 알림 + **`.backup-status`를 지우지 않음**(지우면 그날 06:00 리포트가 「백업 기록 없음」이 되어 진짜 실패와 구분 불가) ④재시작 후 RCON 부팅확인(40회×5초), 실패 시 롤백법과 함께 🔴. skip-once 마커는 정기 전용이라 안 건드림. 미리보기: `PREVIEW=1 NOW=1 nightly-restart.sh`.
- `~/mcserver/scripts/disk-guard.sh` (매시간): `df /` 사용률 85%⚠️경고 / 92%🔴면 가장 오래된 로컬 백업부터 삭제해 88% 아래로 확보(★라이브 데이터·오프사이트는 절대 안 건드림).
- `~/mcserver/scripts/heartbeat.sh` (cron 5분): MC 포트 살아있으면 healthchecks.io로 핑 → 박스 자체가 죽거나 cron이 멈추면 **박스 밖에서** 침묵 감지, 25분 무응답 시 디스코드 알림(데드맨 스위치, 온박스 워치독의 사각 커버).
- **`~/mcserver/scripts/fetch-staging.sh` (cron `*/5`, 2026-08-14 가동)**: GitHub Release → `staging/` **당겨오기**. 방향이 핵심이다 — 폰/맥이 prod에 밀어넣는 게 아니라 prod가 당겨오므로 **폰에 SSH 키가 없어도, 맥이 꺼져 있어도 배포가 돈다.** 전제: Actions가 **수동 promote(`workflow_dispatch` + `promote=true`)일 때만** Release를 만든다 → "최신 Release 존재" = "사람이 승격을 눌렀다". ★push마다 Release가 생기게 바꾸면 이 전제가 깨지니 금지. 토큰 `~/mcserver/.github-token`(fine-grained PAT, contents:read, 600).
  - 무변화면 **로그도 안 남긴다**(주기마다 한 줄씩 쌓이면 진짜 사건이 묻힌다 — 그래서 `*/5`로 조여도 노이즈가 안 늘었다). 404=아직 Release 없음(정상, 조용히 exit 0) / 401·403=진짜 실패만 🔴 알림.
  - **★즉시 적용(APPLY_NOW)은 폐지됐다 (2026-09-02 유저 결정 — 즉시배포는 dev 전용).** 폰·웹에서 승격을 눌러도 prod 는 **staging 까지만** 받고, 적용·재시작은 06:00 정기 경로가 유일하게 한다. 3겹으로 끊어 뒀다: ①`fetch-staging.sh` 의 APPLY 분기가 알림만 내고 exit(죽은 즉시적용 코드 27줄 제거, `nightly-restart.sh --now` 호출 없음) ②`fetch-resourcepack.sh` 는 `server.properties` URL/SHA1 만 갱신하고 재시작 안 함 ③**생산자 쪽도 마커를 안 박는다** — `blockship-smoke.yml`·`mobile-prod-release.yml` 의 `apply_now` 입력과 `APPLY_NOW` 문구를 제거했다. ★버튼만 되살리면 "눌렀는데 아무 일도 안 나는" 거짓 UI 가 된다(소비자가 무시하므로). 즉시 확인이 필요하면 dev: `~/deploy-dev.sh`.
  - ★**PAT 만료가 조용한 사고 지점** — 만료되면 배포가 그냥 안 온다(서버는 멀쩡). 만료일 관리 필요.
- **`~/mcserver/scripts/rollback-jar.sh` (2026-08-14 신설, 수동 전용)**: 깨진 jar 롤백을 한 줄로. `list`(후보+라이브 sha256+staging 대기, 무해) / `dry` / `yes` / `yes to <파일>`. **하이픈 없이 쓴다** — 모바일 키보드가 `--`를 대시로 바꿔 안 먹은 실측 사례가 있어 en/em dash도 정규화한다. 보존→교체→**staging 비움**→`.fetch-staging-state` 초기화→재시작→부팅확인→알림. ★staging을 안 비우면 다음날 06:00에 깨진 jar이 재적용된다(그래서 스크립트로 묶었다).
- 로그: `backups/watchdog.log`(프리즈워치독) · `backups/ops.log`(nightly/diskguard/**fetch-staging/rollback**) · `offsite.log` · `local.log`. ★운영 로그는 `backups/` 에 모인다 — 새 스크립트가 `scripts/ops.log`로 쓰면 장애 때 한쪽만 보게 된다.
- **모바일 리소스팩 배포**: `minecraft-fish-resource-pack`은 `develop`(검증) → `main`(prod) 흐름이다. `develop` push는 빌드만 하고, `main` push/merge가 검증 통과 시 `MOBILE_RP_PROMOTE` + `APPLY_NOW` Release를 자동 발행한다. prod의 `fetch-resourcepack.sh`가 최대 5분 안에 받아 검증·60초 예고·재시작한다. 폰에 SSH 키는 필요 없다. 일반 Release와 dev 업로드는 puller가 무시한다.
- 잔여 리스크(인지함, 미자동화): 박스 자체 재구축(결제 필요, 유저 몫) / 기능적 플러그인 고장(서버는 살아있는데 게임 로직만 깨짐 — RCON 헬스체크로 감지 불가) / 손상 데이터가 백업을 덮는 경우(버전관리+보관기간으로만 완화) / **PAT 만료**. 코드·리소스팩 배포는 2026-08-19부터 클라우드 세션에서도 가능(APPLY_NOW).

### Resize 자동 재시도 (백그라운드)
- 위치: `~/oracle-auto-retry/resize-retry.sh`
- 동작: 현재 사양보다 큰 자리 나는 대로 자동 resize 시도 (목표 4/24)
- 로그: `~/oracle-auto-retry/resize-retry.log`
- 성공: `~/oracle-auto-retry/SUCCESS-RESIZE.txt` 생성 + macOS 알림

## 체스·보드게임 + 피아노 (별도 플러그인 — BlockShip 아님)

### ★2026-09-06 업스트림 통합 — 플러그인이 3개 → 2개가 됐다
원저자가 보드게임과 피아노를 **한 jar 로 합쳐서** 준다: `BarkanBoardGames-Piano-1.1.0.jar`
(`name: BarkanChess`, `version: 1.1.0-combined`, `main: kr.barkan.chess.BarkanChessPlugin`,
안에 `kr.barkan.piano.*`). **체커·요트**가 새로 들어왔고 피아노는 **44 → 49건반**이 됐다.
`BarkanPiano-*.jar` 은 이제 필요 없다 — **같이 두면 피아노를 두 플러그인이 관리한다.**
- ★**빠진 것이 있다**: `kr.barkan.chess.art`(그림·캔버스·이젤)와 `kr.barkan.chess.backrooms`
  (스마일러·손전등·캠코더)를 통째로 들어냈다. 새 메인 클래스에 두 패키지 참조가 **0건**이라
  `tools/patch-art.sh` 식 클래스 오버레이가 안 통한다(죽은 코드만 남는다). → 동반 플러그인
  **`BarkanArt`** 로 밖에서 세운다: `~/development/barkan-chess/tools/build-art-companion.sh`.
  매니저에 **BarkanChess 인스턴스를 넘겨서** NamespacedKey·데이터폴더·config 가 예전과 똑같다
  (`this` 를 넘기면 유저 인벤의 붓·팔레트·손전등이 전부 남남이 된다). 상세는 그 저장소 README.
- **`/piano 설치88`(88건반)은 폐기된 정책** — `piano88.*` 음원은 팩에 넣지 않는다.
- **피아노 데이터 이관은 한 번뿐이다**: 통합 jar 이 부팅 때 `plugins/BarkanPiano/pianos.yml` 을
  `plugins/BarkanChess/pianos.yml` 로 복사하는데, **목적지가 없을 때만** 한다. 레거시 파일 없이
  한 번이라도 뜨면 빈 `pianos.yml` 이 생기고 이관은 영영 건너뛴다(2026-09-06 dev 재현). prod 에
  올릴 때 `plugins/BarkanChess/pianos.yml` 이 없는지 먼저 확인할 것.

## 체스 (별도 플러그인 — BlockShip 아님)
- 소스: **`~/development/barkan-chess`** / GitHub `wsi1212/barkan-chess`(private). 2026-08-11 BlockShip에서 분리(결합도 0 — 순수 Bukkit/Adventure).
- 원저자가 **컴파일된 jar만** 주므로 소스는 vineflower 역컴파일 복원본이다. **배포 전 `tools/gate.sh <업스트림.jar>` 필수** — ①업스트림 바이트코드 대조 ②랜덤 자가대국 퍼징(무한루프/예외). 2026-08-10 `hasBattery` 역컴파일 왜곡으로 무한루프→Paper 워치독이 prod를 죽인 사고 재발 방지책.
- 데이터: `plugins/BarkanChess/`(config.yml=테이블·엔진, skins/preferences/achievements/decks/player-stats/variant-stats.yml). 말 모델은 **메인 리소스팩**에 포함(PAPER `custom_model_data` 21001~22301, `assets/minecraft/items/paper.json`).
- **캔버스(그림·이젤·팔레트)는 2026-09-06 부터 동반 플러그인 `BarkanArt` 다** — `kr.barkan.chess.art`.
  업스트림 통합 jar 이 이 패키지를 들어내서 오버레이(`tools/patch-art.sh`)가 못 쓰게 됐다.
  빌드: `tools/build-art-companion.sh`. ★이젤 모델(`art_easel.json`)과 `PaintingManager.EASEL_Y`
  는 짝이라 리소스팩·jar 을 함께 배포해야 한다(한쪽만 올리면 이젤과 그림이 0.5블록 어긋남).
- `/체스`(cp) — 참가/솔로/AI/퇴장/스킨/규칙/덱/증강/도전과제/전적, op: 생성·제거·테이블·소환·평가·엔진탐지·변형통계·리로드. Stockfish는 dev `/opt/homebrew/bin/stockfish`, prod `/usr/games/stockfish`.

## 피아노 (2026-09-06 부터 위 통합 jar 안에 있다 — 별도 플러그인 아님)
- 소스: **`~/development/barkan-piano`** (2026-08-25 분리 → 2026-09-06 업스트림이 BarkanChess 로
  흡수). **자바 소스는 더 이상 배포되지 않는다** — 살아 있는 건 `tools/sync-resourcepack.py` 하나다.
  코드 후속 작업은 `~/development/barkan-chess`.
- 데이터: **`plugins/BarkanChess/pianos.yml`** (통합 후 위치. `plugins/BarkanPiano/` 는 이관 원본으로만
  남는다 — 위 「업스트림 통합」의 1회성 복사 주의). 엔티티는 태그 `barkan_piano_<id>`/`barkan_seat_<id>`,
  `layout-version`(현재 5) 은 옛 피아노 높이 보정용.
- **소리는 메인 리소스팩에 병합해서 간다** — 팩을 3개로 늘리지 않는다. 업스트림 사운드팩 zip 은
  체스팩+피아노 한 덩어리라 **피아노만 골라** 넣는다: `barkan-piano/tools/sync-resourcepack.py <zip>`
  (매번 zip 에서 다시 뽑음). 배포는 `ops/rp-deploy.sh`.
  - ★**모노 변환은 기본이 아니다**(`--mono` 로만). 2026-08-25 에 모노로 내렸다가 「받은 곳이랑 소리가
    다르다」는 지적을 받고 되돌렸다 — 넓은 스테레오 피아노는 다운믹스에서 위상이 상쇄돼 음색이 얇아진다.
    대가는 알고 간다: 마인크래프트는 스테레오 ogg 를 위치 음원으로 취급하지 않아 거리 감쇠·방향이 없다.
    음색을 지키는 쪽을 택했다. 권위는 그 스크립트의 주석이다(이 줄이 아니라).
  - ★**업스트림이 안 쓰는 `piano.*` 선언은 지운다** — 파일만 지우고 선언을 남기면 클라가 없는 ogg 를
    찾아 로그를 쌓는다(49건반 전환 때 `piano.release_*` 44개가 그럴 뻔했다).
  - ★인코딩은 **`oggenc`** 로 — homebrew ffmpeg 8.1 에 libvorbis 인코더가 없어 위 「커스텀 사운드」
    절의 `ffmpeg -c:a libvorbis` 는 이 맥에서 실패한다. ffmpeg 은 디코드·다운믹스만.
- **실연주는 클라이언트 모드 전제** — 건반 입력이 플러그인 메시지 채널 `barkan_piano:note` 로 온다.
  모드 없으면 `/piano note <a~z>` 로 한 음씩만. 바닐라·베드락 유저는 앉기만 된다.
- `/piano`(피아노) — 설치·앉기·내리기·목록·제거·복구·note. 설치/제거/복구는 `barkan.piano.admin`(op).

## 리소스팩
- **소스 위치(★2026-06-06 이후, Downloads 경로는 낡음): `~/development/barkan-resourcepack`** — `~/Downloads/barkan-resourcepack/`은 더 이상 존재하지 않음(TCC가 Downloads/Desktop 재귀읽기 차단해서 이동함).
- GitHub: `https://github.com/wsi1212/minecraft-fish-resource-pack` (release `latest`에 메인팩 `barkan-resourcepack.zip`+CraftEngine 가구팩 `barkan-furniture.zip` 2개 자산 공존 — `gh release delete` 절대 금지, `--clobber` 업로드만)
- 서버 자동 적용: `server.properties`에 GitHub Releases URL+SHA1 설정됨 (`require-resource-pack=true`)
- **맥 즉시 배포: `ops/rp-deploy.sh <dev|prod> [--restart] [--dry-run]`** — ★진입점은 이 파일 하나다(회귀 가드 20종: 글리프 provider 수·텍스처 존재·pack.mcmeta min/max_format·공개 URL sha1 재확인). `~/deploy-rp.sh` 는 **폐지**됐다 — 검증 없는 생 zip 이라 2026-08-11 에 낡은 스냅샷을 구워 gui 텍스처 761개가 빠진 팩을 prod 에 올렸다. 실행하면 안내만 내고 거부한다.
- **모바일 배포: 기본은 `develop` → `main` 머지**. `main` push가 자동으로 prod Release를 만들고 `APPLY_NOW`로 적용한다. 수동 실행도 가능하지만 `main`에서만 `promote=true`가 실제 승격으로 동작한다.
- **커스텀 사운드**: `assets/barkan/sounds.json`에 등록, `assets/barkan/sounds/weather/*.ogg`에 파일 배치
  - ogg (Vorbis) 형식만 지원, wav→ogg 변환: `ffmpeg -i input.wav -c:a libvorbis -q:a 5 output.ogg`
  - 페이드아웃: `ffmpeg -i input.wav -t 19 -af "afade=t=out:st=16:d=3" -c:a libvorbis -q:a 5 output.ogg`
- 상세: [resourcepack.md](resourcepack.md)
