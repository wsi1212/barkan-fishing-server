#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S 등급 복원 — 마을 종결 작살 5종 + 히든 종결 낚싯대 6종을 A → S 로 승격한다.

    python3 patch_grade_promote_s.py <BlockShip 데이터 폴더> [--apply]

────────────────────────────────────────────────────────────────────────────
왜 이 스크립트가 있나 (2026-09-06)
────────────────────────────────────────────────────────────────────────────
2026-08-02 까지 왕도에는 **S 작살 5종**(왕실 은총·왕립 급습·심해 원정·왕실 예장·
근위대, 전부 Lv60)이 있었다. 08-03 작살 생성기 도입이 이들을 A 로 강등했고,
08-04 커밋 ccdb2e39 「창↔낚싯대 시리즈명 통일」이 4줄을 2줄로 줄이면서
**왕립 급습·심해 원정은 대체 이름 없이 소실**됐다(커밋 메시지에 언급 없음).

그 뒤 라이브의 등급 분포는 이렇게 됐다:

    작살   A 23종(Lv30~61) · S 5종 = 히든-전설 2 + 심해 3   → 마을 라인 S 0종
    낚싯대 A 41종           · S 2종 = 히든-전설 2            → 상점·수집 라인 S 0종
    부품   슬롯마다 S 10종씩(히든-마을 6 + 심해 2 + 전설 2)  ← 여기만 S 가 살아 있다

즉 **한 세트 안에서 낚싯대는 A 인데 릴·줄·바늘·미끼·찌는 S** 인 기형이 굳었다.
시리즈명은 이미 짝이 맞아 있다(여명 릴 S ↔ 여명의 낚싯대 A) — 등급만 어긋났다.

★**생성기를 고쳐 재생성하는 경로는 쓸 수 없다.** gen_spear_builds.py 를 지금
  라이브에 돌리면 67종 → 55종이 되고(관통·기사단·세관·수집·심해 잠수부·장터·
  적재상의·전령·조병창·창병·채집·탐사 작살이 사라진다) 남는 55종도 전부 값이
  달라진다 — 08-26~09-01 의 패치 레이어(patch_spear_lines·patch_wangdo_b·
  patch_line_fill·patch_cast_cost)가 라이브를 다시 썼고 생성기는 그 이전 세대에
  멈춰 있기 때문이다. 그래서 최소 변경 패치로 간다.

무엇을 바꾸나 / 안 바꾸나
────────────────────────────────────────────────────────────────────────────
  바꾼다 : 등급 A → S · 내구도를 그 카테고리 S 기준으로
  안 바꾼다 : 가격 · 레벨제한 · 스탯 · 레시피 재료

★재료(=요구 캐스트, κ)를 그대로 두는 건 **유저 결정**이다(2026-09-06).
  결과적으로 이 11종은 «A 재료로 만드는 S» 가 되어 κ 가 좋아진다 — S 가
  「종수도 적고 만들 이유도 없는」 등급이던 문제를 푸는 게 목적이므로 의도한 방향이다.
  (라이브 κ 실측: 낚싯대 A 20.7 → S 104.7 · 작살 A 7.0 → S 21.0. 설계 슬로프는
   등급당 ×1.15 이므로 S 가 설계선을 3~5배 초과한다.)

★상점 천장과 한 묶음이다. `PartShopGui.shopCeilingBlocks` 가 «마을 출처 S» 를
  예외로 통과시키도록 같이 고쳤다 — 안 그러면 이 상점이 레시피 판매도 겸하므로
  왕도 작살 5종이 노출·해금 양쪽에서 막혀 **획득 불가**가 된다. jar 과 데이터를
  같이 배포할 것.
"""
import json, shutil, sys, pathlib, datetime

#: 승격 대상 — 카테고리 → 이름 목록.
#  작살: 왕도 종결 5종(옛 왕도 S 라인의 후신 — 왕실 은총→왕실, 근위대→근위).
#  낚싯대: 부품 S 와 **시리즈명이 이미 짝인** 6종. 릴·줄·바늘·미끼·찌가 전부 S 인
#          여명/등대/전갈왕/모래폭풍/감정왕/대상인 계열의 낚싯대만 A 로 남아 있었다.
PROMOTE = {
    "작살": ["왕실 작살", "근위 작살", "왕도 상회 작살", "왕립 서고 작살", "왕립 순찰 작살"],
    "낚싯대": ["여명의 낚싯대", "등대지기의 낚싯대", "전갈왕의 낚싯대",
               "모래폭풍의 낚싯대", "감정왕의 낚싯대", "대상인의 낚싯대"],
}

#: 카테고리별 S 내구도 — gen_*_builds.py 의 DURAB 표와 같은 값이어야 한다.
DURAB_S = {"작살": 420, "낚싯대": 800}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = pathlib.Path(sys.argv[1])
    apply_ = "--apply" in sys.argv
    pf = src / "parts.json"
    data = json.loads(pf.read_text(encoding="utf-8"))
    parts = data["parts"]

    changes, errors = [], []
    for cat, names in PROMOTE.items():
        table = parts.get(cat)
        if table is None:
            errors.append(f"{cat}: parts.json 에 카테고리가 없다")
            continue
        for name in names:
            raw = table.get(name)
            if raw is None:
                errors.append(f"{cat}/{name}: 없는 이름 — 개명·삭제됐는지 확인할 것")
                continue
            f = raw.split("|")
            if len(f) < 7:
                errors.append(f"{cat}/{name}: 필드 {len(f)}개 (7개여야 함)")
                continue
            if f[1] == "S":
                changes.append((cat, name, raw, raw, "이미 S — 건너뜀"))
                continue
            if f[1] != "A":
                errors.append(f"{cat}/{name}: 등급이 {f[1]} — A 만 승격한다")
                continue
            new = list(f)
            new[1] = "S"
            new[3] = str(DURAB_S[cat])
            changes.append((cat, name, raw, "|".join(new),
                            f"A→S · 내구 {f[3]}→{DURAB_S[cat]}"))
            table[name] = "|".join(new)

    for cat, name, before, after, note in changes:
        print(f"  {cat:4} {name:16} {note}")
        if before != after:
            print(f"       before: {before}")
            print(f"       after : {after}")
    if errors:
        print("\n❌ 오류 — 쓰지 않고 멈춘다")
        for e in errors:
            print("   ·", e)
        sys.exit(1)

    done = [c for c in changes if c[2] != c[3]]
    print(f"\n승격 {len(done)}종 (작살 {sum(1 for c in done if c[0]=='작살')} · "
          f"낚싯대 {sum(1 for c in done if c[0]=='낚싯대')})")
    if not apply_:
        print("[dry-run] --apply 로 실제 반영")
        return
    if not done:
        print("변경 없음 — 쓰지 않는다")
        return

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = pf.with_suffix(f".json.bak-promote-s-{ts}")
    shutil.copy2(pf, bak)
    pf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {pf} 반영 (백업 {bak.name})")


if __name__ == "__main__":
    main()
