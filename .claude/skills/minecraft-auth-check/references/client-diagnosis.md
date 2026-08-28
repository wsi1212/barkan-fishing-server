# 클라이언트 / 네트워크 진단

`check_auth.sh`가 `UP`인데도 유저가 못 들어가거나, `NETFAIL`이 나올 때 여기를 따른다.
핵심 질문: "엔드포인트는 사는데 왜 이 PC/이 런처만 안 되나?"

## A. 클라이언트 런처 로그에서 실패 지점 찾기 (가장 결정적)

로그인 플로우의 어느 단계에서 깨지는지는 런처 로그가 정확히 말해준다.

**공식 런처 로그 경로:**
- macOS: `~/Library/Application Support/minecraft/launcher_log.txt`
- Windows: `%APPDATA%\.minecraft\launcher_log.txt`
- Linux: `~/.minecraft/launcher_log.txt`

**패더클(Feather) / 서드파티 런처:**
- macOS: `~/Library/Application Support/minecraft/feather/logs/latest.log`, `.../feather/java_error.log`
- 서드파티는 대개 `.minecraft` 하위 또는 각 런처 데이터 폴더에 로그를 둔다.

**찾을 것** — `loginWithXbox`의 응답 코드:
```bash
grep -nE "loginWithXbox|launcher/login|Response code: 5|Error refreshing token" \
  "$HOME/Library/Application Support/minecraft/launcher_log.txt" | tail -20
```
- `loginWithXbox failed - response code: 503` 이 보이면 → **Mojang 서버측 장애**다.
  (`X-Azure-Ref` / `x-minecraft-request-id: gateway-...` 헤더가 같이 찍힘 = Azure 게이트웨이가 백엔드 죽음)
  이건 클라이언트로 못 고친다. 1단계 `check_auth.sh`로 재확인하고 복구를 기다린다.
- Xbox 단계까지 통과하고 이 마지막 단계만 503이면, 계정·비번·네트워크는 다 정상이라는 뜻이다.

## B. 로컬 네트워크/환경 점검 (NETFAIL일 때)

`check_auth.sh`가 `NETFAIL`(000)이면 이 PC에서 엔드포인트로 못 나가는 것이다. 순서대로:

```bash
# 1) 시스템 시계 — 틀어지면 TLS 인증서 검증 실패 → 똑같이 로그인 실패로 보임
date

# 2) 프록시/VPN 환경변수
env | grep -iE "proxy" || echo "(프록시 없음)"

# 3) 인증 백엔드 + Xbox Live 단계까지 연결 확인 (403/404/401 = 연결 성공, 000/timeout = 실패)
for u in \
  https://api.minecraftservices.com/ \
  https://sessionserver.mojang.com/ \
  https://user.auth.xboxlive.com/ \
  https://xsts.auth.xboxlive.com/ \
  https://login.live.com/ ; do
  curl -s -o /dev/null --connect-timeout 8 --max-time 12 \
    -w "%{http_code}  SSLverify=%{ssl_verify_result}  $u"$'\n' "$u"
done

# 4) DNS 해석 (막히는 흔한 도메인)
#   macOS: dscacheutil -q host -a name xsts.auth.xboxlive.com
#   기타 : getent hosts xsts.auth.xboxlive.com  또는  host / dig
```
- `SSLverify`가 0이 아니면 → 시계 오류/중간자(방화벽·필터) 의심.
- Xbox Live 도메인(`*.auth.xboxlive.com`)만 000이고 나머지는 되면 → ISP/방화벽이 그 도메인만 막는 경우.
- VPN을 켰다면 꺼보고 재시도.

## C. UP인데도 로그인이 안 될 때 = 클라이언트 토큰 캐시 문제

엔드포인트가 `UP`이고 네트워크도 정상인데 런처만 "오프라인 플레이"로 남아있다면,
런처가 부팅 시점에 잠깐 놓친 캐시 상태다. 순서대로 시도(비파괴적):
1. 런처의 "다시 시도" 버튼
2. 런처 완전 종료(⌘Q / 작업관리자) 후 재실행 — 토큰 재갱신
3. 계정 로그아웃 → Microsoft 재로그인

이 조치들은 로컬 캐시만 건드리므로 안전하다. 이래도 안 되면 대개 A(=서버측 503)가 진짜 원인이다.
