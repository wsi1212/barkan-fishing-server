#!/usr/bin/env python3
"""
stats-lab/report.py — 주간 밸런스 리포트 markdown 생성 (stats-system-plan.md §10-2).

queries.py의 쿡북 함수를 그대로 재사용한다(쿼리 정의는 한 곳에만). balance-audit 스킬의
리포트 포맷과 동일 결로 audits/ 에 저장 가능하게 markdown 헤더/표 스타일을 맞췄다.

사용:
    python3 report.py                  # stdout 출력
    python3 report.py > weekly.md
    python3 report.py --out weekly.md
"""
import argparse
import datetime
import os
import sys

import queries


def _table(rows, cols, limit=15):
    if not rows:
        return "(데이터 없음)\n"
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in rows[:limit]:
        lines.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    if len(rows) > limit:
        lines.append(f"| ... ({len(rows)}행 중 {limit}행만 표시) |" + " |".join([""] * (len(cols) - 1)))
    return "\n".join(lines) + "\n"


def build_report():
    today = datetime.date.today().isoformat()
    out = [f"# 주간 밸런스 리포트 ({today})", "", "> stats-lab/report.py 자동 생성 — 원본 쿼리는 queries.py 참조.", ""]

    out.append("## C7. 시스템별 이용률(최근 7일)")
    out.append(_table(queries.c7_usage(7), ["type", "n", "players"], limit=20))

    out.append("## C6. 인플레 — money.txn reason별 순액(전체 기간 데이터)")
    out.append(_table(queries.c6_inflation(), ["reason", "sourced", "sunk", "n"], limit=20))

    out.append("## C2. 퀘스트 원/분 랭킹 상위")
    out.append(_table(queries.c2_quest_efficiency(), ["qid", "n", "avg_money", "avg_dur_s", "money_per_sec"]))

    out.append("## C3. 로드아웃별 실적(50캐치 이상)")
    out.append(_table(queries.c3_loadout_perf(50), ["rod", "enh", "catches", "avg_price", "high_rate"]))

    out.append("## C4. 작물 ROI(시간당 산출량)")
    out.append(_table(queries.c4_crop_roi(), ["crop", "harvests", "avg_qty", "avg_grow_s", "qty_per_sec"]))

    out.append("## C5. 부품 구매 하위(0건 후보)")
    out.append(_table(queries.c5_zero_purchase(), ["name", "n"], limit=20))

    out.append("## C8. 카지노 실현 RTP")
    out.append(_table(queries.c8_casino_rtp(), ["game", "total_bet", "total_net", "total_rake", "rounds", "realized_rtp"]))

    out.append("## C9. RNG 검증 — 낚시 등급업(명목 p vs 실측)")
    out.append(_table(queries.c9_rng_fish(), ["p_bucket", "n", "realized_rate"], limit=20))

    out.append("## C9. RNG 검증 — 강화 성공(명목 p_succ vs 실측)")
    out.append(_table(queries.c9_rng_enhance(), ["p_bucket", "n", "realized_rate"], limit=20))

    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="stats-lab 주간 밸런스 리포트 생성")
    ap.add_argument("--out", help="저장할 파일 경로(생략 시 stdout)")
    args = ap.parse_args()
    md = build_report()
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"저장됨: {args.out}", file=sys.stderr)
    else:
        print(md)


if __name__ == "__main__":
    main()
