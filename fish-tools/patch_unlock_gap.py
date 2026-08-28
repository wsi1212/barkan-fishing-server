#!/usr/bin/env python3
"""해금 경로가 없는 레시피를 찾아 고친다 — «잠겨 있는데 파는 데가 없는» 상태 제거.

★규칙(생성기 주석의 설계 의도 그대로)
    상점 NPC 가 있는 마을(스폰=클라우스, 사막=파리드) → locked=true, 그 상점에서 레시피 구매로 해금
    상점이 없는 곳(상단·왕도·히든·심해)             → locked=false, 그 마을 대장간에서 바로 제작

★무엇이 깨져 있었나 (2026-08-28 실측 75종)
  locked 판정이 recipes.json 의 «village» 만 봤다. 그런데 **출처(parts.json 7번째 필드)가
  히든-*/심해면 마을 상점에 아예 안 오른다** — village 는 스폰인데 상점엔 없는 조합이 생긴다.
  그 결과 「locked=true 인데 파는 데가 없는」 레시피가 75종 나왔다:
      S급 장비 52종(릴·줄·바늘·찌·미끼 각 10 + 낚싯대 2) · A급 낚싯대 18종 · 채집 계열 5종
  조합대는 해금된 것만 보여 주므로(CraftingGui.visibleRecipes) 이건 **영구 미획득**이다.
  종결 유저가 쓸 S 장비가 통째로 없는 상태였는데 아무 에러도 안 났다.

★고치는 방식 두 가지
  ① 출처가 히든-*/심해 → locked=false (상점이 없는 게 설계다. 작살 S 5종은 이미 이랬다 —
     그게 의도의 증거다. 부품·낚싯대만 규칙이 어긋나 있었다.)
  ② 그 외(=상점 있는 마을 출처인데 목록 누락) → 그 마을 상점 shopItems 에 추가.
"""
import json, os, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "ops", "blockship-data")
NO_SHOP_ORIGINS = ("히든", "심해", "왕도", "상단마을")
VILLAGE_SHOP = {"스폰마을": "클라우스", "사막마을": "파리드"}


def main():
    R = json.load(open(os.path.join(BASE, "recipes.json"), encoding="utf-8"))
    P = json.load(open(os.path.join(BASE, "parts.json"), encoding="utf-8"))["parts"]
    N = json.load(open(os.path.join(BASE, "npc.json"), encoding="utf-8"))
    npcs = N.get("npcs", N)
    recs, cats = R["recipes"], R["categories"]

    origin, grade = {}, {}
    for t, items in P.items():
        for n, line in items.items():
            f = line.split("|")
            grade[n] = f[1]
            origin[n] = f[6] if len(f) > 6 else ""

    sold = set()
    for v in npcs.values():
        if isinstance(v, dict):
            for i in (v.get("shopItems") or []):
                sold.add(i if isinstance(i, str) else i.get("name"))

    unlocked_n = collections.Counter()
    shop_add = collections.defaultdict(list)
    for cat in ("부품", "낚싯대", "작살"):
        for rid in cats.get(cat, []):
            r = recs[rid]
            n = r.get("resultPartName") or r.get("rodPartName")
            if not n or n not in origin or not r.get("locked") or n in sold:
                continue
            src = origin[n]
            if src.startswith(NO_SHOP_ORIGINS):
                r["locked"] = False                       # ① 상점이 없는 층 = 바로 제작
                unlocked_n[(cat, grade[n], src)] += 1
            else:
                shop = VILLAGE_SHOP.get(src)
                if shop is None or shop not in npcs:
                    print(f"🔴 {n}: 출처 «{src}» 에 대응하는 상점을 모른다 — 수동 확인 필요")
                    sys.exit(1)
                shop_add[shop].append(n)                  # ② 상점 목록 누락 보충

    for shop, names in shop_add.items():
        lst = npcs[shop].setdefault("shopItems", [])
        for n in names:
            if n not in lst:
                lst.append(n)

    json.dump(R, open(os.path.join(BASE, "recipes.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump(N, open(os.path.join(BASE, "npc.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print("① locked=false 로 연 것 (상점이 없는 층)")
    for k in sorted(unlocked_n):
        print(f"   {k[0]:<5} {k[1]}급 · 출처 {k[2]:<12} {unlocked_n[k]:>3}종")
    print(f"   합계 {sum(unlocked_n.values())}종")
    print("② 상점 목록에 보충한 것")
    for shop, names in shop_add.items():
        print(f"   {shop}: {len(names)}종 — {names}")

    # ── 검산: 해금 경로 없는 레시피가 0 이어야 한다 ──
    sold |= {n for names in shop_add.values() for n in names}
    left = [(cat, recs[rid].get("resultPartName") or recs[rid].get("rodPartName"))
            for cat in ("부품", "낚싯대", "작살") for rid in cats.get(cat, [])
            if recs[rid].get("locked")
            and (recs[rid].get("resultPartName") or recs[rid].get("rodPartName")) not in sold]
    if left:
        for c, n in left[:10]:
            print(f"🔴 여전히 해금 불가: [{c}] {n}")
        sys.exit(1)
    print("\n🟢 해금 경로 없는 레시피 0종")


if __name__ == "__main__":
    main()
