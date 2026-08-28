#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_level_spread.py — 장비 **요구 레벨**을 성능 순서대로 구간에 고르게 펴 준다 (2026-08-28).

유저 지시: "레벨 배분을 수정하는건 어떻게생각해? 지금 레벨 벽 느껴지는 부분좀 찾아줘" → "둘 다 해줘"

## 무엇이 문제였나 (실측)
부품 5종(릴·줄·바늘·미끼·찌)은 **마을×등급마다 «라인» 단위로 통째 배치**돼 있어서, 사막마을
A 는 라인이 둘(Lv40·Lv47)뿐이었다. 그 사이 **Lv41~46 여섯 레벨이 부품 사막**이고, 하필
그 한가운데 Lv45 에 경험치 ×1.68 벽이 있다. 반대로 Lv47·Lv54 에는 각 10 종이 겹쳐 있어
selftest [9] 의 «동레벨 성능 이상치» 20 건이 거기서 나온다.
⇒ **부품이 부족한 게 아니라 몇 지점에 뭉쳐 있다.** 뭉친 걸 펴면 두 문제가 같이 풀린다.

## 어떻게 펴나
  ① **사막을 만든 부품 그룹만** 재배치한다(BANDS). 낚싯대·작살과 저레벨 부품은 이미 밴드를
     채우고 있어 건드리지 않는다 — 전 종을 재배치하면 초반까지 흔들려 손해가 크다(실측:
     전 그룹 적용 시 199/322 종이 움직였고 「장터 작살 Lv8→3」 같은 게 나왔다).
  ② 부품은 «라인» 단위(릴·줄·바늘·미끼·찌 5 종이 한 레벨에 통째로)라 카테고리별로 나눠
     펴면 각 그룹이 1 종뿐이라 펴지지 않는다(왕도 A 가 전부 Lv54 에 붙어 있었다).
     ⇒ (출처, 등급) 안에서 **카테고리별 성능 순위(티어)** 를 매기고, «티어 → 카테고리»
       순으로 평탄화해 밴드에 등간격 배치한다. 라인이 레벨에 걸쳐 **계단식**으로 흩어져
       한 레벨에 5 종이 겹치지 않고, 플레이어는 매 레벨 한 칸씩 갈아끼우게 된다.
  ③ 배치 후 같은 (카테고리, 레벨)에 성능이 SPREAD_CAP 넘게 벌어지면 밴드 안에서 ±1 밀어
     충돌을 푼다(다른 마을 밴드가 겹치는 구간 — 예: 낚싯대 Lv52 에 왕도·상단이 함께 온다).

★스탯·재료·가격은 **건드리지 않는다**. 레벨만 움직인다.
★★그런데 요구캐스트 목표는 상대성능 = 성능 ÷ **그 구간 시급** 이라 레벨이 바뀌면 구간이
   바뀌고 목표도 바뀐다. **이 스크립트를 돌린 뒤에는 반드시 patch_cast_cost.py 를 다시 돌릴 것.**

사용:
    python3 patch_level_spread.py <BlockShip경로> [--apply]
"""
import collections, importlib.util, json, os, shutil, sys

SKILL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     ".claude", "skills", "balance-audit", "scripts")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SKILL, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    sv, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = sv
    return m


#: 밴드 덮어쓰기 — «사막»을 만드는 그룹만. (카테고리군, 출처, 등급) → (lo, hi)
#  PARTS = 부품 5종 공통. 낚싯대·작살은 이미 밴드를 채우고 있어 현재값을 그대로 쓴다.
PARTS = ("릴", "줄", "바늘", "미끼", "찌")
BANDS = {
    # 사막마을 A 부품이 Lv40 과 Lv47 두 점에만 있어 41~46 이 비었다 → 밴드를 40~46 으로.
    ("PARTS", "사막마을", "A"): (40, 46),
    # 상단마을 A 부품 29 종이 47~54 에 몰려 Lv47 에 5 종이 겹친다 → 47~53 으로 펴고
    # 54~57 은 왕도에 넘긴다(왕도 낚싯대가 이미 52~57 이라 마을 진행과도 맞는다).
    ("PARTS", "상단마을", "A"): (47, 53),
    ("PARTS", "왕도", "A"): (54, 57),
    # ★2026-08-28 초반 확장 — 전수조사 결과 초반도 같은 병이었다. 라인이 통째로 한 레벨에
    #   떨어져 Lv1(9종)·6(7)·19(6)·20(6)·27·28·34·35·38(각 5종)에 몰리고, 그 사이에
    #   릴 Lv22~26·미끼 Lv21~26 같은 카테고리 사막이 생긴다. 밴드는 그 그룹의 현재
    #   [min, max] 를 그대로 쓰되(진행 순서 보존) 라인만 계단식으로 흩는다.
    ("PARTS", "스폰마을", "D"): (3, 9),
    ("PARTS", "스폰마을", "C"): (10, 19),
    ("PARTS", "스폰마을", "B"): (20, 27),
    ("PARTS", "사막마을", "B"): (28, 34),
    # 왕도 B 는 35~38 인데 Lv39 가 비어 있고 사막마을 A 가 Lv40 부터라 39 만 구멍이다 → 39 까지.
    ("PARTS", "왕도", "B"): (35, 39),
}
#: 낚싯대·작살도 같은 방식으로 편다. 이쪽은 카테고리가 하나뿐이라 «라인» 개념이 없고,
#  그룹 안에서 성능 순으로 현재 밴드에 등간격 배치하면 된다. 밴드는 현재 [min, max].
#  ★대상은 사막(연속 3레벨 이상 공백)이 있는 그룹만 — 멀쩡한 그룹까지 흔들면 손해다.
SOLO_SPREAD = {
    ("낚싯대", "스폰마을", "C"),   # Lv15~17 사막
    ("작살", "사막마을", "B"),     # Lv31~33 사막
}
#: 같은 (카테고리, 레벨) 안에서 허용하는 성능 산포. selftest [9] 와 같은 기준.
SPREAD_CAP = 0.25
#: 레벨을 옮기지 않는 출처 — 특수 층이라 «사다리»가 아니다.
FREEZE_SRC = {"튜토", "잠수상점", "캐시", "개발자", "대장간"}


def band_key(cat, src, grade):
    return ("PARTS" if cat in PARTS else cat, src, grade)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src_dir, apply_ = sys.argv[1], "--apply" in sys.argv
    os.environ["BLOCKSHIP_DATA"] = src_dir

    CC = _load("cast_cost")
    D, K, rows, cph = CC.build_rows()
    perf = {r["name"]: r["perf"] for r in rows}

    P = json.load(open(os.path.join(src_dir, "parts.json"), encoding="utf-8"))
    items = {}
    for cat, d in P["parts"].items():
        for n, s in d.items():
            f = s.split("|")
            items[n] = dict(cat=cat, grade=f[1], lv=int(f[5]),
                            src=f[6] if len(f) > 6 else "", spec=f)

    # ── ① 재배치 ────────────────────────────────────────────────────────────
    newlv = {n: v["lv"] for n, v in items.items()}
    bands = {}
    for n, v in items.items():   # 충돌완화가 참조할 기본 밴드 = 그룹의 현재 [min, max]
        b = bands.setdefault((v["cat"], v["src"], v["grade"]), [99, 0])
        b[0], b[1] = min(b[0], v["lv"]), max(b[1], v["lv"])

    # (a) 부품 — (출처, 등급) 안에서 «티어 → 카테고리» 로 평탄화해 라인을 계단식으로 흩는다
    for (kind, src_v, gr), (lo, hi) in BANDS.items():
        assert kind == "PARTS", kind
        tiers = {}
        for c in PARTS:
            ns = [n for n, v in items.items()
                  if v["cat"] == c and v["src"] == src_v and v["grade"] == gr]
            tiers[c] = sorted(ns, key=lambda n: (perf.get(n, 0.0), n))
        T = max((len(v) for v in tiers.values()), default=0)
        if T == 0:
            continue
        flat = [(t, c, tiers[c][t]) for t in range(T) for c in PARTS if t < len(tiers[c])]
        for i, (t, c, n) in enumerate(flat):
            newlv[n] = lo if len(flat) == 1 else lo + round(i * (hi - lo) / (len(flat) - 1))
            bands[(c, src_v, gr)] = [lo, hi]

    # (b) 낚싯대·작살 — 그룹 안에서 성능 순으로 현재 밴드에 등간격
    for g in SOLO_SPREAD:
        cat, src_v, gr = g
        ns = sorted((n for n, v in items.items()
                     if v["cat"] == cat and v["src"] == src_v and v["grade"] == gr),
                    key=lambda n: (perf.get(n, 0.0), n))
        if not ns:
            continue
        lo, hi = bands[g]
        for i, n in enumerate(ns):
            newlv[n] = lo if len(ns) == 1 else lo + round(i * (hi - lo) / (len(ns) - 1))

    # ── ③ 동레벨 충돌 완화 ──────────────────────────────────────────────────
    moves = 0
    for _ in range(12):
        bylv = collections.defaultdict(list)
        for n, v in items.items():
            bylv[(v["cat"], newlv[n])].append(n)
        worst = None
        for (cat, lv), ns in bylv.items():
            ps = [perf.get(n, 0.0) for n in ns if perf.get(n, 0.0) > 0]
            if len(ps) < 2:
                continue
            sp = max(ps) / min(ps) - 1
            if sp > SPREAD_CAP and (worst is None or sp > worst[0]):
                worst = (sp, cat, lv, ns)
        if not worst:
            break
        sp, cat, lv, ns = worst
        top = max(ns, key=lambda n: perf.get(n, 0.0))
        g = (items[top]["cat"], items[top]["src"], items[top]["grade"])
        lo, hi = bands.get(g, [lv, lv])
        if newlv[top] + 1 <= hi:
            newlv[top] += 1
            moves += 1
            continue
        bot = min(ns, key=lambda n: perf.get(n, 0.0))
        g = (items[bot]["cat"], items[bot]["src"], items[bot]["grade"])
        lo, hi = bands.get(g, [lv, lv])
        if newlv[bot] - 1 >= lo:
            newlv[bot] -= 1
            moves += 1
            continue
        break

    # ── 보고 ────────────────────────────────────────────────────────────────
    changed = [(n, items[n]["lv"], newlv[n]) for n in items if newlv[n] != items[n]["lv"]]
    print(f"레벨 변경 {len(changed)}종 / 전체 {len(items)}종 · 충돌완화 이동 {moves}회\n")

    def hist(getlv, cats, lo, hi, label):
        h = collections.Counter()
        for n, v in items.items():
            if v["cat"] in cats and v["src"] not in FREEZE_SRC and not v["src"].startswith("히든"):
                h[getlv(n)] += 1
        print(f"  {label}")
        line = ""
        for lv in range(lo, hi + 1):
            c = h.get(lv, 0)
            line += f"{lv:>3}:{'█' * c if c else '·':<6}"
            if (lv - lo + 1) % 8 == 0:
                print("   " + line); line = ""
        if line:
            print("   " + line)
        empty = sum(1 for lv in range(lo, hi + 1) if h.get(lv, 0) == 0)
        print(f"   빈 레벨 {empty} / {hi - lo + 1}")

    print("★ 부품 5종 레벨 분포 (정상 입수분)")
    hist(lambda n: items[n]["lv"], PARTS, 1, 60, "이전")
    hist(lambda n: newlv[n],      PARTS, 1, 60, "이후")

    print("\n★ 변경 상위 (이동 폭 큰 순)")
    for n, a, b in sorted(changed, key=lambda x: -abs(x[2] - x[1]))[:20]:
        print(f"   {n:20s} {items[n]['cat']:4s} {items[n]['src']:10s} Lv{a} → Lv{b}  ({b-a:+d})")

    if not apply_:
        print("\n[dry-run] --apply 로 실제 반영")
        return

    shutil.copy(os.path.join(src_dir, "parts.json"),
                os.path.join(src_dir, "parts.json.bak-levelspread"))
    for cat, d in P["parts"].items():
        for n in list(d):
            f = d[n].split("|")
            f[5] = str(newlv[n])
            d[n] = "|".join(f)
    json.dump(P, open(os.path.join(src_dir, "parts.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n✅ parts.json 반영 {len(changed)}종 (백업 parts.json.bak-levelspread)")
    print("★다음: patch_cast_cost.py 재실행 필수 (레벨이 바뀌면 구간 시급이 바뀌어 목표 캐스트가 바뀐다)")


if __name__ == "__main__":
    main()
