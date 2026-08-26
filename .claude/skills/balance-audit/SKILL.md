---
name: balance-audit
description: >-
  Run a comprehensive, repeatable balance audit of the ENTIRE 바르칸 열도 server economy — not just
  fishing. Covers multiple sub-economies as modular dimensions: 낚시(fishing: leveling/RNG/equipment/
  enhance/cooking/weather/stat-values), 광질(mining/drill), 농사(farming/특수작물), and extensible to
  more (채집/forage, 마켓/trade, 길드/guild) as they're added. Use whenever the user wants 밸런스
  전수조사, 밸런스 감사, 서버 전체 밸런스 관리, check the balance of ANY economic system, review
  income/sinks/drop-rates/growth-times for mining or farming or fishing, judge whether 장비/작물/광석이
  재료 대비 구린지, value individual stats, or ask "밸런스 괜찮아?". Pulls authoritative numbers
  directly from BlockShip Java constants + runtime JSON (NOT the drifting balance.md), snapshots them
  per-economy, computes deltas against previous audits for continuity, flags doc-vs-code drift, and
  writes timestamped per-economy reports. ALSO use whenever the question is about individual item
  balance — whether a specific 낚싯대/작살/부품 is worth its materials, its money price, or its level
  requirement; whether material costs are measured correctly; whether the equipment ladder is
  monotone; or whether real alpha-tester/player telemetry agrees with the design model. Pulls live
  prod telemetry (alpha testers' actual throughput, income, loadouts, level pacing) instead of
  assumed constants. Invoke for periodic reviews, after any content/tuning change, when asked to
  audit a new economic system not yet covered, or when the user says the balance "feels off" for
  specific gear.
---

# 바르칸 서버 전체 밸런스 전수조사 (balance-audit)

밸런스 감사는 매번 다르게 보면 쓸모가 없다. **같은 소스에서, 같은 지표를, 같은 포맷으로** 뽑아야
감사 간 비교(연속성)가 성립한다. 이 스킬은 그 일관성을 강제한다.

**★2026-07-25부터 범위가 낚시 하나에서 "서버 전체 경제"로 확장됨.** 사용자 지시: "서버 전체의
밸런스를 관리하고 싶다". 서버엔 여러 독립 경제가 있고(낚시·광질·농사·채집·요리·카지노·마켓·길드…),
각각 자기 수입원·소모처·시간단위(캐스트/h, 채굴사이클, 작물성장일 등)를 갖는다. 이 스킬은 **경제별
모듈**로 구조화돼 있다 — 낚시가 첫 모듈이고, 광질·농사가 두 번째 확장(2026-07-25)이다. 새 경제를
감사해 달라는 요청이 오면 이 스킬로 처리하고, "경제별 모듈 추가" 패턴(아래)을 따라 확장한다.

## 공통 원칙 (모든 경제에 적용)

### 제1원칙 — 라이브 코드가 권위, balance.md는 파생물
밸런스 수치의 진짜 출처는 **BlockShip Java 상수 + 런타임 JSON**이다. `balance.md`는 그걸 사람이
옮겨 적은 문서라 **드리프트한다**(현재는 낚시 위주 — 광질/농사 문서화는 부실하거나 없을 수 있음).
감사할 때 balance.md의 숫자를 "정답"으로 믿지 말 것. balance.md는 오직 **"코드와 문서가
어긋났는가(drift)"를 잡는 대조 대상**으로만 쓴다.

### 제2원칙 — 공통 화폐는 원/h, 그러나 경제마다 "시간"의 의미가 다름
낚시=캐스트/h(150 가정, ★단 소모품 마모 계산엔 과대추정이니 쓰지 말 것 — metrics.md 참조), 광질=
드릴 사이클/h 또는 채굴 액션/h(경제별로 실제 메커니즘 확인 후 정의), 농사=성장일 기반(시간당이
아니라 "사이클당" 단위가 더 자연스러울 수 있음 — 강제로 시간 단위에 끼워맞추지 말 것). **각
경제의 자연스러운 처리량 단위를 코드에서 확인하고 그것부터 정의**하는 게 첫 스텝.

### 제3원칙 — 캡 설계: 확률 자연포화 vs 임의 매직넘버
새 경제에서도 인위적 캡을 만나면 낚시에서 확립한 원칙 적용: "확률이 100%에서 자연포화하는가 vs
임의의 매직넘버인가". 후자만 재검토 대상(예외: 카지노류 하우스엣지 보호 캡은 존치).

### 제4원칙 — 가격 ≠ 진짜 비용 (2026-07-25 낚싯대 사건에서 확립)
어떤 아이템이든 "가격"이라는 필드가 있다고 그게 곧 진짜 획득비용이라 가정하지 말 것.
`PartShopGui` 사례처럼 카테고리 최저사양 1개만 실제 상점가이고 나머지는 "레시피 해금비(보통
가격×0.5, 1회성)"일 수 있으며, 진짜 반복비용은 **조합 재료**(다른 경제에서 옴 — 낚싯대 재료는
광질에서 옴)에 있다. **재료가 어느 경제 소속인지 먼저 확인**하고, 크로스이코노미 비용이면 그
경제의 감사가 먼저 있어야 정확한 값이 나온다(이게 광질/농사 확장을 촉발한 이유).

### 제5원칙 — "코드에 캡이 없다" ≠ "무제한" (2026-07-25 섬광산 사건에서 확립)
어떤 메커니즘에 명시적 쿨타임/캡이 코드에 안 보인다고 바로 🔴(무제한 악용가능)로 단정하지 말 것.
섬 광산 생성기 사례: `BlockBreakEvent`만 가로채고 파괴속도 제한이 없어 "처리량 무제한"이라 초안
판정했으나, 실제로는 ①호퍼(자동수집) 개수 자체가 섬 레벨별로 캡됨 ②상점이 고티어 인챈트를 안 팔고
③인챈트 테이블 자체도 특정 레벨 이상은 실측상 안 나옴 — **인접 시스템 3개가 암묵적으로 상한을
만들고 있었다.** 교훈: 처리량/무제한성 관련 🔴·🟡 판정을 내리기 전에 **반드시 운영자에게 실측·체감을
확인**할 것 — 코드 검토만으로 "안전장치 없음"을 결론내지 말 것(인접 시스템에 있을 수 있음).

### 제6원칙 — "데이터에 있다" ≠ "실제로 존재한다" (2026-07-25 통발/붉은사막 사건에서 확립)
어떤 지역/콘텐츠가 시스템 정의(TrapSpecs.java, fish.json 등)에 등록돼 있다고 실제 게임에 존재한다고
가정하지 말 것. 통발 12개 지역 중 6개가 `regions.json`에서 좌표 `pos1=pos2=[0,0,0]`인 스텁이거나
아예 미등록이었다 — 상점은 이 지역들의 레시피를 팔고 있었지만 설치가 불가능했다. **"지역"을 참조하는
모든 분석(밸런스 수치 포함)은 반드시 regions.json에서 좌표 존재 여부를 먼저 대조**하고, 스텁 지역은
"미구현 콘텐츠"로 분리해 표기할 것 — 안 그러면 존재하지도 않는 콘텐츠의 수치로 잘못된 결론(예:
깊은호수가 진짜 있는 것처럼 "2.4배 불균형"이라 판정)을 내리게 된다.

### 제7원칙 — 가정 상수 금지, 실측이 권위 (2026-08-26 신설)
prod 텔레메트리(`telemetry/events-*.db`, `stats.db`)에 알파 테스터 실측이 쌓여 있다. **모델 상수는
거기서 온다.** 2026-07-24~08-26 넉 달간 이 스킬은 구 가정 「220 포획/h · 시도 259/h · 완주율 85%」로
돌았고, 실측은 **190.1 / 194.0 / 97.2%** 였다 — 소모품 유지비는 34% 과대, 수입은 14% 과대였다.
감사 첫 스텝은 이제 `pull_players.py` 다. 상세·함정 7개: [telemetry-data-sources.md](references/telemetry-data-sources.md).
★**실측 커버리지가 곧 결론의 유효범위다.** 관측 최고 레벨을 넘는 구간(2026-08-26 기준 Lv.26 초과)
은 «모델 외삽»이라고 리포트에 명시할 것 — A/S/G 장비와 종결 앵커는 실측 근거가 0이다.

### 제8원칙 — 재료는 결합생산물이다, 그래서 «원/개» 표를 손으로 적으면 반드시 틀린다 (2026-08-26)
한 번의 포획이 그 지역 드롭테이블 **전체**를 독립 판정한다(`CraftingManager.rollMaterials`). 그래서
「녹슨부품을 캐는 시간」에 나머지 6종이 공짜로 쌓인다. 재료마다 시간을 따로 더하면 같은 시간을
여러 번 센다. 게다가 진주·별빛진주는 **16개 지역 전부**에서 나오고, 장비 레시피 사용빈도 2·3위
중간재(강철심 175회·압축흑정석 163회)는 **광질 산출**이다. 이 셋을 표로는 표현할 수 없다.
⇒ 재료 가치는 **시간 단위 LP 의 쌍대가격**으로 낸다(`material_value.py`). 원 환산은 마지막에
딱 한 번, 그 구간의 실측 시급으로. 방법론: [material-value.md](references/material-value.md).

### 제9원칙 — 통화와 «모델 커버리지»를 먼저 분리하라, 안 하면 경보가 거짓으로 부푼다 (2026-08-26)
두 가지가 판정을 조용히 오염시킨다.
- **유령 가격**: parts.json 의 `price` 필드에는 잠수상점·캐시 아이템에도 원 가격이 들어 있는데
  **그 값으로는 아무도 살 수 없다**(잠수부의 낚싯대 = parts.json 160,000원 ↔ 실제 1,080P). 원
  원장에 섞으면 존재하지 않는 선택지가 생겨 정상 사다리 전체가 «지배당한» 것으로 잡힌다.
- **모델 커버리지**: 원/h 가치 모델이 없는 스탯(수중호흡·호흡시간·수영속도·공격력·공격속도·
  야간투시)이 절반 이상인 아이템은 «약한 아이템»이 아니라 «판정 불가 아이템»이다. 작살 55종 중
  **37종**이 여기 걸린다. 검사에서 제외하고 그 사실 자체를 보고할 것.

각 경제의 데이터 위치·지표·경보선은 economy 하위 문서를 볼 것(아래 "경제별 모듈" 목록).

## 경제별 모듈

| 경제 | 상태 | 데이터소스 | 지표/경보선 | 감사 리포트 |
|---|---|---|---|---|
| 🎣 낚시 | ✅ 완료(2026-07-24, 갱신중) — ★난이도/도주감소 재실측 + 전면 리밸런싱 + 골드곡선 v2(스킬트리·길드·플레이어티어 반영, 2026-07-25) | [data-sources.md](references/data-sources.md) | [metrics.md](references/metrics.md), [stat-values.md](references/stat-values.md) | [audits/2026-07-24.md](audits/2026-07-24.md), [audits/2026-07-25-difficulty-stat-value.md](audits/2026-07-25-difficulty-stat-value.md), [audits/2026-07-25-full-rebalance.md](audits/2026-07-25-full-rebalance.md), [audits/2026-07-25-gold-curve-redesign.md](audits/2026-07-25-gold-curve-redesign.md), ★[audits/2026-08-03-income-aggregation.md](audits/2026-08-03-income-aggregation.md) (수입공식 오류 — 앵커 32,489원/h는 **폐기 대기**), ★★[audits/2026-08-26-material-chance-revaluation.md](audits/2026-08-26-material-chance-revaluation.md) (재료확률 0.50→1.00 재평가 + 게이트 표 3중 오류 정정 + 🔴미끼 소모규칙 붕괴) |
| 📊 실측(알파 테스터) | ✅ 신설(2026-08-26) — 모델 상수 전면 교체(포획 220→190.1·소모 259→194.0·완주 85→97%), 실사용 장비 24/255종 | [telemetry-data-sources.md](references/telemetry-data-sources.md) | 同 문서 §실측요약 | [audits/2026-08-26-material-and-gear-precision.md](audits/2026-08-26-material-and-gear-precision.md) |
| 🧾 장비 사다리(재료·성능·레벨) | ✅ 신설(2026-08-26) — 🔴 지배 55종·🟡 역전 154쌍·전 카테고리 B→A 도매할인 위반 | [item-ladder-metrics.md](references/item-ladder-metrics.md) | 同 문서 | 同 리포트 |
| 🧪 재료 가치(LP 그림자가격) | ✅ 신설(2026-08-26) — 결합생산·다지역·광질 반영. A/S 「재료 관문」 판정 철회 | [material-value.md](references/material-value.md) | 同 문서 §경보선 | 同 리포트 |
| 🔱 작살(harpoon) | ✅ **완료(2026-08-26)** — 창 전용 스탯 6종 모델 신설(사이클+등급천장, 실측 교전 16/16 검증) → 55종 전부 판정 가능. 🔴 지배 30종·🟡 역전 77쌍·C→A 도매할인 +289%. ★실측이 「작살 저평가」 전제를 뒤집음(처리량 174.8 < 낚싯대 190.1, income 비 ×1.001) · ★공격력 1↔2 가 A 등급 천장을 가르므로 D 티어 빌드 4종이 무료급 철 작살에 지배당함 | [harpoon-data-sources.md](references/harpoon-data-sources.md) | 同 문서 §경보선 | [audits/2026-08-26-material-and-gear-precision.md](audits/2026-08-26-material-and-gear-precision.md) |
| ⛏️ 광질(드릴+섬광산) | ✅ 완료(2026-07-25) — 🟢 양호(초안 🔴는 운영자확인 후 철회) | [mining-data-sources.md](references/mining-data-sources.md) | [mining-metrics.md](references/mining-metrics.md) | [audits/2026-07-25-mining.md](audits/2026-07-25-mining.md) |
| 🌾 농사(특수작물) | ✅ 완료(2026-07-25) — 🟡 1건(수박 이상치) | [farming-data-sources.md](references/farming-data-sources.md) | [farming-metrics.md](references/farming-metrics.md) | [audits/2026-07-25-farming.md](audits/2026-07-25-farming.md) |
| 🌿 채집(forage) | ✅ 골드가치만 완료(2026-07-25, 밀도추정 floor값) | (별도 data-sources 없음 — 소규모) | [cross-economy-values.md](references/cross-economy-values.md) §4 | — |
| 🪤 통발(trap) | ✅ 완료(2026-07-25) — 🟢 1건 발견·즉시수정(붉은사막 가격역전) | [trap-data-sources.md](references/trap-data-sources.md) | (audits 문서에 통합) | [audits/2026-07-25-trap.md](audits/2026-07-25-trap.md) |
| 🐉 이무기 보스(boss/ImugiBattle) | 🟡 절반만(재료 신설, 전투밸런스 미감사) | — | — | [audits/2026-07-25-imugi-yeouiju.md](audits/2026-07-25-imugi-yeouiju.md) |
| 🏘️ 마켓/랭킹/여관/송금/길드/스킬트리/카지노/아이스박스 | ✅ 완료(2026-07-25) — 🟢 대부분 정상, 송금 이중과금 1건 발견·즉시수정 | — | — | [audits/2026-07-25-full-system-review.md](audits/2026-07-25-full-system-review.md) §항목6 |
| 🎁 부품/낚싯대 레시피비용 곡선 + 히든장비 | ✅ 완료(2026-07-25) — 🔴 히든 낚싯대 8종 획득불가 버그 발견·즉시수정 | — | — | [audits/2026-07-25-full-system-review.md](audits/2026-07-25-full-system-review.md) §항목1·2 |
| 📜 퀘스트/도전과제 보상 + 마을별 난이도분포 | ✅ 완료(2026-07-25) — 🟡 콘텐츠 갭 다수(수치문제 아님) | — | — | [audits/2026-07-25-full-system-review.md](audits/2026-07-25-full-system-review.md) §항목3·5 |
| ⚙️ 드릴 최종값 | ⚠️ 재개필요(2026-08-03) — 확정구조 **T1 흑정석/T2 철광석(둘 다 mine 월드)/T3 자수정(레드_로드 전용)**, 셋 다 실제 빌드 확인. ★regions.json "광산" 지역은 채굴처 **아님**(채굴 존 등록 금지). 미해결=**철광석 소비 레시피 0건**(T2 산출물 쓸 데 없음), 유저 결정 대기 | [mining-data-sources.md](references/mining-data-sources.md) | — | [audits/2026-07-25-full-system-review.md](audits/2026-07-25-full-system-review.md) §항목4·조치완료3 |

**전 경제 통합 골드가치표**: [cross-economy-values.md](references/cross-economy-values.md) —
★2026-08-05 전면 재산정. 구 단일 앵커 32,489원/h는 **폐기**했다(피티 미반영 + 150캐스트 가정의
곱절 오류, 게다가 구간마다 시급이 4배 차이나 단일 상수가 성립하지 않음). 지금은 **구간별 앵커**
를 쓰고, 활동의 레벨 게이트에 맞는 것을 권장값으로 표시한다. ★**2026-08-26 재교체**: 실측
**초반 76,493 / 중반 115,083 / 종결 327,043(외삽)** — 구 값(95,403 / 133,022 / 370,210)은
«220 포획/h» 가정에서 나왔고 실측은 190.1 이었다. 앵커는 `measured.py` → `price_ladder.py` 로
자동 파생되므로 실측 스냅샷을 갱신하면 전 경제가 같이 갱신된다.
재계산: `scripts/cross_economy_values.py --anchor 중반`.

**장비/소모처 가격 사다리**: [scripts/price_ladder.py](scripts/price_ladder.py) — 실측 처리량
(`measured.py`, 실측 190.1 포획/h) + 피티 반영 MC로 구간 수입을 뽑고, "풀세팅 = 구간 수입의 45%" 기준으로 장비 가격
밴드를, "쓰는 시점의 노동시간" 기준으로 소모처 값을 역산한다. 2026-08-05 리프라이싱의 근거.

### 경제별 모듈 추가 패턴 (새 경제 감사 요청 시)
1. 그 경제의 코드/JSON 위치를 파악(Agent로 조사 — 이 스킬이 아직 모르는 시스템일 확률 높음).
2. `references/<economy>-data-sources.md` 신설 — 낚시의 data-sources.md와 같은 포맷(파일 위치 표).
3. 그 경제의 자연스러운 처리량 단위 확립(제2원칙) → `scripts/pull_<economy>.py` 작성(낚시
   pull.py를 참고하되 그 경제 전용 파서로).
4. `references/<economy>-metrics.md` — 경보선·계산공식.
5. `audits/<date>-<economy>.md` 리포트 (낚시 리포트와 같은 고정 포맷: 요약/델타/축별분석/드리프트/
   조치권고).
6. 이 SKILL.md의 "경제별 모듈" 표에 행 추가 + description frontmatter에 새 경제 키워드 추가.
7. 크로스이코노미 재료가 있으면(예: 낚싯대가 광질 재료로 만들어짐) 그 사실을 양쪽 리포트에 상호
   참조로 남길 것 — 한쪽만 감사하면 재료비용이 빠진 반쪽짜리 결론이 나온다(낚싯대 사건 교훈).

## 낚시 경제 감사 루프 (매번 이 순서대로)

### 0-a. 자기점검 (★먼저 돌린다 — 도구가 고장난 채 감사하면 틀린 리포트가 남는다)
```bash
python3 .claude/skills/balance-audit/scripts/selftest.py
```
검사 8종: 라이브 JSON 스키마 · 실측 스냅샷 유효성 · **상수 단일화**(스크립트 간 같은 값인가) ·
LP 쌍대성 검산 · 작살 모델 vs 실측 대조 · 모델 커버리지 · 문서 드리프트 · 획득 불가 콘텐츠.
🔴 가 하나라도 있으면 감사를 진행하지 말 것. 🟡 는 진행하되 리포트에 명시한다.
★이 스킬의 실패 양식은 «틀린 수치가 조용히 오래 사는 것»이다(넉 달 3건). selftest 가 그 방어다.

### 0-b. 실측 상수 갱신 (★2026-08-26 신설 — 이걸 건너뛰면 나머지 전부가 가정 위에 선다)
```bash
python3 .claude/skills/balance-audit/scripts/pull_players.py --fetch
```
- prod 텔레메트리에서 처리량·완주율·등급분포·실현가·지역분포·작살·광질·실사용 로드아웃·레벨
  도달시간을 뽑아 `audits/snapshots/<date>-players.raw.json` 에 고정한다.
- `--fetch` 는 맥에서만 된다(SSH). 클라우드 세션은 `audits/telemetry-cache/` 사본으로 돌린다.
- **`warnings` 를 반드시 읽어라.** 커버리지 상한·조업 편중·전환율 경고가 그대로 리포트의
  «유효범위» 문장이 된다.
- 이 스냅샷이 있으면 `material_value.py` · `item_ledger.py` 가 자동으로 실측 상수를 쓴다.
  없으면 FALLBACK 상수로 돌고 그 사실을 출력 첫 줄에 밝힌다.

### 1. 스냅샷 추출 (기계, 결정론적)
```bash
python3 .claude/skills/balance-audit/scripts/pull.py --date <오늘 YYYY-MM-DD>
```
- 라이브 Java 상수 + JSON에서 4개 축 핵심 수치를 정규식/파싱으로 뽑아
  `audits/snapshots/<date>.raw.json`에 고정한다.
- **`warnings` 필드를 반드시 확인**하라. 경고가 있으면 정규식이 상수 위치를 놓친 것 —
  코드 구조가 바뀌었다는 신호다. 해당 파일을 직접 읽어 값을 확인하고, 필요하면 pull.py의
  정규식을 고친 뒤 다시 돌린다. **경고를 무시한 채 감사하지 말 것.**

### 2. 델타 비교 (연속성의 핵심)
```bash
python3 .claude/skills/balance-audit/scripts/diff.py --auto <오늘>.raw.json
```
- 직전 스냅샷 대비 바뀐 수치만 출력. "변경 없음"이면 튜닝이 안 들어간 것.
- 첫 감사면 베이스라인이라 델타가 없다 — 그대로 진행.

### 3. 스탯 실질가치 산출 (공통 잣대)
```bash
python3 .claude/skills/balance-audit/scripts/stat_value.py
```
- 각 스탯 1단위를 원/h로 환산(판매1%=1.0 앵커). 요리·날씨·장비를 비교할 **공통 화폐**.
- 상세·방법론·직관 교정: [references/stat-values.md](references/stat-values.md).
- ★**재료 게이트 수치는 손으로 적지 말 것** — `scripts/material_gate.py` 가 라이브 recipes/
  materials/parts 에서 매번 다시 뽑는다(구 표를 손으로 옮겨 적었다가 «아이템 1점을 1티어라
  부르고 별빛진주를 8%로 적는» 3중 오류가 4개월 갔다, 2026-08-26).
- ★**income 곱셈이 안 통하는 스탯이 있다** — 그걸 «0» 이나 «별도 효용»으로 치우지 말 것.
  `재료확률`은 게이트 렌즈(재료 게이트 ÷(1+v/100)), `돌진쿨감`은 작살 사이클 모델로 값을 낸다.
  둘 다 2026-08-23에 편입했고, 1차 모델이 종결값을 0으로 뱉었다가 요리 싱크를 세어 고쳤다 —
  경위·교훈: [audits/2026-08-23-material-chance-stat.md](audits/2026-08-23-material-chance-stat.md).

### 4. 파생 지표 계산 (Claude가 직접)
스냅샷 raw + 스탯가치로 아래를 계산해 스냅샷 `derived`에 적고 리포트에 넣는다:
- **레벨 도달 시간** — 누적 경험치(`cumulative_xp`) ÷ 시간당 경험치(장비/버프 시나리오별).
- **시간당 수입** — 등급 분포 × 등급 기본가 × 크기점수 배율 × 낚시 횟수 (★fish.json에 개별가 없음).
- **강화 기대 비용** — down+체크포인트 반영 선형방정식(metrics.md). 낙관 하한 아님.
- **요리(F)** — 버프 스탯 × stat_value × 지속시간 = 버프가치(원). 티어·재료 대비 균형.
- **날씨(G)** — 환경보너스 × stat_value = 날씨 원/h. 다운사이드(난이도/도주) 차감. 강도·빈도.
- **장비(H)** — 부품 스탯가치(원/h) ÷ 가격 = 회수시간. 등급-가격-가치 정합성.
- ★요리(DishSpecs.java)·날씨(env-bonuses.json+WeatherManager)·장비(parts.json)는 pull.py가
  전량 파싱하진 않으므로, 값이 바뀌었으면 해당 소스를 재추출해 측정한다(data-sources.md 위치 참조).

### 4-b. 재료 가치 + 장비 사다리 (★2026-08-26 신설)
```bash
python3 .claude/skills/balance-audit/scripts/material_value.py     # 재료 λ(h/개) + 등급별 풀세팅 LP
python3 .claude/skills/balance-audit/scripts/item_ledger.py        # 장비 255종 원장 + 사다리 검사 4종
python3 .claude/skills/balance-audit/scripts/item_ledger.py --dead # 죽은 콘텐츠
python3 .claude/skills/balance-audit/scripts/harpoon_value.py      # 창 전용 스탯 + 등급천장
python3 .claude/skills/balance-audit/scripts/harpoon_value.py --validate  # 모델 vs 실측 대조
```
- `material_value.py` 가 **재료 «원/개» 의 유일한 권위**다. 표를 손으로 옮겨 적지 말 것(제8원칙).
- `item_ledger.py` 가 «재료 · 성능 · 레벨제한» 3축을 한 원장에 넣고 지배·역전·도매할인·편차를
  검사한다. 경보선: [item-ladder-metrics.md](references/item-ladder-metrics.md).
- ★`material_gate.py` 는 **구 휴리스틱**이다(지역 안 max / 지역 간 sum, 광질 재료 무시). 결과가
  `material_value.py` 와 다르면 **LP 쪽이 맞다**. 낚싯대 게이트 «가장 나쁜 경우» 상한이 필요할
  때만 참고로 쓰고, 수치를 리포트에 옮길 때는 LP 값을 쓸 것.
- ★`gear_payback.py` 도 구 버전이다(재료비 0, 레벨축 없음, 유령가격 미분리, 작살 270 포획/h 가정).
  `item_ledger.py` 가 대체하며, 남겨 둔 건 과거 감사와의 델타 비교용이다. 둘 다 실행하면
  터미널에 DEPRECATED 경고를 띄운다.
- `harpoon_value.py` 가 **창 전용 스탯 6종**(공격력·공격속도·수영속도·수중호흡·호흡시간·돌진쿨감)의
  원/h 를 낸다. income 곱셈이 아니라 **사이클 + 등급천장** 모델이다 — 공격력이 부족하면 그 등급은
  제한시간 안에 못 잡으므로 가치가 계단으로 뛴다. `--validate` 가 예측을 prod 실측 포획 기록과
  대조하는 회귀 테스트이고, **불일치가 곧 «모델이 코드 규칙을 놓쳤다»는 신호**다(실제로 그렇게
  «돌진 피해 = 공격력 ×2» 를 찾았다). 경보선: [harpoon-data-sources.md](references/harpoon-data-sources.md).

### 5. 이슈 판정 (metrics.md 경보선 대조)
각 축을 metrics.md의 정상 범위와 대조해 이슈를 등급화한다:
- 🔴 **치명** — 경제 붕괴(인플레·머니싱크 부재), 성장 벽이 이탈 유발, 확률 버그
- 🟡 **주의** — 정상 범위 경계, 이전 감사 대비 큰 델타(±15%↑), 종결급 편중
- 🟢 **관찰** — 사소한 편차, 다음 감사에서 추이 볼 것
- ⚪ **드리프트** — 코드 값 ≠ balance.md 값. 값 자체는 정상이어도 문서를 고쳐야 함.

### 6. 리포트 작성 (고정 포맷)
`audits/<date>.md`에 아래 **고정 섹션 순서**로 쓴다 (포맷 고정 = 감사 간 비교 가능):

```markdown
# 밸런스 감사 — <date>

## 요약 (TL;DR)
- 종합 상태: 🟢/🟡/🔴 한 줄
- 직전 감사(<이전date>) 대비 핵심 변화 3줄 이내
- 이번에 조치 권고하는 이슈 개수 (🔴 n · 🟡 n)

## 델타 (직전 감사 대비)
diff.py 출력을 사람 말로 해석. "Lv.70 누적경험치 X→Y (+Z%)" 식. 없으면 "변경 없음".

## A. 레벨링 / 성장 곡선
## B. 경제 (수입/소모)
## C. RNG / 등급
## D. 장비 / 강화 / 부품
## E. 스탯 실질가치 (stat_value.py 표 + 직관 교정)
## F. 요리 (버프가치 원 vs 제작난이도)
## G. 날씨 (환경보너스 원/h + 다운사이드 + 빈도)
## H. 장비 스탯가치 vs 가격 (회수시간, 등급-가격 정합성)
## I. 재료 가치 (LP 그림자가격 · 병목 · 활동배분)
## J. 장비 사다리 (지배 · 레벨-성능 역전 · 도매할인 · 동일레벨 편차)
## K. 실측 대조 (모델 상수 vs 알파 테스터 실측 · 유효범위)
(각 축: 핵심 수치 표 + 파생 지표 + 이슈 등급 + 근거)

## 드리프트 (코드 vs balance.md)
⚪ 항목 목록 + 권고(코드/문서 중 뭘 고칠지)

## 조치 권고 (우선순위 순)
1. [🔴] ... — 무엇을 어느 파일에서 어떻게
```

작성 후 스냅샷의 `derived` 섹션을 채운 최종 JSON을 저장한다(다음 감사가 이 파생값과도 델타 비교 가능).

## 산출물 커밋 (연속성 보존)
감사 산출물(`audits/*.md`, `audits/snapshots/*.raw.json`)은 **git에 커밋**한다 — 히스토리 자체가
연속성이다. blockship-plugin이 아니라 이 scripts 레포에 커밋하며, 커밋은 규칙상 물어보지 않고 바로.
`pending.raw.json`은 임시 파일이니 커밋하지 않는다.

## 스크립트 지도 (무엇이 무엇을 대체했는가)

| 스크립트 | 역할 | 상태 |
|---|---|---|
| `measured.py` | **실측 상수 단일 출처.** 다른 스크립트는 여기서만 가져간다 | ✅ 권위 |
| `pull_players.py` | prod 텔레메트리 → 실측 스냅샷 (감사 0-b 단계) | ✅ 권위 |
| `selftest.py` | 스킬 회귀 테스트 8종 (감사 0-a 단계) | ✅ 권위 |
| `pull.py` / `diff.py` | 라이브 Java·JSON 스냅샷 + 델타 | ✅ 권위 |
| `stat_value.py` | 낚싯대 스탯 원/h (판매보너스 1% = 앵커) | ✅ 권위 |
| `material_value.py` | 재료 원/개 = 시간 LP 쌍대가격 | ✅ 권위 |
| `item_ledger.py` | 장비 255종 재료·성능·레벨 원장 + 사다리 4종 | ✅ 권위 |
| `harpoon_value.py` | 창 전용 스탯 6종 + 등급천장 | ✅ 권위 |
| `price_ladder.py` | 구간 수입·가격 밴드 역산 | ✅ 권위 |
| `minigame_sim.py` `gradroller_sim.py` | 난이도·등급 롤 시뮬 | ✅ 권위 |
| `enhance_lines.py` | 강화표(enhance.json) **라인 기반 재생성** + **난이도 3층 예산의 단일 권위**(낚싯대 기본 ROD_DIFF · 강화 총량 ENH_DIFF · 숙련부품 PART_DIFF) | ✅ 권위 |
| `material_distribution.py` | 재료 **지역 분배** 감사 — 접근 비용(항구 거리 + 어종 난이도) ↔ 드랍 풍족도 상관, 지역 전용 재료, 소비처 없는 재료 | ✅ 권위 |
| `part_lines.py` | 부품 **계열 × 레벨 성능 사다리**(현재 D급). 슬롯 주스탯·난이도·재료확률은 고정, 계열 부스탯만 스케일 | ✅ 권위 |
| `rod_lines.py` | 스폰마을 낚싯대 **라인 설계** — 라인별 메인/부스탯 고정 → 난이도는 순간이동 문턱에서 역산 → 남은 자유도만 회수시간에 적합 | ✅ 권위 |
| `cross_economy_values.py` `buff_values.py` `cooking_full_audit.py` `bait_reprice.py` `xp_curve_lv70.py` `gold_curve*.py` `gen_balance_workbook.py` | 경제별 파생 | ✅ 그대로 |
| `material_gate.py` | 구 재료 게이트 휴리스틱 | ⛔ **DEPRECATED** → `material_value.py` |
| `gear_payback.py` | 구 회수시간 | ⛔ **DEPRECATED** → `item_ledger.py` |
| ~~`rod_rebalance.py`~~ | 구 낚싯대 라인 스케일러 | ⛔ **삭제(2026-08-27)** → `rod_lines.py` |

### ★난이도는 «단가 × 점수»로 세지 않는다 (2026-08-27)

`zoneWidth = 8 + floor(net/2)` 라 난이도 1점이 두 점마다 존 한 칸을 넓히고, 등급마다
«이미 100%» 인 지점에서 값이 죽는다. 1점의 값이 구간에 따라 **3~4배** 다르다.
`stat_value.diff_curve(stage)` 가 누적표를 주고 `item_ledger` 는 그걸 조회한다.
그리고 «순간이동(overflowDiff>0)» 은 캘리브레이션과 무관하게 참인 **구조 지표**다 —
난이도를 논할 때는 성공률보다 이걸 먼저 쓴다(`rod_lines.teleport_frac`).

### ★사다리 기준은 «순성능», 회수시간이 아니다 (2026-08-27 유저 결정)

    "회수는 일단 빼고 계산 다시 해줘. 짜피 재료들 밸런스도 다시 조정해야하거든,
     그래서 일단 성능들로만. 성능은 레벨이 같아도 10% 20%정도는 달라도됨(재료부품가격으로 커버)"

회수시간 = 성능 ÷ 비용이고 비용(재료·가격)이 곧 재조정 예정이라 «움직이는 분모»에 맞추는
일이 된다. 성능만 사다리에 올려놓고 비용은 나중에 덮는다.

    사다리: ln(순성능) = 8.917 + 0.0628 × Lv     → 레벨당 +6.5%
    (스폰마을 낚싯대 21종 로그선형 적합, 2026-08-27 라이브 실측)
    허용: ±10% 목표 · ±20% 경보. `rod_lines.EFF_A/EFF_B/BAND_OK`

★**레벨 배치를 바꾸면 사다리를 재적합한다.** 사다리는 «레벨→성능» 서술이므로 등급의
  레벨제한이 움직이면 서술도 움직인다. D 진입을 Lv5→3 으로 내렸을 때 계수가
  8.814/0.0667 → 8.907/0.0627 로 바뀌었다(저레벨 목표 +8.5% · Lv27 −1.4%, 곡선 완만화).
  ★성능을 구 사다리에 다시 맞추면 안 된다 — 레벨을 내린 것은 «접근성» 조치이고, 성능을
  같이 내리면 13% 너프가 되어 목적과 반대가 된다.

★**`BAND_EXEMPT_UP`** — 사다리보다 강해도 끌어내리지 않는 종. 등록은 «효용이 특정 구간에
  쏠려 있어서 사다리(원/h 등가)가 과소평가하는 경우»만 (현재 `수련생 낚싯대` 1종 — 초반
  레벨링 전용). **면제종은 사다리 적합에서도 뺀다** — 안 빼면 면제분이 사다리를 끌어올려
  나머지가 전부 «약함»으로 잡힌다. 근거 없이 늘리면 사다리가 의미를 잃는다.

★**계수를 매 실행마다 재적합하지 말 것** — 자기 출력에 다시 맞추면 사다리가 표류한다.
  전체 파워를 올리려면 `EFF_A` 를, 진행 속도를 바꾸려면 `EFF_B` 를 옮긴다.

★**라인 안 스탯 단조성이 성능 사다리보다 우선한다.** `item_ledger` 는 스탯 1점을 그
  아이템 레벨의 구간(stage) 가치로 세는데, 스폰마을은 Lv20 에서 초반→중반 경계를 넘고
  그 순간 판매보너스 1% 가 843 → 1,175 원/h 로 **39% 도약**한다. 사다리는 레벨당 6.9% 만
  오르므로 B급은 «더 적은 점수로 목표 성능»을 달성하고 **표시 숫자가 내려간다**(실측:
  예리한 크기 10 < 낚시꾼의 14). 구간 경계는 모델의 산물이라 표시 숫자를 우선하고
  (`rod_lines._apply_line_floor`, 메인+부스탯 전부), 그 낚싯대는 밴드 위쪽으로 올린다.

### ★계열 부스탯의 «정규화 가치»는 계열마다 다르다 (2026-08-27)

    성장 = 경험치 1.00 + 트리플찬스 2.00      상인 = 판매보너스 1.00 + 더블찬스 1.00
    행운 = 등급업 2.11 + 행운 **0.40**        채집 = 재료확률 1.00 (게이트축)

행운 라인은 행운 스탯이 0.40 이라 같은 숫자를 줘도 절반이 안 된다 — **«행운 4» 가
«트리플찬스 1» 보다 약하다.** 유저에게는 4 > 1 로 보이는데 실제로는 1.6 < 2.0 이다.
그래서 계열을 신설할 때 «C급 값을 비율로 줄이기»로는 형평이 안 맞고, 반드시
`part_lines.py` 로 순성능 사다리에 맞춰야 한다(실측: 첫 산출에서 Lv4 성장 부품이
Lv6 상인 부품보다 강한 레벨 역전이 5건 났다).

★`part_lines` 의 가치 조회는 **STAT_KEY 하나로 부족하다** — 경험치는 `GROWTH_KEY`,
  재료확률은 `GATE_KEY` 에 있다. STAT_KEY 만 보면 경험치 기여가 0 으로 잡혀 스케일이
  어긋난다(채집 찌가 목표의 −24.5% 에서 더 못 올라갔다).

### ★접근 비용의 주축은 «항구(판매처)로부터의 거리»다 (2026-08-27 유저 확정)

    "재료는 너가 중요한걸 하나 놓쳤는데 물고기 판매와 떨어진 거리가 정말 중요함.
     난이도는 강이 더 쉽지만 스폰도시에서 강 가는게 귀찮아서 잘 안가게됨.
     고로 강이 항구보다 더 잘나와야하는게 맞음"

**페리가 미구성**이다(`ferries.json` 에 `test` 노선 하나) — 이동은 전부 도보/말이라
거리가 곧 비용이다. 기준점은 스폰이 아니라 **항구**(물고기를 파는 곳). 난이도(어종 풀
평균 등급)는 보조축이고, 둘을 0~1 정규화해 더한 것이 접근 비용이다.

★**드랍표 기본값이 Java 에 그림자 사본으로 있다** — `MaterialLoader.buildDefaults()`.
  `mergeMissingDefaults()` 가 «키가 없으면» 되살리므로 **JSON 에서 지운 지역이 재부팅 때
  부활한다**(실측: 물보라동굴). 분배를 바꾸면 Java 기본값도 같이 바꿔야 한다.

★**드랍표 항목은 «영역이 있고 어종 풀이 있는» 지역에만.** 어종 풀은 부모 지역 체인으로
  상속되므로(`FishingListener`: 항구 → 스폰도시 → 바르칸) 상위 컨테이너 지역은 자기
  어종이 0 이고 낚을 게 없다 = 재료도 안 나온다. `selftest` §7 이 유령 지역을 잡는다.

### ★재료는 «가까운가»가 아니라 «실제로 도달하는가»로 본다 (2026-08-27)

판정 = 실측 지역 분포 × 드랍률 → «아이템 하나 분량의 파밍 시간». 지역은 레벨 게이트가
아니라(regions.json 레벨제한이 대부분 0) **소프트 게이트**이고, 실측 분포가 그 결과다.

    실측: 항구 67.2% · 강 18.9% · 협곡 4.3% · 오아시스 4.3% · 늪지대 1.3% · 정상 1.2%
          (붉은사막 · 물보라동굴 · 대양 · 원양 = 0%)

    ✅ 거대비늘 2.7h · 보석 1.3h · 나뭇가지 4.7h  ← 유저 확정 «좀 멀리 있어도 안 말림»
    🔴 행운의구슬 26h (정상 5% 뿐) · 안개수정 20h · **산호조각 1,070h** (대양/원양 0%)

한도는 부품 3.5h · 장비 7.0h — «채집 라인 테마(거대비늘)를 통과시키는 선»에 뒀다.
이 한도의 역할은 20h/1,070h 급을 잡는 것이다.

### ★난이도 예산은 3층이고 한 곳에서만 정의한다 (2026-08-27)

    ① 낚싯대 기본  `enhance_lines.ROD_DIFF`
    ② 강화 총량    `enhance_lines.ENH_DIFF`   ← 배수 금지. 등급당 +1 사다리다
    ③ 숙련 부품    `enhance_lines.PART_DIFF` × 릴·줄·바늘·찌 4슬롯

세 층의 합이 «순간이동 문턱»을 만든다. 한 층만 보고 조정하면 목표가 깨진다.
유저 제약 두 개가 이 구조를 강제했다 — «C풀강 ≥ B중반강화 ≥ A기본»(강화가 2등급을
건너뛰면 안 됨)과 «C풀강 + C 숙련부품 → S 순간이동 0%». 강화만으로는 둘을 동시에
만족시킬 수 없어서 부품이 나머지를 대야 한다.

**주스탯은 «라인 메인»으로 강제한다** — «정규화 가치 최대»로 고르면 단가 높은 스탯이
라인 정체성을 계속 이긴다(실측: 행운 라인 15종 전부가 등급업 2.11 에 행운 0.40 이 밀려
«강화하면 등급업만 오르는 행운 낚싯대»가 됐다). 유저 요청은 «같은 계열의 스탯»이 오르는
것이므로 기준은 가치가 아니라 계열이다.

**주스탯 배수 규칙**: 풀강 시 주스탯 `+= 기본 × 2.0`(총 3배). 근거는 등급 사다리가
×1.7 이라는 것 — C 6 → 풀강 18 = A 기본. 유저의 «잘해야 A기본» 이 이 배수의 상한이다.
**난이도만 예외**로 총량 고정표를 쓴다(정수 사다리라 배수를 쓰면 C→S 가 된다).

### ★도망감소는 난이도의 대체재가 아니다 (2026-08-27)

0→80 이 B 를 69%→100% 로 올리지만 **A 는 +5%p · S 는 +2%p** 뿐이고 80 에서 포화한다.
존폭이 1~2칸인 A/S 에서는 도주율을 낮춰도 계속 미스해 `escapeInc` 가 100 까지 밀어올린다.
난이도는 «맞히게» 해주고 도망감소는 «한 번 더 기회»를 준다 — 존이 1칸이면 기회를 더 줘도
못 맞힌다. ⇒ 줄 슬롯(도망감소 전담)은 회수 중위 19.7h 로 홀로 무너져 있는데(릴 6.6 ·
바늘 9.5 · 찌 11.8, 재료원은 4슬롯 동일) **수치를 3배로 올려도 해결되지 않는다.**

**시뮬 상수는 라이브와 짝이다.** `minigame_sim.MAX_ZONE_JUMP` ↔
`MinigameManager.MAX_ZONE_JUMP` · `success_rates` 의 크기난이도 가중 ↔
`MinigameTables.sizeDifficulty`. 2026-08-27 전까지 둘 다 어긋나 있었고(전체무작위 도약 ·
size=0 고정) S+ 평가가 통째로 틀렸다.

**상수를 스크립트에 하드코딩하지 말 것.** 2026-08-26 이전엔 구 가정 `220 포획/h` 가 네 파일에 흩어져
있었고 하나만 고쳐진 채 넉 달을 갔다. 새 상수가 필요하면 `measured.py` 에 넣고 거기서 읽는다 —
`selftest.py` §3 이 스크립트 간 값이 갈라지는 순간 잡는다.

## 주의
- **읽기 전용 감사다.** 이 스킬은 밸런스를 *진단*만 한다. 수치를 실제로 바꾸는 건 별개 작업 —
  리포트의 조치 권고를 사용자가 승인한 뒤에 코드를 고친다.
- pull.py는 Java **정규식 파싱**이라 코드 구조가 바뀌면 깨질 수 있다. warnings가 곧 조기경보다.
- 부품 총계는 **255종**이 정답(2026-08-26 parts.json 실측: 낚싯대 76·작살 55·릴 25·줄 25·바늘 25·
  찌 25·미끼 24). CLAUDE.md 의 "131종"은 stale 이다(작살 항목 자체가 없다) — 발견하면 드리프트로
  보고할 것. references 쪽은 2026-08-26 에 갱신했고 `selftest.py` §7 이 재발을 감시한다.
- **구 스크립트를 새 것과 섞어 쓰지 말 것.** `material_gate.py`(재료)·`gear_payback.py`(회수시간)는
  각각 `material_value.py`·`item_ledger.py` 로 대체됐다. 같은 리포트 안에서 두 계열의 숫자를
  나란히 쓰면 단위·전제가 달라 또 3중 오류가 난다(2026-08-26 이전이 그랬다).
