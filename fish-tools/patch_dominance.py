#!/usr/bin/env python3
"""완전열등 제거 — «더 비싸고 레벨도 높은데 모든 스탯이 낮은» 장비를 없앤다 (2026-08-29).

★왜 생기나
  계열 사다리(part_lines / patch_gear_lines)는 «(슬롯 × 계열)» 안에서만 단조성을 지킨다.
  계열이 다르면 서로 제약이 없어서, 튜너가 A급 어떤 줄을 올리고 S급 다른 줄을 안 올리면
  등급을 가로지르는 열등이 남는다. 실측(2026-08-29):
      전갈왕 바늘  S Lv60 1,350,000원  크리배율7 등급업9  크리확률19 크기10 행운16
      사구 바늘    A Lv45   590,000원  크리배율11 등급업18 크리확률33 크기16 행운30
  더 비싸고 더 높은 레벨인데 다섯 축 전부 낮다. 유저에겐 «살 이유가 없는 물건»이고,
  아무 감사도 이걸 안 잡고 있었다.

★판정
  같은 슬롯 · 같은 «스탯 축 구성» · b 의 레벨과 가격이 a 이하 · 모든 축에서 b ≥ a ·
  하나라도 b > a  →  a 는 완전열등.
  ★축 구성이 다르면 비교하지 않는다 — 축이 다르면 «다른 물건» 이지 열등이 아니다.

★고침
  열등한 쪽(레벨·가격이 높은 쪽)을 «우위 쪽 + 여유» 로 끌어올린다. 내리지 않는다 —
  내리면 그 아이템이 자기 계열 사다리에서 다시 어긋난다.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "ops", "blockship-data")
SKIP_SRC = {"캐시", "개발자", "잠수상점"}
#: 우위 아이템 대비 최소 여유. 1.05 = 5% 더 높게(최소 +1).
MARGIN = 1.05


def parse(s):
    out = {}
    for t in s.split(","):
        if ":" not in t:
            continue
        k, v = t.split(":", 1)
        try:
            out[k] = int(float(v))
        except ValueError:
            out[k] = v
    return out


def fmt(d, order):
    keys = [k for k in order if k in d] + [k for k in d if k not in order]
    return ",".join(f"{k}:{d[k]}" for k in keys)


def main():
    apply_ = "--apply" in sys.argv
    P = json.load(open(os.path.join(BASE, "parts.json"), encoding="utf-8"))
    parts = P["parts"]
    fixed, rounds = [], 0
    while rounds < 8:
        rounds += 1
        moved = 0
        for cat, items in parts.items():
            rows = []
            for n, raw in items.items():
                f = raw.split("|")
                if (f[6] if len(f) > 6 else "") in SKIP_SRC:
                    continue
                rows.append((n, f, parse(f[4])))
            for n, f, st in rows:
                ints = {k: v for k, v in st.items() if isinstance(v, int)}
                if not ints:
                    continue
                for n2, f2, st2 in rows:
                    if n2 == n:
                        continue
                    if int(f2[5]) > int(f[5]) or int(f2[2]) > int(f[2]):
                        continue
                    i2 = {k: v for k, v in st2.items() if isinstance(v, int)}
                    if set(ints) != set(i2):
                        continue
                    if not (all(ints[k] <= i2[k] for k in ints) and any(ints[k] < i2[k] for k in ints)):
                        continue
                    new = dict(st)
                    for k in ints:
                        want = max(i2[k] + 1, int(round(i2[k] * MARGIN)))
                        if ints[k] < want:
                            new[k] = want
                    order = list(st)
                    f[4] = fmt(new, order)
                    parts[cat][n] = "|".join(f)
                    fixed.append((cat, n, n2, fmt(st, order), f[4]))
                    moved += 1
                    break
        if not moved:
            break

    print(f"완전열등 해소 {len(fixed)}건 (라운드 {rounds})")
    for cat, a, b, before, after in fixed:
        print(f"   {cat:<5}{a:<18} < {b}")
        print(f"        {before}\n     →  {after}")
    if not fixed:
        print("   🟢 없음")
        return
    if not apply_:
        print("\n[dry-run] --apply 로 반영")
        return
    json.dump(P, open(os.path.join(BASE, "parts.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n✅ parts.json 반영")


if __name__ == "__main__":
    main()
