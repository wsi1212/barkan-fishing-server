# Fish - 바르칸 열도 낚시 서버

## 프로젝트 개요
마크 서버용 종합 낚시 게임. **Paper 1.21 + Java 21.** 모든 게임 로직은 BlockShip 자바 플러그인(`/Users/user/development/blockship-plugin/src/main/java/com/blockship/`)에 기능별 패키지(`fishing/` `enhance/` `parts/` `quest/` `npc/` `ferry/` `region/` `market/` `economy/` `profile/` `ranking/` `mining/` `guild/` `inn/` `portal/` `island/` 등)로 구현돼 있다.
상세 설계: [design.md](design.md) | 수치 밸런스: [balance.md](balance.md) | 스토리: [story.md](story.md)

## 🚫 절대 운영 안전 규칙 — 모든 에이전트 세션 공통 (2026-09-02)

- Codex·Claude를 포함한 **모든 에이전트는 prod 서버를 재시작하지 않는다.** `sudo systemctl restart mcserver`, `systemctl restart mcserver`, `ops/rp-deploy.sh prod --restart`, `~/deploy-blockship.sh`, `ops/deploy-all-prod.sh`, `nightly-restart.sh --now` 및 이와 동등한 재시작 경로를 실행 금지한다.
- 리소스팩 prod 배포는 `ops/rp-deploy.sh prod`를 **`--restart` 없이** 실행해 새 Release와 URL/SHA1만 반영한다. 접속자 확인·공지·승인 없는 운영 중단을 에이전트가 만들지 않는다.
- **매일 06:00 KST 정기 재시작은 켜져 있다 (2026-09-02 유저가 명시적으로 복구).** cron `0 21 * * * nightly-restart.sh` 가 staging 적용 + 재시작을 하고, 30/10/5/1분 전 `restart-warning.sh` 가 예고한다. 이건 «예약된» 재시작이라 위 금지의 예외다 — 에이전트가 임의 시각에 때리는 것만 금지다. 오늘 밤만 건너뛰려면 `touch ~/mcserver/scripts/.skip-nightly-once` (1회 자동 소모). 재시작 없는 점검용 `nightly-maintenance.sh` 는 파일만 남아 있고 cron 에서 빠져 있다.
- **이 금지는 훅으로 강제된다** — `ops/hooks/guard-prod-restart.py` (Claude `settings.json` + Codex `hooks.json` 양쪽 PreToolUse). 문서만으로 막던 2026-09-02 에 에이전트가 하루 6번 prod 를 재시작했다. 검산 `ops/hooks/guard-prod-restart-selftest.py`. 통과시키는 것: 조회·grep·히어독 본문·`crontab` 편집·`PREVIEW=1`·`systemctl start`(inactive 복구)·dev.
- **자동복구 가드는 켜져 있다 (2026-09-02 복구)** — `watchdog.sh`(cron `*/2`, RCON 4회 연속 무응답≈8분이면 프리즈로 보고 재시작) · `jar-guard.sh`(cron `*/2`, 라이브 jar mtime > 서버 시작시각이면 알림+재시작, 30분 쿨다운). 둘은 «사람이 정한 자가복구»라 위 금지의 예외다. 백업·디스크가드·하트비트·crash-watch·fetch-staging 은 애초에 꺼진 적 없고 06:00 작업과 무관한 별도 cron이다 — 06:00 리포트는 `.backup-status` 를 읽어 «보고만» 한다. 막아 둔 것(의도): APPLY_NOW 즉시적용 — 폰에서 승격해도 staging 까지만, 즉시배포는 dev 전용. `resourcepack-restart.sh`(호출자 없는 스텁)·`oneshot-guild-rename-gm.sh` 도 그대로 차단.
- Java/JSON 코드는 반드시 `~/stage-blockship.sh`로 `~/mcserver/staging/`에만 올린다. 운영 `plugins/` 승격은 하지 않는다.
- prod 상태가 `inactive`로 확인된 경우에만 복구 목적으로 `systemctl start mcserver`를 검토할 수 있다. `active`, `activating`, `deactivating` 상태에서는 start/restart를 추가로 호출하지 않는다.
- 이 항목은 아래의 기존 배포 설명보다 우선한다. 사용자가 이 안전 규칙을 명시적으로 변경하기 전까지 계속 적용한다.

## 기술 스택
- **Paper 1.21 + Java 21 — BlockShip 자바 플러그인이 모든 게임 시스템** (빌드: `cd /Users/user/development/blockship-plugin && ./gradlew build`, 상세는 아래 「BlockShip Java 플러그인」 섹션)

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
| **사이드바** | `sidebar/SidebarManager` | 스코어보드 HUD (레벨, 돈, 위치, 환경, 콤보) |
| **배** | `ship/` (ShipManager·ShipFactory·ShipMover) + `model/` + `command/ShipCommandManager` + `editor/ShipEditor` | BlockDisplay+Shulker, 프리셋 3종 |

**기타 시스템 위치**: 도감 `dex/`·`collectible/` · 마켓/거래 `market/`·`trade/`(SalePostManager·TradeManager) · 길드 `guild/`(GuildManager·IslandBuilder) · 섬 `island/`(IslandManager·IslandProtectionListener) · 프로필 `profile/`(ProfileGui·SkinRenderer) · 랭킹 `ranking/RankingManager` · 통발 `trap/`(TrapManager·TrapSpecs) · 특수작물 `crop/`(CropManager·CropSpecs, 요리재료·섬한도·BlockShip네이티브 ItemDisplay) · 요리 `cooking/`(DishSpecs·CookingManager·CookingGui, 먹기버프+제출+판매 3용도, 요리사NPC 주방=대장간분리) · 짚라인 `zipline/` · 스킬 `skill/SkillManager` · 제작 `crafting/`(RecipeLoader·MaterialLoader) · 광질모자 `mining/` · 여관 `inn/` · 포탈 `portal/` · 물텔포 `water/` · 캐시샵 `economy/CashShopGui`·`CashEffectManager` · 돈·수표·송금 `economy/`(MoneyCommand·CheckCommand·TransferCommand)·`playerdata/MoneyBridge` · 스크롤 `scroll/` · 잠긴문/열쇠 `door/`(LockedDoorManager — 아래 「잠긴문/열쇠 규약」 필독) · **데이터 영속** `playerdata/`(PlayerData·PlayerDataManager, 단일 권위) · 유틸 `util/`(Num 숫자포맷·Worlds.dimKey·ItemCodec)

## 코드 컨벤션
- 명령어·UI 텍스트는 한글
- **한글 명령어 영타 별칭 필수** (OP 전용 명령어는 제외): 한글→영타 매핑: ㅂ=q ㅈ=w ㄷ=e ㄱ=r ㅅ=t ㅛ=y ㅕ=u ㅑ=i ㅐ=o ㅔ=p ㅁ=a ㄴ=s ㅇ=d ㄹ=f ㅎ=g ㅗ=h ㅓ=j ㅏ=k ㅣ=l ㅋ=z ㅌ=x ㅊ=c ㅍ=v ㅠ=b ㅜ=n ㅡ=m
- **초성 별칭은 자주 쓰는 핵심 명령어에만** (선택 — 영타와 달리 필수 아님): 한글 명령어의 초성으로 짧은 별칭을 부여. 예: 섬→`ㅅ`, 상점→`ㅅㅈ`, 판매→`ㅍㅁ`, 스폰→`ㅅㅍ`, 레벨→`ㄹㅂ`. 영타 별칭과 함께 `setAliases(List.of("영타", "초성"))`에 추가한다. **모든 명령어에 달지 말 것** — 플레이어가 반복해서 치는 명령어만. 초성끼리만 충돌 검사하고, 겹치면 한쪽만 부여(예: 수표·스폰 둘 다 `ㅅㅍ` → 스폰만).
- **탭 자동완성 필수** (OP 전용 명령어는 제외): 인자가 있는 모든 명령어에 TabCompleter 구현
  - 인자가 **플레이어 닉네임**이면: 접속 중인 플레이어 이름 목록
  - 인자가 **숫자 (금액/수량/레벨 등)**이면: 자동완성 목록 **넣지 않음**. 대신 `<금액>`, `<수량>` 같은 도움말 텍스트만 표시
  - 인자가 **고정 선택지** (등급, 타입 등)이면: 가능한 값을 모두 나열
  - 자동완성 없이 명령어만 만드는 것은 금지

### NPC 닉네임 색 규칙 (2026-07-08 신설, 위반 금지)
NPC 머리 위 표시 이름의 색코드는 역할별로 통일한다. ★표시 이름은 Citizens `saves.yml`의 `name` 필드다(BetterModel/BlockShip 아님). 색만 바꾸면 BlockShip의 uncolored 이름 매칭은 깨지지 않지만, 이름 텍스트를 바꾸면 `npc.json`도 함께 바꾼다.
- 하늘색 `&b`: 기능형 NPC(길드·상점·판매·섬상점·대장간·요리사·마켓·드릴상점·페리·일퀘/주간 게시판·여관·회복·말대여)
- 초록색 `&a`: 스토리·메인·튜토리얼 퀘스트를 주는 NPC(`[Q]`, `[길잡이]`)
- 하얀색 `&f`: 대화만 하는 NPC
- `[퀘스트]` 태그는 일퀘 게시판 기능형(`&b`), `[Q]`는 대화형 퀘스트 NPC(`&a`)다.

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
- `/도감` `/마켓` `/마켓등록 <가격>` `/수표 <금액>`
- `/콤보 [n]` `/낚시테스트 [등급]` `/카메라툴` (op)
- `/ship create/destroy/save/spawn/edit` (배)
- `/지역 생성/삭제/목록/정보/설정/바이옴/파티클/리로드` (Java, op)
- `/날씨설정 <지역|전역> <날씨|해제>` (Java, op) — **날씨 목록을 여기 적지 않는다**(드리프트). `/날씨설정` 을 인자 없이 치면 WeatherManager 가 정의한 전체 목록 + 각각의 전역/지역·시간 조건을 출력한다. 지역전용 날씨는 지역 `allowedWeathers` 화이트리스트에 이름이 있어야 자동 발동한다 — 비어 있으면 OP 수동 발동만 되고 자동으로는 영원히 안 뜬다(2026-08-27 태풍·눈보라가 그 상태였다).
- **중요**: 서버 최초 설정 시 `/gamerule doWeatherCycle false` 필수 (MC 자체 날씨 비활성화, 우리 WeatherManager가 제어)

## 밸런스 핵심 수치
- **등급업 캡 30%**, 크리배율 캡 80%, 슈퍼크리 2%
- **장비 경험치 보너스**: S풀세팅 +330% (장비가 성장 속도 좌우)
- **Lv.60**: G등급+S장비 해금 | **Lv.70**: 엔드게임 진입 (~46시간)
- **Lv.100**: 하드코어 (~517시간)
- 상세: balance.md 참조

## BlockShip Java 플러그인 (배 + 칭호)
- 소스: `/Users/user/development/blockship-plugin/`
- 빌드: `cd /Users/user/development/blockship-plugin && ./gradlew build`
- 전체 prod 배포: `ops/deploy-all-prod.sh` (BlockShip/JSON/메인팩/BetterHud/CraftEngine 단일 체인)
- Java-only 즉시 배포: `~/deploy-blockship.sh` 또는 `ops/deploy-blockship.sh` (prod 정지→JAR 교체→기동)
- **⚠️ 배포 후 서버 풀 재시작 필수** — `/plugman reload`나 실행 중 jar 덮어쓰기는 lazy-load CNFE로 부분 고장 유발(금지). jar 변경은 모아서 한 번에 재시작.
  - **★jar만 올리고 재시작을 미루는 것도 금지** — 중간 상태 자체가 고장이다. 2026-08-03 prod 사고: jar 교체 후 재시작 없이 방치 → `NoClassDefFoundError: WeatherManager$WeatherChoice`로 `/칭호`·계단앉기 등 전방위 고장(3시간 뒤 인지).
  - 3중 방어가 걸려 있다: ① 에이전트 훅 `ops/hooks/guard-live-jar.py` (Claude Code+Codex 양쪽, plugins/ **루트**에 jar 쓰기 차단 — `plugins/<플러그인폴더>/` 데이터는 허용) ② `deploy-blockship.sh`가 JSON 검증 통과 **후**에만 jar 업로드 + dev도 자동 재시작 ③ prod `~/mcserver/scripts/jar-guard.sh` (cron 2분, jar mtime > 서버 시작시각이면 Discord 알림 + 자동 재시작, 30분 쿨다운).
  - 우회하지 말고 전체 변경은 `ops/deploy-all-prod.sh`, Java-only 즉시는 `~/deploy-blockship.sh`, 지연은 `~/stage-blockship.sh`를 쓸 것.
  - `ops/deploy-blockship.sh --no-restart`를 라이브 `plugins/` 대상으로 직접 실행하지 말 것. 전체 래퍼만 임시 경로를 지정해 사용한다.
  - **클라우드 세션(폰·웹)은 이 둘을 못 쓴다** — 22번 포트 egress가 원천 차단이라 SSH 자체가 불가능하다(키를 넣어도 안 되고, git SSH URL도 HTTPS로 재작성된다). 대신 **당겨오는 경로**를 쓴다: GitHub Actions `blockship-smoke.yml` 수동 실행 → `promote=true`(스모크 통과 시 Release 발행 → prod가 staging으로 당겨 06:00 적용) 또는 `apply_now=true`(Release 본문에 `APPLY_NOW` 마커 → prod가 당겨오는 즉시 적용+재시작, 최대 지연 cron `*/5`). GitHub은 셸 curl이 403이므로 MCP 도구로만 다룬다. 상세는 CLAUDE.md 「자동 sync」·스킬 `deploy-prod`.
- 전체 배포 한줄: `cd "/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Skript/scripts" && ./ops/deploy-all-prod.sh`
- Java-only 즉시 배포: `~/deploy-blockship.sh` (라이브 JAR은 정지 상태에서 교체)
- 별도 재시작을 붙이지 말 것 — 각 스크립트가 정지→교체→기동을 한 몸으로 처리한다.

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
- **인스턴스**: `minecraft-server` (ID는 retry log 참조)
- **현재 사양**: VM.Standard.A1.Flex 4 OCPU / 24 GB RAM (목표 달성, Java 힙 16G — 2026-07-07 12G→16G, Aikar ≥12G 대용량 힙 플래그. start.sh)
- **OS**: Ubuntu 24.04 ARM64
- **공인 IP**: `168.107.8.107` (Ephemeral — 인스턴스 재생성 시 변경됨)
- **SSH 키**: `~/.ssh/oracle-mc.key` (Mac 로컬)
- **SSH 접속**: `ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107`
- **OCI CLI 설정**: `~/.oci-family/config` (가족 계정용, OCI_CLI_CONFIG_FILE 환경변수로 지정)
- **서버 경로**: `~/mcserver/` (인스턴스 안)
- **Java**: Azul Zulu JDK 21 ARM (`/usr/lib/jvm/zulu21-ca-arm64`)
- **방화벽**: 22 (SSH), 25565 (마크) 열림 (iptables + OCI Security List)

### Dev / Prod 분리 (옵션 C - 하이브리드)
- **Mac (패더)** = dev: 본인이 개발/테스트하는 곳
- **Oracle (춘천)** = prod: 베타 유저 접속하는 운영 서버
- **유저 데이터(`world/` 등)는 환경별 별개** — sync 금지!
- 코드(jar, 설정)만 dev → prod 동기화

### 자동 sync (옵션 C)
**BlockShip Java plugin** — 빌드 후 배포 스크립트
- 위치: `~/deploy-blockship.sh`
- 한 줄 실행: `~/deploy-blockship.sh`
- 동작: 로컬 빌드 → JSON 검증 → dev 반영 → prod 정지 → JAR 교체 → prod 기동

**전체 변경** — `ops/deploy-all-prod.sh` 하나만 실행한다. JAR은 검증 전 원격 임시 경로에만
두고, 서버가 정지한 뒤 라이브 `plugins/`로 승격하므로 `jar-guard`의 가동 중 교체 경고가
발생하지 않는다.

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

### 자동 백업 (오라클 cron, 시각=UTC / KST=+9h)
- 19:00 UTC(04시 KST): `variables.csv` → `~/mcserver/backups/` **⚠️ 죽은 파일(Skript 제거됨, 6/4 동결) — playerdata 백업으로 교체 필요**
- 20:00 UTC(05시 KST): 월드 폴더 tar.gz → `~/mcserver/backups/` (월드만, `plugins/`는 미포함)
- 21:00 UTC(06시 KST): 오래된 백업 prune (변수 30일 / 월드 14일)
- **⚠️ 실제 플레이어 진행도 `plugins/BlockShip/playerdata/*.json`는 현재 어떤 cron 백업에도 안 들어감 — 추가 필요**

### Resize 자동 재시도 (백그라운드)
- 위치: `~/oracle-auto-retry/resize-retry.sh`
- 동작: 현재 사양보다 큰 자리 나는 대로 자동 resize 시도 (목표 4/24)
- 로그: `~/oracle-auto-retry/resize-retry.log`
- 성공: `~/oracle-auto-retry/SUCCESS-RESIZE.txt` 생성 + macOS 알림

## 리소스팩
- GitHub: `https://github.com/wsi1212/minecraft-fish-resource-pack`
- 로컬: `~/Library/Application Support/minecraft/resourcepacks/barkan-resourcepack.zip`
- 빌드 폴더: `~/Downloads/barkan-resourcepack/`
- 서버 자동 적용: `server.properties`에 GitHub Releases URL+SHA1 설정됨 (`require-resource-pack=true`)
- **자동 배포**: `~/Downloads/barkan-resourcepack/deploy.sh` 실행 한 줄로 전체 자동화
  - ZIP 생성 (로컬+배포) → Git 커밋+푸시 → GitHub Release 업로드 → SHA1 갱신 → server.properties 업데이트
  - 서버 재시작하면 접속자에게 자동 적용
- **수동 배포 절차** (deploy.sh 못 쓸 때):
  1. `~/Downloads/barkan-resourcepack/` 내 파일 수정
  2. `cd ~/Downloads/barkan-resourcepack && zip -r /tmp/barkan-resourcepack.zip . -x ".*" -x "deploy.sh"`
  3. `gh release delete latest --repo wsi1212/minecraft-fish-resource-pack --yes`
  4. `gh release create latest /tmp/barkan-resourcepack.zip --repo wsi1212/minecraft-fish-resource-pack --title "Latest"`
  5. `shasum /tmp/barkan-resourcepack.zip` → server.properties의 `resource-pack-sha1` 업데이트
  6. 서버 재시작
- **커스텀 사운드**: `assets/barkan/sounds.json`에 등록, `assets/barkan/sounds/weather/*.ogg`에 파일 배치
  - ogg (Vorbis) 형식만 지원, wav→ogg 변환: `ffmpeg -i input.wav -c:a libvorbis -q:a 5 output.ogg`
  - 페이드아웃: `ffmpeg -i input.wav -t 19 -af "afade=t=out:st=16:d=3" -c:a libvorbis -q:a 5 output.ogg`
- 상세: [resourcepack.md](resourcepack.md)

## Codex 이식 메모

- 이 프로젝트의 Codex 전용 실행 설정은 `.codex/config.toml`, `.codex/hooks.json`, `.codex/hooks/`에 있다.
- 상세 운영 규칙과 최신 변경 기록은 `CLAUDE.md`에도 남아 있으므로, 이 문서에 없는 서버 운영·워치독·클라이언트 크래시 대응 세부사항이 필요한 작업에서는 `CLAUDE.md`의 해당 절을 함께 읽는다.
- Claude 전용 명칭은 Codex 대응물로 해석한다: `CLAUDE_PROJECT_DIR`는 현재 프로젝트 루트, `claude-in-chrome`는 사용 가능한 브라우저 제어 도구, `mcp__minecraft-ai-builder__*`는 `minecraft-ai-builder` MCP 서버 도구다.
