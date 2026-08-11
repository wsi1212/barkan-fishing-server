"""
낚시 미니게임(MinigameManager.java) 충실 포팅 시뮬레이터.
목적: "난이도"(rodBonus) 스탯과 "도주감소"(escapeReduction) 스탯의 실제 원/h 가치를
      인간 평균 반응속도 + 서버 핑을 반영한 성공확률 시뮬레이션으로 산출.

핵심 공식 (MinigameTables.java 그대로 포팅):
  net = rodBonus - fishDifficulty(grade) - sizeDifficulty(size)
  barWidth = clamp(14 - net, 12, 30)
  zoneWidth = clamp(8 + floor(net/2), 1, 10)  (0 밑으로는 overflowDiff로 흡수)
  escapeBase = clamp(params.escapeBase - floor(escapeReduction/2) - floor(net/4) + envEscape, 1, 100)
"""
import random
import math
import json
from pathlib import Path

TICK_MS = 50  # 1틱 = 50ms

PARAMS = {
    # grade: (zoneWidth_base8, escapeBase, escapeInc, cursorSpeed, shiftPattern, spotMoveSpeed, dirChange, consecutive)
    "E": dict(escapeBase=30, escapeInc=5,  cursorSpeed=250, shiftPattern=0, spotMoveSpeed=0, dirChange=0,  consecutive=1),
    "D": dict(escapeBase=40, escapeInc=6,  cursorSpeed=250, shiftPattern=0, spotMoveSpeed=0, dirChange=0,  consecutive=1),
    "C": dict(escapeBase=50, escapeInc=8,  cursorSpeed=250, shiftPattern=1, spotMoveSpeed=0, dirChange=0,  consecutive=1),
    "B": dict(escapeBase=60, escapeInc=10, cursorSpeed=250, shiftPattern=1, spotMoveSpeed=1, dirChange=0,  consecutive=1),
    "A": dict(escapeBase=70, escapeInc=13, cursorSpeed=250, shiftPattern=2, spotMoveSpeed=1, dirChange=12, consecutive=1),
    "S": dict(escapeBase=80, escapeInc=16, cursorSpeed=300, shiftPattern=2, spotMoveSpeed=2, dirChange=10, consecutive=1),
    "M": dict(escapeBase=90, escapeInc=25, cursorSpeed=400, shiftPattern=3, spotMoveSpeed=3, dirChange=6,  consecutive=2),
    "L": dict(escapeBase=95, escapeInc=30, cursorSpeed=450, shiftPattern=4, spotMoveSpeed=3, dirChange=5,  consecutive=3),
    "G": dict(escapeBase=98, escapeInc=35, cursorSpeed=500, shiftPattern=4, spotMoveSpeed=3, dirChange=3,  consecutive=3),  # gPattern 무시(라이브에선 5~6, 여기선 보수적으로 4 재사용)
}

FISH_DIFFICULTY = {"E": 0, "D": 2, "C": 4, "B": 8, "A": 12, "S": 16, "M": 24, "L": 28, "G": 32}

MAX_STEPS = 200  # 라이브 startJava 기본값(10초)


def speed_mult(step, pattern):
    if pattern == 0:
        return 100
    if pattern == 1:
        ph = step % 20
        return 90 if ph < 5 else 110 if ph < 10 else 120 if ph < 15 else 80
    if pattern == 2:
        ph = step % 12
        return 80 if ph < 3 else 130 if ph < 6 else 70 if ph < 9 else 140
    if pattern == 3:
        ph = step % 32
        return 70 if ph < 8 else 130 if ph < 16 else 60 if ph < 24 else 160
    if pattern == 4:
        ph = step % 30
        if ph < 5: return 60
        if ph < 10: return 180
        if ph < 15: return 50
        if ph < 20: return 200
        if ph < 25: return 80
        return 150
    return 100


def derive(grade, rod_bonus, escape_reduction, size=0, env_diff=0, env_escape=0):
    p = PARAMS[grade]
    net = rod_bonus - FISH_DIFFICULTY[grade] - size
    bar_width = 14 - net
    bar_width = max(12, min(30, bar_width))
    zone_width = 8 + math.floor(net / 2.0)
    overflow_diff = 0
    if zone_width < 1:
        overflow_diff = 1 - zone_width
        zone_width = 1
    if zone_width > 10:
        zone_width = 10
    if env_diff > 0:
        zone_width = max(1, zone_width - env_diff)
    bar_width = max(bar_width, zone_width + 2)
    escape_base = p["escapeBase"] - math.floor(escape_reduction / 2.0) - math.floor(net / 4.0) + env_escape
    escape_base = max(1, min(100, escape_base))
    return dict(net=net, bar_width=bar_width, zone_width=zone_width, overflow_diff=overflow_diff,
                escape_base=escape_base, escape_inc=p["escapeInc"], cursor_speed=p["cursorSpeed"],
                shift_pattern=p["shiftPattern"], spot_move_speed=p["spotMoveSpeed"], dir_change=p["dirChange"],
                consecutive=p["consecutive"])


def simulate_round(d, delay_ticks, rng):
    """한 라운드 시뮬레이션. 반환: 'success' | 'escape' | 'timeout'"""
    bar_width = d["bar_width"]; zone_width = d["zone_width"]
    max_start = max(0, bar_width - zone_width)
    zone_start = rng.randint(0, max_start)
    zone_end = zone_start + zone_width - 1
    cursor = 0; direction = 1; frac = 0.0
    spot_dir = 1 if rng.random() < 0.5 else -1
    spot_move_interval = max(1, 6 - d["spot_move_speed"] + math.floor(d["net"] / 4.0)) if d["spot_move_speed"] > 0 else 999
    spot_frac = 0.0; spot_state = 0; spot_cooldown = 0
    zone_move_count = 0
    zone_move_interval = max(3, 8 - d["overflow_diff"]) if d["overflow_diff"] > 0 else 999
    escape_chance = d["escape_base"]
    was_in_zone = (zone_start <= cursor <= zone_end)
    zone_enter_tick = 0
    pending_click_tick = None  # 예약된 클릭 발동 tick (반응지연 반영)

    for tick in range(1, MAX_STEPS + 1):
        frac += d["cursor_speed"] / 400.0
        moved = False
        while frac >= 1:
            frac -= 1
            max_cursor = bar_width - 1
            cursor += direction
            if cursor >= max_cursor:
                cursor = max_cursor; direction = -1
            if cursor <= 0:
                cursor = 0; direction = 1
            moved = True
        if moved:
            if d["overflow_diff"] > 0:
                zone_move_count += 1
                if zone_move_count >= zone_move_interval:
                    zone_move_count = 0
                    zone_start = rng.randint(0, max(0, bar_width - zone_width))
                    zone_end = zone_start + zone_width - 1
            if d["spot_move_speed"] > 0:
                if spot_cooldown > 0:
                    spot_cooldown -= 1
                    if spot_cooldown == 0:
                        spot_state = 0
                else:
                    mult = speed_mult(tick, d["shift_pattern"])
                    spot_frac += mult / 100.0
                    if spot_frac >= spot_move_interval:
                        spot_frac -= spot_move_interval
                        if d["dir_change"] > 0:
                            turn_chance = 100.0 / d["dir_change"] - math.floor(d["net"] / 2.0)
                            turn_chance = max(1, min(80, turn_chance))
                            if rng.random() * 100 < turn_chance:
                                spot_dir = -spot_dir
                                spot_state = 1; spot_cooldown = 3
                        zone_start += spot_dir; zone_end += spot_dir
                        if zone_end >= bar_width:
                            spot_dir = -1; zone_end = bar_width - 1; zone_start = zone_end - zone_width + 1
                        if zone_start < 0:
                            spot_dir = 1; zone_start = 0; zone_end = zone_width - 1

        in_zone = zone_start <= cursor <= zone_end
        if in_zone and not was_in_zone:
            zone_enter_tick = tick
            if tick >= 8:  # 시작 그레이스(8틱) 이후에만 클릭 예약 (라이브와 동일)
                pending_click_tick = tick + delay_ticks
        was_in_zone = in_zone

        if pending_click_tick is not None and tick == pending_click_tick:
            if zone_start <= cursor <= zone_end:
                return "success"
            else:
                if rng.random() * 100 < escape_chance:
                    return "escape"
                escape_chance = min(100, escape_chance + d["escape_inc"])
            pending_click_tick = None

    return "timeout"


def simulate_catch(grade, rod_bonus, escape_reduction, delay_ticks, trials, seed=0, size=0):
    rng = random.Random(seed)
    d = derive(grade, rod_bonus, escape_reduction, size=size)
    successes = 0
    for _ in range(trials):
        total_rounds = d["consecutive"]
        ok = True
        for _r in range(total_rounds):
            res = simulate_round(d, delay_ticks, rng)
            if res != "success":
                ok = False
                break
        if ok:
            successes += 1
    return successes / trials


def ms_to_ticks(ms):
    return round(ms / TICK_MS)


if __name__ == "__main__":
    import sys

    REACTION_MS = 250
    PING_RTT_MS = 40
    delay_ticks = ms_to_ticks(REACTION_MS + PING_RTT_MS)
    TRIALS = 8000

    print(f"# 반응속도 {REACTION_MS}ms + 핑RTT {PING_RTT_MS}ms = 지연 {REACTION_MS+PING_RTT_MS}ms ≈ {delay_ticks}틱\n")

    grades = ["E", "D", "C", "B", "A", "S", "M", "L", "G"]
    rod_bonus_range = list(range(-6, 31, 2))

    results = {}
    for g in grades:
        results[g] = {}
        for rb in rod_bonus_range:
            p = simulate_catch(g, rb, 0, delay_ticks, TRIALS, seed=hash((g, rb)) & 0xffffffff)
            results[g][rb] = p

    # 표 출력
    header = "난이도\\등급 | " + " | ".join(grades)
    print(header)
    for rb in rod_bonus_range:
        row = [f"{results[g][rb]*100:5.1f}%" for g in grades]
        print(f"{rb:+3d}      | " + " | ".join(row))

    with open(Path(__file__).resolve().parent / "minigame_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
