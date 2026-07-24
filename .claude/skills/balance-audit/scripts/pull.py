#!/usr/bin/env python3
"""
pull.py — 바르칸 열도 밸런스 스냅샷 추출기.

라이브 권위 소스(BlockShip Java 상수 + 런타임 JSON)에서 핵심 밸런스 수치를
정규화된 스냅샷 JSON으로 고정한다. balance.md는 읽지 않는다(드리프트 대상이라 신뢰 안 함).

사용법:
    python3 pull.py [--date YYYY-MM-DD] [--out DIR]

기본 출력: <스킬>/audits/snapshots/<date>.raw.json
날짜를 안 주면 스크립트는 날짜를 '지정 안 됨'으로 두고, 대신 audits/snapshots/pending.raw.json에 쓴다.
(Claude가 감사 시 오늘 날짜를 알고 있으므로 --date로 넘겨주는 걸 권장.)

경로 오버라이드: 환경변수 BLOCKSHIP_JAVA / BLOCKSHIP_JSON
"""
import argparse, json, os, re, sys

JAVA_ROOT = os.environ.get(
    "BLOCKSHIP_JAVA",
    "/Users/user/development/blockship-plugin/src/main/java/com/blockship",
)
JSON_ROOT = os.environ.get(
    "BLOCKSHIP_JSON",
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip",
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


def read_json(name):
    path = os.path.join(JSON_ROOT, name)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        warn(f"JSON 못 읽음: {name} ({e})")
        return None


def nums(text):
    """텍스트에서 숫자(정수/실수, 언더스코어 구분자 포함) 리스트를 뽑는다."""
    return [
        float(x) if ("." in x or "e" in x.lower()) else int(x)
        for x in re.findall(r"-?\d[\d_]*\.?\d*(?:[eE]-?\d+)?", text.replace("_", ""))
    ]


def java_array(text, name):
    """`name = { ... }` 형태의 Java 배열 리터럴 안 숫자들을 뽑는다. 1-indexed 배열의 선두 0은 그대로 둔다."""
    m = re.search(re.escape(name) + r"\s*=\s*\{([^}]*)\}", text)
    if not m:
        warn(f"Java 배열 못 찾음: {name}")
        return None
    return nums(m.group(1))


# ─────────────────────────────────────────────────────────────
# A. 레벨링 / 성장 곡선
# ─────────────────────────────────────────────────────────────
def pull_leveling():
    src = read_java("fishing/FishingLevelManager.java")
    out = {}
    m = re.search(r"MAX_LV\s*=\s*(\d+)", src)
    out["max_level"] = int(m.group(1)) if m else None
    # base requiredExp: `if (need <= 0) need = 200;` (첫 등장, 값 있는 대입만)
    m = re.search(r"\bneed\s*=\s*(\d+)\s*;", src)
    out["base_req_exp"] = int(m.group(1)) if m else None
    # 구간별 벽 배수: `< N) ... mult = M` 쌍 (addExp/needForLevel 두 블록에 중복 → dedupe)
    tiers = re.findall(r"<\s*(\d+)\)\s*(?:\{)?\s*mult\s*=\s*([\d.]+)", src)
    seen, walls = set(), []
    for a, b in tiers:
        if a not in seen:
            seen.add(a)
            walls.append({"below_level": int(a), "mult": float(b)})
    out["tier_walls"] = walls
    m = re.search(r"else\s+mult\s*=\s*([\d.]+)", src)
    out["tier_wall_top"] = float(m.group(1)) if m else None

    # 등급 해금 마일스톤 (RewardMath.maxGradeNum 또는 GradeRoller.maxGradeNum)
    gr = read_java("fishing/GradeRoller.java")
    ms = re.findall(r"level\s*>=\s*(\d+)\)\s*m\s*=\s*(\d+)", gr)
    out["max_grade_unlock"] = [{"level": int(l), "grade_num": int(g)} for l, g in ms]

    # 파생: 각 마일스톤 레벨까지 누적 요구 경험치 (곡선 변화 추적용)
    out["cumulative_xp"] = cumulative_xp(out)
    return out


def cumulative_xp(lvl):
    base = lvl.get("base_req_exp")
    walls = lvl.get("tier_walls")
    top = lvl.get("tier_wall_top")
    maxlv = lvl.get("max_level") or 100
    if not base or not walls or top is None:
        warn("누적 경험치 계산 스킵 (레벨 곡선 상수 누락)")
        return None

    def mult(lv):
        for w in walls:
            if lv < w["below_level"]:
                return w["mult"]
        return top

    # need(lv→lv+1) = base * prod_{k=1..lv-1} mult(k)
    cum, need, result = 0.0, float(base), {}
    marks = {30, 45, 60, 70, maxlv}
    for lv in range(1, maxlv):
        cum += need
        if (lv + 1) in marks:
            result[str(lv + 1)] = round(cum)
        need *= mult(lv)
    return result


# ─────────────────────────────────────────────────────────────
# B. 경제
# ─────────────────────────────────────────────────────────────
def pull_economy():
    fi = read_java("economy/FishItem.java")
    out = {}
    # 등급 기본가 switch
    prices = dict(re.findall(r'case\s+"([EDCBASMLG])"\s*->\s*(\d+)', fi))
    out["grade_base_price"] = {g: int(v) for g, v in prices.items()}
    # 품질 배율 공식 상수 (0.5 + q*0.5/100)
    m = re.search(r"mult\s*=\s*([\d.]+)\s*\+\s*q\s*\*\s*([\d.]+)\s*/\s*(\d+)", fi)
    out["quality_formula"] = (
        {"floor": float(m.group(1)), "slope": float(m.group(2)), "div": int(m.group(3))}
        if m else None
    )
    # 신선도 감소 버킷: `<= N) return M`
    fr = re.findall(r"ageMins\s*<=\s*(\d+)\)\s*return\s*([\d.]+)", fi)
    tail = re.search(r"return\s*([\d.]+);\s*\n\s*\}", fi)
    out["freshness_buckets"] = [{"age_min_max": int(a), "mult": float(b)} for a, b in fr]

    # 돈 상한
    num = read_java("util/Num.java")
    m = re.search(r"MAX_MONEY\s*=\s*([\d_]+)L", num)
    out["max_money"] = int(m.group(1).replace("_", "")) if m else None

    # 제출 보상 상한 + 등급별 제출가
    subv = read_json("submit-values.json")
    if subv is not None:
        out["submit_fish_by_grade"] = subv.get("fishByGrade")
        out["submit_reward_keys"] = list((subv.get("rewards") or {}).keys())
    isc = read_java("island/IslandSubmitConfig.java")
    m = re.search(r"([\d_]+)\s*/\*.*?cap|cap[^\n]*?([\d_]{4,})", isc)
    m2 = re.search(r"Math\.min\(([\d_]{5,}),", isc)
    out["submit_reward_cap"] = int(m2.group(1).replace("_", "")) if m2 else None

    # 퀘스트 보상 총액 분포 (money 필드 합/최대/개수)
    quests = read_json("quests.json")
    out["quest_rewards"] = summarize_quest_money(quests) if quests is not None else None

    # 별빛진주 드롭율 (강화 핵심 재화 — 지역별 chance%)
    mats = read_json("materials.json")
    if mats is not None:
        pearl = {}
        for area, drops in (mats.get("dropTables") or {}).items():
            for x in drops:
                if x.get("matId") == "별빛진주":
                    pearl[area] = x.get("chance")
        out["pearl_drop_chance"] = pearl
        out["pearl_drop_max"] = max(pearl.values()) if pearl else None

    # AFK 포인트 획득율
    afk = read_java("afk/AfkManager.java")
    m = re.search(r"SWEEP_SEC\s*=\s*(\d+)", afk)
    out["afk_sweep_sec"] = int(m.group(1)) if m else None
    m = re.search(r"DEFAULT_IDLE_SEC\s*=\s*(\d+)", afk)
    out["afk_idle_sec"] = int(m.group(1)) if m else None
    return out


def summarize_quest_money(quests):
    vals = []
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("money", "돈", "reward", "보상돈", "rewardMoney") and isinstance(v, (int, float)):
                    vals.append(v)
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(quests)
    if not vals:
        return {"count": 0, "note": "money 필드 자동탐지 실패 — 퀘스트 보상 키 확인 필요"}
    return {"count": len(vals), "sum": sum(vals), "max": max(vals), "min": min(vals)}


# ─────────────────────────────────────────────────────────────
# C. RNG / 등급
# ─────────────────────────────────────────────────────────────
def pull_rng():
    gr = read_java("fishing/GradeRoller.java")
    out = {}
    entries = re.findall(r'new\s+RollEntry\("([EDCBASMLG])",\s*([\d.eE-]+),\s*(\d+)\)', gr)
    out["grade_base_prob"] = {g: float(p) for g, p, _ in entries}
    out["grade_gate"] = {g: int(gate) for g, _, gate in entries}

    rm = read_java("fishing/RewardMath.java")
    m = re.search(r"comboBonusPct.*?/\s*(\d+),\s*(\d+)\)", rm, re.S)
    out["combo_step"] = int(m.group(1)) if m else None
    out["combo_cap_pct"] = int(m.group(2)) if m else None
    # 등급업 총 확률 캡 (gradeUpChance clamp) — balance.md "30%"와 드리프트 감시 대상
    m = re.search(r"gradeUpChance.*?Math\.min\([^,]+,\s*(\d+)\)", rm, re.S)
    out["grade_up_cap"] = int(m.group(1)) if m else None

    # 카지노 하우스엣지
    casino = {}
    sr = read_java("casino/slot/SlotRules.java")
    for key in ("BET_UNIT", "OUTCOME_TICKETS", "WINNING_TICKETS", "THEORETICAL_RTP_BPS"):
        m = re.search(key + r"\s*=\s*([\d_]+)", sr)
        if m:
            casino[f"slot_{key.lower()}"] = int(m.group(1).replace("_", ""))
    if "slot_theoretical_rtp_bps" in casino:
        casino["slot_house_edge_pct"] = round(100 - casino["slot_theoretical_rtp_bps"] / 100, 2)
    pk = read_java("casino/table/PokerTableRuntime.java")
    m = re.search(r"RAKE_BPS\s*=\s*(\d+)", pk)
    if m:
        casino["poker_rake_pct"] = int(m.group(1)) / 100
    se = read_java("casino/seotda/SeotdaTableEngine.java")
    m = re.search(r"CAP_MULTIPLIER\s*=\s*(\d+)", se)
    if m:
        casino["seotda_cap_mult"] = int(m.group(1))
    out["casino"] = casino
    return out


# ─────────────────────────────────────────────────────────────
# D. 장비 / 강화 / 부품
# ─────────────────────────────────────────────────────────────
def pull_equipment():
    out = {}
    parts = read_json("parts.json")
    if parts is not None:
        p = parts.get("parts", parts)
        counts = {k: len(v) for k, v in p.items()} if isinstance(p, dict) else {}
        out["part_counts"] = counts
        out["part_total"] = sum(counts.values())

    em = read_java("enhance/EnhanceManager.java")
    out["enhance_cost"] = java_array(em, "COST")
    out["enhance_success"] = java_array(em, "SUCCESS")
    out["enhance_down"] = java_array(em, "DOWN")
    out["enhance_pearl"] = java_array(em, "PEARL")
    m = re.search(r"CHECKPOINT\s*=\s*Set\.of\(([^)]*)\)", em)
    out["enhance_checkpoint"] = nums(m.group(1)) if m else None

    # 강화 스탯 증가표 (enhance.json)
    ej = read_json("enhance.json")
    if ej is not None:
        out["enhance_stat_order"] = ej.get("order")
        tbl = ej.get("table")
        out["enhance_stat_levels"] = len(tbl) if isinstance(tbl, (list, dict)) else None

    # 파생: +15/+20 도달 기대 시도횟수(단순 기하 근사, down 무시 — 하한선 추정)
    out["enhance_expected_attempts"] = expected_attempts(out.get("enhance_success"))
    return out


def expected_attempts(success):
    """각 강화 단계 성공률(%)로 +N 도달 기대 시도횟수(down 무시한 낙관적 하한). 1-indexed."""
    if not success:
        return None
    result = {}
    total = 0.0
    for lv in range(1, len(success)):
        s = success[lv]
        if s <= 0:
            result[str(lv + 1)] = None
            continue
        total += 100.0 / s  # 이 단계 통과 기대 시도
        if (lv + 1) in (5, 10, 15, 16, 20):
            result[str(lv + 1)] = round(total, 1)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (Claude가 오늘 날짜를 넘겨줌)")
    ap.add_argument("--out", help="출력 디렉터리 (기본 <스킬>/audits/snapshots)")
    args = ap.parse_args()

    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = args.out or os.path.join(skill_dir, "audits", "snapshots")
    os.makedirs(out_dir, exist_ok=True)

    print("밸런스 스냅샷 추출 중...", file=sys.stderr)
    snapshot = {
        "date": args.date,
        "source_roots": {"java": JAVA_ROOT, "json": JSON_ROOT},
        "raw": {
            "leveling": pull_leveling(),
            "economy": pull_economy(),
            "rng": pull_rng(),
            "equipment": pull_equipment(),
        },
        "warnings": WARNINGS,
        # derived 섹션은 Claude가 감사 시 채운다 (수입/시간, drift 목록 등)
        "derived": {},
    }

    fname = f"{args.date}.raw.json" if args.date else "pending.raw.json"
    path = os.path.join(out_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 스냅샷 저장: {path}", file=sys.stderr)
    if WARNINGS:
        print(f"⚠️  경고 {len(WARNINGS)}건 — 스냅샷 warnings 필드 확인 (정규식이 상수 위치를 놓쳤을 수 있음)", file=sys.stderr)
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
