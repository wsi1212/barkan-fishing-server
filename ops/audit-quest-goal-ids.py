#!/usr/bin/env python3
"""퀘스트 목표의 «id 인자»가 실제로 발행되는 값인지 대조한다.

★왜 필요했나 — 2026-08-28 발견
  메인 3-7(사막08)이 `mine|iron_ore|8` 이었다. 드릴이 쏘는 id 는 위장 블록 키
  (`brown_stained_glass_pane` 등)와 전리품 matId(`철광석`)뿐이라 `iron_ore` 는
  «아무 에러 없이» 영원히 0/8 이었다 — 메인 퀘스트 라인이 통째로 막혀 있었다.
  목표 문자열은 자유 텍스트라 오타·개명이 조용히 통과한다. 그래서 대조가 필요하다.

권위(하드코딩 금지 — 전부 소스/데이터에서 읽는다):
  mine     → DrillManager 광맥표 (Material 키 소문자 + mineral matId)
  harvest  → CropSpecs.put(new Spec("<id>" ...
  farm     → VanillaFarmListener CROP.put(..., "<id>")
  forage   → forage-types.json 키
  material → materials.json 키 + name
  submitmat→ 같음
  deliver  → parts.json 부품명 + recipes.json 결과명
  cook     → recipes.json 결과 표시명

`아무` 는 어디서나 허용(bumpIdCounter/onForage 가 와일드카드로 처리).
"""
import json, os, re, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JAVA = os.path.expanduser("~/development/blockship-plugin/src/main/java/com/blockship")
LIVE = os.path.abspath(os.path.join(ROOT, "..", "..", "BlockShip"))
DATA = os.path.join(ROOT, "ops", "blockship-data")


def src(rel):
    return open(os.path.join(JAVA, rel), encoding="utf-8").read()


def die(msg):
    print("🔴 " + msg)
    sys.exit(2)


# ── 권위 수집 ────────────────────────────────────────────────────────────
d = src("drill/DrillManager.java")
mine_ids = set()
for m in re.finditer(r'ores\.put\(Material\.(\w+),\s*\n?\s*new Ore\("[^"]*",[^)]*?"([^"]+)",\s*\d+,\s*\d+\)\)', d):
    mine_ids.add(m.group(1).lower())
    mine_ids.add(m.group(2))
if not mine_ids:
    die("DrillManager 광맥표를 못 읽었다 — 정규식이 소스 변경에 뒤처졌다")

harvest_ids = set(re.findall(r'put\(new Spec\("([^"]+)"', src("crop/CropSpecs.java")))
if not harvest_ids:
    die("CropSpecs 를 못 읽었다")

farm_ids = set(re.findall(r'CROP\.put\(Material\.\w+,\s*"([^"]+)"\)', src("crop/VanillaFarmListener.java")))
if not farm_ids:
    die("VanillaFarmListener CROP 표를 못 읽었다")

forage_ids = set(json.load(open(os.path.join(LIVE, "forage-types.json"), encoding="utf-8")))
if not forage_ids:
    die("forage-types.json 이 비었다")

_m = json.load(open(os.path.join(DATA, "materials.json"), encoding="utf-8"))
_m = _m.get("materials", _m)
mat_ids = set(_m) | {v.get("name") for v in _m.values() if isinstance(v, dict) and v.get("name")}
# ★특수작물은 materials.json 에 없다 — CraftingManager 의 lore 규약 `mat:작물_<id>` 로 제출된다
#   (matDisplay 가 `작물_` 접두를 CropSpecs 로 풀어 준다). 그래서 합성 id 를 함께 허용한다.
mat_ids |= {"작물_" + c for c in harvest_ids}

_p = json.load(open(os.path.join(DATA, "parts.json"), encoding="utf-8"))
_p = _p.get("parts", _p)
part_names = set()
for v in (_p if isinstance(_p, list) else _p.values()):
    if isinstance(v, dict):
        part_names.add(v.get("name") or v.get("displayName"))
_r = json.load(open(os.path.join(DATA, "recipes.json"), encoding="utf-8"))["recipes"]
for v in _r.values():
    for f in ("resultPartName", "displayName"):
        if v.get(f):
            part_names.add(v[f])
part_names.discard(None)

CHECK = {
    "mine": ("드릴 광맥", mine_ids),
    "harvest": ("특수작물", harvest_ids),
    "farm": ("바닐라 작물", farm_ids),
    "forage": ("채집물", forage_ids),
    "material": ("재료", mat_ids),
    "submitmat": ("재료", mat_ids),
    "deliver": ("부품", part_names),
    # cook 은 onCook(p, rec.displayName) 이 «공백 그대로» 넘긴다(craft 와 달리 밑줄 정규화가 없다).
    "cook": ("요리 레시피", part_names),
}

# ── 대조 ────────────────────────────────────────────────────────────────
J = json.load(open(os.path.join(DATA, "quests.json"), encoding="utf-8"))
Q = J["퀘스트"]
bad = []
used = collections.Counter()
for qid, v in Q.items():
    for g in v.get("목표", []):
        o = g.split("|")
        verb = o[0]
        if verb not in CHECK or len(o) < 2:
            continue
        label, allowed = CHECK[verb]
        arg = o[1]
        if arg == "아무":
            continue
        used[verb] += 1
        # deliver 는 isDeliverable 이 공백↔밑줄을 정규화한다 — 대조도 같은 기준으로 본다.
        if verb == "deliver":
            arg = arg.replace(" ", "_")
            allowed = {a.replace(" ", "_") for a in allowed}
        if arg not in allowed:
            bad.append((qid, v.get("카테고리", "?"), g, label))

for qid, cat, g, label in bad:
    print(f"🔴 {qid} [{cat}]  {g}  ← {label} 목록에 없는 id")
print(f"— 목표 id 대조: {sum(used.values())}건 검사 / 오류 {len(bad)}건"
      f"  ({', '.join(f'{k}{n}' for k, n in sorted(used.items()))})")
sys.exit(1 if bad else 0)
