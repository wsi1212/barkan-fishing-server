#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_main_levelgate.py — 메인 퀘스트 레벨 관문 복구 + 재조정 (2026-08-28).

유저 정정: "본섬1은 4렙부터 시작하는게 맞아. **사이드** 렙제를 없애라 했지 메인퀘들 렙제를
없애라 하지는 않았어. 물론 렙제 조절은 좀 필요할 것 같긴해. 중간중간 벽을 느끼되, 너무
터무니 없는게 아니라 **사이드퀘랑 일퀘를 열심히 할 수 있도록 하는 수준**"

patch_quest_levelreq.py 가 «목표가 자연 관문이면 레벨제는 중복» 이라는 규칙으로 139건을
풀었는데, 그 규칙을 **메인에까지 적용한 게 틀렸다**(90건). 메인의 레벨제는 중복 잠금이 아니라
**진행 속도 조절 장치**다 — 여기서 막혀야 사이드·일퀘를 하러 간다.

## 복구 후 조정 규칙
백업(quests.json.bak-levelreq)의 원래 값을 되돌린 뒤, «벽의 크기» 를 검사한다.
  벽 = 그 퀘스트 필요레벨 − 직전 메인 퀘스트 필요레벨
  · 벽이 GAP_MAX 를 넘으면 GAP_MAX 로 낮춘다(터무니없는 벽 제거)
  · 벽이 0 이면 그대로 (연속 진행 구간)
GAP_MAX 는 «사이드·일퀘로 메울 수 있는 폭» 이다. 초반일수록 need 가 작아 한 레벨이 싸므로
구간별로 다르게 둔다.

사용:
    python3 patch_main_levelgate.py <BlockShip경로> [--apply]
"""
import json, os, re, shutil, sys

#: 장 → 허용 최대 벽(레벨). 그 이상 뛰면 낮춘다.
GAP_MAX = {1: 2, 2: 3, 3: 3, 4: 3, 5: 3, 6: 4, 7: 4}


def sec(v):
    m = re.match(r".*?\[(\d+)-(\d+)\]", v.get("이름", ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src, apply_ = sys.argv[1], "--apply" in sys.argv
    path = os.path.join(src, "quests.json")
    bak = path + ".bak-levelreq"
    J = json.load(open(path, encoding="utf-8"))
    Q = J["퀘스트"]
    OLD = json.load(open(bak, encoding="utf-8"))["퀘스트"]

    mains = sorted((sec(v), q) for q, v in Q.items() if sec(v))
    # ① 원래 값 복구
    restored = 0
    for _, q in mains:
        o = (OLD.get(q, {}).get("필요레벨", 1) or 1)
        if (Q[q].get("필요레벨", 1) or 1) != o:
            Q[q]["필요레벨"] = o
            restored += 1
    # ② 벽 조정 — 장·절 순으로 훑으며 직전 대비 상승폭을 자른다
    prev = 1
    fixed = []
    for (c, s), q in mains:
        lv = Q[q].get("필요레벨", 1) or 1
        cap = prev + GAP_MAX.get(c, 3)
        if lv > cap:
            fixed.append((c, s, q, lv, cap))
            Q[q]["필요레벨"] = lv = cap
        prev = max(prev, lv)

    print(f"메인 레벨제 복구 {restored}건 · 벽 완화 {len(fixed)}건\n")
    for c, s, q, o, n in fixed:
        print(f"   [{c}-{s:>2}] {q:<12} Lv{o:>2} → Lv{n:<2}  (직전 대비 벽 {o-(n-GAP_MAX.get(c,3))}→{GAP_MAX.get(c,3)})")
    print("\n장별 최종 관문:")
    prev = 1
    for c in sorted({x[0][0] for x in mains}):
        lvs = [Q[q].get("필요레벨", 1) or 1 for (cc, _), q in mains if cc == c]
        print(f"   {c}장  Lv{min(lvs)}~{max(lvs)}")
    if not apply_:
        print("\n[dry-run] --apply 로 실제 반영")
        return
    shutil.copy(path, path + ".bak-maingate")
    json.dump(J, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n✅ quests.json 반영 (백업 quests.json.bak-maingate)")


if __name__ == "__main__":
    main()
