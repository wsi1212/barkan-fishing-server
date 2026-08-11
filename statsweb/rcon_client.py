"""
rcon_client.py — 의존성 없는 최소 Source RCON 클라이언트 (stats-system-plan.md §10-6 Phase 6).

oracle-ops-scripts/rcon.py(박스 크론에서 쓰는 프리즈 워치독용 CLI)와 동일한 프로토콜 구현을
statsweb이 import해서 쓸 수 있는 함수 형태로 재작성한 것 — 그 스크립트는 CLI 전용이라 여기서
새로 만들되 패킷 포맷은 그대로 재사용(검증된 구현).

★박스 배치 시 statsweb은 RCON과 "같은 박스"에서 돈다(§10-6: "새로 여는 포트가 0개") —
RCON_HOST는 기본 127.0.0.1이고 절대 외부에 노출하지 않는다. RCON_PASSWORD가 비어있으면
(기본값, 샌드박스/미설정 상태) 모든 액션이 즉시 RconDisabled를 던져 안전하게 막힌다.
"""
import os
import socket
import struct


class RconError(Exception):
    """RCON 접속/인증/실행 실패 — 호출부가 사용자에게 그대로 보여줄 메시지."""


class RconDisabled(RconError):
    """RCON_PASSWORD가 설정 안 됨 — 의도적 기본 비활성 상태(운영자가 .env에 명시적으로 설정해야 함)."""


def _config():
    host = os.environ.get("RCON_HOST", "127.0.0.1")
    port = int(os.environ.get("RCON_PORT", "25575"))
    password = os.environ.get("RCON_PASSWORD", "")
    timeout = float(os.environ.get("RCON_TIMEOUT", "10"))
    return host, port, password, timeout


def _pkt(pid, ptype, body):
    data = struct.pack("<ii", pid, ptype) + body.encode("utf8") + b"\x00\x00"
    return struct.pack("<i", len(data)) + data


def _recv(sock):
    raw = b""
    while len(raw) < 4:
        chunk = sock.recv(4 - len(raw))
        if not chunk:
            raise RconError("RCON 연결이 끊겼습니다")
        raw += chunk
    length = struct.unpack("<i", raw)[0]
    data = b""
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            raise RconError("RCON 연결이 끊겼습니다")
        data += chunk
    pid, ptype = struct.unpack("<ii", data[:8])
    return pid, ptype, data[8:-2].decode("utf8", "replace")


def exec_command(command: str) -> str:
    """명령 1개를 실행하고 응답 문자열을 반환. 실패 시 RconError(또는 RconDisabled)."""
    host, port, password, timeout = _config()
    if not password:
        raise RconDisabled("RCON이 비활성 상태입니다(.env의 RCON_PASSWORD 미설정) — 운영자가 "
                            "server.properties의 rcon.password를 확인해 채워야 합니다.")
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except OSError as e:
        raise RconError(f"RCON 접속 실패({host}:{port}): {e}")
    try:
        sock.settimeout(timeout)
        sock.sendall(_pkt(1, 3, password))  # SERVERDATA_AUTH
        pid, _, _ = _recv(sock)
        if pid == -1:
            raise RconError("RCON 인증 실패(비밀번호 확인 필요)")
        sock.sendall(_pkt(2, 2, command))  # SERVERDATA_EXECCOMMAND
        _, _, resp = _recv(sock)
        return resp.strip()
    except socket.timeout:
        raise RconError("RCON 응답 시간 초과(서버가 멎어있을 수 있음)")
    except OSError as e:
        raise RconError(f"RCON 통신 실패: {e}")
    finally:
        sock.close()
