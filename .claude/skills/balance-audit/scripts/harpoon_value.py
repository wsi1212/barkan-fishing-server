#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harpoon_value.py — 창 전용 스탯 6종의 원/h 가치 모델 (사이클 + 등급천장).

★2026-08-26 신설. 이게 없어서 `item_ledger.py` 가 작살 55종 중 **37종을 판정 불가**로 제외하고
있었다. 공격형·호흡형 빌드는 스탯 대부분이 income 모델에 없어 0으로 계산되고, 그 상태로
«약하다»고 판정하면 오판이므로 검사에서 빼는 수밖에 없었다.

## 왜 이 스탯들은 «income 곱셈»이 아닌가

낚싯대 스탯은 대부분 «잡은 물고기의 값»을 올린다(판매보너스·크기·등급업). 창 전용 스탯은
그게 아니라 **사이클 시간**과 **잡을 수 있는 등급의 천장**을 움직인다. 특히 천장은 곱셈이 아니라
계단이다 — 공격력 1 짜리 나무 작살은 A 를 아무리 오래 찔러도 못 잡는다(제한시간 초과).

## 라이브 코드에서 그대로 가져온 규칙 (HarpoonManager / HarpoonListener)

    체력      HP(g, size) = base[g] + floor(max(0, size-100)/50)
              base = E1 D2 C3 B5 A8 S12 M18 L25 G35        (calcFishHp)
    찌르기피해 공격력 (spearAttack = max(1, stat + 특성 완력))
    ★돌진피해  공격력 × 2  (sweepAttack(..., max(1, getAttackPower(p)*2)) — 2026-08-26 발견)
              돌진 쿨타임 = max(20, round(200 / (1+돌진쿨감/100))) 틱 → 기본 10초
    필요타격   dash 로 먼저 깎고 남은 체력을 찌르기로: jabs = ceil((HP − dashes×2×atk) / atk)
    찌르기간격 gap = max(2, round(5 / (1+공격속도/100))) 틱   (jabGapTicks, JAB_GAP_TICKS=5)
    제한시간   W = max(20, round(base_w[g] × (1 + min(0.50, 도망감소/100)))) 틱
              base_w = E140 D140 C140 B130 A120 S120 M130 L160 G200   (escapeWindowBase)
              빗맞힘 1회당 −5틱, 누적 차감 상한 = base_w × 0.34       (ESCAPE_MISS_*)
    포획성립   타이머는 **첫 명중**에 시작하고 명중으로 갱신되지 않는다
              ⇒ jabs × 명중간격 ≤ W                         (2026-08-21 설계 주석)
    수중호흡   breathOf = max(stat, breathFloor[g]) 초        (등급이 바닥을 깐다)
    호흡시간   잠수 1회당 산소정지 N초 (등급 하한 없음, 물 밖으로 나오면 재충전)
    수영속도   WATER_MOVEMENT_EFFICIENCY attribute (물속 전용)

## ★돌진은 «이동»이 아니라 «2배 피해 공격»이다 (2026-08-26 검증에서 발견)

초안 모델은 돌진을 이동수단으로만 봤고, 그래서 «철 작살(공2)로 S(HP12) 포획» 을 불가로 판정했다.
실측은 5 명중으로 1 포획이었다 — 찌르기만으로는 6번이 필요하니 산수가 안 맞았다.
원인은 `HarpoonManager:1420` 의 `sweepAttack(..., max(1, getAttackPower(p) * 2))` 였다.
돌진이 **공격력 ×2** 로 때린다. 그래서 S = 돌진 4 + 찌르기 4×2 = 12 로 정확히 맞는다.
⇒ 돌진쿨감은 «이동 편의»가 아니라 **교전 DPS 스탯**이다. 쿨타임 200틱(10초)이 제한시간(6~7초)보다
길어서 기본은 교전당 1회지만, 돌진쿨감 43% 부터 창 하나에 2회가 들어간다(200/1.43 = 140틱 = 7초).

## ★모델의 핵심 발견 — 공격속도는 실전에서 값이 거의 0이다

`JAB_GAP_TICKS = 5` 는 **0.25초**다. 실측 «교전 내 연속 명중 간격»은 **중위 1.25초**(p25 1.04초,
n=193)다. 즉 병목은 쿨타임이 아니라 **조준**이고, 공격속도는 이미 아무도 못 채우는 0.25초를
더 줄인다. 실측이 그대로 보여준다 — 공격속도 18 인 강철 작살의 명중간격 중위가 1.55초로,
공격속도 0 인 나무 작살(1.00초)보다 **느리다**(표본은 작지만 방향이 반대다).
⇒ 이 모델은 명중간격을 `max(gap, 실측 조준간격)` 으로 둔다. 그래서 공격속도의 미분값이 0 으로
나오고, 그건 버그가 아니라 결론이다. 공격속도를 살리려면 JAB_GAP 을 실측 조준간격(25틱) 근처로
올려 실제로 병목이 되게 만들어야 한다.

## 사이클 모델 (실측 캘리브레이션)

    cycle = t_search + t_approach + t_engage + t_surface
      t_approach = A0 / (1 + 수영속도/100 × SWIM_EFF)     A0 = 실측 spawn→첫명중 2.64초
      t_engage   = (n − 1) × 명중간격
      t_surface  = R / max(1, 잠수당 포획수),  잠수당 포획수 = 유효잠수초 / cycle_dive
                   유효잠수초 = 수중호흡 + 호흡시간,  R = 실측 행동공백 9.7초
      t_search   = 잔차 — 기준 작살(철)에서 실측 사이클 17.3초가 재현되도록 캘리브레이션
    income/h   = (3600 / cycle) × Σ_g P(g) × price(g) × 포획가능(g)

★포획 불가 등급도 사이클을 **소모한다**(찌르다 도주). 그래서 공격력이 천장을 한 칸 올리면 그
등급의 값이 통째로 들어온다 — 계단형 가치의 출처다.

사용:
    python3 harpoon_value.py                 # 스탯별 가치 + 작살별 등급천장
    python3 harpoon_value.py --ceiling       # 등급천장 표만
    python3 harpoon_value.py --calibrate     # 실측 캘리브레이션 근거 출력
"""
import argparse, collections, importlib.util, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = saved
    return m


SV = _load("stat_value")
MEAS = _load("measured")     # ★실측 상수 단일 출처

# ── 라이브 코드 상수 (HarpoonManager / HarpoonListener) ────────────────────
HP_BASE = {"E": 1, "D": 2, "C": 3, "B": 5, "A": 8, "S": 12, "M": 18, "L": 25, "G": 35}
WIN_BASE = {"E": 140, "D": 140, "C": 140, "B": 130, "A": 120, "S": 120,
            "M": 130, "L": 160, "G": 200}          # 틱
JAB_GAP_TICKS = 5
DASH_COOLDOWN_TICKS = 200          # HarpoonManager.DASH_COOLDOWN_TICKS
DASH_DAMAGE_MULT = 2               # sweepAttack(..., getAttackPower*2) — 돌진은 2배 피해
ESCAPE_STAT_CAP = 0.50
ESCAPE_MISS_PENALTY = 5                            # 틱/빗맞힘
ESCAPE_MISS_CAP = 0.34                             # base_w 대비
BREATH_FLOOR = {"E": 5, "D": 8, "C": 10, "B": 13, "A": 15, "S": 18,
                "M": 20, "L": 22, "G": 25}         # 초
HARPOON_QUALITY_MIN, HARPOON_QUALITY_MAX = 70, 100  # HarpoonListener:236 균등

# ★실측 표본의 주력 작살 — 사이클 캘리브레이션 기준. (swing 2,226회)
BASELINE_HARPOON = "철 작살"
# 수영속도 %가 실제 이동시간에 얼마나 반영되는지 — WATER_MOVEMENT_EFFICIENCY 는 선형이 아니고
# 물살·수직이동이 섞여 있다. 실측 회귀를 못 했으므로 **절반만 인정**하고 그 사실을 표기한다.
SWIM_EFF = 0.5
# 잠수 1회 안에 몇 번 교전하나 — 유효잠수초 ÷ 교전당 수중시간. 교전당 수중시간은
# approach + engage 로 본다(탐색은 수면에서도 된다).
MIN_DIVES_PER_CATCH = 1.0


def load_measured():
    """measured.py 의 harpoon 절 + 공통 출처 표기."""
    k = MEAS.load()
    d = dict(k["harpoon"])
    d.setdefault("aim_gap_sample", [])
    d["baseline_harpoon"] = BASELINE_HARPOON
    d["_source"] = k["_source"] if not k["is_fallback"] else "FALLBACK"
    d["_k"] = k
    return d


def parse_stats(raw):
    out = {}
    for pair in raw.split(","):
        kv = pair.split(":", 2)
        if len(kv) < 2:
            continue
        try:
            out[kv[0].strip()] = float(kv[1].strip())
        except ValueError:
            pass
    return out


class Model:
    def __init__(self, parts_json=None, measured=None):
        bs = os.environ.get("BLOCKSHIP_DATA",
                            "/Users/user/Library/Application Support/feather/player-server/servers/"
                            "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
        P = json.load(open(parts_json or os.path.join(bs, "parts.json"), encoding="utf-8"))["parts"]
        self.spears = {}
        for name, line in P.get("작살", {}).items():
            f = line.split("|")
            self.spears[name] = dict(grade=f[1], price=int(f[2]), lvl=int(f[5]),
                                     src=f[6] if len(f) > 6 else "", stats=parse_stats(f[4]))
        self.m = measured or load_measured()
        # 미끼/부품에서 끌어오는 공용 스탯은 여기서 다루지 않는다(item_ledger 가 STAT_KEY 로 본다).
        self.qmult = SV.size_mult(self.m["quality_mean"])
        self._calibrate()

    # ── 규칙 ───────────────────────────────────────────────────────────
    def dash_cd_s(self, dashcut):
        return max(20, round(DASH_COOLDOWN_TICKS / (1.0 + max(0.0, dashcut) / 100.0))) / 20.0

    def hits_needed(self, grade, atk, size=0.0, dashcut=0.0, window_s=None):
        """(찌르기 횟수, 돌진 횟수) — 돌진이 공격력×2 로 먼저 깎는다.

        돌진은 교전 시작에 1회 쓸 수 있다고 본다(플레이어는 돌진으로 접근한다). 그 뒤
        제한시간 안에 쿨타임이 돌아오면 추가로 쓴다. 찌르기 시간만 타이머를 소모한다
        (돌진은 이동+타격이 한 틱이라 사실상 0초).
        """
        atk = max(1, atk)
        hp = HP_BASE.get(grade, 1) + (int(max(0.0, size - 100) / 50) if size else 0)
        w = window_s if window_s is not None else WIN_BASE.get(grade, 140) / 20.0
        cd = self.dash_cd_s(dashcut)
        dashes = 1 + int(w // cd) if cd > 0 else 1
        left = hp - dashes * DASH_DAMAGE_MULT * atk
        jabs = max(0, math.ceil(left / atk)) if left > 0 else 0
        return jabs, dashes

    def aim_gap(self, atkspd):
        """명중 간격(초) = max(코드 쿨타임, 실측 조준 간격). ★공격속도가 0 이 되는 이유가 여기다."""
        gap_s = max(2, round(JAB_GAP_TICKS / (1.0 + max(0.0, atkspd) / 100.0))) / 20.0
        return max(gap_s, self.m["aim_gap_s"])

    def window_s(self, grade, escape_relief, miss_penalty_frac=None):
        """교전 제한시간(초).

        ★빗맞힘 차감은 **기본 0** 이다. 초안은 실측 명중률 18%를 보고 상한(−34%)을 자동 적용했는데,
        prod 교전 로그가 그걸 반박했다 — 철 작살(공2)로 A(HP8, 4타격) 를 잡은 실제 교전이
        «+0.95 / +1.01 / +1.09» (3.05초)와 «+1.40 / +2.60 / +1.35» (5.35초)였고, 후자는 −34% 를
        적용한 3.96초를 넘는데도 성립했다. 즉 `harpoon.miss`(grade 빈칸 = 허공 스윙)는 교전
        타이머를 깎는 그 빗맞힘이 아니다. 상한을 자동 적용하면 모델이 실측 포획을 «불가»로
        판정하므로 기본을 0 으로 두고, 민감도가 필요하면 miss_penalty_frac 로 넣는다.
        """
        base = WIN_BASE.get(grade, 140)
        w = base * (1.0 + min(ESCAPE_STAT_CAP, max(0.0, escape_relief) / 100.0))
        if miss_penalty_frac:
            w -= base * min(ESCAPE_MISS_CAP, max(0.0, miss_penalty_frac))
        return max(20, w) / 20.0

    # ★이진 판정은 경계에서 실측과 어긋난다 — 철 작살(공2) × S 는 모델상 6.25s vs 제한 6.00s 로
    #   «불가»인데 실측은 10 명중 중 2 포획이었다. 조준간격은 분포(중위 1.30s · p25 1.04s)이고
    #   (n−1) 번의 합이 제한시간 안에 들어가면 성립하므로, 경험분포 몬테카를로로 **확률**을 낸다.
    #   중위값 단일 판정은 분포 표본이 없을 때의 폴백으로만 남긴다.
    P_THRESHOLD = 0.05          # 이 확률 미만이면 «사실상 불가»로 본다(표 출력용)
    _MC_N = 4000

    def p_catch(self, grade, st, size=0.0):
        """포획 성립 확률 = P( Σ_{i<jabs} gap_i ≤ 제한시간 )."""
        w = self.window_s(grade, st.get("도망감소", 0))
        jabs, dashes = self.hits_needed(grade, st.get("공격력", 0), size,
                                        st.get("돌진쿨감", 0), w)
        n = jabs + dashes
        if jabs <= 0:
            return 1.0, n, 0.0
        floor_gap = max(2, round(JAB_GAP_TICKS / (1.0 + max(0.0, st.get("공격속도", 0)) / 100.0))) / 20.0
        sample = self.m.get("aim_gap_sample") or []
        if not sample:
            en = jabs * self.aim_gap(st.get("공격속도", 0))
            return (1.0 if en <= w else 0.0), n, en
        # 결정론적 몬테카를로 — 난수 대신 표본을 순환 인덱스로 소비한다(감사 재현성이 규칙이다)
        L = len(sample)
        hit = 0
        for k in range(self._MC_N):
            tot = 0.0
            idx = k * 7919 % L      # 서로 소인 stride 로 표본을 흩는다
            for j in range(jabs):
                tot += max(floor_gap, sample[(idx + j * 2657) % L])
                if tot > w:
                    break
            if tot <= w:
                hit += 1
        p = hit / self._MC_N
        return p, n, jabs * self.aim_gap(st.get("공격속도", 0))

    def catchable(self, grade, st, size=0.0):
        """(사실상 가능한가, 필요타격, 중위 교전시간) — 확률이 P_THRESHOLD 이상이면 가능."""
        p, n, en = self.p_catch(grade, st, size)
        return p >= self.P_THRESHOLD, n, en

    # ── 사이클 ─────────────────────────────────────────────────────────
    def cycle(self, st, dist):
        """등급분포 가중 평균 사이클(초). t_search 는 캘리브레이션 잔차."""
        approach = self.m["approach_s"] / (1.0 + st.get("수영속도", 0) / 100.0 * SWIM_EFF)
        gap = self.aim_gap(st.get("공격속도", 0))
        engage = 0.0
        for g, p in dist.items():
            w = self.window_s(g, st.get("도망감소", 0))
            jabs, _ = self.hits_needed(g, st.get("공격력", 0), 0.0, st.get("돌진쿨감", 0), w)
            engage += p * jabs * gap
        dive = max(1e-6, st.get("수중호흡", 0) + st.get("호흡시간", 0))
        per_dive = max(MIN_DIVES_PER_CATCH, dive / max(1e-6, approach + engage))
        surface = self.m["surface_s"] / per_dive
        return self._search + approach + engage + surface, approach, engage, surface

    def _calibrate(self):
        """기준 작살에서 실측 사이클이 재현되도록 t_search 를 역산한다."""
        base = self.m.get("baseline_harpoon")
        st = dict(self.spears.get(base, {}).get("stats", {}))
        st.setdefault("공격력", 2)
        g = self.spears.get(base, {}).get("grade", "D")
        st["수중호흡"] = max(st.get("수중호흡", 0), BREATH_FLOOR.get(g, 5))
        dist = self.dist_for(self.spears.get(base, {}).get("lvl", 1))
        self._search = 0.0
        total, ap, en, su = self.cycle(st, dist)
        self._search = max(0.0, self.m["cycle_s"] - total)
        self._cal = dict(baseline=base, approach=ap, engage=en, surface=su,
                         search=self._search, target=self.m["cycle_s"])

    # ── 수입 ───────────────────────────────────────────────────────────
    def dist_for(self, lvl):
        stage = "초반" if lvl < 20 else ("중반" if lvl < 50 else "종결")
        pool, level = SV.STAGES[stage]
        return SV.grade_dist(pool, level)

    def income(self, st, dist):
        cyc = self.cycle(st, dist)[0]
        per_catch = 0.0
        for g, p in dist.items():
            pc, _, _ = self.p_catch(g, st)
            per_catch += p * pc * SV.PRICE[g] * self.qmult
        return 3600.0 / cyc * per_catch

    def stat_values(self, st, dist, deltas=None):
        """창 전용 스탯의 유한차분 원/h/단위."""
        base = self.income(st, dist)
        out = {}
        for k, d in (deltas or {"공격력": 1, "공격속도": 10, "수영속도": 10,
                                "수중호흡": 10, "호흡시간": 5, "도망감소": 5,
                                "돌진쿨감": 10}).items():
            s2 = dict(st)
            s2[k] = s2.get(k, 0) + d
            out[k] = ((self.income(s2, dist) - base) / d, d)
        return base, out

    def effective(self, name):
        """그 작살의 실효 스탯 — 수중호흡은 등급 하한을 적용한다."""
        sp = self.spears[name]
        st = dict(sp["stats"])
        st["수중호흡"] = max(st.get("수중호흡", 0), BREATH_FLOOR.get(sp["grade"], 5))
        st["공격력"] = max(1, st.get("공격력", 0))
        return st


def validate(M, cache=None):
    """모델의 «포획 가능» 예측을 prod 실측 (등급 × 작살) 포획 기록과 대조한다.

    ★이게 이 스크립트의 회귀 테스트다. 초안은 빗맞힘 상한(−34%)을 자동 적용해 A 등급을 «불가»로
    판정했는데, 실측은 철 작살로 A 를 10번 잡았다 — 그 불일치가 여기서 잡혀 모델을 고쳤다.
    """
    import sqlite3
    C = cache or os.path.join(SKILL, "audits", "telemetry-cache")
    if not os.path.isdir(C):
        print("  텔레메트리 캐시가 없다 — pull_players.py --fetch 를 먼저 돌릴 것")
        return 1
    OPS = {"wsi1212", "calan123", "all_ways_Incheon", "tnry0315"}
    hits, caught = collections.Counter(), collections.Counter()
    for f in sorted(os.listdir(C)):
        if not (f.startswith("events-") and f.endswith(".db")):
            continue
        c = sqlite3.connect(f"file:{os.path.join(C, f)}?mode=ro", uri=True)
        for t, n, x in c.execute("select type,name,ctx from ev where type in "
                                 "('harpoon.hit','harpoon.damage')"):
            if n in OPS:
                continue
            try:
                d = json.loads(x) if x else {}
            except Exception:
                continue
            if d.get("op", 0) == 1:
                continue
            g, h = d.get("grade") or "", d.get("harpoon") or ""
            if not g or not h:
                continue
            hits[(g, h)] += 1
            if d.get("caught"):
                caught[(g, h)] += 1
        c.close()
    if not hits:
        print("  실측 교전 기록이 없다")
        return 1
    print(f"{'등급':<3}{'작살':<12}{'공격력':>5}{'필요타격':>7}{'교전초':>7}{'제한초':>7}"
          f"{'P(포획)':>7}{'예측':>4}{'실측 명중':>9}{'실측 포획':>9}  판정")
    bad = 0
    for (g, h) in sorted(hits, key=lambda k: (-hits[k],)):
        if h not in M.spears:
            continue
        st = M.effective(h)
        pc, n, en = M.p_catch(g, st)
        ok = pc >= M.P_THRESHOLD
        w = M.window_s(g, st.get("도망감소", 0))
        obs = caught[(g, h)] > 0
        verdict = "일치" if ok == obs else ("★모델 불가·실측 포획" if obs else "★모델 가능·실측 0")
        bad += (ok != obs)
        print(f"{g:<3}{h:<12}{st['공격력']:>5.0f}{n:>7}{en:>7.2f}{w:>7.2f}"
              f"{pc:>7.2f}{('O' if ok else 'X'):>4}{hits[(g,h)]:>9}{caught[(g,h)]:>9}  {verdict}")
    print(f"\n{'🟢 전건 일치' if not bad else f'🔴 불일치 {bad}건 — 모델 전제를 다시 볼 것'}"
          f"  (표본이 0 인 조합은 검증되지 않았다: M·L·G 등급, 공격력 4 이상 작살)")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ceiling", action="store_true")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--validate", action="store_true",
                    help="모델 예측 vs prod 실측 포획 기록 대조 (회귀 테스트)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    M = Model()
    if a.validate:
        print(f"실측 출처: {M.m['_source']} · 조준간격 {M.m['aim_gap_s']}s")
        print("\n=== 모델 검증: 예측 «포획 가능» vs 실측 포획 기록 ===")
        sys.exit(1 if validate(M) else 0)
    print(f"실측 출처: {M.m['_source']}  ·  조준간격 {M.m['aim_gap_s']}s · 접근 {M.m['approach_s']}s · "
          f"사이클 {M.m['cycle_s']}s · 공백 {M.m['surface_s']}s · quality {M.m['quality_mean']}")

    if a.calibrate or not (a.ceiling or a.json):
        c = M._cal
        print(f"\n캘리브레이션 (기준 {c['baseline']}): 접근 {c['approach']:.2f} + 교전 {c['engage']:.2f}"
              f" + 수면 {c['surface']:.2f} + 탐색(잔차) {c['search']:.2f} = {c['target']:.2f}s")
        print(f"  ★찌르기 쿨타임 {JAB_GAP_TICKS/20:.2f}s vs 실측 조준간격 {M.m['aim_gap_s']:.2f}s "
              f"→ 병목은 조준. 공격속도의 미분값이 0 인 이유다.")
        print(f"  ★빗맞힘 차감은 기본 0 — 실측 교전 로그가 상한 적용을 반박했다(--validate 참조).")

    if a.ceiling or not a.json:
        print("\n=== 등급 천장 (포획 성립 = (필요타격−1)×조준간격 ≤ 제한시간) ===")
        print(f"{'등급':<3}{'HP':>3}{'제한시간':>8}  " +
              " ".join(f"{'공'+str(atk):>7}" for atk in (1, 2, 3, 4, 6, 8)))
        for g in "EDCBASMLG":
            row = []
            for atk in (1, 2, 3, 4, 6, 8):
                pc, n, en = M.p_catch(g, {"공격력": atk})
                row.append(f"{pc*100:>3.0f}%/{n}")
            print(f"{g:<3}{HP_BASE[g]:>3}{M.window_s(g,0):>7.2f}s  " + " ".join(f"{r:>7}" for r in row))
        print("  «P(포획)%/총타격수(돌진+찌르기)» · 조준간격 경험분포 몬테카를로 (도망감소·돌진쿨감 0)")
        print(f"  ★돌진 1회가 공격력×{DASH_DAMAGE_MULT} 로 먼저 깎는다 — 이걸 빼면 모델이 실측 포획을 «불가»로 오판한다.")
        print("  코드 주석의 설계 의도는 «나무=B · 철=S 아슬 · 강철=M · 다이아=전등급» 이고,")
        print("  그건 명중간격 0.9s 가정이다. 실측 1.25s 를 넣으면 한 칸씩 내려간다 — 실측 포획")
        print("  기록과 대조한 결과는 `--validate` 로 확인할 것.")

    if not a.ceiling or a.json:
        # 스탯 가치 — 구간별
        rows = {}
        for lvl, label in ((10, "초반(Lv10)"), (30, "중반(Lv30)"), (60, "종결(Lv60)")):
            dist = M.dist_for(lvl)
            # 대표 빌드 = 그 구간에서 실제로 들 만한 공격력
            atk = 2 if lvl < 20 else (3 if lvl < 50 else 6)
            st = {"공격력": atk, "공격속도": 0, "수영속도": 20, "수중호흡": 15,
                  "호흡시간": 0, "도망감소": 0, "돌진쿨감": 0}
            base, vals = M.stat_values(st, dist)
            rows[label] = (base, vals)
        if a.json:
            print(json.dumps({k: {"income": v[0], "stats": {kk: vv[0] for kk, vv in v[1].items()}}
                              for k, v in rows.items()}, ensure_ascii=False, indent=1))
            return
        print("\n=== 창 전용 스탯 가치 (원/h/단위, 유한차분) ===")
        print(f"{'구간':<12}{'기준 income':>13}  " +
              "".join(f"{k:>10}" for k in ("공격력", "공격속도", "수영속도", "수중호흡", "호흡시간", "도망감소", "돌진쿨감")))
        for label, (base, vals) in rows.items():
            print(f"{label:<12}{base:>13,.0f}  " +
                  "".join(f"{vals[k][0]:>10,.0f}" for k in
                          ("공격력", "공격속도", "수영속도", "수중호흡", "호흡시간", "도망감소", "돌진쿨감")))
        print("  ★공격력은 «등급 천장»을 넘는 순간 계단으로 뛴다 — 위 값은 그 구간 대표 빌드에서의")
        print("    국소 미분이라 천장 바로 아래에서는 훨씬 크고 천장 위에서는 0 에 가깝다.")
        print("  ★공격속도 0 = 모델 결론(쿨타임 0.25s ≪ 실측 조준간격 1.25s). 버그가 아니다.")
        print("  ★수영속도는 WATER_MOVEMENT_EFFICIENCY 의 비선형성 때문에 «%의 절반만» 인정했다"
              f"(SWIM_EFF={SWIM_EFF}) — 회귀 표본이 없다.")

        print("\n=== 작살별 등급 천장 · 사이클 · income (실효 스탯, 등급 하한 적용) ===")
        print(f"{'등급':<3}{'Lv':>4} {'이름':<18}{'공격력':>5}{'천장':>5}{'사이클s':>8}{'income/h':>11}"
              f"{'가격':>11}{'회수h':>8}  창 전용 스탯")
        order = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4, "S": 5, "G": 6}
        for name in sorted(M.spears, key=lambda n: (M.spears[n]["lvl"], n)):
            sp = M.spears[name]
            st = M.effective(name)
            dist = M.dist_for(sp["lvl"])
            ceil_g = "-"
            for g in "EDCBASMLG":
                if M.catchable(g, st)[0]:
                    ceil_g = g
            cyc = M.cycle(st, dist)[0]
            inc = M.income(st, dist)
            pb = sp["price"] / inc if inc > 0 else float("inf")
            so = ",".join(f"{k}{int(v)}" for k, v in sp["stats"].items()
                          if k in ("공격력", "공격속도", "수영속도", "수중호흡", "호흡시간",
                                   "야간투시", "돌진쿨감"))
            print(f"{sp['grade']:<3}{sp['lvl']:>4} {name:<18}{st['공격력']:>5.0f}{ceil_g:>5}"
                  f"{cyc:>8.2f}{inc:>11,.0f}{sp['price']:>11,}"
                  f"{('∞' if pb==float('inf') else f'{pb:.2f}'):>8}  {so}")


if __name__ == "__main__":
    main()
