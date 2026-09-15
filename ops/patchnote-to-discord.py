#!/usr/bin/env python3
"""패치노트 마크다운 → 디스코드에 그대로 붙여넣을 수 있는 메시지 묶음.

★디스코드는 마크다운 «표»를 지원하지 않는다. 파이프 문자가 그대로 보인다.
  - 숫자 위주의 좁은 표  → 코드블록 + 폭 맞춤(한글은 2칸으로 계산)
  - 자유 텍스트가 긴 표  → 한 줄짜리 불릿으로 평탄화
  헤딩(#/##/###)·볼드·불릿은 디스코드가 그대로 렌더하므로 건드리지 않는다.

사용: python3 ops/patchnote-to-discord.py patchnotes/2026-09-14.md [출력디렉터리]
"""
import re, sys, unicodedata, pathlib

LIMIT = 1900          # 메시지 2000자 제한에 여유를 둔다
MAX_COLS = 46         # 코드블록 한 줄 폭 — 모바일에서 가로 스크롤이 안 생기는 한계

def w(s):
    """표시 폭. 한글·전각은 2칸."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)

def pad(s, n):
    return s + " " * max(0, n - w(s))

def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]

def is_sep(line):
    return bool(re.fullmatch(r'\|[\s:\-|]+\|', line.strip()))

def render_table(header, rows):
    """좁으면 코드블록 표, 넓으면 불릿 목록."""
    keep = [i for i in range(len(header))
            if any(r[i] not in ("", "—") for r in rows)]
    hdr = [header[i] for i in keep]
    body = [[r[i] for i in keep] for r in rows]
    widths = [max(w(hdr[i]), max(w(r[i]) for r in body)) for i in range(len(hdr))]
    total = sum(widths) + 2 * (len(widths) - 1)

    if total <= MAX_COLS:
        out = ["```"]
        out.append("  ".join(pad(hdr[i], widths[i]) for i in range(len(hdr))).rstrip())
        out.append("  ".join("-" * widths[i] for i in range(len(hdr))))
        for r in body:
            out.append("  ".join(pad(r[i], widths[i]) for i in range(len(r))).rstrip())
        out.append("```")
        return out

    # 행이 하나뿐인 표는 열이 «필드»가 아니라 «분류»다(예: → 평범 / → 숙련 / → 희귀).
    # 행을 평탄화하면 첫 칸이 이름 행세를 해서 뭉개지므로, 열을 세로로 편다.
    if len(body) == 1:
        return [f"- **{hdr[i]}** — {body[0][i]}"
                for i in range(len(hdr)) if body[0][i] not in ("", "—")]

    # 넓은 표 → 불릿. 1열=이름, 2열=꼬리표, 나머지는 「제목: 값」
    lines = []
    for r in body:
        head = f"**{r[0]}**"
        if len(r) > 1 and w(r[1]) <= 6:
            head += f" ({r[1]})"; rest = list(zip(hdr[2:], r[2:]))
        else:
            rest = list(zip(hdr[1:], r[1:]))
        tail = " / ".join(f"{h}: {v}" for h, v in rest if v not in ("", "—"))
        lines.append(f"- {head} — {tail}" if tail else f"- {head}")
    return lines

def convert(md):
    out, i, lines = [], 0, md.splitlines()
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|") and i + 1 < len(lines) and is_sep(lines[i + 1]):
            header = split_row(ln); i += 2; rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(split_row(lines[i])); i += 1
            out += render_table(header, rows); out.append("")
            continue
        if ln.startswith("> "):            # 인용은 디스코드도 지원하지만 헤더 밑엔 군더더기
            out.append("-# " + ln[2:])     # 작은 글씨(디스코드 전용 문법)
        else:
            out.append(ln)
        i += 1
    return out

def chunk(lines):
    """코드블록·표 행을 쪼개지 않고 LIMIT 이하로 자른다."""
    msgs, cur, fence = [], [], False
    def flush():
        if cur and any(x.strip() for x in cur):
            msgs.append("\n".join(cur).strip("\n"))
    for ln in lines:
        if not fence and ln.startswith("## ") and w("\n".join(cur)) > 0:
            flush(); cur = []
        nxt = cur + [ln]
        if not fence and len("\n".join(nxt)) > LIMIT:
            flush(); cur = [ln]
        else:
            cur = nxt
        if ln.startswith("```"):
            fence = not fence
            if not fence and len("\n".join(cur)) > LIMIT:
                flush(); cur = []
    flush()
    return msgs

def main():
    src = pathlib.Path(sys.argv[1])
    outdir = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else src.parent / (src.stem + "-discord"))
    outdir.mkdir(parents=True, exist_ok=True)
    msgs = chunk(convert(src.read_text(encoding="utf-8")))
    for old in outdir.glob("*.txt"):
        old.unlink()
    for n, m in enumerate(msgs, 1):
        (outdir / f"{n:02d}.txt").write_text(m + "\n", encoding="utf-8")
    print(f"{len(msgs)}개 메시지 → {outdir}")
    for n, m in enumerate(msgs, 1):
        print(f"  {n:02d}.txt  {len(m):>5}자")
    over = [n for n, m in enumerate(msgs, 1) if len(m) > 2000]
    print("★2000자 초과:", over if over else "없음")

if __name__ == "__main__":
    main()
