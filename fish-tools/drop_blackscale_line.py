#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""검은비늘 계열 전면 폐지 (2026-08-14 결정) — 교단은 물을 건드리지 않는다.

■ 왜 없애나
  설정상 교단은 **심연어의 기억(혼)을 모아 부활시키려는** 자들이다. 그런데 방해 수단이
  "물을 오염시켜 기억을 왜곡"이면 **자기가 수확할 밭을 자기가 태우는** 꼴이 된다.
  게다가 "기억을 지운다"는 일은 왕립 대도서관의 **기록 검열**이 이미 하고 있고, 그쪽은
  6챕터 한 장을 통째로 써서 극화된다. 물 오염은 선언만 되고 **한 번도 보여지지 않았다** —
  기억을 잃는 NPC가 한 명도 없다. 같은 일을 하는 장치가 둘인데 하나만 일을 했다.

■ 새 규약 (위반 금지)
  **교단은 물을 오염시키지 않는다.** 수단은 두 가지뿐이다 — **기록을 검열**하고,
  **사람을 산다**(상단·궁정). 물은 순수하게 어부의 놀이터로 남는다.
  「오염어」·「검게 죽은 비늘」·「물을 썩힌다」는 표현을 새로 쓰지 말 것.

■ 대체 — 살아 있는 증거를 **물건 증거**로 옮긴다
  기존 교단 증거는 전부 quest 게이트가 걸린 물건이다(`교단의인장`·`상단화물꼬리표`·
  `밀랍봉인문서`·`녹슨열쇠`·`금서의조각`). 검은비늘붕어만 유일하게 "살아 있는" 증거였고,
  그게 모순의 자리였다. 같은 계열로 흡수한다.

  `본섬07` 「교단의 물고기」  → 「강에 버려진 것」  · `교단의제기` (강)
      폐사당에서 의식을 치른 자들이 **제기를 강에 버렸다.** 본섬06(폐사당)과 직결되고,
      "제단 아래 물길이 마을 앞 강으로 내려간다"는 지리도 그대로 살아난다.
  `심해09` 「오염의 냄새」    → 「해도에 없는 항로」 · `교단의해도` (대양)
      물 표본이 아니라 **해도**를 건진다. 5챕터(상단=교단의 물류)를 회수하면서
      동시에 **검은 섬 방향을 가리키는** 진행형 단서가 된다. 냄새보다 낫다.
  `사막12` 「검은 비늘」      → 「제단이 남긴 것」
      사막의 범죄는 물 **도둑질**이지 오염이 아닌데 이름이 오염을 끌어왔다. 분리한다.

■ 심해 성소는 살린다
  `심해29` 「사육 수조」는 **유지한다.** 다만 용도가 바뀐다 — 열도의 물을 썩히려고 기른 게
  아니라 **의식의 그릇과 파수로 쓰려고 기른** 사역어다. 그래서 「심해어의 가면」이
  **저들이 기른 것의 비늘**로 만들어진다는 논리도 그대로 성립한다.

■ 스크립트 밖에서 해야 할 일
  · 리소스팩 3D 모델 `geom_eunbineulbung_eo` (`FishModelRegistry.java:370`) 고아가 된다.
    맵 항목 제거 + 팩에서 모델 삭제, 또는 새 물건 아이콘으로 전용. **플러그인 소스는 Mac에 있다.**
  · `dialogue.json` 세르간 1 · 테클라 3 노드에 오염 대사가 남아 있으면 함께 손볼 것.

사용법 — quests.json·fish.json이 있는 디렉터리에서:
    python3 drop_blackscale_line.py
"""
import json, re, shutil, sys

QP, FP = "quests.json", "fish.json"
Q = json.load(open(QP, encoding="utf-8"))
F = json.load(open(FP, encoding="utf-8"))
QUESTS, FISH, REGIONS = Q["퀘스트"], F["fish"], F["regions"]
log = []

OLD = "검은비늘붕어"

# ══ fish.json — 어종 정의 교체 ═══════════════════════════════════════════════
if OLD in FISH:
    del FISH[OLD]
    log.append(("fish.json", f"어종 정의 `{OLD}` 삭제"))

for rg, subs in REGIONS.items():
    for sub, lst in subs.items():
        if isinstance(lst, list) and OLD in lst:
            lst.remove(OLD)
            log.append(("fish.json", f"`{OLD}` 제거 — regions.{rg}.{sub}"))

# 기존 물건 증거 5종과 **완전히 같은 스키마**로 만든다 (E등급·크기 1·quest 게이트)
NEW_FISH = {
    "교단의제기": ("강",   "본섬07"),
    "교단의해도": ("대양", "심해09"),
}
for name, (region, gate) in NEW_FISH.items():
    if name in FISH:
        sys.exit(f"✗ `{name}`이 이미 있습니다 — 중단")
    FISH[name] = {"minSize": 1, "maxSize": 1, "grade": "E",
                  "time": "전체", "weather": "전체", "quest": gate}
    sub = REGIONS.get(region)
    if sub is None or "기본" not in sub:
        sys.exit(f"✗ regions.{region}.기본 이 없습니다 — 지역 등록 먼저")
    if name not in sub["기본"]:
        sub["기본"].append(name)
    log.append(("fish.json", f"`{name}` 신설 — regions.{region}.기본 · quest={gate}"))


def setq(qid, **kw):
    e = QUESTS.get(qid)
    if e is None:
        sys.exit(f"✗ {qid} 없음")
    before = {k: e.get(k) for k in kw}
    e.update(kw)
    log.append((qid, (before, {k: e.get(k) for k in kw})))


# ══ 본섬07 — 살아 있는 증거 → 버려진 제기 ════════════════════════════════════
setq("본섬07",
     이름="&e강에 버려진 것",
     목표=["fish|교단의제기|아무|1|0", "material|아무|8"],
     설명=[
         "&7폐사당 아래를 지난 물길은 &f마을 앞 강&7으로 내려갑니다.",
         "&7의식을 치른 자들이 쓰고 버린 것도 함께 떠내려왔습니다.",
         "&7강에서 &f교단의 제기&7를 건져 올리세요.",
         "&8교단은 물을 건드리지 않습니다. 사람과 기록을 건드립니다.",
         "&8의뢰: &7세르간",
     ])

# ══ 사막12 — 오염 용어 분리 ══════════════════════════════════════════════════
setq("사막12",
     이름="&e제단이 남긴 것",
     설명=[
         "&7불의 제단 주변, 오직 붉은사막에서만 잡히는",
         "&f나이프피시&7를 1마리 낚으세요.",
         "&8이 물에서 무슨 의식이 있었는지는 그 몸이 말해 줍니다.",
     ])

# ══ 심해09 — 오염 표본 → 해도 (라이브에 있으면 함께 교체) ═══════════════════
if "심해09" in QUESTS:
    setq("심해09",
         이름="&9해도에 없는 항로",
         목표=["fish|교단의해도|아무|1|0"],
         설명=[
             "&7테클라가 물을 떠 보더니 고개를 젓습니다.",
             "&7\"…깨끗해. 이 물엔 아무 짓도 안 했어.\"",
             "&7\"저들은 물이 아니라 &f사람&7을 산 거야. 상단처럼.\"",
             "&7버려진 &f교단의 해도&7를 건져 올리세요.",
         ])

# ══ 저장 ═════════════════════════════════════════════════════════════════════
for path, obj in ((QP, Q), (FP, F)):
    shutil.copy(path, path + ".pre-blackscale")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

for qid, payload in log:
    if qid == "fish.json":
        print(f"  [fish.json] {payload}")
        continue
    b, a = payload
    print(f"\n[{qid}]")
    for k in a:
        if k == "설명":
            print("   설명:")
            for l in (b[k] or []):
                print("     -", l)
            for l in a[k]:
                print("     +", l)
        else:
            print(f"   {k}: {b[k]} → {a[k]}")

# ── 검증 ─────────────────────────────────────────────────────────────────────
bad = []
for qid, e in QUESTS.items():
    if qid.startswith("심해") or qid.startswith("알비스"):
        continue                      # build_ch7_quests.py 소관 (그쪽도 함께 고쳤다)
    blob = " ".join([e["이름"]] + list(e["설명"]) + list(e["목표"]))
    for word in (OLD, "오염", "썩"):
        if word in blob:
            bad.append(f"{qid}: {word}")

# 게이트 대상 퀘스트가 실제로 그 어종을 요구하는지 (역참조 확인)
for name, (_, gate) in NEW_FISH.items():
    e = QUESTS.get(gate)
    if e and not any(f"|{name}|" in g for g in e["목표"]):
        bad.append(f"{gate}: `{name}` 게이트인데 목표에 없다")

print("\n남은 오염 표현:", bad if bad else "없음")
if bad:
    sys.exit("✗ 검증 실패")

left = [k for k, e in QUESTS.items()
        if any(OLD in g for g in e["목표"])]
print(f"`{OLD}` 잔존 목표:", left if left else "없음")
if left:
    sys.exit("✗ 검증 실패 — 생성기(build_ch7_quests.py)도 함께 고쳤는지 확인")
print("✓ 완료. 반영: /데이터리로드")
print("  ★리소스팩: FishModelRegistry:370 `geom_eunbineulbung_eo` 고아 — Mac에서 별도 정리")
