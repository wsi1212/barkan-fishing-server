#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D등급 계열 구멍 메우기 + 초반 접근 불가 재료 교체 (2026-08-27).

유저 지시: "고쳐줘봐 ㅇㅇ" / "모든부품 다 제작하는걸로 하자 최저사양도 레시피가되도록"

────────────────────────────────────────────────────────────────────────────
① D급에 계열이 3개뿐이었다
────────────────────────────────────────────────────────────────────────────
D급 부품은 5슬롯 **전부** 「숙련 · 행운 · 채집」 3계열만 있었다. 성장 · 상인 계열
부품은 C급(Lv16~19)부터다. 낚싯대는 D 에 6계열이 다 있는데 부품이 3계열이라
**초반에는 라인 빌드가 구조적으로 불가능**했다. 특히 경험치(성장)는 레벨링이 유일한
병목인 Lv1~15 구간에 가장 필요한데 부품이 Lv16~17 에 있어 정확히 거꾸로였다.

⇒ 성장 · 상인 계열 D 부품 **10종 신설**(5슬롯 × 2계열). 크리는 바늘 주스탯이 이미
  크리배율·크리확률이고 크기는 크리형 낚싯대가 주므로 D 에서 빌드가 성립한다 — 제외.

레벨 배치는 «세트 해금»으로 읽히게 맞췄다:
    Lv3  숙련·성장 낚싯대 (튼튼한 막대기 · 수련생 낚싯대)
    Lv4  **성장 부품 5종** ← 신설
    Lv6  상인 낚싯대 + **상인 부품 5종** ← 신설

────────────────────────────────────────────────────────────────────────────
② 최저사양도 레시피로 (유저 확정)
────────────────────────────────────────────────────────────────────────────
구 규칙은 `PartShopGui.isRecipeSale` 의 «종류마다 최저사양 1개만 돈, 나머지 레시피»였다.
릴·줄·바늘·찌를 **전부 레시피 판매**로 바꾼다(미끼는 소모품이라 그대로 돈 · 낚싯대는
이미 레시피 경로).
★안전 확인: E·D 최저사양 부품 전부 이미 레시피가 있고 재료도 초반것이다
  (초보자 릴 = 녹슨 부품×2 + 물고기 비늘×1 등). 데이터 공백 없음.

────────────────────────────────────────────────────────────────────────────
③ ★일부 D급 레시피가 «실질 20시간» 재료를 요구했다
────────────────────────────────────────────────────────────────────────────
유저 판단: "D등급 이하여도 채집같은거는 거대비늘처럼 좀 멀리있는거 써도 되긴 함. 안말림"

⇒ 기준은 «가까운가»가 아니라 **실제로 도달하는가**다. 판정은 실측 지역 분포 × 드랍률로
  «재료 1개 기대 캐스트»를 내고, 아이템 하나 분량의 파밍 시간으로 본다(249.1 캐스트/h).

    실측 지역 분포: 항구 67.2% · 강 18.9% · 협곡 4.3% · 오아시스 4.3% · 늪지대 1.3% ·
                   정상 1.2% · 기억의연못 1.2% · 스폰도시 0.8% · (붉은사막·물보라동굴 0%)

  ✅ 유지 — 실질 파밍 3h 이하
     거대비늘 (협곡 5% + 늪지대 6% → 0.30%/캐스트, ×2 = 2.6h)  ← 채집 라인 테마
     보석     (오아시스 7% → 0.30%/캐스트, ×1 = 1.3h)          ← 상인 라인 테마
     나뭇가지  (오아시스 8% → 0.34%/캐스트, ×4 = 4.7h)          ← 선택 장비라 허용
  🔴 교체 — 출처가 **정상(1.2%) 하나뿐**이라 실질 20시간이 넘는다
     행운의구슬 (정상 5% · 붉은사막 0% → 0.06%/캐스트, ×4 = **26h**)
     안개수정   (정상 8% · 물보라동굴 0% · 폭포뒤동굴 0% → 0.10%/캐스트, ×5 = **20h**)

행운의구슬은 D 행운 계열 **전부**(행운 릴·대형 바늘·행운 찌·행운실·향기나는 미끼)와
`대나무 막대기`·`물때 작살`을 물고 있었다 — **D 행운 라인은 26시간짜리 벽 뒤에 있었다.**
안개수정은 `낚시견습생의 낚싯대`(D 크리형)와 `초보 낚싯대`(E)를 물고 있었다.
둘 다 **초반 전 지역 2%인 별빛진주 / 강·항구 8%인 진주**로 교체한다. 라인 테마 재료
(행운의구슬=행운 · 안개수정=크리)는 **C급 이상에 그대로 남긴다** — 그쪽은 갈 레벨이다.

드랍표 실측 대조 결과:
  · `행운의구슬` = **정상 5% · 붉은사막 5%** 뿐 — 실측 지역 분포(항구 67.2% · 강 18.9% ·
    협곡 4.3% · 오아시스 4.3%)에 **정상이 0%** 다. 아무도 안 간다.
    그런데 D 행운 계열 **전부**(행운 릴 Lv5 · 대형 바늘 Lv6 · 행운 찌 Lv6 · 행운실 Lv7 ·
    향기나는 미끼 Lv7)와 `대나무 막대기`(D 행운형 낚싯대) · `물때 작살`이 이걸 요구했다.
    → **D 행운 라인은 데이터상 존재하지만 실제로는 만들 수 없었다.**
  · `나뭇가지`(오아시스 8%) · `안개수정`(정상 8%) — **E급 `초보 낚싯대`** 가 요구한다.
    튜토 직후 장비가 원거리 재료를 요구하는 셈이고, 이것이 그 아이템의 회수시간이
    스폰마을 최악(13.6h · 재료 31,185원)이었던 이유다.
  ★지역은 레벨 게이트가 아니다(regions.json 레벨제한이 대부분 0). 이동은 가능하지만
    Lv3~7 이 정상·오아시스에서 낚시하면 등급이 높아 미니게임이 성립하지 않는다.
    즉 **소프트 게이트**이고, 실측 분포가 그 결과를 보여 준다.

⇒ D 이하 레시피의 원거리 재료를 초반 재료로 교체. 초반 획득 가능(강·항구·스폰도시):
  `물고기비늘 · 강화실 · 녹슨부품 · 낡은갈고리 · 깃털찌조각 · 진주 · 별빛진주`
  (가공재 `단단한자루`=강화실+물고기비늘 · `정제된갈고리`=낡은갈고리 는 초반 BOM 이라 OK)
  행운의구슬은 **C급 이상 행운 계열에 남긴다** — 그쪽은 그 지역에 갈 레벨이다.

사용:
    python3 patch_d_tier_lines.py <BlockShip 데이터 폴더> [--apply]
"""
import json, os, shutil, sys

DUR = 70            # D급 표준 내구
ORIGIN = "스폰마을"

#: 신규 D 부품 — 슬롯: [(이름, 레벨, 가격, 스탯)]
#  스탯 = 슬롯 주스탯(그 슬롯의 D 수준) + 계열 부스탯 + 행운 2~4
#  ★부스탯 «정규화 가치»를 두 계열에서 맞춘다 — 성장(경험치5×1.00 + 트리플1×2.00 = 7.0) ↔
#    상인(판매5×1.00 + 더블3×1.00 = 8.0). 첫 산출은 성장 8.0 ↔ 상인 5.0 이라 Lv4 성장 부품이
#    Lv6 상인 부품보다 강한 레벨 역전이 났다. 상인이 2레벨 위라 8.0 > 7.0 이 맞다.
#  ★D 판매보너스 5 < C 6 · D 더블 3 < C 5 로 등급 사다리도 지킨다.
NEW_PARTS = {
    "릴": [("수습 릴", 4,  9000, "경험치:12,트리플찬스:1,행운:2"),
            ("장터 릴", 6, 10000, "경험치:7,판매보너스:5,더블찬스:3,행운:2")],
    "줄": [("수습 줄", 4,  9000, "도망감소:5,경험치:5,트리플찬스:1,행운:2"),
            ("장터 줄", 6, 10000, "도망감소:5,판매보너스:5,더블찬스:3,행운:2")],
    "바늘": [("수습 바늘", 4,  9000, "크리배율:2,크리확률:3,경험치:5,트리플찬스:1,행운:2"),
             ("장터 바늘", 6, 10000, "크리배율:2,크리확률:3,판매보너스:5,더블찬스:3,행운:2")],
    "찌": [("수습 찌", 4,  9000, "등급업:2,경험치:5,트리플찬스:1,행운:2"),
            ("장터 찌", 6, 10000, "등급업:2,판매보너스:5,더블찬스:3,행운:2")],
    "미끼": [("수습 미끼", 4,   200, "경험치:5,트리플찬스:1,행운:4"),
             ("장터 미끼", 6,   250, "판매보너스:5,더블찬스:3,행운:4")],
}
#: 계열 테마 재료 — C급과 같은 테마를 쓰되 수량만 D 수준으로 줄인다.
#  성장 = 깃털찌조각(강 5% · 협곡 5%) · 상인 = 보석(오아시스 7% → 1개 ≈ 1.3h, 허용 범위)
LINE_MAT = {
    "수습": ("깃털찌조각", "깃털 찌 조각", "feather", 4),
    "장터": ("보석", "보석", "emerald", 1),
}
BASE_ING = [("정제된갈고리", "정제된 갈고리", "tripwire_hook", 1),
            ("강화실", "강화 실", "string", 4),
            ("물고기비늘", "물고기 비늘", "paper", 6)]

#: 원거리 재료 → 초반 재료 교체. (레시피 대상 이름) → [(구 matId, 신 재료, 신 수량)]
PEARL = ("진주", "진주", "nautilus_shell")
STAR = ("별빛진주", "별빛 진주", "heart_of_the_sea")
GIANT = ("거대비늘", "거대 비늘", "paper")
SWAP = {
    # 행운의구슬 = 정상 5% · 붉은사막 0% → 0.06%/캐스트 (4개 ≈ 26h) → 진주(≈7.3%/캐스트)
    "행운 릴":       [("행운의구슬", PEARL, 4)],
    "대형 바늘":     [("행운의구슬", PEARL, 4)],
    "행운 찌":       [("행운의구슬", PEARL, 4)],
    "행운실":        [("행운의구슬", PEARL, 4)],
    "향기나는 미끼":  [("행운의구슬", PEARL, 4)],
    "대나무 막대기":  [("행운의구슬", PEARL, 5)],
    "물때 작살":     [("행운의구슬", PEARL, 4)],
    # 안개수정 = 정상 8% · 물보라동굴/폭포뒤동굴 0% → 0.10%/캐스트 (5개 ≈ 20h)
    #   → 별빛진주(강·협곡·항구·스폰도시 각 2% → 1.82%/캐스트). 크리 = «희귀한 순간» 테마 유지
    "낚시견습생의 낚싯대": [("안개수정", STAR, 3)],
    "초보 낚싯대":        [("안개수정", STAR, 1)],
    "쇠날 작살":          [("안개수정", STAR, 2)],
    # 산호조각 = 대양 10% · 원양 6% · 상단마을 5% — 실측 대양·원양 0% · 상단마을 0.03%
    #   → 0.0009%/캐스트. D Lv3 작살이 **1,070시간**을 요구하고 있었다.
    "갯벌 작살":          [("산호조각", PEARL, 4)],
    # 거대비늘은 채집 라인 테마라 유지(유저 확정) — 수량만 한도에 맞춰 줄인다
    "채집용 낚싯대":       [("거대비늘", GIANT, 3)],
    "벼린 작살":          [("거대비늘", GIANT, 2)],
}


def canon_ing(mid, disp, mc, qty):
    return {"kind": "custom", "typeOrMatId": mid, "displayName": disp,
            "mcItem": mc, "qty": qty}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src, apply_ = sys.argv[1], "--apply" in sys.argv
    pp, rp = os.path.join(src, "parts.json"), os.path.join(src, "recipes.json")
    P = json.load(open(pp, encoding="utf-8"))
    R = json.load(open(rp, encoding="utf-8"))

    # ═══ 1. 신규 D 부품 ═══
    added, next_id = [], max(int(k[1:]) for k in R["recipes"]
                             if k.startswith("P") and k[1:].isdigit()) + 1
    for slot, rows in NEW_PARTS.items():
        for name, lv, price, stats in rows:
            if name in P["parts"][slot]:
                print(f"  = {slot} {name} 이미 있음 — 건너뜀")
                continue
            P["parts"][slot][name] = "|".join(
                [name, "D", str(price), str(DUR), stats, str(lv), ORIGIN])
            mid, disp, mc, qty = LINE_MAT[name.split()[0]]
            rid = f"P{next_id}"
            next_id += 1
            R["recipes"][rid] = {
                "id": rid, "category": "부품", "displayName": name, "locked": True,
                "resultMode": "part", "drillTier": 0,
                "resultPartType": slot, "resultPartName": name,
                "ingredients": [canon_ing(*BASE_ING[0]), canon_ing(mid, disp, mc, qty),
                                canon_ing(*BASE_ING[1]), canon_ing(*BASE_ING[2])],
                "village": "스폰", "materialDiscountVersion": 1,
            }
            added.append((slot, name, lv, price, stats, rid, f"{disp}×{qty}"))
    print(f"[신규 D 부품] {len(added)}종")
    for slot, name, lv, price, stats, rid, mat in sorted(added, key=lambda x: (x[2], x[0])):
        print(f"  · {slot:<4}Lv{lv} {name:<10}{price:>7,}원  {stats}")
        print(f"       {rid}: 정제된 갈고리×1 + {mat} + 강화 실×4 + 물고기 비늘×6")

    # ═══ 2. 원거리 재료 교체 ═══
    idx = {}
    for rid, r in R["recipes"].items():
        for k in ("resultPartName", "rodPartName"):
            if r.get(k):
                idx[r[k]] = rid
    swapped = []
    for target, rules in SWAP.items():
        rid = idx.get(target)
        if rid is None:
            sys.exit(f"❌ {target} 레시피를 찾지 못했다")
        ing = R["recipes"][rid]["ingredients"]
        for old, (nm, disp, mc), qty in rules:
            hit = [i for i in ing if i["typeOrMatId"] == old]
            if not hit:
                print(f"  = {target}: {old} 없음 — 이미 교체됨")
                continue
            i = hit[0]
            oldq = i["qty"]
            # 같은 재료가 이미 있으면 수량 합산, 없으면 제자리 교체
            same = [x for x in ing if x["typeOrMatId"] == nm and x is not i]
            if same:
                same[0]["qty"] += qty
                ing.remove(i)
            else:
                i.update(typeOrMatId=nm, displayName=disp, mcItem=mc, qty=qty)
            swapped.append((target, old, oldq, disp, qty))
    print(f"\n[재료 교체] {len(swapped)}건 — 원거리 → 초반")
    for t, old, oq, nd, nq in swapped:
        print(f"  · {t:<14}{old}×{oq} → {nd}×{nq}")

    # ═══ 3. 검증 — 재료 획득 기대시간 (실측 지역 분포 × 드랍률) ═══
    dt = json.load(open(os.path.join(src, "materials.json"), encoding="utf-8"))["dropTables"]
    #: 실측 지역 분포(%) — audits/snapshots/2026-08-26-players.raw.json region_mix_pct
    SHARE = {"항구": 67.23, "강": 18.88, "협곡": 4.32, "오아시스": 4.27, "늪지대": 1.29,
             "정상": 1.23, "기억의연못": 1.16, "스폰도시": 0.8, "강_상류": 0.51,
             "폭포": 0.1, "레드_로드": 0.1, "바르칸": 0.05, "상단마을": 0.03}
    CASTS_H = 249.1                      # 실측 캐스트/h
    rate = {}                            # 재료 → 캐스트당 획득 기대개수
    for area, tbl in dt.items():
        w = SHARE.get(area, 0.0) / 100.0
        if w <= 0:
            continue
        for e in tbl:
            rate[e["matId"]] = rate.get(e["matId"], 0.0) + w * e["chance"] / 100.0
    #: 가공재 → 하위 BOM (초반 확인용. 정확한 전개는 material_value.Data.expand 가 권위)
    SUB = {"단단한자루": {"강화실": 12, "물고기비늘": 16},
           "정제된갈고리": {"낡은갈고리": 8},
           "강철심": {"녹슨부품": 8},
           "강화철괴": {"녹슨부품": 4},
           "강화석탄": {"녹슨부품": 3},
           "강화실": {"강화실": 1}}

    def hours(mid, qty):
        """그 재료 qty 개를 모으는 실질 시간(h). 미해결이면 None."""
        if mid in rate:
            return qty / rate[mid] / CASTS_H if rate[mid] > 0 else float("inf")
        if mid in SUB:
            return sum(hours(k, v * qty) or 0 for k, v in SUB[mid].items())
        return None

    idx2 = {}
    for rid, r in R["recipes"].items():
        for k in ("resultPartName", "rodPartName"):
            if r.get(k):
                idx2[r[k]] = r
    #: 허용 파밍 시간. 선은 **채집 라인 테마(거대비늘)를 통과시키는 지점**에 뒀다 —
    #  유저 확정: "D등급 이하여도 채집같은거는 거대비늘처럼 좀 멀리있는거 써도 되긴 함".
    #  거대비늘×2 = 2.7h 가 부품 실측 최대이고, 장비는 재료 종류가 많아(단단한 자루 1.5h 등)
    #  기저가 높다. 이 한도의 역할은 «20h/1,070h 급»을 잡는 것이고 거기엔 여유가 충분하다.
    LIMIT_BY = {"부품": 3.5, "장비": 7.0}
    rows = []
    for slot, items in P["parts"].items():
        for name, raw in items.items():
            f = raw.split("|")
            if f[1] not in ("E", "D"):
                continue
            r = idx2.get(name)
            if not r:
                # 무료 지급품 · 튜토 지급품은 레시피가 없는 게 맞다
                if int(f[2]) == 0 or f[6] in ("튜토", "캐시", "개발자"):
                    continue
                rows.append((f[1], int(f[5]), slot, name, None, "레시피 없음"))
                continue
            worst, tot = None, 0.0
            for i in r["ingredients"]:
                h = hours(i["typeOrMatId"], i["qty"])
                if h is None:
                    continue
                tot += h
                if worst is None or h > worst[1]:
                    worst = (f"{i['displayName']}×{i['qty']}", h)
            lim = LIMIT_BY["장비" if slot in ("낚싯대", "작살") else "부품"]
            rows.append((f[1], int(f[5]), slot, name, tot,
                         f"{worst[0]} {worst[1]:.1f}h" if worst else "—", lim))
    over = [x for x in rows if x[4] is None or x[4] > x[6]]
    print(f"\n[검증] E·D {len(rows)}종 재료 파밍 시간 (실측 지역분포 기준 · "
          f"한도 부품 {LIMIT_BY['부품']}h · 장비 {LIMIT_BY['장비']}h)")
    for g, lv, slot, name, tot, why, lim in sorted(rows, key=lambda x: -(x[4] or 1e9)):
        mark = "🔴" if (tot is None or tot > lim) else "🟢"
        t = "?" if tot is None else f"{tot:.1f}h"
        print(f"  {mark} {g} Lv{lv:<3}{slot:<4}{name:<18}{t:>7}  최악 {why}")
    print(f"  → 한도 초과 {len(over)}종")

    cnt = {s: len(v) for s, v in P["parts"].items()}
    print(f"\n부품 총계 {sum(cnt.values())}종  {cnt}")
    if not apply_:
        print("\n[dry-run] --apply 로 실제 반영")
        return
    for path, data in ((pp, P), (rp, R)):
        shutil.copy(path, path + ".bak-dlines")
        json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n✅ parts.json · recipes.json 반영 (백업 *.bak-dlines)")
    print("   ★jar 도 함께 바뀐다(PartShopGui 최저사양 예외 제거) — 서버 풀 재시작 필수")


if __name__ == "__main__":
    main()
