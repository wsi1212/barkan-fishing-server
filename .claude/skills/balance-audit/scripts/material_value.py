#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
material_value.py — 재료 1개의 «진짜» 가치를 LP 그림자가격으로 산출한다.

★2026-08-26 신설. 그 전까지 재료 가치는 두 방식으로 재고 있었고 둘 다 구조적으로 틀렸다:
  ① cross-economy-values.md §5·§6 표 — 손으로 옮겨 적은 «원/개». 확률 오기·단위 혼동이 4개월 갔다.
  ② material_gate.py — «지역 안에서는 동시(max), 지역 간에는 순차(sum)» 휴리스틱. 방향은 맞지만
     세 가지를 놓친다:
       (a) 같은 재료가 여러 지역에서 나온다(진주·별빛진주는 **16개 지역 전부**, 물고기비늘 10곳).
           그래서 «협곡 전용 병목» 같은 판정이 성립하지 않는데도 그렇게 판정했다.
       (b) 광질·바닐라 재료를 **비용 0으로 버린다**. 장비 레시피에서 가장 많이 쓰이는 중간재가
           강철심(175회)·압축흑정석(163회)·강화철괴(91회)인데 셋 다 광질 산출이다.
       (c) 재료는 **결합생산물**이다 — 한 번의 포획이 그 지역 드롭테이블 전체를 독립적으로 굴린다
           (CraftingManager.rollMaterials: 테이블을 순회하며 각각 nextDouble 판정). 즉 «강에서
           녹슨부품을 캐는 시간»에 물고기비늘·진주·별빛진주가 공짜로 같이 쌓인다. 재료마다
           시간을 따로 더하면 같은 시간을 여러 번 세게 된다.

## 이 스크립트의 모델

**1차 단위는 «시간(h)»이고 «원»은 파생이다.** (구 표들이 원과 h를 섞어 쓰다 단위 오류를 냈다.)

활동 A(지역별 낚시 / 섬광산 / 드릴)마다 시간당 산출 벡터 r[A][m] 이 있다.
낚시 지역이면 r = 포획/h × chance/100 (드롭테이블 전체가 매 포획마다 독립 판정되므로 그대로 곱).
광질이면 r = 실측 시간당 산출 개수.

요구 수량 q(레시피 BOM)를 채우는 최소 시간:

    min  Σ_A h_A        s.t.  Σ_A h_A · r[A][m] ≥ q[m] ∀m,   h ≥ 0

이 LP 의 쌍대변수 λ[m] 이 **재료 1개의 시간가격(h/개)** 이다. 성질이 셋 있고 셋 다 설계에 필요하다:
  · 여러 지역에서 나는 재료는 «가장 싸게 겸사겸사 얻어지는 경로»로 자동 평가된다(수동 판단 불필요).
  · 병목이 아닌 재료의 λ 는 **0** 이다 — 결합생산 공짜분을 이중계상하지 않는다.
  · Σ λ[m]·q[m] = 총 게이트 시간. 즉 항목별 가격을 더하면 정확히 전체와 맞는다(구 표는 안 맞았다).

같은 재료의 «단독 시간가»(그 재료만 필요할 때의 h/개)도 함께 낸다 — 상한이고, 병목 후보 판정용.

원 환산은 마지막에 딱 한 번, 그 구간의 실측 시급을 곱해서 한다. 실측 시급은
pull_players.py 스냅샷의 income_by_band 에서 온다(가정 상수 금지).

사용:
    python3 material_value.py                  # 재료별 가격표 + 활동별 산출
    python3 material_value.py --demand-set A   # A 등급 풀세팅 BOM 의 LP 해 + 병목
    python3 material_value.py --json           # 다른 스크립트(item_ledger)용 출력
"""
import argparse, collections, importlib.util, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
BS = os.environ.get("BLOCKSHIP_DATA",
                    "/Users/user/Library/Application Support/feather/player-server/servers/"
                    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")

# ── 실측 상수는 measured.py 단일 출처 (2026-08-26) ─────────────────────────
def _load_mod(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    sv, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = sv
    return m


MEAS = _load_mod("measured")
# 섬광산 ore 이름 → 레시피가 쓰는 바닐라 item id
ORE_TO_ITEM = {"철": "iron ingot", "석탄": "coal", "청금석": "lapis lazuli",
               "구리": "copper ingot", "금": "gold ingot", "다이아몬드": "diamond",
               "에메랄드": "emerald", "네더라이트": "netherite scrap", "돌": "stone"}
# 드릴 산출은 커스텀 재료 id 그대로 쓴다(흑정석/철광석/자수정).
# ★자수정은 T3 전용이고 실측 표본이 0이다 — 관측되지 않은 활동으로 따로 표기한다.
DRILL_UNOBSERVED = {"자수정": 340.0}   # 철광석(T2) 실측을 T3 대리값으로 씀. 반드시 «추정» 표기.


# ══════════════════════════════════════════════════════════════════════════
#  소형 LP — max c'x s.t. Ax ≤ b (b ≥ 0), x ≥ 0.  표준 심플렉스 + Bland 규칙.
#  (numpy/scipy 없이 돌아야 한다 — 이 스킬은 의존성 0이 규칙이다.)
# ══════════════════════════════════════════════════════════════════════════
def simplex_max(c, A, b, eps=1e-11, max_iter=20000):
    """max c'x, Ax ≤ b, x ≥ 0. 반환 (opt, x, y) — y 는 제약의 쌍대가격."""
    m, n = len(A), len(c)
    # 태블로: [A | I | b] 마지막 행 = -c
    T = [list(A[i]) + [1.0 if j == i else 0.0 for j in range(m)] + [float(b[i])]
         for i in range(m)]
    T.append([-float(v) for v in c] + [0.0] * m + [0.0])
    basis = [n + i for i in range(m)]
    for _ in range(max_iter):
        # Bland: 음수 계수 중 가장 작은 인덱스 (순환 방지)
        piv_c = -1
        for j in range(n + m):
            if T[-1][j] < -eps:
                piv_c = j
                break
        if piv_c < 0:
            break
        piv_r, best = -1, None
        for i in range(m):
            if T[i][piv_c] > eps:
                ratio = T[i][-1] / T[i][piv_c]
                if best is None or ratio < best - eps or \
                   (abs(ratio - best) <= eps and basis[i] < basis[piv_r]):
                    best, piv_r = ratio, i
        if piv_r < 0:
            raise ValueError("LP 무계 (unbounded) — 산출 벡터에 0 행이 있는지 확인")
        pv = T[piv_r][piv_c]
        T[piv_r] = [v / pv for v in T[piv_r]]
        for i in range(m + 1):
            if i != piv_r and abs(T[i][piv_c]) > eps:
                f = T[i][piv_c]
                T[i] = [a - f * bb for a, bb in zip(T[i], T[piv_r])]
        basis[piv_r] = piv_c
    else:
        raise ValueError("LP 반복 한계 초과")
    x = [0.0] * n
    for i, bi in enumerate(basis):
        if bi < n:
            x[bi] = T[i][-1]
    y = [T[-1][n + i] for i in range(m)]      # 쌍대가격 (슬랙 열의 목적행)
    return T[-1][-1], x, y


# ══════════════════════════════════════════════════════════════════════════
#  데이터
# ══════════════════════════════════════════════════════════════════════════
#: 통발 재료 굴림 — TrapManager.giveTrapMaterials 와 짝이다. 한쪽만 바꾸면 모델이 틀린다.
#  굴림수 = round(대기초/120)(분당 0.5), 회수/h = 3600/대기초 → 곱하면 대기가 약분돼 30/h.
TRAP_ROLLS_PER_HOUR = 30.0
#: 통발 굴림의 확률 배수 (TrapManager.TRAP_MAT_CHANCE_PCT = 200 → ×3).
TRAP_CHANCE_MULT = 3.0
#: 통발이 설치 가능한 지역 — 권위는 TrapSpecs.java 다(하드코딩하면 드리프트한다).
_TRAP_SRC = os.path.expanduser(
    "~/development/blockship-plugin/src/main/java/com/blockship/trap/TrapSpecs.java")


def trap_regions():
    """TrapSpecs.java 에서 통발 지역 집합을 읽는다. 파일이 없으면 빈 집합(통발 없음)."""
    try:
        src = open(_TRAP_SRC, encoding="utf-8").read()
    except OSError:
        return set()
    return set(re.findall(r'put\(new Spec\("([^"]+)"', src))


def load_snapshot(path=None):
    return MEAS.load(path)


class Data:
    def __init__(self, bs=BS, snap=None):
        self.mat = json.load(open(os.path.join(bs, "materials.json"), encoding="utf-8"))
        self.rec = json.load(open(os.path.join(bs, "recipes.json"), encoding="utf-8"))["recipes"]
        self.parts = json.load(open(os.path.join(bs, "parts.json"), encoding="utf-8"))["parts"]
        self.k = load_snapshot(snap)

        # 낚시 드롭으로 얻는 base 재료
        self.fish_base = set()
        for t in list(self.mat["dropTables"].values()) + list(self.mat["weatherDrops"].values()):
            self.fish_base |= {d["matId"] for d in t}

        # matId → 그 재료를 만드는 direct 레시피 (중간재 전개용)
        self.matrec = {}
        for v in self.rec.values():
            if v["resultMode"] != "direct":
                continue
            for l in (v.get("result", {}) or {}).get("lore", []) or []:
                if l.startswith("&8mat:"):
                    self.matrec[l[6:]] = v

        # 부품 이름 → 스펙, 부품 이름 → 레시피
        self.meta = {}
        for cat, items in self.parts.items():
            for name, line in items.items():
                f = line.split("|")
                self.meta[name] = dict(cat=cat, grade=f[1], price=int(f[2]), dur=int(f[3]),
                                       stats=f[4], lvl=int(f[5]),
                                       src=f[6] if len(f) > 6 else "")
        self.recby = {}
        for v in self.rec.values():
            n = (v.get("rodPartName") if v["resultMode"] == "rod"
                 else v.get("resultPartName") if v["resultMode"] == "part" else None)
            if n:
                self.recby[n] = v

        self._build_activities()

    # ── 활동별 시간당 산출 ─────────────────────────────────────────────
    def _build_activities(self):
        ch = self.k["catches_per_active_h"]
        self.act = {}       # 활동명 → {재료: 개/h}
        self.act_note = {}
        trap = trap_regions()
        for area, tbl in self.mat["dropTables"].items():
            # ★통발이 있는 지역은 낚시와 «동시에» 재료가 나온다(2026-08-28). 통발은 낚시하는
            #   자리 바로 옆에 설치하고 그 옆에서 낚시하므로 회수 비용이 사실상 0 이고,
            #   따라서 별도 활동이 아니라 **그 지역 낚시의 산출 증가**로 모델링한다.
            #   시간당 굴림수 = (대기초/120) × (3600/대기초) = 30 — 대기가 약분돼 티어 무관 상수다.
            #   확률은 ×3 이므로 기여 = 30×3 / 190.1 ≈ 47%.
            rate = ch + (TRAP_ROLLS_PER_HOUR * TRAP_CHANCE_MULT if area in trap else 0.0)
            self.act["낚시:" + area] = {d["matId"]: rate * d["chance"] / 100.0 for d in tbl}
        for w, tbl in self.mat["weatherDrops"].items():
            # 날씨는 «선택 가능한 활동»이 아니다(발생 빈도에 종속) — 별도 표시하고 LP 에는
            # 넣지 않는다. 넣으면 「유성우 때 잡으면 된다」는 비현실적 해가 나온다.
            self.act_note["날씨:" + w] = {d["matId"]: ch * d["chance"] / 100.0 for d in tbl}
        im = {ORE_TO_ITEM.get(k, k): v for k, v in self.k["island_mine_per_hour"].items()}
        self.act["광질:섬광산"] = im
        self.act["광질:드릴"] = dict(self.k["drill_per_hour"])
        self.act["광질:드릴T3(추정)"] = dict(DRILL_UNOBSERVED)

    # ── BOM 전개 ───────────────────────────────────────────────────────
    def expand(self, ingredients, mult=1.0):
        """레시피 재료 목록을 base(낚시드롭 / 광석 / 바닐라 아이템 / 미해결)까지 전개.
        반환 Counter{(종류, id): 수량}. 종류: fish / ore / vanilla / orphan / cycle"""
        out = collections.Counter()
        for i in ingredients:
            q = i["qty"] * mult
            if i["kind"] == "custom":
                self._exp(i["typeOrMatId"], q, out, 0, ())
            else:
                out[("vanilla", i["typeOrMatId"])] += q
        return out

    def _exp(self, mid, q, out, dep, path):
        if dep > 12 or mid in path:
            out[("cycle", mid)] += q
            return
        if mid in self.fish_base:
            out[("fish", mid)] += q
            return
        r = self.matrec.get(mid)
        if r is None:
            kind = "ore" if any(mid in a for a in self.act.values()) else "orphan"
            out[(kind, mid)] += q
            return
        for i in r["ingredients"]:
            if i["kind"] == "custom":
                self._exp(i["typeOrMatId"], i["qty"] * q, out, dep + 1, path + (mid,))
            else:
                out[("vanilla", i["typeOrMatId"])] += i["qty"] * q

    # ── LP ─────────────────────────────────────────────────────────────
    def reachable_acts(self, level=None):
        """그 레벨에서 «실제로 갈 수 있는» 활동만 남긴다.

        ★2026-09-01 신설. 이걸 안 하면 LP 가 재료 단가를 전 지역 최적 출처로 매긴다 —
          Lv7 아이템의 진주를 오아시스(10%, Lv12 해금) 가격으로 계산해서 초반 장비 원가를
          2~3배 과소평가했다. 그 위에서 요구 수량을 정한 cast_cost 가 「정상」이라고
          판정했고, 실측으로는 D급 낚싯대 하나가 1.8~3.4h 였다(유저 제보).
          지역 해금 레벨의 권위는 region_unlock.py (메인 체인에서 도출).
        ★level=None 이면 구 동작(전 활동) — 전역 가격표·상위 아이템 분석용.
        """
        if level is None:
            return self.act
        RU = _load_mod("region_unlock")
        out = {}
        for name, r in self.act.items():
            if name.startswith("낚시:"):
                if not RU.reachable(name.split(":", 1)[1], level):
                    continue
            out[name] = r
        return out

    def gate(self, base, level=None):
        """base(expand 결과) → (총시간h, {재료: 시간가 h/개}, {활동: 시간h}, 미해결목록)"""
        demand = collections.Counter()
        unresolved = []
        for (kind, mid), q in base.items():
            if kind in ("fish", "ore"):
                demand[mid] += q
            elif kind == "vanilla":
                demand[mid] += q
            else:
                unresolved.append((kind, mid, q))
        # 어느 활동에서도 안 나오는 요구는 LP 에서 제외하되 반드시 보고한다
        acts_pool = self.reachable_acts(level)
        # ★레벨 필터로 «공급원이 통째로 사라진» 재료는 LP 에서 빠지고 — 그러면 그 재료가
        #   «공짜»가 된다(2026-09-01 실측: 깃털찌조각 등 때문에 25종이 목표 대비 ±15% 초과).
        #   도달 불가는 「싸다」가 아니라 「나중에 가야 한다」다. 그래서 그 재료를 공급하는
        #   활동을 «가장 싼 것 하나만» 되돌려 넣는다 — 원가는 정직해지고, 「그 레벨에 못 간다」
        #   는 사실은 ops/audit-material-reachability.py 가 따로 보고한다.
        want = {m for (kind, m), q in base.items() if kind in ("fish", "ore", "vanilla")}
        have = set()
        for a in acts_pool.values():
            have |= {m for m, r in a.items() if r > 0}
        for m in want - have:
            best, bname = 0.0, None
            for aname, r in self.act.items():
                if r.get(m, 0) > best:
                    best, bname = r[m], aname
            if bname:
                acts_pool = dict(acts_pool)
                acts_pool[bname] = self.act[bname]
        supplied = set()
        for a in acts_pool.values():
            supplied |= set(a)
        for mid in list(demand):
            if mid not in supplied:
                unresolved.append(("no-source", mid, demand.pop(mid)))
        if not demand:
            return 0.0, {}, {}, unresolved
        mats = sorted(demand)
        acts = [a for a in acts_pool if any(acts_pool[a].get(m, 0) > 0 for m in mats)]
        # 쌍대: max Σ q λ  s.t.  Σ_m r[A][m] λ_m ≤ 1 ∀A ; λ ≥ 0
        c = [demand[m] for m in mats]
        A = [[acts_pool[a].get(m, 0.0) for m in mats] for a in acts]
        b = [1.0] * len(acts)
        opt, lam, h = simplex_max(c, A, b)
        return (opt,
                {m: lam[i] for i, m in enumerate(mats) if lam[i] > 1e-12},
                {acts[i]: h[i] for i in range(len(acts)) if h[i] > 1e-9},
                unresolved)

    def solo_hours(self, mid):
        """그 재료만 필요할 때의 단독 시간가(h/개) = 1 / (최고 산출 활동의 개/h)."""
        best = 0.0
        for a, r in self.act.items():
            best = max(best, r.get(mid, 0.0))
        return (1.0 / best) if best > 0 else float("inf")

    def wage(self, band=None, stage=None):
        """원 환산 환율(원/h).

        ★2026-08-27 결함 수정. 구 동작은 «구간 미지정이면 관측 최고 구간(115,083)»이었고,
          그래서 A/S 세트의 «돈 게이트»를 종결 시급이 아니라 Lv20-29 시급으로 나눴다.
          A 세트 3,982,600원 ÷ 115,083 = 34.6h (실제 종결 시급 327,043 이면 12.2h) →
          「A·S 는 돈이 관문」 판정이 이 한 줄에서 나왔고, 종결 시급을 쓰면 뒤집힌다
          (재료 13.74h > 돈 12.18h). item_ledger 는 같은 상황에서 종결 모델값을 써서
          두 스크립트가 서로 다른 시급을 쓰고 있었다 — selftest §3 이 포획/h·크기점수만
          대조하고 시급은 안 봐서 못 잡았다.
          이제 stage 를 받으면 그 구간의 모델 시급으로 외삽하고, 외삽임을 호출부에 알린다.
        """
        w, measured = MEAS.wage(band, self.k)
        if measured or stage is None:
            return w
        return self.stage_wage(stage)

    _stage_wage_cache = None

    def stage_wage(self, stage):
        """실측이 없는 구간(Lv30+)의 모델 시급. stat_value 의 구간 수입을 그대로 쓴다."""
        if Data._stage_wage_cache is None:
            SV = _load_mod("stat_value")
            MEAS.apply(SV, self.k)
            Data._stage_wage_cache = {st: SV.compute(st)["income"] for st in SV.STAGES}
        return Data._stage_wage_cache.get(stage, self.wage())


# ══════════════════════════════════════════════════════════════════════════
def full_set_bom(D, grade, slots=("릴", "줄", "바늘", "찌")):
    """등급별 «풀세팅» BOM — 각 카테고리 가격 중앙값 아이템(히든/캐시/잠수상점 제외)."""
    import statistics as st

    def pick(cat, g, allow_hidden=False):
        c = [(n, m) for n, m in D.meta.items()
             if m["cat"] == cat and m["grade"] == g and m["price"] > 0 and n in D.recby
             and (allow_hidden or "히든" not in m["src"])
             and m["src"] not in ("캐시", "개발자", "잠수상점")]
        if not c:
            return None if allow_hidden else pick(cat, g, True)
        med = st.median([m["price"] for _, m in c])
        return min(c, key=lambda x: abs(x[1]["price"] - med))[0]

    pg = "A" if grade == "S" else grade      # 부품엔 S 등급이 없다
    names = [pick("낚싯대", grade)] + [pick(c, pg) for c in slots]
    if any(n is None for n in names):
        return None, None, 0
    bom = collections.Counter()
    price = 0
    for n in names:
        for k, v in D.expand(D.recby[n]["ingredients"]).items():
            bom[k] += v
        price += D.meta[n]["price"]
    return names, bom, price


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=None)
    ap.add_argument("--band", default=None, help="원 환산에 쓸 실측 구간 (예 Lv20-29)")
    ap.add_argument("--demand-set", default=None, help="풀세팅 등급 (D/C/B/A/S)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verify", action="store_true",
                    help="LP 자체 검산 (쌍대정리 Σλq==총게이트 + 원문제 실현가능성)")
    a = ap.parse_args()

    D = Data(snap=a.snapshot)
    W = D.wage(a.band)

    if a.verify:
        # ★심플렉스를 손으로 구현했으니 검산도 코드로 남긴다. 셋 다 통과해야 λ 를 믿을 수 있다:
        #   ① 강한 쌍대성: Σ λ[m]·q[m] == 총 게이트  ② 원문제 배분합 == 총 게이트
        #   ③ 그 배분으로 모든 수요가 실제로 충족됨(실현가능)
        bad = 0
        for g in ["D", "C", "B", "A", "S"]:
            names, bom, price = full_set_bom(D, g)
            if not names:
                continue
            h, lam, hact, _ = D.gate(bom)
            dem = collections.Counter()
            for (k, m), q in bom.items():
                if k in ("fish", "ore", "vanilla"):
                    dem[m] += q
            s = sum(lam.get(m, 0) * q for m, q in dem.items())
            feas = all(sum(hh * D.act[ac].get(m, 0) for ac, hh in hact.items()) >= q - 1e-6
                       for m, q in dem.items())
            ok = abs(h - s) < 1e-6 and abs(sum(hact.values()) - h) < 1e-6 and feas
            bad += (not ok)
            print(f"  {g}: 게이트 {h:.4f}h · Σλq {s:.4f}h · 배분합 {sum(hact.values()):.4f}h · "
                  f"실현가능 {feas} → {'OK' if ok else '✗ 실패'}")
        print("🟢 LP 검산 통과" if not bad else f"🔴 {bad}건 실패 — simplex_max 를 의심할 것")
        return

    if a.json:
        out = {"constants": D.k, "wage": W,
               "activities": D.act,
               "solo_hours": {m: D.solo_hours(m) for m in
                              sorted({x for r in D.act.values() for x in r})}}
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return

    print(MEAS.banner(D.k))
    print(f"  원 환산 환율 {W:,.0f}원/h" + (f" ({a.band})" if a.band else " (관측 최고 구간)")
          + f"  ★Lv.{D.k['max_level_observed']} 초과 구간의 결론은 외삽이다.")

    print("\n=== 활동별 시간당 산출 (LP 공급행렬) ===")
    for name, r in D.act.items():
        mix = D.k.get("region_mix_pct", {}).get(name.split(":", 1)[-1])
        tag = f"  [실측 조업비중 {mix:.1f}%]" if mix is not None else ""
        print(f"  {name:<20} " + ", ".join(f"{k} {v:,.1f}" for k, v in
                                          sorted(r.items(), key=lambda kv: -kv[1])[:6]) + tag)
    for name, r in D.act_note.items():
        print(f"  {name:<20} (LP 제외 — 발생빈도 종속) " +
              ", ".join(f"{k} {v:,.1f}" for k, v in r.items()))

    print("\n=== 재료별 단독 시간가 (그 재료만 필요할 때) ===")
    print(f"{'재료':<16}{'출처활동':<20}{'개/h':>9}{'h/개':>10}{'원/개':>11}")
    allm = sorted({x for r in D.act.values() for x in r},
                  key=lambda m: -D.solo_hours(m))
    for m in allm:
        h = D.solo_hours(m)
        src = max(D.act.items(), key=lambda kv: kv[1].get(m, 0))
        print(f"{m:<16}{src[0]:<20}{src[1].get(m,0):>9,.1f}{h:>10.4f}{h*W:>11,.0f}")

    print("\n=== 결합생산 LP — 등급별 풀세팅 ===")
    print("  ★λ(그림자가격)이 0 인 재료는 «다른 재료를 캐는 동안 공짜로 쌓이는» 것이다.")
    for g in (["D", "C", "B", "A", "S"] if not a.demand_set else [a.demand_set]):
        names, bom, price = full_set_bom(D, g)
        if not names:
            continue
        h, lam, hact, unres = D.gate(bom)
        # ★등급이 쓰이는 구간의 시급으로 나눈다 — 관측 최고 구간으로 일괄 나누면 A/S 의
        #   돈 게이트가 3배 부풀어 「돈이 관문」으로 뒤집힌다(2026-08-27 수정).
        stage_of_grade = {"D": "초반", "C": "초반", "B": "중반", "A": "종결", "S": "종결"}[g]
        Wg = D.wage(None, stage_of_grade) if stage_of_grade == "종결" else W
        ext = "~" if stage_of_grade == "종결" else ""
        print(f"\n  [{g}] {' + '.join(names)}")
        print(f"      가격합 {price:,}원 (= {price/Wg:.2f}h 노동{ext}, 시급 {Wg:,.0f})  ·  "
              f"재료 게이트 {h:.2f}h  → 관문: {'재료' if h > price/Wg else '돈'}")
        print(f"      활동배분: " + ", ".join(f"{k} {v:.2f}h" for k, v in
                                          sorted(hact.items(), key=lambda kv: -kv[1])))
        binding = sorted(lam.items(), key=lambda kv: -kv[1] * bom_qty(bom, kv[0]))
        print(f"      병목(λ>0): " + ", ".join(
            f"{m}×{bom_qty(bom,m):g} λ={v:.4f}h/개={v*W:,.0f}원 (총 {v*bom_qty(bom,m):.2f}h)"
            for m, v in binding[:5]))
        free = [m for (k, m) in bom if k in ("fish", "ore", "vanilla") and m not in lam]
        if free:
            print(f"      공짜(λ=0, 겸사겸사 확보): " + ", ".join(sorted(set(free))[:12]))
        if unres:
            print(f"      ★미해결(가격 못 냄): " + ", ".join(f"{m}×{q:g}[{k}]" for k, m, q in unres))


def bom_qty(bom, mid):
    return sum(q for (k, m), q in bom.items() if m == mid)


if __name__ == "__main__":
    main()
