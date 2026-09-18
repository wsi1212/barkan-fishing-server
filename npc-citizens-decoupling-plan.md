# NPC 런타임에서 Citizens 원본 Player 엔티티 걷어내기 — 조사 + staging 구현 계획

작성 2026-09-18. **prod 변경·재시작 없음.** 이 문서의 모든 판정은 소스/바이트코드/prod 읽기 전용 조회 실측이다.

---

## 0. 한 줄 결론

**된다.** BetterModel 은 `BaseEntity.of(BukkitAdapter.adapt(entity))` 로 **아무 Bukkit 엔티티나** 모델 앵커로 받는다(바이트코드 확인). 클릭은 이미 우리 `Interaction` 히트박스가 처리하고, 클릭 라우팅은 이미 Citizens 가 아니라 **이름 매칭 폴백**을 갖고 있다. 남는 진짜 작업은 **Citizens 에만 있는 두 데이터(위치·스킨)를 BlockShip 영속으로 옮기는 것**과 **베드락 하이브리드 수명주기**다.

---

## 1. 실측한 사실 (근거 포함)

### 1.1 Citizens 쪽 현황 (prod 읽기 전용)

| 항목 | 실측값 | 출처 |
|---|---|---|
| 저장 NPC 수 | **201** | `plugins/Citizens/saves.yml` 정규식 카운트 |
| 전원 보유 트레잇 | `owner, scoreboardtrait, spawned, skintrait, location, type, inventory` (각 201) | traitnames 히스토그램 |
| 추가 트레잇 | `lookclose` 26, `rotationtrait` 8, `hologramtrait` 7, `equipment` 2 | 〃 |
| 월드 분포 | 메인 192 / 그 외 5 + 4 | `worldid` 카운터 |
| 전역 look-close | **`enabled: false`** (개별 26명만 on) | prod `Citizens/config.yml:18` |
| `always-keep-loaded` | `false` | 〃 :192 |
| 엔티티 트래킹 반경 | `players: 64`, **`misc: 64`**, `display: 48` | prod `spigot.yml:152` |
| view / simulation distance | **32** / 8 | `server.properties` |

### 1.2 왜 Citizens 가 11.44% 를 먹는가 — 스케일링 축이 다르다

- Citizens NPC 는 **«플레이어가 근처에 있을 때»가 아니라 «청크가 로드돼 있을 때» 스폰**된다. `view-distance=32` × 17명이면 마을 청크는 사실상 상시 로드다 → 메인월드 **192명이 거의 항상 스폰 상태**로 매 틱 돈다.
- 스폰된 플레이어형 NPC 1명 = **진짜 `ServerPlayer` 엔티티 1개**. 엔티티 틱 + 트래커(`ServerEntity.sendChanges`) + Citizens 자체 `NPCUpdate` 에서 트레잇 7종 `run()` + `ScoreboardTrait` 팀 패킷 + 스킨/탭리스트 패킷이 전부 따라온다.
- 즉 **Citizens 비용은 접속자 수와 거의 무관하게 상수**다. 17명에서 11.44% 였다면 50명에서도 비슷한 절대 비용이 남되, 전체 틱 예산이 빠듯해지면서 상대적으로 더 아프다. **동시에 «플레이어당» 비용(트래커 패킷·팀 패킷)은 선형으로 늘어난다.**
- 반면 우리 BetterModel 경로는 **이미 근접 스케일**이다: 반경 16 부착 / 20 해제, 뷰어당 부착 10개·유지 14개, 10틱 주기 (`NpcAnimator.java:74-88`). 이게 BlockShip 4.75% 의 주요 몫이다.

⇒ **Citizens 를 걷어내면 「192개 상수 부하」가 「뷰어당 근접 N개」로 바뀐다.** 이게 이 작업의 본질이고, 50명 대비 확장성의 핵심이다.

### 1.3 BetterModel 이 Interaction 을 앵커로 받는가 — **받는다**

`libs/BetterModel.jar` 바이트코드 검증:

- `BukkitAdapter.adapt(org.bukkit.entity.Entity) → PlatformEntity` — Player 전용 오버로드와 **별개로 일반 Entity 오버로드가 존재**한다.
- `BaseEntity.of(PlatformEntity)` 는 `instanceof PlatformPlayer` 가 아니면 `NMS.adapt(PlatformEntity)` 로 빠진다 → `BaseEntityImpl(CraftEntity)`. **LivingEntity 도 Player 도 요구하지 않는다.**
- 비-Living 안전성(전부 가드 확인):
  - `scale()` → `instanceof LivingEntity` 아니면 **`1.0`** (모델이 찌그러지지 않음)
  - `walkSpeed()` / `damageTick()` → 아니면 **`0`**
  - `mainHand()`/`offHand()` (`BaseBukkitEntity` default) → 아니면 **`empty()`**
  - `invisible()` → `Entity.isInvisible()` (Interaction 기본 false) → 모델 정상 렌더
- `ModelRenderer.create(BaseEntity, ModelProfile)` — 지금 쓰는 그 오버로드 그대로 쓸 수 있다.
- 보너스: **`create(PlatformLocation, ModelProfile) → DummyTracker`** 도 있다(앵커 엔티티 0개). 다만 `sourceEntity()` 가 없어 지금의 이름표 복구 로직(`restoreModelNametag`)을 통째로 다시 써야 하고 뷰어 관리도 수동이다 → **1차에서는 채택하지 않는다**(§8 참조).

### 1.4 클릭 경로는 이미 Citizens 비의존

`NpcInteractListener.onInteract` (`npc/NpcInteractListener.java:118-135`):
1. `BLOCKSHIP_NPC_HITBOX` 태그 + PDC `npc_hitbox_source` 로 원본 UUID 복원
2. `mgr.findByEntity(clicked)` (Citizens 경로)
3. **실패하면 uncolored 이름 매칭 폴백** ← Citizens 없이도 도는 경로가 이미 있다

`NpcDialogueManager.start(Player, String npcId, Entity npcEntity)` — 시그니처가 **`Entity`** 다. Player 를 요구하지 않는다.

### 1.5 Citizens 에만 있고 BlockShip 에 없는 것 — 정확히 둘

`npc.json` 은 **197 entry**, 각 항목은 `citizensId` + `name` + 역할 플래그뿐. **위치도 스킨도 없다.**
- 위치: `NpcManager.liveLocationOf()` 가 매번 Citizens 레지스트리를 훑는다 (`NpcManager.java:153-173`)
- 스킨: `NpcAnimator.buildSkinProfile()` 이 Paper `getPlayerProfile()` → 실패 시 **Citizens `SkinTrait.getTexture()` 리플렉션** (`NpcAnimator.java:1323-1382`)

둘 다 prod `saves.yml` 의 `traits.location`(worldid,x,y,z,bodyYaw,pitch)·`traits.skintrait`(textureRaw/signature)에 있으므로 **일회성 추출로 이관 가능**하다.

### 1.6 Citizens 를 참조하는 전체 파일 (11개)

```
26  npc/NpcAnimator.java            ← 핵심
 9  npc/NpcManager.java             ← liveLocationOf / findByEntity / nearestActiveNpc / setCitizensName
 8  npc/NpcCommand.java             ← OP 도구
 6  ship/PilotAvatar.java           ← 별도 레지스트리, 이번 범위 밖
 6  npc/NpcAdminGui.java            ← OP 도구
 4  quest/QuestMarkerManager.java   ← ! 마커를 Citizens 순회로 붙임
 3  fishing/BpsManager.java         ← BPS NPC 를 코드에서 createNPC
 2  npc/NpcSkinPersistListener.java ← 이관 후 소멸
 2  casino/table/DealerNpcService.java
 1  npc/NpcMovePersistListener.java ← 이관 후 소멸
 1  inn/InnManager.java
```

---

## 2. 목표 아키텍처

```
권위 데이터 (BlockShip, 디스크)
  npc.json  ─ id → { name, world,x,y,z,yaw,pitch, skinRaw, skinSignature, 역할플래그… }
        │
        ▼
NpcRuntime  ─ 근접 스캔(10틱) · 공간 색인(청크 버킷)
        ├─ Java 뷰어  : Interaction 앵커 1개 + BetterModel EntityTracker
        │                (앵커는 근접 시 생성 / 이탈 시 제거, persistent=false)
        └─ 베드락 뷰어: Citizens NPC 를 «그때만» 스폰 (하이브리드, §5)
```

핵심 규칙 세 가지:

1. **엔티티는 전부 파생물**이다. 디스크 권위는 `npc.json` 하나. 앵커 Interaction 도, 베드락용 Citizens NPC 도 언제든 재생성 가능해야 한다 (CraftEngine 의 Interaction 스윕 때문에 이건 선택이 아니라 필수 — §7.1).
2. **Java 경로에는 Citizens 가 전혀 등장하지 않는다.** `CitizensAPI` 호출은 베드락 하이브리드와 OP 도구에만 남는다.
3. 앵커의 `hideOption` 은 **`EntityHideOption.FALSE`** 로 둔다. 지금 쓰는 `(true,true,true,false)` 는 «원본 Citizens Player 를 숨기려고» 넣은 것이고, Interaction 앵커에 그대로 쓰면 **클라이언트에서 앵커가 사라져 클릭이 죽을 수 있다.** Interaction 은 원래 안 보이므로 숨길 게 없다.

---

## 3. 데이터 이관 (Phase 0 — 코드 변경 전에 끝낸다)

### 3.1 NpcDef 확장

```java
// npc/data/NpcDef.java 에 추가
public String  world;      // Bukkit 월드 이름 (worldid UUID → 이름 변환해서 저장)
public Double  x, y, z;
public Float   yaw, pitch;
public String  skinRaw;       // base64 textures property value
public String  skinSignature; // 있으면 저장(없어도 렌더는 됨)
public String  skinUpdatedAt; // 이관·갱신 시각(감사용)
```

`citizensId` 는 **지우지 않는다** — 베드락 하이브리드와 OP 도구가 계속 쓴다.

### 3.2 추출 스크립트 (신규, `ops/extract-npc-anchors.py`)

- 입력: prod `plugins/Citizens/saves.yml` 사본 + `ops/blockship-data/npc.json`
- `npc.'<id>'.traits.location` → world/x/y/z/yaw/pitch. `worldid`(UUID) → 월드 이름은 `Multiverse-Core/worlds.yml` 또는 각 월드의 `level.dat` 로 해석
- `npc.'<id>'.traits.skintrait.textureRaw` / `signature` → skinRaw/skinSignature
- `npc.json` 의 `citizensId` 로 조인. **조인 실패 항목은 침묵하지 말고 전부 출력하고 non-zero exit**
- 생성물을 고정 사본으로 두지 않는다 — 재실행 가능한 스크립트가 권위 (`feedback_dont_freeze_generated_artifacts` 규약)

### 3.3 이관 검산 게이트 (신규, `ops/audit-npc-anchors.py` — preflight 에 추가)

1. `npc.json` 의 모든 NPC 가 world/x/y/z/skinRaw 를 갖는가 (미달 항목 전부 나열)
2. Citizens saves.yml 좌표와 **1e-3 이내 일치**
3. skinRaw 가 base64 디코드되고 `"url"` 키를 갖는가 (지금 `buildSkinProfile` 2차 폴백이 하는 파싱과 동일 판정)
4. 좌표 중복(같은 칸에 2명 이상) 경고 — 이관 사고 조기 감지
5. **역방향**: Citizens 에는 있는데 npc.json 에 없는 NPC 목록 (201 − 197 = 최소 4개는 미등록. BPS·카지노 딜러 등 코드 생성분일 가능성이 높으니 확인 필요)

★ 이 게이트가 통과하기 전에는 §4 코드를 staging 에 올리지 않는다.

---

## 4. 구현 단계 (staging 전용)

### Phase 1 — `NpcRuntime` 신설 + 공간 색인

신규 `npc/NpcRuntime.java`:

- 부팅 시 `npc.json` 을 읽어 **청크 좌표 버킷 색인**(`Map<Long, List<String npcId>>`)을 만든다.
- 근접 스캔은 **플레이어마다 전체 201 순회를 하지 않는다.** 현재 `NpcAnimator.tick()` 은 뷰어마다 모든 레지스트리를 완전 순회한다 (`NpcAnimator.java:953-978`) → 17명 × 201 = 3,417 회/10틱. 50명이면 10,050 회. 청크 버킷이면 뷰어당 주변 3×3 청크만 본다 (`NpcGazeManager` 가 2026-08-17 에 이미 같은 처방을 받았다).
- API: `List<NpcAnchor> near(Player, double range)`, `Location locationOf(String id)`, `String idAt(Entity)`.

`NpcManager.liveLocationOf/nearestActiveNpc/findByEntity` 를 **NpcRuntime 위임으로 교체**한다. 호출처가 이미 10곳 이상이라(퀘스트 네비·판매·섬상점·마켓·대화) 여기만 바꾸면 나머지는 그대로 돈다.

### Phase 2 — 앵커를 Interaction 으로 교체

`NpcAnimator.attach(UUID, Player npc)` → `attach(String npcId, NpcAnchor a)`:

```java
Interaction anchor = world.spawn(loc, Interaction.class, i -> {
    i.setInteractionWidth(1.15f);
    i.setInteractionHeight(2.25f);
    i.setResponsive(true);
    i.setPersistent(false);
    i.setGravity(false);
    i.setInvulnerable(true);
    i.customName(displayName);                 // ★ BetterModel 이름표 소스
    i.setCustomNameVisible(false);             // 바닐라 이름표는 끈다
    i.getPersistentDataContainer().set(NPC_HITBOX_SOURCE, STRING, npcId);
    i.addScoreboardTag("BLOCKSHIP_NPC_HITBOX");
});
EntityTracker t = limbRenderer().create(
        BaseEntity.of(BukkitAdapter.adapt(anchor)), profileFrom(def));
t.hideOption(EntityHideOption.FALSE);          // ★ (true,true,true,false) 금지
```

- `buildSkinProfile` 은 **`NpcDef.skinRaw` 에서 만드는 경로를 1차**로 올린다. 기존 Citizens 리플렉션 경로는 베드락/이관 미완 NPC 폴백으로 뒤에 남긴다.
- `restoreModelNametag` 은 `t.sourceEntity().customName()` 을 읽으므로 **그대로 동작**한다(앵커에 customName 을 넣었으므로). 2026-08-24 의 `viewedPlayer` 토글 처방(`refreshNametagFor`)도 그대로 유효하다.
- `setNameplateByEntity` (Citizens NAMEPLATE_VISIBLE 토글)은 Java 경로에서 **불필요해진다** — 앵커에 바닐라 이름표가 애초에 없다. 베드락 경로에만 남긴다.
- `syncInteractionHitboxes` 는 «Citizens 엔티티를 따라간다»에서 «npc.json 좌표에 고정»으로 바뀐다 → `teleport` 호출이 사실상 사라진다(NPC 는 안 움직인다).

### Phase 3 — 부수 시스템 이관

| 대상 | 변경 |
|---|---|
| `NpcGazeManager` | Citizens 엔티티에 회전 패킷 보내던 경로 삭제. 모델 루트 yaw(`lookState` + `t.rotation()`)가 유일한 출처가 된다. **ProtocolLib 의존 하나가 통째로 빠진다.** |
| `QuestMarkerManager.tick()` | Citizens 순회 → `NpcRuntime.near()` 순회. 마커 TextDisplay 를 앵커 UUID 에 맺는다 |
| `TabListManager` | NPC 필터(`hasMetadata("NPC")`)는 남겨두되 Java 경로에선 대상이 0이 된다 |
| `NpcMovePersistListener` / `NpcSkinPersistListener` | Citizens 이벤트 기반 → **OP 편집 명령이 직접 npc.json 을 쓰는 방식으로 교체**. 이 두 리스너는 최종적으로 삭제 |
| `BpsManager` / `InnManager` / `DealerNpcService` | `liveLocationOf` 위임으로 이미 커버. `BpsManager` 의 `createNPC` 는 npc.json 항목 생성으로 대체 |
| `NpcCommand` / `NpcAdminGui` | `/npc이동`·`/npc텔포`·`/npc이름`을 **npc.json 편집 + 앵커 재생성**으로. Citizens 경로는 베드락 NPC 동기화용으로만 유지 |

### Phase 4 — Citizens NPC 를 «베드락 전용»으로 강등

- Citizens `config.yml` 은 건드리지 않되, **부팅 시 전 NPC 를 despawn** 상태로 두고 §5 가 필요할 때만 spawn 한다.
- 남은 Citizens 역할: 베드락 렌더 + OP 편집 시 시각 확인. 이 둘은 «가끔»이다.

---

## 5. 베드락 하이브리드 수명주기

```
베드락 뷰어 B 가 NPC n 의 반경 BR_ON(=24) 안으로 진입
   → n 의 Citizens NPC 가 despawned 면 spawn()
   → n 에 Java 모델이 붙어 있으면 그 EntityTracker 를 B 에게서 hide()  (지금 hideFromBedrock 과 동일)
모든 베드락 뷰어가 BR_OFF(=32) 밖으로 이탈
   → GRACE(=20s) 타이머 시작, 그 사이 재진입하면 취소
   → 만료 시 Citizens NPC despawn()
```

설계 근거·주의:

- **BR_ON(24) > Java RANGE_ON(16)** 으로 벌려 둔다. 베드락은 Citizens 원본을 보므로 Java 유저보다 먼저 보여야 팝인이 덜 튄다. `misc: 64` / `players: 64` 트래킹 반경 안이라 둘 다 여유.
- **GRACE 20초는 히스테리시스가 아니라 스폰 비용 방어다.** Citizens spawn 은 ServerPlayer 생성 + 스킨 패킷 + 팀 패킷이라 비싸다. 베드락 유저가 마을을 오가며 왕복하면 spawn/despawn 이 채터링한다.
- **Java 유저에게 원본이 새면 안 된다.** 지금은 BetterModel `hideOption(visibility=true)` 가 원본을 숨겼는데, 새 구조에선 Java 유저의 모델이 Interaction 에 붙어 있어 **원본 Citizens 를 숨기는 주체가 사라진다.** 따라서 베드락 때문에 spawn 된 Citizens NPC 는 **Java 유저 전원에게 `player.hideEntity(plugin, npcEntity)` 로 명시적으로 숨겨야 한다.** 이게 이 하이브리드의 가장 놓치기 쉬운 지점이다. 신규 접속자·월드 이동·리스폰에도 재적용해야 한다(`PlayerJoinEvent`, `PlayerTrackEntityEvent`).
- 베드락 유저의 **클릭은 Citizens 원본과 Interaction 둘 다** 맞을 수 있다 → `NpcInteractListener` 가 두 경로 모두 같은 npcId 로 수렴하는지 확인 필요(현재 코드는 수렴한다: PDC 복원 → `findByEntity` → 이름 폴백).
- **이 게이트는 «아무 플레이어»가 아니라 «베드락 플레이어»에만 걸린다.** Java 유저만 있는 마을에서는 Citizens 가 한 명도 스폰되지 않는다. 절감 규모는 §6.4 표.
- 베드락 비율은 실측 24% 가 «플레이 불가» 상태였다는 기록이 있다(`project_newbie_funnel_telemetry`). 하이브리드가 그 경로를 더 나쁘게 만들면 안 된다 — §9 테스트에서 베드락 전용 시나리오를 Java 와 동등 비중으로 돌린다.

---

## 6. 기대 효과 — ★2026-09-18 실측으로 전면 수정

> 이전 초안은 «근접 게이팅이면 스폰 수가 준다» 고 썼다. **그건 틀렸다.** prod `saves.yml` 좌표
> 201개를 뽑아 시뮬레이션한 결과, 사람이 늘면 근접 집합의 합집합은 전체에 수렴한다.

### 6.1 NPC 공간 분포 (prod 실측)

- 메인월드 192명, 40칸 단일연결 클러스터 **29개** — 크기 `[40, 40, 32, 20, 18, 5, 4, 2×11, 1×11]`
- NPC 1명 주변의 다른 NPC 수: **R=8 평균 1.9 / R=16 평균 3.5 / R=20 평균 4.4(중앙 4, 최대 13) / R=24 평균 5.3(최대 20)**

### 6.2 앵커 working set — 근접 게이팅은 «개수»를 못 줄인다

플레이어가 NPC 위치에 무작위로 흩어져 있을 때, 반경 안에 들어오는 NPC의 **합집합**:

| 반경 | K=17 (지금) | K=50 | K=50 최악배치 |
|---|---|---|---|
| 20 (모델 유지반경) | 62 (32%) | **125 (65%)** | 169 (88%) |
| 24 | 67 (34%) | 132 (68%) | 176 (91%) |
| 8 | 30 (15%) | 78 (40%) | 106 |
| 6 | 26 (13%) | **70 (36%)** | 94 |

⇒ **50명 시대에는 앵커가 125개 안팎으로, 지금 Citizens 192개와 자릿수가 같다.** 「근처에 한 명이라도 있으면 소환해야 한다」는 지적 그대로다.

### 6.3 그런데 절감의 근거는 «개수»가 아니라 «개당 단가»다 (바이트코드 확인)

| | Citizens 플레이어형 NPC | Interaction 앵커 |
|---|---|---|
| 엔티티 틱 | `ServerPlayer` 전체 틱 — 이동·충돌 push 스캔·속성·효과·인벤 | **`Interaction.tick()` = `return` (바이트코드 1줄)** |
| 플러그인 틱 | `CitizensNPC.update()` **매 틱**: `getLocation()` 할당 → `ACTIVATION_RANGE` 메타 조회 → `LocationLookup.getNearbyPlayers()` → swim 판정 → navigator → `AbstractNPC.update()` 의 **트레잇 7종 `run()`** | 없음 |
| 뷰어별 패킷 | `ScoreboardTrait` 팀 패킷 · 스킨/탭리스트 패킷 · 플레이어 메타데이터 | 스폰 1회 후 변화 없음 (좌표 고정) |
| 충돌 | 플레이어끼리 push 검사 대상 | `isPushable()=false`, 충돌 없음 |

⇒ **125개 Interaction ≪ 192개 Citizens ServerPlayer.** 개수는 비슷해도 단가가 자릿수로 다르다. 이게 이 작업의 유일한 정당화이고, 「개수가 준다」는 근거로 이 작업을 팔면 안 된다.

### 6.4 베드락 게이팅이 진짜 절감 구간 — 수치

베드락 비율 실측 ~24% 가정, 하이브리드 반경 24:

| 시나리오 | 베드락 인원 | Citizens 스폰 수 (중앙) | 최악 |
|---|---|---|---|
| 지금 (17명) | ~4 | **19 (9%)** | 51 |
| 50명 | ~12 | **52 (27%)** | 103 |
| 베드락 0명 | 0 | **0** | 0 |

⇒ 베드락 전용 게이팅은 Citizens 실체를 **192 상수 → 19~52 변동**으로 바꾼다. 다만 베드락 비중이 커지면 이 이득이 깎인다 — 그게 §8 패킷 경로의 우선순위를 정하는 기준이다.

### 6.5 안 줄어드는 것

BetterModel 디스플레이(steve = 본 18개 × 뷰어당 ≤14 NPC). 지금 BlockShip 4.75% 의 주요 몫은 그대로 남는다.

★ 위 표는 **공간 분포 시뮬레이션**이지 tick 측정이 아니다. 최종 판정은 staging spark 대조로만 한다.

---

## 6.6 모델 상한(CAP)과 Citizens 폴백 — ★2026-09-19 정정: 문제가 아니었다

`CAP_ON=10` / `CAP_OFF=14` 는 「상한을 넘은 NPC 는 모델 없이 **원본 Citizens 로 보인다**」는 전제 위에 있다(주석 그대로). Citizens 를 걷어내면 그 폴백이 사라지므로 상한 초과분이 유령이 된다 — 고 적었는데, **좌표 실측이 그 걱정을 지운다**:

| 반경 | NPC 1명 주변의 다른 NPC 수 | 해당 상한 | 걸리는가 |
|---|---|---|---|
| 16 (RANGE_ON, 부착) | 평균 3.5 / 중앙 3 / **최대 9** | CAP_ON **10** | **안 걸림** |
| 20 (RANGE_OFF, 유지) | 평균 4.4 / 중앙 4 / **최대 13** | CAP_OFF **14** | **안 걸림** |

최밀집 지점조차 상한 아래다 — 상한은 2026-08-03 에 «반경 25 + 무제한» 을 막으려 넣은 것이고, 지금 반경이 16/20 으로 좁혀진 시점에서 이미 이중 안전장치였다. **상수를 건드리지 않는다.**

다만 구현에서 한 가지는 지켰다: **클릭 앵커는 상한과 무관하게 반경 안 전원에게 만든다**(`NpcAnimator.tick` 이 CAP 적용 «전에» `ensureAnchor` 를 부른다). 나중에 NPC 를 더 촘촘히 놓아 상한이 걸리기 시작해도 「안 보이지만 눌리는」 선에서 끝나고, 「눌리지도 않는」 상태로는 안 간다.

---

## 6.7 지적이 열어준 선택지 — 히트박스 반경을 모델 반경에서 분리

모델은 16칸에서 보여야 하지만 **클릭은 ~6칸이면 충분하다**(플레이어 엔티티 리치 3칸, 여유 포함). 앵커를 Interaction 으로 쓰면 둘이 묶여 16칸 = 125개가 되지만, **DummyTracker(앵커 엔티티 0개)** 를 쓰면 엔티티는 6칸짜리 히트박스뿐 → **70개(36%)** 로 떨어진다.

| 안 | 50명 기준 엔티티 수 | 비용 |
|---|---|---|
| (A) Interaction 앵커 R=16/20 | 125 | 낮음 — 지금 이름표 복구 로직(`sourceEntity()` 기반) 그대로 재사용 |
| (B) DummyTracker + 히트박스 R=6/8 | 70 | 높음 — `sourceEntity()` 부재로 `restoreModelNametag`·`refreshNametagFor` 전면 재작성, 뷰어 관리 수동 |

**판정: Phase 2 는 (A)** — `Interaction.tick()` 이 `return` 인 이상 125 vs 70 의 차이는 «엔티티 트래커 순회» 뿐이고, 2026-08-24 이름표 처방을 다시 짜는 위험이 그보다 크다. (B) 는 **staging spark 에서 엔티티 트래킹이 실제로 뜨거울 때만** 착수하는 Phase 6 후보로 둔다.

---

## 7. 함정 목록 (이미 이 서버에서 터진 것들)

### 7.1 ★ CraftEngine 이 청크 로드 때 모든 Interaction 을 지운다
`collision-entity-type: "interaction"` 이라 `FurnitureEventListener.onEntitiesLoadEarly` 가 **남의 플러그인 Interaction 까지 전부** 제거한다(2026-08-25 prod A/B 실측). 
⇒ 앵커를 **절대 `setPersistent(true)` 로 두지 않는다.** 10틱 reconcile 이 로드된 청크 한정으로 되살리는 구조를 유지한다. 지금 코드가 이미 그렇게 돼 있으니 **되돌리지만 않으면 된다.**

### 7.2 `hideOption` 오용 → 클릭 사망
§2 규칙 3. `EntityHideOption.FALSE` 를 쓴다. 이걸 지금 값 그대로 복사하면 «모델은 보이는데 우클릭이 안 먹는» 증상이 나온다.

### 7.3 이름표 `viewedPlayer` 토글 (2026-08-24 처방)
`alwaysVisible(true)` 를 매 주기 다시 걸면 `ModelNametagImpl.send` 의 else 분기에 영원히 도달하지 못해 **그 뷰어에게만 이름표가 영구 소실**된다. `refreshNametagFor` 의 ±20000 텔레포트 처방을 **그대로 옮겨야 한다.** 앵커가 바뀌어도 이 버그는 BetterModel 쪽이라 그대로 남는다.

### 7.4 월드 간 `distanceSquared` 예외가 tick 전체를 죽인다
2026-08-01 사고: 잠수월드 이동 시 `Cannot measure distance between world and afk_world` 로 매 틱 예외 → 마을 NPC 전원 유령화. **NpcRuntime 의 근접 스캔도 NPC 단위 try/catch 를 유지한다.**

### 7.5 `player.teleport()` cross-world 불가
앵커 이동은 같은 월드 안이므로 무관하지만, **베드락 Citizens spawn 위치를 코드로 옮길 일이 생기면** `execute in <dimKey> run tp` 를 써야 한다(`util.Worlds.dimKey`).

### 7.6 dev 가동 중 라이브 JSON 편집은 덮인다
`npc.json` 은 **dev 서버 종료 시 저장**된다. 이관 스크립트를 dev 라이브 폴더에 돌리면 종료 때 덮인다. 작업 원본은 레포 `ops/blockship-data/npc.json` 이다.

### 7.7 새 월드 하드코딩 목록
NPC 가 있는 월드가 늘면 `SUPPRESS_WORLDS` 류 목록이 자동으로 따라오지 않는다. NpcRuntime 의 월드 필터는 npc.json 에서 유도한다.

### 7.8 OP 명령 게이트
새로 만드는 관리 명령은 `isOp()` 가 아니라 **`GuideAccess.admin(sender)`** 를 쓴다. `setPermission("blockship.admin")` 병행.

---

## 8. 패킷 기반 베드락 NPC (후순위 평가 — 지금은 안 한다)

Citizens 를 **완전히** 없애려면 베드락용 가짜 플레이어를 우리가 직접 패킷으로 그려야 한다: `PLAYER_INFO_UPDATE(add + 텍스처 property)` → `SPAWN_ENTITY(player)` → 메타데이터 → `PLAYER_INFO_REMOVE`(탭 숨김) → 회전 패킷.

평가:
- **비용**: ProtocolLib 의존 재도입, 뷰어별 엔티티 ID 관리, Geyser 의 Java→베드락 변환 경로가 fake player 를 어떻게 다루는지 검증 필요, 클릭은 서버가 `Interact` 패킷을 직접 해석해야 함.
- **이득**: 하이브리드 대비 추가 절감은 **베드락 유저가 NPC 근처에 있을 때만** 발생. 위 §5 로 이미 그 시간대만 남겨 뒀으므로 **한계이득이 작다.**
- **판정**: §4~§5 를 staging 에서 완주하고 **spark 재측정에서 Citizens 잔여 비용이 여전히 유의미할 때만** 착수한다. 지금 착수하면 베드락 24% 를 이유 없이 위험에 빠뜨린다.
- ★단 §6.4 가 보여주듯 **베드락 인원이 늘수록 하이브리드의 이득이 깎인다**(4명→19개, 12명→52개). 베드락 비중이 30% 를 넘거나 동시 40명대가 상시화되면 이 항목의 우선순위를 재평가한다. 중간 단계로 **Citizens 없이 우리가 직접 띄우는 순수 `ServerPlayer`**(트레잇·네비게이터·ScoreboardTrait 없음) 도 있다 — §6.3 표의 「플러그인 틱」 행만 지우는 절충안이고 패킷 경로보다 훨씬 싸다.

---

## 9. staging 검증 계획

> 전부 dev(`~/deploy-dev.sh`) 에서 먼저 돌고, 통과분만 `~/stage-blockship.sh` 로 prod staging 에 올린다. **prod 재시작은 06:00 정기 경로에 맡긴다.**

### 9.1 자동 게이트 (배포 전, 사람 없이)

| # | 게이트 | 통과 기준 |
|---|---|---|
| G1 | `ops/audit-npc-anchors.py` | §3.3 전 항목 통과, 미이관 0건 |
| G2 | `quest_audit.py` | ERROR 0 (NPC 배정이 깨지지 않았는가) |
| G3 | 신규 self-test `NpcRuntimeSelfTest` | 청크 버킷 색인이 전수 순회와 **같은 결과**를 낸다(201개 무작위 좌표 × 반경 16/20/24) |
| G4 | `ops/audit-copies.py` · preflight 10종 | 기존 그대로 |

### 9.2 dev 수동 시나리오

| # | 시나리오 | 확인 |
|---|---|---|
| T1 | **Java 단독 근접** | 스폰마을 진입 → NPC 모델 표시 · 이름표 표시 · 숨쉬기/제스처 재생 · **Citizens 원본 0명 스폰** (`/npc list` 또는 엔티티 카운트) |
| T2 | **Java 클릭 전수** | 대화 NPC / 페리 / 물고기판매 / 부품상점 / 대장간 / 요리 / 마켓 / 퀘스트게시판 / 카지노딜러 / 여관 / 말·배대여 / 조선소 / 섬상점 / 제출소 / 감정 / 랭킹 / BPS — **역할 GUI 가 전부 열리는가** (`NpcDef.GUI_ROLES` 전수) |
| T3 | **퀘스트 흐름** | 수락 → 진행 → 완료 → 보상. 특히 **찾아가기(visit) 퀘스트**가 도착 즉시 완료되는가 (`project_visit_quest_skips_dialogue` 회귀) |
| T4 | **퀘스트 마커** | `!`/`?` 가 NPC 머리 위 올바른 높이에 뜨는가, NPC 이탈 시 정리되는가 |
| T5 | **베드락 단독** | 베드락 클라 접속 → NPC 반경 진입 시 Citizens 원본이 스폰되고 **보이는가**, 이탈 20초 후 despawn 되는가, 클릭·대화·GUI(폼) 정상인가 |
| T6 | **혼합 근접** | Java 1 + 베드락 1 이 같은 NPC 앞 → Java 는 모델만, 베드락은 원본만. **Java 화면에 원본이 겹쳐 보이면 실패** (§5 hideEntity 검증) |
| T7 | **텔레포트/월드 이동** | 페리 항해 · 포탈 · 섬 · 여관 부활 · 잠수월드 왕복 → 앵커 누수 0, 유령 NPC 0, 예외 로그 0 |
| T8 | **사망·리스폰** | NPC 앞에서 사망 → 부활 후 모델·이름표가 돌아오는가 (2026-09-03 회귀) |
| T9 | **재접속** | 로그아웃 → 재접속 시 가까운 NPC 이름표가 보이는가 (2026-08-24 `viewedPlayer` 회귀) |
| T10 | **청크 왕복** | NPC 마을에서 128칸 밖으로 나갔다가 복귀 ×3 → Interaction 앵커 중복 생성 0, CE 스윕 후 자동 복구 |
| T11 | **OP 편집** | `/npc이동`·`/npc텔포`·`/npc이름` → npc.json 이 즉시 갱신되고 앵커가 재생성되며 **재시작 후에도 유지** |
| T12 | **부하** | dev 테스트 봇 다수를 스폰마을에 모으고 spark 샘플링 → Citizens % 와 BlockShip % 를 **변경 전/후 같은 조건으로 대조** |

### 9.3 prod 관측 (배포 후, 변경 없이 읽기만)

1. 06:00 정기 적용 다음날 `spark profiler` 장기 샘플 → **Citizens % · BlockShip % · 전체 MSPT** 를 이전 17명 샘플과 비교
2. `[NpcAnim]` warning 카운트 (스킨 없음 / 히트박스 실패 / 부착 예외)
3. 유령 NPC 제보 0건
4. 베드락 유저 세션 길이 회귀 여부 (텔레메트리)

### 9.4 롤백

- jar: `~/mcserver/scripts/rollback-jar.sh` (staging 도 함께 비움 — 안 비우면 다음날 06:00 에 되돌아온다)
- 데이터: `npc.json` 은 Citizens saves.yml 이 그대로 남아 있으므로 **새 필드를 무시하는 이전 jar 로 돌아가면 그대로 복구**된다. 즉 이관은 **가산적(additive)** 으로만 한다 — `citizensId` 를 지우거나 Citizens saves.yml 을 건드리는 순간 롤백이 불가능해진다. **saves.yml 은 이 작업 전체에서 읽기 전용이다.**

---

## 9.5 ★진행 상황 (2026-09-19, dev)

### 끝난 것

| 항목 | 결과 |
|---|---|
| **Phase 0 데이터 이관** | `ops/extract-npc-anchors.py` 신설 → prod `saves.yml` 에서 **197/197** 앵커(world/x/y/z/yaw/pitch·displayName·skinRaw·signature) 이관. 원본 필드 손실 0 검산 통과 |
| **G1 게이트** | `ops/audit-npc-anchors.py` 신설 → 필수필드·스킨 base64/SKIN url·좌표중복·**Citizens 원본과 1e-3 이내 대조** 전부 통과 |
| **Phase 1 NpcRuntime** | 신설. 청크 버킷 공간색인. 뷰어 전수순회(192×접속자) → 주변 3×3 청크 |
| **Phase 2 앵커 렌더** | `NpcAnimator` 가 `Interaction` 앵커에 BetterModel 부착. `hideOption(EntityHideOption.FALSE)`(앵커=클릭 히트박스라 숨기면 안 됨), 스킨은 `def.skinRaw` 0차 경로, 이름표는 앵커 `customName` |
| **Citizens 억제** | `CitizensSuppressor` 신설 — `NPCSpawnEvent` 취소 + 부팅 스윕. **npc.json 등록 + 앵커 보유 NPC 만** 대상(명예의전당 등 미등록 4명은 Citizens 가 계속 그린다). `onDisable` 에 `restore()` |
| **Phase 3 일부** | `NpcInteractListener` 가 앵커 PDC(`npc_hitbox_npcid`)로 직행 — 이름 매칭을 안 거친다(표시이름≠npc.json name 인 2/197 이 끊기던 경로). `QuestMarkerManager` 는 앵커 «좌표»로 마커를 띄운다(앵커 엔티티는 20칸, 마커는 48칸이라 엔티티에 못 맺는다) |
| **설정** | `config.yml` `npc.citizens-free`(기본 false). 앵커 0개면 경고 후 자동으로 끈다 |
| **dev 배포** | jar + 앵커 npc.json + 플래그 on 으로 기동 |

dev 기동 로그 (실측):
```
[NpcRuntime] citizens-free 활성 — 앵커 197개
[NpcAnim] reconcileSkins: registry 오브젝트 192개 중 플레이어형 0개 확인
[NpcSuppress] Citizens 원본 0명 내림 (남은 스폰 0명)
```
RCON: 플레이어 0명 · `@e[type=player]` 0 · `@e[type=interaction,tag=BLOCKSHIP_NPC_HITBOX]` 0 (접속자가 없으니 앵커도 0 — 의도대로). 예외 로그 0.

### 공간색인 경계 검산 (해석)

버킷 반경은 `cr = ceil(range/16)`, 버킷 키는 `floor(coord) >> 4`. 뷰어가 청크 안 최댓값
(`c*16+15.999`)에 서 있을 때 거리 `range` 지점의 청크는 `c + floor((15.999+range)/16)` 이다.
`range = 16k` 면 `= c+k` 이고 `cr = k`, `range = 16k+r (0<r<16)` 면 `= c+k+1` 이고 `cr = k+1`.
**정확히 맞닿는다 — 가장자리 NPC 가 새지 않는다.**

### 아직 안 된 것

- **베드락**: 하이브리드(§5)가 없어서 **지금 dev 에서 베드락 유저에겐 NPC 가 안 보인다.** config 주석에 명시해 뒀다. 다음 작업.
- **육안·클릭 검증**: dev 가 Velocity(`online-mode = true`) 뒤에 있어 오프라인 테스트 봇이 붙지 못한다(봇은 백엔드 25567 직결이라 «requires Velocity» 로 거부). 프록시 설정은 다른 세션이 세운 것이라 건드리지 않았다 → **T1·T2 는 사람이 dev 에 접속해야 한다.**
- `NpcGazeManager`(앵커 모드에선 대상이 0이라 무해하지만 낭비) · `NpcMovePersistListener`/`NpcSkinPersistListener` 정리 · `/npc이동` 계열의 npc.json 쓰기 · `DealerNpcService.playGesture`(Citizens 엔티티 UUID 기준이라 앵커 모드에서 안 맞는다) — 전부 Phase 3 잔여.

---

## 10. 작업 순서 요약

```
0. ops/extract-npc-anchors.py + ops/audit-npc-anchors.py 작성 → G1 통과   ← 코드 변경 없음
1. NpcDef 확장 + NpcRuntime 신설 + NpcManager 위임 교체 (동작 동일, Citizens 아직 유지)
2. 앵커를 Interaction 으로 교체 + hideOption FALSE + skinRaw 1차 경로 + **CAP_ON 상향(§6.6)**
3. QuestMarker / Gaze / TabList / 영속 리스너 이관
4. 베드락 하이브리드 (spawn/despawn + Java 쪽 hideEntity)
5. dev 전수 테스트(T1~T12) → staging → 06:00 정기 적용 → prod 관측
6. (조건부) 패킷 베드락 NPC 재평가
```

Phase 1 은 **동작이 완전히 동일한 리팩터링**이라 단독 배포해도 안전하다. Phase 2 부터가 진짜 변경이니 **Phase 1 을 먼저 따로 내보내 회귀를 분리**하는 것을 권한다.
