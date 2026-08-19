#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PreToolUse hook (matcher: Bash) — plugman reload 차단.

BlockShip은 라이브 서버에서 plugman reload/실행중 jar 덮어쓰기 시 lazy-load
CNFE로 부분 고장(클래스로더 손상)을 낸다 (CLAUDE.md 「BlockShip Java 플러그인」
섹션, feedback_blockship_no_plugman_reload 메모리). 항상 stop → jar 교체 → start
순서(풀 재시작)를 강제한다.

stdin  : Claude Code hook JSON  /  exit 0 : 허용  /  exit 2 : 차단(재시도 유도)
"""
import sys
import json
import re

# ★2026-08-20 정밀도 수정 — 예전 패턴은 `\bplugman\b.*\breload\b` + DOTALL 이라 두 낱말이
#   명령 어디에 있든 걸렸다. 그래서 **이 파일 이름만 나와도** 차단됐다:
#     grep ... guard-plugman-reload.py        → 차단(가드를 읽을 수조차 없다)
#     git commit -m "...guard-plugman-reload" → 차단(재발방지 내용을 커밋에 못 쓴다)
#   우회를 강요하는 가드는 안 지켜지므로, «실제 실행»만 잡도록 조인다:
#   ① 두 낱말이 공백으로 «붙어» 있어야 한다(명령 형태). 명령 전체를 훑지 않는다.
#   ② 하이픈/문자로 이어진 경우는 제외 → 파일명 plugman-reload 는 안 걸린다.
#   rcon·tmux send-keys·콘솔 파이프 같은 실제 실행 경로는 전부 이 형태를 지나므로 보호는 유지된다.
PATTERN = re.compile(
    r"(?<![\w-])plugman\s+(?:reload|rl)(?![\w-])"
    r"|(?<![\w-])reload\s+plugman(?![\w-])",
    re.IGNORECASE,
)
# 커밋 메시지·태그 본문은 실행이 아니다. 이 가드의 존재 이유를 문서·커밋에 적을 수 있어야 한다.
PROSE_ONLY = re.compile(r"^\s*git\s+(commit|tag|notes)\b")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    command = (data.get("tool_input") or {}).get("command") or ""
    if PROSE_ONLY.match(command):
        return 0
    if not PATTERN.search(command):
        return 0

    sys.stderr.write(
        "⛔ plugman reload 차단: BlockShip은 실행 중 리로드/jar 덮어쓰기 시 "
        "lazy-load CNFE로 부분 고장이 남 (클래스로더 손상, 재발방지 규칙).\n"
        "대신 stop → jar 교체 → start 순서로 서버 풀 재시작할 것:\n"
        "  · dev: ~/deploy-dev.sh (빌드+복사+dev-mc.sh restart 자동)\n"
        "  · prod: ~/deploy-blockship.sh (즉시배포) 또는 ~/stage-blockship.sh (다음 데일리 유지보수 때 자동적용)\n"
        "재시작은 모아서 한 번에, 매번 사용자 허락 받고 진행.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
