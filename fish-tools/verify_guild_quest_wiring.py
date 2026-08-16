#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""주간 길드 퀘스트 — 배선 전수 검증 (2026-08-16).

■ 왜 이 스크립트가 필요한가
  이 기능의 **유일한 실패 모드는 조용한 누락**이다. `GuildQuestSpecs`에 템플릿을 추가했는데
  그 verb가 `QuestManager`에서 길드로 흘러가지 않으면 **그 목표만 영원히 0**이고
  에러도 로그도 안 난다. 마인팜 때 겪은 것과 같은 모양이다.

  그래서 「템플릿이 쓰는 verb」 ↔ 「실제로 fan-out 되는 verb」를 **소스에서 직접 읽어** 대조한다.

■ 무엇을 보나
  ① `GuildQuestSpecs`의 템플릿 verb 전부가 길드로 흘러가나
  ② fan-out 이 중복되지 않나 (같은 이벤트가 두 번 세지면 목표가 반값이 된다)
  ③ 신설 verb(`farm`·`submitpts`)가 표시·판정·훅 3곳에 다 있나
  ④ 배수표가 단조증가하고 Lv15 기준 수치가 설계와 맞나

사용법 — 저장소 루트에서 (BLOCKSHIP_SRC 로 플러그인 소스 경로 지정 가능):
    python3 fish-tools/verify_guild_quest_wiring.py
"""
import os, re, sys

ROOTS = [os.environ.get("BLOCKSHIP_SRC", ""),
         os.path.expanduser("~/development/blockship-plugin"),
         "/Users/user/development/blockship-plugin",
         "/workspace/blockship-plugin"]
SRC = next((os.path.join(r, "src/main/java/com/blockship")
            for r in ROOTS if r and os.path.isdir(os.path.join(r, "src/main/java/com/blockship"))), None)
if not SRC:
    sys.exit("✗ blockship-plugin 소스를 못 찾았다 — BLOCKSHIP_SRC 로 경로를 지정할 것")


def read(rel):
    with open(os.path.join(SRC, rel), encoding="utf-8") as f:
        return f.read()


specs = read("guild/GuildQuestSpecs.java")
qm = read("quest/QuestManager.java")
gqm = read("guild/GuildQuestManager.java")
farm = read("crop/VanillaFarmListener.java")
submit = read("island/IslandSubmitManager.java")

ok = True

# ══ ① 템플릿 파싱 ═══════════════════════════════════════════════════════════
TPL = re.findall(
    r'new Tpl\("([^"]+)",\s*(AXIS_\w+),\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]*)",\s*"([^"]*)",\s*(\d+)\)', specs)
if not TPL:
    sys.exit("✗ 템플릿을 하나도 못 읽었다 — GuildQuestSpecs 형식이 바뀌었나")
print(f"템플릿 {len(TPL)}개 · 축 {len({t[1] for t in TPL})}종")

MULT = [float(x) for x in re.search(r'MULT = \{([^}]+)\}', specs).group(1).replace("\n", "").split(",") if x.strip()]
if len(MULT) != 16:
    print(f"✗ 배수표가 16칸이 아니다: {len(MULT)}"); ok = False
if any(MULT[i] <= MULT[i - 1] for i in range(1, len(MULT))):
    print("✗ 배수표가 단조증가가 아니다"); ok = False

# ══ ② verb → fan-out 도달 검사 ═════════════════════════════════════════════
# 직접 gq(p, "<verb>" 를 부르는 것들
DIRECT = set(re.findall(r'gq\(p,\s*"([a-z_]+)"', qm))
# bumpIdCounter / bumpPlainCounter 를 지나가는 verb (이 둘은 내부에서 gq 를 부른다)
VIA_ID = set(re.findall(r'bumpIdCounter\(p,\s*"([a-z_]+)"', qm))
VIA_PLAIN = set(re.findall(r'bumpPlainCounter\(p,\s*"([a-z_]+)"', qm))
if 'gq(p, verb, id, "", amount)' not in qm and 'gq(p, verb, id, "", amount);' not in qm:
    print("✗ bumpIdCounter 안의 길드 fan-out 이 사라졌다"); ok = False
if 'gq(p, verb, "", "", amount)' not in qm:
    print("✗ bumpPlainCounter 안의 길드 fan-out 이 사라졌다"); ok = False

REACH = DIRECT | VIA_ID | VIA_PLAIN
print(f"\nfan-out 도달 verb — 직접 {sorted(DIRECT)}")
print(f"                    bumpId {sorted(VIA_ID)}")
print(f"                    bumpPlain {sorted(VIA_PLAIN)}")

print("\n템플릿별 배선 —")
seen_verbs = set()
for tid, axis, name, verb, arg, grade, base in TPL:
    seen_verbs.add(verb)
    hit = verb in REACH
    how = ("직접" if verb in DIRECT else "") + ("+bumpId" if verb in VIA_ID else "") \
          + ("+bumpPlain" if verb in VIA_PLAIN else "")
    print(f"  {'✅' if hit else '❌'} {tid:16} {verb:10} {how.strip('+') or '— 도달 경로 없음'}")
    if not hit:
        ok = False

# ══ ③ 중복 집계 검사 ═══════════════════════════════════════════════════════
# submitpts 는 onSubmitPoints 가 직접 gq 를 부르므로 bumpIdCounter 쪽은 막혀 있어야 한다.
dup = (DIRECT & VIA_ID) | (DIRECT & VIA_PLAIN) | (VIA_ID & VIA_PLAIN)
guard = '!"submitpts".equals(verb)' in qm
print(f"\n중복 집계 위험 verb: {sorted(dup) if dup else '없음'}")
for v in dup:
    if v == "submitpts" and guard:
        print(f"  ✅ {v} — bumpIdCounter 에 제외 가드 있음")
    else:
        print(f"  ❌ {v} — 같은 이벤트가 두 번 세진다(목표가 반값이 된다)"); ok = False

# ══ ④ 신설 verb 3점 세트 ═══════════════════════════════════════════════════
print("\n신설 verb 배선 —")
CHECKS = [
    ("farm", "표시",  qm, r'case "farm":'),
    ("farm", "판정",  qm, r'"farm", "submitpts" -> target'),
    ("farm", "훅",    qm, r'public void onFarm\('),
    ("farm", "발생원", farm, r'quests\.onFarm\('),
    ("farm", "설치표시 ON", farm, r'onPlace\(BlockPlaceEvent'),
    ("farm", "설치표시 OFF(성장만)", farm, r'onGrow\(BlockGrowEvent'),
    ("farm", "놓고부수기 거부", farm, r'if \(wasPlaced\) return;'),
    ("submitpts", "표시", qm, r'case "submitpts":'),
    ("submitpts", "훅",   qm, r'public void onSubmitPoints\('),
    ("submitpts", "발생원 재료", submit, r'questPoints\(p, "재료"'),
    ("submitpts", "발생원 물고기", submit, r'questPoints\(p, "물고기"'),
    ("submitpts", "발생원 요리", submit, r'questPoints\(p, "요리"'),
]
for verb, part, body, pat in CHECKS:
    hit = re.search(pat, body) is not None
    print(f"  {'✅' if hit else '❌'} {verb:10} {part}")
    if not hit:
        ok = False

# ══ ⑤ 엔진 규약 ════════════════════════════════════════════════════════════
print("\n엔진 규약 —")
ENGINE = [
    ("목표치를 주 시작에 확정", gqm, r'getQuestTarget\(\)\.put\(qid, GuildQuestSpecs\.targetFor'),
    ("금고 즉시 입금", gqm, r'guilds\.deposit\('),
    ("개인 배당 없음(지급 로직 부재)", gqm, r'표시 전용'),
    ("길드원 접속 시 주차 확인", gqm, r'public void onJoin\('),
]
for part, body, pat in ENGINE:
    hit = re.search(pat, body) is not None
    print(f"  {'✅' if hit else '❌'} {part}")
    if not hit:
        ok = False

# ══ ⑥ Lv15 수치 스냅샷 ═════════════════════════════════════════════════════
print("\nLv15 목표 (설계 대조용) —")
for tid, axis, name, verb, arg, grade, base in TPL:
    v = round(int(base) * MULT[15])
    v = round(v, -3) if v >= 10000 else round(v, -2) if v >= 1000 else round(v, -1) if v >= 100 else v
    print(f"  {name:22} {verb}|{arg or '—'}|{grade or '—'}  {v:>9,}")

print(f"\n{'✓ 배선 전수 통과.' if ok else '✗ 검증 실패 — 위 ❌ 를 고칠 것'}")
if not ok:
    sys.exit(1)
