#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PreToolUse hook (matcher: Bash) — **가동 중 서버의 plugins/ 에 jar 직접 쓰기** 차단.

Claude Code / Codex 양쪽에서 같은 파일을 쓴다(중복 사본 금지 — 갈라지면 한쪽만 막힌다).

왜: 라이브 서버의 jar을 덮어쓰면 그 시점 이후 **처음 로드되는 클래스**가 전부
    NoClassDefFoundError가 된다. 이미 로드된 기능은 멀쩡하니 즉시 안 터지고,
    유저가 안 써본 기능부터 하나씩 죽는다 → "갑자기 온갖 게 다 안 됨".
    2026-08-03 prod 실사고: 18:05에 jar이 갈리고 20:55에
    `NoClassDefFoundError: com/blockship/region/WeatherManager$WeatherChoice`.
    plugman reload와 원인은 같지만 명령 문자열이 달라 기존 훅을 그냥 지나갔다.

차단 대상: scp/rsync/cp/mv/install/curl -o/tee 로 *.jar 을 다음 경로에 쓰는 것
  · prod  ~/mcserver/plugins/
  · dev   .../feather/.../servers/<id>/plugins/
허용: ~/mcserver/staging/ (데일리 유지보수가 재시작과 함께 적용하는 안전 경로)
      배포 스크립트 호출(~/deploy-*.sh, ~/stage-blockship.sh) — 스크립트 내부 scp는
      훅에 보이지 않고, 스크립트가 stop→교체→start 순서를 보장한다.

stdin : hook JSON  /  exit 0 = 허용  /  exit 2 = 차단
"""
import json
import re
import sys

# ★판정은 "목적지 경로"로 한다 — `.jar` 문자열 유무로 보면 `cp "$LOCAL_JAR" ".../plugins/"`
#   처럼 변수로 감싼 경우를 그냥 통과시킨다(실제로 그렇게 뚫렸다).
#   plugins/ **루트**에 뭔가를 쓰는 건 곧 jar 교체다. plugins/<플러그인폴더>/ 안은 데이터라 허용.
PLUGINS_ROOT = re.compile(
    r"(?:mcserver/plugins|player-server/[^\s'\"]*/plugins|servers/[0-9a-f-]{8,}/plugins)"
    r"/?$|"
    r"(?:mcserver/plugins|player-server/[^\s'\"]*/plugins|servers/[0-9a-f-]{8,}/plugins)"
    r"/[^/]*\.jar$",
    re.IGNORECASE,
)
# 마지막 인자가 목적지인 계열 (읽어오는 방향은 오탐이라 목적지만 본다)
DEST_LAST = re.compile(r"\b(?:scp|rsync|cp|mv|install|ditto)\b", re.IGNORECASE)
# 목적지가 플래그 뒤/아무 위치인 계열
DEST_ANY = re.compile(r"\b(?:curl|wget|tee|dd)\b", re.IGNORECASE)

# 안전 경로 / 정식 배포 경로
# ops/deploy-jar.sh = 이미 빌드된 jar 을 stop→교체→start 로 올리는 스크립트.
# 공용 트리가 다른 세션 때문에 안 빌드될 때 격리 worktree 산출물을 올리는 정식 경로다.
SAFE = re.compile(r"mcserver/staging|deploy-blockship\.sh|deploy-dev\.sh|stage-blockship\.sh"
                  r"|ops/deploy-jar\.sh|ops/deploy-worldwarp-dev\.sh",
                  re.IGNORECASE)

MSG = """⛔ 가동 중 서버의 plugins/ 에 jar 직접 쓰기 차단.

라이브 jar을 덮어쓰면 그 뒤 처음 로드되는 클래스가 전부 NoClassDefFoundError가 된다.
즉시 안 터지고 유저가 안 써본 기능부터 하나씩 죽어서 원인 추적이 지옥이다.
(2026-08-03 prod 실사고: 18:05 jar 교체 → 20:55 WeatherManager$WeatherChoice CNFE,
 /칭호·계단앉기 등 전방위 고장)

반드시 stop → jar 교체 → start 를 한 몸으로 처리하는 스크립트를 쓸 것:
  · dev        ~/deploy-dev.sh              (빌드+복사+dev-mc.sh restart)
  · prod 즉시   ~/deploy-blockship.sh        (JSON검증 → jar업로드 → systemctl restart)
  · prod 지연   ~/stage-blockship.sh         (staging/ 에만 두고 06:00 유지보수가 적용)

jar만 올리고 재시작을 나중에 하는 건 금지다. 중간 상태 자체가 고장이다.
정말 수동으로 해야 하면: 먼저 서버를 멈추고(stop) 그 다음 jar을 교체할 것.
"""


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not cmd or SAFE.search(cmd):
        return 0

    # `&&`·`;`·파이프로 이어진 각 절을 따로 본다 (한 절만 위반해도 차단)
    for part in re.split(r"&&|\|\||[;|]|\$\(|`", cmd):
        toks = [t.strip("'\"") for t in part.split() if t.strip("'\"")]
        if not toks:
            continue
        hit = []
        if DEST_LAST.search(part):
            hit.append(toks[-1])
        if DEST_ANY.search(part):
            hit.extend(toks)
        if any(PLUGINS_ROOT.search(t) for t in hit):
            sys.stderr.write(MSG)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
