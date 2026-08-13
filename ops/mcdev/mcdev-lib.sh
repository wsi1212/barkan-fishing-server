# ─────────────────────────────────────────────────────────────────────────────
# mcdev 공통 설정·헬퍼 (source 전용, 직접 실행하지 않음)
#
# 설계 원칙: prod를 절대 위험에 빠뜨리지 않는다.
#   - dev 트리는 ~/mcdev/ 에 완전 분리. ~/mcserver/ 안에 두면
#     jar-guard.sh(2분 cron) · disk-guard.sh · 백업 glob · staging glob 에 전부 걸린다.
#   - 포트도 분리(25566/25576). watchdog.sh 가 rcon.py로 25575를 때리므로 겹치면 안 된다.
#   - systemd 유닛 없음. Restart=always 로 되살아나는 dev는 재앙이다.
# ─────────────────────────────────────────────────────────────────────────────

# 테스트·이식을 위해 전부 환경변수로 덮어쓸 수 있게 둔다
PROD_ROOT="${PROD_ROOT:-$HOME/mcserver}"
MCDEV_ROOT="${MCDEV_ROOT:-$HOME/mcdev}"
MCDEV_GAME_PORT="${MCDEV_GAME_PORT:-25566}"
MCDEV_RCON_PORT="${MCDEV_RCON_PORT:-25576}"
MCDEV_HEAP="${MCDEV_HEAP:-2G}"
MCDEV_TMUX="${MCDEV_TMUX:-mcdev}"
MCDEV_MINUTES_DEFAULT="${MCDEV_MINUTES_DEFAULT:-60}"

# 시작 거부 문턱 — prod 보호선
MEM_FLOOR_MB="${MEM_FLOOR_MB:-3500}"   # MemAvailable 이 이보다 낮으면 시작 거부
DISK_CEIL_PCT="${DISK_CEIL_PCT:-80}"   # 이 이상이면 sync 거부 (disk-guard 는 85%부터 백업을 지운다)

# ★화이트리스트 — 본인 마크 계정. 반드시 확인하고 고칠 것.
MCDEV_WHITELIST="${MCDEV_WHITELIST:-wsi1212}"

LOG_FILE="${MCDEV_LOG:-$PROD_ROOT/scripts/mcdev.log}"
WEBHOOK_FILE="${WEBHOOK_FILE:-$PROD_ROOT/scripts/discord-webhook.url}"
DEADLINE_FILE="$MCDEV_ROOT/.deadline"
TIMER_PID_FILE="$MCDEV_ROOT/.timer.pid"
JAVA_PID_FILE="$MCDEV_ROOT/.java.pid"
RCON_PW_FILE="$MCDEV_ROOT/.rcon-pw"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg"
  mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null
  echo "$msg" >> "$LOG_FILE" 2>/dev/null || true
}
die() { log "✗ $*"; exit 1; }

# Discord — prod 스크립트들과 같은 webhook 재사용
notify() {
  [[ -f "$WEBHOOK_FILE" ]] || return 0
  local url; url=$(<"$WEBHOOK_FILE")
  [[ -n "$url" ]] || return 0
  curl -fsS --max-time 15 -H 'Content-Type: application/json' \
    -d "$(python3 -c 'import json,sys; print(json.dumps({"content": sys.argv[1]}))' "$1")" \
    "$url" >/dev/null 2>&1 || true
}

# dev 가 살아있나 (tmux 세션 + 자바 프로세스)
# ★★ 프로세스 판정은 PID 파일 + /proc 검증으로만 한다. pgrep -f / pkill -f 금지.
#
# 실측으로 물린 함정: `pgrep -f "mcdev-paper.jar"` 는 그 문자열을 **명령줄에 언급한**
# 아무 프로세스나 잡는다 — 로그를 tail 하는 셸, ssh 명령, 다른 스크립트, 심지어
# 진단하려고 그 이름을 타이핑한 셸까지. 그래서 JVM 이 정상 종료된 뒤에도 true 가
# 나와 "stop 이 안 먹었다" 로 오판했다.
# 더 위험한 건 `pkill -f` 쪽 — 그 무관한 프로세스들을 실제로 죽인다. prod 박스에서
# 절대 있으면 안 되는 코드다.
dev_java_pid() {
  [[ -f "$JAVA_PID_FILE" ]] || return 1
  local p; p=$(<"$JAVA_PID_FILE")
  [[ "$p" =~ ^[0-9]+$ ]] || return 1
  # 그 PID 가 지금도 java 인지 확인한다 (PID 재사용 방어)
  [[ -r "/proc/$p/comm" ]] || return 1
  [[ "$(</proc/"$p"/comm)" == "java" ]] || return 1
  echo "$p"
}
dev_java_running() { dev_java_pid >/dev/null; }

# 마지막 수단. 대상은 PID 파일이 가리키는 java 프로세스 하나뿐이다.
dev_java_kill() {
  local p; p=$(dev_java_pid) || return 0
  log "강제 종료: java PID $p"
  kill -9 "$p" 2>/dev/null
}

dev_running() {
  tmux has-session -t "$MCDEV_TMUX" 2>/dev/null && dev_java_running
}

# prod 가 살아있나 — prod 가 죽어있으면 dev 를 켤 때가 아니다.
# systemd 를 먼저 믿는다(권위). pgrep 은 유닛 이름이 다를 때의 예비 수단일 뿐이고,
# 여기서는 아무것도 죽이지 않으므로 문자열 매칭이어도 위험하지 않다.
prod_running() {
  systemctl is-active --quiet mcserver 2>/dev/null && return 0
  pgrep -f "$PROD_ROOT.*paper.*\.jar" >/dev/null 2>&1
}

mem_available_mb() { awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo; }
disk_used_pct()    { df --output=pcent "$1" 2>/dev/null | tail -1 | tr -dc '0-9'; }

# dev rcon 호출. 성공 시 응답을 stdout 으로.
dev_rcon() {
  [[ -f "$RCON_PW_FILE" ]] || return 1
  python3 - "$(<"$RCON_PW_FILE")" "$MCDEV_RCON_PORT" "$*" <<'PY'
import socket, struct, sys
pw, port, cmd = sys.argv[1], int(sys.argv[2]), sys.argv[3]
def pkt(i, t, b):
    p = struct.pack('<ii', i, t) + b.encode('utf-8') + b'\x00\x00'
    return struct.pack('<i', len(p)) + p
def read(s):
    raw = s.recv(4)
    if len(raw) < 4: raise SystemExit(1)
    n = struct.unpack('<i', raw)[0]
    d = b''
    while len(d) < n: d += s.recv(n - len(d))
    return struct.unpack('<i', d[0:4])[0], d[8:-2].decode('utf-8', 'replace')
try:
    s = socket.create_connection(('127.0.0.1', port), timeout=10)
    s.sendall(pkt(1, 3, pw))
    if read(s)[0] == -1: raise SystemExit(1)
    s.sendall(pkt(2, 2, cmd))
    print(read(s)[1].strip())
except Exception:
    raise SystemExit(1)
PY
}
