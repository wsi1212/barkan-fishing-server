"""레벨별 골드곡선 v2 — 스킬트리(연속성장) + 길드버프 반영, 조밀한 레벨 샘플링."""
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
    # 골드곡선 전용 스코어러 — 경험치는 compute_income에 전혀 안 쓰이므로(레벨링 전용)
    # best-in-slot 픽에서 제외(포함 시 경험치 특화 아이템이 순수 소득 무관하게 항상 최선으로 뽑히는 왜곡).
    s = 0.0
    for k, v in stats.items():
        if k == "경험치":
            continue
        key = NAME_MAP.get(k)
        if key:
            s += PER_UNIT.get(key, 0) * v
    return s


def best_in_slot(cat, max_level):
    items = [parse_item(raw) for raw in parts[cat].values()]
    items = [it for it in items if not (it["grade"] == "S" and it["lvl"] == 0)]
    items = [it for it in items if it["lvl"] <= max_level]
    if not items:
        return None
    return max(items, key=lambda it: stat_value_score(it["stats"]))


# ===== 스킬트리 (SkillTreeManager.java 낚시 트리 그대로 포팅) =====
# (statKey, maxRank, perRank) — proc 노드는 None (스탯 미기여, 1점 소모만)
BRANCHES = {
    "만선": [("더블찬스", 15, 0.3), ("트리플찬스", 12, 0.2), (None, 1, 0), ("판매보너스", 10, 0.8), (None, 1, 0)],
    "대물": [("크기", 15, 0.8), ("크리확률", 20, 1.5), (None, 1, 0), ("크리배율", 7, 1.0), (None, 1, 0)],
    "심해": [("행운", 15, 1.0), ("등급업", 12, 0.7), (None, 1, 0), ("도망감소", 15, 2.0), (None, 1, 0)],
}
ROOT = ("경험치", 5, 2.0)


def skilltree_stats(total_points):
    """레벨-1 포인트를 근원 우선 채우고, 이후 3계열 라운드로빈 순차투자(각 계열 내부는 노드 순서 고정)."""
    stats = {}
    remaining = total_points
    # 근원
    root_rank = min(ROOT[1], remaining)
    stats[ROOT[0]] = stats.get(ROOT[0], 0) + root_rank * ROOT[2]
    remaining -= root_rank
    # 계열별 진행 포인터(노드 인덱스, 그 노드 내 랭크)
    ptr = {b: [0, 0] for b in BRANCHES}
    while remaining > 0:
        progressed = False
        for b in BRANCHES:
            if remaining <= 0:
                break
            nodes = BRANCHES[b]
            idx, rank = ptr[b]
            if idx >= len(nodes):
                continue
            statKey, maxRank, perRank = nodes[idx]
            rank += 1
            remaining -= 1
            progressed = True
            if statKey:
                stats[statKey] = stats.get(statKey, 0) + perRank
            if rank >= maxRank:
                idx += 1
                rank = 0
            ptr[b] = [idx, rank]
        if not progressed:
            break
    return stats


# ===== 길드 버프 (GuildManager.BUFF_DEFS, "평균적으로 자금 모은 길드" 가정 시나리오) =====
def guild_stats(level_of_guild=2):
    # 경험치부스트/크기부스트/등급업부스트/더블확률, 레벨1~3, values[level-1]
    if level_of_guild <= 0:
        return {}
    return {
        "경험치": [5, 10, 15][level_of_guild - 1],
        "크기": [3, 7, 12][level_of_guild - 1],
        "등급업": [1, 2, 3][level_of_guild - 1],
        "더블찬스": [2, 4, 6][level_of_guild - 1],
    }


LEVELS = list(range(1, 101, 5)) + [100]
LEVELS = sorted(set(LEVELS))

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
        p[g] = 0.0 if rank > gate else (1.0 / avgc) * luck_mult
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


def compute_income(level, stats, quality=50):
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
        psucc = 1.0 if g in ("E", "D", "C") else simulate_catch(g, rodBonus, 0, DELAY_TICKS, 8000, seed=hash((level, g, rodBonus)) & 0xffffffff)
        price = PRICE[g] * m * (1 + sell_bonus) * (1 + crit_rate * crit_dmg * 0.06)
        total += pbite * psucc * price
    return total * CASTS_PER_HOUR * fish_mult, rodBonus


def merge(*dicts):
    out = {}
    for d in dicts:
        for k, v in d.items():
            out[k] = out.get(k, 0) + v
    return out


if __name__ == "__main__":
    print(f"{'Lv':>4} {'티어':>6} {'장비':>10} {'+강화':>10} {'+스킬트리':>12} {'+길드':>12} {'난이도':>6}")
    rows = []
    for lv in LEVELS:
        gear = {}
        for cat in CATS:
            it = best_in_slot(cat, lv)
            if it is None:
                continue
            for k, v in it["stats"].items():
                gear[k] = gear.get(k, 0) + v
        enhance_extra = {"난이도": 4} if lv >= 40 else ({"난이도": 1} if lv >= 10 else {})
        skill = skilltree_stats(max(0, lv - 1))
        guild = guild_stats(2) if lv >= 15 else {}

        inc_gear, rb = compute_income(lv, gear)
        inc_enh, rb2 = compute_income(lv, merge(gear, enhance_extra))
        inc_skill, rb3 = compute_income(lv, merge(gear, enhance_extra, skill))
        inc_guild, rb4 = compute_income(lv, merge(gear, enhance_extra, skill, guild))
        tier = "초보" if lv < 20 else "중수" if lv < 40 else "중고수" if lv < 60 else "고수"
        rows.append((lv, tier, inc_gear, inc_enh, inc_skill, inc_guild, rb4))
        print(f"{lv:>4} {tier:>6} {inc_gear:>10,.0f} {inc_enh:>10,.0f} {inc_skill:>12,.0f} {inc_guild:>12,.0f} {rb4:>6}")

    with open("gold_curve2.json", "w") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
