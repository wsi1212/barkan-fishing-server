#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""창(작살) 빌드 다양화 — parts.json / recipes.json 생성기.

낚싯대와 같은 방식으로 마을별 작살 라인업을 만든다.
  - 빌드 5종(주력 + 전용 보상 스탯):
      행운형 = 행운 + 판매보너스 / 속도형 = 수영속도·돌진쿨감 + 경험치 / 호흡형 = 수중호흡 + 더블찬스
      크리형 = 크리확률·크리배율 + 크기 / 공격형 = 공격력·공격속도 + 트리플찬스(A부터)
  - ★수중호흡은 빌드와 무관하게 등급 하한 보장(E5 D8 C10 B13 A15 S18 …) — 코드(HarpoonManager.breathFloor)가
    강제하지만 데이터도 하한 이상으로 적어 로어·표를 일치시킨다
  - 마을별 티어: 스폰(C Lv10, B Lv25) / 상단(A Lv40, 균형형) / 사막(A Lv45, 극단형) / 왕도(S Lv60)
  - 가격·레벨·등급은 그 마을 낚싯대와 맞춤 (스폰 C 2000~2800, B 9500~10000, 상단 21000, 사막 22000, 전설 72000~76500)

입력/출력은 인자로 받은 디렉터리의 parts.json / recipes.json (제자리 갱신, .bak 생성).
"""
import json, shutil, sys, os

SRC = sys.argv[1]

# ── 작살 카탈로그 ────────────────────────────────────────────────────────────
# (이름, 등급, 가격, 내구, 스탯, 레벨제한, 출처, 마을(레시피 소속), 빌드재료)
SPEARS = [
    # ═══ 스폰마을 1차 — C등급 Lv10 (스폰마을 C 낚싯대 2000~2800원과 동급) ═══
    ("물때 작살",     "C",  2400, 110, "행운:6,판매보너스:3,수중호흡:12,수영속도:8,공격력:2",                 10, "스폰마을", "스폰", ("행운의구슬", 6)),
    ("여울 작살",     "C",  2400, 110, "수영속도:22,돌진쿨감:12,경험치:12,수중호흡:10,공격력:2",              10, "스폰마을", "스폰", ("거대비늘", 5)),
    ("해녀 작살",     "C",  2500, 120, "수중호흡:26,더블찬스:2,수영속도:6,공격력:2",                          10, "스폰마을", "스폰", ("진주", 8)),
    ("벼린 작살",     "C",  2600, 110, "크리확률:9,크리배율:1,크기:3,수중호흡:10,수영속도:6,공격력:2",        10, "스폰마을", "스폰", ("안개수정", 6)),
    ("쇠날 작살",     "C",  2600, 120, "공격력:3,공격속도:18,수중호흡:10,수영속도:5",                         10, "스폰마을", "스폰", ("강화철괴", 8)),

    # ═══ 스폰마을 2차 — B등급 Lv25 (스폰마을 B 낚싯대 9500~10000원과 동급) ═══
    ("만조 작살",     "B",  9600, 170, "행운:10,판매보너스:6,수중호흡:18,수영속도:12,공격력:2",               25, "스폰마을", "스폰", ("행운의구슬", 16)),
    ("조류 작살",     "B",  9600, 170, "수영속도:33,돌진쿨감:20,경험치:22,수중호흡:14,공격력:2",              25, "스폰마을", "스폰", ("거대비늘", 14)),
    ("잠수부 작살",   "B",  9800, 180, "수중호흡:38,더블찬스:3,수영속도:10,공격력:2",                         25, "스폰마을", "스폰", ("진주", 20)),
    ("예봉 작살",     "B", 10000, 170, "크리확률:14,크리배율:2,크기:5,수중호흡:14,수영속도:9,공격력:2",       25, "스폰마을", "스폰", ("안개수정", 16)),
    ("강철날 작살",   "B", 10000, 180, "공격력:4,공격속도:24,수중호흡:14,수영속도:8",                         25, "스폰마을", "스폰", ("강화철괴", 20)),

    # ═══ 상단마을 — A등급 Lv40 (흑단목 낚싯대 21000원과 동급). 균형형: 주력 낮고 보조 두껍다 ═══
    ("행상인의 작살", "A", 21000, 240, "행운:12,판매보너스:12,수중호흡:28,수영속도:20,공격력:3",              40, "상단마을", "상단", ("행운의매듭", 8)),
    ("쾌속선 작살",   "A", 21000, 240, "수영속도:38,돌진쿨감:26,경험치:30,수중호흡:22,공격력:3",              40, "상단마을", "상단", ("거대비늘", 26)),
    ("심해교역 작살", "A", 21500, 250, "수중호흡:46,더블찬스:4,판매보너스:6,수영속도:18,공격력:3",            40, "상단마을", "상단", ("진주코어", 8)),
    ("세공사의 작살", "A", 22000, 240, "크리확률:17,크리배율:3,크기:8,수중호흡:22,수영속도:15,공격력:3",      40, "상단마을", "상단", ("자수정", 20)),
    ("호위대 작살",   "A", 22000, 250, "공격력:5,공격속도:28,트리플찬스:1,수중호흡:22,수영속도:14",           40, "상단마을", "상단", ("강화철괴", 40)),

    # ═══ 사막마을 — A등급 Lv45 (사막 낚싯대 22000원과 동급). 극단형: 주력 높고 보조 얇다 ═══
    ("신기루 작살",     "A", 22500, 250, "행운:18,판매보너스:8,수중호흡:16,수영속도:10,공격력:3",             45, "사막마을", "사막", ("행운의매듭", 10)),
    ("모래바람 작살",   "A", 22500, 250, "수영속도:52,돌진쿨감:36,경험치:40,수중호흡:15,공격력:3",            45, "사막마을", "사막", ("거대비늘", 30)),
    ("오아시스 작살",   "A", 23000, 260, "수중호흡:64,더블찬스:6,수영속도:8,공격력:3",                        45, "사막마을", "사막", ("진주코어", 10)),
    ("전갈 작살",       "A", 23500, 250, "크리확률:26,크리배율:4,크기:12,수중호흡:15,수영속도:8,공격력:3",    45, "사막마을", "사막", ("자수정", 26)),
    ("사막군주의 작살", "A", 23500, 260, "공격력:5,공격속도:42,트리플찬스:2,수중호흡:15,수영속도:8",          45, "사막마을", "사막", ("강화철괴", 46)),

    # ═══ 왕도 — S등급 Lv60 (전설 낚싯대 72000~76500원과 동급, 상점 미판매 대신 왕도 대장간 제작) ═══
    ("왕실 은총 작살", "S", 70000, 400, "행운:24,판매보너스:18,수중호흡:36,수영속도:26,공격력:4",             60, "왕도", "왕도", ("행운의매듭", 20)),
    ("왕립 급습 작살", "S", 70000, 400, "수영속도:60,돌진쿨감:48,경험치:60,수중호흡:28,공격력:4",             60, "왕도", "왕도", ("거대비늘", 56)),
    ("심해 원정 작살", "S", 71000, 420, "수중호흡:80,더블찬스:8,판매보너스:8,수영속도:24,공격력:4",           60, "왕도", "왕도", ("진주코어", 20)),
    ("왕실 예장 작살", "S", 72000, 400, "크리확률:30,크리배율:6,크기:16,수중호흡:28,수영속도:20,공격력:4",    60, "왕도", "왕도", ("자수정", 48)),
    ("근위대 작살",    "S", 72000, 420, "공격력:6,공격속도:52,트리플찬스:3,수중호흡:28,수영속도:20",          60, "왕도", "왕도", ("네더라이트주괴", 4)),
]

# 티어별 공통 재료 (빌드 재료는 위 카탈로그에서 개별 지정)
COMMON = {
    "C":  [("단단한자루", 4), ("강철심", 4), ("물고기비늘", 10)],
    "B":  [("단단한자루", 8), ("강철심", 12), ("진주", 10), ("압축흑정석", 4)],
    "A":  [("단단한자루", 16), ("강철심", 24), ("진주", 24), ("압축흑정석", 16)],
    "S":  [("단단한자루", 24), ("강철심", 44), ("별빛진주", 10), ("바르칸조각", 24), ("압축흑정석", 32)],
}
# 사막(A Lv45)은 상단(A Lv40)보다 한 급 더 든다
DESERT_MULT = 1.15

# 기존 중립 라인(철/강철/다이아/네더라이트) — 지금까지 제작·구매 경로가 없어 사실상 미획득 아이템이었다.
# 빌드 라인과 함께 조합대에 올려 작살 트리를 완성한다.
LEGACY_RECIPES = [
    ("HP30", "강철 작살", "",     [("단단한자루", 10), ("강철심", 20), ("강화철괴", 20), ("진주", 12)]),
    ("HP31", "다이아 작살", "왕도", [("단단한자루", 20), ("강철심", 40), ("강화다이아몬드", 24), ("별빛진주", 8), ("압축흑정석", 30)]),
    ("HP32", "네더라이트 작살", "", [("단단한자루", 32), ("네더라이트주괴", 8), ("강화네더라이트파편", 24), ("바르칸핵", 2), ("용비늘", 4), ("별빛진주", 24)]),
]


# 등급별 수중호흡 하한 — HarpoonManager.breathFloor와 반드시 같은 값이어야 한다.
BREATH_FLOOR = {"E": 5, "D": 8, "C": 10, "B": 13, "A": 15, "S": 18, "M": 20, "L": 22, "G": 25}


def check_breath_floor():
    """모든 작살이 등급 하한 이상의 수중호흡을 갖는지 검증 — 데이터와 코드 하한이 어긋나면 조기 실패."""
    for (name, grade, _p, _d, stats, *_rest) in SPEARS:
        got = 0
        for pair in stats.split(","):
            k, _, v = pair.partition(":")
            if k.strip() == "수중호흡":
                got = float(v)
        floor = BREATH_FLOOR[grade]
        if got < floor:
            raise SystemExit(f"{name}: 수중호흡 {got} < {grade}등급 하한 {floor}")


def merge(items):
    """같은 재료가 두 번 나오면 수량을 합쳐 한 줄로 — 조합대 재료 표시·소모 중복 방지."""
    out = []
    for it in items:
        for o in out:
            if o["typeOrMatId"] == it["typeOrMatId"]:
                o["qty"] += it["qty"]
                break
        else:
            out.append(it)
    return out


def main():
    check_breath_floor()
    parts_path = os.path.join(SRC, "parts.json")
    rec_path = os.path.join(SRC, "recipes.json")
    mat_path = os.path.join(SRC, "materials.json")
    mats = json.load(open(mat_path, encoding="utf-8"))["materials"]

    def ing(mat_id, qty):
        m = mats.get(mat_id)
        if m is None:
            raise SystemExit(f"materials.json에 없는 재료: {mat_id}")
        return {"kind": "custom", "typeOrMatId": mat_id, "displayName": m["name"],
                "mcItem": m["mcItem"], "qty": int(qty)}

    # ── parts.json ──
    P = json.load(open(parts_path, encoding="utf-8"))
    shutil.copy(parts_path, parts_path + ".bak-spearbuilds")
    order, parts = P["order"], P["parts"]
    existing = set(parts["작살"])
    added = 0
    for (name, grade, price, dur, stats, lv, origin, village, buildmat) in SPEARS:
        line = f"{name}|{grade}|{price}|{dur}|{stats}|{lv}|{origin}"
        parts["작살"][name] = line
        if name not in existing:
            order.append(["작살", name])
            added += 1
    json.dump(P, open(parts_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"parts.json: 작살 {added}종 추가 (총 {len(parts['작살'])}종)")

    # ── recipes.json ──
    R = json.load(open(rec_path, encoding="utf-8"))
    shutil.copy(rec_path, rec_path + ".bak-spearbuilds")
    recs, cats = R["recipes"], R["categories"]

    # 작살 카테고리 신설 + HP01(나무 작살)을 부품 → 작살로 이관
    cats.setdefault("작살", [])
    if "HP01" in cats.get("부품", []):
        cats["부품"].remove("HP01")
    if "HP01" in recs:
        recs["HP01"]["category"] = "작살"
    if "HP01" not in cats["작살"]:
        cats["작살"].append("HP01")

    def put(rid, display, part_name, village, ingredients):
        recs[rid] = {
            "id": rid, "category": "작살", "displayName": display,
            "locked": False, "resultMode": "part", "drillTier": 0,
            "village": village,
            "resultPartType": "작살", "resultPartName": part_name,
            "ingredients": ingredients,
        }
        if rid not in cats["작살"]:
            cats["작살"].append(rid)

    for i, (name, grade, price, dur, stats, lv, origin, village, buildmat) in enumerate(SPEARS):
        rid = f"HP{i + 2:02d}"                       # HP02 ~ HP26
        mult = DESERT_MULT if village == "사막" else 1.0
        items = [ing(mid, max(1, round(q * mult))) for mid, q in COMMON[grade]]
        items.insert(2, ing(buildmat[0], max(1, round(buildmat[1] * mult))))  # 빌드 재료를 눈에 띄게 앞쪽에
        items = merge(items)
        put(rid, name, name, village, items)

    for rid, name, village, ings in LEGACY_RECIPES:
        put(rid, name, name, village, [ing(m, q) for m, q in ings])

    json.dump(R, open(rec_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"recipes.json: 작살 카테고리 {len(cats['작살'])}개 레시피")


if __name__ == "__main__":
    main()
