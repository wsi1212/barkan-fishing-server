# Fish - 바르칸 열도 낚시 서버

## 프로젝트 개요
마크 서버용 종합 낚시 게임. **Paper 1.21.11 + Java 21 툴체인(런타임 JVM 은 Java 25).** 모든 게임 로직은 BlockShip 자바 플러그인에 기능별 패키지로 구현돼 있다 — **자바 359파일 / `com/blockship/` 아래 70개 패키지**(2026-08-14 실측). 낚시는 그중 하나일 뿐이고 채집·채굴·요리·카지노·길드·섬·보스까지 한 플러그인에 다 들어있다.
- **소스(Mac 로컬)**: `/Users/user/development/blockship-plugin/src/main/java/com/blockship/`
- **소스(GitHub)**: `wsi1212/blockship-plugin` (**private**) — 맥이 없는 환경(웹/모바일 세션)에서는 이쪽을 클론해서 본다. 루트에 라이브 JSON(`fish.json` `parts.json` `quests.json` `npc.json` `enhance.json` `materials.json` `recipes.json` `titles.json` `dialogue.json`)도 같이 들어있다.
- 이 리포(`wsi1212/barkan-fishing-server`)는 **설계 문서 + 에셋 파이프라인 + 운영 스크립트**만 있고 게임 코드는 없다. 둘은 별개 리포다.

상세 설계: [design.md](design.md) | 수치 밸런스: [balance.md](balance.md) | 스토리: [story.md](story.md)

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
| **페리** | `ferry/FerryManager` | 지역간 자동 이동 (노선, 요금, 보스바) |
| **지역** | `region/RegionManager` (RegionData·RegionTracker·RegionCommand) | Java 데이터(regions.json) |
| **날씨** | `region/WeatherManager` (WeatherCommand·WeatherInfoCommand) | 지역별 독립 날씨, 파티클, 사운드, 시야 제한 |
| **사이드바** | `sidebar/SidebarManager` | 스코어보드 — **콤보만 남음**. 레벨·소지금·위치·환경 4줄은 2026-08-09에 `hud/StatusHud`(BetterHud 그래픽 HUD)로 이관. 위치·환경 **문자열 자체는 여전히 SidebarManager가 만든다**(지역 부모체인·날씨예외 재사용) → 되돌릴 땐 양쪽 같이 볼 것 |
| **화면 HUD** | `hud/StatusHud` (BetterHud) | `barkan_status`(우상단: 소지금·낚시Lv+경험치·캐시) / `barkan_place`(좌상단: 위치·환경). 숫자포맷·경험치바 칸수는 **자바가 완성해서** 넣는다(yml에서 조립 금지 — 규칙 두 곳 분기) |
| **메뉴 허브** | `misc/MenuManager` | `/메뉴` 타일형 3장(메뉴·내 정보·상점) + Shift+F 단축키. ★**타일은 아이템이 아니라 그림이다** — 배경 글리프에 아이콘·라벨까지 구워두고(`gui-forge/compose_gui3_imagegen.py`) 칸엔 아무것도 안 올린다(올리면 겹쳐 가림). 클릭은 슬롯 번호로만 판정. 3열 타일 기준(9열을 3+3+3) |
| **숙련 특성 트리** | `skilltree/SkillTreeManager` (RewardRevealFx) | 설계 전거 [skill-tree-dopamine-design.md](skill-tree-dopamine-design.md). 레벨업마다 숙련 포인트 +1 **소급**(가용 = (레벨-1) - 총투자, 별도 지급절차 없음). 저장=PlayerData.extraNums(`특성<숙련>.<노드id>`), 초기화 처음 10P 무료·이후 P당 5000원. 한 행동에 대형 잭팟 1종만 |
| **채집** | `forage/ForageManager` | 지역 채집물 노드(ItemDisplay+Interaction, crop과 동일 네이티브 방식) + **유저별 쿨타임**(수확자에게만 hideEntity, 남들은 그대로 캠) + 리듬 연타 미니게임. 쿨 흔함 90분 / 희귀 20시간 |
| **작살(창낚시)** | `harpoon/` (HarpoonManager·FishHitbox) | 1.21.11 창(spear) 기반. 물고기=ItemDisplay 1개, **투명몹 히트박스 없음** — 판정은 서버측 ray↔OBB 교차로 렌더 변환을 그대로 역산(회전·크기·위치 정의상 일치) |
| **채굴 (2종, ★별개)** | `drill/` (mine 월드) vs `islandmine/` (island_world·guild_world) | **드릴**=PDC 티어 곡괭이, block_break_speed ×0 잠금 후 우리가 직접 파괴·균열 렌더·재생 예약. **섬 광산**=코블스톤 생성기 방식(물↔참나무 울타리 사이 공기칸이 광석으로 참, 캐면 즉시 재생, 저장 불필요·상시부하 0). 서로 무관하니 헷갈리지 말 것 |
| **카지노** | `casino/` (34파일 — `slot/` `table/` `card/` `blackjack/` `holdem/` `seotda/` `roulette/`) | ★2026-07-14 구 GUI 카지노(로비+GUI 카드게임) **전면 폐지** — 카드·룰렛은 전부 **물리 테이블**(`casino.table`), `CasinoManager`는 슬롯머신 캐비닛 흐름만. 베팅은 판 종료 후 **net만 반영**, roundId+viewSeq로 오래된 GUI·더블클릭 이중정산 차단 |
| **텔레메트리** | `telemetry/` (20파일 — Telemetry 파사드·TeleWriter·TeleDb) | 설계 전거 [stats-system-plan.md](stats-system-plan.md). **어떤 메서드도 예외를 호출부로 전파하지 않는다**(통계가 죽어도 게임은 안 죽는다). 호출은 큐 삽입까지만(µs), 직렬화·디스크 IO는 TeleWriter 전용 스레드. ★**신규 시스템은 계측 필수** — 플러그인 리포 CLAUDE.md의 「텔레메트리 계측 규약」 참조 |
| **도전과제** | `misc/AchievementManager` | 카탈로그 권위 = `BlockShip/achievements.json`. **카탈로그 버전이 바뀌면 `PlayerData.completedAchievements` 전체 리셋**(베타 정책 — 구 ID가 새 과제 오염시키는 것 방지). 조건은 이벤트가 아니라 PlayerData 현재 상태를 읽어 평가 |
| **이무기 보스** | `boss/` (ImugiBossManager·ImugiBattle·ImugiRig) | 리그 데이터 `plugins/BlockShip/imugi_rig.json` (`imugi-boss/` 변환 파이프라인 산출물). 보스 엔티티 `persistent=false`(배와 동일 정책) + PDC 태그 고아 sweep 이중방어 |
| **배** | `ship/` (ShipManager·ShipFactory·ShipTickTask) + `model/` + `command/ShipCommandManager` + `editor/ShipEditor` | BlockDisplay+Shulker, 프리셋 3종. ★**`ShipMover`는 호출자 0건인 죽은 코드** — 실제 이동은 `task/ShipTickTask`이고 `pilot.getCurrentInput()`에 하드결합(파일럿 없으면 감속 후 강제도킹). 그래서 컷씬은 배 시스템을 안 쓴다(`cutscene/` 참조) |

**기타 시스템 위치**: 도감 `dex/`·`collectible/` · 마켓/거래 `market/`·`trade/`(SalePostManager·TradeManager·TradeLog) · 길드 `guild/`(GuildManager·IslandBuilder·SchematicPaster·GuildBuffEffects·GuildCookingManager) · 섬 `island/`(IslandManager·IslandProtectionListener·IslandFlyManager·IslandAutoPlantManager·IslandSubmitManager) · 프로필 `profile/`(ProfileGui·SkinRenderer) · 랭킹 `ranking/RankingManager` · 통발 `trap/`(TrapManager·TrapSpecs) · 특수작물 `crop/`(CropManager·CropSpecs, 요리재료·섬한도·BlockShip네이티브 ItemDisplay) · 요리 `cooking/`(DishSpecs·CookingManager·CookingGui·CookingQueueManager·CampfireManager, 먹기버프+제출+판매 3용도, 요리사NPC 주방=대장간분리) · 짚라인 `zipline/` · 스킬 `skill/SkillManager` · 제작 `crafting/`(RecipeLoader·MaterialLoader·ArtifactAppraisalGui 유물감정) · 광질모자 `mining/` · 여관 `inn/` · 포탈 `portal/`(PortalManager·PadManager) · 물텔포 `water/` · 캐시샵 `economy/CashShopGui`·`CashEffectManager` · 돈·수표·송금 `economy/`(MoneyCommand·CheckCommand·TransferCommand)·`playerdata/MoneyBridge` · 스크롤 `scroll/` · 잠긴문/열쇠 `door/`(LockedDoorManager — 아래 「잠긴문/열쇠 규약」 필독) · 상자잠금 `lock/`(ChestLockManager·ChestLockListener — 아래 「상자 잠금 규약」) · 잠수(AFK) `afk/`(AfkManager — 방치 10분→잠수대 월드 afk_world 자동이동, `/잠수`(wkatn·ㅈㅅ) 토글, 복귀위치=extraStrs[잠수복귀], `/잠수 설정 <초>` OP, AfkShopGui) · **데이터 영속** `playerdata/`(PlayerData·PlayerDataManager, 단일 권위) · 유틸 `util/`(Num 숫자포맷·Worlds.dimKey·ItemCodec·GuiFrame·GuiTitle·ItemFlavor·Plates)

**기타 시스템 위치 ②** (2026-08-14 추가 — 위 목록에 아예 빠져 있던 것들):
- **BGM** `bgm/BgmManager` — 지역·날씨별 배경음악. **"이동 스피커" 방식**: 플레이어마다 보이지 않는 ItemDisplay 스피커를 두고 모노 사운드를 AMBIENT로 재생, 매 틱 플레이어에게 TP. 볼륨은 못 바꾸지만 MC 클라가 **모노 사운드 볼륨을 거리로 실시간 갱신**하므로 스피커를 위로 멀리 보내면 재트리거·끊김 없는 진짜 페이드아웃이 된다. ★아머스텐드 등 다른 엔티티는 이 서버에서 엔티티부착 사운드가 **무음**, ItemDisplay만 정상(2026-07-15 실측)
- **이모트/버스커** `emote/`(EmoteManager·EmoteGui·BuskerRegistry) — 'steve' 플레이어 limb 모델로 본인을 디스가이즈 후 애니 재생(짚라인과 동일 메커니즘). 춤(loop)은 움직이면 정지, 감정표현(once)은 1회 후 자동해제. 피격·사망·탑승·퇴장 시 즉시 해제(디스가이즈 잔류 방지). **BetterModel 클래스를 직접 참조** → 플러그인 존재 확인 후에만 인스턴스화. 관련 스킬: `mocap-emote`
- **길찾기** `nav/`(NavigationManager·NavTarget·NavCommand) — 발 높이 지면에 눕는 ▷ BlockDisplay 화살표. 점프해도 안 흔들리게 Y를 착지높이 고정, 목적지가 지역이면 매 틱 최근접점 조준. **방문한 지역만** 수동 길찾기 가능(퀘스트 자동안내는 미방문도 허용). Citizens 미사용
- **우편함** `mail/`(MailboxManager·MailboxGui·MailboxLoginListener) — 수령 전용. 구 `PlayerData.mail`의 ItemCodec 문자열도 읽어 7일짜리 아이템 우편으로 전환. **인벤 지급과 우편 삭제는 같은 PlayerData 저장이 성공할 때만 확정**
- **도개교** `drawbridge/`(DrawbridgeManager·Drawbridge) — 경첩축 회전, 체인은 앵커→발판끝 매 틱 재계산. **열쇠(`extraFlags["열쇠"]`) 보유자만** 성문 우클릭 개폐(잠긴문 시스템과 열쇠 저장소 공유). 휴지=실블록, 여닫는 동안만 디스플레이 전환. 디스플레이 전부 non-persistent → 재시작 시 `drawbridges.json`에서 재구성
- **말 대여** `horse/`(HorseRentalManager·HorseRentalGui) — 1000원, 300초 뒤 자동회수, 1인 1마리, 소환자만 탑승. `setPersistent(false)` + 스코어보드 태그 sweep 이중안전
- **엠블럼** `emblem/EmblemCommand` — `/엠블럼`(op) 길드 엠블럼 item_display를 벽에 부착 후 크기·회전·롤·이동 전부 명령으로 제어
- **가구 크기** `furniture/FurnitureSizeManager` — OP 전용, **새로 설치하는** CraftEngine 가구만. CE 가구는 인스턴스 단위 리사이즈가 불가(스케일이 immutable config에만 존재)라, 기존 `ground` variant는 **절대 안 건드리고** 명령마다 새 `blockship_size_N` variant를 추가 → FurniturePlaceEvent에서 새 가구만 전환. 그래야 기존 배치 가구 크기가 청크 리로드·재시작 후에도 유지된다
- **계단 앉기** `sit/`(StairSitManager) — 빈 ItemStack ItemDisplay 좌석을 **클릭 시점에만** 스폰, 하차 즉시 제거(계단당 상시 엔티티 0)
- **자연회복 너프** `survival/RegenManager` — 난이도 평화로움 + SATIATED/REGEN 회복 취소, **60초당 1hp**만. 실질 회복은 체력포션(DishSpecs `PURPOSE_HEAL`). MAGIC/MAGIC_REGEN은 통과. ★**Multiverse-Core가 onEnable에 자기 worlds.yml 난이도(easy)를 재적용**해 덮어쓴다 → 부팅 루프를 1틱 지연 + WorldLoadEvent MONITOR로 이후 로드 월드(길드섬 등)까지 계속 강제
- **컷씬** `cutscene/`(BoatArrivalCutscene·IntroChatFilter) — 튜토리얼 3막 입항 컷씬. 설계 전거 [tutorial-cutscene.md](tutorial-cutscene.md). **기존 배 시스템 미사용**(위 「배」 행의 ShipMover 死코드 사유 참조)
- **VIP 구독** `subscription/`(SubscriptionManager·SubscriptionCommand·DiscordCommand) — 결제 권위는 **Oracle PostgreSQL**, 플러그인은 내부 Bearer 토큰으로 조회/연결코드/수동지급만 요청. ★**API 토큰은 서버 config.yml에만** — PlayerData·채팅에 절대 기록 금지. 관련 디렉터리 `vip-billing/`
- **추천(투표) 보상** `vote/`(MineListVoteRewardManager 외) — VotifierPlus의 MineList.kr 추천 신호 → 추천코인. 마인리스트는 **at-least-once** 전송이라 "추천 받은 날짜"를 PlayerData에 영속해 같은 날짜 재전송은 거절. 코인+영수증을 **함께 저장하고 실패 시 메모리까지 롤백**
- **스탯 GUI** `stats/StatsGui` — `/능력치` 6행 54칸 read-only 집계뷰(레벨+부품5+낚싯대강화+도핑+환경 합산 → 12스탯 아이콘). 스탯.sk 완전 이관
- **중앙 도움말** `help/HelpManager` — `/<명령> 도움말|help|?|ehdnaakf` 을 PlayerCommandPreprocessEvent에서 가로채 큐레이팅 도움말 출력. 등록된 게 없으면 통과
- **진단** `diagnostics/PacketBlackbox` — 아래 「클라이언트 크래시 자동감지」 참조. ★ProtocolLib은 softdepend라 **존재 확인 후 참조 필수**
- **기타 잡동사니** `misc/`(27파일) — 도전과제·메뉴 외에 금지템(BannedItem*)·쓰레기통·아이템청소·인벤보기·카메라툴·사거리툴·쉐이더 안내·맵보호(MapProtectionListener)·폭발/드래곤알 가드·워프·스폰·팁(TipManager)·설정GUI(SettingsGui)·대장간허브(SmithyHubGui)·어드민(AdminManager)
- **배 부속** `listener/`(PlayerInteractListener·ShipEntityListener·ChunkListener) · `persistence/`(ShipSerializer·JsonShipStorage) · `player/PlayerStateManager`(탑승중인 배 추적) · `selection/`(SelectionManager·SelectionRegion, pos1/pos2 영역선택) · `task/ShipTickTask`

## 코드 컨벤션
- 명령어·UI 텍스트는 한글
- **★명령어는 `plugin.yml`이 아니라 런타임 등록이다** (2026-08-14 명문화). `plugin.yml`에 있는 건 **`ship` · `textride` · `bgm` 딱 3개**뿐이고, 나머지 **177개**는 `BlockShipPlugin.java`에서 `getServer().getCommandMap().register("blockship", <Command 객체>)` 로 등록한다.
  - 새 명령 만들 때: `org.bukkit.command.Command`를 상속하고 생성자에서 `super("한글명")` + `setDescription` + `setAliases(...)` + (OP면) `setPermission("blockship.admin")` → `BlockShipPlugin`에서 `cmdMap.register` 한 줄 추가. **plugin.yml은 건드리지 않는다.**
  - 표본: `sit/StairSitCommand` (짧고 별칭·tabComplete 규약을 다 갖춘 모범 사례)
  - **전체 명령 목록을 알고 싶으면 `grep -n 'cmdMap.register' BlockShipPlugin.java`** — 문서의 「주요 명령어」는 큐레이팅이라 전수가 아니다.
- **명령어 별칭 규칙 → 전역 훅이 강제** (`~/.claude/hooks/guard-security.py`, 두벌식 변환·초성 검출 내장): 한글 플레이어 명령엔 영타 별칭(두벌식) 부여, 자주 쓰는 건 초성도(선택). **초성 별칭을 달면 그 초성의 영타(영키보드 로마자)도 함께** 부여(예 ㅅㅍ→tv·ㅅㅈ→tw·ㅅ→t, 한/영 안 바꿔도 먹히게 — 단 1~3자라 충돌 주의). **OP 전용 명령(setPermission blockship.admin)엔 영타·초성 별칭 금지** — 위반 시 훅이 경고. (구 CLAUDE.md의 매핑표·초성 예시는 훅으로 이관됨)
- **탭 자동완성 필수** (OP 전용 명령어는 제외): 인자가 있는 모든 명령어에 TabCompleter 구현
  - 인자가 **플레이어 닉네임**이면: 접속 중인 플레이어 이름 목록
  - 인자가 **숫자 (금액/수량/레벨 등)**이면: 자동완성 목록 **넣지 않음**. 대신 `<금액>`, `<수량>` 같은 도움말 텍스트만 표시
  - 인자가 **고정 선택지** (등급, 타입 등)이면: 가능한 값을 모두 나열
  - 자동완성 없이 명령어만 만드는 것은 금지

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
- 잠그는 법: 상자·통·화로·마법부여대 등에 표지판을 붙이면 자동으로 `[lock]` + 본인 이름 각인. 다른 글자를 적으면 장식 표지판으로 남는다(자동잠금 회피구).
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
> **큐레이팅 목록이다 — 전수 아님.** 실제 등록은 **177개**이고 권위는 `BlockShipPlugin.java`의 `cmdMap.register` 호출이다(위 「코드 컨벤션」 참조). 여기 없다고 없는 명령이 아니다.

- `/레벨` `/장비` `/강화` `/칭호` `/부품상점` `/판매` `/작물` `/능력치` `/메뉴`
- `/도감` `/마켓` `/마켓등록 <가격>` `/수표 <금액>` `/잠수` (잠수대 토글 — 10분 방치 시 자동)
- `/상자잠금` (섬/길드섬 컨테이너 자물쇠 — 잠그는 건 표지판, 이 명령은 정보·명단수정·해제)
- `/콤보` (조회=일반, `/콤보 <n>` 설정만 op) · `/낚시테스트 [등급]` `/카메라툴` (op)
- `/ship create/destroy/save/spawn/edit` (배)
- **추가분(2026-08-14 반영)**: `/채집` `/카지노` `/이모트` `/버스커` `/길찾기` `/우편함` `/도전과제` `/통계` `/구독` `/디스코드` `/추천` `/추천보상` `/말대여` `/브금` `/계단앉기`(의자) `/도개교` `/드릴` `/섬` `/플라이` `/자동심기` `/낚시대회` `/보물상자` `/이무기`·`/심해전왕` `/짚라인` `/조합대` `/재료제작` `/수리` `/분해` `/거래` `/우편함` `/설정` `/화면` `/팁` `/쓰레기통` `/접속시간`
- **OP 추가분**: `/엠블럼` `/가구크기` `/사거리툴` `/쉐이더` `/랜덤블럭10` `/스탯관리` `/퀘스트관리` `/도감관리` `/npc관리` `/금지템` `/매크로의심` `/초음파탐지기` `/지역이동` `/데이터리로드`
- `/지역 생성/삭제/목록/정보/설정/바이옴/파티클/리로드` (Java, op)
- `/날씨설정 <지역|전역> <날씨|해제>` (Java, op) — 비,뇌우,태풍,안개,모래바람,눈보라,열대야,땡볕
- **중요**: 서버 최초 설정 시 `/gamerule doWeatherCycle false` 필수 (MC 자체 날씨 비활성화, 우리 WeatherManager가 제어)

## 밸런스 핵심 수치
- **등급업 캡 30%**, 크리배율 캡 80%, 슈퍼크리 2%
- **장비 경험치 보너스**: S풀세팅 +330% (장비가 성장 속도 좌우)
- **Lv.60**: G등급+S장비 해금 | **Lv.70**: 엔드게임 진입 (~46시간)
- **Lv.100**: 하드코어 (~517시간)
- 상세: balance.md 참조

## BlockShip Java 플러그인 (= 게임 로직 전부)
> 섹션 제목이 오래 「배 + 칭호」였는데 **한참 전에 틀린 말이 됐다** — 지금은 낚시·채집·채굴·요리·카지노·길드·섬·보스·텔레메트리까지 전부 이 플러그인 하나다(70패키지/359파일).

- 소스(Mac): `/Users/user/development/blockship-plugin/`
- 소스(GitHub): `wsi1212/blockship-plugin` (**private**). 맥이 없는 세션은 `git clone --depth 1` 로 받아서 읽는다 — 코드 대조 없이 이 문서만 믿고 작업하지 말 것(문서가 드리프트한다).
- 빌드: `cd /Users/user/development/blockship-plugin && ./gradlew build`
- 빌드 환경: **Gradle 9.0** + paperweight-userdev **2.0.0-beta.21** + shadow 9.0.0-beta4, `paperDevBundle("1.21.11-R0.1-SNAPSHOT")` (아래 「MC/Paper 버전」의 드리프트 경고 참조)
- 배포: `cp build/libs/BlockShip-1.0.0-SNAPSHOT.jar /Users/user/Library/Application\ Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/`
- **⚠️ 배포 후 서버 풀 재시작 필수** — `/plugman reload`나 실행 중 jar 덮어쓰기는 lazy-load CNFE로 부분 고장 유발(금지). jar 변경은 모아서 한 번에 재시작.
  - **★jar만 올리고 재시작을 미루는 것도 금지** — 중간 상태 자체가 고장이다. 2026-08-03 prod 사고: jar 교체 후 재시작 없이 방치 → `NoClassDefFoundError: WeatherManager$WeatherChoice`로 `/칭호`·계단앉기 등 전방위 고장(3시간 뒤 인지).
  - 3중 방어가 걸려 있다: ① 에이전트 훅 `ops/hooks/guard-live-jar.py` (Claude Code+Codex 양쪽, plugins/ **루트**에 jar 쓰기 차단 — `plugins/<플러그인폴더>/` 데이터는 허용) ② `deploy-blockship.sh`가 JSON 검증 통과 **후**에만 jar 업로드 + dev도 자동 재시작 ③ prod `~/mcserver/scripts/jar-guard.sh` (cron 2분, jar mtime > 서버 시작시각이면 Discord 알림 + 자동 재시작, 30분 쿨다운).
  - 우회하지 말고 `~/deploy-blockship.sh`(즉시) / `~/stage-blockship.sh`(지연, staging/)를 쓸 것.
- 빌드+배포 한줄: `cd /Users/user/development/blockship-plugin && ./gradlew build && cp build/libs/BlockShip-1.0.0-SNAPSHOT.jar "/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/"`
- 이후 **서버 풀 재시작** (dev=`~/dev-mc.sh restart` — RCON 25575, **feather 미사용** / prod=`sudo systemctl restart mcserver`)

### 맥이 아닌 세션에서 게임 코드 보기 (웹·모바일 = Claude Code on the web / 원격 컨테이너)
> 2026-08-14 신설. **"코드가 여기 없다"에서 멈추지 말 것** — 안 붙어 있는 것이지 막힌 게 아니다. 실제로 이 함정에 한 번 빠졌다.

- 원격 세션은 **세션에 붙은 리포만** 클론된 상태로 뜬다. 시작 시점 스코프가 `barkan-fishing-server` 하나면 플러그인 소스는 디스크에 없다. CLAUDE.md의 맥 경로(`/Users/user/development/...`)도 당연히 없다.
- 절차 (툴 3번이면 끝):
  1. `list_repos` — 계정이 접근 가능한 리포 확인 (`wsi1212/blockship-plugin`이 여기 뜬다)
  2. `add_repo {owner: wsi1212, repo: blockship-plugin}` → 응답이 시키는 대로 **`git clone --depth 1 <url> /workspace/blockship-plugin` 을 인라인으로 딱 한 번** (서브에이전트·병렬 금지 — 같은 리포 동시 2개면 429)
  3. `register_repo_root` — 그 리포의 CLAUDE.md/스킬을 다음 턴에 로드
- **★private 리포는 사전 확인으로 판단하면 안 된다.** `curl`·`gh repo view`·`git ls-remote`로 미리 찔러보면 **실재하고 권한이 있어도 404**가 뜬다(비인증 요청이라). 그 404를 보고 "없네" 하고 `add_repo`를 건너뛰는 게 정확히 위에서 말한 함정이다. 그냥 `add_repo`를 호출하고 **서버 응답**으로 판단할 것.
- **컨테이너는 일회용이다** — 비활성 상태가 이어지면 회수되고 `/workspace/` 클론도 같이 사라진다. 세션마다 위 절차를 다시 밟아야 하고, 남길 게 있으면 **반드시 커밋·푸시**해야 한다.
- shallow 클론이라 `git log`/`blame`/`bisect`가 필요하면 그때 `git -C /workspace/blockship-plugin fetch --unshallow`.
- ⚠️ 원격 세션에서 **할 수 없는 것**: 맥 전용 작업(리소스팩 배포 `~/deploy-rp.sh`, dev 서버 `~/dev-mc.sh`, MCP 의존 작업, 크롬 제어). 빌드도 여기서 하지 말 것 — 검증되지 않은 jar이 배포 경로에 섞이면 안 된다(위 「배포 후 서버 풀 재시작 필수」).

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
- **유저 데이터(`world/` 등)는 환경별 별개** — sync 금지!
- 코드(jar, 설정)만 dev → prod 동기화
- **dev 코드 배포 한 줄**: `~/deploy-dev.sh` (BlockShip 빌드 → dev plugins/ 복사 → dev-mc.sh restart 자동)
- **⚠️ dev 기동 느림(~83s, 타임아웃 90s 아슬아슬)**: 타임아웃 떠도 실패 아님(그냥 느림), 몇 초 더 기다리면 뜸. 곧바로 재시작하면 뜨는 중인 인스턴스가 `world/session.lock`을 잡은 채라 새 인스턴스가 죽고 **좀비 java 누적**(락만 잡고 25565 미리슨) — 감지: `ps aux|grep paper-1.21.11.jar` 2개 이상. 해결: `pkill -9 -f paper-1.21.11.jar` → 락 해제 확인 → `dev-mc.sh start` 1회.
- **prod↔dev 데이터 동기화(수동, 기본 꺼짐)**: `~/mc-sync/mc-sync.sh` (launchd 자동 sync는 2026-07-05 해제 — dev의 플러그인 편집이 매일 덮여 유실된 사고 이후 수동 전환). `DATA_PATHS` 비어있어 **플러그인 데이터는 sync 안 됨**, 월드만 prod→dev 미러. `--dry-run`으로 미리 확인.

### 자동 sync (옵션 C)
**BlockShip Java plugin** — 빌드 후 배포 스크립트
- 위치: `~/deploy-blockship.sh`
- 한 줄 실행: `~/deploy-blockship.sh`
- 동작: 로컬 빌드 → SCP로 오라클 plugins/ 업로드 → SSH로 **`systemctl restart mcserver` (전체 재시작)**. ★plugman reload 아님(위 라인 100 규칙대로 금지 — 클래스로더 손상). 접속자 없을 때 실행 권장. = **즉시 배포**.
- **지연 배포(스테이징)**: `~/stage-blockship.sh` — 빌드 후 오라클 `~/mcserver/staging/`에 jar만 올리고 재시작 안 함 → **매일 06:00 KST 데일리 유지보수 때 자동 적용**(Mac 꺼져있어도 미리 올려두면 됨). 설정 JSON은 `staging/BlockShip/`에 두면 같이 반영. 무인기간 배포에 적합. 적용 시 구 jar는 `backups/deployed-jars/`에 자동 백업(롤백용). ★자동배포=미검증 jar도 그대로 적용되니 dev 테스트 후 스테이징할 것.

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

### 자동 백업 (오라클 cron, 시각=UTC / KST=+9h) — 2026-07-24 오프사이트 DR 전면 개편
**2겹 백업**: 로컬(빠른 되돌리기) + 오프사이트(인스턴스 사망 대비 DR). 스크립트는 박스 `~/mcserver/scripts/`.
- **오프사이트 → Oracle Object Storage 버킷 `mc-backups`** (instance principal 인증=박스에 OCI키 없음, 버전관리 ON):
  - 19:00 `offsite-backup.sh` — BlockShip 폴더 전체(playerdata + 라이브 JSON) → `blockship/`, 원격 30개
  - 20:30 `offsite-worlds.sh islands` — guild_world+island_world → `islands/`, 원격 5개
  - 1·15일 22:00 `offsite-worlds.sh main` — world계열+flatroom+mine → `world/`, 원격 2개(격주)
- **로컬 → `~/mcserver/backups/`** (`local-backup.sh <main|islands>`, 파일명 접두어 `localmain-`/`localislands-`):
  - 20:00 main(본월드) 매일 3개 / 20:10 islands 매일 7개
  - 21:00 구 `playerdata-*.tar.gz` prune(자동소멸, 신규생성 없음)
- 모든 백업: 백업 전 tmux `mc`에 `save-all flush`(스냅샷 일관성). **알림**: 실패=즉시 개별 🔴, 성공=상태파일(`.backup-status`)에 누적 → `nightly-restart.sh`(cron 21:00 UTC=06:00 KST, "데일리 유지보수")가 **①staging 자동배포 ②무조건 재시작 ③데일리 리포트** 🌅(배포결과+백업 성공목록+헬스)로 하루 1회 통합 발송(노이즈 최소화). 재시작 사전예고는 `restart-warning.sh <30|10|5|1>`(각각 05:30/05:50/05:55/05:59 KST 별도 cron, 접속자 0명이면 조용히 스킵)이 담당 — nightly-restart.sh 자체는 재시작 직전 즉시 알림 1회만. ★그래서 격주 본월드 오프사이트는 20:45로 당겨 리포트 전에 끝냄. PREVIEW=1로 발송·재시작·배포 없이 리포트 미리보기 가능. webhook=`~/mcserver/scripts/discord-webhook.url`.
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
- `~/mcserver/scripts/crash-watch.py` (cron `*/2`, flock, 상태 `.crash-watch-state.json`에 오프셋/최근접속시각/알림쿨다운 영속): 로그에서 접속↔`lost connection` 페어링, 짧으면 Discord ⚡알림(위치 포함). 같은 유저 재알림 쿨다운 10분.
- 실전검증(2026-07-27 마리/잉그리드 오진 사고): 과거 7건의 lost connection 중 실제 급끊김(크래시성) 6건을 정확히 잡아냄, 정상 3분 세션 뒤 끊긴 1건은 올바르게 제외.
- ★진짜 원인은 ViaVersion/ViaBackwards가 최신 클라(26.2) 미지원 낡은 스냅샷(5.11.1-SNAPSHOT)이었던 것으로 판명 — 정식 5.11.0(1.8~26.2 지원)로 교체 후 해결. NPC 모델부착(NpcAnimator)은 무관했음(오진, 원복 완료). 향후 이런 "클라 최신버전 vs Via 구버전" 드리프트가 재발 원인 1순위. 수정 전/후 로그 대조로 해결 검증 완료(수정후 정상 5분+ 세션 확인).
- **패킷 블랙박스**(`com.blockship.diagnostics.PacketBlackbox`, ProtocolLib): 급끊김(15초 이내)이면 직전 엔티티 패킷(ENTITY_METADATA·EQUIPMENT·SPAWN_ENTITY·ENTITY_DESTROY) 40개를 `plugins/BlockShip/packet-blackbox/`에 덤프. crash-watch.py가 찾아서 Discord에 **파일 첨부**로 자동 전송(멀티파트, payload_json+file). 실전 검증 완료(3초 급끊김 테스트→덤프→Discord 첨부 확인).

### 무인운영 자동화 추가분 (2026-07-24, 군입대 대비 자가복구 시리즈)
- `~/mcserver/scripts/nightly-restart.sh` (cron 21:00 UTC=06:00 KST): staging 자동배포+**무조건** `systemctl restart`(누수 정리, 접속자 있어도 실행)+디스코드 데일리 리포트. 사전예고(30/10/5/1분 전 인게임 방송)는 `restart-warning.sh`가 별도 cron으로 담당(2026-07-27 신설).
- `~/mcserver/scripts/disk-guard.sh` (매시간): `df /` 사용률 85%⚠️경고 / 92%🔴면 가장 오래된 로컬 백업부터 삭제해 88% 아래로 확보(★라이브 데이터·오프사이트는 절대 안 건드림).
- `~/mcserver/scripts/heartbeat.sh` (cron 5분): MC 포트 살아있으면 healthchecks.io로 핑 → 박스 자체가 죽거나 cron이 멈추면 **박스 밖에서** 침묵 감지, 25분 무응답 시 디스코드 알림(데드맨 스위치, 온박스 워치독의 사각 커버).
- **`~/mcserver/scripts/fetch-staging.sh` (cron `*/15`, 2026-08-14 가동)**: GitHub Release → `staging/` **당겨오기**. 방향이 핵심이다 — 폰/맥이 prod에 밀어넣는 게 아니라 prod가 당겨오므로 **폰에 SSH 키가 없어도, 맥이 꺼져 있어도 배포가 돈다.** 전제: Actions가 **수동 promote(`workflow_dispatch` + `promote=true`)일 때만** Release를 만든다 → "최신 Release 존재" = "사람이 승격을 눌렀다". ★push마다 Release가 생기게 바꾸면 이 전제가 깨지니 금지. 토큰 `~/mcserver/.github-token`(fine-grained PAT, contents:read, 600).
  - 무변화면 **로그도 안 남긴다**(*/15 × 96줄/일이면 진짜 사건이 묻힌다). 404=아직 Release 없음(정상, 조용히 exit 0) / 401·403=진짜 실패만 🔴 알림.
  - ★**PAT 만료가 조용한 사고 지점** — 만료되면 배포가 그냥 안 온다(서버는 멀쩡). 만료일 관리 필요.
- **`~/mcserver/scripts/rollback-jar.sh` (2026-08-14 신설, 수동 전용)**: 깨진 jar 롤백을 한 줄로. `list`(후보+라이브 sha256+staging 대기, 무해) / `dry` / `yes` / `yes to <파일>`. **하이픈 없이 쓴다** — 모바일 키보드가 `--`를 대시로 바꿔 안 먹은 실측 사례가 있어 en/em dash도 정규화한다. 보존→교체→**staging 비움**→`.fetch-staging-state` 초기화→재시작→부팅확인→알림. ★staging을 안 비우면 다음날 06:00에 깨진 jar이 재적용된다(그래서 스크립트로 묶었다).
- 로그: `backups/watchdog.log`(프리즈워치독) · `backups/ops.log`(nightly/diskguard/**fetch-staging/rollback**) · `offsite.log` · `local.log`. ★운영 로그는 `backups/` 에 모인다 — 새 스크립트가 `scripts/ops.log`로 쓰면 장애 때 한쪽만 보게 된다.
- 잔여 리스크(인지함, 미자동화): 박스 자체 재구축(결제 필요, 유저 몫) / 기능적 플러그인 고장(서버는 살아있는데 게임 로직만 깨짐 — RCON 헬스체크로 감지 불가) / 손상 데이터가 백업을 덮는 경우(버전관리+보관기간으로만 완화) / **PAT 만료** / **리소스팩·MCP 의존 작업은 여전히 맥 전용**.

### Resize 자동 재시도 (백그라운드)
- 위치: `~/oracle-auto-retry/resize-retry.sh`
- 동작: 현재 사양보다 큰 자리 나는 대로 자동 resize 시도 (목표 4/24)
- 로그: `~/oracle-auto-retry/resize-retry.log`
- 성공: `~/oracle-auto-retry/SUCCESS-RESIZE.txt` 생성 + macOS 알림

## 체스 (별도 플러그인 — BlockShip 아님)
- 소스: **`~/development/barkan-chess`** / GitHub `wsi1212/barkan-chess`(private). 2026-08-11 BlockShip에서 분리(결합도 0 — 순수 Bukkit/Adventure).
- 원저자가 **컴파일된 jar만** 주므로 소스는 vineflower 역컴파일 복원본이다. **배포 전 `tools/gate.sh <업스트림.jar>` 필수** — ①업스트림 바이트코드 대조 ②랜덤 자가대국 퍼징(무한루프/예외). 2026-08-10 `hasBattery` 역컴파일 왜곡으로 무한루프→Paper 워치독이 prod를 죽인 사고 재발 방지책.
- 데이터: `plugins/BarkanChess/`(config.yml=테이블·엔진, skins/preferences/achievements/decks/player-stats/variant-stats.yml). 말 모델은 **메인 리소스팩**에 포함(PAPER `custom_model_data` 21001~22301, `assets/minecraft/items/paper.json`).
- `/체스`(cp) — 참가/솔로/AI/퇴장/스킨/규칙/덱/증강/도전과제/전적, op: 생성·제거·테이블·소환·평가·엔진탐지·변형통계·리로드. Stockfish는 dev `/opt/homebrew/bin/stockfish`, prod `/usr/games/stockfish`.

## 리소스팩
- **소스 위치(★2026-06-06 이후, Downloads 경로는 낡음): `~/development/barkan-resourcepack`** — `~/Downloads/barkan-resourcepack/`은 더 이상 존재하지 않음(TCC가 Downloads/Desktop 재귀읽기 차단해서 이동함).
- GitHub: `https://github.com/wsi1212/minecraft-fish-resource-pack` (release `latest`에 메인팩 `barkan-resourcepack.zip`+CraftEngine 가구팩 `barkan-furniture.zip` 2개 자산 공존 — `gh release delete` 절대 금지, `--clobber` 업로드만)
- 서버 자동 적용: `server.properties`에 GitHub Releases URL+SHA1 설정됨 (`require-resource-pack=true`)
- **배포: `~/deploy-rp.sh` 실행 한 줄** (zip 생성 → GitHub Release 업로드 → SHA1 갱신 → server.properties 업데이트) → 서버 재시작하면 접속자에게 자동 적용. zip 파일명은 반드시 `barkan-resourcepack.zip`.
- **커스텀 사운드**: `assets/barkan/sounds.json`에 등록, `assets/barkan/sounds/weather/*.ogg`에 파일 배치
  - ogg (Vorbis) 형식만 지원, wav→ogg 변환: `ffmpeg -i input.wav -c:a libvorbis -q:a 5 output.ogg`
  - 페이드아웃: `ffmpeg -i input.wav -t 19 -af "afade=t=out:st=16:d=3" -c:a libvorbis -q:a 5 output.ogg`
- 상세: [resourcepack.md](resourcepack.md)
