import random

ROLL_ORDER_BASE = {"G": 0.0000035, "L": 0.00035, "M": 0.0035, "S": 0.21, "A": 0.7, "B": 1.868, "C": 7.13, "D": 21.12}
ORDER = ["G", "L", "M", "S", "A", "B", "C", "D"]  # 희귀→흔함, 순서대로 시도

def simulate_avg_casts(base_overrides, target_grade, trials=3000, max_casts=200000):
    bases = dict(ROLL_ORDER_BASE)
    bases.update(base_overrides)
    rng = random.Random(42)
    totals = []
    for _ in range(trials):
        pity = {g: 0 for g in ORDER}
        casts = 0
        while casts < max_casts:
            casts += 1
            grade = "E"
            for g in ORDER:
                if grade != "E":
                    break
                prob = bases[g] * (1 + pity[g])
                if rng.random() * 100 < prob:
                    grade = g
                    pity[g] = 0
            for g in ORDER:
                if g != grade:
                    pity[g] += 1
            if grade == target_grade:
                totals.append(casts)
                break
    return sum(totals) / len(totals) if totals else None, len(totals)

if __name__ == "__main__":
    print("=== 현재 base 기준 검증 ===")
    for g in ["M", "L", "G"]:
        avg, n = simulate_avg_casts({}, g, trials=2000)
        print(f"{g}: 평균 {avg:.0f}캐스트 (n={n})")

    print("\n=== 후보 배율 테스트 ===")
    candidates = {
        "M": [0.0035*3, 0.0035*5, 0.0035*8],
        "L": [0.00035*3, 0.00035*5, 0.00035*8],
        "G": [0.0000035*5, 0.0000035*8, 0.0000035*15],
    }
    for g, vals in candidates.items():
        for v in vals:
            avg, n = simulate_avg_casts({g: v}, g, trials=1500)
            mult = v / ROLL_ORDER_BASE[g]
            print(f"{g} base×{mult:.1f} ({v:.7f}): 평균 {avg:.0f}캐스트 = {avg/150:.1f}h@150캐스트/h")
