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
    # ★2026-08-28 종결층 신설분(gen_part_builds --add-only 로 50종). 마을 순서대로 Lv57~70 을
    #   틈 없이 덮는다. 생성기는 그룹마다 3~4 레벨 폭에 10 종을 넣으므로 계단식 흩기가 필요하다.
    ("PARTS", "히든-스폰마을", "S"): (57, 59),
    ("PARTS", "히든-사막마을", "S"): (59, 61),
    ("PARTS", "히든-상단마을", "S"): (61, 63),
    ("PARTS", "심해", "S"): (64, 66),
    ("PARTS", "히든-전설", "S"): (67, 70),
}
#: 낚싯대·작살도 같은 방식으로 편다. 이쪽은 카테고리가 하나뿐이라 «라인» 개념이 없고,
#  그룹 안에서 성능 순으로 현재 밴드에 등간격 배치하면 된다. 밴드는 현재 [min, max].
#  ★대상은 사막(연속 3레벨 이상 공백)이 있는 그룹만 — 멀쩡한 그룹까지 흔들면 손해다.
SOLO_SPREAD = {
    ("낚싯대", "스폰마을", "C"),   # Lv15~17 사막
    ("작살", "사막마을", "B"),     # Lv31~33 사막
    ("낚싯대", "스폰마을", "D"),   # Lv8~9 사막 — D 가 Lv7 에서 끝나고 C 가 Lv10 부터였다
    # ★2026-08-28 종결 사막 — 부품은 Lv57~70 을 채웠는데 낚싯대는 히든 3마을 18종이
    #   Lv57~62(6레벨)에 몰려 Lv64~69 가, 작살은 Lv59~61·64~67 이 비었다. 신규 제작 없이
    #   **있는 것을 조금씩 밀어서** 메운다(유저 지시: "살짝씩 조정해서 매우는 방법으로").
    ("낚싯대", "히든-스폰마을", "A"),
    ("낚싯대", "히든-사막마을", "A"),
    ("낚싯대", "히든-상단마을", "A"),
    ("낚싯대", "히든-전설", "S"),
    ("작살", "왕도", "A"),
    ("작살", "심해", "S"),
    ("작살", "히든-전설", "S"),
}
#: 낚싯대·작살 밴드 덮어쓰기 (SOLO_SPREAD 대상에만 적용).
SOLO_BANDS = {
    # D 낚싯대 6 종이 Lv3~7 에 몰려 있고 C 는 Lv10 부터라 Lv8~9 가 빈다 → 3~9 로 늘린다.
    ("낚싯대", "스폰마을", "D"): (3, 9),
    # ★C 는 밴드를 못 박아야 한다 — 현재 [min,max] 로 잡으면, 한 번 Lv10 을 잃은 뒤로는
    #   min 이 11 이 되어 영영 되찾지 못한다(밴드가 데이터에서 파생되는 구조의 함정).
    ("낚싯대", "스폰마을", "C"): (10, 18),
    # 마을 순서대로 Lv57~67 을 덮고, S 2종이 68·70 을 잡는다(69 는 한 칸 구멍 — 사막 아님).
    ("낚싯대", "히든-스폰마을", "A"): (57, 60),
    ("낚싯대", "히든-사막마을", "A"): (60, 63),
    ("낚싯대", "히든-상단마을", "A"): (64, 67),
    ("낚싯대", "히든-전설", "S"):     (68, 70),
    # 작살: 왕도 5종이 54~61 을 덮고, 심해 3종이 64·66·68, 전설 2종이 62·70.
    # 63·65·67·69 는 한 칸씩 비지만 연속 3레벨이 아니라 사막이 아니다.
    ("작살", "왕도", "A"):     (54, 61),
    ("작살", "심해", "S"):     (64, 68),
    ("작살", "히든-전설", "S"): (62, 70),
}
#: 같은 (카테고리, 레벨) 안에서 허용하는 성능 산포. selftest [9] 와 같은 기준.
SPREAD_CAP = 0.25
#: 산포 검사에서 빼는 레벨 — Lv1 은 «무료 시작 세트»라 사다리가 아니다(밴드도 한 칸이라
#  옮길 데가 없다). 여기 성능이 벌어지는 건 정상이다(나뭇가지 vs 초보 낚싯대).
EXEMPT_LV = {1}
#: 레벨을 옮기지 않는 출처 — 특수 층이라 «사다리»가 아니다.
FREEZE_SRC = {"튜토", "잠수상점", "캐시", "개발자", "대장간"}


def ladder(src):
    """«정상 진행으로 얻는 사다리» 인가. 히든은 사다리지만 잠수상점·캐시는 아니다."""
    return src not in FREEZE_SRC


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
            # ★정렬 키에 «현재 레벨»을 앞세운다 — 이 스크립트를 멱등으로 만들기 위해서다.
            #   perf 는 구간 시급으로 정규화되고 구간은 레벨이 정하므로, 레벨을 옮기면
            #   perf 가 바뀌고 다음 실행에서 티어 순서가 미세하게 뒤집힌다. 그러면 이미
            #   잘 퍼진 배치가 다시 흔들려 없던 구멍이 생긴다(2026-08-28 실측: 빈 레벨 4→6).
            #   최초 실행에서는 라인이 전부 같은 레벨이라 perf 가 순서를 정하고, 이후
            #   재실행에서는 그 결과가 그대로 유지된다.
            tiers[c] = sorted(ns, key=lambda n: (items[n]["lv"], perf.get(n, 0.0), n))
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
                    key=lambda n: (items[n]["lv"], perf.get(n, 0.0), n))
        if not ns:
            continue
        lo, hi = SOLO_BANDS.get(g, tuple(bands[g]))
        bands[g] = [lo, hi]
        for i, n in enumerate(ns):
            newlv[n] = lo if len(ns) == 1 else lo + round(i * (hi - lo) / (len(ns) - 1))

    # ── ③ 동레벨 충돌 완화 ──────────────────────────────────────────────────
    moves = 0
    unfixable, fixed_skip = [], set()
    for _ in range(200):
        bylv = collections.defaultdict(list)
        for n, v in items.items():
            bylv[(v["cat"], newlv[n])].append(n)
        worst = None
        for (cat, lv), ns in bylv.items():
            ps = [perf.get(n, 0.0) for n in ns if perf.get(n, 0.0) > 0]
            if len(ps) < 2:
                continue
            sp = max(ps) / min(ps) - 1
            if lv in EXEMPT_LV or (cat, lv) in fixed_skip:
                continue
            if sp > SPREAD_CAP and (worst is None or sp > worst[0]):
                worst = (sp, cat, lv, ns)
        if not worst:
            break
        sp, cat, lv, ns = worst
        # ★밴드 안 «가장 덜 붐비는 레벨»로 옮긴다. ±1 만 보면 옆칸도 꽉 차 있을 때 막히고,
        #   그 자리에서 loop 를 break 해 나머지 위반까지 통째로 포기하게 된다(2026-08-28:
        #   그래서 «이동 0회» 로 끝나고 미끼 Lv4 +177% 가 그대로 남았다).
        # ★부품은 여기서 옮기지 않는다 — 부품의 목적은 «사막 제거»이고 ① 이 이미 밴드를
        #   빈틈없이 채워 놨다. 산포를 잡겠다고 한 종을 빼면 그 레벨이 비어 사막이 되살아난다
        #   (2026-08-28 실측: 빈 레벨 4 → 6). 부품 5종은 서로 대체재라 같은 레벨에 성능이
        #   좀 벌어져도 «그 레벨에 갈아끼울 게 있다» 가 먼저다. 낚싯대·작살은 각자가 유일한
        #   슬롯이라 반대다 — 같은 레벨에 성능이 벌어지면 한쪽이 그냥 함정 선택지가 된다.
        # ★부품도 이제 옮긴다 — 다만 구멍 벌점(아래 hole)에 전적으로 맡긴다. 통째로 빼면
        #   S 종결층처럼 «밴드 3~4 레벨에 10 종» 이라 밀도가 충분한 구간까지 못 고친다
        #   (2026-08-28: 신규 부품 50종이 들어오자 산포가 2 → 10 건이 됐다).
        #   저티어처럼 그 레벨에 그 종밖에 없으면 hole=1 로 이동이 거부되므로 사막은 안 생긴다.
        done = False
        for pick in sorted(ns, key=lambda n: -perf.get(n, 0.0)):
            g = (items[pick]["cat"], items[pick]["src"], items[pick]["grade"])
            lo, hi = bands.get(g, [lv, lv])
            cand = []
            for L in range(lo, hi + 1):
                if L == newlv[pick]:
                    continue
                peers = [perf.get(m, 0.0) for m, v in items.items()
                         if v["cat"] == cat and newlv[m] == L and m != pick
                         and perf.get(m, 0.0) > 0]
                mine = perf.get(pick, 0.0)
                if mine <= 0:
                    continue
                sp2 = (max(peers + [mine]) / min(peers + [mine]) - 1) if peers else 0.0
                # ★구멍을 만드는 이동에 벌점 — 산포를 잡으려다 사막을 되살리면 본말전도다
                #   (2026-08-28: 초판이 빈 레벨을 4 → 6 으로 늘렸다). «슬롯 가족» 기준으로
                #   센다 — 부품 5종은 서로 대체재라 합산이 끊기지 않으면 되고, 낚싯대·작살은
                #   각자가 유일한 슬롯이라 자기 카테고리로 센다.
                fam = PARTS if items[pick]["cat"] in PARTS else (items[pick]["cat"],)
                # ★«사다리 아닌 출처»는 점유로 세지 않는다 — 사막 판정에서 빼 놓고 여기서만
                #   세면 «그 레벨엔 아직 있다» 는 거짓 판정이 나온다(2026-08-28: 잠수상점
                #   Lv10 낚싯대 때문에 마지막 C 급 낚싯대가 Lv10 을 떠나 Lv8~10 사막이 생겼다.
                #   잠수부의 낚싯대는 포인트로 사는 별도 층이라 사다리를 잇지 않는다).
                src_occ = sum(1 for m, v in items.items()
                              if v["cat"] in fam and newlv[m] == newlv[pick]
                              and ladder(v["src"]))
                hole = 1 if src_occ <= 1 else 0
                cand.append((hole, sp2, abs(L - newlv[pick]), L))
            cand.sort()
            if cand and cand[0][0] == 0 and cand[0][1] < sp - 1e-9:
                newlv[pick] = cand[0][3]
                moves += 1
                done = True
                break
        if not done:
            unfixable.append((cat, lv, sp))
            fixed_skip.add((cat, lv))
            continue

    # ── 보고 ────────────────────────────────────────────────────────────────
    changed = [(n, items[n]["lv"], newlv[n]) for n in items if newlv[n] != items[n]["lv"]]
    print(f"레벨 변경 {len(changed)}종 / 전체 {len(items)}종 · 충돌완화 이동 {moves}회")
    if unfixable:
        print(f"★레벨로 못 푼 동레벨 산포 {len(unfixable)}건 "
              "(부품=사막 우선이라 의도적 보류 / 그 외=스탯 결함):")
        for cat, lv, sp in sorted(unfixable, key=lambda x: -x[2])[:12]:
            print(f"   {cat} Lv{lv} +{sp*100:.0f}%")
    print()

    def hist(getlv, cats, lo, hi, label):
        h = collections.Counter()
        for n, v in items.items():
            # ★히든을 빼면 안 된다 — 종결층 부품이 전부 히든이라 Lv57~70 이 통째로 «빈» 것처럼
            #   보인다(2026-08-28). 표시 기준은 판정 기준(ladder)과 같아야 한다.
            if v["cat"] in cats and ladder(v["src"]):
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
