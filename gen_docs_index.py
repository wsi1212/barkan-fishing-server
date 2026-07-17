#!/usr/bin/env python3
"""문서 인덱스 생성기 — 이 폴더의 모든 .md를 스캔해 docs-index.md 갱신.

목적: LLM(Claude)이 story/design/balance 등 큰 문서를 통독하지 않고,
이 인덱스로 구조를 파악한 뒤 필요한 섹션만 `Read offset:N`으로 조준해 읽게 한다.
문서 수정 후 `python3 gen_docs_index.py` 재실행(또는 훅으로 자동).
"""
import glob
import re
import os

OUT = "docs-index.md"
# 인덱스 자체 + 편집기 부산물 제외
SKIP = {OUT}


def scan(path):
    with open(path, encoding="utf-8") as fh:
        raw = fh.readlines()
    title, firstprose = None, None
    headers = []  # (line_no, level, text)
    in_fence = False
    for i, ln in enumerate(raw, 1):
        s = ln.rstrip("\n")
        st = s.lstrip()
        if st.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if title is None and s.startswith("# ") and not s.startswith("##"):
            title = s[2:].strip()
            continue
        if title and firstprose is None and s.strip() \
                and not s.startswith(("#", ">", "|", "-", "```")):
            firstprose = s.strip()
        m = re.match(r"^(#{2,3}) +(.+?)\s*$", s)
        if m:
            headers.append((i, len(m.group(1)), m.group(2).strip()))
    return len(raw), title, firstprose, headers


def main():
    files = sorted(f for f in glob.glob("*.md") if f not in SKIP)
    out = []
    out.append("# 문서 인덱스 (docs-index)")
    out.append("")
    out.append("> 문서 구조 맵. 여기서 위치를 찾고 **필요한 구간만** "
               "`Read offset:N limit:M`으로 조준해 읽는다 (통독 금지 = 토큰 절약).")
    out.append("> **갱신**: 문서 수정 후 `python3 gen_docs_index.py`. 줄 번호(L…)는 갱신 시점 기준.")
    out.append("")
    out.append(f"총 {len(files)}개 문서.")
    for fn in files:
        n, title, fp, headers = scan(fn)
        head = title if title else fn
        out.append("")
        out.append(f"## `{fn}` — {head} ({n}줄)")
        if fp:
            out.append(f"> {fp[:90]}")
        for (i, level, text) in headers:
            indent = "  " if level == 3 else ""
            out.append(f"{indent}- L{i} {text}")
    txt = "\n".join(out) + "\n"
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(txt)
    print(f"wrote {OUT}: {len(files)} docs indexed, {txt.count(chr(10))} lines")


if __name__ == "__main__":
    main()
