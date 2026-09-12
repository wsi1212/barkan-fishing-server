#!/usr/bin/env python3
"""Configure one Paper backend for Velocity modern forwarding without replacing unrelated settings."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import tempfile
import time


PROPERTY_VALUES = {
    "online-mode": "false",
    "server-ip": "127.0.0.1",
}


def update_properties(text: str, port: int) -> str:
    wanted = dict(PROPERTY_VALUES, **{"server-port": str(port)})
    found: set[str] = set()
    output: list[str] = []
    for line in text.splitlines():
        key = line.split("=", 1)[0] if "=" in line and not line.startswith("#") else ""
        if key in wanted:
            output.append(f"{key}={wanted[key]}")
            found.add(key)
        else:
            output.append(line)
    for key, value in wanted.items():
        if key not in found:
            output.append(f"{key}={value}")
    return "\n".join(output) + "\n"


def update_paper_global(text: str, secret: str) -> str:
    lines = text.splitlines()
    proxies = next((i for i, line in enumerate(lines) if line == "proxies:"), None)
    if proxies is None:
        if lines and lines[-1]:
            lines.append("")
        lines.extend([
            "proxies:",
            "  velocity:",
            "    enabled: true",
            "    online-mode: true",
            f"    secret: '{secret}'",
        ])
        return "\n".join(lines) + "\n"

    section_end = len(lines)
    for index in range(proxies + 1, len(lines)):
        if lines[index] and not lines[index].startswith(" "):
            section_end = index
            break

    velocity = next((i for i in range(proxies + 1, section_end)
                     if lines[i] == "  velocity:"), None)
    if velocity is None:
        lines[section_end:section_end] = [
            "  velocity:",
            "    enabled: true",
            "    online-mode: true",
            f"    secret: '{secret}'",
        ]
        return "\n".join(lines) + "\n"

    velocity_end = section_end
    for index in range(velocity + 1, section_end):
        if lines[index] and not lines[index].startswith("    "):
            velocity_end = index
            break

    values = {
        "enabled": "true",
        "online-mode": "true",
        "secret": f"'{secret}'",
    }
    found: set[str] = set()
    for index in range(velocity + 1, velocity_end):
        stripped = lines[index].strip()
        key = stripped.split(":", 1)[0] if ":" in stripped else ""
        if key in values:
            lines[index] = f"    {key}: {values[key]}"
            found.add(key)
    additions = [f"    {key}: {value}" for key, value in values.items() if key not in found]
    lines[velocity_end:velocity_end] = additions
    return "\n".join(lines) + "\n"


def update_spigot(text: str) -> str:
    lines = text.splitlines()
    settings = next((i for i, line in enumerate(lines) if line == "settings:"), None)
    if settings is None:
        if lines and lines[-1]:
            lines.append("")
        lines.extend(["settings:", "  bungeecord: false"])
        return "\n".join(lines) + "\n"
    end = len(lines)
    for index in range(settings + 1, len(lines)):
        if lines[index] and not lines[index].startswith(" "):
            end = index
            break
    for index in range(settings + 1, end):
        if lines[index].strip().startswith("bungeecord:"):
            lines[index] = "  bungeecord: false"
            break
    else:
        lines.insert(end, "  bungeecord: false")
    return "\n".join(lines) + "\n"


def atomic_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
            temporary.write(value)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path, help="Paper server root")
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--secret-file", required=True, type=Path)
    parser.add_argument("--apply", action="store_true", help="write changes; default is a check")
    args = parser.parse_args()

    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    secret = args.secret_file.read_text(encoding="utf-8").strip()
    if len(secret) < 32 or any(char.isspace() for char in secret):
        raise SystemExit("forwarding secret is missing or invalid")

    paths = {
        args.root / "server.properties": lambda value: update_properties(value, args.port),
        args.root / "config/paper-global.yml": lambda value: update_paper_global(value, secret),
        args.root / "spigot.yml": update_spigot,
    }
    changed: dict[Path, str] = {}
    for path, transform in paths.items():
        if not path.is_file():
            raise SystemExit(f"missing backend configuration: {path}")
        current = path.read_text(encoding="utf-8")
        updated = transform(current)
        if current != updated:
            changed[path] = updated

    if not args.apply:
        for path in changed:
            print(f"NEEDS_CHANGE {path}")
        return 1 if changed else 0

    stamp = time.strftime("%Y%m%d-%H%M%S")
    for path, updated in changed.items():
        backup = path.with_name(path.name + f".pre-velocity-{stamp}")
        shutil.copy2(path, backup)
        atomic_write(path, updated)
        print(f"UPDATED {path} (backup {backup.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
