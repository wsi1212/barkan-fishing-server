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
| 채집 노드 | **7,092개** (`forage-nodes.json` 222KB) |
| NPC | 330명 · 지역 35개(폴리곤/3D 24개) |

---

## S급 — 지금 터질 수 있는 것

### S1. ChunkLoadEvent 하나에 전수순회가 8겹으로 붙어 있다
`forage/ForageManager.java:838` → `repairChunk()`가 **청크 하나 로드될 때마다 노드 7,092개를 전부 순회**한다.
같은 이벤트에 7개가 더 붙어 있다:

| 위치 | 청크 로드 1회당 하는 일 |
|---|---|
| `forage/ForageManager.java:846` | 노드 **7,092개** 전수 |
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
   순회 7,092 → 그 청크 노드 0~3개. forage/collectible/trap/zipline 전부 같은 처방.
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
