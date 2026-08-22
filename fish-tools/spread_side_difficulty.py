#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""사이드 난이도 스프레드 — 마을마다 봉우리를 만든다 (2026-08-14).

■ 문제
  사이드 난이도가 **아래쪽에 뭉쳐 있고 천장이 없었다.** 마을별 실측:

      스폰마을 43개  1~5칸 26 · 6~10칸 17 · 11+칸 **0**   (최고 9)
      사막마을 27개  1~5칸 17 · 6~10칸  9 · 11+칸  1
      상단마을 21개  1~5칸 13 · 6~10칸  8 · 11+칸 **0**   (최고 10)
      왕도     10개  1~5칸  6 · 6~10칸  3 · 11+칸  1

  어느 마을에서도 "이건 진짜 빡세다" 싶은 게 없다. 게다가 **라인의 마지막 퀘스트가
  중간 퀘스트보다 쉬운** 경우가 널려 있었다 — `본사이드_세르간07`(7단 라인의 종점)이
  1칸, `본사이드_노인05`가 1칸(그냥 방문).

■ 방침 — 라인의 끝을 봉우리로
  ① **라인 캡스톤만 손댄다.** 각 NPC 라인의 최고레벨 퀘스트가 그 라인의 종점이다.
     앞 단계는 그대로 둔다 — 초반이 쉬운 건 옳다.
  ② **마을마다 하나를 더 올려** 마을 캡스톤으로 세운다.
  ③ **절대 낮추지 않는다.** 이미 목표보다 어려우면 건드리지 않는다.

  ⇒ 결과는 마을마다 「1~5 위주 + 6~10 몇 개 + 10칸 이상 하나」의 봉우리 모양이 된다.

■ 난이도는 숫자가 아니라 목표를 올려서 얻는다
  `난이도` 필드만 키우면 거짓말이 된다. `add_quest_difficulty.py`가 **목표에서** 계산하므로
  실제로 **목표를 빡세게** 만든다 — 수량↑, 등급↑, 크기·신선도 조건 추가.
  ★그리고 **설명의 요구 줄도 함께 다시 쓴다.** 안 그러면 설명↔목표 불일치가 재발한다
  (그 버그를 이미 12건 잡았다 — `fix_desc_goal_sync.py`).

■ 히든 3개 — 획득 경로가 없었다
  `히든_수호자`·`히든_사막군주`·`히든_대상인` (전부 Lv60) 이 **선행·다음·NPC 배정이 전부
  없고**, 자바에도 「히든」 카테고리 해금 처리가 없다. 즉 **아무도 받을 수 없다.**
  게다가 셋 다 목표가 `fish|아무|S|1|0`으로 **완전히 동일**해서 이름만 다른 같은 퀘스트였다.
  ⇒ 세력별 수여자를 붙이고, 셋을 서로 다른 시험으로 갈라 놓는다.

사용법 — quests.json·fish.json·npc.json이 있는 디렉터리에서
         (★`add_quest_difficulty.py` **앞에** 돌릴 것 — 목표를 바꾸므로):
    python3 spread_side_difficulty.py
    python3 spread_side_difficulty.py --dry
"""
import json, re, shutil, sys, collections, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

QP, NP, DP = "quests.json", "npc.json", "dialogue.json"
DRY = "--dry" in sys.argv
Q = json.load(open(QP, encoding="utf-8"))
N = json.load(open(NP, encoding="utf-8"))
QUESTS, NPCS = Q["퀘스트"], N["npcs"]
DLG = json.load(open(DP, encoding="utf-8")) if os.path.exists(DP) else None

# 난이도 계산기를 그대로 빌려 쓴다 — 두 곳에 규칙을 두지 않는다.
import add_quest_difficulty as D   # noqa: E402  (side effect: 자기 리포트를 찍는다)

TOWN = {"본사이드": "스폰마을", "사사이드": "사막마을",
        "상사이드": "상단마을", "왕사이드": "왕도"}
# 마을별 (라인 캡스톤 최소, 마을 캡스톤)
# ★라인 최소는 낮게 잡는다. 전부 6으로 밀면 중간대가 과밀해져 "1~5 위주"가 깨진다
#   (첫 시안에서 스폰마을이 1~5칸 17 < 6~10칸 26으로 역전됐다). 라인은 **종점인데
#   앞 단계보다 쉬운 것**만 고치고, 봉우리는 마을 캡스톤 하나로 세운다.
# ★2026-08-15 하향: 마을 캡스톤은 이제 **두 번째** 봉우리다. `add_village_capstones.py`가
#   마을마다 「어보」(12~19칸)를 세우므로 여기서 무리하게 밀 이유가 없다. 예전 값(최대 12)을
#   산정 모델 v2에 그대로 쓰면 도감 요구가 눈덩이처럼 불어난다 — `왕사이드_상인03`(왕실
#   납품상)이 「판매 70 + 10만원 + **도감 66종**」이 되어 버렸다. 주제도 안 맞고 과했다.
TARGET = {"스폰마을": (5, 9), "사막마을": (5, 10), "상단마을": (5, 10), "왕도": (6, 10)}
GRADES = ["E", "D", "C", "B", "A", "S"]
CLEAN = re.compile(r"&[0-9a-fk-or]")


def town_of(qid):
    for p, t in TOWN.items():
        if qid.startswith(p):
            return t
    return None


def rank(e):
    return D.to_rank(sum(D.goal_minutes(g) for g in e["목표"]))


def bump(goal):
    """물고기 목표 한 단계 강화 — 수량 → 등급 → 크기 순으로 조인다."""
    p = goal.split("|")
    if p[0] not in ("fish", "fish_fresh", "harpoon") or p[1] != "아무":
        return None                       # 특정 어종·비낚시 목표는 안 건드린다
    n, gr = int(p[3]), p[2]
    # ★수량을 먼저 조이되 **6마리에서 멈춘다.** 안 그러면 "S등급 12마리" 같은 게 나온다
    #   (첫 시안 `상사이드_레일라06`). 그다음은 등급, 마지막이 크기다.
    if n < 6:
        p[3] = str(n + 1)
    elif gr in GRADES and GRADES.index(gr) < len(GRADES) - 1:
        p[2] = GRADES[GRADES.index(gr) + 1]
        p[3] = str(max(2, n // 2))
    elif int(p[4]) < 80:
        p[4] = str(int(p[4]) + 20)
    else:
        return None
    return "|".join(p)


def goal_text(g):
    p = g.split("|")
    if p[0] not in ("fish", "fish_fresh", "harpoon"):
        return None
    t = "작살로 " if p[0] == "harpoon" else ""
    if p[2] != "아무":
        t += f"&f{p[2]}등급 이상&7 "
    t += f"&f{p[3]}마리&7"
    if p[4] != "0":
        t += f" · &f{p[4]}cm 이상&7"
    if p[0] == "fish_fresh" and len(p) > 5 and p[5] != "0":
        t += f" · &f신선도 {p[5]}+&7"
    return t


def rewrite_desc(e):
    """요구 줄을 다시 쓴다. 분위기 줄은 살리고, 수량/등급이 박힌 줄만 갈아 끼운다."""
    req = [goal_text(g) for g in e["목표"]]
    req = [r for r in req if r]
    if not req:
        return
    keep, tail = [], []
    for l in e["설명"]:
        c = CLEAN.sub("", l)
        if c.startswith("의뢰:"):
            tail.append(l)
        elif re.search(r"\d+\s*마리|등급 이상|\d+\s*cm|신선도\s*\d+", c):
            continue                      # 옛 요구 줄 — 버린다
        else:
            keep.append(l)
    e["설명"] = keep + ["&7" + " + ".join(req) + "&7를 채우세요."] + tail


# ══ 대상 선정 — 라인 캡스톤 ══════════════════════════════════════════════════
SIDE = {k: v for k, v in QUESTS.items() if v.get("카테고리") == "사이드"}
lines = collections.defaultdict(list)
for k, v in SIDE.items():
    m = re.match(r"^([가-힣]+사이드_[가-힣]+)", k)
    if m and town_of(k):
        lines[m.group(1)].append(k)

caps = {}                                  # 라인 → 캡스톤 qid
for ln, ks in lines.items():
    caps[ln] = sorted(ks, key=lambda k: (QUESTS[k]["필요레벨"], k))[-1]

# 마을 캡스톤 = 그 마을에서 **이미 가장 어려운** 사이드. 최고레벨이 아니다.
# ★레벨로 고르면 서사 퀘가 봉우리가 된다 — `상사이드_레일라06`(레일라 후일담, Lv43)이
#   마을 최고 난이도가 되어 버렸다. 감정으로 닫는 에필로그를 최고 난관으로 만들 이유가 없다.
#   이미 제일 빡센 놈을 조금 더 올리는 쪽이 자연스럽고 개입도 작다.
town_cap = {}
for k in SIDE:
    t = town_of(k)
    if not t:
        continue
    if t not in town_cap or (rank(QUESTS[k]), QUESTS[k]["필요레벨"]) > \
                            (rank(QUESTS[town_cap[t]]), QUESTS[town_cap[t]]["필요레벨"]):
        town_cap[t] = k

targets = dict(caps)                       # 라인 캡스톤
for t, k in town_cap.items():               # + 마을 캡스톤(라인 캡스톤이 아닐 수 있다)
    targets.setdefault("마을:" + t, k)

log = []
for ln, qid in sorted(targets.items()):
    e, t = QUESTS[qid], town_of(qid)
    if t not in TARGET:
        continue
    want = TARGET[t][1] if town_cap.get(t) == qid else TARGET[t][0]
    before = rank(e)
    if before >= want:
        continue                           # ★절대 낮추지 않는다
    goals, guard = list(e["목표"]), 0
    while rank({"목표": goals}) < want and guard < 40:
        guard += 1
        idx = next((i for i, g in enumerate(goals) if bump(g)), None)
        if idx is None:
            # 낚시 목표가 없거나 더 못 올린다.
            # ★도감 얹기는 **마을 캡스톤에만** 허용한다 — 라인 종점에 무차별로 붙이면
            #   "잃어버린 목걸이 찾기 + 도감 10종" 같은 뜬금없는 조합이 나온다(첫 시안).
            if town_cap.get(t) != qid:
                break
            reg = {"스폰마을": "강,협곡,항구", "사막마을": "오아시스,붉은사막",
                   "상단마을": "상단마을,대양", "왕도": "강,항구,상단마을"}[t]
            have = next((g for g in goals if g.startswith("dogam|")), None)
            if have:
                p = have.split("|"); p[2] = str(int(p[2]) + 2)
                goals[goals.index(have)] = "|".join(p)
            else:
                goals.append(f"dogam|{reg}|10")
            continue
        goals[idx] = bump(goals[idx])
    if rank({"목표": goals}) == before:
        continue                           # 올릴 수단이 없었다 — 손대지 않는다
    e["목표"] = goals
    rewrite_desc(e)
    log.append((qid, t, before, rank(e), "마을" if town_cap.get(t) == qid else "라인",
                " + ".join(goals)))

# ══ 히든 3개 — 획득 경로 + 서로 다른 시험 ═══════════════════════════════════
HIDDEN = {
    "히든_수호자": ("하겐", ["fish|아무|S|3|0", "dogam|강,협곡,정상,항구|30"],
                 ["&7길드가 조용히 전하는 시험입니다.",
                  "&7&f바르칸의 물을 전부 읽은 자&7만 통과합니다.",
                  "&7&fS등급 3마리&7 · &f본섬 도감 30종&7.",
                  "&8아무도 이 시험을 공표하지 않습니다."]),
    "히든_사막군주": ("유세프", ["fish|아무|S|2|60", "forage|barkan:forage_z_sage|20"],
                  ["&7사막이 사람을 고르는 방식입니다.",
                   "&7&f불의 땅에서 큰 것을 건져 올리고&7, 모래가 기른 것을 모으세요.",
                   "&7&fS등급 60cm 이상 2마리&7 · &f세이지 20개&7.",
                   "&8누가 냈는지는 유세프도 모른다고 합니다."]),
    "히든_대상인": ("이자벨라", ["fish|아무|S|2|0", "money|500000", "sell|60"],
                 ["&7상단이 무너진 뒤에도 이 시험만은 남았습니다.",
                  "&7&f물건을 알아보는 눈&7을 증명하세요.",
                  "&7&fS등급 2마리&7 · &f소지금 500,000원&7 · &f판매 60회&7.",
                  "&8이자벨라: \"내가 낸 게 아니야. 배에 원래 붙어 있던 거지.\""]),
}
# ★수여자를 붙이면 대화 3노드도 따라와야 한다(story.md 「대화 노드 규약」).
#   안 붙이면 NPC가 기본 대사로 떨어져 시험을 주는 장면 자체가 사라진다.
HIDDEN_DLG = {
    "히든_수호자": (["…자네에게만 말하는 걸세. 길드 명부에도 없는 시험이 하나 있어.",
                 "바르칸의 물을 전부 읽고, 그 위에 S등급 셋을 얹으면 통과지.",
                 "누가 만들었는지는 나도 몰라. 내 선대도 몰랐다더군."],
                ["서두를 것 없네. 삼십 년 기다린 시험이야."],
                ["…통과로군. 축하하네.",
                 "이제 자네 이름이 명부에 없는 그 자리에 올라가네."]),
    "히든_사막군주": (["사막이 사람을 고르는 방식이 있소.",
                  "큰 놈 둘과, 모래가 기른 것 스물.",
                  "…내가 낸 시험이 아니오. 나도 전해 들었을 뿐이지."],
                 ["모래는 재촉하지 않소."],
                 ["됐소. 이 땅이 당신을 알아본 거요.",
                  "…나도 이걸 통과한 사람은 처음 보오."]),
    "히든_대상인": (["…이 배에 원래 붙어 있던 종이가 하나 있어.",
                 "상단이 무너질 때도 아무도 안 뗐지. 뗄 생각을 못 했달까.",
                 "물건을 알아보는 눈을 증명하라더군. 해 볼 텐가— 아니, 해 볼 거지?"],
                ["급할 것 없다. 종이는 안 도망가니까."],
                ["…허. 진짜로 해냈군.",
                 "상단은 없어졌는데 그 눈만 남았어. 그게 제일 값나가는 거였는지도."]),
}
ASK = [{"id": "c1", "text": "부탁을 들어볼게요", "action": "퀘스트목록", "next": "x"},
       {"id": "c2", "text": "조금 더 생각해볼게요", "action": "닫기", "next": "x"}]
TAKE = [{"id": "c1", "text": "보상 받기", "action": "퀘스트목록", "next": "x"}]

for qid, (giver, goals, desc) in HIDDEN.items():
    e = QUESTS.get(qid)
    if e is None:
        continue
    e["목표"], e["설명"] = goals, desc
    if giver not in NPCS:
        print(f"※ npc.json에 {giver} 없음 — {qid} 수여자 미배정")
        continue
    cur = NPCS[giver].setdefault("quests", [])
    if qid not in cur:
        cur.append(qid)                   # 히든은 목록 맨 뒤에
    if DLG is not None and qid in HIDDEN_DLG:
        g, pr, dn = HIDDEN_DLG[qid]
        d = DLG.setdefault(giver, {})
        d[f"인사/{qid}"] = {"lines": g, "choices": ASK}
        d[f"진행중/{qid}"] = {"lines": pr, "choices": []}
        d[f"퀘스트완료/{qid}"] = {"lines": dn, "choices": TAKE}
    log.append((qid, "히든", 4, rank(e), f"수여 {giver}", " + ".join(goals)))

# ══ 저장 ═════════════════════════════════════════════════════════════════════
if not DRY:
    for path, obj in [(QP, Q), (NP, N)] + ([(DP, DLG)] if DLG is not None else []):
        shutil.copy(path, path + ".pre-spread")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 78)
print(f"강화 {len(log)}건\n")
for qid, t, b, a, kind, goals in sorted(log, key=lambda r: (r[1], -r[3])):
    print(f"  {t:5} {kind:6} {qid:22} {b:2}칸 → {a:2}칸   {goals[:56]}")

# ── 검증 ─────────────────────────────────────────────────────────────────────
print("\n마을별 결과 —")
ok = True
for t in ("스폰마을", "사막마을", "상단마을", "왕도"):
    ks = [k for k in SIDE if town_of(k) == t]
    d = collections.Counter(rank(QUESTS[k]) for k in ks)
    lo = sum(n for r, n in d.items() if r <= 5)
    mid = sum(n for r, n in d.items() if 6 <= r <= 10)
    hi = sum(n for r, n in d.items() if r >= 11)
    top = max(d)
    print(f"  {t:5} {len(ks):3}개  1~5칸 {lo:3} · 6~10칸 {mid:3} · 11+칸 {hi:2}  (최고 {top}칸)")
    if top < TARGET[t][1]:
        print(f"        ✗ 마을 캡스톤이 목표 {TARGET[t][1]}칸에 못 미친다")
        ok = False

# 설명↔목표 불일치가 재발했는지
bad = []
for k in SIDE:
    e = QUESTS[k]
    d = " ".join(CLEAN.sub("", x) for x in e["설명"])
    for g in e["목표"]:
        p = g.split("|")
        if p[0] in ("fish", "fish_fresh", "harpoon"):
            nums = re.findall(r"(\d+)\s*마리", d)
            if nums and p[3] not in nums:
                bad.append(f"{k} 수량 {p[3]}≠{nums}")
            if p[2] != "아무" and p[2] not in d:
                bad.append(f"{k} 등급 {p[2]} 미언급")
print("\n설명↔목표 불일치:", bad if bad else "없음")
if bad or not ok:
    sys.exit("✗ 검증 실패")
print(f"\n{'(드라이런 — 저장 안 함)' if DRY else '✓ 완료.'} "
      "★다음: add_quest_difficulty.py 를 반드시 다시 돌릴 것")
