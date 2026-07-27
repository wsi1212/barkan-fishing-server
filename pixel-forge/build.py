#!/usr/bin/env python3
# 매니페스트 단일 파이프라인: manifest.json -> 스프라이트(painters) -> 린트 -> 모델(cross/voxel)
# -> CE 텍스처/모델 배치 -> configuration/forage_custom.yml 생성. 멱등(재실행 안전).
# 배포는 별도: devrcon "ce reload all".
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(HERE, "..", ".claude", "skills", "pixel-art", "scripts")
sys.path.insert(0, SKILL); sys.path.insert(0, HERE)
from painters import REGISTRY
from sprite_to_voxel import voxelize
from lint_sprite import lint
from render_textured import render as render3d, auto_camera, assert_camera_convention
from PIL import Image
BF = os.path.expanduser("~/Library/Application Support/feather/player-server/servers/"
                        "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/CraftEngine/resources/barkan_furniture")
# 아이템 한줄 설명(세계관 플레이버) 단일 소스 — BlockShip이 물고기/부품/재료에 쓰는 것과 같은 파일.
# 채집물 lore는 CraftEngine이 소유하므로 여기서 읽어 yml에 굽는다(원문은 item-flavor.json 한 곳에만 존재).
FLAVOR_JSON = os.path.expanduser("~/Library/Application Support/feather/player-server/servers/"
                                 "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip/item-flavor.json")
FLAVOR_WRAP = 30   # ItemFlavor.WRAP 과 동일하게 유지할 것


def load_flavor(category):
    try:
        return json.load(open(FLAVOR_JSON, encoding="utf-8")).get(category, {}) or {}
    except Exception:
        return {}


def flavor_lore(flavor, name):
    """설명 → CE lore 줄 리스트(회색, 이탤릭 해제). 없으면 빈 리스트."""
    text = (flavor.get(name) or "").strip()
    if not text:
        return []
    lines, cur = [], ""
    for word in text.split():
        if not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= FLAVOR_WRAP:
            cur += " " + word
        else:
            lines.append(cur); cur = word
    if cur:
        lines.append(cur)
    return [f'        - "<!i><gray>{l}</gray>"' for l in lines]

# (X자 크로스 템플릿은 2026-07-17 유저 결정으로 삭제 — 평면 2장 금지, modelkit boxes가 기본)

COLOR_KEYS = {"base", "cap", "stem", "petal", "center", "spot", "glow"}

def lint_shape_diversity(mf):
    """색칠놀이 하드가드(유저 지시 2026-07-17): 같은 페인터를 색 파라미터만 바꿔 재사용하면 빌드 실패.
    같은 종족이라도 실루엣이 달라야 함 — 변형은 seed(형태 변주)나 별도 페인터로."""
    groups = {}
    for it in mf["items"]:
        fn, kw = REGISTRY[it["painter"]]
        groups.setdefault(fn.__name__, []).append((it["id"], it["painter"], kw))
    bad = []
    for fname, uses in groups.items():
        if len(uses) < 2: continue
        shape_kw = [{k: v for k, v in kw.items() if k not in COLOR_KEYS} for _, _, kw in uses]
        if all(sk == shape_kw[0] for sk in shape_kw):
            bad.append(f"{fname}: " + ", ".join(u[0] for u in uses))
    if bad:
        raise SystemExit("✗ 색칠놀이 감지(같은 실루엣 + 색만 교체) — 실루엣을 분화하거나 형태 파라미터를 바꿀 것:\n  " + "\n  ".join(bad))

def main():
    mf = json.load(open(os.path.join(HERE, "manifest.json")))
    flavor = load_flavor("채집")
    lint_shape_diversity(mf)
    assert_camera_convention()   # pitch 양수=조감 회귀 방지 (2026-07-18 벌레시점 아이콘 사고)
    g, pfx = mf["group"], mf["prefix"]
    mdl_dir = f"{BF}/resourcepack/assets/barkan/models/item/furniture/{g}"
    tex_dir = f"{BF}/resourcepack/assets/barkan/textures/furniture/{g}"
    os.makedirs(f"{mdl_dir}/icon", exist_ok=True); os.makedirs(f"{tex_dir}/icon", exist_ok=True)
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    cfg = [f"# pixel-forge 생성 — 직접 제작 채집물 (manifest.json이 단일 소스)\nitems:\n"]
    for it in mf["items"]:
        iid = pfx + it["id"]; fn, kw = REGISTRY[it["painter"]]
        res = fn(**kw, seed=it.get("seed", 0))
        im, box_els = res if isinstance(res, tuple) else (res, None)
        out_png = os.path.join(HERE, "out", iid + ".png"); im.save(out_png)
        if it["model"] != "boxes":                       # boxes의 텍스처는 아틀라스라 스프라이트 린트 비적용
            for w in lint(out_png, it.get("plant", False)): print(f"  ⚠ {iid}: {w}")
        tex_ref = f"barkan:furniture/{g}/{iid}"
        import shutil; shutil.copy(out_png, f"{tex_dir}/{iid}.png")
        if it["model"] == "cross":
            raise SystemExit(f"✗ {iid}: 'cross' 모델은 금지됨(유저 결정 2026-07-17) — X자 평면은 부피가 없어 퀄이 낮음. 'boxes'(modelkit)로 만들 것.")
        elif it["model"] == "voxel": model = voxelize(out_png, tex_ref)
        else:                        model = {"textures": {"0": tex_ref, "particle": tex_ref}, "elements": box_els,
                                              "display": {"fixed": {"rotation": [0,0,0], "translation": [0,0,0], "scale": [1,1,1]}}}
        json.dump(model, open(f"{mdl_dir}/{iid}.json", "w"), indent=1)
        # GUI 아이콘: 형태 기반 자동 카메라(auto_camera)로 3/4뷰 렌더 → 잘라내기 → 32px 스프라이트.
        # 가시면 감사: 최종 이미지에서 밑면(down)이 25%+ 보이면 벌레시점으로 간주하고 빌드 실패
        # (예외 품목만 manifest icon_pitch/icon_yaw로 명시 오버라이드).
        icon_raw = os.path.join(HERE, "out", iid + "_icon_raw.png")
        ayaw, apitch, aklass = auto_camera(model["elements"])
        yv, pv = it.get("icon_yaw", ayaw), it.get("icon_pitch", apitch)
        st = render3d(f"{mdl_dir}/{iid}.json", f"{tex_dir}/{iid}.png", icon_raw, yaw=yv, pitch=pv, size=256)
        downr = st["down"] / (sum(st.values()) or 1)
        if downr > 0.25:
            raise SystemExit(f"✗ {iid}: 아이콘이 벌레시점(밑면 {downr:.0%} 노출, 카메라 {aklass} p{pv}) — "
                             "모델 형태를 확인하거나 manifest에 icon_pitch를 명시할 것")
        ic = Image.open(icon_raw).convert("RGBA")
        bb = ic.getbbox(); ic = ic.crop(bb) if bb else ic
        side = max(ic.size); sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        sq.paste(ic, ((side-ic.width)//2, (side-ic.height)//2), ic)
        ic = sq.resize((30, 30), Image.LANCZOS)
        pad = Image.new("RGBA", (32, 32), (0, 0, 0, 0)); pad.paste(ic, (1, 1), ic)
        px = pad.load()
        for yy in range(32):
            for xx in range(32):
                r_, g_, b_, a_ = px[xx, yy]
                px[xx, yy] = (r_, g_, b_, 255 if a_ > 96 else 0)   # 알파 이진화 = 경계 크리스프
        for yy in range(32):                                        # selout: 경계 픽셀을 동색 어둡게(×0.55)
            for xx in range(32):                                    # — 슬롯 배경 대비 아웃라인(바닐라 관행)
                if px[xx, yy][3] != 255: continue
                if any(not (0 <= xx+dx < 32 and 0 <= yy+dy < 32) or px[xx+dx, yy+dy][3] == 0
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    r_, g_, b_, _ = px[xx, yy]
                    px[xx, yy] = (int(r_*0.55), int(g_*0.55), int(b_*0.55), 255)
        pad.save(f"{tex_dir}/icon/{iid}.png"); os.remove(icon_raw)
        json.dump({"parent": "minecraft:item/generated",
                   "textures": {"layer0": f"barkan:furniture/{g}/icon/{iid}"}},
                  open(f"{mdl_dir}/icon/{iid}.json", "w"), indent=1)
        sc = it.get("scale", 1.0)
        ymin = min(e["from"][1] for e in model["elements"])
        ty = round(sc * (8 - ymin) / 16, 3)
        region = it.get("region", "평원"); matid = it["name"].replace(" ", "")
        rarity = it.get("rarity", "흔함")
        ncol = {"흔함": "white", "희귀": "aqua", "전설": "gold"}.get(rarity, "white")
        # 세계관 한줄 설명 — [채집] 태그 바로 아래, 서식지/등급 위 (BlockShip 아이템 lore 규약과 동일 순서)
        desc = flavor_lore(flavor, it["name"])
        desc_block = ("\n".join(desc) + "\n        - \"\"\n") if desc else ""
        cfg.append(f"""  barkan:{g}_{iid}:
    data:
      item_name: "<!i><{ncol}>{it['name']}</{ncol}>"
      lore:
        - "<!i><dark_gray>[채집]</dark_gray>"
{desc_block}        - "<!i><gray>서식지: <white>{region}</white>  <dark_gray>·</dark_gray>  등급: <{ncol}>{rarity}</{ncol}></gray>"
        - "<!i><dark_gray>mat:채집_{matid}</dark_gray>"
    model:
      type: minecraft:select
      property: minecraft:display_context
      cases:
        - when: gui
          model:
            type: minecraft:model
            model: barkan:item/furniture/{g}/icon/{iid}
      fallback:
        type: minecraft:model
        model: barkan:item/furniture/{g}/{iid}
    behavior:
      type: furniture_item
      rules:
        ground: {{rotation: any, alignment: center}}
      furniture:
        events:
          - template: default:rotatable_furniture_8
        settings:
          item: barkan:{g}_{iid}
          hit_times: 1
          sounds: {{break: minecraft:block.{it['sound']}.break, place: minecraft:block.{it['sound']}.place, hit: minecraft:block.{it['sound']}.hit}}
        variants:
          ground:
            elements:
              - item: barkan:{g}_{iid}
                display_transform: FIXED
                billboard: FIXED
                translation: 0,{ty},0
                scale: {sc}
            hitboxes:
              - position: 0,0,0
                type: interaction
                invisible: true
                blocks_building: true
                interactive: true
                width: 0.8
                height: 1.0
        loot:
          template: default:loot_table/furniture
          arguments: {{item: barkan:{g}_{iid}}}
""")
        print(f"  ✔ {iid}: {it['model']} ({len(model['elements'])} elem, ty={ty}) | icon {aklass} y{yv} p{pv} 밑면{downr:.0%}")
    open(f"{BF}/configuration/forage_custom.yml", "w").write("\n".join(cfg))
    # 채집 시스템용 종류 정의 (ForageManager가 읽음) — manifest 단일 소스
    types = {}
    for it in mf["items"]:
        rarity = it.get("rarity", "흔함")
        types[f"barkan:{g}_{pfx}{it['id']}"] = {
            "name": it["name"], "region": it.get("region", "평원"), "rarity": rarity,
            "cooldownSec": it.get("cooldownSec", 72000 if rarity == "희귀" else 5400)}
    plug = os.path.expanduser("~/Library/Application Support/feather/player-server/servers/"
                              "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip/forage-types.json")
    json.dump(types, open(plug, "w"), ensure_ascii=False, indent=1)
    print(f"forage-types.json: {len(types)}종 (흔함 1.5h / 희귀 20h)")
    missing = [it["name"] for it in mf["items"] if not (flavor.get(it["name"]) or "").strip()]
    if missing:
        print(f"  ⚠ 한줄 설명 없음 {len(missing)}종 (item-flavor.json '채집'): " + ", ".join(missing))
    print(f"OK — {len(mf['items'])}종. 다음: devrcon 'ce reload all'")

if __name__ == "__main__":
    main()
