---
name: minecraft-auth-check
description: >-
  마인크래프트/Mojang/Microsoft 로그인·인증 서버가 지금 살아있는지 실시간으로 판정하고 진단한다.
  "오프라인 플레이", "auth.failure", "인증 서버에 연결할 수 없음", "보유 게임 목록을 확인하지 못했습니다",
  로그인/재로그인 실패, 멀티플레이 서버 접속 불가, "Failed to login", "authentication servers are down"
  같은 증상이 보이면 반드시 이 스킬을 쓸 것. 사용자가 "인증 서버 또 죽었냐", "왜 로그인이 안 되냐",
  "마크가 자꾸 오프라인으로 뜬다"처럼 스킬 이름을 대지 않고 물어도 트리거해야 한다. Mojang 엔드포인트
  (launcher/login·login_with_xbox·sessionserver)의 실시간 HTTP 상태로 503 서버측 장애인지 vs
  클라이언트/네트워크 문제인지 즉시 구분하고, 복구 모니터링과 마크 서버 운영자용 online-mode 점검까지 한다.
---

# Minecraft 인증 상태 체크 & 진단

## 왜 이게 필요한가

마인크래프트 로그인은 여러 단계를 거친다:
`Microsoft OAuth → Xbox Live 인증 → XSTS → Minecraft 서비스 로그인(api.minecraftservices.com)`.
이 중 **마지막 Minecraft 서비스 단계**가 자주 말썽이다. Mojang 백엔드(Azure)가 5xx를 뱉으면
공식 런처는 "오프라인 플레이"로 폴백하고, 서드파티 런처(패더클 등)는 `auth.failure`를 띄운다.

증상만 보면 "내 계정이 풀렸나", "내 서버가 죽었나", "인터넷이 문제인가" 싶지만 —
대부분은 **Mojang 서버측 일시 장애**다. 이 스킬의 목적은 추측 대신 **실측**으로
"지금 죽은 게 누구인지"를 1분 안에 가리는 것.

함정 하나: minecraftstatus.com 같은 상태 페이지는 단순 핑만 봐서 "operational"로 떠도
실제 토큰 교환 엔드포인트는 503일 수 있다. 상태 페이지를 믿지 말고 **직접 엔드포인트를 찔러라.**

## 1단계 — 즉시 판정 (항상 여기서 시작)

`scripts/check_auth.sh`가 Mojang 핵심 인증 엔드포인트 3개를 실시간으로 찔러 판정한다.

```bash
bash scripts/check_auth.sh          # 사람이 읽는 표
bash scripts/check_auth.sh --json   # 기계 판독용 한 줄 JSON
```

VERDICT는 넷 중 하나이며, 각각 대응이 다르다:

| VERDICT | 의미 | 대응 |
|---------|------|------|
| `UP` | 인증 정상 (로그인 엔드포인트가 400/401 등 정상 응답) | 서비스는 멀쩡. 그래도 유저가 못 들어가면 → 2단계 |
| `DOWN` | **Mojang 서버측 장애** (로그인 엔드포인트가 5xx) | 클라·서버 손댈 것 없음. 복구 대기 + 3단계 모니터 제안 |
| `NETFAIL` | 엔드포인트 연결 자체 실패 (000) | 로컬 문제 → 2단계의 네트워크 진단 |
| `DEGRADED` | 일부만 이상 (플래핑 가능) | 잠시 후 재확인. 반복되면 DOWN 취급 |

HTTP 코드 읽는 법: 로그인 엔드포인트에 **빈 바디로 POST**하므로 `400`/`401`이 오히려 "정상"이다
(= 엔드포인트가 살아서 요청을 처리 중). `503`은 서버측 장애, `000`은 연결 실패.

## 2단계 — 클라이언트/네트워크 진단 (UP인데 안 되거나, NETFAIL일 때)

`references/client-diagnosis.md`를 읽고 따라간다. 다루는 것:
- 클라이언트 런처 로그에서 `loginWithXbox ... 503` 확인 (공식 런처 / 패더클 경로, macOS·Windows·Linux)
- 로컬 시계·프록시·DNS·Xbox Live 엔드포인트 연결 점검
- UP인데 못 들어갈 때: 토큰 캐시 문제 → 런처 재시작/재로그인

## 3단계 — 복구 모니터링 (DOWN일 때, 원하면)

장애가 풀리는 순간을 잡으려면 백그라운드 모니터를 돌린다. 단발 회복(플래핑)에
속지 않게 **연속 정상 확인** 후에만 알린다.

```bash
bash scripts/check_auth.sh --monitor          # 기본: 2분 간격, 연속 3회 UP이면 알림, 상한 6h
bash scripts/check_auth.sh --monitor --interval 120 --need 3 --max 21600
```

Claude Code라면 이걸 `run_in_background: true`로 띄운다 — 복구되는 순간 스크립트가 종료하며
자동으로 알림이 온다. 단발 감지(`--need 1`)는 플래핑에 속으니, 기본값(연속 3회)을 유지할 것.

## 4단계 — 마크 서버 운영자라면

내가 서버(online-mode=true)를 운영 중이고 "유저들이 못 들어온다"는 상황이면,
`references/server-side.md`를 읽는다. 서버측이 결백한지 확인하는 법과, 장애 동안의 영향,
그리고 **절대 하면 안 되는 임시방편**(online-mode=false로 여는 것)을 다룬다.

## 요약 한 줄

증상 → `check_auth.sh` → `DOWN`이면 "Mojang 장애, 기다리세요"(+모니터), `UP`이면 클라/네트워크로,
`NETFAIL`이면 로컬 네트워크로. 상태 페이지 말고 엔드포인트를 직접 믿어라.
