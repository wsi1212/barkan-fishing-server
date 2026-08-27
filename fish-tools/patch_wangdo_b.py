#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_wangdo_b.py — 왕도에 **B급 Lv35~39** 층을 신설한다 (2026-08-27).

유저 요청:
    "왕도 같은 경우에 지금 미끼 하나밖에 없고 아이템 다 ㅈㄴ 고랩제던데 퀘스트 라인상
     나름 초반? 에도 오니까 B급한 3n렙 정도도 필요할듯?"

## 왜 이 층이 필요한가 — 두 구멍이 정확히 맞물린다

  ① **레벨 구멍**: `Lv35~39` 에 살 수 있는 장비가 **전 카테고리 0종**이다.
     (사막 B 가 Lv34 에서 끝나고 사막 A 가 Lv40 에서 시작한다.)
  ② **라인 구멍**: B 급에 **숙련·성장** 라인이 부품 슬롯 대부분에서 비어 있다
     (릴 숙련 · 줄 성장 · 바늘 숙련·성장 · 찌 숙련·성장 · 미끼 숙련·성장).
  ③ 왕도 자체는 **A급 Lv52~62 만** 있고 부품은 슬롯당 1종(바르칸 시리즈)뿐이었다.

그래서 왕도 B = «Lv35~39 × B 급에 없던 라인» 으로 채운다. 셋이 한 번에 해결된다.

## 스탯을 어떻게 정하나 — 손으로 안 짓는다

같은 (카테고리, 라인) 의 **기존 균형 잡힌 아이템을 씨앗**으로 쓰고 레벨 차이만큼만 스케일한다:

    새 스탯 = round(씨앗 스탯 × exp(EFF_B × Δ레벨))        EFF_B = rod_lines.EFF_B (레벨당 +6.5%)

★새로 짓지 않는 이유: 라인 정체성·기반 스탯·슬롯 주스탯이 이미 씨앗에 담겨 있다. 손으로
  지으면 그 세 가지를 매번 다시 맞춰야 하고, 실제로 이번 세션에 그렇게 하다 두 번 틀렸다.
★씨앗이 B 에 없는 라인(숙련·성장)은 C·D 급 씨앗을 쓴다. 그런데 Δ레벨이 30 이 넘으면
  스케일이 ×7 까지 뛴다 — 초판이 그래서 «방벽 찌 등급업 22»(B급 최대의 3배), «방벽 바늘
  크리확률 58» 같은 걸 뱉었다. 그래서 안전장치 둘을 건다:
    · **기반은 목적지 등급에서 가져온다.** 씨앗의 «라인 초과분»만 스케일하고 기반(그 등급
      전 종에 깔린 p25)은 B 급 값을 쓴다. 기반까지 곱하면 난이도·등급업이 통째로 부푼다.
    · **스케일 상한 K_CAP, 스탯별 상한 STAT_CAP** — 그 카테고리 B급 최대치의 배수로 자른다.

레시피는 같은 등급 최근접 레벨 아이템에서 베끼고 **수량은 `patch_cast_cost.py` 가 다시 맞춘다**
(권위 분리 — 여기서 캐스트를 정하지 않는다).

사용:
    python3 patch_wangdo_b.py <BlockShip경로>            # dry-run
    python3 patch_wangdo_b.py <BlockShip경로> --apply
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


SRC = "왕도"
GRADE = "B"
#: 왕도 테마 이름 ↔ 라인. 왕성의 기능 부서로 라인을 은유한다.
THEME = {"숙련": "방벽", "성장": "문서고", "크리": "사자", "행운": "왕관",
         "상인": "세관", "채집": "조병창", "기동": "전령", "깡스탯": "기사단",
         "관통": "창병", "잠수": "잠수부"}
#: 신설 목록 — (카테고리, 라인, 레벨). 라인 구멍(숙련·성장)을 최우선으로 채운다.
PLAN = [
    # 낚싯대 6라인 전부 — 이 층의 «주력»이라 6개 다 둔다
    ("낚싯대", "숙련", 35), ("낚싯대", "크리", 36), ("낚싯대", "왕관", 37),
    ("낚싯대", "상인", 37), ("낚싯대", "성장", 38), ("낚싯대", "채집", 39),
    # 작살 — B·A 에 통째로 없는 라인(기동·채집·깡스탯) 우선 + 상인·관통
    ("작살", "기동", 35), ("작살", "채집", 36), ("작살", "깡스탯", 37),
    ("작살", "상인", 38), ("작살", "관통", 39),
    # 부품 — 슬롯별 «없는 라인» + 가장 오래된 라인 갱신
    ("릴", "숙련", 35), ("릴", "크리", 37), ("릴", "행운", 38),
    ("줄", "성장", 35), ("줄", "숙련", 36), ("줄", "크리", 38),
    ("바늘", "숙련", 35), ("바늘", "성장", 37), ("바늘", "행운", 38),
    ("찌", "숙련", 35), ("찌", "성장", 37), ("찌", "크리", 38),
    ("미끼", "숙련", 35), ("미끼", "성장", 37), ("미끼", "크리", 38),
]
#: 낚싯대의 «왕관» 은 행운 라인이다(이름을 라인 키로 쓰지 않으려고 별칭을 뒀다)
ALIAS = {"왕관": "행운"}
#: 씨앗이 D~B 어디에도 없는 라인 — 손으로 «라인 가산분»만 적는다(기반은 목적지 등급에서).
#  ★이 넷은 그 라인이 그 카테고리에 **한 번도 존재한 적이 없다**는 뜻이다:
#    작살 기동·깡스탯 — 수영속도/돌진쿨감이 기반에 묻혀 라벨이 안 잡힌다(돌진쿨감은 45+ 필요)
#    릴·미끼 숙련     — 난이도·도망감소를 주스탯으로 가진 릴·미끼가 아예 없었다
FALLBACK = {
    ("작살", "기동"):   dict(수영속도=40, 돌진쿨감=50, 경험치=18),
    ("작살", "깡스탯"): dict(공격력=2, 수중호흡=22, 수영속도=18, 호흡시간=10),
    ("릴", "숙련"):     dict(난이도=2, 도망감소=30),
    ("미끼", "숙련"):   dict(난이도=2, 도망감소=28),
}

#: 씨앗 스케일 상한. Δ레벨 30 이면 exp(0.0628×30)=6.6 인데 그대로 쓰면 B급을 넘어선다.
K_CAP = 2.4
#: 스탯별 상한 = 그 카테고리 B급 기존 최대치 × 이 배수. 신설이 기존 최고를 크게 넘지 않게.
STAT_CAP = 1.5

#: 왕도 테마 재료 — 왕도 A급 레시피가 실제로 쓰는 것에서 고른다(새 재료를 만들지 않는다).
WD_MAT = "강화에메랄드"


def _add_recipe(cat, lv, name, rows, R, nxt, SKIPSRC, recs, WD_MAT, GRADE):
    """같은 카테고리·등급의 최근접 레벨 레시피를 베끼고 왕도 테마 재료를 섞는다.
    ★수량은 여기서 정하지 않는다 — patch_cast_cost.py 가 사다리에 맞춘다."""
    cand = [r for r in rows if r["cat"] == cat and r["grade"] == GRADE
            and r["craftable"] and r["src"] not in SKIPSRC]
    if not cand:
        return
    base_item = min(cand, key=lambda r: abs(r["lv"] - lv))
    rid_src = next(k2 for k2, v in R["recipes"].items()
                   if (v.get("rodPartName") or v.get("resultPartName")) == base_item["name"])
    seedrec = R["recipes"][rid_src]
    key = "낚싯대" if cat == "낚싯대" else ("작살" if cat == "작살" else "part")
    pre = {"낚싯대": "R", "작살": "HP", "part": "P"}[key]
    rid = f"{pre}{nxt[key]:02d}"
    nxt[key] += 1
    ing = [dict(i) for i in seedrec["ingredients"]]
    if not any(i.get("typeOrMatId") == WD_MAT for i in ing):
        dn, mc = WD_MAT, "emerald"
        for v in R["recipes"].values():
            for x in v.get("ingredients", []):
                if x.get("typeOrMatId") == WD_MAT:
                    dn, mc = x.get("displayName"), x.get("mcItem")
                    break
        ing.append({"kind": "custom", "typeOrMatId": WD_MAT,
                    "displayName": dn, "mcItem": mc, "qty": 2})
    rk = "rodPartName" if cat == "낚싯대" else "resultPartName"
    R["recipes"][rid] = {**{a: b for a, b in seedrec.items()
                            if a not in ("id", "displayName", "rodPartName",
                                         "resultPartName", "ingredients")},
                         "id": rid, "displayName": name, rk: name, "ingredients": ing}
    recs.append((rid, name, base_item["name"]))


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

    # ── 라인 라벨 (등급별 기반 차감) ────────────────────────────────────
    SKIPSRC = {"캐시", "개발자", "잠수상점"}
    label = {}
    for cat in {r["cat"] for r in rows}:
        for g in ("D", "C", "B", "A"):
            arr = [r for r in rows if r["cat"] == cat and r["grade"] == g
                   and r["src"] not in SKIPSRC]
            if not arr:
                continue
            b = VS.group_base(arr)
            for r in arr:
                label[r["name"]] = VS.line_label(r["stats"], cat, b)

    # (카테고리, 등급) 기반 p25 + 그 카테고리 B급 스탯 최대치
    base_of, capmax = {}, {}
    for cat in {r["cat"] for r in rows}:
        for g in ("D", "C", "B", "A"):
            arr = [r for r in rows if r["cat"] == cat and r["grade"] == g
                   and r["src"] not in SKIPSRC]
            if arr:
                base_of[(cat, g)] = {a: b for a, b in VS.group_base(arr).items() if b}
        arr = [r for r in rows if r["cat"] == cat and r["grade"] == GRADE
               and r["src"] not in SKIPSRC]
        capmax[cat] = {k2: max(float(r["stats"].get(k2, 0) or 0) for r in arr)
                       for k2 in {x for r in arr for x in r["stats"]}} if arr else {}
    meta = {r["name"]: r for r in rows}

    def pick_seed(cat, line):
        """같은 (카테고리, 라인) 의 최고레벨 아이템. B → C → D 순으로 찾는다."""
        for g in ("B", "C", "D"):
            c = [r for r in rows if r["cat"] == cat and r["grade"] == g
                 and label.get(r["name"]) == line and r["src"] not in SKIPSRC]
            if c:
                return max(c, key=lambda r: r["lv"])
        return None

    def price_at(cat, lv):
        """같은 카테고리 B급 가격을 레벨로 회귀해 보간(하드코딩 금지)."""
        c = [r for r in rows if r["cat"] == cat and r["grade"] == GRADE
             and r["price"] > 0 and r["src"] not in SKIPSRC]
        if not c:
            return 100000
        c.sort(key=lambda r: r["lv"])
        lo = max([r for r in c if r["lv"] <= lv], key=lambda r: r["lv"], default=c[0])
        hi = min([r for r in c if r["lv"] >= lv], key=lambda r: r["lv"], default=c[-1])
        if hi["lv"] == lo["lv"]:
            base = lo["price"]
        else:
            t = (lv - lo["lv"]) / (hi["lv"] - lo["lv"])
            base = lo["price"] + t * (hi["price"] - lo["price"])
        # 구간 밖이면 레벨당 +6.5% 로 외삽
        if lv > c[-1]["lv"]:
            base = c[-1]["price"] * math.exp(RL.EFF_B * (lv - c[-1]["lv"]))
        return int(round(base / 100.0) * 100)

    added, recs, missing = [], [], []
    nxt = {"낚싯대": max(int(k[1:]) for k in R["recipes"]
                       if k.startswith("R") and k[1:].isdigit()) + 1,
           "part": max(int(k[1:]) for k in R["recipes"]
                       if k.startswith("P") and k[1:].isdigit()) + 1,
           "작살": max(int(k[2:]) for k in R["recipes"]
                     if k.startswith("HP") and k[2:].isdigit()) + 1}

    for cat, lname, lv in PLAN:
        line = ALIAS.get(lname, lname)
        seed = pick_seed(cat, line)
        name = f"{THEME.get(lname, lname)} {cat if cat != '낚싯대' else '낚싯대'}"
        if name in P["parts"][cat]:
            continue
        if seed is None and (cat, line) not in FALLBACK:
            missing.append((cat, line))
            continue
        if seed is None:
            stats = dict(base_of[(cat, GRADE)])
            for sk, sv in FALLBACK[(cat, line)].items():
                stats[sk] = stats.get(sk, 0) + sv
            stats = {a: (int(b) if float(b).is_integer() else b)
                     for a, b in stats.items() if b > 0}
            dur = max(int(l.split("|")[3]) for l in P["parts"][cat].values()
                      if l.split("|")[1] == GRADE)
            price = price_at(cat, lv)
            P["parts"][cat][name] = "|".join(
                [name, GRADE, str(price), str(dur),
                 ",".join(f"{a}:{b:g}" for a, b in stats.items()), str(lv), SRC])
            added.append((cat, line, lv, name, price, stats, "★손작성(FALLBACK)", lv))
            _add_recipe(cat, lv, name, rows, R, nxt, SKIPSRC, recs, WD_MAT, GRADE)
            continue
        k = min(K_CAP, math.exp(RL.EFF_B * (lv - seed["lv"])))
        sbase = base_of[(cat, seed["grade"])]
        tbase = base_of[(cat, GRADE)]
        cap = capmax[cat]
        stats = dict(tbase)                      # ① 기반은 목적지 등급에서
        for sk, sv in seed["stats"].items():
            if not isinstance(sv, (int, float)):
                continue
            exc = sv - sbase.get(sk, 0)          # ② 라인 초과분만 스케일
            if exc <= 0:
                continue
            if sk in ("공격력", "크리배율", "더블찬스", "트리플찬스", "난이도"):
                add = round(exc) + (1 if k >= 1.6 else 0)
            else:
                add = max(1, int(round(exc * k)))
            stats[sk] = stats.get(sk, 0) + add
        # ③ 스탯별 상한
        stats = {a: min(b, max(1, round(cap.get(a, b) * STAT_CAP))) for a, b in stats.items()}
        stats = {a: (int(b) if float(b).is_integer() else b) for a, b in stats.items() if b > 0}
        dur = max(int(l.split("|")[3]) for l in P["parts"][cat].values()
                  if l.split("|")[1] == GRADE)
        price = price_at(cat, lv)
        P["parts"][cat][name] = "|".join(
            [name, GRADE, str(price), str(dur),
             ",".join(f"{a}:{b:g}" for a, b in stats.items()), str(lv), SRC])
        added.append((cat, line, lv, name, price, stats, seed["name"], seed["lv"]))

        _add_recipe(cat, lv, name, rows, R, nxt, SKIPSRC, recs, WD_MAT, GRADE)

    print(f"왕도 {GRADE}급 신설 {len(added)}종 (Lv35~39 — 전 카테고리 0종이던 구간)")
    cur = None
    for cat, line, lv, name, price, stats, sn, slv in added:
        if cat != cur:
            print(f"  [{cat}]")
            cur = cat
        print(f"    Lv{lv} {name:<14}{line:<5}{price:>10,}원  씨앗 {sn}(Lv{slv}) "
              f"×{math.exp(RL.EFF_B*(lv-slv)):.2f}")
        print(f"         {', '.join(f'{a}:{b:g}' for a, b in stats.items())}")
    if missing:
        print(f"\n★씨앗 없음 {len(missing)}건 (그 라인이 D~B 어디에도 없다): {missing}")
    print(f"\n레시피 {len(recs)}건 (수량은 patch_cast_cost 가 맞춘다)")

    if not apply_:
        print("\n[dry-run] --apply 로 실제 반영")
        return
    for path, data in ((pp, P), (rp, R)):
        shutil.copy(path, path + ".bak-wangdo")
        json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n✅ parts.json · recipes.json 반영")
    print("   → 다음: patch_cast_cost.py 로 요구 캐스트를 사다리에 맞출 것")


if __name__ == "__main__":
    main()
