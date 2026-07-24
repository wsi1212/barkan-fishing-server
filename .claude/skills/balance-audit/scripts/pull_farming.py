#!/usr/bin/env python3
"""
pull_farming.py — 농사(특수작물) 경제 스냅샷 추출기. balance-audit 낚시 pull.py와 같은 패턴.

작물엔 직접 판매가가 없다(요리재료 전용) — "개/h"가 1차 처리량 지표.
farming-data-sources.md/farming-metrics.md 참조.

사용법: python3 pull_farming.py [--date YYYY-MM-DD]
"""
import argparse, json, os, re, sys

JAVA_ROOT = os.environ.get(
    "BLOCKSHIP_JAVA",
    "/Users/user/development/blockship-plugin/src/main/java/com/blockship",
)
WARNINGS = []


def warn(msg):
    WARNINGS.append(msg)
    print(f"  ⚠️  {msg}", file=sys.stderr)


def read_java(rel):
    path = os.path.join(JAVA_ROOT, rel)
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        warn(f"Java 파일 못 읽음: {rel} ({e})")
        return ""


def pull_crops():
    src = read_java("crop/CropSpecs.java")
    rows = re.findall(
        r'new Spec\("([^"]+)",\s*"([^"]+)",\s*(\d+),',
        src,
    )
    if not rows:
        warn("CropSpecs Spec 테이블 정규식 매치 실패")
    crops = []
    for cid, name, grow in rows:
        grow = int(grow)
        # 산출수량은 생성자 마지막 int 인자 — 별도 정규식으로 라인당 재매치
        m = re.search(re.escape(f'"{cid}"') + r'[^;]*?,\s*"[^"]+",\s*(\d+)\)\);', src)
        qty = int(m.group(1)) if m else None
        crops.append({"id": cid, "name": name, "grow_sec": grow, "qty": qty,
                      "qty_per_hour": round(qty * 3600 / grow, 3) if qty else None})
    return crops


def pull_plot_limits():
    out = {}
    isl = read_java("island/IslandManager.java")
    m = re.search(r"CROP_LIMIT\s*=\s*\{([^}]*)\}", isl)
    n = re.search(r"CROP_PRICE\s*=\s*\{([^}]*)\}", isl)
    if m and n:
        out["individual"] = {
            "limit": [int(x) for x in m.group(1).split(",")],
            "price": [int(x.strip().replace("_", "")) for x in n.group(1).split(",")],
        }
    else:
        warn("개인 CROP_LIMIT/CROP_PRICE 못 찾음")

    gld = read_java("guild/GuildManager.java")
    m = re.search(r"G_CROP_LIMIT\s*=\s*\{([^}]*)\}", gld)
    n = re.search(r"G_CROP_PRICE\s*=\s*\{([^}]*)\}", gld)
    if m and n:
        out["guild"] = {
            "limit": [int(x) for x in m.group(1).split(",")],
            "price": [int(x.strip().replace("_", "")) for x in n.group(1).split(",")],
        }
    else:
        warn("길드 G_CROP_LIMIT/G_CROP_PRICE 못 찾음")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--out")
    args = ap.parse_args()

    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = args.out or os.path.join(skill_dir, "audits", "snapshots")
    os.makedirs(out_dir, exist_ok=True)

    print("농사 스냅샷 추출 중...", file=sys.stderr)
    snapshot = {
        "date": args.date,
        "economy": "farming",
        "raw": {"crops": pull_crops(), "plot_limits": pull_plot_limits()},
        "warnings": WARNINGS,
        "derived": {},
    }
    fname = f"{args.date}-farming.raw.json" if args.date else "pending-farming.raw.json"
    path = os.path.join(out_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 스냅샷 저장: {path}", file=sys.stderr)
    if WARNINGS:
        print(f"⚠️  경고 {len(WARNINGS)}건", file=sys.stderr)
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
