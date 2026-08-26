#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pull_players.py — 알파 테스터 실측치 추출 (prod 텔레메트리 → 스냅샷 JSON)

★2026-08-26 신설. 그때까지 이 스킬의 모든 모델은 «가정 상수»(220 포획/h, 시도 259/h, quality
85% 완주, 작살 270 포획/h)로 돌아갔다. prod 에는 2026-07 부터 이벤트 로그가 쌓여 있었는데
감사가 한 번도 읽지 않았다 — 그래서 가정이 실측과 최대 55% 어긋난 채 넉 달을 갔다.

이 스크립트가 뽑는 것은 «모델 상수의 실측 대체값»이다. 파생 지표(스탯가치·게이트·회수시간)를
계산하지 않는다 — 그건 stat_value / material_value / item_ledger 가 이 스냅샷을 먹고 한다.

출처:
  prod:~/mcserver/plugins/BlockShip/telemetry/events-YYYY-MM.db   (테이블 ev, loadout)
  prod:~/mcserver/plugins/BlockShip/telemetry/stats.db            (day_player, player_snapshot)

사용:
    python3 pull_players.py --fetch                 # prod 에서 받아와 캐시에 넣고 분석
    python3 pull_players.py                         # 캐시로 분석 (오프라인)
    python3 pull_players.py --out ../audits/snapshots/2026-08-26-players.raw.json

★함정 3개 (전부 실측으로 확인했다):
 1. **op 필터 없이 세면 개발자 플레이가 표본을 오염시킨다.** wsi1212/calan123 등은 크리에이티브·
    /낚시테스트·무한돈으로 돌아 실측 가치가 없다. ctx.op==1 이 그 표시이고, 이름 기준
    OPS 집합으로 한 번 더 걸러야 한다(op 플래그가 빠진 이벤트가 있다).
 2. **«세션 시간»과 «활성 낚시 시간»은 3~4배 다르다.** day_player.playtime_s 로 나누면
    포획/h 가 44 로 나오고, 캐스트 간격이 이어지는 구간만 세면 190 이 나온다. 장비 가치·유지비는
    «낚시하는 동안»의 비율이라 후자를 써야 하고, 레벨 도달시간·수입 총량은 전자를 써야 한다.
    둘 다 뽑아서 이름을 다르게 남긴다.
 3. **캐스트 ≠ 시도.** 실측 캐스트→결과 전환이 62% 다(찌를 던지고 입질 전에 회수/이동/중단).
    미끼 소모는 «결과»가 아니라 캐스트 쪽에 붙을 수 있으니 소모품 모델은 어느 쪽인지 코드로
    확인한 뒤 쓸 것 — 이 스냅샷은 두 값을 모두 남긴다.
"""
import argparse, collections, json, os, sqlite3, statistics as st, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.environ.get("BALANCE_TELEMETRY_CACHE",
                       os.path.join(HERE, "..", "audits", "telemetry-cache"))
PROD = "ubuntu@168.107.8.107"
KEY = os.path.expanduser("~/.ssh/oracle-mc.key")
REMOTE = "~/mcserver/plugins/BlockShip/telemetry"

# 개발자/운영자 계정 — 실측 표본에서 제외. ctx.op 플래그와 이중으로 쓴다.
OPS = {"wsi1212", "calan123", "all_ways_Incheon", "tnry0315"}
# 활성 구간 판정: 같은 종류 이벤트가 이 간격 안에 이어지면 «쉬지 않고 하는 중»으로 본다.
ACTIVE_GAP_MS = 90_000
# 세션 활동시간 판정(레벨 도달시간용) — 아무 이벤트든 이 간격 안이면 접속해 노는 중.
SESSION_GAP_MS = 300_000


def fetch():
    os.makedirs(CACHE, exist_ok=True)
    pats = ["events-*.db", "stats.db"]
    for p in pats:
        cmd = ["scp", "-q", "-o", "ConnectTimeout=15", "-i", KEY, f"{PROD}:{REMOTE}/{p}", CACHE]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            print(f"  ! scp {p} 실패: {r.stderr.strip()[:200]}", file=sys.stderr)
    print(f"  캐시: {CACHE}  ({', '.join(sorted(os.listdir(CACHE)))})")


def load_events():
    out = []
    dbs = sorted(f for f in os.listdir(CACHE) if f.startswith("events-") and f.endswith(".db"))
    if not dbs:
        sys.exit(f"이벤트 DB 가 캐시에 없다: {CACHE}  — --fetch 로 먼저 받아올 것")
    for f in dbs:
        c = sqlite3.connect(f"file:{os.path.join(CACHE, f)}?mode=ro", uri=True)
        for t, ts, u, n, w, r, x in c.execute(
                "select type,ts,uuid,name,world,region,ctx from ev"):
            try:
                d = json.loads(x) if x else {}
            except Exception:
                d = {}
            out.append((t, ts, u, n or "", r or "", d))
        c.close()
    out.sort(key=lambda e: e[1])
    return out, dbs


def is_real(e):
    """실측 표본 여부 — 개발자 계정도 아니고 op 컨텍스트도 아닌 이벤트."""
    return e[3] not in OPS and e[5].get("op", 0) == 0


def active_rate(ev, types, pred=None, gap=ACTIVE_GAP_MS):
    """활성 구간 처리량. 반환 (건수, 활성시간h, 시간당)."""
    per = collections.defaultdict(list)
    for e in ev:
        if e[0] in types and is_real(e) and (pred is None or pred(e[5])):
            per[e[3]].append(e[1])
    span = cnt = 0
    for L in per.values():
        L.sort()
        for a, b in zip(L, L[1:]):
            if b - a <= gap:
                span += b - a
                cnt += 1
    h = span / 3.6e6
    return cnt, h, (cnt / h if h else 0.0)


def level_track(ev):
    """level.up 으로 «시점별 낚시 레벨» 을 복원한다. player_snapshot 은 하루 1회라 너무 거칠다."""
    lv = collections.defaultdict(list)
    for t, ts, u, n, r, d in ev:
        if t == "level.up" and d.get("sys") == "낚시" and n not in OPS:
            lv[n].append((ts, d.get("to")))
    for L in lv.values():
        L.sort()
    return lv


def level_at(lv, name, ts):
    L = lv.get(name, [])
    cur = None
    for t2, v in L:
        if t2 <= ts:
            cur = v
        else:
            break
    if cur is None and L:
        return max(1, (L[0][1] or 2) - 1)   # 첫 레벨업 전 = 그 직전 레벨
    return cur


def band(l):
    if not l:
        return "미상"
    for lo, hi in ((1, 9), (10, 19), (20, 29), (30, 49), (50, 69)):
        if lo <= l <= hi:
            return f"Lv{lo}-{hi}"
    return "Lv70+"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="prod 에서 텔레메트리 DB 를 받아온다")
    ap.add_argument("--out", default=None, help="스냅샷 JSON 경로")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if a.fetch:
        fetch()
    ev, dbs = load_events()
    lv = level_track(ev)
    snap = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "source_dbs": dbs,
            "warnings": []}
    P = (lambda *x: None) if a.quiet else print

    # ── 표본 규모 ───────────────────────────────────────────────────────
    names = collections.Counter(e[3] for e in ev if is_real(e) and e[3])
    span = (min(e[1] for e in ev), max(e[1] for e in ev))
    snap["sample"] = {
        "events_total": len(ev),
        "events_real": sum(1 for e in ev if is_real(e)),
        "players_real": len(names),
        "players": dict(names.most_common()),
        "first_ts": span[0], "last_ts": span[1],
        "days": round((span[1] - span[0]) / 86.4e6, 1),
    }
    P(f"표본: 이벤트 {len(ev):,} (실측 {snap['sample']['events_real']:,}) · "
      f"플레이어 {len(names)}명 · {snap['sample']['days']}일")

    # ── 낚시 처리량 ─────────────────────────────────────────────────────
    caught = lambda d: d.get("res") in ("성공", "크리티컬")
    n_cast, h_cast, r_cast = active_rate(ev, {"fish.cast"})
    n_res, h_res, r_res = active_rate(ev, {"fish.result"})
    n_ok, h_ok, r_ok = active_rate(ev, {"fish.result"}, caught)
    results = [e[5] for e in ev if e[0] == "fish.result" and is_real(e)
               and e[5].get("res") != "대기"]
    oks = [d for d in results if caught(d)]
    # ★전환율 분모는 «활성구간 쌍 개수»(n_cast)가 아니라 실측 캐스트 총건수다 — 섞으면 사과와 배.
    casts_total = sum(1 for e in ev if e[0] == "fish.cast" and is_real(e))
    snap["fishing"] = {
        "casts_per_active_h": round(r_cast, 1),
        "results_per_active_h": round(r_res, 1),
        "catches_per_active_h": round(r_ok, 1),
        "casts_total": casts_total,
        "cast_to_result_pct": round(len(results) / max(1, casts_total) * 100, 1),
        "completion_pct": round(len(oks) / max(1, len(results)) * 100, 1),
        "escape_pct": round(sum(1 for d in results if d.get("res") == "도주")
                            / max(1, len(results)) * 100, 2),
        "active_hours_sampled": round(h_ok, 2),
        "n_results": len(results), "n_catches": len(oks),
        "quality_mean": round(st.mean([d.get("q", 0) for d in oks]), 1) if oks else None,
        "quality_median": st.median([d.get("q", 0) for d in oks]) if oks else None,
        "xp_per_catch_mean": round(st.mean([d.get("xp", 0) for d in oks]), 2) if oks else None,
    }
    gd = collections.Counter(d.get("g") for d in oks)
    tot = sum(gd.values()) or 1
    snap["fishing"]["grade_dist_pct"] = {k: round(v / tot * 100, 3)
                                         for k, v in sorted(gd.items(), key=lambda kv: "GLMSABCDE".find(kv[0]))}
    P(f"낚시: {r_ok:.1f} 포획/h (활성) · 캐스트 {r_cast:.1f}/h · 전환 "
      f"{snap['fishing']['cast_to_result_pct']:.0f}% · 완주 {snap['fishing']['completion_pct']:.0f}% · "
      f"quality {snap['fishing']['quality_mean']}")

    # ── 레벨 구간별 실현가 (원/포획) ────────────────────────────────────
    #   fish.result.price = FishItem.calcPrice = 등급기본가 × 크기배율 × 크리 × 판매보너스
    #   (신선도는 포획 직후라 1.0). 즉 «그 플레이어의 실제 장비로 실현된 값»이다.
    pb = collections.defaultdict(list)
    for e in ev:
        if e[0] != "fish.result" or not is_real(e) or not caught(e[5]):
            continue
        pb[band(level_at(lv, e[3], e[1]))].append(e[5].get("price", 0))
    snap["income_by_band"] = {}
    for b, L in pb.items():
        snap["income_by_band"][b] = {
            "n": len(L), "price_mean": round(st.mean(L), 1), "price_median": st.median(L),
            "gross_per_active_h": round(st.mean(L) * r_ok),
        }
    P("구간별 실현가(원/포획) → 총수입(원/h, 활성):")
    for b in sorted(snap["income_by_band"], key=lambda x: (x == "미상", x)):
        d = snap["income_by_band"][b]
        P(f"   {b:<9} n={d['n']:<5} 평균 {d['price_mean']:>7,.0f}  중위 {d['price_median']:>6,.0f}"
          f"  → {d['gross_per_active_h']:>9,}원/h")

    # ── 지역 분포 (재료 드롭테이블 접근성의 실측) ───────────────────────
    reg = collections.Counter(e[4] for e in ev
                              if e[0] == "fish.result" and is_real(e) and caught(e[5]))
    tr = sum(reg.values()) or 1
    snap["region_mix_pct"] = {k: round(v / tr * 100, 2) for k, v in reg.most_common()}
    P("지역 분포(포획): " + ", ".join(f"{k} {v:.0f}%" for k, v in
                                 list(snap["region_mix_pct"].items())[:6]))

    # ── 작살 ────────────────────────────────────────────────────────────
    hcat = [e[5] for e in ev if e[0] == "harpoon.catch" and is_real(e)]
    n_hc, h_hc, r_hc = active_rate(ev, {"harpoon.catch"})
    counts = {t: sum(1 for e in ev if e[0] == t and is_real(e))
              for t in ("harpoon.spawn", "harpoon.swing", "harpoon.hit", "harpoon.miss",
                        "harpoon.dash", "harpoon.escape", "harpoon.catch")}
    hq = [d.get("quality") for d in hcat if d.get("quality") is not None]
    hgd = collections.Counter(d.get("grade") for d in hcat)
    hto = sum(hgd.values()) or 1
    snap["harpoon"] = {
        "catches_per_active_h": round(r_hc, 1), "active_hours_sampled": round(h_hc, 2),
        "counts": counts,
        "spawn_to_catch_pct": round(counts["harpoon.catch"] / max(1, counts["harpoon.spawn"]) * 100, 1),
        "hit_rate_pct": round(counts["harpoon.hit"] /
                              max(1, counts["harpoon.hit"] + counts["harpoon.miss"]) * 100, 1),
        "quality_mean": round(st.mean(hq), 1) if hq else None,
        "quality_min": min(hq) if hq else None, "quality_max": max(hq) if hq else None,
        "grade_dist_pct": {k: round(v / hto * 100, 3)
                           for k, v in sorted(hgd.items(), key=lambda kv: "GLMSABCDE".find(kv[0] or "?"))},
        "used": dict(collections.Counter(e[5].get("harpoon") for e in ev
                                         if e[0] == "harpoon.swing" and is_real(e))),
    }
    P(f"작살: {r_hc:.1f} 포획/h · quality 평균 {snap['harpoon']['quality_mean']} "
      f"({snap['harpoon']['quality_min']}~{snap['harpoon']['quality_max']}) · "
      f"스폰→포획 {snap['harpoon']['spawn_to_catch_pct']:.0f}% · 명중 {snap['harpoon']['hit_rate_pct']:.0f}%")

    # ── 섬광산 / 드릴 (장비 레시피의 광질 재료 원가 실측) ───────────────
    for key, typ in (("island_mine", "imine.min"), ("drill", "mine.min")):
        buckets = [e[5] for e in ev if e[0] == typ and is_real(e)]
        ore = collections.Counter()
        for d in buckets:
            for k, v in (d.get("ores") or {}).items():
                ore[k] += v
        # imine.min/mine.min 은 1분 집계 이벤트다 → 버킷 수 = 채굴한 분(min)
        mins = len(buckets)
        snap[key] = {"minute_buckets": mins, "ores_total": sum(ore.values()),
                     "per_hour": {k: round(v / mins * 60, 1) for k, v in ore.most_common()} if mins else {}}
        if mins:
            P(f"{key}: {mins}분 표본 · 시간당 총 {sum(ore.values())/mins*60:,.0f}개 · " +
              ", ".join(f"{k} {v/mins*60:,.0f}" for k, v in ore.most_common(5)))

    # ── 실제 장착 로드아웃 (죽은 콘텐츠 판별용) ─────────────────────────
    lo_json = {}
    for f in dbs:
        c = sqlite3.connect(f"file:{os.path.join(CACHE, f)}?mode=ro", uri=True)
        for h, j in c.execute("select hash,json from loadout"):
            lo_json[h] = j
        c.close()
    used = collections.Counter()
    rods = collections.Counter()
    for e in ev:
        if e[0] != "fish.result" or not is_real(e):
            continue
        rods[e[5].get("rod") or "(작살/맨손)"] += 1
        j = lo_json.get(e[5].get("lo"))
        if not j:
            continue
        try:
            d = json.loads(j)
        except Exception:
            continue
        for slot, name in (d.get("parts") or {}).items():
            if name:
                used[(slot, name)] += 1
    snap["loadout_usage"] = {f"{s}/{n}": c for (s, n), c in used.most_common()}
    snap["rod_usage"] = dict(rods.most_common())
    P(f"실사용 부품 {len(used)}종 · 실사용 낚싯대 {len(rods)}종 "
      f"(parts.json 총계 대비 커버리지는 item_ledger.py 가 판정)")

    # ── 세션 기준 총량 (레벨 도달시간·이탈률) ───────────────────────────
    prev, act, lvtime = {}, collections.defaultdict(float), collections.defaultdict(dict)
    for t, ts, u, n, r, d in ev:
        if n in OPS or not n:
            continue
        p = prev.get(n)
        if p is not None and ts - p <= SESSION_GAP_MS:
            act[n] += (ts - p) / 3.6e6
        prev[n] = ts
        if t == "level.up" and d.get("sys") == "낚시":
            lvtime[n][d.get("to")] = round(act[n], 2)
    snap["level_pacing"] = {n: {"active_h_total": round(act[n], 2), "level_at_h": m}
                            for n, m in lvtime.items()}
    reach = collections.defaultdict(list)
    for n, m in lvtime.items():
        for L, h in m.items():
            reach[L].append(h)
    snap["level_reach_hours"] = {str(L): {"n": len(v), "median": round(st.median(v), 2),
                                          "min": round(min(v), 2), "max": round(max(v), 2)}
                                 for L, v in sorted(reach.items()) if L}
    P("레벨 도달(활동h, 중위/최소~최대): " + ", ".join(
        f"L{L} {d['median']:.1f}({d['min']:.1f}~{d['max']:.1f})"
        for L, d in list(snap["level_reach_hours"].items())[::5]))

    # ── stats.db 일별/스냅샷 ────────────────────────────────────────────
    sp = os.path.join(CACHE, "stats.db")
    if os.path.exists(sp):
        c = sqlite3.connect(f"file:{sp}?mode=ro", uri=True)
        cols = [r[1] for r in c.execute("PRAGMA table_info(day_player)")]
        rows = [dict(zip(cols, r)) for r in c.execute(f"select {','.join(cols)} from day_player")]
        rows = [r for r in rows if r["name"] not in OPS]
        tp = sum(r["playtime_s"] or 0 for r in rows) / 3600
        mi = sum(r["money_in"] or 0 for r in rows)
        mo = sum(r["money_out"] or 0 for r in rows)
        cn = sum(r["casino_net"] or 0 for r in rows)
        snap["session_totals"] = {
            "playtime_h": round(tp, 1),
            "casts": sum(r["casts"] or 0 for r in rows),
            "catches": sum(r["catches"] or 0 for r in rows),
            "money_in": mi, "money_out": mo, "casino_net": cn,
            "income_per_playtime_h_excl_casino": round((mi - max(0, cn)) / tp) if tp else None,
            "net_worth_per_playtime_h": round((mi + mo) / tp) if tp else None,
            "catches_per_playtime_h": round(sum(r["catches"] or 0 for r in rows) / tp, 1) if tp else None,
            "harpoon_attempts": sum(r["harpoon_attempts"] or 0 for r in rows),
            "harpoon_catches": sum(r["harpoon_catches"] or 0 for r in rows),
        }
        sc = [r[1] for r in c.execute("PRAGMA table_info(player_snapshot)")]
        latest = {}
        for r in c.execute(f"select {','.join(sc)} from player_snapshot order by date"):
            d = dict(zip(sc, r))
            if d["name"] in OPS:
                continue
            latest[d["name"]] = d
        snap["progress"] = {n: {"level": d["level"], "money": d["money"],
                                "total_fish": d["total_fish"], "dex_fish": d["dex_fish"],
                                "max_combo": d["max_combo"], "date": d["date"]}
                            for n, d in latest.items() if (d["total_fish"] or 0) > 0}
        lvls = [d["level"] for d in snap["progress"].values()]
        snap["coverage"] = {"max_level_observed": max(lvls) if lvls else None,
                           "levels": sorted(lvls, reverse=True)}
        c.close()
        P(f"세션: {tp:.1f}h · 카지노제외 수입 {snap['session_totals']['income_per_playtime_h_excl_casino']:,}원/h "
          f"(플레이시간 기준) · 최고레벨 {snap['coverage']['max_level_observed']}")

    # ── 경고 (모델을 어디까지 신뢰할 수 있는가) ─────────────────────────
    mx = (snap.get("coverage") or {}).get("max_level_observed") or 0
    if mx < 40:
        snap["warnings"].append(
            f"실측 커버리지가 Lv.{mx} 까지다 — A/S/G 등급 장비, 종결 앵커, 늪지대·대양 이후 "
            f"콘텐츠에 대한 수치는 전부 «모델 외삽»이며 실측 근거가 없다. 리포트에 그렇게 표기할 것.")
    for a_, need in (("협곡", 3), ("늪지대", 3), ("대양", 1), ("정상", 3)):
        if snap["region_mix_pct"].get(a_, 0) < need:
            snap["warnings"].append(
                f"{a_} 실측 조업 비중 {snap['region_mix_pct'].get(a_,0):.1f}% — 이 지역 전용 재료의 "
                f"«현실 획득속도»는 관측되지 않았다(모델은 «가면 얻는다»를 가정한다).")
    if snap["fishing"]["cast_to_result_pct"] < 80:
        snap["warnings"].append(
            f"캐스트→결과 전환 {snap['fishing']['cast_to_result_pct']:.0f}% — 소모품(미끼) 비용을 "
            f"«캐스트당»으로 잡으면 실제보다 {100/snap['fishing']['cast_to_result_pct']:.2f}배 과대계상된다.")
    for w in snap["warnings"]:
        P("  ! " + w)

    out = a.out or os.path.join(HERE, "..", "audits", "snapshots",
                                time.strftime("%Y-%m-%d") + "-players.raw.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    P(f"\n스냅샷 → {out}")


if __name__ == "__main__":
    main()
