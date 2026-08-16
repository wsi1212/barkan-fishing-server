#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""스폰마을 사이드 — 「오스발트의 마인팜」 7단 라인 (2026-08-16).

■ 왜 이 라인인가
  스폰마을 사이드는 전부 **낚시의 곁가지**였다(비늘·실·버섯·도감). 그런데 이 서버에는
  섬·특수작물·자동심기·플라이가 이미 다 있는데도 **그것들을 향하는 퀘스트가 하나도 없다.**
  튜토 졸업 선물로 섬을 받고 나면 아무도 아무 말도 안 해 준다.
  이 라인이 그 자리를 메운다 — 「낚시 말고 밭」이라는 두 번째 축.

■ 성격 — 오래 끌고 가는 배경 과제
  다른 사이드는 앉은자리에서 끝난다. 이건 **Lv5에 시작해 Lv22까지 이어지는** 장기 과제다.
  낚시하다 돌아와서 한 칸씩 미는 물건이라, 목표도 「지금 섬의 상태」로 잡았다
  (경작지 몇 칸 · 방문 몇 회). 카운터가 아니라 상태라 언제 떠났다 돌아와도 이어진다.

■ 난이도 곡선 (add_quest_difficulty.py 산정 기준)
      01 밭 32칸             →  1칸   "자네 혹시 마인팜이라고 아는가...?"
      02 첫 수확 6회          →  6칸
      03 특수 밀 32개 제출     →  8칸
      04 밭 400칸 + 당근 12    →  9칸
      05 밀 64 + 감자 32      → 11칸
      06 밭 2,000칸 + 방문 25 → 12칸
      07 밭 3,000칸 + 토마토 48 + 방문 40 → 13칸  ★캡스톤

  ★방문 목표를 40으로 잡은 이유 — 처음 예시는 100이었는데, **이건 남이 올려 주는 유일한
    수치**다. 동시접속 한 자릿수인 베타 서버에서 100회는 「어렵다」가 아니라 「막힌다」다.
    40이면 하루 한두 명씩 몇 주다 — 밭이 커져서 사람이 오기 시작하는 시점과 맞물린다.
    서버가 커지면 그때 올릴 것.

  ★**스폰마을 어보(`본사이드_노인06`, 12칸)보다 굵다.** 일부러다 — 어보는 「그 마을 물의
    끝」이고 이건 「섬 경영의 끝」이라 축이 다르다. 레벨대도 Lv22까지 넘어간다.
    `add_village_capstones.py`의 "어보가 그 마을 최고 사이드" 검증은 그 스크립트가
    **먼저** 돌아 그 시점 상태만 보므로 깨지지 않는다. 다만 사실은 알고 있을 것.

■ 「한 번에 하나」 잠금과의 관계 — 06·07만 `동시진행: true`
  이 서버는 비-일일 퀘스트를 **한 번에 하나만** 받게 막아 둔다(`QuestGui.hasOtherMain`).
  좋은 규칙이지만 06·07의 `islandvisit`은 **남이 올려 주는 수치**라, 수락한 채로 몇 주를
  기다리는 동안 메인도 사이드도 전부 잠긴다 — 사실상 「받지 마라」가 된다.
  그래서 그 둘만 잠금 밖에 둔다.

  ★이건 「두 퀘스트를 동시에 미는 쌀먹」과 다르다. 마인팜 목표(밭칸·방문·작물 성장)는
    낚시 목표와 **한 동작도 겹치지 않는다.** 한 번 낚아 둘을 채우는 경로가 없다.
    01~05는 혼자 힘으로 끝나므로 그냥 잠금 안에 둔다.

■ 보상 — 밭이 밭을 키운다
  돈·경험치는 다른 사이드 수준으로 두고, **섬 편의**를 준다.
    · `cropseed:<작물>:<수>`  특수작물 씨앗. ★이게 없으면 특수작물 재배를 **시작할 방법이
      아예 없었다** — 그전까지 씨앗은 op `/작물 지급` 전용이었다.
    · `autoplant:<횟수>`      자동심기 추가권 (100 → 500 → 2000)
    · `fly:<분>[:<장수>]`      비행 추가권 (10분 → 20분)
    · `cropbundle:<작물>`     압축 작물 꾸러미 1개 = 산출물 64개. 뒤로 갈수록 낱개 대신 꾸러미.
  마지막에 칭호 `마인팜장`.

■ 자바 의존 (★`ops/patches/minefarm-quest-line.patch` 없이는 안 돈다)
  새 목표 verb 3종 `submitmat` · `farmland` · `islandvisit`,
  새 보상 타입 3종 `cropseed` · `cropbundle` · `fly`/`autoplant`.
  패치를 안 올린 채 이 데이터만 반영하면 그 목표들이 **영원히 0**으로 남는다.

■ 배치 TODO (스크립트가 못 하는 것)
  · Citizens NPC 「오스발트」 생성 → `npc.json`의 `citizensId` 채우기
  · 스폰마을 밭/헛간 근처에 세울 것 (낚시터에서 떨어진 곳이 좋다 — 축이 다르다는 신호)
  · `saves.yml`의 표시이름은 `&a[Q] 오스발트` (초록 = 퀘스트 주는 NPC)

사용법 — quests.json·npc.json·dialogue.json·titles.json이 있는 디렉터리에서
         (★`add_quest_difficulty.py` **앞에**, `add_village_capstones.py` 뒤에):
    python3 add_minefarm_line.py
    python3 add_minefarm_line.py --dry
"""
import json, os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

QP, NP, DP, TP = "quests.json", "npc.json", "dialogue.json", "titles.json"
DRY = "--dry" in sys.argv
Q = json.load(open(QP, encoding="utf-8"))
N = json.load(open(NP, encoding="utf-8"))
D = json.load(open(DP, encoding="utf-8"))
T = json.load(open(TP, encoding="utf-8"))
QUESTS, NPCS, TITLES = Q["퀘스트"], N["npcs"], T["titles"]

# ★`add_quest_difficulty`는 **import만으로 quests.json을 덮어쓴다**(모듈 최상위에서 계산·저장).
#   여기선 `to_rank`/`goal_minutes`만 빌려 쓰므로 argv를 잠깐 --dry로 바꿔 저장을 막는다.
_argv = sys.argv
sys.argv = [_argv[0], "--dry"]
import add_quest_difficulty as D_          # noqa: E402
sys.argv = _argv

GIVER = "오스발트"
ROOT = "튜토11"                            # 졸업 = 섬을 받는 퀘스트. 밭 얘기는 그다음이다.

ASK = [{"id": "c1", "text": "이야기를 들어볼게요", "action": "퀘스트목록", "next": "x"},
       {"id": "c2", "text": "지금은 됐습니다", "action": "닫기", "next": "x"}]
TAKE = [{"id": "c1", "text": "보상 받기", "action": "퀘스트목록", "next": "x"}]

# ══ NPC ════════════════════════════════════════════════════════════════════
# 하얀색(&f)이 아니라 초록(&a[Q]) — 퀘스트를 대화로 주는 NPC다. (CLAUDE.md 색 규칙)
#
# ★이름이 이미 쓰이고 있으면 **멈춘다.** 처음 「구스타프」로 지었다가 그 이름이
#   `&b[랭킹] 구스타프`(기능형 NPC)로 이미 있는 걸 발견했다. 그대로 뒀으면 랭킹판
#   NPC가 퀘스트까지 주는 잡종이 되고, 하늘색/초록 색 규칙도 깨진다.
if GIVER in NPCS:
    sys.exit(f"✗ npc.json에 「{GIVER}」가 이미 있다({NPCS[GIVER].get('name')}) — 다른 이름을 쓸 것")
NPCS[GIVER] = {
    "citizensId": "",                 # ★TODO: Citizens 생성 후 채울 것
    "name": "&a[Q] 오스발트",
    "ferry": False, "shop": False, "inn": False, "smithy": False,
    "islandShop": False, "scrollShop": False, "guild": False, "submit": False,
    "cooking": False, "drillShop": False, "heal": False, "horseRental": False,
    "market": False, "quest": False, "casino": False, "appraisal": False,
    "villageQuest": False, "ranking": False,
    "quests": [], "shopItems": [],
}
if "order" in N and GIVER not in N["order"]:
    N["order"].append(GIVER)

# 첫 대면 — 이 라인 전체의 인장이 되는 대사.
D.setdefault(GIVER, {})
D[GIVER].setdefault("첫만남", {
    "lines": [
        "자네 혹시... 마인팜이라고 아는가?",
        "허허, 모르는 얼굴이군. 하긴 요즘 젊은것들은 죄 물가에만 붙어 있으니.",
        "물고기는 잡으면 없어져. 밭은 안 그래. 한 번 갈아 두면 평생 자네 걸세.",
        "섬을 하나 받았다고 들었네. 흙은 만져 봤나?"],
    "choices": ASK})
D[GIVER].setdefault("인사", {
    "lines": ["왔는가. 흙 냄새가 좋지 않나.",
              "밭은 거짓말을 안 해. 딱 손댄 만큼만 돌려주지."],
    "choices": ASK})
D[GIVER].setdefault("진행중", {
    "lines": ["급할 것 없네. 밭일은 원래 하루아침에 안 끝나."], "choices": []})
D[GIVER].setdefault("퀘스트완료", {
    "lines": ["오, 해냈구먼. 자, 받게."], "choices": TAKE})

# ══ 칭호 ═══════════════════════════════════════════════════════════════════
if "마인팜장" not in TITLES:
    TITLES["마인팜장"] = {
        "name": "&2마인팜장", "color": "&2",
        "desc": "&7섬을 통째로 밭으로 만든 사람", "icon": "hay block",
    }
    if "order" in T and "마인팜장" not in T["order"]:
        T["order"].append("마인팜장")

# ══ 퀘스트 7단 ══════════════════════════════════════════════════════════════
#   (id, Lv, 이름, [목표], 설명, 보상돈, exp, 보상아이템, 대화 3종)
LINE = [
    dict(id="본사이드_마인팜01", lv=5, 이름="&a자네, 마인팜이라고 아는가",
         목표=["farmland|32"],
         설명=["&7오스발트: \"물고기는 잡으면 없어져. 밭은 안 그래.\"",
              "&7자기 섬에 &f경작지 32칸&7을 만드세요.",
              "&8괭이로 흙을 갈면 됩니다. 물이 가까이 있어야 마르지 않아요."],
         돈=1500, exp=250, 아이템="cropseed:밀:6",
         대화=(["자네 섬에 흙이 있지? 괭이로 갈아 보게. 서른두 칸이면 충분하네.",
               "물을 가까이 대 두게. 안 그러면 도로 흙이 돼 버려.",
               "밭이 생기거든 오게. 씨앗은 내가 주지."],
              ["서른두 칸이면 되네. 물 대는 걸 잊지 말고."],
              ["허허, 제법이군. 밭 냄새가 나는구먼.",
               "자, 이건 특수 밀 씨앗일세. 흔한 밀이 아니야."])),

    dict(id="본사이드_마인팜02", lv=6, 이름="&a첫 수확",
         목표=["harvest|밀|6"],
         설명=["&7심었으면 거두는 게 순서지요.",
              "&f특수 밀&7을 &f6번&7 수확하세요.",
              "&8특수 작물은 실시간으로 자랍니다 — 밀은 20분."],
         돈=3000, exp=500, 아이템="crop:밀:16,cropseed:당근:4",
         대화=(["씨앗은 줬으니 이제 자네 차례일세. 밭에 우클릭해서 심게.",
               "특수 밀은 스무 날쯤... 아니, 스무 '분'쯤 걸리네. 요즘 말로.",
               "여섯 번만 거둬 보게. 그러면 감이 올 걸세."],
              ["기다리는 게 일이라네. 그동안 물고기라도 잡으러 가게."],
              ["봤나? 흙은 손댄 만큼 돌려준다니까.",
               "당근 씨앗도 가져가게. 밀만 심으면 밭이 심심하지."])),

    dict(id="본사이드_마인팜03", lv=8, 이름="&a제 손으로 기른 것",
         목표=["submitmat|작물_밀|32"],
         설명=["&7오스발트: \"장에 내다 팔 게 아니라, 나한테 가져와 보게.\"",
              "&f특수 밀 32개&7를 오스발트에게 제출하세요.",
              "&8제출하면 인벤토리에서 실제로 회수됩니다."],
         돈=8000, exp=1200, 아이템="autoplant:100,cropseed:감자:4",
         대화=(["자네가 기른 걸 내 눈으로 보고 싶네. 서른두 개면 되겠어.",
               "사다가 채우려 해도 소용없어 — 특수 밀은 파는 데가 없거든. 허허.",
               "다 모으거든 들고 오게."],
              ["서른두 개일세. 다 모아서 한 번에 가져오게."],
              ["좋아, 좋아. 알이 굵구먼.",
               "이건 자동심기 추가권일세. 거두면 알아서 다시 심어 줘.",
               "손이 줄면 밭을 늘릴 수 있지. 그게 시작이야."])),

    dict(id="본사이드_마인팜04", lv=11, 이름="&a밭은 손이 아니라 머리로",
         목표=["farmland|400", "harvest|당근|12"],
         설명=["&7\"서른두 칸으로는 평생 그 자리일세.\"",
              "&f경작지 400칸&7을 확보하고 &f특수 당근&7을 &f12번&7 수확하세요.",
              "&8섬 경계가 좁으면 &f/섬 업그레이드&8로 넓히세요."],
         돈=18000, exp=2500, 아이템="fly:10:2,cropseed:토마토:4",
         대화=(["사백 칸일세. 놀라지 말게, 밭이란 게 원래 그래.",
               "다 갈고 나면 걸어다니기도 힘들 걸세. 그래서 이걸 주려는 거야.",
               "아, 당근도 열두 번 거둬 오고."],
              ["사백 칸. 섬이 좁거든 경계부터 넓히게."],
              ["이 정도면 밭이라고 불러도 되겠구먼.",
               "비행 추가권일세. 밭 위를 날아다니면 일이 반으로 준다네.",
               "토마토 씨앗도 넣었어. 이건 한 시간짜리라 성질 급한 사람은 못 키우지."])),

    dict(id="본사이드_마인팜05", lv=14, 이름="&a물을 대는 법",
         목표=["submitmat|작물_밀|64", "submitmat|작물_감자|32"],
         설명=["&7\"이제 자네 밭이 나보다 크네. 그럼 값을 해야지.\"",
              "&f특수 밀 64개&7와 &f특수 감자 32개&7를 제출하세요.",
              "&8밀은 20분, 감자는 45분. 한 판에 몰아 심는 게 낫습니다."],
         돈=40000, exp=5000, 아이템="autoplant:500,cropbundle:밀:1",
         대화=(["밀 예순넷, 감자 서른둘. 한 번에 다 대려면 밭이 꽤 필요할 걸세.",
               "요령을 하나 알려 주지 — 자라는 시간이 다른 걸 섞어 심게.",
               "그래야 손이 노는 시간이 없어."],
              ["밀 예순넷에 감자 서른둘. 서두르지 말고."],
              ["…자네, 이제 농부구먼.",
               "이건 압축 꾸러미라는 걸세. 하나에 예순네 개가 들어 있어.",
               "우클릭하면 풀리네. 창고가 좁을 때 요긴하지."])),

    dict(id="본사이드_마인팜06", lv=18, 이름="&6마인팜에는 사람이 온다",
         목표=["farmland|2000", "islandvisit|25"],
         설명=["&7\"밭이 커지면 사람이 오네. 그게 순서야.\"",
              "&f경작지 2,000칸&7을 확보하고 &f섬 방문 25회&7를 받으세요.",
              "&8&f/섬 공개&8 설정과 워프를 열어 두면 사람이 찾아옵니다.",
              "&8★방문은 남이 올려 주는 수치입니다 — 혼자서는 못 채웁니다."],
         돈=70000, exp=8000, 아이템="fly:20:3,cropseed:수박:2,cropbundle:당근:1",
         동시진행=True,
         대화=(["이천 칸. 이제 슬슬 남들 눈에 띌 걸세.",
               "그리고 문을 열어 두게. 스물다섯 번만 다녀가면 되네.",
               "밭은 혼자 보면 밭이지만, 남이 보면 마을이 되거든."],
              ["이천 칸에 방문 스물다섯 번. 사람은 억지로 못 부르니 느긋하게."],
              ["사람이 왔다 갔구먼. 발자국이 보이네.",
               "수박 씨앗을 주지. 하루가 꼬박 걸리는 놈이야 — 자네니까 주는 걸세."])),

    dict(id="본사이드_마인팜07", lv=22, 이름="&6바르칸의 마인팜",
         목표=["farmland|3000", "submitmat|작물_토마토|48", "islandvisit|40"],
         설명=["&7오스발트: \"내가 평생 못 한 걸 자네가 하는군.\"",
              "&f경작지 3,000칸&7 · &f특수 토마토 48개&7 · &f섬 방문 40회&7.",
              "&8이 섬에서 가장 긴 밭일입니다. 몇 주를 각오하세요.",
              "&8완료 시 칭호 &2마인팜장&8을 받습니다."],
         돈=200000, exp=20000,
         아이템="autoplant:2000,fly:20:5,cropbundle:밀:2,cropbundle:토마토:2",
         칭호="마인팜장", 동시진행=True,
         대화=(["마지막일세. 삼천 칸.",
               "…웃지 말게. 나도 젊을 적에 해 보려다 못 했어. 무릎이 먼저 갔지.",
               "토마토 마흔여덟에, 사람도 마흔은 다녀가야 하네.",
               "밭이 그만하면 그건 이제 자네 섬이 아니라 자네 마을일세."],
              ["삼천 칸. 하루에 백 칸씩 갈아도 한 달일세. 천천히 하게."],
              ["…내가 살아서 이걸 볼 줄은 몰랐네.",
               "저기 끝이 안 보이는 게 다 밭이야. 자네가 갈아 놓은 거고.",
               "이제 자네를 마인팜장이라 부르겠네. 내가 못 한 걸 한 사람이니까."])),
]

# ══ 적용 ═══════════════════════════════════════════════════════════════════
rows = []
prev = ROOT
for i, c in enumerate(LINE):
    qid = c["id"]
    if qid in QUESTS:
        sys.exit(f"✗ {qid} 이 이미 있다 — 두 번 적용됐다")
    e = {
        "id": qid, "이름": c["이름"], "설명": c["설명"], "목표": c["목표"],
        "타입": "복합", "카테고리": "사이드", "필요레벨": c["lv"],
        "선행퀘스트": prev, "보상돈": c["돈"], "보상경험치": c["exp"],
        "보상아이템": c["아이템"],
    }
    if c.get("칭호"):
        e["보상칭호"] = c["칭호"]
    if c.get("동시진행"):
        e["동시진행"] = True
    QUESTS[qid] = e
    # 라인은 다음퀘스트로 잇는다 — 첫 칸만 튜토11에 매달고 그다음은 사슬.
    if i > 0:
        QUESTS[prev]["다음퀘스트"] = qid
    prev = qid

    NPCS[GIVER]["quests"].append(qid)
    g, pr, dn = c["대화"]
    D[GIVER][f"인사/{qid}"] = {"lines": g, "choices": ASK}
    D[GIVER][f"진행중/{qid}"] = {"lines": pr, "choices": []}
    D[GIVER][f"퀘스트완료/{qid}"] = {"lines": dn, "choices": TAKE}

    rank = D_.to_rank(sum(D_.goal_minutes(x) for x in c["목표"]))
    mins = sum(D_.goal_minutes(x) for x in c["목표"])
    rows.append((qid, c["lv"], rank, mins, " + ".join(c["목표"])))

if not DRY:
    for path, obj in [(QP, Q), (NP, N), (DP, D), (TP, T)]:
        shutil.copy(path, path + ".pre-minefarm")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

# ══ 리포트 ═════════════════════════════════════════════════════════════════
print("\n" + "=" * 78)
print("  「오스발트의 마인팜」 — 스폰마을 사이드 7단")
print("=" * 78)
for qid, lv, rank, mins, goals in rows:
    print(f"  {qid:20} Lv{lv:<3} {rank:2}칸 {mins:6.0f}분   {goals}")

# ══ 검증 ═══════════════════════════════════════════════════════════════════
ok = True

# ① 난이도가 단조증가하는가 — 「밀수록 어려워진다」가 이 라인의 전부다
ranks = [r for _, _, r, _, _ in rows]
if any(ranks[i] < ranks[i - 1] for i in range(1, len(ranks))):
    print("\n✗ 난이도가 도중에 내려간다:", ranks); ok = False
else:
    print(f"\n난이도 곡선: {' → '.join(str(r) for r in ranks)}  ✓ 단조증가")

# ② 레벨도 단조증가하는가
lvs = [lv for _, lv, _, _, _ in rows]
if any(lvs[i] < lvs[i - 1] for i in range(1, len(lvs))):
    print("✗ 필요레벨이 역행한다:", lvs); ok = False

# ③ 체인이 끊기지 않는가 (선행 ↔ 다음 상호 정합)
for i, c in enumerate(LINE):
    want = ROOT if i == 0 else LINE[i - 1]["id"]
    if QUESTS[c["id"]]["선행퀘스트"] != want:
        print(f"✗ {c['id']} 선행 어긋남"); ok = False
    if i > 0 and QUESTS[want].get("다음퀘스트") != c["id"]:
        print(f"✗ {want} → {c['id']} 배선 누락"); ok = False
if ROOT not in QUESTS:
    print(f"✗ 뿌리 {ROOT} 가 없다"); ok = False

# ④ ★visit 목표를 섞지 않았는가 — QuestManager.onVisit은 visit 목표가 하나라도
#    맞으면 그 퀘스트를 통째로 완료시킨다(다른 목표를 안 본다). 치명적 함정.
for c in LINE:
    if any(g.startswith("visit|") for g in c["목표"]) and len(c["목표"]) > 1:
        print(f"✗ {c['id']}: visit을 다른 목표와 섞었다"); ok = False

# ⑤ 대화 3노드가 다 붙었는가
miss = [c["id"] for c in LINE
        if any(f"{k}/{c['id']}" not in D[GIVER] for k in ("인사", "진행중", "퀘스트완료"))]
print("대화 누락:", miss if miss else "없음")
if miss:
    ok = False

# ⑥ 보상 spec이 자바가 아는 타입인가 (오타 = 조용히 아무것도 안 줌)
KNOWN = {"crop", "cropseed", "cropbundle", "dish", "trap", "mat", "harpoon", "part",
         "fly", "autoplant"}
for c in LINE:
    for entry in c["아이템"].split(","):
        head = entry.split(":")[0].strip()
        if head not in KNOWN:
            print(f"✗ {c['id']}: 알 수 없는 보상 타입 '{head}'"); ok = False

# ⑦ 자바 패치 전제 — 새 verb를 자바가 모르면 진행도가 영원히 0이다
NEW_VERBS = {"submitmat", "farmland", "islandvisit"}
used = {g.split("|")[0] for c in LINE for g in c["목표"]} & NEW_VERBS
print(f"자바 패치 필요 verb: {sorted(used)}  → ops/patches/minefarm-quest-line.patch")

# ⑧ 스폰마을 안에서의 자리 — 어보보다 굵다는 걸 눈으로 확인하고 넘어간다
peers = [(k, D_.to_rank(sum(D_.goal_minutes(g) for g in v["목표"])))
         for k, v in QUESTS.items()
         if v.get("카테고리") == "사이드" and k.startswith("본사이드")]
peers.sort(key=lambda x: -x[1])
print("\n스폰마을 사이드 상위 5 —")
for k, r in peers[:5]:
    print(f"  {r:2}칸  {k}")

print(f"\n{'(드라이런 — 저장 안 함)' if DRY else '✓ 완료.'}")
print("★TODO — Citizens 「오스발트」 생성 후 npc.json citizensId 채우기 (스폰마을 밭 근처)")
print("★다음: add_quest_difficulty.py")
if not ok:
    sys.exit("✗ 검증 실패")
