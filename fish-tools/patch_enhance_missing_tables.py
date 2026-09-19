#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""enhance.json 에 표가 «없는» 낚싯대를 채운다 (2026-09-19).

왜 필요한가 — 폴백이 조용히 쓰레기 스탯을 준다
────────────────────────────────────────────────────────────────────────────
`EnhanceLoader.getCumulativeStats` 는 표가 없는 낚싯대를 만나면 레벨마다
`난이도:1,크기:2,크리확률:1` (+짝수 등급업:1 · 5배수 행운:1) 을 준다. 에러도
경고도 없다. 그래서 **표가 빠진 낚싯대는 라인과 무관하게 난이도만 -N 씩 받는다** —
채집형(난이도 0 설계)이면 설계가 통째로 뒤집힌다.

2026-08-27 `patch_enhance_and_skill_parts.py` 가 이 사고를 한 번 청소했는데
(당시 누락 = 잠수부 2종), 같은 시기 `patch_wangdo_b.py`·`patch_line_fill.py` 가
신설한 **왕도 B 6종(방벽·사자·왕관·세관·문서고·조병창)** 은 그 뒤에 들어와
표가 없는 채로 남았다. 실측 제보: 「조병창 낚싯대 9강인데 난이도 -9」
— 폴백 계산 그대로다(조병창은 재료확률 41 짜리 **채집형**이라 난이도가 0 이어야 한다).

`gen_rod_builds.py` 는 자기 격자(cat)에 있는 낚싯대만 표를 만든다. KEEP_AS_IS·
재료확률 라인처럼 **격자 밖에서 보존되는 낚싯대는 영원히 표가 안 생긴다** — 이
스크립트가 그 구멍을 담당한다. 수치 권위는 손으로 적지 않고
`.claude/skills/balance-audit/scripts/enhance_lines.py` 에서 그때그때 뽑는다.

★**기존 표는 절대 건드리지 않는다.** 이미 강화해 둔 아이템의 누적 스탯이 소급으로
  바뀌기 때문이다(강화 레벨만 저장하고 스탯은 매번 표에서 다시 계산한다).

사용:
    python3 patch_enhance_missing_tables.py <BlockShip데이터폴더>            # dry-run
    python3 patch_enhance_missing_tables.py <BlockShip데이터폴더> --apply
"""
import importlib.util, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
AUTHORITY = os.path.join(os.path.dirname(HERE),
                         ".claude", "skills", "balance-audit", "scripts", "enhance_lines.py")


def load_authority(src):
    """enhance_lines.py 를 «이 데이터 폴더» 기준으로 import 한다 (BS 는 import 시각에 읽힌다)."""
    os.environ["BLOCKSHIP_DATA"] = src
    spec = importlib.util.spec_from_file_location("enhance_lines", AUTHORITY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply_ = "--apply" in sys.argv
    if not args:
        raise SystemExit("사용: patch_enhance_missing_tables.py <BlockShip데이터폴더> [--apply]")
    src = os.path.abspath(args[0])
    ep = os.path.join(src, "enhance.json")
    pp = os.path.join(src, "parts.json")

    E = json.load(open(ep, encoding="utf-8"))
    rods = json.load(open(pp, encoding="utf-8"))["parts"]["낚싯대"]
    tbl, order = E["table"], E.setdefault("order", [])

    missing = [n for n in rods if n not in tbl]
    if not missing:
        print("누락 없음 — enhance.json 이 parts.json 낚싯대 전수를 덮는다.")
        return

    el = load_authority(src)
    gen, meta = el.generate()

    print(f"표 누락 {len(missing)}종 / 낚싯대 {len(rods)}종")
    for n in missing:
        grade, origin, line, dk, base, mx, main_stat = meta[n]
        t = gen[n]
        fb = el.collections.Counter()          # 지금 라이브가 주고 있는 폴백 값
        for step in range(1, mx + 1):
            fb["난이도"] += 1; fb["크기"] += 2; fb["크리확률"] += 1
            if step % 2 == 0: fb["등급업"] += 1
            if step % 5 == 0: fb["행운"] += 1
        new = el.cum(t["levels"], mx)
        print(f"\n  {n}  [{grade}·{origin}]  라인={line}  max={mx}")
        print(f"    기본      {rods[n].split('|')[4]}")
        print(f"    폴백(현재) {', '.join(f'{k}{v:+d}' for k, v in fb.items())}")
        print(f"    새 표(풀강) {', '.join(f'{k}{int(v):+d}' for k, v in new.items())}")
        if apply_:
            tbl[n] = t
            if n not in order:
                order.append(n)

    if not apply_:
        print("\n(dry-run) 적용하려면 --apply")
        return
    shutil.copy(ep, ep + ".bak-missing-tables")
    json.dump(E, open(ep, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nenhance.json: 강화표 {len(missing)}종 추가 (총 {len(tbl)}종) — 기존 표 무변경")


if __name__ == "__main__":
    main()
