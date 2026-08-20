#!/usr/bin/env python3
"""
cross_economy_values.py — 전 경제(낚시·광질·농사·채집) 원재료에 골드 가치를 매기는 통합 모델.

핵심 원칙: "시간"의 의미는 경제마다 다르다.
- 능동 경제(낚시/드릴채굴/채집): 플레이어가 그 시간 동안 다른 걸 못 함 → 기회비용 = 낚시 시급(앵커).
- 반능동(섬광산): 클릭 기반이나 바닐라 도구티어+호퍼캡으로 이미 안전하게 제약(운영자 확인) →
  같은 앵커를 쓰되 "느긋한 채굴" 가정(광클 아님).
- 수동 경제(농사): 성장시간 동안 플레이어는 자유(다른 활동 가능) → growSec 자체는 비용이 아니다.
  진짜 비용은 "플롯 슬롯"(유한하고 돈으로 사야 함) 점유 기회비용.

앵커: 실행 시 최신 raw snapshot의 stat_value.py 결과를 읽는다. 과거 32,489원/h는
고정 레거시 값이며 현재 코드가 바뀌어도 유지되는 상수가 아니다.
"""
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import stat_value as sv

skill_dir = SCRIPT_DIR.parent
snapshot_dir = skill_dir / "audits" / "snapshots"
snapshot_override = os.environ.get("BALANCE_SNAPSHOT")
if snapshot_override:
    snapshot_path = Path(snapshot_override)
else:
    snapshots = sorted(p for p in snapshot_dir.glob("*.raw.json") if "pending" not in p.name)
    snapshot_path = snapshots[-1] if snapshots else None
if snapshot_path and snapshot_path.exists():
    _snapshot = sv.load_snapshot(str(snapshot_path))
    ANCHOR_WON_PER_HOUR = round(sv.compute(_snapshot, 150, 50)[0])
else:
    raise SystemExit("raw snapshot이 없습니다. pull.py를 먼저 실행하세요.")
ANCHOR_WON_PER_SEC = ANCHOR_WON_PER_HOUR / 3600  # 9.0247

print("=" * 78)
print(f"공통 앵커: 낚시 무버프 시급 {ANCHOR_WON_PER_HOUR:,}원/h = {ANCHOR_WON_PER_SEC:.4f}원/초")
print("=" * 78)

# ── 1. 광질 — 드릴채굴 (능동, breakTicks=활동시간, T1기준 표준 인건비) ──────
print("\n### 광질 — 드릴채굴 (능동, T1 기준 breakTicks=활동시간)")
drill_ores = [
    ("얇은 흑정석 광맥", 30, "흑정석", 1),
    ("흑정석 광맥", 50, "흑정석", 1.5),   # 1~2개 평균
    ("풍부한 흑정석 광맥", 80, "흑정석", 2),  # 1~3개 평균
    ("얇은 자수정 광맥", 40, "자수정", 1),
    ("자수정 광맥", 60, "자수정", 1.5),
    ("자수정 정동", 90, "자수정", 2),
    ("자수정 군집", 70, "자수정", 1.5),
]
mineral_unit_values = {}
for label, ticks, drop, qty in drill_ores:
    sec = ticks / 20
    won = sec * ANCHOR_WON_PER_SEC
    per_unit = won / qty
    print(f"  {label:<14} {sec:>5.1f}초 → 블록당 {won:>6.1f}원 → {drop} 1개당 {per_unit:>6.1f}원")
    mineral_unit_values.setdefault(drop, []).append(per_unit)

for k in list(mineral_unit_values):
    mineral_unit_values[k] = sum(mineral_unit_values[k]) / len(mineral_unit_values[k])
print(f"\n  → 흑정석 평균단가 {mineral_unit_values['흑정석']:.1f}원/개, 자수정 평균단가 {mineral_unit_values['자수정']:.1f}원/개")

# 압축흑정석 = 흑정석9개 조합 (조합 자체는 무료, 재료비만)
compressed_bg = mineral_unit_values['흑정석'] * 9
print(f"  압축흑정석(흑정석9 조합) 재료가치 = {compressed_bg:.0f}원")

# ── 2. 광질 — 섬광산 (반능동, 가정: 블록당 1.5초 느긋한 채굴 — 광클 아님, 운영자 확인 반영) ──
print("\n### 광질 — 섬광산 (반능동, ★가정: 블록당 1.5초 — 도구상한+실측으로 광클 불가 확인됨)")
ASSUMED_SEC_PER_BLOCK = 1.5
island_ores = [
    ("돌", "cobblestone", 1), ("석탄", "coal", 1), ("철", "raw_iron", 1),
    ("구리", "raw_copper", 3), ("금", "raw_gold", 1), ("청금석", "lapis_lazuli", 6),
    ("다이아몬드", "diamond", 1), ("에메랄드", "emerald", 1),
]
island_unit_values = {}
won_per_block = ASSUMED_SEC_PER_BLOCK * ANCHOR_WON_PER_SEC
for label, drop, qty in island_ores:
    per_unit = won_per_block / qty
    island_unit_values[label] = per_unit
    print(f"  {label:<8}({drop:<12}) 평균{qty}개/블록 → {per_unit:>6.1f}원/개")

# 강화X = 바닐라 원석 16개 압축
print("\n  강화계열(원석×16 압축) 재료가치:")
for name, base in [("강화철괴", island_unit_values["철"]), ("강화금괴", island_unit_values["금"]),
                    ("강화다이아몬드", island_unit_values["다이아몬드"]), ("강화에메랄드", island_unit_values["에메랄드"]),
                    ("강화청금석", island_unit_values["청금석"]), ("강화석탄", island_unit_values["석탄"])]:
    print(f"    {name}: {base*16:.0f}원")

# ── 3. 농사 — 크롭 (수동, 슬롯 임대료 모델) ──────────────────────────────
print("\n### 농사 — 크롭 (수동, ★슬롯 임대료 모델: growSec는 비용 아님)")
print("  방법: 슬롯 1개의 '가치'는 그 슬롯이 낼 수 있는 최선의 산출(밀=9.00개/h)에 준한다고 가정")
print("  (합리적 농부라면 최고효율 작물로 슬롯을 채우므로, 슬롯의 기회비용=밀 재배 포기분)")
print("  단, 작물별 개/h가 다르므로 '작물 하나의 가치' = 슬롯임대료 ÷ 그 작물의 개/h")
crops = [("밀", 1200, 3), ("당근", 1800, 2), ("감자", 2700, 2), ("토마토", 3600, 2),
         ("양배추", 1500, 2), ("버섯", 2400, 3), ("수박", 86400, 4)]
# 슬롯임대료 추정: 5레벨(32칸) 총 810,000원을 "슬롯-생애가치"로 보고, 생애를 밀 300회 수확(약 100h)으로 가정
# → 슬롯당 부담 810,000/32 = 25,312.5원 ì 100h = 253.1원/h (근사, 명시적 가정)
SLOT_LIFETIME_HOURS = 100  # ★가정치 — 명시. 실측 대체 가능(플레이어 평균 사용기간 확인 시)
slot_won_per_hour = (810000 / 32) / SLOT_LIFETIME_HOURS
print(f"  슬롯당 시간가치 가정: {slot_won_per_hour:.1f}원/h (★가정: 슬롯비용 25,312.5원 ÷ {SLOT_LIFETIME_HOURS}h 수명)")
for name, sec, qty in crops:
    per_h = qty * 3600 / sec
    slot_cost_per_batch = slot_won_per_hour * sec / 3600
    per_unit = slot_cost_per_batch / qty
    print(f"  {name:<6} {qty}개/{sec/60:.0f}분 ({per_h:.2f}개/h) → 1개당 슬롯비용 {per_unit:>6.2f}원")

# ── 4. 채집 (능동, 8스윙 행동시간 + 희귀도 배율) ────────────────────────
print("\n### 채집 (능동, 8스윙×평균1.2초=행동시간, 희귀는 쿨타임비 배율 적용)")
SWINGS = 8
AVG_SWING_SEC = 1.2  # (0.35~2초 구간 중간값 가정)
action_sec = SWINGS * AVG_SWING_SEC
action_won = action_sec * ANCHOR_WON_PER_SEC
print(f"  1회 채집 행동시간 {action_sec:.1f}초 → 행동가치 {action_won:.1f}원 (흔함 기준선)")
common_cd, rare_cd = 5400, 72000
scarcity_mult = rare_cd / common_cd
print(f"  희귀 쿨타임비(20h/1.5h)={scarcity_mult:.2f}배 → 희귀 채집물 가치 ≈ {action_won*scarcity_mult:.0f}원")
print(f"  ★가정 명시: 행동시간은 확정(코드), 노드밀도(실제 시간당 몇 회 가능한지)는 서버빌드 데이터라 미지수.")
print(f"  위 값은 '행동당 최소가치'(floor) — 실제 개/h는 밀도에 따라 이보다 낮아질 수 있음(대기시간 포함 시).")

print("\n" + "=" * 78)
print("전체 요약 (개당 원화가치)")
print("=" * 78)
summary = {
    "흑정석": mineral_unit_values['흑정석'], "자수정": mineral_unit_values['자수정'],
    "압축흑정석": compressed_bg,
    **{k: v for k, v in island_unit_values.items()},
    "채집(흔함, floor)": action_won, "채집(희귀, floor)": action_won * scarcity_mult,
}
for k, v in sorted(summary.items(), key=lambda x: -x[1]):
    print(f"  {k:<16} {v:>8.1f}원")
