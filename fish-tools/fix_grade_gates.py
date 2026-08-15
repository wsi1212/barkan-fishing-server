#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""저레벨 등급 요구 정리 — 「Lv8한테 S등급을 낚아 오라니」 (2026-08-15).

■ 문제
  S등급의 **실제 출현율은 1%** 다(`GradeRoller.ROLL_ORDER`, 몬테카를로 80만 캐스트 실측).
  S이상까지 쳐도 2.2% — 한 마리에 **45캐스트**다. 레벨 게이트는 없어서(M30·L45·G60만
  잠긴다) 기술적으로는 Lv1도 낚을 수 있지만, 그건 「가능하다」지 「할 만하다」가 아니다.

  전수 스캔에서 나온 것들:

      Lv8   본사이드_마리02      S등급 2마리      ≒ 90캐스트
      Lv8   본사이드_세르간04     S등급 1마리
      Lv9   본섬09(메인)        바르칸의심연 = S + 밤 + 비   ≒ 7시간 ★체인 블록
      Lv12  사사이드_사피르03     S등급 1마리
      Lv15  왕사이드_견습생01     S등급 6마리 80cm+  ≒ 270캐스트

■ 규칙 — **S등급 이상은 Lv25부터**
  A는 21캐스트(≒6분)라 저레벨에도 무리가 없다. 벽이 되는 건 S부터다(45캐스트).
  Lv25는 3챕터 후반 `사막12b`(이프리트의 시련) — 원래 「첫 S 요구」로 설계된 자리다.
  등급을 내리는 대신 **수량을 늘려** 체감 분량은 유지한다.

■ `본섬09` — 2챕터 클라이맥스라 따로 다룬다
  이 퀘는 메인 체인이라 **막히면 진행이 멈춘다.** 그런데 `바르칸의심연`은
  S등급(100캐스트) × 밤(2.5) × 비(3) = **약 7시간**짜리였다. Lv9에 세울 벽이 아니다.
  ★게다가 `밤비` 버킷에만 들어 있어 **비가 안 오면 아예 풀에 안 들어온다** — 하드 게이트다.

  ⇒ **A등급 · 밤 전용**으로 바꾸고 `밤맑음` 버킷에도 넣는다(≒1시간 20분).
    「달이 뜬 밤에만 올라오는 놈」은 그대로 남고, 비 대기만 사라진다.
    조각을 품은 특별한 개체라는 사실은 등급표와 무관하다 — 3챕터 전설어
    `실러캔스`(S, Lv26)보다 아래에 두는 편이 서열도 맞는다.

사용법 — quests.json·fish.json·dialogue.json이 있는 디렉터리에서
         (★`add_quest_difficulty.py` 앞에):
    python3 fix_grade_gates.py
    python3 fix_grade_gates.py --dry
"""
import json, os, re, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

QP, FP, DP = "quests.json", "fish.json", "dialogue.json"
DRY = "--dry" in sys.argv
Q = json.load(open(QP, encoding="utf-8"))
F = json.load(open(FP, encoding="utf-8"))
D = json.load(open(DP, encoding="utf-8"))
QUESTS = Q["퀘스트"]

S_MIN_LEVEL = 25                     # 이 레벨 미만에는 S 이상을 요구하지 않는다
RANK = {"E": 1, "D": 2, "C": 3, "B": 4, "A": 5, "S": 6, "M": 7, "L": 8, "G": 9}


def cap_for(lv):
    return "A" if lv < S_MIN_LEVEL else None


# ══ 1. 저레벨 등급 하향 (목표 + 설명) ═══════════════════════════════════════
FIX = {
    "본사이드_마리02": (["fish|아무|A|3|0"], [
        "&7&fA등급 이상&7 &f3마리&7를 채우세요.",
        "&8마리: \"비늘이 고와야 값을 쳐줘요. 등급은 그다음이고요.\""]),
    "본사이드_세르간04": (["fish|아무|A|2|0"], [
        "&7A등급 이상 &f물고기&7를 2마리 잡으세요.",
        "&8세르간: \"전설을 보려면 먼저 좋은 놈을 손에 익혀야 하네.\""]),
    "사사이드_사피르03": (["fish|아무|A|1|0", "material|진주|2"], [
        "&7A등급 1마리 — 그리고 표본 손질용",
        "&f진주&7 2개가 필요합니다."]),
    "왕사이드_견습생01": (["fish|아무|A|3|80", "dogam|강,항구,상단마을|18"], [
        "&7왕도 일대 도감 18종을 정리해 주세요.",
        "&7&fA등급 이상&7 &f3마리&7 · &f80cm 이상&7도 함께 필요합니다.",
        "&8니나: \"표본은 크기가 있어야 골격을 볼 수 있거든요.\""]),
}

log = []
for qid, (goals, desc) in FIX.items():
    e = QUESTS[qid]
    log.append((qid, e["필요레벨"], " + ".join(e["목표"]), " + ".join(goals)))
    e["목표"], e["설명"] = goals, desc

# ══ 2. 바르칸의심연 — S/밤/비 → A/밤/전천후 ═════════════════════════════════
SP = "바르칸의심연"
d = F["fish"][SP]
d["grade"], d["weather"] = "A", "전체"          # time="밤"은 유지
# ★버킷도 옮겨야 실제로 풀에 들어온다. `밤비`에만 있으면 비 올 때만 로드된다.
for r in ("강", "강_상류"):
    b = F["regions"][r].setdefault("밤맑음", [])
    if SP not in b:
        b.append(SP)

q = QUESTS["본섬09"]
q["이름"] = "&6달이 뜬 밤의 전설"
q["설명"] = [
    "&7세르간: \"달이 뜬 밤에만 올라오는 놈이 있네.\"",
    "&7&f바르칸 물길&7에서 &6바르칸의심연&7을 1마리 낚으세요.",
    "&8상류에도 살지만 그쪽은 큰 놈이 많아 경쟁이 심하네. 아래쪽이 낫지.",
    "&8그 몸 안에 무엇이 들었는지는 올려 봐야 압니다."]
D["세르간"]["인사/본섬09"]["lines"] = [
    "좋아, 다음으로 맡길 일이 생겼네.",
    "달이 뜬 밤에만 올라오는 놈이 있어. 바르칸의심연이라 부르지.",
    "한 마리면 되네. 마음이 정해지면 내 부탁을 받아주게."]
D["세르간"]["진행중/본섬09"]["lines"] = [
    "해가 지거든 물길로 가게. 낮에는 좀처럼 안 올라오니까.",
    "상류는 큰 놈들이 많아 오히려 성가시네. 마을 앞 강이 나아."]

# ══ 저장 ═══════════════════════════════════════════════════════════════════
if not DRY:
    for path, obj in [(QP, Q), (FP, F), (DP, D)]:
        shutil.copy(path, path + ".pre-gradegate")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 78)
for qid, lv, before, after in log:
    print(f"  {qid:20} Lv{lv:<3} {before:28} → {after}")
print(f"  {SP:20} Lv9   S/밤/비                      → A/밤/전천후 (밤맑음 버킷 추가)")

# ══ 검증 — 규칙 위반이 남았는지 전수 확인 ═══════════════════════════════════
FISH = F["fish"]
bad = []
for qid, e in QUESTS.items():
    cap = cap_for(e["필요레벨"])
    if cap is None:
        continue
    for g in e["목표"]:
        p = g.split("|")
        if p[0] not in ("fish", "fish_fresh", "harpoon"):
            continue
        gr = FISH.get(p[1], {}).get("grade", p[2]) if p[1] not in ("아무", "") else p[2]
        gr = gr.split("~")[0] if "~" in gr else gr
        if gr in RANK and RANK[gr] > RANK[cap]:
            bad.append(f"{qid}(Lv{e['필요레벨']}) {g} — 상한 {cap}")
print("\n레벨-등급 규칙 위반:", bad if bad else "없음")
if bad:
    sys.exit("✗ 검증 실패")
print(f"\n{'(드라이런 — 저장 안 함)' if DRY else '✓ 완료.'} ★다음: add_quest_difficulty.py")
