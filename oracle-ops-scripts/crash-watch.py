#!/usr/bin/env python3
# =====================================================================
# 바르칸 prod 클라이언트 크래시 자동 감지 — "접속 직후 급끊김" 패턴 탐지
#   서버는 클라 크래시의 진짜 원인(DecoderException 등)을 모른다 — 그건 유저 로컬
#   disconnect-*.txt 에만 있음. 대신 "접속 후 N초 이내 끊김"을 크래시 의심 신호로 보고
#   자동 알림 → 유저가 매번 수동 제보 안 해도 우리가 먼저 알아챈다.
#   cron 2분마다 실행. 상태(마지막 처리 오프셋/접속시각/알림쿨다운)는 파일에 영속.
# =====================================================================
import json, os, re, subprocess, sys, time

HOME = os.path.expanduser("~")
DIR = f"{HOME}/mcserver/scripts"
LOG = os.environ.get("CW_LOG", f"{HOME}/mcserver/logs/latest.log")
STATE_FILE = os.environ.get("CW_STATE", f"{DIR}/.crash-watch-state.json")
WEBHOOK_FILE = os.environ.get("CW_WEBHOOK", f"{DIR}/discord-webhook.url")
LABEL = "[바르칸 prod]"
FAST_THRESHOLD = int(os.environ.get("CW_THRESHOLD", "15"))  # 초 — 접속 후 이 안에 끊기면 크래시 의심
COOLDOWN = int(os.environ.get("CW_COOLDOWN", "600"))        # 초 — 같은 플레이어 재알림 최소 간격

JOIN_RE = re.compile(r"^\[(\d{2}):(\d{2}):(\d{2})\].*: (\S+)\[.*logged in with entity id \d+ at \(\[?([^\],]+)\]?[, ]*([-\d.]+)[, ]*([-\d.]+)[, ]*([-\d.]+)\)")
DISC_RE = re.compile(r"^\[(\d{2}):(\d{2}):(\d{2})\].*: (\S+) lost connection: (.+)$")


def hms_to_epoch(h, m, s, base):
    # 로그엔 날짜가 없어 오늘 날짜 기준으로 재구성(자정 넘김 등 극단 케이스는 무시 — 알림 용도로 충분).
    t = time.localtime(base)
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, int(h), int(m), int(s), 0, 0, -1))


def load(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


def notify(msg):
    if not os.path.exists(WEBHOOK_FILE) or os.path.getsize(WEBHOOK_FILE) == 0:
        return
    url = open(WEBHOOK_FILE).read().strip()
    payload = json.dumps({"content": msg})
    try:
        subprocess.run(
            ["curl", "-sf", "-m", "10", "-H", "Content-Type: application/json", "-d", payload, url],
            capture_output=True, timeout=15,
        )
    except Exception:
        pass


def main():
    if not os.path.exists(LOG):
        return
    state = load(STATE_FILE, {"offset": 0, "last_join": {}, "last_alert": {}})
    cur_size = os.path.getsize(LOG)
    if state["offset"] > cur_size:  # 로그 로테이션됨(재시작 등) → 처음부터
        state["offset"] = 0

    with open(LOG, "rb") as f:
        f.seek(state["offset"])
        chunk = f.read().decode("utf8", "replace")
    state["offset"] = cur_size

    now = time.time()
    for line in chunk.splitlines():
        jm = JOIN_RE.match(line)
        if jm:
            h, m, s, name, world, x, y, z = jm.groups()
            state["last_join"][name] = {
                "t": hms_to_epoch(h, m, s, now),
                "loc": f"{world} ({float(x):.0f},{float(y):.0f},{float(z):.0f})",
            }
            continue
        dm = DISC_RE.match(line)
        if dm:
            h, m, s, name, reason = dm.groups()
            disc_t = hms_to_epoch(h, m, s, now)
            j = state["last_join"].get(name)
            if not j:
                continue
            elapsed = disc_t - j["t"]
            if 0 <= elapsed <= FAST_THRESHOLD:
                last_alert = state["last_alert"].get(name, 0)
                if now - last_alert >= COOLDOWN:
                    notify(
                        f"{LABEL} ⚡ 빠른 접속끊김 감지: {name} — 접속 {elapsed:.0f}초 만에 끊김"
                        f" (클라 크래시 의심, 위치 {j['loc']}). 재현되면 클라 disconnect 로그 확인 요청."
                    )
                    state["last_alert"][name] = now

    json.dump(state, open(STATE_FILE, "w"))


if __name__ == "__main__":
    main()
