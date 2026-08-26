#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
part_lines.py — 부품(릴·줄·바늘·찌·미끼) «계열 × 레벨» 성능 사다리 (2026-08-27).

`rod_lines.py` 가 낚싯대에 한 것을 부품에 한다. 지금은 **D등급만** 대상이다
(요청 범위 = 초반 계열 구멍). C·B·A 로 넓힐 때 GRADES 만 늘리면 된다.

────────────────────────────────────────────────────────────────────────────
왜 필요한가
────────────────────────────────────────────────────────────────────────────
D 에 성장·상인 계열을 신설하자 **기존 계열이 상대적으로 약하다는 게 드러났다** —
슬롯 안에서 레벨이 올라가는데 순성능이 내려가는 역전이 5건 났다:
    행운 릴 Lv5 8,516 < 수습 릴 Lv4 10,314 · 행운 찌 Lv6 4,343 < 수습 찌 Lv4 7,868
    대형 바늘 Lv6 7,835 < 수습 바늘 Lv4 9,632 · 행운실 Lv7 3,786 < 장터 줄 Lv6 6,426
    채집 찌 Lv7 6,141 < 장터 찌 Lv6 8,710

원인은 계열 부스탯의 «정규화 가치»가 계열마다 제각각이라는 것:
    성장 = 경험치 1.00 + 트리플찬스 2.00      상인 = 판매보너스 1.00 + 더블찬스 1.00
    행운 = 등급업 2.11 + 행운 **0.40**        채집 = 재료확률 1.00 (게이트축)
행운 라인은 행운 스탯이 0.40 이라 같은 숫자를 줘도 절반도 안 된다. 그래서 «행운 4» 가
«트리플찬스 1» 보다 약하다 — 유저에게는 4 > 1 로 보이는데 실제로는 1.6 < 2.0 이다.

────────────────────────────────────────────────────────────────────────────
설계
────────────────────────────────────────────────────────────────────────────
슬롯마다 «레벨 → 순성능» 선형 사다리를 두고, **계열 부스탯만** 스케일한다.
  · 슬롯 주스탯(릴 경험치 · 줄 도망감소 · 바늘 크리배율+크리확률 · 찌 등급업 · 미끼 행운)은
    그 슬롯의 정체성이므로 고정.
  · 난이도(숙련 시리즈) · 재료확률(채집)도 고정 — 각각 3층 예산과 라인 정체성이다.
  · 남은 계열 부스탯만 정수 스케일해 사다리에 맞춘다.

★미끼는 사다리에서 제외한다. `item_ledger` 의 미끼 순성능은 자기유지비(가격÷내구 ×
  소모율)가 income 을 넘어 **전 미끼가 음수**다(회수 ∞). 모델 결함이지 밸런스가 아니라
  여기서 고칠 수 없다 — 미끼는 스탯 정규화 가치로만 계열 간 형평을 맞추고 보고한다.

사용:
    python3 part_lines.py            # 현재 상태 진단
    python3 part_lines.py --tune     # 사다리에 맞춰 재탐색
    python3 part_lines.py --plan     # patch 스크립트용 PART_STATS 출력
"""
import argparse, collections, importlib.util, json, os, shutil
import sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, [name]
    spec.loader.exec_module(mod)
    sys.argv = saved
    return mod


MV = _load("material_value")
SV = _load("stat_value")
HV = _load("harpoon_value")
IL = _load("item_ledger")
MEAS = _load("measured")

GRADES = ("D",)
SLOTS = ("릴", "줄", "바늘", "찌")          # 미끼는 원장 모델 결함으로 제외(위 주석)
STAT_ORDER = ["난이도", "도망감소", "크리배율", "등급업", "크리확률", "크기", "경험치",
              "판매보너스", "더블찬스", "트리플찬스", "행운", "재료확률"]

#: 슬롯 주스탯 — 고정(슬롯 정체성)
SLOT_MAIN = {"릴": {"경험치"}, "줄": {"도망감소"}, "바늘": {"크리배율", "크리확률"},
             "찌": {"등급업"}, "미끼": {"행운"}}
#: 고정 축 — 3층 예산(난이도)과 라인 정체성(재료확률)
FROZEN = {"난이도", "재료확률"}
#: 사다리 — 슬롯별 (기준레벨 성능, 레벨당 증가). D 구간(Lv3~7)은 짧아 선형으로 충분하다.
#  값은 «현재 라이브에서 역전 없이 서 있는 행» 을 통과하도록 잡았다(2026-08-27 실측).
LADDER = {
    "릴":  (7800, 1250),      # Lv3 7,800 → Lv7 12,800
    "줄":  (2100, 1100),      # Lv3 2,100 → Lv7 6,500   (도망감소 축이 약해 기저가 낮다)
    "바늘": (6700, 1050),      # Lv3 6,700 → Lv7 10,900
    "찌":  (5450,  950),      # Lv3 5,450 → Lv7 9,250
}
BASE_LV = 3
BAND_OK, BAND_WARN = 0.10, 0.20
MINV = collections.defaultdict(lambda: 1, {"경험치": 3, "도망감소": 5})
#: D 등급 스탯 상한 — 상위 등급과의 사다리를 지킨다(C 참조: 등급업 6 · 판매 6 · 더블 5 ·
#  트리플 1 · 행운 3~7 · 경험치 30). 상한이 없으면 튜너가 «조정 가능한 축 하나»에 전부
#  쏟아붓는다(실측: 행운 찌가 조정축이 행운뿐이라 행운 16 이 나왔다 — D 에 과하다).
CAP = {"행운": 6, "트리플찬스": 1, "더블찬스": 3, "판매보너스": 5, "등급업": 6,
       "경험치": 15, "도망감소": 8, "크리확률": 6, "크리배율": 2, "크기": 3}


def target(slot, lv):
    a, b = LADDER[slot]
    return a + b * (lv - BASE_LV)


def parse(stat):
    d = {}
    for t in stat.split(","):
        if ":" in t:
            k, v = t.split(":", 1)
            try:
                d[k] = int(float(v))
            except ValueError:
                pass
    return d


def fmt(d):
    return ",".join(f"{k}:{d[k]}" for k in STAT_ORDER if d.get(k))


def load_targets():
    """대상 = GRADES 등급의 SLOTS 부품. 반환 {(slot,name): (lv, 스탯dict)}"""
    P = json.load(open(os.path.join(MV.BS, "parts.json"), encoding="utf-8"))["parts"]
    out = {}
    for slot in SLOTS:
        for name, raw in P[slot].items():
            f = raw.split("|")
            if f[1] in GRADES:
                out[(slot, name)] = (int(f[5]), parse(f[4]))
    return out


def ledger(overrides=None):
    P = json.load(open(os.path.join(MV.BS, "parts.json"), encoding="utf-8"))
    for (slot, name), stats in (overrides or {}).items():
        f = P["parts"][slot][name].split("|")
        f[4] = fmt(stats)
        P["parts"][slot][name] = "|".join(f)
    tmp = tempfile.mkdtemp()
    try:
        for fn in ("materials.json", "recipes.json"):
            shutil.copy(os.path.join(MV.BS, fn), tmp)
        json.dump(P, open(os.path.join(tmp, "parts.json"), "w", encoding="utf-8"),
                  ensure_ascii=False)
        rows = IL.build(MV.Data(bs=tmp), _SV, _INC, _RATIO, _HM)
    finally:
        shutil.rmtree(tmp)
    return {r["name"]: r for r in rows}


def tune(rounds=24):
    cur = {k: dict(v[1]) for k, v in load_targets().items()}
    for _ in range(rounds):
        sel = ledger(cur)
        moved = 0
        for (slot, name), stats in cur.items():
            lv = load_targets()[(slot, name)][0]
            r = sel.get(name)
            if not r or r["eff_net"] <= 0:
                continue
            want = target(slot, lv)
            if abs(r["eff_net"] / want - 1) <= BAND_OK * 0.6:
                continue
            # ★슬롯 주스탯도 조정 대상이다 — 행운 찌처럼 «주스탯 = 라인 메인» 인 조합은
            #   주스탯을 빼면 조정축이 행운(0.40) 하나뿐이 되어 극단값이 나온다.
            #   슬롯 정체성은 «어느 스탯을 갖는가»로 이미 지켜지고, 크기는 등급이 정한다.
            adj = [s for s in stats if s not in FROZEN]
            if not adj:
                continue
            # 조정 가능한 축이 만드는 몫만 스케일한다
            # ★가치축 조회는 STAT_KEY 하나로 부족하다 — 경험치는 GROWTH_KEY, 재료확률은
            #   GATE_KEY 에 있다. STAT_KEY 만 보면 경험치 기여가 0 으로 잡혀 스케일이 어긋난다
            #   (실측: 채집 찌가 목표의 −24.5% 에서 더 못 올라갔다).
            V = _SV[IL.STAGE_OF_LEVEL(lv)]
            def _val(st):
                for tbl in (IL.STAT_KEY, IL.GROWTH_KEY, IL.GATE_KEY):
                    if st in tbl:
                        return V.get(tbl[st], 0.0)
                return 0.0
            part = sum(stats[s] * _val(s) for s in adj)
            if part <= 0:
                continue
            need = want - (r["eff_net"] - part)
            f = max(0.5, min(2.5, need / part))
            new = dict(stats)
            for s in adj:
                new[s] = max(MINV[s], min(CAP.get(s, 99), int(round(stats[s] * f))))
            if new != stats:
                cur[(slot, name)] = new
                moved += 1
        if not moved:
            break
    return cur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tune", action="store_true")
    ap.add_argument("--plan", action="store_true")
    a = ap.parse_args()
    print(MEAS.banner(_K))
    tgt = load_targets()
    cur = tune() if a.tune else {k: dict(v[1]) for k, v in tgt.items()}
    sel = ledger(cur)

    if a.plan:
        print("\nPART_STATS = {")
        for (slot, name), stats in sorted(cur.items(), key=lambda kv: (kv[0][0], tgt[kv[0]][0])):
            print(f'    "{name}":{" " * max(1, 14 - len(name))}("{slot}", "{fmt(stats)}"),')
        print("}")
        return

    print(f"\n{'슬롯':<4}{'Lv':<4}{'이름':<14}{'순성능':>9}{'사다리':>9}{'편차':>8}  스탯")
    dev, inv = [], []
    for slot in SLOTS:
        seq = sorted(((tgt[k][0], k) for k in cur if k[0] == slot))
        prev, pn = 0, ""
        for lv, key in seq:
            r = sel[key[1]]
            t = target(slot, lv)
            d = r["eff_net"] / t - 1
            dev.append(abs(d))
            mark = "  " if abs(d) <= BAND_OK else ("🟡" if abs(d) <= BAND_WARN else "🔴")
            if r["eff_net"] < prev * (1 - BAND_WARN):
                inv.append((slot, pn, key[1]))
                mark = "🔴"
            print(f"{slot:<4}{lv:<4}{key[1]:<14}{r['eff_net']:>9,.0f}{t:>9,.0f}"
                  f"{d*100:>+7.1f}%{mark}{fmt(cur[key])}")
            prev, pn = max(prev, r["eff_net"]), key[1]
        print()
    print(f"  평균 절대편차 {sum(dev)/len(dev)*100:.1f}% · 최대 {max(dev)*100:.1f}%")
    print(f"  레벨 역전({BAND_WARN*100:.0f}% 초과 하락) {len(inv)}건"
          + ("".join(f"\n    {s}: {a_} → {b}" for s, a_, b in inv) if inv else " 🟢"))

    # 미끼 — 계열 부스탯 정규화 가치로만 형평 확인(원장 모델 결함으로 순성능 사용 불가)
    P = json.load(open(os.path.join(MV.BS, "parts.json"), encoding="utf-8"))["parts"]["미끼"]
    W = {"경험치": 1.00, "트리플찬스": 2.00, "판매보너스": 1.00, "더블찬스": 1.00,
         "등급업": 2.11, "행운": 0.40, "재료확률": 1.00, "크기": 0.59, "크리확률": 0.48}
    print("\n=== 미끼 D — 계열 부스탯 정규화 합 (판매보너스 1% = 1.00) ===")
    rows = []
    for name, raw in P.items():
        f = raw.split("|")
        if f[1] != "D":
            continue
        st = parse(f[4])
        rows.append((int(f[5]), name, sum(v * W.get(k, 0) for k, v in st.items()), fmt(st)))
    for lv, name, val, st in sorted(rows):
        print(f"  Lv{lv:<3}{name:<14}{val:>6.1f}  {st}")


_K = MEAS.apply(SV)
_SV, _INC = {}, {}
for _s in SV.STAGES:
    _r = SV.compute(_s)
    _SV[_s] = {k: v[0] for k, v in _r["V"].items()}
    _INC[_s] = _r["income"]
_HM = HV.Model()
_HS = _K["harpoon"]
_RATIO = ((_HS["catches_per_active_h"] / SV.CATCH_PER_HOUR)
          * (SV.size_mult(_HS["quality_mean"]) / SV.size_mult(_K["size_score"])))

if __name__ == "__main__":
    main()
