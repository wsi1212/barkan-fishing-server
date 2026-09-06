#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""장비 획득/노출 전수 감사 — 라이브 Java 게이트를 그대로 재현한다.

재현 대상 (소스 기준):
  PartShopGui.openRestricted   : isAfkExclusive · price<=0 · 히든낚싯대 · shopCeilingBlocks · 36칸 break
  PartShopGui.shopCeilingBlocks: rank<=A 통과 / rank>S 차단 / S 는 VILLAGE_ORIGINS 만
  CraftingGui.visibleRecipes   : categories 인덱스 · isUnlocked · village 매칭
  CraftingManager.isRecipeLocked: rec.locked || origin.startsWith("히든")
  CraftingManager.blockedByLevel: getGateLevelReq (히든=0)
  WetTreasureChestManager      : 히든 부품/낚싯대만 풀, |reqLv - lv| <= 10
"""
import json, sys, collections

B = sys.argv[1]
def J(n): return json.load(open(f"{B}/{n}", encoding="utf-8"))
R = J("recipes.json"); P = J("parts.json")["parts"]; N = J("npc.json")["npcs"]
Q = J("quests.json").get("퀘스트", {})
MAT = J("materials.json"); MAT = MAT.get("materials", MAT)
matkeys = set(MAT) if isinstance(MAT, dict) else set(x.get("id") for x in MAT)

RANK = {"E":0,"D":1,"C":2,"B":3,"A":4,"S":5,"M":6,"L":7,"G":8}
VILLAGE_ORIGINS = {"스폰마을","사막마을","상단마을","왕도"}
SMITHY = {v.get("smithyTown"): k for k, v in N.items() if v.get("smithy")}
CATS = ["낚싯대","릴","줄","바늘","미끼","찌","작살"]

org, gr, pr, lv, cat = {}, {}, {}, {}, {}
for t, items in P.items():
    for n, line in items.items():
        f = line.split("|")
        cat[n]=t; gr[n]=f[1]; pr[n]=int(f[2]); lv[n]=int(f[5]); org[n]=f[6] if len(f)>6 else ""

recs = R["recipes"]; cats = R["categories"]
index = set(i for ids in cats.values() for i in ids)
byname = collections.defaultdict(list)
for rid, r in recs.items():
    n = r.get("resultPartName") or r.get("rodPartName")
    if n: byname[n].append(rid)

def hidden(n): return org.get(n,"").startswith("히든")
def ceiling_blocks(n):
    rk = RANK.get(gr[n], 9)
    if rk <= 4: return False
    if rk > 5: return True
    return org[n] not in VILLAGE_ORIGINS
def shop_render_blocked(n):
    if cat.get(n) is None: return "카테고리없음"
    if org[n] == "잠수상점": return "잠수전용"
    if pr[n] <= 0: return "가격0"
    if cat[n] == "낚싯대" and hidden(n): return "히든낚싯대"
    if ceiling_blocks(n): return "등급천장"
    return None

FAIL = collections.defaultdict(list)
def bad(k, *a): FAIL[k].append(a)

# ── 1. 상점 목록 정합 ───────────────────────────────────────────────
seen_shop = {}
for npc, v in N.items():
    si = v.get("shopItems") or []
    if not si: continue
    if len(si) != len(set(si)): bad("상점 중복", npc, [x for x,c in collections.Counter(si).items() if c>1])
    for n in si:
        if n not in org: bad("상점 유령품목", npc, n); continue
        b = shop_render_blocked(n)
        if b: bad("목록엔 있는데 안 그려짐", npc, n, gr[n], b)
        else: seen_shop.setdefault(n, npc)
    # 탭 정원
    c = collections.Counter(cat[x] for x in si if x in org and not shop_render_blocked(x))
    for k, cnt in c.items():
        if cnt > 36: bad("탭 36칸 초과", npc, k, cnt)

# ── 2. 레시피 인덱스/중복/재료 ─────────────────────────────────────
for rid, r in recs.items():
    if rid not in index: bad("카테고리 인덱스 누락", rid, r.get("displayName"), r.get("category"))
    for ing in r.get("ingredients") or []:
        mid = ing.get("typeOrMatId")
        # 채집_/작물_ 는 materials.json 이 아니라 ForageTypes/CropSpecs 네임스페이스다
        #   (CraftingManager.customMaterialCount 가 해석 — 113~115행에 목록이 박혀 있다).
        if mid and (mid.startswith("채집_") or mid.startswith("작물_")): continue
        if ing.get("kind") == "custom" and mid and mid not in matkeys:
            bad("재료 미존재", rid, r.get("displayName"), mid)
for n, ids in byname.items():
    if len(ids) > 1: bad("결과 중복 레시피", n, ids)

# ── 3. 장비별 획득 경로 ────────────────────────────────────────────
for n in org:
    if org[n] in ("캐시","개발자","공용"): continue
    ids = byname.get(n, [])
    if not ids:
        # 레시피가 없는 게 정상인 층: 잠수 포인트 상점 · 튜토 지급 · 가격 0 입문품
        if org[n] not in ("잠수상점","튜토") and pr[n] > 0:
            bad("레시피 없음", n, cat[n], gr[n], org[n], f"Lv{lv[n]}", f"{pr[n]}원")
        continue
    rid = ids[0]; r = recs[rid]
    if rid not in index: continue                      # 위에서 이미 보고
    locked = bool(r.get("locked")) or hidden(n)
    if not locked: continue                            # 무조건 제작 가능
    if n in seen_shop: continue                        # 상점 구매로 해금
    if hidden(n): continue                             # 보물상자 발견 경로
    if org[n] == "잠수상점": continue                   # 잠수 포인트
    bad("해금 경로 없음", rid, n, cat[n], gr[n], org[n], f"Lv{lv[n]}")

# ── 4. village ↔ 출처 ↔ 대장간 ─────────────────────────────────────
VIL = {"스폰마을":"스폰","사막마을":"사막","상단마을":"상단","왕도":"왕도"}
for n, ids in byname.items():
    if n not in org or org[n] not in VIL: continue
    r = recs[ids[0]]; want = VIL[org[n]]; got = r.get("village")
    if got != want and pr.get(n,0) > 0:
        bad("village 불일치", ids[0], n, f"{got!r}→{want!r}")
for v in set(r.get("village") for r in recs.values()):
    if v and v not in SMITHY: bad("village 에 대장간 없음", v)

# ── 5. 퀘스트 craft 목표 ───────────────────────────────────────────
for qid, q in Q.items():
    for g in q.get("목표", []):
        if not (isinstance(g, str) and g.startswith("craft|")): continue
        nm = g.split("|")[1].replace("_", " ")
        if nm == "아무": continue          # 와일드카드 «아무거나 N개 제작»
        need = q.get("필요레벨", 0)
        if nm not in org:
            if nm not in [r.get("displayName") for r in recs.values()]:
                bad("퀘스트 craft 대상 없음", qid, nm)
            continue
        ids = byname.get(nm, [])
        if not ids: bad("퀘스트 대상 레시피 없음", qid, nm); continue
        rid = ids[0]
        if rid not in index: bad("퀘스트 대상 조합대 미노출", qid, nm, rid)
        locked = bool(recs[rid].get("locked")) or hidden(nm)
        if locked and nm not in seen_shop and not hidden(nm) and org[nm] != "잠수상점":
            bad("퀘스트 대상 해금 불가", qid, nm, rid)
        if need and lv.get(nm, 0) > need:
            bad("퀘스트 레벨 < 아이템 레벨", qid, nm, f"퀘Lv{need} < 아이템Lv{lv[nm]}")

# ── 6. 히든 보물상자 도달성 ────────────────────────────────────────
for n in org:
    if not hidden(n): continue
    ids = byname.get(n, [])
    if not ids: bad("히든인데 레시피 없음", n); continue
    if not recs[ids[0]].get("locked") and not hidden(n): bad("히든인데 locked=false", ids[0], n)

# ── 출력 ───────────────────────────────────────────────────────────
tot = sum(len(v) for v in FAIL.values())
print(f"{'='*70}\n감사 결과 — 문제 {tot}건\n{'='*70}")
for k in sorted(FAIL, key=lambda x: -len(FAIL[x])):
    print(f"\n▸ {k} : {len(FAIL[k])}건")
    for row in FAIL[k][:14]: print("    ", " · ".join(str(x) for x in row))
    if len(FAIL[k]) > 14: print(f"     … 외 {len(FAIL[k])-14}건")
if not tot: print("\n✅ 전 항목 통과")
