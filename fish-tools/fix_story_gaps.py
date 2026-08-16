#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""남은 서사 구멍 일괄 보수 (2026-08-14) — 전수 검토 지적 중 텍스트·데이터로 닫히는 전부.

⑤ 영주성 사본 회수가 설정만 있고 장면이 없다
   story.md는 "왕도08 시점에 영주성 서고의 사본이 대조 증거가 된다"고 적어 뒀는데
   `왕도08`의 목표는 `visit|필경사` 하나뿐이었다. 2챕터와 6챕터를 잇는 가장 좋은 카드가
   문서에만 있었다. → **`왕도08b` 「지방의 사본」 신설** — 영주성 사관에게 다시 간다.

⑥ 상단 붕괴가 화면 밖에서 일어난다
   5챕터에서 문서를 건진 게 마지막이고 7챕터에 "상단이 무너진 뒤" 한 줄뿐이었다.
   → `왕도06`(귀환, 그리고 보고) 설명에 처리 결과를 싣는다.

⑩ 폐사당(대수림)과 강 오염의 인과가 없다
   무대를 갈라놓고 나니 두 사건이 병렬로 떴다. → 폐사당 아래를 지나는 물길로 잇는다.

⑬ 6챕터 밀도 붕괴 — Lv40~50을 10퀘로 커버(109분/퀘). 목표도 `visit` 6개로 단조롭다.
   → **4개 신설**(08b·09b·11b·12b), verb를 전부 다르게 준다. 14퀘가 된다.

⑭ 튜토(Lv5 종료)와 본섬01~05(Lv1~5)의 레벨 역전 → 5·5·6·6·6으로 정리.

사용법 — quests.json·npc.json이 있는 디렉터리에서:
    python3 fix_story_gaps.py
"""
import json, os, shutil, sys

QP, NP, DP = "quests.json", "npc.json", "dialogue.json"
Q = json.load(open(QP, encoding="utf-8"))
N = json.load(open(NP, encoding="utf-8"))
QUESTS, NPCS = Q["퀘스트"], N["npcs"]
DLG = json.load(open(DP, encoding="utf-8")) if os.path.exists(DP) else None
log = []

ASK = [{"id": "c1", "text": "부탁을 들어볼게요", "action": "퀘스트목록", "next": "x"},
       {"id": "c2", "text": "조금 더 생각해볼게요", "action": "닫기", "next": "x"}]
TAKE = [{"id": "c1", "text": "보상 받기", "action": "퀘스트목록", "next": "x"}]


def dnodes(npc, qid, greet, doing, done):
    """★신설 퀘스트엔 대화 노드가 따라와야 한다 — 없으면 NPC가 기본 대사로 떨어진다."""
    if DLG is None:
        return
    d = DLG.setdefault(npc, {})
    d[f"인사/{qid}"] = {"lines": greet, "choices": ASK}
    d[f"진행중/{qid}"] = {"lines": doing, "choices": []}
    d[f"퀘스트완료/{qid}"] = {"lines": done, "choices": TAKE}
    log.append((f"{npc}.*/{qid}", "대화 3노드 신설"))


def q(qid):
    e = QUESTS.get(qid)
    if e is None:
        sys.exit(f"✗ {qid} 없음")
    return e


# ══ ⑭ 레벨 역전 — 튜토를 Lv5에 졸업하는데 본섬01~04가 Lv1~4였다 ═══════════════
for qid, lv in (("본섬01", 5), ("본섬02", 5), ("본섬03", 6), ("본섬04", 6), ("본섬05", 6)):
    e = q(qid)
    log.append((qid, f"필요레벨 {e['필요레벨']} → {lv}"))
    e["필요레벨"] = lv

# ══ ⑩ 폐사당과 강을 잇는다 ═══════════════════════════════════════════════════
e = q("본섬06")
e["설명"] = [
    "&7강 너머 &f대수림&7 깊은 곳, 버려진 폐사당 터.",
    "&7건물은 멀쩡한데 사람이 다녀간 자국만 새것입니다.",
    "&8제단 아래로 물길이 지납니다. &7그 물이 어디로 내려가는지 보세요.",
    "&8의뢰: &7세르간",
]
log.append(("본섬06", "폐사당 아래 물길 — 강과 잇는 고리"))

e = q("본섬07")
e["설명"] = [
    "&7폐사당 아래를 지난 물길은 &f마을 앞 강&7으로 내려갑니다.",
    "&7그 강에서 비늘이 검게 죽은 놈이 올라오기 시작했습니다.",
    "&7&f검은비늘붕어&7를 1마리 잡으세요.",
    "&8교단은 땅을 뺏지 않습니다. 물을 썩혀 기억을 지웁니다.",
]
log.append(("본섬07", "오염의 출처를 폐사당 물길로 연결"))

# ══ ⑥ 상단 붕괴를 화면 안으로 ═════════════════════════════════════════════════
e = q("왕도06")
e["설명"] = [
    "&7안개 너머에서 본 것을 왕에게 고하러 돌아갑니다.",
    "&8도란과 마르코는 끌려갔고 상단은 해체됐습니다.",
    "&8은빛 갈매기호는 왕실에 압류됐습니다 — 그런데도 끝난 것 같지 않습니다.",
    "&7왕도로 향하세요.",
]
log.append(("왕도06", "상단 처리 결과를 명시 — 붕괴가 화면 밖이었다"))

# ══ ⑬ + ⑤ 6챕터 4개 신설 ════════════════════════════════════════════════════
#   verb를 전부 다르게 준다(visit 6개로 단조롭던 장이다).
NEW = [
    ("왕도08b", 43, "이동", "&9지방의 사본", "사관", ["visit|사관|사관 게르하르트"],
     ["&7왕도의 원본은 위조됐습니다. 대조할 것이 필요합니다.",
      "&7&f영주성 서고&7 — 궁정이 손대지 못한 사본이 거기 있습니다.",
      "&7발데마르가 보고를 미룬 덕에 남은 유일한 기록입니다.",
      "&7사관 &f게르하르트&7를 다시 찾아가세요."]),

    ("왕도09b", 45, "재료", "&9금서고의 값", "금서고지기", ["material|아무|20"],
     ["&7금서고 지기: \"열쇠는 있소. 다만 공짜는 아니지.\"",
      "&7봉인 서가를 여는 데도 대가가 듭니다.",
      "&f재료 20개&7를 모아 오세요."]),

    ("왕도11b", 46, "물고기", "&9종탑의 밤", "종지기", ["fish_fresh|아무|A|4|0"],
     ["&7신호는 밤에만 올라갑니다. 종탑 아래에서 밤을 새웁니다.",
      "&7기다리는 동안 손은 놀리지 않습니다.",
      "&f신선도를 지킨 A등급 이상 4마리&7를 올리세요."]),

    ("왕도12b", 47, "조합", "&9첨탑의 손님", "은둔학자", ["craft|아무|4"],
     ["&7첨탑 정상. 늙은 학자의 도구는 죄다 삭아 있습니다.",
      "&7\"…손님이 온 게 몇 해 만인지 모르겠군.\"",
      "&f조합 4회&7로 낡은 것들을 갈아 끼워 주세요."]),
]

# 체인 재배선 — 08 → 08b → 09 → 09b → 10 → 11 → 11b → 12 → 12b → 13
LINK = [("왕도08", "왕도08b"), ("왕도08b", "왕도09"),
        ("왕도09", "왕도09b"), ("왕도09b", "왕도10"),
        ("왕도11", "왕도11b"), ("왕도11b", "왕도12"),
        ("왕도12", "왕도12b"), ("왕도12b", "왕도13")]

for qid, lv, typ, name, giver, goals, desc in NEW:
    if qid in QUESTS:
        sys.exit(f"✗ {qid}가 이미 있습니다 — 중단")
    if giver not in NPCS:
        sys.exit(f"✗ npc.json에 {giver} 없음")
    QUESTS[qid] = {
        "id": qid, "이름": name, "설명": desc, "목표": goals,
        "타입": typ, "카테고리": "메인", "필요레벨": lv,
        "보상돈": 30000 + (lv - 40) * 2000, "보상경험치": 1400 + (lv - 40) * 120,
        "마을": "왕도",
    }
    cur = NPCS[giver].setdefault("quests", [])
    if qid not in cur:
        cur.insert(0, qid)          # 메인은 사이드보다 앞에
    log.append((qid, f"신설 Lv{lv} {goals} (수여 {giver})"))


# ── 신설 4개의 대화 ──────────────────────────────────────────────────────────
dnodes("사관", "왕도08b",
       ["또 뵙는군요. 왕도에서 오셨다니… 짐작은 갑니다.",
        "궁정이 손대지 못한 사본이 여기 남아 있습니다.",
        "영주께서 보고를 미루신 덕이지요. 아이러니한 일입니다."],
       ["서고 안쪽입니다. 천천히 보십시오."],
       ["대조가 끝났군요. 왕도의 원본이 위조라는 것이 이걸로 증명됩니다.",
        "…이 기록을 지운 자는 궁정 안에 있습니다. 조심하십시오."])

dnodes("금서고지기", "왕도09b",
       ["열쇠는 있소. 다만 공짜는 아니지.",
        "봉인 서가를 여는 데도 대가가 드는 법이오.",
        "재료 20개를 모아 오시오."],
       ["아직 부족하오. 봉인은 값을 치러야 열리는 법이지."],
       ["됐소. 이제 그 문을 열어 드리리다.",
        "…들어가고 나면, 못 본 걸로 하고 싶어질 거요."])

dnodes("종지기", "왕도11b",
       ["신호는 밤에만 올라간다오. 종탑 아래서 밤을 새워야 하지요.",
        "기다리는 동안 손은 놀리지 마시오.",
        "신선도를 지킨 A등급 이상으로 4마리."],
       ["아직 밤이 깊지 않았소. 종은 내가 지키리다."],
       ["보셨소? 저 불빛. 매일 같은 각도로 바다 너머를 향하지요.",
        "저건 신호요. 이 성 안 누군가가 보내는."])

dnodes("은둔학자", "왕도12b",
       ["…손님이 온 게 몇 해 만인지 모르겠군.",
        "보다시피 도구는 죄다 삭았네. 첨탑 꼭대기라 습기가 심해서.",
        "조합 네 번이면 쓸 만하게 갈아 끼울 수 있을 걸세."],
       ["급할 것 없네. 나는 여기서 삼십 년을 기다렸으니."],
       ["오, 손에 맞는군. 고맙네.",
        "…이제 자네가 찾는 이야기를 해도 되겠구먼. 앉게."])

for a, b in LINK:
    q(a)["다음퀘스트"] = b
    q(b)["선행퀘스트"] = a
log.append(("체인", " → ".join(["왕도08", "왕도08b", "왕도09", "왕도09b", "왕도10",
                                "왕도11", "왕도11b", "왕도12", "왕도12b", "왕도13"])))

# ══ 저장 ═════════════════════════════════════════════════════════════════════
for path, obj in [(QP, Q), (NP, N)] + ([(DP, DLG)] if DLG is not None else []):
    shutil.copy(path, path + ".pre-gaps")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

for qid, why in log:
    print(f"  {qid:10} {why}")

# ── 검증 ─────────────────────────────────────────────────────────────────────
cur, seen, chain = "튜토_길드", set(), []
while cur and cur in QUESTS and cur not in seen:
    seen.add(cur); chain.append(cur); cur = QUESTS[cur].get("다음퀘스트")
lv, bad = 0, []
for k in chain:
    v = QUESTS[k].get("필요레벨", 0)
    if v < lv:
        bad.append((k, lv, v))
    lv = max(lv, v)
ch6 = [k for k in chain if k.startswith("왕도") and QUESTS[k]["필요레벨"] >= 40]
print(f"\n체인 {len(chain)}단 · 끝 {chain[-1]}")
print(f"레벨 역전: {bad if bad else '없음'}")
print(f"6챕터: {len(ch6)}개 (Lv40~50) — {' '.join(ch6)}")
# ★심해*는 build_ch7_quests.py가 권위라 여기서 고치지 않는다(그쪽에서 이미 수정됨).
mix = [k for k in chain
       if any(g.startswith("visit|") for g in QUESTS[k]["목표"]) and len(QUESTS[k]["목표"]) > 1
       and not k.startswith("심해")]
skipped = [k for k in chain
           if any(g.startswith("visit|") for g in QUESTS[k]["목표"]) and len(QUESTS[k]["목표"]) > 1
           and k.startswith("심해")]
print(f"visit 혼합: {mix if mix else '없음'}"
      + (f"  (심해는 생성기 소관: {skipped})" if skipped else ""))
assigned = {x for v in NPCS.values() for x in (v.get("quests") or [])}
miss = [k for k, v in QUESTS.items() if v.get("카테고리") == "메인" and k not in assigned]
print(f"메인 미배정: {miss if miss else '없음'}")
if bad or mix or miss:
    sys.exit("✗ 검증 실패")
print("\n✓ 완료. 반영: /데이터리로드 + /npc동기화")
