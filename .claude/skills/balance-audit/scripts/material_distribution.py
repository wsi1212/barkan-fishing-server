#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
material_distribution.py — 재료 «지역 분배» 감사 (2026-08-27 신설).

유저 질문 그대로가 검사 항목이다:
  ① 각 지역마다 **가기 어려울수록** 더 희귀하고 좋은 게 나오는가?
     (개수·확률·재료 등급이 난이도와 함께 오르는가)
  ② 그렇다고 정상 같은 데서 **모든 게 다 나오는** 건 아니고
     «강 전용 / 늪지대 전용» 같은 **독점**이 있는가?

────────────────────────────────────────────────────────────────────────────
«가기 어려움»을 무엇으로 재는가 — 판매상 거리 + 어종 난이도
────────────────────────────────────────────────────────────────────────────
★**주축은 «가장 가까운 물고기 판매상까지의 거리»**다(2026-08-27 유저 확정). 고정점
  (항구)이 아니다 — `/판매`(SellCommand)는 «가장 가까운 판매상»으로 안내하므로
  (`shop=true` + `shopItems` 빈 NPC) 상단마을에서 낚으면 상단마을에서 판다.
  페리는 미구성(`ferries.json` 에 `test` 노선 하나)이라 이동은 전부 도보/말이고
  **거리가 곧 왕복 비용**이다.
  판매상 좌표의 권위는 **prod `Citizens/saves.yml`** — npc.json 에는 좌표가 없고
  dev 사본은 낡았다(판매상 8명 중 1명만 있었다).

보조축은 난이도다. regions.json 의 레벨제한은 대부분 0 이라(원양 50 · 심해협곡 62 등
소수만) 게이트가 아니고, 실제 난이도는 **그 지역 어종 풀의 평균 등급**이다 — 등급이 높으면 미니게임
존폭이 좁아져(zoneWidth = 8+floor(net/2)) 장비 없이는 아예 못 낚는다. 그래서
`fish.json.regions[지역]["기본"]` 의 등급 분포로 «평균 등급 인덱스»(E=0 … G=8)를 낸다.
실측 지역 분포도 이 순서를 뒷받침한다(쉬운 항구 67.2% ↔ 어려운 늪지대 1.3%).

────────────────────────────────────────────────────────────────────────────
«좋은 재료»를 무엇으로 재는가
────────────────────────────────────────────────────────────────────────────
두 축을 같이 본다.
  · **재료 티어** = 그 재료를 쓰는 아이템의 **최고 등급**(레시피 BOM 역추적).
    E~D 짜리에만 쓰이는 재료 = 초반 재료 · A~S 에 쓰이면 종결 재료.
  · **가치 가중치** = 그 재료를 요구하는 레시피의 **최저 등급**(E=1 … S=6). «어느 티어부터
    필요한가»가 곧 값이다. 최고 등급으로 재면 기초 재료(물고기비늘·강화실)가 G 급에도
    쓰여 전부 6 이 되어 변별력이 없다.
  · **희소성** = 전 지역 합확률의 역수. 흔한 재료는 값이 없다.

★2026-08-27 2차 설계부터 **1번 지표는 «합확률»이 아니라 «가치 가중 기대치»** 다.
  유저 확정: "합이 너무 큰데 75%가 합이면 재료 보너스 20%만 달려도 매번 하나씩은 나온다는
  말이잖아. 합 차이를 조금 줄일 필요가 있어보임. 합차이가 드라마틱 하지 않지만 대신 더
  비싼 가치를 지니는 재료가 나오잖아 대신"
  `rollMaterials` 가 표의 모든 항목을 독립으로 굴리고 `× (1 + 재료확률/100)` 을 곱하므로
  **합 = 캐스트당 기대 개수**다. 합으로 차별화하면 어려운 지역일수록 «매 캐스트 드롭 +
  채팅 도배»가 된다. 그래서 합은 좁게(22~39%) 두고 «무엇이 나오는가»로 차별화한다.
LP 그림자가격(material_value)은 «지금 레시피 수요»에 따라 움직여서 분배 자체의
정당성을 재는 데는 부적절하다 — 수요가 없으면 좋은 재료도 0 이 된다.

사용:
    python3 material_distribution.py            # 전체 감사
    python3 material_distribution.py --matrix   # 지역 × 재료 행렬만
"""
import argparse, collections, json, math, os, sys

BS = os.environ.get("BLOCKSHIP_DATA",
                    "/Users/user/Library/Application Support/feather/player-server/servers/"
                    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
GRADES = list("EDCBASMLG")
#: 물고기 판매상 좌표 — prod Citizens/saves.yml 실측 (2026-08-27).
#  `shop=true` 이면서 `shopItems` 가 빈 NPC = 물고기 판매상(SellCommand 필터와 동일).
#  ★drift: npc.json 에는 한스·궁정상인이 있는데 prod 에 스폰돼 있지 않고,
#    반대로 prod 의 헬가는 npc.json 에 없다. 좌표 권위는 prod saves.yml 이다.
SELLERS = {"그레타": (301.5, 1005.5), "오토": (444.5, 919.5), "헬가": (369.5, 873.5),
           "카심": (-428.5, 211.5), "틸만": (425.6, 199.8),
           "파올로": (1132.0, -65.0), "루카": (1168.0, -167.0)}

#: 실측 지역 분포(%) — audits/snapshots/*-players.raw.json region_mix_pct
SHARE = {"항구": 67.23, "강": 18.88, "협곡": 4.32, "오아시스": 4.27, "늪지대": 1.29,
         "정상": 1.23, "기억의_연못": 1.16, "스폰도시": 0.8, "강_상류": 0.51,
         "폭포": 0.1, "레드_로드": 0.1, "바르칸": 0.05, "상단마을": 0.03}


def quest_sinks():
    """재료 → 퀘스트에서 언급된 횟수.

    ★레시피만 보면 «죽은 재료»를 오판한다 — 오아시스 전용 5종(미감정 유물·깨진 토기 조각·
      진주조개·고대 유물·보석)은 레시피 사용처가 0 이지만 **퀘스트 제출처**(주간_토기복원 8개·
      주간_고대유물제출 3개·사피르04·견습생03·실비아01)와 **유물 감정 GUI**
      (`crafting/ArtifactAppraisalGui`: 미감정 유물 + 감정료 500원 → 토기55%/진주조개20%/
      보석15%/고대유물8%/별빛진주3개 2%)가 있다.
    """
    try:
        raw = open(os.path.join(BS, "quests.json"), encoding="utf-8").read()
    except OSError:
        return {}
    M = json.load(open(os.path.join(BS, "materials.json"), encoding="utf-8"))["materials"]
    return {m: raw.count(d.get("name", m)) for m, d in M.items()
            if raw.count(d.get("name", m)) > 0}


def load():
    M = json.load(open(os.path.join(BS, "materials.json"), encoding="utf-8"))
    F = json.load(open(os.path.join(BS, "fish.json"), encoding="utf-8"))
    R = json.load(open(os.path.join(BS, "recipes.json"), encoding="utf-8"))
    P = json.load(open(os.path.join(BS, "parts.json"), encoding="utf-8"))
    return M, F, R, P


def centroid(rd):
    """지역 폴리곤의 **면적 가중** 무게중심. 단순 평균은 정점 밀집 쪽으로 쏠린다."""
    poly = rd.get("polygon") or []
    if len(poly) >= 3:
        A = cx = cy = 0.0
        for i in range(len(poly)):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % len(poly)]
            cr = x1 * y2 - x2 * y1
            A += cr
            cx += (x1 + x2) * cr
            cy += (y1 + y2) * cr
        if abs(A) > 1e-9:
            A *= 0.5
            return cx / (6 * A), cy / (6 * A)
        return sum(q[0] for q in poly) / len(poly), sum(q[1] for q in poly) / len(poly)
    p1, p2 = rd.get("pos1"), rd.get("pos2")
    if p1 and p2 and p1 != [0, 0, 0]:
        return (p1[0] + p2[0]) / 2, (p1[2] + p2[2]) / 2
    return None


def seller_distance(rd):
    """그 지역 중심 → 가장 가까운 물고기 판매상 (거리, 이름). 좌표 없으면 (None, None)."""
    c = centroid(rd)
    if not c:
        return None, None
    return min((math.dist(c, xz), n) for n, xz in SELLERS.items())


def region_difficulty(F):
    """지역 → (평균 등급 인덱스, 어종 수, 최고 등급). 등급이 'E~S' 처럼 범위인 건 버린다."""
    fish, reg = F["fish"], F["regions"]
    out = {}
    for area, d in reg.items():
        c = collections.Counter()
        for n in d.get("기본", []):
            g = (fish.get(n) or {}).get("grade")
            if g in GRADES:
                c[g] += 1
        tot = sum(c.values())
        if not tot:
            continue
        out[area] = (sum(GRADES.index(g) * v for g, v in c.items()) / tot, tot,
                     max(c, key=lambda g: GRADES.index(g)), c)
    return out


def material_tier(R, P):
    """재료 → (그 재료를 쓰는 아이템의 최고 등급, 최저 등급, 사용 아이템 수).

    가공재는 하위 BOM 으로 전개한다 — `단단한 자루`를 쓰는 A급 낚싯대가 있으면
    그 자루의 재료(강화실·물고기비늘)도 A급 수요를 가진 셈이다.
    """
    grade_of = {}
    for slot, items in P["parts"].items():
        for name, raw in items.items():
            grade_of[name] = raw.split("|")[1]
    # 레시피: 결과 이름 → 재료 목록
    ing_of, made = {}, set()
    for rid, r in R["recipes"].items():
        out = r.get("resultPartName") or r.get("rodPartName") or r.get("displayName")
        if not out:
            continue
        ing_of[out] = [(i["typeOrMatId"], i["qty"]) for i in r["ingredients"]]
        made.add(out)

    def expand(name, depth=0):
        """아이템 → 최종 재료 집합(가공재 전개)."""
        if depth > 4:
            return set()
        out = set()
        for mid, _q in ing_of.get(name, []):
            out.add(mid)
            if mid in ing_of:                     # 가공재(그 자체가 레시피 결과)
                out |= expand(mid, depth + 1)
            else:
                # matId 가 «표시이름 없는 id» 인 가공재도 있다 — 이름 매칭 재시도
                for cand in ing_of:
                    if cand.replace(" ", "") == mid:
                        out |= expand(cand, depth + 1)
                        break
        return out

    use = collections.defaultdict(list)
    for item, g in grade_of.items():
        if item not in ing_of:
            continue
        for mid in expand(item):
            use[mid].append(g)
    return {m: (max(gs, key=lambda g: GRADES.index(g)),
                min(gs, key=lambda g: GRADES.index(g)), len(gs))
            for m, gs in use.items()}


def spearman(xs, ys):
    def rank(v):
        s = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(s):
            j = i
            while j + 1 < len(s) and v[s[j + 1]] == v[s[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[s[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", action="store_true")
    a = ap.parse_args()
    M, F, R, P = load()
    dt, mats = M["dropTables"], M["materials"]
    areas = list(dt)
    allm = sorted({e["matId"] for t in dt.values() for e in t})
    diff = region_difficulty(F)
    tier = material_tier(R, P)

    if a.matrix:
        print(f"{'재료':<12}" + "".join(f"{x[:4]:>6}" for x in areas) + f"{'출처':>5}{'합%':>6}")
        for m in allm:
            row = {x: 0 for x in areas}
            for x, t in dt.items():
                for e in t:
                    if e["matId"] == m:
                        row[x] = e["chance"]
            print(f"{m:<12}" + "".join(f"{(row[x] or ''):>6}" for x in areas)
                  + f"{sum(1 for v in row.values() if v):>5}{sum(row.values()):>6}")
        return

    # ── ① 난이도 ↔ 드랍 풍족도 ────────────────────────────────────────
    print("=" * 100)
    print("① 가기 어려울수록 더 좋은 게 나오는가")
    print("=" * 100)
    excl = collections.defaultdict(list)
    for m in allm:
        src = [x for x, t in dt.items() if any(e["matId"] == m for e in t)]
        if len(src) == 1:
            excl[src[0]].append(m)
    Rj = json.load(open(os.path.join(BS, "regions.json"), encoding="utf-8"))
    print(f"\n{'지역':<14}{'판매상':>7}{'거리':>6}{'난이도':>6}{'비용':>6}  |{'재료':>5}{'합%':>6}"
          f"{'전용':>5}  실측방문%")
    rows = []
    for area in areas:
        t = dt[area]
        d = diff.get(area)
        n = len(t)
        tot = sum(e["chance"] for e in t)
        best = max((tier.get(e["matId"], ("E", "E", 0))[0] for e in t),
                   key=lambda g: GRADES.index(g), default="—")
        rows.append((area, d, n, tot, best, len(excl.get(area, []))))
    dists = {a: seller_distance(Rj.get(a) or {}) for a in areas}
    dmax = max((v[0] for v in dists.values() if v[0]), default=1.0)
    dvals = [r[1][0] for r in rows if r[1]]
    lo, hi = (min(dvals), max(dvals)) if dvals else (0, 1)
    cost = {}
    for area, d, n, tot, best, ex in rows:
        dd, _nm = dists.get(area, (None, None))
        cost[area] = ((dd / dmax if dd else 0.5)
                      + ((d[0] - lo) / (hi - lo) if d and hi > lo else 0.5))
    for area, d, n, tot, best, ex in sorted(rows, key=lambda r: cost[r[0]]):
        dd, nm = dists.get(area, (None, None))
        print(f"{area:<14}{(nm or '—'):>7}{(f'{dd:.0f}' if dd else '—'):>6}"
              f"{(f'{d[0]:.2f}' if d else '—'):>6}{cost[area]:>6.2f}  |{n:>5}{tot:>6}{ex:>5}"
              f"  {SHARE.get(area, 0):>8.2f}%")
    # 가치 가중 기대치 = Σ 확률 × 가치가중치(그 재료 최저 사용 등급). 유물 축은 뺀다.
    ART = {"미끼", "나뭇가지", "깨진 토기 조각", "미감정 유물", "진주조개", "고대 유물"}
    def wt(m):
        lo = tier.get(m, (None, None, 0))[1]
        return 1.0 + GRADES.index(lo) if lo in GRADES else 2.0
    val = {a: sum(e["chance"] * wt(e["matId"]) for e in dt[a] if e["matId"] not in ART)
           for a in areas}
    eq = {a: sum(e["chance"] for e in dt[a] if e["matId"] not in ART) for a in areas}
    print(f"\n  {'지역':<16}{'장비합%':>8}{'가치':>7}   (유물 축 제외)")
    for area in sorted(areas, key=lambda x: cost[x]):
        print(f"  {area:<16}{eq[area]:>8}{val[area]:>7.0f}")
    cs = [(cost[a], eq[a], val[a]) for a in areas]
    lo_, hi_ = min(x[1] for x in cs), max(x[1] for x in cs)
    print(f"\n  ★스피어만 (접근 비용 ↔ **가치**) "
          f"{spearman([c for c, _, _ in cs], [v for _, _, v in cs]):+.2f}"
          "   ← 1번 지표 (2026-08-27~)")
    print(f"    스피어만 (접근 비용 ↔ 합확률) "
          f"{spearman([c for c, _, _ in cs], [e for _, e, _ in cs]):+.2f}"
          "   ← 완만하게만 (합으로 차별화하면 드롭 도배가 된다)")
    print(f"    장비 합 범위 {lo_}~{hi_}% ({hi_/lo_:.2f}배) · "
          f"재료확률 30%(D 채집 풀세팅)에서 {lo_*1.3/100:.2f}~{hi_*1.3/100:.2f}개/캐스트")

    have = [(r[0], r[1][0], r[3], r[2]) for r in rows if r[1]]
    print(f"\n  스피어만 상관 (난이도 ↔ …)")
    print(f"    합확률   {spearman([x[1] for x in have], [x[2] for x in have]):+.2f}"
          "   ← +면 «어려울수록 많이 나온다»")
    print(f"    재료종수 {spearman([x[1] for x in have], [x[3] for x in have]):+.2f}")
    ti = [(x[0], x[1], GRADES.index(max((tier.get(e['matId'], ('E',))[0] for e in dt[x[0]]),
                                        key=lambda g: GRADES.index(g), default='E')))
          for x in have]
    print(f"    최고티어 {spearman([x[1] for x in ti], [x[2] for x in ti]):+.2f}")

    # ── ② 독점 ────────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("② 지역 전용(독점) 재료가 있는가")
    print("=" * 100)
    print(f"\n{'지역':<14}{'전용 재료':<44}{'전용 수':>7}")
    for area in areas:
        e = excl.get(area, [])
        print(f"{area:<14}{', '.join(e) if e else '—':<44}{len(e):>7}")
    ubi = [m for m in allm
           if sum(1 for t in dt.values() if any(x['matId'] == m for x in t)) >= len(areas) - 1]
    print(f"\n  거의 전 지역(≥{len(areas)-1}/{len(areas)})에서 나오는 재료: {ubi}")
    for m in ubi:
        ch = {t[0]: c for t in [(x, [e['chance'] for e in dt[x] if e['matId'] == m])
                               for x in areas] for c in t[1]}
        uniq = sorted(set(ch.values()))
        print(f"    {m:<10} 확률 {uniq}  ← 값이 하나면 **지역 차별이 0** 이다")

    # ── ③ 재료 티어 × 최초 획득 난이도 ────────────────────────────────
    print("\n" + "=" * 100)
    print("③ 좋은 재료가 어려운 지역에 있는가 (재료 티어 ↔ 최저 난이도 출처)")
    print("=" * 100)
    qs = quest_sinks()
    print(f"\n{'재료':<12}{'최고티어':>7}{'레시피':>6}{'퀘스트':>6}{'출처수':>6}{'합%':>6}"
          f"{'가장 쉬운 출처':>16}{'그 난이도':>8}")
    tri = []
    for m in allm:
        src = [(x, e["chance"]) for x, t in dt.items() for e in t if e["matId"] == m]
        tg, _lo, cnt = tier.get(m, ("—", "—", 0))
        ds = [(diff[x][0], x) for x, _ in src if x in diff]
        easiest = min(ds) if ds else (None, "—")
        print(f"{m:<12}{tg:>7}{cnt:>6}{qs.get(m, 0):>6}{len(src):>6}"
              f"{sum(c for _, c in src):>6}"
              f"{easiest[1]:>16}{(f'{easiest[0]:.2f}' if easiest[0] is not None else '—'):>8}")
        if tg in GRADES and easiest[0] is not None:
            tri.append((GRADES.index(tg), easiest[0]))
    if tri:
        print(f"\n  스피어만 (재료 티어 ↔ 가장 쉬운 출처의 난이도) "
              f"{spearman([x[0] for x in tri], [x[1] for x in tri]):+.2f}"
              "   ← +면 «좋은 재료는 어려운 곳에만»")

    # ── ④ 정의만 있고 안 나오는 재료 ──────────────────────────────────
    print("\n" + "=" * 100)
    print("④ materials.json 정의 vs 실제 드랍")
    print("=" * 100)
    crafted = set()
    for rid, r in R["recipes"].items():
        out = r.get("resultPartName") or r.get("rodPartName") or r.get("displayName")
        if out:
            crafted.add(out.replace(" ", ""))
    nodrop = [m for m in mats if m not in allm]
    print(f"\n  정의 {len(mats)}종 · 드랍표 {len(allm)}종 · 드랍 없음 {len(nodrop)}종")
    sub = [m for m in nodrop if m in crafted]
    orphan = [m for m in nodrop if m not in crafted]
    print(f"    가공재(레시피 결과) {len(sub)}종: {sub}")
    print(f"    🔴 낚시 드랍도 레시피도 없음 {len(orphan)}종: {orphan}")
    print("       ★일부는 광질·드릴 경로다(흑정석·철광석·자수정 등) — 낚시 드랍표에 없다는 뜻이다.")
    dead = [m for m in allm if tier.get(m, ("", "", 0))[2] == 0 and quest_sinks().get(m, 0) == 0]
    print(f"\n  🔴 드랍은 되는데 레시피·퀘스트 소비처가 둘 다 없는 재료: {dead or '없음'}")


if __name__ == "__main__":
    main()
