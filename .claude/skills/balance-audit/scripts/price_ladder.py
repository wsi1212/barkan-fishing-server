#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""price_ladder.py — 장비 가격 사다리 재산출 (2026-08-05 전면 리프라이싱의 근거).

문제(2026-08-05 발견): 장비 가격이 수입 대비 2자리 낮았다. 티어 구간을 다 플레이해서 버는 돈
대비 그 티어 풀세팅 값이 **0.8~3.7%** 였다 → "종결 장비 풀세팅 1시간 43분". 레벨 축(Lv70 목표
46h)보다 장비 축이 27배 빨리 끝나 성장 곡선이 무의미해졌다.

이 스크립트가 하는 일:
  1. 구간별 수입/XP를 GradeRoller 충실복제 몬테카를로로 산출 (★flat 확률 금지 — 피티 반영).
     - 처리량은 텔레메트리 실측 확정치 사용: 낚싯대 220 포획/h, 크기점수 65.6 (2026-08-05 측정,
       활성 사이클 16.2초 = Lure2+바닐라 입질+미니게임의 기계적 하한. audits/2026-08-05 참조).
  2. 레벨 need 테이블로 티어별 체류시간 → 티어 구간 수입 총액.
  3. "풀세팅 = 구간 수입의 TARGET_SET_SHARE" 를 만족하는 등급별 가격 밴드 산출.
  4. 기존 밴드의 마을별 하위분할 비율을 보존한 채 새 밴드로 사상(SUB_BAND 재생성).
  5. 부품 수리 단가(EquipmentManager.gradeUnitRate)도 같이 역산 — 유지비/h = 캐스트/h × 단가라
     내구도와 무관하므로, 단가를 안 고치면 A티어 유지비가 수입의 2배(704,000원/h)가 된다.

사용법: python3 price_ladder.py            # 표 + 생성기에 넣을 dict 출력
"""
import random

# ── 라이브 상수 (코드 권위) ────────────────────────────────────────────────
PRICE = {"E": 100, "D": 250, "C": 600, "B": 2000, "A": 6000,
         "S": 20000, "M": 65000, "L": 170000, "G": 450000}      # FishItem 등급 기본가
BEXP = {"E": 5, "D": 6, "C": 8, "B": 10, "A": 13,
        "S": 17, "M": 30, "L": 40, "G": 55}                      # RewardMath.baseExp
# GradeRoller.ROLL_ORDER (2026-08-04 B/A/S 하향 반영)
ROLL = [("G", 0.0000175, 9), ("L", 0.0021, 8), ("M", 0.0105, 7), ("S", 0.0165, 0),
        ("A", 0.0977, 0), ("B", 0.5712, 0), ("C", 7.13, 0), ("D", 21.12, 0)]
# FishingLevelManager.NEED_TABLE (2026-08-01 초반 너프 반영)
NEED = [500, 521, 534, 546, 556, 566, 575, 583, 591, 599, 607, 614, 621, 628, 635, 642,
        649, 655, 662, 668, 674, 680, 686, 692, 747, 785, 824, 865, 908, 954, 1002, 1052,
        1104, 1159, 1217, 1278, 1342, 1409, 1480, 1554, 1694, 1846, 2013, 2194, 2391, 2606,
        2841, 3097, 3376, 3679, 3900, 4134, 4382, 4645, 4924, 5220, 5533, 5865, 6217, 6590,
        7249, 7974, 8771, 9648, 10613, 11674, 12842, 14126, 15539, 17093, 18802, 20682,
        22751, 25026, 27528, 30281, 33309, 36640, 40304, 44335, 48768, 53645, 59010, 64911,
        71402, 78542, 86397, 95036, 104540, 114994, 126494, 139143, 153057, 168363, 185200,
        203720, 224092, 246501, 271151, 298266]

# ── 실측 파라미터 (2026-08-05 prod 텔레메트리) ─────────────────────────────
CATCH_PER_HOUR = 220          # 낚싯대 활성 사이클 16.2s + 완주율 85% → 220 포획/h
SIZE_SCORE = 65.6             # 실측 평균 크기점수
PRICE_MULT = 0.5 + SIZE_SCORE / 200.0   # 가격 배율 0.828
XP_MULT = 0.5 + SIZE_SCORE / 100.0      # XP 배율 1.156

# ── 설계 목표 ─────────────────────────────────────────────────────────────
TARGET_SET_SHARE = 0.45   # 풀세팅 = 그 티어 구간에 버는 돈의 45%
ROD_WEIGHT = 2.0          # 낚싯대/작살은 내구 없음(유지비 0) 프리미엄 → 부품 2배
PART_SLOTS = 5            # 릴·줄·바늘·미끼·찌
BAND_MIN_RATIO = 0.40     # 밴드 하한 = 상한의 40% (기존 밴드 모양 유지)
S_BAND_MIN_RATIO = 0.94   # ★S만 예외 — 원래도 85,000~90,000의 좁은 밴드였다(종결등급은 값이 수렴)
MAINT_SHARE = 0.10        # 부품 4개 수리 유지비 = 티어 수입의 10%
BAIT_MAINT_SHARE = 0.03   # 미끼(소모품) 유지비 = 티어 수입의 3%. ★A티어 기준으로 배수를 고정한다
                          #   (티어 평균으로 잡으면 저티어 밴드 비율에 끌려 A에서 3배로 튄다)

# 티어 = (등급, 레벨 구간, 그 구간에서 접근 가능한 지역 어종 등급집합)
STAGES = [
    ("D", 5, 9, set("EDCBA")),          # 스폰도시
    ("C", 10, 19, set("EDCBAS")),       # 스폰+강
    ("B", 20, 39, set("EDCBAS")),       # 강/붉은사막
    ("A", 40, 59, set("EDCBASML")),     # 정상/원양어선
    ("S", 60, 70, set("EDCBASMLG")),    # 늪지대
]


def mc(pool, level, luck=0, n=400_000, seed=20260805):
    """GradeRoller.roll 충실복제 — 피티 영속·미가용 등급 스킵·레벨캡 반영."""
    rnd = random.Random(seed)
    mg = 6
    if level >= 30: mg = 7
    if level >= 45: mg = 8
    if level >= 60: mg = 9
    lm = (100.0 + luck) / 100.0
    pity = {k: 0 for k in "GLMSABCD"}
    won = xp = 0.0
    for _ in range(n):
        g = "E"
        for gr, base, gate in ROLL:
            if g != "E": break
            if gate > 0 and mg < gate: continue
            if gr not in pool: continue
            if rnd.random() < base * lm * (1 + pity[gr]) / 100.0:
                g = gr; pity[gr] = 0
        for k in pity:
            if k != g: pity[k] += 1
        won += PRICE[g] * PRICE_MULT
        xp += BEXP[g] * XP_MULT
    return won / n, xp / n


def stage_table():
    rows = []
    for grade, l0, l1, pool in STAGES:
        w, x = mc(pool, (l0 + l1) // 2)
        need = sum(NEED[i] for i in range(l0, min(l1 + 1, len(NEED))))
        hours = need / (x * CATCH_PER_HOUR)
        rows.append(dict(grade=grade, l0=l0, l1=l1, won_catch=w, won_h=w * CATCH_PER_HOUR,
                         xp_catch=x, hours=hours, seg_income=w * CATCH_PER_HOUR * hours))
    return rows


def round_to(v, step):
    return int(round(v / step) * step)


def bands(rows):
    """등급별 (부품 상한, 낚싯대 상한) → 밴드."""
    weight = ROD_WEIGHT + PART_SLOTS
    part, rod = {}, {}
    for r in rows:
        budget = r["seg_income"] * TARGET_SET_SHARE
        unit = budget / weight
        step = 1000 if unit < 100_000 else 10_000
        phi = round_to(unit, step)
        rhi = round_to(unit * ROD_WEIGHT, step)
        ratio = S_BAND_MIN_RATIO if r["grade"] == "S" else BAND_MIN_RATIO
        part[r["grade"]] = (round_to(phi * ratio, step), phi)
        rod[r["grade"]] = (round_to(rhi * ratio, step), rhi)
    return part, rod


def monotonic(band, order):
    """밴드 겹침 제거 — 하위 등급 상한 < 상위 등급 하한."""
    out, prev_hi = {}, 0
    for g in order:
        if g not in band: continue
        lo, hi = band[g]
        lo = max(lo, int(prev_hi * 1.05))
        out[g] = (lo, hi)
        prev_hi = hi
    return out


def remap(old_sub, old_band, new_band):
    """기존 SUB_BAND의 밴드 내 상대위치를 새 밴드로 사상 (마을 성장경로 보존)."""
    out = {}
    for (vil, grade), (lvb, prb) in old_sub.items():
        if grade not in old_band or grade not in new_band:
            out[(vil, grade)] = (lvb, prb); continue
        olo, ohi = old_band[grade]; nlo, nhi = new_band[grade]
        span = (ohi - olo) or 1
        t0 = (prb[0] - olo) / span; t1 = (prb[1] - olo) / span
        step = 1000 if nhi < 100_000 else 10_000
        out[(vil, grade)] = (lvb, (round_to(nlo + t0 * (nhi - nlo), step),
                                   round_to(nlo + t1 * (nhi - nlo), step)))
    return out


def fmt_band(name, band):
    inner = ", ".join(f'"{g}": ({lo}, {hi})' for g, (lo, hi) in band.items())
    return f"{name} = {{{inner}}}"


def fmt_sub(name, sub):
    lines = [f"{name} = {{"]
    for (vil, grade), (lvb, prb) in sub.items():
        key = f'("{vil}", "{grade}"):'
        lines.append(f"    {key:<22}({lvb}, {prb}),")
    lines.append("}")
    return "\n".join(lines)


# 기존 밴드/하위밴드 (리프라이싱 전 — 사상 기준)
OLD_ROD_BAND = {"D": (280, 600), "C": (1100, 2500), "B": (4200, 10000),
                "A": (15500, 43000), "S": (85000, 90000)}
OLD_ROD_SUB = {("스폰마을", "B"): ((20, 27), (4200, 7500)), ("사막마을", "B"): ((26, 34), (7000, 10000)),
               ("사막마을", "A"): ((40, 45), (15500, 24000)), ("상단마을", "A"): ((44, 50), (24000, 33000)),
               ("왕도", "A"): ((50, 54), (33000, 39000)), ("히든", "A"): ((52, 58), (36000, 43000))}
OLD_SPEAR_BAND = {"D": (280, 600), "C": (1100, 2500), "B": (4500, 10000),
                  "A": (16000, 43000), "S": (85000, 90000)}
OLD_SPEAR_SUB = {("스폰마을", "B"): ((20, 27), (4500, 7500)), ("스폰마을", "C"): ((10, 18), (1100, 2500)),
                 ("사막마을", "B"): ((26, 34), (7000, 10000)), ("사막마을", "A"): ((40, 46), (16000, 26000)),
                 ("상단마을", "A"): ((45, 52), (26000, 36000)), ("왕도", "A"): ((50, 55), (36000, 43000))}
OLD_PART_BAND = {"D": (250, 600), "C": (1000, 2500), "B": (4000, 10000), "A": (15000, 25000)}
OLD_PART_SUB = {("스폰마을", "B"): ((20, 27), (4000, 7000)), ("사막마을", "B"): ((28, 34), (7000, 10000)),
                ("사막마을", "A"): ((40, 44), (15000, 18500)), ("상단마을", "A"): ((44, 49), (18500, 23000)),
                ("왕도", "A"): ((49, 52), (23000, 25000))}
OLD_UNIT_RATE = {"E": 50, "D": 100, "C": 200, "B": 400, "A": 800, "S": 1500,
                 "M": 6000, "L": 12000, "G": 25000}


def main():
    rows = stage_table()
    print(f"기준: {CATCH_PER_HOUR} 포획/h · 크기점수 {SIZE_SCORE} (2026-08-05 prod 실측)\n")
    print(f"{'티어':<4}{'레벨':>9}{'원/포획':>9}{'원/h':>11}{'구간h':>8}{'구간수입':>14}")
    print("─" * 58)
    for r in rows:
        print(f"{r['grade']:<4}{f'{r[chr(108)+chr(48)]}~{r[chr(108)+chr(49)]}':>9}"
              f"{r['won_catch']:>9,.0f}{r['won_h']:>11,.0f}{r['hours']:>8.2f}{r['seg_income']:>14,.0f}")

    part, rod = bands(rows)
    order = ["E", "D", "C", "B", "A", "S"]
    part = monotonic({g: v for g, v in part.items() if g != "S"}, order)  # 부품은 A까지
    rod = monotonic(rod, order)

    print(f"\n{'티어':<4}{'구세팅':>12}{'신세팅':>14}{'구/구간수입':>12}{'신/구간수입':>12}")
    print("─" * 58)
    for r in rows:
        g = r["grade"]
        old_set = OLD_ROD_BAND.get(g, (0, 0))[1] + PART_SLOTS * OLD_PART_BAND.get(g, OLD_PART_BAND["A"])[1]
        new_set = rod[g][1] + PART_SLOTS * part.get(g, part["A"])[1]
        print(f"{g:<4}{old_set:>12,}{new_set:>14,}{old_set/r['seg_income']*100:>11.1f}%"
              f"{new_set/r['seg_income']*100:>11.1f}%")

    # 미끼 배수: A티어(최고 부품등급)에서 유지비가 수입의 BAIT_MAINT_SHARE가 되도록 고정.
    BAIT_DUR = {"D": 70, "C": 130, "B": 220, "A": 340}
    ra = next(r for r in rows if r["grade"] == "A")
    bait_mult = round(ra["won_h"] * BAIT_MAINT_SHARE * BAIT_DUR["A"]
                      / CATCH_PER_HOUR / part["A"][1], 4)

    # 수리 단가: 유지비/h = 캐스트/h × 단가 (★내구도와 무관 — 1캐스트에 1점씩 깎이므로)
    #   → 4부품 합계가 티어 수입의 MAINT_SHARE가 되도록 역산. 등급 단조는 강제.
    unit = {}
    for r in rows:
        if r["grade"] == "S": continue
        unit[r["grade"]] = max(1, round(r["won_h"] * MAINT_SHARE / (4 * CATCH_PER_HOUR)))
    unit["E"] = 5
    prev = 0
    for g in ["E", "D", "C", "B", "A"]:
        unit[g] = max(unit[g], prev + 3 if prev else unit[g])
        prev = unit[g]
    for g, v in (("S", 60), ("M", 100), ("L", 150), ("G", 220)):
        unit[g] = v                      # 부품엔 없는 등급(사문화) — 비율만 유지

    print("\n" + "=" * 70)
    print("생성기에 넣을 값")
    print("=" * 70)
    print("\n# gen_rod_builds.py")
    print(fmt_band("PRICE_BAND", rod))
    print(fmt_sub("SUB_BAND", remap(OLD_ROD_SUB, OLD_ROD_BAND, rod)))
    print("\n# gen_spear_builds.py")
    print(fmt_band("PRICE_BAND", rod))
    print(fmt_sub("SUB_BAND", remap(OLD_SPEAR_SUB, OLD_SPEAR_BAND, rod)))
    print("\n# gen_part_builds.py")
    print(fmt_band("PRICE_BAND", part))
    print(fmt_sub("SUB_BAND", remap(OLD_PART_SUB, OLD_PART_BAND, part)))
    print(f"BAIT_PRICE_MULT = {bait_mult}")
    print("\n# EquipmentManager.gradeUnitRate (부품 수리 단가, 원/내구1점)")
    for g in ["E", "D", "C", "B", "A", "S", "M", "L", "G"]:
        old = OLD_UNIT_RATE[g]
        cost_h = 220 * unit[g] * 4
        print(f"  {g}: {old:>6} → {unit[g]:>5}   (4부품 유지비 {cost_h:>9,}원/h)")


if __name__ == "__main__":
    main()
