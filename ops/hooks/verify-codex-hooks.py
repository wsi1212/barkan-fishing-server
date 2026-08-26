#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""~/.codex/hooks.json 에 등록된 그대로 훅을 실행해 실제 차단되는지 확인한다.

Bash 히어독으로 만들면 안의 예시 명령을 훅이 실제 명령으로 보고 막는다 → Write 로 만들 것.
"""
import json
import os
import shlex
import subprocess
import sys

CFG = os.path.expanduser("~/.codex/hooks.json")
LIVE = "~/mcserver/plugins/BlockShip"
PROD = "ubuntu@168.107.8.107"

CASES = [
    # (이름, 명령, 차단돼야 하는가)
    ("dev regions.json -> prod (이번 사고)",
     "scp /dev/BlockShip/regions.json %s:%s/regions.json" % (PROD, LIVE), True),
    ("islands.json -> prod",
     "scp islands.json %s:%s/islands.json" % (PROD, LIVE), True),
    ("BlockShip 폴더 통째 rsync",
     "rsync -a /dev/BlockShip/ %s:%s/" % (PROD, LIVE), True),
    ("라이브 plugins/ 에 jar 직접 쓰기",
     "scp BlockShip-1.0.0-SNAPSHOT.jar %s:~/mcserver/plugins/" % PROD, True),
    ("실행중 리로드",
     "ssh %s 'rcon.py \"plugman rl BlockShip\"'" % PROD, True),
    ("정상: prod -> /tmp 로 받아오기",
     "scp %s:%s/regions.json /tmp/r.json" % (PROD, LIVE), False),
    ("정상: 정식 배포 스크립트",
     "~/deploy-blockship.sh", False),
    ("정상: staging 에 jar",
     "scp BlockShip.jar %s:~/mcserver/staging/" % PROD, False),
]


def bash_hooks():
    cfg = json.load(open(CFG))
    out = []
    for grp in cfg["hooks"].get("PreToolUse", []):
        if grp.get("matcher") == "Bash":
            for h in grp["hooks"]:
                out.append(h["command"])
    return out


def main():
    hooks = bash_hooks()
    print("등록된 Bash 훅 %d개" % len(hooks))
    for h in hooks:
        print("   ·", os.path.basename(shlex.split(h)[-1]))
    print()

    fail = 0
    for name, cmd, want_block in CASES:
        blocked_by = None
        for h in hooks:
            argv = shlex.split(h)
            p = subprocess.run(argv, input=json.dumps({"tool_input": {"command": cmd}}),
                               capture_output=True, text=True)
            if p.returncode == 2:
                blocked_by = os.path.basename(argv[-1])
                break
        ok = bool(blocked_by) == want_block
        mark = "  ✓ " if ok else "  ✗ FAIL "
        state = ("차단(%s)" % blocked_by) if blocked_by else "통과"
        print(mark + name + " → " + state)
        fail += 0 if ok else 1

    print()
    print("실패 %d건" % fail)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
