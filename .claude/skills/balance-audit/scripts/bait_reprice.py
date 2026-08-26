#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bait_reprice.py — 미끼 가격 재산출.

★2026-08-26 **전면 재작성**. 같은 날 오전 버전은 설계 철학을 반대로 잡고 있었다 —
「전부 양수 = 끼면 이득」을 목표로 가격을 뽑았다. 유저가 확정한 철학은 그 반대다:

> 미끼의 큰 철학은 **돈을 써서 재료·경험치를 더 얻거나, 큰 물고기 혹은 행운을 높여 좋은
> 물고기를 낚겠다**임. 그래서 **가격보다 (돈)효율이 좋으면 안 된다.**

즉 미끼는 **의도적인 골드 싱크**다. 돈으로는 항상 손해여야 하고, 그 손해가 곧 진행(재료·경험치)
과 수집(도감·기록·대물)의 대가다. 「끼면 돈이 더 번다」가 되면 미끼는 싱크가 아니라 수입원이 되고,
안 끼는 게 손해라 선택이 사라진다.

## 가격 공식

    가격 = V수입 + c × V진행 + s × 포획당 실현가
      V수입 = 수입축 스탯 가치(원/시도) = Σ(스탯 × stat_value 원/h) ÷ 소모/h
              수입축 = 행운·등급업·크기·판매보너스·더블·트리플·크리확률·크리배율·도망감소
      V진행 = 진행축(경험치·재료확률) 가치(원/시도)
      c     = 진행축 지불배수 ← 레버 2
      s     = 싱크 비율 ← 레버 1

★★2026-08-27 정정 — 「가격이 5~80배 과대」는 **틀린 결론이었다**. 그 판정은 «낚시 수입만이
유일한 수입원»이라는 암묵 가정에서 나왔는데, 실측 자금 유입은 **카지노 59.4% · 낚시 판매 16.2% ·
퀘스트 15.8% · 업적 3.5%** 다(money.txn 실측, admin/길드금고 제외). 낚시 판매는 유입의 1/6이라
«수입잠식 1678%» 는 *낚시 수입 대비* 사실이어도 파산 판정으로 읽으면 안 된다 — 실제로 유저는
370원 수집 미끼를 가장 많이 산다(74회, 최다 구매).
또 단위를 per-시도로 맞추면: 재료확률 1% 의 골드 가치는 **4.3원(초반)~19원(종결)/시도** 인데
채집 라인 현행 단가는 **31~647원/재확 1%** — 이미 7~34배 프리미엄이다.
⇒ **가격은 대체로 맞고 문제는 스탯 크기다.** 그래서 처방은 «스탯 너프 + 가격 유지»이고,
그러면 재확 단가가 자동으로 2~3배 오른다(= 유저가 요청한 «가격도 비싸게»의 실질).

★c 를 1 보다 크게 두는 것이 정당한 이유: **재료는 돈으로 살 수 없다**(어종 재료에 상점 경로가
없고 마켓 물량도 거의 없다). 대체 공급이 없는 재화는 프리미엄이 붙는 게 정상이고, 골드 환산
(`stat_value` 의 게이트 렌즈)은 그 프리미엄을 **구조적으로 못 잡는다** — 모델은 «시간을 시급으로
환산»할 뿐이다. 유저 체감이 「채집 미끼가 사기다」인 근거가 여기 있고, 그 체감은 모델보다 우선한다.

이 형태의 성질:
  · `가격 > V수입` 이 **구조적으로 보장**된다(싱크가 양수인 한). 철학의 하드 룰.
  · 플레이어의 돈 흐름은 정확히 **싱크만큼** 나빠진다 — 「이 미끼를 끼면 시간당 얼마를 태우나」가
    한 숫자로 읽힌다. 가격을 그냥 «수입의 몇 %»로 잡으면 그 해석이 안 나온다(수입축 스탯이
    돌려주는 몫이 가려진다).
  · 소모가 «시도 1건 = 1개»라 per-시도 회계가 자연 단위다(EquipmentManager.reduceDurability).

## 소모 규칙 (라이브 권위)
`reduceDurability()` 는 `fish.result` **1건마다 1회** 호출된다(성공·도주·중단 전부).
미끼는 내구가 아니라 **개수**라 이 차감 1회 = 미끼 1개. parts.json 의 미끼 내구 필드는 사문화다.
실측 소모율 = `measured.attempts_per_active_h`.

## 축 분류 — 왜 필요한가
- **수입축**: 돈으로 환산되는 것. 여기에 싱크를 얹어야 «돈으로는 손해»가 성립한다.
- **진행축**(경험치·재료확률): 미끼를 사는 **이유**. 값을 매기되 가격에 넣지 않는다
  (넣으면 진행까지 돈으로 사게 만들어 싱크가 두 배가 된다).
- **수집축 겹침**: 행운·등급업·크기·크리는 수입축이면서 동시에 «희귀·대물»을 만든다 —
  도감·기록·업적·퀘스트 가치는 `stat_value` 가 재지 않는다(가격에 안 들어간다는 뜻이고,
  그 미분값만큼 유저가 공짜로 얻는 몫이다).
- ★**순수 수익축 미끼**(판매보너스·더블·트리플·크리만 있는 것)는 이 철학에서 **존재 이유가 없다**.
  돈으로 돈을 사는데 손해다 — 안 끼는 게 항상 낫다. 이 스크립트가 그 목록을 따로 뽑는다.

사용:
    python3 bait_reprice.py                 # 권장 s 로 재산출
    python3 bait_reprice.py --sink 0.16     # 싱크 비율 바꿔서
    python3 bait_reprice.py --sweep         # s 민감도 표
    python3 bait_reprice.py --apply-plan    # parts.json 패치용 (등급|가격) 목록만
"""
import argparse, importlib.util, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
BS = os.environ.get("BLOCKSHIP_DATA",
                    "/Users/user/Library/Application Support/feather/player-server/servers/"
                    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    sv, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = sv
    return m


SV = _load("stat_value")
MEAS = _load("measured")

# ── 축 분류 ────────────────────────────────────────────────────────────────
#  수입축 = stat_value 가 원/h 로 환산하는 것 전부. 가격의 기준선이 된다.
INCOME = {"판매보너스": "판매보너스 (1%)", "더블찬스": "더블찬스 (1%)",
          "트리플찬스": "트리플찬스 (1%)", "등급업": "등급업 (1%)", "크기": "크기 (1%)",
          "행운": "행운 (1점)", "크리확률": "크리확률 (1%)", "크리배율": "크리배율 (1점)",
          "도망감소": "도주감소 (1%)", "도주감소": "도주감소 (1%)", "난이도": "난이도 (1점)"}
PROGRESS = {"경험치": "경험치 (1%)", "재료확률": "재료확률 (1%)"}
#  수집축과 겹치는 것 — 희귀·대물을 만들어 도감/기록/퀘스트로도 값을 한다(가격에는 안 넣는다)
COLLECT = {"행운", "등급업", "크기", "크리확률", "크리배율"}
#  순수 수익축 — 이것만 있으면 «돈으로 돈을 사는» 미끼다
PURE_PROFIT = {"판매보너스", "더블찬스", "트리플찬스", "도망감소", "도주감소", "난이도"}

# ── 설계 레버 ──────────────────────────────────────────────────────────────
#  싱크 = 포획당 실현가의 이 비율. 「이 미끼를 끼면 수입의 몇 %를 태우나」가 그대로 이 값이다.
#  ★평탄(flat)으로 둔다: 절대 싱크는 구간 수입에 비례해 자동으로 커지고, 상위 등급은 같은
#    비율로 훨씬 많은 스탯을 주므로 「상위 등급이 가성비가 좋아야」 원칙이 자동 충족된다.
DEFAULT_SINK = 0.12
#  진행축 지불배수. 0 이면 진행은 공짜(구 동작), 1 이면 골드 환산 그대로, >1 이면 프리미엄.
#  ★1.5 로 확정(2026-08-27). 채집 라인은 수입축이 0 이라 가격 전체가 «진행 대가 + 싱크»다.
#    c=1.0 → 수집 미끼 150원(낚시 수입의 29% 소모) / c=1.5 → 190원(37%) / c=2.0 → 230원(45%).
#    37% = 「재료를 캐는 동안 낚시 수입의 1/3 을 낸다」로 읽히고, 진행 가치의 약 2.4배를 지불한다.
DEFAULT_CHARGE = 1.5
#  가격 라운딩 — 상점 표기가 읽히도록. 자릿수별 단계.
def tidy(p):
    if p < 50:
        return max(5, int(round(p / 5.0)) * 5)
    if p < 500:
        return int(round(p / 10.0)) * 10
    if p < 5000:
        return int(round(p / 50.0)) * 50
    return int(round(p / 100.0)) * 100


KEEP = {"지렁이"}      # ★유저 지시 — 지렁이는 손대지 않는다(무료급 입문 미끼)
OTHER_CURRENCY = ("잠수상점", "캐시", "개발자")

stage_of = lambda lv: "초반" if lv < 20 else ("중반" if lv < 50 else "종결")
band_of = lambda lv: ("Lv1-9" if lv < 10 else "Lv10-19" if lv < 20
                      else "Lv20-29" if lv < 30 else None)


def build():
    k = MEAS.apply(SV)
    A = k["attempts_per_active_h"]
    V, INC = {}, {}
    for st in SV.STAGES:
        r = SV.compute(st)
        V[st] = {kk: v[0] for kk, v in r["V"].items()}
        INC[st] = r["income"]
    parts = json.load(open(os.path.join(BS, "parts.json"), encoding="utf-8"))["parts"]["미끼"]
    order = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4, "S": 5}
    rows = []
    for name, line in parts.items():
        f = line.split("|")
        grade, price, lv = f[1], int(f[2]), int(f[5])
        src = f[6] if len(f) > 6 else ""
        stats = {}
        for tok in f[4].split(","):
            if ":" in tok:
                kk, vv = tok.split(":", 1)
                try:
                    stats[kk] = float(vv)
                except ValueError:
                    pass
        S = stage_of(lv)
        v_inc = sum(v * V[S][INCOME[kk]] for kk, v in stats.items() if kk in INCOME) / A
        v_prog = sum(v * V[S][PROGRESS[kk]] for kk, v in stats.items() if kk in PROGRESS) / A
        b = band_of(lv)
        per_catch = (k["income_by_band"][b] if b else INC[S]) / k["catches_per_active_h"]
        rows.append(dict(name=name, grade=grade, lv=lv, price=price, src=src, stats=stats,
                         v_inc=v_inc, v_prog=v_prog, per_catch=per_catch, measured=bool(b),
                         ord=order.get(grade, 9),
                         other_cur=any(o in src for o in OTHER_CURRENCY),
                         has_prog=v_prog > 0,
                         has_collect=any(s in COLLECT for s in stats),
                         pure_profit=bool(stats) and all(s in PURE_PROFIT for s in stats)))
    rows.sort(key=lambda r: (r["ord"], r["lv"]))
    return k, A, rows


def price_of(r, s, c=DEFAULT_CHARGE):
    return tidy(r["v_inc"] + c * r["v_prog"] + s * r["per_catch"])


# ── 채집 라인 재설계 — «재료확률 전문 미끼» (2026-08-27 유저 지시) ──────────
#  지시: "채집 시리즈들 행운을 없애고 재료확률을 살리는 방향으로 가자 그래야 좀 독창적이지"
#
#  왜 이게 더 좋은 설계인가:
#   ① **정체성이 갈린다.** 지금은 모든 미끼에 행운이 붙어 «행운 미끼 + 약간의 무엇»이라 선택이
#      없다(실측: 22종 전부 행운 보유). 채집 라인에서 행운을 빼면 처음으로 진짜 분기가 생긴다 —
#      「물고기 값을 올릴 것인가(행운·판매·크리) vs 재료를 캘 것인가(채집)」.
#   ② **철학이 문자 그대로 성립한다.** 행운을 빼면 V수입 ≈ 0 이라 어떤 가격이든 «돈으로는
#      손해»가 자동 보장된다. 「돈을 써서 재료를 얻는다」가 은유가 아니라 회계가 된다.
#   ③ **행운은 재료확률보다 훨씬 싸다** — 초반 행운 1점 ≈ 재료확률 0.4%. 그래서 행운을 통째로
#      빼도 잃는 가치가 작고, 그 몫을 재료확률로 되돌려 주면 «강화»처럼 느껴진다(체감 이득).
#
#  스탯 처방: 행운·등급업·판매보너스(수입축) 전부 제거 → 경험치 유지 + 재료확률 ×1.5
#            (÷2 너프 초안은 폐기. 이 라인은 «약하게»가 아니라 «전문화»가 목표다)
NERF_MATCHANCE = {"D": 6, "C": 12, "B": 22, "A": 30}   # 현행 4/8/15/20 의 ×1.5
STRIP_STATS = {"행운", "등급업", "판매보너스", "더블찬스", "트리플찬스",
               "크리확률", "크리배율", "크기", "도망감소"}
COLLECTOR_LINE = {"채집 미끼", "수집 미끼", "유적 미끼", "수집상 미끼"}

def apply_nerf(rows, k, A):
    """채집/수집 라인에 스탯 재설계를 적용하고 V수입·V진행을 다시 계산한다."""
    V = {}
    for st in SV.STAGES:
        r = SV.compute(st)
        V[st] = {kk: v[0] for kk, v in r["V"].items()}
    for r in rows:
        if r["name"] not in COLLECTOR_LINE:
            continue
        g = r["grade"]
        old = dict(r["stats"])
        for k_ in list(r["stats"]):
            if k_ in STRIP_STATS:
                r["stats"].pop(k_)          # 수입축 전부 제거 → 채집 전문화
        if g in NERF_MATCHANCE:
            r["stats"]["재료확률"] = NERF_MATCHANCE[g]
        S = stage_of(r["lv"])
        r["v_inc"] = sum(v * V[S][INCOME[kk]] for kk, v in r["stats"].items() if kk in INCOME) / A
        r["v_prog"] = sum(v * V[S][PROGRESS[kk]] for kk, v in r["stats"].items() if kk in PROGRESS) / A
        r["nerfed"] = (old, dict(r["stats"]))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sink", type=float, default=DEFAULT_SINK, help="싱크 비율 (기본 0.12)")
    ap.add_argument("--charge", type=float, default=DEFAULT_CHARGE,
                    help="진행축 지불배수 c (기본 1.5 · >1 이면 프리미엄)")
    ap.add_argument("--nerf", action="store_true",
                    help="채집/수집 라인 스탯 재설계안을 적용해 재산출")
    ap.add_argument("--final", action="store_true",
                    help="확정 제안 — 채집 라인 너프 + 가격 유지, 나머지는 모델가")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--apply-plan", action="store_true")
    a = ap.parse_args()

    k, A, rows = build()
    if a.final:
        a.nerf = True
    if a.nerf:
        rows = apply_nerf(rows, k, A)
    live = [r for r in rows if not r["other_cur"] and r["name"] not in KEEP]

    if a.apply_plan:
        for r in live:
            st = ",".join(f"{kk}:{int(v)}" for kk, v in r["stats"].items())
            pf = (FINAL_COLLECTOR_PRICE.get(r["name"]) if a.final else None) \
                 or price_of(r, a.sink, a.charge)
            print(f"{r['name']}\t{r['price']}\t{pf}\t{st}")
        return

    print(MEAS.banner(k))
    print(f"소모 {A:.0f}회/h (fish.result 1건 = 미끼 1개) · 싱크 s = {a.sink:.0%} · 진행축 배수 c = {a.charge:.1f}"
          + ("  · ★채집/수집 라인 스탯 너프 적용" if a.nerf else ""))
    print("가격 = V수입 + c×V진행 + 싱크  →  «돈(수입)으로는 항상 손해»가 구조적으로 보장된다")
    if a.nerf:
        print("\n=== 채집 라인 재설계 — «재료확률 전문 미끼» (수입축 제거 + 재확 ×1.5) ===")
        for r in rows:
            if r.get("nerfed"):
                o, n = r["nerfed"]
                keys = list(dict.fromkeys(list(o) + list(n)))
                ch = ", ".join(f"{kk} {int(o.get(kk,0))}→{int(n.get(kk,0))}"
                               for kk in keys if o.get(kk) != n.get(kk))
                print(f"  {r['grade']} Lv{r['lv']:<3}{r['name']:<16}{ch}")

    if a.sweep:
        print("\n=== 싱크 s 민감도 (등급별 신가격 중위) ===")
        gs = ["D", "C", "B", "A"]
        print(f"{'s':>6}" + "".join(f"{g:>12}" for g in gs) + f"{'A 최고가':>12}")
        for s in (0.06, 0.08, 0.10, 0.12, 0.16, 0.20, 0.25):
            import statistics as st
            row = []
            for g in gs:
                arr = [price_of(r, s, a.charge) for r in live if r["grade"] == g]
                row.append(st.median(arr) if arr else 0)
            mx = max((price_of(r, s, a.charge) for r in live if r["grade"] == "A"), default=0)
            print(f"{s:>5.0%}" + "".join(f"{v:>12,.0f}" for v in row) + f"{mx:>12,.0f}")
        return

    print(f"\n{'등급':<3}{'Lv':>4} {'이름':<16}{'V수입':>7}{'V진행':>7}{'싱크':>7}"
          f"{'신가격':>8}{'현재가':>8}{'배율':>7}{'싱크/수입':>9}{'진행/싱크':>9}  축")
    for r in rows:
        s_amt = a.sink * r["per_catch"]
        if r["other_cur"]:
            axis = "★다른통화(P)"
            print(f"{r['grade']:<3}{r['lv']:>4} {r['name']:<16}{r['v_inc']:>7,.0f}{r['v_prog']:>7,.0f}"
                  f"{'-':>7}{'-':>8}{r['price']:>8,}{'-':>7}{'-':>9}{'-':>9}  {axis}")
            continue
        if r["name"] in KEEP:
            print(f"{r['grade']:<3}{r['lv']:>4} {r['name']:<16}{r['v_inc']:>7,.0f}{r['v_prog']:>7,.0f}"
                  f"{'-':>7}{'유지':>8}{r['price']:>8,}{'-':>7}{'-':>9}{'-':>9}  ★유저 지시로 고정")
            continue
        p = (FINAL_COLLECTOR_PRICE.get(r["name"]) if a.final else None) \
            or price_of(r, a.sink, a.charge)
        axis = []
        if r["has_prog"]:
            axis.append("진행")
        if r["has_collect"]:
            axis.append("수집")
        if r["pure_profit"]:
            axis.append("🔴순수수익")
        star = "" if r["measured"] else "~"
        print(f"{r['grade']:<3}{r['lv']:>4} {r['name']:<16}{r['v_inc']:>7,.0f}{r['v_prog']:>7,.0f}"
              f"{s_amt:>7,.0f}{p:>8,}{r['price']:>8,}{p/max(1,r['price']):>6.2f}x"
              f"{s_amt/r['per_catch']*100:>8.0f}%{star}"
              f"{(r['v_prog']/s_amt if s_amt else 0):>9.2f}  " + "+".join(axis or ["-"]))

    print("\n※ 배율 = 신가격 ÷ 현재가 · 싱크/수입 = 그 미끼를 끼면 태우는 수입 비율(설계상 s 고정)")
    print("※ 진행/싱크 = 태운 돈 1원당 돌아오는 진행(경험치·재료확률) 가치 — 클수록 «살 이유»가 크다")
    print("※ ~ = 그 레벨 구간의 실측 시급이 없어 모델 외삽 (Lv30+)")

    # ── 하드 룰 검증 ────────────────────────────────────────────────────
    print("\n=== 하드 룰 검증 — 「가격 > V수입」 (돈으로는 항상 손해) ===")
    final_p = lambda r: ((FINAL_COLLECTOR_PRICE.get(r["name"]) if a.final else None)
                         or price_of(r, a.sink, a.charge))
    bad = [r for r in live if final_p(r) <= r["v_inc"]]
    if bad:
        for r in bad:
            print(f"  🔴 {r['name']} 신가격 {final_p(r):,} ≤ V수입 {r['v_inc']:,.0f} "
                  f"— 라운딩이 싱크를 먹었다. s 를 올리거나 tidy() 단계를 줄일 것")
    else:
        print(f"  🟢 {len(live)}종 전부 통과 (최소 여유 "
              f"{min(final_p(r)-r['v_inc'] for r in live):,.0f}원/시도)")

    # ── 철학 위반 콘텐츠 ────────────────────────────────────────────────
    pp = [r for r in live if r["pure_profit"]]
    print(f"\n=== 🔴 순수 수익축 미끼 {len(pp)}종 — 이 철학에서 존재 이유가 없다 ===")
    for r in pp:
        print(f"  {r['grade']} Lv{r['lv']:<3}{r['name']:<16} {', '.join(f'{a_}:{int(b)}' for a_, b in r['stats'].items())}")
    if pp:
        print("  돈으로 돈을 사는데 가격이 더 비싸다 → 안 끼는 게 항상 낫다. 셋 중 하나가 필요하다:")
        print("   (a) 진행축 스탯(경험치·재료확률)을 하나 붙여 «사는 이유»를 만든다  ← 권장")
        print("   (b) 수집축(행운·크기·등급업)으로 갈아 «좋은 물고기» 미끼로 만든다")
        print("   (c) 삭제 — 다만 콘텐츠가 줄어든다")

    # ── ★구조 진단: 수입축에만 스탯이 실린 미끼는 «값을 매기든 안 매기든 무의미»하다 ──
    #  ★2026-08-27 판정 완화 (유저 지적). 초안은 「수입축 전용 미끼는 wash 니까 스탯을 진행축으로
    #  옮겨야 한다」고 결론했는데 그건 **단일 최적 로드아웃을 가정한 모델의 결론**이다. 실제로는
    #   ① 유저는 판매·더블·크리에 «혹해서» 산다(체감 매력은 모델 밖) ② 자기 장비가 크리 빌드면
    #      크리 미끼를 사고, 그 **시너지를 모델이 모른다** ③ 판매보너스는 상황에 따라 더/덜 효율적이다.
    #  그래서 이 표는 «판정»이 아니라 **모델 한계 표시**다 — 수입 증가폭이 클수록 「가격 > 효율」
    #  규칙이 순수입에 미치는 영향이 커진다는 정보만 준다. 스탯 이관 권고는 철회했다.
    print("\n=== 구조 정보 — 미끼가 수입을 몇 % 올리나 (모델 한계 표시, 판정 아님) ===")
    print(f"{'등급':<3}{'Lv':>4} {'이름':<16}{'수입증가':>9}{'V진행 비중':>11}  판정")
    wash = []
    for r in live:
        gross = r["per_catch"] * k["catches_per_active_h"]
        up = r["v_inc"] * A / gross * 100
        share = r["v_prog"] / (r["v_inc"] + r["v_prog"]) * 100 if (r["v_inc"] + r["v_prog"]) else 0
        verdict = ("진행축 주도" if share >= 50 else
                   "혼합" if share >= 20 else
                   "수입축 위주 (시너지·체감은 모델 밖)")
        if share < 20:
            wash.append(r)
        print(f"{r['grade']:<3}{r['lv']:>4} {r['name']:<16}{up:>8.1f}%{share:>10.0f}%  {verdict}")
    print(f"\n  수입축 위주 {len(wash)}/{len(live)}종. ★이건 결함 목록이 아니다 — 빌드 시너지와")
    print("  체감 매력은 이 모델이 재지 못한다(유저 판단, 2026-08-27). 다만 수입 증가폭이 큰 미끼는")
    print("  「가격 > 효율」 규칙 때문에 가격도 같이 커진다는 점만 알고 있을 것.")

    # ── 가격 역전 = 스탯 역전의 그림자 ──────────────────────────────────
    #  가격이 V수입을 따라가므로, 등급이 올라가는데 신가격이 내려가면 그건 «가격 버그»가 아니라
    #  **스탯 사다리가 뒤집혔다**는 뜻이다. 공식이 콘텐츠 결함을 드러내는 자리다.
    print("\n=== 가격 역전 → 스탯 사다리 역전 (공식이 드러낸 콘텐츠 결함) ===")
    inv = []
    for hi in live:
        for lo in live:
            # ★축이 다르면 역전이 아니다 — 진행축 전문 미끼가 수입축 미끼보다 비싼 것은
            #   설계 의도다(다른 물건을 파는 것이다). 같은 축끼리만 비교한다.
            if (hi["has_prog"] == lo["has_prog"]
                    and hi["ord"] > lo["ord"] and hi["lv"] > lo["lv"]
                    and price_of(hi, a.sink, a.charge) < price_of(lo, a.sink, a.charge) * 0.98):
                inv.append((hi, lo))
    if not inv:
        print("  🟢 없음")
    for hi, lo in sorted(inv, key=lambda t: price_of(t[1], a.sink, a.charge)
                         / max(1, price_of(t[0], a.sink, a.charge)), reverse=True)[:8]:
        print(f"  🟡 {hi['grade']} Lv{hi['lv']:<3}{hi['name']:<16}{price_of(hi,a.sink,a.charge):>7,}원 "
              f"< {lo['grade']} Lv{lo['lv']:<3}{lo['name']:<16}{price_of(lo,a.sink,a.charge):>7,}원 "
              f"(V수입 {hi['v_inc']:,.0f} < {lo['v_inc']:,.0f})")

    # ── 다른 통화 미끼는 철학을 우회한다 ────────────────────────────────
    oc = [r for r in rows if r["other_cur"]]
    if oc:
        print("\n=== 🔴 다른 통화 미끼 — 「돈으로는 손해」 규칙을 우회한다 ===")
        afk = _load("item_ledger").afk_shop_costs()
        for r in oc:
            e = afk.get(r["name"])
            per = (e[0] / max(1, e[1])) if e else None
            note = (f"{e[0]:,}P / {e[1]}개 = {per:.1f}P/개 (AFK {per:.1f}분)" if e
                    else f"{r['src']} 통화")
            print(f"  {r['grade']} Lv{r['lv']:<3}{r['name']:<16} {note} · V수입 {r['v_inc']:,.0f}원/시도"
                  + (f" → 1P ≈ {r['v_inc']/per:,.1f}원의 순수익" if per else ""))
        print("  AFK 시간의 기회비용이 0 에 가까우므로 이 미끼는 **끼면 돈을 번다** — 철학 위반이다.")
        print("  처방: P 가격을 올리거나(1P ≈ 원 환산 기준을 정하고 V수입 위로), 미끼 판매를 빼고")
        print("        다른 편의 품목으로 바꾸거나, 수입축 스탯을 진행축으로 갈아탈 것.")

    # ── 재료확률 단가 (유저 요청 «가격도 비싸게» 의 실질 검증) ──────────────
    coll = [r for r in rows if r["name"] in COLLECTOR_LINE]
    if coll:
        print("\n=== 재료확률 단가 (원/재확 1%) — 스탯 너프의 실질 효과 ===")
        print(f"{'미끼':<12}{'현재 재확':>8}{'현재가':>9}{'현 단가':>8}   "
              f"{'신 재확':>7}{'신가격':>9}{'신 단가':>8}{'단가배율':>9}   재확 1% 골드가치/시도")
        Vm = {}
        for st in SV.STAGES:
            Vm[st] = SV.compute(st)["V"]["재료확률 (1%)"][0] / A
        for r in sorted(coll, key=lambda r: r["ord"]):
            old = r.get("nerfed", (r["stats"], r["stats"]))[0]
            mo, mn = old.get("재료확률", 0), r["stats"].get("재료확률", 0)
            po, pn = r["price"], final_p(r)
            if not (mo and mn):
                continue
            print(f"{r['name']:<12}{mo:>8g}{po:>9,}{po/mo:>8,.0f}   {mn:>7g}{pn:>9,}"
                  f"{pn/mn:>8,.0f}{(pn/mn)/(po/mo):>8.2f}x   {Vm[stage_of(r['lv'])]:>10,.1f}원")
        print("  ★재확 1% 의 골드가치가 4~19원/시도인데 단가는 90~650원 — 이미 7~34배 프리미엄이다.")
        print("    재료는 돈으로 살 수 없으니(어종 재료 상점 경로 없음) 그 프리미엄 자체는 정당하다.")

    # ── 사다리 검증 ──────────────────────────────────────────────────────
    print("\n=== 사다리 — 등급이 오르면 «태운 돈당 진행»이 좋아지는가 ===")
    import statistics as st
    for g in ("D", "C", "B", "A"):
        arr = [r for r in live if r["grade"] == g and r["has_prog"]]
        if not arr:
            print(f"  {g}: 진행축 미끼 없음")
            continue
        v = [r["v_prog"] / (a.sink * r["per_catch"]) for r in arr]
        print(f"  {g}: 진행/싱크 중위 {st.median(v):>6.2f}  (n={len(arr)}: "
              f"{', '.join(r['name'] for r in arr)})")

    # ── 총 싱크 규모 ────────────────────────────────────────────────────
    print("\n=== 싱크 규모 (그 구간에서 최고 미끼를 상시 착용할 때) ===")
    for label, lv in (("초반 Lv1-9", 5), ("중반 Lv10-19", 15), ("중반 Lv20-29", 25),
                      ("종결 Lv50+", 54)):
        cand = [r for r in live if r["lv"] <= lv]
        if not cand:
            continue
        best = max(cand, key=lambda r: r["v_inc"] + r["v_prog"])
        p = final_p(best)
        sink_h = (p - best["v_inc"]) * A
        gross = best["per_catch"] * k["catches_per_active_h"]
        print(f"  {label:<14} {best['name']:<16} {p:>7,}원  →  싱크 {sink_h:>10,.0f}원/h "
              f"({sink_h/gross*100:>4.1f}% of {gross:,.0f}원/h)")


if __name__ == "__main__":
    main()
