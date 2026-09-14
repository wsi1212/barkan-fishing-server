#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
measured.py — 실측 상수의 **단일 출처**. 다른 스크립트는 여기서만 가져간다.

★2026-08-26 신설. 그전엔 스크립트마다 자기 상수를 하드코딩하고 있었다:
    price_ladder.py   CATCH_PER_HOUR = 220 · SIZE_SCORE = 65.6
    stat_value.py     CATCH_PER_HOUR = 220 · COMPLETION = 0.85 · SIZE_SCORE = 65.6
    material_gate.py  CATCH_H = 220 · ATTEMPT_H = 259
    gear_payback.py   HARP_CATCH = 270 · HARP_Q = 84
같은 값을 네 군데 적어 두면 하나만 고쳐지고 나머지는 남는다 — 실제로 그렇게 됐고, 넉 달 뒤
실측이 190.1/194.0/97.2% 임을 알았을 때 네 파일을 다 찾아야 했다. 이 모듈이 그 반복을 끝낸다.

**«같은 소스에서, 같은 지표를, 같은 포맷으로»** 가 이 스킬의 설계 목적이다(SKILL.md 첫 줄).
상수가 갈라져 있으면 그 목적이 성립하지 않는다.

사용:
    import measured
    K = measured.load()                 # dict — 없으면 FALLBACK + is_fallback=True
    measured.apply(SV)                  # stat_value 모듈에 실측치를 주입
    python3 measured.py                 # 현재 실측치와 출처 확인
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)

# ── 폴백: 2026-08-26 prod 실측 (스냅샷이 없을 때만 쓴다) ────────────────────
#   ★이 값을 손으로 고치지 말 것. pull_players.py 를 돌려 스냅샷을 갱신하면 자동으로 이긴다.
#   폴백은 «스냅샷 없이도 스크립트가 돌게» 하는 안전망이고, 출처가 FALLBACK 이면 모든
#   스크립트가 첫 줄에 그렇게 찍는다.
FALLBACK = {
    "catches_per_active_h": 190.1,   # 포획/h — 활성 낚시 구간
    "attempts_per_active_h": 194.0,  # 소모(내구·미끼) 1회 = fish.result 1건
    "casts_per_active_h": 249.1,
    "completion_pct": 97.2,          # 결과 → 포획
    "cast_to_result_pct": 62.0,      # 캐스트 → 결과
    "escape_pct": 2.8,
    "size_score": 69.3,              # 평균 quality
    # ★등급별 실측 성공률 (1 − 도주율). 전체 97.2% 는 E/D/C 물량에 묻힌 값이고 고등급은 다르다.
    "success_by_grade": {"E": 0.996, "D": 0.995, "C": 0.981, "B": 0.870, "A": 0.706, "S": 0.190},
    "mean_difficulty_stat": 1.81,    # 모집단 평균 난이도 스탯 (캘리브레이션 기준점)
    "income_by_band": {"Lv1-9": 76493, "Lv10-19": 99645, "Lv20-29": 115083},
    "per_catch_by_band": {"Lv1-9": 402.0, "Lv10-19": 524.0, "Lv20-29": 606.0},
    "max_level_observed": 26,
    "region_mix_pct": {"항구": 67.2, "강": 18.9, "협곡": 4.3, "오아시스": 4.3},
    "harpoon": {"catches_per_active_h": 174.8, "quality_mean": 84.3,
                "aim_gap_s": 1.295, "approach_s": 2.639, "cycle_s": 17.302,
                "surface_s": 9.703, "spawn_to_catch_pct": 31.7, "hit_rate_pct": 17.9},
    "island_mine_per_hour": {"돌": 1926, "구리": 1577, "청금석": 1181, "석탄": 1054,
                             "철": 863, "금": 364, "다이아몬드": 296, "에메랄드": 294,
                             "네더라이트": 19},
    "drill_per_hour": {"흑정석": 2715, "철광석": 340},
    # ── 크리 (2026-09-14 prod 실측) ──────────────────────────────────────────
    # ★`크리확률 20` 을 «캐치의 20%» 로 읽는 환산은 금지다.  금칸은 존의 «칸마다» 굴러가고
    #   사람이 조준해야 하므로 실현치가 훨씬 높다 — 명목 20% 의 실측 실현 크리율은 45.7% 다.
    #   명목→실현은 `crit_telemetry.realised_from_nominal()` 하나만 쓴다.
    # ★`sb_eq_pct` = 판매보너스 등가치.  판매보너스·신선도를 **뺀** 등급×품질 기본가가 분모라
    #   "판매보너스 +19%" 와 정확히 같은 순수 판매수익이다.  크기보너스는 분자·분모에 똑같이
    #   들어가 비율에는 영향이 없다(원/캐치 절대값에는 들어간다).
    # ★갱신:  python3 crit_telemetry.py --remote      (698 MB DB 를 내려받지 않는다)
    "crit": {
        "era_kst": "2026-09-13",
        "catches": 16161, "criticals": 5182, "players": 80,
        "realised_rate": 0.32065,
        "realised_rate_value_weighted": 0.32439,
        "crit_damage_mean": 8.208,
        "crit_damage_value_weighted": 9.747,
        "sb_eq_pct": 18.95,
        "extra_won_per_catch": 115.0,
        "aim_conversion": 0.545,
        "aim_opportunities": 127173.0,
        "nominal_to_realised_slope_pp": 2.0,   # 플레이어 내 대조 50명 중앙값, 명목 50%+ 는 0
        "saturation_nominal_pct": 50,
        "evidence": "측정 가능",
        "_source": "FALLBACK(prod 2026-09-14)",
    },
    "_source": "FALLBACK(2026-08-26)", "is_fallback": True,
}

_cache = None


#: 구간 시급을 «환율»로 쓰기 위한 최소 표본(포획 건수).
#  이보다 얇으면 관측은 남기되 income_by_band 에서 빼 환율·앵커가 흔들리지 않게 한다.
MIN_BAND_N = 200


def snapshot_path():
    d = os.path.join(SKILL, "audits", "snapshots")
    if not os.path.isdir(d):
        return None
    c = sorted(f for f in os.listdir(d) if f.endswith("-players.raw.json"))
    return os.path.join(d, c[-1]) if c else None


def load(path=None, refresh=False):
    """최신 players 스냅샷 → 실측 상수. 없으면 FALLBACK."""
    global _cache
    if _cache is not None and not refresh and path is None:
        return _cache
    k = dict(FALLBACK)
    p = path or snapshot_path()
    if p and os.path.exists(p):
        s = json.load(open(p, encoding="utf-8"))
        f = s.get("fishing") or {}
        for src, dst in (("catches_per_active_h", "catches_per_active_h"),
                         ("results_per_active_h", "attempts_per_active_h"),
                         ("casts_per_active_h", "casts_per_active_h"),
                         ("completion_pct", "completion_pct"),
                         ("cast_to_result_pct", "cast_to_result_pct"),
                         ("escape_pct", "escape_pct"),
                         ("quality_mean", "size_score"),
                         ("success_by_grade", "success_by_grade"),
                         ("mean_difficulty_stat", "mean_difficulty_stat")):
            if f.get(src) is not None:
                k[dst] = f[src]
        if s.get("income_by_band"):
            # ★표본이 얇은 구간은 «환율»로 쓰지 않는다 (2026-09-01 신설).
            #   그날 스냅샷에 Lv30-49 가 **n=44** 로 처음 등장했는데, wage() 는 «관측 최고
            #   구간»을 쓰므로 전 경제의 원 환산이 113,167 → 80,504 (−29%) 로 한 번에 내려
            #   앉았다. selftest 3 종(구간 시급 단조 · 요구캐스트 비례 25종 · 작살 예측)이
            #   동시에 🔴 로 뒤집힌 게 그 여파다 — 콘텐츠가 바뀐 게 아니라 44 마리가 바꾼 것이다.
            #   버리지는 않는다(관측은 관측이다) — `income_by_band_thin` 에 남겨 보고한다.
            keep, thin = {}, {}
            for b, v in s["income_by_band"].items():
                if b == "미상":
                    continue
                (thin if v.get("n", 0) < MIN_BAND_N else keep)[b] = v
            k["income_by_band"] = {b: v["gross_per_active_h"] for b, v in keep.items()}
            k["per_catch_by_band"] = {b: v["price_mean"] for b, v in keep.items()}
            k["income_by_band_thin"] = {b: (v["gross_per_active_h"], v.get("n", 0))
                                        for b, v in thin.items()}
        if s.get("harpoon"):
            k["harpoon"] = {**k["harpoon"], **{kk: vv for kk, vv in s["harpoon"].items()
                                               if vv is not None and kk != "counts"}}
        if (s.get("island_mine") or {}).get("per_hour"):
            k["island_mine_per_hour"] = s["island_mine"]["per_hour"]
        if (s.get("drill") or {}).get("per_hour"):
            k["drill_per_hour"] = s["drill"]["per_hour"]
        if s.get("crit"):
            k["crit"] = {**k["crit"], **{kk: vv for kk, vv in s["crit"].items() if vv is not None}}
        if s.get("region_mix_pct"):
            k["region_mix_pct"] = s["region_mix_pct"]
        if (s.get("coverage") or {}).get("max_level_observed"):
            k["max_level_observed"] = s["coverage"]["max_level_observed"]
        k["warnings"] = s.get("warnings", [])
        k["_source"] = os.path.basename(p)
        k["is_fallback"] = False
    if path is None:
        _cache = k
    return k


def crit(k=None):
    """크리 실측 블록.  ★선형 환산 금지 — 명목 크확은 `crit_telemetry.realised_from_nominal()`."""
    return (k or load())["crit"]


def refresh_crit(revenue_since=None, write=True):
    """prod 에서 크리 상수를 다시 재고 FALLBACK 을 갱신할 값을 돌려준다.

    ★DB 를 내려받지 않는다 — 박스에서 집계해 JSON 만 받는다(2026-09-14 기준 698 MB).
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("crit_telemetry",
                                                  os.path.join(HERE, "crit_telemetry.py"))
    ct = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ct)
    out = ct.remote_constants(revenue_since or FALLBACK["crit"]["era_kst"])
    if write and out.get("evidence") == "측정 가능":
        d = os.path.join(SKILL, "audits", "snapshots")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, "crit-latest.json")
        json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        out["_written"] = path
    return out


def apply(SV, k=None):
    """stat_value 모듈에 실측치를 주입한다.

    ★`income_of` 의 기본인자는 import 시점에 바인딩되므로 `__defaults__` 도 같이 갈아야 한다.
      이걸 빼면 SIZE_SCORE 를 바꿔도 수입 계산은 옛 값으로 돈다(조용한 오차).
    """
    k = k or load()
    SV.CATCH_PER_HOUR = k["catches_per_active_h"]
    SV.CASTS_PER_HOUR = k["attempts_per_active_h"]
    SV.COMPLETION = k["completion_pct"] / 100.0
    SV.SIZE_SCORE = k["size_score"]
    # ★크리도 가정 상수를 쓰지 않는다 (제7원칙).  개수가중이 아니라 **금액가중**을 넣는다 —
    #   SB-eq 항등식 `r × d × 6%` 가 금액가중일 때만 성립하기 때문(개수가중은 17% 과소평가).
    c = k.get("crit") or {}
    if c.get("realised_rate_value_weighted") is not None:
        SV.DEFAULT_CRIT_RATE = c["realised_rate_value_weighted"]
    if c.get("crit_damage_value_weighted") is not None:
        SV.DEFAULT_CRIT_DMG = c["crit_damage_value_weighted"]
    try:
        SV.income_of.__defaults__ = (k["size_score"], 0.0)
    except Exception:
        pass
    return k


def banner(k=None):
    """모든 스크립트가 첫 줄에 찍는 출처 한 줄. 폴백이면 그렇게 밝힌다."""
    k = k or load()
    tag = "★FALLBACK — pull_players.py 로 실측을 갱신할 것" if k["is_fallback"] else k["_source"]
    c = k.get("crit") or {}
    return (f"실측: 포획 {k['catches_per_active_h']}/h · 소모 {k['attempts_per_active_h']}/h · "
            f"완주 {k['completion_pct']}% · 크기점수 {k['size_score']} · "
            f"크리 {c.get('realised_rate_value_weighted', 0) * 100:.1f}%×배율 "
            f"{c.get('crit_damage_value_weighted', 0):.1f} = SB-eq {c.get('sb_eq_pct', 0):.1f}% · "
            f"커버리지 Lv.{k['max_level_observed']} · 출처 {tag}")


def wage(band=None, k=None):
    """원 환산 환율(원/h). 구간 미지정이면 관측 최고 구간. Lv30+ 은 실측이 없다."""
    k = k or load()
    inc = k["income_by_band"]
    if band and band in inc:
        return inc[band], True
    return (inc[sorted(inc)[-1]] if inc else 0.0), False


if __name__ == "__main__":
    k = load()
    print(banner(k))
    print(f"구간 시급: " + " / ".join(f"{b} {v:,}" for b, v in k["income_by_band"].items()))
    h = k["harpoon"]
    print(f"작살: 포획 {h.get('catches_per_active_h')}/h · quality {h.get('quality_mean')} · "
          f"조준간격 {h.get('aim_gap_s')}s · 사이클 {h.get('cycle_s')}s · "
          f"스폰→포획 {h.get('spawn_to_catch_pct')}% · 조준표본 {h.get('aim_gap_n')}건")
    print(f"광질: 섬광산 {sum(k['island_mine_per_hour'].values()):,}/h · "
          f"드릴 {sum(k['drill_per_hour'].values()):,}/h")
    for w in k.get("warnings", []):
        print("  ! " + w)
