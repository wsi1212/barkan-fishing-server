---
name: balance-audit
description: >-
  Run a comprehensive, repeatable balance audit of the 바르칸 열도 fishing server across four
  dimensions — leveling/growth curve, economy (income vs sinks), RNG/grades, and
  equipment/enhance/parts. Use whenever the user wants to 밸런스 전수조사, 밸런스 감사, 밸런스 점검,
  check the balance, review the economy/curve/drop-rates, audit money income vs sinks, or ask
  "밸런스 괜찮아?" / "지금 밸런스 어때?". Pulls authoritative numbers directly from the BlockShip
  Java constants + runtime JSON (NOT the drifting balance.md), snapshots them, computes deltas
  against the previous audit for continuity, flags doc-vs-code drift, and writes a timestamped
  report. Invoke it for periodic balance reviews and after any content/tuning change.
---

# 바르칸 밸런스 전수조사 (balance-audit)

밸런스 감사는 매번 다르게 보면 쓸모가 없다. **같은 소스에서, 같은 지표를, 같은 포맷으로** 뽑아야
감사 간 비교(연속성)가 성립한다. 이 스킬은 그 일관성을 강제한다.

## 제1원칙 — 라이브 코드가 권위, balance.md는 파생물

밸런스 수치의 진짜 출처는 **BlockShip Java 상수 + 런타임 JSON**이다. `balance.md`(636줄)는 그걸
사람이 옮겨 적은 문서라 **드리프트한다**. 감사할 때 balance.md의 숫자를 "정답"으로 믿지 말 것.
balance.md는 오직 **"코드와 문서가 어긋났는가(drift)"를 잡는 대조 대상**으로만 쓴다.

각 수치가 정확히 어디 사는지는 → [references/data-sources.md](references/data-sources.md)
지표별 정상 범위·경보선·계산법 → [references/metrics.md](references/metrics.md)

## 감사 루프 — 매번 이 순서대로

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

### 3. 파생 지표 계산 (Claude가 직접)
스냅샷의 raw 상수만으로는 체감이 안 온다. metrics.md의 공식대로 아래를 계산해 스냅샷의
`derived` 섹션에 적고 리포트에 넣는다 (pull.py가 누적경험치·강화 기대시도는 이미 계산해 둠):
- **레벨 도달 시간** — 누적 경험치(스냅샷 `cumulative_xp`) ÷ 시간당 경험치(장비/버프 시나리오별). Lv.30/45/60/70/100.
- **시간당 수입** — 등급 분포 × 등급 기본가 × 시간당 낚시 횟수. 초반/중반/종결급 3구간.
- **강화 기대 비용** — +15/+20 도달 기대 시도(스냅샷 `enhance_expected_attempts`) × 단계별 COST/PEARL.
- **수입/소모 균형** — 주요 소모처(강화·상점·업그레이드) 대비 시간당 수입으로 "몇 시간 벌어야 하나".

### 4. 이슈 판정 (metrics.md 경보선 대조)
각 축을 metrics.md의 정상 범위와 대조해 이슈를 등급화한다:
- 🔴 **치명** — 경제 붕괴(인플레·머니싱크 부재), 성장 벽이 이탈 유발, 확률 버그
- 🟡 **주의** — 정상 범위 경계, 이전 감사 대비 큰 델타(±15%↑), 종결급 편중
- 🟢 **관찰** — 사소한 편차, 다음 감사에서 추이 볼 것
- ⚪ **드리프트** — 코드 값 ≠ balance.md 값. 값 자체는 정상이어도 문서를 고쳐야 함.

### 5. 리포트 작성 (고정 포맷)
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
