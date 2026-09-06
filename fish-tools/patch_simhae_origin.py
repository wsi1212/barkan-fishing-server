#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""심해 S급 13종을 상단마을 상점(니콜로) 라인업으로 편입 (유저 지시 2026-09-07).

★왜 출처를 바꾸는가 — 이름이 아니라 «상점 노출 판정» 때문이다.
  PartShopGui.shopCeilingBlocks 는 S 급을 VILLAGE_ORIGINS = {스폰마을,사막마을,상단마을,왕도}
  출처일 때만 상점에 올린다. 출처가 "심해" 인 동안에는 니콜로 shopItems 에 이름을 넣어도
  그리기 직전에 걷어내진다 — 목록에 있는데 안 보이는 상태가 된다.
  코드( VILLAGE_ORIGINS 에 "심해" 추가 )로도 열 수 있지만 jar 배포가 필요해 데이터로 연다.

  대가: 아이템 로어의 «출처» 줄이 "심해" → "상단마을" 로 바뀐다. 이름(심연·심해수정)은 그대로다.
  ★parts.json 을 재생성하는 스크립트가 이 13종의 출처를 «심해» 로 되돌리면 상점에서 다시
    사라진다. 되돌릴 거면 VILLAGE_ORIGINS 쪽을 같이 고칠 것.

locked/상점등록/village 는 건드리지 않는다 — 출처가 상단마을이 된 뒤
patch_unlock_all_villages.py 가 나머지를 규칙대로 처리한다.
"""
import json, shutil, sys, datetime

path, mode = sys.argv[1], sys.argv[2]
OLD, NEW = "심해", "상단마을"
D = json.load(open(path, encoding="utf-8"))
rows = []
for t, items in D["parts"].items():
    for n, line in items.items():
        f = line.split("|")
        if len(f) > 6 and f[6] == OLD:
            f[6] = NEW
            items[n] = "|".join(f)
            rows.append((t, n, f[1], f[5], int(f[2])))
print(f"■ 출처 {OLD!r} → {NEW!r} : {len(rows)}종")
for t, n, g, lv, pr in rows:
    print(f"   {t:<4} {n:<14} {g}급 Lv{lv:<4} {pr:>9,}원")
if mode != "--write":
    print("\n(드라이런)")
else:
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(path, f"{path}.bak-simhae-{ts}")
    json.dump(D, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.load(open(path, encoding="utf-8"))
    print(f"\n✅ 기록 (백업 .bak-simhae-{ts})")
