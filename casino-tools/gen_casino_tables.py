#!/usr/bin/env python3
"""casino-tables.json 생성기 — 카지노 실물 건축 측량값에서 좌석/존 좌표를 계산한다.

★손편집 금지. 좌석이 어긋나면 아래 TABLES 측량값을 고치고 이 스크립트를 다시 돌린다.
   (측량은 AIBuilder mc_inspect_volume 로 world x −479~−424 / y 39~43 / z 227~262 스캔)

측량 사실 (2026-08-20 실측):
  · 카드/칩게임 상판 = 초록 카펫(1/16 두께) → 상판 표면 y = 카펫블록y + 0.0625
  · 홀덤·섯다 구역 바닥블록 y=39  → 서는 높이 y=40, 상판 카펫 y=41 → 표면 41.0625
  · 블랙잭·쓰리카드 구역 바닥블록 y=40 → 서는 높이 y=41, 상판 카펫 y=42 → 표면 42.0625
  · 홀덤 타원테이블 2개: x블록 −465..−459, z블록 239..242(A) / 246..249(B), 네 꼭짓점 컷
  · 섯다 팔각테이블 2개: x −449..−445(C) / −442..−438(D), z 242..246, 네 꼭짓점 컷
  · 블랙잭 초승달테이블 3개: z 229..232, 중심 x −470.5 / −462.5 / −454.5
  · 쓰리카드 쐐기테이블 2개: z 228..232, 서쪽(T1) x −442..−438 / 동쪽(T2) x −436..−432
  · 딜러 NPC 위치(Citizens saves.yml): 홀덤 (−461.5,238) / 홀덤Ⅱ (−461.5,250)
    섯다 (−437.5,242)=D테이블 / 섯다Ⅱ (−448.5,242)=C테이블
    블랙잭 (−462.5,229) / Ⅱ (−471,229) / Ⅲ (−455,229) · 쓰리카드 (−434.5,228) / Ⅱ (−441,228)

좌석 배치 규칙 (런타임 렌더 상수에서 역산):
  · PokerTableRuntime/HouseTableRuntime: 홀카드 = 좌석 + 시선×0.55, 칩 = 좌석 + 시선×1.15
  · 따라서 좌석은 상판 모서리에서 **0.35블록** 밖에 두고 시선은 그 모서리의 **법선**(테이블
    안쪽 수직)으로 잡는다. 중심을 정확히 겨누면(대각) 0.55 전진이 모서리를 못 넘어
    카드가 허공에 뜬다 — 구 설정이 이 실수(좌석 1.5블록 밖 + 대각 시선)였다.
  · 컷된 꼭짓점(팔각/타원 노치)은 좌석으로 쓰지 않는다: 그 칸에서 0.55 대각 전진해도
    같은 칸을 못 벗어나 카드가 상판에 안 얹힌다.
  · 딜러 NPC가 선 변은 비운다.
"""

import json
import math
from pathlib import Path

# MC yaw: 0=+z(남), 90=−x(서), 180=−z(북), −90=+x(동)
YAW = {"south": 0.0, "west": 90.0, "north": 180.0, "east": -90.0}

SETBACK = 0.35   # 상판 모서리에서 좌석까지(블록)
POKER_TOP = 41.0625
POKER_FLOOR = 40.0
HOUSE_TOP = 42.0625
HOUSE_FLOOR = 41.0


def spot(x, y, z, yaw):
    return {"x": round(x, 4), "y": round(y, 4), "z": round(z, 4), "yaw": round(float(yaw), 1)}


def oval_seats(cx, north_edge, south_edge, west_edge, east_edge, floor, wing_dx):
    """타원/직사각 상판 6인 배치: 북2·남2·서1·동1 (전부 모서리 법선 시선)."""
    zc = (north_edge + south_edge) / 2.0
    return [
        spot(cx - wing_dx, floor, north_edge - SETBACK, YAW["south"]),
        spot(cx + wing_dx, floor, north_edge - SETBACK, YAW["south"]),
        spot(east_edge + SETBACK, floor, zc, YAW["west"]),
        spot(cx + wing_dx, floor, south_edge + SETBACK, YAW["north"]),
        spot(cx - wing_dx, floor, south_edge + SETBACK, YAW["north"]),
        spot(west_edge - SETBACK, floor, zc, YAW["east"]),
    ]


def tables():
    out = []

    # ── 룰렛 (좌석 없음, 베팅판 + 휠) ───────────────────────────────────────
    # 베팅판 상판 x블록 −471..−468 (좌표 −471..−467) · z블록 240..245 → 기하중심 (−469.0, 243.0)
    # 휠은 3×3 스테어 링의 빈 중앙칸 (−470,247) → 중심 (−469.5, 247.5)
    out.append({
        "id": "roulette", "game": "ROULETTE", "world": "world", "seats": [],
        "zones": {
            "board": spot(-469.0, POKER_TOP, 243.0, 0.0),
            "wheel": spot(-469.5, POKER_TOP, 247.5, 0.0),
        },
    })

    # ── 홀덤 A (딜러 북쪽) ────────────────────────────────────────────────
    # 상판 x −465..−458, z 239..243 → 중심 (−461.5, 241.0)
    out.append({
        "id": "holdem", "game": "HOLDEM", "world": "world",
        "seats": oval_seats(-461.5, 239.0, 243.0, -465.0, -458.0, POKER_FLOOR, 2.0),
        "zones": {
            "shoe": spot(-461.5, POKER_TOP, 239.5, YAW["north"]),   # 딜러 앞
            "pot": spot(-461.5, POKER_TOP, 240.5, YAW["north"]),
            "board": spot(-461.5, POKER_TOP, 241.5, YAW["north"]),
        },
    })

    # ── 홀덤 B (딜러 남쪽) — 신설, 딜러Ⅱ NPC 담당 ──────────────────────────
    out.append({
        "id": "holdem2", "game": "HOLDEM", "world": "world",
        "seats": oval_seats(-461.5, 246.0, 250.0, -465.0, -458.0, POKER_FLOOR, 2.0),
        "zones": {
            "shoe": spot(-461.5, POKER_TOP, 249.5, YAW["south"]),   # 딜러 앞
            "pot": spot(-461.5, POKER_TOP, 248.5, YAW["south"]),
            "board": spot(-461.5, POKER_TOP, 247.5, YAW["south"]),
        },
    })

    # ── 섯다 D (딜러 북동 노치) — 2인 → 6인 ────────────────────────────────
    # 상판 x −442..−437, z 242..247 → 중심 (−439.5, 244.5)
    out.append({
        "id": "seotda", "game": "SEOTDA", "world": "world",
        "seats": oval_seats(-439.5, 242.0, 247.0, -442.0, -437.0, POKER_FLOOR, 1.0),
        "zones": {
            "shoe": spot(-438.5, POKER_TOP, 242.5, YAW["north"]),
            "pot": spot(-439.5, POKER_TOP, 244.5, YAW["north"]),
        },
    })

    # ── 섯다 C (딜러 북서 노치) — 신설, 딜러Ⅱ NPC 담당 ─────────────────────
    out.append({
        "id": "seotda2", "game": "SEOTDA", "world": "world",
        "seats": oval_seats(-446.5, 242.0, 247.0, -449.0, -444.0, POKER_FLOOR, 1.0),
        "zones": {
            "shoe": spot(-447.5, POKER_TOP, 242.5, YAW["north"]),
            "pot": spot(-446.5, POKER_TOP, 244.5, YAW["north"]),
        },
    })

    # ── 블랙잭 3개 (초승달, 플레이어는 남쪽 볼록면) ─────────────────────────
    # 남쪽 상판 마지막 줄 z블록 232(표면 z=233.0), 그 줄이 덮는 x = 중심±2블록
    for tid, cx in (("blackjack2", -470.5), ("blackjack", -462.5), ("blackjack3", -454.5)):
        # 카드가 4장까지 늘어나도 옆 사람 카드와 안 겹치게 1.3~1.4블록 간격으로 벌린다
        # (좌석 x는 남쪽 상판줄이 덮는 구간 = 중심±2.5 안이어야 카드가 상판에 얹힌다)
        seats = [spot(cx + dx, HOUSE_FLOOR, 233.0 + SETBACK, YAW["north"])
                 for dx in (-2.0, -0.7, 0.7, 2.0)]
        out.append({
            "id": tid, "game": "BLACKJACK", "world": "world", "seats": seats,
            "zones": {
                "shoe": spot(cx, HOUSE_TOP, 230.5, YAW["south"]),
                "pot": spot(cx, HOUSE_TOP, 231.5, YAW["south"]),
            },
        })

    # ── 쓰리카드 2개 (쐐기형: 계단식 3좌석, 전부 북향) ──────────────────────
    # T1(서) 상판: z228~229 x −440..−438 / z230~231 x −442..−439 / z232 x −442..−441
    out.append({
        "id": "threecard2", "game": "THREE_CARD", "world": "world",
        "seats": [
            spot(-441.5, HOUSE_FLOOR, 233.0 + SETBACK, YAW["north"]),
            spot(-439.5, HOUSE_FLOOR, 232.0 + SETBACK, YAW["north"]),
            spot(-437.5, HOUSE_FLOOR, 230.0 + SETBACK, YAW["north"]),
        ],
        "zones": {
            "shoe": spot(-439.5, HOUSE_TOP, 228.5, YAW["south"]),
            "pot": spot(-440.5, HOUSE_TOP, 230.5, YAW["south"]),
        },
    })
    # T2(동) = T1을 x=−436.5 축으로 미러
    out.append({
        "id": "threecard", "game": "THREE_CARD", "world": "world",
        "seats": [
            spot(-431.5, HOUSE_FLOOR, 233.0 + SETBACK, YAW["north"]),
            spot(-433.5, HOUSE_FLOOR, 232.0 + SETBACK, YAW["north"]),
            spot(-435.5, HOUSE_FLOOR, 230.0 + SETBACK, YAW["north"]),
        ],
        "zones": {
            "shoe": spot(-433.5, HOUSE_TOP, 228.5, YAW["south"]),
            "pot": spot(-432.5, HOUSE_TOP, 230.5, YAW["south"]),
        },
    })

    # ── 슬롯 캐비닛 2대 (좌석 개념 없음) ───────────────────────────────────
    out.append({"id": "slot1", "game": "SLOT", "world": "world", "seats": [],
                "zones": {"cabinet": spot(-473.5, 41.0, 255.5, 0.0)}})
    out.append({"id": "slot2", "game": "SLOT", "world": "world", "seats": [],
                "zones": {"cabinet": spot(-429.5, 41.0, 255.5, 0.0)}})

    return out


def main():
    data = {"tables": tables()}
    out = Path(__file__).resolve().parent / "casino-tables.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} — 테이블 {len(data['tables'])}개")
    for t in data["tables"]:
        print(f"  {t['id']:<11} {t['game']:<11} 좌석 {len(t['seats'])}  존 {','.join(t['zones'])}")


if __name__ == "__main__":
    main()
