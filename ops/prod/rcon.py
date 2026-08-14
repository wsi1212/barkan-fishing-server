#!/usr/bin/env python3
# 의존성 없는 최소 Source RCON 클라이언트.
# server.properties에서 rcon.port/rcon.password를 읽어 127.0.0.1로 접속.
# 사용: rcon.py [명령]   (기본 "list")
# 종료코드 0=성공(응답 받음) / 그 외=실패(접속불가·인증실패·타임아웃)
#   → 메인스레드가 얼면 명령이 실행 안 돼 소켓 read 타임아웃 → 실패로 판정됨.
import socket, struct, sys, os

PROPS = os.path.expanduser("~/mcserver/server.properties")
TIMEOUT = 10  # 초. 프리즈 서버는 이 안에 응답 못 함.

def props():
    d = {}
    with open(PROPS) as f:
        for ln in f:
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1); d[k] = v
    return d

def pkt(pid, ptype, body):
    data = struct.pack("<ii", pid, ptype) + body.encode("utf8") + b"\x00\x00"
    return struct.pack("<i", len(data)) + data

def recv(sock):
    raw = b""
    while len(raw) < 4:
        c = sock.recv(4 - len(raw))
        if not c: raise IOError("연결 끊김")
        raw += c
    ln = struct.unpack("<i", raw)[0]
    data = b""
    while len(data) < ln:
        c = sock.recv(ln - len(data))
        if not c: raise IOError("연결 끊김")
        data += c
    pid, ptype = struct.unpack("<ii", data[:8])
    return pid, ptype, data[8:-2].decode("utf8", "replace")

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    p = props()
    port = int(p.get("rcon.port", "25575"))
    pw = p.get("rcon.password", "")
    if not pw:
        print("rcon.password 비어있음", file=sys.stderr); return 3
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=TIMEOUT)
        s.settimeout(TIMEOUT)
        s.sendall(pkt(1, 3, pw))            # AUTH
        pid, _, _ = recv(s)
        if pid == -1:
            print("RCON 인증 실패", file=sys.stderr); return 2
        s.sendall(pkt(2, 2, cmd))           # EXEC
        _, _, resp = recv(s)
        s.close()
        print(resp.strip())
        return 0
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        print(f"RCON 실패: {e}", file=sys.stderr); return 1

if __name__ == "__main__":
    sys.exit(main())
