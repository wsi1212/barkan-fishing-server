#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Paper 부팅 스모크 테스트
#
# 새 플러그인 jar를 꽂은 Paper 서버를 버려질 월드에서 실제로 부팅시켜,
# "뜨는가 / 플러그인이 enable까지 가는가 / 치명 예외가 없는가"를 판정한다.
# 마크 클라이언트도 사람도 필요 없다 → CI에서 무인으로 돌리는 게 목적.
#
# 이게 잡는 사고: 2026-08-03 prod 장애(jar 교체 후 NoClassDefFoundError:
# WeatherManager$WeatherChoice → /칭호·계단앉기 전방위 고장, 3시간 뒤 인지).
# 부팅만 시켜봤다면 배포 전에 걸렸다.
#
# 사용법:
#   paper-smoke-test.sh --plugin build/libs/BlockShip-1.0.0-SNAPSHOT.jar \
#                       --expect-plugin BlockShip
#
# 종료코드: 0 = 통과, 1 = 실패(치명 예외/미부팅/플러그인 enable 실패), 2 = 사용법 오류
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

MC_VERSION="1.21.11"          # prod 구동 버전 (2026-08-13 확인, version_history.json)
TIMEOUT=240                   # Done 대기 상한(초). 컨테이너 실측 ~40s
HEAP="1G"
WORKDIR=""
CACHE_DIR="${PAPER_CACHE_DIR:-$PWD/.paper-cache}"
KEEP=0
PLUGINS=()
EXPECT_PLUGINS=()
RCON_COMMANDS=()
EXTRA_IGNORES=()

usage() {
  sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'
  echo
  echo "옵션:"
  echo "  --plugin PATH          plugins/ 에 넣을 jar (반복 가능 — 의존 플러그인도 이걸로)"
  echo "  --expect-plugin NAME   반드시 enable 돼야 하는 플러그인 이름 (반복 가능)"
  echo "  --rcon-command CMD     부팅 후 실행할 rcon 명령 (반복 가능, 예: 데이터리로드)"
  echo "  --mc-version VER       Paper 버전 (기본 $MC_VERSION)"
  echo "  --timeout SEC          Done 대기 상한 (기본 $TIMEOUT)"
  echo "  --heap SIZE            -Xmx 값 (기본 $HEAP)"
  echo "  --ignore PATTERN       무해로 취급할 로그 패턴 추가 (반복 가능)"
  echo "  --cache-dir DIR        Paper jar 캐시 위치 (기본 \$PWD/.paper-cache)"
  echo "  --workdir DIR          서버 실행 디렉토리 (기본 mktemp, 종료 시 삭제)"
  echo "  --keep                 실행 디렉토리·로그를 남긴다 (디버깅용)"
  exit "${1:-2}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plugin)        PLUGINS+=("$2"); shift 2 ;;
    --expect-plugin) EXPECT_PLUGINS+=("$2"); shift 2 ;;
    --rcon-command)  RCON_COMMANDS+=("$2"); shift 2 ;;
    --mc-version)    MC_VERSION="$2"; shift 2 ;;
    --timeout)       TIMEOUT="$2"; shift 2 ;;
    --heap)          HEAP="$2"; shift 2 ;;
    --ignore)        EXTRA_IGNORES+=("$2"); shift 2 ;;
    --cache-dir)     CACHE_DIR="$2"; shift 2 ;;
    --workdir)       WORKDIR="$2"; shift 2 ;;
    --keep)          KEEP=1; shift ;;
    -h|--help)       usage 0 ;;
    *) echo "알 수 없는 인자: $1" >&2; usage 2 ;;
  esac
done

# 플러그인 경로를 절대경로로 고정한다 — 아래에서 서버 디렉토리로 cd 하므로
# 상대경로를 그대로 들고 가면 "플러그인 jar 없음"으로 오판한다.
for i in "${!PLUGINS[@]}"; do
  if [[ ! -f "${PLUGINS[$i]}" ]]; then
    echo "플러그인 jar 없음: ${PLUGINS[$i]}" >&2; exit 2
  fi
  PLUGINS[$i]=$(realpath "${PLUGINS[$i]}")
done
[[ -n "$WORKDIR" ]] && WORKDIR=$(realpath -m "$WORKDIR")
CACHE_DIR=$(realpath -m "$CACHE_DIR")

# ── 치명 패턴 ────────────────────────────────────────────────────────────────
# 하나라도 로그에 있으면 실패. 넓게 잡으면 오탐으로 게이트가 무의미해지므로
# "배포를 되돌려야 하는 종류"만 엄선한다.
FATAL_PATTERNS=(
  'NoClassDefFoundError'                 # ★2026-08-03 사고
  'ClassNotFoundException'
  'UnsupportedClassVersionError'         # 자바 버전 불일치
  'NoSuchMethodError'                    # ★API 드리프트 (1.21.4 빌드 vs 1.21.11 구동, 7패치 차)
  'NoSuchFieldError'
  'IncompatibleClassChangeError'
  'Error occurred while enabling'
  'Could not load '
  'is not a valid plugin'
  'Ambiguous plugin name'
  'Could not initialize plugin'
  'Encountered an unexpected exception'
  'Failed to start the minecraft server'
)
# ── 무해 패턴 ────────────────────────────────────────────────────────────────
# CI 환경·버전 드리프트 때문에 정상적으로 뜨는 경고들. 치명 스캔에서 제외.
IGNORE_PATTERNS=(
  'Advanced terminal features are not available'   # 헤드리스 CI에서 항상 뜸
  'not yet been tested'                            # ProtocolLib이 1.21.11에 대해 내는 경고
  'You are running an outdated'
)
IGNORE_PATTERNS+=("${EXTRA_IGNORES[@]+"${EXTRA_IGNORES[@]}"}")

log()  { printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*"; }
fail() { printf '\n\033[31m✗ 스모크 실패\033[0m — %s\n' "$*"; }
pass() { printf '\n\033[32m✓ 스모크 통과\033[0m — %s\n' "$*"; }

# ── Paper jar 확보 (fill v3 API) ─────────────────────────────────────────────
# ★v2 API(api.papermc.io)는 sunset — {"ok":false,"error":"sunset"} 만 돌려준다.
#   낡은 스크립트를 그대로 쓰면 조용히 깨지므로 v3(fill.papermc.io)를 쓴다.
mkdir -p "$CACHE_DIR"
log "Paper $MC_VERSION 최신 빌드 조회 (fill v3)"
BUILDS_JSON="$CACHE_DIR/builds-$MC_VERSION.json"
if ! curl -fsS --max-time 60 \
      "https://fill.papermc.io/v3/projects/paper/versions/$MC_VERSION/builds" \
      -o "$BUILDS_JSON"; then
  fail "Paper 빌드 목록 조회 실패 (네트워크/버전 확인: $MC_VERSION)"
  exit 1
fi

read -r BUILD_ID PAPER_NAME PAPER_URL PAPER_SHA <<<"$(python3 - "$BUILDS_JSON" <<'PY'
import json, sys
builds = json.load(open(sys.argv[1]))
if not builds:
    sys.exit("빌드 없음")
b = max(builds, key=lambda x: x["id"])
d = b["downloads"]["server:default"]
print(b["id"], d["name"], d["url"], d["checksums"]["sha256"])
PY
)" || { fail "빌드 메타 파싱 실패"; exit 1; }

PAPER_JAR="$CACHE_DIR/$PAPER_NAME"
if [[ -f "$PAPER_JAR" ]] && [[ "$(sha256sum "$PAPER_JAR" | cut -d' ' -f1)" == "$PAPER_SHA" ]]; then
  log "캐시 적중: $PAPER_NAME (build $BUILD_ID)"
else
  log "다운로드: $PAPER_NAME (build $BUILD_ID)"
  curl -fsS --max-time 300 -o "$PAPER_JAR" "$PAPER_URL" || { fail "Paper 다운로드 실패"; exit 1; }
  ACTUAL=$(sha256sum "$PAPER_JAR" | cut -d' ' -f1)
  if [[ "$ACTUAL" != "$PAPER_SHA" ]]; then
    fail "체크섬 불일치 (기대 $PAPER_SHA / 실제 $ACTUAL)"
    rm -f "$PAPER_JAR"; exit 1
  fi
  log "체크섬 검증 OK"
fi

# ── 서버 디렉토리 준비 ───────────────────────────────────────────────────────
if [[ -z "$WORKDIR" ]]; then
  WORKDIR=$(mktemp -d -t paper-smoke-XXXXXX)
  TEMP_WORKDIR=1
else
  mkdir -p "$WORKDIR"; TEMP_WORKDIR=0
fi
cleanup() {
  [[ -n "${JAVA_PID:-}" ]] && kill "$JAVA_PID" 2>/dev/null
  [[ -n "${HOLDER_PID:-}" ]] && kill "$HOLDER_PID" 2>/dev/null
  if [[ $KEEP -eq 0 && $TEMP_WORKDIR -eq 1 ]]; then rm -rf "$WORKDIR"; fi
}
trap cleanup EXIT

cd "$WORKDIR"
cp "$PAPER_JAR" paper.jar
echo "eula=true" > eula.txt
RCON_PW="smoke$RANDOM$RANDOM"
RCON_ON=false; [[ ${#RCON_COMMANDS[@]} -gt 0 ]] && RCON_ON=true
# 슈퍼플랫 + 최소 시야 = 월드 생성 비용·디스크 최소화
cat > server.properties <<EOF
online-mode=false
level-type=minecraft\\:flat
level-name=smokeworld
view-distance=4
simulation-distance=4
max-players=1
spawn-protection=0
spawn-npcs=false
spawn-animals=false
spawn-monsters=false
enable-rcon=$RCON_ON
rcon.port=25575
rcon.password=$RCON_PW
server-port=25599
motd=smoke-test
sync-chunk-writes=false
EOF

mkdir -p plugins
for p in ${PLUGINS[@]+"${PLUGINS[@]}"}; do
  [[ -f "$p" ]] || { fail "플러그인 jar 없음: $p"; exit 1; }
  cp "$p" plugins/
  log "플러그인 투입: $(basename "$p") ($(du -h "$p" | cut -f1))"
done

# ── 부팅 ────────────────────────────────────────────────────────────────────
# stdin을 fifo로 물려야 나중에 'stop'을 넣어 정상 종료시킬 수 있다.
mkfifo ctl
# ★홀더의 stdout/stderr를 반드시 /dev/null로 보낼 것 — 상속받은 파이프를 붙잡고
#   있으면 호출측의 `| tail` 같은 파이프라인이 홀더가 죽을 때까지 안 닫힌다.
( exec 3>ctl; sleep "$((TIMEOUT + 120))" >&3 ) >/dev/null 2>&1 &
HOLDER_PID=$!
log "부팅 시작 (heap $HEAP, timeout ${TIMEOUT}s)"
START=$(date +%s)
java -Xms512M -Xmx"$HEAP" -XX:+UseG1GC -jar paper.jar --nogui < ctl > boot.log 2>&1 &
JAVA_PID=$!

BOOTED=0
for ((i = 0; i < TIMEOUT; i++)); do
  if grep -q 'Done (' boot.log 2>/dev/null; then BOOTED=1; break; fi
  if ! kill -0 "$JAVA_PID" 2>/dev/null; then break; fi
  sleep 1
done
ELAPSED=$(( $(date +%s) - START ))

# ── rcon 프로브 ─────────────────────────────────────────────────────────────
# "서버는 살아있는데 게임 로직만 깨짐"은 부팅 로그로 안 잡힌다.
# 플러그인 코드 경로를 실제로 때려서 그 사각을 좁힌다.
RCON_FAILED=0
if [[ $BOOTED -eq 1 && ${#RCON_COMMANDS[@]} -gt 0 ]]; then
  sleep 3
  for cmd in "${RCON_COMMANDS[@]}"; do
    log "rcon → $cmd"
    if OUT=$(python3 - "$RCON_PW" "$cmd" <<'PY'
import socket, struct, sys
pw, cmd = sys.argv[1], sys.argv[2]
def pkt(i, t, b):
    p = struct.pack('<ii', i, t) + b.encode('utf-8') + b'\x00\x00'
    return struct.pack('<i', len(p)) + p
def read(s):
    raw = s.recv(4)
    if len(raw) < 4: raise RuntimeError('응답 없음')
    n = struct.unpack('<i', raw)[0]
    data = b''
    while len(data) < n: data += s.recv(n - len(data))
    return struct.unpack('<i', data[0:4])[0], data[8:-2].decode('utf-8', 'replace')
s = socket.create_connection(('127.0.0.1', 25575), timeout=20)
s.sendall(pkt(1, 3, pw))
rid, _ = read(s)
if rid == -1: raise RuntimeError('rcon 인증 실패')
s.sendall(pkt(2, 2, cmd))
_, body = read(s)
print(body.strip())
PY
    ); then
      printf '      ↳ %s\n' "${OUT:-(빈 응답)}"
    else
      fail "rcon 명령 실패: $cmd"; RCON_FAILED=1
    fi
  done
fi

# ── 종료 ────────────────────────────────────────────────────────────────────
if [[ $BOOTED -eq 1 ]]; then
  log "정상 종료 요청 (stop)"
  echo "stop" > ctl
  for ((i = 0; i < 90; i++)); do kill -0 "$JAVA_PID" 2>/dev/null || break; sleep 1; done
fi
kill "$JAVA_PID" "$HOLDER_PID" 2>/dev/null
wait "$JAVA_PID" 2>/dev/null

# ── 판정 ────────────────────────────────────────────────────────────────────
echo
echo "──────────── 판정 ────────────"
PROBLEMS=()

if [[ $BOOTED -eq 0 ]]; then
  PROBLEMS+=("${TIMEOUT}s 안에 'Done ('에 도달하지 못함 (서버가 뜨지 않았다)")
else
  log "부팅 완료: ${ELAPSED}s"
fi

# 무해 패턴을 걷어낸 뒤 치명 패턴 스캔
IGNORE_RE=$(IFS='|'; echo "${IGNORE_PATTERNS[*]}")
grep -vE "$IGNORE_RE" boot.log > scan.log 2>/dev/null || cp boot.log scan.log
for pat in "${FATAL_PATTERNS[@]}"; do
  if grep -qF "$pat" scan.log; then
    PROBLEMS+=("치명 패턴 발견: $pat")
    echo "  ┌─ $pat 관련 로그"
    grep -F -m3 -A4 "$pat" scan.log | sed 's/^/  │ /'
    echo "  └─"
  fi
done

# ★Paper는 onEnable 을 실행하기 "전에" Enabling 을 찍는다. 그래서 Enabling 만
#   보면 onEnable 이 터져도 통과로 읽힌다(실측 확인). enable 실패 로그를 함께 본다.
for name in ${EXPECT_PLUGINS[@]+"${EXPECT_PLUGINS[@]}"}; do
  if ! grep -qE "Enabling $name" boot.log; then
    PROBLEMS+=("$name 이 로드되지 않았다 (jar 손상 / plugin.yml / 의존 플러그인 누락 확인)")
  elif grep -qE "Error occurred while enabling $name" boot.log; then
    PROBLEMS+=("$name 이 enable 도중 예외로 죽었다")
  else
    log "플러그인 enable 확인: $name"
  fi
done

[[ $RCON_FAILED -eq 1 ]] && PROBLEMS+=("rcon 프로브 실패")

# 참고용: 치명은 아니지만 사람이 볼 만한 경고
WARN_COUNT=$(grep -cE '(WARN|ERROR)\]' scan.log 2>/dev/null || echo 0)
if [[ "$WARN_COUNT" -gt 0 ]]; then
  echo "  ⓘ WARN/ERROR $WARN_COUNT 줄 (치명 아님, 참고):"
  grep -E '(WARN|ERROR)\]' scan.log | head -5 | sed 's/^/  ⓘ /'
fi

if [[ $KEEP -eq 1 ]]; then echo "  로그: $WORKDIR/boot.log"; fi

if [[ ${#PROBLEMS[@]} -eq 0 ]]; then
  pass "부팅 ${ELAPSED}s, 치명 예외 없음"
  exit 0
else
  for p in "${PROBLEMS[@]}"; do echo "  • $p"; done
  fail "${#PROBLEMS[@]}건"
  exit 1
fi
