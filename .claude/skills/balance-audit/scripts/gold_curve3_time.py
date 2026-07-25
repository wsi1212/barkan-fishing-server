"""레벨→실제시간 변환 후 골드곡선을 '시간축'으로 재투영."""
import json, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-user-Library-Application-Support-feather-player-server-servers-07de2d81-991a-47e2-b62d-06c0d1b5150a-plugins-Skript-scripts/2c80f7f6-f6b3-4393-90ef-2d96a0f2a58a/scratchpad")
from gold_curve2 import (best_in_slot, skilltree_stats, guild_stats, merge, compute_income,
                          CATS, qmult, CASTS_PER_HOUR)

BASE_EXP = {"E": 5, "D": 6, "C": 8, "B": 10, "A": 13, "S": 17, "M": 30, "L": 40, "G": 55}


def need_for_level(target_lv):
    need = 200.0
    for lv in range(1, target_lv):
        if lv < 15: mult = 1.04
        elif lv < 25: mult = 1.08
        elif lv < 40: mult = 1.05
        elif lv < 50: mult = 1.09
        elif lv < 60: mult = 1.06
        else: mult = 1.10
        need *= mult
    return need


# 검증: 스냅샷 cumulative_xp와 대조
def cumulative_xp(target_lv):
    return sum(need_for_level(lv) for lv in range(2, target_lv + 1))


if __name__ == "__main__":
    print("검증(스냅샷 대조): Lv30", round(cumulative_xp(30)), "(기대 12807)")
    print("검증: Lv60", round(cumulative_xp(60)), "(기대 96931)")
    print("검증: Lv70", round(cumulative_xp(70)), "(기대 201961)")
    print("검증: Lv100", round(cumulative_xp(100)), "(기대 3013697)")
    print()

    from gold_curve2 import bite_dist

    def exp_per_hour(level, stats, quality=50):
        exp_bonus = stats.get("경험치", 0) / 100.0
        luck = stats.get("행운", 0)
        gradeup = stats.get("등급업", 0)
        dist = bite_dist(level, luck, gradeup)
        m = qmult(quality)
        avg_exp = sum(dist.get(g, 0) * BASE_EXP.get(g, 5) * m for g in BASE_EXP)
        return avg_exp * CASTS_PER_HOUR * (1 + exp_bonus)

    cumulative_hours = 0.0
    rows = []
    for lv in range(1, 101):
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
        stats = merge(gear, enhance_extra, skill, guild)

        eph = exp_per_hour(lv, stats)
        need = need_for_level(lv + 1) if lv < 100 else 0
        hours_this_level = need / eph if eph > 0 else 0
        cumulative_hours += hours_this_level

        if lv in (1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100) or lv % 10 == 0:
            income, rb = compute_income(lv, stats)
            rows.append((lv, round(cumulative_hours, 1), round(income)))

    print(f"{'Lv':>4} {'누적시간(h)':>12} {'원/h':>10}")
    for lv, hrs, inc in rows:
        print(f"{lv:>4} {hrs:>12,.1f} {inc:>10,.0f}")

    with open("gold_curve3_time.json", "w") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
