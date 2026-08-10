#!/usr/bin/env python3
"""안 쓰는 어종 분리 — 어디에도 배정 안 된 물고기를 fish.json 에서 빼 따로 보관한다.

## 무엇이 '안 쓰는' 것인가
어종이 실제로 잡히려면 셋 중 하나에 이름이 있어야 한다.
  · fish.json  regions[지역][조건]      ← 보통의 배정
  · fish.json  environment[환경]        ← 새벽·오로라 같은 환경 한정
  · regions.json <지역>.customFish      ← 지역이 따로 얹는 어종
셋 다 없으면 GradeRoller 후보에 들어갈 길이 없다 — 도감에 칸만 있고 못 잡는다.
(regions.json 의 excludedFish 는 '제외' 목록이라 배정이 아니다. 헷갈리지 말 것.)

## 지운 걸 어디에 두나
`fish-unused.json` 에 스펙을 통째로 옮긴다. 되돌리려면 이 파일의 fish 를 fish.json 의
fish 에 도로 합치고 지역 배정을 넣으면 된다. **playerdata 의 fishRecords 는 안 건드린다** —
실유저 5명이 이 어종들을 잡은 기록이 있어서(과거엔 배정돼 있었다) 되돌릴 여지를 남긴다.

## 같이 치우는 것
regions.json 의 excludedFish 에 남은 이름 중 fish.json 에서 사라진 것은 유령이라 지운다.
목록만 남아도 동작엔 지장 없지만, 다음 사람이 '이 어종은 여기서 제외됐구나'라고 오해한다.

사용: python3 split_unused_fish.py [--check]      (--check: 세보기만, 파일 안 씀)
"""
import json
import os
import shutil
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "..", "BlockShip"))
FISH = os.path.join(DATA, "fish.json")
REGIONS = os.path.join(DATA, "regions.json")
UNUSED = os.path.join(DATA, "fish-unused.json")


def load(path):
    return json.load(open(path, encoding="utf-8"))


def save(path, data):
    shutil.copy2(path, path + ".bak-unusedsplit")
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def assigned(fish, regions):
    """실제로 잡힐 수 있는 어종 이름 집합."""
    names = set()
    for conds in fish["regions"].values():
        for lst in conds.values():
            names.update(lst)
    for lst in fish["environment"].values():
        names.update(lst)
    for r in regions.values():
        names.update(r.get("customFish") or [])
    return names


def main():
    check = "--check" in sys.argv
    fish, regions = load(FISH), load(REGIONS)
    live = assigned(fish, regions)
    dead = [n for n in fish["fish"] if n not in live]
    print(f"  어종 {len(fish['fish'])} · 살아있음 {len(fish['fish']) - len(dead)} · 안 쓰는 것 {len(dead)}")
    if not dead:
        print("  분리할 것 없음")
        return

    ghosts = {rid: [n for n in (r.get("excludedFish") or []) if n in dead]
              for rid, r in regions.items()}
    ghosts = {k: v for k, v in ghosts.items() if v}
    print(f"  excludedFish 유령 {sum(len(v) for v in ghosts.values())}개 (지역 {len(ghosts)}곳)")
    if check:
        print(f"  --check: 파일 안 씀 · 예시 {dead[:8]}")
        return

    # 이미 분리해 둔 게 있으면 합친다 — 두 번 돌려도 앞의 기록을 잃지 않는다.
    old = load(UNUSED) if os.path.exists(UNUSED) else {"fish": {}, "history": []}
    old["fish"].update({n: fish["fish"][n] for n in dead})
    old["history"].append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                           "removed": dead,
                           "reason": "지역·환경·customFish 어디에도 배정이 없어 잡을 수 없음"})
    old["note"] = ("여기 있는 어종은 fish.json 에서 뺀 것이다. 되살리려면 fish 를 fish.json 의 "
                   "fish 에 합치고 regions 에 배정을 넣어라. playerdata 의 fishRecords 는 그대로 남아 있다.")
    json.dump(old, open(UNUSED, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    for n in dead:
        del fish["fish"][n]
    save(FISH, fish)
    for rid, names in ghosts.items():
        regions[rid]["excludedFish"] = [n for n in regions[rid]["excludedFish"] if n not in dead]
    if ghosts:
        save(REGIONS, regions)

    print(f"  → {UNUSED} (누적 {len(old['fish'])}종)")
    print(f"  → {FISH} 어종 {len(fish['fish'])}종 남김 (.bak-unusedsplit 백업)")


if __name__ == "__main__":
    main()
