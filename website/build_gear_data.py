#!/usr/bin/env python3
"""웹 장비 도감 데이터 뽑기 — 라이브 parts.json(+recipes.json) → assets/gear-data.js.

## 권위
`plugins/BlockShip/parts.json` — 한 줄 문자열이 한 장비다.
    이름|등급|가격|내구|스탯|레벨제한|출처      예) 초보자 낚싯대|E|0|60|경험치:3|1|스폰마을
스탯은 `이름:값` 을 콤마로 잇는다. `order` 는 진열 순서(사다리 순)라 그대로 따른다 —
등급만으로 정렬하면 같은 등급 안의 사다리 순서를 잃는다.

## 제작법
`recipes.json` 에서 이 장비를 만드는 레시피를 붙인다. 매칭 키가 종류마다 다르다:
    낚싯대 → resultMode "rod"  · rodPartName
    부품   → resultMode "part" · resultPartType + resultPartName
결과 이름(result.name)으로는 안 붙는다 — 거기엔 색코드가 붙은 표시용 이름이 들어간다.

## 그림
인게임과 같은 카탈로그 아이콘을 쓴다. 파일명 규칙은 자바 `ItemIconModel` 과 같다:
    catalog_<분류>_<sha1(유형 \\0 이름)의 앞 10자>
226종 전부 리소스팩에 있다(2026-08-11 확인). 규칙이 어긋나면 바로 '아이콘 없음'으로 잡힌다.

사용: python3 build_gear_data.py [--check]
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "..", "BlockShip"))
PARTS = os.path.join(DATA, "parts.json")
RECIPES = os.path.join(DATA, "recipes.json")
OUT = os.path.join(HERE, "assets", "gear-data.js")
TEXTURES = os.path.expanduser("~/development/barkan-resourcepack/assets/minecraft/textures/item/barkan_icon")
ICONDIR = os.path.join(HERE, "assets", "gear")
ICON_PX = 128
HEAD = "/* 서버 parts.json + recipes.json 에서 생성됨. 직접 수정하지 말고 원본을 갱신하세요. */\n"

# ItemIconModel.category 와 같은 표. 여기가 어긋나면 아이콘이 통째로 안 붙는다.
CATEGORY = {"낚싯대": "rod", "릴": "reel", "줄": "line", "바늘": "hook",
            "미끼": "bait", "찌": "bobber", "작살": "harpoon"}


def sha10(*parts):
    return hashlib.sha1("\0".join(parts).encode("utf-8")).hexdigest()[:10]


def icon_id(category, name):
    return f"catalog_{CATEGORY[category]}_{sha10(category, name)}"


def recipes_by_part():
    """(유형, 이름) → 재료 목록. 낚싯대와 부품이 서로 다른 키를 쓴다."""
    if not os.path.exists(RECIPES):
        return {}
    out = {}
    for r in json.load(open(RECIPES, encoding="utf-8"))["recipes"].values():
        mode = r.get("resultMode")
        if mode == "rod" and r.get("rodPartName"):
            key = ("낚싯대", r["rodPartName"])
        elif mode == "part" and r.get("resultPartName"):
            key = (r.get("resultPartType", ""), r["resultPartName"])
        else:
            continue
        out[key] = {"id": r.get("id", ""),
                    "village": r.get("village", ""),
                    "ingredients": [{"name": i.get("displayName") or i.get("typeOrMatId", ""),
                                     "qty": i.get("qty", 1)} for i in (r.get("ingredients") or [])]}
    return out


def export_icons(ids):
    from PIL import Image
    os.makedirs(ICONDIR, exist_ok=True)
    wrote = skipped = missing = 0
    for i in sorted(set(ids)):
        src, dst = os.path.join(TEXTURES, i + ".png"), os.path.join(ICONDIR, i + ".png")
        if not os.path.exists(src):
            missing += 1
            continue
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            skipped += 1
            continue
        im = Image.open(src).convert("RGBA")
        if im.width > ICON_PX:
            im = im.resize((ICON_PX, ICON_PX), Image.LANCZOS)
        im.save(dst, optimize=True)
        wrote += 1
    keep = {i + ".png" for i in ids}
    stale = [f for f in os.listdir(ICONDIR) if f.endswith(".png") and f not in keep]
    for f in stale:
        os.remove(os.path.join(ICONDIR, f))
    total = sum(os.path.getsize(os.path.join(ICONDIR, f)) for f in os.listdir(ICONDIR))
    print(f"  그림 {len(os.listdir(ICONDIR))}장 ({total/1e6:.1f}MB) · 새로 {wrote} · 유지 {skipped}"
          + (f" · ★원본없음 {missing}" if missing else "") + (f" · 정리 {len(stale)}" if stale else ""))


def build():
    d = json.load(open(PARTS, encoding="utf-8"))
    parts, order = d["parts"], d.get("order") or []
    craft = recipes_by_part()
    have = set(os.listdir(TEXTURES)) if os.path.isdir(TEXTURES) else set()

    # order 가 진열 순서다. 거기 없는 장비는 뒤에 붙여 하나도 빠뜨리지 않는다.
    seq = [(c, n) for c, n in order if c in parts and n in parts[c]]
    seq += [(c, n) for c in parts for n in parts[c] if (c, n) not in set(seq)]

    out, noicon = [], []
    for cat, name in seq:
        f = parts[cat][name].split("|")
        stats = {}
        for chunk in (f[4] if len(f) > 4 else "").split(","):
            if ":" in chunk:
                k, v = chunk.split(":", 1)
                try:
                    stats[k.strip()] = float(v) if "." in v else int(v)
                except ValueError:
                    stats[k.strip()] = v.strip()
        icon = icon_id(cat, name)
        if icon + ".png" not in have:
            noicon.append(f"{cat}/{name}")
            icon = ""
        out.append({
            "name": name,
            "category": cat,
            "grade": f[1] if len(f) > 1 else "E",
            "price": int(f[2]) if len(f) > 2 and f[2].lstrip("-").isdigit() else 0,
            "durability": int(f[3]) if len(f) > 3 and f[3].lstrip("-").isdigit() else 0,
            "stats": stats,
            "level": int(f[5]) if len(f) > 5 and f[5].lstrip("-").isdigit() else 1,
            "origin": f[6] if len(f) > 6 else "",
            "icon": icon,
            "recipe": craft.get((cat, name)),
        })
    return out, noicon


def main():
    check = "--check" in sys.argv
    gear, noicon = build()
    cats = list(dict.fromkeys(g["category"] for g in gear))
    tally = " ".join("%s:%d" % (c, sum(1 for g in gear if g["category"] == c)) for c in cats)
    print(f"  장비 {len(gear)}종 · 분류 {len(cats)} ({tally})")
    print(f"  제작법 있음 {sum(1 for g in gear if g['recipe'])} · 상점가 있음 {sum(1 for g in gear if g['price'] > 0)}")
    if noicon:
        print(f"  ★아이콘 없음 {len(noicon)}종 → {noicon[:6]}")
    if check:
        print("  --check: 파일 안 씀")
        return
    export_icons([g["icon"] for g in gear if g["icon"]])
    payload = {"generatedAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
               "count": len(gear), "categories": cats, "gear": gear}
    open(OUT, "w", encoding="utf-8").write(HEAD + "window.BARKAN_GEAR_DATA=" +
                                           json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"  → {OUT}")


if __name__ == "__main__":
    main()
