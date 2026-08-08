#!/usr/bin/env python3
"""배포 전 BlockShip 런타임 텍스트의 굵은 포맷을 전수 차단한다."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


TEXT_EXTENSIONS = {".java", ".json", ".yml", ".yaml", ".sk"}
PATTERNS = [
    (re.compile(r"§[lL]"), "§l (섹션기호 볼드)"),
    (re.compile(r"\\u00a7[lL]", re.IGNORECASE), r"\u00a7l (유니코드 이스케이프 볼드)"),
    (re.compile(r"&[lL](?![a-zA-Z])"), "&l (앰퍼샌드 볼드)"),
    (re.compile(r"\bChatColor\.BOLD\b"), "ChatColor.BOLD (레거시 볼드)"),
    (re.compile(r"decorate\s*\(\s*TextDecoration\.BOLD"), "decorate(TextDecoration.BOLD)"),
    (re.compile(r"TextDecoration\.BOLD\s*,\s*true"), "TextDecoration.BOLD, true"),
]


def without_java_comments(source: str) -> str:
    """주석만 공백으로 바꿔 Javadoc 속 &l 예시를 런타임 코드로 오인하지 않는다."""
    out: list[str] = []
    index = 0
    state = "code"

    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""

        if state == "code":
            if char == "/" and next_char == "/":
                out.extend((" ", " "))
                index += 2
                state = "line_comment"
                continue
            if char == "/" and next_char == "*":
                out.extend((" ", " "))
                index += 2
                state = "block_comment"
                continue
            out.append(char)
            if char == '"':
                state = "string"
            elif char == "'":
                state = "char"
        elif state == "line_comment":
            out.append("\n" if char == "\n" else " ")
            if char == "\n":
                state = "code"
        elif state == "block_comment":
            if char == "*" and next_char == "/":
                out.extend((" ", " "))
                index += 2
                state = "code"
                continue
            out.append("\n" if char == "\n" else " ")
        else:
            out.append(char)
            if char == "\\" and index + 1 < len(source):
                out.append(source[index + 1])
                index += 2
                continue
            if (state == "string" and char == '"') or (state == "char" and char == "'"):
                state = "code"
        index += 1

    return "".join(out)


def scan_file(path: Path) -> list[tuple[int, str]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    source = without_java_comments(raw) if path.suffix == ".java" else raw
    findings: list[tuple[int, str]] = []
    for pattern, label in PATTERNS:
        for match in pattern.finditer(source):
            findings.append((source.count("\n", 0, match.start()) + 1, label))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="BlockShip 런타임 굵은 포맷 검사")
    parser.add_argument("source_root", type=Path, help="검사할 src/main 디렉터리")
    args = parser.parse_args()

    if not args.source_root.is_dir():
        print(f"❌ 볼드 검사 실패: 디렉터리가 없습니다: {args.source_root}", file=sys.stderr)
        return 2

    violations: list[tuple[Path, int, str]] = []
    for path in args.source_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS:
            violations.extend((path, line, label) for line, label in scan_file(path))

    if not violations:
        print("✓ 굵은 포맷 전수 검사 통과")
        return 0

    print("⛔ 배포 중단: 런타임 굵은 포맷이 발견되었습니다.", file=sys.stderr)
    for path, line, label in violations:
        print(f"  - {path}:{line}: {label}", file=sys.stderr)
    print("색코드는 유지하고 §l/&l 또는 Adventure bold 활성화만 제거하세요.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
