#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
item_ledger.py — 장비 1점의 «재료 · 성능 · 레벨제한» 3축 정합성 원장.

★2026-08-26 신설. 사용자 지적: "각 낚싯대·작살·부품의 재료와 성능, 레벨제한 밸런스가 안 맞는
것 같다". 기존 스크립트로는 그 판정이 구조적으로 불가능했다:
  · gear_payback.py 는 «가격 ÷ 성능» 만 본다 — 재료비용이 0으로 빠져 있다.
  · material_gate.py 는 «재료 시간» 만 본다 — 성능·레벨을 안 본다.
  · 둘 다 **레벨제한을 축으로 쓰지 않는다.** 그래서 「Lv.40 인데 Lv.28 것보다 약한 A 등급」 같은
    사다리 붕괴를 아무도 못 잡았다.

이 스크립트는 셋을 한 원장에 넣고 사다리 자체를 검사한다.

## 원장 한 줄
    총획득비용(원) = 돈가격 + 재료게이트(h) × 그 레벨 구간의 실측 시급
    실효성능(원/h) = income 스탯가치 + (릴/미끼는) 성장가치 + 게이트가치(재료확률)
    회수시간(h)   = 총획득비용 ÷ 실효성능
    단가          = 총획득비용 ÷ 실효성능  (= 회수시간과 동일. «성능 1원/h 당 지불액»)

재료게이트는 material_value.py 의 LP 그림자가격을 쓴다 — 결합생산(한 번의 포획이 그 지역
드롭테이블 전체를 굴린다)을 반영하고 다지역 재료를 자동으로 최저비용 경로로 평가한다.

## 사다리 검사 4종 (경보선은 references/item-ladder-metrics.md)
  ① 지배(dominated) — 레벨제한이 같거나 낮고 총비용도 같거나 낮은데 성능이 더 높은 물건이 있다.
     지배당한 아이템은 «영구히 살 이유가 없는 콘텐츠»다. 🔴
  ② 레벨-성능 역전 — 카테고리 안에서 레벨제한이 오르는데 성능이 떨어진다. 🟡
  ③ 도매할인 위반 — 상위 등급의 «성능당 비용»이 하위 등급보다 비싸다. 상위 등급은 양(성능)이
     많은 대신 단가가 싸야 한다(feedback: 성능 같으면 상위 등급은 가성비가 좋아야). 🟡
  ④ 동일 레벨대 편차 — Lv±2 밴드 안에서 «성능당 비용»이 3배 넘게 벌어진다. 🟡

사용:
    python3 item_ledger.py                    # 전체 원장 + 사다리 검사
    python3 item_ledger.py --cat 작살          # 카테고리 한정
    python3 item_ledger.py --checks-only      # 경보만
    python3 item_ledger.py --dead             # 죽은 콘텐츠(실사용 0 + 획득경로 없음)
"""
import argparse, collections, importlib.util, json, os, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = saved
    return m


MV = _load("material_value")
SV = _load("stat_value")
HV = _load("harpoon_value")   # 창 전용 스탯 6종 + 돌진쿨감의 원/h 모델 (2026-08-26)
MEAS = _load("measured")      # ★실측 상수 단일 출처

# ── 스탯 → 가치축 배정 (gear_payback.py 와 같은 분류를 유지한다) ────────────
STAT_KEY = {
    "판매보너스": "판매보너스 (1%)", "더블찬스": "더블찬스 (1%)", "트리플찬스": "트리플찬스 (1%)",
    "등급업": "등급업 (1%)", "크기": "크기 (1%)", "행운": "행운 (1점)",
    "도망감소": "도주감소 (1%)", "도주감소": "도주감소 (1%)",
    "크리확률": "크리확률 (1%)", "크리배율": "크리배율 (1점)", "난이도": "난이도 (1점)",
}
GROWTH_KEY = {"경험치": "경험치 (1%)"}
GATE_KEY = {"재료확률": "재료확률 (1%)"}
DASH_KEY = {"돌진쿨감": "돌진쿨감 (1%)"}
# 창 전용 — ★2026-08-26 부터 harpoon_value.py 가 원/h 모델을 낸다(사이클 + 등급천장, 실측 16/16
# 검증). 그전까지는 «모델 없음»이라 작살 55종 중 37종이 판정 불가였다.
# 야간투시만 여전히 모델이 없다(심해 3종 전용 편의 효과).
SPEAR_ONLY = {"수중호흡", "호흡시간", "수영속도", "공격력", "공격속도", "돌진쿨감"}
SPEAR_UNMODELED = {"야간투시"}
# 낚싯대 전용 유지비 절감 — 회수시간이 아니라 유지비 쪽에서 값이 난다.
#: 유지비 절감축 — 2026-08-27 «내구보존» 폐지로 비었다. 집합은 남겨 둔다(다시 그런 축이
#  생기면 여기에 넣으면 되고, 비어 있는 채로도 모델커버리지 계산이 그대로 돈다).
UPKEEP = set()
SPECIAL = {"등급특화"}

# EquipmentManager.gradeUnitRate — 내구 1점 회복 단가(원). 내구는 시도 1건에 1점 깎인다.
REPAIR_RATE = {"E": 5, "D": 11, "C": 15, "B": 18, "A": 39, "S": 60, "M": 100, "L": 150, "G": 220}
#: 세트 유지비 산정용 최저가 미끼(지렁이 5원). 내구보존이 있던 동안 «절감액»의 분모였고,
#  스탯 폐지 후에도 미끼 자기유지비의 하한 기준으로 남는다.
CHEAPEST_BAIT = 5

STAGE_OF_LEVEL = lambda lv: "초반" if lv < 20 else ("중반" if lv < 50 else "종결")
# 원 환산 환율(시급) — 실측 구간이 있으면 실측, 없으면 모델(외삽 표기)
BAND_OF_LEVEL = lambda lv: ("Lv1-9" if lv < 10 else "Lv10-19" if lv < 20
                            else "Lv20-29" if lv < 30 else None)
# 작살은 낚싯대와 처리량·quality 가 달라 income 이 다르다. 실측 비로 보정한다.
#   (실측: 작살 174.8 포획/h · quality 70~100 균등 / 낚싯대 190.1 포획/h · quality 실측평균)
HARPOON_QUALITY = 85.0


# ── 다른 통화로 파는 장비 ────────────────────────────────────────────────
#  ★2026-08-26 발견: parts.json 의 price 필드는 **잠수상점/캐시 아이템에도 원 가격이 들어 있는데
#    그 값으로는 아무도 살 수 없다**(잠수상점은 잠수 포인트 P, 캐시샵은 캐시). 예: 잠수부의 낚싯대는
#    parts.json 160,000원인데 실제 판매가는 AfkShopGui 하드코딩 1,080P(=AFK 18시간)다. 이 유령
#    가격을 원 원장에 섞으면 「Lv10 에 B급 세트가 16만원」이라는 존재하지 않는 선택지가 생겨
#    돈·재료로 가는 정상 사다리 전체가 «지배당한» 것으로 오판된다. 그래서 통화별로 분리한다.
AFK_SHOP_JAVA = os.path.expanduser(
    "~/development/blockship-plugin/src/main/java/com/blockship/afk/AfkShopGui.java")
AFK_MIN_PER_POINT = 1.0     # AfkManager: 잠수대 1분 = 1P


def afk_shop_costs(path=AFK_SHOP_JAVA):
    """AfkShopGui.ITEMS 를 파싱해 {장비이름: (P비용, 지급개수)}. 파일이 없으면 빈 dict."""
    import re
    out = {}
    if not os.path.exists(path):
        return out
    src = open(path, encoding="utf-8").read()
    for m in re.finditer(r'new Entry\(\s*"[^"]+",[^,]+,\s*"[^"]*",\s*([0-9_]+),\s*"([^"]+)"', src):
        cost, tag = int(m.group(1).replace("_", "")), m.group(2)
        if tag.startswith("rod:"):
            out[tag[4:]] = (cost, 1)
        elif tag.startswith("harpoon:"):
            out[tag[8:]] = (cost, 1)
        elif tag.startswith("part:"):
            t = tag.split(":", 3)
            if len(t) == 4:
                out[t[2]] = (cost, int(t[3]))
    return out


def parse_stats(raw):
    out = {}
    for pair in raw.split(","):
        kv = pair.split(":", 2)
        if len(kv) < 2:
            continue
        k = kv[0].strip()
        try:
            out[k] = float(kv[1].strip())
        except ValueError:
            out[k] = kv[1].strip()
    return out


def load_usage():
    """pull_players.py 스냅샷의 실사용 로드아웃 — 죽은 콘텐츠 판정용."""
    d = os.path.join(SKILL, "audits", "snapshots")
    if not os.path.isdir(d):
        return {}, {}
    cands = sorted(f for f in os.listdir(d) if f.endswith("-players.raw.json"))
    if not cands:
        return {}, {}
    s = json.load(open(os.path.join(d, cands[-1]), encoding="utf-8"))
    used = {}
    for k, v in (s.get("loadout_usage") or {}).items():
        used[k.split("/", 1)[-1]] = v
    return used, (s.get("rod_usage") or {})


def build(D, statvals, incomes, harp_ratio, HM=None):
    """parts.json 전체를 원장 행으로."""
    afk = afk_shop_costs()
    # 작살 기준선 = 무료 나무 작살(Lv1). 낚싯대의 «나뭇가지»와 같은 역할 —
    # 작살 성능은 «이 작살이 무료 작살 대비 시간당 얼마를 더 벌어주나»로 잰다.
    spear_base = {}
    if HM:
        for lvl in (10, 30, 60):
            dist = HM.dist_for(lvl)
            spear_base[lvl] = (HM.income(HM.effective("나무 작살"), dist), dist)
    rows = []
    for name, m in D.meta.items():
        cat, grade, lv, price = m["cat"], m["grade"], m["lvl"], m["price"]
        stats = parse_stats(m["stats"])
        stage = STAGE_OF_LEVEL(lv)
        V = statvals[stage]
        # 작살은 같은 스탯 1점의 값이 낚싯대와 다르다(처리량·quality 차) → 실측 비로 스케일
        scale = harp_ratio if cat == "작살" else 1.0
        inc = growth = gate = dash = 0.0
        diff_pts = 0.0
        unknown = []
        for k, v in stats.items():
            if not isinstance(v, (int, float)):
                continue
            if k == "난이도":
                # ★난이도만 «누적 곡선»으로 센다(단가 × 점수 금지) — stat_value.diff_curve 참조.
                #   존폭이 2점마다 1칸 넓어지고 등급별로 100% 에서 포화하는 계단 함수라
                #   단가 하나로 곱하면 고난이도(숙련형 6~10)를 통째로 과대평가한다.
                diff_pts += v
            elif k in STAT_KEY:
                inc += v * V[STAT_KEY[k]] * scale
            elif k in GROWTH_KEY:
                growth += v * V[GROWTH_KEY[k]] * scale
            elif k in GATE_KEY:
                gate += v * V[GATE_KEY[k]]
            elif k in DASH_KEY and cat != "작살":
                dash += v * V[DASH_KEY[k]]
            elif k not in SPEAR_ONLY | SPEAR_UNMODELED | UPKEEP | SPECIAL:
                unknown.append(k)
        # ── 작살: 창 전용 스탯을 harpoon_value 모델로 환산 ────────────────
        #   돌진쿨감은 stat_value 의 «사이클» 근사가 아니라 이 모델(교전 DPS + 사이클)로 센다 —
        #   돌진이 공격력×2 피해라 교전 안에서 등급 천장을 직접 움직인다.
        spear_val = 0.0
        if cat == "작살" and HM and name in HM.spears:
            key = 10 if lv < 20 else (30 if lv < 50 else 60)
            b, dist = spear_base[key]
            spear_val = HM.income(HM.effective(name), dist) - b
        # ★2026-08-27 — 성장(경험치)을 **전 카테고리**에 포함한다.
        #   구 동작은 릴·미끼만 포함했는데 낚싯대에도 경험치 라인이 있다(수련생·경험의·학도의·
        #   전승자). 그래서 경험의 낚싯대가 19.5h(최악)로 잡혔지만 성장을 넣으면 8.4h(상위권)다.
        #   근거: stat_value 의 경험치 값 자체가 「레벨링 국면: income 1%와 동가치(병렬진행)」로
        #   정의돼 있다 — 이미 원/h 로 환산된 값이므로 카테고리에 따라 넣고 빼면 일관성이 깨진다.
        #   ★단 이 값은 **만렙 후 0** 이다. growth_share 컬럼으로 그 비중을 드러낸다.
        # 난이도 누적 곡선 (작살은 미니게임이 없어 해당 없음 — HarpoonManager 가 제외한다)
        diff_val = 0.0
        if diff_pts > 0 and cat != "작살":
            curve = SV.diff_curve(stage)
            d = int(round(diff_pts))
            diff_val = curve.get(d, curve[max(curve)])
        eff = inc + gate + growth + spear_val + diff_val

        # ── 유지비 (2026-08-26 신설) ──────────────────────────────────
        #   ★2026-08-27 «내구보존» 스탯 폐지 — 소모를 확률로 스킵하는 경로가 없어졌다.
        #     수리비·미끼값은 이제 스탯으로 깎이지 않는 고정 유지비다(자기유지비만 남음).
        A = SV.CASTS_PER_HOUR
        own_upkeep = 0.0
        if cat in ("릴", "줄", "바늘", "찌"):
            own_upkeep = A * REPAIR_RATE.get(grade, 5)
        elif cat == "미끼":
            unit = (m["price"] if name not in afk
                    else afk[name][0] / max(1, afk[name][1]))   # P 단위는 아래에서 분리 표기
            own_upkeep = A * unit if name not in afk else 0.0
        dur_val = 0.0          # 구 내구보존 절감액 — 스탯 폐지로 영구 0(컬럼 호환 유지)
        eff_net = eff - own_upkeep

        # ── 모델 커버리지 ──────────────────────────────────────────────
        #  ★이게 없으면 «모델이 값을 모르는 아이템»을 «약한 아이템»으로 오판한다. 작살 6종
        #    (수중호흡·호흡시간·수영속도·공격력·공격속도·야간투시)은 원/h 모델이 아예 없어서,
        #    공격형·호흡형 빌드는 스탯 대부분이 0으로 계산된다. 그런 행은 사다리 판정에서 빼고
        #    따로 보고한다 — 판정하려면 먼저 그 스탯들의 가치 모델을 만들어야 한다.
        keys = [k for k, v in stats.items() if isinstance(v, (int, float))]
        modeled = [k for k in keys if k in STAT_KEY or k in GROWTH_KEY or k in GATE_KEY
                   or k in DASH_KEY or k in UPKEEP or (cat == "작살" and k in SPEAR_ONLY)]
        cover = (len(modeled) / len(keys)) if keys else 0.0
        gate_led = (gate / eff) if eff > 0 else 0.0
        growth_share = (growth / eff) if eff > 0 else 0.0

        rec = D.recby.get(name)
        mat_h, lam, hact, unres = (0.0, {}, {}, [])
        if rec:
            bom = D.expand(rec["ingredients"])
            mat_h, lam, hact, unres = D.gate(bom)
        wage_band = BAND_OF_LEVEL(lv)
        wage = (D.k["income_by_band"].get(wage_band) if wage_band
                else incomes[stage])          # Lv30+ 은 실측 없음 → 모델 외삽
        mat_won = mat_h * wage
        # 통화 판정 — 원이 아닌 것은 원 원장에서 뺀다(지배·도매할인 검사 제외)
        cur = "원"
        p_cost = None
        if name in afk:
            cur, p_cost = "P", afk[name]
        elif m["src"] in ("캐시", "개발자"):
            cur = m["src"]
        total = (price + mat_won) if cur == "원" else float("nan")
        rows.append(dict(name=name, cat=cat, grade=grade, lv=lv, price=price, dur=m["dur"],
                         src=m["src"], stage=stage, wage=wage, measured=bool(wage_band),
                         currency=cur, p_cost=p_cost,
                         inc=inc, growth=growth, gate=gate, dash=dash, spear=spear_val, eff=eff,
                         dur_val=dur_val, own_upkeep=own_upkeep, eff_net=eff_net,
                         cover=cover, gate_led=gate_led, growth_share=growth_share,
                         mat_h=mat_h, mat_won=mat_won, total=total,
                         payback=(total / eff_net if (eff_net > 0 and total == total)
                                  else float("inf")),
                         craftable=bool(rec), unresolved=unres, unknown=unknown,
                         bottleneck=sorted(lam.items(), key=lambda kv: -kv[1])[:3],
                         stats=stats))
    return rows


def ladder_checks(rows):
    """사다리 검사 4종. 반환 (경보 리스트, 등급별 요약)."""
    warn = []
    order = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4, "S": 5, "G": 6}
    by_cat = collections.defaultdict(list)
    for r in rows:
        # 원 통화 + 성능 > 0 인 것만 원 원장 검사 대상. 잠수상점(P)·캐시는 다른 통화라 제외한다.
        # ★cover<0.5 (원/h 모델이 없는 스탯이 절반 이상)는 검사 4종 전부에서 뺀다 — 넣으면
        #   «모델이 모르는 물건»이 «약한 물건»으로 잡혀 경보가 거짓으로 부푼다.
        if (r["eff_net"] > 0 and r["currency"] == "원" and r["total"] == r["total"]
                and r["total"] > 0 and r["cover"] >= 0.5):
            by_cat[r["cat"]].append(r)

    # ① 지배 — 레벨·비용 둘 다 같거나 낮은데 성능이 더 높은 물건이 있다
    for cat, arr in by_cat.items():
        arr = [r for r in arr if "히든" not in r["src"]]
        dominated = []
        for x in arr:
            best = None
            for y in arr:
                if y is x:
                    continue
                if y["lv"] <= x["lv"] and y["total"] <= x["total"] * 1.001 and y["eff_net"] > x["eff_net"] * 1.02:
                    if best is None or y["eff_net"] > best["eff_net"]:
                        best = y
            if best:
                dominated.append((x, best))
        if dominated:
            warn.append(("🔴", f"{cat}: 지배당한 아이템 {len(dominated)}종 "
                               f"(레벨·비용이 같거나 낮은 대안이 더 강하다)",
                         [(f"{x['name']}(Lv{x['lv']} {x['total']:,.0f}원 {x['eff_net']:,.0f}원/h)"
                           f" ← {b['name']}(Lv{b['lv']} {b['total']:,.0f}원 {b['eff_net']:,.0f}원/h)")
                          for x, b in sorted(dominated, key=lambda t: t[1]["eff_net"] / max(1,t[0]["eff_net"]),
                                             reverse=True)[:8]]))

    # ② 레벨-성능 역전 (등급 내 레벨 정렬에서 성능이 떨어지는 쌍)
    for cat, arr in by_cat.items():
        inv = []
        s = sorted(arr, key=lambda r: r["lv"])
        for i, x in enumerate(s):
            for y in s[i + 1:]:
                if y["lv"] > x["lv"] and y["eff_net"] < x["eff_net"] * 0.98 and y["total"] >= x["total"]:
                    inv.append((x, y))
        if inv:
            warn.append(("🟡", f"{cat}: 레벨제한이 높고 더 비싼데 약한 조합 {len(inv)}쌍",
                         [f"{y['name']}(Lv{y['lv']} {y['eff_net']:,.0f}원/h) < "
                          f"{x['name']}(Lv{x['lv']} {x['eff_net']:,.0f}원/h)"
                          for x, y in sorted(inv, key=lambda t: t[0]["eff_net"] / max(1,t[1]["eff_net"]),
                                             reverse=True)[:6]]))

    # ③ 도매할인 위반 — 등급이 오르면 «성능당 비용»(=회수시간)이 내려가야 한다
    summary = {}
    for cat, arr in by_cat.items():
        g = collections.defaultdict(list)
        for r in arr:
            g[r["grade"]].append(r["payback"])
        med = {k: st.median(v) for k, v in g.items() if v}
        summary[cat] = med
        ks = sorted(med, key=lambda x: order.get(x, 9))
        for a, b in zip(ks, ks[1:]):
            if med[b] > med[a] * 1.05:
                warn.append(("🟡", f"{cat}: 도매할인 위반 {a}→{b} — 성능당 비용이 "
                                   f"{med[a]:.2f}h → {med[b]:.2f}h 로 오른다 "
                                   f"(+{(med[b]/med[a]-1)*100:.0f}%)", []))

    # ④ 동일 레벨대 편차
    for cat, arr in by_cat.items():
        for lo in range(1, 101, 5):
            band = [r for r in arr if lo <= r["lv"] < lo + 5 and r["payback"] < float("inf")]
            if len(band) < 3:
                continue
            b, w = min(band, key=lambda r: r["payback"]), max(band, key=lambda r: r["payback"])
            if w["payback"] > b["payback"] * 3:
                warn.append(("🟡", f"{cat} Lv{lo}~{lo+4}: 성능당 비용 편차 "
                                   f"{w['payback']/b['payback']:.1f}배 "
                                   f"({b['name']} {b['payback']:.2f}h ↔ {w['name']} {w['payback']:.2f}h)",
                             []))
    return warn, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cat", default=None)
    ap.add_argument("--checks-only", action="store_true")
    ap.add_argument("--dead", action="store_true")
    ap.add_argument("--top", type=int, default=14)
    a = ap.parse_args()

    D = MV.Data()
    k = D.k
    # ★실측을 stat_value 에 주입 (measured.apply 가 income_of 기본인자까지 갈아 준다)
    MEAS.apply(SV, k)
    q = k["size_score"]

    statvals, incomes = {}, {}
    for stage in SV.STAGES:
        r = SV.compute(stage)
        statvals[stage] = {kk: v[0] for kk, v in r["V"].items()}
        incomes[stage] = r["income"]

    # 작살 income 비 — 처리량 × quality 가격배율
    hs = k.get("harpoon") or {}
    h_catch = hs.get("catches_per_active_h") or 174.8
    h_q = hs.get("quality_mean") or HARPOON_QUALITY
    harp_ratio = (h_catch / SV.CATCH_PER_HOUR) * (SV.size_mult(h_q) / SV.size_mult(q))

    print(MEAS.banner(k))
    print(f"모델 시급: " + " / ".join(f"{s} {incomes[s]:,.0f}" for s in SV.STAGES) +
          "  ·  실측 시급: " + " / ".join(f"{b} {v:,.0f}" for b, v in k["income_by_band"].items()))
    print(f"작살 income 비: 처리량 ×{h_catch/SV.CATCH_PER_HOUR:.3f} × quality "
          f"×{SV.size_mult(h_q)/SV.size_mult(q):.3f} = ×{harp_ratio:.3f}  "
          f"(작살 {h_catch} 포획/h · quality {h_q})")

    HM = HV.Model()
    rows = build(D, statvals, incomes, harp_ratio, HM)
    used, rod_used = load_usage()

    if a.dead:
        print("\n=== 죽은 콘텐츠 후보 ===")
        no_path = [r for r in rows if not r["craftable"] and r["price"] == 0
                   and r["src"] not in ("튜토", "스폰마을")]
        print(f"획득경로 불명(레시피 없고 가격 0): {len(no_path)}종")
        for r in no_path[:20]:
            print(f"   {r['cat']:<5}{r['grade']:<3}{r['name']:<20} src={r['src']}")
        seen = set(used) | set(rod_used)
        never = [r for r in rows if r["name"] not in seen]
        print(f"\n실측 사용 0회: {len(never)}/{len(rows)}종 "
              f"(★표본 커버리지 Lv.{k.get('max_level_observed')} 라 고레벨은 당연히 0 — "
              f"판정은 Lv.{k.get('max_level_observed')} 이하만)")
        low = [r for r in never if r["lv"] <= (k.get("max_level_observed") or 26)]
        for r in sorted(low, key=lambda r: (r["cat"], r["lv"]))[:40]:
            print(f"   {r['cat']:<5}{r['grade']:<3}Lv{r['lv']:<3}{r['name']:<20}"
                  f"{r['total']:>12,.0f}원  {r['eff']:>10,.0f}원/h")
        unres = [r for r in rows if r["unresolved"]]
        if unres:
            print(f"\n★재료 가격을 못 낸 아이템 {len(unres)}종 (LP 공급원 없는 재료 포함):")
            seen_m = collections.Counter()
            for r in unres:
                for kind, mid, qq in r["unresolved"]:
                    seen_m[(kind, mid)] += 1
            for (kind, mid), c in seen_m.most_common():
                print(f"   {mid:<16}[{kind}] {c}개 아이템에서")
        return

    if not a.checks_only:
        for cat in (["낚싯대", "릴", "줄", "바늘", "찌", "미끼", "작살"] if not a.cat else [a.cat]):
            arr = [r for r in rows if r["cat"] == cat]
            if not arr:
                continue
            print(f"\n{'='*118}\n{cat}  (n={len(arr)})\n{'='*118}")
            print(f"{'등급':<3}{'Lv':>4} {'이름':<20}{'돈':>11}{'재료h':>7}{'재료원':>11}"
                  f"{'총비용':>12}{'성능/h':>10}{'회수h':>8}{'실사용':>6}  병목")
            for r in sorted(arr, key=lambda r: (r["lv"], r["name"])):
                u = used.get(r["name"], rod_used.get(r["name"], 0))
                bn = ", ".join(f"{m}" for m, _ in r["bottleneck"][:2]) or "-"
                pb = "∞" if r["payback"] == float("inf") else f"{r['payback']:.2f}"
                star = "" if r["measured"] else "~"      # ~ = 시급이 외삽
                if r["currency"] != "원":
                    money = (f"{r['p_cost'][0]:,}P/{r['p_cost'][1]}개"
                             if r["p_cost"] else r["currency"])
                    print(f"{r['grade']:<3}{r['lv']:>4} {r['name']:<20}{money:>11}"
                          f"{r['mat_h']:>7.2f}{'':>11}{'다른통화':>12}"
                          f"{r['eff']:>10,.0f}{'-':>8}{u:>6}  {bn}")
                    continue
                print(f"{r['grade']:<3}{r['lv']:>4} {r['name']:<20}{r['price']:>11,}"
                      f"{r['mat_h']:>7.2f}{r['mat_won']:>11,.0f}{star}{r['total']:>11,.0f}"
                      f"{r['eff']:>10,.0f}{pb:>8}{u:>6}  {bn}")

    # ── 소모품 유지비 (실측 소모율로) ────────────────────────────────────
    #  ★판정 지표를 «원/h» 가 아니라 «포획당 수입의 몇 %» 로 쓴다 — 소모는 시도 1건당 1개이므로
    #    이 비율은 처리량 가정(190 vs 220 vs 259)에 전혀 의존하지 않는다. 시간당으로 재면
    #    가정 하나가 흔들릴 때마다 결론이 바뀐다(구 material_gate 는 259/h 로 34% 과대계상했다).
    print(f"\n{'='*118}\n소모품(미끼) — 소모 규칙 = fish.result 1건마다 1개 "
          f"(EquipmentManager.reduceDurability, parts.json 내구 필드는 미끼에서 사문화)\n{'='*118}")
    print(f"{'등급':<3}{'Lv':>4} {'이름':<18}{'개당가':>9}{'포획당수입':>10}{'수입잠식':>9}"
          f"{'스탯가치/포획':>13}{'순이득/포획':>11}  판정")
    for r in sorted([r for r in rows if r["cat"] == "미끼"], key=lambda r: r["lv"]):
        band = BAND_OF_LEVEL(r["lv"])
        per_catch = (r["wage"] / SV.CATCH_PER_HOUR)
        cost = r["price"] if r["currency"] == "원" else (r["p_cost"][0] / r["p_cost"][1]
                                                        if r["p_cost"] else r["price"])
        unit = "원" if r["currency"] == "원" else "P"
        eat = cost / per_catch * 100
        perf_pc = r["eff"] / SV.CATCH_PER_HOUR
        verdict = ("🟢" if eat < 20 else "🟡" if eat < 60 else "🔴")
        print(f"{r['grade']:<3}{r['lv']:>4} {r['name']:<18}{cost:>8,.0f}{unit}{per_catch:>10,.0f}"
              f"{eat:>8.0f}%{perf_pc:>13,.0f}{perf_pc-(cost if unit=='원' else 0):>11,.0f}  {verdict}"
              + ("" if band else "  ~시급 외삽"))
    print("  ★릴/줄/바늘/찌는 내구 소모 후 «수리»다(파괴 아님) — 수리비/내구 × 소모율이 유지비.")
    print("  판정선: 수입잠식 <20% 🟢 · 20~60% 🟡 · >60% 🔴 (소모품이 그 등급 수입을 먹는 비율)")

    # ── 잠수상점 (다른 통화 = 잠수 포인트) ────────────────────────────────
    afkrows = [r for r in rows if r["currency"] == "P"]
    if afkrows:
        print(f"\n{'='*118}\n잠수상점 — 통화가 P(잠수대 1분=1P)다. 원 원장과 섞지 않는다.\n{'='*118}")
        print(f"{'등급':<3}{'Lv':>4} {'이름':<22}{'P':>9}{'AFK h':>8}{'성능/h':>11}"
              f"{'동급 원 대안 중위비용':>20}  parts.json 유령가격")
        for r in sorted(afkrows, key=lambda r: r["lv"]):
            peers = [x["total"] for x in rows if x["cat"] == r["cat"] and x["grade"] == r["grade"]
                     and x["currency"] == "원" and x["total"] == x["total"] and x["total"] > 0]
            peer = st.median(peers) if peers else float("nan")
            pc, n = r["p_cost"]
            print(f"{r['grade']:<3}{r['lv']:>4} {r['name']:<22}{pc:>9,}"
                  f"{pc*AFK_MIN_PER_POINT/60:>8.1f}{r['eff']:>11,.0f}{peer:>20,.0f}"
                  f"  {r['price']:,}원 (아무도 이 값으로 못 산다)")
        print("  ★AFK 시간은 기회비용이 0 에 가깝다(자리를 비운 시간) — 같은 성능을 «원+재료»로 사는 "
              "정상 경로와 비교하면 사실상 무료 경로다. 레벨 게이트만이 유일한 제동이다.")

    # ── 모델 커버리지 (판정 불가 구간을 드러낸다) ──────────────────────────
    print(f"\n{'='*118}\n모델 커버리지 — 원/h 가치 모델이 없는 스탯이 절반 이상인 아이템은 "
          f"사다리 판정에서 제외했다\n{'='*118}")
    low = [r for r in rows if r["cover"] < 0.5 and r["currency"] == "원"]
    bycat = collections.Counter(r["cat"] for r in low)
    print("  제외: " + (", ".join(f"{c} {n}종" for c, n in bycat.most_common()) or "없음"))
    print(f"  모델 없는 스탯: {', '.join(sorted(SPEAR_UNMODELED))} "
          f"(작살 {sum(1 for r in rows if r['cat']=='작살')}종 중 {bycat.get('작살',0)}종이 여기 걸린다)")
    print(f"  ★창 전용 스탯 {len(SPEAR_ONLY)}종은 harpoon_value.py 가 모델링한다"
          f"(실측 교전 16/16 검증) — 2026-08-26 이전엔 37종이 판정 불가였다.")
    gl = [r for r in rows if r["gate_led"] > 0.5 and r["eff"] > 0]
    print(f"  게이트가치(재료확률) 주도 아이템 {len(gl)}종 — income 아이템과 직접 비교할 때 주의: "
          f"{', '.join(r['name'] for r in sorted(gl, key=lambda r: -r['gate_led'])[:6])}")
    gs = [r for r in rows if r["growth_share"] > 0.5 and r["eff"] > 0]
    print(f"  성장가치(경험치) 주도 아이템 {len(gs)}종 — ★만렙 후 가치가 0 이 된다: "
          f"{', '.join(r['name'] for r in sorted(gs, key=lambda r: -r['growth_share'])[:6])}")

    warn, summary = ladder_checks(rows)
    print(f"\n{'='*118}\n사다리 검사\n{'='*118}")
    if not warn:
        print("🟢 지배·역전·도매할인·편차 경보 없음")
    for icon, msg, detail in warn:
        print(f"{icon} {msg}")
        for d in detail[:a.top]:
            print(f"     · {d}")
    print("\n등급별 «성능당 비용»(회수 h, 중위) — 오른쪽으로 갈수록 내려가야 정상")
    for cat, med in summary.items():
        ks = sorted(med, key=lambda x: {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4, "S": 5, "G": 6}.get(x, 9))
        print(f"  {cat:<6}" + "  ".join(f"{g} {med[g]:.2f}" for g in ks))


if __name__ == "__main__":
    main()
