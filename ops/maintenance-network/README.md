# 바르칸 무중단 정기 재시작 네트워크

## 목표

공개 Java/Bedrock 연결은 재시작하지 않는 Velocity+Geyser가 계속 소유하고, 본 Paper만
내리는 동안 플레이어를 내부 공허 Paper(`waiting`)에 둔다. 클라이언트는 서버 목록으로
튕기지 않고 백엔드 전환 로딩 화면만 본다.

```text
TCP/25565 -> Velocity ---------> main Paper     127.0.0.1:25567
UDP/19132 -> Geyser-Velocity \-> waiting Paper  127.0.0.1:25568
```

`BarkanMaintenanceProxy`는 `control/request`의 `drain|resume`을 0.5초마다 읽는다.

- `drain`: 현재 main 유저와 신규 접속을 waiting으로 옮긴다.
- `resume`: main ping이 성공한 뒤 waiting 유저를 main으로 되돌린다.
- main이 예기치 않게 유저를 끊어도 Velocity의 kick event를 waiting으로 리다이렉트한다.
- `control/status.json`은 nightly 스크립트가 `mainPlayers=0`을 확인하는 ACK다.

`~/mc-network/enabled` 마커가 없으면 기존 `nightly-restart.sh`는 예전 kick 동작을 그대로
쓴다. 마커가 있으면 drain ACK 실패 시 재시작을 취소하며 kick으로 폴백하지 않는다.

## 빌드

Velocity 4.1.x API 때문에 JDK 25가 필요하다. macOS에 JDK 25가 없으면 임시 JDK를 받은 뒤:

```bash
JAVA25_ROOT=/path/to/jdk-25 ./build.sh
```

산출물:

- `proxy-plugin/build/libs/BarkanMaintenanceProxy.jar`
- `waiting-plugin/build/libs/BarkanWaitingRoom.jar`

빌드 산출물과 `BarkanShipGeyserExtension.jar`를 prod의 이 디렉터리에 함께 올린 뒤
`prepare-prod-layout.sh`를 실행하면 `/home/ubuntu/mc-network`의 **비활성** 레이아웃만
만든다. 이 단계는 main 설정·서비스·포트를 건드리지 않는다.

BlockShip 본체도 함께 빌드해야 한다. `BedrockShipMarkerStore`가 systemd 환경변수
`BLOCKSHIP_SHIP_MARKER_DIR=/home/ubuntu/mc-network/shared/ship-entities` 경로에 UUID 표식을
원자적으로 써서, 프록시 JVM의 Geyser가 기존 선박 custom entity를 계속 선택한다.

## 최초 cutover 전 필수 조건

1. `/home/ubuntu/mc-network/velocity`와 `waiting` 레이아웃 및 두 systemd unit 준비.
2. Velocity `forwarding.secret` 생성. 비밀값을 git/로그/Discord에 넣지 않는다.
3. main과 waiting의 `paper-global.yml`에 같은 secret으로 Velocity modern forwarding 활성화.
4. main/waiting `online-mode=false`, `server-ip=127.0.0.1`; Velocity만 `online-mode=true`.
5. main은 25567, waiting은 25568, Velocity만 public 25565를 소유.
6. Geyser는 `Geyser-Velocity`로 이동. main에는 Floodgate API/폼 때문에
   `floodgate-spigot`을 유지하고 proxy Floodgate의 `send-floodgate-data: true`와 같은
   `key.pem`을 사용.
7. `BarkanShipGeyserExtension.jar`는 Geyser-Velocity의 `extensions/`로 이동.
8. 기존 `mcserver.service.d/maintenance-gate.conf`는 제거. 남겨두면 main stop 시 iptables가
   public 25565를 옛 점검 responder로 가로채 Velocity 신규 접속을 망친다.
9. `nightly-restart.sh`, `restart-warning.sh`, 새 BlockShip jar를 staging에 둔다.
10. `preflight-prod.sh` 통과 후에만 한 번의 계획된 cutover를 수행한다.

백엔드 설정은 기존 값을 통째로 덮지 않고 필요한 키만 바꾸는 도구를 사용한다. 기본은
읽기 전용 점검이고 `--apply`일 때만 타임스탬프 백업을 만든 뒤 쓴다.

```bash
./configure-backend.py --root /home/ubuntu/mcserver --port 25567 \
  --secret-file /home/ubuntu/mc-network/velocity/forwarding.secret
./configure-backend.py --root /home/ubuntu/mc-network/waiting --port 25568 \
  --secret-file /home/ubuntu/mc-network/velocity/forwarding.secret
```

최초 cutover에는 Paper가 public 25565를 내려놓고 backend 25567로 다시 떠야 하므로 기존
접속이 한 번 끊긴다. 이후 `~/mc-network/enabled`를 마지막에 만들면 정기 main 재시작은
대기실 경로를 쓴다.

## Geyser 자산 업데이트 주의

Geyser 팩·custom mapping·extension은 가동 중 파일을 덮지 않는다. 기존 nightly의
`Geyser-Spigot` 스테이징 적용은 proxy cutover 전에 별도 무접속 프록시 유지보수 경로로
옮겨야 한다. main Paper 재시작과 Velocity/Geyser 재시작은 서로 다른 작업이다. 평상시
main-only 재시작은 Java와 Bedrock 모두 연결을 유지하지만 Velocity 자체를 재시작하면
연결이 끊긴다.
