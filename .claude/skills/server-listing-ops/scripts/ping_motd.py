#!/usr/bin/env python3
"""자바(TCP 25565) + 베드락(UDP 19132) MOTD 를 한 번에 읽는다.

MOTD 인증코드를 넣거나 되돌린 뒤 «양쪽 다» 확인하는 데 쓴다. 자바만 보고 통과로 판정하면
베드락 검증기가 주 MOTD(line1)만 읽는 경우에 걸린다 — 2026-09-01 마인리스트 베드락 인증이
정확히 그렇게 실패했다.

  python3 ping_motd.py                    # barkan.kr 기본
  python3 ping_motd.py 168.107.8.107      # IP 로
  python3 ping_motd.py barkan.kr --wait   # 재시작 후 부팅 대기(최대 5분)

종료코드: 0=양쪽 응답, 1=한쪽 이상 실패.
"""
import json
import socket
import struct
import sys
import time

DEFAULT_HOST = "barkan.kr"
JAVA_PORT = 25565
BEDROCK_PORT = 19132
BEDROCK_MAGIC = bytes.fromhex("00ffff00fefefefefdfdfdfd12345678")
# 1.21.x 계열 아무 값이나 handshake 에 실으면 status 응답은 그대로 온다.
PROTOCOL = 772


def _varint(n: int) -> bytes:
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        out += bytes([b | (0x80 if n else 0)])
        if not n:
            return out


def java_motd(host: str, port: int = JAVA_PORT, timeout: float = 8.0):
    """status 응답의 description 을 «표시 텍스트»로 평탄화해서 돌려준다."""
    sock = socket.create_connection((host, port), timeout)
    sock.settimeout(timeout)
    try:
        name = host.encode()
        payload = _varint(PROTOCOL) + _varint(len(name)) + name + struct.pack(">H", port) + _varint(1)
        for packet in (_varint(0x00) + payload, _varint(0x00)):
            sock.sendall(_varint(len(packet)) + packet)

        def read(n: int) -> bytes:
            buf = b""
            while len(buf) < n:
                chunk = sock.recv(n - len(buf))
                if not chunk:
                    raise EOFError("연결이 끊겼습니다")
                buf += chunk
            return buf

        def read_varint() -> int:
            n = shift = 0
            while True:
                b = read(1)[0]
                n |= (b & 0x7F) << shift
                if not (b & 0x80):
                    return n
                shift += 7

        read_varint()  # 패킷 길이
        read_varint()  # 패킷 id
        data = json.loads(read(read_varint()).decode("utf-8"))
    finally:
        sock.close()

    version = data.get("version") or {}
    return flatten(data.get("description")), version.get("name", "?"), (data.get("players") or {}).get("online")


def flatten(node) -> str:
    """description 은 문자열일 수도, {text, extra[]} 컴포넌트일 수도 있다."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(flatten(x) for x in node)
    return flatten(node.get("text", "")) + flatten(node.get("extra"))


def bedrock_motd(host: str, port: int = BEDROCK_PORT, timeout: float = 6.0):
    """UNCONNECTED_PONG 의 세미콜론 구분 필드에서 line1/line2 를 뽑는다."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(b"\x01" + struct.pack(">Q", 0) + BEDROCK_MAGIC + struct.pack(">Q", 2), (host, port))
        data, _ = sock.recvfrom(4096)
    finally:
        sock.close()
    # 0x1c | time(8) | serverGUID(8) | MAGIC(16) | len(2) | string
    body = data[1 + 8 + 8 + 16:]
    length = struct.unpack(">H", body[:2])[0]
    fields = body[2:2 + length].decode("utf-8", "replace").split(";")
    line1 = fields[1] if len(fields) > 1 else ""
    line2 = fields[7] if len(fields) > 7 else ""
    version = fields[3] if len(fields) > 3 else "?"
    return line1, line2, version


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    wait = "--wait" in sys.argv
    host = args[0] if args else DEFAULT_HOST

    if wait:
        for attempt in range(60):
            try:
                java_motd(host)
                print(f"부팅 확인 (~{attempt * 5}초)")
                break
            except Exception:
                time.sleep(5)
        else:
            print("부팅 대기 시간 초과 (5분)")
            return 1

    failed = False

    print(f"=== 자바  {host}:{JAVA_PORT} (TCP) ===")
    try:
        text, version, online = java_motd(host)
        for i, line in enumerate(text.split("\n"), 1):
            print(f"  line{i} = {line!r}")
        print(f"  버전 = {version} / 접속자 {online}")
    except Exception as exc:
        print(f"  ❌ 실패: {type(exc).__name__}: {exc}")
        failed = True

    print(f"=== 베드락 {host}:{BEDROCK_PORT} (UDP) ===")
    try:
        line1, line2, version = bedrock_motd(host)
        print(f"  line1 = {line1!r}")
        print(f"  line2 = {line2!r}")
        print(f"  버전 = {version}")
        if "Another Geyser server" in line2 or line1.startswith('"'):
            print("  ⚠ § 색코드 없는 MOTD 로 보입니다 — Paper 가 컴포넌트로 파싱하지 못해")
            print("    Geyser 가 JSON 문자열째로 내보내는 상태입니다. 각 줄에 §b/§e 를 붙이세요.")
            failed = True
    except socket.timeout:
        print(f"  ❌ 무응답 — 19132/UDP 가 막혔거나 Geyser 가 안 떴습니다")
        failed = True
    except Exception as exc:
        print(f"  ❌ 실패: {type(exc).__name__}: {exc}")
        failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
