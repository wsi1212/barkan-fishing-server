#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""강화표 전면 재생성 + 숙련 계열 부품 신설 + 난이도 3층 예산 반영 (2026-08-27).

산출 권위는 `.claude/skills/balance-audit/scripts/` 의 두 모듈이다 —
`enhance_lines.py`(강화표·난이도 3층 예산) · `rod_lines.py`(낚싯대 라인·회수시간).
**이 파일은 그 산출의 적용기**이고, 수치를 바꿀 땐 저 모듈을 고쳐 다시 뽑는다.

────────────────────────────────────────────────────────────────────────────
① 강화 시스템 — 유저 지적이 맞았고 실태는 더 나빴다
────────────────────────────────────────────────────────────────────────────
"강화했을 때 지금 다 똑같은 스탯이 올라가는 것 같던데"

라이브 90개 표 전수 조사:
  · **주스탯 칸이 빈 표가 30개 이상** — A급 대부분(왕실·근위·왕립순찰·열사·오아시스·
    교역로·고고학자·정밀·감별사·무역상·회계사·사구·전갈·행렬·유목민…)이 15강 전체에서
    `행운 9 · 난이도 3` 동일. 실제로 «다 똑같은 스탯»이었다.
  · **강화가 라인을 배신** — 대나무(행운형)→경험치 42 · 참나무(숙련형)→경험치 62 ·
    전문가(숙련형)→크리확률 27 · 흑단목→크기 110.
  · **채집형이 난이도를 받음** — 매 레벨 `난이도:1` 이라 +13강이면 난이도 13.
    「채집형 난이도 0」 설계를 강화가 통째로 무효화했다.
    `채집용 낚싯대 +8` = `난이도:1,행운:1,난이도:1` (한 줄에 같은 키 둘, 뒤가 앞을 덮음).
  · **고아 16 / 누락 2** — parts.json 에 없는 표 16개. 표 없는 잠수부 낚싯대 2종은
    EnhanceLoader 폴백(`난이도:1,크기:2,크리확률:1`)을 타서 레벨만큼 난이도를 받았다.
  · **주스탯 배수 2.3~12배** — 바르칸 더블찬스 9 → +110.
  · **빈 레벨** — 강화했는데 아무것도 안 오르는 레벨이 다수.

⇒ 76종(= parts.json 낚싯대 전수) 표를 라인 기반으로 재생성. 고아 16개 삭제, 누락 2종 생성.
  레벨마다 반드시 1개 이상 오른다. 재료확률도 강화 대상에 편입(Java 배열 index 10 신설).

────────────────────────────────────────────────────────────────────────────
② 난이도 3층 예산 — 유저 제약 두 개를 동시에 만족시킨다
────────────────────────────────────────────────────────────────────────────
제약 A: "아무리 숙련 계열이여도 1강마다 -1씩 되면 큰일남. 그러면 C급 풀강이 S급보다
        쎄잖아. 강화로 C→S는 너무 과하지. 잘해야 C풀강 >= B 중반 강화 >= A기본"
제약 B: "C풀강 + 숙련계열 부품 C 올장착 정도면 S 순간이동은 안하도록. B풀강 + 숙련
        부품이면 훨씬 쉽고"

두 제약이 «강화만으로는 안 되고, 부품이 나머지를 대야 한다»를 강제한다. 그래서 3층:

    ① 낚싯대 기본  숙련 D2/C3/B4/A5/S6 · 혼합 D2/C3/B3/A3/S4 · 기타 D1/C2/B2/A3/S4 · 채집 0
    ② 강화 총량    숙련 D1/C2/B3/A4/S5 · 혼합 D1/C1/B2/A2/S3 · 기타 D0/C1/B2/A2/S3 · 채집 0
    ③ 숙련 부품    E0/D1/C1/B1/A2/S2 × 릴·줄·바늘·찌 4슬롯

검증 (순간이동 = zoneWidth<1, 캘리브레이션과 무관한 구조 지표):
    C 숙련 풀강 + C 숙련부품   3+2+4 =  9  → S   0.0% · M 100%   ★목표 달성
    B 숙련 풀강 + B 숙련부품   4+3+4 = 11  → S   0.0% · M  67.9% ★«훨씬 쉬움»
    C 숙련 풀강 + 일반부품     3+2+0 =  5  → S  41.8%
    C 일반 풀강 + 일반부품     2+1+0 =  3  → S  73.7%
    B 채집 풀강 + B 숙련부품   0+0+4 =  4  → S  57.5%
사다리: 숙련 C풀강 5 = B중반 5 = A기본 5 ✓ / 혼합 4·4·3 ✓ / 기타 3·3·3 ✓ / 채집 0 ✓

────────────────────────────────────────────────────────────────────────────
③ 숙련 계열 부품 — 새 아이템을 만들지 않는다
────────────────────────────────────────────────────────────────────────────
부품 100종 중 난이도를 주는 것이 **0종**이었다. 그래서 제약 B 가 데이터상 불가능했다.

슬롯 주스탯은 잘 서 있다(23~24/25 커버리지): 릴=경험치 · 줄=도망감소 ·
바늘=크리배율+크리확률 · 찌=등급업 · 미끼=행운. 계열 부스탯도 이미 일관됐다 —
채집(재확+경험치) · 행운(등급업) · 상인(판매+더블) · 크리(크리확률+크기) ·
성장(경험치+트리플). **딱 숙련 계열만 없었다.**

각 슬롯의 «군더더기 없는 기본형» 시리즈에 난이도를 부스탯으로 준다(D/C/B).
새 아이템·레시피·상점 항목을 늘리지 않는다. 잠수상점(P 통화)은 제외 — 돈 경제를 우회한다.
가격은 **추가한 가치만큼만** 올린다(난이도 1점의 원/h × 목표 회수시간). 목표 회수로
역산하면 릴 3종이 6.8배로 뛰는데, 그건 난이도를 얹어서가 아니라 릴 슬롯이 원래 싸기
때문(회수 중위 6.6h)이고 같은 시리즈의 나머지 19종과 역전이 생긴다.

★**줄은 가격을 올리지 않는다.** 줄 슬롯은 회수 중위 19.7h 로 홀로 무너져 있다
(릴 6.6 · 바늘 9.5 · 찌 11.8, 재료원은 4슬롯 동일 213,427원). 원인은 도망감소가
**B등급 전용 스탯**이라는 것 — 0→80 이 B 를 69%→100% 로 올리지만 A +5%p · S +2%p 뿐이고
80 에서 포화한다. 존폭 1~2칸인 A/S 에서는 도주율을 낮춰도 계속 미스해 escapeInc 가
100 까지 밀어올린다. 즉 도망감소는 난이도의 대체재가 아니다. 수치를 3배로 올려도
해결되지 않고 남은 처방은 **줄 레시피 원가 인하**뿐이다(별건 — 원가는 전 슬롯·낚싯대의
재료 게이트를 공유해 건드리면 방금 맞춘 회수시간이 전부 흔들린다).

사용:
    python3 patch_enhance_and_skill_parts.py <BlockShip 데이터 폴더> [--apply]
"""
import importlib.util, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(os.path.dirname(HERE), ".claude", "skills", "balance-audit", "scripts")

STAT_ORDER = ["난이도", "도망감소", "크리배율", "등급업", "크리확률", "크기", "경험치",
              "판매보너스", "더블찬스", "트리플찬스", "행운", "재료확률", "등급특화"]

# ── rod_lines.py --tune --plan 산출 ────────────────────────────────────────
ROD_PLAN = {
    "나뭇가지":           ("행운:1", None),
    "초보자 낚싯대":       ("경험치:3", None),
    "초보 낚싯대":         ("크리확률:2,크기:3", None),
    "튼튼한 막대기":       ("난이도:2,도망감소:3,경험치:2", 8700),
    "참나무 낚싯대":       ("난이도:3,도망감소:4,경험치:2", 48200),
    "전문가 낚싯대":       ("난이도:4,도망감소:8,경험치:4", 52300),
    "낚시견습생의 낚싯대":  ("난이도:1,크리확률:7,크기:11", None),
    "낚시꾼의 낚싯대":     ("난이도:2,크리확률:8,크기:11", None),
    "예리한 낚싯대":       ("난이도:2,크리배율:2,크리확률:11,크기:15", None),
    "대나무 막대기":       ("난이도:1,등급업:3,행운:11", None),
    "잉어꾼의 낚싯대":     ("난이도:2,등급업:5,행운:13,등급특화:C:50", None),
    "숙련자의 낚싯대":     ("난이도:2,등급업:8,행운:17", None),
    "장터 낚싯대":         ("난이도:1,판매보너스:8,더블찬스:3", None),
    "장사꾼의 낚싯대":     ("난이도:2,판매보너스:6,더블찬스:2", None),
    "거래상의 낚싯대":     ("난이도:2,판매보너스:17,더블찬스:7", None),
    "수련생 낚싯대":       ("난이도:1,경험치:8,트리플찬스:1", None),
    "경험의 낚싯대":       ("난이도:2,경험치:6,트리플찬스:1", None),
    "학도의 낚싯대":       ("난이도:2,경험치:17,트리플찬스:2", None),
    "다목적 낚싯대":       ("난이도:3,도망감소:3,판매보너스:5,더블찬스:2", 84500),
    "겸업 낚싯대":         ("난이도:2,등급업:5,크리확률:8,크기:14", None),
    "만능 낚싯대":         ("난이도:3,도망감소:5,판매보너스:9,더블찬스:4", 64300),
    "채집용 낚싯대":       ("경험치:3,재료확률:10", None),
    "수집가의 낚싯대":     ("경험치:5,재료확률:19", None),
    "탐사자의 낚싯대":     ("경험치:7,재료확률:28", None),
}
#: 숙련 계열 부품 — 이름: (슬롯, 난이도, 새 돈가격|None=유지)
PART_PLAN = {
    "나무 릴":      ("릴", 1, 26900),
    "철제 릴":      ("릴", 1, 48700),
    "전술 릴":      ("릴", 1, 97600),
    "면줄":        ("줄", 1, None),
    "나일론줄":      ("줄", 1, None),
    "카본줄":       ("줄", 1, None),
    "철 바늘":      ("바늘", 1, 19900),
    "날카로운 바늘":  ("바늘", 1, 29700),
    "미늘 바늘":     ("바늘", 1, 67600),
    "코르크 찌":     ("찌", 1, 19900),
    "가벼운 찌":     ("찌", 1, 29700),
    "전자 찌":      ("찌", 1, 67600),
}
#: 스폰마을 밖 낚싯대의 기본 난이도도 3층 예산에 맞춘다(라인 밸런스는 건드리지 않는다 —
#  사막·상단·왕도·히든은 아직 감사하지 않았다. 난이도만 예산표로 정렬한다).
FORAGE = {"채집용 낚싯대", "수집가의 낚싯대", "탐사자의 낚싯대", "발굴자의 낚싯대",
          "유물사냥꾼의 낚싯대", "수집상의 낚싯대", "탐구자의 낚싯대",
          "발굴왕의 낚싯대", "수집왕의 낚싯대"}


def load_mod(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SKILL, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    saved, sys.argv = sys.argv, [name]
    spec.loader.exec_module(mod)
    sys.argv = saved
    return mod


def canon(stat):
    d, extra = {}, []
    for t in stat.split(","):
        if ":" not in t:
            continue
        k, v = t.split(":", 1)
        d[k] = v
        if k not in STAT_ORDER:
            extra.append(k)
    return ",".join(f"{k}:{d[k]}" for k in STAT_ORDER + extra if k in d)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src, apply_ = sys.argv[1], "--apply" in sys.argv
    os.environ["BLOCKSHIP_DATA"] = src
    EL = load_mod("enhance_lines")

    pp = os.path.join(src, "parts.json")
    P = json.load(open(pp, encoding="utf-8"))
    rods = P["parts"]["낚싯대"]

    # ═══ 1. 스폰마을 낚싯대 24종 ═══
    log = []
    for name, (stat, price) in ROD_PLAN.items():
        f = rods[name].split("|")
        new, old = canon(stat), f[4]
        oldp = f[2]
        if price is not None:
            f[2] = str(price)
        if new == old and f[2] == oldp:
            continue
        if name in FORAGE and "재료확률" not in new:
            sys.exit(f"❌ {name}: 재료확률 소실 — is_external 보호를 잃는다")
        f[4] = new
        rods[name] = "|".join(f)
        log.append((name, old, new, oldp, f[2]))
    print(f"[낚싯대] 스폰마을 {len(log)}종")
    for n, a, b, pa, pb in log:
        pr = "" if pa == pb else f"   가격 {int(pa):,} → {int(pb):,}"
        print(f"  · {n:<20} {a}\n     → {b}{pr}")

    # ═══ 2. 스폰마을 밖 낚싯대 — 난이도만 3층 예산으로 정렬 ═══
    dlog = []
    for name, raw in list(rods.items()):
        if name in ROD_PLAN:
            continue
        f = raw.split("|")
        base = EL.parse_stats(f[4])
        line = EL.line_of(base, f[1])
        dk = EL.diff_key(line, base, f[1])
        want = EL.ROD_DIFF[dk].get(f[1], 0)
        cur = int(base.get("난이도", 0))
        if cur == want:
            continue
        d = {k: v for k, v in (x.split(":", 1) for x in f[4].split(",") if ":" in x)}
        if want > 0:
            d["난이도"] = str(want)
        else:
            d.pop("난이도", None)
        f[4] = canon(",".join(f"{k}:{v}" for k, v in d.items()))
        rods[name] = "|".join(f)
        dlog.append((name, f[1], line, dk, cur, want))
    print(f"\n[낚싯대] 스폰마을 밖 난이도 정렬 {len(dlog)}종")
    for n, g, line, dk, a, b in dlog:
        print(f"  · {n:<20} [{g}] {line}/{dk}  난이도 {a} → {b}")

    # ═══ 3. 숙련 계열 부품 12종 ═══
    plog = []
    for pname, (slot, dv, price) in PART_PLAN.items():
        f = P["parts"][slot][pname].split("|")
        d = {k: v for k, v in (x.split(":", 1) for x in f[4].split(",") if ":" in x)}
        old, oldp = f[4], f[2]
        d["난이도"] = str(dv)
        f[4] = canon(",".join(f"{k}:{v}" for k, v in d.items()))
        if price is not None:
            f[2] = str(price)
        if f[4] == old and f[2] == oldp:
            continue
        P["parts"][slot][pname] = "|".join(f)
        plog.append((slot, pname, old, f[4], oldp, f[2]))
    print(f"\n[부품] 숙련 계열 {len(plog)}종")
    for slot, n, a, b, pa, pb in plog:
        pr = "" if pa == pb else f"   가격 {int(pa):,} → {int(pb):,}"
        print(f"  · {slot} {n:<14} {a}\n     → {b}{pr}")

    # ═══ 4. 강화표 전면 재생성 ═══
    if apply_:                              # 낚싯대 변경 후의 스탯으로 표를 뽑아야 한다
        shutil.copy(pp, pp + ".bak-enh")
        json.dump(P, open(pp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    EL2 = load_mod("enhance_lines")         # 갱신된 parts.json 재적재
    table, meta = EL2.generate()
    ep = os.path.join(src, "enhance.json")
    E = json.load(open(ep, encoding="utf-8"))
    old_names = set(E["table"])
    orphan = sorted(old_names - set(table))
    added = sorted(set(table) - old_names)
    print(f"\n[강화표] {len(E['table'])}개 → {len(table)}개")
    print(f"  고아 삭제 {len(orphan)}: {orphan}")
    print(f"  누락 생성 {len(added)}: {added}")
    empty = [(n, l) for n, e in table.items() for l, v in e["levels"].items() if not v]
    if empty:
        sys.exit(f"❌ 빈 레벨 {len(empty)}건: {empty[:5]}")
    leak = [n for n, m in meta.items()
            if m[2] == "채집" and EL2.cum(table[n]["levels"], m[5]).get("난이도", 0) > 0]
    if leak:
        sys.exit(f"❌ 채집형 난이도 누출: {leak}")
    print("  🟢 빈 레벨 0 · 채집형 난이도 누출 0")
    for n in ("참나무 낚싯대", "전문가 낚싯대", "탐사자의 낚싯대", "거래상의 낚싯대"):
        c = EL2.cum(table[n]["levels"], table[n]["max"])
        print(f"  예시 {n:<14} 풀강 누적: "
              + ",".join(f"{k}:{int(v)}" for k, v in c.most_common()))

    if not apply_:
        print("\n[dry-run] --apply 로 실제 반영")
        return
    shutil.copy(ep, ep + ".bak-enh")
    E["table"] = table
    E["order"] = sorted(table)
    json.dump(E, open(ep, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n✅ parts.json · enhance.json 반영 (백업 *.bak-enh)")
    print("   ★jar 도 함께 바뀐다(강화 배열에 재료확률 편입) — 서버 풀 재시작 필수")


if __name__ == "__main__":
    main()
