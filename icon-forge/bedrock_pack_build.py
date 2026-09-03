#!/usr/bin/env python3
"""베드락(Geyser) 커스텀 아이템 팩 생성기 — 자바 리소스팩 아이콘을 BE 에서도 보이게 한다.

왜 필요한가
    자바 클라는 `item_model` 컴포넌트로 커스텀 아이콘을 그리지만 베드락 클라는 그 개념이
    없다. Geyser 가 «자바 아이템 + item_model → 베드락 커스텀 아이템» 으로 바꿔 주는데,
    그러려면 두 짝이 필요하다:
      ① 매핑 JSON  — plugins/Geyser-Spigot/packs/barkan_mappings.json
      ② 베드락 팩  — plugins/Geyser-Spigot/packs/barkan_bedrock.mcpack
                     (textures/items/*.png + textures/item_texture.json + manifest.json)
    둘 중 하나만 있으면 아이템이 «보이지 않거나» 이름만 나온다.

★생성물을 손으로 고치지 말 것 — 이 스크립트를 다시 돌린다.
    여태 이 팩은 물고기 486종만 든 채 «한 번 만들어진 사본» 으로 굳어 있었고 생성기가
    없었다(2026-09-04 확인). 그래서 낚싯대·부품·재료 아이콘 548종이 베드락에서
    전부 안 보였다. 규칙이 바뀌면 이 파일을 고치고 다시 돌린다.

권위(=입력)
    · 카탈로그 아이콘 : icon-forge/out/catalog/catalog_manifest.json (catalog_build.py 산출)
    · 재료 아이콘     : plugins/BlockShip/materials.json + ItemIconModel 규칙
    · 물고기          : 기존 매핑의 minecraft:cod 항목을 그대로 승계(생성 규칙이 다르다)
    · 텍스처 실물     : ~/development/barkan-resourcepack/assets/**/barkan_icon/<id>.png

베이스 아이템(자바) — EquipmentManager.partIcon / TrapSpecs.ITEM_MAT / MaterialLoader 실측
    낚싯대·작살 외 부품은 종류마다 베이스가 다르다. Geyser 매핑은 «자바 아이템 id» 로
    묶이므로 이 표가 틀리면 그 종류만 통째로 안 나온다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SERVER = Path("/Users/user/Library/Application Support/feather/player-server/"
              "servers/07de2d81-991a-47e2-b62d-06c0d1b5150a")
RP = Path(os.path.expanduser("~/development/barkan-resourcepack"))
CATALOG = HERE / "out/catalog/catalog_manifest.json"
MATERIALS = SERVER / "plugins/BlockShip/materials.json"
OUT = HERE / "out/bedrock"

NS = "barkan"

# ── 자바 베이스 아이템 ────────────────────────────────────────────────────────
#   EquipmentManager.partIcon(type) 실측(2026-09-04):
#     릴=CLOCK 줄=STRING 바늘=TRIPWIRE_HOOK 미끼=WHEAT_SEEDS 찌=PUFFERFISH 그 외=PAPER
#   작살은 HarpoonManager 가 COD, 통발은 TrapSpecs.ITEM_MAT=BARREL,
#   재료는 MaterialLoader 가 mcItem 을 무조건 "paper" 로 강제한다.
BASE_ITEM = {
    "rod": "minecraft:paper",
    "reel": "minecraft:clock",
    "line": "minecraft:string",
    "hook": "minecraft:tripwire_hook",
    "bait": "minecraft:wheat_seeds",
    "bobber": "minecraft:pufferfish",
    "harpoon": "minecraft:wooden_spear",   # ★기본값 — 실제로는 이름·등급별로 창 재질이 다르다(spear_id 참조)
    "trap": "minecraft:barrel",
    "material": "minecraft:paper",
}

# ItemIconModel.category(type) 와 같아야 한다 — 어긋나면 모델 경로가 안 맞아 조용히 빠진다.
TYPE_KEY = {
    "낚싯대": "rod", "릴": "reel", "줄": "line", "바늘": "hook",
    "미끼": "bait", "찌": "bobber", "작살": "harpoon", "통발": "trap",
    "재료": "material",
}


def sha10(*parts: str) -> str:
    """ItemIconModel.sha10 과 동일 — SHA-1 앞 5바이트를 hex 10자로."""
    return hashlib.sha1("\0".join(p or "" for p in parts).encode("utf-8")).hexdigest()[:10]


def icon_id(kind: str, name: str, variant: str | None = None) -> str:
    if kind == "통발":
        return f"catalog_trap_{sha10('통발', name, variant or '표준')}"
    return f"catalog_{TYPE_KEY[kind]}_{sha10(kind, name)}"


def spear_id(name: str | None, grade: str | None) -> str:
    """작살 베이스 아이템 — HarpoonItemFactory.vanillaSpearId 와 «같은 규칙» 이어야 한다.

    작살만 유독 베이스가 8종으로 갈린다(등급이 창 재질로 보이게 한 2026-08-03 설계).
    여기가 어긋나면 그 등급대 작살만 베드락에서 아이콘이 안 뜬다.
    """
    if name:
        if "네더라이트" in name: return "minecraft:netherite_spear"
        if "다이아" in name:    return "minecraft:diamond_spear"
        if "강철" in name:      return "minecraft:iron_spear"
        if "철" in name:        return "minecraft:iron_spear"
        if "나무" in name:      return "minecraft:wooden_spear"
    return {
        "D": "minecraft:stone_spear",
        "C": "minecraft:copper_spear",
        "B": "minecraft:iron_spear",
        "A": "minecraft:golden_spear",
        "S": "minecraft:diamond_spear",
        "M": "minecraft:diamond_spear",
        "L": "minecraft:diamond_spear",
        "G": "minecraft:netherite_spear",
    }.get(grade or "", "minecraft:wooden_spear")


def find_texture(icon: str) -> Path | None:
    """리소스팩에서 <icon>.png 를 찾는다.

    ★네임스페이스가 섞여 있다 — 카탈로그는 assets/minecraft/textures/item/barkan_icon/ 에,
      일부 아이콘은 assets/barkan/textures/item/ 아래에 있다. 둘 다 뒤진다.
    """
    for base in (RP / "assets/minecraft/textures/item",
                 RP / "assets/barkan/textures/item",
                 RP / "assets/minecraft/textures",
                 RP / "assets/barkan/textures"):
        if not base.is_dir():
            continue
        hit = next(base.rglob(f"{icon}.png"), None)
        if hit:
            return hit
    return None


def collect() -> tuple[list[dict], list[str]]:
    """(항목, 경고) — 항목 = {icon, model, base, label}.

    ★권위는 «리소스팩에 실제로 있는 아이템 정의» 다(assets/barkan/items/barkan_icon/).
      카탈로그 매니페스트만 믿으면 거기 없는 것(히든 장비·추가 통발 등)이 통째로 빠진다 —
      2026-09-04 실측: 매니페스트 431+재료 69 = 497 인데 리소스팩엔 548 개가 있었다.
      매니페스트는 «사람이 읽을 이름» 을 붙이는 용도로만 쓴다.
    """
    entries: list[dict] = []
    warns: list[str] = []

    defs_dir = RP / "assets/barkan/items/barkan_icon"
    if not defs_dir.is_dir():
        return entries, [f"아이템 정의 폴더 없음: {defs_dir}"]

    # 매니페스트 → {icon: "종류 이름"} 라벨 사전(있으면 로그가 읽기 쉬워진다)
    labels: dict[str, str] = {}
    harpoon_base: dict[str, str] = {}
    if CATALOG.is_file():
        for row in json.loads(CATALOG.read_text(encoding="utf-8")):
            if not row.get("id"):
                continue
            labels[row["id"]] = f"{row.get('kind')} {row.get('name')}"
            if row.get("kind") == "작살":
                harpoon_base[row["id"]] = spear_id(row.get("name"), row.get("grade"))
    if MATERIALS.is_file():
        mats = json.loads(MATERIALS.read_text(encoding="utf-8")).get("materials", {})
        names = mats.keys() if isinstance(mats, dict) else [m.get("name") for m in mats]
        for name in names:
            labels[icon_id("재료", name)] = f"재료 {name}"

    families = {v: k for k, v in TYPE_KEY.items()}   # rod -> 낚싯대 …
    for f in sorted(defs_dir.glob("catalog_*.json")):
        icon = f.stem
        fam = icon.split("_")[1] if icon.count("_") >= 2 else None
        if fam not in BASE_ITEM:
            warns.append(f"모르는 계열 건너뜀: {icon}")
            continue
        base = harpoon_base.get(icon, BASE_ITEM[fam]) if fam == "harpoon" else BASE_ITEM[fam]
        entries.append({
            "icon": icon,
            "model": f"{NS}:barkan_icon/{icon}",
            "base": base,
            "label": labels.get(icon, f"{families.get(fam, fam)} ?({icon})"),
        })
    return entries, warns


def _emit_texture(src: Path, dst: Path, max_px: int) -> None:
    """텍스처 1장 — 필요하면 축소해서 쓴다.

    ★카탈로그 아이콘은 512/256px 로 그려져 있는데(물고기는 128) 베드락은 이걸 인벤토리
      한 칸에 그린다. 원본 그대로 넣으면 팩이 28MB 가 되어 모바일 첫 접속이 그만큼 길어진다.
      이미 128px 로 잘 돌고 있는 물고기에 맞춰 정규화한다 — 화질 손해 없이 팩이 1/3 이 된다.
    ★리샘플러는 LANCZOS. 이 그림들은 «업스케일된 픽셀아트가 아니라» 안티에일리어싱된
      회화체다(4x/2x 블록 균일도 0.6~0.84 실측) — NEAREST 로 줄이면 가장자리가 부서진다.
    """
    try:
        with Image.open(src) as im:
            if max(im.size) <= max_px:
                if src.resolve() != dst.resolve():
                    shutil.copyfile(src, dst)
                return
            im = im.convert("RGBA")
            w, h = im.size
            scale = max_px / max(w, h)
            im.resize((max(1, round(w * scale)), max(1, round(h * scale))),
                      Image.LANCZOS).save(dst, "PNG", optimize=True)
    except Exception:
        if src.resolve() != dst.resolve():
            shutil.copyfile(src, dst)   # 이미지 처리 실패해도 아이콘은 나가야 한다


def build(dry: bool, max_px: int = 128) -> int:
    entries, warns = collect()
    for w in warns:
        print(f"  ⚠ {w}")

    resolved, missing = [], []
    for e in entries:
        tex = find_texture(e["icon"])
        if tex is None:
            missing.append(e)
        else:
            e["texture"] = tex
            resolved.append(e)

    print(f"▶ 대상 {len(entries)}종 — 텍스처 있음 {len(resolved)} / 없음 {len(missing)}")
    if missing:
        print("  ⚠ 텍스처를 못 찾아 뺀 항목(상위 10):")
        for e in missing[:10]:
            print(f"     · {e['label']} ({e['icon']})")

    # ── 매핑: 기존 물고기 항목을 승계하고 새 항목을 합친다 ──────────────────
    #   물고기는 custom_model_data 규칙이라 여기서 다시 만들지 않는다. 덮어쓰면
    #   486종이 통째로 날아간다.
    old_path = OUT / "barkan_mappings.json"
    legacy = {}
    for cand in (old_path, HERE / "out/bedrock/barkan_mappings.json"):
        if cand.is_file():
            legacy = json.loads(cand.read_text(encoding="utf-8")).get("items", {})
            break
    if not legacy:
        print("  ⚠ 기존 매핑(물고기)을 못 찾았습니다 — --fish 로 경로를 주면 승계합니다")

    # ★bedrock_identifier 로 «중복 제거» 한다 — 이게 없으면 실행할 때마다 누적된다.
    #   legacy 를 자기 출력에서 읽기 때문이다(2026-09-04 사고: 3번 돌려 2130개가 됐다).
    #   Geyser 는 중복을 조용히 무시해 겉으로는 멀쩡해 보이지만 파일만 계속 커진다.
    items: dict[str, list] = {}
    seen_ids: set[str] = set()

    def put(base: str, entry: dict) -> bool:
        bid = entry.get("bedrock_identifier")
        if not bid or bid in seen_ids:
            return False
        seen_ids.add(bid)
        items.setdefault(base, []).append(entry)
        return True

    # 새로 만든 것이 «우선» — 규칙이 바뀌면 옛 정의가 아니라 이번 정의가 남아야 한다.
    for e in resolved:
        put(e["base"], {
            "type": "definition",
            "model": e["model"],
            "bedrock_identifier": f"{NS}:{e['icon']}",
            "bedrock_options": {"icon": e["icon"], "creative_category": "items"},
        })
    carried_defs = 0
    for base, defs in legacy.items():
        for entry in defs:
            if put(base, entry):
                carried_defs += 1

    mappings = {"format_version": "2", "items": items}
    total = sum(len(v) for v in items.values())
    print(f"▶ 매핑 총 {total}종 (신규 {len(resolved)} + 기존 승계 {carried_defs}"
          f", 중복 제거 {sum(len(v) for v in legacy.values()) - carried_defs})")
    for k, v in sorted(items.items(), key=lambda kv: -len(kv[1])):
        print(f"     {k}: {len(v)}")

    if dry:
        print("— dry-run: 파일을 쓰지 않았습니다")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    old_path.write_text(json.dumps(mappings, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 베드락 팩 ────────────────────────────────────────────────────────────
    stage = OUT / "pack"
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "textures/items").mkdir(parents=True)

    # manifest — ★uuid 를 고정한다. 바뀌면 클라가 «다른 팩» 으로 보고 전부 다시 받는다.
    manifest = {
        "format_version": 2,
        "header": {
            "name": "바르칸 열도 (베드락)",
            "description": "Geyser 커스텀 아이템 — 물고기·낚싯대·부품·재료 아이콘",
            "uuid": "2af7a31c-f3b7-5fd3-b260-d608317953ab",
            "version": [1, 0, 0],
            "min_engine_version": [1, 21, 0],
        },
        "modules": [{
            "type": "resources",
            "uuid": "6f1d5b7c-1c9a-5a55-9a2c-2f0a9c4e77b1",
            "version": [1, 0, 0],
        }],
    }
    (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                         encoding="utf-8")

    texture_data = {}
    for e in resolved:
        _emit_texture(e["texture"], stage / "textures/items" / f"{e['icon']}.png", max_px)
        texture_data[e["icon"]] = {"textures": f"textures/items/{e['icon']}"}

    # 기존 물고기 텍스처도 팩에 남아 있어야 한다 — 이전 팩에서 그대로 가져온다.
    prev = SERVER / "plugins/Geyser-Spigot/packs/barkan_bedrock.mcpack"
    carried = 0
    if prev.is_file():
        with zipfile.ZipFile(prev) as z:
            for n in z.namelist():
                if not n.startswith("textures/items/") or not n.endswith(".png"):
                    continue
                icon = Path(n).stem
                if icon in texture_data:
                    continue
                tmp = stage / "textures/items" / f"{icon}.png"
                tmp.write_bytes(z.read(n))
                _emit_texture(tmp, tmp, max_px)
                texture_data[icon] = {"textures": f"textures/items/{icon}"}
                carried += 1
    print(f"▶ 텍스처 {len(texture_data)}장 (신규 {len(resolved)} + 기존 승계 {carried})")

    # ★item_texture.json 이 없으면 아이콘 이름이 해석되지 않아 전부 «보라/검정» 이 된다.
    (stage / "textures").mkdir(exist_ok=True)
    (stage / "textures/item_texture.json").write_text(json.dumps({
        "resource_pack_name": "barkan",
        "texture_name": "atlas.items",
        "texture_data": texture_data,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    mcpack = OUT / "barkan_bedrock.mcpack"
    if mcpack.exists():
        mcpack.unlink()
    with zipfile.ZipFile(mcpack, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(stage.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(stage))
    print(f"✅ {mcpack}  ({mcpack.stat().st_size // 1024} KB)")
    print(f"✅ {old_path}")
    print("\n배포: bedrock_pack_deploy.sh <dev|prod>")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-px", type=int, default=128,
                    help="텍스처 최대 변 길이(기본 128 — 물고기와 같은 규격)")
    a = ap.parse_args()
    sys.exit(build(a.dry_run, a.max_px))
