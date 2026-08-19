#!/usr/bin/env python3
"""NPC·대사·퀘스트 라이브 데이터 정합성 감사.

왜 있나 — 2026-08-20, 3막 입항 컷씬이 2026-08-06부터 **한 번도 실행되지 않았던** 걸 발견했다.
`튜토_선원`의 목표가 `visit|선원`이라 `QuestManager.onVisit`이 방문을 자동완료하고, 호출자가
**대화를 열기 전에 early return** 했다. 컷씬의 유일한 트리거는 그 대화의 `action: "항해"`였다.
에러도 로그도 안 나온다 — 그냥 안 뜬다. 같은 부류를 전역으로 훑어 보니 자기방문 퀘스트 17개에서
완료 대사 15개가 똑같이 묻혀 있었다(왕도15 「왕에게 진실을」 같은 스토리 정점 포함).

그래서 사람 기억이 아니라 정적 검사로 막는다. 이 파일은 훅과 배포 게이트가 같이 쓴다.
  훅   : .claude/settings.json PostToolUse (--hook, stdin으로 훅 JSON)
  배포 : ops/... 또는 ~/deploy-blockship.sh JSON 게이트에서 직접 실행
ERROR 가 하나라도 있으면 exit 1.

수동 실행:  python3 ops/audit-dialogue.py [--dir <폴더>] [--quiet] [--full]
  --full 은 «상시 조건» WARN(대사 없는 NPC 39건 · 죽은 진행중 노드 15건 · 자동생성 대사 461건)까지
  같이 낸다. 편집마다 나오면 진짜 신호가 묻히므로 기본 출력에서는 뺀다.
"""
import json
import os
import re
import sys
import collections

# 라이브 데이터 위치 — dev(맥) 기본값. --dir 나 BLOCKSHIP_DATA 로 덮어쓸 수 있다.
DEFAULT_DIR = ("/Users/user/Library/Application Support/feather/player-server/servers/"
               "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
# 엔진 소스 — 있으면 여기서 choice action 목록을 «파싱»한다(하드코딩은 드리프트한다).
ENGINE_SRC = ("/Users/user/development/blockship-plugin/src/main/java/com/blockship/npc/"
              "NpcDialogueManager.java")
# 엔진 소스를 못 읽을 때만 쓰는 폴백. NpcDialogueManager 의 choice action switch 와 일치해야 한다.
FALLBACK_ACTIONS = {"기본낚싯대", "닫기", "대기열", "대화", "슬롯업그레이드",
                    "여관설정", "퀘스트목록", "포기", "항해"}

# NPC 없이 코드가 직접 부여하는 퀘스트 — QuestManager.FORCE_GRANTED 와 같아야 한다.
FORCE_GRANTED = {"튜토_선원", "튜토_길드"}
# npc.json 에 대응 NPC가 없어도 정상인 대사 키(가상 화자).
VIRTUAL_DIALOGUE = {"인트로"}
# npc.json 의 역할 플래그 — 하나라도 켜져 있으면 «기능형»(닉네임 하늘색 &b)
ROLE_FLAGS = ["ferry", "shop", "inn", "smithy", "islandShop", "scrollShop", "guild", "submit",
              "cooking", "drillShop", "heal", "horseRental", "market", "quest", "casino",
              "appraisal", "villageQuest", "ranking"]
# 「처음 만난 사람」에게만 성립하는 문장 — 제네릭 인사 노드에 이게 있으면 폴백이 참사가 된다
FIRST_MEET = re.compile(r"처음 (보는|뵙|만나|보네|손을|맡는)|신참|초면|누구(시|신)|낯선|어디서 왔")
# 자동생성 티가 나는 문구 — 퀘스트 목표를 기계적으로 문장화한 흔적
BOILERPLATE = ["이번에 맡길 일은", "해야 할 일은", "이번에도 네 솜씨 믿어도", "지난 도움 안 잊었",
               "이 정도면 충분해", "아직 기다리고 있", "다 끝내고 다시 얘기하자",
               "우선 이 일부터 천천히 익혀", "이제 다음 일 생각해도 되겠",
               "지금까지 맡긴 일은 다 끝났", "먼저 .*까지 찾아가는 것부터"]


def uncolor(s):
    return re.sub(r"[&§].", "", s or "").strip()


def load(dirpath):
    def j(name):
        with open(os.path.join(dirpath, name), encoding="utf-8") as f:
            return json.load(f)
    npc = j("npc.json")
    return npc["npcs"], j("dialogue.json"), j("quests.json")


def handled_actions():
    """엔진의 choice action switch 를 소스에서 파싱한다. 실패하면 폴백 + 경고."""
    try:
        src = open(ENGINE_SRC, encoding="utf-8").read()
    except OSError:
        return FALLBACK_ACTIONS, False
    # ★NpcDialogueManager 에는 `switch (c.action)` 이 «두 개» 있다 — 선택지 아이콘 색을 고르는 것과
    #   실제 dispatch. 첫 번째만 잡으면 case 3개만 읽고 나머지 전부를 «모르는 action» 으로 오판한다
    #   (처음에 그렇게 짰다가 707건 오탐이 났다). 그래서 모든 블록의 case 를 합집합으로 모은다.
    #   각 블록은 자기 `default ->` 에서 끊는다 — 중괄호로 끝을 찾으면 첫 case 에서 잘린다.
    acts = set()
    pos = 0
    while True:
        start = src.find("switch (c.action) {", pos)
        if start < 0:
            break
        end = src.find("default ->", start)
        end = len(src) if end < 0 else end
        acts |= set(re.findall(r'case "([^"]+)"', src[start:end]))
        pos = start + 1
    # 파싱이 «성공한 척» 하는 걸 막는 하한선. 리팩터로 블록 모양이 바뀌면 조용히 줄어드는데,
    # 그게 곧 전건 오탐이므로 수상하면 폴백으로 내려간다.
    if len(acts) < 6 or "닫기" not in acts or "퀘스트목록" not in acts:
        return FALLBACK_ACTIONS, False
    return acts, True


def audit(npcs, dlg, qroot, full=False):
    quests = qroot.get("퀘스트", {})
    errors = collections.OrderedDict()
    warns = collections.OrderedDict()

    def err(k, v):
        errors.setdefault(k, []).append(v)

    def warn(k, v):
        warns.setdefault(k, []).append(v)

    actions, parsed = handled_actions()
    if not parsed:
        warn("엔진 action 목록을 소스에서 못 읽어 폴백을 썼다 — 새 action 이 생겼으면 놓친다",
             ENGINE_SRC)

    giver = collections.defaultdict(list)
    for nid, n in npcs.items():
        for q in (n.get("quests") or []):
            giver[q].append(nid)

    # 방문 목표 qid -> 대상 npcId
    vtarget = {}
    for q, v in quests.items():
        for g in (v.get("목표") or []):
            pa = g.split("|")
            if pa[0] == "visit" and len(pa) > 1:
                vtarget[q] = pa[1]

    # 내부 id = 표시이름에 그 id 가 안 들어가는 NPC (대사가 실명 대신 id 를 읽으면 그대로 노출된다)
    internal = {i for i, v in npcs.items() if i not in uncolor(v.get("name", ""))}

    # ── ERROR ────────────────────────────────────────────────────────────
    for npc, nodes in dlg.items():
        for key, node in nodes.items():
            for c in (node.get("choices") or []):
                a = c.get("action")
                if a not in actions:
                    err("엔진이 모르는 choice action — 눌러도 «조용히 대화창만 닫힘»",
                        f"{npc}/{key} action=«{a}» text=«{c.get('text')}»")
                if a == "대화" and c.get("next") not in nodes:
                    err("«대화» 선택지가 없는 노드를 가리킴 — 대사가 «...» 로 뜨고 끝난다",
                        f"{npc}/{key} → «{c.get('next')}»")
            if "/" in key:
                qid = key.split("/", 1)[1]
                if qid not in quests:
                    err("없는 퀘스트를 가리키는 대사 노드", f"{npc}/{key} (퀘스트 «{qid}» 없음)")
            if key.startswith("퀘스트완료"):
                acts = {c.get("action") for c in (node.get("choices") or [])}
                if "퀘스트목록" not in acts:
                    err("퀘스트완료 노드에 «퀘스트목록» 선택지가 없다 — 작성한 대사가 공용 폴백으로 대체된다",
                        f"{npc}/{key} 선택지={sorted(a for a in acts if a) or '없음'}")
            for line in (node.get("lines") or []):
                if re.search(r"[&§]l", line):
                    err("볼드(&l) 사용 — 전역 금지", f"{npc}/{key}: {line}")
                for i in internal:
                    if i in line and re.search(r"(까지|에게|한테)\s*(찾아|가|말)", line):
                        err("대사가 표시이름 대신 NPC 내부 id 를 노출한다",
                            f"{npc}/{key}: {line}  → 실명 «{uncolor(npcs[i]['name'])}»")

    for nid, n in npcs.items():
        if re.search(r"[&§]l", n.get("name") or ""):
            err("볼드(&l) 사용 — 전역 금지", f"npc.json {nid}.name")
        for q in (n.get("quests") or []):
            if q not in quests:
                err("없는 퀘스트를 가리키는 npc.quests", f"{nid} → «{q}»")

    for q, v in quests.items():
        for f in ("선행퀘스트", "다음퀘스트"):
            t = v.get(f)
            if t and t not in quests:
                err("없는 퀘스트 참조", f"{q}.{f} → «{t}»")

    # 체인으로 해금되는데 제공 NPC가 없다 = 그 지점에서 «영구 진행불가»
    # (prod 에서 Lv.17 유저가 본섬01 에 갇혀 있던 사고와 같은 부류)
    for q, v in quests.items():
        nx = v.get("다음퀘스트")
        if not nx or nx not in quests:
            continue
        if nx in FORCE_GRANTED or quests[nx].get("카테고리") in ("일일", "주간"):
            continue
        if not giver[nx]:
            err("체인으로 해금되는데 제공 NPC가 없다 — 그 지점에서 영구 진행불가",
                f"{q} → «{nx}» ({uncolor(quests[nx].get('이름'))})")

    # 퀘스트를 여러 개 주는 NPC에서 «중간 대사 빈 곳» — 인사/<qid> 가 없으면 제네릭 인사로 폴백한다.
    # 제네릭 인사에 첫대면 문장이 들어 있으면, 이미 열 번 만난 상대에게 "자네 같은 신참에게"를 다시 말한다.
    # (2026-08-20 실측: 하겐이 퀘스트 12개 중 알비스00·심해35 에서 정확히 이 상태였다.)
    for nid, n in npcs.items():
        qs = [q for q in (n.get("quests") or []) if q in quests]
        if not qs:
            continue
        nodes = dlg.get(nid, {})
        greeting = " ".join(nodes.get("인사", {}).get("lines") or [])
        first_meet_greeting = bool(FIRST_MEET.search(greeting))
        for q in qs:
            if f"인사/{q}" not in nodes:
                if first_meet_greeting:
                    err("인사/<qid> 가 없어 «첫대면 문장이 든 제네릭 인사»로 폴백한다 — 구면에게 초면 대사",
                        f"{nid}/인사/{q} 없음 → 제네릭 인사: «{greeting[:40]}…»")
                else:
                    warn("인사/<qid> 없음 — 제네릭 인사로 폴백(그 퀘스트 부탁 내용이 사라진다)",
                         f"{nid} → {q} ({uncolor(quests[q].get('이름'))})")
            if f"퀘스트완료/{q}" not in nodes and "퀘스트완료" not in nodes:
                warn("퀘스트완료 대사가 퀘스트별·제네릭 둘 다 없다 — 엔진 하드코딩 폴백(「목표를 해냈구먼!」)으로 나간다",
                     f"{nid} → {q} ({uncolor(quests[q].get('이름'))})")
            if f"진행중/{q}" not in nodes and "진행중" not in nodes:
                warn("진행중 대사가 퀘스트별·제네릭 둘 다 없다 — 엔진 하드코딩 폴백으로 나간다",
                     f"{nid} → {q}")

    # 첫만남 노드가 «영구 미표시»인 NPC — 첫 퀘스트에 선행이 걸려 있으면 shouldShowFirstMeeting 이 항상 false
    for nid, n in npcs.items():
        qs = [q for q in (n.get("quests") or []) if q in quests]
        if not qs or "첫만남" not in dlg.get(nid, {}):
            continue
        prereq = quests[qs[0]].get("선행퀘스트")
        if prereq:
            warn("첫만남 노드가 뜰 수 없다 — 첫 퀘스트에 선행퀘스트가 있어 항상 중간 진입으로 판정된다",
                 f"{nid}/첫만남 (첫 퀘스트 {qs[0]} 의 선행={prereq})")

    byname = collections.defaultdict(list)
    for nid, n in npcs.items():
        byname[uncolor(n.get("name"))].append(nid)
    for nm, ids in byname.items():
        if len(ids) > 1:
            err("uncolored 이름 중복 — 클릭이 첫 매치로만 라우팅된다", f"«{nm}» → {ids}")

    # ── WARN ─────────────────────────────────────────────────────────────
    for nid, n in npcs.items():
        nm = n.get("name") or ""
        m = re.match(r"&([0-9a-fk-or])", nm)
        col = m.group(1) if m else None
        plain = uncolor(nm)
        func = any(n.get(r) for r in ROLE_FLAGS)
        tagged = plain.startswith("[Q]") or plain.startswith("[길잡이]")
        want = "b" if func else ("a" if (tagged or n.get("quests")) else "f")
        # 색코드 없음은 기본 흰색이라 &f 요구와 사실상 같다 → 통과
        if col != want and not (want == "f" and col is None):
            warn("NPC 닉네임 색 규칙 (기능형&b / 퀘스트&a / 대화만&f)",
                 f"{nid} «{plain}» 기대&{want} 실제&{col or '없음'}")
        if full and nid not in dlg:
            warn("대사가 아예 없는 NPC — 클릭하면 «...» 만 뜬다", nid)

    for k in dlg:
        if k not in npcs and k not in VIRTUAL_DIALOGUE:
            warn("npc.json 에 없는 대사 키(고아)", k)

    for q, tgt in vtarget.items():
        if tgt not in giver.get(q, []):
            continue  # 자기방문(제공자==목표)만 본다
        nodes = dlg.get(tgt, {})
        if f"퀘스트완료/{q}" not in nodes:
            warn("자기방문 퀘스트인데 완료 대사가 없다 — 클릭 한 번에 조용히 끝난다",
                 f"{q} «{uncolor(quests[q].get('이름'))}» @{tgt}")
        if full and f"진행중/{q}" in nodes:
            warn("자기방문 퀘스트의 «진행중» 노드는 구조상 뜰 수 없다(클릭=달성) — 죽은 데이터",
                 f"{tgt}/진행중/{q}")

    for npc, nodes in dlg.items():
        for key, node in nodes.items():
            for line in (full and (node.get("lines") or []) or []):
                for b in BOILERPLATE:
                    if re.search(b, line):
                        warn("자동생성 티가 나는 대사(퀘스트 목표를 기계적으로 문장화)",
                             f"{npc}/{key}: {line}")
                        break
            if any(c.get("action") == "퀘스트목록" for c in (node.get("choices") or [])):
                if npc in npcs and not (npcs[npc].get("quests") or []):
                    warn("«퀘스트목록» 선택지가 있는데 그 NPC의 quests 가 비어 있다 — 빈 GUI",
                         f"{npc}/{key}")

    return errors, warns


def render(errors, warns, quiet=False):
    out = []
    ne = sum(len(v) for v in errors.values())
    nw = sum(len(v) for v in warns.values())
    for title, items in errors.items():
        out.append(f"❌ {title} — {len(items)}건")
        for x in items[:12]:
            out.append(f"     {x}")
        if len(items) > 12:
            out.append(f"     … 외 {len(items) - 12}건")
    if not quiet:
        for title, items in warns.items():
            out.append(f"⚠️  {title} — {len(items)}건")
            for x in items[:6]:
                out.append(f"     {x}")
            if len(items) > 6:
                out.append(f"     … 외 {len(items) - 6}건")
    out.append(f"— NPC·대사 감사: ERROR {ne}건 / WARN {nw}건")
    return "\n".join(out), ne


def main():
    argv = sys.argv[1:]
    hook = "--hook" in argv
    quiet = "--quiet" in argv or hook
    dirpath = os.environ.get("BLOCKSHIP_DATA", DEFAULT_DIR)
    if "--dir" in argv:
        dirpath = argv[argv.index("--dir") + 1]

    if hook:
        # 훅 모드 — 관련 파일을 건드린 호출에서만 돈다. 그 외에는 즉시 통과(토큰·시간 0).
        try:
            payload = json.load(sys.stdin)
        except Exception:
            return 0
        blob = json.dumps(payload, ensure_ascii=False)
        if not re.search(r"(npc|dialogue|quests)\.json", blob):
            return 0

    if not os.path.isdir(dirpath):
        # 클라우드 세션 등 라이브 데이터가 없는 환경 — 검사할 게 없으니 조용히 통과한다.
        if not hook:
            print(f"라이브 데이터 폴더 없음: {dirpath}  (검사 생략)")
        return 0

    try:
        npcs, dlg, qroot = load(dirpath)
    except Exception as e:
        print(f"❌ NPC·대사 데이터를 읽지 못했다: {e}", file=sys.stderr)
        return 1

    errors, warns = audit(npcs, dlg, qroot, full="--full" in argv)
    text, ne = render(errors, warns, quiet=quiet)
    if ne:
        print(text, file=sys.stderr)
        # ★훅에서는 exit 2 여야 stderr 가 에이전트에게 «피드백»으로 전달된다.
        #   1로 두면 사용자 화면에만 찍히고 에이전트는 못 보므로 그냥 진행해 버린다.
        return 2 if hook else 1
    if not hook:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
