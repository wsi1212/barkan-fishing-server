#!/usr/bin/env python3
"""Known-good Bedrock pack에 아이콘 정의를 하나씩 안전하게 덧붙인다.

Geyser custom item은 특정 base item/definition 조합에서 로그인 협상을 깨뜨릴 수 있다.
전체 재생성물을 곧바로 올리지 않고, 정상 팩을 보존한 채 선택한 icon만 추가해 실제
모바일 접속으로 검증할 때 사용한다. 매핑·텍스처·manifest는 항상 함께 갱신한다.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path


def read_items(path: Path) -> dict[str, list[dict]]:
    return json.loads(path.read_text(encoding="utf-8"))["items"]


def definitions_for(items: dict[str, list[dict]], icon: str) -> list[tuple[str, dict]]:
    return [(base, definition) for base, definitions in items.items() for definition in definitions
            if definition.get("bedrock_options", {}).get("icon") == icon]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-map", type=Path, required=True)
    parser.add_argument("--baseline-pack", type=Path, required=True)
    parser.add_argument("--source-map", type=Path, required=True)
    parser.add_argument("--source-pack", type=Path, required=True)
    parser.add_argument("--out-map", type=Path, required=True)
    parser.add_argument("--out-pack", type=Path, required=True)
    parser.add_argument("--item", action="append", required=True,
                        help="추가할 barkan_icon id. 여러 번 지정 가능")
    args = parser.parse_args()

    baseline = read_items(args.baseline_map)
    source = read_items(args.source_map)
    selected = list(dict.fromkeys(args.item))
    additions: list[tuple[str, dict]] = []
    known_ids = {d["bedrock_identifier"] for defs in baseline.values() for d in defs}
    known_pairs = {(base, d["bedrock_identifier"])
                   for base, defs in baseline.items() for d in defs}
    for icon in selected:
        found = definitions_for(source, icon)
        if not found:
            raise SystemExit(f"소스 매핑에 없는 아이콘: {icon}")
        for base, definition in found:
            if (base, definition["bedrock_identifier"]) in known_pairs:
                continue
            # 정상 팩이 예전 규칙으로 같은 identifier를 다른 베이스에 이미 쓰고 있을 수 있다.
            # Geyser identifier는 전역 유일해야 하므로, 새 베이스 쪽만 bN_ 접두어로 바꾼다.
            # 이걸 단순히 건너뛰면 아이템이 지급되는 실제 베이스에서 조용히 바닐라로 보인다.
            candidate = dict(definition)
            original_id = candidate["bedrock_identifier"]
            if original_id in known_ids:
                namespace, raw = original_id.split(":", 1)
                index = 1
                while f"{namespace}:b{index}_{icon}" in known_ids:
                    index += 1
                candidate["bedrock_identifier"] = f"{namespace}:b{index}_{icon}"
            additions.append((base, candidate))
            known_ids.add(candidate["bedrock_identifier"])
            known_pairs.add((base, candidate["bedrock_identifier"]))

    with tempfile.TemporaryDirectory(prefix="barkan-bedrock-incremental-") as tmp:
        stage = Path(tmp) / "pack"
        with zipfile.ZipFile(args.baseline_pack) as archive:
            archive.extractall(stage)
        texture_data_path = stage / "textures/item_texture.json"
        texture_data = json.loads(texture_data_path.read_text(encoding="utf-8"))["texture_data"]
        with zipfile.ZipFile(args.source_pack) as archive:
            source_textures = json.loads(archive.read("textures/item_texture.json"))["texture_data"]
            for icon in selected:
                entry = source_textures.get(icon)
                if entry is None:
                    raise SystemExit(f"소스 팩에 없는 텍스처 정의: {icon}")
                rel = entry["textures"]
                source_png = f"{rel}.png"
                if source_png not in archive.namelist():
                    raise SystemExit(f"소스 팩에 없는 텍스처 파일: {source_png}")
                destination = stage / source_png
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(source_png))
                texture_data[icon] = entry

        manifest_path = stage / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rev = int(manifest["header"]["version"][2]) + 1
        manifest["header"]["version"][2] = rev
        for module in manifest.get("modules", []):
            module["version"][2] = rev
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        texture_data_path.write_text(json.dumps({
            "resource_pack_name": "barkan", "texture_name": "atlas.items",
            "texture_data": texture_data,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        merged = {base: list(definitions) for base, definitions in baseline.items()}
        for base, definition in additions:
            merged.setdefault(base, []).append(definition)
        for base, definitions in merged.items():
            for definition in definitions:
                icon = definition.get("bedrock_options", {}).get("icon")
                rel = texture_data.get(icon, {}).get("textures") if icon else None
                if not rel or not (stage / f"{rel}.png").is_file():
                    raise SystemExit(f"매핑↔텍스처 누락: {base}/{icon}")

        args.out_map.parent.mkdir(parents=True, exist_ok=True)
        args.out_map.write_text(json.dumps({"format_version": "2", "items": merged},
                                           ensure_ascii=False, indent=2), encoding="utf-8")
        args.out_pack.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.out_pack, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(stage.rglob("*")):
                if file.is_file():
                    archive.write(file, file.relative_to(stage).as_posix())

    print(f"추가 아이콘: {', '.join(selected)}")
    print(f"신규 정의: {len(additions)}개 / 총 {sum(len(v) for v in merged.values())}개")
    print(f"팩 버전: 1.0.{rev}")
    print(f"{args.out_map}\n{args.out_pack}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
