#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D등급 레벨제한 하향 — 진입을 Lv5 → Lv3 으로 (2026-08-27).

유저 지시: "D등급 렙제를 좀 낮출 필요가 있어 3렙부터 시작하도록. 튜토 깨면 3렙
극초반이라서 말이야"

문제: 튜토리얼을 마치면 Lv3 인데 **D등급 최저 레벨이 5** 였다. Lv3~4 는 E등급(Lv1)
말고는 살 것도 만들 것도 없는 죽은 구간이었다.

처방: D 26종 전부 **−2 레벨** (Lv5~9 → Lv3~7). 티어 내부 간격(5/6/7/8/9 로 의도적으로
계단을 둔 것)을 보존하고 티어 전체를 2 레벨 앞으로 당긴다. 개별 아이템만 옮기면
중간 레벨이 비어 «Lv5 에 새로 살 게 없는» 다른 죽은 구간이 생긴다.
  · `철 작살`(D, Lv1, 튜토 지급)은 이미 하한 밖 — 건드리지 않는다.
  · 상한이 9 → 7 로 내려가면서 **Lv8~9 는 C(Lv10)를 위해 모으는 구간**이 된다.
    구 배치는 Lv9 D → Lv10 C 로 숨돌릴 틈이 없었다.

★레벨제한의 권위는 `parts.json` 6번째 필드 하나다(`PartShopGui` 가 구매를,
  `PartLoader` 가 제작을 이 값으로 막는다). recipes.json 에는 레벨 필드가 없다 —
  레시피는 결과 부품의 레벨제한을 따른다. 그래서 이 파일만 고치면 된다.

★성능은 건드리지 않는다. 요청은 «접근성»이고, 성능을 레벨 사다리에 다시 맞추면
  D 를 13% 너프하는 셈이 되어 요청과 반대가 된다. 대신 `rod_lines.py` 의 사다리
  계수를 새 레벨 배치로 재적합한다(사다리는 «레벨→성능» 서술이므로 레벨이 바뀌면
  서술도 바뀐다).

사용:
    python3 patch_d_tier_levels.py <BlockShip 데이터 폴더> [--apply]
"""
import json, os, shutil, sys

#: 구 레벨 → 새 레벨. D 티어 내부 계단을 보존한 −2 시프트.
SHIFT = {5: 3, 6: 4, 7: 5, 8: 6, 9: 7}
#: 하한 밖 예외 — 튜토 지급품은 이미 Lv1 이다.
EXEMPT = {"철 작살"}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src, apply_ = sys.argv[1], "--apply" in sys.argv
    path = os.path.join(src, "parts.json")
    P = json.load(open(path, encoding="utf-8"))

    log, skipped = [], []
    for slot, items in P["parts"].items():
        for name, raw in list(items.items()):
            f = raw.split("|")
            if f[1] != "D":
                continue
            lv = int(f[5])
            if name in EXEMPT or lv not in SHIFT:
                skipped.append((slot, name, lv))
                continue
            f[5] = str(SHIFT[lv])
            items[name] = "|".join(f)
            log.append((slot, name, lv, SHIFT[lv]))

    print(f"[parts.json] D등급 {len(log)}종 레벨 하향")
    for slot, name, a, b in sorted(log, key=lambda x: (x[2], x[0])):
        print(f"  · {slot:<4}{name:<18} Lv{a} → Lv{b}")
    if skipped:
        print(f"\n  건드리지 않음 {len(skipped)}종: "
              + ", ".join(f"{n}(Lv{l})" for _, n, l in skipped))

    # 검증 — E(1) < D(새 하한) < C(10) 이 유지되는지
    band = {}
    for slot, items in P["parts"].items():
        for name, raw in items.items():
            f = raw.split("|")
            band.setdefault(f[1], []).append(int(f[5]))
    print("\n  등급 레벨 밴드:")
    for g in "EDCBAS":
        if g in band:
            print(f"    {g}: Lv{min(band[g])}~{max(band[g])} ({len(band[g])}종)")
    dmin = min(l for _, _, _, l in log) if log else None
    if dmin is not None and dmin <= max(band.get("E", [1])):
        sys.exit(f"❌ D 하한 Lv{dmin} 이 E 상한과 겹친다")
    if log and max(l for _, _, _, l in log) >= min(band.get("C", [10])):
        sys.exit("❌ D 상한이 C 하한과 겹친다")
    print("  🟢 E < D < C 순서 유지")

    if not apply_:
        print("\n[dry-run] --apply 로 실제 반영")
        return
    shutil.copy(path, path + ".bak-dtier")
    json.dump(P, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n✅ 반영 · 백업 {os.path.basename(path)}.bak-dtier")
    print("   ★강화표는 레벨과 무관하지만 성능 사다리는 레벨 함수다 —")
    print("     `rod_lines.py` 사다리 계수 재적합 필요. /데이터리로드 또는 재시작.")


if __name__ == "__main__":
    main()
