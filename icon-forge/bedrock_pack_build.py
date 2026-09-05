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

import yaml
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
#   ★낚싯대는 «완성품» 이 minecraft:fishing_rod 다(EquipmentManager.buildRodResult).
#     partIcon 기본값(PAPER)만 보고 paper 로 잡았다가 낚싯대만 베드락에서 바닐라
#     텍스처로 나왔다(2026-09-04 유저 제보). 조합대 미리보기 등 paper 로 뜨는 경로도
#     있어 «둘 다» 등록한다 — 리스트를 주면 각각 다른 bedrock_identifier 로 나간다.
BASE_ITEM = {
    "rod": ["minecraft:fishing_rod", "minecraft:paper"],
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


PLUGIN_SRC = Path(os.path.expanduser("~/development/blockship-plugin/src/main/java/com/blockship"))

# 코드에서 규칙이 명확한 계열 — 스캔이 놓쳐도 여기서 확정한다.
EXPLICIT_PREFIX = {
    "recipe_": "minecraft:paper",   # PartShopGui.withRecipeModel — 레시피 두루마리는 종이
    "crop_": "minecraft:paper",     # CropSpecs.ITEM_BASE
}


def scan_source_bases() -> dict[str, str]:
    """플러그인 소스에서 «아이콘 → 베이스 아이템» 쌍을 긁어낸다.

    ★GUI 아이콘(skill_*·ui_* 등 500여 종)은 화면마다 다른 바닐라 아이템 위에 얹힌다.
      표를 손으로 관리하면 새 아이콘이 추가될 때마다 조용히 빠지므로 «코드를 읽어»
      맞춘다. 못 찾은 것은 등록하지 않는다 — 틀린 베이스로 등록하면 어차피 매칭되지
      않고 매핑만 부풀기 때문이다.
    """
    import re
    out: dict[str, str] = {}
    if not PLUGIN_SRC.is_dir():
        return out
    # GuiIcons.custom("모델", Material.XXX  /  icon("모델", Material.XXX
    pat = re.compile(r'(?:GuiIcons\.)?custom\(\s*"([A-Za-z0-9_/]+)"\s*,\s*Material\.([A-Z_]+)')
    # applyRaw(meta, "barkan_icon/모델") 앞쪽 6줄 안의 new ItemStack(Material.XXX)
    raw = re.compile(r'applyRaw\([^,]+,\s*"barkan_icon/([A-Za-z0-9_/]+)"')
    mat = re.compile(r'new ItemStack\(\s*(?:org\.bukkit\.)?Material\.([A-Z_]+)')
    for f in PLUGIN_SRC.rglob("*.java"):
        try:
            lines = f.read_text(encoding="utf-8").split("\n")
        except Exception:
            continue
        for i, line in enumerate(lines):
            for m in pat.finditer(line):
                out.setdefault(m.group(1).split("/")[-1], f"minecraft:{m.group(2).lower()}")
            for m in raw.finditer(line):
                icon = m.group(1).split("/")[-1]
                for j in range(max(0, i - 6), i + 1):
                    mm = mat.search(lines[j])
                    if mm:
                        out.setdefault(icon, f"minecraft:{mm.group(1).lower()}")
                        break
    return out


CE_ROOT = SERVER / "plugins/CraftEngine/resources/barkan_furniture"
# 플레이어가 «들고 다니는» CE 아이템만 — 가구 라이브러리까지 넣으면 팩이 15MB 를 넘어
# 베드락 접속 자체가 실패한다(_emit_texture 주석 참조).
CE_CONFIGS = ["dishes.yml", "food_library.yml", "forage_custom.yml"]


def _ce_default_material() -> str:
    """CE 아이템에 {@code material} 이 없을 때의 베이스. CraftEngine config 를 읽는다.

    ★값을 여기 적어 두지 않는다 — 2026-09-06 시점 prod 는 {@code nether_brick} 이고,
      채집물 31종이 material 을 안 적어서 «베드락에서 네더벽돌» 로 보였다. 운영자가 이 설정을
      바꾸면 베이스가 통째로 달라지므로 설정을 따라간다.
    """
    cfg = SERVER / "plugins/CraftEngine/config.yml"
    try:
        for line in cfg.read_text(encoding="utf-8").split("\n"):
            m = re.match(r'\s*default-material:\s*"?([a-z0-9_]+)"?', line)
            if m:
                return m.group(1)
    except Exception:
        pass
    return "nether_brick"


def _ce_gui_model(model):
    """CE 의 {@code model:} 은 문자열이거나 select 구조다.

    채집물은 «GUI 에서는 2D 아이콘, 바닥에 놓으면 3D» 라 select 로 갈라 둔다. 베드락은 인벤
    아이콘만 필요하므로 gui 케이스를 먼저 찾고, 없으면 fallback 을 쓴다.
    ★구버전 파서는 {@code model:} 뒤에 값이 오는 줄만 읽어서 이 구조를 통째로 놓쳤고,
      그래서 채집물이 매핑에서 조용히 빠져 있었다.
    """
    if isinstance(model, str):
        return model
    if not isinstance(model, dict):
        return None
    for case in model.get("cases") or []:
        when = case.get("when")
        if when == "gui" or (isinstance(when, list) and "gui" in when):
            got = _ce_gui_model(case.get("model"))
            if got:
                return got
    for key in ("model", "fallback"):
        if key in model:
            got = _ce_gui_model(model[key])
            if got:
                return got
    return None


def collect_craftengine() -> tuple[list[dict], list[str]]:
    """CraftEngine 아이템(요리·채집물 등) — CE 는 Geyser 연동이 없어 베드락에서 바닐라로 보인다.

    CE 아이템도 자바에선 {@code item_model} 로 그려진다(생성 팩의
    {@code assets/barkan/items/<id>.json} 이 그 증거). 그래서 우리 매핑에 그대로 넣을 수 있다.
    · 베이스     = configuration/*.yml 의 {@code material}, 없으면 CE {@code default-material}
    · item_model = barkan:<id>
    · 텍스처     = {@code model:} 이 가리키는 모델(select 면 gui 케이스)의 layer0
    """
    out: list[dict] = []
    warns: list[str] = []
    if not CE_ROOT.is_dir():
        return out, ["CraftEngine 리소스 폴더 없음 — 요리 아이콘을 건너뜁니다"]
    rp = CE_ROOT / "resourcepack/assets"
    default_mat = _ce_default_material()

    def texture_of(model_id: str) -> Path | None:
        # barkan:item/food/pasta → assets/barkan/models/item/food/pasta.json → layer0
        if not model_id or ":" not in model_id:
            return None
        ns, path = model_id.split(":", 1)
        mj = rp / ns / "models" / f"{path}.json"
        if not mj.is_file():
            return None
        try:
            j = json.loads(mj.read_text(encoding="utf-8"))
        except Exception:
            return None
        tex = j.get("textures") or {}
        tid = tex.get("layer0") or next(iter(tex.values()), None)
        if not tid or ":" not in str(tid):
            return None
        tns, tpath = str(tid).split(":", 1)
        png = rp / tns / "textures" / f"{tpath}.png"
        return png if png.is_file() else None

    for name in CE_CONFIGS:
        f = CE_ROOT / "configuration" / name
        if not f.is_file():
            continue
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except Exception as e:
            warns.append(f"{name} 파싱 실패 — 건너뜁니다: {e}")
            continue
        got = 0
        for ident_full, spec in (doc.get("items") or {}).items():
            if not isinstance(spec, dict) or ":" not in str(ident_full):
                continue
            mat = spec.get("material") or default_mat
            png = texture_of(_ce_gui_model(spec.get("model")))
            if not png:
                continue
            ident = str(ident_full).split(":", 1)[1]
            out.append({
                "icon": f"ce_{ident}",
                "model": f"{NS}:{ident}",
                "bases": [f"minecraft:{mat}"],
                "label": f"CE {ident}",
                "texture": png,
            })
            got += 1
        warns.append(f"  {name}: {got}종")
    warns.append(f"CraftEngine 아이템 {len(out)}종 등록 (기본 베이스 minecraft:{default_mat})")
    return out, warns


def _seed_pack() -> Path | None:
    """텍스처를 «승계» 해 올 팩. 물고기 486종은 생성기가 없는 원본 입력이라 씨앗에서 가져온다."""
    p = HERE / "seed/fish_pack_original.mcpack"
    if p.is_file():
        return p
    p = SERVER / "plugins/Geyser-Spigot/packs/barkan_bedrock.mcpack"
    return p if p.is_file() else None


def _seed_texture_keys() -> set[str]:
    """씨앗 팩이 실제 PNG 까지 갖고 있는 아이콘 키. 승계 매핑을 거르는 기준이 된다."""
    pk = _seed_pack()
    if not pk:
        return set()
    try:
        with zipfile.ZipFile(pk) as z:
            td = json.loads(z.read("textures/item_texture.json"))["texture_data"]
            names = set(z.namelist())
            return {k for k, v in td.items()
                    if isinstance(v, dict) and f"{v.get('textures')}.png" in names}
    except Exception:
        return set()


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

    scanned = scan_source_bases()
    families = {v: k for k, v in TYPE_KEY.items()}   # rod -> 낚싯대 …

    # ① 카탈로그 외 아이콘(레시피 두루마리·특수작물·GUI 아이콘 등)
    extra = 0
    for f in sorted(defs_dir.glob("*.json")):
        icon = f.stem
        if icon.startswith("catalog_"):
            continue
        base = None
        for pre, b in EXPLICIT_PREFIX.items():
            if icon.startswith(pre):
                base = b
                break
        if base is None:
            base = scanned.get(icon)
        if base is None:
            continue                      # 베이스를 모르면 등록하지 않는다(틀린 등록은 무용지물)
        extra += 1
        entries.append({
            "icon": icon,
            "model": f"{NS}:barkan_icon/{icon}",
            "bases": [base],
            "label": icon,
        })
    warns.append(f"카탈로그 외 아이콘 {extra}종 등록 (정의 {len(list(defs_dir.glob('*.json'))) - len(list(defs_dir.glob('catalog_*.json')))}종 중)")

    # ② 카탈로그
    for f in sorted(defs_dir.glob("catalog_*.json")):
        icon = f.stem
        fam = icon.split("_")[1] if icon.count("_") >= 2 else None
        if fam not in BASE_ITEM:
            warns.append(f"모르는 계열 건너뜀: {icon}")
            continue
        base = harpoon_base.get(icon, BASE_ITEM[fam][0] if isinstance(BASE_ITEM[fam], list)
                                else BASE_ITEM[fam]) if fam == "harpoon" else BASE_ITEM[fam]
        bases = base if isinstance(base, list) else [base]
        entries.append({
            "icon": icon,
            "model": f"{NS}:barkan_icon/{icon}",
            "bases": bases,
            "label": labels.get(icon, f"{families.get(fam, fam)} ?({icon})"),
        })
    ce, cw = collect_craftengine()
    entries.extend(ce)
    warns.extend(cw)
    return entries, warns


def _emit_texture(src: Path, dst: Path, max_px: int) -> None:
    """텍스처 1장 — 필요하면 축소해서 쓴다.

    ★카탈로그 아이콘은 512/256px 로 그려져 있는데(물고기는 128) 베드락은 이걸 인벤토리
      한 칸에 그린다. 원본 그대로 넣으면 팩이 28MB 가 되어 모바일 첫 접속이 그만큼 길어진다.
      ★★크기가 «접속 가능 여부»를 가른다(2026-09-04 실측). 128px(15MB) 팩은 베드락
      클라가 받다가 연결을 끊어 «오류가 발생했습니다» 로 접속 자체가 실패했다. 64px(5.9MB)
      로 내리자 정상 접속 + 아이콘 표시. 여태 잘 돌던 물고기 전용 팩이 5.5MB 였다.
      정확한 임계값은 모르지만 6MB 대는 안전하고 15MB 는 안 된다 — 기본값을 올리지 말 것.
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


def build(dry: bool, max_px: int = 64, bedrock_hud: bool = False) -> int:
    entries, warns = collect()
    for w in warns:
        print(f"  ⚠ {w}")

    resolved, missing = [], []
    for e in entries:
        if e.get("texture"):          # CE 항목은 수집 때 이미 실물 경로를 안다
            resolved.append(e)
            continue
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
        for i, base in enumerate(e["bases"]):
            # 같은 아이콘을 여러 베이스에 달 때 식별자가 겹치면 안 된다 — 두 번째부터 접두어.
            bid = f"{NS}:{e['icon']}" if i == 0 else f"{NS}:b{i}_{e['icon']}"
            put(base, {
                "type": "definition",
                "model": e["model"],
                "bedrock_identifier": bid,
                "bedrock_options": {"icon": e["icon"], "creative_category": "items"},
            })
    # ★승계는 «텍스처까지 따라올 수 있는 것» 만. 코드에서 사라진 아이콘(예: 더는 쓰지 않는
    #   GUI 버튼)이 옛 매핑에 남아 있으면, 정의만 있고 그림이 없는 항목이 되어 자기검증이
    #   배포를 통째로 막는다. 2026-09-06 실측: ui_guild_chat 하나가 그렇게 팩 생성을 세웠다.
    seed_keys = _seed_texture_keys()
    fresh_icons = {e["icon"] for e in resolved}
    carried_defs = 0
    dropped: list[str] = []
    for base, defs in legacy.items():
        for entry in defs:
            icon = entry.get("bedrock_options", {}).get("icon")
            if icon and icon not in fresh_icons and icon not in seed_keys:
                dropped.append(icon)
                continue
            if put(base, entry):
                carried_defs += 1
    if dropped:
        print(f"  ⚠ 텍스처가 사라져 승계에서 뺀 옛 정의 {len(dropped)}개: {', '.join(dropped[:8])}")

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

    # ── manifest ────────────────────────────────────────────────────────────
    #   ★uuid 는 «고정», version 은 «내용이 바뀌면 반드시 올라가야» 한다.
    #     베드락 클라는 (uuid, version) 으로 캐시한다. 둘 다 그대로면 팩을 다시 받지 않고
    #     캐시본을 쓴다 — 2026-09-04 실측: 아이콘 548종을 넣었는데 폰에서 «다운로드 안내도

    texture_data = {}
    for e in resolved:
        _emit_texture(e["texture"], stage / "textures/items" / f"{e['icon']}.png", max_px)
        texture_data[e["icon"]] = {"textures": f"textures/items/{e['icon']}"}

    # ── 기존(물고기) 텍스처 승계 ─────────────────────────────────────────────
    #   ★파일명이 아니라 «옛 item_texture.json 의 키→경로» 를 그대로 가져온다.
    #     물고기는 키가 fish_<이름> 인데 파일은 textures/items/fish/<이름>.png 에 있다.
    #     파일명으로 키를 다시 만들면 접두어가 사라져 매핑이 끊기고 — 2026-09-04 실측 —
    #     물고기 486종이 통째로 투명해진다. 남의 규칙을 추측하지 말고 있는 그대로 옮긴다.
    #   ★씨앗은 seed/fish_pack_original.mcpack — 물고기 팩은 «생성기가 없는» 원본 입력이라
    #     레포에 그대로 둔다(libs/*.jar 과 같은 취급). 배포된 팩을 씨앗으로 삼으면 한 번
    #     잘못 만든 팩이 다음 판의 입력이 되어 오류가 눌러앉는다 — 실제로 그렇게 됐었다.
    prev = _seed_pack()
    carried = 0
    if prev and prev.is_file():
        with zipfile.ZipFile(prev) as z:
            try:
                old_td = json.loads(z.read("textures/item_texture.json"))["texture_data"]
            except Exception:
                old_td = {}
            names = set(z.namelist())
            for key, val in old_td.items():
                if key in texture_data:
                    continue
                rel = val.get("textures") if isinstance(val, dict) else None
                if not rel:
                    continue
                src = f"{rel}.png"
                if src not in names:
                    continue
                dst = stage / src
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(z.read(src))
                _emit_texture(dst, dst, max_px)
                texture_data[key] = {"textures": rel}
                carried += 1
    print(f"▶ 텍스처 {len(texture_data)}장 (신규 {len(resolved)} + 기존 승계 {carried})")

    # ── manifest ────────────────────────────────────────────────────────────
    #   ★uuid 는 «고정», version 은 «내용이 바뀌면 반드시 올라가야» 한다.
    #     베드락 클라는 (uuid, version) 으로 캐시한다. 둘 다 그대로면 팩을 다시 받지 않고
    #     캐시본을 쓴다 — 2026-09-04 실측: 아이콘을 548종 넣었는데 폰에서 «다운로드 안내도
    #     안 뜨고 아이템이 투명» 했다. 옛 팩이 그대로 쓰이고 있었던 것.
    #   ★해시는 «스테이징이 다 끝난 뒤» 실제 산출물에서 뽑는다. 원본 텍스처만 해싱했다가
    #     축소 크기·승계 방식을 바꿔도 버전이 그대로여서 같은 사고를 두 번 더 냈다.
    # ── JSON UI 덮어쓰기 ─────────────────────────────────────────────────────
    #   ★사이드바 오른쪽의 «빨간 점수 숫자» 를 지운다.
    #     자바 1.20.3+ 의 number_format=blank(SidebarManager 가 이미 쓴다) 는 자바 클라에서만
    #     듣는다. Geyser 2.11.2 실측(SidebarDisplayScore.update): FixedFormat 만 처리하고
    #     BlankFormat 은 «무시» 한 채 ScoreInfo 에 점수 정수를 그대로 실어 보낸다. 베드락 클라는
    #     받은 점수를 항상 그린다 → 서버에서는 끌 방법이 없고 클라 UI 를 덮어써야 한다.
    #   베드락 JSON UI 는 같은 경로의 파일을 «최상위 컨트롤 단위로» 병합한다. 그래서 바꿀
    #   컨트롤 하나만 적으면 되고 나머지 사이드바(제목·이름줄·일시정지 화면 명단)는 바닐라 그대로다.
    #   ★locked_alpha 를 쓰지 말 것 — 알파를 그 값으로 «고정» 해서 숨김이 풀린다.
    #   원본: Mojang/bedrock-samples resource_pack/ui/scoreboards.json 의
    #        scoreboard.scoreboard_sidebar_score (label, text="#player_score_sidebar")
    ui_files = {
        "ui/scoreboards.json": {
            "namespace": "scoreboard",
            # 바꿀 속성만 적는다(위 ★★ 참조). text 를 비우면 그릴 게 없고, 폭 0 이면
            # 오른쪽 여백도 사라진다. ★locked_alpha 는 알파를 고정하니 건드리지 않는다.
            "scoreboard_sidebar_score": {
                "text": "",
                "size": [0, 10],
            },
            # ★줄 폭 — 바닐라는 max_size 100px 라 퀘스트 안내·위치 줄이 베드락에서만 잘린다.
            #   Geyser 자체 팩(GeyserIntegratedPack, enable-integrated-pack: true 로 «항상 같이
            #   전송된다»)이 이미 250px 로 넓혀 두었다. 우리가 이 컨트롤을 건드리면 팩 적용
            #   순서에 따라 그 250 을 도로 좁힐 수 있어서, 같은 값을 명시해 어느 쪽이 이기든
            #   결과가 같게 만든다.
            # ★★통짜로 다시 쓰지 말 것 — Geyser 팩의 scoreboards.json 이 정확히 이 형태다:
            #   {"scoreboard_sidebar_player": {"max_size": [250, 10]}} — 바꿀 «속성만» 적는다.
            #   JSON UI 는 속성 단위로 병합되므로 type·bindings 를 다시 쓸 이유가 없고,
            #   다시 쓰면 바닐라가 나중에 바꾼 속성을 우리가 낡은 값으로 덮어쓰게 된다.
            "scoreboard_sidebar_player": {
                "max_size": [250, 10],
            },
        },
    }

    # ── 베드락 전용 HUD 실험 (--bedrock-hud, 기본 꺼짐) ──────────────────────
    #   BetterHud 는 자바 리소스팩의 음수 폭 space 글리프로 그림을 겹쳐 그린다. 베드락
    #   글리프는 16×16 고정 셀이라 음수 전진값이 없어 합성 자체가 성립하지 않고, BetterHud
    #   자신도 disable-to-bedrock-player: true 로 베드락에는 HUD 를 보내지 않는다.
    #   베드락에서 «판» 을 그리려면 클라 UI 를 덮어쓰는 수밖에 없는데, JSON UI 가 서버에서
    #   받을 수 있는 문자열은 액션바($actionbar_text)·제목·부제목뿐이다. 그래서 서버
    #   (com.blockship.hud.BedrockHud)가 액션바로 세 줄을 보내고 여기서 자리만 옮긴다.
    #   ★서버 config 의 bedrock.hud-experiment 와 «짝» 이다. 팩만 넣으면 아무 일도 없고,
    #     서버만 켜면 액션바가 화면 한가운데 그대로 뜬다.
    if bedrock_hud:
        # ★v1 은 베드락 클라를 죽였다(2026-09-06 실측: 리소스팩 협상 단계에서 클라가 스스로
        #   끊음, 서버 로그엔 아무 단서도 안 남는다). v1 이 한 짓: hud_actionbar_text 를 통짜로
        #   다시 쓰고 **바닐라 애니메이션 두 개**(anim_actionbar_text_alpha_out /
        #   _background_alpha_out)까지 갈아엎었다. 그 애니메이션은 바닐라 팩토리가 참조하는
        #   공용 정의라 건드리면 안 된다 — 실제로 도는 남의 팩(TrippleAWap/Sidebar-HUD)도
        #   hud_actionbar_text 는 다시 쓰되 애니메이션은 «자기 이름으로 새로» 만든다.
        # ★v2 는 «바꿀 속성만» 적는다 — Geyser 자체 팩(GeyserIntegratedPack)의 hud_screen.json
        #   과 같은 idiom. 위치만 옮기고 애니메이션·팩토리·컨트롤 구조는 바닐라 그대로 둔다.
        #   페이드는 in_expo 3초라 «거의 끝까지 알파 1» 이고, 서버가 1초마다 다시 보내면
        #   매번 처음부터 재생돼 사실상 항상 떠 있다 → 애니메이션을 건드릴 이유가 없다.
        ui_files["ui/hud_screen.json"] = {
            "namespace": "hud",
            "hud_actionbar_text": {
                "anchor_from": "top_right",
                "anchor_to": "top_right",
                "offset": [-4, 4],
            },
        }

    for rel, doc in ui_files.items():
        dst = stage / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"▶ JSON UI 덮어쓰기 {len(ui_files)}개"
          + (" (사이드바 점수 숨김 + 베드락 HUD 실험)" if bedrock_hud else " (사이드바 점수 숨김)"))

    stamp = hashlib.sha1()
    stamp.update(f"max_px={max_px}".encode())
    stamp.update(json.dumps(mappings, sort_keys=True, ensure_ascii=False).encode())
    stamp.update(json.dumps(texture_data, sort_keys=True, ensure_ascii=False).encode())
    # ★UI 덮어쓰기도 해시에 넣는다 — 안 넣으면 UI 만 고쳤을 때 팩 버전이 그대로라
    #   클라가 캐시본을 쓰고 «고쳤는데 그대로» 가 된다(2026-09-04 아이콘 사고와 같은 원인).
    stamp.update(json.dumps(ui_files, sort_keys=True, ensure_ascii=False).encode())
    for f in sorted((stage / "textures").rglob("*.png")):
        stamp.update(str(f.relative_to(stage)).encode())
        stamp.update(f.read_bytes())
    rev = int(stamp.hexdigest()[:6], 16) % 100000
    print(f"▶ 팩 버전 1.0.{rev} (산출물 해시 — 바뀌면 클라가 다시 받는다)")

    manifest = {
        "format_version": 2,
        "header": {
            "name": "바르칸 열도 (베드락)",
            "description": "Geyser 커스텀 아이템 — 물고기·낚싯대·부품·재료 아이콘",
            "uuid": "2af7a31c-f3b7-5fd3-b260-d608317953ab",
            "version": [1, 0, rev],
            "min_engine_version": [1, 21, 0],
        },
        "modules": [{
            "type": "resources",
            "uuid": "654e8f2a-a98a-5429-9f2a-6660d8e60ed7",
            "version": [1, 0, rev],
        }],
    }
    (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                         encoding="utf-8")

    # ★item_texture.json 이 없으면 아이콘 이름이 해석되지 않아 전부 «보라/검정» 이 된다.
    (stage / "textures").mkdir(exist_ok=True)
    (stage / "textures/item_texture.json").write_text(json.dumps({
        "resource_pack_name": "barkan",
        "texture_name": "atlas.items",
        "texture_data": texture_data,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 자기검증 ────────────────────────────────────────────────────────────
    #   ★매핑의 icon 이 item_texture 키로 풀리고, 그 키가 실제 PNG 를 가리키는가.
    #     이 사슬이 한 칸만 끊겨도 «아이템은 있는데 투명» 이 된다 — 서버 로그엔 아무것도
    #     안 남아서 폰을 켜 보기 전엔 모른다. 2026-09-04 에 물고기 486종이 이렇게 날아갔다
    #     (키는 fish_<이름> 인데 파일은 fish/<이름>.png 라 파일명으로 키를 만들면 끊긴다).
    broken = []
    for base, defs in items.items():
        for d in defs:
            icon = d.get("bedrock_options", {}).get("icon")
            rel = texture_data.get(icon, {}).get("textures") if icon else None
            if not rel or not (stage / f"{rel}.png").is_file():
                broken.append(f"{base} / {icon}")
    if broken:
        print(f"❌ 매핑↔텍스처 사슬이 끊긴 항목 {len(broken)}개 — 팩을 만들지 않습니다")
        for b in broken[:10]:
            print(f"     · {b}")
        return 1
    print(f"✓ 자기검증 통과 — 정의 {sum(len(v) for v in items.values())}종 전부 텍스처까지 연결됨")

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
    ap.add_argument("--max-px", type=int, default=64,
                    help="텍스처 최대 변 길이(기본 64). ★올리지 말 것 — 아래 주석 참조")
    ap.add_argument("--bedrock-hud", action="store_true",
                    help="베드락 HUD 실험용 JSON UI 를 넣는다(dev 전용). "
                         "서버 config 의 bedrock.hud-experiment 와 짝이다")
    a = ap.parse_args()
    sys.exit(build(a.dry_run, a.max_px, a.bedrock_hud))
