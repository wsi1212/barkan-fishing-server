# 2층 — 오라클 dev 인스턴스

맥이 사라진 뒤의 검증 환경. **prod와 같은 박스에 두 번째 Paper를 띄우되, prod를
절대 위험에 빠뜨리지 않는 것**이 설계의 1순위다.

## 왜 맥 dev보다 나은가

맥 dev가 망가진 원인은 **드리프트**였다 — Citizens NPC가 12명 적어서 튜토 검증이
불가했고(`codex-handoff.md` §0), 그래서 작업 대상이 prod가 되어버렸다.

여기 dev는 **매번 prod에서 부어 만든다.** 드리프트할 시간을 주지 않는다.
`plugins/Citizens/saves.yml`(NPC 157명) · `plugins/BlockShip/`(퀘스트·어종·지역 JSON +
playerdata)이 그대로 넘어온다.

## 파일

| 스크립트 | 하는 일 |
|---|---|
| `mcdev-lib.sh` | 공통 설정·헬퍼 (source 전용) |
| `mcdev-sync.sh` | prod → dev 반영 (시딩/갱신) |
| `mcdev-up.sh` | dev 켜기 + **자동 종료 예약** |
| `mcdev-down.sh` | 즉시 내리기 |
| `mcdev-reaper.sh` | cron 안전망 — 시한 초과·고아 dev 강제 종료 |

전부 `~/mcserver/scripts/` 에 놓는다(스크립트는 한곳에). **데이터는 `~/mcdev/` 에 분리.**

## 설치 (오라클에서 한 번)

```bash
# 스크립트 배치
cp mcdev-*.sh ~/mcserver/scripts/ && chmod +x ~/mcserver/scripts/mcdev-*.sh

# ★화이트리스트 본인 계정 확인 (mcdev-lib.sh 의 MCDEV_WHITELIST, 기본값 wsi1212)

# 안전망 cron
( crontab -l 2>/dev/null; \
  echo '*/5 * * * * flock -n ~/mcdev/.reaper.lock ~/mcserver/scripts/mcdev-reaper.sh' ) | crontab -

# 포트 개방 (폰에서 접속하려면 둘 다 필요)
sudo iptables -I INPUT -p tcp --dport 25566 -j ACCEPT
#  + OCI 콘솔 → Security List → 25566/tcp 인그레스 추가
```

## 쓰는 법

```bash
~/mcserver/scripts/mcdev-sync.sh                      # prod 반영 (메인 월드 3종)
~/mcserver/scripts/mcdev-up.sh --minutes 60           # 켜기, 60분 뒤 자동 종료
#  → 폰 마크 클라로 <서버IP>:25566 접속해서 검증
~/mcserver/scripts/mcdev-down.sh                      # 끝났으면 즉시 내리기
```

**핵심 용도 — 후보 jar 검증** (빠진 dev 테스트 자리를 메우는 단계):

```bash
~/mcserver/scripts/mcdev-up.sh --jar ~/mcserver/staging/BlockShip-*.jar
```

staging에 올라간 jar를 **06:00에 prod가 적용하기 전에** 실제로 띄워보고 들어가 본다.

자주 쓰는 변형:
- `mcdev-sync.sh --no-worlds` — 플러그인/JSON만 갱신 (빠름, 퀘스트 데이터 작업용)
- `mcdev-sync.sh --worlds all` — 섬·길드섬·광산까지 (디스크 주의)
- `mcdev-up.sh --minutes 90` — **이미 켜져 있으면 시한만 연장**

## 자동 종료 (2중 안전망)

```
① 타이머 데몬  mcdev-up.sh 가 setsid 로 띄운다.
                T-10 / T-5 / T-1 분에 인게임 경고 → save-all flush → stop
② 리퍼 cron    */5. 타이머가 죽어도 시한을 강제한다.
                시한 파일 없이 도는 고아 dev 도 15분 유예 후 종료
```

①만 있으면 프로세스가 죽는 순간 dev가 영원히 돈다. **군 복무 중 잊힌 dev가 prod와
자원 경쟁을 몇 주 하는 게 최악의 시나리오**라 ②를 독립적으로 둔다.

## prod 보호 장치 — 이게 이 설계의 핵심

| 위험 | 막는 방법 |
|---|---|
| **OOM으로 prod가 죽음** | 시작 시 `MemAvailable < 3500MB` 면 **시작 거부** |
| **dev가 디스크를 밀어 백업이 지워짐** | `disk-guard.sh`는 92%에서 백업부터 지운다 → sync는 80%, up은 88%에서 거부 |
| **jar-guard가 dev jar를 prod 변경으로 오인** | dev를 `~/mcserver/` **밖**(`~/mcdev/`)에 둠 |
| **watchdog의 rcon 헬스체크와 충돌** | 포트 분리 (게임 25566 / rcon 25576) |
| **백업 tar가 dev 월드를 삼킴** | 백업 glob(`~/mcserver/backups/local*`)과 경로가 겹치지 않음 |
| **dev가 죽어도 되살아남** | **systemd 유닛을 만들지 않는다.** `Restart=always` dev는 재앙 |
| prod가 죽은 상태에서 dev를 켬 | `prod_running()` 확인 후 거부 (prod가 먼저다) |
| 남이 dev에 들어옴 | `white-list=true` + 부팅 후 rcon으로 본인만 등록 |

## ★`online-mode=true` 를 반드시 유지할 것

`mcdev-sync.sh`가 prod `server.properties`를 베이스로 쓰고 필요한 키만 덮는 이유다.

**offline-mode면 UUID가 달라져서 prod playerdata가 안 붙는다.** 레벨·돈·장비·강화가
전부 초기화된 상태로 "검증"하게 되고, 그 검증은 거짓말이다. 리소스팩 URL·SHA1도
prod 것을 물려받아야 텍스처 검증이 의미가 있다.

## 실측 검증 (2026-08-13)

컨테이너에서 포트·경로만 바꿔 실제로 돌려봤다:

| 항목 | 결과 |
|---|---|
| 기동 | ✅ 18~25초, tmux 세션 정상 |
| PID 파일 | ✅ `java.pid` → 실제 java, `timer.pid` → 진짜 데몬 |
| 시한 등록 | ✅ 정확, 인게임 경고 `say` 전송 |
| **자동 종료** | ✅ `save-all flush` → `stop` → 정상 저장 |
| **수동 종료** | ✅ 7초, 강제종료 0회 |
| **리퍼(안전망)** | ✅ 타이머를 kill -9 하고 시한을 과거로 돌린 상태에서 발동, 정상 종료·정리·멱등 |
| 잔여물 정리 | ✅ deadline·timer.pid·java.pid·tmux 전부 |
| 포트 미개방 감지 | ✅ iptables 규칙 없음을 잡아 정확한 명령 안내 |

### 돌려보니 나온 버그 4개

써놓고 안 돌렸으면 전부 살아남았을 것들이다:

1. **`pgrep -f "mcdev-paper.jar"` 가 그 문자열을 명령줄에 언급한 아무 프로세스나 잡았다**
   — 로그를 tail 하는 셸, ssh 명령, 진단하려고 그 이름을 타이핑한 셸까지. JVM이
   정상 종료된 뒤에도 true가 나와 "stop이 안 먹었다"로 오판(수동 종료가 7초 대신
   2분 6초 + 불필요한 강제종료). **더 위험한 건 `pkill -f` 쪽 — 그 무관한 프로세스들을
   실제로 죽인다.** prod 박스에서 절대 있으면 안 되는 코드였다.
   → PID 파일 + `/proc/<pid>/comm == java` 검증으로 교체, `pkill` 전면 제거.
2. **`setsid` 의 `$!` 가 곧 사라지는 중간 프로세스를 가리켰다** — 그 PID를 kill 해도
   타이머는 안 죽는다. → 데몬이 자기 `$$` 를 직접 기록.
3. **타이머 데몬의 stdout을 로그로 리다이렉트해서 모든 줄이 두 번 찍혔다**
   (`log()` 가 이미 파일에 쓴다). → stdout은 버리고 stderr만 남김.
4. **시한이 임계값보다 짧으면 경고가 거짓말을 했다** — `--minutes 2` 에서
   "5분 후 종료" → "10분 후 종료" 순으로 나왔다. → 시작 시점에 이미 지난 임계값은
   발송 대상에서 제외.

`mcdev-sync.sh`의 rsync 구간은 컨테이너에 rsync가 없어 미검증 — 오라클에는 있다
(`mc-sync.sh`가 이미 씀). **오라클에서 첫 실행은 `--dry-run`으로 확인할 것.**

## 남은 확인 항목

- [ ] **메모리 실측** — prod 힙 16G에 dev 2G를 얹을 여유가 실제로 있나.
      `free -m` 으로 `MemAvailable` 확인. 3500MB 미만이면 `start.sh`의 힙을
      12G로 되돌리는 게 맞다 (2026-07-07에 12G→16G 올린 것의 원복).
- [ ] `MCDEV_WHITELIST` 가 본인 마크 계정인지 (기본값 `wsi1212`)
- [ ] prod `server.properties`의 `level-name` 이 `world` 인지 — 다르면
      `mcdev-sync.sh` 의 `WORLDS` 기본값을 맞출 것
- [ ] OCI Security List 25566 인그레스 (박스 안에서는 확인 불가)
