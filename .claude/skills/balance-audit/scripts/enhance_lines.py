#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enhance_lines.py — 강화표(enhance.json) «라인 기반» 재생성의 단일 권위 (2026-08-27).

────────────────────────────────────────────────────────────────────────────
왜 다시 만드는가 — 라이브 90개 표 전수 조사 결과
────────────────────────────────────────────────────────────────────────────
① **주스탯 칸이 빈 표가 30개 이상.** A급 대부분(왕실·근위·왕립순찰·열사·오아시스·
   교역로·고고학자·정밀·감별사·무역상·회계사·사구·전갈·행렬·유목민…)이 15강 전체에서
   `행운 9 · 난이도 3` **동일**하다. 유저 표현 그대로 «강화하면 다 똑같은 스탯이 오른다».
② **강화가 라인을 배신한다** — 표가 라인 재설계 이전 값으로 굳었다.
   대나무 막대기(행운형) → 경험치 42 · 참나무(숙련형) → 경험치 62 ·
   전문가(숙련형) → 크리확률 27 · 흑단목 → 크기 110.
③ **채집형이 난이도를 받는다** — 채집용/수집가의/탐사자의 표가 매 레벨 `난이도:1` 이라
   +13강이면 난이도 13. 「채집형은 난이도 0」 설계를 강화가 통째로 무효화했다.
   `채집용 낚싯대 +8` 은 `난이도:1,행운:1,난이도:1` — 한 줄에 같은 키가 둘(뒤가 앞을 덮음).
④ **고아 16 / 누락 2** — parts.json 에 없는 표 16개, 표 없는 낚싯대 2종(잠수부 계열)은
   EnhanceLoader 폴백(`난이도:1,크기:2,크리확률:1`)을 타서 레벨만큼 난이도를 받는다.
⑤ **주스탯 배수가 2.3~12배로 제멋대로** — 바르칸 더블찬스 9 → +110.

────────────────────────────────────────────────────────────────────────────
설계 규약
────────────────────────────────────────────────────────────────────────────
라인은 **라이브 기본 스탯에서 판정**한다(parts.json 이 권위 — 표에 라인을 적어 두면
낚싯대 스탯을 바꿀 때 또 갈라진다).

    주스탯   = 그 라인의 메인          풀강 총 += 기본 × MAIN_MULT(2.0)   → 총 3배
    부스탯   = 그 라인의 서브          풀강 총 += 기본 × SUB_MULT(1.5)
    신규스탯 = 기본에 없는 1종         풀강 총 = 1~3 (고레벨에서만, «해금» 연출)
    난이도   = 라인·등급별 총량 고정   5의 배수 레벨 + max 에만
    행운     = **행운 라인만**         (구 표는 전 라인에 행운을 뿌렸다 — 행운형의 정체성
                                       을 훔치는 구조였다. 낚싯대 기본에서 뺀 것과 짝)

★배수 규칙의 근거 = 유저가 준 사다리 «C풀강 ≥ B중반강화 ≥ A기본».
  판매보너스 등급 사다리는 D3/C6/B10/A18/S24 로 등급당 ~1.7배다. 따라서
  C 기본 6 → 풀강 18(= A 기본) 이 되려면 «기본 × 2 추가»가 정확한 값이다.
  B 기본 10 → 중반(절반) +10 = 20 ≈ A 기본 18, 풀강 30 ≈ S 기본 24. 사다리 성립.

★**난이도는 이 배수를 쓰지 않는다.** 난이도 등급 사다리는 ×1.7 이 아니라 **+1** 이다
  (숙련 D2/C3/B4/A5/S6). 배수를 적용하면 C 3 → 풀강 9 가 되어 «강화로 C→S» 가 되고,
  그건 유저가 명시적으로 막은 것("1강마다 -1씩 되면 큰일남"). 그래서 난이도만 총량
  고정표(ENH_DIFF)를 쓴다 — 숙련 C +2 → 풀강 5 = A 기본 5.

사용:
    python3 enhance_lines.py                # 라인 판정 + 생성 결과 요약
    python3 enhance_lines.py --rod 참나무 낚싯대   # 한 낚싯대 레벨별 상세
    python3 enhance_lines.py --json         # enhance.json table 형태로 출력
    python3 enhance_lines.py --check        # 사다리·난이도 상한 검증만
"""
import argparse, collections, json, math, os, sys

BS = os.environ.get("BLOCKSHIP_DATA",
                    "/Users/user/Library/Application Support/feather/player-server/servers/"
                    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")

#: 라인 → (메인, 서브들, 신규스탯). rod_lines.LINES 와 같은 지도 + 신규스탯 1종.
LINES = {
    "숙련": ("난이도",      ["도망감소", "경험치"],           "크기"),
    "크리": ("크기",        ["크리확률", "크리배율"],          "판매보너스"),
    "행운": ("행운",        ["등급업"],                     "크기"),
    "상인": ("판매보너스",   ["더블찬스"],                   "트리플찬스"),
    "성장": ("경험치",      ["트리플찬스"],                  "더블찬스"),
    "채집": ("재료확률",     ["경험치"],                     "도망감소"),
}
#: 스탯 → 라인 (판정용). 난이도는 전 라인에 얕게 깔리므로 판정에서 제외한다.
STAT_LINE = {
    "도망감소": "숙련",
    "크기": "크리", "크리확률": "크리", "크리배율": "크리",
    "행운": "행운", "등급업": "행운",
    "판매보너스": "상인", "더블찬스": "상인",
    "경험치": "성장", "트리플찬스": "성장",
    "재료확률": "채집",
}
#: 라인 판정 가중치 — 정규화 가치(판매보너스 1% = 1.00, stat_value 산출)
W = {"도망감소": 0.36, "크기": 0.59, "크리확률": 0.48, "크리배율": 2.38,
     "행운": 0.40, "등급업": 2.11, "판매보너스": 1.00, "더블찬스": 1.00,
     "경험치": 1.00, "트리플찬스": 2.00, "재료확률": 1.00}

MAIN_MULT = 2.0      # 주스탯 풀강 추가분 = 기본 × 이 값
SUB_MULT = 1.5       # 부스탯 풀강 추가분
NEW_TOTAL = {"E": 0, "D": 1, "C": 1, "B": 2, "A": 3, "S": 3}   # 신규스탯 풀강 총량

#: 난이도 풀강 총량 — ★배수 금지, 등급당 +1 사다리.
#  ★★난이도 3층 예산 — 이 모듈이 **단일 권위**다. rod_lines.py 도 여기서 import 한다.
#    복제하면 갈라진다(내구보존 사태와 같은 실패 모드).
#      ① 낚싯대 기본 ROD_DIFF   ② 강화 총량 ENH_DIFF   ③ 숙련 계열 부품 PART_DIFF × 4슬롯
#    합계가 «순간이동 문턱»(S: rodBonus 9)을 만든다.
ENH_DIFF = {
    "숙련": {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4, "S": 5},
    "혼합": {"E": 0, "D": 1, "C": 1, "B": 2, "A": 2, "S": 3},
    "기타": {"E": 0, "D": 0, "C": 1, "B": 2, "A": 2, "S": 3},
    "채집": {"E": 0, "D": 0, "C": 0, "B": 0, "A": 0, "S": 0},
}
ROD_DIFF = {
    "숙련": {"E": 0, "D": 2, "C": 3, "B": 4, "A": 5, "S": 6},
    "혼합": {"E": 0, "D": 2, "C": 3, "B": 3, "A": 3, "S": 4},
    "기타": {"E": 0, "D": 1, "C": 2, "B": 2, "A": 3, "S": 4},
    "채집": {"E": 0, "D": 0, "C": 0, "B": 0, "A": 0, "S": 0},
}
#: 숙련 계열 부품 1개당 난이도 (릴·줄·바늘·찌 4슬롯 — 미끼는 행운 축 유지)
PART_DIFF = {"E": 0, "D": 1, "C": 1, "B": 1, "A": 2, "S": 2}
#: 숙련 계열 = 각 슬롯의 «군더더기 없는 기본형» 시리즈. 새 아이템을 만들지 않고 이 12종에
#  난이도를 부스탯으로 준다(레시피·상점 목록을 늘리지 않는다). 잠수상점(P 통화)은 제외.
SKILL_SERIES = {
    "릴":  {"나무 릴": "D", "철제 릴": "C", "전술 릴": "B"},
    "줄":  {"면줄": "D", "나일론줄": "C", "카본줄": "B"},
    "바늘": {"철 바늘": "D", "날카로운 바늘": "C", "미늘 바늘": "B"},
    "찌":  {"코르크 찌": "D", "가벼운 찌": "C", "전자 찌": "B"},
}


def parse_stats(s):
    d = {}
    for t in (s or "").split(","):
        if ":" not in t:
            continue
        k, v = t.split(":", 1)
        if k == "등급특화":
            continue
        try:
            d[k] = float(v)
        except ValueError:
            pass
    return d


def load():
    P = json.load(open(os.path.join(BS, "parts.json"), encoding="utf-8"))
    E = json.load(open(os.path.join(BS, "enhance.json"), encoding="utf-8"))
    return P, E


def line_of(base, grade):
    """기본 스탯 → 라인.

    ★난이도를 정규화 가치로 «점수»에 넣으면 안 된다 — 전 라인에 얕게 깔리는 축이라
      가중치를 크게 주면 모든 낚싯대가 숙련형이 되고, 작게 주면 진짜 숙련형(참나무·
      전문가)이 경험치 2점에 밀려 «성장형» 으로 잡힌다(실제로 그렇게 잡혔다).
      대신 **설계 상수와 비교**한다: 그 등급의 «기타» 기본치를 1 이상 넘고 도망감소를
      가졌으면 숙련형이다. 판정에 쓰는 상수(ROD_DIFF)가 곧 설계 의도라 드리프트가 없다.
    """
    if base.get("재료확률", 0) > 0:
        return "채집"
    if (base.get("난이도", 0) >= ROD_DIFF["숙련"].get(grade, 99)
            and base.get("도망감소", 0) > 0):
        return "숙련"
    score = collections.Counter()
    for k, v in base.items():
        ln = STAT_LINE.get(k)
        if ln:
            score[ln] += v * W.get(k, 1.0)
    if not score:
        return "숙련" if base.get("난이도", 0) > 0 else "행운"
    return score.most_common(1)[0][0]


def diff_key(line, base, grade):
    """난이도 예산 키. 숙련형 / 채집형 / 혼합(라인 2개 이상 뚜렷) / 기타."""
    if line in ("채집", "숙련"):
        return line
    score = collections.Counter()
    for k, v in base.items():
        ln = STAT_LINE.get(k)
        if ln:
            score[ln] += v * W.get(k, 1.0)
    top = score.most_common()
    if len(top) >= 2 and top[1][1] >= top[0][1] * 0.55:
        return "혼합"
    return "기타"


def spread(total, levels, weights=None):
    """total 을 levels 리스트에 정수로 배분. 뒤 레벨에 더 실어 «성장 체감»을 만든다."""
    if not levels or total <= 0:
        return {}
    w = weights or [1 + i / max(1, len(levels) - 1) for i in range(len(levels))]
    sw = sum(w)
    raw = [total * x / sw for x in w]
    out, acc = {}, 0.0
    for i, lv in enumerate(levels):
        acc += raw[i]
        take = int(round(acc)) - sum(out.values())
        if take > 0:
            out[lv] = take
    # 반올림 오차 보정 — 마지막 레벨에 넣는다
    gap = total - sum(out.values())
    if gap:
        out[levels[-1]] = out.get(levels[-1], 0) + gap
        if out[levels[-1]] <= 0:
            out.pop(levels[-1], None)
    return out


def build_table(name, base, grade, mx):
    """한 낚싯대의 강화표 {레벨: "스탯:값,..."} 생성.

    **낚싯대 자기 기본 스탯이 계획을 만든다** — 라인표를 그대로 베끼면 혼합형
    (다목적·만능·겸업)의 두 번째 축이 강화에서 통째로 빠진다. 그래서:

        주스탯 = 기본 스탯 중 정규화 가치 최대(난이도·재료확률 제외)  → 풀강 +기본×2.0
        부스탯 = 그다음 1~2개                                    → 풀강 +기본×1.5
        신규   = 주스탯과 같은 라인인데 기본에 없는 1종             → 1~3 (고레벨 해금)
        난이도 = 예산표 총량 고정 (5의 배수 + max)

    ★난이도가 라인 메인인 숙련형에서도 «주스탯 자리»는 도망감소가 맡는다. 난이도는
      정수 사다리(등급당 +1)라 배수 규칙을 쓸 수 없고(유저 제약: 「1강마다 -1 은 큰일」),
      도망감소가 같은 «놓치지 않는다» 축이라 성장 축으로 자연스럽다.
    ★재료확률은 2026-08-27 부터 강화에 **들어간다**(EnhanceManager 배열 index 10 신설 +
      FishingBonuses 가산). 그전엔 슬롯이 없어 채집형이 강화해도 정체성 스탯이 안 올랐다.
    """
    line = line_of(base, grade)
    dk = diff_key(line, base, grade)
    _, _, new = LINES[line]
    lv = list(range(1, mx + 1))
    plan = collections.defaultdict(dict)

    # ── 성장 가능한 기본 스탯을 가치순으로 정렬 (난이도·재료확률 제외)
    growable = sorted(((k, v) for k, v in base.items()
                       if k != "난이도" and v > 0),
                      key=lambda kv: -kv[1] * W.get(kv[0], 1.0))
    if not growable:                       # 나뭇가지처럼 스탯이 난이도/재확뿐인 경우
        growable = [(LINES[line][0] if LINES[line][0] != "난이도" else "도망감소", 1)]

    if line == "숙련":
        # ★강제 — 도망감소의 정규화 가치(0.36)가 낮아 «가치순»으로는 경험치 2점에도 밀린다.
        #   그러면 숙련형 강화가 성장형처럼 보인다(실측: 참나무가 그렇게 잡혔다).
        #   도망감소는 난이도와 같은 «놓치지 않는다» 축이므로 이 라인의 성장축이 맞다.
        growable.sort(key=lambda kv: (kv[0] != "도망감소", -kv[1] * W.get(kv[0], 1.0)))
    main_stat, mbase = growable[0]
    for l, v in spread(int(round(mbase * MAIN_MULT)), lv).items():
        plan[l][main_stat] = plan[l].get(main_stat, 0) + v

    even = [l for l in lv if l % 2 == 0] or lv
    for s_, sbase in growable[1:3]:
        for l, v in spread(max(1, int(round(sbase * SUB_MULT))), even).items():
            plan[l][s_] = plan[l].get(s_, 0) + v

    # ── 신규스탯: 주스탯과 같은 라인의 «없는» 스탯 1종 (없으면 라인 신규스탯)
    have = set(base) | {main_stat}
    cand = [k for k in LINES[STAT_LINE.get(main_stat, line)][1] if k not in have]
    pick = cand[0] if cand else (new if new not in have else None)
    if pick and NEW_TOTAL.get(grade, 0) > 0 and mx >= 3:
        hi = [l for l in lv if l >= max(3, int(mx * 0.6))]
        for l, v in spread(NEW_TOTAL[grade], (hi[-3:] or hi)).items():
            plan[l][pick] = plan[l].get(pick, 0) + v

    # ── 난이도: 5의 배수 + max. ★총량 고정(배수 금지 — 유저 제약)
    dtot = ENH_DIFF[dk].get(grade, 0)
    if dtot > 0:
        slots = [l for l in lv if l % 5 == 0]
        if mx not in slots:
            slots.append(mx)
        for l, v in spread(dtot, slots or [mx], weights=[1.0] * len(slots or [mx])).items():
            plan[l]["난이도"] = plan[l].get("난이도", 0) + v

    # ── 빈 레벨 제거 — «강화했는데 아무것도 안 오른다»는 그 자체로 버그 체감이다.
    #    총량은 건드리지 않고 1점만 옮긴다: ① 2점 이상 쌓인 스탯에서 한 점,
    #    ② 없으면 스탯이 2종 이상인 레벨에서 가장 값싼 1종을 통째로.
    for l in lv:
        if plan.get(l):
            continue
        best = None
        for x in lv:
            for k, v in (plan.get(x) or {}).items():
                if v >= 2 and (best is None or v > best[2]):
                    best = (x, k, v)
        if best:
            x, k, _ = best
            plan[x][k] -= 1
            plan[l][k] = 1
            continue
        cand = [x for x in lv if len(plan.get(x) or {}) >= 2]
        if not cand:
            continue
        x = min(cand, key=lambda x: len(plan[x]))
        k = min(plan[x], key=lambda k: W.get(k, 1.0))
        plan[l][k] = plan[x].pop(k)

    order = ["난이도", "도망감소", "크리배율", "등급업", "크리확률", "크기", "경험치",
             "판매보너스", "더블찬스", "트리플찬스", "행운", "재료확률"]
    out = {}
    for l in lv:
        d = {k: v for k, v in (plan.get(l) or {}).items() if v > 0}
        out[str(l)] = ",".join(f"{k}:{int(d[k])}" for k in order if d.get(k))
    return line, dk, out


def generate():
    P, E = load()
    rods = P["parts"]["낚싯대"]
    table, meta = {}, {}
    for name, raw in rods.items():
        f = raw.split("|")
        grade, base = f[1], parse_stats(f[4])
        mx = (E["table"].get(name) or {}).get("max")
        if mx is None:
            mx = {"E": 3, "D": 8, "C": 10, "B": 13, "A": 15, "S": 20}.get(grade, 8)
        line, dk, levels = build_table(name, base, grade, mx)
        table[name] = {"max": mx, "levels": levels}
        meta[name] = (grade, f[6], line, dk, base, mx)
    return table, meta


def cum(levels, upto):
    c = collections.Counter()
    for i in range(1, upto + 1):
        for k, v in parse_stats(levels.get(str(i), "")).items():
            c[k] += v
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rod")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    table, meta = generate()

    if a.json:
        print(json.dumps({"order": sorted(table), "table": table},
                         ensure_ascii=False, indent=2))
        return

    if a.rod:
        t = table[a.rod]
        g, src, line, dk, base, mx = meta[a.rod]
        print(f"{a.rod} [{g}] {src} · 라인 {line} · 난이도예산 {dk} · max {mx}")
        print(f"  기본: {','.join(f'{k}:{int(v)}' for k, v in base.items())}")
        for i in range(1, mx + 1):
            print(f"   +{i:<3} {t['levels'][str(i)] or '(없음)'}")
        c = cum(t["levels"], mx)
        print("  풀강 누적: " + ",".join(f"{k}:{int(v)}" for k, v in c.most_common()))
        return

    if a.check:
        print("=== 난이도 사다리 (낚싯대만) — 목표: C풀강 ≥ B중반강화 ≥ A기본 ===")
        for dk in ("숙련", "혼합", "기타", "채집"):
            c = ROD_DIFF[dk]["C"] + ENH_DIFF[dk]["C"]
            b = ROD_DIFF[dk]["B"] + ENH_DIFF[dk]["B"] // 2
            aa = ROD_DIFF[dk]["A"]
            s = ROD_DIFF[dk]["S"] + ENH_DIFF[dk]["S"]
            ok = "✓" if c >= aa and abs(c - b) <= 1 else "✗"
            print(f"  {dk:<4} C풀강 {c:>2} · B중반 {b:>2} · A기본 {aa:>2} · S풀강 {s:>2}   {ok}")
        print("\n=== 강화 후 라인 이탈 검사 (주스탯이 기본 라인과 다르면 ✗) ===")
        bad = []
        for name, (g, src, line, dk, base, mx) in meta.items():
            c = cum(table[name]["levels"], mx)
            if not c:
                continue
            gr = [k for k in base if k != "난이도" and base[k] > 0]
            if not gr:
                continue
            want = max(gr, key=lambda k: base[k] * W.get(k, 1.0))
            top = max((k for k in c if k != "난이도"), key=lambda k: c[k] * W.get(k, 1.0),
                      default=None)
            if top and top != want:
                bad.append((name, want, top))
        print(f"  이탈 {len(bad)}종" + (f": {bad[:8]}" if bad else " 🟢"))
        print("\n=== 채집형 난이도 누출 검사 ===")
        leak = [n for n, (g, s, l, dk, b, mx) in meta.items()
                if l == "채집" and cum(table[n]["levels"], mx).get("난이도", 0) > 0]
        print(f"  누출 {len(leak)}종" + (f": {leak}" if leak else " 🟢"))
        return

    print(f"{'낚싯대':<20}{'등':<3}{'라인':<5}{'예산':<5}{'max':>4}  기본 → 풀강 누적")
    for name, (g, src, line, dk, base, mx) in meta.items():
        c = cum(table[name]["levels"], mx)
        print(f"{name:<20}{g:<3}{line:<5}{dk:<5}{mx:>4}  "
              f"{','.join(f'{k}{int(v)}' for k, v in base.items())}"
              f"  →  {','.join(f'{k}{int(v)}' for k, v in c.most_common())}")


if __name__ == "__main__":
    main()
