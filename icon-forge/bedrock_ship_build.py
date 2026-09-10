#!/usr/bin/env python3
"""BlockShip 구운 Java 선체 모델 → 회전 가능한 Bedrock custom entity 팩 자산.

배에는 BedrockBlockMirror(가짜 블록)를 쓰지 않는다. 서버의 Interaction 컨트롤러를
Geyser ServerSpawnEntityEvent에서 custom entity로 치환하고, 이 스크립트가 그 identifier가
그릴 geometry/texture/client_entity를 기존 barkan_bedrock.mcpack에 합친다.

빌드 순서
    python3 bedrock_pack_build.py
    python3 bedrock_block_build.py
    python3 bedrock_ship_build.py

입력
    ~/development/barkan-resourcepack/assets/barkan/models/ship/*.json
    plugins/BlockShip/ship-models.json (scale/pivot_y 단일 진실원)
    Minecraft client jar (모델이 참조하는 바닐라 블록 텍스처)

산출물
    out/bedrock/barkan_bedrock.mcpack 에 entity/geometry/atlas/render_controller 병합
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import zipfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SERVER = Path("/Users/user/Library/Application Support/feather/player-server/"
              "servers/07de2d81-991a-47e2-b62d-06c0d1b5150a")
RP = Path(os.path.expanduser("~/development/barkan-resourcepack"))
SHIP_MODELS = SERVER / "plugins/BlockShip/ship-models.json"
OUT = HERE / "out/bedrock"
STAGE = OUT / "pack"

# Geyser extension과 Bukkit 브리지의 identifier와 반드시 같아야 한다.
ENTITY_IDS = {
    "barkan:ship/dotdanbae": "barkan:ship_dotdanbae",
    "barkan:ship/viking_longship": "barkan:ship_viking_longship",
}

TILE = 16
FACE_NAME = {
    "north": "north", "south": "south", "up": "up", "down": "down",
    "east": "west", "west": "east",  # Java/Bedrock 모델 X축 손잡이 차이
}


def client_jar() -> Path:
    versions = Path("/Users/user/Library/Application Support/minecraft/versions")
    for version in ("1.21.11", "1.21.10", "26.2", "1.21.8", "1.21"):
        p = versions / version / f"{version}.jar"
        if p.is_file():
            return p
    raise SystemExit("Minecraft client jar를 못 찾았습니다 — 바닐라 선체 텍스처를 읽을 수 없습니다")


def item_model_path(item_model: str) -> Path:
    if ":" not in item_model:
        raise SystemExit(f"잘못된 item_model: {item_model}")
    ns, path = item_model.split(":", 1)
    return RP / "assets" / ns / "models" / f"{path}.json"


def texture_bytes(texture_id: str, vanilla: zipfile.ZipFile) -> bytes:
    if ":" not in texture_id:
        texture_id = "minecraft:" + texture_id
    ns, path = texture_id.split(":", 1)
    rel = f"assets/{ns}/textures/{path}.png"
    custom = RP / rel
    if custom.is_file():
        return custom.read_bytes()
    try:
        return vanilla.read(rel)
    except KeyError as e:
        raise SystemExit(f"선체 텍스처 없음: {texture_id} ({rel})") from e


def tile_image(raw: bytes, uv: tuple[float, float, float, float], rotation: int) -> Image.Image:
    """Java face의 UV 자르기·반전·회전을 16×16 한 장에 미리 굽는다.

    Bedrock geometry의 per-face UV는 90도 축 교환을 직접 표현하지 못한다. 텍스처 전체를
    돌리고 좌표만 옮기면 부분 UV와 역방향 UV에서 회전이 상쇄되거나 다른 영역을 읽는다.
    그래서 각 고유 face를 작은 정방형 타일로 래스터화하고 geometry는 그 타일 전체를 쓴다.
    """
    with Image.open(io.BytesIO(raw)) as src:
        im = src.convert("RGBA")
        # 애니메이션 세로 스트립은 첫 프레임을 쓴다. 선체는 정적 엔티티 텍스처다.
        if im.height != im.width:
            side = min(im.width, im.height)
            im = im.crop((0, 0, side, side))
        if im.size != (TILE, TILE):
            im = im.resize((TILE, TILE), Image.Resampling.NEAREST)

        u1, v1, u2, v2 = uv
        left, right = sorted((u1, u2))
        top, bottom = sorted((v1, v2))
        if right <= left or bottom <= top:
            raise SystemExit(f"넓이 0인 face UV: {uv}")
        im = im.crop((left, top, right, bottom)).resize(
            (TILE, TILE), Image.Resampling.NEAREST)
        if u2 < u1:
            im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if v2 < v1:
            im = im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        if rotation == 90:
            im = im.transpose(Image.Transpose.ROTATE_270)  # clockwise
        elif rotation == 180:
            im = im.transpose(Image.Transpose.ROTATE_180)
        elif rotation == 270:
            im = im.transpose(Image.Transpose.ROTATE_90)
        return im


def texture_ref(model: dict, face: dict) -> str:
    ref = str(face.get("texture", ""))
    seen = set()
    while ref.startswith("#"):
        key = ref[1:]
        if key in seen:
            raise SystemExit(f"순환 texture 참조: {key}")
        seen.add(key)
        ref = str((model.get("textures") or {}).get(key, ""))
    if not ref:
        raise SystemExit(f"texture 참조를 해석할 수 없습니다: {face.get('texture')}")
    return ref


def face_key(model: dict, face: dict) -> tuple[str, tuple[float, float, float, float], int]:
    uv = tuple(map(float, face.get("uv", [0, 0, 16, 16])))
    rotation = int(face.get("rotation", 0))
    if rotation not in (0, 90, 180, 270):
        raise SystemExit(f"지원하지 않는 face rotation: {rotation}")
    return texture_ref(model, face), uv, rotation


def atlas_for(model: dict, vanilla: zipfile.ZipFile) -> tuple[Image.Image, dict[tuple, tuple[int, int]]]:
    keys = sorted({
        face_key(model, face)
        for element in model.get("elements", [])
        for face in (element.get("faces") or {}).values()
    })
    cells = max(1, math.ceil(math.sqrt(len(keys))))
    side = 1
    while side < cells * TILE:
        side *= 2
    cols = side // TILE
    atlas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    positions: dict[tuple, tuple[int, int]] = {}
    cache: dict[str, bytes] = {}
    for i, key in enumerate(keys):
        texture_id, uv, rotation = key
        raw = cache.setdefault(texture_id, texture_bytes(texture_id, vanilla))
        x, y = (i % cols) * TILE, (i // cols) * TILE
        atlas.alpha_composite(tile_image(raw, uv, rotation), (x, y))
        positions[key] = (x, y)
    return atlas, positions


def r4(value: float) -> float:
    return round(float(value), 4)


def geometry(model: dict, identifier: str, atlas: Image.Image, positions: dict,
             scale: float, pivot_y: float) -> dict:
    cubes = []
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for element in model.get("elements", []):
        f, t = element["from"], element["to"]
        # Bedrock entity geometry 단위도 1/16블록이다. Java ItemDisplay의 scale을 좌표에
        # 미리 구워 넣고, ItemDisplay 위치의 pivot_y는 Y 오프셋으로 합친다.
        origin = [
            (8.0 - float(t[0])) * scale,
            (float(f[1]) - 8.0) * scale + pivot_y * 16.0,
            (float(f[2]) - 8.0) * scale,
        ]
        size = [
            (float(t[0]) - float(f[0])) * scale,
            (float(t[1]) - float(f[1])) * scale,
            (float(t[2]) - float(f[2])) * scale,
        ]
        uv_faces = {}
        for face_name, face in (element.get("faces") or {}).items():
            tile_x, tile_y = positions[face_key(model, face)]
            uv_faces[FACE_NAME[face_name]] = {
                "uv": [tile_x, tile_y],
                "uv_size": [TILE, TILE],
            }
        cube = {
            "origin": [r4(v) for v in origin],
            "size": [r4(v) for v in size],
            "uv": uv_faces,
        }
        rotation = element.get("rotation")
        if rotation:
            axis = str(rotation["axis"])
            angle = float(rotation["angle"])
            vec = [0.0, 0.0, 0.0]
            vec[{"x": 0, "y": 1, "z": 2}[axis]] = -angle if axis in ("y", "z") else angle
            o = rotation.get("origin", [8, 8, 8])
            cube["pivot"] = [
                r4((8.0 - float(o[0])) * scale),
                r4((float(o[1]) - 8.0) * scale + pivot_y * 16.0),
                r4((float(o[2]) - 8.0) * scale),
            ]
            cube["rotation"] = [r4(v) for v in vec]
        cubes.append(cube)
        xs.extend((origin[0], origin[0] + size[0]))
        ys.extend((origin[1], origin[1] + size[1]))
        zs.extend((origin[2], origin[2] + size[2]))

    radius_blocks = max(math.hypot(x, z) for x in xs for z in zs) / 16.0
    min_y, max_y = min(ys) / 16.0, max(ys) / 16.0
    return {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {
                "identifier": identifier,
                "texture_width": atlas.width,
                "texture_height": atlas.height,
                "visible_bounds_width": r4(radius_blocks * 2.0 + 4.0),
                "visible_bounds_height": r4(max_y - min_y + 4.0),
                "visible_bounds_offset": [0, r4((min_y + max_y) / 2.0), 0],
            },
            "bones": [{"name": "root", "pivot": [0, 0, 0], "cubes": cubes}],
        }],
    }


def client_entity(entity_id: str, slug: str) -> dict:
    return {
        "format_version": "1.10.0",
        "minecraft:client_entity": {
            "description": {
                "identifier": entity_id,
                "materials": {"default": "entity_alphatest"},
                "textures": {"default": f"textures/entity/barkan/{slug}"},
                "geometry": {"default": f"geometry.barkan.{slug}"},
                "render_controllers": ["controller.render.barkan_ship"],
            }
        },
    }


def main() -> int:
    if not STAGE.is_dir() or not (STAGE / "manifest.json").is_file():
        raise SystemExit("팩 스테이지가 없습니다 — item → block 빌더를 먼저 실행하세요")
    if not SHIP_MODELS.is_file():
        raise SystemExit(f"ship-models.json 없음: {SHIP_MODELS}")

    # 재실행 시 폐기된 선체만 지운다. entity/ 같은 공용 디렉터리를 통째로 지우면 다른
    # custom entity가 추가된 날 그 자산까지 조용히 날아간다.
    owned = [
        STAGE / f"entity/{entity_id.split(':', 1)[1]}.entity.json"
        for entity_id in ENTITY_IDS.values()
    ] + [
        STAGE / f"models/entity/{entity_id.split(':', 1)[1]}.geo.json"
        for entity_id in ENTITY_IDS.values()
    ] + [
        STAGE / f"textures/entity/barkan/{entity_id.split(':', 1)[1]}.png"
        for entity_id in ENTITY_IDS.values()
    ] + [STAGE / "render_controllers/barkan_ship.render_controllers.json"]
    for path in owned:
        path.unlink(missing_ok=True)
        path.parent.mkdir(parents=True, exist_ok=True)

    definitions = json.loads(SHIP_MODELS.read_text(encoding="utf-8"))
    built = []
    with zipfile.ZipFile(client_jar()) as vanilla:
        for preset, spec in definitions.items():
            item_model = str(spec["item_model"])
            entity_id = ENTITY_IDS.get(item_model)
            if entity_id is None:
                raise SystemExit(f"Geyser extension에 등록되지 않은 선체입니다: {preset} → {item_model}")
            source = item_model_path(item_model)
            if not source.is_file():
                raise SystemExit(f"Java 선체 모델 없음: {source}")
            model = json.loads(source.read_text(encoding="utf-8"))
            if not model.get("elements"):
                raise SystemExit(f"elements 없는 선체 모델: {source}")

            slug = entity_id.split(":", 1)[1]
            atlas, positions = atlas_for(model, vanilla)
            atlas.save(STAGE / f"textures/entity/barkan/{slug}.png", "PNG", optimize=True)
            geo = geometry(model, f"geometry.barkan.{slug}", atlas, positions,
                           float(spec["scale"]), float(spec["pivot_y"]))
            (STAGE / f"models/entity/{slug}.geo.json").write_text(
                json.dumps(geo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            (STAGE / f"entity/{slug}.entity.json").write_text(
                json.dumps(client_entity(entity_id, slug), ensure_ascii=False, indent=2), encoding="utf-8")
            built.append((preset, entity_id, len(model["elements"]), atlas.size))

    render = {
        "format_version": "1.8.0",
        "render_controllers": {
            "controller.render.barkan_ship": {
                "geometry": "Geometry.default",
                "materials": [{"*": "Material.default"}],
                "textures": ["Texture.default"],
            }
        },
    }
    (STAGE / "render_controllers/barkan_ship.render_controllers.json").write_text(
        json.dumps(render, ensure_ascii=False, indent=2), encoding="utf-8")

    # 동일 uuid의 내용이 바뀌면 캐시 버전도 반드시 달라져야 한다. 단순 +1은 매번 전체
    # 빌드가 같은 기준 버전에서 시작하므로 선체/블록만 바뀌었을 때 결과가 늘 같은 숫자가
    # 되는 함정이 있다. 최종 팩 전체(아직 쓸 manifest 제외)를 해시해 내용 기반 버전을 만든다.
    stamp = hashlib.sha1()
    for path in sorted(STAGE.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            stamp.update(path.relative_to(STAGE).as_posix().encode("utf-8"))
            stamp.update(path.read_bytes())
    rev = int(stamp.hexdigest()[:6], 16) % 100000
    manifest_path = STAGE / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for block in [manifest["header"]] + manifest["modules"]:
        block["version"][2] = rev
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    pack = OUT / "barkan_bedrock.mcpack"
    pack.unlink(missing_ok=True)
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as out:
        for path in sorted(STAGE.rglob("*")):
            if path.is_file():
                out.write(path, path.relative_to(STAGE).as_posix())

    for preset, entity_id, cubes, atlas_size in built:
        print(f"  {preset}: {entity_id} · cube {cubes} · atlas {atlas_size[0]}×{atlas_size[1]}")
    print(f"▶ 회전형 베드락 선체 {len(built)}종 · 팩 {pack.stat().st_size // 1024} KB"
          f" · manifest {manifest['header']['version']}")
    print(f"✅ {pack}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
