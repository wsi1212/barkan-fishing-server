#!/usr/bin/env python3
"""웹 도감 데이터 뽑기 — 라이브 fish.json → assets/fish-data.js.

## 왜 스크립트인가
assets/fish-data.js 는 머리에 "직접 수정하지 말고 원본을 갱신하세요"라고 적힌 채
**생성기 없이** 굴러다니던 사본이었다(2026-08-11 확인). 그래서 fish.json 이 바뀌어도
웹 도감은 안 따라갔고, `sources` 필드는 아예 빠져 있어서 어종을 누르면 예외가 났다.

## 권위
`plugins/BlockShip/fish.json` — 라이브 파일이 권위다(설계 문서 아님).
  fish[이름]        = {grade,minSize,maxSize,time,weather[,quest]}
  regions[지역][조건] = [어종...]      조건: 기본·통발·밤·낮비·이벤트 …
  environment[환경]  = [어종...]      새벽·오로라·유성우 …

## 내보내는 필드
기존 페이지가 쓰던 것(regions/conditions/environment/methods)을 그대로 재현하고
**sources=[{region,condition}]** 를 더한다 — 상세 패널의 '서식 지역·획득 조건' 원본이다.
지역·조건을 따로 평탄화해 두면 어느 지역이 어느 조건인지 잃어버린다.

## 그림
인게임 아이콘을 그대로 쓴다. 한글 이름 → 텍스처 파일명은 **FishModelRegistry.java** 가
유일한 규칙이라(로마자 표기가 불규칙해서 다시 만들 수 없다) 그 파일을 읽어 쓴다.
리소스팩 원본은 256px 라 웹엔 과하다 — 128px 로 줄여 담는다. 매핑이 없는 어종은
인게임에서도 바닐라 대구라 그림 없이 두고, 페이지가 등급 색 자리표시를 그린다.

사용: python3 build_fish_data.py [--check]      (--check: 파일 안 쓰고 기존 것과 대조만)
"""
import collections
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.normpath(os.path.join(HERE, "..", "..", "..", "BlockShip", "fish.json"))
OUT = os.path.join(HERE, "assets", "fish-data.js")
# 한글 이름 → 텍스처 파일명. 이 자바 파일이 규칙 자체다(671줄 if/else 를 포팅한 표).
REGISTRY = "/Users/user/development/blockship-plugin/src/main/java/com/blockship/fishing/FishModelRegistry.java"
TEXTURES = os.path.expanduser("~/development/barkan-resourcepack/assets/minecraft/textures/item/fish")
ICONDIR = os.path.join(HERE, "assets", "fish")
ICON_PX = 128
HEAD = "/* 서버 fish.json에서 생성됨. 직접 수정하지 말고 원본을 갱신하세요. */\n"
# '기본'은 조건이 아니라 '조건 없음'이라 목록에서 뺀다(페이지가 '상시'로 표시한다).
PLAIN = "기본"
TRAP = "통발"


def icon_names():
    """어종 이름 → 텍스처 파일명(확장자 없음). 매핑이 비어 있으면 그림이 없는 것이다."""
    if not os.path.exists(REGISTRY):
        print(f"  ⚠ FishModelRegistry 를 못 찾음 — 그림 없이 만든다: {REGISTRY}")
        return {}
    src = open(REGISTRY, encoding="utf-8").read()
    return {k: v for k, v in re.findall(r'm\.put\("([^"]+)",\s*"([^"]*)"\)', src) if v}


def export_icons(names):
    """쓰는 그림만 128px 로 줄여 assets/fish/ 에 둔다. 이미 최신이면 건너뛴다."""
    from PIL import Image
    os.makedirs(ICONDIR, exist_ok=True)
    wrote = skipped = 0
    for model in sorted(set(names)):
        src = os.path.join(TEXTURES, model + ".png")
        dst = os.path.join(ICONDIR, model + ".png")
        if not os.path.exists(src):
            continue
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            skipped += 1
            continue
        im = Image.open(src).convert("RGBA")
        if im.width > ICON_PX:
            im = im.resize((ICON_PX, ICON_PX), Image.LANCZOS)
        im.save(dst, optimize=True)
        wrote += 1
    # 더 이상 안 쓰는 그림은 지운다 — 어종을 빼면 파일도 같이 빠져야 한다.
    keep = {m + ".png" for m in names}
    stale = [f for f in os.listdir(ICONDIR) if f.endswith(".png") and f not in keep]
    for f in stale:
        os.remove(os.path.join(ICONDIR, f))
    total = sum(os.path.getsize(os.path.join(ICONDIR, f)) for f in os.listdir(ICONDIR))
    print(f"  그림 {len(os.listdir(ICONDIR))}장 ({total/1e6:.1f}MB) · 새로 {wrote} · 유지 {skipped}"
          + (f" · 정리 {len(stale)}" if stale else ""))


def build(live=LIVE):
    d = json.load(open(live, encoding="utf-8"))
    fish, regions, env = d["fish"], d["regions"], d["environment"]
    icons = icon_names()

    sources = collections.defaultdict(list)
    for region, conds in regions.items():
        for cond, names in conds.items():
            for n in names:
                sources[n].append({"region": region, "condition": cond})
    envof = collections.defaultdict(list)
    for e, names in env.items():
        for n in names:
            envof[n].append(e)

    out = []
    for name, spec in fish.items():
        src = sources[name]
        conds = list(dict.fromkeys(s["condition"] for s in src if s["condition"] != PLAIN))
        methods = []
        if any(s["condition"] != TRAP for s in src):
            methods.append("낚시")
        if any(s["condition"] == TRAP for s in src):
            methods.append(TRAP)
        out.append({
            "name": name,
            "grade": spec.get("grade", "E"),
            "minSize": spec.get("minSize"),
            "maxSize": spec.get("maxSize"),
            "time": spec.get("time", "전체"),
            "weather": spec.get("weather", "전체"),
            "quest": spec.get("quest"),
            "regions": list(dict.fromkeys(s["region"] for s in src)),
            "conditions": conds,
            "environment": envof[name],
            "methods": methods,
            "sources": src,
            "icon": icons.get(name, ""),
        })
    return out


def main():
    check = "--check" in sys.argv
    fish = build()
    payload = {"generatedAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
               "count": len(fish), "fish": fish}

    if os.path.exists(OUT):
        old = open(OUT, encoding="utf-8").read()
        old = json.loads(old[old.index("{"):old.rindex("}") + 1])["fish"]
        O = {f["name"]: f for f in old}
        gone = [n for n in O if n not in {f["name"] for f in fish}]
        # 새로 더한 필드를 뺀 나머지가 예전과 같아야 한다 — 재현이 맞는지 보는 자기검증이다.
        NEW = ("sources", "icon")
        diff = [f["name"] for f in fish
                if f["name"] in O and {k: v for k, v in f.items() if k not in NEW}
                != {k: v for k, v in O[f["name"]].items() if k not in NEW}]
        print(f"  기존 {len(old)} → 새로 {len(fish)}  ·  사라진 어종 {len(gone)}  ·  sources 외 차이 {len(diff)}")
        for n in diff[:5]:
            print(f"    ≠ {n}\n      기존 {json.dumps(O[n], ensure_ascii=False)}"
                  f"\n      신규 {json.dumps({k: v for k, v in next(f for f in fish if f['name'] == n).items() if k != 'sources'}, ensure_ascii=False)}")
        if gone:
            print(f"    ⚠ 사라짐: {gone[:8]}")

    unassigned = [f["name"] for f in fish if not f["sources"] and not f["environment"]]
    print(f"  어종 {len(fish)} · 지역배정 {sum(1 for f in fish if f['sources'])}"
          f" · 환경전용 {sum(1 for f in fish if not f['sources'] and f['environment'])}"
          f" · ★어디에도 없음 {len(unassigned)}")
    print(f"  그림 있는 어종 {sum(1 for f in fish if f['icon'])} / {len(fish)}")
    if check:
        print("  --check: 파일 안 씀")
        return
    export_icons([f["icon"] for f in fish if f["icon"]])
    open(OUT, "w", encoding="utf-8").write(HEAD + "window.BARKAN_FISH_DATA=" +
                                           json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"  → {OUT}")


if __name__ == "__main__":
    main()
