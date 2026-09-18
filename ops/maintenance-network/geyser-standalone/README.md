# Geyser 분리 (Velocity 플러그인 → standalone 프로세스)

## 왜

지금 Geyser 는 **Velocity 플러그인**이다. 그래서 Geyser 를 만지려면 Java 유저의 접속점인
Velocity 를 내려야 한다 — 확장(`extensions/*.jar`)·코어 jar 교체가 **전원 끊김**이 된다.
JVM 안에서 이걸 피할 방법은 없다(실측):

- `geyser reload` = `disconnectAll` + `reloadGeyser` — **config·팩·매핑만** 다시 읽는다.
- `geyser extensions` 는 **목록 출력 전용**. load/unload/reload 명령도 API 도 없고,
  확장마다 `GeyserExtensionClassLoader` 를 부트스트랩 때 한 번 물고 끝까지 유지한다.
- Velocity 는 설계상 플러그인 재로드가 없다. 그래서 코어 교체가
  `Geyser-Velocity.jar.next` + Velocity 전면 재기동 경로로 따로 빠져 있다.

**핵심**: `geyser reload` 는 지금도 베드락을 전부 끊는다. 즉 베드락 입장에선 팩 교체든
확장 교체든 «어차피 한 번 끊긴다». 분리하면 그 비용이 **베드락에만** 갇히고 Java 는 영원히
안 끊긴다.

|              | 지금(플러그인)            | standalone            |
|--------------|---------------------------|-----------------------|
| 팩·매핑      | geyser reload → 베드락만  | 동일                  |
| 확장 jar     | **Velocity 재기동 → 전원**| Geyser 재기동 → 베드락만 |
| 코어 jar     | **Velocity 재기동 → 전원**| Geyser 재기동 → 베드락만 |

## 구조

```
지금:  Bedrock ─UDP19132→ [Velocity JVM: Geyser 플러그인 → localSession] → main(25567)
이후:  Bedrock ─UDP19132→ [Geyser standalone] ─TCP127.0.0.1:25565→ [Velocity] → main(25567)
```

Velocity 는 `player-info-forwarding-mode = modern`, floodgate-velocity 가 베드락 핸드셰이크를
해독한다. **Geyser standalone 과 floodgate-velocity 가 같은 `key.pem` 을 써야 한다** —
현재 velocity/paper 양쪽 키가 이미 동일하다(sha256 `91bf0bd9f69d829c`).

## 전제·실측값 (2026-09-19)

- Velocity `bind = 0.0.0.0:25565`, servers `main=127.0.0.1:25567` `waiting=127.0.0.1:25568`
- Geyser 플러그인 `bedrock.address 0.0.0.0` `port 19132`, `java.auth-type floodgate`
- UDP 19132 는 Velocity JVM 이 들고 있다 → 분리 시 소유자가 Geyser 프로세스로 바뀐다
- 확장 `BarkanShipGeyserExtension`(id `barkanships`, api 2.11.0)은 **이미 extensions/ 에 있다**.
  분리해도 그대로 따라간다.
- ★`BarkanMaintenanceProxy` 의 `ProxyGeyserShipBridge` 가 **같은 일을 중복**으로 하고 있다.
  Geyser 가 JVM 에서 빠지면 GeyserApi 가 없어 이 브릿지는 죽는다 — 분리와 함께 제거해야 한다
  (기능은 확장이 이미 담당).

## 끊김은 «한 번»이면 끝난다

Velocity 재기동은 어차피 한 번 필요하다 — 새 `BarkanMaintenanceProxy.jar`(무중단 리로드
프로토콜)을 로드해야 하기 때문. **그 한 번에 Geyser 플러그인 제거까지 같이 태운다.**
그 뒤로는 팩·매핑·확장·코어 전부 베드락만 끊긴다.

## 절차

```bash
# 1) 준비 — 라이브를 건드리지 않고 병렬 레이아웃만 만든다 (몇 번을 돌려도 안전)
ops/maintenance-network/geyser-standalone/prepare.sh

# 2) 컷오버 — Velocity 1회 재기동 (전원 ~10초 끊김). 이 순간이 유일한 전면 끊김이다.
ops/maintenance-network/geyser-standalone/cutover.sh

# 3) 되돌리기 — 문제가 있으면
ops/maintenance-network/geyser-standalone/rollback.sh
```

## 위험 목록 (컷오버 때 이것만 보면 된다)

1. **베드락이 아예 못 들어온다** — floodgate 키 불일치 또는 `force-key-authentication`.
   판정: Geyser 로그에 `Floodgate` 오류 / Velocity 가 `force-key-authentication` 으로 킥.
   즉시 `rollback.sh`.
2. **Java 가 못 들어온다** — 컷오버는 Java 경로를 바꾸지 않으므로 나면 안 된다.
   나면 Velocity 기동 실패이므로 `rollback.sh`.
3. **UDP 19132 이중 바인딩** — 플러그인 제거가 안 된 채 standalone 을 켜면 포트 충돌.
   `cutover.sh` 가 순서를 강제한다(Velocity 정지 → jar 제거 → Velocity 기동 → Geyser 기동).
4. MOTD·플레이어 수가 Geyser 자체 값으로 보인다 → `passthrough-motd: true` 유지로 해결.
