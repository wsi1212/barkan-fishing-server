#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""숙련형(난이도) 사다리를 A 7 · S 9 로 올린다 (유저 지시 2026-09-07).

★무엇이 평평했나 — 난이도 최댓값이 D2 → C3 → B5 → A5 → S5 로 B 에서 멈춰 있었다.
  생성기 표(PRIMARY/CAP)는 S 8 까지 허용하는데 S급 숙련형 낚싯대가 카탈로그에 없어서
  8 이 도달 불가 상한이었고, 2026-08-27 주석이 «숙련형 기본을 D3/C5/B7 로 올렸다» 고
  적어 둔 것도 실제로는 검증 상한만 올라갔지 값 표는 구 밴드 그대로였다.
  유저 결정: B 5(방벽 낚싯대)는 그대로 두고 A·S 만 올린다.

난이도는 포화하지 않는 스탯이다(zoneWidth = 8 + floor(net/2), 고등급은 net 이 깊게 음수).
그래서 값 하나가 성공률을 크게 흔든다 — 실측(반응 290ms, 4000회):
    A 어종  난5 44.9% → 난7 63.9%
    S 어종  난5  7.3% → 난9 31.1%
    풀스택(강화2+요리6): S 현행 13 → 64.6% · S9 스택 17 → 100%
"""
import json, shutil, sys, datetime

TARGET = {  # 이름 → 새 난이도 (등급별 숙련형 라인)
    "열사의 낚싯대": 7, "흑단목 낚싯대": 7, "수호자의 낚싯대": 7, "선단장의 낚싯대": 7,  # A
    "모래폭풍의 낚싯대": 9,                                                          # S
}
path, mode = sys.argv[1], sys.argv[2]
D = json.load(open(path, encoding="utf-8"))
rods = D["parts"]["낚싯대"]
rows = []
for n, new in TARGET.items():
    if n not in rods: sys.exit(f"❌ {n} 없음")
    f = rods[n].split("|")
    st = f[4].split(",")
    for i, kv in enumerate(st):
        if kv.startswith("난이도:"):
            old = float(kv.split(":")[1])
            if old != new:
                st[i] = f"난이도:{new}"
                rows.append((n, f[1], int(f[5]), old, new, int(f[2])))
            break
    else:
        sys.exit(f"❌ {n} 에 난이도 스탯이 없다")
    f[4] = ",".join(st); rods[n] = "|".join(f)
print(f"■ 숙련형 난이도 상향 {len(rows)}종")
for n, g, lv, o, w, pr in sorted(rows, key=lambda x: (x[1], x[2])):
    print(f"   {g}급 Lv{lv:<3} {n:<16} 난이도 {o:g} → {w}   ({pr:,}원 · 가격 변경 없음)")
if mode != "--write": print("\n(드라이런)")
else:
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(path, f"{path}.bak-mastery-{ts}")
    json.dump(D, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.load(open(path, encoding="utf-8"))
    print(f"\n✅ 기록 (백업 .bak-mastery-{ts})")
