#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostToolUse hook — 경제/동시성/명령별칭/OP권한/월드이동 재발방지 경고 (2026-07 치명적버그 전수조사 + 별칭규칙).

no-bold-format.py(PreToolUse, 볼드·빈권한게이트 '차단')의 짝. 여기서는 파일 전체 문맥이
필요한 휴리스틱을 '경고'(비차단)로 알린다. Edit/Write 후 결과 파일을 읽어 검사.

- 아이템 표시이름/lore를 파싱해 금액에 씀 (모루 개명 위조 → PDC 권장)      : 수표 위조 버그
- AsyncChatEvent 핸들러 근처 공유 HashMap/HashSet (→ ConcurrentHashMap)     : 길드 프롬프트 버그
- 금액 취급 파일의 raw Long.parseLong/Double.parseDouble (오버플로 포화)     : 수표 오버플로 버그
- ★OP 전용 명령(setPermission blockship.admin)에 영타/한글초성 별칭         : 별칭 규칙(아래)
- ★OP스러운 명령(isOp/hasPermission admin 체크)인데 setPermission 누락      : 2026-07-25 명령어 전수조사 사고
- ★인벤 초과분을 바닥에 드롭하거나 addItem 반환값을 버림                       : 2026-08-26 우편함 일원화
- ★"execute in " 뒤 Worlds.dimKey() 없이 월드이름 직접 연결/"minecraft:world" 리터럴 : 2026-06-06 워프 무응답 버그

명령 별칭 규칙(구 CLAUDE.md에서 이관):
  · 한글 플레이어 명령 = 영타 별칭 필수(두벌식 로마자). 초성 별칭은 자주 쓰는 것만(선택).
  · OP 전용 명령 = 영타/초성 별칭 금지 (이 훅이 감지).
  두벌식: ㅂq ㅈw ㄷe ㄱr ㅅt ㅛy ㅕu ㅑi ㅐo ㅔp | ㅁa ㄴs ㅇd ㄹf ㅎg ㅗh ㅓj ㅏk ㅣl
          | ㅋz ㅌx ㅊc ㅍv ㅠb ㅜn ㅡm  (쌍자음=shift)

stdin  : Claude Code hook JSON  /  exit 0 : 통과(경고는 additionalContext로 전달, 비차단)
"""
import sys, os, json, re
import hashlib
import tempfile
import time

MC_ROOTS = ("blockship-plugin", "feather/player-server")


def already_ran(payload):
    """같은 툴 호출에 두 번 불렸으면 두 번째는 조용히 통과.

    이 훅은 두 곳에 등록돼 있다 — 유저 설정(`~/.claude/settings.json`: 맥에서 blockship-plugin
    레포까지 커버)과 레포 설정(`.claude/settings.json`: git 추적이라 **클라우드 세션에서도** 돈다).
    이 repo 안에서는 둘이 겹쳐서 같은 경고가 두 번 찍히므로, 페이로드 해시로 5초 TTL 마커를 남겨
    한 번만 말하게 한다. 한쪽 등록을 지우면 맥 커버리지나 클라우드 커버리지 중 하나가 사라진다.
    """
    try:
        key = hashlib.sha1(json.dumps(payload, sort_keys=True,
                                      ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
        marker = os.path.join(tempfile.gettempdir(), f".bs-guard-sec-{key}")
        now = time.time()
        if os.path.exists(marker) and now - os.path.getmtime(marker) < 5:
            return True
        open(marker, "w").close()
    except OSError:
        return False
    return False

CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
JONG = ["", "ㄱ","ㄲ","ㄳ","ㄴ","ㄵ","ㄶ","ㄷ","ㄹ","ㄺ","ㄻ","ㄼ","ㄽ","ㄾ","ㄿ","ㅀ",
        "ㅁ","ㅂ","ㅄ","ㅅ","ㅆ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]
J2K = {"ㅂ":"q","ㅈ":"w","ㄷ":"e","ㄱ":"r","ㅅ":"t","ㅛ":"y","ㅕ":"u","ㅑ":"i","ㅐ":"o","ㅔ":"p",
       "ㅁ":"a","ㄴ":"s","ㅇ":"d","ㄹ":"f","ㅎ":"g","ㅗ":"h","ㅓ":"j","ㅏ":"k","ㅣ":"l",
       "ㅋ":"z","ㅌ":"x","ㅊ":"c","ㅍ":"v","ㅠ":"b","ㅜ":"n","ㅡ":"m",
       "ㅃ":"Q","ㅉ":"W","ㄸ":"E","ㄲ":"R","ㅆ":"T","ㅒ":"O","ㅖ":"P",
       # 겹받침/복모음 = 두 키
       "ㄳ":"rt","ㄵ":"sw","ㄶ":"sg","ㄺ":"fr","ㄻ":"fa","ㄼ":"fq","ㄽ":"ft","ㄾ":"fx",
       "ㄿ":"fv","ㅀ":"fg","ㅄ":"qt","ㅘ":"hk","ㅙ":"ho","ㅚ":"hl","ㅝ":"nj","ㅞ":"np","ㅟ":"nl","ㅢ":"ml"}


def romanize(kr):
    out = []
    for ch in kr:
        c = ord(ch) - 0xAC00
        if 0 <= c < 11172:
            out.append(J2K.get(CHO[c // 588], ""))
            out.append(J2K.get(JUNG[(c % 588) // 28], ""))
            if c % 28:
                out.append(J2K.get(JONG[c % 28], ""))
        elif ch in J2K:
            out.append(J2K[ch])
    return "".join(out)


def chosung(kr):
    return "".join(CHO[(ord(ch) - 0xAC00) // 588] for ch in kr if 0 <= ord(ch) - 0xAC00 < 11172)


JAMO_ONLY = re.compile(r"^[ㄱ-ㅎ]+$")  # 한글 호환 자모(초성 별칭)만


def alias_tokens(scope):
    """scope 텍스트 안 setAliases(...) 호출들에서 따옴표 별칭 토큰 추출."""
    toks = []
    for m in re.finditer(r"setAliases\s*\(([^;]*?)\)\s*;", scope, re.DOTALL):
        toks += re.findall(r'"([^"]+)"', m.group(1))
    return toks


def extract_command_units(text):
    """파일에서 (command_name, scope_text) 목록 추출 — 인라인 익명클래스 / extends Command 두 형태."""
    units = []
    # 인라인: new ...Command("한글") { { ...초기화블록... } ...
    for m in re.finditer(r'new\s+[\w.]*Command\s*\(\s*"([가-힣][^"]*)"\s*\)\s*\{\s*\{([^{}]*)\}', text):
        units.append((m.group(1), m.group(2)))
    # 별도 클래스: super("한글") + 파일 전체 (단일 명령 클래스 가정)
    if "extends Command" in text:
        for m in re.finditer(r'super\s*\(\s*"([가-힣][^"]*)"\s*\)', text):
            units.append((m.group(1), text))
    return units


def check_op_aliases(text, warns):
    """OP 전용(setPermission blockship.admin) 명령에 영타/초성 별칭이 붙었는지."""
    if "blockship.admin" not in text:
        return
    for name, scope in extract_command_units(text):
        if "blockship.admin" not in scope:
            continue
        yeong, cho = romanize(name), chosung(name)
        for tok in alias_tokens(scope):
            if tok == yeong:
                warns.append("[별칭규칙] OP 전용 명령 /%s 에 영타 별칭 \"%s\" — OP 명령은 영타 금지. setAliases에서 제거."
                             % (name, tok))
            elif JAMO_ONLY.match(tok) or tok == cho:
                warns.append("[별칭규칙] OP 전용 명령 /%s 에 초성 별칭 \"%s\" — OP 명령은 초성 금지. setAliases에서 제거."
                             % (name, tok))


ADMIN_CHECK = re.compile(r'\.isOp\s*\(\s*\)|hasPermission\s*\(\s*"blockship\.admin"\s*\)')


def check_missing_setpermission(text, warns):
    """isOp()/hasPermission("blockship.admin")로 OP전용처럼 동작하면서 setPermission 호출이 없는 명령.
    (2026-07-25 명령어 전수조사: 드릴/초음파탐지기 등에서 실제 발견된 패턴 — 비OP 탭완성에 노출됨)"""
    for name, scope in extract_command_units(text):
        if ADMIN_CHECK.search(scope) and "setPermission(" not in scope:
            warns.append("[OP권한] 명령 /%s 이 isOp()/hasPermission(\"blockship.admin\")로 OP전용처럼 동작하는데 "
                         "setPermission(\"blockship.admin\") 호출이 없음 — 비OP 플레이어 탭완성에 노출됨."
                         % name)


def check_world_teleport(text, warns):
    """cross-world 텔레포트에서 Worlds.dimKey() 우회 패턴 (2026-06-06 워프 무응답 사고 재발방지)."""
    if re.search(r"minecraft:world\b", text):
        warns.append("[월드이동] 리터럴 \"minecraft:world\"는 유효하지 않은 dimension key(정답은 minecraft:overworld) "
                     "— tp가 콘솔에만 에러 남기고 플레이어에겐 조용히 무시됨.")
    for i, ln in enumerate(text.splitlines(), 1):
        if '"execute in "' in ln and "dimKey" not in ln:
            warns.append("[월드이동] %d줄: \"execute in \" 뒤에 Worlds.dimKey() 없이 월드 이름을 직접 붙이는 것으로 보임 "
                         "— dimension key 불일치 시 tp가 조용히 무시됨. Worlds.dimKey(world) 사용." % i)


MAIL_EXEMPT = ("mail/ItemDelivery.java", "mail/MailboxManager.java",
               "trade/TradeManager.java", "skill/SkillManager.java", "crop/CropManager.java")


def check_inventory_overflow(text, fp, warns):
    """인벤 초과분을 바닥에 떨구거나 통째로 버리는 패턴 (2026-08-26 우편함 일원화 재발방지).

    바닥 아이템은 5분이면 디스폰된다 — 인벤이 꽉 찬 줄 모르고 계속 플레이하면 보상이 조용히 증발했다.
    새 지급 경로는 com.blockship.mail.ItemDelivery.give(p, "출처", item) 하나만 쓴다.
    폴백 드롭이 정당한 파일(우편 저장 실패 반환·주인 오프라인 회수·바닐라 수확)은 MAIL_EXEMPT 로 뺀다.
    """
    if any(fp.endswith(x) or x in fp for x in MAIL_EXEMPT):
        return
    lines = text.splitlines()
    for i, ln in enumerate(lines, 1):
        # ① addItem(...) 의 잔량을 바닥에 떨구는 고전 패턴 (같은 줄 또는 다음 줄에 drop)
        if ".addItem(" in ln and ".values()" in ln:
            window = " ".join(lines[i - 1:i + 2])
            if "dropItem" in window:
                warns.append("[우편함] %d줄: addItem 잔량을 바닥에 떨굼 — 5분 뒤 디스폰돼 유실된다. "
                             "com.blockship.mail.ItemDelivery.give(p, \"출처\", item) 사용." % i)
        # ② 반환값을 아예 안 쓰는 addItem — 초과분이 바닥에도 안 떨어지고 그냥 사라진다
        if re.search(r"^\s*(?:\w+(?:\.\w+)*)?\.?getInventory\(\)\.addItem\([^;]*\);\s*$", ln):
            warns.append("[우편함] %d줄: addItem 반환값(초과분)을 버림 — 인벤이 꽉 차면 아이템이 «조용히» 사라진다. "
                         "com.blockship.mail.ItemDelivery.give(p, \"출처\", item) 사용." % i)


def line_positions(text, needle):
    return [i for i, ln in enumerate(text.splitlines()) if needle in ln]


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if already_ran(data):
        return 0
    ti = data.get("tool_input") or {}
    fp = ti.get("file_path") or (data.get("tool_response") or {}).get("filePath") or ""
    if not fp or not any(r in fp for r in MC_ROOTS) or not fp.endswith(".java"):
        return 0
    if not os.path.isfile(fp):
        return 0
    try:
        text = open(fp, "r", encoding="utf-8", errors="replace").read()
    except Exception:
        return 0

    warns = []
    uses_pdc = ("PersistentDataType" in text) or ("getPersistentDataContainer" in text)

    # 표시이름/lore → 금액 파싱 (PDC 안 쓰는 파일만)
    if re.search(r"(?:getDisplayName|\bdisplayName\s*\(\)|\.lore\s*\(\)|getLore\s*\()", text) \
       and re.search(r"\b(?:parseLong|parseDouble|parseInt)\s*\(", text) \
       and re.search(r"\bmoney\.(?:add|subtract|set|read)\b|MoneyBridge", text) \
       and not uses_pdc:
        warns.append("[위조위험] 아이템 표시이름/lore를 파싱해 금액에 쓰는 것으로 보임 — 모루 개명으로 위조 가능. "
                     "값/정체는 PersistentDataContainer(PDC)에 저장·검증할 것 (2026-07 수표 위조 버그)")

    # AsyncChatEvent 핸들러 '근처(±50줄)'의 공유 HashMap/HashSet — god-class 오탐 방지 위해 근접 스코프
    if "AsyncChatEvent" in text and re.search(r"=\s*new\s+(?:\w+\.)*Hash(?:Map|Set)\s*<", text):
        async_lines = line_positions(text, "AsyncChatEvent")
        hash_lines = [i for i, ln in enumerate(text.splitlines())
                      if re.search(r"=\s*new\s+(?:\w+\.)*Hash(?:Map|Set)\s*<", ln)]
        if any(abs(a - h) <= 50 for a in async_lines for h in hash_lines):
            warns.append("[동시성] AsyncChatEvent 핸들러 근처의 new HashMap/HashSet 필드 — "
                         "메인+비동기 동시접근 시 손상(CME/무한루프 DoS). ConcurrentHashMap(.newKeySet) 사용")

    # 금액 취급 파일의 raw parse (Num/PDC 안 쓰는 경우만)
    if re.search(r"\bmoney\.(?:add|subtract|set|read)\b", text) \
       and re.search(r"\b(?:Long\.parseLong|Double\.parseDouble)\s*\(", text) \
       and "parseLongOrNull" not in text and not uses_pdc:
        warns.append("[오버플로] 금액 취급 파일에서 Long.parseLong/Double.parseDouble 직접 사용 — "
                     "거대입력이 Long.MAX로 포화됨. com.blockship.util.Num.parseLongOrNull + ≤Num.MAX_MONEY 검사")

    # OP 전용 명령의 영타/초성 별칭
    check_op_aliases(text, warns)

    # OP전용처럼 동작하는데 setPermission 누락
    check_missing_setpermission(text, warns)

    # cross-world 텔레포트 dimKey 우회
    check_world_teleport(text, warns)

    # 인벤 초과분 바닥 드롭/무시 (우편함 일원화)
    check_inventory_overflow(text, fp, warns)

    if warns:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "[보안가드 경고] " + " / ".join(warns)}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
