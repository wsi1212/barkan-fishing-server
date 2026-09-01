#!/usr/bin/env python3
"""fish.json 도달성 감사 — 「도감엔 보이는데 영원히 못 잡는 어종」을 잡는다.

★왜 필요한가 (2026-09-02):
  fish.json 의 지역 서브리스트 이름은 자유롭게 적을 수 있지만, 실제로 읽는 코드는
  정해진 키만 읽는다. 원양/대양에 «낮»·«밤» 이라는 서브리스트가 139종을 담고 있었는데
  FishingListener 는 «낮맑음/낮비/밤맑음/밤비» 만 읽어서 108종이 전 서버 어디서도
  안 잡혔다. 도감(MainDexGui.regionFish)은 그 «낮»·«밤» 을 목록에 넣었기 때문에
  유저에겐 보이기만 하고 평생 안 나오는 어종이 됐다 — 오타 하나면 조용히 재발한다.

읽는 쪽 (권위 = 자바 소스, 아래 상수와 어긋나면 이 파일을 고칠 것):
  FishingListener  기본(+부모섬 체인) / 낮맑음 / 낮비 / 밤맑음 / 밤비 / environment 전체
  TrapManager      통발 / 기본
  HarpoonManager   기본(+부모섬 체인)

사용:
  ops/audit-fish-reachability.py [fish.json경로]      (기본 = ops/blockship-data/fish.json)
종료코드: 도달 불가 어종이 있으면 1
"""
import json, sys, os

# 코드가 실제로 읽는 지역 서브리스트
LIVE_SUBLISTS = ("기본", "낮맑음", "낮비", "밤맑음", "밤비", "통발")
# 못 잡히는 게 «의도»인 서브리스트 (이벤트 지급 전용 — 낚시로는 안 나오는 게 맞다)
INTENTIONAL_SUBLISTS = ("이벤트",)

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "ops/blockship-data/fish.json")
    d = json.load(open(path, encoding="utf-8"))
    regions, env = d.get("regions", {}), d.get("environment", {})

    reachable = set()
    for lst in env.values():
        reachable.update(lst or [])
    for sub in regions.values():
        for key in LIVE_SUBLISTS:
            reachable.update(sub.get(key) or [])

    # 죽은 서브리스트 = 코드가 안 읽는 키. 그 안에만 있는 어종은 잡을 방법이 없다.
    dead_keys, orphans = {}, {}
    for rid, sub in regions.items():
        for key, lst in sub.items():
            if key in LIVE_SUBLISTS or key in INTENTIONAL_SUBLISTS:
                continue
            dead_keys[f"{rid}.{key}"] = len(lst or [])
            for name in (lst or []):
                if name not in reachable:
                    orphans.setdefault(name, []).append(f"{rid}.{key}")

    print(f"[fish-reach] {path}")
    print(f"[fish-reach] 어종 {len(d.get('fish', {}))}종 / 낚을 수 있는 어종 {len(reachable)}종")
    if dead_keys:
        print("[fish-reach] 코드가 읽지 않는 서브리스트:")
        for k, n in sorted(dead_keys.items(), key=lambda x: -x[1]):
            print(f"    {k:24} {n}종")
    # 어디에도 배정 안 된 어종 — 오타가 아니라 «미출시 지역용 대기» 인 경우가 많아 경고만 낸다.
    assigned = set()
    for sub in regions.values():
        for lst in sub.values():
            assigned.update(lst or [])
    for lst in env.values():
        assigned.update(lst or [])
    unassigned = [n for n in d.get("fish", {}) if n not in assigned]
    if unassigned:
        print(f"[fish-reach] 경고 — 어느 지역·환경에도 배정 안 된 어종 {len(unassigned)}종 (미출시 지역용이면 정상):")
        print("    " + ", ".join(unassigned))

    if orphans:
        print(f"[fish-reach] \033[31m잡을 방법이 없는 어종 {len(orphans)}종\033[0m:")
        for name, where in sorted(orphans.items()):
            print(f"    {name} ({', '.join(where)})")
        print("[fish-reach] → 지역 서브리스트를 낮맑음/낮비/밤맑음/밤비 로 옮기거나, 어종을 지울 것.")
        return 1
    print("[fish-reach] OK — 도달 불가 어종 없음")
    return 0

if __name__ == "__main__":
    sys.exit(main())
