#!/usr/bin/env python3
"""
diff.py — 두 밸런스 스냅샷의 델타 비교.

이전 감사 스냅샷 대비 '바뀐 수치만' 뽑아 연속성 추적을 가능하게 한다.

사용법:
    python3 diff.py <old.raw.json> <new.raw.json>
    python3 diff.py --auto            # snapshots/에서 최신 2개 자동 선택
    python3 diff.py --auto <new.raw.json>   # new 대비 그 직전 스냅샷

출력: 변경/추가/삭제된 리프 경로 + old→new 값 (+변화율). 변경 없으면 명시.
"""
import argparse, glob, json, os, sys


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def flatten(obj, prefix=""):
    """중첩 dict/list를 dotted-path 리프 맵으로 평탄화."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def pct(old, new):
    try:
        if isinstance(old, (int, float)) and isinstance(new, (int, float)) and old:
            return f"  ({(new - old) / abs(old) * 100:+.2f}%)"
    except (TypeError, ZeroDivisionError):
        pass
    return ""


def latest_two(snap_dir):
    files = sorted(glob.glob(os.path.join(snap_dir, "*.raw.json")))
    files = [f for f in files if "pending" not in os.path.basename(f)]
    return files[-2:] if len(files) >= 2 else files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old", nargs="?")
    ap.add_argument("new", nargs="?")
    ap.add_argument("--auto", action="store_true", help="snapshots/에서 자동 선택")
    args = ap.parse_args()

    snap_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "audits", "snapshots"
    )

    def resolve(p):
        """맨 파일명이면 snapshots 디렉터리 기준으로 해석."""
        if p and not os.path.exists(p) and os.path.exists(os.path.join(snap_dir, p)):
            return os.path.join(snap_dir, p)
        return p

    args.old = resolve(args.old)
    args.new = resolve(args.new)

    if args.auto:
        if args.old and not args.new:
            new_path = args.old
            files = sorted(glob.glob(os.path.join(snap_dir, "*.raw.json")))
            files = [f for f in files if "pending" not in os.path.basename(f) and f != new_path]
            if not files:
                print("비교할 이전 스냅샷이 없음 — 이번이 첫 베이스라인.")
                return
            old_path = files[-1]
        else:
            two = latest_two(snap_dir)
            if len(two) < 2:
                print("스냅샷이 2개 미만 — 이번이 첫 베이스라인 (델타 없음).")
                return
            old_path, new_path = two
    else:
        if not (args.old and args.new):
            ap.error("old/new 스냅샷 경로 2개, 또는 --auto 필요")
        old_path, new_path = args.old, args.new

    old = flatten(load(old_path).get("raw", {}))
    new = flatten(load(new_path).get("raw", {}))

    print(f"OLD: {os.path.basename(old_path)}")
    print(f"NEW: {os.path.basename(new_path)}\n")

    keys = sorted(set(old) | set(new))
    changed = added = removed = 0
    for k in keys:
        if k not in old:
            print(f"  + {k} = {new[k]}   [추가]")
            added += 1
        elif k not in new:
            print(f"  - {k} (was {old[k]})   [삭제]")
            removed += 1
        elif old[k] != new[k]:
            print(f"  ~ {k}: {old[k]} → {new[k]}{pct(old[k], new[k])}")
            changed += 1

    if not (changed or added or removed):
        print("변경 없음 — 밸런스 수치 동일. ✅")
    else:
        print(f"\n요약: 변경 {changed} · 추가 {added} · 삭제 {removed}")


if __name__ == "__main__":
    main()
