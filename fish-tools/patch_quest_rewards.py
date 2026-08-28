#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_quest_rewards.py — 퀘스트 보상(돈·경험치) 단계별 재분배 (2026-08-28).

유저 지시: "퀘스트들 돈을 줄이고 경험치를 늘리는 방향으로 가야하지 않을까"
          "축이랑 다 세우고 그걸 기반으로 사이드퀘스트들 보상 분배"

## 진행 축 — 무엇을 기준으로 «단계» 를 정하나
필요레벨은 못 쓴다(악순환 때문에 유저가 사이드를 전부 Lv1 로 낮춰 놨고, 2026-08-28 에
중복 잠금 139건을 마저 해제했다). 난이도도 못 쓴다 — «그 퀘스트 한 건의 조작 난이도» 라
메인 7장의 «국왕에게 말 걸기» 가 난이도 1 이다(실측: 난이도1 중앙 60xp, 상위 5개가 84%).

쓸 수 있는 건 둘뿐이다:
  · 메인 — 이름의 [장-절] 표기
  · 사이드 — qid 접두어(본/사/왕/상/심)가 곧 그 마을이고, 마을이 곧 장이다
레벨 구간은 **백업(quests.json.bak-levelreq)의 메인 퀘스트 원래 필요레벨**에서 뽑았다.
그게 설계자가 남긴 유일한 단계 정보다.

## 목표
  경험치 = 그 구간 need 의 50%(설계식 need = h × xph ÷ (1 − 퀘스트분담 0.5))
  돈     = 그 구간 «풀세팅 레시피 해금비 × 3» (장비 사고도 강화·소모에 여유)
           ★해금비 = parts.json 가격 × 0.25 (PartPricing.DISCOUNTED_PRICE_RATE)

## ★올리기만/내리기만
  · 경험치는 **미달 구간만 올린다.** 실측 xp/h 가 155~740 으로 모델(1,473)의 1/2~1/9 이라
    퀘스트가 50% 보다 더 지고 있는 게 정상 보정이다. 여기서 50% 로 «맞추면» 2장(96%)·
    3장(71%)이 깎여 유저가 겪는 랩업 정체가 더 나빠진다.
  · 돈은 **초과 구간만 내린다.** 2장이 세트값의 66.6배로 압도적이다.

사용:
    python3 patch_quest_rewards.py <BlockShip경로> [--apply]
"""
import collections, json, os, re, shutil, sys

#: 장 → 레벨 구간 (백업의 메인 퀘스트 원래 필요레벨 min~max)
BAND = {1: (1, 3), 2: (4, 14), 3: (15, 28), 4: (28, 32), 5: (32, 40), 6: (40, 50), 7: (50, 70)}
#: 사이드 qid 접두어 → 장
PREFIX = {"본": 2, "사": 3, "왕": 6, "상": 5, "심": 7}
#: 그 구간 «풀세팅 해금비»(parts.json 가격 ×0.25 합). 4장은 왕도 진입 직후라 3장과 같은 급.
# ★1장(튜토)은 «세트값 0» 이 아니다 — 첫 D 급 장비를 갖추는 시드머니가 필요하다.
#   0 으로 두면 목표가 0 이 되어 튜토 보상금이 전멸한다.
SET_COST = {1: 30515, 2: 30515, 3: 73682, 4: 73682, 5: 272875, 6: 272875, 7: 1823506}
#: 돈 목표 = 세트값 × 이 배수
MONEY_MULT = 3.0
#: 보상금 하한 — 비례 축소가 저난도 퀘스트를 50원짜리로 만들지 않게.
MONEY_FLOOR = 300
#: 경험치 목표 = 구간 need × 이 비율 (설계식의 퀘스트 분담)
XP_SHARE = 0.5
JAVA = os.path.expanduser("~/development/blockship-plugin/src/main/java/com/blockship")


def need_table():
    src = open(os.path.join(JAVA, "fishing", "FishingLevelManager.java"), encoding="utf-8").read()
    m = re.search(r"NEED_TABLE = new int\[\] \{(.*?)\};", src, re.S)
    if not m:
        raise SystemExit("★NEED_TABLE 을 못 읽었다 — 목표를 못 세우므로 중단")
    return [int(x) for x in re.findall(r"\d+", m.group(1))]


#: 사이드 중 이 난이도 이상은 «그 마을에 있을 뿐 종반 콘텐츠» 다 — 접두어로 매긴 장을 쓰면
#  안 된다. 실측: 본사이드_마인팜08(난이도15)이 100만원인데 2장(Lv4~14)으로 잡혀 ×0.05 를
#  맞았다. 어보·대지주·마인팜 계열이 전부 여기 해당한다.
HARD_DIFF = 10
HARD_STAGE = 6


def stage_of(qid, v):
    m = re.match(r".*?\[(\d+)-\d+\]", v.get("이름", ""))
    if m:
        return int(m.group(1))
    p = re.match(r"([가-힣])사이드", qid)
    if not p:
        return None
    s = PREFIX.get(p.group(1))
    if s and (v.get("난이도", 0) or 0) >= HARD_DIFF:
        return max(s, HARD_STAGE)
    return s


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src, apply_ = sys.argv[1], "--apply" in sys.argv
    path = os.path.join(src, "quests.json")
    J = json.load(open(path, encoding="utf-8"))
    Q = J["퀘스트"]
    NEED = need_table()

    grp = collections.defaultdict(list)
    for qid, v in Q.items():
        s = stage_of(qid, v)
        if s:
            grp[s].append(qid)

    print(f"{'장':>3}{'퀘':>5}{'현재xp':>9}{'목표xp':>9}{'xp배':>6}"
          f"{'현재돈':>11}{'목표돈':>11}{'돈배':>6}")
    scale = {}
    for s in sorted(grp):
        lo, hi = BAND[s]
        need = sum(NEED[i] for i in range(lo - 1, min(hi, len(NEED))))
        xp = sum(Q[q].get("보상경험치", 0) or 0 for q in grp[s])
        mn = sum(Q[q].get("보상돈", 0) or 0 for q in grp[s])
        xt, mt = need * XP_SHARE, SET_COST[s] * MONEY_MULT
        # ★경험치는 올리기만, 돈은 내리기만
        xs = max(1.0, xt / xp) if xp else 1.0
        ms = min(1.0, mt / mn) if mn else 1.0
        scale[s] = (xs, ms)
        print(f"{s:>3}{len(grp[s]):>5}{xp:>9,}{xp*xs:>9,.0f}{xs:>6.2f}"
              f"{mn:>11,}{mn*ms:>11,.0f}{ms:>6.2f}")

    ch = []
    for s, qids in grp.items():
        xs, ms = scale[s]
        for q in qids:
            v = Q[q]
            ox, om = v.get("보상경험치", 0) or 0, v.get("보상돈", 0) or 0
            nx, nm = round(ox * xs), round(om * ms)
            if om > 0:
                nm = max(nm, MONEY_FLOOR)   # 보상이 «0원에 가까운 숫자» 가 되면 안 준 것만 못하다
            if (nx, nm) != (ox, om):
                ch.append((s, q, ox, nx, om, nm))
    print(f"\n변경 {len(ch)}건")
    for s, q, ox, nx, om, nm in sorted(ch, key=lambda x: -(x[4] - x[5]))[:10]:
        print(f"   {s}장 {q:<16} xp {ox:>6,}→{nx:<6,}  돈 {om:>8,}→{nm:<8,}")

    if not apply_:
        print("\n[dry-run] --apply 로 실제 반영")
        return
    shutil.copy(path, path + ".bak-rewards")
    for s, q, ox, nx, om, nm in ch:
        if nx != ox:
            Q[q]["보상경험치"] = nx
        if nm != om:
            Q[q]["보상돈"] = nm
    json.dump(J, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n✅ quests.json 반영 {len(ch)}건 (백업 quests.json.bak-rewards)")


if __name__ == "__main__":
    main()
