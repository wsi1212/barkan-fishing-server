#!/usr/bin/env python3
"""범선 → 돛단배 교체에 딸린 텍스트 수정 (튜토리얼 퀘스트 + 조선공 하인츠 대사).

프리셋 자체 교체는 imugi-boss/scan_ship_world.py + bake_ship.py 가 한다. 여기는 「범선」이라는
이름을 문장 안에서 부르는 곳만 고친다 — 프리셋이 없어지면 퀘스트 설명이 없는 배를 사라고 시킨다.

대상: ops/blockship-data/{quests.json,dialogue.json} (배포 소스인 미러가 권위) + dev 라이브 사본.
멱등 — 이미 고쳐져 있으면 아무것도 안 한다.
"""
import json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIRROR = os.path.join(REPO, "ops", "blockship-data")
LIVE = os.path.expanduser("~/Library/Application Support/feather/player-server/servers/"
                          "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
# CI(quest_audit.py)가 읽는 세 번째 사본 — 빠뜨리면 ops/audit-copies.py ②가 배포를 멈춘다
PLUGIN_REPO = os.path.expanduser("~/development/blockship-plugin")

QUEST_LINES = {
    "튜토_배2": [
        ("&7하인츠에게 말을 걸어 조선소를 열고 &f범선&7을 사세요. &8(10,000원)",
         "&7하인츠에게 말을 걸어 조선소를 열고 &f돛단배&7를 사세요. &8(10,000원)"),
        ("&8▸ 산 배는 조선소에서 다시 눌러도, &f/배 소환 범선&8 으로도 부를 수 있어요.",
         "&8▸ 산 배는 조선소에서 다시 눌러도, &f/배 소환 돛단배&8 으로도 부를 수 있어요."),
    ],
}

DIALOGUE_LINES = {
    "인사/튜토_배2": [
        ("&f범선&7 한 척, &f10,000원&7. 갑판도 넓고 돛도 제대로 물린 놈이야.",
         "&f돛단배&7 한 척, &f10,000원&7. 작아도 돛은 제대로 물린 놈이야."),
    ],
    "진행중/튜토_배2": [
        ("조선소는 나한테 말 걸면 열려. 범선 10,000원.",
         "조선소는 나한테 말 걸면 열려. 돛단배 10,000원."),
    ],
}


def patch_quests(path):
    d = json.load(open(path, encoding="utf-8"))
    n = 0
    for qid, subs in QUEST_LINES.items():
        q = d["퀘스트"].get(qid)
        if not q:
            print(f"  ! {qid} 없음 — 스킵"); continue
        for i, line in enumerate(q.get("설명", [])):
            for old, new in subs:
                if line == old:
                    q["설명"][i] = new; n += 1
    return d, n


def patch_dialogue(path):
    d = json.load(open(path, encoding="utf-8"))
    n = 0
    # dialogue.json 은 NPC → 노드키 → {lines,choices} 구조라 노드키를 전 NPC에서 찾는다
    def walk(node):
        nonlocal n
        if isinstance(node, dict):
            for k, v in node.items():
                if k in DIALOGUE_LINES and isinstance(v, dict) and isinstance(v.get("lines"), list):
                    for i, line in enumerate(v["lines"]):
                        for old, new in DIALOGUE_LINES[k]:
                            if line == old:
                                v["lines"][i] = new; n += 1
                walk(v)
        elif isinstance(node, list):
            for v in node: walk(v)
    walk(d)
    return d, n


def write(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    total = 0
    for base in (MIRROR, LIVE, PLUGIN_REPO):
        if not os.path.isdir(base):
            print(f"- {base} 없음, 스킵"); continue
        for fname, fn in (("quests.json", patch_quests), ("dialogue.json", patch_dialogue)):
            p = os.path.join(base, fname)
            if not os.path.exists(p):
                print(f"- {p} 없음, 스킵"); continue
            data, n = fn(p)
            if n:
                write(p, data)
            print(f"  {'✓' if n else '·'} {p} — {n}줄 교체")
            total += n
    if total == 0:
        print("변경 없음 (이미 적용됨)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
