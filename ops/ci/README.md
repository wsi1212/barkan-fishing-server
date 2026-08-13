# 배포 전 부팅 스모크 게이트

맥 dev 서버가 워크플로에서 빠진 뒤, **jar가 라이브로 가기 전에 사람 없이 걸러내는 층.**

## 왜 필요한가

2026-08-03 prod 사고 — jar 교체 후 재시작을 미뤘더니 `NoClassDefFoundError:
WeatherManager$WeatherChoice`로 `/칭호`·계단앉기가 전방위로 죽었고 3시간 뒤에야
인지했다. **서버를 한 번 띄워보기만 했어도 배포 전에 걸렸다.**

`watchdog.sh`도 `jar-guard.sh`도 "재시작"까지만 한다. 깨진 jar를 되돌리는 건
사람 손이다. 그 손이 없는 기간(무인운영)에 대비해 **적용 전에** 거른다.

CLAUDE.md가 "잔여 리스크(인지함, 미자동화)"로 적어둔 항목 —
*"기능적 플러그인 고장(서버는 살아있는데 게임 로직만 깨짐, RCON 헬스체크로 감지 불가)"* —
의 상당 부분이 여기서 메워진다.

## 무엇을 하나

버려질 슈퍼플랫 월드에 Paper 1.21.10을 띄우고 새 jar를 꽂아 실제로 부팅시킨다.
마크 클라이언트도 사람도 필요 없다.

판정:
- `Done (` 에 도달했는가 (안 뜨면 실패)
- 치명 예외가 없는가 — CNFE / ClassNotFound / NoSuchMethod / UnsupportedClassVersion /
  `Error occurred while enabling` 등 **배포를 되돌려야 하는 종류만** 엄선
- 지정한 플러그인이 **enable까지 갔는가**
- (선택) rcon 명령이 응답하는가 — 플러그인 코드 경로를 실제로 때린다

## 실측 검증 (2026-08-13, 이 컨테이너)

| 케이스 | 결과 |
|---|---|
| Paper 1.21.10 build 130 부팅 | ✅ 35~37초, 정상 종료 |
| 정상 플러그인 + rcon `list` | ✅ 종료코드 0, enable 확인, rcon 응답 |
| **Helper 클래스를 뺀 jar (CNFE 재현)** | ✅ **종료코드 1**, 스택트레이스 + 4건 진단 |

즉 2026-08-03 사고 유형을 그대로 잡는다.

## 사용법

```bash
ops/ci/paper-smoke-test.sh \
  --plugin build/libs/BlockShip-1.0.0-SNAPSHOT.jar \
  --expect-plugin BlockShip \
  --rcon-command "데이터리로드"
```

`--help`로 전체 옵션. 종료코드 0=통과 / 1=실패 / 2=사용법 오류.

## 파일

| 파일 | 놓을 곳 |
|---|---|
| `paper-smoke-test.sh` | **blockship-plugin repo의 `ci/`** 로 복사 |
| `blockship-smoke.yml` | **blockship-plugin repo의 `.github/workflows/`** 로 복사 |

★fish repo의 `.github/workflows/`에 넣지 말 것 — 여긴 gradle 프로젝트가 아니라 빌드에서 죽는다.

## 승격 게이트

```
push        → 빌드 + 스모크까지만 (staging 근처에도 안 감)
수동 실행   → promote=true 일 때만 Release 발행
오라클 cron → Release를 당겨 ~/mcserver/staging/ 에 투입
06:00       → 데일리 유지보수가 적용 + 구 jar 백업
```

`push`마다 staging에 떨어지게 만들면 **오타 하나가 다음날 06:00에 라이브로 간다.**
그래서 승격을 사람이 누르는 단계로 끊어놨다. 그 사이에 폰 마크 클라로 확인하는 게
빠진 dev 서버의 자리를 메운다.

## 의존 플러그인 — 필요 없음 (2026-08-13 실측 확정)

```
name: BlockShip · main: com.blockship.BlockShipPlugin · api-version: '1.21'
softdepend: [ BetterHud, BetterModel, ProtocolLib, Citizens, VotifierPlus ]
```

**`depend` 가 하나도 없다.** 의존 jar 없이 로드·enable 되므로 CI 에 아무것도 안 넣어도
된다. Citizens 미러 문제도 사라졌다.

그리고 이 구성이 오히려 **더 민감하다** — softdepend 를 가드 없이 쓰는 코드가 있으면
스모크가 잡는다. 가장 의심스러운 곳은 `diagnostics/PacketBlackbox`(ProtocolLib) 다.
터지면 오탐이 아니라 실제 버그다: prod 에서 ProtocolLib 이 로드 실패하면 같은 방식으로
깨진다.

## 남은 확인 항목

- [ ] **prod 실제 MC 버전** — CLAUDE.md 는 1.21.10 인데 `plugins/` 에 1.21.11 용
      jar(`AxiomPaperPlugin-5.0.4-for-MC1.21.11`, `BarkanChess-1.21.11`)가 있다.
      스모크가 엉뚱한 버전을 테스트하면 의미가 없다. 워크플로의 `MC_VERSION` 을 맞출 것
- [ ] 빌드 타겟(1.21.4)과 구동(1.21.10)의 버전 드리프트 — `NoSuchMethodError`를
      치명 패턴에 넣어둔 이유. 스모크가 이걸 잡으면 드리프트가 실제로 터진 것

## 알아둘 것

- **Paper API v2(`api.papermc.io`)는 sunset됨.** `{"ok":false,"error":"sunset"}`만 돌려준다.
  이 스크립트는 v3(`fill.papermc.io`)를 쓴다. 인터넷의 낡은 예제를 복붙하면 조용히 깨진다.
- 헤드리스 CI에서 정상적으로 뜨는 경고(터미널 기능 없음, root 실행, ProtocolLib
  버전 경고)는 무해 목록으로 걸러낸다. 추가하려면 `--ignore`.
- Paper jar 52MB는 캐시된다. 첫 부팅은 Mojang 서버 jar·라이브러리를 받느라 조금 더 걸린다.
