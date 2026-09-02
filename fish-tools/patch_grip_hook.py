#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_grip_hook.py — 「등급 올라갔는데 자루 요구량이 줄었다」를 고친다.

## 왜 (2026-09-02 유저 결정)
prod 실측: D Lv9 채집용이 자루 3, C Lv17 수집가가 자루 2 — 등급이 올라갔는데 줄었다.
반대로 갈고리는 A급에서 10~25 까지 치솟는다. 그런데 **낡은갈고리는 부두(Lv1) 6% 단일
출처**다(materials.json 실측 · MaterialLoader:358). Lv65 장비를 만들려고 튜토 지역으로
되돌아가 833포획을 해야 하는 구조다.

## 스왑이 원가 중립인 이유 (이게 이 스크립트의 근거다)
  정제된갈고리 1 = 낡은갈고리 2 @ 6%  → 33.3포획
  단단한 자루   1 = 강화실   2 @ 6%  → 33.3포획  (+ 물고기비늘 3 @10% = 30포획)
둘 다 6% 재료를 2개 먹는다. 그래서 갈고리 1 → 자루 1 스왑은 **병목 포획수를 유지**하면서
요구를 «부두 전용»에서 «전 지역 공통»으로 옮긴다. 개수만 바꾸는 게 아니라 접근성이 바뀐다.

## 규칙
① Lv≤EARLY 는 손대지 않는다 — 「5렙까지는 완전 초반이라 자루 빼라」(유저, 09-02).
② 자루 하한 사다리 = 1 + Lv//5 (레벨 단조). 이미 그보다 많으면 그대로 둔다(내리지 않는다).
③ 갈고리 상한 HOOK_CAP. 초과분은 **자루로 1:1 전환**(원가 중립).
④ ②로 자루를 더 올려야 하는데 ③이 못 채우면, 갈고리를 HOOK_FLOOR 까지 더 쓰고,
   그다음엔 «직접 강화실 2 · 물고기비늘 3»을 빼서 낸다(자루가 그걸 가져가므로 총량 동일).
   그래도 못 내면 자루 목표를 그만큼 내린다 — 원가를 올리지 않는 게 우선이다.
⑤ ④까지 해도 «등급 하한»(GRADE_FLOOR)에 못 미치면, **병목이 안 올라가는 한** 공짜로
   올린다. 자루가 그 장비의 병목이 아니면 개수를 늘려도 완성 시각이 안 변한다(포획 한 번에
   전 재료가 같이 굴려지므로 지표는 합이 아니라 최댓값이다). 그래도 병목이 오르면 멈춘다.
★수량 산식을 손으로 적지 않는다. 드롭률·중간재 레시피가 바뀌면 다시 돌리면 된다.

사용:  python3 patch_grip_hook.py [--hook-cap 10] [--apply]
"""
import argparse
import importlib.util
import json
import pathlib

LIVE = pathlib.Path(
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
REPO = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = pathlib.Path.home() / "development" / "blockship-plugin"
CPH = 190.1
EARLY = 5
HOOK_FLOOR = 1
#: 등급별 자루 하한 — 「등급 올라갔는데 자루가 줄었다」를 막는 최종 방어선(유저 09-02).
#  값은 적용 후 각 등급의 «중위»에서 뽑았다(D1·C3·B5·A12·S64) — 손으로 정한 수가 아니다.
GRADE_FLOOR = {"D": 1, "C": 3, "B": 5, "A": 8, "S": 14}
#: ⑤에서 허용할 병목 상승폭 — 이걸 넘으면 하한을 포기한다.
FREE_TOL = 0.02
GRIP, HOOK = "단단한자루", "정제된갈고리"


def _ru():
    f = REPO / ".claude/skills/balance-audit/scripts/region_unlock.py"
    spec = importlib.util.spec_from_file_location("region_unlock", f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hook-cap", type=int, default=10)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    RU = _ru()

    rec_p = LIVE / "recipes.json"
    root = json.loads(rec_p.read_text(encoding="utf-8"))
    recs = root["recipes"]
    parts = json.loads((LIVE / "parts.json").read_text(encoding="utf-8"))["parts"]
    drops = json.loads((LIVE / "materials.json").read_text(encoding="utf-8"))["dropTables"]

    meta = {}
    for grp in parts.values():
        for n, v in grp.items():
            f = v.split("|")
            if len(f) >= 6:
                meta[n] = (f[1], int(f[5]) if f[5].isdigit() else 99)

    inter = {}
    for rid, r in recs.items():
        if r.get("category") != "재료":
            continue
        out = None
        for ln in (r.get("result") or {}).get("lore") or []:
            if ln.startswith("&8mat:"):
                out = ln.split(":", 1)[1].strip()
        if out:
            inter[out] = {(i.get("typeOrMatId") or i.get("mcItem")): i.get("qty", 1)
                          for i in r.get("ingredients") or []}

    def expand(d, depth=0):
        out = {}
        for m, q in d.items():
            if m in inter and depth < 4:
                for k, v in expand(inter[m], depth + 1).items():
                    out[k] = out.get(k, 0) + q * v
            else:
                out[m] = out.get(m, 0) + q
        return out

    def rate(m, lv):
        b = 0.0
        for rg, ds in drops.items():
            if RU.unlock_level(rg) > lv:
                continue
            for d in ds:
                if d["matId"] == m:
                    b = max(b, d["chance"] / 100)
        return b or None

    def cost(d, lv):
        w = 0.0
        for m, q in expand(d).items():
            c = rate(m, lv)
            if c:
                w = max(w, q / c)
        return w

    changed, skipped = [], []
    for rid, v in recs.items():
        if v.get("category") not in ("낚싯대", "작살"):
            continue
        nm = v.get("rodPartName") or v.get("resultPartName") or v.get("displayName")
        if nm not in meta:
            continue
        g, lv = meta[nm]
        if lv <= EARLY:
            continue
        q = {(i.get("typeOrMatId") or i.get("mcItem")): i.get("qty", 1)
             for i in v["ingredients"]}
        before = dict(q)
        grip, hook = q.get(GRIP, 0), q.get(HOOK, 0)

        # ③ 갈고리 상한 초과분 → 자루 (1:1, 원가 중립)
        excess = max(0, hook - a.hook_cap)
        grip_t = grip + excess
        hook_n = hook - excess
        # ② 자루 하한 사다리
        need = max(0, (1 + lv // 5) - grip_t)
        if need:
            take = min(need, max(0, hook_n - HOOK_FLOOR))
            hook_n -= take
            grip_t += take
            need -= take
        # ④ 직접 강화실/비늘에서 낸다
        while need > 0:
            if q.get("강화실", 0) >= 2 and q.get("물고기비늘", 0) >= 3:
                q["강화실"] -= 2
                q["물고기비늘"] -= 3
            elif q.get("강화실", 0) >= 2:
                q["강화실"] -= 2
            elif q.get("물고기비늘", 0) >= 3:
                q["물고기비늘"] -= 3
            else:
                break                      # 낼 게 없다 → 자루 목표를 포기한다
            grip_t += 1
            need -= 1
        # ⑤ 등급 하한 — 병목이 안 오르는 범위에서만 공짜로 채운다
        floor = GRADE_FLOOR.get(g, 0)
        if grip_t < floor:
            probe = dict(q)
            probe[HOOK] = hook_n
            probe[GRIP] = grip_t
            base_cost = cost(probe, lv)
            while grip_t < floor:
                probe[GRIP] = grip_t + 1
                if base_cost and cost(probe, lv) > base_cost * (1 + FREE_TOL):
                    break
                grip_t += 1

        if grip_t == grip and hook_n == hook:
            skipped.append((v["category"], lv, g, nm, grip, hook))
            continue
        if grip_t:
            q[GRIP] = grip_t
        if hook_n:
            q[HOOK] = hook_n
        elif HOOK in q:
            del q[HOOK]
        q = {m: n for m, n in q.items() if n > 0}

        # 재료 목록 재구성 — 기존 항목의 mcItem/type 을 그대로 보존한다(추측 금지)
        base = {(i.get("typeOrMatId") or i.get("mcItem")): i for i in v["ingredients"]}
        ings = []
        for m, n in q.items():
            src = base.get(m)
            if src is None:                # 새로 생긴 재료는 없다(자루·갈고리는 원래 있던 것)
                continue
            ings.append(dict(src, qty=n))
        v["ingredients"] = ings
        changed.append((v["category"], lv, g, nm, before, dict(q),
                        cost(before, lv), cost(q, lv)))

    changed.sort(key=lambda t: (t[0], t[1]))
    for cat in ("낚싯대", "작살"):
        sub = [c for c in changed if c[0] == cat]
        if not sub:
            continue
        print(f"\n═══ {cat} {len(sub)}종 변경 (갈고리 상한 {a.hook_cap}) ═══")
        for _, lv, g, nm, b, af, cb, ca in sub:
            d = (ca - cb) / cb * 100 if cb else 0
            print(f"  {g} Lv{lv:<3}{nm:<20} 갈고리 {b.get(HOOK,0):>2}→{af.get(HOOK,0):<2} "
                  f"자루 {b.get(GRIP,0):>2}→{af.get(GRIP,0):<2}  "
                  f"{cb:>5.0f}→{ca:>5.0f}포획 ({d:+.0f}%)")
    print(f"\n변경 {len(changed)}종 · 유지 {len(skipped)}종")
    tot_b = sum(c[6] for c in changed)
    tot_a = sum(c[7] for c in changed)
    print(f"변경분 합계 원가 {tot_b:.0f} → {tot_a:.0f}포획 ({(tot_a-tot_b)/tot_b*100:+.1f}%)")
    if not a.apply:
        print("(--apply 를 붙이면 실제로 씀)")
        return 0
    blob = json.dumps(root, ensure_ascii=False, indent=2) + "\n"
    for t in (rec_p, REPO / "ops/blockship-data/recipes.json", PLUGIN / "recipes.json"):
        if t.parent.exists():
            t.write_text(blob, encoding="utf-8")
            print(f"  ✓ {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
