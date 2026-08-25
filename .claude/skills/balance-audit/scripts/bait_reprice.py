#!/usr/bin/env python3
"""미끼 가격 재산출 — «미끼 = 캐스트마다 돈이 나가는 소모품»이 설계 의도임을 유저가 확정
(2026-08-26)한 뒤, 그 규칙 위에서 가격을 다시 뽑는다.

★구 가격은 «미끼 1개 = 내구도만큼의 캐스트»를 전제로 뽑혀 있었다
  (gen_part_builds.py BAIT_PRICE_MULT · price_ladder.py BAIT_DUR). 규칙이 반대이므로 가격이
  내구 배(D 70배~A 340배)로 부풀어 A급 미끼가 수입의 916%가 됐고, prod 텔레메트리상 실제로
  A/B급 미끼는 거의 장착되지 않는다(지렁이가 구매 43%).

권위 수치:
  K = 포획 1회당 미끼 소모 개수 — reduceDurability 는 «미니게임 결과»에만 걸린다(캐스트마다 아님).
      prod events-2026-08 비OP 6명·39.2h 실측 = 1.027
  W = 원/포획 (price_ladder.py) — 유지비율(가격×K÷W)은 수입 앵커와 무관한 불변량이라
      «220 포획/h 가정»의 드리프트에 영향받지 않는다.
  R = 등급별 지불비율. 고티어일수록 낮춰(가성비 우대) 종결 유저가 A 미끼로 졸업할 유인을 만든다.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from material_gate import META, PARTS, stat_of
K=1.027                                   # 실측: 포획 1회당 미끼 개수
W={"E":434,"D":434,"C":605,"B":605,"A":1572,"S":1683}   # 원/포획 (price_ladder)
NORM={"경험치":1.00,"등급업":1.68,"판매보너스":1.00,"더블찬스":1.00,"재료확률":1.00,
      "크리확률":0.48,"크기":0.60,"행운":0.50,"크리배율":2.41,"트리플찬스":2.00,
      "도망감소":0.47,"난이도":8.82,"내구보존":0.0}
def S(n):
    t=0
    for tok in META[n]['stats'].split(','):
        if ':' not in tok: continue
        k,v=tok.split(':',1)
        try: v=float(v)
        except: continue
        t+=NORM.get(k,0)*v
    return t
R={"E":0.90,"D":0.80,"C":0.70,"B":0.55,"A":0.40}   # 고티어일수록 «가성비» 우대 → 졸업 유인
order={"E":0,"D":1,"C":2,"B":3,"A":4}
baits=sorted(PARTS['미끼'], key=lambda n:(order[META[n]['grade']],META[n]['lvl']))
print("제안 — 등급별 지불비율 R:", ", ".join(f"{k} {v:.0%}" for k,v in R.items()))
print(f"가격 = R × S% × (원/포획) ÷ {K}\n")
print(f"{'등급':<3}{'Lv':>4} {'이름':<18}{'S%':>6}{'현재가':>8}{'신가격':>8}{'변화':>8}"
      f"{'자기티어 순이득%':>16}{'종결 순이득%':>13}  재료확률")
prev=None
for n in baits:
    m=META[n]; g=m['grade']; s=S(n)
    p=max(1,round(R[g]*s/100*W[g]/K))
    own = s - p*K/W[g]*100
    end = s - p*K/1683*100
    mark = "" if prev is None or end>=prev else "  ← 역전"
    prev=max(prev or 0, end)
    print(f"{g:<3}{m['lvl']:>4} {n:<18}{s:>6.1f}{m['price']:>8,}{p:>8,}{p/m['price']:>7.2f}x"
          f"{own:>15.1f}%{end:>12.1f}%  {stat_of(n,'재료확률'):g}{mark}")
print("\n※ «자기티어 순이득» = 그 등급 수입 기준 (스탯가치% − 유지비율%). 전부 양수 = 끼면 이득.")
print("※ «종결 순이득» = Lv.60+ 수입(1,683원/포획) 기준. 등급 따라 단조 증가 = 고티어 미끼로 졸업할 유인.")
