#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""채집 미끼 라인을 «재료확률 전문 미끼»로 전환 — parts.json 패치 (2026-08-27).

유저 지시: "채집 시리즈들 행운을 없애고 재료확률을 살리는 방향으로 가자 그래야 좀 독창적이지"

★왜 생성기(gen_part_builds.py)가 아니라 이 패치 스크립트인가
   gen_part_builds.py 는 `is_external()` 로 «스탯에 재료확률이 있는 부품»을 카탈로그 밖으로
   빼 둔다 — 삭제·덮어쓰기·order 정리·레시피 정리 전부에서 제외한다(gen_part_builds.py L262~271,
   L529·L537·L570). 재료확률 축은 그 사다리(BUILDS)에 없는 축이라 공식으로 재생성하면 수치가
   깨지기 때문이다. 그래서 이 4종은 **parts.json 직접 수정이 정본**이고, 재생성에도 살아남는다.
   ★단 «재료확률을 빼면» external 집합에서 이탈해 생성기 관리 대상이 되고, 그 순간
   guard_drift 가 멈추거나(운 좋으면) 조용히 사다리 값으로 덮인다(운 나쁘면). 이 라인에서
   재료확률을 제거하는 변경은 절대 하지 말 것.

설계 근거 (balance-audit/scripts/bait_reprice.py --nerf 로 재현)
  · 실측상 미끼 22종 **전부** 행운을 갖고 있어 모든 미끼가 «행운 미끼 + 약간의 무엇»이었다.
    채집 라인에서 수입축을 빼면 처음으로 진짜 분기가 생긴다 —
    「물고기 값을 올릴 것인가(행운·판매·크리) vs 재료를 캘 것인가(채집)」.
  · 미끼 철학은 «돈을 써서 재료·경험치를 얻는다»이고 «가격보다 (돈)효율이 좋으면 안 된다».
    수입축을 0 으로 만들면 그 규칙이 **어떤 가격에서든 자동 성립**한다.
  · 행운은 재료확률보다 훨씬 싸다(초반 행운 1점 ≈ 재확 0.4%). 통째로 빼도 잃는 가치가 작아
    그 몫을 재확으로 되돌리면 체감은 강화다.
  · 세트 영향은 미미하다 — 세트 재확 합 D 30→32 · C 58→62 · B 103→110 · A 150→160,
    게이트 −1.5~−3.8%. 낚싯대가 재확의 절반을 들고 있어(10/18/28/50) 미끼 1.5배로는 안 터진다.

가격 = V수입 + 1.5×V진행 + 0.12×포획당 실현가  (bait_reprice.py 공식, c=1.5)
  V수입이 0 이므로 가격 전체가 «진행 대가 + 싱크»다. 수집 미끼 기준 낚시 수입의 37% 소모.

사용:
    python3 patch_forage_bait_line.py <BlockShip 데이터 폴더> [--apply]
    (--apply 없으면 dry-run)
"""
import json, os, shutil, sys

# 이름: (등급, 새 가격, 새 스탯)  — 내구·레벨·출처는 건드리지 않는다(미끼 내구는 사문화 필드)
PLAN = {
    "채집 미끼":   ("D",   110, {"경험치": 3,  "재료확률": 6}),
    "수집 미끼":   ("C",   190, {"경험치": 7,  "재료확률": 12}),
    "유적 미끼":   ("B",   360, {"경험치": 10, "재료확률": 22}),
    "수집상 미끼": ("A",  1350, {"경험치": 15, "재료확률": 30}),
}
# gen_part_builds.STAT_ORDER 와 같은 순서로 적는다(생성기와 표기 규약을 맞춘다)
STAT_ORDER = ["도망감소", "크리배율", "등급업", "크리확률", "크기", "경험치",
              "판매보너스", "더블찬스", "트리플찬스", "행운", "재료확률"]


def stat_str(st):
    keys = [k for k in STAT_ORDER if k in st] + [k for k in st if k not in STAT_ORDER]
    return ",".join(f"{k}:{int(st[k])}" for k in keys)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    apply_ = "--apply" in sys.argv
    path = os.path.join(src, "parts.json")
    P = json.load(open(path, encoding="utf-8"))
    baits = P["parts"]["미끼"]

    print(f"대상: {path}\n")
    changes = []
    for name, (grade, price, st) in PLAN.items():
        if name not in baits:
            sys.exit(f"❌ {name} 이 parts.json 미끼에 없다 — 이름이 바뀌었는지 확인할 것")
        f = baits[name].split("|")
        if f[1] != grade:
            sys.exit(f"❌ {name} 등급이 {f[1]} (계획은 {grade}) — 계획표를 갱신할 것")
        new = "|".join([f[0], f[1], str(price), f[3], stat_str(st), f[5], f[6]])
        # ★재료확률이 남아 있는지 확인 — 빠지면 생성기 external 집합에서 이탈한다
        if "재료확률" not in stat_str(st):
            sys.exit(f"❌ {name} 에 재료확률이 없다 — 생성기가 이 부품을 관리 대상으로 삼아버린다")
        if baits[name] == new:
            print(f"  = {name:<12} 이미 적용됨")
            continue
        print(f"  · {name}")
        print(f"      before {baits[name]}")
        print(f"      after  {new}")
        changes.append((name, new))

    if not changes:
        print("\n변경 없음 (idempotent).")
        return
    if not apply_:
        print(f"\n[dry-run] {len(changes)}종 변경 예정 — --apply 로 실제 반영")
        return
    shutil.copy(path, path + ".bak-foragebait")
    for name, new in changes:
        baits[name] = new
    json.dump(P, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n✅ {len(changes)}종 반영 · 백업 {os.path.basename(path)}.bak-foragebait")
    print("   서버에 /데이터리로드 (또는 재시작) 필요")


if __name__ == "__main__":
    main()
