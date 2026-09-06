#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""마을 상점에서 «남의 마을 출처» 품목을 걷어낸다 (유저 지적 2026-09-07).

라인하르트(왕도)가 스폰마을 출처 저티어 70종(Lv1~19)을 팔고 있었다. 두 가지가 문제다:
  ① 왕도는 Lv52+ 도시인데 Lv1 짜리가 목록의 앞자리를 차지한다.
  ② openRestricted 는 페이지네이션이 없고 «전체» 탭이 36칸에서 잘린다. 정렬이
     카테고리→등급→레벨이라 **저티어 스폰 품목이 앞을 다 먹고 왕도 품목은 전체 탭에서
     한 개도 안 보인다.** 유저가 사자 릴을 못 찾은 이유가 여기 있다.

안전 조건: 빼는 품목이 담당 상점(클라우스)에도 있어야 한다. 한 곳에만 있으면 빼지 않는다.
★출처 «대장간» 은 마을 소속이 아니다(강철 작살=클라우스 · 다이아 작살=라인하르트) — 유지.
"""
import json, shutil, sys, datetime, collections

SHOP = {"스폰마을": "클라우스", "사막마을": "파리드", "상단마을": "니콜로", "왕도": "라인하르트"}
NEUTRAL = ("대장간",)

pp, np_, mode = sys.argv[1], sys.argv[2], sys.argv[3]
P = json.load(open(pp, encoding="utf-8"))["parts"]
NJ = json.load(open(np_, encoding="utf-8")); N = NJ.get("npcs", NJ)
org, gr, lvl, cat = {}, {}, {}, {}
for t, items in P.items():
    for n, line in items.items():
        f = line.split("|")
        org[n] = f[6] if len(f) > 6 else ""; gr[n] = f[1]; lvl[n] = int(f[5]); cat[n] = t

owner = {v: k for k, v in SHOP.items()}     # 상점 → 담당 출처
removed, kept = collections.defaultdict(list), []
for shop, home in owner.items():
    if shop not in N: continue
    lst = N[shop].get("shopItems") or []
    keep = []
    for n in lst:
        o = org.get(n, "")
        if o == home or o in NEUTRAL or o not in SHOP:
            keep.append(n); continue
        dest = SHOP[o]
        if n in (N.get(dest, {}).get("shopItems") or []):
            removed[shop].append((n, o, gr[n], lvl[n], dest))
        else:
            keep.append(n); kept.append((shop, n, o, dest))
    N[shop]["shopItems"] = keep

print("■ 제거 (담당 상점에 이미 있는 것만)")
for shop, rows in removed.items():
    print(f"   {shop}: -{len(rows)}종 → {len(N[shop]['shopItems'])}종  (출처 " +
          ", ".join(f"{k} {v}" for k, v in collections.Counter(r[1] for r in rows).items()) + ")")
    print(f"      레벨대 Lv{min(r[3] for r in rows)}~Lv{max(r[3] for r in rows)} · 전부 {rows[0][4]} 판매 확인")
if kept:
    print("\n■ 남겨 둠 (담당 상점에 없어 빼면 획득 불가)")
    for shop, n, o, dest in kept: print(f"   {shop}: {n} (출처 {o} · {dest} 미판매)")

print("\n■ 결과 탭 구성 (탭당 36칸)")
for shop in ("클라우스", "파리드", "니콜로", "라인하르트"):
    si = N[shop]["shopItems"]
    c = collections.Counter(cat.get(x, "?") for x in si)
    warn = "🔴 초과" if any(v > 36 for v in c.values()) else "✅"
    print(f"   {shop:<8} {len(si):>3}종 {warn} | " + " · ".join(f"{k} {v}" for k, v in sorted(c.items(), key=lambda x: -x[1])))

if mode != "--write":
    print("\n(드라이런)")
else:
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(np_, f"{np_}.bak-shoppurity-{ts}")
    json.dump(NJ, open(np_, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.load(open(np_, encoding="utf-8"))
    print(f"\n✅ 기록 (백업 .bak-shoppurity-{ts})")
