#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rod_lines.py — 스폰마을 낚싯대 «라인 설계»의 단일 권위 (2026-08-27).

`rod_rebalance.py` 를 대체한다. 구 스크립트는 «회수시간을 등급 중위에 맞추도록
부스탯을 스케일»하는 것만 했는데, 그 접근은 두 번 실패했다:
  ① 내구보존이 숙련형의 유일한 조정축이라 스케일러가 행운에 전부 쏟아부었다.
  ② 난이도를 «단가 × 점수»로 세는 바람에 고난이도(6~10)를 통째로 과대평가했다.
둘 다 원인이 같다 — **난이도는 선형이 아니고, 라인 정체성은 스칼라가 아니다.**

이 스크립트는 순서를 뒤집는다:
    1. 라인마다 «메인 + 부스탯 1~2» 를 사람이 고정한다(LINES).
    2. 난이도는 «구조 목표»에서 역산한다(순간이동 문턱, teleport_table()).
    3. 남은 자유도(부스탯 크기 · 돈가격)만 회수시간에 맞춘다.

★난이도가 왜 특별한가
    net = rodBonus − fishDifficulty(등급) − sizeDifficulty(cm)
    zoneWidth = 8 + floor(net/2)  → 1 미만이면 존이 «순간이동»(overflowDiff>0)
고등급 매출 비중이 초반 A 29% · 중반 S 28.6% 라 난이도는 «매출 절반의 문지기»다.
그래서 모든 라인에 깔면 전 라인이 «난이도 낚싯대 + 장식»으로 수렴한다(실측: C
상인형 판매보너스가 6 → 2 로 밀렸다). 숙련형에 몰아주고 나머지는 얕게 깐다.

사용:
    python3 rod_lines.py                # 설계표 + 회수시간 + 순간이동 검증
    python3 rod_lines.py --tune         # 부스탯을 회수시간 목표에 맞춰 재탐색
    python3 rod_lines.py --plan         # patch_*.py 에 붙일 ROD_PLAN 형태로 출력
"""
import argparse, collections, importlib.util, json, os, shutil
import statistics as st
import sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, [name]
    spec.loader.exec_module(mod)
    sys.argv = saved
    return mod


MV = _load("material_value")
SV = _load("stat_value")
HV = _load("harpoon_value")
IL = _load("item_ledger")
MEAS = _load("measured")
EL = _load("enhance_lines")   # 난이도 3층 예산·숙련 시리즈의 단일 권위

STAT_ORDER = ["난이도", "도망감소", "크리배율", "등급업", "크리확률", "크기", "경험치",
              "판매보너스", "더블찬스", "트리플찬스", "행운", "재료확률", "등급특화"]

#: 라인 → (메인, 부스탯…). 부스탯은 «1~2개» 가 원칙 — 3개를 넘으면 정체성이 안 읽힌다.
LINES = {
    "숙련":  ("난이도", ["도망감소", "경험치"]),
    "크리":  ("크기", ["크리확률", "크리배율"]),
    "행운":  ("행운", ["등급업"]),
    "상인":  ("판매보너스", ["더블찬스"]),
    "성장":  ("경험치", ["트리플찬스"]),
    "채집":  ("재료확률", ["경험치"]),
}
#: 등급 → 라인별 기본 난이도. ★복제 금지 — `enhance_lines.ROD_DIFF` 가 단일 권위다
#  (낚싯대 기본 + 강화 총량 + 숙련부품 3층이 «순간이동 문턱»을 함께 만들기 때문에
#   한 곳에서만 정의해야 한다).
DIFF_BY_GRADE = EL.ROD_DIFF
#  ★2026-08-27 **회수시간 목표 폐기 → 순성능 사다리**. 유저 결정:
#    "회수는 일단 빼고 계산 다시 해줘. 왜냐면 짜피 재료들 밸런스도 다시 조정해야하거든,
#     그래서 일단 성능들로만 해줘. 성능은 레벨이 같아도 10% 20%정도는 달라도됨."
#    재료·가격이 곧 재조정될 예정이라 회수시간(= 성능 ÷ 비용)을 맞추는 것은 «움직이는
#    분모»에 맞추는 일이다. 성능만 사다리에 올려놓고 비용은 나중에 덮는다.
#
#  사다리 = 스폰마을 낚싯대 21종의 순성능 로그선형 적합 (2026-08-27 라이브 실측):
#      ln(순성능) = 8.917 + 0.0628 × Lv       → 레벨당 +6.5%
#      Lv3 9,007 · Lv7 11,573 · Lv13 16,872 · Lv27 40,672 원/h
#      ★BAND_EXEMPT_UP 종은 적합에서 **뺀다** — 위쪽 면제분이 사다리를 끌어올려 나머지가
#        전부 «약함»으로 잡힌다(수련생 포함 시 Lv3 목표가 9,007 → 9,278 로 3% 밀렸다).
#  ★2026-08-27 재적합 — D등급 진입이 Lv5 → **Lv3** 으로 내려가면서(튜토 종료가 Lv3 인데
#    D 하한이 5 라 Lv3~4 가 죽은 구간이었다) 레벨 배치가 바뀌었다. 사다리는 «레벨→성능»
#    서술이므로 레벨이 바뀌면 서술도 바뀐다. 성능은 그대로 두고 계수만 옮겼다 —
#    성능을 구 사다리에 다시 맞추면 D 를 13% 너프하는 셈이고 그건 요청과 반대다.
#    구 계수(8.814/0.0667) 대비: 저레벨 목표 +8.5% · Lv27 −1.4% (곡선이 완만해졌다)
#  ★계수를 매 실행마다 재적합하지 않는다 — 자기 출력에 다시 맞추면 사다리가 표류한다.
#    전체 파워 레벨을 올리거나 내리려면 EFF_A 를 옮긴다(기울기 EFF_B 는 진행 속도).
EFF_A, EFF_B = 8.917, 0.0628
#: 허용 밴드 — 유저 확정 «같은 레벨이라도 10~20% 차이는 가격으로 커버». 안쪽(±10%)을 목표로
#  잡고 바깥(±20%)을 경보선으로 쓴다.
BAND_OK, BAND_WARN = 0.10, 0.20
#: E급 3종은 사다리 밖 — 튜토리얼 구간이다. 나뭇가지는 무료(가격 0·재료 0)라 성능도 거의 0
#  이어야 하고, 초보자/초보 낚싯대는 사다리 시작점(Lv3 8,914) 이전에 둔다. 실측 2,300~2,500
#  → D 첫 장비(Lv3 9,451)로 3.7배 도약한다. 그게 «튜토 졸업»의 체감이고 의도다.
EXEMPT = {"나뭇가지", "초보자 낚싯대", "초보 낚싯대"}
#: 사다리 «위쪽»만 면제 — 목표보다 강해도 끌어내리지 않고, 적합에서도 뺀다(사다리를 왜곡한다).
#  값은 이유. ★근거 없이 늘리지 말 것 — 면제가 늘면 사다리가 의미를 잃는다.
BAND_EXEMPT_UP = {
    "수련생 낚싯대":
        "성장형 D — 2026-08-27 Lv6 → Lv3 이동. 초반이 레벨링 국면의 핵심인데 E급 13종 중 "
        "경험치 보유가 1종(초보자 낚싯대 3%)뿐이라 Lv1~6 이 «레벨링 부스트 공백»이었다. "
        "실측 Lv6 도달 중위 2.86h(느린 쪽 4.4h). 경험치의 효용은 앞으로 쏠려 있으므로 "
        "이 낚싯대가 Lv3 최강인 것은 설계 의도다. 다만 경험치 9 → 8 로 한 칸만 깎아 "
        "+13.2% 로 맞췄다(유저 허용 10~20% 안). Lv3 동레벨 산포 +10.6%.",
}


def eff_target(lv):
    import math
    return math.exp(EFF_A + EFF_B * lv)


#: 설계 대상 — 이름: (등급, 라인표시, 부스탯, 등급특화, 돈가격 덮어쓰기|None)
#  ★부스탯 수치는 --tune 산출값이다. 손으로 만지지 말고 --tune 을 다시 돌릴 것.
DESIGN = {
    "나뭇가지":           ("E", "입문", {"행운": 1}, None, None),
    "초보자 낚싯대":       ("E", "입문", {"경험치": 3}, None, None),
    "초보 낚싯대":         ("E", "입문", {"크기": 3, "크리확률": 2}, None, None),
    "튼튼한 막대기":       ("D", "숙련", {"도망감소": 2, "경험치": 2}, None, 8700),
    "참나무 낚싯대":       ("C", "숙련", {"도망감소": 11, "경험치": 5}, None, 48200),
    "전문가 낚싯대":       ("B", "숙련", {"도망감소": 11, "경험치": 6}, None, 52300),
    "낚시견습생의 낚싯대":  ("D", "크리", {"크기": 11, "크리확률": 7}, None, None),
    "낚시꾼의 낚싯대":     ("C", "크리", {"크기": 15, "크리확률": 11}, None, None),
    "예리한 낚싯대":       ("B", "크리", {"크기": 15, "크리확률": 11, "크리배율": 1}, None, None),
    "대나무 막대기":       ("D", "행운", {"행운": 11, "등급업": 3}, None, None),
    "잉어꾼의 낚싯대":     ("C", "행운", {"행운": 14, "등급업": 4}, "C:50", None),
    "숙련자의 낚싯대":     ("B", "행운", {"행운": 14, "등급업": 5}, None, None),
    "장터 낚싯대":         ("D", "상인", {"판매보너스": 8, "더블찬스": 3}, None, None),
    "장사꾼의 낚싯대":     ("C", "상인", {"판매보너스": 13, "더블찬스": 4}, None, None),
    "거래상의 낚싯대":     ("B", "상인", {"판매보너스": 19, "더블찬스": 8}, None, None),
    "수련생 낚싯대":       ("D", "성장", {"경험치": 8, "트리플찬스": 1}, None, None),
    "경험의 낚싯대":       ("C", "성장", {"경험치": 13, "트리플찬스": 2}, None, None),
    "학도의 낚싯대":       ("B", "성장", {"경험치": 19, "트리플찬스": 2}, None, None),
    "다목적 낚싯대":       ("C", "혼합", {"도망감소": 6, "판매보너스": 10, "더블찬스": 4}, None, 84500),
    "겸업 낚싯대":         ("B", "기타", {"등급업": 4, "크리확률": 6, "크기": 11}, None, None),
    "만능 낚싯대":         ("B", "혼합", {"도망감소": 6, "판매보너스": 10, "더블찬스": 5}, None, 64300),
    "채집용 낚싯대":       ("D", "채집", {"재료확률": 11, "경험치": 3}, None, None),
    "수집가의 낚싯대":     ("C", "채집", {"재료확률": 16, "경험치": 4}, None, None),
    "탐사자의 낚싯대":     ("B", "채집", {"재료확률": 28, "경험치": 7}, None, None),
}
#: 숙련 계열 부품 — 각 슬롯의 «군더더기 없는 기본형» 시리즈에 난이도를 부스탯으로 준다.
#  새 아이템/레시피를 만들지 않는다(상점 목록·제작 UI 를 늘리지 않는 것이 설계 의도).
#  값은 `enhance_lines.PART_DIFF` · 대상은 `enhance_lines.SKILL_SERIES`.
#  ★슬롯별로 목표가 다르다 — 줄은 축 자체가 약하다. 실측(전 부품 원장):
#      릴 회수 중위 6.6h · 바늘 9.5h · 찌 11.8h · **줄 19.7h** (재료원은 4슬롯 동일 213,427원)
#    원인은 도망감소가 **B등급 전용 스탯**이라는 것이다 — 0→80 이 B 를 69%→100% 로 올리지만
#    A 는 +5%p · S 는 +2%p 뿐이고 80 에서 완전 포화한다. 존폭이 1~2칸인 A/S 에서는 도주율을
#    낮춰도 계속 미스해 escapeInc 가 100 까지 밀어올린다. 즉 **도망감소는 난이도의 대체재가
#    아니다** — 난이도는 «맞히게» 해주고 도망감소는 «한 번 더 기회»를 준다. 존이 1칸이면
#    기회를 더 줘도 못 맞힌다. ⇒ 수치를 3배로 올려도 해결 안 되고, 남은 처방은 **줄 레시피
#    원가 인하**뿐이다(별건 — 원가를 건드리면 전 슬롯·낚싯대의 재료 게이트가 다 흔들린다).
#    여기서는 줄에만 완화 목표를 주고 그 사실을 드러낸다.
PART_TARGET = {"E": None, "D": 9.0, "C": 9.5, "B": 10.5, "A": 12.0, "S": 13.0}
PART_TARGET_BY_SLOT = {"줄": {"D": 15.0, "C": 15.0, "B": 15.0, "A": 16.0, "S": 16.0}}

#: 라인 표시 → DIFF_BY_GRADE 키. «겸업»(크리+행운)은 난이도가 정체성이 아니라 기타.
DIFF_KEY = {"숙련": "숙련", "채집": "채집", "혼합": "혼합", "입문": "기타"}

#: 부스탯 최소값 — 0 이 되면 라인의 부스탯이 사라져 정체성이 깨진다.
MINV = collections.defaultdict(lambda: 1)


def diff_of(name):
    g, line, *_ = DESIGN[name]
    return DIFF_BY_GRADE[DIFF_KEY.get(line, "기타")][g]


def stat_str(name, subs=None):
    g, line, s0, spec, _ = DESIGN[name]
    subs = s0 if subs is None else subs
    d = {}
    dv = diff_of(name)
    if dv:
        d["난이도"] = dv
    for a, b in subs.items():
        if b > 0:
            d[a] = int(b)
    if spec:
        d["등급특화"] = spec
    return ",".join(f"{a}:{d[a]}" for a in STAT_ORDER if a in d)


# ── 순간이동 문턱 (구조 지표 — 모델 캘리브레이션과 무관하게 참) ─────────────
def teleport_frac(rod_bonus, grade="S"):
    """그 등급 어종 중 «존 순간이동»이 걸리는 크기 비율. zoneWidth<1 ⇔ net ≤ −15."""
    fd = {"E": 0, "D": 2, "C": 4, "B": 8, "A": 12, "S": 16, "M": 24, "L": 28, "G": 32}[grade]
    dist = SV.size_difficulty_dist()[grade]
    return sum(w for sd, w in dist.items() if (rod_bonus - fd - sd) <= -15)


_ENH_TABLE = None


def enh_tables():
    """`enhance_lines` 가 생성한 강화표 — 난이도 검증의 권위. 라이브 파일이 아니라
    «지금 설계가 산출하는» 표를 봐야 한다(라이브는 아직 구 표일 수 있다)."""
    global _ENH_TABLE
    if _ENH_TABLE is None:
        _ENH_TABLE, _ = EL.generate()
    return _ENH_TABLE


def enh_diff(rod, level):
    """rod 를 level 까지 강화했을 때 누적 난이도 (생성된 표 기준)."""
    ent = enh_tables().get(rod) or {}
    tot = 0
    for i in range(1, level + 1):
        for t in (ent.get("levels") or {}).get(str(i), "").split(","):
            if t.startswith("난이도:"):
                tot += float(t.split(":", 1)[1])
    return tot


# ── 원장 ────────────────────────────────────────────────────────────────
def ledger(subs_by_name=None, part_prices=None):
    """DESIGN 을 임시 parts.json 에 써서 item_ledger 로 총비용·순성능·회수를 낸다."""
    P = json.load(open(os.path.join(MV.BS, "parts.json"), encoding="utf-8"))
    for n, (g, line, s0, spec, price) in DESIGN.items():
        f = P["parts"]["낚싯대"][n].split("|")
        over = (part_prices or {}).get(n, price)
        if over is not None:
            f[2] = str(over)
        f[4] = stat_str(n, (subs_by_name or {}).get(n))
        P["parts"]["낚싯대"][n] = "|".join(f)
    # 숙련 계열 부품 12종에 난이도 부스탯
    for slot, members in EL.SKILL_SERIES.items():
        for pname, pg in members.items():
            f = P["parts"][slot][pname].split("|")
            st = {k: v for k, v in (x.split(":", 1) for x in f[4].split(",") if ":" in x)}
            st["난이도"] = str(EL.PART_DIFF[pg])
            if part_prices and pname in part_prices:
                f[2] = str(part_prices[pname])
            f[4] = ",".join(f"{k}:{st[k]}" for k in
                            ["난이도", "도망감소", "크리배율", "등급업", "크리확률", "크기",
                             "경험치", "판매보너스", "더블찬스", "트리플찬스", "행운",
                             "재료확률"] if k in st)
            P["parts"][slot][pname] = "|".join(f)
    tmp = tempfile.mkdtemp()
    try:
        for fn in ("materials.json", "recipes.json"):
            shutil.copy(os.path.join(MV.BS, fn), tmp)
        json.dump(P, open(os.path.join(tmp, "parts.json"), "w", encoding="utf-8"),
                  ensure_ascii=False)
        rows = IL.build(MV.Data(bs=tmp), _SV, _INC, _RATIO, _HM)
    finally:
        shutil.rmtree(tmp)
    return {r["name"]: r for r in rows}


_BASE_PRICE = {}
for _slot, _mem in EL.SKILL_SERIES.items():
    _P = json.load(open(os.path.join(MV.BS, "parts.json"), encoding="utf-8"))["parts"]
    for _n in _mem:
        _BASE_PRICE[_n] = int(_P[_slot][_n].split("|")[2])


def tune(rounds=14):
    """부스탯을 **순성능 사다리**에 맞춘다(회수시간·가격은 건드리지 않는다).

    난이도는 3층 예산(`enhance_lines.ROD_DIFF`)으로 고정이고 순성능의 큰 몫을 차지한다 —
    남은 자유도인 부스탯만 정수 스케일한다. 최소 1 을 지켜 라인 정체성이 사라지지 않게 한다.
    """
    cur = {n: dict(v[2]) for n, v in DESIGN.items()}
    for _ in range(rounds):
        sel = ledger(cur)
        moved = 0
        for n, (g, line, s0, spec, price) in DESIGN.items():
            if n in EXEMPT or not cur[n]:
                continue
            r = sel[n]
            if r["eff_net"] <= 0:
                continue
            want = eff_target(r["lv"])
            ratio = r["eff_net"] / want
            if n in BAND_EXEMPT_UP and ratio >= 1:     # 위쪽 면제 — 끌어내리지 않는다
                continue
            if abs(ratio - 1) <= BAND_OK * 0.6:        # 밴드 안쪽이면 건드리지 않는다
                continue
            # 부스탯이 만드는 몫만 스케일한다 — 난이도 고정분은 분모에서 뺀다
            fixed = r["eff_net"] - _sub_value(n, cur[n], r)
            need = max(0.0, want - fixed)
            have = max(1.0, _sub_value(n, cur[n], r))
            f = max(0.5, min(2.2, need / have))
            new = {a: max(MINV[a], int(round(b * f))) for a, b in cur[n].items()}
            if new != cur[n]:
                cur[n] = new
                moved += 1
        moved += _apply_line_floor(cur)
        if not moved:
            break
    _apply_line_floor(cur)
    return cur, None


def _line_of_design(name):
    g, line, *_ = DESIGN[name]
    return line


def _apply_line_floor(cur):
    """라인 안에서 메인 스탯이 레벨과 함께 **감소하지 않게** 하는 하한 제약.

    ★왜 필요한가 — `item_ledger` 는 스탯 1점을 **그 아이템 레벨의 구간(stage)** 가치로
      센다. 스폰마을은 Lv5~27 이라 Lv20 에서 초반→중반 경계를 넘고, 그 순간 판매보너스
      1% 가 843 → 1,175 원/h 로 **39% 도약**한다. 사다리는 레벨당 6.9% 만 오르므로 B급
      낚싯대는 «더 적은 점수로 목표 성능»을 달성하고, 표시 숫자가 내려간다(실측: 예리한
      크기 10 < 낚시꾼의 14 · 숙련자의 행운 11 < 잉어꾼의 12).
      성능은 맞지만 **유저 눈에는 하향**이다 — 구간 경계는 모델의 산물이고 설계 사실이
      아니므로, 표시 숫자 쪽을 우선한다. 그 대가로 그 낚싯대는 사다리 위쪽 밴드로 올라간다
      (유저 허용 «같은 레벨 10~20% 차이는 가격으로 커버»의 여유를 여기에 쓴다).
    """
    changed = 0
    for line, (mainst, subs) in LINES.items():
        # 메인만이 아니라 **부스탯까지** 단조로 만든다 — 부스탯도 유저가 읽는 숫자다
        #   (실측: 예리한 크리확률 8 < 낚시꾼의 10 — 메인만 보면 놓친다).
        keys = [mainst if mainst != "난이도" else "도망감소"] + list(subs)
        members = sorted((_lv_of(n), n) for n in DESIGN
                         if n not in EXEMPT and _line_of_design(n) == line)
        for key in keys:
            floor = 0
            for _lv, n in members:
                if key not in cur[n]:
                    continue
                if cur[n][key] < floor:
                    cur[n][key] = floor
                    changed += 1
                floor = max(floor, cur[n][key])
    return changed


_LVCACHE = {}


def _lv_of(name):
    if not _LVCACHE:
        P = json.load(open(os.path.join(MV.BS, "parts.json"), encoding="utf-8"))
        for k, v in P["parts"]["낚싯대"].items():
            _LVCACHE[k] = int(v.split("|")[5])
    return _LVCACHE[name]


def _sub_value(name, subs, row):
    """그 낚싯대의 순성능 중 «부스탯이 만든 몫»(원/h). 난이도 누적곡선 몫을 뺀 값."""
    stage = IL.STAGE_OF_LEVEL(row["lv"])
    dv = diff_of(name)
    diff_part = SV.diff_curve(stage).get(int(dv), 0.0) if dv else 0.0
    return max(0.0, row["eff_net"] - diff_part)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tune", action="store_true", help="부스탯을 회수시간 목표에 재적합")
    ap.add_argument("--plan", action="store_true", help="ROD_PLAN 형태로 출력")
    a = ap.parse_args()

    print(MEAS.banner(_K))
    subs, prices = tune() if a.tune else (None, None)
    sel = ledger(subs, prices)

    if a.plan:
        print("\nROD_PLAN = {")
        for n, (g, line, s0, spec, price) in DESIGN.items():
            s = stat_str(n, (subs or {}).get(n))
            pr = (prices or {}).get(n, price)
            print(f'    "{n}":{" " * max(1, 20 - len(n))}("{s}", {pr!r}),')
        print("}")
        print("\nPART_PLAN = {   # 숙련 계열 부품: 난이도 부스탯 + 가격")
        for slot, members in EL.SKILL_SERIES.items():
            for pname, pg in members.items():
                print(f'    "{pname}":{" " * max(1, 16 - len(pname))}'
                      f'("{slot}", {EL.PART_DIFF[pg]}, {(prices or {}).get(pname)!r}),')
        print("}")
        return

    print(f"\n{'등':<3}{'Lv':<4}{'라인':<7}{'이름':<20}{'순성능':>9}{'사다리':>9}{'편차':>8}"
          f"{'':<2}스탯")
    dev, warn = [], []
    for n, (g, line, s0, spec, price) in sorted(
            DESIGN.items(), key=lambda kv: sel[kv[0]]["lv"]):
        r = sel[n]
        if n in EXEMPT:
            print(f"{g:<3}{r['lv']:<4}{line:<7}{n:<20}{r['eff_net']:>9,.0f}"
                  f"{'—':>9}{'면제':>8}  {stat_str(n, (subs or {}).get(n))}")
            continue
        t = eff_target(r["lv"])
        d = r["eff_net"] / t - 1
        dev.append(abs(d))
        if n in BAND_EXEMPT_UP and d >= 0:
            mark = "★ "
        else:
            mark = "  " if abs(d) <= BAND_OK else ("🟡" if abs(d) <= BAND_WARN else "🔴")
            if abs(d) > BAND_OK:
                warn.append((n, d))
        print(f"{g:<3}{r['lv']:<4}{line:<7}{n:<20}{r['eff_net']:>9,.0f}{t:>9,.0f}"
              f"{d*100:>+7.1f}%{mark}{stat_str(n, (subs or {}).get(n))}")
    import math as _m
    print(f"\n  사다리 ln(순성능) = {EFF_A} + {EFF_B}×Lv (레벨당 +{(_m.exp(EFF_B)-1)*100:.1f}%)")
    print(f"  평균 절대편차 {sum(dev)/len(dev)*100:.1f}% · 최대 {max(dev)*100:.1f}%"
          f" · 밴드(±{BAND_OK*100:.0f}%) 밖 {len(warn)}종"
          + (f" · ★위쪽 면제 {len(BAND_EXEMPT_UP)}종" if BAND_EXEMPT_UP else ""))
    for n, why in BAND_EXEMPT_UP.items():
        print(f"    ★ {n}: {why.splitlines()[0]}…")

    # 같은 레벨 산포 · 레벨 단조성
    byl = collections.defaultdict(list)
    for n in DESIGN:
        if n in EXEMPT:
            continue
        byl[sel[n]["lv"]].append((n, sel[n]["eff_net"]))
    print("\n  같은 레벨 산포 (유저 허용 10~20%):")
    for lv in sorted(byl):
        a_ = byl[lv]
        if len(a_) < 2:
            continue
        v = [x[1] for x in a_]
        sp = max(v) / min(v) - 1
        print(f"    Lv{lv:<3} {len(a_)}종  {min(v):,.0f}~{max(v):,.0f}  산포 {sp*100:+.1f}%"
              f"{'  🟡' if sp > BAND_WARN else ''}  " + ", ".join(x[0] for x in a_))
    # 라인 안 «메인 스탯» 단조성 — 성능이 같아도 상위 레벨의 정체성 스탯이 더 작으면
    # 유저 눈에는 하향이다. 난이도가 예산을 먹을 때 정확히 이 역전이 생긴다.
    print("\n  라인 안 메인 스탯 단조성:")
    for ln, (mainst, _subs) in LINES.items():
        seqm = []
        for n, (g, line, s0, spec, price) in DESIGN.items():
            if n in EXEMPT or DIFF_KEY.get(line, line) != ln and line != ln:
                continue
            st = {k: v for k, v in (x.split(":", 1) for x in
                                    stat_str(n, (subs or {}).get(n)).split(",") if ":" in x)}
            key = mainst if mainst != "난이도" else "도망감소"
            if key in st:
                seqm.append((sel[n]["lv"], int(st[key]), n))
        seqm.sort()
        if len(seqm) < 2:
            continue
        bad = [(seqm[i], seqm[i + 1]) for i in range(len(seqm) - 1)
               if seqm[i + 1][1] < seqm[i][1]]
        line_s = " → ".join(f"Lv{l} {v}" for l, v, _ in seqm)
        print(f"    {ln:<4} {key:<6} {line_s}" + ("  🔴 역전" if bad else "  🟢"))

    seq = sorted(((sel[n]["lv"], sel[n]["eff_net"], n) for n in DESIGN if n not in EXEMPT))
    inv = [(seq[i], seq[i + 1]) for i in range(len(seq) - 1)
           if seq[i + 1][1] < seq[i][1] * (1 - BAND_WARN)]
    print(f"\n  레벨 역전(다음 레벨이 {BAND_WARN*100:.0f}% 이상 약함): {len(inv)}건"
          + ("".join(f"\n    Lv{a[0]} {a[2]} {a[1]:,.0f} → Lv{b[0]} {b[2]} {b[1]:,.0f}"
                     for a, b in inv) if inv else " 🟢"))

    print(f"\n=== 숙련 계열 부품 (난이도 부스탯 신설) ===")
    print(f"  {'슬롯':<4}{'이름':<16}{'등':<3}{'난이도':>5}{'돈':>10}{'재료원':>10}"
          f"{'총비용':>10}{'순성능':>9}{'회수h':>7}  스탯")
    for slot, members in EL.SKILL_SERIES.items():
        for pname, pg in members.items():
            r = sel.get(pname)
            if not r:
                continue
            pb = r["payback"]
            print(f"  {slot:<4}{pname:<16}{pg:<3}{EL.PART_DIFF[pg]:>5}{r['price']:>10,.0f}"
                  f"{r['mat_won']:>10,.0f}{r['total']:>10,.0f}{r['eff_net']:>9,.0f}"
                  f"{('∞' if pb >= 1e6 else f'{pb:.1f}'):>7}  {','.join(f'{k}:{int(v)}' for k,v in r['stats'].items() if isinstance(v,(int,float)))}")

    print("\n=== 순간이동 검증 (구조 지표 — zoneWidth<1) ===")
    print("  ★부품 = 숙련 계열 릴·줄·바늘·찌 4슬롯 (미끼는 행운 축 유지)")
    print(f"  {'구성':<30}{'낚싯대':>7}{'강화':>5}{'부품':>5}{'합계':>5}"
          f"{'S':>8}{'A':>7}{'M':>7}")
    for rod, lab, lvl, pg in [
            ("튼튼한 막대기", "D 숙련 풀강 + D 숙련부품", 8, "D"),
            ("참나무 낚싯대", "C 숙련 풀강 + C 숙련부품", 10, "C"),
            ("참나무 낚싯대", "C 숙련 풀강 + 일반부품", 10, None),
            ("전문가 낚싯대", "B 숙련 중반강화 + C 숙련부품", 6, "C"),
            ("전문가 낚싯대", "B 숙련 풀강 + B 숙련부품", 13, "B"),
            ("낚시꾼의 낚싯대", "C 일반 풀강 + C 숙련부품", 10, "C"),
            ("낚시꾼의 낚싯대", "C 일반 풀강 + 일반부품", 10, None),
            ("예리한 낚싯대", "B 일반 풀강 + B 숙련부품", 13, "B"),
            ("다목적 낚싯대", "C 혼합 풀강 + C 숙련부품", 10, "C"),
            ("만능 낚싯대", "B 혼합 풀강 + B 숙련부품", 13, "B"),
            ("탐사자의 낚싯대", "B 채집 풀강 + B 숙련부품", 13, "B")]:
        base, e = diff_of(rod), enh_diff(rod, lvl)
        pd = EL.PART_DIFF[pg] * 4 if pg else 0
        rb = base + e + pd
        print(f"  {lab:<30}{base:>7}{e:>5.0f}{pd:>5}{rb:>5.0f}"
              f"{teleport_frac(rb,'S')*100:>7.1f}%{teleport_frac(rb,'A')*100:>6.1f}%"
              f"{teleport_frac(rb,'M')*100:>6.1f}%")

    print("\n=== 강화 사다리 (유저 제약: C풀강 ≥ B중반강화 ≥ A기본) ===")
    for dk in ("숙련", "혼합", "기타", "채집"):
        c = EL.ROD_DIFF[dk]["C"] + EL.ENH_DIFF[dk]["C"]
        b = EL.ROD_DIFF[dk]["B"] + EL.ENH_DIFF[dk]["B"] // 2
        aa = EL.ROD_DIFF[dk]["A"]
        print(f"  {dk:<4} C풀강 {c:>2} · B중반 {b:>2} · A기본 {aa:>2}"
              f"   {'✓' if c >= aa and abs(c - b) <= 1 else '✗'}")


_K = MEAS.apply(SV)
_SV, _INC = {}, {}
for _s in SV.STAGES:
    _r = SV.compute(_s)
    _SV[_s] = {k: v[0] for k, v in _r["V"].items()}
    _INC[_s] = _r["income"]
_HM = HV.Model()
_HS = _K["harpoon"]
_RATIO = ((_HS["catches_per_active_h"] / SV.CATCH_PER_HOUR)
          * (SV.size_mult(_HS["quality_mean"]) / SV.size_mult(_K["size_score"])))

if __name__ == "__main__":
    main()
