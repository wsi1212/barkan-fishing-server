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
BF = os.path.expanduser("~/Library/Application Support/feather/player-server/servers/"
                        "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/CraftEngine/resources/barkan_furniture")

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
    lint_shape_diversity(mf)
    g, pfx = mf["group"], mf["prefix"]
    mdl_dir = f"{BF}/resourcepack/assets/barkan/models/item/furniture/{g}"
    tex_dir = f"{BF}/resourcepack/assets/barkan/textures/furniture/{g}"
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
        sc = it.get("scale", 1.0)
        ymin = min(e["from"][1] for e in model["elements"])
        ty = round(sc * (8 - ymin) / 16, 3)
        region = it.get("region", "평원"); matid = it["name"].replace(" ", "")
        rarity = it.get("rarity", "흔함")
        ncol = {"흔함": "white", "희귀": "aqua", "전설": "gold"}.get(rarity, "white")
        cfg.append(f"""  barkan:{g}_{iid}:
    data:
      item_name: "<!i><{ncol}>{it['name']}</{ncol}>"
      lore:
        - "<!i><dark_gray>[채집]</dark_gray>"
        - "<!i><gray>서식지: <white>{region}</white>  <dark_gray>·</dark_gray>  등급: <{ncol}>{rarity}</{ncol}></gray>"
        - "<!i><dark_gray>mat:채집_{matid}</dark_gray>"
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
        print(f"  ✔ {iid}: {it['model']} ({len(model['elements'])} elem, ty={ty})")
    open(f"{BF}/configuration/forage_custom.yml", "w").write("\n".join(cfg))
    print(f"OK — {len(mf['items'])}종. 다음: devrcon 'ce reload all'")

if __name__ == "__main__":
    main()
