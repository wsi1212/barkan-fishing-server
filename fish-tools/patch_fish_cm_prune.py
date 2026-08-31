#!/usr/bin/env python3
"""fish_cm 목표의 «죽은 행» 정리 — fish.json 에 없는 어종을 cm 기준표에서 걷어낸다.

배경(2026-08-31): `fish_cm|아무|C|6|가다랑어=86.9;…` 은 **어종마다 다른 최소 크기**를
요구하는 목표라, 기준표에 어종 전체가 나열된다. 어종을 지우거나 개명해도 이 표는 따라오지
않아서 삭제된 어종 42종이 5개 퀘스트에 죽은 행으로 남아 있었다.

런타임에는 무해하다(그 어종이 안 잡히니 그 행은 영영 안 쓰인다). 문제는 **감사 노이즈**다 —
quest_audit 이 이걸 125건의 ERROR 로 뱉어서, 진짜 진행불가 오류가 그 안에 묻혔다.

★기준 cm 가 maxSize 이상인 «달성 불가» 행은 지우지 않고 **실패로 멈춘다** — 조용히 지우면
  목표가 소리 없이 쉬워진다. 그건 사람이 판단할 일이다.

사용: python3 patch_fish_cm_prune.py [--apply]
"""
import json, sys, pathlib

LIVE = pathlib.Path("/Users/user/Library/Application Support/feather/player-server/servers/"
                    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
REPO = pathlib.Path(__file__).resolve().parent.parent / "ops" / "blockship-data"
PLUGIN = pathlib.Path.home() / "development" / "blockship-plugin"

apply = "--apply" in sys.argv
fish = json.loads((LIVE / "fish.json").read_text(encoding="utf-8"))["fish"]
qpath = LIVE / "quests.json"
root = json.loads(qpath.read_text(encoding="utf-8"))
quests = root["퀘스트"]

dropped, impossible, touched = {}, [], 0
for qid, e in quests.items():
    goals = e.get("목표")
    if not isinstance(goals, list):
        continue
    for i, g in enumerate(goals):
        if not isinstance(g, str) or not g.startswith("fish_cm|"):
            continue
        o = g.split("|")
        if len(o) < 5:
            continue
        keep, gone = [], []
        for ent in o[4].split(";"):
            name, sep, val = ent.rpartition("=")
            if not sep or name not in fish:
                gone.append(name or ent)
                continue
            try:
                if float(val) >= float(fish[name].get("maxSize", 0)):
                    impossible.append((qid, name, val, fish[name].get("maxSize")))
            except ValueError:
                gone.append(name)
                continue
            keep.append(ent)
        if not gone:
            continue
        target = o[1]
        if target != "아무" and target not in {k.rpartition("=")[0] for k in keep}:
            sys.exit(f"❌ {qid}: 목표 어종 {target} 이 기준표에서 사라진다 — 손대지 않는다")
        if not keep:
            sys.exit(f"❌ {qid}: 기준표가 비게 된다 — 손대지 않는다")
        dropped.setdefault(qid, []).extend(gone)
        o[4] = ";".join(keep)
        goals[i] = "|".join(o)
        touched += 1

if impossible:
    for qid, n, v, mx in impossible:
        print(f"  ⛔ {qid}: {n}={v} 인데 maxSize={mx} — 달성 불가")
    sys.exit("❌ 달성 불가 기준이 있다. 자동으로 지우지 않는다(목표가 조용히 쉬워진다).")

allgone = sorted({n for v in dropped.values() for n in v})
print(f"죽은 행 정리: 목표 {touched}개 / 퀘스트 {len(dropped)}개 / 어종 {len(allgone)}종")
for qid, names in sorted(dropped.items()):
    print(f"  {qid}: {len(names)}종")
print(f"  삭제 어종: {', '.join(allgone)}")

if not apply:
    print("\n(--apply 를 붙이면 실제로 씀)")
    sys.exit(0)

blob = json.dumps(root, ensure_ascii=False, indent=2) + "\n"
for p in (qpath, REPO / "quests.json", PLUGIN / "quests.json"):
    if p.parent.exists():
        p.write_text(blob, encoding="utf-8")
        print(f"  ✓ {p}")
