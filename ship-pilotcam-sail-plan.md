# 배 리워크 2건: 돛 양털 축 수정 + 조종석 파일럿 캠 (작업지시서)

> 작업자: Sonnet 5 세션. 이 문서만 보고 작업 가능하도록 원인 분석·파일 앵커·구현 단계·검증·배포 절차를 전부 포함했다.
> 발주: wsi1212, 2026-06-30. 스크린샷 증거: 범선 돛(흰 양털)이 얇은 세로 슬랫들로 조각조각 잘려 보임 + 조종석 착석 시 시야가 선체에 파묻힘.

---

## 0. 환경/규칙 (필독)

- **소스**: `/Users/user/development/blockship-plugin/` (Paper 1.21.4 빌드, prod는 1.21.10에서 구동 중)
- **빌드**: `cd /Users/user/development/blockship-plugin && ./gradlew build` (`build.gradle.kts`, paperweight)
- **유저는 prod(오라클)에서 테스트 중**. dev가 아니라 **prod에 배포해야 유저 눈에 보인다.**
- **prod 배포 = jar만, stop→scp→start 순서** (실행 중 jar 덮어쓰기·plugman reload 절대 금지 — lazy-load CNFE):
  ```bash
  cd /Users/user/development/blockship-plugin && ./gradlew build -q
  KEY=~/.ssh/oracle-mc.key; H=ubuntu@134.185.113.25
  ssh -i $KEY $H 'sudo systemctl stop mcserver'
  scp -i $KEY build/libs/BlockShip-1.0.0-SNAPSHOT.jar "$H:/home/ubuntu/mcserver/plugins/BlockShip-1.0.0-SNAPSHOT.jar"
  ssh -i $KEY $H 'sudo systemctl start mcserver'
  # 부팅 확인: ssh로 latest.log에 새 "Done (" 뜰 때까지 대기 (기존 stale "Done" 줄에 속지 말 것 — 타임스탬프 확인)
  ```
  `~/deploy-blockship.sh`는 **쓰지 말 것** (dev JSON 6종을 prod에 덮어써 prod측 편집을 날림).
- **재시작은 모아서 한 번**: 두 Task를 전부 구현·빌드한 뒤 1회 배포/재시작. 재시작 전 유저에게 물어보기(접속자 wsi1212 혼자면 바로 진행 가능).
- **병렬 세션 경고**: blockship 트리에 다른 세션들의 미커밋 WIP가 다수 있다(git status에 M 파일 수십 개 — 카지노/이무기/요리 등). **jar는 트리 전체를 번들**하므로 어차피 같이 나간다(이미 그렇게 운영 중). 남의 파일을 revert하거나 커밋하지 말 것. 커밋한다면 이번 작업 파일만 선택 커밋.
- **이번 작업 직전 세션(2026-06-30)의 미커밋 변경 — 절대 되돌리지 말 것** (전부 prod 라이브):
  - `task/ShipTickTask.java`: 정지+무스로틀 시 A/D 회전 금지, DOCK_THRESHOLD=0.15, 적응형 dockLerp(f=vel/dist, clamp 0.08~0.22), DOCK_MAX_YAW=3°/틱, HUD "⚓ 정박"
  - `model/Ship.java`: applyFriction = ×0.96 − 0.006(상수항), beginDock(…,lerp)/getDockLerp
  - `ship/ShipFactory.java`: 컨트롤러 customName("blockship:uuid") 제거 — **복원 금지**(호버 시 노출 버그)
  - `command/ShipCommandManager.java`: `/배 admin spin <도>` 디버그(라이브 회전 테스트용)
- 게임 텍스트에 **볼드(§l/&l) 금지**(전역 훅이 차단), UI 텍스트는 한글. 신규 명령은 admin 서브커맨드라 영타 별칭 규칙 해당 없음.
- 봇으로 배 조종 테스트 불가(mineflayer가 getCurrentInput 발화 못함) → **최종 검증은 유저 육안**. 코드 검증은 빌드 성공 + 로직 리뷰 + (가능하면) RCON 데이터 확인까지.

---

## Task A — 돛 양털이 슬랫으로 잘려 보임 → thin축 90° 수정

### 증상
범선의 흰 양털 돛이 한 장의 면이 아니라 **얇은 세로 판자들이 틈을 두고 늘어선 모양**으로 렌더됨(스크린샷). 선체는 정상.

### 원인 (코드로 확정)
돛 양털은 BlockDisplay에 per-block displayScale로 얇게 렌더된다. 그 thin축이 잘못된 축을 향하고 있다:

1. `model/ShipBlock.java` → `autoClassify()`: `*_WOOL`이면 **무조건** `displayScale = {1f, 1f, 0.15f}` (Z-thin 고정). 돛이 X-Y 평면(가로돛)일 때만 맞는 가정.
2. `ship/ShipRotator.java` → `bakeRotation()`: 블록 좌표(`rotateCoord`)와 blockData는 90°씩 돌리지만 **`b.getDisplayScale()`을 그대로 복사** — 90°/270° 베이크 시 thin축이 따라 돌지 않음. **← 이번 증상의 직접 원인** (범선 프리셋이 베이크 회전을 거치며 깨짐).
3. `model/ShipBlock.java` → `rotated90()`: 동일 버그(displayScale 그대로 복사).

즉 scale [sx, sy, sz]에서 90°/270° 회전 시 **sx↔sz 스왑**이 빠져 있다.

### 수정 (코드 2곳 + 리페어 명령 1개)

**A-1. `ShipRotator.bakeRotation()` — q(90° 횟수)가 홀수면 scale sx↔sz 스왑**
```java
float[] sc = b.getDisplayScale();
if (sc != null && (q % 2) == 1) sc = new float[]{sc[2], sc[1], sc[0]};
// newBlocks.add(... , sc) 로 전달 (기존 b.getDisplayScale() 대신)
```

**A-2. `ShipBlock.rotated90()` — 동일 스왑**
```java
float[] sc = (displayScale != null) ? new float[]{displayScale[2], displayScale[1], displayScale[0]} : null;
```
(90° 1회 회전이므로 무조건 스왑.)

**A-3. 데이터 리페어 명령 `/배 admin sailaxis <프리셋>` 신설** — 이미 깨진 프리셋을 고치는 유일한 경로. `command/ShipCommandManager.java`의 `handleAdmin()`(약 609행, `spin` 분기 뒤)에 추가:
- `plugin.getShipStorage().loadByName(name)` → blueprint의 블록들 중 `scale != null`인 것 전부 `[sx,sy,sz] → [sz,sy,sx]` 스왑 → `plugin.getShipStorage().save(bp)`
- 블루프린트 직렬화는 `persistence/JsonShipStorage.java` (`plugins/BlockShip/ships/<이름>.json`), 블록 레코드는 `ShipBlueprint.BlueprintBlock` — **scale 필드의 정확한 형태(배열/객체)를 먼저 읽고** 스왑 코드를 맞출 것.
- 완료 메시지: `"§a'<프리셋>' 돛 축 스왑 완료 (<n>개 블록). §7/배 소환으로 재소환해 확인하세요."`
- admin 탭완성 목록(`filter(List.of("list", ..., "spin"), ...)`)에 `sailaxis` 추가, 3번째 인자는 프리셋 이름 자동완성(`getPresetNames` 재사용).

주의: **활성 배는 blueprint 수정의 영향을 안 받음** — 스폰 시점 사본이므로, 리페어 후 기존 배 제거(`/배 admin purge` 또는 destroy) 후 재소환 필요. 명령 안내 문구에 포함할 것.

주의 2: autoClassify의 고정 Z-thin은 이번엔 건드리지 않는다(신규 생성 배에서 또 틀리면 그때 이웃-휴리스틱 검토). 이번 스코프는 베이크 스왑 + 리페어.

### 검증 (Task A)
1. 빌드 성공.
2. (재시작 후, prod) `/배 admin sailaxis 범선` → 스왑된 블록 수가 돛 블록 수와 비슷한지 확인 (0개면 blueprint에 scale 필드가 없다는 뜻 → 직렬화 필드명 다시 확인).
3. 유저에게: 기존 배 제거 → `/배 소환 범선` → 돛이 한 장의 면으로 보이는지, `/배 admin spin 45`로 돌려도 돛이 선체와 같이 자연스럽게 도는지 육안 확인 요청.
4. 만약 스왑 후에도 이상하면(축이 원래 맞았을 가능성) `sailaxis`를 한 번 더 실행하면 원복된다(스왑은 대합).

---

## Task B — 조종석 파일럿 캠 (앉은 아바타 + 실플레이어는 상공 조종)

### 요구사항 (유저 원문 요지)
- 조종석에 앉으면 시야가 선체에 파묻혀 조종이 힘듦.
- 조종석에는 **앉아있는 플레이어 아바타(더미)** 가 보이고,
- **실제 플레이어는 투명 + 배 위 ~25블록 상공**에서 넓은 시야로 조종.

### 설계

```
[조종석 우클릭] → boardPilot 성공
  ├─ 아바타: 플레이어 스킨의 더미를 조종석(pilotSeatEntity)에 착석
  ├─ 실플레이어: camSeat(투명 ArmorStand, 배 중심 + Y_CAM 상공)에 addPassenger
  ├─ player.setInvisible(true) + 칭호 TextDisplay 숨김 + PDC 마커 "pilotcam"
  └─ (기존) grim exempt, pilotId 유지 → ShipTickTask 조종 로직 무변경
[하차(sneak)/퀴트/회수/파괴] → exitPilotCam() 단일 복원 함수
```

핵심 불변: **`ship.pilotId`와 `passengers`는 기존 그대로** — `ShipTickTask.processShipTick`의 `pilot.getCurrentInput()` 조종, HUD, 도킹 로직은 플레이어가 어느 좌석에 앉았는지 모름/몰라도 됨. getCurrentInput은 아무 엔티티에 탑승 중에도 동작(현 좌석 시스템 + `zipline/ZiplineManager.java:336`으로 실증됨).

### 아바타 구현 방식 결정

`plugin.yml` softdepend는 현재 `[BetterModel, ProtocolLib]` — **Citizens API 의존성 없음**. 선택지:

| 방식 | 평가 |
|---|---|
| **① Citizens API (권장)** | 서버(dev+prod)에 Citizens 설치·1.21.10 정상 구동 중. in-memory registry NPC = 진짜 플레이어 모델 + 스킨 미러 + 좌석 탑승 시 앉은 포즈 자동. 이번에 compileOnly 의존성 추가 필요 |
| ② ProtocolLib 패킷 가짜 플레이어 | ProtocolLib 5.4.0은 1.21.10 "untested"(메모리 경고: 패킷/NMS 이상 시 1순위 의심) — 스폰 패킷 리스크. 비권장 |
| ③ ArmorStand+플레이어 머리 | 품질 낮음(머리만). 최후 폴백 |

**①로 구현하되 클래스가드**: Citizens 미설치 환경에서도 아바타만 생략되고 캠은 동작하도록 (`Bukkit.getPluginManager().getPlugin("Citizens") != null` 체크 + Citizens 타입은 별도 헬퍼 클래스로 격리해 NoClassDefFoundError 방지).

빌드 설정 (`build.gradle.kts`):
```kotlin
repositories { maven("https://maven.citizensnpcs.co/repo") }
dependencies { compileOnly("net.citizensnpcs:citizens-main:2.0.35-SNAPSHOT") { exclude(group = "*", module = "*") } }
```
(버전은 리졸브되는 최신 2.0.x로; exclude 없이 의존성 지옥이 나면 exclude 추가.) `plugin.yml` softdepend에 `Citizens` 추가.

아바타 스폰 헬퍼 (`ship/PilotAvatar.java` 신설 권장):
```java
// in-memory registry — saves.yml 오염 없음, 재시작 시 자동 소멸
NPCRegistry reg = CitizensAPI.createInMemoryNPCRegistry("blockship-pilot");  // 1회 생성 후 재사용
NPC npc = reg.createNPC(EntityType.PLAYER, player.getName());
npc.data().set(NPC.Metadata.NAMEPLATE_VISIBLE, false);        // 이름표 중복 방지
npc.setProtected(true);
// 스킨: 플레이어의 현재 텍스처를 그대로 미러 (Mojang 조회 없이)
var textures = player.getPlayerProfile().getProperties().stream()
    .filter(p -> p.getName().equals("textures")).findFirst();
textures.ifPresent(t -> npc.getOrAddTrait(SkinTrait.class)
    .setSkinPersistent(player.getName(), t.getSignature(), t.getValue()));
npc.spawn(seatLoc);
pilotSeatEntity.addPassenger(npc.getEntity());               // 착석 포즈
```
리스크 노트: Citizens NPC를 armorstand 승객으로 매틱 텔포(teleportSeats)하는 조합이 desync하면 → NPC를 좌석 승객이 아니라 **teleportSeats에서 좌석과 같은 좌표로 직접 텔포 + `npc.getEntity()`에 setPose(SITTING)은 불가하므로** Citizens `SitTrait`(있으면) 또는 승객 방식 유지하되 teleport 순서 조정. 1차는 승객 방식으로 구현하고 dev에서 육안 확인.

### 구현 단계

**B-1. `model/Ship.java`**
- 필드: `private ArmorStand camSeat; private Object pilotAvatar; // NPC (Citizens 없으면 null)`
- `maxRelY()` 헬퍼: `blocks.stream().mapToInt(ShipBlock::relY).max().orElse(0)`
- `boardPilot(Player)` 변경: 기존 로직(passengers/pilotId/nametag)은 유지하되, **파일럿 캠 분기**:
  - `int camH = Math.max(25, maxRelY() + 8);` (돛대가 25보다 높으면 그 위로)
  - camSeat 스폰: invisible+marker+non-persistent ArmorStand at `center + (0, camH, 0)`, PDC에 기존 좌석과 **동일한 태그**(`blockship:seat` + ship_id) 부여 → `ShipOrphanCleaner`가 재시작 고아를 자동 청소(cleaner의 PDC 키 목록 확인해 맞출 것)
  - `pilotSeatEntity.addPassenger(p)` 대신 → 아바타를 조종석에, `camSeat.addPassenger(p)`
  - `p.setInvisible(true)` + PDC 마커(`blockship:pilotcam`=1) + 칭호 숨김(아래 B-4)
- `removePassenger(Player)` 파일럿 분기: camSeat에서 내려주고 `exitPilotCam(p)` 호출 (아바타 despawn/destroy, camSeat.remove(), setInvisible(false), 칭호 복원, PDC 마커 제거, fallDistance 0). **idempotent하게** — 이미 정리됐어도 예외 없이.
- `teleportSeats()`:
  - camSeat 텔포 추가: `centerLocation + (0, camH, 0)` (회전 무관), yaw는 ship yaw(플레이어 시점은 자유 마우스라 무관하지만 일관성).
  - 파일럿 좌석 yaw 로직 변경: 기존엔 pilot의 look yaw를 복사(`if (pilot != null) seatLoc.setYaw(...)`) — 이제 조종석 탑승자는 아바타이므로 **ship yaw**로 (아바타가 항상 뱃머리를 보게).
- `destroyEntities()`: camSeat 제거 + 아바타 정리 추가.

**B-2. `listener/ShipEntityListener.java` (`onEntityDismount`, 51행)**
- dismount된 vehicle이 **camSeat인 경우**를 기존 좌석 하차와 동일하게 처리: `ship.removePassenger(player)` 경로로 → exitPilotCam이 복원 + **갑판 안전좌표로 TP**(25블록 낙하 방지 — 기존 하차 TP 로직이 있으면 재사용, 없으면 조종석 위 1블록으로 TP + fallDistance 0).
- camSeat 식별: Ship에 `isCamSeat(Entity)` 헬퍼.

**B-3. `listener/PlayerInteractListener.java` (80행 근처)**
- `ship.boardPilot(player)` 시그니처/동작이 바뀌므로 호출부 확인만 (grant exempt 등 기존 코드 유지).
- onPlayerQuit(113행 근처 revoke 지점): `exitPilotCam` 계열 정리도 같이 (Ship 쪽 removePassenger가 불리는지 확인, 안 불리면 명시 호출).

**B-4. 칭호 숨김/복원**
- 플레이어 칭호/닉 TextDisplay는 플레이어에 addPassenger돼 있어 **상공에서 칭호만 둥둥 뜬다** → 탑승 시 숨기고 하차 시 복원.
- `title/TitleManager.java:157 removeAll(Player, titleTag, nameTag)` + 재적용 경로(textride update 핸들러가 쓰는 메서드)를 참조해 **hide/restore 쌍**을 정확히 구현. `/textride update` 서브커맨드 구현부(BlockShipPlugin)를 읽고 같은 방식으로 복원할 것. FishDisplayManager(등 물고기 자랑 디스플레이)도 `removeFromBack(207행)` 확인.
- 복원이 복잡하면(칭호 상태를 서버가 재계산 가능한지 확인) — TitleLogic에 "재적용" 진입점이 있는지 먼저 찾아보고, 없으면 하차 시 기존 칭호 갱신 명령 경로를 performCommand가 아닌 내부 호출로.

**B-5. 재시작 좀비 상태 복구**
- 파일럿 캠 중 서버가 재시작하면: 배·camSeat는 OrphanCleaner가 치우지만 **플레이어 invisible 플래그와 PDC 마커는 playerdata에 남을 수 있음**.
- PlayerJoinEvent(기존 리스너 아무거나, 예: EnhanceManager onJoin처럼 가벼운 곳 말고 **ship 관련 리스너**)에서: PDC `blockship:pilotcam` 있으면 → setInvisible(false), 칭호 복원, PDC 제거.

**B-6. 기타 정리 경로**
- `autoRecall`(ShipTickTask), `/배 destroy`, `/배 admin purge` — 전부 `ship.removePassenger` 또는 `destroyEntities`를 지나는지 확인하고, 지나면 자동 해결. 안 지나는 경로가 있으면 exitPilotCam 명시 호출.
- 승객(탑승석)은 **변경 없음** — 파일럿만 캠 적용.

### 검증 (Task B)
빌드 + 로직 리뷰 후, 유저 육안 체크리스트 (한 번에 안내):
1. 조종석 우클릭 → 자기 스킨의 아바타가 조종석에 앉아 있고, 본인은 상공 ~25블록에서 시야 확보되는지
2. W/A/S/D 조종이 그대로 되는지 (전진·회전·도킹·HUD)
3. sneak 하차 → 갑판/조종석 옆으로 안전 복귀(낙하 없음) + 투명 해제 + 칭호 복귀 + 아바타 소멸
4. 다른 플레이어(또는 봇 소환해 육안)에게 아바타가 보이고 본인은 안 보이는지 — 봇은 `~/dev-test-bot/bot.js`로 dev에서만 가능, prod는 유저 판단
5. 조종 중 재접속(강제 퀴트) → 재접 시 투명 아님, 칭호 정상
6. 배 회수(유지시간 만료)나 `/배 destroy` 중에도 상태 복원되는지
7. GrimAC 오탐 폭주 없는지 (grim exempt는 기존 grant/revoke 그대로라 정상이어야 함)

### 알려진 함정 (이 프로젝트에서 이미 겪은 것)
- **Citizens 콘솔 create는 phantom 생성** — 이번엔 API in-memory registry라 무관하지만, saves.yml은 절대 건드리지 말 것.
- ArmorStand 좌석 매틱 teleport에 승객이 유지되는 것은 현 시스템으로 실증됨(같은 메커니즘 재사용이라 camSeat도 동일).
- 아바타 NPC가 GrimAC에 걸리는 일은 없음(NPC는 검사 대상 아님).
- Citizens NPC 이름 = 플레이어 이름이어도 BlockShip NpcManager 대화 매칭(npc.json 등록 이름 기준)과 충돌 안 함. 다만 아바타 우클릭 시 Citizens 이벤트가 발생할 수 있으니, 아바타 NPC에 클릭 무시 메타를 설정하거나 NpcInteractListener에서 in-memory registry NPC는 스킵.

---

## 완료 후

1. 두 Task 모두 빌드 통과 → **한 번의 prod 배포**(stop→scp→start, 0장 규칙 준수). dev 먼저 검증하고 싶으면 `~/deploy-dev.sh`(빌드+배포+재시작) 사용 가능 — 단 유저 육안 확인은 prod.
2. 배포 후: `/배 admin sailaxis 범선` 실행(prod 콘솔 tmux 또는 유저가 인게임 op) → 재소환 안내.
3. 유저에게 검증 체크리스트 전달.
4. 유저 확인 후 blockship repo에 **이번 작업 파일만** 커밋 (Ship.java/ShipTickTask.java 등은 이전 세션 WIP와 같은 파일일 수 있음 — 파일 단위 커밋이라 이전 배 튜닝 변경이 같이 들어가는 건 OK, 배 관련이므로. 카지노/이무기 등 무관 파일은 제외).
5. 메모리 갱신: `project_ship_grim_exempt.md`(도킹/조종 메모)에 파일럿 캠 추가, 돛 축 스왑은 `project_ship_baked_hull.md`에 한 줄.

## 하지 말 것
- 항해 중 90° 스냅 회전(유저 명시 거부), 즉시 정지, 배 영속화 복원
- 컨트롤러 customName 복원 (호버 노출 버그)
- 정지 상태 A/D 제자리 회전 되살리기 (유저가 원해서 막은 것)
- `deploy-blockship.sh` 실행, plugman reload, 실행 중 jar 덮어쓰기
- prod JSON(npc.json 등) 덮어쓰기
