#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PreToolUse hook (matcher: Bash / mc_run_command) — 에이전트가 prod 를 재시작·정지하는 것을 차단.

★왜 훅인가: CLAUDE.md·AGENTS.md 텍스트만으로 막던 동안 에이전트가 그냥 무시하고
  `sudo systemctl restart mcserver` 를 때렸다(2026-09-02 auth.log 실측, 하루 6회).
  기계적 규칙은 문서가 아니라 훅으로 강제한다(feedback_hooks_over_claudemd_for_mechanical_rules).

★막지 않는 것 — 사람이 정한 «예약» 재시작:
  · prod cron 06:00 KST `nightly-restart.sh` (훅은 에이전트 도구호출만 본다. cron 은 안 지난다)
  · `crontab` 편집 — 스케줄 관리 자체는 허용한다. 즉시 재시작이 아니다.
  · `systemctl start mcserver` — inactive 복구 경로(CLAUDE.md 예외). restart/stop 만 막는다.
  · dev(맥) 재시작 — `dev-mc.sh` / `deploy-dev.sh` 는 prod 가 아니다.
  · PREVIEW=1 / DRY=1 미리보기.

stdin  : Claude Code / Codex hook JSON  /  exit 0 : 허용  /  exit 2 : 차단
"""
import json
import os
import re
import sys

# 실행이 아니라 «읽기»인 명령. 이 세그먼트 안에 위험 낱말이 있어도 그냥 문자열이다.
# (가드를 grep 조차 못 하게 만들면 우회를 강요하게 된다 — plugman 가드에서 배운 것)
READONLY = {
    "grep", "rg", "egrep", "fgrep", "cat", "bat", "sed", "awk", "head", "tail",
    "less", "more", "echo", "printf", "ls", "find", "diff", "cmp", "wc", "stat",
    "md5", "md5sum", "sha1sum", "sha256sum", "file", "git", "crontab",
    "journalctl", "systemctl-show", "column", "sort", "uniq", "cut", "tr",
}
# systemctl 은 조회 서브커맨드면 읽기다.
SYSTEMCTL_READONLY = re.compile(r"^\s*systemctl\s+(is-active|is-enabled|is-failed|show|status|cat|list-\S+)\b")

# ① 스크립트 이름은 «명령 위치»(세그먼트의 선두 실행파일)에서만 본다.
#    ★그냥 낱말로 찾으면 이름을 입에 올리는 것 자체가 막힌다:
#      for f in ops/deploy-blockship.sh …; do grep …   ← 목록에 있을 뿐인데 차단됐다(실측)
#    실제 실행은 항상 선두 토큰이므로 정밀도만 오르고 보호는 그대로다.
DENY_HEAD = {
    "nightly-restart.sh": "nightly-restart.sh 수동 실행 — 즉시 적용+재시작",
    "deploy-blockship.sh": "deploy-blockship.sh — 업로드 후 prod 를 바로 재시작한다",
    "deploy-all-prod.sh": "deploy-all-prod.sh — prod 재시작 포함",
    "deploy-jar.sh": "deploy-jar.sh — prod 재시작 포함",
    "resourcepack-restart.sh": "resourcepack-restart.sh — prod 재시작",
    "toggle-plugin-jar.sh": "toggle-plugin-jar.sh — prod 재시작 포함",
    "oneshot-guild-rename-gm.sh": "oneshot 스크립트 — prod 재시작 포함",
}
# 셸 인터프리터로 우회하는 형태(`bash ~/deploy-blockship.sh`)도 선두 다음 토큰까지 본다.
INTERPRETERS = {"bash", "sh", "zsh", "source", "."}

# ② 여러 토큰이 모여야 위험해지는 형태는 정규식으로. (rp-deploy 는 --restart 만, rollback 은 yes 만)
DENY = [
    (re.compile(r"(?<![\w-])systemctl\s+(?:--\S+\s+)*(restart|stop|kill)\s+mcserver(?![\w-])"),
     "systemctl restart/stop mcserver — prod 운영 중단"),
    (re.compile(r"(?<![\w-])rollback-jar\.sh\s+(?:yes|예)(?![\w-])"), "rollback-jar.sh yes — prod 재시작"),
    (re.compile(r"(?<![\w-])apply-betterhud-staging\.sh\s+--post(?![\w-])"), "BetterHud --post — prod 재시작"),
    (re.compile(r"(?<![\w-])rp-deploy\.sh\b[^|;&]*--restart(?![\w-])"), "rp-deploy.sh --restart — prod 재시작"),
    (re.compile(r"(?<![\w-])rcon\.py\s+[\"']?stop[\"']?\s*$"), "RCON stop — prod 정지"),
    (re.compile(r"send-keys\b[^|;&]*[\"']\s*stop\s*[\"']"), "tmux 콘솔에 stop 주입 — prod 정지"),
]
# 미리보기 모드는 실제로 재시작하지 않는다(스크립트가 restart 전에 exit).
PREVIEW = re.compile(r"(?<![\w-])(?:PREVIEW|DRY|DRY_RUN)\s*=\s*1(?![\w-])")
# 커밋 메시지·문서에 규칙을 적는 것은 실행이 아니다.
PROSE_ONLY = re.compile(r"^\s*git\s+(commit|tag|notes)\b")

# 히어독 «본문»은 파일에 쓰는 데이터지 명령줄이 아니다. 이 가드/문서/테스트에 규칙을
# 적으려면 본문에 금지 낱말이 당연히 들어간다 — 그걸 막으면 재발방지 문서를 못 쓴다.
#   cat/tee/python3 … <<EOF  → 본문 비움(데이터)
#   bash/sh/ssh      <<EOF  → 본문 유지(그건 실행된다)
#   git commit -F -  <<MSG   → 본문은 커밋 메시지다(재발방지 내용을 못 쓰면 안 된다)
HEREDOC_INERT = {"cat", "tee", "python3", "python", "perl", "ruby", "node", "jq", "patch", "git"}
HEREDOC_START = re.compile(r"""<<-?\s*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\1""")


def strip_heredocs(command):
    lines = command.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = HEREDOC_START.search(line)
        i += 1
        if not m:
            continue
        term = m.group(2)
        head, _ = strip_prefix(line)
        inert = head in HEREDOC_INERT
        while i < len(lines) and lines[i].strip() != term:
            if not inert:
                out.append(lines[i])
            i += 1
        if i < len(lines):
            i += 1  # 종료 마커 소모
    return "\n".join(out)


SPLIT = re.compile(r"&&|\|\||;|\n|(?<!\|)\|(?!\|)")
ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
QUOTED = re.compile(r"'((?:[^'])*)'|\"((?:[^\"\\]|\\.)*)\"", re.S)


PREFIXES = ("sudo", "env", "command", "exec", "nohup", "time")


def strip_prefix(segment):
    """환경변수 대입과 sudo/env 같은 접두어를 떼고, (선두 실행파일명, 나머지 명령) 반환."""
    toks = segment.split()
    i = 0
    while i < len(toks) and (ENV_ASSIGN.match(toks[i]) or toks[i] in PREFIXES):
        i += 1
    if i >= len(toks):
        return "", ""
    return os.path.basename(toks[i]), " ".join(toks[i:])


def scan(command, depth=0):
    """차단 사유를 돌려주거나, 문제없으면 None."""
    if depth > 3:
        return None
    for segment in SPLIT.split(command):
        seg = (segment or "").strip()
        if not seg:
            continue
        head, bare = strip_prefix(seg)
        if head in READONLY or SYSTEMCTL_READONLY.match(bare):
            continue
        if PREVIEW.search(seg):
            continue

        # 명령 위치의 스크립트 이름 (bash <script> 형태면 그 다음 토큰까지)
        toks = bare.split()
        for cand in (os.path.basename(t) for t in toks[:2] if t):
            if cand in DENY_HEAD and (cand == head or head in INTERPRETERS):
                return DENY_HEAD[cand]

        # ssh 'payload' / bash -c "payload" 안쪽도 같은 규칙으로 본다.
        # ★따온 payload 가 «읽기 명령»이면 그 구간을 직접검사에서 비운다 —
        #   ssh host 'grep "systemctl restart mcserver" f' 를 막으면 가드를 조사할 수조차 없다.
        direct = seg
        for m in QUOTED.finditer(seg):
            inner = m.group(1) if m.group(1) is not None else (m.group(2) or "")
            if len(inner) < 4:
                continue
            inner_head, inner_bare = strip_prefix(inner)
            if inner_head in READONLY or SYSTEMCTL_READONLY.match(inner_bare):
                direct = direct.replace(m.group(0), " ", 1)
                continue
            reason = scan(inner, depth + 1)
            if reason:
                return reason

        for pattern, why in DENY:
            if pattern.search(direct):
                return why
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    tool = data.get("tool_name") or ""
    tool_input = data.get("tool_input") or {}
    command = tool_input.get("command") or ""

    if tool and "Bash" not in tool:
        # MCP 콘솔 경로(mc_run_command 등): prod 콘솔에 stop 을 넣는 것만 본다.
        if re.match(r"^\s*/?stop\b", str(command), re.I):
            sys.stderr.write("⛔ prod 콘솔 stop 차단 — 서버를 멈추지 않는다.\n")
            return 2
        return 0

    if PROSE_ONLY.match(command):
        return 0

    reason = scan(strip_heredocs(command))
    if not reason:
        return 0

    sys.stderr.write(
        "⛔ prod 재시작·정지 차단: {}\n"
        "에이전트는 prod 를 재시작하지 않는다 (CLAUDE.md / AGENTS.md 절대 운영 안전 규칙).\n"
        "대신:\n"
        "  · 코드/JSON → ~/stage-blockship.sh 로 staging 에만 올린다 (06:00 KST 정기 재시작이 적용)\n"
        "  · 리소스팩 → ops/rp-deploy.sh prod (--restart 없이)\n"
        "  · 즉시 재시작이 정말 필요하면 사용자에게 물어보고, 사용자가 직접 실행한다\n"
        "  · prod 가 inactive 로 확인된 복구 상황이면 systemctl start 는 허용된다\n".format(reason)
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
