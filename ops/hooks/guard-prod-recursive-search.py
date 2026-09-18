#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse(Bash): prod 홈 전체를 훑는 재귀 검색을 차단한다.

2026-09-18 사고: 원격 점검 명령의 ``grep -R ... /home/ubuntu`` 가 21GB를
읽으며 Oracle 볼륨을 84% I/O busy 상태로 만들었다. 그 동안 월드 청크 I/O가
75~134ms까지 밀려 TPS가 급락했다.

프로젝트/로그처럼 범위가 명확한 경로의 grep/find는 허용한다. 차단 대상은
prod SSH 명령 안에서 홈 전체(``/home/ubuntu``, ``$HOME``, ``~``)를 재귀로
훑는 grep/rg 및 깊이 3 이상(또는 무제한) find다.
"""
import json
import re
import sys

PROD = re.compile(r"(?:ubuntu@168\.107\.8\.107|168\.107\.8\.107|minecraft-server)")
HOME_WIDE = r"(?:/home/ubuntu/?|\$HOME/?|~/?)(?=\s|$|['\"])"
RECURSIVE_GREP = re.compile(
    r"\b(?:grep|egrep|fgrep|rg|ripgrep)\b[^|;&\n]*(?:--recursive\b|--files\b|-[-A-Za-z]*[rR][-A-Za-z]*)",
    re.IGNORECASE,
)
FIND_HOME = re.compile(r"\bfind\s+" + HOME_WIDE, re.IGNORECASE)
MAXDEPTH = re.compile(r"(?:^|\s)-maxdepth\s+(\d+)")


def reason(command: str) -> str | None:
    if not PROD.search(command):
        return None

    # grep/rg 자체가 재귀 모드여야 하며, 그 뒤 명령 세그먼트에 홈 전체가 있어야 한다.
    for segment in re.split(r"(?:&&|\|\||;|\n)", command):
        if RECURSIVE_GREP.search(segment) and re.search(HOME_WIDE, segment):
            return "prod 홈 전체 재귀 grep/rg"

        if FIND_HOME.search(segment):
            depth = MAXDEPTH.search(segment)
            if depth is None or int(depth.group(1)) >= 3:
                return "prod 홈 전체/깊은 find"
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    command = str((payload.get("tool_input") or {}).get("command") or "")
    hit = reason(command)
    if not hit:
        return 0

    sys.stderr.write(
        "⛔ {} 차단: 운영 서버 홈 디렉터리를 재귀 검색하면 월드 청크 I/O와 충돌해 "
        "실제 플레이 렉을 만든다.\\n"
        "대신 대상 디렉터리를 좁혀 검색한다 (예: ~/mcserver/logs, ~/mcserver/scripts).\\n"
        "2026-09-18: /home/ubuntu 재귀 grep가 21GB를 읽어 디스크 사용률 84%, "
        "읽기 지연 75~134ms, TPS 급락을 유발했다.\\n".format(hit)
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
