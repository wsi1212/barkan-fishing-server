#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""마을 어보(魚譜) — 마을마다 「그 물의 모든 물고기」 캡스톤 하나 (2026-08-15).

■ 왜
  마을별 사이드 봉우리는 10~12칸에서 멈춘다(`spread_side_difficulty.py`). 그 위에,
  **「이 마을 물을 전부 읽었다」** 는 한 판을 마을마다 하나씩 세운다. 어보는 낚시
  서버가 낼 수 있는 가장 정직한 최종 과제다 — 운도 전투도 아니고 **전수 조사**다.

■ 종수는 하드코딩하지 않는다
  `fish.json`의 지역 버킷에서 **런타임에 센다.** 어종을 추가/삭제하면 목표가 따라온다.
  ★**퀘스트 전용 어종(`def.quest`)은 뺀다.** 그놈들은 특정 퀘스트가 활성일 때만 풀에
  들어오므로(`FishingListener`), 총수를 그대로 요구하면 **영구 미완성**이 된다.
  (`검은비늘붕어` 사고와 같은 함정 — 그때는 `심해09`가 잡을 수 없는 5마리를 요구했다.)
  자바 `QuestManager.dexCount`는 버킷 전체를 세므로 퀘스트 어종을 잡아 뒀다면 그것도
  진행도에 들어간다. 즉 **비퀘스트 종수 = 확실히 도달 가능한 상한**이다.

■ 램프
  마을 순서대로 어보가 굵어진다 — 물이 넓어지니까 자연히 그렇게 된다.

      스폰마을  강                   → 12칸   (노인 — 평생 이 강만 판 사람)
      사막마을  오아시스·붉은사막·레드_로드 → 14칸   (사피르 — 이미 사막 도감 퀘 담당)
      상단마을  상단마을·대양·항구       → 17칸   (알도 — 자칭 낚시광, 도감 퀘 담당)
      왕도     왕국 전 수역 10곳        → 19칸   (견습 사서 니나 — 왕립 어보 편찬)

  왕도만 성격이 다르다. 왕도의 물은 `기억의연못` 4종뿐이라 「우리 마을 물고기」가
  성립하지 않는다. 대신 왕도는 **기록의 도시**다 — 그래서 왕도의 어보는 자기 물이
  아니라 **왕국 전체의 목록**이다. 이 편이 챕터 주제(봉인=기록 지우기)와도 맞는다.

■ 칭호
  놀고 있던 `도감박사`(50종)·`백과사전`(100종)을 여기에 붙인다. 원래 이 둘은
  어디서도 안 주고 있었다.

사용법 — quests.json·npc.json·dialogue.json·fish.json이 있는 디렉터리에서
         (★`add_quest_difficulty.py` **앞에**):
    python3 add_village_capstones.py
    python3 add_village_capstones.py --dry
"""
import json, os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

QP, NP, DP, FP = "quests.json", "npc.json", "dialogue.json", "fish.json"
DRY = "--dry" in sys.argv
Q = json.load(open(QP, encoding="utf-8"))
N = json.load(open(NP, encoding="utf-8"))
D = json.load(open(DP, encoding="utf-8"))
F = json.load(open(FP, encoding="utf-8"))
QUESTS, NPCS = Q["퀘스트"], N["npcs"]
FISH, REGIONS = F["fish"], F["regions"]

import add_quest_difficulty as D_  # noqa: E402


def catchable(regs):
    """지역 목록에서 **어보에 실을 수 있는** 어종 수.
    빼는 것 둘 —
      ① 퀘스트 전용(`def.quest`): 그 퀘가 켜져 있을 때만 풀에 들어온다.
      ② **G등급(신화)**: 출현율 1/3030 캐스트다. 대왕오징어·골리앗그루퍼·황금아로와나
         셋 때문에 대양 전종이 234시간, 전역 전종이 614시간으로 튀었다.
         신화급은 어보가 아니라 **전설로 따로 친다** — 그래야 「모든 물고기」가 말이 된다."""
    sp = set()
    for r in regs:
        if r not in REGIONS:
            sys.exit(f"✗ fish.json에 지역 '{r}' 없음")
        for bucket in REGIONS[r].values():
            sp.update(bucket)
    return sum(1 for x in sp
               if not FISH.get(x, {}).get("quest")
               and FISH.get(x, {}).get("grade") != "G")


ALL_REGIONS = ["강", "협곡", "정상", "항구", "늪지대",
               "오아시스", "붉은사막", "레드_로드", "상단마을", "대양"]

CAPSTONES = [
    dict(id="본사이드_노인06", giver="노인", after="본사이드_노인05", lv=40,
         이름="&b바르칸 물길 어보", 돈=200000, exp=9000, 칭호="도감박사",
         regs=["강"],
         설명=lambda n: [
             "&7노인이 평생 적어 온 공책을 내밉니다. 뒤쪽 절반이 비어 있습니다.",
             "&7\"내 눈이 이제 물속을 못 보네. 자네가 마저 채워 주게.\"",
             f"&7&f마을 앞 강의 물고기 {n}종&7 — 이 물에서 낚을 수 있는 전부입니다.",
             "&8평생 한 사람이 못 채운 공책입니다. 짧게 끝날 리가 없습니다."],
         대화=(["…자네에게 부탁이 하나 남았네.",
               "내가 예순 해를 적어 온 공책일세. 뒤쪽 절반이 아직 비었어.",
               "이 강에 사는 것들을 전부 — 그게 내 마지막 부탁이라네."],
              ["급할 것 없네. 나도 예순 해가 걸렸으니까."],
              ["…다 찼군. 다 찼어.",
               "이건 이제 내 공책이 아닐세. 자네 것이야."])),
    dict(id="사사이드_사피르05", giver="사피르", after="사사이드_사피르04", lv=45,
         이름="&b모래바다 어보", 돈=260000, exp=11000, 칭호=None,
         regs=["오아시스", "붉은사막", "레드_로드"],
         설명=lambda n: [
             "&7사피르의 연구실 벽에 사막 물길 지도가 걸려 있습니다. 표본 칸은 절반이 빕니다.",
             "&7\"물이 적은 땅일수록 목록이 중요해요. 하나 사라지면 티가 나거든요.\"",
             f"&7&f오아시스·붉은사막·레드 로드의 물고기 {n}종&7을 전부 등록하세요.",
             "&8레드로드 호수 쪽은 아직 아무도 제대로 세어 본 적이 없습니다."],
         대화=(["부탁이 하나 있어요. 제 평생 연구이기도 하고요.",
               "물이 적은 땅일수록 목록이 중요해요. 하나 사라지면 바로 티가 나니까요.",
               "오아시스와 붉은사막, 그리고 레드로드 호수까지 — 전부요."],
              ["표본은 서두르면 상해요. 천천히 하세요."],
              ["…전부 찼네요. 이 땅의 물이 이렇게 생겼구나.",
               "이제 무언가 사라지면, 우리가 제일 먼저 알 수 있어요."])),
    dict(id="상사이드_알도03", giver="알도", after="상사이드_알도02", lv=50,
         이름="&b대양 어보", 돈=340000, exp=14000, 칭호=None,
         regs=["상단마을", "대양", "항구"],
         목표추가=["fish|아무|S|8|0", "harpoon|아무|A|20|0"],
         설명=lambda n: [
             "&7알도: \"낚시광이라 불리는 게 부끄럽지 않으려면 이건 해야 하오.\"",
             f"&7&f상단마을·대양·항구의 물고기 {n}종&7 · &fS등급 8마리&7 ·",
             "&7&f작살로 A등급 이상 20마리&7.",
             "&8낚싯대로 못 닿는 놈은 작살로 봐야 목록이 채워집니다.",
             "&8의뢰: &7알도"],
         대화=(["낚시광이라 불리는 게 부끄럽지 않으려면 이건 해야 하오.",
               "상단마을과 대양, 항구까지 — 물고기를 전부 보는 것이오.",
               "낚싯대로 못 닿는 놈은 작살로 보시오. 그래야 목록이 채워지오."],
              ["아직이오? 나도 이십 년째 못 채웠소. 부끄러울 것 없소."],
              ["…내가 못 한 걸 해냈구려.",
               "이제부터 낚시광은 당신이오. 나는 그냥 낚시 좋아하는 늙은이고."])),
    dict(id="왕사이드_견습생04", giver="도서관견습생", after="왕사이드_견습생03", lv=60,
         이름="&b왕립 어보", 돈=600000, exp=26000, 칭호="백과사전",
         regs=ALL_REGIONS,
         설명=lambda n: [
             "&7견습 사서 니나: \"봉인이 어떻게 이뤄지는지 봤잖아요. 이름을 지우는 거였죠.\"",
             "&7\"그럼 반대도 되겠죠. &f전부 적어 두면 아무도 못 지워요&7.\"",
             f"&7왕국 모든 물의 물고기 &f{n}종&7을 한 권에 담으세요.",
             "&8왕도의 물은 기억의 연못 하나뿐입니다. 그래서 왕도의 어보는",
             "&8자기 물이 아니라 &f왕국 전부&7의 목록입니다.",
             "&8서버에서 가장 긴 일입니다. 몇 달을 각오하세요."],
         대화=(["봉인이 어떻게 이뤄지는지 보셨잖아요. 이름을 지우는 거였어요.",
               "그럼 반대도 되겠죠. 전부 적어 두면 아무도 못 지워요.",
               "왕국 모든 물의 물고기를 한 권에 — 제 평생 과제예요.",
               "…혼자서는 못 해요. 그래서 부탁드리는 거예요."],
              ["몇 달이 걸릴 거예요. 그래도 포기 안 하실 거죠?"],
              ["…다 찼어요. 정말로 다 찼어요.",
               "이제 이 왕국에서 물고기 한 종이 사라져도, 우리가 압니다.",
               "그게 봉인의 반대말이에요."])),
]

ASK = [{"id": "c1", "text": "부탁을 들어볼게요", "action": "퀘스트목록", "next": "x"},
       {"id": "c2", "text": "조금 더 생각해볼게요", "action": "닫기", "next": "x"}]
TAKE = [{"id": "c1", "text": "보상 받기", "action": "퀘스트목록", "next": "x"}]

rows = []
for c in CAPSTONES:
    qid = c["id"]
    if qid in QUESTS:
        sys.exit(f"✗ {qid} 이 이미 있다 — 두 번 적용됐다")
    n = catchable(c["regs"])
    goals = [f"dogam|{','.join(c['regs'])}|{n}"] + c.get("목표추가", [])
    e = {
        "id": qid, "이름": c["이름"], "설명": c["설명"](n), "목표": goals,
        "타입": "복합", "카테고리": "사이드", "필요레벨": c["lv"],
        "선행퀘스트": c["after"], "보상돈": c["돈"], "보상경험치": c["exp"],
    }
    if c["칭호"]:
        e["보상칭호"] = c["칭호"]
    QUESTS[qid] = e

    giver = c["giver"]
    if giver not in NPCS:
        sys.exit(f"✗ npc.json에 {giver} 없음")
    if c["after"] not in QUESTS:
        sys.exit(f"✗ 선행 {c['after']} 없음")
    qs = NPCS[giver].setdefault("quests", [])
    if qid not in qs:
        qs.append(qid)
    g, pr, dn = c["대화"]
    d = D.setdefault(giver, {})
    d[f"인사/{qid}"] = {"lines": g, "choices": ASK}
    d[f"진행중/{qid}"] = {"lines": pr, "choices": []}
    d[f"퀘스트완료/{qid}"] = {"lines": dn, "choices": TAKE}
    rows.append((qid, giver, n, D_.to_rank(sum(D_.goal_minutes(x) for x in goals)), goals))

if not DRY:
    for path, obj in [(QP, Q), (NP, N), (DP, D)]:
        shutil.copy(path, path + ".pre-capstone")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 78)
for qid, giver, n, r, goals in rows:
    print(f"  {qid:20} {giver:8} {n:4}종  {r:2}칸   {' + '.join(goals)[:48]}")

# ── 검증 ─────────────────────────────────────────────────────────────────────
ok = True
ranks = [r for _, _, _, r, _ in rows]
if ranks != sorted(ranks) or len(set(ranks)) != len(ranks):
    print("✗ 마을 순서대로 굵어지지 않는다:", ranks)
    ok = False
# 어보가 그 마을에서 가장 어려운 사이드인가
TOWN = {"본사이드": "스폰마을", "사사이드": "사막마을",
        "상사이드": "상단마을", "왕사이드": "왕도"}
print("\n마을별 사이드 최고 —")
for pre, t in TOWN.items():
    ks = [k for k, v in QUESTS.items()
          if v.get("카테고리") == "사이드" and k.startswith(pre)]
    best = max(ks, key=lambda k: D_.to_rank(sum(D_.goal_minutes(g) for g in QUESTS[k]["목표"])))
    r = D_.to_rank(sum(D_.goal_minutes(g) for g in QUESTS[best]["목표"]))
    mark = "" if best.endswith(("노인06", "사피르05", "알도03", "견습생04")) else "  ✗ 어보가 최고가 아니다"
    print(f"  {t:5} {best:20} {r:2}칸{mark}")
    if mark:
        ok = False
# 대화 3노드가 다 붙었는가
miss = [c["id"] for c in CAPSTONES
        if any(f"{k}/{c['id']}" not in D.get(c["giver"], {})
               for k in ("인사", "진행중", "퀘스트완료"))]
print("대화 누락:", miss if miss else "없음")
if miss or not ok:
    sys.exit("✗ 검증 실패")
print(f"\n{'(드라이런 — 저장 안 함)' if DRY else '✓ 완료.'} "
      "★다음: add_quest_difficulty.py")
