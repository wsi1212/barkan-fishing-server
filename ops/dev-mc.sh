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
RHOST=127.0.0.1; RPORT=25575; RPW=devtest2026

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

is_up() { lsof -nP -iTCP:25565 -sTCP:LISTEN >/dev/null 2>&1; }

start() {
  if is_up; then echo "⚠ 25565 이미 사용중 — feather 서버나 기존 인스턴스를 먼저 끄세요 (./dev-mc.sh stop). 새 jar는 그 서버 재시작 시 반영됨."; return 0; fi
  cd "$SRV" || exit 1
  nohup "$JAVA" -Xms2048M -Xmx2048M -jar "$PAPER" nogui >"$LOG" 2>&1 &
  echo "▶ dev 서버 시작 (pid $!)"
  for i in $(seq 1 90); do grep -q 'Done (' "$LOG" 2>/dev/null && { echo "✅ 기동 완료 ($(grep -o 'Done ([0-9.]*s)' "$LOG" | tail -1))"; return 0; }; sleep 1; done
  echo "⏱ 기동 대기 타임아웃 — 로그: $LOG"
}

stop() {
  if ! is_up; then echo "서버가 떠있지 않음"; return 0; fi
  echo "⏹ 저장+정지 (RCON)..."; rcon "save-all" >/dev/null; rcon "stop" >/dev/null
  for i in $(seq 1 45); do is_up || { echo "✅ 정지됨"; return 0; }; sleep 1; done
  echo "⏱ 정지 지연 — 강제 종료"; pkill -f "paper-.*\.jar"
}

case "$1" in
  start) start;;
  stop) stop;;
  restart) stop; sleep 2; start;;
  cmd) shift; rcon "$*";;
  log) tail -n "${2:-40}" "$LOG" 2>/dev/null || echo "로그 없음(아직 스크립트로 안 띄움): $LOG";;
  *) echo "사용법: dev-mc.sh start | stop | restart | cmd <명령> | log [N]";;
esac
