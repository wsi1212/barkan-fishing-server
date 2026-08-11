"""레벨별 평균 스탯 → 골드/h 곡선. best-in-slot 가정 + 미니게임 성공률 반영 풀파이프라인."""
import json, sys
sys.path.insert(0, "/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Skript/scripts/.agents/skills/balance-audit/scripts")
import stat_value as sv
from minigame_sim import simulate_catch, ms_to_ticks

PARTS_PATH = "/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip/parts.json"
SNAP_PATH = "/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Skript/scripts/.agents/skills/balance-audit/audits/snapshots/2026-07-24.raw.json"

snap = sv.load_snapshot(SNAP_PATH)
income0, avg0, dist0, V = sv.compute(snap, 150, 50)
PER_UNIT = {name: won for name, (won, why) in V.items()}
NAME_MAP = {
    "경험치": "경험치 (1%)", "크기": "크기 (1%)", "등급업": "등급업 (1%)", "도망감소": "도주감소 (1%)",
    "크리확률": "크리확률 (1%)", "크리배율": "크리배율 (1점)", "더블찬스": "더블찬스 (1%)",
    "트리플찬스": "트리플찬스 (1%)", "판매보너스": "판매보너스 (1%)", "난이도": "난이도 (1점)",
    "행운": "행운 (1점)",
}

with open(PARTS_PATH) as f:
    parts = json.load(f)["parts"]

CATS = ["낚싯대", "릴", "줄", "바늘", "미끼", "찌"]


def parse_item(raw):
    f = raw.split("|")
    name, grade, price, dur, statstr, lvl = f[0], f[1], f[2], f[3], f[4], f[5]
    stats = {}
    for kv in statstr.split(","):
        if ":" not in kv:
            continue
        k, v = kv.split(":", 1)
        try:
            stats[k] = float(v)
        except ValueError:
            pass
    return dict(name=name, grade=grade, price=int(price), lvl=int(lvl), stats=stats)


def stat_value_score(stats):
    s = 0.0
    for k, v in stats.items():
        key = NAME_MAP.get(k)
        if key:
            s += PER_UNIT.get(key, 0) * v
    return s


def best_in_slot(cat, max_level):
    items = [parse_item(raw) for raw in parts[cat].values()]
    items = [it for it in items if it["lvl"] <= max_level and it["lvl"] > 0 or (it["lvl"] == 0 and it["grade"] != "S")]
    items = [it for it in items if not (it["grade"] == "S" and it["lvl"] == 0)]  # 개발자 아이템 제외
    if not items:
        return None
    return max(items, key=lambda it: stat_value_score(it["stats"]))


LEVELS = [1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

# GradeRoller 신규 base(2026-07-25 상향분) 기준 실효 확률(피티 평균캐스트 역산, 몬테카를로 재검증치)
NEW_PITY_AVG_CASTS = {"M": 122, "L": 277, "G": 3002}
BASE_PROB_PCT = {"D": 21.12, "C": 7.13, "B": 1.868, "A": 0.7, "S": 0.21}
PRICE = {"E": 100, "D": 250, "C": 600, "B": 2000, "A": 6000, "S": 20000, "M": 65000, "L": 170000, "G": 450000}
GRADE_ORDER = ["E", "D", "C", "B", "A", "S", "M", "L", "G"]
CASTS_PER_HOUR = 150
REACTION_MS, PING_MS = 250, 50
DELAY_TICKS = ms_to_ticks(REACTION_MS + PING_MS)


def max_grade_gate(level):
    if level >= 60:
        return 9
    if level >= 45:
        return 8
    if level >= 30:
        return 7
    return 6


def bite_dist(level, luck, gradeup_pct):
    gate = max_grade_gate(level)
    luck_mult = (100 + luck) / 100.0
    p = {}
    for g in ["D", "C", "B", "A", "S"]:
        p[g] = BASE_PROB_PCT[g] / 100.0 * luck_mult
    for g, avgc in NEW_PITY_AVG_CASTS.items():
        rank = GRADE_ORDER.index(g) + 1
        if rank > gate:
            p[g] = 0.0
        else:
            p[g] = (1.0 / avgc) * luck_mult
    # 등급업: gradeup% 확률로 한 티어 상승 (인접 등급으로 질량 이동, 단순 근사)
    order = ["E", "D", "C", "B", "A", "S", "M", "L", "G"]
    base_p = {"E": max(0.0, 1 - sum(p.values()))}
    base_p.update(p)
    shift = gradeup_pct / 100.0
    shifted = dict(base_p)
    for i in range(len(order) - 1):
        g, nxt = order[i], order[i + 1]
        if base_p.get(g, 0) <= 0:
            continue
        moved = base_p[g] * shift
        shifted[g] = shifted.get(g, 0) - moved
        shifted[nxt] = shifted.get(nxt, 0) + moved
    return shifted


def qmult(q):
    return 0.5 + q * 0.5 / 100.0


def compute_income(level, gear_stats, enhance_extra, quality=50):
    stats = dict(gear_stats)
    for k, v in enhance_extra.items():
        stats[k] = stats.get(k, 0) + v
    luck = stats.get("행운", 0)
    gradeup = stats.get("등급업", 0)
    rodBonus = int(stats.get("난이도", 0))
    crit_rate = min(1.0, stats.get("크리확률", 0) / 100.0)
    crit_dmg = 1 + stats.get("크리배율", 0)
    sell_bonus = stats.get("판매보너스", 0) / 100.0
    dbl = stats.get("더블찬스", 0) / 100.0
    trp = stats.get("트리플찬스", 0) / 100.0
    fish_mult = 1 + dbl + 2 * trp

    dist = bite_dist(level, luck, gradeup)
    m = qmult(quality)
    total = 0.0
    for g in GRADE_ORDER:
        pbite = dist.get(g, 0)
        if pbite <= 0:
            continue
        psucc = 1.0 if g in ("E", "D", "C") else simulate_catch(g, rodBonus, 0, DELAY_TICKS, 4000, seed=hash((level, g, rodBonus)) & 0xffffffff)
        price = PRICE[g] * m * (1 + sell_bonus) * (1 + crit_rate * crit_dmg * 0.06)
        total += pbite * psucc * price
    return total * CASTS_PER_HOUR * fish_mult, rodBonus, dist


if __name__ == "__main__":
    print(f"{'Lv':>4} {'최대등급':>6} {'장비만(원/h)':>14} {'+풀강화(원/h)':>14} {'난이도(장비)':>10} {'난이도(+강화)':>10}")
    results = []
    for lv in LEVELS:
        gear = {}
        for cat in CATS:
            it = best_in_slot(cat, lv)
            if it is None:
                continue
            for k, v in it["stats"].items():
                gear[k] = gear.get(k, 0) + v
        income_gear, rb_gear, _ = compute_income(lv, gear, {})
        # 강화 최대(모든 슬롯 만렙 강화) — enhance.json 대표치: 낚싯대만 강화 시뮬 반영(단순화: 난이도만 +4, 다른스탯 비례추정 생략)
        enhance_extra = {"난이도": 4} if lv >= 40 else ({"난이도": 1} if lv >= 10 else {})
        income_full, rb_full, _ = compute_income(lv, gear, enhance_extra)
        results.append((lv, income_gear, income_full, rb_gear, rb_gear + enhance_extra.get("난이도", 0)))
        print(f"{lv:>4} {max_grade_gate(lv):>6} {income_gear:>14,.0f} {income_full:>14,.0f} {rb_gear:>10} {rb_gear+enhance_extra.get('난이도',0):>10}")

    with open("gold_curve.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
