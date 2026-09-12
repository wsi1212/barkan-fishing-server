#!/bin/bash
# dev Minecraft(Paper) 서버 관리 — feather 밖에서 직접 띄워 자동 재시작 제어.
# RCON(enable-rcon)으로 명령/정지, nohup으로 기동. prod의 tmux 대체.
# ★JAVA 경로를 박아두면 런처가 번들 JRE를 갈아치울 때 dev가 조용히 못 뜬다
#   (2026-08-04: zulu25.32.21이 사라져 "No such file or directory"로 기동 실패).
#   번들 zulu 중 21 이상 최신을 자동 선택하고, 없으면 시스템 JDK 21로 폴백한다.
JAVA=""; JAVA_VER=0
# ★글롭으로 순회한다 — $(ls -d "…Application Support…") 는 공백에서 쪼개져 전부 놓친다.
for cand in "/Users/user/Library/Application Support/minecraft/jre/"zulu*/Contents/Home/bin/java; do
  [ -x "$cand" ] || continue
  ver=$("$cand" -version 2>&1 | head -1 | grep -oE '"[0-9]+' | tr -d '"')
  [ -n "$ver" ] || continue
  if [ "$ver" -ge 21 ] && [ "$ver" -gt "$JAVA_VER" ]; then JAVA="$cand"; JAVA_VER="$ver"; fi
done
if [ -z "$JAVA" ]; then
  JAVA="$(/usr/libexec/java_home -v 21 2>/dev/null)/bin/java"
fi
if [ ! -x "$JAVA" ]; then
  echo "❌ Java 21+ 를 못 찾았다. 마크 런처 번들 JRE도, 시스템 JDK 21도 없다."
  exit 1
fi
SRV="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a"
PAPER="/Users/user/Library/Application Support/minecraft/libraries/java/paper-1.21.11-132.jar"
LOG="$SRV/logs/dev-script.log"
PIDFILE="$SRV/dev-paper.pid"
RHOST=127.0.0.1; RPORT=25575; RPW=devtest2026
DEV_NETWORK="$SRV/dev-maintenance-network"
LEGACY_LAUNCHD_LABEL=com.barkan.blockship-dev
TMUX_SESSION=barkan-dev-main

rcon() { # RCON으로 명령 1개 전송 (외부 의존성 없음, 순수 python)
  RCMD="$1" python3 - "$RHOST" "$RPORT" "$RPW" <<'PY'
import socket,struct,os,sys,time
host,port,pw=sys.argv[1],int(sys.argv[2]),sys.argv[3]
cmd=os.environ.get('RCMD','')
def pk(i,t,b):
    d=struct.pack('<ii',i,t)+b.encode('utf-8')+b'\x00\x00'; return struct.pack('<i',len(d))+d
try:
    s=socket.create_connection((host,port),timeout=4)
    s.sendall(pk(1,3,pw)); s.recv(4096)
    s.sendall(pk(2,2,cmd)); time.sleep(0.3)
    data=s.recv(4096); s.close()
    print(data[12:].split(b'\x00')[0].decode('utf-8','ignore') if len(data)>12 else 'OK')
except Exception as e:
    print('RCON_ERR',e); sys.exit(1)
PY
}

server_port() { awk -F= '$1 == "server-port" { print $2; exit }' "$SRV/server.properties"; }
is_up() { local port; port=$(server_port); lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; }
paper_pids() { ps -axo pid=,command= | awk -v jar="$PAPER" 'index($0, " -jar " jar " ") { print $1 }'; }
is_running() { [ -n "$(paper_pids)" ]; }
signal_paper() {
  local signal="$1" pid
  while read -r pid; do [ -z "$pid" ] || kill "-$signal" "$pid" 2>/dev/null || true; done < <(paper_pids)
}
remove_legacy_launchd() {
  launchctl print "gui/$(id -u)/$LEGACY_LAUNCHD_LABEL" >/dev/null 2>&1 || return 0
  echo "⏹ 기존 launchd 자동재기동 해제"
  launchctl remove "$LEGACY_LAUNCHD_LABEL" >/dev/null 2>&1 || true
}

start() {
  if is_up || is_running; then echo "⚠ dev Paper 프로세스가 이미 실행중 — 기존 인스턴스를 먼저 끄세요 (./dev-mc.sh stop)."; return 0; fi
  local command
  : > "$LOG"
  tmux kill-session -t "$TMUX_SESSION" >/dev/null 2>&1 || true
  if [ -d "$DEV_NETWORK/shared/ship-entities" ]; then
    printf -v command 'echo $$ > %q; exec env BLOCKSHIP_SHIP_MARKER_DIR=%q %q -Dterminal.jline=false -Dterminal.ansi=false -Xms2048M -Xmx2048M -jar %q nogui > %q 2>&1' \
      "$PIDFILE" "$DEV_NETWORK/shared/ship-entities" "$JAVA" "$PAPER" "$LOG"
  else
    printf -v command 'echo $$ > %q; exec %q -Dterminal.jline=false -Dterminal.ansi=false -Xms2048M -Xmx2048M -jar %q nogui > %q 2>&1' \
      "$PIDFILE" "$JAVA" "$PAPER" "$LOG"
  fi
  tmux new-session -d -s "$TMUX_SESSION" -c "$SRV" "$command"
  for i in $(seq 1 5); do [ -s "$PIDFILE" ] && break; sleep 0.2; done
  echo "▶ dev 서버 시작 (pid $(cat "$PIDFILE" 2>/dev/null || echo '?'))"
  for i in $(seq 1 90); do grep -q 'Done (' "$LOG" 2>/dev/null && { echo "✅ 기동 완료 ($(grep -o 'Done ([0-9.]*s)' "$LOG" | tail -1))"; return 0; }; sleep 1; done
  echo "⏱ 기동 대기 타임아웃 — 로그: $LOG" >&2
  return 1
}

stop() {
  if ! is_up && ! is_running; then rm -f "$PIDFILE"; tmux kill-session -t "$TMUX_SESSION" >/dev/null 2>&1 || true; echo "서버가 떠있지 않음"; return 0; fi
  if is_up; then
    echo "⏹ 저장+정지 (RCON)..."; rcon "save-all" >/dev/null; rcon "stop" >/dev/null
  else
    echo "⏹ 포트는 닫혔지만 남은 dev Paper 프로세스 종료 중..."
  fi
  remove_legacy_launchd
  for i in $(seq 1 45); do
    if ! is_up && ! is_running; then rm -f "$PIDFILE"; tmux kill-session -t "$TMUX_SESSION" >/dev/null 2>&1 || true; echo "✅ 정지됨"; return 0; fi
    sleep 1
  done
  echo "⏱ 정지 지연 — SIGTERM"; signal_paper TERM
  for i in $(seq 1 15); do
    if ! is_up && ! is_running; then rm -f "$PIDFILE"; tmux kill-session -t "$TMUX_SESSION" >/dev/null 2>&1 || true; echo "✅ 강제 종료 완료"; return 0; fi
    sleep 1
  done
  echo "⏱ 종료 고착 — dev Paper만 SIGKILL"; signal_paper KILL
  for i in $(seq 1 5); do
    if ! is_up && ! is_running; then rm -f "$PIDFILE"; tmux kill-session -t "$TMUX_SESSION" >/dev/null 2>&1 || true; echo "✅ 최종 종료 완료"; return 0; fi
    sleep 1
  done
  echo "❌ dev Paper 프로세스가 계속 남아 있음" >&2
  return 1
}

case "$1" in
  start) start;;
  stop) stop;;
  restart) stop; sleep 2; start;;
  cmd) shift; rcon "$*";;
  log) tail -n "${2:-40}" "$LOG" 2>/dev/null || echo "로그 없음(아직 스크립트로 안 띄움): $LOG";;
  *) echo "사용법: dev-mc.sh start | stop | restart | cmd <명령> | log [N]";;
esac
