# 서버 부하 전수조사 — 2026-08-17

대상: `blockship-plugin` 자바 소스 356파일 / 102,751줄 전체 + 라이브 JSON 실측.
판정 근거는 전부 코드/데이터 실측이다(추정치는 그렇다고 표시).
라이브 TPS 대조는 못 했다 — AIBuilder 브리지(25599 터널)가 내려가 있어서 `tps` 캡처 실패.

기준 하드웨어: 오라클 A1 **4 OCPU / 24GB, 힙 16G**. 코어가 4개뿐이라
"메인스레드 1개가 틱당 얼마나 도는가"가 사실상 전부다.

---

## 요약 — 실측된 전역 수치

| 항목 | 실측 |
|---|---|
| 반복 스케줄러(runTaskTimer) | **81개** |
| 그중 1~2틱 주기 | 12개 |
| 비동기 태스크(runTaskAsynchronously) | **3개** ← 파일 I/O 사실상 전부 메인스레드 |
| 등록 리스너 | 156개 / `@EventHandler` **364개** |
| ChunkLoadEvent 핸들러 | **8개** |
| InventoryClick 69 · PlayerInteract 32 · BlockBreak/Place 27 | |
| 채집 노드 | **786개** (prod 실측, `forage-nodes.json` 222KB) |
| NPC | 330명 · 지역 35개(폴리곤/3D 24개) |

---

## S급 — 지금 터질 수 있는 것

### S1. ChunkLoadEvent 하나에 전수순회가 8겹으로 붙어 있다
`forage/ForageManager.java:838` → `repairChunk()`가 **청크 하나 로드될 때마다 노드 786개를 전부 순회**한다.
같은 이벤트에 7개가 더 붙어 있다:

| 위치 | 청크 로드 1회당 하는 일 |
|---|---|
| `forage/ForageManager.java:846` | 노드 **786개** 전수 |
| `collectible/CollectibleListener.java:84` | 수집품 전수 |
| `trap/TrapManager.java:721` | 청크 엔티티 전수 + 통발 전수 |
| `zipline/ZiplineManager.java:457` | 청크 엔티티 **2회** 순회 + 로프 재스폰 |
| `guild/GuildGui.java:155` | 길드 전수 + `world.getBlockAt()` |
| `listener/ChunkListener.java:33` | 배 전수 |
| `BlockShipPlugin.java:547` | 청크 엔티티 전수 |
| `drawbridge/DrawbridgeListener.java:20` | 도개교 조회 |

- 청크 로드는 플레이어가 걷기만 해도 초당 수십 건, 미생성 지역 탐험/봇 테스트에선 수백 건이다.
  메모리에 남은 **"100명 봇 테스트 51초 프리즈, 병목=청크GEN"** 의 상당 부분이 여기일 가능성이 높다.
- `ForageManager.repairChunk` 는 수리가 실제로 일어나면 **222KB JSON을 메인스레드에서 그 자리에서 쓴다**(`if (anyFixed) saveNodes()`).
  재시작 직후처럼 엔티티가 아직 안 올라온 구간에선 청크 로드마다 저장이 연달아 터진다.
- `guild/GuildGui.java:161` 의 `world.getBlockAt(...)` 은 **다른 청크를 동기 로드시킬 수 있다** — 청크 로드 처리 중에 또 청크 로드(연쇄).

**해결**
1. 좌표 컬렉션을 **청크키 인덱스**로 바꾼다. `Map<Long, List<Node>>`, 키 = `(long)cx << 32 | (cz & 0xffffffffL)`.
   순회 786 → 그 청크 노드 0~3개(prod 786노드가 ~700청크에 흩어져 있다). forage/collectible/trap/zipline 전부 같은 처방.
2. `saveNodes()` 를 **dirty 플래그 + 주기 저장**(예 600틱)으로 디바운스. 이벤트 안에서 직접 쓰지 않는다.
3. `GuildGui` 는 `getBlockAt` 대신 좌표 비교(`x>>4 == cx`)로 먼저 거른다. 블록 접근은 그 뒤에.
4. `ForageManager.onChunkLoad` 가 청크마다 `runTask` 를 새로 예약하는 것도 없앤다(스케줄러 큐 churn).

### S2. 디스크 I/O가 전부 메인스레드 — 그중 하나는 15틱 태스크가 트리거한다
`runTaskAsynchronously` 는 **전 코드에 3곳뿐**이고, `Files.write`/`FileWriter` 계열은 38곳 전부 동기다.

가장 나쁜 건 `trap/TrapManager.java:179`:
```java
private void sendNearbyStatus() {   // 15틱(0.75초)마다
    ...
    if (dirty) save();              // ← 여기서 JSON 디스크 쓰기
}
```
통발이 완료 상태로 넘어가는 순간마다 0.75초 주기 태스크 안에서 파일을 쓴다.

**해결** — 공용 `JsonStore` 하나로 정리: `markDirty()` 만 하고, 실제 쓰기는
① 주기 태스크(예 600틱)에서 **직렬화는 메인, 쓰기는 async** ② `onDisable` 즉시 flush.
`PlayerDataManager` 는 이미 dirty 기반이라 그 패턴을 그대로 확장하면 된다.

### S3. `nearbyOwnTrapKey` — 플레이어 × 전체 통발, 0.75초마다
`trap/TrapManager.java:481`. 플레이어마다 전체 통발을 돌며 `Location.distance()`(제곱근 + `new Location` 할당).
**해결**: 소유자 UUID → 통발 인덱스, `distanceSquared` 사용, 월드 먼저 거르기.

---

## A급 — 인원이 늘면 선형으로 무너지는 것

### A1. 플레이어 1명당 초당 고정 작업량이 이미 크다
전부 `Bukkit.getOnlinePlayers()` 전수 루프다:

| 태스크 | 주기 | 초당 |
|---|---|---|
| `bgm/BgmManager` followAll | 2틱 | 10 |
| `nav/NavigationManager` tick | 2틱 | 10 |
| `economy/CashEffectManager` tickWings | 2틱 | 10 |
| `mining/MiningHatManager` tick | 2틱 | 10 |
| `harpoon/HarpoonManager` tick | 2틱 | 10 |
| `npc/NpcAnimator` look | 2틱 | 10 |
| `npc/NpcGazeManager` tick | 3틱 | 6.7 |
| `region/RegionParticleTask` tick | 5틱 | 4 |
| `bgm/BgmManager` tickAll | 5틱 | 4 |
| `sidebar/SidebarManager` · `region/RegionTracker` | 20틱 | 각 1 |

합쳐서 **플레이어당 초당 ~77회**의 전용 순회다. 100명이면 초당 7,700회 —
각 순회가 지역판정·엔티티스캔·패킷생성을 하니 실제 비용은 그 몇 배다.

**해결** — 구조를 바꾸는 게 답이지 주기만 늘리는 게 아니다.
1. **관심 없는 플레이어를 루프 진입 전에 버린다.** wings/harpoon/mining/nav 는 해당 상태인 플레이어 집합(`Set<UUID>`)만 돌면 된다. 지금은 전원을 돌고 안에서 `continue` 한다.
2. **틱 분산(stagger)**: 플레이어를 `entityId % N` 으로 나눠 틱마다 1/N만 처리. 체감은 같고 스파이크가 사라진다.
3. NpcGaze·NpcAnimator·BGM follow 는 같은 "플레이어 주변 상태" 를 각자 다시 계산한다 — **공용 per-player 컨텍스트**(위치·지역·주변 NPC)를 1틱 캐시로 만들어 공유.

### A2. `RegionManager.getRegionAt()` — 캐시 0, 호출마다 재할당
`region/RegionManager.java:484`. 호출처 19곳 + 위 틱 태스크들(파티클 4/s, BGM 4/s, 트래커 1/s …).
매 호출마다 지역 35개를 돌고, 폴리곤 지역(24개)에서 `getPolygonSections()`(`RegionData.java:223`)가
**호출마다 새 `ArrayList` 를 섹션 수만큼 만들고 `subList` 를 복사**한다. `computeAreaXZ()` 도 매번 다시 계산한다.
(3D 볼록껍질 `pairHulls()` 는 캐시돼 있다 — 여긴 잘 돼 있음.)

**해결**
1. `getPolygonSections()` 결과와 `computeAreaXZ()` 결과를 `RegionData` 에 캐시(폴리곤 편집 시 무효화). 지금 `pairHullCache` 가 하는 것과 같은 패턴.
2. 플레이어별 **블록좌표 기억 캐시**: 직전 판정 블록좌표와 같으면 지역 재판정을 건너뛴다. 가만히 있거나 한 블록 안에서 움직이는 대부분의 시간이 공짜가 된다.
3. 월드별로 지역 목록을 미리 나눠 둔다(지금은 매 호출 문자열 비교로 거른다).

### A3. 파티클을 개별 호출로 뿌린다 (패킷 폭탄)
- `region/RegionParticleTask.java:240` — `count` 만큼 루프 돌며 `base.clone()` + `spawnParticle(..., 1, ...)`. 폭풍은 더 많다.
- `economy/CashEffectManager.java:407` `drawWing` — 날개 좌표 리스트 길이만큼 개별 `spawnParticle`, **2틱마다**.

**해결**: 마인크래프트 파티클 패킷은 `count` + `offset` 으로 **한 번에 흩뿌릴 수 있다**.
랜덤 오프셋 루프는 대부분 `spawnParticle(p, center, count, dx, dy, dz, speed)` 한 방으로 대체된다.
모양이 있어야 하는 날개만 개별 좌표를 유지하되 주기를 4틱으로 내리고 `Location` 재사용.

---

## B급 — 상황 의존, 그러나 실재

| # | 위치 | 문제 | 해결 |
|---|---|---|---|
| B1 | `lock/ChestLockManager.java:447`, `vote/MineListVoteRewardManager.java:172` | `Bukkit.getOfflinePlayers()` 전수 — usercache 전체를 훑는다. 표지판 이름 해석마다 발생 | 이름→UUID 캐시 맵을 1회 구축해 재사용 |
| B2 | `BlockShipPlugin.java:1435` | 2분마다 전 플레이어 인벤 36칸의 물고기 **전부** ItemMeta 재생성 + `setItem` (인벤 갱신 패킷) | 신선도 구간(%)이 실제로 바뀐 아이템만 교체 |
| B3 | 이벤트 밀도 | 우클릭 1회 = `PlayerInteract` 핸들러 **32개** 통과, 블록 파괴 = 27개 | 핸들러 첫 줄에서 월드/아이템으로 즉시 탈출(early return) 일관 적용, `ignoreCancelled=true` 활용 |
| B4 | `npc/NpcGazeManager.java:62` | 3틱마다 플레이어별 `getNearbyEntities(9,9,9)` — 엔티티 밀집 구역에서 비쌈 | NPC는 거의 안 움직인다 → 청크키 인덱스로 주변 NPC를 O(1) 조회 |
| B5 | `region/RegionTracker.java:129` | guild_world 이탈 판정이 `dispatchCommand("execute in ... run tp")` — 명령 파싱 비용 | 크로스월드가 아니면 `player.teleport()` 로 충분(같은 월드 이동은 동작함) |
| B6 | 데이터 크기 | `telemetry/` 8.1MB, `recipes.json` 430KB, `dialogue.json` 482KB + **백업 사본 10개 이상이 같은 폴더** | 백업(`dialogue.json.pre-*`)을 `backups/` 로 이동 — 폴더 스캔·오배포 위험 감소 |

---

## 좋았던 것 (되돌리지 말 것)

- 텔레메트리 쓰기는 **전용 `Thread` + `LinkedBlockingQueue`** 로 이미 분리돼 있다(`telemetry/TeleWriter.java:34`). 이 패턴이 정답이고, S2를 고칠 때 그대로 복제하면 된다.
- `PlayerDataManager` 는 dirty 기반 부분 저장이고 파일이 플레이어별로 쪼개져 있다.
- `RegionData.pairHulls()` 는 캐시돼 있다.
- GUI 디스패치가 타이틀 문자열 비교가 아니다(1곳뿐).
- `PlayerMoveEvent` 핸들러가 5개뿐이다 — 흔한 대형 함정을 피했다.
- `ShipTickTask` 는 배가 없으면 사실상 공짜다.

---

## 권장 순서

1. **S1 청크키 인덱스** (forage → collectible → trap → zipline). 가장 크고, 가장 국소적인 수정.
2. **S2 dirty+async 저장 공용화**, S3 함께.
3. **A2 지역 판정 캐시** — A1의 비용 상당 부분이 여기서 자동으로 줄어든다.
4. **A1 관심집합 + stagger**, A3 파티클 배치화.
5. B급은 여유 있을 때.

검증은 추측 말고 **spark**(`/spark profiler start`)로 전후를 뜨는 게 맞다.
지금 prod 에 spark 가 없다면 그것부터 넣는 게 이 목록 전체보다 먼저다.


---

# 정정 및 실측 (2026-08-17 저녁, 수정 반영 후)

## ★수치 정정 — 채집 노드는 7,092개가 아니라 786개다
최초 집계 스크립트가 `sum(len(v) for v in d.values())` 로 세는 바람에
**노드 788개 × 필드 9개 = 7,092** 을 노드 수로 잘못 읽었다.
prod 실측: 채집 노드 **786** · 통발 **1** · 수집품 **81** · 짚라인 **6**.

영향: S1 의 방향과 처방은 그대로 유효하지만 **절대 규모는 9배 작다**.
S2·S3(통발)는 현재 데이터(통발 1개)에서는 사실상 이득이 없는 **잠재적 위험 제거**다
— 통발 수에 비례해 커지는 구조를 고친 것이지, 지금 느린 걸 고친 게 아니다.
커밋 `46c5ec6`·`f15ba9b` 메시지에는 옛 수치(7,092)가 남아 있다.

## dev 실측 (배포 후 부팅 로그)
```
[채집] 종류 31 / 노드 788 로드 (월드 1 · 청크 711곳)
```
- 인덱스 자가대조 경고 **없음** — 788개 전부 제 청크에서 조회된다.
- 청크 711곳은 JSON 을 파이썬으로 따로 세어 얻은 값과 **정확히 일치**한다(교차검증).
- 부팅 중 우리 코드발 예외 0건(로그의 ERROR 3건은 GrimAC SLF4J 경고, 무관).

## 효과 추정 — 접속자 100명 기준, 전부 **모델 계산**이다
실측 프로파일이 아니다. spark 도입 전까지 아래 숫자는 "제거된 연산/할당 횟수"이지
"빨라진 ms" 가 아니다.

| 수정 | 이전 (추정/초) | 이후 (추정/초) | 성격 |
|---|---|---|---|
| 짚라인 10초 전역 스캔 | 전 월드(9개) 로드청크×엔티티를 10초마다 — 스파이크성 수만 방문 | 좌석 목록(대개 0) | **주기적 스터터 제거** |
| forage 청크로드 순회 | 786 × 청크로드율 (~157k 방문/s @200청크/s) | ~400 해시조회 | 탐험 중 부하 |
| forage 청크로드 JSON 쓰기 | 복구 폭풍 시 222KB 쓰기 반복 | 30초 1회 | **프리즈 원인 제거** |
| getRegionAt 섹션 할당 | ~43,000 ArrayList 할당 | 0 (캐시) | **GC 압력** |
| getRegionAt 지오메트리 판정 | ~31,500 지역 테스트 | 정지 중이면 ~0 (LRU) | CPU |
| NpcAnimator.tickLook | ~30,000 Location 할당 + ~60,000 메타/태그 조회 | 스냅샷 100 할당 | **GC 압력** |
| NpcGazeManager | ~667 AABB 질의(각 수백 엔티티 방문) | ~8,200 단순 연산 | CPU (전제 성립 시) |
| 지역 파티클 | ~4,000 개별 호출 + 동수 Location | ~400 | 패킷·할당 |
| 날개 파티클 | 착용자당 450 호출 | 225 | 패킷 |
| 신선도 갱신 | 2분마다 전 물고기 인벤 갱신 패킷 | 변화분만 | 패킷 |
| 타이머 위상 | 10분마다 30여개 동시 발화 | 분산 | 스파이크 평탄화 |

**요약**: 초당 10⁵ 규모의 연산·할당을 걷어냈고, 성격은 대부분 **GC 압력과 주기적
스파이크** 다. 4코어 ARM 에서 이 둘은 평균 TPS 보다 체감(스터터)에 크게 작용한다.
다만 **현재 베타 동시접속 수에서는 대부분 잠재적 이득** 이다 — 위 수치는 전부
100명 가정이고, 실제 이득은 동시접속에 비례한다.

**여전히 미측정**: 실제 TPS/MSPT 개선폭. prod 에 spark 를 넣고 전후를 뜨기 전까지
이 표는 근거 있는 추정일 뿐 증명이 아니다.


## B3 정정 — 「핸들러 32개 통과」는 비용이 아니었다 (기각)

B3 은 핸들러 **개수**를 비용의 대리지표로 삼았다. 전수로 열어 보니 틀렸다.

| 확인 | 결과 |
|---|---|
| PlayerInteract·BlockBreak·BlockPlace 핸들러 59개 중 값싼 가드 없이 곧장 비싼 호출 | **0개** |
| 그중 `ignoreCancelled=true` 사용 | 36개 |
| `BlockPhysicsEvent` 핸들러 (버킷 최악의 함정) | **0개** |
| `PlayerMoveEvent` 5개의 첫 줄 | 전부 블록경계/Y/세션 가드 |
| `BlockFromToEvent` 2개 | 하나는 월드명 비교가 첫 줄, 하나는 아래 건 |

즉 이 코드베이스는 이벤트 핸들러 규율이 이미 서 있다. 개수가 많은 건
`InventoryClickEvent` 65개인데, 그건 사람 손 속도로만 터지므로 부하와 무관하다.

**유일한 실소득**: `island/IslandFarmlandCounter.mark(Block)` 이
`chunkIndex.isEmpty()` 가드보다 **먼저** `b.getLocation()` 을 불렀다. 이 오버로드는
물·용암 흐름·설치·파괴·피스톤·폭발에 물려 있어 평상시에도 계속 불리는데, 그때마다
Location 을 만들어 첫 줄에서 버렸다. 가드를 앞으로 옮겼다(`3fc27d5`).

## 이 감사에서 내가 틀렸던 것 (기록)
1. **채집 노드 7,092 → 786** — 집계 스크립트가 필드 수를 곱해 셌다.
2. **A1 관심집합** — `getEquipped`(해시 2회)·`isMiningHat`(타입 早期탈출)은 이미 공짜였다.
   그 77회/초 중 실제로 비쌌던 건 NPC 두 곳뿐이었다.
3. **B3** — 위와 같이 기각.
4. **ChunkLoadEvent "8겹"** — collectible 81·trap 1·zipline 6 이라 forage 외엔 작았다.
5. **놓친 것**: `ZiplineManager` 의 10초 전역 엔티티 스캔. 병렬 세션이 잡아 줬고,
   실측 규모로는 이번에 고친 것 중 단일 최대 건이었다.

교훈: **개수·크기를 비용의 대리지표로 쓰지 말 것.** 다섯 중 넷이 그 실수였다.
