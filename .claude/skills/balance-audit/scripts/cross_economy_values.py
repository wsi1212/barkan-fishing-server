#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cross_economy_values.py — 전 경제(낚시·광질·농사·채집) 원재료에 골드 가치를 매기는 통합 모델.

★2026-08-05 전면 재작성. 바뀐 것 두 가지:
  1) **앵커가 단일 상수가 아니다.** 구 버전은 `ANCHOR_WON_PER_HOUR = 32489` 하나로 전 경제를
     환산했는데, 그 값 자체가 틀렸고(피티 미반영 + 150캐스트/h 가정 → 실측의 1/3~1/16)
     애초에 **구간마다 낚시 시급이 4배 차이**나서 단일 상수가 성립하지 않는다.
     이제 낚시 시급을 구간별로 뽑아(price_ladder.stage_table) **활동의 레벨 게이트에 맞는
     앵커**를 권장값으로 표시하고, 3개 앵커 전부를 병기한다.
  2) **드랍 분포를 실제 가중치로 계산한다.** 구 버전은 섬광산 드랍을 손으로 적은 qty로
     계산했는데, 스냅샷에 실제 weight/qty_min/qty_max가 있다(pull_mining.py).

핵심 원칙: "시간"의 의미는 경제마다 다르다.
- 능동 경제(낚시/드릴채굴/채집): 그 시간 동안 다른 걸 못 함 → 기회비용 = 그 구간의 낚시 시급.
- 반능동(섬광산): 클릭 기반이나 도구티어+호퍼캡으로 제약(운영자 확인) → 같은 앵커, 느긋한 채굴 가정.
- 수동 경제(농사): 성장시간 동안 플레이어는 자유 → growSec는 비용이 아니다. 진짜 비용은
  "플롯 슬롯"(유한하고 돈으로 사야 함) 점유 기회비용.

사용법: python3 cross_economy_values.py [--anchor 초반|중반|종결]
"""
import argparse, importlib.util, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)


def _load_price_ladder():
    spec = importlib.util.spec_from_file_location("price_ladder", os.path.join(HERE, "price_ladder.py"))
    m = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, ["price_ladder"]
    spec.loader.exec_module(m)
    sys.argv = saved
    return m


PL = _load_price_ladder()
_STAGES = {r["grade"]: r for r in PL.stage_table()}

# 구간 앵커 — 낚시 시급(원/h). ★단일 상수 금지. price_ladder와 같은 소스에서 파생된다.
ANCHORS = {
    "초반": _STAGES["D"]["won_h"],   # Lv5~9   스폰도시 풀
    "중반": _STAGES["B"]["won_h"],   # Lv20~39 강/붉은사막 풀
    "종결": _STAGES["S"]["won_h"],   # Lv60~70 늪지대 전등급 풀
}

# 활동별 권장 앵커 — 그 콘텐츠의 레벨 게이트로 결정한다(코드 실측).
RECOMMENDED = {
    "드릴 T1 (흑정석)": "중반",     # 레벨 게이트 없음(3,000원 구매) — 실사용은 중반
    "드릴 T2 (철광석)": "중반",     # DrillShopGui.T2_LEVEL = 15
    "드릴 T3 (자수정)": "중반",     # DrillShopGui.T3_LEVEL = 30 (B구간 20~39 안)
    "섬광산": "중반",               # 레벨 게이트 없음, 개인섬 필요
    "농사(특수작물)": "중반",       # 섬 플롯 업그레이드가 실질 게이트
    "채집": "중반",                 # 지역 접근이 실질 게이트
}


def load_snapshot(name):
    p = os.path.join(SKILL, "audits", "snapshots", name)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def won_per_sec(anchor_name):
    return ANCHORS[anchor_name] / 3600.0


def fmt(v):
    return f"{v:,.0f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchor", default="중반", choices=list(ANCHORS))
    ap.add_argument("--mining-snapshot", default="2026-08-05-mining.raw.json")
    ap.add_argument("--farming-snapshot", default="2026-08-05-farming.raw.json")
    args = ap.parse_args()

    print("=" * 82)
    print("공통 앵커 — ★단일 상수가 아니다 (구 32,489원/h는 2026-08-05 폐기)")
    print("=" * 82)
    for k, v in ANCHORS.items():
        print(f"  {k:<4} {fmt(v):>10}원/h = {v/3600:>7.2f}원/초"
              f"{'   ← 기본 표시 앵커' if k == args.anchor else ''}")
    print("  근거: price_ladder.stage_table() — 실측 220 포획/h + 피티 반영 몬테카를로")

    mine = load_snapshot(args.mining_snapshot)["raw"]
    farm = load_snapshot(args.farming_snapshot)["raw"]
    wps = won_per_sec(args.anchor)

    # ── 1. 광질 — 드릴채굴 ────────────────────────────────────────────────
    print("\n" + "=" * 82)
    print(f"### 광질 — 드릴채굴 (능동, break_ticks = 활동시간)   앵커: {args.anchor}")
    print("=" * 82)
    print(f"{'광맥':<16}{'T':>2}{'활동':>7}{'평균개':>7}{'블록당':>10}{'개당':>10}   재생")
    print("─" * 82)
    tier_units = {}
    for o in mine["drill"]["ores"]:
        sec = o["break_ticks"] / 20.0
        qty = (o["qty_min"] + o["qty_max"]) / 2.0
        won = sec * wps
        per_unit = won / qty
        tier_units.setdefault(o["drop"], []).append(per_unit)
        print(f"{o['label']:<16}{o['tier']:>2}{sec:>6.1f}초{qty:>7.1f}{fmt(won):>10}{fmt(per_unit):>10}"
              f"   {o['regen_sec']}초")
    mineral = {k: sum(v) / len(v) for k, v in tier_units.items()}
    print("\n  → 평균 단가: " + " · ".join(f"{k} {fmt(v)}원/개" for k, v in mineral.items()))
    print(f"  압축흑정석(흑정석×9) = {fmt(mineral['흑정석']*9)}원 · "
          f"압축철광석(철광석×9) = {fmt(mineral['철광석']*9)}원")
    print("  ★주의: 위는 '활동시간만' 센 상한값이다. 광맥 재생 180~480초라 노드 수가 적으면"
          "\n    대기시간이 붙어 실제 개/h는 이보다 낮고 → 개당 실질가치는 더 높다.")

    # ── 2. 광질 — 섬광산 (실제 weight/qty 반영) ──────────────────────────
    print("\n" + "=" * 82)
    print(f"### 광질 — 섬광산 (반능동, 블록당 {1.5}초 가정 — 도구상한+호퍼캡으로 광클 불가)")
    print("=" * 82)
    SEC_PER_BLOCK = 1.5
    won_block = SEC_PER_BLOCK * wps
    print(f"  블록 1개 = {SEC_PER_BLOCK}초 → {fmt(won_block)}원의 노동")
    print("  ★배분 방식(2026-08-05 수정): 한 블록은 **고를 수 없는 결합생산물**이라 '블록노동÷수량'으로"
          "\n    개당가를 매기면 확률이 통째로 무시된다(구 버전 오류 — 돌과 다이아가 같은 값이 나옴).")
    print("    희소도 비례 배분을 쓴다: value_i ∝ 1/기대산출_i 이고, 전체 배분액이 블록노동과 같도록"
          "\n    정규화 → value_i = 블록노동 / (종류수 × 기대산출_i).")
    print(f"\n{'광물':<10}{'확률':>7}{'평균개':>8}{'기대개/블록':>12}{'개당가치':>12}{'몇블록/개':>11}")
    print("─" * 82)
    island = {}
    ores = mine["island_mine"]["ores"]
    n_types = len(ores)
    for o in ores:
        p = o["chance_pct"] / 100.0
        qty = (o["qty_min"] + o["qty_max"]) / 2.0
        exp = p * qty                       # 블록당 기대 산출
        per_unit = won_block / (n_types * exp) if exp else 0
        island[o["label"]] = per_unit
        print(f"{o['label']:<10}{o['chance_pct']:>6.1f}%{qty:>8.1f}{exp:>12.3f}{fmt(per_unit):>12}"
              f"{1/exp if exp else 0:>11.1f}")
    print("\n  강화계열(원석×16 압축) 재료가치:")
    for name, base in [("강화철괴", "철"), ("강화금괴", "금"), ("강화다이아몬드", "다이아몬드"),
                       ("강화에메랄드", "에메랄드"), ("강화청금석", "청금석"), ("강화석탄", "석탄")]:
        print(f"    {name:<14}{fmt(island[base]*16):>12}원")

    # ── 3. 농사 — 슬롯 임대료 모델 ────────────────────────────────────────
    print("\n" + "=" * 82)
    print("### 농사 — 특수작물 (수동, 슬롯 임대료 모델: growSec는 비용이 아니다)")
    print("=" * 82)
    lim = farm["plot_limits"]["individual"]
    total_price = sum(lim["price"])
    max_slots = max(lim["limit"])
    SLOT_LIFETIME_HOURS = 100  # ★가정 — 실측 대체 가능(플레이어 평균 사용기간)
    slot_h = (total_price / max_slots) / SLOT_LIFETIME_HOURS
    print(f"  플롯 업그레이드 총액 {fmt(total_price)}원 ÷ {max_slots}슬롯 ÷ {SLOT_LIFETIME_HOURS}h"
          f" = 슬롯당 {slot_h:.1f}원/h (★수명은 가정치)")
    print(f"\n{'작물':<8}{'성장':>8}{'수확':>6}{'개/h':>8}{'슬롯비용/개':>13}{'앵커대비':>10}")
    print("─" * 82)
    for c in farm["crops"]:
        sec, qty = c["grow_sec"], c["qty"]
        per_h = c["qty_per_hour"]
        slot_cost = slot_h * sec / 3600.0
        per_unit = slot_cost / qty
        print(f"{c['id']:<8}{sec/60:>6.0f}분{qty:>6}{per_h:>8.2f}{per_unit:>13.2f}"
              f"{per_unit/ANCHORS[args.anchor]*3600:>9.2f}초")
    print("  ★해석: 작물 1개의 '원가'는 슬롯 점유 임대료뿐이라 극히 싸다(수 초 노동 상당).")
    print("    즉 농사는 시간이 아니라 **슬롯 수**가 병목 — 수익성 판정은 개당가가 아니라"
          "\n    '슬롯당 시간수익(원/슬롯/h)'으로 해야 한다.")
    print(f"\n{'작물':<8}{'슬롯당 시간수익 지표(개/h)':>26}   ※제출/요리 가치는 별도")
    for c in sorted(farm["crops"], key=lambda x: -x["qty_per_hour"]):
        print(f"{c['id']:<8}{c['qty_per_hour']:>20.2f} 개/h")

    # ── 4. 채집 ──────────────────────────────────────────────────────────
    print("\n" + "=" * 82)
    print("### 채집 (능동, 8스윙 리듬 미니게임 + 유저별 쿨타임)")
    print("=" * 82)
    SWINGS, AVG_SWING_SEC = 8, 1.2
    action_sec = SWINGS * AVG_SWING_SEC
    action_won = action_sec * wps
    COMMON_CD, RARE_CD = 5400, 72000     # ForageManager: 흔함 90분 / 희귀 20시간
    scarcity = RARE_CD / COMMON_CD
    print(f"  1회 채집 행동 {action_sec:.1f}초 → {fmt(action_won)}원 (흔함 기준선)")
    print(f"  희귀 쿨타임비 {RARE_CD/3600:.0f}h / {COMMON_CD/3600:.1f}h = {scarcity:.2f}배"
          f" → 희귀 1회 ≈ {fmt(action_won*scarcity)}원")
    print("  ★이 값은 floor(하한)다 — 노드 밀도(시간당 몇 회 가능한가)는 서버 빌드 데이터라 미지수.")

    # ── 5. 요약 + 3앵커 병기 ─────────────────────────────────────────────
    print("\n" + "=" * 82)
    print("요약 — 개당 원화가치 (3개 앵커 병기)")
    print("=" * 82)
    base = {
        "흑정석": mineral["흑정석"], "철광석": mineral["철광석"], "자수정": mineral["자수정"],
        "압축흑정석": mineral["흑정석"] * 9, "압축철광석": mineral["철광석"] * 9,
        **island,
        "채집(흔함)": action_won, "채집(희귀)": action_won * scarcity,
    }
    ratio = {k: ANCHORS[k] / ANCHORS[args.anchor] for k in ANCHORS}
    print(f"{'재료':<16}" + "".join(f"{k:>12}" for k in ANCHORS) + "   권장앵커")
    print("─" * 82)
    rec_of = {"흑정석": "드릴 T1 (흑정석)", "압축흑정석": "드릴 T1 (흑정석)",
              "철광석": "드릴 T2 (철광석)", "압축철광석": "드릴 T2 (철광석)",
              "자수정": "드릴 T3 (자수정)",
              "채집(흔함)": "채집", "채집(희귀)": "채집"}
    for k, v in sorted(base.items(), key=lambda x: -x[1]):
        act = rec_of.get(k, "섬광산")
        print(f"{k:<16}" + "".join(f"{fmt(v*ratio[a]):>12}" for a in ANCHORS)
              + f"   {RECOMMENDED[act]}({act})")
    print("\n※ 구 버전 대비: 앵커가 32,489 → 중반 기준 "
          f"{ANCHORS['중반']:,.0f}원/h 이므로 전 재료 가치가 일괄 "
          f"×{ANCHORS['중반']/32489:.2f} (종결 앵커면 ×{ANCHORS['종결']/32489:.2f}).")


if __name__ == "__main__":
    main()
