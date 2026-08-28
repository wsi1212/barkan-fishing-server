#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_early_xp.py — 초반(Lv1~10) 접근가능 퀘스트 경험치 보강 (2026-08-28).

유저: "지금 보면 다들 랩업에서 크게 막히더라고"

## 왜 장(章)·난이도 축으로는 못 잡았나
· **장 축** — 2장 전체로는 경험치 분담이 96% 라 멀쩡해 보인다. 그런데 그 안에서 고난도
  사이드(어보·마인팜)가 대부분을 먹고, 저렙이 실제로 깰 수 있는 건 굶고 있었다.
· **난이도 축** — 난이도 1~2 가 2146% 로 과잉처럼 보인다. 메인 7장의 «국왕에게 말 걸기»
  (난이도 1, 21,184xp)가 섞이기 때문이다. 난이도는 «그 한 건의 조작 난이도» 라 진행 단계가 아니다.
⇒ 둘 다 단독으로는 못 쓴다. **«그 시점에 실제로 접근 가능한가»** 로 골라야 한다.

## 대상 = 초반 접근 가능 62종
  튜토 전체 + 1~2장 메인 + 본사이드 중 난이도 ≤4

## 목표 분담을 왜 70% 로 잡나 (설계식은 50%)
설계식 need = h × xph ÷ (1 − 0.5) 은 **모델 xph 1,473** 을 전제한다. 그런데 prod 실측
초보 xph 는 **264** 다(1/5.6). 초반 유저는 퀘스트 따라 걷고 NPC 와 말하느라 캐스트를 못 던진다.
그 시간을 퀘스트가 보상하지 않으면 «퀘스트를 하느라 레벨이 안 오르는» 구조가 된다.
  실측: 퀘스트 2,050(37%) → 낚시로 3,521 필요 = **13.3시간**
  50%  : 낚시 2,786 = 10.6시간   ·   70%: 낚시 1,671 = **6.3시간**

★중·후반은 건드리지 않는다 — 거기선 실측 xph 가 740 까지 오르고(ryan7047), 장(章) 단위
  패치(patch_quest_rewards.py)가 이미 처리했다.

사용:
    python3 patch_early_xp.py <BlockShip경로> [--apply]
"""
import json, os, re, shutil, sys

SHARE = 0.70
EARLY_LV = 10
SIDE_MAX_DIFF = 4
JAVA = os.path.expanduser("~/development/blockship-plugin/src/main/java/com/blockship")


def need_table():
    s = open(os.path.join(JAVA, "fishing", "FishingLevelManager.java"), encoding="utf-8").read()
    m = re.search(r"NEED_TABLE = new int\[\] \{(.*?)\};", s, re.S)
    if not m:
        raise SystemExit("★NEED_TABLE 을 못 읽었다 — 중단")
    return [int(x) for x in re.findall(r"\d+", m.group(1))]


def chapter(v):
    m = re.match(r".*?\[(\d+)-\d+\]", v.get("이름", ""))
    return int(m.group(1)) if m else None


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src, apply_ = sys.argv[1], "--apply" in sys.argv
    path = os.path.join(src, "quests.json")
    J = json.load(open(path, encoding="utf-8"))
    Q = J["퀘스트"]
    NEED = need_table()

    acc = []
    for qid, v in Q.items():
        c, d = chapter(v), v.get("난이도", 0) or 0
        if (v.get("카테고리") == "튜토" or c in (1, 2)
                or (qid.startswith("본사이드") and d <= SIDE_MAX_DIFF)):
            acc.append(qid)

    cur = sum(Q[q].get("보상경험치", 0) or 0 for q in acc)
    need = sum(NEED[:EARLY_LV])
    tgt = need * SHARE
    scale = tgt / cur if cur else 1.0
    print(f"대상 {len(acc)}종 · 현재 {cur:,}xp (분담 {cur/need*100:.0f}%)")
    print(f"목표 {tgt:,.0f}xp (분담 {SHARE*100:.0f}%) → ×{scale:.2f}")
    print(f"낚시 부담 {(need-cur)/264:.1f}h → {(need-tgt)/264:.1f}h  (실측 264xp/h)\n")

    ch = []
    for q in acc:
        o = Q[q].get("보상경험치", 0) or 0
        n = max(1, round(o * scale)) if o else 0
        if n != o:
            ch.append((q, o, n))
    for q, o, n in sorted(ch, key=lambda x: -(x[2] - x[1]))[:10]:
        print(f"   {q:<20}{o:>6,} → {n:<6,}")
    print(f"\n변경 {len(ch)}건")
    if not apply_:
        print("[dry-run] --apply 로 실제 반영")
        return
    shutil.copy(path, path + ".bak-earlyxp")
    for q, o, n in ch:
        Q[q]["보상경험치"] = n
    json.dump(J, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("✅ quests.json 반영 (백업 quests.json.bak-earlyxp)")


if __name__ == "__main__":
    main()
