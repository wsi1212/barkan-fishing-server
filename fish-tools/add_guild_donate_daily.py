#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""일일 퀘스트에 「길드 계좌 기부」 4종 추가 (2026-08-16).

■ 왜
  길드 금고로 들어오는 길이 **기부 하나뿐**인데, 기부를 유도하는 장치가 아무것도 없었다.
  주간 길드 퀘스트에 `guilddonate`를 넣은 김에 **개인 일일**에도 같은 verb로 한 칸씩 둔다.
  매일 조금씩 들어가는 흐름이 주간 한 방보다 금고를 훨씬 안정적으로 채운다.

■ 경제적으로 뭘 하나 — **통화를 줄인다**
  기부는 개인 지갑 → 금고 **이동**이고, 금고는 개인 지갑으로 **다시 나올 수 없다**
  (소비처가 버프·슬롯확장·섬확장뿐). 보상을 기부액의 **80%**로 잡았으므로

      개인 −기부액 +보상(80%)  =  −20%
      금고 +기부액
      서버 총통화 −20%

  즉 **싱크**다. 개인에겐 20%가 「길드세」고, 그 대가로 길드 버프가 돌아온다.

■ ★길드 없는 사람 문제
  `QuestManager.acceptDaily`는 그 난이도 **풀 전체**를 배정한다. 그냥 넣으면 길드 미가입자의
  그날 목록에 **절대 못 깨는 칸**이 하나 생긴다. 그래서 퀘스트에 **`길드필요: true`**를 달고,
  자바 쪽 `acceptDaily`/`checkWeekly`가 그 플래그를 보고 미가입자에겐 건너뛴다
  (`ops/patches/guild-weekly-quest.patch`).
  ⇒ **패치 없이 이 데이터만 넣으면 미가입자 일퀘가 하나 죽는다.** 반드시 같이 갈 것.

사용법 — quests.json 이 있는 디렉터리에서 (★`add_quest_difficulty.py` 앞에):
    python3 add_guild_donate_daily.py
    python3 add_guild_donate_daily.py --dry
"""
import json, os, shutil, sys

QP = "quests.json"
DRY = "--dry" in sys.argv
Q = json.load(open(QP, encoding="utf-8"))
QUESTS, DAILY, LEVELS = Q["퀘스트"], Q["일일"], Q["난이도레벨"]

# (난이도, 기부액, 이름) — 보상은 기부액의 80%. 그 버킷의 기존 보상대와 겹치게 잡았다.
#   쉬움 350~500 / 보통 900~1,400 / 어려움 2,600~3,800 / 전문 7,500~9,500
ROWS = [
    ("쉬움",   3_000, "&d길드에 보태기",   "&7길드 계좌에 &f3,000원&7을 기부하세요."),
    ("보통",  10_000, "&d길드의 살림",     "&7길드 계좌에 &f10,000원&7을 기부하세요."),
    ("어려움", 30_000, "&d금고를 채우다",   "&7길드 계좌에 &f30,000원&7을 기부하세요."),
    ("전문",  80_000, "&d길드의 기둥",     "&7길드 계좌에 &f80,000원&7을 기부하세요."),
]

rows = []
for diff, amount, name, desc in ROWS:
    qid = f"일퀘_{diff}_기부"
    if qid in QUESTS:
        sys.exit(f"✗ {qid} 이 이미 있다 — 두 번 적용됐다")
    if diff not in DAILY:
        sys.exit(f"✗ 일일 버킷에 {diff} 가 없다")
    reward = int(amount * 0.8)
    QUESTS[qid] = {
        "id": qid,
        "이름": name,
        "설명": [desc,
               "&8기부한 돈은 길드 버프·섬 확장에 쓰입니다.",
               "&8&f/길드&8 → 길드 계좌 기부"],
        "목표": [f"guilddonate|{amount}"],
        "타입": "기여",
        "카테고리": "일일",
        "필요레벨": LEVELS[diff],
        "보상돈": reward,
        "보상경험치": 0,
        "길드필요": True,       # ★미가입자에겐 배정하지 않는다 (자바 게이트)
    }
    DAILY[diff].append(qid)
    rows.append((qid, LEVELS[diff], amount, reward, amount - reward))

if not DRY:
    shutil.copy(QP, QP + ".pre-guilddonate")
    with open(QP, "w", encoding="utf-8") as f:
        json.dump(Q, f, ensure_ascii=False, indent=2)

# ══ 리포트 ═════════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("  일일 「길드 계좌 기부」 4종")
print("=" * 72)
print(f"  {'퀘스트':18}{'Lv':>4}{'기부':>10}{'보상':>10}{'개인 순비용':>12}")
for qid, lv, amt, rw, net in rows:
    print(f"  {qid:18}{lv:>4}{amt:>10,}{rw:>10,}{-net:>12,}")
print(f"\n  버킷당 4개 → 5개. 서버 총통화는 기부액의 20%만큼 줄어든다(싱크).")

# ══ 검증 ═══════════════════════════════════════════════════════════════════
ok = True
for diff in DAILY:
    n = len(DAILY[diff])
    dup = len(DAILY[diff]) != len(set(DAILY[diff]))
    if dup:
        print(f"✗ {diff} 버킷에 중복 id"); ok = False
    print(f"  {diff:5} {n}개")

miss = [q for q in rows if not QUESTS[q[0]].get("길드필요")]
print("\n길드필요 플래그 누락:", miss if miss else "없음")
if miss:
    ok = False

# 보상이 기부액을 넘으면 무한 증식이다 — 반드시 막는다
bad = [(q, a, r) for q, _, a, r, _ in rows if r >= a]
print("보상 ≥ 기부액 (증식 위험):", bad if bad else "없음")
if bad:
    print("  ✗ 보상이 기부액 이상이면 기부→보상→기부 로 돈이 늘어난다"); ok = False

print(f"\n{'(드라이런 — 저장 안 함)' if DRY else '✓ 완료.'}")
print("★자바 패치 ops/patches/guild-weekly-quest.patch 가 있어야 「길드필요」 게이트와")
print("  guilddonate verb 가 동작한다. 데이터만 넣으면 미가입자 일퀘가 하나 죽는다.")
print("★다음: add_quest_difficulty.py")
if not ok:
    sys.exit("✗ 검증 실패")
