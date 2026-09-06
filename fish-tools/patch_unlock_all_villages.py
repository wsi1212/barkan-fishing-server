#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""장비 획득 경로 정규화 — «레시피는 사서 만든다» 규칙을 전 마을 장비에 적용.

★유저 확정 규칙(2026-09-07): "레시피 구매 없이 바로 제작 가능한 건 튜토리얼 말고는 없다."
  → patch_unlock_gap.py 가 쓰던 «출처 왕도·상단·히든·심해 = 상점 없는 층이니 locked=false»
    라는 전제를 폐기한다. 마을 출처 장비는 전부 locked=true + 담당 상점 판매.

건드리는 것 : 출처 ∈ {스폰마을, 사막마을, 상단마을, 왕도}
건드리지 않는 것:
  · 히든-*      발견(보물상자·도감)이 해금 경로 — 원래 상점에 안 판다
  · 튜토        규칙의 명시적 예외
  · 잠수상점    잠수 포인트 전용 통화 (PartShopGui.isAfkExclusive 가 일반상점에서 항상 제외)
  · 심해·대장간 담당 상점 NPC 가 없다 → 잠그면 획득 불가가 된다. 별도 판단 필요(리포트에 표시)

세 가지를 맞춘다:
  ① locked=true            (구매로만 해금)
  ② 담당 상점 shopItems 등록 (스폰=클라우스 · 사막=파리드 · 상단=니콜로 · 왕도=라인하르트)
  ③ village = 출처의 마을    (씨앗 레시피에서 물려받은 오염 교정 — 사자 릴이 그 사례)
"""
import json, shutil, sys, datetime, collections

SHOP = {"스폰마을": "클라우스", "사막마을": "파리드", "상단마을": "니콜로", "왕도": "라인하르트"}
VILLAGE = {"스폰마을": "스폰", "사막마을": "사막", "상단마을": "상단", "왕도": "왕도"}
UNTOUCHED_PREFIX = ("히든",)
UNTOUCHED = ("튜토", "잠수상점", "심해", "대장간", "캐시", "개발자", "공용")
GRADE_RANK = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4, "S": 5}

rp, pp, np_, mode = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
R = json.load(open(rp, encoding="utf-8"))
P = json.load(open(pp, encoding="utf-8"))["parts"]
NJ = json.load(open(np_, encoding="utf-8")); N = NJ.get("npcs", NJ)

cat_of, org, grade, price = {}, {}, {}, {}
for t, items in P.items():
    for n, line in items.items():
        f = line.split("|")
        cat_of[n], grade[n], price[n] = t, f[1], int(f[2])
        org[n] = f[6] if len(f) > 6 else ""

def shop_blocked(n):
    """openRestricted 가 목록에 실려도 걷어내는 조건 — 여기 걸리면 상점 등록이 무의미하다."""
    t = cat_of.get(n)
    if t is None: return "카테고리없음"
    if org[n] == "잠수상점": return "잠수전용"
    if price[n] <= 0: return "가격0"
    if t == "낚싯대" and org[n].startswith("히든"): return "히든낚싯대"
    r = GRADE_RANK.get(grade[n], 9)
    if r > 5: return "G이상"
    if r == 5 and org[n] not in SHOP: return "마을밖S"
    return None

sold = {k: (v.get("shopItems") or []) for k, v in N.items() if isinstance(v, dict)}
allsold = set(x for v in sold.values() for x in v)

lock_fix, shop_fix, vil_fix, skipped = [], [], [], []
for rid, r in R["recipes"].items():
    if r.get("resultMode") not in ("part", "rod"): continue
    n = r.get("resultPartName") or r.get("rodPartName")
    if not n or n not in org: continue
    o = org[n]
    if o.startswith(UNTOUCHED_PREFIX) or o in UNTOUCHED:
        if not r.get("locked"):
            skipped.append((rid, n, o, grade[n], "locked=false 유지(담당 상점 없음)"))
        continue
    if o not in SHOP: continue
    # ★팔 수 없는 것은 잠그지 않는다 — 잠그면 획득 경로가 0 이 된다.
    #   초보자 4종+초보자 낚싯대(가격 0, 조합 전용 입문)가 여기 걸린다. 유저 규칙의 «튜토리얼 예외».
    blk = shop_blocked(n)
    if blk and n not in allsold:
        skipped.append((rid, n, o, grade[n], f"상점 노출 불가({blk}) → locked 그대로 {r.get('locked')}"))
        continue
    if not r.get("locked"):
        lock_fix.append((rid, n, o, grade[n])); r["locked"] = True
    want = VILLAGE[o]
    if r.get("village") != want:
        vil_fix.append((rid, n, o, r.get("village"), want)); r["village"] = want
    if n not in allsold:
        shop_fix.append((SHOP[o], n, grade[n], rid)); sold[SHOP[o]].append(n); allsold.add(n)

def head(t): print("\n" + t)
head(f"① locked=false → true : {len(lock_fix)}종  (구매 없이 제작되던 것)")
for o in ("스폰마을", "사막마을", "상단마을", "왕도"):
    g = [x for x in lock_fix if x[2] == o]
    if g: print(f"   {o}: {len(g)}종 — " + ", ".join(f"{x[1]}({x[3]})" for x in g[:8]) + (" …" if len(g) > 8 else ""))
head(f"② 상점 등록 : {len(shop_fix)}종")
for s, k in collections.Counter(x[0] for x in shop_fix).items():
    print(f"   {s}: +{k}종 → {len(sold[s])}종")
head(f"③ village 교정 : {len(vil_fix)}종")
for o in ("스폰마을", "사막마을", "상단마을", "왕도"):
    g = [x for x in vil_fix if x[2] == o]
    if g: print(f"   출처 {o}: {len(g)}종  {sorted(set(x[3] for x in g))} → {VILLAGE[o]!r}")
head(f"⚠ 손대지 않음 : {len(skipped)}종")
for rid, n, o, gr, why in sorted(skipped, key=lambda x: (x[2], x[1])):
    print(f"   {rid:<6} {n:<16} {gr}급 출처{o:<8} {why}")

if mode != "--write":
    print("\n(드라이런 — --write 로 반영)")
else:
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    for k, v in sold.items():
        if isinstance(N.get(k), dict): N[k]["shopItems"] = v
    for path, obj in ((rp, R), (np_, NJ)):
        shutil.copy2(path, f"{path}.bak-unlockall-{ts}")
        json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        json.load(open(path, encoding="utf-8"))
    print(f"\n✅ 기록 (백업 .bak-unlockall-{ts})")
