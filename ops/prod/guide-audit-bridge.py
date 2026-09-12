#!/usr/bin/env python3
"""Temporarily forward real guide admin actions while the plugin webhook is disabled.

The old live JAR can falsely audit public commands from Paper's async command-tree
builder.  This bridge only accepts GuideAudit lines emitted on the main server
thread, applies the same public-command exclusions as the fixed JAR, and exits as
soon as the normal plugin webhook is restored.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path.home() / "mcserver"
LATEST_LOG = ROOT / "logs" / "latest.log"
CONFIG = ROOT / "plugins" / "BlockShip" / "config.yml"
RESTORE_MARKER = ROOT / "scripts" / ".guide-webhook-restore-once"
LOCK_FILE = ROOT / "scripts" / ".guide-audit-bridge.lock"
MAX_BATCH = 15
FLUSH_SECONDS = 2.0

LINE_RE = re.compile(
    r"^\[(?P<time>\d{2}:\d{2}:\d{2})\] "
    r"\[Server thread/INFO\]: \[BlockShip\] \[Guide\] "
    r"(?P<player>\S+?)(?P<denied> 차단됨)? → (?P<command>/.*)$"
)
WEBHOOK_RE = re.compile(r"^\s*guide-webhook\s*:\s*(.*)$", re.MULTILINE)

SILENT_READ_COMMANDS = {"도감", "ehrka", "ㄷㄱ", "er"}
AUDIT_FREE_PUBLIC_COMMANDS = {
    "귣", "rnlt", "ㄱ", "r", "귣말", "w", "msg", "tell", "whisper",
    "채팅", "coxld", "ㅊㅌ", "cx",
    "길드", "rlfem", "ㄱㄷ", "re",
    "스폰", "넥주", "tmvhs", "spawn", "ㅅㅍ", "tv",
}
ISLAND_COMMANDS = {"섬", "tja", "개인섬", "rodlstja", "ㅅ", "t", "is", "island"}
ISLAND_ADMIN_COMMANDS = {"초기화", "템플릿저장", "템플릿붙이기"}


def log(message: str) -> None:
    print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), message, flush=True)


def configured_webhook() -> bool:
    try:
        match = WEBHOOK_RE.search(CONFIG.read_text(encoding="utf-8"))
    except OSError:
        return False
    if not match:
        return False
    return bool(match.group(1).strip().strip("\"'"))


def bridge_enabled() -> bool:
    try:
        return RESTORE_MARKER.stat().st_size > 0 and not configured_webhook()
    except OSError:
        return False


def webhook_url() -> str:
    url = RESTORE_MARKER.read_text(encoding="utf-8").splitlines()[0].strip()
    if not url.startswith((
        "https://discord.com/api/webhooks/",
        "https://discordapp.com/api/webhooks/",
    )):
        raise ValueError("invalid Discord webhook URL in restore marker")
    return url


def command_tokens(command: str) -> list[str]:
    raw = command[1:] if command.startswith("/") else command
    tokens = raw.strip().lower().split()
    if tokens and ":" in tokens[0]:
        tokens[0] = tokens[0].split(":", 1)[1]
    return tokens


def should_forward(command: str) -> bool:
    tokens = command_tokens(command)
    if not tokens:
        return False
    root = tokens[0]
    if root in SILENT_READ_COMMANDS:
        # GUI opening/reading is silent; taking an item is an explicit audited action.
        return root in {"도감", "ehrka", "ㄷㄱ", "er"} and tokens[1:3] == ["아이템", "지급"]
    if root in AUDIT_FREE_PUBLIC_COMMANDS:
        return False
    if root in ISLAND_COMMANDS:
        return len(tokens) >= 2 and tokens[1] in ISLAND_ADMIN_COMMANDS
    return True


def markdown_escape(value: str) -> str:
    return re.sub(r"([*_~`|\\])", r"\\\1", value)


def parse_line(raw: str) -> str | None:
    match = LINE_RE.match(raw.rstrip("\r\n"))
    if not match:
        return None
    command = match.group("command").replace("`", "'")[:160]
    if not should_forward(command):
        return None
    player = markdown_escape(match.group("player"))
    stamp = match.group("time")
    if match.group("denied"):
        return f"`{stamp}` 🚫 **{player}** 님이 `{command}` 를 시도했으나 차단됐습니다."
    return f"`{stamp}` **{player}** 님이 `{command}` 명령어를 실행했습니다."


def post_batch(lines: list[str]) -> bool:
    payload = json.dumps({
        "embeds": [{
            "title": "🧭 가이드 명령 사용",
            "description": "\n".join(lines),
            "color": 0xABF2D7,
            "footer": {"text": "바르칸 열도 · 가이드 감사 로그 (임시 필터)"},
        }],
    }, ensure_ascii=False).encode("utf-8")
    request = Request(
        webhook_url(), data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "BlockShip-guide-audit-bridge/1"},
        method="POST",
    )
    for attempt in range(2):
        try:
            with urlopen(request, timeout=10) as response:
                if response.status in (200, 204):
                    return True
        except HTTPError as error:
            if error.code == 429 and attempt == 0:
                try:
                    retry = float(json.loads(error.read().decode("utf-8")).get("retry_after", 1.0))
                except Exception:
                    retry = 1.0
                time.sleep(min(max(retry, 0.25), 10.0))
                continue
            log(f"Discord HTTP error: {error.code}")
        except (OSError, URLError, ValueError) as error:
            log(f"Discord send error: {error}")
        break
    return False


def flush(queue: list[str]) -> None:
    while queue and bridge_enabled():
        batch = queue[:MAX_BATCH]
        if not post_batch(batch):
            return
        del queue[:MAX_BATCH]
        log(f"forwarded {len(batch)} guide audit event(s)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backfill-after", metavar="HH:MM:SS")
    args = parser.parse_args()

    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock = LOCK_FILE.open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("another bridge is already running")
        return 0

    if not bridge_enabled():
        log("bridge not armed; exiting")
        return 0

    queue: list[str] = []
    last_flush = time.monotonic()
    handle = LATEST_LOG.open(encoding="utf-8", errors="replace")
    inode = os.fstat(handle.fileno()).st_ino

    if args.backfill_after:
        for raw in handle:
            match = LINE_RE.match(raw)
            if match and match.group("time") >= args.backfill_after:
                event = parse_line(raw)
                if event:
                    queue.append(event)
        flush(queue)
    else:
        handle.seek(0, os.SEEK_END)

    log("temporary guide audit bridge started")
    buffer = ""
    while bridge_enabled():
        chunk = handle.read()
        if chunk:
            buffer += chunk
            complete = buffer.split("\n")
            buffer = complete.pop()
            for raw in complete:
                event = parse_line(raw)
                if event:
                    queue.append(event)
        else:
            try:
                current = LATEST_LOG.stat()
                if current.st_ino != inode or current.st_size < handle.tell():
                    handle.close()
                    handle = LATEST_LOG.open(encoding="utf-8", errors="replace")
                    inode = os.fstat(handle.fileno()).st_ino
                    buffer = ""
            except OSError:
                pass
            time.sleep(0.25)

        now = time.monotonic()
        if queue and (len(queue) >= MAX_BATCH or now - last_flush >= FLUSH_SECONDS):
            flush(queue)
            last_flush = now

    flush(queue)
    handle.close()
    log("normal plugin webhook restored or bridge disarmed; exiting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
