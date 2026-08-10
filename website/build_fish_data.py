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

사용: python3 build_fish_data.py [--check]      (--check: 파일 안 쓰고 기존 것과 대조만)
"""
import collections
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.normpath(os.path.join(HERE, "..", "..", "..", "BlockShip", "fish.json"))
OUT = os.path.join(HERE, "assets", "fish-data.js")
HEAD = "/* 서버 fish.json에서 생성됨. 직접 수정하지 말고 원본을 갱신하세요. */\n"
# '기본'은 조건이 아니라 '조건 없음'이라 목록에서 뺀다(페이지가 '상시'로 표시한다).
PLAIN = "기본"
TRAP = "통발"


def build(live=LIVE):
    d = json.load(open(live, encoding="utf-8"))
    fish, regions, env = d["fish"], d["regions"], d["environment"]

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
        # sources 를 뺀 나머지가 예전과 같아야 한다 — 재현이 맞는지 보는 자기검증이다.
        diff = [f["name"] for f in fish
                if f["name"] in O and {k: v for k, v in f.items() if k != "sources"} != O[f["name"]]]
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
    if check:
        print("  --check: 파일 안 씀")
        return
    open(OUT, "w", encoding="utf-8").write(HEAD + "window.BARKAN_FISH_DATA=" +
                                           json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"  → {OUT}")


if __name__ == "__main__":
    main()
