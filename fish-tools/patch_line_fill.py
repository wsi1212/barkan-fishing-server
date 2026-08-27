#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_line_fill.py — «(카테고리 × 등급)» 격자의 **빈 라인을 자동 탐지해 메운다** (2026-08-27).

`patch_wangdo_b.py` 가 왕도 B 한 층을 손으로 계획했던 것을 일반화한 것이다. 목록을 손으로
적지 않는다 — `village_scan` 의 라벨러로 격자를 스캔해 **없는 라인만** 만든다.

## 배치 규칙
  · 등급 → 마을·레벨: 그 등급을 실제로 파는 마을의 레벨 범위 안에서 **가장 빈 구간**에 둔다.
  · 스탯: 같은 (카테고리, 라인) 최고레벨 아이템을 씨앗으로, **라인 초과분만** 스케일하고
    기반은 목적지 등급에서 가져온다(K_CAP·STAT_CAP 로 자름). 씨앗이 없으면 FALLBACK.
  · 레시피: 같은 등급 최근접 레벨에서 베끼고 마을 테마 재료를 섞는다.
    **수량은 `patch_cast_cost.py` 가 맞춘다.**

## ★S 급은 자동 채우지 않는다
히든-전설·심해라 «상점에서 사는 층»이 아니다. 격자 구멍으로 보고하되 생성 대상에서 뺀다.

사용:
    python3 patch_line_fill.py <BlockShip경로>            # dry-run
    python3 patch_line_fill.py <BlockShip경로> --apply
"""
import importlib.util, json, math, os, shutil, sys

SKILL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     ".claude", "skills", "balance-audit", "scripts")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SKILL, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    sv, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = sv
    return m


#: 등급 → (그 등급을 파는 마을, 테마 이름 접두, 테마 재료). 레벨은 실측 범위에서 고른다.
HOME = {
    "D": ("스폰마을", {"숙련": "억센", "성장": "수련", "크리": "예민한", "행운": "복점",
                    "상인": "장터", "채집": "채집", "관통": "쇠", "잠수": "갯벌"}, "녹슨부품"),
    "C": ("스폰마을", {"숙련": "단련된", "성장": "학습", "크리": "정밀한", "행운": "길조",
                    "상인": "거래", "채집": "수집", "관통": "관통", "잠수": "해녀"}, "낡은갈고리"),
    "B": ("왕도", {"숙련": "방벽", "성장": "문서고", "크리": "사자", "행운": "왕관",
                  "상인": "세관", "채집": "조병창", "관통": "창병", "잠수": "친위"}, "강화에메랄드"),
    "A": ("상단마을", {"숙련": "선단", "성장": "서기", "크리": "감정사의", "행운": "복운",
                    "상인": "환전상의", "채집": "적재상의", "관통": "호선", "잠수": "잠수교역"},
          "별빛진주"),
}
#: 씨앗이 아예 없는 (카테고리, 라인) — 라인 가산분만 손으로 적는다.
FALLBACK = {
    ("릴", "숙련"):   dict(난이도=2, 도망감소=26),
    ("미끼", "숙련"): dict(난이도=2, 도망감소=24),
    ("줄", "크리"):   dict(크리확률=9, 크리배율=1, 크기=4),
    ("찌", "크리"):   dict(크리확률=9, 크리배율=1, 크기=4),
    ("바늘", "크리"): dict(크리확률=10, 크리배율=2, 크기=4),
    ("릴", "크리"):   dict(크리확률=9, 크리배율=1, 크기=4),
    ("미끼", "크리"): dict(크리확률=9, 크리배율=1, 크기=4),
    ("줄", "채집"):   dict(재료확률=10, 경험치=4),
    ("찌", "채집"):   dict(재료확률=10, 경험치=4),
    ("줄", "행운"):   dict(행운=8, 등급업=3),
    ("바늘", "행운"): dict(행운=8, 등급업=3),
    ("릴", "행운"):   dict(행운=8, 등급업=3),
    ("찌", "숙련"):   dict(난이도=2, 도망감소=22),
    ("바늘", "숙련"): dict(난이도=2, 도망감소=22),
    ("줄", "숙련"):   dict(난이도=2, 도망감소=28),
    ("줄", "성장"):   dict(경험치=12, 트리플찬스=1),
    ("바늘", "성장"): dict(경험치=12, 트리플찬스=1),
    ("찌", "성장"):   dict(경험치=12, 트리플찬스=1),
    ("미끼", "성장"): dict(경험치=12, 트리플찬스=1),
    ("작살", "상인"): dict(판매보너스=8, 행운=10),
    ("작살", "관통"): dict(공격력=2, 도망감소=20),
    ("작살", "채집"): dict(재료확률=14, 경험치=6),
}
K_CAP = 2.4
STAT_CAP = 1.5
SKIPSRC = {"캐시", "개발자", "잠수상점"}
GRADES = ("D", "C", "B", "A")        # ★S 는 제외 (히든-전설·심해)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src, apply_ = sys.argv[1], "--apply" in sys.argv
    os.environ["BLOCKSHIP_DATA"] = src
    VS = _load("village_scan")
    RL = _load("rod_lines")
    CC = VS.CC
    D, K, rows, cph = CC.build_rows()

    pp, rp = os.path.join(src, "parts.json"), os.path.join(src, "recipes.json")
    P = json.load(open(pp, encoding="utf-8"))
    R = json.load(open(rp, encoding="utf-8"))

    # ── 격자 스캔: (카테고리, 등급) → 있는 라인 / 기반 / 스탯 상한 ──────
    label, base_of, capmax, lv_of = {}, {}, {}, {}
    for cat in {r["cat"] for r in rows}:
        for g in GRADES:
            arr = [r for r in rows if r["cat"] == cat and r["grade"] == g
                   and r["src"] not in SKIPSRC]
            if not arr:
                continue
            b = VS.group_base(arr)
            base_of[(cat, g)] = {a: v for a, v in b.items() if v}
            # ★스탯 값이 문자열인 것도 있다(등급특화:"C") — 숫자만 본다.
            def _num(r, k2):
                v = r["stats"].get(k2, 0)
                return float(v) if isinstance(v, (int, float)) else 0.0
            capmax[(cat, g)] = {k2: max(_num(r, k2) for r in arr)
                                for k2 in {x for r in arr for x in r["stats"]}}
            lv_of[(cat, g)] = sorted(r["lv"] for r in arr)
            for r in arr:
                label[r["name"]] = VS.line_label(r["stats"], cat, b)

    def pick_seed(cat, line, upto):
        order = [g for g in ("A", "B", "C", "D") if GRADES.index(g) <= GRADES.index(upto)]
        for g in reversed(order):          # 목적 등급에 가까운 쪽부터
            c = [r for r in rows if r["cat"] == cat and r["grade"] == g
                 and label.get(r["name"]) == line and r["src"] not in SKIPSRC]
            if c:
                return max(c, key=lambda r: r["lv"])
        return None

    def price_at(cat, g, lv):
        c = [r for r in rows if r["cat"] == cat and r["grade"] == g and r["price"] > 0
             and r["src"] not in SKIPSRC]
        if not c:
            return 100000
        c.sort(key=lambda r: r["lv"])
        lo = max([r for r in c if r["lv"] <= lv], key=lambda r: r["lv"], default=c[0])
        hi = min([r for r in c if r["lv"] >= lv], key=lambda r: r["lv"], default=c[-1])
        base = lo["price"] if hi["lv"] == lo["lv"] else (
            lo["price"] + (lv - lo["lv"]) / (hi["lv"] - lo["lv"]) * (hi["price"] - lo["price"]))
        return max(100, int(round(base / 100.0) * 100))

    def pick_level(cat, g, home_src, used):
        """그 마을이 파는 레벨 범위 안에서 «가장 빈 구간»을 고른다."""
        mine = sorted(r["lv"] for r in rows if r["cat"] == cat and r["grade"] == g
                      and r["src"] == home_src)
        span = lv_of.get((cat, g)) or [1]
        lo, hi = (min(mine), max(mine)) if mine else (span[0], span[-1])
        taken = set(span) | used
        for d in range(0, (hi - lo) + 6):
            for v in (lo + d, hi - d):
                if lo <= v <= hi + 4 and v not in taken:
                    return v
        return hi + 1

    plan = []
    for cat in ["낚싯대", "작살", "릴", "줄", "바늘", "찌", "미끼"]:
        canon = VS.CANON.get(cat, [])
        for g in GRADES:
            if (cat, g) not in base_of:
                continue
            have = {label[r["name"]] for r in rows if r["cat"] == cat and r["grade"] == g
                    and r["src"] not in SKIPSRC}
            for line in canon:
                if line not in have:
                    plan.append((cat, g, line))

    added, recs, missing = [], [], []
    nxt = {"낚싯대": max(int(k[1:]) for k in R["recipes"]
                       if k.startswith("R") and k[1:].isdigit()) + 1,
           "part": max(int(k[1:]) for k in R["recipes"]
                       if k.startswith("P") and k[1:].isdigit()) + 1,
           "작살": max(int(k[2:]) for k in R["recipes"]
                     if k.startswith("HP") and k[2:].isdigit()) + 1}
    used_lv = {}

    for cat, g, line in plan:
        home_src, theme, wmat = HOME[g]
        pre = theme.get(line, line)
        # ★이름 충돌 — 테마 접두가 등급 간에 겹친다(«길조 릴» 이 B 에 이미 있는데 C 행운을
        #   만들려 했다). 초판은 그냥 건너뛰어서 «구멍 5칸 → 신설 0종» 이 됐다.
        cands = [f"{pre} {cat}", f"{pre}의 {cat}", f"{pre}형 {cat}", f"신형 {pre} {cat}"]
        name = next((x for x in cands if x not in P["parts"][cat]), None)
        if name is None:
            missing.append((cat, g, line))
            continue
        seed = pick_seed(cat, line, g)
        if seed is None and (cat, line) not in FALLBACK:
            missing.append((cat, g, line))
            continue
        u = used_lv.setdefault((cat, g), set())
        lv = pick_level(cat, g, home_src, u)
        u.add(lv)
        tbase = dict(base_of[(cat, g)])
        cap = capmax[(cat, g)]
        stats = dict(tbase)
        if seed is None:
            for sk, sv in FALLBACK[(cat, line)].items():
                stats[sk] = stats.get(sk, 0) + sv
            tag = "★FALLBACK"
        else:
            k = min(K_CAP, math.exp(RL.EFF_B * (lv - seed["lv"])))
            sb = base_of.get((cat, seed["grade"]), {})
            for sk, sv in seed["stats"].items():
                if not isinstance(sv, (int, float)):
                    continue
                exc = sv - sb.get(sk, 0)
                if exc <= 0:
                    continue
                if sk in ("공격력", "크리배율", "더블찬스", "트리플찬스", "난이도"):
                    add = round(exc) + (1 if k >= 1.6 else 0)
                else:
                    add = max(1, int(round(exc * k)))
                stats[sk] = stats.get(sk, 0) + add
            tag = f"{seed['name']}(Lv{seed['lv']}) ×{k:.2f}"
        stats = {a: min(b, max(1, round(cap.get(a, b) * STAT_CAP))) for a, b in stats.items()}
        stats = {a: (int(b) if float(b).is_integer() else b) for a, b in stats.items() if b > 0}
        dur = max(int(l.split("|")[3]) for l in P["parts"][cat].values()
                  if l.split("|")[1] == g)
        price = price_at(cat, g, lv)
        P["parts"][cat][name] = "|".join(
            [name, g, str(price), str(dur),
             ",".join(f"{a}:{b:g}" for a, b in stats.items()), str(lv), home_src])
        added.append((cat, g, line, lv, name, price, stats, tag, home_src))
        _add_recipe(cat, g, lv, name, rows, R, nxt, recs, wmat)

    print(f"라인 구멍 {len(plan)}칸 → 신설 {len(added)}종")
    cur = None
    for cat, g, line, lv, name, price, stats, tag, hs in added:
        if (cat, g) != cur:
            print(f"  [{cat} {g}] ({hs})")
            cur = (cat, g)
        print(f"    Lv{lv:<3}{name:<16}{line:<5}{price:>10,}원  씨앗 {tag}")
        print(f"         {', '.join(f'{a}:{b:g}' for a, b in stats.items())}")
    if missing:
        print(f"\n★씨앗·FALLBACK 둘 다 없음 {len(missing)}건: {missing}")
    print(f"\n레시피 {len(recs)}건 (수량은 patch_cast_cost 가 맞춘다)")
    if not apply_:
        print("\n[dry-run] --apply 로 실제 반영")
        return
    for path, data in ((pp, P), (rp, R)):
        shutil.copy(path, path + ".bak-linefill")
        json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n✅ parts.json · recipes.json 반영 → 다음: patch_cast_cost.py")


def _add_recipe(cat, g, lv, name, rows, R, nxt, recs, wmat):
    cand = [r for r in rows if r["cat"] == cat and r["grade"] == g
            and r["craftable"] and r["src"] not in SKIPSRC]
    if not cand:
        return
    b = min(cand, key=lambda r: abs(r["lv"] - lv))
    rid_src = next(k2 for k2, v in R["recipes"].items()
                   if (v.get("rodPartName") or v.get("resultPartName")) == b["name"])
    seedrec = R["recipes"][rid_src]
    key = "낚싯대" if cat == "낚싯대" else ("작살" if cat == "작살" else "part")
    rid = f"{ {'낚싯대':'R','작살':'HP','part':'P'}[key] }{nxt[key]:02d}".replace(" ", "")
    nxt[key] += 1
    ing = [dict(i) for i in seedrec["ingredients"]]
    if not any(i.get("typeOrMatId") == wmat for i in ing):
        dn, mc = wmat, "paper"
        for v in R["recipes"].values():
            for x in v.get("ingredients", []):
                if x.get("typeOrMatId") == wmat:
                    dn, mc = x.get("displayName"), x.get("mcItem")
                    break
        ing.append({"kind": "custom", "typeOrMatId": wmat,
                    "displayName": dn, "mcItem": mc, "qty": 2})
    rk = "rodPartName" if cat == "낚싯대" else "resultPartName"
    R["recipes"][rid] = {**{a: b2 for a, b2 in seedrec.items()
                            if a not in ("id", "displayName", "rodPartName",
                                         "resultPartName", "ingredients")},
                         "id": rid, "displayName": name, rk: name, "ingredients": ing}
    recs.append((rid, name, b["name"]))


if __name__ == "__main__":
    main()
