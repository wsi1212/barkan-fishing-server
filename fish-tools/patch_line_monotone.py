#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_line_monotone.py — 한 «계열» 안에서 원가를 레벨 순으로 단조화한다.

## 왜 (유저 지시 2026-09-02: 「채집 계열 역전 고쳐줘」)
채집(재료확률) 낚싯대 10종의 원가가 레벨과 어긋나 있었다 — `수집왕`(Lv67, 재료확률 50)이
`유물사냥꾼`(Lv44, 재료확률 45)의 2/3 값이다. 23레벨 높고 성능도 높은데 더 싸다.
유저 기준: 「각 계열 안에서도 성능·렙제에 따라 차이 있어야 함」.

## 어떻게 — «값의 다중집합»을 보존하고 순서만 바로잡는다
목표 원가를 새로 발명하지 않는다. 그 계열이 지금 가진 원가 값들을 **정렬해서 레벨 순으로
다시 배정**한다. 그래서 합계·최소·최대가 그대로다 — 계열 전체 부담을 바꾸는 결정은
따로 받아야 하는 사안이고, 여기서는 순서만 고친다.
동률 구간은 평균 주위로 ±TIE_SPREAD 만큼 대칭 분산시켜 **강한 단조**로 만든다
(합은 대칭이라 보존된다). 성능이 평평한 구간이라도 렙제 서열은 남아야 한다.

## 계열 판정
「그 스탯을 가진 것」이 아니라 **「그 스탯이 그 장비의 최대 스탯인 것」**으로 고른다.
★전자로 고르면 `교역 릴`(재료확률 3, 실제로는 돈 계열)·`신기루 줄`(2)·`사구 찌`(3)
  처럼 곁가지로 조금 붙은 다른 계열이 섞여 들어와 엉뚱한 걸 조정한다(실측).

## 수량 반영
원재료·중간재 수량에 목표비를 곱한다. 병목은 최댓값이라 일률 배율이면 그대로 따라온다.
반올림 때문에 한 번에 안 맞으므로 몇 번 반복한다. 앞선 결정 두 개는 침범하지 않는다:
  · 단단한자루 ≥ 등급 하한(GRADE_FLOOR)   · 정제된갈고리 ≤ HOOK_CAP, 초과분은 자루로
자루·갈고리는 개당 포획수가 같아 그 전환은 원가 중립이다.

사용:  python3 patch_line_monotone.py --stat 재료확률 --category 낚싯대 [--apply]
"""
import argparse
import importlib.util
import json
import pathlib

LIVE = pathlib.Path(
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
REPO = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = pathlib.Path.home() / "development" / "blockship-plugin"
CPH = 190.1
TIE_SPREAD = 0.04
GRADE_FLOOR = {"D": 1, "C": 3, "B": 5, "A": 8, "S": 14}
HOOK_CAP = 10
GRIP, HOOK = "단단한자루", "정제된갈고리"
ITERS = 8


def _ru():
    f = REPO / ".claude/skills/balance-audit/scripts/region_unlock.py"
    spec = importlib.util.spec_from_file_location("region_unlock", f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stat", default="재료확률")
    ap.add_argument("--category", default="낚싯대")
    ap.add_argument("--part-type", default=None, help="category=부품 일 때 릴/줄/바늘/찌")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    RU = _ru()

    rec_p = LIVE / "recipes.json"
    root = json.loads(rec_p.read_text(encoding="utf-8"))
    recs = root["recipes"]
    parts = json.loads((LIVE / "parts.json").read_text(encoding="utf-8"))["parts"]
    drops = json.loads((LIVE / "materials.json").read_text(encoding="utf-8"))["dropTables"]

    meta = {}
    for grp in parts.values():
        for n, v in grp.items():
            f = v.split("|")
            if len(f) >= 7:
                meta[n] = (f[1], int(f[5]) if f[5].isdigit() else 99, f[4])

    inter = {}
    for rid, r in recs.items():
        if r.get("category") != "재료":
            continue
        out = None
        for ln in (r.get("result") or {}).get("lore") or []:
            if ln.startswith("&8mat:"):
                out = ln.split(":", 1)[1].strip()
        if out:
            inter[out] = {(i.get("typeOrMatId") or i.get("mcItem")): i.get("qty", 1)
                          for i in r.get("ingredients") or []}

    def expand(d, depth=0):
        out = {}
        for m, q in d.items():
            if m in inter and depth < 4:
                for k, v in expand(inter[m], depth + 1).items():
                    out[k] = out.get(k, 0) + q * v
            else:
                out[m] = out.get(m, 0) + q
        return out

    def cost(d, lv):
        w = 0.0
        for m, q in expand(d).items():
            b = 0.0
            for rg, ds in drops.items():
                if RU.unlock_level(rg) > lv:
                    continue
                for x in ds:
                    if x["matId"] == m:
                        b = max(b, x["chance"] / 100)
            if b:
                w = max(w, q / b)
        return w

    def stats(s):
        out = {}
        for part in s.split(","):
            if ":" in part:
                k, v = part.split(":", 1)
                if v.strip().lstrip("-").isdigit():
                    out[k.strip()] = int(v)
        return out

    # ── 계열 수집 ──
    line = []
    for rid, v in recs.items():
        if v.get("category") != a.category:
            continue
        if a.part_type and v.get("resultPartType") != a.part_type:
            continue
        nm = v.get("rodPartName") or v.get("resultPartName") or v.get("displayName")
        if nm not in meta:
            continue
        g, lv, sraw = meta[nm]
        st = stats(sraw)
        if not st or a.stat not in st:
            continue
        if st[a.stat] != max(st.values()):        # ★그 스탯이 «최대»인 것만
            continue
        q = {(i.get("typeOrMatId") or i.get("mcItem")): i.get("qty", 1)
             for i in v["ingredients"]}
        line.append({"rid": rid, "nm": nm, "g": g, "lv": lv, "st": st[a.stat],
                     "q0": dict(q), "c0": cost(q, lv), "v": v})
    if len(line) < 3:
        print(f"계열 {a.category}/{a.stat} 이 {len(line)}종 — 조정할 게 없다")
        return 0
    line.sort(key=lambda d: d["lv"])

    # ── 목표: 지금 값들을 정렬해 레벨 순으로 재배정 + 동률 분산 ──
    tg = sorted(d["c0"] for d in line)
    i = 0
    while i < len(tg):
        j = i
        while j + 1 < len(tg) and abs(tg[j + 1] - tg[i]) < 1e-9:
            j += 1
        m = j - i + 1
        if m > 1:
            mean = tg[i]
            for k in range(m):
                tg[i + k] = mean * (1 + TIE_SPREAD * (k - (m - 1) / 2))
        i = j + 1
    for d, t in zip(line, tg):
        d["target"] = t

    # ── 수량 반영 ──
    for d in line:
        q = dict(d["q0"])
        for _ in range(ITERS):
            cur = cost(q, d["lv"])
            if not cur:
                break
            ratio = d["target"] / cur
            if abs(ratio - 1) < 0.01:
                break
            q = {m: max(1, round(n * ratio)) for m, n in q.items()}
            # 앞선 결정 보존: 갈고리 상한 초과분은 자루로(원가 중립), 자루는 등급 하한 이상
            if q.get(HOOK, 0) > HOOK_CAP:
                over = q[HOOK] - HOOK_CAP
                q[HOOK] = HOOK_CAP
                q[GRIP] = q.get(GRIP, 0) + over
            if GRIP in q:
                q[GRIP] = max(q[GRIP], GRADE_FLOOR.get(d["g"], 0))
        d["q1"] = q
        d["c1"] = cost(q, d["lv"])

    inv0 = sum(1 for i in range(1, len(line)) if line[i]["c0"] < line[i - 1]["c0"])
    inv1 = sum(1 for i in range(1, len(line)) if line[i]["c1"] < line[i - 1]["c1"])
    print(f"═══ {a.category}{'/' + a.part_type if a.part_type else ''} · {a.stat} 계열 "
          f"{len(line)}종 — 역전 {inv0} → {inv1}건 ═══")
    for d in line:
        mark = "" if d["c1"] >= (d.get("_p") or 0) else ""
        print(f"  {d['g']} Lv{d['lv']:<3}{d['nm']:<20}{d['c0']:>5.0f} → {d['c1']:>5.0f}포획"
              f"  ({d['c1'] / CPH:>4.1f}h)  {a.stat} {d['st']:>2}{mark}")
        ch = [f"{m}×{d['q0'].get(m, 0)}→{n}" for m, n in d["q1"].items()
              if d["q0"].get(m, 0) != n]
        if ch:
            print(f"        {'  '.join(ch)}")
    t0 = sum(d["c0"] for d in line)
    t1 = sum(d["c1"] for d in line)
    # ★미끼 계열은 낚시 드롭이 아닌 재료(압축흑정석)만 써서 원가가 전부 0 이다 —
    #   0 으로 나누면 죽는다(2026-09-02 실측). 조정할 게 없으니 그대로 알리고 끝낸다.
    if t0 <= 0:
        print("\n이 계열은 낚시 원가가 0 이다(광질/제작 재료만 씀) — 조정하지 않는다")
        return 0
    print(f"\n계열 합계 {t0:.0f} → {t1:.0f}포획 ({(t1 - t0) / t0 * 100:+.1f}%)")
    if not a.apply:
        print("(--apply 를 붙이면 실제로 씀)")
        return 0
    for d in line:
        base = {(i.get("typeOrMatId") or i.get("mcItem")): i for i in d["v"]["ingredients"]}
        out = []
        for m, n in d["q1"].items():
            src = base.get(m)
            if src is None:
                continue
            out.append(dict(src, qty=n))
        d["v"]["ingredients"] = out
    blob = json.dumps(root, ensure_ascii=False, indent=2) + "\n"
    for t in (rec_p, REPO / "ops/blockship-data/recipes.json", PLUGIN / "recipes.json"):
        if t.parent.exists():
            t.write_text(blob, encoding="utf-8")
            print(f"  ✓ {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
