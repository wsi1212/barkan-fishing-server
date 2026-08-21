#!/usr/bin/env python3
# =====================================================================
# 바르칸 prod 클라이언트 크래시 감지 — "접속 직후 급끊김" 패턴 탐지
#   서버는 클라 크래시의 진짜 원인(DecoderException 등)을 모른다 — 그건 유저 로컬
#   disconnect-*.txt 에만 있음. 대신 "접속 후 N초 이내 끊김"을 크래시 의심 신호로 보고
#   기록할 수 있다. 다만 빠른 끊김의 Discord 알림과 패킷 첨부는 2026-08-22부터
#   비활성화했다. cron 2분마다 실행하며 상태(마지막 처리 오프셋/접속시각)는 파일에 영속.
# =====================================================================
import json, os, re, subprocess, sys, time

HOME = os.path.expanduser("~")
DIR = f"{HOME}/mcserver/scripts"
LOG = os.environ.get("CW_LOG", f"{HOME}/mcserver/logs/latest.log")
STATE_FILE = os.environ.get("CW_STATE", f"{DIR}/.crash-watch-state.json")
WEBHOOK_FILE = os.environ.get("CW_WEBHOOK", f"{DIR}/discord-webhook.url")
# PacketBlackbox(Java)가 급끊김 시 남기는 패킷 이력 덤프 — 여기서 찾아 Discord에 첨부 전송.
DUMP_DIR = os.environ.get("CW_DUMPDIR", f"{HOME}/mcserver/plugins/BlockShip/packet-blackbox")
LABEL = "[바르칸 prod]"
FAST_THRESHOLD = int(os.environ.get("CW_THRESHOLD", "15"))  # 초 — 접속 후 이 안에 끊기면 크래시 의심
COOLDOWN = int(os.environ.get("CW_COOLDOWN", "600"))        # 초 — 같은 플레이어 재알림 최소 간격
DUMP_MATCH_WINDOW = 60                                       # 초 — 덤프 파일명 타임스탬프 매칭 허용오차
# 의미 없는 "접속 직후 퇴장" 노이즈를 Discord에 보내지 않는다.
# 로컬 로그/패킷 덤프 수집 코드는 남겨 두되, 이 값이 False인 동안에는
# 빠른 끊김에 대한 웹훅 호출과 패킷 파일 첨부가 절대 실행되지 않는다.
FAST_DISCONNECT_ALERTS = False

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


def notify(msg, file_path=None):
    if not os.path.exists(WEBHOOK_FILE) or os.path.getsize(WEBHOOK_FILE) == 0:
        return
    url = open(WEBHOOK_FILE).read().strip()
    try:
        if file_path and os.path.exists(file_path):
            # 파일 첨부는 payload_json + file 필드로 멀티파트 전송(JSON-only curl -d 로는 첨부 불가).
            subprocess.run(
                ["curl", "-sf", "-m", "20",
                 "-F", f"payload_json={json.dumps({'content': msg})}",
                 "-F", f"file=@{file_path}", url],
                capture_output=True, timeout=25,
            )
        else:
            payload = json.dumps({"content": msg})
            subprocess.run(
                ["curl", "-sf", "-m", "10", "-H", "Content-Type: application/json", "-d", payload, url],
                capture_output=True, timeout=15,
            )
    except Exception:
        pass


def find_dump(name, around_epoch):
    """PacketBlackbox가 남긴 '{name}-{epochMillis}.txt' 덤프 중 around_epoch에 가장 가까운 것을 찾는다."""
    if not os.path.isdir(DUMP_DIR):
        return None
    prefix = f"{name}-"
    best, best_diff = None, None
    for fn in os.listdir(DUMP_DIR):
        if not fn.startswith(prefix) or not fn.endswith(".txt"):
            continue
        try:
            ms = int(fn[len(prefix):-4])
        except ValueError:
            continue
        diff = abs(ms / 1000.0 - around_epoch)
        if diff <= DUMP_MATCH_WINDOW and (best_diff is None or diff < best_diff):
            best, best_diff = fn, diff
    return os.path.join(DUMP_DIR, best) if best else None


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
                if not FAST_DISCONNECT_ALERTS:
                    continue
                last_alert = state["last_alert"].get(name, 0)
                if now - last_alert >= COOLDOWN:
                    dump = find_dump(name, disc_t)
                    msg = (
                        f"{LABEL} ⚡ 빠른 접속끊김 감지: {name} — 접속 {elapsed:.0f}초 만에 끊김"
                        f" (클라 크래시 의심, 위치 {j['loc']})."
                    )
                    if dump:
                        msg += " 직전 패킷 이력 첨부됨(끊기기 전 엔티티 관련 패킷)."
                    else:
                        msg += " 재현되면 클라 disconnect 로그 확인 요청."
                    notify(msg, file_path=dump)
                    state["last_alert"][name] = now

    json.dump(state, open(STATE_FILE, "w"))


if __name__ == "__main__":
    main()
