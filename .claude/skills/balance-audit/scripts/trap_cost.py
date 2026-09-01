#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trap_cost.py — 통발 «산출 ↔ 재료비» 단일 권위 (2026-09-01 신설).

낚싯대·부품은 `cast_cost.py` 가 요구 캐스트를 정하지만 통발은 그 격자 밖이다.
통발은 장착물이 아니라 **소모성 설비**이고, 산출이 원/h 가 아니라 «회수 1회당»으로 난다.

    회수 1회 산출 = 물고기(1.3마리 × 등급가중 × 품질 0.675) + 재료(드랍표 ×3 × round(waitSec/120) 굴림)
    통발 1개 총산출 = 회수 1회 산출 × maxDur
    재료비            = 레시피 LP 시간(h) × 그 지역 해금레벨 구간의 시급
    τ (비용률)        = 재료비 ÷ 총산출        ← 이 값의 사다리를 설계한다

## 왜 τ 인가
통발은 «몇 캐스트»로 재면 안 된다 — 담가 두는 동안 플레이어는 낚시를 하므로 대기시간이
노동시간이 아니다. 비용도 산출도 «통발 1개» 단위로 닫혀 있어서 비율이 자연 단위다.

## 규약
- 재료 λ 는 `material_value.py` 의 LP 쌍대가격. 손으로 원/개 표를 적지 말 것(제8원칙).
- 지역 해금 레벨은 `region_unlock.py` (메인 퀘스트 체인에서 도출).
- **바닐라 재료는 no-source 로 잡힌다** — 어느 활동에서도 안 나오면 LP 가 제외하고 보고한다.
  그게 이 스크립트를 만든 계기다(프리즈머린·마그마크림·끈은 파는 데도 나오는 데도 없었다).

사용:
    python3 trap_cost.py            # 현행 진단
    python3 trap_cost.py --design   # 신설 레시피 제안(τ 사다리 적합)
"""
import collections, importlib.util, json, math, os, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
BS = pathlib.Path(os.environ.get("BLOCKSHIP_DATA",
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip"))
TRAPSPECS = pathlib.Path(os.path.expanduser(
    "~/development/blockship-plugin/src/main/java/com/blockship/trap/TrapSpecs.java"))


def _mod(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sv, sys.argv = sys.argv, [name]
    spec.loader.exec_module(m)
    sys.argv = sv
    return m


MV = _mod("material_value")
RU = _mod("region_unlock")
MEAS = _mod("measured")

def rolls_for(waitSec):
    """TrapManager.giveTrapMaterials 와 같은 반올림 — ★Java Math.round 는 «half up» 이다.
    파이썬 round 는 half-to-even 이라 540/120=4.5 에서 4 를 주고 Java 는 5 를 준다."""
    return max(1, int(math.floor(waitSec / ROLL_SECONDS + 0.5)))


#: TrapManager 와 짝인 상수 — 한쪽만 바꾸면 모델이 틀린다.
TRAP_CHANCE_MULT = 3.0          # TRAP_MAT_CHANCE_PCT = 200 → ×3
ROLL_SECONDS = 120.0            # rolls = round(waitSec / 120)
FISH_COUNT = 1.3                # 70% 1마리 / 30% 2마리
QUALITY_MULT = 0.675            # 균등 10~60 → 평균 35 → 0.5 + 35×0.5/100
GRADE_BASE = {"E": 100, "D": 250, "C": 600, "B": 2000, "A": 6000,
              "S": 20000, "M": 65000, "L": 170000, "G": 450000}
GRADE_WEIGHT = {"E": 100, "D": 80, "C": 55, "B": 32, "A": 16,
                "S": 8, "M": 4, "L": 2, "G": 1}


# ── TrapSpecs.java 파싱 ────────────────────────────────────────────────
SPEC_RE = re.compile(
    r'put\(new Spec\("([^"]+)",\s*"([^"]+)",\s*"([^"]+)",\s*(\d+),\s*(\d+),\s*"([^"]+)",\s*(\d+),'
    r'(.*?)\)\);', re.S)
ING_RE = re.compile(r'\bing\("([^"]+)",\s*"([^"]+)",\s*(\d+)\)')
MAT_RE = re.compile(r'\bmat\("([^"]+)",\s*"([^"]+)",\s*"([^"]+)",\s*(\d+)\)')


def load_specs():
    src = TRAPSPECS.read_text(encoding="utf-8")
    out = []
    for m in SPEC_RE.finditer(src):
        region, label, name, dur, wait, rid, price, tail = m.groups()
        ings = [{"kind": "item", "typeOrMatId": a, "displayName": b, "qty": int(q)}
                for a, b, q in ING_RE.findall(tail)]
        ings += [{"kind": "custom", "typeOrMatId": a, "displayName": c, "qty": int(q)}
                 for a, _mc, c, q in MAT_RE.findall(tail)]
        out.append(dict(region=region, label=label, name=re.sub(r"&.", "", name),
                        maxDur=int(dur), waitSec=int(wait), recipeId=rid,
                        unlockPrice=int(price), ingredients=ings))
    return out


# ── 산출 ───────────────────────────────────────────────────────────────
def fish_value(D, region):
    """회수 1회 물고기 기대 판매가(원). fish.json 의 그 지역 «통발» 풀 + gradeWeight 추첨."""
    fish = json.load(open(BS / "fish.json", encoding="utf-8"))
    regions = fish.get("regions", fish)
    pool = (regions.get(region) or {}).get("통발") or []
    defs = fish.get("fish", {})
    if not pool:
        return 0.0, 0, []
    tot = 0.0
    wsum = 0.0
    for n in pool:
        d = defs.get(n) or {}
        g = (d.get("grade") or "E").split("~")[0]
        w = GRADE_WEIGHT.get(g, 50)
        wsum += w
        tot += w * GRADE_BASE.get(g, 0)
    return (tot / wsum) * QUALITY_MULT * FISH_COUNT, len(pool), pool


def output_bundle(D, region, waitSec, maxDur):
    """통발 1개가 평생 뱉는 재료 다발 {matId: 개수}."""
    mats = json.load(open(BS / "materials.json", encoding="utf-8"))
    table = mats["dropTables"].get(region) or []
    rolls = rolls_for(waitSec)
    return {d["matId"]: maxDur * rolls * TRAP_CHANCE_MULT * d["chance"] / 100.0 for d in table}


def bundle_hours(D, bundle, level):
    """재료 다발을 «낚시로 모으는 데 걸리는 시간»(h) — 비용과 같은 LP 게이트를 쓴다.

    ★산출을 재료별 단가 합으로 재면 안 된다(제8원칙) — 한 굴림이 표 전체를 독립 판정하므로
      같은 시간을 여러 번 세게 된다. 다발째로 LP 에 넣으면 «한 지역에서 동시에 나온다» 는
      결합생산이 그대로 반영된다(실측: 합산 방식이 다발 방식의 3.4 배로 부풀었다).
    """
    base = collections.Counter({("fish", m): q for m, q in bundle.items()})
    h, _lam, _acts, _un = D.gate(base, level)
    return h


def recipe_cost(D, ings, level):
    """레시피 재료비 — LP 시간(h) + no-source 목록."""
    base = D.expand(ings)
    hours, lam, acts, unresolved = D.gate(base, level)
    dead = [(m, q) for k, m, q in unresolved if k == "no-source"]
    return hours, dead



# ── 신설 레시피 설계 ───────────────────────────────────────────────────
#: τ 사다리 — 「재료비 ÷ 평생 산출」. 상위 티어일수록 마진이 얇아진다(SKILL ★② 등급 상승 규칙).
TAU_LO, TAU_HI = 0.30, 0.55
#: 재료별 모양 가중 — 1.0 이면 그 재료가 «게이트를 물린다»(비용을 정하는 축).
#  1.0 미만은 같은 시간 안에서 공짜로 얹히는 양이라 레시피가 얇아 보이지 않게 해 준다.
SHAPE = {"물고기비늘": 1.00, "강화실": 1.00, "진주": 0.80, "나뭇가지": 0.80, "별빛진주": 0.50}
SHAPE_DEFAULT = 1.00                     # 지역 전용 재료 — 정체성 축이라 항상 물린다
#: 레시피에 넣지 않는 재료.
#   미감정 유물 = 감정해서 «여는» 보상물이고 레시피 사용처가 0 이다.
#   용암수지    = S 급 전용(바르칸 낚싯대·작살에만 쓴다) — 저티어 침범 금지.
#   별빛진주   = A/S 종결 전용(사용처 63 곳 중 A 46·S 7) — 통발은 중반 보조 시스템이라
#                넣으면 저티어 침범이다(selftest §7 과 같은 규약). 대체재는 «진주».
#                ★게다가 상단마을·부두는 별빛진주가 1~2% 라, 한 개만 넣어도 LP 가 그 재료를
#                  다른 지역에서 조달해 버린다 = 「그 지역 재료로 그 지역 통발」이 깨진다.
EXCLUDE = {"미감정 유물", "용암수지", "별빛진주"}
#: 범용 재료 — 전 지역에서 같은 확률로 나오는 것들. 나머지가 «그 지역 전용»이다.
UNIVERSAL = {"물고기비늘", "강화실", "진주", "별빛진주", "나뭇가지"}
#: 전용 재료 요구량 상한 = 그 통발이 평생 뱉는 양 × 이 값.
#  ★통발이 제 정체성 재료를 «순소비»하면 안 된다 — 원양 통발이 용비늘 4 를 요구하는데
#    평생 3.8 만 뱉으면 「통발로 용비늘을 모은다」가 성립하지 않는다(설계 목적과 반대).
IDENTITY_MAX_SHARE = 0.60


def design(D):
    specs = load_specs()
    specs.sort(key=lambda x: x["unlockPrice"])
    mats = json.load(open(BS / "materials.json", encoding="utf-8"))
    names = {k: v["name"] for k, v in mats["materials"].items()}
    mcitem = {k: v["mcItem"] for k, v in mats["materials"].items()}
    tables = mats["dropTables"]
    won, _ = MEAS.wage()
    out = []
    n = len(specs) - 1
    for i, sp in enumerate(specs):
        lv = RU.unlock_level(sp["region"])
        fv, npool, _ = fish_value(D, sp["region"])
        out_h = fv * sp["maxDur"] / won + bundle_hours(
            D, output_bundle(D, sp["region"], sp["waitSec"], sp["maxDur"]), lv)
        tau = TAU_LO + (TAU_HI - TAU_LO) * (i / n if n else 0)
        target = tau * out_h
        rate = D.act["낚시:" + sp["region"]]
        yields = output_bundle(D, sp["region"], sp["waitSec"], sp["maxDur"])
        ings = []
        for row in tables[sp["region"]]:
            mid = row["matId"]
            if mid in EXCLUDE:
                continue
            q = max(1, int(round(target * rate.get(mid, 0) * SHAPE.get(mid, SHAPE_DEFAULT))))
            if mid not in UNIVERSAL:      # 전용 재료 — 자기소비 상한
                cap = int(yields.get(mid, 0) * IDENTITY_MAX_SHARE)
                q = max(1, min(q, cap)) if cap >= 1 else 1
            ings.append({"kind": "custom", "typeOrMatId": mid,
                         # ★mcItem 은 «GUI 그리드의 폴백 베이스» 일 뿐이다 — CraftingGui 가 custom 재료엔
            #   ItemIconModel.apply(matId) 로 리소스팩 아이콘을 덮어씌운다. materials.json 을
            #   그대로 따른다(구 TrapSpecs 는 물고기비늘을 cod 로 써 실제 아이템과 어긋나 있었다).
                         "displayName": names.get(mid, mid), "mcItem": mcitem.get(mid, "paper"),
                         "qty": q})
        # ★정체성 먼저 — 「그 지역의 것 → 엮을 실 → 유인 → 진주」 순으로 읽히게.
        #   수량 순으로 정렬하면 어느 통발이나 「물고기 비늘」이 맨 앞에 와서 다 똑같아 보인다.
        order = {"강화실": 1, "물고기비늘": 2, "진주": 3, "나뭇가지": 4}
        ings.sort(key=lambda x: (order.get(x["typeOrMatId"], 0), -x["qty"]))
        real_h, dead = recipe_cost(D, ings, lv)
        out.append(dict(spec=sp, lv=lv, out_h=out_h, tau_target=tau,
                        tau_real=real_h / out_h if out_h else float("inf"),
                        cost_h=real_h, ings=ings, dead=dead, yields=yields, npool=npool))
    return out


def print_design(rows):
    print("\n=== 신설 레시피 (전 재료 커스텀) ===")
    print(f"{'지역':<15}{'Lv':>4}{'산출h':>7}{'목표τ':>7}{'실제τ':>7}{'비용h':>7}  레시피")
    for r in rows:
        ing = " · ".join(f"{i['displayName']}×{i['qty']}" for i in r["ings"])
        print(f"{r['spec']['label']:<15}{r['lv']:>4}{r['out_h']:>7.2f}"
              f"{r['tau_target']:>7.0%}{r['tau_real']:>7.0%}{r['cost_h']:>7.2f}  {ing}")
        if r["dead"]:
            print(f"{'':<15}  🔴 조달불가 잔존: {r['dead']}")
    print("\n=== TrapSpecs.java 재료 인자 (patch_trap_materials.py 가 이걸 넣는다) ===")
    for r in rows:
        args = ", ".join(f'mat("{i["typeOrMatId"]}", "{i["mcItem"]}", "{i["displayName"]}", {i["qty"]})'
                         for i in r["ings"])
        print(f'  {r["spec"]["region"]}: {args}')
    print("\n=== 자기소비 검사 — 통발이 제 정체성 재료를 순소비하지 않는가 ===")
    print(f"{'지역':<15}{'전용재료':<12}{'요구':>5}{'평생산출':>9}{'순증':>8}")
    bad = 0
    for r in rows:
        for i in r["ings"]:
            mid = i["typeOrMatId"]
            if mid in UNIVERSAL:
                continue
            y = r["yields"].get(mid, 0.0)
            net = y - i["qty"]
            flag = "" if net > 0 else "  🔴 순소비"
            bad += net <= 0
            print(f"{r['spec']['label']:<15}{i['displayName']:<12}{i['qty']:>5}{y:>9.1f}{net:>8.1f}{flag}")
    print("  🟢 전 종 순증" if not bad else f"  🔴 {bad}종이 자기 재료를 순소비한다")


def main():
    D = MV.Data()
    specs = load_specs()
    won, _exact = MEAS.wage()
    print(MEAS.banner())
    print(f"  원 환산 {won:,.0f}원/h · 통발 재료 굴림 = round(대기초/120) × 확률 ×{TRAP_CHANCE_MULT:g}")
    print(f"\n=== 통발 {len(specs)}종 — 현행 진단 ===")
    print(f"{'지역':<15}{'Lv':>4}{'내구':>4}{'대기':>5}{'풀':>3}  {'물고기h':>8}{'재료h':>7}{'산출h':>7}"
          f"{'재료비h':>8}{'τ':>7}  조달불가")
    rows = []
    for s_ in specs:
        lv = RU.unlock_level(s_["region"])
        fv, npool, _pool = fish_value(D, s_["region"])
        fish_h = fv * s_["maxDur"] / won
        mat_h = bundle_hours(D, output_bundle(D, s_["region"], s_["waitSec"], s_["maxDur"]), lv)
        out_h = fish_h + mat_h
        cost_h, dead = recipe_cost(D, s_["ingredients"], lv)
        tau = cost_h / out_h if out_h else float("inf")
        rows.append(dict(spec=s_, lv=lv, fish_h=fish_h, mat_h=mat_h, out_h=out_h,
                         cost_h=cost_h, tau=tau, dead=dead, npool=npool))
        dstr = ", ".join(f"{m}×{int(q)}" for m, q in dead) if dead else "—"
        print(f"{s_['label']:<15}{lv:>4}{s_['maxDur']:>4}{s_['waitSec']//60:>4}분{npool:>3}  "
              f"{fish_h:>8.2f}{mat_h:>7.2f}{out_h:>7.2f}{cost_h:>8.2f}{tau:>7.1%}  {dstr}")

    if "--design" in sys.argv:
        print_design(design(D))
        return rows
    dead_all = sorted({m for r in rows for m, _ in r["dead"]})
    if dead_all:
        print(f"\n  🔴 조달 불가(LP 공급원 0) {len(dead_all)}종: {', '.join(dead_all)}")
        print("     ★LP 는 이것들을 비용 0 으로 빼고 센다 — 위 τ 는 하한이고, 실제로는 만들 수 없다.")
    else:
        print("\n  🟢 조달 불가 재료 없음 — 전 재료가 그 지역 낚시 드롭이다")
    bad = [r for r in rows if r["tau"] >= 1.0]
    if bad:
        print(f"  🔴 τ ≥ 100%% (재료비가 평생 산출보다 비쌈) {len(bad)}종: "
              + ", ".join(f"{r['spec']['label']} {r['tau']:.0%}" for r in bad))
    nofish = [r for r in rows if r["npool"] == 0]
    if nofish:
        print(f"  🔴 통발 어종 풀이 비어 있음 {len(nofish)}종: "
              + ", ".join(r["spec"]["label"] for r in nofish) + "  (fish.json regions.<지역>.통발)")
    return rows


if __name__ == "__main__":
    main()
