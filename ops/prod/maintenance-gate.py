#!/usr/bin/env python3
"""Minecraft maintenance responder used while Paper is restarting.

Paper continues to own TCP/25565.  During a restart, maintenance-gate-control
temporarily redirects new public connections to this process on 127.0.0.1:25566.
It speaks the small part of the Minecraft protocol needed for the multiplayer
list ping and for a login disconnect, so players receive a useful Korean
maintenance notice instead of a TCP ``Connection refused`` error.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import socket
import socketserver
import struct
import subprocess
import threading
import time


# REDIRECT preserves the primary address of the incoming interface rather than
# rewriting it to 127.0.0.1, so the listener must accept that local address.
# OCI exposes only TCP/25565; TCP/25566 is reachable solely through the local
# redirect while the gate is armed.
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 25566
DEFAULT_CONTROL = "/home/ubuntu/mcserver/scripts/maintenance-gate-control.sh"
DEFAULT_PROPERTIES = "/home/ubuntu/mcserver/server.properties"
DEFAULT_STATE = "/run/barkan-maintenance-gate/state"
MESSAGE = "서버 정기점검 중입니다\\n잠시 후 다시 시도해 주세요."


class ProtocolError(ValueError):
    """The peer did not send a complete, supported Minecraft packet."""


def recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ProtocolError("unexpected EOF")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_varint_sock(sock: socket.socket) -> int:
    value = 0
    for index in range(5):
        byte = recv_exact(sock, 1)[0]
        value |= (byte & 0x7F) << (7 * index)
        if not byte & 0x80:
            return value
    raise ProtocolError("VarInt is too large")


def read_varint_bytes(data: bytes, offset: int = 0) -> tuple[int, int]:
    value = 0
    for index in range(5):
        if offset >= len(data):
            raise ProtocolError("truncated VarInt")
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << (7 * index)
        if not byte & 0x80:
            return value, offset
    raise ProtocolError("VarInt is too large")


def write_varint(value: int) -> bytes:
    if value < 0:
        value &= 0xFFFFFFFF
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        encoded.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(encoded)


def read_packet(sock: socket.socket) -> tuple[int, bytes]:
    length = read_varint_sock(sock)
    if not 0 < length <= 1_048_576:
        raise ProtocolError(f"invalid packet length {length}")
    packet = recv_exact(sock, length)
    packet_id, offset = read_varint_bytes(packet)
    return packet_id, packet[offset:]


def send_packet(sock: socket.socket, packet_id: int, payload: bytes = b"") -> None:
    body = write_varint(packet_id) + payload
    sock.sendall(write_varint(len(body)) + body)


def write_string(value: str) -> bytes:
    data = value.encode("utf-8")
    return write_varint(len(data)) + data


def handshake_protocol(payload: bytes) -> tuple[int, int]:
    """Return (client protocol number, next state) from a Handshake packet."""
    protocol, offset = read_varint_bytes(payload)
    address_len, offset = read_varint_bytes(payload, offset)
    offset += address_len
    if offset + 2 > len(payload):
        raise ProtocolError("truncated handshake port")
    offset += 2
    next_state, _ = read_varint_bytes(payload, offset)
    return protocol, next_state


def status_payload(protocol: int) -> bytes:
    # Echoing the connecting client's protocol number prevents a misleading
    # "incompatible version" result in the multiplayer server list.
    response = {
        "version": {"name": "정기 점검 중", "protocol": protocol},
        "players": {"max": 0, "online": 0, "sample": []},
        "description": {"text": MESSAGE, "color": "yellow"},
        "enforcesSecureChat": False,
    }
    return write_string(json.dumps(response, ensure_ascii=False, separators=(",", ":")))


def legacy_status(sock: socket.socket) -> None:
    # Legacy 1.6-style ping. Modern clients use the regular status request,
    # but this gives old launchers a readable server-list entry as well.
    text = "§1\x00767\x00정기 점검 중\x000\x000"
    encoded = text.encode("utf-16-be")
    sock.sendall(b"\xff" + struct.pack(">H", len(text)) + encoded)


class GateHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        sock: socket.socket = self.request
        sock.settimeout(4)
        try:
            first = sock.recv(1, socket.MSG_PEEK)
            if first == b"\xfe":
                recv_exact(sock, 1)
                legacy_status(sock)
                return

            packet_id, payload = read_packet(sock)
            if packet_id != 0:
                raise ProtocolError("expected Handshake")
            protocol, next_state = handshake_protocol(payload)

            if next_state == 1:  # status request
                request_id, _ = read_packet(sock)
                if request_id != 0:
                    raise ProtocolError("expected status request")
                send_packet(sock, 0, status_payload(protocol))
                # The optional ping packet lets the client measure latency.
                try:
                    ping_id, ping_payload = read_packet(sock)
                    if ping_id == 1 and len(ping_payload) == 8:
                        send_packet(sock, 1, ping_payload)
                except (ProtocolError, OSError, socket.timeout):
                    pass
                return

            if next_state == 2:  # login start
                try:
                    read_packet(sock)
                except (ProtocolError, OSError, socket.timeout):
                    return
                reason = json.dumps({"text": MESSAGE, "color": "yellow"}, ensure_ascii=False)
                send_packet(sock, 0, write_string(reason))
                return

            raise ProtocolError(f"unsupported next state {next_state}")
        except (ProtocolError, OSError, socket.timeout):
            # Internet scanners and cancelled client handshakes are expected;
            # do not make the service log noisy while a restart is in progress.
            return


class ThreadedTcpServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def rcon_packet(request_id: int, packet_type: int, body: str) -> bytes:
    payload = struct.pack("<ii", request_id, packet_type) + body.encode("utf-8") + b"\x00\x00"
    return struct.pack("<i", len(payload)) + payload


def rcon_response(sock: socket.socket) -> tuple[int, int, str]:
    length = struct.unpack("<i", recv_exact(sock, 4))[0]
    if not 10 <= length <= 1_048_576:
        raise ProtocolError("invalid RCON response length")
    data = recv_exact(sock, length)
    request_id, packet_type = struct.unpack("<ii", data[:8])
    return request_id, packet_type, data[8:-2].decode("utf-8", "replace")


def paper_ready(properties_path: str) -> bool:
    """Paper is ready only once its own RCON responds, not merely when a port opens."""
    try:
        properties: dict[str, str] = {}
        with open(properties_path, encoding="utf-8") as props_file:
            for line in props_file:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    properties[key] = value
        password = properties.get("rcon.password", "")
        if not password:
            return False
        port = int(properties.get("rcon.port", "25575"))
        with socket.create_connection(("127.0.0.1", port), timeout=4) as rcon:
            rcon.settimeout(4)
            rcon.sendall(rcon_packet(1, 3, password))
            request_id, _, _ = rcon_response(rcon)
            if request_id == -1:
                return False
            rcon.sendall(rcon_packet(2, 2, "list"))
            request_id, _, _ = rcon_response(rcon)
            return request_id == 2
    except (OSError, ValueError, struct.error, ProtocolError):
        return False


def state_monitor(state_path: str, control_path: str, properties_path: str) -> None:
    """Release traffic only after one observed down->RCON-ready transition."""
    while True:
        try:
            with open(state_path, encoding="utf-8") as state_file:
                state = state_file.read().strip()
        except FileNotFoundError:
            state = ""
        except OSError:
            logging.exception("could not read maintenance state")
            time.sleep(2)
            continue

        if state == "arming":
            if not paper_ready(properties_path):
                try:
                    with open(state_path, "w", encoding="utf-8") as state_file:
                        state_file.write("down\n")
                except OSError:
                    logging.exception("could not mark Paper as down")
        elif state == "down" and paper_ready(properties_path):
            result = subprocess.run(
                [control_path, "disable"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
                check=False,
            )
            if result.returncode:
                logging.error("could not release maintenance gate: %s", result.stderr.strip())
            else:
                logging.info("Paper RCON is ready; maintenance gate released")
        time.sleep(2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Minecraft maintenance protocol responder")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--state", default=DEFAULT_STATE)
    parser.add_argument("--control", default=DEFAULT_CONTROL)
    parser.add_argument("--properties", default=DEFAULT_PROPERTIES)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [maintenance-gate] %(message)s")
    monitor = threading.Thread(
        target=state_monitor,
        args=(args.state, args.control, args.properties),
        name="maintenance-state-monitor",
        daemon=True,
    )
    monitor.start()
    with ThreadedTcpServer((args.host, args.port), GateHandler) as server:
        logging.info("listening on %s:%d", args.host, args.port)
        server.serve_forever(poll_interval=0.5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
