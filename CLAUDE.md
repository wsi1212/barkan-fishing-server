# Fish - 바르칸 열도 낚시 서버

## 프로젝트 개요
마크 서버용 종합 낚시 게임. Skript 2.13.2 + SkBee 3.15.0 + BlockShip(Java 배 플러그인).
상세 설계: [design.md](design.md) | 수치 밸런스: [balance.md](balance.md) | 스토리: [story.md](story.md)

## 기술 스택
- Skript 2.13.2 + SkBee + SkQuery + skRayFall + MarSkRebirth(지역관리)
- Paper 1.21, Java 21, BlockShip Java 플러그인 (배 시스템)

## 핵심 시스템 요약

| 시스템 | 파일 | 핵심 |
|--------|------|------|
| **낚시** | `낚시.sk` | PRD 등급 결정, 미니게임, 크리티컬(캡8), 등급업(캡30%), 더블/트리플(독립) |
| **레벨** | `낚시레벨.sk` | 만렙100, 구간별 벽(1.04/1.08/1.05/1.09/1.06/1.10), 로드맵 GUI |
| **장비** | `부품데이터.sk` | 131종, 포맷:`이름\|등급\|가격\|내구\|스탯\|레벨제한\|출처` |
| **축복/강화** | `낚싯대강화.sk` | 축복=계정귀속(`/축복`), 강화=낚싯대별(`/강화`) |
| **도핑** | `도핑.sk` | 6종 버프, `/도핑상점`, 1종만 활성 |
| **판매** | `판매.sk` | 품질배율 0.3~1.0, 신선도 감소 |
| **칭호** | `칭호.sk` | TextDisplay(addPassenger), 채팅 포맷 |
| **퀘스트** | `퀘스트.sk`+`퀘스트훅.sk` | 일일/주간/메인, 쉬운건 타이틀 표시 |
| **NPC/대화** | `NPC.sk` | NPC 우클릭 대화, 퀘스트 수락/완료 |
| **아이스박스** | `아이스박스.sk` | 물고기 보관함 (9단계, 신선도 보존) |
| **보트** | `보트.sk` | 투명 말 보트 (연료제, 9단계 업그레이드) |
| **페리** | `페리.sk` | 지역간 자동 이동 (노선, 요금, 보스바) |
| **지역** | `공간.sk` + Java RegionManager | MarSkRebirth 감지 + Java 데이터(regions.json) |
| **날씨** | Java WeatherManager | 지역별 독립 날씨, 파티클, 사운드, 시야 제한 |
| **사이드바** | `사이드바.sk` | 스코어보드 HUD (레벨, 돈, 위치, 환경, 콤보) |
| **배** | BlockShip Java | BlockDisplay+Shulker, 프리셋 3종 |

## 코드 컨벤션
- 변수명/함수명 한글 (일부 영문: `get_fish`, `gui` 등)
- 로컬: `{_변수}`, 글로벌: `{변수::키}`
- GUI 클릭: `index of clicked slot` 사용 (`clicked slot`은 Slot 타입이라 변수경로 불가)
- `continue` in nested loop 불가 → `{_skip}` boolean 플래그 패턴
- **한글 명령어 영타 별칭 필수** (OP 전용 명령어는 제외): 한글→영타 매핑: ㅂ=q ㅈ=w ㄷ=e ㄱ=r ㅅ=t ㅛ=y ㅕ=u ㅑ=i ㅐ=o ㅔ=p ㅁ=a ㄴ=s ㅇ=d ㄹ=f ㅎ=g ㅗ=h ㅓ=j ㅏ=k ㅣ=l ㅋ=z ㅌ=x ㅊ=c ㅍ=v ㅠ=b ㅜ=n ㅡ=m
- **탭 자동완성 필수** (OP 전용 명령어는 제외): 인자가 있는 모든 명령어에 `on tab complete of "/명령어":` 블록을 반드시 추가할 것
  - 인자가 **플레이어 닉네임**이면: `set tab completions for position N to names of all players`
  - 인자가 **숫자 (금액/수량/레벨 등)**이면: 자동완성 목록 **넣지 않음**. 대신 `"<금액>"`, `"<수량>"` 같은 도움말 텍스트만 표시 (예: `set tab completions for position 2 to "<금액>"`)
  - 인자가 **고정 선택지** (등급, 타입 등)이면: 가능한 값을 모두 나열
  - 자동완성 없이 명령어만 만드는 것은 금지

### 변수 키 규칙 (중요 — 반드시 준수)

**Skript config에 `use player UUIDs in variable names: true`** 설정됨. `{변수::%player%}`는 UUID를 키로 사용함.

#### 플레이어별 글로벌 변수 (`{돈::}`, `{낚시레벨::}` 등)
- **player 객체를 키로 사용** → `{돈::%player%}`, `{돈::%{_p}%}` (function 파라미터)
- **절대 이름 텍스트를 키로 쓰지 않음** → `{돈::%player's name%}` ← **금지!**
- 이유: UUID 키 `{돈::9b2e2922-...}`와 이름 키 `{돈::wsi1212}`가 분리되어 돈이 사라지는 버그 발생
- 오프라인 플레이어 돈 접근 시: `{돈::%("이름" parsed as offline player)%}` 사용

```
# 올바른 예
{돈::%player%}                          # on 이벤트에서
{돈::%{_p}%}                            # function 파라미터(player 타입)
{돈::%("wsi1212" parsed as offline player)%}  # 오프라인 플레이어

# 잘못된 예 — 절대 쓰지 말 것
{돈::%player's name%}
{돈::%{_playerName}%}  ← 텍스트 변수를 키로 직접 사용
```

#### Java 브릿지에서 Skript 변수 접근
- Java→Skript 브릿지 명령어에서 플레이어 이름을 받으면, **Skript에서 `parsed as player`로 변환 후** 변수 접근
- 예: `guildcreatecheck`에서 `set {_p} to arg-1 parsed as player` → `{돈::%{_p}%}`

#### 길드 시스템 변수 (예외)
- `{길드::%이름%}`, `{길드역할::%이름%}` — Java `guildmembersync`에서 이름 텍스트로 저장
- 이 변수들은 **이름 키 전용**으로 설계됨 (UUID 아님). 읽을 때도 `name of player`로 접근
- 예: `{길드::%name of player%}`, `{길드::%{_pn}%}` (where `{_pn} = name of player`)

### 월드 이동 규칙
- **`player.teleport()` (Java Bukkit API)로 커스텀 월드 이동 불가** — Paper에서 작동 안 함
- 반드시 `execute in minecraft:<월드이름> run tp <플레이어> <x> <y> <z>` 명령어 사용
- Skript에서: `make player execute command "execute in minecraft:%world% run tp @s %x% %y% %z%"`
- Java에서: `Bukkit.dispatchCommand(consoleSender, "execute in minecraft:world run tp player x y z")`

### 메시지 전송 필터 패턴
- 전체 메시지(broadcast) 전송 시 차단 변수 체크 필수:
  - `{차단전체채팅::%name of player%}` — 전체 채팅 차단
  - `{차단길드채팅::%name of player%}` — 길드 채팅 차단
  - `{차단홍보::%name of player%}` — 길드 홍보 차단
  - `{차단팁::%name of player%}` — 서버 팁 차단
  - `{차단낚시공지::%name of player%}` — S등급+ 낚시 공지 차단
- guild_world에 있는 플레이어에게는 날씨 알림 보내지 않음

### guild_world 규칙
- guild_world는 길드 전용 공허 월드
- 날씨 시스템 적용 안 됨 (항상 맑음)
- 날씨 알림 메시지 보내지 않음 (Java WeatherManager에서 `guild_world` 체크)
- 사이드바에 "☀ 맑음" 고정 표시
- 길드 미가입자가 guild_world에 있으면 자동 스폰 이동

## 스탯 용어 표준
모든 UI(상점/장비/스탯/도핑/강화)에서 동일 용어 사용. 상세: balance.md 6장 참조.

## 주요 명령어
- `/레벨` `/장비` `/축복` `/강화` `/칭호` `/도핑상점` `/부품상점` `/판매`
- `/도감` `/마켓` `/마켓등록 <가격>` `/수표 <금액>`
- `/콤보 [n]` `/낚시테스트 [등급]` `/카메라툴` (op)
- `/ship create/destroy/save/spawn/edit` (배)
- `/지역 생성/삭제/목록/정보/설정/바이옴/파티클/리로드` (Java, op)
- `/날씨설정 <지역|전역> <날씨|해제>` (Java, op) — 비,뇌우,태풍,안개,모래바람,눈보라,열대야,땡볕
- **중요**: 서버 최초 설정 시 `/gamerule doWeatherCycle false` 필수 (MC 자체 날씨 비활성화, 우리 WeatherManager가 제어)

## 핵심 변수 (축약)
```
{낚시레벨::%p%}, {낚시레벨현재경험치::%p%}, {낚시레벨필요경험치::%p%}
{돈::%p%}, {area::%p%}, {낚시콤보::%p%}, {낚시최대콤보::%p%}
{플레이어축복::%ID%::%p%}          — 축복 레벨 (계정)
{낚싯대강화::%rod_name%::%p%}      — 강화 레벨 (낚싯대별)
{등급피티::%p%::%grade%}           — PRD 피티 카운터
{장착칭호::%p%}, {도핑::%p%::타입}
{부품::%유형%::%이름%}              — 부품 DB
```

## 밸런스 핵심 수치
- **등급업 캡 30%**, 크리배율 캡 80%, 슈퍼크리 2%
- **장비 경험치 보너스**: S풀세팅 +330% (장비가 성장 속도 좌우)
- **Lv.60**: G등급+S장비 해금 | **Lv.70**: 엔드게임 진입 (~46시간)
- **Lv.100**: 하드코어 (~517시간)
- 상세: balance.md 참조

## BlockShip Java 플러그인 (배 + 칭호)
- 소스: `/Users/user/development/blockship-plugin/`
- 빌드: `cd /Users/user/development/blockship-plugin && ./gradlew build`
- 배포: `cp build/libs/BlockShip-1.0.0-SNAPSHOT.jar /Users/user/Library/Application\ Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/`
- **핫리로드**: `/plugman reload BlockShip` (PlugManX — 서버 재시작 없이 JAR 리로드)
- 빌드+배포+리로드 한줄: `cd /Users/user/development/blockship-plugin && ./gradlew build && cp build/libs/BlockShip-1.0.0-SNAPSHOT.jar "/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/"`
- 이후 인게임에서 `/plugman reload BlockShip`

### /textride 서브커맨드 (기존 명령어에 통합, 새 명령어 등록 불필요)
- `/textride <player> <tag>` — Paper addPassenger (기존)
- `/textride update <player> <titleTag> <nameTag> <titleText>` — 칭호 업데이트 (HEX 지원)
- `/textride combo <player> <titleTag> <nameTag> <combo>` — 콤보 파스텔 그라데이션
- `/textride remove <player> <titleTag> <nameTag>` — 칭호 제거

## 운영 서버 (Oracle Cloud)

### 서버 정보
- **Provider**: Oracle Cloud Infrastructure (Always Free)
- **계정**: 가족 명의 (rhfipkk tenancy, ap-chuncheon-1)
- **리전**: South Korea North (Chuncheon) — 한국 핑 5~10ms
- **인스턴스**: `minecraft-server` (ID는 retry log 참조)
- **현재 사양**: VM.Standard.A1.Flex 4 OCPU / 24 GB RAM (목표 달성, Java 힙 12G)
- **OS**: Ubuntu 24.04 ARM64
- **공인 IP**: `134.185.113.25` (Ephemeral — 인스턴스 재생성 시 변경됨)
- **SSH 키**: `~/.ssh/oracle-mc.key` (Mac 로컬)
- **SSH 접속**: `ssh -i ~/.ssh/oracle-mc.key ubuntu@134.185.113.25`
- **OCI CLI 설정**: `~/.oci-family/config` (가족 계정용, OCI_CLI_CONFIG_FILE 환경변수로 지정)
- **서버 경로**: `~/mcserver/` (인스턴스 안)
- **Java**: Azul Zulu JDK 21 ARM (`/usr/lib/jvm/zulu21-ca-arm64`)
- **방화벽**: 22 (SSH), 25565 (마크) 열림 (iptables + OCI Security List)

### Dev / Prod 분리 (옵션 C - 하이브리드)
- **Mac (패더)** = dev: 본인이 개발/테스트하는 곳
- **Oracle (춘천)** = prod: 베타 유저 접속하는 운영 서버
- **유저 데이터(`variables.csv`, `world/`)는 환경별 별개** — sync 금지!
- 코드(`.sk`, jar, 설정)만 dev → prod 동기화

### 자동 sync (옵션 C)
**.sk 파일** — fswatch + rsync 자동 동기화
- 위치: `~/auto-sync-skript.sh`
- 작동: Mac에서 `.sk` 저장 → 즉시 오라클 업로드 (1초)
- 백그라운드 실행: `nohup ~/auto-sync-skript.sh > ~/auto-sync.log 2>&1 &`
- 적용: 인게임에서 `/sk reload <파일명>` 또는 `/sk reload scripts/`

**BlockShip Java plugin** — 빌드 후 배포 스크립트
- 위치: `~/deploy-blockship.sh`
- 한 줄 실행: `~/deploy-blockship.sh`
- 동작: 로컬 빌드 → SCP로 오라클 plugins/ 업로드 → SSH로 plugman reload

**전체 변경** — Git 백업
- Skript scripts 폴더가 git repo
- 의미 있는 변경마다 commit
- 오라클은 git pull 하지 않음 (rsync로 이미 sync됨). Git은 백업/롤백용

### 운영 명령어
```bash
# 오라클 SSH 접속
ssh -i ~/.ssh/oracle-mc.key ubuntu@134.185.113.25

# 마크 서버 콘솔 (tmux 세션)
ssh -i ~/.ssh/oracle-mc.key ubuntu@134.185.113.25 -t 'tmux attach -t mc'
# 분리: Ctrl+B, D

# 마크 서버 재시작 (systemd)
ssh -i ~/.ssh/oracle-mc.key ubuntu@134.185.113.25 'sudo systemctl restart mcserver'

# 로그 확인
ssh -i ~/.ssh/oracle-mc.key ubuntu@134.185.113.25 'tail -f ~/mcserver/logs/latest.log'

# variables.csv 백업
scp -i ~/.ssh/oracle-mc.key ubuntu@134.185.113.25:~/mcserver/plugins/Skript/variables.csv ~/Desktop/prod-vars-$(date +%Y%m%d).csv
```

### 자동 백업 (오라클 cron)
- 매일 04:00: `variables.csv` → `~/mcserver/backups/`
- 매일 05:00: 월드 폴더 tar.gz → `~/mcserver/backups/`
- 30일 지난 백업 자동 삭제

### Resize 자동 재시도 (백그라운드)
- 위치: `~/oracle-auto-retry/resize-retry.sh`
- 동작: 현재 사양보다 큰 자리 나는 대로 자동 resize 시도 (목표 4/24)
- 로그: `~/oracle-auto-retry/resize-retry.log`
- 성공: `~/oracle-auto-retry/SUCCESS-RESIZE.txt` 생성 + macOS 알림

## 리소스팩
- GitHub: `https://github.com/wsi1212/minecraft-fish-resource-pack`
- 로컬: `~/Library/Application Support/minecraft/resourcepacks/barkan-resourcepack.zip`
- 빌드 폴더: `~/Downloads/barkan-resourcepack/`
- 서버 자동 적용: `server.properties`에 GitHub Releases URL+SHA1 설정됨 (`require-resource-pack=true`)
- **자동 배포**: `~/Downloads/barkan-resourcepack/deploy.sh` 실행 한 줄로 전체 자동화
  - ZIP 생성 (로컬+배포) → Git 커밋+푸시 → GitHub Release 업로드 → SHA1 갱신 → server.properties 업데이트
  - 서버 재시작하면 접속자에게 자동 적용
- **수동 배포 절차** (deploy.sh 못 쓸 때):
  1. `~/Downloads/barkan-resourcepack/` 내 파일 수정
  2. `cd ~/Downloads/barkan-resourcepack && zip -r /tmp/barkan-resourcepack.zip . -x ".*" -x "deploy.sh"`
  3. `gh release delete latest --repo wsi1212/minecraft-fish-resource-pack --yes`
  4. `gh release create latest /tmp/barkan-resourcepack.zip --repo wsi1212/minecraft-fish-resource-pack --title "Latest"`
  5. `shasum /tmp/barkan-resourcepack.zip` → server.properties의 `resource-pack-sha1` 업데이트
  6. 서버 재시작
- **커스텀 사운드**: `assets/barkan/sounds.json`에 등록, `assets/barkan/sounds/weather/*.ogg`에 파일 배치
  - ogg (Vorbis) 형식만 지원, wav→ogg 변환: `ffmpeg -i input.wav -c:a libvorbis -q:a 5 output.ogg`
  - 페이드아웃: `ffmpeg -i input.wav -t 19 -af "afade=t=out:st=16:d=3" -c:a libvorbis -q:a 5 output.ogg`
- 상세: [resourcepack.md](resourcepack.md)
