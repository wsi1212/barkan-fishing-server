#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_quest_bottleneck.py — 진행 병목 3건 해소 (2026-08-28, 유저 지목).

유저: "사막마을 보면 릴 2개 납품하라는게 3-8인가 있는데 그것도 ㅈㄴ 벽이야.
       그리고 여관 찍으라는거랑 광질하라는거를 앞으로 떙겨야함"

## ① 3-8 «모래 위의 대장장이» — 사막 릴 2개 납품
사막 릴은 **B급 레벨제한 32** 인데 3장은 Lv15~28 구간이다. 쓸 수도 없는 부품을 둘이나
만들어 내라고 한다. 게다가 레시피에 **압축흑정석**(광질 산출)이 들어가는데 광질을 알려 주는
퀘스트는 3-14 다 — 6절 뒤다. 거기다 3-9 가 «사막 릴 1개 제작» 이라 **2개 납품이 1개 제작보다
앞서는** 순서 역전까지 있다.
  → 납품 수량 2 → 1. 스토리(대장장이에게 릴을 갖다준다)는 그대로 두고 부담만 반으로.

## ② 광질을 3-8 앞으로
3-14 «마른 우물»(mine|iron_ore|8)을 3-7 자리로 당긴다. 사막 릴에 압축흑정석이 필요하므로
**광질 → 릴 납품** 순서가 되어야 한다. 체인(다음퀘스트)과 [3-n] 표기를 함께 다시 엮는다.

## ③ 여관 거점을 1장으로
3-6 «모래의 잠자리»(action|거점)가 사막마을이라 너무 늦다. 거점은 **사망 복귀 지점**이라
초반에 잡아야 한다. 스폰마을에도 여관이 있다(InnManager.SPAWN_INN_ID = 루드비히).
  → 튜토 막바지에 «거점 설정» 퀘스트를 신설해 끼워 넣는다. 3-6 은 사막 거점 안내로 남긴다
    (마을마다 거점을 새로 잡을 수 있으므로 중복이 아니다).

사용:
    python3 patch_quest_bottleneck.py <BlockShip경로> [--apply]
"""
import json, os, re, shutil, sys

TUTO_ANCHOR = "튜토_통발"        # 이 퀘스트 뒤에 거점 퀘스트를 끼운다
NEW_INN_QID = "튜토_거점"


def sec(v):
    m = re.match(r".*?\[(\d+)-(\d+)\]", v.get("이름", ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src, apply_ = sys.argv[1], "--apply" in sys.argv
    path = os.path.join(src, "quests.json")
    J = json.load(open(path, encoding="utf-8"))
    Q = J["퀘스트"]
    log = []

    # ── ① 릴 납품 2 → 1 ────────────────────────────────────────────────
    v = Q.get("사막05")
    if v:
        for i, g in enumerate(v.get("목표") or []):
            if isinstance(g, str) and g.startswith("deliver|사막 릴|"):
                v["목표"][i] = "deliver|사막 릴|1"
                log.append(("① 릴 납품", "사막05", g, v["목표"][i]))

    # ── ② 광질(사막08)을 사막04 앞으로 ────────────────────────────────
    #   기존 체인: 사막03b → 사막04 → 사막05 … 사막07b → 사막08 → 사막09
    #   새 체인  : 사막03b → 사막08 → 사막04 → 사막05 … 사막07b → 사막09
    chain = [("사막03b", "사막08"), ("사막08", "사막04"), ("사막07b", "사막09")]
    for a, b in chain:
        if a in Q and Q[a].get("다음퀘스트") != b:
            log.append(("② 광질 체인", a, Q[a].get("다음퀘스트"), b))
            Q[a]["다음퀘스트"] = b
    # [3-n] 번호 재부여 — 체인을 따라가며 다시 매긴다
    order, cur, guard = [], "본섬11", 0
    while cur and cur in Q and guard < 60:
        order.append(cur); cur = Q[cur].get("다음퀘스트"); guard += 1
    for i, qid in enumerate(order, 1):
        old = Q[qid].get("이름", "")
        new = re.sub(r"\[3-\d+\]", f"[3-{i}]", old)
        if new != old:
            log.append(("② 절 번호", qid, old[:22], new[:22]))
            Q[qid]["이름"] = new

    # ── ③ 튜토에 거점 퀘스트 신설 ──────────────────────────────────────
    if NEW_INN_QID not in Q and TUTO_ANCHOR in Q:
        nxt = Q[TUTO_ANCHOR].get("다음퀘스트")
        Q[NEW_INN_QID] = {
            "id": NEW_INN_QID,
            "이름": "&e[1-29] 오늘은 여기서 묵는다",
            "설명": ["&7여관 주인 루드비히에게 숙박하면", "&7이곳이 &f거점&7이 됩니다.",
                     "&7죽어도 여기서 다시 시작해요."],
            "목표": ["action|거점"],
            "타입": "행동", "카테고리": "튜토", "필요레벨": 1, "난이도": 1,
            "보상경험치": 20, "보상돈": 800,
            "마을": "스폰도시", "다음퀘스트": nxt,
        }
        Q[TUTO_ANCHOR]["다음퀘스트"] = NEW_INN_QID
        log.append(("③ 거점 신설", NEW_INN_QID, TUTO_ANCHOR + "→" + str(nxt),
                    TUTO_ANCHOR + "→" + NEW_INN_QID + "→" + str(nxt)))
        # 튜토 [1-n] 재번호
        o, cur, guard = [], "튜토_선원", 0
        while cur and cur in Q and guard < 60:
            o.append(cur); cur = Q[cur].get("다음퀘스트"); guard += 1
        for i, qid in enumerate(o, 1):
            old = Q[qid].get("이름", "")
            new = re.sub(r"\[1-\d+\]", f"[1-{i}]", old)
            if new != old:
                Q[qid]["이름"] = new

    for tag, qid, a, b in log:
        print(f"  {tag:<12}{qid:<12}{str(a)[:34]:<36}→ {str(b)[:34]}")
    print(f"\n변경 {len(log)}건")
    if not apply_:
        print("[dry-run] --apply 로 실제 반영")
        return
    shutil.copy(path, path + ".bak-bottleneck")
    json.dump(J, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"✅ quests.json 반영 (백업 quests.json.bak-bottleneck)")


if __name__ == "__main__":
    main()
