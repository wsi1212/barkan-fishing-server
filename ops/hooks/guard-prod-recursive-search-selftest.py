#!/usr/bin/env python3
"""guard-prod-recursive-search.py 회귀 검산."""
import json
import os
import subprocess
import sys

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guard-prod-recursive-search.py")

CASES = [
    ("차단: 실제 사고 grep", "ssh ubuntu@168.107.8.107 'grep -R needle ~/mcserver/scripts /home/ubuntu'", 2),
    ("차단: rg 홈 전체", "ssh ubuntu@168.107.8.107 'rg --files /home/ubuntu'", 2),
    ("차단: 깊은 find", "ssh ubuntu@168.107.8.107 'find /home/ubuntu -maxdepth 4 -type f'", 2),
    ("차단: 무제한 find", "ssh ubuntu@168.107.8.107 'find $HOME -type f'", 2),
    ("통과: prod 로그만", "ssh ubuntu@168.107.8.107 'grep -R error ~/mcserver/logs'", 0),
    ("통과: 얕은 홈 find", "ssh ubuntu@168.107.8.107 'find /home/ubuntu -maxdepth 2 -type f'", 0),
    ("통과: 로컬 소스 검색", "rg -n recursive ops/hooks", 0),
]

failed = []
for name, command, expected in CASES:
    result = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
        text=True,
        capture_output=True,
    )
    if result.returncode != expected:
        failed.append(f"{name}: expected {expected}, got {result.returncode}: {result.stderr.strip()}")

if failed:
    print("\n".join(failed), file=sys.stderr)
    raise SystemExit(1)
print(f"guard-prod-recursive-search selftest: {len(CASES)} cases passed")
