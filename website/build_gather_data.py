#!/usr/bin/env python3
"""웹 채집·수집품 도감 산출기 — 운영 BlockShip 데이터 → gather-data.js."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LIVE = ROOT.parents[2] / "BlockShip"
OUT = ROOT / "assets" / "gather-data.js"
HEAD = "/* 서버 BlockShip의 forage-types.json · collectibles.json에서 생성됨. */\n"


def load_js(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


def collectible_name(identifier: str, island: str) -> str:
    sequence = identifier.rsplit("_", 1)[-1]
    return f"{island} 수집품 #{sequence}" if sequence.isdigit() else f"{island} 수집품"


def build(data_dir: Path) -> dict:
    forages = json.loads((data_dir / "forage-types.json").read_text(encoding="utf-8"))
    collectibles = json.loads((data_dir / "collectibles.json").read_text(encoding="utf-8"))
    previous = load_js(OUT) if OUT.exists() else {}
    previous_forage = {item["id"]: item for item in previous.get("forages", [])}
    forage_rows = []
    for identifier, row in forages.items():
        old = previous_forage.get(identifier, {})
        name = row.get("name") or identifier
        forage_rows.append({
            "kind": "forage", "id": identifier, "name": name,
            "region": row.get("region", ""), "rarity": row.get("rarity", "흔함"),
            "cooldownSec": row.get("cooldownSec", 0),
            "desc": old.get("desc") or f"{row.get('region', '바르칸')}에서 발견할 수 있는 채집품입니다.",
        })
    collectible_rows = []
    for identifier, row in collectibles.items():
        # 운영자 전용 테스트 수집품은 일반 탐험 도감에 노출하지 않는다.
        if identifier.startswith("어드민의 수집품_"):
            continue
        island = row.get("island") or "바르칸"
        collectible_rows.append({
            "kind": "collectible", "id": identifier, "name": collectible_name(identifier, island),
            "island": island, "world": row.get("world", "world"),
            "x": row.get("x", 0), "y": row.get("y", 0), "z": row.get("z", 0),
            "headType": row.get("headType", "PLAYER_HEAD"),
            "desc": f"{island}에 배치된 수집품입니다. 가까이에서 상호작용해 탐험 기록에 등록하세요.",
        })
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "forageCount": len(forage_rows), "collectibleCount": len(collectible_rows),
        "forages": forage_rows, "collectibles": collectible_rows,
    }


def validate(data_dir: Path) -> list[str]:
    expected = build(data_dir)
    actual = load_js(OUT)
    return [f"{field}가 운영 원본과 다름" for field in ("forageCount", "collectibleCount", "forages", "collectibles")
            if actual.get(field) != expected.get(field)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=LIVE, help="forage-types.json·collectibles.json이 있는 BlockShip 데이터 폴더")
    parser.add_argument("--check", action="store_true", help="파일을 쓰지 않고 운영 원본과 대조")
    args = parser.parse_args()
    if args.check:
        errors = validate(args.data)
        if errors:
            print("\n".join(f"ERROR: {error}" for error in errors))
            return 1
        current = load_js(OUT)
        print(f"PASS: 채집품 {current['forageCount']}종 · 수집품 {current['collectibleCount']}종")
        return 0
    payload = build(args.data)
    OUT.write_text(HEAD + "window.BARKAN_GATHER_DATA=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    errors = validate(args.data)
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        return 1
    print(f"gather updated: 채집품 {payload['forageCount']}종 · 수집품 {payload['collectibleCount']}종")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
