#!/usr/bin/env python3
"""icon-forge 매니페스트 파이프라인 — manifest.json → 아이콘 PNG(+애니 스트립/.mcmeta)
→ 린트 → 콘택트시트 + 슬롯 목업 + 애니 GIF → (--install) RP 텍스처/모델/items 정의 배치.

pixel-forge/build.py의 동생. 멱등(재실행 안전). 배포는 별도(deploy-rp / dev 8801 재빌드).
사용: python3 build.py [--install]
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ICON_SKILL = os.path.join(HERE, "..", ".claude", "skills", "item-icons", "scripts")
PIXEL_SKILL = os.path.join(HERE, "..", ".claude", "skills", "pixel-art", "scripts")
sys.path[:0] = [ICON_SKILL, PIXEL_SKILL, HERE]
from painters import REGISTRY                      # noqa: E402
from palette import ramp                           # noqa: E402
from fx import fire_aura, glow_halo, save_anim, save_gif  # noqa: E402
from icon_lint import lint                         # noqa: E402
import imagegen_cash                                # noqa: E402
import imagegen_256_pipeline                         # noqa: E402
import slot_preview                                # noqa: E402

RP = os.path.expanduser("~/development/barkan-resourcepack")

# 색칠놀이 하드가드(pixel-forge와 동일한 오너 규칙): 색 파라미터만 다른 페인터 재사용 금지
COLOR_KEYS = {"base", "grip", "line", "accent", "gold", "glass", "glow", "field"}


def lint_shape_diversity(mf):
    groups = {}
    for it in mf["items"]:
        if "source" in it:
            continue
        fn, kw = REGISTRY[it["painter"]]
        groups.setdefault(fn.__name__, []).append((it["id"], kw))
    bad = []
    for fname, uses in groups.items():
        if len(uses) < 2:
            continue
        shapes = [{k: v for k, v in kw.items() if k not in COLOR_KEYS} for _, kw in uses]
        if all(s == shapes[0] for s in shapes):
            bad.append(f"{fname}: " + ", ".join(u[0] for u in uses))
    if bad:
        raise SystemExit("✗ 색칠놀이 감지(같은 실루엣+색만 교체) — 실루엣을 분화할 것:\n  "
                         + "\n  ".join(bad))


def main(install=False):
    mf = json.load(open(os.path.join(HERE, "manifest.json")))
    lint_shape_diversity(mf)
    out = os.path.join(HERE, "out")
    os.makedirs(out, exist_ok=True)
    group = mf["group"]
    frame0_paths, total_warn = [], 0
    installs = []  # (id, 텍스처경로, 애니여부)

    for it in mf["items"]:
        iid, cat = it["id"], it.get("category", "prop")
        if "source" in it:
            source = os.path.join(HERE, it["source"])
            if it.get("pipeline") == "imagegen_256":
                base = imagegen_256_pipeline.prepare(source, size=it.get("size", 256))
            else:
                base = imagegen_cash.prepare(source)
        else:
            fn, kw = REGISTRY[it["painter"]]
            base = fn(**kw, seed=it.get("seed", 0))
        fxc = it.get("fx", {})
        allow_semi = 0
        anim_frames = None
        if "fire_aura" in fxc:
            fa = fxc["fire_aura"]
            anim_frames = fire_aura(base, ramp(fa["base"]), seed=it.get("seed", 1),
                                    frames=fa.get("frames", 4), density=fa.get("density", 5),
                                    y_max=fa.get("y_max", 11))
            display = anim_frames[0]
        elif "glow" in fxc:
            g = fxc["glow"]
            display = glow_halo(base, g["base"], alpha=g.get("alpha", 80),
                                seed=it.get("seed", 1), sparkles=g.get("sparkles", 2))
            allow_semi = 60
        else:
            display = base

        f0 = os.path.join(out, f"{iid}.png")
        display.save(f0)
        frame0_paths.append(f0)
        if anim_frames:
            strip = os.path.join(out, f"{iid}_anim.png")
            save_anim(anim_frames, strip, frametime=3)
            save_gif(anim_frames, os.path.join(out, f"{iid}_preview.gif"))
            installs.append((iid, strip, True))
        else:
            installs.append((iid, f0, False))

        warns = lint(f0, cat, allow_semi)
        total_warn += len(warns)
        print(f"{'✓' if not warns else '✗'} {iid} ({it['name']})")
        for w in warns:
            print(f"   - {w}")

    # 리뷰 산출물: 콘택트시트(라벨) + 슬롯 목업(실전 무대)
    subprocess.run([sys.executable, os.path.join(PIXEL_SKILL, "contact.py"),
                    *frame0_paths, os.path.join(out, "contact.png")], check=False)
    slot_preview.compose(frame0_paths, os.path.join(out, "slots.png"), scale=8)

    if install:
        tex_dir = f"{RP}/assets/minecraft/textures/item/{group}"
        mdl_dir = f"{RP}/assets/barkan/models/{group}"
        def_dir = f"{RP}/assets/barkan/items/{group}"
        for d in (tex_dir, mdl_dir, def_dir):
            os.makedirs(d, exist_ok=True)
        for iid, tex, anim in installs:
            dst = f"{tex_dir}/{iid}.png"
            with open(tex, "rb") as s, open(dst, "wb") as d:
                d.write(s.read())
            if anim:
                with open(tex + ".mcmeta") as s, open(dst + ".mcmeta", "w") as d:
                    d.write(s.read())
            elif os.path.exists(dst + ".mcmeta"):
                os.remove(dst + ".mcmeta")
            json.dump({"parent": "minecraft:item/generated",
                       "textures": {"layer0": f"minecraft:item/{group}/{iid}"}},
                      open(f"{mdl_dir}/{iid}.json", "w"))
            item_def = {"model": {"type": "minecraft:model", "model": f"barkan:{group}/{iid}"}}
            if it.get("oversized_in_gui"):
                item_def["oversized_in_gui"] = True
            json.dump(item_def, open(f"{def_dir}/{iid}.json", "w"))
        print(f"\nRP 배치 완료 → {RP} (item_model 키: barkan:{group}/<id>)")
        print("배포는 별도: dev=RP 재빌드+8801, prod=deploy-rp.sh(명시 요청 시만)")
    print(f"\n총 경고 {total_warn} | 리뷰: out/contact.png, out/slots.png, out/*_preview.gif")


if __name__ == "__main__":
    main(install="--install" in sys.argv)
