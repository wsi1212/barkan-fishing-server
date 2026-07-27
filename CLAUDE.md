# Fish - 바르칸 열도 낚시 서버

## 프로젝트 개요
마크 서버용 종합 낚시 게임. **Paper 1.21 + Java 21.** 모든 게임 로직은 BlockShip 자바 플러그인(`/Users/user/development/blockship-plugin/src/main/java/com/blockship/`)에 기능별 패키지(`fishing/` `enhance/` `parts/` `quest/` `npc/` `ferry/` `region/` `market/` `economy/` `profile/` `ranking/` `mining/` `guild/` `inn/` `portal/` `island/` 등)로 구현돼 있다.
상세 설계: [design.md](design.md) | 수치 밸런스: [balance.md](balance.md) | 스토리: [story.md](story.md)

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
| **판매** | `economy/SellCommand`·`SellGuiListener` | 품질배율 0.3~1.0, 신선도 감소 |
| **칭호** | `title/` (TitleManager·TitleLogic·FishDisplayManager) | TextDisplay(addPassenger), 채팅 포맷 |
| **퀘스트** | `quest/` (QuestManager·QuestGui·QuestCatalogGui) | 일일/주간/메인, 쉬운건 타이틀 표시 |
| **NPC/대화** | `npc/` (NpcManager·NpcDialogueManager, data/) | NPC 우클릭 대화, 퀘스트 수락/완료 |
| **아이스박스** | `economy/IceboxGui` | 물고기 보관함 (9단계, 신선도 보존) |
| **페리** | `ferry/FerryManager` | 지역간 자동 이동 (노선, 요금, 보스바) |
| **지역** | `region/RegionManager` (RegionData·RegionTracker·RegionCommand) | Java 데이터(regions.json) |
| **날씨** | `region/WeatherManager` (WeatherCommand·WeatherInfoCommand) | 지역별 독립 날씨, 파티클, 사운드, 시야 제한 |
| **사이드바** | `sidebar/SidebarManager` | 스코어보드 HUD (레벨, 돈, 위치, 환경, 콤보) |
| **배** | `ship/` (ShipManager·ShipFactory·ShipMover) + `model/` + `command/ShipCommandManager` + `editor/ShipEditor` | BlockDisplay+Shulker, 프리셋 3종 |

**기타 시스템 위치**: 도감 `dex/`·`collectible/` · 마켓/거래 `market/`·`trade/`(SalePostManager·TradeManager) · 길드 `guild/`(GuildManager·IslandBuilder) · 섬 `island/`(IslandManager·IslandProtectionListener) · 프로필 `profile/`(ProfileGui·SkinRenderer) · 랭킹 `ranking/RankingManager` · 통발 `trap/`(TrapManager·TrapSpecs) · 특수작물 `crop/`(CropManager·CropSpecs, 요리재료·섬한도·BlockShip네이티브 ItemDisplay) · 요리 `cooking/`(DishSpecs·CookingManager·CookingGui, 먹기버프+제출+판매 3용도, 요리사NPC 주방=대장간분리) · 짚라인 `zipline/` · 스킬 `skill/SkillManager` · 제작 `crafting/`(RecipeLoader·MaterialLoader) · 광질모자 `mining/` · 여관 `inn/` · 포탈 `portal/` · 물텔포 `water/` · 캐시샵 `economy/CashShopGui`·`CashEffectManager` · 돈·수표·송금 `economy/`(MoneyCommand·CheckCommand·TransferCommand)·`playerdata/MoneyBridge` · 스크롤 `scroll/` · 잠긴문/열쇠 `door/`(LockedDoorManager — 아래 「잠긴문/열쇠 규약」 필독) · 잠수(AFK) `afk/`(AfkManager — 방치 10분→잠수대 월드 afk_world 자동이동, `/잠수`(wkatn·ㅈㅅ) 토글, 복귀위치=extraStrs[잠수복귀], `/잠수 설정 <초>` OP) · **데이터 영속** `playerdata/`(PlayerData·PlayerDataManager, 단일 권위) · 유틸 `util/`(Num 숫자포맷·Worlds.dimKey·ItemCodec)

## 코드 컨벤션
- 명령어·UI 텍스트는 한글
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
- `/도감` `/마켓` `/마켓등록 <가격>` `/수표 <금액>` `/잠수` (잠수대 토글 — 10분 방치 시 자동)
- `/콤보 [n]` `/낚시테스트 [등급]` `/카메라툴` (op)
- `/ship create/destroy/save/spawn/edit` (배)
- `/지역 생성/삭제/목록/정보/설정/바이옴/파티클/리로드` (Java, op)
- `/날씨설정 <지역|전역> <날씨|해제>` (Java, op) — 비,뇌우,태풍,안개,모래바람,눈보라,열대야,땡볕
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
- 배포: `cp build/libs/BlockShip-1.0.0-SNAPSHOT.jar /Users/user/Library/Application\ Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/`
- **⚠️ 배포 후 서버 풀 재시작 필수** — `/plugman reload`나 실행 중 jar 덮어쓰기는 lazy-load CNFE로 부분 고장 유발(금지). jar 변경은 모아서 한 번에 재시작.
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
- **현재 사양**: VM.Standard.A1.Flex 4 OCPU / 24 GB RAM (목표 달성, Java 힙 16G — 2026-07-07 12G→16G, Aikar ≥12G 대용량 힙 플래그. start.sh)
- **OS**: Ubuntu 24.04 ARM64
- **MC/Paper 버전**: prod 구동 = **Paper 1.21.10** (version_history.json 확인). BlockShip 빌드 타겟 = **1.21.4** (build.gradle.kts paperDevBundle 1.21.4, api-version '1.21') → **버전 드리프트 있음(작동중, Bukkit API 호환 범위 내·NMS 사용 파일 1개뿐)**. 패킷/NMS 오류 시 1순위 의심.
- **ProtocolLib 5.4.0**: 지원 명시 범위는 1.21.4–1.21.8 → prod(1.21.10)에서 부팅 시 "not yet been tested" 경고 뜸(로드·리스너 등록은 정상). dev(Mac) 버전은 별도 확인 필요 — 패킷 작업 전 양쪽 버전 대조할 것.
- **ViaVersion/ViaBackwards 5.11.0**(정식, 2026-07-27 교체 — 이전 5.11.1-SNAPSHOT 개발버전이 최신 클라(26.2) 미지원해 접속끊김 유발했음, 상세는 「클라이언트 크래시 자동감지」 참조). Hangar 다운로드: `https://hangar.papermc.io/api/v1/projects/<ViaVersion|ViaBackwards>/versions/<버전>/PAPER/download`.
- **공인 IP**: `168.107.8.107` (Reserved 예약 IP — 인스턴스 재생성에도 불변. 2026-07-24 임시 IP 134.185.113.25에서 교체. 예약IP OCID: `ocid1.publicip.oc1.ap-chuncheon-1.amaaaaaaipxk3paarwjmvgd5ii3js5qes7jmsbyh5sy2holja6x4vhdust7a`)
- **도메인**: `barkan.kro.kr` (내도메인.한국 무료 서브도메인, A레코드 → 168.107.8.107 예정)
- **SSH 키**: `~/.ssh/oracle-mc.key` (Mac 로컬)
- **SSH 접속**: `ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107`
- **OCI CLI 설정**: `~/.oci-family/config` (가족 계정용, OCI_CLI_CONFIG_FILE 환경변수로 지정)
- **서버 경로**: `~/mcserver/` (인스턴스 안)
- **Java**: Azul Zulu JDK 21 ARM (`/usr/lib/jvm/zulu21-ca-arm64`)
- **방화벽 (2계층 — 외부 접근은 둘 다 통과해야 함)**: OCI Security List(외부 관문) + iptables(박스 내부)
  - **외부 열림 포트**: `22`(SSH) · `25565`(마크) · `80`·`443`·`3000`(다른 서비스용, 예: LH cron) · icmp — OCI SL·iptables 양쪽에 존재
  - **RCON `25575`**: enabled지만 **localhost 전용** — OCI SL에 없고 iptables 기본 REJECT라 외부에서 이중 차단

### Dev / Prod 분리 (옵션 C - 하이브리드)
- **Mac** = dev: 본인이 개발/테스트하는 곳 (★**feather 미사용** — `~/dev-mc.sh start/stop/restart/cmd <명령>/log [N]`로 관리, RCON 25575 pw devtest2026. 서버파일은 옛 feather 폴더 경로에 있지만 실행/재시작은 dev-mc.sh)
- **Oracle (춘천)** = prod: 베타 유저 접속하는 운영 서버
- **유저 데이터(`world/` 등)는 환경별 별개** — sync 금지!
- 코드(jar, 설정)만 dev → prod 동기화
- **dev 코드 배포 한 줄**: `~/deploy-dev.sh` (BlockShip 빌드 → dev plugins/ 복사 → dev-mc.sh restart 자동)
- **⚠️ dev 기동 느림(~83s, 타임아웃 90s 아슬아슬)**: 타임아웃 떠도 실패 아님(그냥 느림), 몇 초 더 기다리면 뜸. 곧바로 재시작하면 뜨는 중인 인스턴스가 `world/session.lock`을 잡은 채라 새 인스턴스가 죽고 **좀비 java 누적**(락만 잡고 25565 미리슨) — 감지: `ps aux|grep paper-1.21.10.jar` 2개 이상. 해결: `pkill -9 -f paper-1.21.10.jar` → 락 해제 확인 → `dev-mc.sh start` 1회.
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
- 모든 백업: 백업 전 tmux `mc`에 `save-all flush`(스냅샷 일관성). **알림**: 실패=즉시 개별 🔴, 성공=상태파일(`.backup-status`)에 누적 → `nightly-restart.sh`(cron 21:00 UTC=06:00 KST, "데일리 유지보수")가 **①staging 자동배포 ②무조건 재시작(접속중이면 인게임 카운트다운 예고 후) ③데일리 리포트** 🌅(배포결과+백업 성공목록+헬스)로 하루 1회 통합 발송(노이즈 최소화). ★그래서 격주 본월드 오프사이트는 20:45로 당겨 리포트 전에 끝냄. PREVIEW=1로 발송·재시작·배포 없이 리포트 미리보기 가능. webhook=`~/mcserver/scripts/discord-webhook.url`.
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
- ★진짜 원인은 ViaVersion/ViaBackwards가 최신 클라(26.2) 미지원 낡은 스냅샷(5.11.1-SNAPSHOT)이었던 것으로 판명 — 정식 5.11.0(1.8~26.2 지원)로 교체 후 해결. NPC 모델부착(NpcAnimator)은 무관했음(오진, 원복 완료). 향후 이런 "클라 최신버전 vs Via 구버전" 드리프트가 재발 원인 1순위.

### 무인운영 자동화 추가분 (2026-07-24, 군입대 대비 자가복구 시리즈)
- `~/mcserver/scripts/nightly-restart.sh` (cron 21:00 UTC=06:00 KST): RCON으로 접속자수 확인, **0명일 때만** `systemctl restart`(누수 정리)+디스코드 알림. 1명 이상이면 skip.
- `~/mcserver/scripts/disk-guard.sh` (매시간): `df /` 사용률 85%⚠️경고 / 92%🔴면 가장 오래된 로컬 백업부터 삭제해 88% 아래로 확보(★라이브 데이터·오프사이트는 절대 안 건드림).
- `~/mcserver/scripts/heartbeat.sh` (cron 5분): MC 포트 살아있으면 healthchecks.io로 핑 → 박스 자체가 죽거나 cron이 멈추면 **박스 밖에서** 침묵 감지, 25분 무응답 시 디스코드 알림(데드맨 스위치, 온박스 워치독의 사각 커버).
- 로그: `watchdog.log`(프리즈워치독) · `ops.log`(nightly/diskguard) · `offsite.log` · `local.log`.
- 잔여 리스크(인지함, 미자동화): 박스 자체 재구축(결제 필요, 유저 몫) / 기능적 플러그인 고장(서버는 살아있는데 게임 로직만 깨짐 — RCON 헬스체크로 감지 불가) / 손상 데이터가 백업을 덮는 경우(버전관리+보관기간으로만 완화).

### Resize 자동 재시도 (백그라운드)
- 위치: `~/oracle-auto-retry/resize-retry.sh`
- 동작: 현재 사양보다 큰 자리 나는 대로 자동 resize 시도 (목표 4/24)
- 로그: `~/oracle-auto-retry/resize-retry.log`
- 성공: `~/oracle-auto-retry/SUCCESS-RESIZE.txt` 생성 + macOS 알림

## 리소스팩
- **소스 위치(★2026-06-06 이후, Downloads 경로는 낡음): `~/development/barkan-resourcepack`** — `~/Downloads/barkan-resourcepack/`은 더 이상 존재하지 않음(TCC가 Downloads/Desktop 재귀읽기 차단해서 이동함).
- GitHub: `https://github.com/wsi1212/minecraft-fish-resource-pack` (release `latest`에 메인팩 `barkan-resourcepack.zip`+CraftEngine 가구팩 `barkan-furniture.zip` 2개 자산 공존 — `gh release delete` 절대 금지, `--clobber` 업로드만)
- 서버 자동 적용: `server.properties`에 GitHub Releases URL+SHA1 설정됨 (`require-resource-pack=true`)
- **배포: `~/deploy-rp.sh` 실행 한 줄** (zip 생성 → GitHub Release 업로드 → SHA1 갱신 → server.properties 업데이트) → 서버 재시작하면 접속자에게 자동 적용. zip 파일명은 반드시 `barkan-resourcepack.zip`.
- **커스텀 사운드**: `assets/barkan/sounds.json`에 등록, `assets/barkan/sounds/weather/*.ogg`에 파일 배치
  - ogg (Vorbis) 형식만 지원, wav→ogg 변환: `ffmpeg -i input.wav -c:a libvorbis -q:a 5 output.ogg`
  - 페이드아웃: `ffmpeg -i input.wav -t 19 -af "afade=t=out:st=16:d=3" -c:a libvorbis -q:a 5 output.ogg`
- 상세: [resourcepack.md](resourcepack.md)
