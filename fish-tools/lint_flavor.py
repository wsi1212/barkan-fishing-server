#!/usr/bin/env python3
"""아이템 한줄 설명(item-flavor.json) 품질 린트.

집필 품질을 사람 눈에만 맡기지 않기 위한 기계 검증. item-flavor-plan.md 6장 규약 구현.
  - 커버리지: 카테고리별 대상 목록 대비 누락 / 존재하지 않는 키(오타)
  - 길이: 원문 60자 초과, 줄바꿈 후 3줄 되는 항목
  - 중복: 완전 동일 문장, 유사도 높은 쌍 (색칠놀이 방지)
  - 관용구 편중: 같은 어미/표현이 전체의 5% 초과
  - 유머 비율: 물음표/감탄부호 포함 항목이 25% 초과 (물고기 기준)
  - 금칙: 이모지, 밈, 스탯 수치, 볼드 코드
  - 등급 톤: M/L/G 등급 물고기에 물음표/감탄부호 금지

사용: python3 fish-tools/lint_flavor.py [--strict]
  --strict 면 경고도 실패로 취급 (CI/배포 전 게이트용)
"""
import json, os, re, sys, unicodedata
from collections import Counter
from difflib import SequenceMatcher

PLUG = os.path.expanduser("~/Library/Application Support/feather/player-server/servers/"
                          "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
JAVA_SRC = os.path.expanduser("~/development/blockship-plugin/src/main/java/com/blockship")

FLAVOR = os.path.join(PLUG, "item-flavor.json")
WRAP = 30            # ItemFlavor.WRAP 과 동일
MAX_RAW = 60         # 원문 최대 길이
MAX_LINES = 2        # 줄바꿈 후 최대 줄 수
SIMILAR = 0.80       # 유사 문장 판정 임계
IDIOM_SHARE = 0.05   # 한 관용구가 차지할 수 있는 최대 비율
HUMOR_MIN = 0.08     # 유머 항목 최소 비율 (전부 도감 설명문이면 밋밋하다)
HUMOR_MAX = 0.25     # 유머 항목 최대 비율 (전부 농담이면 세계관이 가벼워진다)
STRUCT_MAX = 0.90    # "명사구. 부연문." 2문장 골격이 차지할 수 있는 최대 비율

# 유머 판정 — 물음표 + 화자가 슬쩍 끼어드는 어투(권유/체념/자조). ?만 세면 건조한 농담을 놓친다.
HUMOR_PAT = re.compile(
    r"(\?|[가-힣]자\.$|싶다|말리진|각오|감수|헷갈|아깝|성의가 없|신세|되묻|얕보|"
    r"소심|시끄럽|모자란다|미움|손해|일쑤|줄지를|왜 시작|자존심|손을 못 뗀다|"
    r"놀랍다|겨우|끝이다|여러 가지다|두 배로)")

# 반복되면 AI티가 나는 관용구 (부분 문자열로 카운트)
IDIOMS = ["라고 전해진다", "로 유명하다", "라고 한다", "으로 알려져", "로 알려져",
          "하는 것으로 유명", "라 불린다", "이라고 불린다", "말이 있다"]
BANNED_PAT = [
    (re.compile(r"[§&][lL]"), "볼드 코드(§l/&l) — 전역 금지"),
    (re.compile(r"[0-9]+\s*%"), "스탯 수치(%) — 밸런스 변경 시 거짓말이 된다"),
    (re.compile(r"[!?]{2,}"), "감탄/의문 부호 연속"),
    (re.compile(r"\.{4,}"), "말줄임표 과다"),
    # "갓"은 버섯 갓(cap)과 충돌해 제외 — 밈 용법은 대개 "갓+명사"라 오탐이 훨씬 잦다
    (re.compile(r"(가성비|혜자|ㅋㅋ|ㄷㄷ|레전드|치트키|사기템|꿀잼)"), "밈/인터넷 슬랭"),
    (re.compile(r"(개발자|서버|플레이어|유저|리스폰|아이템창)"), "4th wall / 게임 시스템 용어"),
]


def is_emoji(ch):
    return unicodedata.category(ch) == "So" or ord(ch) > 0x1F000


def wrap(text, width=WRAP):
    lines, cur = [], ""
    for w in text.split():
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= width:
            cur += " " + w
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def load_targets():
    """카테고리 → {키: 표시명} 기대 목록. 라이브 JSON/자바 소스가 권위."""
    t = {}

    # 물고기 — 지역/환경에 배정된 어종만 (고아 97종은 집필 제외, plan Phase 0)
    fish = json.load(open(os.path.join(PLUG, "fish.json"), encoding="utf-8"))
    reachable = set()
    for subs in fish["regions"].values():
        for lst in subs.values():
            reachable.update(lst)
    for lst in fish["environment"].values():
        reachable.update(lst)
    t["물고기"] = {n: n for n in sorted(reachable) if n in fish["fish"]}

    # 부품 — parts.json 전 카테고리
    parts = json.load(open(os.path.join(PLUG, "parts.json"), encoding="utf-8"))["parts"]
    t["부품"] = {n: n for cat in parts.values() for n in cat}

    # 재료 — materials.json
    mats = json.load(open(os.path.join(PLUG, "materials.json"), encoding="utf-8"))["materials"]
    t["재료"] = {k: (v.get("name") or k) for k, v in mats.items()}

    # 채집 — forage-types.json (키 = 표시명, CE lore가 이름으로 매칭)
    forage = json.load(open(os.path.join(PLUG, "forage-types.json"), encoding="utf-8"))
    t["채집"] = {v["name"]: v["name"] for v in forage.values()}

    # 작물/요리/통발 — 자바 소스가 단일 소스라 소스에서 id 추출
    t["작물"] = ids_from("crop/CropSpecs.java", r'new Spec\("([^"]+)"')
    t["요리"] = ids_from("cooking/DishSpecs.java", r'(?:buff|submit|heal)\("([^"]+)"')
    t["통발"] = ids_from("trap/TrapSpecs.java", r'new Spec\("([^"]+)"')

    # 지역 — 도감 「지역」 탭에 실제로 노출되는 지역만(자기 물고기 있는 비섬 지역, MainDexGui.regionDexList
    # 필터 미러). 길드섬/개인섬은 도감에 안 뜨므로 제외.
    regions = json.load(open(os.path.join(PLUG, "regions.json"), encoding="utf-8"))
    OWN_SUBS = {"기본", "낮", "낮맑음", "낮비", "밤", "밤맑음", "밤비", "통발"}
    def has_own_fish(rid):
        subs = fish["regions"].get(rid, {})
        return any(k in OWN_SUBS and v for k, v in subs.items())
    t["지역"] = {rid: (r.get("displayName") or rid) for rid, r in regions.items()
                if not rid.startswith("길드섬_") and not rid.startswith("개인섬_") and has_own_fish(rid)}
    return t


def ids_from(rel, pattern):
    path = os.path.join(JAVA_SRC, rel)
    if not os.path.exists(path):
        print(f"  ⚠ 소스 없음 (대상 목록 스킵): {path}")
        return {}
    src = open(path, encoding="utf-8").read()
    return {m: m for m in re.findall(pattern, src)}


def fish_grades():
    fish = json.load(open(os.path.join(PLUG, "fish.json"), encoding="utf-8"))["fish"]
    return {k: (v.get("grade") or "") for k, v in fish.items()}


def main():
    strict = "--strict" in sys.argv
    if not os.path.exists(FLAVOR):
        print(f"✗ {FLAVOR} 없음"); return 1
    data = json.load(open(FLAVOR, encoding="utf-8"))
    targets = load_targets()
    grades = fish_grades()

    errors, warns = [], []
    total = 0

    for cat, expected in targets.items():
        got = data.get(cat) or {}
        total += len(got)
        missing = [k for k in expected if not (got.get(k) or "").strip()]
        unknown = [k for k in got if k not in expected]
        done = len(expected) - len(missing)
        print(f"[{cat}] {done}/{len(expected)}"
              + (f"  누락 {len(missing)}" if missing else "")
              + (f"  ✗알수없는키 {len(unknown)}" if unknown else ""))
        if unknown:
            errors.append(f"{cat}: 존재하지 않는 아이템 키 {unknown[:10]}")
        if missing and strict:
            errors.append(f"{cat}: 설명 누락 {len(missing)}개 (예: {missing[:5]})")

        for key, text in got.items():
            text = (text or "").strip()
            if not text:
                continue
            where = f"{cat}/{key}"
            if len(text) > MAX_RAW:
                errors.append(f"{where}: 원문 {len(text)}자 (최대 {MAX_RAW})")
            if len(wrap(text)) > MAX_LINES:
                warns.append(f"{where}: 줄바꿈 후 {len(wrap(text))}줄 (권장 {MAX_LINES})")
            for ch in text:
                if is_emoji(ch):
                    errors.append(f"{where}: 이모지 '{ch}'"); break
            for pat, why in BANNED_PAT:
                if pat.search(text):
                    errors.append(f"{where}: {why} — \"{text}\"")

        # 중복 / 유사
        items = [(k, v.strip()) for k, v in got.items() if (v or "").strip()]
        seen = {}
        for k, v in items:
            if v in seen:
                errors.append(f"{cat}: 동일 문장 — {seen[v]} / {k}")
            seen[v] = k
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                r = SequenceMatcher(None, items[i][1], items[j][1]).ratio()
                if r >= SIMILAR:
                    warns.append(f"{cat}: 유사도 {r:.0%} — {items[i][0]} / {items[j][0]}")

        # 관용구 편중
        if items:
            c = Counter()
            for _, v in items:
                for idiom in IDIOMS:
                    if idiom in v:
                        c[idiom] += 1
            for idiom, n in c.items():
                if n / len(items) > IDIOM_SHARE:
                    errors.append(f"{cat}: 관용구 '{idiom}' {n}/{len(items)}회 "
                                  f"({n/len(items):.0%} > {IDIOM_SHARE:.0%})")

        # 유머 비율 — 물음표뿐 아니라 건조한 농담 어투까지 센다(?만 세면 실제 유머를 놓친다)
        if items:
            humor = [k for k, v in items if HUMOR_PAT.search(v)]
            share = len(humor) / len(items)
            if share > HUMOR_MAX:
                warns.append(f"{cat}: 유머 항목 {len(humor)}/{len(items)} "
                             f"({share:.0%} > {HUMOR_MAX:.0%}) — 과하다")
            elif share < HUMOR_MIN and len(items) >= 20:
                warns.append(f"{cat}: 유머 항목 {len(humor)}/{len(items)} "
                             f"({share:.0%} < {HUMOR_MIN:.0%}) — 전부 설명문이라 밋밋하다")

        # 구조 단조로움 — "명사구. 부연문." 2문장 골격만 반복되면 기계적으로 읽힌다
        if len(items) >= 20:
            two = sum(1 for _, v in items if v.rstrip(".?!").count(".") >= 1)
            if two / len(items) > STRUCT_MAX:
                warns.append(f"{cat}: 2문장 골격 {two}/{len(items)} "
                             f"({two/len(items):.0%} > {STRUCT_MAX:.0%}) — 단문/다른 리듬을 섞을 것")

        # 등급 톤 (물고기 전용): 신화/전설은 진지하게
        if cat == "물고기":
            for k, v in items:
                if grades.get(k, "") in ("M", "L", "G") and ("?" in v or "!" in v):
                    errors.append(f"물고기/{k}: {grades[k]}등급(신화·전설)에 물음표/감탄부호 — 진지한 톤 규약 위반")

    print(f"\n총 {total}개 설명")
    for w in warns:
        print(f"  ⚠ {w}")
    for e in errors:
        print(f"  ✗ {e}")
    if errors or (strict and warns):
        print(f"\n실패 — 오류 {len(errors)} / 경고 {len(warns)}")
        return 1
    print(f"\n통과 (경고 {len(warns)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
