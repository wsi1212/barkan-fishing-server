#!/usr/bin/env python3
"""누락 어종의 안정적인 모델 ID와 Java/resourcepack 연결 체인을 추가한다.

이 스크립트는 그림을 만들지 않는다. fish-asset-manifest.json의 Java 매핑 누락
항목만 대상으로 ID·cod select case·generated 모델 JSON을 만들고, 기존 매핑과
파일은 덮어쓰지 않는다. 텍스처는 imagegen 후처리본을 별도로 복사해야 한다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path


CHO = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"]
JUNG = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i"]
JONG = ["", "k", "k", "ks", "n", "nj", "nh", "t", "l", "lk", "lm", "lp", "ls", "lt", "lp", "lh", "m", "p", "ps", "t", "t", "ng", "t", "t", "k", "t", "p", "h"]


def romanize_char(ch: str) -> str:
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        offset = code - 0xAC00
        return CHO[offset // 588] + JUNG[(offset % 588) // 28] + JONG[offset % 28]
    return ch


def slug(name: str) -> str:
    value = "".join(romanize_char(ch) for ch in unicodedata.normalize("NFC", name))
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return value or "fish"


def load_registry(path: Path) -> dict[str, str]:
    return dict(re.findall(r'm\.put\("([^"]+)"\s*,\s*"([^"]+)"\)', path.read_text(encoding="utf-8")))


def unique_ids(names: list[str], existing: dict[str, str]) -> dict[str, str]:
    used = set(existing.values())
    out: dict[str, str] = {}
    for name in names:
        base = slug(name)
        candidate = base
        if candidate in used:
            suffix = hashlib.sha1(name.encode("utf-8")).hexdigest()[:6]
            candidate = f"{base}_{suffix}"
        n = 2
        while candidate in used:
            candidate = f"{base}_{n}"
            n += 1
        used.add(candidate)
        out[name] = candidate
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--registry", type=Path, required=True)
    ap.add_argument("--cod", type=Path, required=True)
    ap.add_argument("--models", type=Path, required=True)
    ap.add_argument("--mapping-out", type=Path, required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    registry = load_registry(args.registry)
    names = [row["name"] for row in manifest["missing_java_mapping"] if row["name"] not in registry]
    mapping = unique_ids(names, registry)
    payload = {"count": len(mapping), "mapping": mapping}
    args.mapping_out.parent.mkdir(parents=True, exist_ok=True)
    args.mapping_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    if not args.apply:
        return

    # Java static map: 기존 마지막 put 뒤, static initializer 닫기 직전에만 삽입.
    java = args.registry.read_text(encoding="utf-8")
    marker = "\n    }\n\n    /** 물고기 이름 → 모델 ID."
    if marker not in java:
        raise SystemExit("FishModelRegistry static initializer marker not found")
    puts = "\n" + "\n".join(f'        m.put({json.dumps(name, ensure_ascii=False)}, {json.dumps(mid)});' for name, mid in mapping.items())
    java = java.replace(marker, puts + marker, 1)
    args.registry.write_text(java, encoding="utf-8")

    # cod select cases: fallback 직전 cases 배열 끝에만 삽입.
    cod = args.cod.read_text(encoding="utf-8")
    cod_marker = '    ],\n    "fallback":'
    if cod_marker not in cod:
        raise SystemExit("cod.json cases marker not found")
    cases = []
    for mid in mapping.values():
        cases.append(json.dumps({"when": mid, "model": {"type": "minecraft:model", "model": f"minecraft:item/fish/{mid}"}}, ensure_ascii=False, indent=2))
    # 들여쓰기 2칸을 JSON 파일의 기존 배열 원소 수준에 맞춘다.
    block = ",\n" + "\n".join("      " + line if i == 0 else "      " + line for case in cases for i, line in enumerate(case.splitlines()))
    # 위 표현은 case 내부 줄마다 6칸을 더하므로 첫 줄의 여는 중괄호도 동일하게 맞는다.
    cod = cod.replace(cod_marker, block + "\n" + cod_marker, 1)
    args.cod.write_text(cod, encoding="utf-8")

    args.models.mkdir(parents=True, exist_ok=True)
    for mid in mapping.values():
        path = args.models / f"{mid}.json"
        if path.exists():
            raise SystemExit(f"refusing to overwrite existing model: {path}")
        path.write_text(json.dumps({
            "parent": "minecraft:item/generated",
            "textures": {"layer0": f"minecraft:item/fish/{mid}"},
            "display": {"gui": {"scale": [1.0, 1.0, 1.0]}},
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"applied {len(mapping)} fish chains")


if __name__ == "__main__":
    main()
