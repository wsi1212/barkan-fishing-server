#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PreToolUse hook (matcher: Bash) — **인스턴스 전용 데이터를 다른 서버 트리에 쓰는 것** 차단.

dev(맥)와 prod(오라클)는 유저 데이터가 완전히 별개인 서버다. 섬·길드·플레이어 진행도는
"그 인스턴스에서 그 유저가 만든 상태"라서 애초에 동기화 대상이 아니다. 그런데 사고는
매번 같은 모양으로 온다: 정식 배포 스크립트가 이 파일들을 sync 목록에서 **제외**해 뒀는데,
그 스크립트를 못 써서 손으로 재현한 세션이 **제외까지 재현하지 않는다.**

실사고 3건 (전부 regions.json, 전부 사람 손):
  · 2026-08-23  dev regions.json → prod. 섬 지역 7개+붉은호수 소실.
                빈 격자로 오인해 **남의 섬 위에 시작섬을 덮어씀** (vwv38→dssfjdfldsjf).
  · 2026-08-25  quest_audit 게이트에 막혀 deploy-blockship.sh 를 못 쓰고 손으로 scp.
                올린 4개 묶음에 regions.json 이 끼어 개인섬 5개 소실(42→37 regions).
  · 2026-08-26  그 결과가 하루 뒤 발화. SEXY___YAMA·vwv38 이 /섬 치는 순간
                「지역 없음 → 새 격자로 재발급」= 유저 눈에는 **섬 초기화**.

차단 규칙 — **목적지가 라이브 서버 트리**일 때만 본다.
  라이브 트리 = ~/mcserver/plugins/<플러그인>/   (prod)
                .../feather/.../servers/<id>/plugins/<플러그인>/   (dev)
  · 목적지가 인스턴스 파일이면            → 차단
  · 목적지가 그 디렉터리(파일명 없음)면   → 소스를 본다. 소스에 인스턴스 파일이 있거나
                                            소스가 디렉터리(=통째 sync)면 차단
  · /tmp·scratchpad·backups 로 **받아오는** 건 허용 (조사·백업은 정상 작업)

탈출구: 진짜 복구 작업이면 명령 앞에 ALLOW_INSTANCE_DATA_WRITE=1 을 붙인다.
        단 라이브가 이 파일들을 되쓰므로 **서버를 멈춘 뒤** 할 것.

stdin : hook JSON  /  exit 0 = 허용  /  exit 2 = 차단
"""
import json
import os
import re
import sys

# ── 인스턴스 전용 = 그 서버에서 유저가 만든 상태. 절대 서버 간 복사 대상이 아니다.
INSTANCE_FILES = {
    "regions.json",         # 지역·섬 경계. 사고 3건 전부 이 파일이다.
    "islands.json",         # 개인섬 레코드
    "islandmines.json",     # 섬 광산
    "island-template.json", # /섬 템플릿저장 산출물(인스턴스 실섬을 뜬 것)
    "guilds.json",          # 길드. vip-billing DB guild_id 와 짝이라 더 위험
    "guild-notices.json",
    "chest-locks.json",     # 상자 자물쇠(소유자 UUID)
    "locked-doors.json",
    "casino-tables.json",   # 물리 테이블 배치
    "forage-nodes.json",    # 채집 노드 배치
    "forage-seq.json",
    "emblem-placements.json",
    "drawbridges.json",
    "portals.json",
    "market.json",          # 유저 마켓 등록물
    "canvases.json",
    "collectibles.json",    # 월드 배치물
    "env-bonuses.json",
    "achievements.json",
    "playerdata",           # 디렉터리 — 레벨·돈·장비·강화 전부
    "packet-blackbox",
}

# 라이브 서버의 플러그인 데이터 트리. plugins/<플러그인폴더>/... 까지 잡는다.
LIVE_TREE = re.compile(
    r"(?:mcserver/plugins|servers/[0-9a-f-]{8,}/plugins|player-server/[^\s'\"]*/plugins)"
    r"/[^/]+(?:/|$)",
    re.IGNORECASE,
)

DEST_LAST = re.compile(r"\b(?:scp|rsync|cp|mv|install|ditto)\b", re.IGNORECASE)
DEST_ANY = re.compile(r"\b(?:curl|wget|tee|dd)\b", re.IGNORECASE)
TAR_EXTRACT = re.compile(r"\btar\b(?=[^|;&]*\s-{0,2}[a-zA-Z]*x)", re.IGNORECASE)
REDIRECT = re.compile(r">>?\s*(\"[^\"]+\"|'[^']+'|[^\s;|&<>]+)")
TAR_C = re.compile(r"-C\s+(\"[^\"]+\"|'[^']+'|[^\s;|&]+)")

OVERRIDE = "ALLOW_INSTANCE_DATA_WRITE=1"

# 정식 경로 — 스크립트 내부 복사는 훅에 안 보이고, 스크립트가 제외 목록을 지킨다.
SAFE = re.compile(
    r"deploy-blockship\.sh|deploy-dev\.sh|stage-blockship\.sh|ops/deploy-jar\.sh|rp-deploy\.sh",
    re.IGNORECASE,
)

MSG = """⛔ 인스턴스 전용 데이터를 라이브 서버 트리에 쓰려고 했다: {what}
   목적지: {dest}

dev(맥)와 prod(오라클)는 유저 데이터가 별개인 서버다. 섬·길드·플레이어 진행도는
그 인스턴스에서 유저가 만든 상태라 **서버 간 동기화 대상이 아니다.**
정식 배포 스크립트가 이 파일들을 sync 목록에서 제외해 둔 이유가 이것이다.

같은 사고가 이미 3번 났고 3번 다 사람 손이었다 (전부 regions.json):
  · 08-23  남의 섬 위에 시작섬을 덮어씀
  · 08-25  quest_audit 게이트 우회 scp 에 regions.json 이 끼어 개인섬 5개 소실
  · 08-26  그게 발화 — 유저 눈에 「섬 초기화」

이 파일들은 서버 간 복사 대상이 아니다:
  regions/islands/islandmines/island-template/guilds/chest-locks/locked-doors/
  casino-tables/forage-nodes/emblem-placements/portals/market/collectibles/playerdata …

지금 하려던 게 무엇이냐에 따라:
  · 코드·콘텐츠 배포     → ~/deploy-blockship.sh (게이트가 막으면 게이트를 고칠 것.
                            손으로 재현하면 제외 목록이 같이 사라진다 = 이 사고)
  · prod 데이터 들여다보기 → /tmp 나 scratchpad 로 받아올 것 (그건 허용된다)
  · 진짜 복구 작업        → 서버를 먼저 멈추고 {ov} 를 명령 앞에 붙일 것
"""


def unwrap(tok: str) -> str:
    tok = tok.strip().strip("'\"")
    # scp 의 user@host: 접두어 제거
    if ":" in tok and not tok.startswith("/") and re.match(r"^[\w.\-]+@[\w.\-]+:", tok):
        tok = tok.split(":", 1)[1]
    return tok


def basename(path: str) -> str:
    return os.path.basename(path.rstrip("/"))


def is_instance_path(path: str) -> bool:
    """경로 어딘가에 인스턴스 전용 파일/디렉터리 이름이 있는가."""
    parts = [p for p in path.replace("\\", "/").split("/") if p]
    return any(p in INSTANCE_FILES for p in parts)


def looks_like_dir(tok: str) -> bool:
    return tok.endswith("/") or basename(tok) in ("BlockShip", "plugins") or "." not in basename(tok)


def check(part: str):
    """(무엇, 목적지) 를 돌려주면 차단."""
    toks = [t for t in re.split(r"\s+", part.strip()) if t]
    if not toks:
        return None

    dests, srcs, tar_dests = [], [], []

    if DEST_LAST.search(part):
        cand = [unwrap(t) for t in toks[1:] if not t.startswith("-")]
        if len(cand) >= 2:
            dests.append(cand[-1])
            srcs.extend(cand[:-1])
        elif cand:
            dests.append(cand[-1])
    if DEST_ANY.search(part):
        dests.extend(unwrap(t) for t in toks if not t.startswith("-"))
    if TAR_EXTRACT.search(part):
        tar_dests.extend(unwrap(m) for m in TAR_C.findall(part))
    dests.extend(unwrap(m) for m in REDIRECT.findall(part))

    # 아카이브 전개는 내용물을 알 수 없다 — 라이브 트리로 푸는 건 무조건 막고
    # 복구 의도라면 탈출구를 거치게 한다 (복구는 서버 정지가 전제이기도 하다).
    for dest in tar_dests:
        if dest and LIVE_TREE.search(dest):
            return "tar 아카이브 전개 (내용물 불명)", dest

    for dest in dests:
        if not dest or not LIVE_TREE.search(dest):
            continue
        # ① 목적지 자체가 인스턴스 파일
        if is_instance_path(dest):
            return basename(dest), dest
        # ② 목적지는 디렉터리 → 소스를 본다
        if looks_like_dir(dest):
            for s in srcs:
                if is_instance_path(s):
                    return basename(s), dest
                if s.endswith("/") or basename(s) == "BlockShip":
                    return "디렉터리 통째 sync (%s)" % s, dest
    return None


def check_list(names):
    """`--check-list <파일…>` — 배포 스크립트의 sync 목록에 인스턴스 파일이 끼었는지 검사.

    제외 목록이 주석으로만 지켜지면 언젠가 누가 한 줄 더한다. 목록의 권위를
    INSTANCE_FILES 한 곳으로 모아 두고 스크립트가 매 실행마다 스스로 검산하게 한다.
    """
    bad = [n for n in names if basename(n) in INSTANCE_FILES]
    if not bad:
        return 0
    sys.stderr.write(
        "⛔ 배포 sync 목록에 인스턴스 전용 파일이 들어 있다: %s\n"
        "   이 파일들은 dev/prod 가 각자 따로 들고 있는 유저 상태다 — 배포 대상이 아니다.\n"
        "   목록의 권위는 ops/hooks/guard-instance-data.py 의 INSTANCE_FILES 다.\n"
        % ", ".join(bad)
    )
    return 2


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--check-list":
        return check_list(sys.argv[2:])

    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not cmd or OVERRIDE in cmd or SAFE.search(cmd):
        return 0

    # ★줄바꿈도 절 경계다. 빼먹으면 여러 줄 스크립트가 한 절로 뭉쳐서, 앞줄의 `cp`(라이브에서
    #   /tmp 로 받아오는 정상 동작)와 뒷줄에 적힌 라이브 경로가 짝지어져 오탐이 난다(실측).
    for part in re.split(r"&&|\|\||[;|\n]|\$\(|`", cmd):
        hit = check(part)
        if hit:
            what, dest = hit
            sys.stderr.write(MSG.format(what=what, dest=dest, ov=OVERRIDE))
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
