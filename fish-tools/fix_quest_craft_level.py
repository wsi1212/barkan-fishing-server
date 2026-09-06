#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""craft 목표 퀘스트의 필요레벨을 «만들라는 아이템의 레벨제한» 이상으로 맞춘다.

퀘스트를 받을 수 있는데 정작 CraftingManager.blockedByLevel 이 제작을 막는 구간이 생긴다.
영구 차단은 아니지만(레벨 올리면 풀린다) 퀘스트를 받아 놓고 못 만드는 창이 열린다.
"""
import json, shutil, sys, datetime

qp, pp, mode = sys.argv[1], sys.argv[2], sys.argv[3]
Q = json.load(open(qp, encoding="utf-8")); QQ = Q["퀘스트"]
P = json.load(open(pp, encoding="utf-8"))["parts"]
lv = {n: int(l.split("|")[5]) for t, i in P.items() for n, l in i.items()}
rows = []
for qid, q in QQ.items():
    need = q.get("필요레벨")
    if not need: continue
    for g in q.get("목표", []):
        if not (isinstance(g, str) and g.startswith("craft|")): continue
        nm = g.split("|")[1].replace("_", " ")
        if nm not in lv or lv[nm] <= need: continue
        rows.append((qid, nm, need, lv[nm], q.get("이름", "")))
        q["필요레벨"] = lv[nm]
print(f"■ craft 목표 ↔ 아이템 레벨 불일치 {len(rows)}건")
for qid, nm, old, new, name in rows:
    print(f"   {qid:<9} {nm:<10} 필요레벨 {old} → {new}   {name}")
if mode != "--write": print("\n(드라이런)")
else:
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(qp, f"{qp}.bak-craftlv-{ts}")
    json.dump(Q, open(qp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.load(open(qp, encoding="utf-8"))
    print(f"\n✅ 기록 (백업 .bak-craftlv-{ts})")
