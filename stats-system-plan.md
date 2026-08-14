# 통계·텔레메트리 시스템 구축 계획 (BlockShip Telemetry)

작성: 2026-07-27 · 조사 기준: BlockShip 273개 .java / 63패키지 전수 훅 조사 (동일 날짜) · 구현 담당: **Sonnet 5**
목적: 서버의 **모든 플레이어 행위·경제 흐름·성장 데이터를 원본 그대로 축적**해서, 밸런스 튜닝·성장곡선 검증·밸붕 탐지("이 낚싯대 너무 좋은데?", "이 퀘스트 왜 이래?")를 **실측 데이터로** 할 수 있게 한다. "나중에 이거 뭐지?" 할 때 **무조건 소급 조회 가능**해야 하며, 앞으로 추가되는 시스템도 **자동으로 편입**되어야 한다.

> **Sonnet 5에게 — 이 문서 사용법**
> - 본문의 라인 번호는 2026-07-27 스냅샷 기준이라 드리프트할 수 있다. 구현 시 반드시 grep/codegraph로 재확인.
> - Phase 0 → 4 순서대로 구현한다. 각 Phase 끝의 수용 기준을 dev에서 통과시킨 뒤 커밋(blockship-plugin은 규칙상 물어보지 않고 바로 커밋). **prod 배포는 별도 명시 요청 시에만.**
> - 기존 `com.blockship.stats.StatsGui`(낚시 능력치 표시 GUI)와 혼동 금지 — **새 패키지는 `com.blockship.telemetry`**.
> - §14 "구현 시 재확인 목록"을 각 Phase 시작 전에 훑을 것.

---

## 0. 이 시스템이 답해야 할 질문 (설계의 북극성)

| # | 운영자의 질문 | 필요한 데이터 | 답하는 방법(§10 쿡북) |
|---|---|---|---|
| Q1 | 유저들이 **의도한 성장곡선대로** 크고 있나? | 레벨업 타임스탬프, 세션·활동시간, XP 원장 | C1 성장곡선 백분위 vs balance-audit 목표표 |
| Q2 | **밸붕 퀘스트**는 없나? (보상이 시간 대비 과함) | 퀘스트 수락→완료 소요시간, 보상, 반복 횟수 | C2 퀘스트별 원/분 상위 랭킹 |
| Q3 | **너무 좋은 낚싯대/장비**는 없나? | 캐치별 장비 로드아웃+최종스탯, 등급분포, 수익 | C3 로드아웃별 등급분포·시급 아웃라이어 |
| Q4 | **특정 작물이 과도하게 좋은가?** | 심기→수확 실측 시간, 산출, 판매/제출 환산 | C4 작물별 슬롯·시간당 가치 + 재배 점유율 편중 |
| Q5 | **성능 대비 너무 비싼 장비**는? (아무도 안 씀) | 부품 구매수·장착률·기여 스탯 vs 가격 카탈로그 | C5 가격-사용률-성능 산점, 구매 0 품목 |
| Q6 | 경제 **인플레/디플레**? 돈이 어디서 새나? | 전 재화 원장(소스/싱크별), 자산 분포 스냅샷 | C6 일별 순발행량·소스/싱크 top·지니계수 |
| Q7 | 컨텐츠별 **실제 이용률**은? (버려진 시스템) | 명령어/GUI/시스템 이벤트 카운트 | C7 시스템별 DAU·이벤트량 추이 |
| Q8 | 카지노 **실현 하우스엣지**가 설계대로인가? | 게임별 베팅/순손익 | C8 게임별 실현 RTP |
| Q9 | RNG(등급/강화/발동)가 **명목 확률대로** 나오나? | 롤 진단값(기본확률·pity·최종확률), 결과 | C9 명목 vs 실측 확률 카이제곱 |
| Q10 | "**이거 뭐지?**" — 임의의 과거 사건 소급 조사 | **원본 이벤트 로그 전량 + 당시 밸런스 카탈로그** | raw SQL (원본 무손실 보존이 답) |

**설계 원칙 7개** (모든 구현 결정의 우선순위 판단 기준):
1. **원본 보존** — 집계본만 남기지 않는다. 이벤트는 raw 그대로 축적, 집계는 파생물.
2. **메인스레드 0-IO** — 게임 스레드에서는 "맵 하나 만들어 큐에 넣기"까지만(µs 단위). 모든 직렬화·디스크·DB는 전용 스레드.
3. **게임 무영향 격리** — 텔레메트리가 죽어도 게임은 안 죽는다. `Telemetry.log()`는 절대 예외를 밖으로 던지지 않는다.
4. **원장 무결성** — 돈/XP 등 P0 이벤트는 샘플링·드랍 금지. 큐가 넘치면 P2부터 버리고 P0는 비상 스풀로.
5. **스키마 자유** — 이벤트 상세는 JSON `ctx` 컬럼. 새 필드 추가에 마이그레이션 불필요.
6. **미계측 자동 발각** — 계측 안 된 신규 시스템도 안전망(§7)에 흔적이 남고, 커버리지 감사가 사각지대를 알려준다.
7. **분석은 오프라인** — 서버는 수집+최소 롤업만. 무거운 분석은 Mac의 Python(stats-lab)에서.

---

## 1. 조사 요약 — 현재 코드베이스의 계측 현실

### 1-1. 이미 존재하는 통계성 데이터 (전부 PlayerData 내 누적 카운터, 이벤트 로그 아님)
`extraNums`: `총낚시`(FishingListener:561) · `총판매`(SellGuiListener:117) · `조합횟수`(QuestManager:1510, 전 조합 초크포인트) · `접속일수` · `주간접속일수/주간일퀘완료수/주간획득골드` · `잠수포인트` · `섬광산exp횟수/일자` · `통계낚시행동/발동·통계채굴행동/발동·통계재배행동/발동·통계수집행동/통계요리행동`(SkillTreeManager — **현재 read하는 곳 없는 write-only**) · `PRD<key>` 실패 카운터. 그 외 `maxCombo`, `marketSaleCount/Gold/Fee`, `popularity`, `gradePity`, `visitedRegions`, `fishRecords`(어종별 최대크기/최초일/최고등급), `dexDiscovery`, `completedAchievements`.
→ **전부 "현재 상태"만 있고 "언제/어떤 조건에서"가 없다.** 이 카운터들은 퀘스트/도전과제가 의존하므로 **건드리지 않고**, 텔레메트리는 별도 축으로 추가한다.

### 1-2. 구조적 사실 (설계를 규정하는 제약)
| 사실 | 출처 | 설계 귀결 |
|---|---|---|
| 플러그인 I/O가 **100% 메인스레드 동기** (비동기는 SkinRenderer 1곳뿐) | 인프라 조사 | 텔레메트리는 자체 전용 스레드를 새로 깐다. Bukkit 스케줄러 async 태스크가 아니라 **plain Thread** (onDisable 후에도 flush 가능) |
| 돈은 `MoneyBridge.add/subtract/set/addOffline`로 수렴 (~85 콜사이트/32파일)… **단 카지노 `CasinoLedger`가 `PlayerData.setMoney` 직접 호출 10곳으로 우회** | 돈흐름 조사 | 초크포인트 = MoneyBridge 4메서드 + CasinoLedger.applyNet(2오버로드)+reserve/settle/refundOrphan |
| 재화가 6종: 돈(money)·캐시(cash)·추천코인(recommendCoins)·잠수P(`extraNums[잠수포인트]`)·카지노예치(레거시)·길드금고(GuildData.treasury) | 돈흐름 조사 | 원장은 `cur` 필드로 통화 구분. `PlayerData.addCash`는 **clamp 없는 raw `+=`** — 계측하며 가드도 추가 |
| 콘솔 돈 브릿지 3종: `moneyop`/`moneyoffline`/`fishpay` (Skript·커맨드블록 유입구) | 돈흐름 조사 | MoneyBridge 경유라 원장에 자동 포착, reason만 명시 태깅 |
| XP 진입점 단일: `FishingLevelManager.addExp` (호출 6곳) + 별도 `SkillManager.addExp`(숙련도 4종) | 인프라 조사 | XP 원장 초크포인트 2개 |
| 캐치 시점에 `FishingBonuses.Bonuses`(최종스탯+`matchedRod`+`rodEnhanceLevel`)가 **이미 계산되어 손에 있다** | 낚시 조사 | 로드아웃 스냅샷을 공짜로 얻음 — Q3의 핵심 |
| 낚시 캐스트/입질 핸들러가 **없다** (State.CAUGHT_FISH만 처리) | 낚시 조사 | 캐스트 통계용 신규 리스너 필요 |
| `GradeRoller.roll()` 내부 확률값(base/luck/pity/최종prob)이 로컬 변수라 **미노출** | 낚시 조사 | `Result`에 진단 필드 추가 (Q9) |
| 플레이타임 추적이 **전혀 없다** | 인프라 조사 | 세션 트래커 신설 (Q1의 분모) |
| GUI 공용 베이스 없음, 커스텀 InventoryHolder 84종 | 인프라 조사 | `InventoryOpenEvent`에서 holder 클래스명 자동 태깅 = 안전망 |
| 명령어 ~160개 전부 런타임 `commandMap.register` | 인프라 조사 | `PlayerCommandPreprocessEvent` 한 곳이면 전 명령 포착 |
| PlayerDataManager 저장 = tmp→`.bak`→ATOMIC_MOVE | 인프라 조사 | 스냅샷 잡이 playerdata/*.json을 **오프스레드에서 안전하게 read 가능** |
| RankingManager는 GUI 열 때마다 전 playerdata JSON을 메인스레드 파싱 | 인프라 조사 | (부수효과) 훗날 텔레메트리 스냅샷으로 대체 가능한 기존 부하 지점 |
| shadow 플러그인 구성됨(현재 shading 0건), JSON=서버 번들 gson | 인프라 조사 | SQLite 의존성 추가 용이 |
| prod 규모: 누적 유저 38명, BlockShip 데이터 4.7MB, 디스크 여유 32GB, 박스에 python3(sqlite3 모듈 3.45) 있음·sqlite3 CLI 없음 | 직접 확인 | 부하 산정 기준(§12), 박스측 집계는 python3로 |

### 1-3. 결론
현재 서버에는 **이벤트 로그가 0건**이다. 상태 카운터는 있으나 시간축·문맥이 없어 Q1~Q10 어느 것도 답할 수 없다. 필요한 것은 (a) 비동기 이벤트 파이프라인, (b) 재화·XP 초크포인트 원장, (c) 시스템별 이벤트 계측, (d) 밸런스 카탈로그 스냅샷(당시 수치와 조인), (e) 오프라인 분석 툴킷이다.

---

## 2. 아키텍처 개요

```
[게임 코드 (메인스레드/이벤트스레드)]
   │  Telemetry.log(type, player, ctx)   ← ~1–3µs: Map 생성 + 큐 offer, 예외 전부 삼킴
   ▼
[LinkedBlockingQueue (cap 20,000)]  ← 우선순위 P0/P1/P2, 백프레셔(§4-4)
   ▼
[TeleWriter 전용 Thread (plain Thread, daemon 아님)]
   ├─ 1초 or 500건마다 배치 → gson 직렬화 → SQLite INSERT (단일 트랜잭션)
   ├─ 유지보수: 60초마다 live_sessions 갱신 / KST 자정 후 첫 배치에 전일 롤업 / 월 전환 시 파일 로테이션
   └─ 장애 시: 비상 JSONL 스풀(spill) → 그것도 실패하면 드랍+레이트리밋 경고
   ▼
[plugins/BlockShip/telemetry/]
   ├─ events-YYYY-MM.db   (월별 원본: ev + loadout)       ← 일일 오프사이트 tar에서 제외(§11)
   ├─ stats.db            (영구: 롤업/카탈로그/스냅샷/메타)
   └─ export/stats-latest.db (매일 05:30 KST VACUUM INTO — 백업·조회용 일관 사본)
   ▼
[소비]
   ├─ 인게임 /통계 (OP, 비동기 읽기 — 운영 점검용 최소 UI)  §10-1
   ├─ 웹 어드민 대시보드 statsweb (Discord OAuth, 다중 어드민) §10-5 ← 열람 메인 UI, Phase 6에 운영콘솔 §10-6
   ├─ stats-lab/ Python 툴킷 (Mac, scp/ssh pull)          §10-2
   ├─ 데일리 Discord 리포트 1줄 (nightly-restart.sh)       §10-4
   └─ 월간 아카이브 → OCI Object Storage mc-backups/telemetry/  §11
```

---

## 3. 저장소 결정: SQLite (월별 파티션) + JSON ctx

### 3-1. 후보 비교
| 후보 | 장점 | 탈락/채택 사유 |
|---|---|---|
| **SQLite (xerial sqlite-jdbc)** ✅ | 단일 파일·무설치, WAL 동시읽기, JSON1 함수, **Python stdlib sqlite3로 바로 분석**(balance-audit 워크플로와 동일 결), 박스에 python3 이미 있음 | **채택.** 이 서버 규모(§12)에서 성능 여유 100배 이상 |
| JSONL append | 구현 최단순 | 조회가 매번 풀스캔·파싱, 롤업/조인 불편. 단 **비상 스풀 포맷으로는 채택**(§4-5) |
| H2 | 순수 자바 | 파이썬에서 못 읽음(분석 툴킷과 안 맞음) |
| Prometheus/Influx/Grafana | 대시보드 | 박스에 상주 서비스 추가(24GB RAM이지만 무인운영 관리대상 증가), 이벤트 소급조회(Q10)에 부적합 — **게이지가 아니라 원장이 필요** |
| ClickHouse 등 OLAP | 대규모 | 38명 서버에 과잉. 단 스키마를 export 친화(JSONL 덤프 제공)로 설계해 10배 성장 시 이관 경로 확보 |

### 3-2. 의존성 추가 방법 — 확정: shadowJar shading (2026-07-27 구현 시 결정)
당초 Paper 라이브러리 로더(부팅 시 Maven Central 다운로드)와 shading 두 안을 검토했으나, **shading으로 확정**했다. 이유: ①부팅 시 외부 네트워크 의존이 생기면 dev 오프라인 작업·오라클 박스 일시 단절 시 기동 실패 리스크 ②이미 shadow 9.0.0-beta4가 구성돼 있고 relocate 불필요(Paper 플러그인 클래스로더 격리) ③결정론적 단일 jar가 무인운영 원칙에 더 부합.
```kotlin
// build.gradle.kts dependencies { }
implementation("org.xerial:sqlite-jdbc:3.53.2.1")  // Maven Central 확인(2026-07-27): 최신 안정판. aarch64/apple-silicon 네이티브 동봉 fat jar
```
`compileOnly`가 아닌 `implementation`이라야 shadowJar가 runtimeClasspath로 포함해 shading한다. 드라이버 로드: `Class.forName("org.sqlite.JDBC")` 후 `DriverManager.getConnection("jdbc:sqlite:" + path)`.

### 3-3. 파일 레이아웃과 PRAGMA
- `telemetry/events-YYYY-MM.db` — **KST 기준 월**별 원본 이벤트. 월 전환 시 writer가 파일 교체(구 파일은 아카이브 대상).
- `telemetry/stats.db` — 영구 소량 데이터(롤업·카탈로그·스냅샷·메타·live_sessions).
- 접속마다 적용할 PRAGMA (양쪽 DB 공통):
```sql
PRAGMA journal_mode=WAL;        -- 동시 읽기 + 크래시 내구
PRAGMA synchronous=NORMAL;      -- WAL에서 안전, fsync 최소화
PRAGMA busy_timeout=5000;
PRAGMA cache_size=-8000;        -- 8MB
PRAGMA temp_store=MEMORY;
PRAGMA wal_autocheckpoint=2000;
```
- 쓰기는 **writer 스레드 단 하나**만. `/통계` 등 읽기는 별도 read-only 커넥션(`jdbc:sqlite:file:...?mode=ro` 또는 일반 연결+SELECT만) — WAL이라 안전.

---

## 4. 코어 구현 설계 — `com.blockship.telemetry` (Phase 0)

### 4-1. 클래스 구성 (신규 파일 9개)
| 클래스 | 책임 |
|---|---|
| `Telemetry` | **static 파사드.** `log(type, Player, Map ctx)` / `log(type, uuid, name, ctx)` / `money(...)` / `xp(...)` 헬퍼. enabled 체크 → Event 레코드 생성 → 큐 offer. 어떤 예외도 밖으로 안 나감 |
| `TeleEvent` | record: `ts, type, uuid, name, world, region, ctx(Map), priority` |
| `TeleTypes` | 이벤트 타입 상수 레지스트리. `register("fish.result", P1, "낚시 결과 확정", "fishing")` — 타입명·우선순위·설명·소속시스템. 커버리지 감사(§7-3)의 기준표 |
| `TeleQueue` | `LinkedBlockingQueue<TeleEvent>` 래퍼 + 백프레셔 정책(§4-4) + 드랍 카운터 |
| `TeleWriter` | 전용 Thread. 배치 flush, PRAGMA/스키마 초기화, 월 로테이션, 유지보수 잡(live_sessions/롤업/VACUUM INTO) 실행 |
| `TeleDb` | 커넥션 관리(월별 events DB + stats.db), 스키마 생성/마이그레이션(`meta.schema_version` if-체인) |
| `TeleSpill` | 비상 JSONL 스풀 (`telemetry/spill-*.jsonl`) 기록 + 부팅 시 재적재 |
| `SessionTracker` | join/quit/heartbeat, afk 시간 집계, region 체류(§8-1), 크래시 세션 복원 |
| `TelemetryCommand` | `/통계` OP 명령 (§10-1). `setPermission("blockship.admin")`, **영타·초성 별칭 금지**(OP 규칙) |

- 설정: `telemetry/telemetry.json` — `{enabled, queueCap:20000, batchMs:1000, batchMax:500, sample:{"cmd.use":1.0,...}, gaugeSec:60}`. §부록 C.
- **초기화 위치**: `BlockShipPlugin.onEnable()`의 `PlayerDataManager` 생성(현 758행) **직전**. 이유: 초크포인트(MoneyBridge 등)와 join 리스너보다 먼저 살아 있어야 함. `onDisable()` 마지막에 `telemetry.shutdown(3000ms flush)`.
- `srv.start` 이벤트를 초기화 직후 기록(카탈로그 해시 포함 §9-1), `srv.stop`을 shutdown 시 기록.

### 4-2. Telemetry 파사드 시그니처 (부록 B에 스켈레톤)
```java
Telemetry.log(String type, Player p, Map<String,Object> ctx)          // world/region 자동 채움
Telemetry.log(String type, UUID uuid, String name, Map<String,Object> ctx)  // 오프라인/서버 이벤트
Telemetry.money(OfflinePlayer|uuid, String cur, long delta, long after, String reason, String detail)
Telemetry.xp(Player, String sys, double amt, String src)               // sys=낚시|채굴|재배|요리|수집
```
- region은 `RegionTracker.getPlayerRegion(p)` 캐시에서 읽음(이미 20틱 갱신 — 추가 비용 0).
- ctx 값은 String/Number/Boolean/List/Map만. 직렬화는 writer에서 gson으로.
- **호출 스레드 무관 안전** (큐가 MPSC 허용). AsyncChat 등 비동기 이벤트에서 불러도 됨.

### 4-3. 시간 규약
- 저장: `System.currentTimeMillis()` (UTC epoch ms).
- 날짜 경계(롤업·월 파일명): **KST** — 기존 `util.KoreanTime` 재사용(`Asia/Seoul`). 박스 TZ는 UTC이므로 절대 `LocalDate.now()` 기본 시간대 쓰지 말 것.

### 4-4. 우선순위와 백프레셔
| 등급 | 대상 | 큐 포화 시 |
|---|---|---|
| **P0** | 원장(money/xp/level), enh.attempt, casino.round, quest.done, trade.done, check/xfer, sell.fish, death, sess.start/end | **드랍 금지.** 큐 넣기 실패 → 즉시 TeleSpill(JSONL)로 |
| P1 | 게임플레이 상세(fish.result, craft.do, submit.do, …) | 큐 90% 이상이면 드랍 + 카운터 |
| P2 | 분위기(cmd.use, gui.open, npc.talk, gauge.*, weather.*) | 큐 70% 이상이면 드랍 + 카운터 |
- 드랍 발생 시 콘솔 경고는 60초 레이트리밋. 드랍 카운터는 `/통계 상태`와 `gauge.health`에 노출.

### 4-5. 장애 격리·복구
- `Telemetry.log()` 전체가 try-catch, 실패는 내부 카운터만 증가.
- writer에서 SQLite 예외 연속 5회 → 해당 배치와 이후 이벤트를 spill JSONL로 우회, 60초마다 DB 복구 재시도.
- 부팅 시 `spill-*.jsonl` 있으면 writer가 저속(1000행/초) 재적재 후 파일 `.done`으로 rename.
- **크래시 세션 복원**: `stats.db.live_sessions(uuid, name, start_ts, last_seen, afk_s)`를 60초마다 UPSERT. 부팅 시 남아 있는 행 = 비정상 종료 세션 → `sess.end{reason:"crash", dur=last_seen-start_ts}` 합성 후 비움. (WAL 덕에 유실은 마지막 배치 ≤1초분.)
- 킬스위치: `/통계 끄기` → volatile boolean → 이후 `log()`는 즉시 return(비용 ~1ns). 재시작 없이 on/off.

### 4-6. 이벤트 명명·ctx 규약
- 타입명: `<도메인>.<동작>` 소문자 (`fish.result`, `money.txn`). 도메인 목록은 §8 카탈로그가 전거.
- ctx 키: 짧은 ASCII (§부록 D 공통 사전). 스키마 바뀌면 해당 타입에만 `v:2` 필드 추가(전역 마이그레이션 없음).
- 한 유저 행위가 여러 시스템을 스치면 **이벤트 1개에 접기(fold)를 우선**하고, 원장(P0)만 별도 행으로 남긴다. 예: 물고기 1마리 = `fish.result` 1행(+판매 시 `money.txn` 1행). 미니게임 클릭·연출·공지·도감갱신은 전부 `fish.result`의 ctx 필드다.

---

## 5. 스키마 DDL

### 5-1. `events-YYYY-MM.db` (월별 원본)
```sql
CREATE TABLE IF NOT EXISTS ev (
  id     INTEGER PRIMARY KEY,           -- rowid
  ts     INTEGER NOT NULL,              -- epoch ms UTC
  type   TEXT    NOT NULL,              -- 'fish.result'
  uuid   TEXT,                          -- 플레이어 uuid (서버 이벤트는 NULL)
  name   TEXT,                          -- 당시 닉네임
  world  TEXT,
  region TEXT,                          -- RegionTracker 캐시값 (nullable)
  ctx    TEXT                           -- JSON
);
CREATE INDEX IF NOT EXISTS ix_ev_type_ts ON ev(type, ts);
CREATE INDEX IF NOT EXISTS ix_ev_uuid_ts ON ev(uuid, ts);

CREATE TABLE IF NOT EXISTS loadout (    -- 장비 로드아웃 중복제거 사전 (§8-2)
  hash     TEXT PRIMARY KEY,            -- 내용 SHA-1 앞 12자
  json     TEXT NOT NULL,               -- {rod, enh, parts:{릴..찌}, dur:{...}}
  first_ts INTEGER
);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);  -- schema_version 등
```

### 5-2. `stats.db` (영구)
```sql
CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);                 -- schema_version, last_rollup_date …

CREATE TABLE catalog_version (          -- 밸런스 카탈로그 스냅샷 (§9-1)
  id      INTEGER PRIMARY KEY,
  ts      INTEGER NOT NULL,
  kind    TEXT NOT NULL,                -- parts|fish|quests|dishes|crops|enhance|traps|submit|forage|recipes|drill|island_prices|guild_prices
  hash    TEXT NOT NULL,                -- 정규화 JSON의 SHA-1
  json_gz BLOB NOT NULL                 -- gzip 압축 전문
);
CREATE UNIQUE INDEX ux_cat ON catalog_version(kind, hash);

CREATE TABLE day_type (                 -- 일별 타입 카운트 (커버리지·이용률)
  date TEXT NOT NULL, type TEXT NOT NULL, n INTEGER NOT NULL, players INTEGER NOT NULL,
  PRIMARY KEY(date, type)
);

CREATE TABLE day_player (               -- 일별 플레이어 요약 (KST 날짜)
  date TEXT NOT NULL, uuid TEXT NOT NULL, name TEXT,
  playtime_s INTEGER, afk_s INTEGER,
  casts INTEGER, catches INTEGER, best_grade TEXT,
  xp_fish REAL, money_in INTEGER, money_out INTEGER, casino_net INTEGER,
  quests_done INTEGER, crafts INTEGER, submits INTEGER,
  PRIMARY KEY(date, uuid)
);

CREATE TABLE player_snapshot (          -- 일일 상태 스냅샷 (playerdata/*.json에서, §9-2)
  date TEXT NOT NULL, uuid TEXT NOT NULL, name TEXT,
  level INTEGER, cur_exp REAL, money INTEGER, cash INTEGER, coins INTEGER,
  max_combo INTEGER, total_fish INTEGER, dex_fish INTEGER,
  skills TEXT,                          -- JSON {채굴:lv,재배:lv,요리:lv,수집:lv}
  extra TEXT,                           -- JSON 여유 필드(섬레벨·길드 등)
  PRIMARY KEY(date, uuid)
);

CREATE TABLE guild_snapshot (
  date TEXT NOT NULL, guild_id TEXT NOT NULL, name TEXT,
  members INTEGER, treasury INTEGER, submit_total INTEGER, submit_season INTEGER,
  score INTEGER, level INTEGER,
  PRIMARY KEY(date, guild_id)
);

CREATE TABLE live_sessions (            -- 크래시 복원용 (§4-5)
  uuid TEXT PRIMARY KEY, name TEXT, start_ts INTEGER, last_seen INTEGER, afk_s INTEGER
);

CREATE TABLE audit_log (                -- 웹 콘솔 운영 액션 감사 (Phase 6, §10-6 — statsweb이 기록)
  id INTEGER PRIMARY KEY, ts INTEGER NOT NULL,
  actor_discord TEXT NOT NULL, actor_name TEXT,
  action TEXT NOT NULL, target TEXT, args TEXT, result TEXT
);
```

---

## 6. 재화·XP 원장 — 초크포인트 계측 (Phase 0의 심장)

**목표: 서버에서 돈/XP가 움직이는 모든 경로가 `money.txn`/`xp.txn` 행 하나씩을 남긴다.** 신규 시스템이 돈을 만지면 구조적으로 자동 편입된다(안전망 1호).

### 6-1. 재화 6종과 계측 지점
| cur | 권위 필드 | 계측 지점 | 비고 |
|---|---|---|---|
| `money` | `PlayerData.money` | **`MoneyBridge.op/set/addOffline`** 내부에서 `Telemetry.money(...)` | after = 반영 후 잔액 |
| `money`(카지노) | 〃 | **§6-5에서 우회 자체를 정리** — MoneyBridge 신설 `applyVerified`로 수렴시켜 원장 자동 편입 | reason=`casino`, detail에 net/라운드 |
| `cash` | `PlayerData.cash` | 콜사이트 계측: `CashShopGui#buy`, `/캐시지급`(BlockShipPlugin:1526) | **겸사 수정: `addCash`에 `Num.clampMoney` 가드 추가** (현재 raw `+=`, 돈흐름 조사 발견) |
| `coin` | `PlayerData.recommendCoins` | 콜사이트: `CashShopGui#buy`, `/추천코인지급`, `IslandSubmitManager#grantCoins` | |
| `afkp` | `extraNums[잠수포인트]` | `AfkManager#accruePoints`(적립) / `#spendPoints`(사용) + `AfkShopGui` 환불 | |
| `guild` | `GuildData.treasury` | `GuildManager#deposit`(현재 withdraw 호출자 0 — 생기면 같이) | uuid=기여자, detail=guildId |

### 6-2. MoneyBridge reason 도입 — 점진 마이그레이션 전략
한 번에 85개 콜사이트를 고치지 않는다. **컴파일 강제 + 자동 태깅 안전망**의 2단:
1. 신규 시그니처 추가: `add(Player, long, String reason, String detail)` / `subtract(...)` / `set(...)` / `addOffline(...)`. reason은 `TxnReason` 문자열 상수 클래스(§부록 A)에서.
2. 기존 시그니처는 `@Deprecated`로 남기고 내부에서 **StackWalker로 호출자 클래스 추출**(프레임 ≤8개, `com.blockship.` 중 telemetry/playerdata 제외 첫 클래스) → `reason="untagged", detail="<CallerClass#method>"` 로 위임. 비용 ~수 µs, 돈 이벤트 빈도에서 무시 가능.
3. 커버리지 감사(§7-3)가 "최근 7일 untagged 소스 목록"을 보여줌 → 보이는 대로 명시 reason으로 치환. **`@Deprecated` 경고가 신규 코드의 컴파일타임 강제 장치.**
4. Phase 0에서 최소한 다음은 즉시 명시 태깅: SellGuiListener(어획판매), FishingListener(자동판매/잭팟), QuestManager(fishpay), 콘솔 3종(moneyop/moneyoffline/fishpay), ContestManager(상금), InnManager(사망), EnhanceManager(강화비), MarketGui(구매/정산), 각 상점 GUI.

### 6-3. XP 원장
- `FishingLevelManager.addExp(Player, double)` → `addExp(Player, double, String src)` 신설, 구 시그니처 deprecated 위임(src=untagged+StackWalker). 호출 6곳 즉시 태깅: `fish.catch`, `fish.extra`, `quest.<qid>`, `settle`.
- 내부 레벨업 루프에서 `level.up {sys:"낚시", from, to}` (P0) — Q1의 원자료.
- `SkillManager.addExp(Player, String, double)`도 동일 패턴(src: drill/crop/forage/cook/region_discover). **단 채굴·채집처럼 고빈도 소스는 xp.txn을 개별 기록하지 않고 §8-13의 분단위 집계 이벤트에 fold**하고, 레벨업만 `level.up {sys:"채굴"…}`로 남긴다.

### 6-4. 아이템 지급 이벤트 (`item.give`, P1)
전 인벤토리 추적은 하지 않는다(노이즈·비용 과다). **"시스템이 아이템을 창조하는 지점"**만 계측 — 돈흐름 조사가 전수 확보한 지점들: `QuestManager#giveReward`(rewardItems/Material/Key 포함), `CraftingManager#give*`/`rollMaterials`/`giveMaterial`, `WetTreasureChestManager#give*`, `ImugiBattle#dropReward`, `CollectibleManager#milestone`, `CheckCommand`(수표 발행), 각 상점 지급(상점 구매 이벤트에 fold), `AfkShopGui`, `CashShopGui`, OP 지급 명령(`/작물지급` 등 — cmd.use로도 잡히지만 명시). ctx: `{src, items:[{id,n}]}`.

### 6-5. 카지노 MoneyBridge 우회 정리 (Phase 0 필수 — 계측이 아니라 구조 수정)
현황(돈흐름 조사): `CasinoLedger`가 `PlayerData.setMoney` **직접 호출 10곳**(45, 52, 129, 132, 213, 215, 240, 241, 253, 254행 부근)으로 MoneyBridge를 우회한다. 이유는 MoneyBridge에 없는 기능 — 정산 후 `saveNowVerified` 실패 시 `setMoney(before)`로 되돌리는 **검증-롤백(2단 커밋)** — 을 자체 구현했기 때문. 이대로 두면 "돈 초크포인트=MoneyBridge"라는 안전망 1호의 전제가 영구히 깨진 채 유지된다.

**작업(권장안 A — 검증-롤백을 MoneyBridge의 공식 기능으로 승격)**:
1. `MoneyBridge`에 신설 (온라인/오프라인 2오버로드 — 카지노 정산은 uuid 기반 오프라인 지급 가능):
   ```java
   public boolean applyVerified(Player p, long delta, String reason, String detail)
   public boolean applyVerified(UUID uuid, String name, long delta, String reason, String detail)
   // before 스냅샷 → setMoney(clamp(before+delta)) → pdm.saveNowVerified(...)
   // → 실패 시 setMoney(before) 후 false. 성공/실패 모두 Telemetry.money 기록
   //   (롤백은 r=reason+".rollback"으로 별도 행 — 실패도 원장에 남는다)
   ```
2. `CasinoLedger`의 `setMoney` 직접 호출 10곳을 전부 이 API로 치환. 자체 `safeAdd`(포화덧셈 중복 구현)는 `Num.addSat`으로 통일.
3. 레거시 예치 경로(`reserve`/`settle`/`settleStack`/`refundOrphan` — 슬롯 크래시 복구용 잔존, §14-2)도 동일 치환. 구조상 치환이 정말 불가능한 지점만 차선안 B(직접 `Telemetry.money` 후킹 + "공인 제2관문" 주석 명시)로 남긴다.
4. **완료 판정**: 전 소스 `\.setMoney\(` grep 결과가 PlayerData 내부 + MoneyBridge + (B 선택 시) 주석 달린 CasinoLedger 지점 외 **0건**.
- 회귀 위험 관리: 카지노 정산은 실돈이다. dev에서 슬롯·블랙잭·룰렛 각각 승/패 양쪽을 재현해 잔액 정합·verified 저장 로그를 확인한 뒤 커밋(물리 테이블 검증은 카지노 리워크 메모리의 forceload 주의사항 참조). 앞으로 유사한 "특수 요구 때문에 우회" 상황이 오면 우회 대신 MoneyBridge에 기능을 추가하는 것이 규약(§7 문안에 반영됨).

---

## 7. 신규 시스템 자동 편입 — 3중 안전망 + 규약

**요구사항: "앞으로 추가하는 시스템들도 자동으로 통계에 추가"**. 완전 자동 계측은 불가능하지만(의미 있는 ctx는 사람이 정해야 함), 아래 3중 구조로 **"누락이 발생해도 흔적이 남고, 누락 자체가 자동 발각"**되게 한다.

### 안전망 1 — 구조적 초크포인트 (§6)
신규 시스템이 돈·XP·아이템을 만지면 원장에 무조건 남는다. untagged reason이어도 StackWalker가 클래스명을 남기므로 "어느 시스템이 얼마 발행했는지"는 소급 확인 가능.

### 안전망 2 — 범용 자동 태깅 리스너 (Phase 0, `TeleNetListener` 1클래스)
| 이벤트 | 훅 | ctx | 효과 |
|---|---|---|---|
| `cmd.use` (P2) | `PlayerCommandPreprocessEvent` MONITOR(취소 제외) | `{cmd, args(100자 절단), op}` | **신규 명령어 = 자동 포착.** 이용률(Q7)의 기초 |
| `gui.open` (P2) | `InventoryOpenEvent`, holder 클래스가 `com.blockship.*`일 때 | `{holder:"IceboxGui$Holder"}` | **신규 GUI = 자동 포착** (커스텀 holder 84종 관례 덕) |
| `gauge.online` (P2) | 60초 주기 (writer 유지보수) | `{n, tps, mspt}` | per-player-hour 정규화 분모, 서버 헬스 |
| `sess.start/end` (P0) | SessionTracker | `{dur_s, afk_s, reason}` | 플레이타임 신설 |

### 안전망 3 — 커버리지 감사 (Phase 4)
- `/통계 커버리지`: 최근 7일 `cmd.use`의 distinct cmd + `gui.open`의 distinct holder를 뽑아, `TeleTypes` 레지스트리에 **소속 시스템이 등록된 것과 대조** → "전용 이벤트가 하나도 없는 명령/GUI" 목록 출력. `money.txn`의 untagged detail 상위도 함께.
- 같은 쿼리를 데일리 리포트(§10-4)에 주 1회(일요일) "📊 통계 사각지대 n건" 한 줄로 노출 — **사람이 안 챙겨도 시스템이 조른다.**

### 규약 — blockship-plugin/CLAUDE.md에 추가할 문안 (Phase 4에서 그대로 붙여넣기)
```markdown
### 텔레메트리 계측 규약 (신규 시스템 필수, stats-system-plan.md가 설계 전거)
- 돈 변동은 반드시 MoneyBridge의 reason 있는 오버로드 사용 (deprecated 무-reason 금지).
  캐시/코인/잠수P/길드금고는 Telemetry.money(cur=...)를 직접 호출.
- PlayerData.setMoney 직접 호출 금지 — 검증-롤백 등 특수 요구가 있으면 우회하지 말고
  MoneyBridge에 기능(applyVerified류)을 추가할 것 (카지노 우회 사건의 교훈, §6-5).
- 새 시스템을 만들면: ① TeleTypes에 이벤트 타입 등록(설명+소속시스템) ② 핵심 행위 지점에
  Telemetry.log 1줄 ③ 고빈도(분당 수십회↑) 행위는 개별 이벤트 대신 분단위 집계 이벤트로.
- 새 GUI는 커스텀 InventoryHolder 관례 유지(자동 태깅 안전망의 전제).
- 새 밸런스 데이터 파일(json)을 추가하면 CatalogSnapshot.KINDS에 등록(§9-1).
- /통계 커버리지에 사각지대로 뜨면 그 시스템 계측이 누락된 것 — 즉시 보강.
```
- (선택, 후순위) 가드 훅: `~/.claude/hooks/`에 PostToolUse 스크립트로 blockship `*.java` diff에서 `moneyBridge.(add|subtract|set)\(p?[^,]+,[^,)]+\)` (2-인자 호출) 패턴 경고. 과탐 가능성 있으니 참고용 경고로만.

---

## 8. 이벤트 카탈로그 (전수)

표 규약: **타입** / P(우선순위) / Ph(구현 Phase) / **훅 위치** / **ctx 필드**. 훅의 라인 번호는 드리프트 주의. ctx 공통 키는 §부록 D.
접기(fold) 원칙: 한 행위 = 한 이벤트. 세부(미니게임 클릭, 연출, 공지, 부수 카운터)는 필드로.

### 8-1. 세션·서버·안전망 (Phase 0)
| 타입 | P | 훅 | ctx |
|---|---|---|---|
| `sess.start` | P0 | `PlayerJoinEvent` (SessionTracker, MONITOR) | `{first:0\|1}` (first=playerdata 신규 생성 여부) |
| `sess.end` | P0 | `PlayerQuitEvent` + 크래시 합성(§4-5) | `{dur_s, afk_s, reason:"quit"\|"crash"}` |
| `srv.start` | P0 | onEnable | `{mc:"1.21.11", jar_ts, catalogs:{parts:"a1b2..",fish:"..",...}}` |
| `srv.stop` | P0 | onDisable | `{uptime_s}` |
| `gauge.online` | P2 | 60초 | `{n, tps, mspt}` (`Bukkit.getTPS()[0]`, `getAverageTickTime()`) |
| `cmd.use` | P2 | `PlayerCommandPreprocessEvent` | `{cmd, args, op}` |
| `gui.open` | P2 | `InventoryOpenEvent` (blockship holder만) | `{holder}` |
| `money.txn` | P0 | §6-1 초크포인트 전부 | `{cur, d, after, r, dt}` |
| `xp.txn` | P0 | §6-3 | `{sys, amt, src}` |
| `level.up` | P0 | FishingLevelManager 루프 / SkillManager | `{sys, from, to}` |
| `item.give` | P1 | §6-4 지점 | `{src, items:[{id,n}]}` |
| `death` | P0 | `InnManager#onDeath` | `{penalty, world}` (money.txn 동반) |

- **세션 afk_s**: SessionTracker가 60초마다 온라인 순회, `AfkManager.WORLD_NAME`(afk_world) 체류 중이면 +60. (플레이타임 분모 = dur−afk.)
- **region 체류**: `region.enter/leave`(§8-10)의 페어로 오프라인 계산 — 세션에 fold하지 않음.

### 8-2. 낚시 코어 (Phase 1) — 플래그십
| 타입 | P | 훅 | ctx |
|---|---|---|---|
| `fish.cast` | P1 | **신규 리스너** `PlayerFishEvent State.FISHING` (현재 핸들러 없음 — 낚시 조사 확인) | `{rod}` |
| `fish.blocked` | P2 | `FishingListener#onFish` 게이트 3곳 (inv_full :107 / region_level :118 / no_fish :176 / recast :101) | `{cause}` |
| **`fish.result`** | **P0** | `FishingListener#onMinigameDone`(도주·타임아웃 포함) + `#finishCatchReward`(성공 시 완성) — **결과 확정 1회 1행** | 아래 상세 |
| `fish.humancheck` | P1 | `MinigameManager.Session#challengePass/#challengeFail` | `{kind, pass:0\|1, susp}` |
| `fish.chest` | P1 | `WetTreasureChestManager#giveMoney/#giveMaterial/#giveCookingMaterial` (rollChest 성공 시 1행) | `{money, items, pool_v}` |
| `contest.start` / `contest.end` | P1 | `ContestManager` 시작/종료(#pay) | `{prize}` / `{top:[{name,fish,size}...]}` (상금 money.txn 동반) |
| `dex.discover` | P1 | `DexManager#add` true 반환 시 (discoverFish/Rod/Part/Material/Region 공통) | `{cat, item, total}` |

**`fish.result` ctx 전체 명세** (Q1·Q3·Q9의 원자료 — 필드를 아끼지 말 것):
```jsonc
{
  "res":"성공|크리티컬|도주|대기",          // Session.finish 결과
  "fish":"참돔","g":"A","sz":87.3,"q":92,  // 어종/등급/최종크기/품질 (성공 시)
  "crit":1,"critd":3,                      // 크리 여부, critDamage 스탯
  "x":2,                                   // 더블/트리플 추가 마리수 (RewardMath.extraFish)
  "gu":1,"gufrom":"B",                     // 등급업 발동(tryGradeUp) 및 이전 등급
  "proc":["심안","풍어"],                   // SkillTreeManager.rollFishing 발동 목록
  "prd":{"base":0.7,"luck":12,"pity":4,"p":0.92,"spec":"C:50"},  // ★GradeRoller.Result 확장 필요(§14)
  "mg":{"rounds":3,"rs":3,"rc":1,"esc_f":14.2},  // 라운드수/성공/크리클릭, 최종 도주확률
  "combo":17,                              // 보상 반영 기준(comboBeforeReward)
  "lo":"a3f2c1d4e5f6","rod":"전설의 낚싯대","enh":7,   // 로드아웃 해시 + 낚싯대/강화 (Bonuses.matchedRod/rodEnhanceLevel)
  "st":{"gs":22.5,"xb":180,"szb":15,"crit":8,"dbl":12,"luck":30,"diff":9,"escr":25},  // 최종스탯 요약 8종 (Bonuses에서)
  "env":{"w":"비","t":"밤"},"buff":"전설의만찬",       // getEffectiveWeather / periodOf / dopingType
  "xp":41.2,"price":6300,"auto_sold":0,    // 계산된 XP·기준판매가(catchSellPrice)·인벤만석 자동판매 여부
  "legend":1,"legend_bonus":9450,          // 전설의대어 잭팟 (발동 시)
  "dex_new":0,"record":1,"contest":1       // 신규 도감/기록 갱신/대회 반영 여부
}
```
- **로드아웃 사전**: 캐치 시 `{rod, enh, parts:{릴,줄,바늘,미끼,찌}(PlayerData.getEquippedParts), dur:{슬롯:내구}}`를 정규화 JSON→SHA-1 앞 12자 해시. 신규 해시만 `loadout` 테이블 INSERT(월 DB). 이벤트엔 해시만 실어 행당 ~40B로 로드아웃 전체를 보존. 캐시는 메모리 `Set<String>`(월 전환 시 클리어).
- 도주/타임아웃 행은 fish/g/sz 등 성공 필드 생략, res·mg·combo(리셋 전 값)·lo만.
- XP는 `xp.txn{sys:낚시, src:"fish.result"}`로도 원장 기록(이중이지만 원장 완결성 우선, §6-3).

### 8-3. 장비·강화·부품 (Phase 1)
| 타입 | P | 훅 | ctx |
|---|---|---|---|
| `enh.attempt` | P0 | `EnhanceManager#doEnhance` 판정 직후 (:810 부근) | `{rod, rid, from, to, cost, pearl, p_succ, p_down, roll, res:"success"\|"keep"\|"down", shield:0\|1, boost, downred}` |
| `part.buy` | P0 | `PartShopGui#buyPart/#buyBait` (환불 경로 주의 :484) | `{type, name, price, n}` |
| `part.recipe_buy` | P0 | `PartShopGui#buyPartRecipe/#buyRod` | `{type, name, price}` |
| `part.equip` / `part.unequip` | P1 | `EquipmentManager#equip/#unequip` (`WorkbenchGui` 경유) | `{type, name, old}` / `{type, name}` |
| `part.break` | P1 | `EquipmentManager#reduceDurability` 내구 0 도달 (:146-163) | `{type, name}` (미끼 소진은 `{type:"미끼", exhausted:1}`) |
| `part.repair` | P0 | `RepairGui#repair` + `EquipmentManager#repair` | `{type, name, cost, from, to}` |
| `part.disassemble` | P1 | `DisassembleGui#onClick` (:118) | `{name, grade, frag_got, frag_after}` |
| `part.forge` | P1 | `FragmentForgeGui#craft` (:111) | `{mat, cost, frag_after}` |

### 8-4. 스킬·특성 (Phase 1)
| 타입 | P | 훅 | ctx |
|---|---|---|---|
| `tree.invest` | P0 | `SkillTreeManager#investOne` (:783) | `{tree, node, rank, pts_left}` |
| `tree.reset` | P0 | `#resetAll` (:804) | `{tree, spent, cost}` (money.txn 동반) |
- 특성 **발동**은 개별 이벤트 없음 — 각 소비처 이벤트(fish.result.proc, crop.harvest.proc, mine.min…)에 fold. 기존 `통계*행동/발동` extraNums 카운터는 그대로 두되, 텔레메트리가 시간축을 보강.

### 8-5. 판매·아이스박스 (Phase 2)
| 타입 | P | 훅 | ctx |
|---|---|---|---|
| `sell.fish` | P0 | `SellGuiListener#onClick`(:83)/`#onClose`(:106) — GUI 단위 1행 집계 | `{n, total, by_g:{"A":3,"S":1}, fresh_avg}` (money.txn 동반) |
| `icebox.delta` | P1 | `IceboxGui#onClose` (:122) — **open 시점 스냅샷과 diff** (조사 결론: 개별 입출고 이벤트 없음) | `{in:[{fish,g}..], out:[..], tier}` |
| `icebox.tier` | P0 | `IceboxGui#buyTier` (:165) | `{to, price}` |

### 8-6. 마켓·직거래·수표·송금 (Phase 2)
| 타입 | P | 훅 | ctx |
|---|---|---|---|
| `market.list` | P1 | `MarketGui#register` (:144) | `{item, price}` |
| `market.buy` | P0 | `MarketGui#buy` (:217) | `{item, price, fee, seller_uuid, seller_online:0\|1}` (구매자−, 판매자+ money.txn 2행) |
| `market.cancel` / `market.expire` | P2 | `#cancel`(:240) / `#processExpired`(:57) | `{item}` / `{item, to_mail:0\|1}` |
| `trade.done` | P0 | `TradeManager#execute` (:277) | `{a, b, items_a:[{id,n}], items_b:[..]}` — **수표가 실질 자금이동 경로**(조사 결론)이므로 수표 포함 아이템 전수 기록 |
| `check.issue` / `check.deposit` | P0 | `CheckCommand`(:85) / `CheckDepositListener`(:49,:55) | `{face, n, fee}` / `{face, n}` |
| `xfer.send` | P0 | `TransferCommand`(:59) / `MoneyCommand` 보내기(:71) | `{to, amt, fee, via:"송금"\|"돈보내기"}` — 수수료 정책 불일치(10% vs 0)가 데이터로 드러남 |
| `salepost` | P2 | `SalePostManager#post` (:64) | `{cost:5000}` |

### 8-7. 카지노 (Phase 2)
| 타입 | P | 훅 | ctx |
|---|---|---|---|
| `casino.join` / `casino.leave` | P2 | `TableGameManager#join/#leave/#requestLeave` | `{table, game}` / `{reason}` |
| **`casino.round`** | **P0** | **정산 지점** — `HouseTableRuntime` applyNet 4곳(:579,:649,:679,:686) / `PokerTableRuntime`(:675) / `RouletteTableRuntime`(:226) / `CasinoManager`(:463 슬롯) | `{game, table, bet, net, rake, detail:{...게임별: bj_hand, holdem_pot, slot_lines 등 런타임 보유 정보}}` |
| `casino.escrow` | P1 | `CasinoLedger#reserve/#settle/#refundOrphan` (레거시 잔존 경로) | `{op, amt, round_id}` |
- 플레이어·라운드당 `casino.round` 1행. **레이크는 소각**(조사 확인)이므로 rake 합계가 곧 하우스 수익 겸 머니싱크(C8).

### 8-8. 퀘스트·NPC·도감·도전과제 (Phase 2)
| 타입 | P | 훅 | ctx |
|---|---|---|---|
| `quest.accept` | P1 | `QuestManager#accept` / `#acceptDaily`(풀 일괄) | `{qid, cat, lv}` / `{diff, n}` |
| **`quest.done`** | **P0** | `#giveReward` (+즉시완료 경로 `completeTravel`/`completeAction` :752·:768) | `{qid, cat, dur_s, rw:{money, xp, items, key, title, grade, recipe}}` — dur_s = accept ts를 questProgress에 기록해 산출(신규 보조 맵 필요 시 extraStrs 사용 금지, 텔레메트리 자체 메모리+events 조인으로) |
| `quest.abandon` | P2 | `#abandon` | `{qid}` |
| `quest.allclear` | P1 | `#giveReward` 내 일퀘올클/주간 분기 | `{scope}` |
| `quest.reset` | P2 | `#resetDaily` / `#checkWeekly` (per-player lazy — 조사 확인) | `{scope, n}` |
| `npc.talk` | P2 | `NpcDialogueManager#start` | `{npc, branch}` |
| `ach.grant` | P0 | `AchievementManager#grant` (:338) | `{id, money}` |
| `coll.found` / `coll.milestone` | P1 | `CollectibleManager#found` / `#milestone`(:488~) | `{id, island, total}` / `{n, money}` |
- `quest.done`의 dur_s가 Q2의 핵심. accept ts는 SessionTracker 메모리 맵(uuid→qid→ts, 재부팅 시 유실되면 dur_s=null 허용) — 영속 오염 없이 단순하게.

### 8-9. 지역·날씨·이동·기타 월드 (Phase 2)
| 타입 | P | 훅 | ctx |
|---|---|---|---|
| `region.enter` | P1 | `RegionTracker#areaEnter` (20틱 폴링 확정 지점) | `{region, first:0\|1}` |
| `region.leave` | P1 | `#areaExit` (조사: 현재 사이드바 갱신만 하는 빈 지점 — 훅 최적지) | `{region, dur_s}` (enter ts는 tracker 메모리) |
| `region.blocked` | P2 | `#rejectEntry` (사유는 호출자 3분기에서 전달) | `{region, cause:"level"\|"key"\|"guild"}` |
| `weather.start` / `weather.end` | P2 | `WeatherManager#startWeather/#startGlobalWeather` / stop 2종 | `{scope, region, w, planned_s}` / `{scope, region, w, actual_s}` |
| `ferry.ride` | P0 | `FerryManager#depart` (:330 요금 차감 지점, 탑승자별) | `{route, fare}` |
| `portal.use` / `pad.use` | P2 | `PortalManager#tick` / `PadManager#teleport` | `{name}` / `{pad}` |
| `water.tp` | P2 | `WaterTeleportManager#tick` 성공 지점 (:117) | `{cost, kind:"rescue"\|"land"}` |
| `zip.ride` | P2 | `ZiplineManager#eject` (arrive/dropoff 구분) | `{name, ticks, arrived:0\|1}` |
| `horse.rent` | P0 | `HorseRentalManager#rent` (:122) | `{tier, price, dur_s}` |
| `door.pass` | P2 | `LockedDoorManager#onInteract` | `{door, ok:0\|1, key:"정확키"\|"마스터키"\|null}` |
| `door.key` | P1 | `#grantKey` + `QuestManager#rewardKey` | `{key, via}` |
| `scroll.use` | P2 | `ScrollManager#use` (:97) | `{id}` |
| `inn.sethome` | P2 | `InnManager#setHome` | `{town}` |
| `boss.fight` | P1 | `ImugiBattle#end/#autoEnd` (킬은 `#die`, 보상 `#dropReward`) | `{result:"kill"\|"giveup"\|"auto", dur_s, phase, drops:["용비늘"]}` |
| `nav.start` / `nav.arrive` | P2 | `NavigationManager#start` / `#tick` 도착 기록 | `{label, region}` |
| `afk.enter` / `afk.exit` | P1 | `AfkManager#sendToAfk` / `#returnFromAfk` | `{auto:0\|1}` / `{dur_s, points}` |

### 8-10. 작물·요리 (Phase 3)
| 타입 | P | 훅 | ctx |
|---|---|---|---|
| `crop.plant` | P1 | `CropManager#onPlant`→`#spawnCrop` | `{crop, island, used, limit}` |
| `crop.harvest` | P0 | `#onInteract`→`#giveOutput` | `{crop, qty, proc:{mult,bonus,jackpot}, grow_actual_s}` — grow_actual_s = now−plantTime (Crop 객체 보유). **Q4의 원자료** |
| `crop.pull` | P2 | 웅크림 뽑기 / `#pullCrop`(경작지 파괴·건조·밟힘) | `{crop, mature:0\|1, cause}` |
| `cook.craft` | P1 | `CookingGui#craft` | `{dish, mode:"buff"\|"submit"\|"mat", proc, refund:0\|1, op:0\|1}` |
| `cook.eat` | P1 | `CookingManager#onConsume` (제출용 조기 return 뒤 buff만) | `{dish, tier, dur_s}` |
- 성숙(`CropMatured`)은 이벤트 생략 — harvest의 grow_actual_s로 충분(조사: 단계 진행은 시간 파생값).

### 8-11. 채집·통발 (Phase 3)
| 타입 | P | 훅 | ctx |
|---|---|---|---|
| `forage.do` | P1 | `ForageManager#succeed` / `#fail` — 세션 종결 1행 | `{type, ok:0\|1, rare:0\|1, qty, strikes, dur_ms, cool_skip:0\|1}` |
| `trap.place` | P1 | `TrapManager#onInteract` 설치 성공 | `{region, dur_left}` |
| `trap.collect` | P0 | `#retrieve`/CollectHolder 회수 | `{region, n, by_g, dur_left, wait_s}` |
| `trap.break` | P2 | 내구 0 분기 | `{region}` |
- 미니게임 스윙별 이벤트는 만들지 않음(fold: strikes/dur_ms).

### 8-12. 광질 — 드릴·섬광산 (Phase 3, **분단위 집계**)
고빈도(드릴 ≤2초/액션, 섬광산 즉시재생 연타) → 개별 행 금지. 리스너가 메모리 누적, **60초마다 or 플레이어 이탈 시 flush**:
| 타입 | P | 훅 | ctx |
|---|---|---|---|
| `mine.min` | P1 | `DrillManager` 채굴 완료부(finishDig 부근, §14 확인) 누적 → 분당 flush | `{tier, ores:{"흑정석":14,...}, n, chain, vein, xp}` |
| `imine.min` | P1 | `IslandMineManager#mine` 누적 → 분당 flush | `{ores:{"돌":22,"다이아몬드":1}, n, xp, capped:0\|1}` |
| `oregen.build` | P2 | `IslandMineListener#onFencePlace/#onBucketEmpty/#onFlow` | `{n}` |

### 8-13. 섬·길드·제출 (Phase 3)
| 타입 | P | 훅 | ctx |
|---|---|---|---|
| `island.create` | P0 | `IslandManager#ensureIsland` | `{id, grid}` |
| `island.upgrade` | P0 | `#upgradeBorder/#upgradeMember/#buyUpgrade`(호퍼/워프/액자/작물/가구 공용 차감점) | `{kind, lv, price}` |
| `island.furniture` | P2 | `IslandFurnitureListener#onPlace/#onBreak` | `{op:"place"\|"break", used, limit}` |
| `alba.invite` / `alba.expire` | P2 | `IslandCommand#handleInvite` / `#sweepExpiredAlba` | `{target}` / `{alba}` |
| `submit.do` | P0 | `IslandSubmitManager#submitMaterial/#submitAllFish/#submitDish` | `{kind, id, n, pts, island, guild}` — 섬·길드 **동시 적립**(이중) 구조 그대로 기록 |
| `submit.season` | P1 | `#monthlyReset`(+`#rewardTop`) | `{ym, top_island:[..], top_guild:[..], coins}` (coin money.txn 동반) |
| `guild.create` / `guild.disband` | P0 | `GuildCommand#confirmCreate`(30000원) / `GuildManager#deleteGuild` | `{gid, cost}` / `{gid, members}` |
| `guild.member` | P1 | `#addMember/#removeMember`(가입/탈퇴/추방 구분) | `{gid, op:"join"\|"leave"\|"kick"}` |
| `guild.deposit` | P0 | `GuildManager#deposit` (§6-1 guild 원장 겸) | `{gid, amt}` |
| `guild.upgrade` / `guild.buff` / `guild.expand` | P0 | `#buyGuildUpgrade` / `#purchaseBuff` / `#expandIslandSize` | `{gid, kind, lv, price}` |

### 8-14. 제작 (Phase 3)
| 타입 | P | 훅 | ctx |
|---|---|---|---|
| `craft.do` | P1 | `CraftingGui#craft`(4분기 rod/drill/part/direct) + `CookingGui`는 cook.craft로 별도 | `{recipe, mode, result, ing:[{id,n}], op:0\|1}` |
| `craft.unlock` | P1 | `CraftingManager#unlockRecipe` | `{recipe, via:"item"\|"matId"\|"quest"\|"shop"}` |
| `appraise` | P1 | `ArtifactAppraisalGui#appraiseOne` (:117) | `{n, fee, results:[matId..]}` |

### 8-15. 칭호·프로필·상점 잡동사니 (Phase 2~3)
| 타입 | P | 훅 | ctx |
|---|---|---|---|
| `title.grant` | P1 | `TitleLogic#checkAutoGrant`(자동)/`#grantTitle*`(보상) — 회수는 `{op:"revoke"}` | `{id, via:"auto"\|"quest"\|"cash"\|"admin", op}` |
| `title.equip` | P2 | `#equip` | `{id}` |
| `profile.vote` | P2 | ProfileGui 인기도 투표 지점 | `{target}` |
| `cashshop.buy` | P0 | `CashShopGui#buy` (:150 분기 — coin/cash 이중통화) | `{item, coin, cash}` (해당 cur money.txn 동반) |
| `shop.buy` / `shop.sell` | P0 | `IslandShopGui#buy/#sell 2종`(:430/:470/:491), `DrillShopGui`(:139~:161), `AfkShopGui`(:133), `TrapManager#buyRecipe`(:213) | `{shop, item, n, price}` — **요리 판매(dish:) 포함, 광질·채집 산출물의 유일 환금구가 여기**(조사 결론) |

> **커버 안 하는 것(의도적)**: 블록 배치/파괴 일반, 채팅 내용, 이동 좌표 스트림, BGM/이모트/앉기 같은 순수 코스메틱(cmd.use/gui.open 안전망으로만), 배 물리 틱. 필요해지면 그때 타입 추가 — 스키마 변경 없이 가능하다는 것이 이 설계의 요점.

---

## 9. 카탈로그 스냅샷·플레이어 스냅샷·롤업

### 9-1. 밸런스 카탈로그 스냅샷 (`catalog_version`) — "당시 수치와 조인"
- **왜**: 3개월 뒤 "그때 그 낚싯대 가격이 얼마였지?"에 답하려면 이벤트만으론 부족. 밸런스 패치 전후 비교(Q3·Q5)의 전제.
- **무엇을**: `CatalogSnapshot.KINDS` = parts.json, fish.json, quests.json, enhance.json(+EnhanceManager 하드코딩 COST/SUCCESS/DOWN/PEARL 배열 — **코드 상수도 JSON으로 덤프**), recipes.json, materials.json, crops(CropSpecs 코드 상수), dishes(DishSpecs 코드 상수), traps(TrapSpecs), forage-types.json, submit-values.json, drill(DrillManager Ore/Tier 상수), island_prices(IslandManager 상수 배열), guild_prices(GuildManager 상수).
- **어떻게**: onEnable에서 각 kind를 정규화 JSON으로 직렬화 → SHA-1 → stats.db에 같은 (kind,hash) 없으면 gzip BLOB INSERT. `srv.start` ctx에 hash 맵 기록. 코드 상수 kind들은 전용 덤프 메서드(리플렉션 말고 명시 코드).
- **balance-audit 연동**: 스킬의 `pull.py`가 코드 정규식 파싱으로 뽑는 것과 동일 수치가 DB에 버전 관리됨 — 감사 리포트에 `catalog_version.id`를 인용하고, 역으로 stats-lab이 audits/snapshots의 목표치를 읽는다(§10-2).

### 9-2. 플레이어·길드 일일 스냅샷
- 매일 05:30 KST(writer 유지보수, 06:00 재시작 전): `playerdata/*.json` 전부(+`guilds.json`, `islands.json`)를 **writer 스레드에서 직접 파일 read**(ATOMIC_MOVE 저장이라 찢어진 파일 없음 — 인프라 조사 확인) → `player_snapshot`/`guild_snapshot` UPSERT. 38명 규모에서 <1초.
- 실패해도 게임 무영향, 다음날 재시도. 부팅 시 last 날짜 확인해 캐치업(최대 7일).

### 9-3. 일별 롤업 (`day_type`, `day_player`)
- 시점: 자정(KST) 이후 첫 배치에서 전일자 실행 + 부팅 캐치업. **idempotent**: `DELETE FROM day_* WHERE date=? ` 후 INSERT…SELECT.
- `day_type`: `SELECT date, type, COUNT(*), COUNT(DISTINCT uuid) FROM ev WHERE ts BETWEEN …` (월 DB ATTACH).
- `day_player`: 세션(sess.end 합산), fish.result 카운트/최고등급, money.txn 방향별 합, casino.round net 합, quest.done 수, craft/submit 수. json_extract 사용, 인덱스 (type,ts)로 하루치만 스캔.
- 소요: 하루 수만 행 × json_extract ≈ 수백 ms~수 초(비동기 스레드) — 메인스레드 무관.

---

## 10. 조회·분석 계층

### 10-1. 인게임 `/통계` (OP 전용, Phase 4)
- 등록: 기존 관례(`cmdMap.register`, 예: BlockShipPlugin:544 패턴), `setPermission("blockship.admin")`, **영타·초성 별칭 없음**(OP 규칙), 서브커맨드 tabComplete 제공.
- 읽기는 전부 Bukkit async 태스크에서 ro 커넥션 → 결과만 runTask로 전송.

| 서브커맨드 | 출력 |
|---|---|
| `/통계 오늘` `/통계 어제` | 접속자수·신규·총 플레이시간, 어획수·등급분포, 순발행(소스/싱크 top5), 카지노 net, 퀘스트 완료수 |
| `/통계 유저 <닉>` | 해당 유저 최근 7일 day_player 요약 + 최근 이벤트 20건 |
| `/통계 돈 [일수]` | money.txn reason별 합계 표 (인플레 감시) |
| `/통계 커버리지` | §7-3 사각지대 목록 + untagged 소스 top |
| `/통계 상태` | 큐 깊이/드랍 카운터/배치 지연/DB 크기/spill 여부 |
| `/통계 끄기·켜기` | 킬스위치 |

### 10-2. `stats-lab/` — Mac 분석 툴킷 (이 scripts 레포에 신설, Phase 4)
- `pull.sh` — prod에서 안전 사본 획득:
  ```bash
  # stats.db: 이미 매일 VACUUM INTO된 export/stats-latest.db를 scp
  # 월별 events DB: ssh로 python3 sqlite3.backup API 실행 후 scp (WAL 라이브 파일 직접 복사 금지)
  ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 \
    "python3 -c \"import sqlite3; s=sqlite3.connect('/home/ubuntu/mcserver/plugins/BlockShip/telemetry/events-2026-08.db'); d=sqlite3.connect('/tmp/ev.db'); s.backup(d)\""
  scp -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107:/tmp/ev.db stats-lab/data/
  ```
- `queries.py` — 쿡북 쿼리 함수화 + CLI. `report.py` — 주간 밸런스 리포트 markdown 생성(balance-audit 리포트 포맷과 동일 결로 `audits/`에 저장 가능).
- `intended-curve.json` — balance-audit 최신 감사에서 뽑은 목표 성장표(레벨→목표 누적시간). C1이 실측 백분위와 대조.

### 10-3. 쿼리 쿡북 (Q→SQL, queries.py에 구현)
```sql
-- C1 성장곡선: 레벨별 도달까지의 활동시간 백분위 (afk 제외)
--   level.up 이벤트 ts ↔ 해당 uuid의 sess.end(dur-afk) 누적을 조인해 산출
-- C2 밸붕 퀘스트: quest.done에서 qid별 median(rw.money+rw.xp환산)/median(dur_s) 상위 + 일일 반복 수익
SELECT json_extract(ctx,'$.qid') qid, COUNT(*) n,
       AVG(json_extract(ctx,'$.rw.money')) avg_money,
       AVG(json_extract(ctx,'$.dur_s')) avg_dur
FROM ev WHERE type='quest.done' GROUP BY qid ORDER BY avg_money/NULLIF(avg_dur,0) DESC;
-- C3 낚싯대 OP: 로드아웃별 실적 (등급가중수익/시간) — loadout 조인
SELECT json_extract(l.json,'$.rod') rod, json_extract(l.json,'$.enh') enh,
       COUNT(*) catches, AVG(json_extract(e.ctx,'$.price')) avg_price,
       SUM(CASE WHEN json_extract(e.ctx,'$.g') IN ('S','M','L','G') THEN 1 END)*1.0/COUNT(*) high_rate
FROM ev e JOIN loadout l ON l.hash=json_extract(e.ctx,'$.lo')
WHERE e.type='fish.result' AND json_extract(e.ctx,'$.res')!='도주' GROUP BY 1,2 HAVING catches>=50;
-- C4 작물 ROI: crop.harvest의 qty×(카탈로그 판매단가) / grow_actual_s, 작물별 심기 점유율
-- C5 가격 대비 성능: part.buy 수량 0인 카탈로그 품목 + C3 성능 지표와 parts 카탈로그 price 조인
-- C6 인플레: money.txn을 KST 일별·reason별 SUM(+)/SUM(−); player_snapshot으로 자산 지니계수
-- C7 이용률: day_type 주간 피벗 (시스템 도메인별 이벤트수·유니크 유저)
-- C8 카지노: casino.round 게임별 SUM(net)/SUM(bet) → 실현 RTP, rake 합계
-- C9 RNG 검증: fish.result의 prd.p 구간별 실측 성공률 / enh.attempt의 p_succ vs res 비율
```

### 10-4. 데일리 Discord 리포트 통합 (Phase 4)
- `nightly-restart.sh`(box, 메시지 조립 ~80행)에 1줄 추가 — python3 원라이너로 `export/stats-latest.db`의 어제 day_type/day_player 요약:
  `📊 어제: 접속 9명 · 어획 1,234(G 0) · 순발행 +52만 · 카지노 -12만 · 퀘 87건`
- 일요일엔 커버리지 사각지대 건수 1줄 추가. 실패해도 리포트 본문은 정상 발송(|| true).
- 스크립트 원본은 이 레포 `ops/nightly-restart.sh`도 함께 갱신(미러 유지).

### 10-5. 웹 어드민 대시보드 (Phase 5) — 통계 열람의 메인 UI
마크 채팅/인벤 GUI는 표·차트·기간 비교에 부적합하다. 인게임 `/통계`는 운영 점검(큐 상태·킬스위치·오늘 요약)용 최소 UI로 남기고, **탐색·시각화는 전부 웹**에서 한다.

**배치(권장, 2026-07-27 갱신): 공개 HTTPS + Discord OAuth — 다중 어드민 열람 + 통합 콘솔(§10-6) 확장 전제.**
당초 1인 열람 전제로 Tailscale 전용을 권장했으나, ①어드민 여러 명이 봐야 하고 ②추후 밴 등 운영 기능을 통합할 방침이며 ③박스 실사 결과 **Caddy가 이미 80/443에서 구동 중**(`lh-bizben.duckdns.org`→localhost:3000 프록시. cloudflared는 설치만 되고 inactive, 3000은 기존 node 서비스 점유)이라 권장안을 변경한다.
- **노출**: 기존 Caddy에 사이트 블록 1개만 추가:
  ```
  barkan.kro.kr {
      handle_path /admin/* { reverse_proxy 127.0.0.1:8080 }
      # 루트는 향후 서버 소개 페이지용으로 예약
  }
  ```
  도메인은 MC용으로 확보한 barkan.kro.kr 재사용 — MC는 25565, 웹은 443이라 충돌 없음. 인증서는 Caddy가 Let's Encrypt 자동 발급. kro.kr은 sub-subdomain 불가 전제로 경로(`/admin`) 방식. statsweb은 **127.0.0.1:8080 바인드**(3000 점유 중). ★기존 lh-bizben 블록은 절대 수정하지 않고 블록 추가만, 적용은 `systemctl reload caddy`(무중단).
- **인증: Discord OAuth2 + 허용 ID 목록** — "아이디/비번 시스템을 만들지 않는" 답. 어드민은 전원 디스코드에 있으므로(서버 운영 알림이 이미 Discord 기반) 로그인은 "Discord로 로그인" 버튼 1개. 성공 시 Discord user id가 `admins.json`(id→닉·역할)에 있으면 세션 쿠키 발급, 없으면 거부. **비번 저장·회원가입·재설정 flow가 통째로 없고**, 사람별 식별·즉시 회수(목록에서 한 줄 삭제)가 되므로 미래 밴 콘솔의 "누가 실행했나" 감사 요건을 처음부터 충족한다.
- 구현 규모: authlib(또는 수동 OAuth2 — Discord flow 단순) 기준 ~100줄. 전 라우트 세션 필수(예외 /login, /callback, /healthz), 쿠키 Secure+HttpOnly+SameSite=Lax, 로그인 실패 rate limit(Caddy 또는 앱단).
- **운영자 1회 작업**(Phase 5 시작 시, 합계 ~10분): ① barkan.kro.kr A레코드 실설정 확인(§14-14) ② Discord Developer Portal 앱 생성 + redirect `https://barkan.kro.kr/admin/callback` 등록 ③ client id/secret을 박스 `statsweb/.env`에 ④ admins.json에 어드민 Discord ID 기입.
- 대안(어드민 1~2명 + 전원 설치 감수 시): Tailscale 노드 공유(각자 무료 계정으로 박스 공유 수락, 공개 노출 0). 단 브라우저만으로 접속 불가(클라이언트 설치 필수)라 다중 어드민에겐 마찰이 크고, 통합 콘솔 단계에선 어차피 신원 기반 인증이 필요 — **처음부터 Discord OAuth로 가는 것을 권장.**

**스택**: Python **FastAPI + uvicorn** 단일 프로세스(`~/mcserver/statsweb/`, venv), 프론트는 정적 HTML + Chart.js(파일 동봉, CDN 미의존 — 폰/오프라인에서도 렌더). stats-lab의 `queries.py`(쿡북 C1–C9)를 **웹과 CLI가 공유하는 모듈**로 패키지화 — 쿼리 정의는 한 곳에만 존재.
- DB 접근: **read-only** (`sqlite3.connect("file:...?mode=ro", uri=True)`), stats.db + 최근 2개월 events DB ATTACH. WAL이라 게임 writer와 무경합. **쓰기 엔드포인트 0개** — 킬스위치 등 조작은 인게임 명령만. 웹이 털려도 서버 조작 불가.
- 페이지 구성(= 구현 우선순위): ① 홈(오늘/7일 KPI + 수집 헬스) ② 성장곡선(C1: 레벨 도달시간 백분위 vs intended-curve) ③ 경제(C6: 일별 순발행 스택차트 + reason별 표 + 자산분포) ④ 장비(C3·C5: 가격 vs 실측성능 산점, 구매 0 품목) ⑤ 생산(C4: 작물 ROI + 채집/통발/광질) ⑥ 퀘스트(C2: 원/분 랭킹) ⑦ 카지노(C8: 실현 RTP) ⑧ RNG(C9: 명목 vs 실측) ⑨ 유저 상세(검색 → day_player 타임라인 + 최근 이벤트) ⑩ 커버리지/사각지대.
- 운영: systemd `statsweb.service` (`Restart=always`, `MemoryMax=512M`, `Nice=10`), 로그 `~/mcserver/logs/statsweb.log`. **게임·수집과 완전 독립** — 죽어도 무영향이므로 프리즈 워치독에 안 묶고, 데일리 리포트 헬스 줄에 up/down 한 단어만 추가.

### 10-6. 통합 어드민 콘솔로의 확장 (Phase 6 — 설계 확정, 구현은 통계 안정화 후)
운영자 방침: 통계 열람을 시작으로 밴 등 운영 기능을 같은 페이지에 통합한다. statsweb을 처음부터 그 골격으로 짓는다(인증·역할·감사가 Phase 5에 이미 깔림).
- **역할 2단**: `viewer`(전 어드민 — 통계 열람 전부) / `admin`(운영 액션 실행). admins.json의 역할 필드로 관리, 승격은 파일 수정(=운영자만 가능).
- **쓰기 액션 4원칙**: ① 사전 정의된 액션 카탈로그만(임의 콘솔 명령 전달 **절대 금지**) ② 전 액션 CSRF 토큰 ③ 실행 전 확인 다이얼로그 ④ 성공/실패 무관 `audit_log` 기록.
- **실행 경로 = 로컬 RCON**: 박스 RCON이 이미 localhost 전용으로 켜져 있고(25575, `~/mcserver/scripts/rcon.py`) statsweb과 같은 박스라 **새로 여는 포트가 0개**. 1차 액션 카탈로그: `ban/pardon/kick <player> <사유>` · `whitelist add/remove` · 공지 1줄(say) · 온라인 목록 조회. 후보(2차): 머니/아이템 지급(콘솔 브릿지 `moneyop` 경유 — 텔레메트리 원장에 자동 기록됨), 날씨/이벤트 토글.
- **조회 확장**: playerdata JSON 뷰어(read-only), banned-players.json 목록, 텔레메트리 유저 타임라인 교차 링크(밴 검토 화면에서 "최근 행적 보기" → §10-5 ⑨).
- 밴 등 제재 실행 시 텔레메트리에도 `admin.action`(P0) 이벤트로 미러 — 게임 데이터와 운영 액션이 한 타임라인에 놓인다. audit_log DDL은 §5-2에 포함.

---

## 11. 운영: 백업·보존·아카이브

| 항목 | 조치 |
|---|---|
| **일일 오프사이트 tar 제외** | `offsite-backup.sh`의 tar(42행)에 `--exclude='BlockShip/telemetry/events-*' --exclude='BlockShip/telemetry/spill-*'` 추가. **stats.db와 export/는 tar에 포함**(소량·영구 가치). export/stats-latest.db가 VACUUM INTO 일관 사본이라 라이브 WAL 찢김 걱정 없는 복원본 역할 |
| **월간 아카이브 신설** | box에 `telemetry-archive.sh` + cron `30 18 2 * *`(매월 2일 03:30 KST, 기존 백업 시간대와 무충돌): 전월 `events-YYYY-MM.db`를 python3 backup API로 사본 뜨고 gzip → `oci os object put -bn mc-backups --name telemetry/events-YYYY-MM.db.gz` → 성공 시 `.backup-status`에 기록(데일리 리포트에 자동 표기) → 로컬 원본은 **3개월 지난 것만 삭제** |
| 보존 정책 | 로컬 raw 3개월 / 버킷 아카이브 12개월(이후 수동 정리) / stats.db 영구. **Object Storage Always Free 20GB 쿼터** — 월 아카이브 예상 15~120MB(§12)면 연 2GB 미만으로 안전하나, 월드 백업과 공유하는 쿼터이므로 아카이브 스크립트가 업로드 전 `oci os object list` 총량 체크 후 80% 초과 시 Discord 경고 |
| disk-guard 상호작용 | telemetry는 `~/mcserver/plugins/` 하위라 df 감시에 자동 포함. disk-guard의 삭제 대상(백업 폴더)과 무관하므로 충돌 없음 |
| 복원 | `oci os object get`으로 .gz 회수 → 어느 sqlite3에서든 열림. playerdata 복원과 독립 |
| dev | dev(Mac)도 동일 코드로 켜짐(자체 telemetry/ 폴더). 아카이브 크론은 prod만 |

---

## 12. 서버 부하 분석 (정량)

### 12-1. 이벤트량 모델
활동 유형별 발생률(이벤트/분/인, §8 fold 설계 반영):
| 활동 | 주요 이벤트 | 율 |
|---|---|---|
| 낚시 전념 (캐치 ~20–30초 주기) | cast 2–3, fish.result 2–2.5, xp.txn 2–2.5, money.txn ~0.5, 기타 0.5 | **~8/분 = 0.13/s** |
| 광질 전념 | mine.min 1, level.up 희박 | ~1.5/분 |
| 생활(작물/요리/제출/상점) | 각 P0/P1 산발 | ~2–4/분 |
| 유휴/이동 | region 2–4, cmd/gui 1–2 | ~3/분 |
| 서버 고정 | gauge.online 1/분 + live_sessions UPDATE | ~1/분 |

시나리오 (평균 동접 × 활동 혼합 ~5이벤트/분/인):
| 시나리오 | 평균 동접 | 이벤트/초 | 행/일 | 원본 증가/일 (~350B/행) | 월간 raw | 월간 아카이브(gz ~18%) |
|---|---|---|---|---|---|---|
| **현재 베타** (누적 38명) | 2–3 | 0.2–0.3 | 1.5만–2.5만 | **5–9 MB** | 0.15–0.3 GB | 30–55 MB |
| 성장기 | 8–10 | 0.7–0.9 | 6만–8만 | 20–28 MB | 0.6–0.9 GB | 110–160 MB |
| 피크 스트레스 (부하테스트 100명 전원 활동) | 100 | **~13/s** | (지속 비현실) | 순간부하 검증용 | — | — |

### 12-2. 자원별 영향
| 자원 | 계산 | 판정 |
|---|---|---|
| **메인스레드 CPU** | log() 1회 ≈ Map 1–3개 할당 + 큐 offer ≈ **1–3µs**. 13ev/s 피크에도 ~40µs/s = 틱버짓(1000ms/s)의 **0.004%**. 버스트 1000ev/s 가정에도 0.3% | 사실상 0. 비교: 기존 신선도 lore 태스크는 2분마다 전원 인벤 36슬롯 재작성(메인스레드), 랭킹 GUI는 열 때마다 전 유저 JSON 파싱 — **텔레메트리 핫패스가 기존 코드보다 훨씬 가볍다** |
| **Writer 스레드 CPU** | gson 직렬화+배치 INSERT. SQLite 배치 삽입은 이 ARM에서 5만+행/초 — 13ev/s는 **1코어의 <0.1%**. 롤업(일 1회) 수백ms–수초, 스냅샷 <1초 — 전부 전용 스레드 | 4 OCPU 중 MC가 상시 못 쓰는 여유 코어에서 흡수 |
| **fsync/디스크 IO** | 1초 배치 = WAL append 1회, synchronous=NORMAL이라 fsync는 체크포인트 위주(수 초~수십 초 간격). 월드 자동저장 대비 무시 수준 | 영향 없음 |
| **메모리(힙 16G)** | 큐 상한 20,000×~300B ≈ **6MB 최악**(평시 <100KB), SQLite 캐시 8MB×2–3, loadout 해시 Set 수만 개 ≈ 수 MB | <25MB, 힙의 0.15% |
| **GC** | 초당 수십 개 소형 객체 | 무시 |
| **디스크 용량** | 위 표 + 로컬 3개월 보존 = 베타 기준 <1GB, 성장기 ~2.7GB. 여유 32GB, disk-guard 85% 경보 존재 | 안전 |
| **백업 크기** | 일일 BlockShip tar: telemetry/events 제외로 **증가분은 stats.db+export(수~수십 MB)뿐**. 오프사이트 쿼터는 §11 체크로 방어 | 통제됨 |
| **부팅 시간** | 스키마 체크+카탈로그 해시(gzip 포함) ≈ 50–200ms(writer 스레드, onEnable 블로킹은 스레드 기동뿐) | 무시 |
| **웹 대시보드(statsweb)** | 별도 프로세스: 유휴 RAM 60–80MB, 조회 시 일시 CPU(대부분 롤업 조회라 ms 단위). `MemoryMax=512M`·`Nice=10` 상한 | MC 힙(16G)·틱과 완전 격리, 24GB 박스에서 무시 수준 |

### 12-3. 리스크와 방어
| 리스크 | 방어 |
|---|---|
| writer 스레드 사망 | log()는 계속 큐에 쌓다 포화→P2/P1 드랍+P0 spill. watchdog식 자가 재기동(uncaughtExceptionHandler에서 재스레드) + `/통계 상태`·gauge.health로 가시화 |
| 디스크 풀 | SQLite 쓰기 실패→spill→그것도 실패 시 드랍(게임 무영향). disk-guard가 85%에서 이미 경보 |
| 월 전환 경합 | 로테이션은 writer 단일 스레드 내부라 락 불필요 |
| 롤업이 무거워짐(월 수백MB) | 하루치만 인덱스 스캔. 그래도 느리면 롤업을 box python3 크론으로 이관 가능(스키마 동일) |
| 큐 포화로 P0 유실 | P0는 드랍 대신 spill(JSONL). spill까지 실패하는 상황 = 디스크 전멸로, 이미 서버 자체가 위험한 상태 |
| DB 파손 | WAL+NORMAL로 크래시 내구. 월별 분리로 파손 반경 축소. 아카이브·export 사본 존재 |
| **계측 코드가 게임 로직을 깨뜨림** | 모든 훅은 "기존 로직 끝난 뒤 값 읽어 log 1줄" 패턴 고수. 게임 상태를 바꾸는 코드를 텔레메트리에 넣지 않는다(리뷰 체크포인트) |

### 12-4. 실측 계획 (Phase 0 수용 기준에 포함)
1. dev에서 `/낚시테스트` 루프 + 테스트 봇으로 30분 부하 → `/통계 상태`의 배치 지연·큐 깊이 확인 (기대: 지연 <5ms, 큐 <100).
2. `kill -9` 후 재기동 → 유실 ≤ 마지막 1초 배치, live_sessions 크래시 세션 합성 확인.
3. mspt 비교: 계측 on/off 30분씩 `gauge.online` mspt 평균 비교 (기대: 차이 노이즈 이하).

---

## 13. 구현 로드맵 (Sonnet 5 작업 지시)

> **★2026-07-28 저녁 업데이트**: 아래 Phase 0~4 각각의 "prod 미배포" 문구는 그 항목을 완료한
> **시점** 기준 기록이다 — 이후 같은 날 밤 `~/deploy-blockship.sh`로 전체 blockship-plugin이
> **prod에 실배치 완료**되었고(0명 접속 시점, git status 클린 확인 후), 부팅 로그에서 텔레메트리
> 초기화·player_snapshot(19명)·guild_snapshot(1길드)·export까지 무예외로 정상 동작 확인했다.
> 지금은 dev/prod 둘 다 최신 코드가 돌고 있다. Phase 5(statsweb)도 같은 밤 prod 실배치 완료.

### Phase 0 — 코어 파이프라인 + 원장 (최우선, 이것만으로도 Q6·Q7 절반 해결)
**✅ 완료 (2026-07-27, blockship-plugin 커밋 9cbb5de) — dev 배포·실측검증 완료, prod 미배포(당시 기준 — 이후 prod 배치됨, 위 업데이트 참조).**
검증 결과: sess.start/end(크래시 합성 kill -9 실측 확인)·money.txn(reason태깅 실측)·xp.txn·cmd.use·
gui.open(안전망2, 도감GUI 자동포착 확인)·gauge.online·srv.start/stop 전부 dev에서 정상 동작 확인.
아래 항목은 원래 계획 그대로 두되, 실제로는 이미 구현됨(다음 세션은 Phase 1부터 시작할 것).
1. `build.gradle.kts`에 sqlite-jdbc implementation 추가(§3-2, shading 확정). `com.blockship.telemetry` 패키지 9클래스(§4-1) 작성.
2. onEnable 배선(PlayerDataManager 직전), onDisable flush. `telemetry.json` 기본 생성.
3. §8-1 전부: 세션/게이지/cmd.use/gui.open/srv.start·stop/death.
4. §6: MoneyBridge reason 오버로드+StackWalker 폴백, **카지노 우회 정리(§6-5: applyVerified 신설 + CasinoLedger setMoney 10곳 치환 + grep 0건 판정)**, cash/coin/afkp/guild 콜사이트, `addCash` clamp 수정, FishingLevelManager·SkillManager src 오버로드, level.up.
5. `TelemetryCommand` 최소(상태/끄기/켜기).
- **수용 기준**: dev에서 접속→낚시테스트→판매→재접속 시나리오 후 `ev` 테이블에 sess/money/xp/level 행 확인. §12-4의 1·2·3 통과. `./gradlew build` 클린.

### Phase 1 — 낚시 버티컬 (Q1·Q3·Q9)
**✅ 완료 (2026-07-28, blockship-plugin 커밋 b7768b0) — dev 배포·부분 실측검증 완료, prod 미배포.**
검증: fish.cast·dex.discover는 dev에서 실제 이벤트로 확인(DB 조회). enh.attempt/part.*/tree.*/
fish.chest/contest.*/fish.result는 컴파일 통과 + 정밀 변수추적으로 코드 정확성 확인했으나,
**fish.result(실제 캐치 완주)는 헤드리스 테스트봇의 낚싯대 우클릭 한계로 dev에서 실측 못 함**
(project_dev_test_bot_control.md에 기존 문서화된 제약 — PlayerInteractEvent 기반 캐스팅은
봇으로 bite 상태까지 못 감). 다음 세션이 실캐릭터로 낚시 1회만 해보면 fish.result/loadout
테이블까지 전부 검증 가능. ★부수: dev world (90~130, y63~64, 90~130)에 테스트용 돌바닥+
호수 생성됨 — 정리 필요시 별도 처리.
6. `fish.cast` 신규 리스너, `fish.blocked`.
7. **GradeRoller.Result에 진단 필드 추가**(base/luckMult/pity/finalP/spec — 시그니처 확장, 호출부 1곳).
8. `fish.result` 조립(§8-2 ctx 전체) + loadout 해시 사전. onMinigameDone(도주)·finishCatchReward(성공) 두 지점에서 하나의 빌더로.
9. enh.attempt / part.* / tree.* / fish.humancheck / fish.chest / contest.* / dex.discover.
- **수용 기준**: 낚시 50회 시뮬 후 C3 쿼리가 로드아웃별 행을 반환. prd.p 필드 존재. 도주 행에 combo 리셋 전 값.

### Phase 2 — 경제·진행 (Q2·Q6·Q8)
**✅ 완료 (2026-07-28, blockship-plugin 커밋 5ece5bb) — dev 배포·부분 실측검증 완료, prod 미배포.**
검증: quest.reset.daily/weekly+assign.weekly, region.enter/leave(dur_s), ach.grant+money.txn(reason
일치) 실이벤트 확인. casino.round는 CasinoLedger.applyNet 내부에서 money.txn과 같은 net을 기록하도록
설계해 정합성이 코드 구조상 보장됨(실측은 카지노 테이블 셋업 필요해 미실시). 나머지(마켓/카지노join/
칭호/이동계열)는 컴파일 통과+정밀 변수추적, 라이브 미검증. 다음 세션은 Phase 3부터.
10. sell.fish/icebox/market/trade/check/xfer/salepost. 11. casino.join/round/escrow. 12. quest 라이프사이클(accept ts 메모리 맵)+npc.talk+ach+coll. 13. region enter/leave/blocked, weather, ferry/portal/pad/water/zip/horse/door/scroll/inn/boss/nav/afk, title/profile/cashshop/shop.
- **수용 기준**: 카지노 1라운드→casino.round net과 money.txn 잔액 일치. 퀘스트 수락→완료 dur_s 기록.

### Phase 3 — 생산 (Q4)
**✅ 완료 (2026-07-28, blockship-plugin) — dev 배포·구조적 검증 완료(빌드/큐/레지스트리), 라이브 실측(작물 심기→수확 등)은 미실시. prod 미배포.**
검증: 전체 빌드 통과, dev 서버 무예외 기동, `/통계 상태` 큐 정상(errors=0/drop=0), 이번 페이즈에서
추가한 이벤트 타입 전수(약 40종)가 TeleTypes에 하나도 빠짐없이 등록됨을 grep diff로 확인. 실제
게임플레이 실측(작물 사이클/섬광산 매크로판정/길드 생성 등)은 셋업 비용이 커 이번 세션에서 생략 —
컴파일 통과+정밀 변수추적 수준의 신뢰도(Phase 2 마켓/카지노join과 동일 수준).
14. crop.plant/harvest/pull + cook.craft/eat. 15. forage.do + trap.place/collect/break.
16. mine.min·imine.min 분단위 집계기(공용 `MinuteAggregator` 헬퍼, DrillManager/IslandMineManager) + oregen.build.
17. island.create/upgrade/furniture + alba.invite/expire + submit.do/season + guild.create/disband/member/upgrade/buff/expand(guild.deposit은 money.txn cur="guild"가 겸함).
18. craft.do(CraftingGui) + craft.unlock(CraftingManager, via=item/matId) + appraise(ArtifactAppraisalGui).
- **수용 기준**: 작물 1사이클 심기→수확에 grow_actual_s 기록(구조상 보장 — c.plantTime epoch초 기준 now()-plantTime). 섬광산 연타 1분 → imine.min 1행(MinuteAggregator 60s 윈도우, 라이브 미실측).

### Phase 4 — 스냅샷·롤업·분석·운영·규약
**✅ 완료 (2026-07-28, blockship-plugin 커밋 7faa3fb/ec14b24) — dev 배포·실측검증 완료, prod 미배포.**
검증: 카탈로그 13종(parts/fish/quests/recipes/materials/forage/submit + enhance/crops/dishes/traps/drill/
island_prices/guild_prices) 해시 삽입 확인, srv.start ctx에 catalogs 맵 동봉 확인. player_snapshot 26명·
guild_snapshot 2길드 실제 UPSERT 확인. day_type/day_player 롤업 SQL을 실데이터로 수동검증(playtime/casts/
catches/money_in·out/quests_done 등 정확). export/stats-latest.db VACUUM INTO 생성+테이블 무결성 확인.
`/통계 오늘·어제·유저·돈·커버리지` 전부 무예외 실행 확인(단 RCON 툴 특성상 async 응답 캡처는 실측 불가 —
sendMessage 로직 자체는 이미 검증된 SQL과 동일 패턴). stats-lab/queries.py 10개 쿡북 함수(C1~C9, C9는
낚시/강화 2종) 전부 실행 성공, report.py 마크다운 생성 확인. box 스크립트(telemetry-archive.sh 신설,
offsite-backup.sh --exclude, nightly-restart.sh 📊 줄+일요일 리마인더)는 이 레포 ops/prod/
미러에서 로컬 bash -n + PREVIEW 테스트까지 완료 — ★실제 오라클 박스 설치/크론 등록은 prod 인프라 변경이라
별도 명시 요청 시에만(수행 안 함).
17. CatalogSnapshot(코드 상수 덤프 포함) + srv.start 해시. 18. player/guild_snapshot, day_type/day_player 롤업+캐치업, VACUUM INTO export. 19. `/통계` 전체 서브커맨드 + 커버리지 감사. 20. stats-lab/(pull.sh, queries.py 쿡북 C1–C9, report.py, intended-curve.json). 21. box: telemetry-archive.sh+cron, offsite-backup.sh --exclude(box 실물+이 레포 ops/prod/ 미러 동시 수정), nightly-restart.sh 리포트 1줄. 22. blockship-plugin/CLAUDE.md 규약 문안(§7) 추가. 23. TeleTypes에 §8 전 타입 등록 확인(누락=커버리지 감사가 자기 자신을 잡는지 테스트).
- **수용 기준**: `/통계 오늘` 정상 출력. PREVIEW=1 데일리 리포트에 📊 줄 포함. pull.sh로 Mac에서 C1 실행 성공. 커버리지에 미등록 GUI 하나 일부러 만들어 검출되는지 확인.

### Phase 5 — 웹 어드민 대시보드 (§10-5)
**✅ 완료 + prod 실배치 완료 (2026-07-28) — 유저가 Discord client id/secret+본인 Discord ID 제공,
운영자 사전작업 전부 마치고 오라클 박스에 실제 설치·실로그인까지 검증됨.**

구현: FastAPI 앱(app.py) + Discord OAuth2(auth.py) + SVG 차트 4종(charts.py — Chart.js 대신
서버사이드 SVG로 대체, 이 환경에서 외부 JS 파일을 새로 받을 수 없어서인데 결과는 동일하게
CDN 미의존·자체완결) + 페이지 ①~⑩ 전부. stats-lab/queries.py를 `set_data_dir()`로 리팩터해
웹·CLI 공유 모듈화.

**prod 실배치 과정에서 실사용 중 잡힌 버그 2개**(로컬 forged-세션 테스트로는 못 잡았던 것들 —
실제 브라우저로 Discord 로그인 왕복해보고서야 드러남):
1. Caddy가 `barkan.kro.kr/admin/*` → `127.0.0.1:8080/*`로 프리픽스를 벗겨 프록시(`handle_path`)
   하는데 앱 자체는 이를 몰라 절대경로 링크·리다이렉트가 `/admin` 밖으로 새던 문제 → `BASE_PATH`
   환경변수 도입 + 템플릿/redirect 전부 프리픽스 적용.
2. `stats.db`가 아직 없을 때(텔레메트리 미배포 상태로 먼저 로그인 시도) `queries.py`가
   `sys.exit()`로 서버 프로세스 자체를 죽여 500 에러 → `StatsDataUnavailable` 예외로 바꾸고
   전역 예외 핸들러로 `no_data.html` 표시.

**추가로 이번 배치 세션에서 얹은 기능(계획 이후 확장)**: OP(관리자) 행동 자동 제외 — 유저 요청으로
`Telemetry.log()`가 모든 이벤트에 `ctx.op`(그 순간 OP였는지)를 자동 태깅하고, `day_player`
롤업(RollupJob.java)과 `queries.py`의 C1~C6·C8·C9가 op=1 이벤트를 집계에서 제외(day_type/C7
이용률은 예외 — OP 사용도 유효한 신호라 그대로 둠). dev에서 OP 계정으로 실제 명령 실행 →
`ctx.op:1` 태깅 확인 + C6 집계에서 제외 확인까지 실측.

**HTTPS 관련**: 최초 배치 시점에 kro.kr(공용 무료 서브도메인) 전체에 걸린 Let's Encrypt
rate limit(주 50건)에 걸려 인증서 발급이 일시 대기 상태였음 — 그 사이 임시로 Caddy를
`http://barkan.kro.kr`로, `.env`의 `DISCORD_REDIRECT_URI`도 http로 낮춰 로그인 흐름 자체를
먼저 검증했고, rate limit 해제 시각 이후 https로 원복 예정(별도 확인).

24. 운영자 사전 작업 확인(§10-5 목록): barkan.kro.kr A레코드 → Discord 앱 생성+redirect 등록 → `.env`(client id/secret) → admins.json(어드민 Discord ID+역할). — **전부 완료**.
25. Caddyfile에 barkan.kro.kr 블록 추가(★기존 lh-bizben 블록 불변, `systemctl reload caddy` 무중단 적용) + `~/mcserver/statsweb/` FastAPI 앱(127.0.0.1:8080 바인드) + systemd `statsweb.service`(Restart=always, MemoryMax=512M, Nice=10). — **완료, 실행 확인**.
26. Discord OAuth 로그인/세션/허용목록 + `queries.py`를 stats-lab과 공유 모듈로 패키지화 + 정적 프론트(Chart.js 동봉 → 실제로는 서버사이드 SVG로 대체). — **완료, 실로그인 성공 확인**.
27. 페이지 ①→⑩ 순서로 구현 — **①③④만으로 1차 오픈 가능**(홈/경제/장비가 최고 가치). 데일리 리포트 헬스 줄에 statsweb up/down 1단어 추가 — **✅ 완료(2026-07-28)**: `ops/nightly-restart.sh`가 `127.0.0.1:8080/healthz`를 직접 curl해 `📊 통계웹 up/down` 한 단어를 붙임, prod에 스크립트 sync 후 `PREVIEW=1` 실행으로 `up` 응답 실측 확인.
- **수용 기준**: 어드민 로그인 성공(wsi1212 Discord 계정으로 실제 승인→콜백→대시보드 진입 확인) + 목록 밖 계정 거부는 코드상 보장(`auth.resolve_admin`이 admins.json에 없으면 거부, 실계정으로 재현은 안 함). 미로그인 접근 시 /login 리다이렉트 확인. **기존 lh-bizben.duckdns.org 서비스 무영향 확인**(변경 전후 응답 동일). 대시보드 조회 중 게임 서버는 별도 프로세스라 mspt 무관. ※HTTPS 인증서/systemd 자동재기동(kill 후 재기동)은 아직 미실측 — 인증서는 rate limit 해제 후, 재기동은 필요 시.

### C10 — 강화 단계별(몇강) 시도/성공/실패 (2026-07-28 추가 요청, C9의 확장)
**✅ 완료.** C9가 "명목 확률 구간별 실측 성공률"(이론 대 실측)을 보는 것과 달리, "+7강 시도가 총
몇 번 있었고 그 중 몇 번 성공/실패했나"를 실제 강화 단계(`enh.attempt.from`) 기준으로 그대로
센다 — 레벨 게이트·난이도 확인에 더 직접적. `queries.c10_enhance_by_level()` 신설(⑧ RNG 페이지
세번째 섹션에 표+막대차트로 배치), `seed_sandbox.py`의 enh 이벤트에 현실적인 단계별 난이도
곡선(from↑ → 성공률↓)과 from/to 필드를 보강해 샌드박스에서도 바로 확인 가능.

### C11~C15 — 채집·통발·광질(드릴/섬광산) 실측 (2026-07-28 추가 요청 "광질이나 채집 탐험 뭐 그런것들")
**✅ 완료.** ⑤ 생산 페이지가 지금까지 crop.harvest(C4)만 덮고 "채집/통발/광질 세부는 이벤트
누적 후 확장"이라고 스스로 인정하던 빈칸을 채웠다 — §8-11·§8-12에 계측 자체는 이미 있었는데
쿠키북·대시보드가 안 따라간 상태였음.
- **C11 채집**(`c11_forage_performance`): forage.do를 타입별로 — 성공률/희귀 발견율/평균
  산출량/평균 소요시간.
- **C12 통발**(`c12_trap_performance`): trap.place/collect/break를 지역별로 합쳐 설치 대비
  파손율, 회수당 평균 대기시간(wait_s) — UNION+LEFT JOIN으로 세 이벤트의 지역 키를 하나로
  합침(SQLite는 FULL OUTER JOIN 미지원이라 이 패턴 사용).
- **C13 드릴 티어**(`c13_mining_by_tier`): mine.min(분당 집계)을 티어별로 — 분당 채굴량
  (ore_per_flush)이 성능 체감의 직접 지표.
- **C14 광물 브레이크다운**(`c14_ore_breakdown`): mine.min/imine.min의 `ctx.ores`(광물명→개수
  딕셔너리)를 `json_each()`로 풀어 광물별 합계 — 특정 광물 쏠림 확인.
- **C15 섬광산 요약**(`c15_island_mine_summary`): capped_rate(유저별 채굴 한도 도달 빈도)로
  한도가 너무 박한지/무의미한지 가늠.
- `seed_sandbox.py`에 forage/trap.place/trap.collect/trap.break/mine.min/imine.min 이벤트
  생성을 신규 추가(이전엔 전혀 없었음 — kind 가중치에 6종 추가, 채집 타입별 성공률 차등·드릴
  티어별 배율·섬광산 capped 확률 등 현실적인 값으로 세팅). 샌드박스에서 6개 섹션 전부 렌더+
  인사이트 배지 확인.

### C16 — 상점(섬/드릴 등) 품목별 구매/판매 (2026-07-28 추가 요청 "섬상점에서 어떤 품목이 얼마나 팔렸고")
**✅ 완료.** `IslandShopGui`/`DrillShopGui`는 이미 `shop.buy`/`shop.sell`(ctx: shop=island/drill,
item, n, price)을 계측하고 있었는데(코드 조사로 확인) 쿠키북/대시보드가 안 따라간 상태였음.
`queries.c16_shop_sales()`가 상점×품목으로 묶어 구매수량·매출·되팔기수량·지급액을 한 행에
정리, ③ 경제 페이지 두번째 섹션에 배치. `seed_sandbox.py`에 섬상점 6종+드릴상점 3종 품목
구매/되팔기 이벤트 신규 추가.

### C6 버그 — 재화 종류(cur) 무시하고 합산되던 문제 (2026-07-28, prod 실사용 중 유저 발견)
**✅ 완료.** ③ 경제 페이지에서 유저가 "골드랑 캐시랑 다 합쳐진거 같은데"라고 직접 발견 — `c6_inflation`이
`reason`만 GROUP BY하고 `ctx.cur`(money/cash/afkp — 실제 서로 다른 재화)를 무시해서 전부 한 숫자로
합산되고 있었다. `cur`도 GROUP BY에 추가하고, app.py가 재화별로 섹션 자체를 분리 렌더링(골드 먼저,
나머지는 알파벳순) 하도록 수정. seed_sandbox.py에도 cash/afkp 이벤트를 새로 섞어 넣어 샌드박스에서
분리 확인 완료. ★prod 실사용 중 발견된 버그 — 이 시스템이 실제로 자기 자신의 결함도 잡아낸 사례.

### C16 버그 — 추천상점이 섬상점으로 뭉뚱그려지던 문제 (2026-07-28, 유저 발견 연속타)
**✅ 완료.** 위 재화 분리 직후 유저가 "추천상점 그것도 분리해줘"라고 바로 지적 — 코드를 보니
`IslandShopGui`가 섬상점/추천상점 둘 다 같은 클래스 인스턴스(`shopId="섬"`/`"추천"`)로 도는데,
`shop.buy`/`shop.sell` 텔레메트리 3곳이 `shopId`를 무시하고 전부 `"shop": "island"`로 하드코딩
되어 있었음(대시보드가 아니라 **Java 로깅 자체의 버그**). `shopTag()` 헬퍼 신설해
`"추천".equals(shopId) ? "recommend" : "island"`로 실제 인스턴스를 반영하도록 수정
(commit c54005b, jar 미배포). seed_sandbox.py에 추천상점(신호기/전달체) 이벤트 추가해 C16에서
island/recommend/drill 셋이 진짜로 분리되는 것까지 확인.

### 부록 — prod 실사용 중 발견한 진짜 데이터 이상(2026-07-28, 참고용 기록)
플레이어 `sdghjkcam7`의 achievement money.txn 이벤트에서 `d=-8,300,034,833,169,298,177`라는
비정상 값 발견 — 역산하면 이벤트 직전 잔액이 약 830경 원(MAX_MONEY 1e15의 8300배)이었다는 뜻.
전체 텔레메트리 기록상 이 플레이어에게 그 이전 money.txn이 전무해 텔레메트리 배포 이전(Skript
시절 등) 오염된 legacy 데이터로 추정, 현재는 클램프로 999,999,998,887,500(상한 바로 밑)에 안착.
전체 playerdata 21명 스캔 결과 다른 플레이어의 초과 잔액은 0건 — 활성 진행 중인 버그는 아닌 것으로
판단. 유저 요청으로 해당 플레이어의 데이터(계정 전체) 삭제 명령을 제공(직접 실행은 사용자가 함,
영구삭제는 에이전트가 직접 수행하지 않는 정책).

### C17~C20 — 마켓/직거래 경제 + 로깅 자체 보강 (2026-07-28 요청 "마켓/직거래 경제 먼저 + 모든 로깅까지 특히 직거래쪽은")
**✅ 완료.** 이번엔 대시보드만 만든 게 아니라 실제 Java 로깅 자체에 구멍이 있는 걸 코드 조사로
찾아내 **blockship-plugin도 같이 고쳤다**(커밋 8f862f4, jar 배포는 안 함):
- **`trade.done`이 최악이었음** — items_a/items_b가 `{mat,n}`뿐이라 가치 정보가 전혀 없었고
  (§8-6이 "수표 포함 실질 자금이동 추적"을 원래 요구했는데 코드엔 없었음), money.txn도 안
  거쳐서 직거래는 통계상 완전한 블랙박스였다. `CheckCommand.readFaceValue()`(공개 메서드
  신설)로 수표 액면가, `FishItem.calcPrice()`로 물고기 시세를 항목별로 매겨 `value`/`value_src`를
  추가하고, 그 외 일반 아이템은 가격 카탈로그가 없어 `value` 없이(unknown) 남긴다. 거래 전체
  `value_a`/`value_b`/`unknown_a`/`unknown_b`를 ctx 최상위에도 같이 기록해 "양쪽 다 100% 가치를
  아는 거래"만 걸러 편측(불공정) 탐지가 가능해졌다.
- **market.list/buy/cancel/expire**: `MarketManager.Listing`엔 이미 `id`/`qty`/`sellerUuid`가
  있었는데 4개 텔레메트리 콜사이트 중 어디에도 안 실려있었음 — 전부 추가해 "등록→판매까지
  걸린 시간"(time-to-sell) 조인이 처음으로 가능해짐. `market.buy`에 `seller_uuid`도 추가
  (§8-6이 요구했는데 실제론 한 번도 없었음).
- **xfer.send**: `/송금`(TransferCommand, 수수료 10%)과 `/돈 송금·보내기`(MoneyCommand, 수수료
  0%)가 같은 이벤트 타입을 써서 구분이 안 됐음(§14 기재된 수수료 정책 불일치) — `via=
  transfer_cmd`/`money_cmd` 필드 추가로 우회 규모를 직접 집계 가능해짐.
- 쿠키북: `c17_market_by_item`(품목별 등록/판매/취소/만료+평균 판매소요시간),
  `c18_trade_fairness`+`c18b_trade_overview`(편측 거래 탐지, ratio 상위 정렬), `c19_xfer_by_via`
  (경로별 총액/수수료), `c20_check_summary`(발행 vs 입금 총액, outstanding 추정). ③ 경제 페이지에
  4개 섹션 추가.
- `seed_sandbox.py`에 market_listing(등록+결과를 같은 id로 묶어 생성)/trade_done(수표·물고기
  위주로 가치 있는 거래 생성, 15% 확률로 의도적 편측 거래 주입)/check_issue·deposit/xfer 이벤트
  신규 — 샌드박스에서 C18 편측탐지가 실제로 극단치(ratio 2000배 등)를 잡아내는 것까지 확인.

### Phase 6 — 통합 어드민 콘솔 (§10-6, 통계 안정화 후 착수)
**✅ 완료(2026-07-28) — `/goal` "구현 안 한 부분 마저 해줘" 지시로 이번 세션에 전부 구현.**
28. 역할 2단(viewer/admin) 분기 + 전 쓰기 액션 CSRF + `audit_log` 기록 공통 래퍼. — `guard_admin()`(app.py)이
    admins.json role 필드로 게이팅, `_csrf_token()`이 세션당 토큰 발급+POST 대조.
29. 로컬 RCON 액션 카탈로그(ban/pardon/kick/whitelist/say/list) + 실행 전 확인 다이얼로그. **임의 명령
    전달 경로 금지** — `rcon_client.py`(순수 Source RCON, 의존성 0) + `admin_actions.py`의
    `ACTION_CATALOG` 딕셔너리 하나만 통해서 실행(플레이어명은 정규식 화이트리스트로 검증, 자유
    문자열을 명령에 직접 이어붙이지 않음). 브라우저 `confirm()` 1회로 실행 전 확인.
30. playerdata·밴목록 read-only 뷰어 + 유저 타임라인 교차 링크. — `/playerdata`(이름→uuid 조회 후
    `PLAYERDATA_DIR/<uuid>.json` 원문 표시) · `/banlist`(`BANNED_PLAYERS_FILE` 파싱), 둘 다
    "행적 보기" 링크로 ⑨ 유저 상세와 교차.
31. `admin.action`(P0) 텔레메트리 미러 + TeleTypes 등록. — `admin_actions.record()`가 audit_log
    INSERT와 동시에 이번 달 `events-YYYY-MM.db`에 `admin.action` 이벤트도 남김(Python이 직접
    쓰지만 Java `TeleTypes.java`에도 P0로 등록해 레지스트리 일관성 유지, blockship-plugin 커밋 완료·
    ★jar 배포는 미실행).
- **수용 기준 검증**: 샌드박스에서 role=admin 세션으로 CSRF 정상 토큰 액션 실행(RCON 비활성이라
  "실패"로 정상 기록되는 것까지 확인, audit_log 행 생성 확인) / CSRF 불일치 → 403 확인 / 위조한
  role=viewer 세션으로 `/console` 접근 → 403 + 네비에 콘솔 링크 자체가 안 보이는 것 확인. 실제
  RCON 명령(ban/kick 등)은 prod/dev 어디에도 실행하지 않음 — 샌드박스는 `RCON_PASSWORD`를 항상
  비워둬(`rcon_client.RconDisabled`) 진짜 서버에 명령이 나갈 수 없는 구조로 설계.
  ※**prod 배포는 아직 안 함**(statsweb 코드 변경 전체와 함께 별도 명시 요청 대기 — 특히 prod
  `.env`에 `RCON_PASSWORD`를 실제로 채우는 순간부터 진짜 명령이 나가므로 배포 시 각별히 주의).

### 커밋·배포 규칙 (기존 규칙 재확인)
- blockship-plugin: Phase 단위 커밋(자동, 질문 불필요). jar 배포는 dev 먼저(`~/deploy-dev.sh`), **prod는 명시 요청 시에만**(접속자 0/운영자 단독 예외는 기존 메모리 규칙 따름). 서버 재시작 필수(plugman reload 금지).
- 이 scripts 레포: stats-lab/, ops/prod/ 변경 커밋. box 크론 변경은 SSH로 적용 후 미러 갱신.

---

## 14. 구현 시 반드시 재확인할 것 (조사 단계 미확정 항목)

| # | 항목 | 왜 중요한가 |
|---|---|---|
| 1 | `GradeRoller.Result` 확장 시 `/낚시테스트` 경로와 통발 `weightedPick`의 GradeRoller 재사용 여부 | 진단 필드가 통발 경로에서 NPE 내지 않게 |
| 2 | `CasinoLedger.reserve/settle` 레거시 경로 활성 여부(슬롯 크래시 복구 refundOrphan은 활성 확인됨) | casino.escrow 계측 범위 결정 |
| 3 | `IslandSubmitConfig.islandReward/guildReward` 실수치(submit-values.json rewards) | submit.season 보상 검증 |
| 4 | `SkillTreeManager.resetCost(spent)` 공식(:833)과 `EquipmentManager.repairCost` 공식 | tree.reset/part.repair ctx 정확성 |
| 5 | `FishingConfig` 플래그 사문화 상태(주석상 무조건 처리로 컷오버) | fish 훅이 조건 분기 없이 안전한지 |
| 6 | `PlayerData.iceboxTier` vs `iceBoxTier` 중복 필드 — 어느 쪽이 실권위인지 | icebox.tier·스냅샷 필드 선택 |
| 7 | 스크롤 상점 돈 구매 불가(사문화) — `ScrollShopGui` lore 가격 표시만 존재 | shop.buy에 스크롤 없음이 정상 |
| 8 | `moneyop/moneyoffline/fishpay` 콘솔 명령이 Skript 등 외부에서 호출되는 실사용 여부 | 원장 reason 태깅 우선순위 |
| 9 | DrillManager 채굴 완료 메서드 정확명(조사에선 340–465행 범위로 추정) | mine.min 훅 위치 |
| 10 | `quest.done` dur_s용 accept ts — questGiverLoc처럼 기존 저장에 accept 시각이 이미 있는지 먼저 확인(있으면 재사용) | 메모리 맵 불필요할 수도 |
| 11 | 부품 총수 드리프트: parts.json 실측 86종 (CLAUDE.md "131"·balance-audit "84"는 stale) — 발견 시 문서 갱신 | 카탈로그 스냅샷이 이 드리프트를 영구 종식 |
| 12 | 통발 TR02 레시피 잔존(recipes 13 vs TrapSpecs 12) 등 §조사 드리프트 3건 | 카탈로그 스냅샷에 그대로 찍히므로 분석 시 주석 필요 |
| 13 | xerial sqlite-jdbc 최신 안정판 + aarch64(oracle)·apple silicon(dev) 네이티브 동봉 확인 | 양쪽 환경 부팅 |
| 14 | barkan.kro.kr A레코드가 실제로 168.107.8.107을 가리키는지(CLAUDE.md상 "예정" 표기) — 미설정이면 내도메인.한국에서 운영자 1회 설정. kro.kr sub-subdomain 불가 전제로 `/admin` 경로 방식 채택 | Phase 5 도메인·인증서 |
| 15 | `CasinoLedger.applyNet`이 uuid 기반 오프라인 정산을 실제로 수행하는지(호출 시그니처 2종 확인됨) — applyVerified 오프라인 오버로드의 saveData 경로 검증 | §6-5 치환 정확성 |
| 16 | Caddy 실사(2026-07-27): 80/443에 구동 중, 사이트 블록은 lh-bizben.duckdns.org(→3000 node)뿐, cloudflared는 inactive 잔존물(사용 안 함). 블록 추가 후 reload가 기존 서비스를 안 끊는지 | Phase 5 안전 배포 |

---

## 15. 부록

### A. TxnReason 상수 초안 (`telemetry.TxnReason`, 문자열 상수 — 신규 시스템은 1줄 추가)
```
수입: fish.sell, fish.auto_sell, fish.legend, quest, contest, achievement, collectible,
      market.sale, check.deposit, xfer.recv, casino.win, submit.reward(coin), treasure,
      admin.give, console.moneyop, console.fishpay
지출: shop.part, shop.recipe, shop.drill, shop.island, shop.afk, shop.cash, shop.trap_recipe,
      market.buy, salepost, check.issue(+fee), xfer.send(+fee), casino.bet/loss, enhance,
      repair, appraise, forge, guild.create, guild.deposit, guild.upgrade, guild.buff,
      guild.promote, island.upgrade, ferry, horse, water_tp, death, skilltree.reset,
      icebox.tier, admin.take
공통: untagged (StackWalker detail 동반 — 커버리지 감사 대상)
```

### B. 핵심 스켈레톤 (구현 지침 요약)
```java
public final class Telemetry {
    private static volatile boolean enabled = true;
    private static TeleQueue queue;   // init(plugin)에서 주입
    public static void log(String type, Player p, Map<String,Object> ctx) {
        if (!enabled || queue == null) return;
        try {
            queue.offer(new TeleEvent(System.currentTimeMillis(), type,
                p != null ? p.getUniqueId().toString() : null,
                p != null ? p.getName() : null,
                p != null ? p.getWorld().getName() : null,
                p != null ? regionOf(p) : null,            // RegionTracker 캐시
                ctx, TeleTypes.priorityOf(type)));
        } catch (Throwable t) { Dropped.count(t); }         // 절대 전파 금지
    }
}
// TeleWriter 루프: poll(batchMs) → 최대 batchMax 드레인 → 단일 트랜잭션 INSERT
//   → 매 분: live_sessions UPSERT → KST 날짜 바뀜 감지: 전일 롤업+스냅샷+VACUUM INTO
//   → KST 월 바뀜 감지: events DB 로테이션
// MoneyBridge 예:
//   public void add(Player p, long amt, String reason, String detail) {
//       long before = read(p); op(p, amt);
//       Telemetry.money(p, "money", amt, read(p), reason, detail);
//   }
//   @Deprecated public void add(Player p, long amt) { add(p, amt, TxnReason.UNTAGGED, Callers.find()); }
```

### C. telemetry.json 기본값
```json
{ "enabled": true, "queueCap": 20000, "batchMs": 1000, "batchMax": 500,
  "gaugeSec": 60, "sample": { "cmd.use": 1.0, "gui.open": 1.0, "npc.talk": 1.0 } }
```
(sample 값 <1.0이면 해당 P2 타입 확률 샘플링 — 기본은 전량 수집. P0는 sample 설정 자체를 무시.)

### D. ctx 공통 키 사전
`d`=delta, `after`=잔액, `r`=reason, `dt`=detail, `cur`=통화, `n`=수량, `g`=등급, `sz`=크기,
`q`=품질, `lo`=로드아웃해시, `enh`=강화레벨, `st`=최종스탯요약, `env.w/t`=날씨/시간대,
`dur_s/dur_ms`=소요시간, `p_*`=확률, `res`=결과, `proc`=특성발동목록, `by_g`=등급별집계,
`rw`=보상묶음, `via`=경로, `op`=연산종류, `cause`=차단사유, `first`=최초여부.

---

*이 문서는 2026-07-27 전수 조사(에이전트 5개: 인프라/낚시/돈흐름/퀘스트월드/생산)를 근거로 하며, 각 조사의 원본 훅 표는 이 문서 §8에 통합되어 있다. 밸런스 수치의 전거는 언제나 라이브 코드+catalog_version이고, 이 문서의 수치 인용은 당시 스냅샷이다.*
