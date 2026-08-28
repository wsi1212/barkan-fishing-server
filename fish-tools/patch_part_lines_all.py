#!/usr/bin/env python3
"""부품 계열 사다리를 «전 등급» 으로 확장 적용 (2026-08-29, 출시 점검).

★무엇이 빠져 있었나
  `part_lines.py` 는 `GRADES = ("D",)` 였다 — 스폰마을 초반(D)만 계열 사다리를 맞췄고
  사막마을 이후(C·B·A·S)는 손대지 않았다. 그 결과 «계열 안에서 레벨이 올라갔는데 순성능이
  내려가는» 역전이 라이브에 34건 남아 있었다(2026-08-29 실측):
      찌/행운 12 · 줄/행운 4 · 바늘/행운 4 · 릴/행운 3 · 미끼/행운 3 · 그 외 8
  행운 계열이 26/34 를 차지한다 — 행운 스탯의 정규화 가치가 0.40 이라 같은 «숫자»를 줘도
  다른 계열의 절반이 안 되기 때문이다(유저 눈엔 행운 4 > 트리플 1 인데 실제론 1.6 < 2.0).

★사다리를 어떻게 세웠나 — 선형 상수표 → 등위회귀(PAV)
  옛 LADDER 는 «Lv3 7,800 + 레벨당 1,250» 같은 선형 상수였다. Lv3~7 은 그걸로 되지만
  Lv1~70 은 구간 시급이 세 번 계단을 밟아(초반/중반/종결) 선형으로 못 맞춘다.
  대신 라이브 값에 PAV 등위회귀를 걸어 **단조 비감소 사다리**를 만든다:
    · 역전이 정의상 사라진다.       · 이미 맞게 선 항목은 제자리에 남는다(최소 이동).
    · 사다리 «수준» 을 라이브가 정한다 — 내가 고른 상수가 아니다.
  ★사다리는 (슬롯 × 계열) 마다 따로 세운다. 순성능은 재료확률(게이트축)·난이도(3층 예산)를
    값으로 세지 않아서, 슬롯 하나로 묶으면 채집·숙련이 영원히 «미달» 로 잡힌다.

결과: 역전 34 → 0, 평균 절대편차 21.1% → 9.3%.

계획은 `part_lines.py --tune --plan` 이 뽑는다. 이 파일은 그걸 parts.json 에 바르기만 한다.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "ops", "blockship-data")
PLAN = sys.argv[1] if len(sys.argv) > 1 else None


def main():
    if not PLAN or not os.path.exists(PLAN):
        raise SystemExit("사용: patch_part_lines_all.py <part_lines --tune --plan 출력파일>")
    ns = {}
    exec(open(PLAN, encoding="utf-8").read(), ns)
    plan = ns.get("PART_STATS")
    if not plan:
        raise SystemExit("★PART_STATS 를 못 읽었다 — 계획 파일이 비었다")

    P = json.load(open(os.path.join(BASE, "parts.json"), encoding="utf-8"))
    parts = P["parts"]
    changed, same, missing = [], 0, []
    for name, (slot, stat) in plan.items():
        if slot not in parts or name not in parts[slot]:
            missing.append((slot, name)); continue
        f = parts[slot][name].split("|")
        if f[4] == stat:
            same += 1; continue
        changed.append((slot, name, f[4], stat))
        f[4] = stat
        parts[slot][name] = "|".join(f)
    if missing:
        for s, n in missing[:10]:
            print(f"🔴 parts.json 에 없음: {s}/{n}")
        raise SystemExit(f"★계획에 있는데 데이터에 없는 부품 {len(missing)}종 — 중단")

    json.dump(P, open(os.path.join(BASE, "parts.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"부품 스탯 조정 {len(changed)}종 · 무변경 {same}종")
    for s, n, a, b in changed[:20]:
        print(f"   {s:<4}{n:<16} {a}")
        print(f"   {'':4}{'':16} → {b}")
    if len(changed) > 20:
        print(f"   … 외 {len(changed)-20}종")


if __name__ == "__main__":
    main()
