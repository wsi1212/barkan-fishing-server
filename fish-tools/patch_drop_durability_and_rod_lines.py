#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""내구보존 스탯 전면 폐지 + 스폰마을 낚싯대 라인 재설계 (2026-08-27).

────────────────────────────────────────────────────────────────────────────
① 왜 내구보존을 지우는가
────────────────────────────────────────────────────────────────────────────
실측 정규화 가치가 **판매보너스 1% 기준 0.081(D) ~ 0.266(A)** 이다. 낚싯대 28종에
붙어 있었는데도 «있으나 없으나» 인 수치라, 라인 정체성만 흐리고 유저에게는 읽을
가치가 없는 줄이었다. 유지비(수리비)는 이제 스탯으로 깎이지 않는 고정비다.
  · Java 쪽은 `EquipmentManager.reduceDurability` 맨 앞의 «확률로 소모 전체 스킵»
    분기와 집계·GUI·강화 누적배열 슬롯까지 함께 제거했다(같은 커밋).
  · ★강화 누적배열이 11 → 10 칸으로 줄어 **행운 인덱스가 10 → 9** 로 앞당겨졌다.
    `EnhanceManager.STAT_LEN` · `StatsGui.EI` · `WorkbenchGui` 의 enh[...] 는 짝이다.

────────────────────────────────────────────────────────────────────────────
② 왜 난이도를 올리는가 — 유저 지시
────────────────────────────────────────────────────────────────────────────
"C낚싯대 풀강 + 부품 or B낚싯대 숙련 하위강 + 부품들이면 S급이 순간이동은 안되어야지"

순간이동은 감각이 아니라 **구조**다 — `MinigameTables.derive` 에서
    net = rodBonus − fishDifficulty(등급) − sizeDifficulty(cm)
    zoneWidth = 8 + floor(net/2)   → 1 미만이면 overflowDiff>0 = 존 순간이동
S(16) 기준 sizeDifficulty 는 fish.json 46종 균등롤 기대값 3.23 이고, 순간이동을
피하려면 `rodBonus ≥ 2 + sizeDiff` 다. 그래서 목표는 **rodBonus 9**(= S 전 크기대
순간이동 0%). 실측 모집단 평균 난이도는 1.81 이었다.

난이도는 «스탯 하나»가 아니다 — A 가 초반 매출의 29%, S 가 중반 매출의 28.6% 라
**고등급 포획 가능성 = 매출의 절반**을 난이도가 문지기로 쥐고 있다. 그래서 모든
라인에 난이도를 깔면 라인 정체성이 전부 «난이도 낚싯대 + 장식»으로 수렴한다
(실측: C 등급 상인형의 판매보너스가 6 → 2 까지 밀렸다). 결론:
  · **숙련형이 난이도 라인**이다 — D3 / C5 / B7, 강화표에 난이도를 증설해 «풀강/하위강»
    투자로 9 를 넘긴다. 그 대가로 돈가격을 올렸다(회수시간을 등급 중위에 고정).
  · 다른 라인은 난이도 1~2 만 얕게(정체성 스탯이 살아남는 상한). 혼합형만 3~4.
  · 채집형은 난이도 0 (유저 확정 — 「재료는 쏟아지지만 대물은 못 잡는다」).

검증(순간이동 비율):
    C 숙련 풀강  (참나무 +10) 5+6 = 11 →   0%
    B 숙련 하위강 (전문가 +5)  7+2 =  9 →   0%
    C 일반 풀강  (낚시꾼 +10) 2+2 =  4 →  57.5%
    B 혼합 풀강  (만능  +13) 4+3 =  7 →  20.1%
회수시간 편차: D 1.07배 · C 1.07배 · B 1.04배 (개편 전 1.9~2.3배)

산출 근거는 `.claude/skills/balance-audit` — `stat_value.diff_curve`(난이도 누적
가치곡선, 단가×점수 금지) · `item_ledger`(총비용/순성능/회수) · `minigame_sim`
(2026-08-27 MAX_ZONE_JUMP 라이브 동기화 + 크기난이도 가중).

사용:
    python3 patch_drop_durability_and_rod_lines.py <BlockShip 데이터 폴더> [--apply]
"""
import json, os, shutil, sys

STAT_ORDER = ["난이도", "도망감소", "크리배율", "등급업", "크리확률", "크기", "경험치",
              "판매보너스", "더블찬스", "트리플찬스", "행운", "재료확률", "등급특화"]

# ── 스폰마을 24종: 이름 → (새 스탯, 새 돈가격|None) ────────────────────────
#   라인 지도 — 숙련형 난이도(부: 도망감소·경험치) · 크리형 크기(부: 크리확률·크리배율)
#   · 행운형 행운(부: 등급업) · 상인형 판매보너스(부: 더블찬스) · 성장형 경험치(부:
#   트리플찬스) · 채집형 재료확률(부: 경험치, 난이도 0)
ROD_PLAN = {
    "나뭇가지":           ("행운:1", None),
    "초보자 낚싯대":       ("경험치:3", None),
    "초보 낚싯대":         ("크리확률:2,크기:3", None),
    "튼튼한 막대기":       ("난이도:3,도망감소:3,경험치:2", 35000),
    "참나무 낚싯대":       ("난이도:5,도망감소:4,경험치:2", 112000),
    "전문가 낚싯대":       ("난이도:7,도망감소:8,경험치:4", 130000),
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
    "다목적 낚싯대":       ("난이도:3,도망감소:3,판매보너스:5,더블찬스:2", 84000),
    "겸업 낚싯대":         ("난이도:2,등급업:5,크리확률:8,크기:14", None),
    "만능 낚싯대":         ("난이도:4,도망감소:5,판매보너스:9,더블찬스:4", 145000),
    "채집용 낚싯대":       ("경험치:3,재료확률:10", None),
    "수집가의 낚싯대":     ("경험치:5,재료확률:18", None),
    "탐사자의 낚싯대":     ("경험치:7,재료확률:28", None),
}
#: 재료확률이 반드시 남아야 하는 채집 라인 — 빠지면 `gen_rod_builds.is_external()`
#  보호를 잃어 생성기가 카탈로그로 되덮는다.
FORAGE = {"채집용 낚싯대", "수집가의 낚싯대", "탐사자의 낚싯대", "발굴자의 낚싯대",
          "유물사냥꾼의 낚싯대", "수집상의 낚싯대", "탐구자의 낚싯대",
          "발굴왕의 낚싯대", "수집왕의 낚싯대"}

# ── 스폰마을 밖 낚싯대: 내구보존을 «등가 도망감소»로 환산해 조용한 너프를 막는다 ──
#   환산율 0.74 = 내구보존 정규화 0.266(A) ÷ 도망감소 0.36. 사막·상단·왕도·히든은
#   아직 감사하지 않았으므로 «가치 보존»만 하고 라인 밸런스는 건드리지 않는다.
DUR_TO_ESCAPE = 0.74

# ── 숙련형 강화표에 난이도 증설 (기존 난이도 항목을 이 표로 «교체») ──────────
#   투자(강화)로 순간이동 문턱을 넘게 만드는 장치. 강화 비용은 원장 총비용에 안
#   들어가지만 유저에게는 실비용이다 — 그래서 기본값을 낮추고 여기로 옮겼다.
ENH_DIFF = {
    "튼튼한 막대기": {2: 1, 4: 1, 6: 1, 8: 1},                    # 풀강 +4 → rodBonus 7
    "참나무 낚싯대": {2: 1, 4: 1, 5: 1, 7: 1, 8: 1, 10: 1},        # 풀강 +6 → 11
    "전문가 낚싯대": {3: 1, 5: 1, 7: 1, 9: 1, 11: 1, 13: 1},       # +5 에서 +2 → 9
}


def canon(s):
    d, order = {}, []
    for t in s.split(","):
        if ":" not in t:
            continue
        k, v = t.split(":", 1)
        if k == "등급특화":            # 값이 "C:50" 이라 재분해되면 안 된다
            d[k] = v
        else:
            d[k] = v
        if k not in order:
            order.append(k)
    keys = [k for k in STAT_ORDER if k in d] + [k for k in order if k not in STAT_ORDER]
    return ",".join(f"{k}:{d[k]}" for k in keys)


def strip_dur(stat):
    """내구보존 제거. 스폰마을 밖이면 등가 도망감소로 환산해 합산."""
    keep, dur = [], 0
    i = 0
    parts = stat.split(",")
    while i < len(parts):
        t = parts[i]
        if t.startswith("등급특화:"):          # "등급특화:C:50" → 다음 조각까지 한 항목
            keep.append(t + ("," + parts[i + 1] if i + 1 < len(parts) and ":" not in parts[i + 1] else ""))
            i += 1
            continue
        if t.startswith("내구보존:"):
            try:
                dur = float(t.split(":", 1)[1])
            except ValueError:
                dur = 0
        else:
            keep.append(t)
        i += 1
    return ",".join(keep), dur


def add_stat(stat, key, amount):
    d = {}
    for t in stat.split(","):
        if ":" in t:
            k, v = t.split(":", 1)
            d[k] = v
    if amount <= 0:
        return stat
    try:
        d[key] = str(int(float(d.get(key, 0))) + int(amount))
    except ValueError:
        d[key] = str(int(amount))
    return ",".join(f"{k}:{v}" for k, v in d.items())


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src, apply_ = sys.argv[1], "--apply" in sys.argv
    changed_files = []

    # ═══ parts.json ═══
    pp = os.path.join(src, "parts.json")
    P = json.load(open(pp, encoding="utf-8"))
    log = []
    for cat, d in P["parts"].items():
        for name in list(d):
            f = d[name].split("|")
            old_stat, old_price = f[4], f[2]
            stat = old_stat
            if name in ROD_PLAN:
                new, price = ROD_PLAN[name]
                stat = canon(new)
                if price is not None:
                    f[2] = str(price)
            elif "내구보존" in stat:
                base, dur = strip_dur(stat)
                if name in FORAGE:
                    stat = canon(base)                      # 채집 라인은 부스탯만 남긴다
                else:
                    conv = int(round(dur * DUR_TO_ESCAPE))
                    stat = canon(add_stat(base, "도망감소", conv))
            if stat == old_stat and f[2] == old_price:
                continue
            if name in FORAGE and "재료확률" not in stat:
                sys.exit(f"❌ {name}: 재료확률이 사라졌다 — is_external 보호를 잃는다")
            if "내구보존" in stat:
                sys.exit(f"❌ {name}: 내구보존이 남아 있다")
            f[4] = stat
            d[name] = "|".join(f)
            log.append((cat, name, old_stat, stat, old_price, f[2]))
    print(f"[parts.json] {len(log)}종 변경")
    for cat, n, a, b, pa, pb in log:
        pr = "" if pa == pb else f"   가격 {int(pa):,} → {int(pb):,}"
        print(f"  · {n:<22} {a}\n     → {b}{pr}")

    # ═══ enhance.json ═══
    ep = os.path.join(src, "enhance.json")
    E = json.load(open(ep, encoding="utf-8"))
    elog = []
    for rod, ent in E["table"].items():
        lv = ent.get("levels") or {}
        add = ENH_DIFF.get(rod, {})
        for step, raw in list(lv.items()):
            keep, dur = [], 0.0
            for t in raw.split(","):
                if t.startswith("내구보존:"):
                    try:
                        dur += float(t.split(":", 1)[1])
                    except ValueError:
                        pass
                    continue
                if t.startswith("난이도:") and rod in ENH_DIFF:
                    continue                                # 증설표로 «교체»
                keep.append(t)
            n = int(step)
            if rod in ENH_DIFF and add.get(n):
                keep.append(f"난이도:{add[n]}")
            # 강화표의 내구보존도 등가 도망감소로 환산한다 — 안 하면 그 낚싯대의
            # 강화 보상이 통째로 빈 줄이 된다(견고한·수호자의 낚싯대가 그랬다).
            if dur > 0 and rod not in ENH_DIFF:
                conv = int(round(dur * DUR_TO_ESCAPE))
                if conv > 0:
                    keep.append(f"도망감소:{conv}")
            new = ",".join(x for x in keep if x)
            if new != raw:
                lv[step] = new
                elog.append((rod, step, raw, new))
    print(f"\n[enhance.json] {len(elog)}행 변경")
    for rod, step, a, b in elog:
        print(f"  · {rod} +{step:<3} {a or '(없음)'} → {b or '(없음)'}")

    # ═══ env-bonuses.json — 눈보라 ═══
    vp = os.path.join(src, "env-bonuses.json")
    V = json.load(open(vp, encoding="utf-8"))
    vlog = []
    for grp in V.values():
        if not isinstance(grp, dict):
            continue
        for key, bonus in grp.items():
            if isinstance(bonus, dict) and "내구보존" in bonus:
                dur = bonus.pop("내구보존")
                bonus["도망감소"] = bonus.get("도망감소", 0.0) + round(dur * DUR_TO_ESCAPE)
                vlog.append((key, dur, bonus["도망감소"]))
    for key, dur, esc in vlog:
        print(f"\n[env-bonuses.json] {key}: 내구보존 {dur:.0f} → 도망감소 {esc:.0f}")

    # ═══ item-flavor.json — 고아 항목 ═══
    ip = os.path.join(src, "item-flavor.json")
    F = json.load(open(ip, encoding="utf-8"))
    ilog = []

    def scrub(o):
        if isinstance(o, dict):
            for k in [k for k in o if "내구보존" in str(k)]:
                ilog.append(k)
                o.pop(k)
            for v in o.values():
                scrub(v)
    scrub(F)
    if ilog:
        print(f"\n[item-flavor.json] 고아 항목 제거: {', '.join(ilog)}")

    if not apply_:
        print("\n[dry-run] --apply 로 실제 반영")
        return
    for path, data, tag in ((pp, P, "parts"), (ep, E, "enhance"),
                            (vp, V, "env-bonuses"), (ip, F, "item-flavor")):
        shutil.copy(path, path + ".bak-nodur")
        json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        changed_files.append(os.path.basename(path))
    print(f"\n✅ 반영: {', '.join(changed_files)} (백업 *.bak-nodur)")
    print("   ★jar 도 같이 바뀐다 — 서버 풀 재시작 필요(/데이터리로드 만으로는 부족)")


if __name__ == "__main__":
    main()
