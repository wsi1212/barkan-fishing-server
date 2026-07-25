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
  writes timestamped per-economy reports. Invoke for periodic reviews, after any content/tuning
  change, or when asked to audit a new economic system not yet covered.
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

각 경제의 데이터 위치·지표·경보선은 economy 하위 문서를 볼 것(아래 "경제별 모듈" 목록).

## 경제별 모듈

| 경제 | 상태 | 데이터소스 | 지표/경보선 | 감사 리포트 |
|---|---|---|---|---|
| 🎣 낚시 | ✅ 완료(2026-07-24, 갱신중) | [data-sources.md](references/data-sources.md) | [metrics.md](references/metrics.md), [stat-values.md](references/stat-values.md) | [audits/2026-07-24.md](audits/2026-07-24.md) |
| ⛏️ 광질(드릴+섬광산) | ✅ 완료(2026-07-25) — 🟢 양호(초안 🔴는 운영자확인 후 철회) | [mining-data-sources.md](references/mining-data-sources.md) | [mining-metrics.md](references/mining-metrics.md) | [audits/2026-07-25-mining.md](audits/2026-07-25-mining.md) |
| 🌾 농사(특수작물) | ✅ 완료(2026-07-25) — 🟡 1건(수박 이상치) | [farming-data-sources.md](references/farming-data-sources.md) | [farming-metrics.md](references/farming-metrics.md) | [audits/2026-07-25-farming.md](audits/2026-07-25-farming.md) |
| 🌿 채집(forage) | ✅ 골드가치만 완료(2026-07-25, 밀도추정 floor값) | (별도 data-sources 없음 — 소규모) | [cross-economy-values.md](references/cross-economy-values.md) §4 | — |
| 🪤 통발(trap) | ✅ 완료(2026-07-25) — 🟢 1건 발견·즉시수정(붉은사막 가격역전) | [trap-data-sources.md](references/trap-data-sources.md) | (audits 문서에 통합) | [audits/2026-07-25-trap.md](audits/2026-07-25-trap.md) |
| 🐉 이무기 보스(boss/ImugiBattle) | 🟡 절반만(재료 신설, 전투밸런스 미감사) | — | — | [audits/2026-07-25-imugi-yeouiju.md](audits/2026-07-25-imugi-yeouiju.md) |
| 카지노/요리/마켓/길드 | 미착수 (요리·카지노는 낚시 감사에 일부 편입됨) | — | — | — |

**전 경제 통합 골드가치표**: [cross-economy-values.md](references/cross-economy-values.md) — 낚시
시급 32,489원/h를 공통 앵커로, 4개 경제(낚시/광질/농사/채집) 전 원재료에 골드가치 산출 완료
(2026-07-25). 재계산: `scripts/cross_economy_values.py`.

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

## 낚시 경제 감사 루프 (기존, 매번 이 순서대로)

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

### 4. 파생 지표 계산 (Claude가 직접)
스냅샷 raw + 스탯가치로 아래를 계산해 스냅샷 `derived`에 적고 리포트에 넣는다:
- **레벨 도달 시간** — 누적 경험치(`cumulative_xp`) ÷ 시간당 경험치(장비/버프 시나리오별).
- **시간당 수입** — 등급 분포 × 등급 기본가 × 낚시 횟수 (★fish.json에 개별가 없음, grade×quality만).
- **강화 기대 비용** — down+체크포인트 반영 선형방정식(metrics.md). 낙관 하한 아님.
- **요리(F)** — 버프 스탯 × stat_value × 지속시간 = 버프가치(원). 티어·재료 대비 균형.
- **날씨(G)** — 환경보너스 × stat_value = 날씨 원/h. 다운사이드(난이도/도주) 차감. 강도·빈도.
- **장비(H)** — 부품 스탯가치(원/h) ÷ 가격 = 회수시간. 등급-가격-가치 정합성.
- ★요리(DishSpecs.java)·날씨(env-bonuses.json+WeatherManager)·장비(parts.json)는 pull.py가
  전량 파싱하진 않으므로, 값이 바뀌었으면 해당 소스를 재추출해 측정한다(data-sources.md 위치 참조).

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

## 주의
- **읽기 전용 감사다.** 이 스킬은 밸런스를 *진단*만 한다. 수치를 실제로 바꾸는 건 별개 작업 —
  리포트의 조치 권고를 사용자가 승인한 뒤에 코드를 고친다.
- pull.py는 Java **정규식 파싱**이라 코드 구조가 바뀌면 깨질 수 있다. warnings가 곧 조기경보다.
- 부품 총계는 **84종**이 정답(CLAUDE.md의 "131"은 stale — 발견 시 드리프트로 보고).
