# 밸런스 감사 — 2026-09-04 (길드 생성 비용)

## 요약 (TL;DR)

- 종합 상태: 🟢 요청된 튜닝 반영 완료.
- 길드 생성 비용을 100,000원에서 50,000원으로 낮췄다(50% 감소).
- 실제 차감 로직과 모든 주요 안내 UI가 동일한 `GuildManager.CREATE_COST`를 참조한다.

## 델타 (직전 코드 대비)

| 항목 | 이전 | 현재 | 변화 |
|---|---:|---:|---:|
| 길드 생성 비용 | 100,000원 | 50,000원 | -50,000원 (-50%) |

`pull.py` 스냅샷 경고는 없었다. 카탈로그 검증은 부품 379종·레시피 476종·레시피 미연결 15종을 확인했다.

## A. 진입 비용 / 성장 곡선

길드 생성은 1회성 진입 비용이므로 낚시 수입/h 곡선 자체에는 영향을 주지 않는다. 신규 길드의 초기 진입 장벽과 필요한 현금 보유액만 절반으로 낮아진다.

## B. 경제 (수입/소모)

생성 시 개인 보유금에서 50,000원을 차감하는 기존 머니 싱크는 유지된다. 다만 길드 생성 1회당 소멸액은 기존 대비 50,000원 줄어든다.

## D. 구현 검증

- 권위 상수: `GuildManager.CREATE_COST = 50_000`
- 차감·텔레메트리: `GuildCommand`가 동일 상수 사용
- 안내: `GuildCommand`, `GuildCreatePrompt`, `GuildGui`, `HelpManager`가 동일 상수 사용
- 운영·분석 문서: `stats-system-plan.md`의 이벤트 설명도 50,000원 기준으로 갱신

## 드리프트 (코드 vs 문서)

기존 `/도움말`의 10,000원 하드코딩을 상수 기반 표시로 교체해 재발 시 드리프트가 생기지 않도록 했다.

## 조치 결과

1. [🟢] 코드·안내 수치 일치 — 완료
2. [🟢] Java 플러그인 `./gradlew build` — 성공
3. [🟢] 밸런스 스냅샷·델타·카탈로그·스탯 가치·코호트 검증 — 완료

## 재현 명령

```bash
cd /Users/user/development/blockship-plugin && ./gradlew build
cd "/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Skript/scripts"
python3 .agents/skills/balance-audit/scripts/pull.py --date 2026-09-04
python3 .agents/skills/balance-audit/scripts/diff.py --auto
python3 .agents/skills/balance-audit/scripts/catalog.py
```
