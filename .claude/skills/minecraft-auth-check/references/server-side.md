# 마크 서버 운영자용 점검

내가 `online-mode=true` 서버를 운영 중이고 "유저들이 접속을 못 한다"는 신고를 받았을 때.
핵심: **서버가 결백한지 먼저 증명**하고, 범인이 Mojang이면 기다리는 것 외엔 할 게 없다.

## 서버측 결백 확인 (SSH로 서버에 접속해서)

프로젝트에 서버 접속 정보(IP/SSH 키/경로)가 있으면 CLAUDE.md 등에서 가져다 쓴다.

```bash
# 1) online-mode 설정 (true여야 정상 인증. 아래 경고 참고)
grep -iE "online-mode|enforce-secure" ~/mcserver/server.properties

# 2) 서버→Mojang 세션서버 연결 (200이면 서버는 Mojang과 정상 통신)
curl -s -o /dev/null -w "sessionserver: HTTP %{http_code}\n" \
  https://sessionserver.mojang.com/session/minecraft/profile/853c80ef3c3749fdaa49938b674adae6

# 3) 실제 인증 성공 흔적 — 이 줄은 online-mode=true에서만 찍힌다
grep -iE "UUID of player|authenticat|OFFLINE/INSECURE" ~/mcserver/logs/latest.log | tail -20
```
- `UUID of player X is ...` 줄이 있으면 = 서버가 Mojang 인증을 정상 수행 중이라는 강력한 증거.
- `RUNNING IN OFFLINE/INSECURE MODE` 경고가 **없어야** 정상(online-mode=true).

이 셋이 정상이면 서버는 결백하다. 그다음 1단계 `check_auth.sh`로 Mojang 상태를 본다.

## 장애 동안의 영향 (유저에게 안내할 내용)

`check_auth.sh`가 `DOWN`이면:
- 서버는 멀쩡히 돌지만, online-mode=true라 **신규 로그인이 전부 막힌다.**
- 이미 접속 중인 플레이어는 유지되지만, 끊기면 재접속 불가.
- 모든 유저가 같은 증상 → "서버 죽었냐" 문의엔 "Mojang 인증 장애, 서버는 정상"이라고 안내.

## 절대 하면 안 되는 임시방편: online-mode=false

장애를 우회하려고 `online-mode=false`로 서버를 여는 것은 **금지**. 이유:
- 오프라인 UUID는 온라인 UUID와 **다르다** → 플레이어 데이터(레벨/돈/장비 등 UUID 키로 저장된 모든 것)가
  통째로 딴 사람 것처럼 취급되어 **사실상 초기화**된다. 장애 복구 후 되돌려도 그 사이 데이터는 꼬인다.
- 인증이 없어져 **아무나 아무 닉네임으로 접속** 가능 → 관리자 사칭·계정 도용 위험.

득보다 실이 압도적으로 크다. 장애는 그냥 기다리는 게 정답이다(3단계 모니터로 복구 감지).
