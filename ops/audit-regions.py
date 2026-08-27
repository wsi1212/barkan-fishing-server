#!/usr/bin/env python3
"""지역 ID 정합성 감사 — 라이브 데이터(권위) 기준.

2026-08-27 하루에 같은 함정이 네 번 나와서 만들었다:
  · `/지역 생성 붉은호수` 가 RegionIds 별칭에 걸려 레드_로드로 접혔다 (에러 문구는 "이미 존재").
  · 은빛_갈매기호도 같은 이유로 개명이 몇 달째 표시명에만 걸려 있었다.
  · 협곡 BGM 이 삭제된 옛 ID «강_상류» 에 등록돼 있어 협곡에선 아무 소리도 안 났다.
  · 도달 불가 지역(물보라동굴·폭포)에 어종 12종과 통발 8종이 매달려 있었다.

넷 다 «조용한» 고장이다 — 로그도 경고도 안 뜨고 게임만 안 돈다. 그래서 사람 기억이
아니라 검사로 옮긴다.

★검사 대상은 **prod 라이브 JSON** 이다. 레포의 `ops/blockship-data/` 는 미러라서
낡아 있을 수 있고, 오늘 사고들도 전부 라이브 파일에서 났다.

    python3 ops/audit-regions.py --data ~/mcserver/plugins/BlockShip [--src <blockship>/src/main/java]

exit 0 = 이상 없음 / 1 = ERROR / 2 = 스크립트 자체 실패.
WARN 은 종료코드를 바꾸지 않는다(의도된 예외가 있다).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 표시명이 ID 와 «밑줄↔공백» 관계가 아니어도 되는 지역 — 의도된 별명.
DISPLAY_EXEMPT = {
    "스폰도시": "바르칸 항구",   # 마을 이름은 바꿨지만 ID 는 퀘스트 마을 필드 60곳이 물고 있다
}

# 지역 ID 가 아니라 자유 문자열인 필드(수집품 표시 지역명 등)
FREEFORM_ISLAND_LABELS = {"어드민의 수집품"}

ERRORS: list[str] = []
WARNS: list[str] = []
NOTES: list[str] = []


def err(msg: str) -> None: ERRORS.append(msg)
def warn(msg: str) -> None: WARNS.append(msg)
def note(msg: str) -> None: NOTES.append(msg)


def load(data_dir: Path, name: str):
    p = data_dir / name
    if not p.exists():
        warn(f"{name} 없음 — 이 파일 검사는 건너뛴다")
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        err(f"{name} 파싱 실패: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 1) ID 작명 규약
# ─────────────────────────────────────────────────────────────────────────────
def check_naming(regions: dict) -> None:
    for key, v in regions.items():
        if key.startswith(("개인섬_", "길드섬_")):
            continue
        rid = v.get("id")
        if rid != key:
            err(f"[ID] regions.json 키와 id 불일치: 키={key!r} id={rid!r}")
        if " " in key:
            err(f"[ID] 지역 ID 에 공백: {key!r} — 명령어 인자라 공백을 못 쓴다. 밑줄을 써라")
        dn = v.get("displayName") or ""
        if not dn:
            warn(f"[ID] 표시명 없음: {key}")
            continue
        if DISPLAY_EXEMPT.get(key) == dn:
            note(f"[ID] 의도된 별명(면제): {key} → {dn}")
            continue
        if key.replace("_", " ") != dn:
            err(
                f"[ID] «어절 = 밑줄» 규약 위반: id={key!r} 표시명={dn!r} "
                f"→ id 를 {dn.replace(' ', '_')!r} 로 맞춰라"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 2) 도달 가능성 — 좌표 없는 지역에 콘텐츠가 매달리면 조용히 죽는다
# ─────────────────────────────────────────────────────────────────────────────
def check_reachable(regions: dict, fish: dict | None) -> None:
    for key, v in regions.items():
        if key.startswith(("개인섬_", "길드섬_")):
            continue
        shape = v.get("shape")
        p1, p2 = v.get("pos1"), v.get("pos2")
        if shape == "polygon":
            ok = bool(v.get("polygon")) and len(v["polygon"]) >= 3
            why = f"polygon {len(v.get('polygon') or [])}점"
        elif shape == "points3d":
            ok = bool(v.get("points3d")) and len(v["points3d"]) >= 3
            why = f"points3d {len(v.get('points3d') or [])}점"
        else:
            # shape 미지정은 코드상 box 로 취급된다 (RegionData: null="box")
            ok = p1 != p2
            why = f"box {p1}~{p2}"
        if ok:
            continue
        nf = 0
        if fish and key in (fish.get("regions") or {}):
            nf = sum(len(x) for x in fish["regions"][key].values() if isinstance(x, list))
        tail = f" — 어종 {nf}종이 매달려 있다" if nf else ""
        err(f"[영역] 도달 불가: {key} ({why}){tail}")


# ─────────────────────────────────────────────────────────────────────────────
# 3) 참조 무결성 — 존재하지 않는 지역을 가리키는 데이터
# ─────────────────────────────────────────────────────────────────────────────
GOAL_REGION_PREFIX = ("area", "dogam", "fish", "harpoon", "trap")


def goal_region_tokens(goal: str) -> list[str]:
    """퀘스트 목표 스펙에서 «지역 ID 로 쓰인» 토큰만 뽑는다."""
    parts = goal.split("|")
    if not parts or parts[0] not in GOAL_REGION_PREFIX:
        return []
    out: list[str] = []
    if parts[0] in ("area", "dogam") and len(parts) > 1:
        out += [t.strip() for t in parts[1].split(",") if t.strip()]
    # fish|어종|등급|수|크기|지역목록  ·  harpoon 동일
    if parts[0] in ("fish", "harpoon") and len(parts) > 5:
        out += [t.strip() for t in parts[5].split(",") if t.strip()]
    return [t for t in out if t and not t.isdigit()]


def check_references(regions: dict, data_dir: Path) -> None:
    known = set(regions)

    def ref(where: str, rid: str) -> None:
        if rid not in known:
            err(f"[참조] 없는 지역을 가리킨다: {where} → {rid!r}")

    for fname, path in (("fish.json", "regions"), ("materials.json", "dropTables")):
        d = load(data_dir, fname)
        if d and isinstance(d.get(path), dict):
            for rid in d[path]:
                ref(f"{fname}/{path}", rid)

    fl = load(data_dir, "item-flavor.json")
    if fl:
        for cat in ("지역", "통발"):
            for rid in (fl.get(cat) or {}):
                ref(f"item-flavor.json/{cat}", rid)

    bgm = load(data_dir, "bgm.json")
    if bgm:
        for rid in (bgm.get("regions") or {}):
            ref("bgm.json/regions", rid)
        # 역방향: 어장이 있는데 BGM 이 없는 지역은 무음이다(협곡이 그랬다).
        # ★BgmManager 는 매핑이 없으면 parentIsland 체인을 12단계까지 타고 올라간다 —
        #   그 폴백까지 실패할 때만 진짜 무음이므로, 여기서도 같은 체인을 따라간다.
        bmap = bgm.get("regions") or {}

        def has_bgm(rid: str) -> bool:
            cur, guard = rid, 0
            while cur and guard < 12:
                if cur in bmap:
                    return True
                cur = (regions.get(cur) or {}).get("parentIsland")
                guard += 1
            return False

        fish = load(data_dir, "fish.json")
        if fish:
            for rid, rd in (fish.get("regions") or {}).items():
                n = sum(len(x) for x in rd.values() if isinstance(x, list))
                if n and not has_bgm(rid):
                    warn(f"[BGM] 어종 {n}종인데 BGM 이 무음이다(부모 체인까지 없음): {rid}")

    q = load(data_dir, "quests.json")
    if q:
        for qid, qd in (q.get("퀘스트") or {}).items():
            for g in (qd.get("목표") or []):
                for tok in goal_region_tokens(g):
                    if tok in known or tok in ("아무", "전역"):
                        continue
                    err(f"[참조] 퀘스트 목표가 없는 지역을 가리킨다: {qid} {g!r} → {tok!r}")

    rc = load(data_dir, "recipes.json")
    if rc:
        recipes = rc.get("recipes") or {}
        for rid, v in recipes.items():
            for line in ((v.get("result") or {}).get("lore") or []):
                m = re.search(r"trap:([^:]+):", line or "")
                if m:
                    ref(f"recipes.json/{rid} trap 태그", m.group(1))
        # 카테고리 순서 배열에 남은 고아 ID (심연 통발이 이렇게 남아 있었다)
        def scan(o, path=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    scan(v, f"{path}/{k}")
            elif isinstance(o, list):
                for x in o:
                    if isinstance(x, str):
                        if x not in recipes and re.fullmatch(r"[A-Z]{2,}[0-9]+[A-Z]?", x):
                            err(f"[레시피] 목록에 없는 레시피 ID: {path} → {x!r}")
                    else:
                        scan(x, f"{path}/[]")
        for k, v in rc.items():
            if k != "recipes":
                scan(v, k)

    col = load(data_dir, "collectibles.json")
    if col:
        labels = {v.get("island") for v in col.values() if isinstance(v, dict)}
        display = {v.get("displayName") for v in regions.values()}
        for lab in labels - display - FREEFORM_ISLAND_LABELS - {None}:
            warn(f"[수집품] 표시 지역명이 어느 지역 표시명과도 안 맞는다: {lab!r}")


# ─────────────────────────────────────────────────────────────────────────────
# 4) 플레이어에게 보이는 문자열에 지역 ID 원형(밑줄)이 박혔는가
# ─────────────────────────────────────────────────────────────────────────────
VISIBLE = {
    "quests.json": ("이름", "설명"),
    "dialogue.json": ("lines",),
    "item-flavor.json": None,   # 값 전체가 표시 문구
    "materials.json": ("desc",),
}


def check_visible(regions: dict, data_dir: Path) -> None:
    underscored = {k for k in regions if "_" in k and not k.startswith(("개인섬_", "길드섬_"))}
    if not underscored:
        return
    for fname, fields in VISIBLE.items():
        d = load(data_dir, fname)
        if d is None:
            continue

        def walk(o, path: str, under_field: bool) -> None:
            if isinstance(o, dict):
                for k, v in o.items():
                    walk(v, f"{path}/{k}", under_field or (fields is not None and k in fields))
            elif isinstance(o, list):
                for x in o:
                    walk(x, f"{path}/[]", under_field)
            elif isinstance(o, str):
                if fields is not None and not under_field:
                    return
                if path.endswith("/목표") or "/목표/" in path:
                    return
                for rid in underscored:
                    if rid in o:
                        err(f"[표시] 화면 문구에 지역 ID 가 그대로 들어갔다: {fname}{path} → {rid!r} ({o[:50]!r})")

        walk(d, "", fields is None)


# ─────────────────────────────────────────────────────────────────────────────
# 5) RegionIds 별칭표 — 예약어 목록을 눈에 보이게
# ─────────────────────────────────────────────────────────────────────────────
ALIAS_RE = re.compile(r'Map\.entry\("([^"]+)",\s*"([^"]+)"\)')


def check_aliases(regions: dict, src: Path | None) -> None:
    if src is None:
        return
    f = src / "com" / "blockship" / "region" / "RegionIds.java"
    if not f.exists():
        warn(f"RegionIds.java 를 못 찾았다: {f}")
        return
    text = f.read_text(encoding="utf-8")
    body = text.split("ALIASES", 1)[-1].split(");", 1)[0]
    aliases = ALIAS_RE.findall(body)
    for old, new in aliases:
        if new not in regions:
            err(f"[별칭] 가리키는 지역이 없다: {old!r} → {new!r}")
        if old in regions:
            err(f"[별칭] 실재하는 지역을 가리고 있다: {old!r} 는 지역인데 {new!r} 로 접힌다")
    removed = re.search(r"REMOVED\s*=\s*Set\.of\(([^)]*)\)", text)
    if removed and removed.group(1).strip():
        warn(
            "[별칭] REMOVED 가 비어 있지 않다: "
            + removed.group(1).strip()
            + " — 여기 있는 이름은 canonical 이 null 이라 «다시 만들 수도» 없다"
        )
    if aliases:
        note(
            "[별칭] 아래 "
            + str(len(aliases))
            + "개는 예약어다 — 이 이름으로는 새 지역을 만들 수 없다(입력이 오른쪽으로 접힌다):\n    "
            + ", ".join(f"{o}→{n}" for o, n in aliases)
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="BlockShip 데이터 폴더(라이브가 권위)")
    ap.add_argument("--src", help="blockship-plugin/src/main/java — 별칭표 검사용")
    ap.add_argument("--quiet", action="store_true", help="이상 없으면 아무것도 출력하지 않는다")
    a = ap.parse_args()

    data_dir = Path(a.data).expanduser()
    regions = load(data_dir, "regions.json")
    if not isinstance(regions, dict):
        print("❌ regions.json 을 읽지 못했다 — 감사 불가", file=sys.stderr)
        return 2

    check_naming(regions)
    fish = load(data_dir, "fish.json")
    check_reachable(regions, fish)
    check_references(regions, data_dir)
    check_visible(regions, data_dir)
    check_aliases(regions, Path(a.src).expanduser() if a.src else None)

    if a.quiet and not ERRORS and not WARNS:
        return 0

    n_reg = len([k for k in regions if not k.startswith(("개인섬_", "길드섬_"))])
    print(f"지역 감사 — {n_reg}개 지역 ({data_dir})")
    for label, items in (("ERROR", ERRORS), ("WARN", WARNS)):
        for m in items:
            print(f"  {label}  {m}")
    if not a.quiet:
        for m in NOTES:
            print(f"  note   {m}")
    print(f"→ ERROR {len(ERRORS)} · WARN {len(WARNS)}")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
