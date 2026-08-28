#!/usr/bin/env python3
"""낚싯대·작살 «계열 × 레벨» 사다리 — 전 등급 (2026-08-29, 출시 점검).

★왜 새로 쓰나
  `rod_lines.py` 의 DESIGN 표는 **E~B 24종뿐**이고 A·S 가 없다. 라이브 낚싯대는 73종이라
  49종이 표 밖이다. `spear_lines.py` 는 아예 튜너가 없다(--plan 만). 그래서
  「스폰마을(E~B)은 계열을 맞췄는데 사막마을 이후는 안 했다」는 상태가 그대로 남아 있었다.
  실측(2026-08-29): 계열 안에서 레벨이 올라갔는데 순성능이 내려가는 역전이
      낚싯대 40건(숙련 37) · 작살 32건(깡스탯 16 · 행운 8)

  손으로 DESIGN 표를 49줄 늘리는 대신, **스탯 서명으로 계열을 읽고 사다리를 데이터에서
  적합하는** 범용 튜너를 쓴다. 그래야 항목이 늘어도 표를 안 고친다.

★사다리 = (카테고리 × 계열) 별 등위회귀(PAV)
  단조 비감소가 구조적으로 보장되고, 이미 맞게 선 항목은 제자리에 남는다(최소 이동).
  사다리 «수준» 은 라이브가 정한다 — 임의 상수가 아니다.
  ★계열마다 따로 세운다: 순성능(eff_net)은 재료확률(게이트축)·난이도(3층 예산)를 값으로
    안 센다. 한 덩어리로 묶으면 채집·숙련이 영원히 «미달» 로 잡힌다.

★건드리지 않는 축
  · 카테고리 주스탯 — 낚싯대는 없음(계열이 곧 정체성), 작살은 공격력·수영속도·수중호흡·
    호흡시간(수중 생존 = 작살의 존재 이유. 이걸 스케일하면 물속에서 죽는다).
  · 난이도(3층 예산) · 재료확률(채집 라인 정체성) · 야간투시(0/1/2 플래그성).

사용:  patch_gear_lines.py [--apply]
"""
import collections, importlib.util, json, os, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "ops", "blockship-data")
SKILL = os.path.join(ROOT, ".claude", "skills", "balance-audit", "scripts")
os.environ.setdefault("BLOCKSHIP_DATA", os.path.abspath(os.path.join(ROOT, "..", "..", "BlockShip")))


def _load(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(SKILL, n + ".py"))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


MV = _load("material_value")
IL = _load("item_ledger")
SV = _load("stat_value")
PL = _load("part_lines")       # ledger 인프라·정규화 상수 재사용 (복제 금지)

CATS = ("낚싯대", "작살")
#: 스케일하지 않는 축
FROZEN = {"난이도", "재료확률", "야간투시"}
#: 작살 주스탯 — 수중 생존은 작살의 존재 이유다. 스케일하면 물속에서 죽는다.
FROZEN_SPEAR = {"공격력", "수영속도", "수중호흡", "호흡시간", "돌진쿨감"}
BAND_OK, BAND_WARN = 0.10, 0.20
#: ★자체 fmt 를 쓴다. part_lines.fmt 은 «부품 12축» STAT_ORDER 에 없는 키를 조용히 버린다 —
#:  작살의 공격력·수영속도·수중호흡·호흡시간·돌진쿨감·야간투시가 통째로 사라졌다
#:  (2026-08-29 실측: 66종에서 주스탯이 날아가 「나무 작살 → 스탯 없음」이 됐다).
#:  키를 잃지 않는 게 우선이라 «알려진 순서 먼저, 나머지는 원래 순서대로» 로 쓴다.
STAT_ORDER = ["난이도", "공격력", "공격속도", "도망감소", "수영속도", "수중호흡", "호흡시간",
              "돌진쿨감", "야간투시", "크리배율", "등급업", "크리확률", "크기", "경험치",
              "판매보너스", "더블찬스", "트리플찬스", "행운", "재료확률"]


def fmt(d):
    keys = [k for k in STAT_ORDER if d.get(k)] + [k for k in d if k not in STAT_ORDER and d.get(k)]
    return ",".join(f"{k}:{d[k]}" for k in keys)
MINV = collections.defaultdict(lambda: 1)
#: 스탯 상한 — ★상수로 적지 않고 «라이브 그 등급의 실제 최대값 × 여유» 로 잡는다.
#:  상수표는 등급이 늘거나 스탯 축이 추가되면 조용히 어긋난다. 그리고 임의 배율(D캡 × 5.5)
#:  로 A 상한을 만들면 라이브에 없는 값이 나온다 — 실제로 흑단목 낚싯대가 행운 6 → 44 로
#:  튀었다(A 실측 천장은 36). 라이브를 기준으로 두면 그런 일이 없다.
_HEADROOM = 1.15
_CAP_CACHE = {}


def _caps():
    if _CAP_CACHE:
        return _CAP_CACHE
    P = json.load(open(os.path.join(BASE, "parts.json"), encoding="utf-8"))["parts"]
    for cat, items in P.items():
        for _n, raw in items.items():
            f = raw.split("|")
            g = f[1]
            for t in f[4].split(","):
                if ":" not in t:
                    continue
                k, v = t.split(":", 1)
                try:
                    v = int(float(v))
                except ValueError:
                    continue
                d = _CAP_CACHE.setdefault(g, {})
                d[k] = max(d.get(k, 0), v)
    return _CAP_CACHE


def cap_for(grade, stat):
    return max(1, int(round(_caps().get(grade, {}).get(stat, 99) * _HEADROOM)))


#: 원본 대비 누적 이동 한계. 라운드마다 ±2.5배가 곱해지면 «알아볼 수 없는 물건»이 된다.
MOVE_LO, MOVE_HI = 0.5, 3.0


def line_of(cat, stats):
    """스탯 서명 → 계열.

    ★«난이도» 를 맨 뒤에서 본다. 낚싯대는 거의 전부 난이도를 갖는 공통 스탯이라,
      앞에서 보면 73종 중 67종이 「숙련」 한 바구니에 들어가고 크리 낚싯대와 행운 낚싯대를
      맞대 놓고 «역전» 이라 부르게 된다(2026-08-29 실측: 그렇게 41건이 잡혔다).
      난이도만 있고 다른 표식이 없을 때에만 숙련이다.
    """
    s = set(stats)
    if "재료확률" in s:
        return "채집"
    if "등급업" in s and "행운" in s:
        return "행운"
    if "판매보너스" in s:
        return "상인"
    if "크리확률" in s or "크리배율" in s:
        return "크리"
    if "트리플찬스" in s or "경험치" in s:
        return "성장"
    if "행운" in s:
        return "행운"
    if "난이도" in s or "도망감소" in s:
        return "숙련"
    return "깡스탯"


def targets():
    P = json.load(open(os.path.join(BASE, "parts.json"), encoding="utf-8"))["parts"]
    out = {}
    for cat in CATS:
        for name, raw in P[cat].items():
            f = raw.split("|")
            src = f[6] if len(f) > 6 else ""
            if src in ("캐시", "개발자", "잠수상점"):
                continue
            out[(cat, name)] = (int(f[5]), PL.parse(f[4]), f[1])
    return out


def ledger(overrides):
    P = json.load(open(os.path.join(BASE, "parts.json"), encoding="utf-8"))
    for (cat, name), st in overrides.items():
        f = P["parts"][cat][name].split("|")
        f[4] = fmt(st)
        P["parts"][cat][name] = "|".join(f)
    tmp = tempfile.mkdtemp()
    try:
        for fn in ("materials.json", "recipes.json"):
            shutil.copy(os.path.join(BASE, fn), tmp)
        json.dump(P, open(os.path.join(tmp, "parts.json"), "w", encoding="utf-8"), ensure_ascii=False)
        rows = IL.build(MV.Data(bs=tmp), PL._SV, PL._INC, PL._RATIO, PL._HM)
    finally:
        shutil.rmtree(tmp)
    return {r["name"]: r for r in rows}


def fit(pts):
    """PAV 등위회귀 — [(lv, v)] → {lv: 목표}."""
    if not pts:
        return {}
    pts = sorted(pts)
    grouped, i = [], 0
    while i < len(pts):
        j = i
        while j < len(pts) and pts[j][0] == pts[i][0]:
            j += 1
        grouped.append([pts[i][0], sum(v for _, v in pts[i:j]) / (j - i), j - i])
        i = j
    st = []
    for lv, v, w in grouped:
        st.append([lv, v, w])
        while len(st) > 1 and st[-2][1] > st[-1][1]:
            l2, v2, w2 = st.pop(); l1, v1, w1 = st.pop()
            st.append([l1, (v1 * w1 + v2 * w2) / (w1 + w2), w1 + w2])
    out, k = {}, 0
    for lv, _v, _w in grouped:
        while k < len(st) - 1 and lv > st[k][0]:
            k += 1
        out[lv] = st[min(k, len(st) - 1)][1]
    return out


def inversions(sel, tgt):
    n = 0
    by = collections.defaultdict(list)
    for (cat, name), (lv, st, _g) in tgt.items():
        r = sel.get(name)
        if r and r["eff_net"] > 0:
            by[(cat, line_of(cat, st))].append((lv, r["eff_net"]))
    for k, v in by.items():
        v.sort(); best = 0
        for lv, e in v:
            if best and e < best * 0.98:
                n += 1
            best = max(best, e)
    return n


def main():
    apply_ = "--apply" in sys.argv
    tgt = targets()
    cur = {k: dict(v[1]) for k, v in tgt.items()}
    sel = ledger(cur)
    print(f"시작 — 대상 {len(cur)}종 · 계열 내 역전 {inversions(sel, tgt)}건")

    for _ in range(24):
        sel = ledger(cur)
        lad = {}
        for (cat, name), (lv, st, _g) in tgt.items():
            r = sel.get(name)
            if r and r["eff_net"] > 0:
                lad.setdefault((cat, line_of(cat, st)), []).append((lv, r["eff_net"]))
        lad = {k: fit(v) for k, v in lad.items()}
        moved = 0
        for (cat, name), stats in cur.items():
            lv, s0, grade = tgt[(cat, name)]
            r = sel.get(name)
            if not r or r["eff_net"] <= 0:
                continue
            want = lad.get((cat, line_of(cat, s0)), {}).get(lv)
            if not want or abs(r["eff_net"] / want - 1) <= BAND_OK * 0.6:
                continue
            frozen = FROZEN | (FROZEN_SPEAR if cat == "작살" else set())
            # 문자열 값(등급특화:C:50 같은 특수 축)은 스케일 대상이 아니다 — 보존만 한다.
            adj = [s for s in stats if s not in frozen and isinstance(stats[s], int)]
            if not adj:
                continue
            V = PL._SV[IL.STAGE_OF_LEVEL(lv)]

            def _val(s):
                for tbl in (IL.STAT_KEY, IL.GROWTH_KEY, IL.GATE_KEY):
                    if s in tbl:
                        return V.get(tbl[s], 0.0)
                return 0.0
            part = sum(stats[s] * _val(s) for s in adj)
            if part <= 0:
                continue
            f = max(0.5, min(2.5, (want - (r["eff_net"] - part)) / part))
            new = dict(stats)
            for s in adj:
                v = int(round(stats[s] * f))
                # ★원본 대비 누적 이동 제한 — 라운드마다 배율이 곱해지는 걸 막는다.
                lo = max(MINV[s], int(round(s0.get(s, v) * MOVE_LO)))
                hi = max(lo, int(round(s0.get(s, v) * MOVE_HI)))
                new[s] = max(lo, min(hi, min(cap_for(grade, s), max(MINV[s], v))))
            if new != stats:
                cur[(cat, name)] = new
                moved += 1
        if not moved:
            break

    sel = ledger(cur)
    print(f"튜닝 후 — 계열 내 역전 {inversions(sel, tgt)}건")
    diff = [(c, n, fmt(tgt[(c, n)][1]), fmt(v)) for (c, n), v in cur.items()
            if fmt(v) != fmt(tgt[(c, n)][1])]
    print(f"수치 변경 {len(diff)}종")
    for c, n, a, b in diff[:12]:
        print(f"   {c:<4}{n:<16} {a}\n   {'':4}{'':16}→ {b}")
    if not apply_:
        print("\n[dry-run] --apply 로 반영")
        return
    P = json.load(open(os.path.join(BASE, "parts.json"), encoding="utf-8"))
    for (cat, name), st in cur.items():
        f = P["parts"][cat][name].split("|")
        f[4] = fmt(st)
        P["parts"][cat][name] = "|".join(f)
    json.dump(P, open(os.path.join(BASE, "parts.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n✅ parts.json 반영 {len(diff)}종")


if __name__ == "__main__":
    main()
