#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buff_values.py — F절(요리 버프가치) · G절(날씨 효과) 재판정.

★2026-08-05 신설. stat_value.py 교체(피티 MC + 실측 220 포획/h)로 스탯 원/h가 전부 바뀌었으므로
버프·날씨 가치도 처음부터 다시 계산한다.

F 요리: 버프가치(원) = Σ(버프스탯 × 스탯가치 원/h) × 지속(h).
   경보선: 🟡 같은 티어 내 버프가치 편차 > 3배 / 재료난이도와 버프가치 역전
G 날씨: 순이득(원/h) = Σ(환경보너스 × 스탯가치) − 다운사이드(difficultyAdd·escapeAdd).
   ★difficultyAdd/escapeAdd는 WeatherDef 하드코딩(JSON 무관)이라 Java에서 읽는다.
   경보선: 🟡 단일 날씨 순이득 > 기본수입의 +30%

사용법: python3 buff_values.py [--stage 초반|중반|종결]
"""
import argparse, collections, importlib.util, json, os, re, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BS = ("/Users/user/Library/Application Support/feather/player-server/servers/"
      "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
SRC = "/Users/user/development/blockship-plugin/src/main/java/com/blockship"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = saved
    return m


SV = _load("stat_value")

# 요리 buff() 인자 순서 (DishSpecs.java:104)
#   buff(id, name, base, tier, exp, size, gradeup, escape, crit, dbl, sellBonus, difficulty, durationSec, sellPrice, ing)
BUFF_ORDER = ["exp", "size", "gradeup", "escape", "crit", "dbl", "sellBonus", "difficulty"]
BUFF_STAT = {
    "exp": "경험치 (1%)", "size": "크기 (1%)", "gradeup": "등급업 (1%)",
    "escape": "도주감소 (1%)", "crit": "크리확률 (1%)", "dbl": "더블찬스 (1%)",
    "sellBonus": "판매보너스 (1%)", "difficulty": "난이도 (1점)",
}
WEATHER_STAT = {
    "경험치": "경험치 (1%)", "크기": "크기 (1%)", "등급업": "등급업 (1%)",
    "행운": "행운 (1점)", "판매보너스": "판매보너스 (1%)", "크리확률": "크리확률 (1%)",
    "더블찬스": "더블찬스 (1%)", "내구보존": None,   # income 아님(유지비 절감)
}


def _split_args(s):
    """괄호/문자열을 존중하며 최상위 콤마로 인자 분리."""
    out, depth, cur, instr = [], 0, [], False
    i = 0
    while i < len(s):
        c = s[i]
        if instr:
            if c == "\\":
                cur.append(s[i:i+2]); i += 2; continue
            if c == '"':
                instr = False
            cur.append(c)
        elif c == '"':
            instr = True; cur.append(c)
        elif c in "([{":
            depth += 1; cur.append(c)
        elif c in ")]}":
            depth -= 1; cur.append(c)
        elif c == "," and depth == 0:
            out.append("".join(cur).strip()); cur = []
        else:
            cur.append(c)
        i += 1
    if cur:
        out.append("".join(cur).strip())
    return out


def parse_dishes():
    """DishSpecs.java의 buff(...) 호출을 괄호 매칭으로 파싱 (8스탯/7스탯 오버로드 모두).

    ★정규식 하나로 뽑으려 하면 durationSec을 스탯으로 오독한다(2026-08-05 실제로 겪음 —
    difficulty=780 같은 값이 나왔다). 인자 개수로 오버로드를 판별해야 한다.
    """
    src = open(os.path.join(SRC, "cooking", "DishSpecs.java"), encoding="utf-8").read()
    # ★줄 끝 주석(`// 평원`)을 먼저 제거한다 — 안 하면 인자 중간에 주석이 섞여 int() 파싱이 깨지고
    #   그 요리가 조용히 누락된다(2026-08-05: 24종 중 9종이 이렇게 빠졌다).
    src = re.sub(r'//[^\n]*', '', src)
    out = []
    for m in re.finditer(r'\breturn\s+buff\(|\bbuff\(', src):
        start = m.end()
        depth, i = 1, start
        while i < len(src) and depth:
            if src[i] == "(": depth += 1
            elif src[i] == ")": depth -= 1
            i += 1
        args = _split_args(src[start:i-1])
        if len(args) < 6 or not args[0].startswith('"'):
            continue
        did = args[0].strip('"')
        name = re.sub(r'§.', '', args[1].strip('"'))
        try:
            tier = int(args[3])
        except ValueError:
            continue
        nums = args[4:-1]            # 마지막은 재료 List.of(...)
        ing_src = args[-1]
        if len(nums) < 3:
            continue
        try:
            vals = [float(x) for x in nums]
        except ValueError:
            continue
        dur, sell = int(vals[-2]), int(vals[-1])
        stats_v = vals[:-2]
        keys = BUFF_ORDER if len(stats_v) == 8 else [k for k in BUFF_ORDER if k != "difficulty"]
        stats = {k: v for k, v in zip(keys, stats_v) if v}
        n_ing = len(re.findall(r'\b(?:item|custom|fish|herbany|forage|crop)\(', ing_src))
        out.append(dict(id=did, name=name, tier=tier, stats=stats, dur=dur, sell=sell, ing=n_ing))
    return out


def parse_weathers():
    """WeatherManager.java의 WeatherDef(...)에서 diff/escape/weight를 읽는다."""
    src = open(os.path.join(SRC, "region", "WeatherManager.java"), encoding="utf-8").read()
    out = {}
    for m in re.finditer(r'new WeatherDef\(\s*"([^"]+)"\s*,\s*"[^"]*"\s*,\s*"[^"]*"\s*,'
                         r'\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,'
                         r'\s*(-?\d+)\s*,\s*(true|false)\s*(?:,\s*(null|"[^"]*")\s*)?(?:,\s*(\d+)\s*)?\)', src):
        out[m.group(1)] = dict(exp=int(m.group(2)), size=int(m.group(3)), grade=int(m.group(4)),
                               diff=int(m.group(5)), escape=int(m.group(6)),
                               weight=int(m.group(10)) if m.group(10) else 10)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="중반", choices=list(SV.STAGES))
    args = ap.parse_args()

    r = SV.compute(args.stage)
    V = {k: v[0] for k, v in r["V"].items()}
    income = r["income"]
    print(f"기준 구간 [{args.stage}] — 수입 {income:,.0f}원/h · 포획 {SV.CATCH_PER_HOUR}/h")

    # ── F. 요리 ───────────────────────────────────────────────────────────
    dishes = parse_dishes()
    print("\n" + "=" * 104)
    print(f"F. 요리 버프가치 (버프용 {len(dishes)}종) — 버프가치 = Σ(스탯×원/h) × 지속h")
    print("=" * 104)
    rows = []
    for d in dishes:
        per_h = sum(v * V[BUFF_STAT[k]] for k, v in d["stats"].items() if k in BUFF_STAT)
        total = per_h * d["dur"] / 3600.0
        rows.append(dict(**d, per_h=per_h, total=total))
    by_tier = collections.defaultdict(list)
    for x in rows:
        by_tier[x["tier"]].append(x)
    print(f"{'티어':<4}{'n':>3}{'평균 버프원/h':>15}{'평균 지속':>10}{'평균 버프가치':>15}"
          f"{'최소':>12}{'최대':>12}{'편차':>7}")
    print("─" * 104)
    warn = []
    for t in sorted(by_tier):
        arr = by_tier[t]
        tot = [x["total"] for x in arr]
        lo, hi = min(tot), max(tot)
        spread = hi / lo if lo > 0 else float("inf")
        print(f"{t:<4}{len(arr):>3}{sum(x['per_h'] for x in arr)/len(arr):>15,.0f}"
              f"{sum(x['dur'] for x in arr)/len(arr)/60:>9.0f}분{sum(tot)/len(tot):>15,.0f}"
              f"{lo:>12,.0f}{hi:>12,.0f}{spread:>6.1f}x")
        if spread > 3:
            b = min(arr, key=lambda x: x["total"]); w = max(arr, key=lambda x: x["total"])
            warn.append(f"🟡 요리 T{t} 버프가치 편차 {spread:.1f}배 "
                        f"({b['name']} {b['total']:,.0f}원 ↔ {w['name']} {w['total']:,.0f}원)")
    print("\n버프가치 상위 8종")
    for x in sorted(rows, key=lambda x: -x["total"])[:8]:
        s = " ".join(f"{k}{v:g}" for k, v in x["stats"].items())
        print(f"  T{x['tier']} {x['name']:<16}{x['total']:>12,.0f}원 "
              f"({x['dur']//60}분, {x['per_h']:,.0f}원/h)  재료{x['ing']}종  [{s}]")
    print("\n버프가치 하위 5종")
    for x in sorted(rows, key=lambda x: x["total"])[:5]:
        s = " ".join(f"{k}{v:g}" for k, v in x["stats"].items())
        print(f"  T{x['tier']} {x['name']:<16}{x['total']:>12,.0f}원 "
              f"({x['dur']//60}분, {x['per_h']:,.0f}원/h)  재료{x['ing']}종  [{s}]")

    # ── G. 날씨 ───────────────────────────────────────────────────────────
    env = json.load(open(os.path.join(BS, "env-bonuses.json"), encoding="utf-8"))["weathers"]
    wdefs = parse_weathers()
    print("\n" + "=" * 104)
    print(f"G. 날씨 순이득 (JSON 보너스 {len(env)}종 + WeatherDef 다운사이드)")
    print("=" * 104)
    print(f"{'날씨':<8}{'상방 원/h':>12}{'diff':>6}{'esc':>5}{'다운사이드':>12}"
          f"{'순이득 원/h':>13}{'기본수입比':>10}{'가중치':>7}")
    print("─" * 104)
    # 다운사이드: difficultyAdd는 난이도 스탯의 역방향, escapeAdd는 도주감소의 역방향
    for name, bon in sorted(env.items(), key=lambda kv: -sum(kv[1].values())):
        up = 0.0
        for k, v in bon.items():
            key = WEATHER_STAT.get(k)
            if key:
                up += v * V[key]
        d = wdefs.get(name, {})
        diff, esc = d.get("diff", 0), d.get("escape", 0)
        down = diff * V["난이도 (1점)"] + esc * V["도주감소 (1%)"]
        net = up - down
        print(f"{name:<8}{up:>12,.0f}{diff:>6}{esc:>5}{down:>12,.0f}{net:>13,.0f}"
              f"{net/income*100:>9.1f}%{d.get('weight', 10):>7}")
        if net / income > 0.30:
            warn.append(f"🟡 날씨 {name} 순이득 {net/income*100:.0f}% (>30% 경보선)")
        if net < 0:
            warn.append(f"🟢 날씨 {name} 순이득 음수({net:,.0f}원/h) — 페널티 날씨(의도 확인)")
    # 유성우/오로라는 JSON에 없으면 WeatherDef만
    for name in ("유성우", "오로라"):
        if name in env or name not in wdefs:
            continue
        d = wdefs[name]
        up = d["exp"] * V["경험치 (1%)"] + d["size"] * V["크기 (1%)"] + d["grade"] * V["등급업 (1%)"]
        down = d["diff"] * V["난이도 (1점)"] + d["escape"] * V["도주감소 (1%)"]
        print(f"{name:<8}{up:>12,.0f}{d['diff']:>6}{d['escape']:>5}{down:>12,.0f}"
              f"{up-down:>13,.0f}{(up-down)/income*100:>9.1f}%{d['weight']:>7}   ※JSON 미등록")

    print("\n" + "=" * 104)
    if warn:
        print("경보")
        print("=" * 104)
        for w in warn:
            print("  " + w)
    else:
        print("🟢 F/G 경보선 위반 없음")


if __name__ == "__main__":
    main()
