#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guard-prod-restart.py 검산 — 차단해야 하는 것과 통과해야 하는 것을 둘 다 본다.

거짓양성(읽기·조회·dev·cron 편집이 막히는 것)이 거짓음성보다 위험하다:
우회를 강요하는 가드는 결국 껀 채로 방치된다.
"""
import json
import subprocess
import sys
import os

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guard-prod-restart.py")
SSH = "ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 "

BLOCK = [
    "sudo systemctl restart mcserver",
    "systemctl restart mcserver",
    SSH + "'sudo systemctl restart mcserver'",
    SSH + '"sudo systemctl stop mcserver"',
    "~/deploy-blockship.sh",
    "cd /Users/user/development/blockship-plugin && ./gradlew build && ~/deploy-blockship.sh",
    SSH + "'~/mcserver/scripts/nightly-restart.sh --now'",
    SSH + "'NOW=1 ~/mcserver/scripts/nightly-restart.sh'",
    "ops/rp-deploy.sh prod --restart",
    SSH + "'~/mcserver/scripts/rollback-jar.sh yes'",
    SSH + "'~/mcserver/scripts/apply-betterhud-staging.sh --post'",
    SSH + "'~/mcserver/scripts/rcon.py stop'",
    SSH + "\"tmux send-keys -t mc 'stop' Enter\"",
    "ops/deploy-all-prod.sh",
]
ALLOW = [
    # 조회·읽기
    SSH + "'systemctl is-active mcserver'",
    SSH + "'sudo systemctl show mcserver -p ExecMainStartTimestamp --value'",
    SSH + "'grep -n \"systemctl restart mcserver\" ~/mcserver/scripts/*.sh'",
    "grep -rn 'deploy-blockship.sh' CLAUDE.md",
    "git show 34381671 -- ops/nightly-restart.sh",
    'git commit -m "운영 안전: nightly-restart.sh 재개"',
    # 예약·스케줄 관리
    SSH + "'crontab -l | grep nightly'",
    SSH + "'crontab /tmp/ct.new'",
    # 미리보기
    SSH + "'PREVIEW=1 ~/mcserver/scripts/nightly-restart.sh'",
    # 복구용 start 는 허용
    SSH + "'sudo systemctl start mcserver'",
    # dev(맥)는 prod 가 아니다
    "~/dev-mc.sh restart",
    "~/deploy-dev.sh",
    # staging 경로는 재시작 안 함
    "~/stage-blockship.sh",
    "ops/rp-deploy.sh prod",
    # 히어독 본문은 «파일에 쓰는 데이터»다 — 이 가드와 문서 자체를 쓸 수 있어야 한다
    "cat > /tmp/doc.md <<'EOF'\nsudo systemctl restart mcserver 는 금지다\nEOF",
    "python3 - <<'PY'\nprint('~/deploy-blockship.sh 는 차단된다')\nPY",
    "git add -A && git commit -F - <<'MSG'\n운영: nightly-restart.sh 재개\nsudo systemctl restart mcserver 는 여전히 금지\nMSG",
]
# 반대로 셸에 먹이는 히어독은 «실행»이므로 본문도 검사한다.
BLOCK_HEREDOC = [
    "ssh host <<'EOF'\nsudo systemctl restart mcserver\nEOF",
    "bash <<EOF\nsudo systemctl stop mcserver\nEOF",
]


def verdict(command, tool="Bash"):
    payload = json.dumps({"tool_name": tool, "tool_input": {"command": command}})
    r = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True)
    return r.returncode, r.stderr.strip()


def main():
    fails = []
    for c in BLOCK + BLOCK_HEREDOC:
        code, _ = verdict(c)
        if code != 2:
            fails.append("차단 실패(거짓음성): " + c)
    for c in ALLOW:
        code, err = verdict(c)
        if code != 0:
            fails.append("오차단(거짓양성): " + c + "  ← " + err.splitlines()[0] if err else c)
    # MCP 콘솔 경로
    if verdict("stop", "mcp__minecraft-ai-builder__mc_run_command")[0] != 2:
        fails.append("차단 실패: MCP 콘솔 stop")
    if verdict("time set day", "mcp__minecraft-ai-builder__mc_run_command")[0] != 0:
        fails.append("오차단: MCP 일반 명령")

    for f in fails:
        print("✗ " + f)
    total = len(BLOCK) + len(BLOCK_HEREDOC) + len(ALLOW) + 2
    print("{}/{} 통과".format(total - len(fails), total))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
