#!/usr/bin/env python3
"""
pull_mining.py — 광질(mining) 경제 스냅샷 추출기. balance-audit 스킬의 낚시 pull.py와 같은 패턴.

드릴채굴(drill/)과 섬광산 생성기(islandmine/)는 완전히 다른 두 시스템이라 각각 별도 섹션으로 뽑는다.
mining-data-sources.md/mining-metrics.md 참조.

사용법: python3 pull_mining.py [--date YYYY-MM-DD]
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


def pull_drill():
    out = {}
    shop = read_java("economy/DrillShopGui.java")
    for key in ("T1_PRICE", "T2_RECIPE_PRICE", "T3_RECIPE_PRICE"):
        m = re.search(key + r"\s*=\s*(\d+)", shop)
        if m:
            out[key.lower()] = int(m.group(1))
        else:
            warn(f"DrillShopGui {key} 못 찾음")

    dm = read_java("drill/DrillManager.java")
    ores = re.findall(
        r'new Ore\("([^"]+)",\s*(\d+),\s*(\d+),\s*Material\.\w+,\s*(\d+),\s*"([^"]+)",\s*(\d+),\s*(\d+)\)',
        dm,
    )
    if not ores:
        warn("드릴 Ore 테이블 정규식 매치 실패 — DrillManager 구조 확인 필요")
    out["ores"] = [
        {"label": label, "tier": int(tier), "break_ticks": int(bt), "regen_sec": int(regen),
         "drop": drop, "qty_min": int(qmin), "qty_max": int(qmax)}
        for label, tier, bt, regen, drop, qmin, qmax in ores
    ]
    return out


def pull_islandmine():
    out = {}
    im = read_java("islandmine/IslandMineManager.java")
    ores = re.findall(
        r'new Ore\("([^"]+)",\s*Material\.\w+,\s*Material\.\w+,\s*(\d+),\s*(\d+),\s*([\d.]+),\s*(\d+)\)',
        im,
    )
    if not ores:
        warn("섬광산 Ore 테이블 정규식 매치 실패 — IslandMineManager 구조 확인 필요")
    total_weight = sum(float(w) for _, _, _, w, _ in ores) if ores else 0
    out["ores"] = [
        {"label": label, "qty_min": int(qmin), "qty_max": int(qmax), "weight": float(w),
         "xp": int(xp), "chance_pct": round(float(w) / total_weight * 100, 2) if total_weight else None}
        for label, qmin, qmax, w, xp in ores
    ]
    out["total_weight"] = total_weight

    sk = read_java("skill/SkillManager.java")
    m = re.search(r"ISLAND_MINE_DAILY_CAP\s*=\s*(\d+)", sk)
    out["daily_xp_cap"] = int(m.group(1)) if m else None
    if not m:
        warn("ISLAND_MINE_DAILY_CAP 못 찾음")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--out")
    args = ap.parse_args()

    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = args.out or os.path.join(skill_dir, "audits", "snapshots")
    os.makedirs(out_dir, exist_ok=True)

    print("광질 스냅샷 추출 중...", file=sys.stderr)
    snapshot = {
        "date": args.date,
        "economy": "mining",
        "raw": {"drill": pull_drill(), "island_mine": pull_islandmine()},
        "warnings": WARNINGS,
        "derived": {},
    }
    fname = f"{args.date}-mining.raw.json" if args.date else "pending-mining.raw.json"
    path = os.path.join(out_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 스냅샷 저장: {path}", file=sys.stderr)
    if WARNINGS:
        print(f"⚠️  경고 {len(WARNINGS)}건", file=sys.stderr)
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
