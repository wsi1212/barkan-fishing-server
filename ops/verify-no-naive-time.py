#!/usr/bin/env python3
"""배포 전 BlockShip 자바 코드의 「타임존 미지정 시간 API」를 전수 차단한다.

왜 정적 검사인가
----------------
prod 박스는 ``Etc/UTC`` 이고 dev(맥)는 ``Asia/Seoul`` 이다. 그래서 존을 빠뜨린 코드는
**dev 에서 절대 재현되지 않고 prod 에서만 틀린다.** 테스트로 못 잡는 부류라 배포 게이트에 건다.

시간 권위는 ``com.blockship.util.KoreanTime`` (``ZONE = Asia/Seoul``) 하나다.
날짜·주·월 경계 판정과 사람이 읽는 시각은 전부 이걸 경유해야 한다.

2026-08-17 전수조사에서 실제로 잡힌 것들:
  * ``AchievementManager``  — 접속일수의 「하루」 경계가 09:00 KST 였다
  * ``IslandSubmitManager`` — 월간 시즌 리셋과 top3 코인 보상이 1일 09:00 KST 에 터졌다
  * ``TradeLog``            — 사기 신고 대조용 거래 시각이 UTC 로 박제됐다(9시간 + 날짜 하루)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib import import_module

# 굵은포맷 검사기의 주석 제거기를 재사용한다 — 주석 속 설명("LocalDate.now() 를 쓰면 안 된다")을
# 위반으로 오인하면 이 검사기 자체가 못 쓰게 된다.
_bold = import_module("verify-no-bold-format".replace("-", "_")) if False else None
try:  # 파일명에 하이픈이 있어 일반 import 가 안 된다 — 소스에서 직접 끌어온다.
    _src = (Path(__file__).resolve().parent / "verify-no-bold-format.py").read_text(encoding="utf-8")
    _ns: dict = {}
    exec(compile(_src.split("def main(")[0], "verify-no-bold-format.py", "exec"), _ns)
    without_java_comments = _ns["without_java_comments"]
except Exception:  # 재사용 실패 시에도 검사는 돌아야 한다(주석 오탐만 감수)
    def without_java_comments(source: str) -> str:  # type: ignore[misc]
        return source


# 시간 권위 자신은 예외 — 여기서만 존을 확정한다.
EXEMPT_FILES = {"KoreanTime.java"}

PATTERNS = [
    # .now() 무인자 = JVM 기본 존. .now(ZONE) 형태는 통과시킨다.
    (re.compile(r"\b(?:LocalDate|LocalDateTime|LocalTime|ZonedDateTime|YearMonth|Year|MonthDay|OffsetDateTime|OffsetTime)\.now\(\s*\)"),
     "X.now() — 존 미지정. KoreanTime.today()/todayText() 또는 .now(KoreanTime.ZONE)"),
    (re.compile(r"\bnew\s+SimpleDateFormat\s*\("),
     "new SimpleDateFormat(...) — 존 미지정 + 스레드 비안전. KoreanTime 포매터를 쓸 것"),
    (re.compile(r"\bCalendar\.getInstance\s*\(\s*\)"),
     "Calendar.getInstance() — 존 미지정"),
    (re.compile(r"\bTimeZone\.getDefault\s*\(\s*\)"),
     "TimeZone.getDefault() — 박스 존에 의존(prod=UTC)"),
    (re.compile(r"\bZoneId\.systemDefault\s*\(\s*\)"),
     "ZoneId.systemDefault() — 박스 존에 의존(prod=UTC)"),
    # Instant → 로컬 날짜 변환에 존이 빠진 형태
    (re.compile(r"\.atZone\(\s*ZoneId\.systemDefault\(\)\s*\)"),
     "atZone(systemDefault()) — KoreanTime.ZONE 을 쓸 것"),
]


def scan(root: Path) -> list[tuple[Path, int, str, str]]:
    hits: list[tuple[Path, int, str, str]] = []
    for path in sorted(root.rglob("*.java")):
        if path.name in EXEMPT_FILES:
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        stripped = without_java_comments(raw)
        raw_lines = raw.splitlines()
        for lineno, line in enumerate(stripped.splitlines(), start=1):
            for pattern, why in PATTERNS:
                if pattern.search(line):
                    original = raw_lines[lineno - 1].strip() if lineno <= len(raw_lines) else line.strip()
                    hits.append((path, lineno, why, original))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description="타임존 미지정 시간 API 전수 차단")
    ap.add_argument("root", nargs="?", default="src/main",
                    help="검사할 루트 (기본: src/main)")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"✗ 경로 없음: {root}", file=sys.stderr)
        return 2

    hits = scan(root)
    if not hits:
        print("✓ 타임존 미지정 시간 API 전수 검사 통과")
        return 0

    print(f"✗ 타임존 미지정 시간 API {len(hits)}건 — prod(Etc/UTC)에서만 틀리는 부류다\n", file=sys.stderr)
    for path, lineno, why, original in hits:
        print(f"  {path}:{lineno}", file=sys.stderr)
        print(f"    {original}", file=sys.stderr)
        print(f"    → {why}\n", file=sys.stderr)
    print("시간 권위는 com.blockship.util.KoreanTime (Asia/Seoul) 하나다.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
