#!/usr/bin/env python3
"""Register and bake the reviewed 2026-08-24 portrait repairs.

The manifest source points at the high-resolution, chroma-clean panels.  The
BetterHUD filenames and keys stay unchanged; all 128x154 and size variants are
rebuilt from the source using the project's canonical framing function.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[3]
BETTERHUD = SCRIPTS / "ops" / "prod" / "betterhud"
ASSET = BETTERHUD / "assets" / "dialogue"
MANIFEST = SCRIPTS / "npc-profiles" / "npc-dialogue-portrait-manifest.json"
QUEUE = HERE / "queue.json"
FRAMED = HERE / "framed"
TRANSPARENT = HERE / "transparent"

spec = importlib.util.spec_from_file_location("gen", BETTERHUD / "gen_npc_portrait_huds.py")
gen = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gen)


def frame_rgba(src: Image.Image, cw: int, ch: int) -> Image.Image:
    box = src.getchannel("A").getbbox()
    if box is None:
        raise ValueError("empty alpha source")
    im = src.crop(box)
    vw = gen.VISIBLE[0] / gen.CANVAS[0] * cw
    vh = gen.VISIBLE[1] / gen.CANVAS[1] * ch
    k = min(vw / im.width, vh / im.height)
    size = (max(1, round(im.width * k)), max(1, round(im.height * k)))
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    out.alpha_composite(im.resize(size, Image.Resampling.LANCZOS), ((cw - size[0]) // 2, ch - size[1]))
    return out


def main() -> None:
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))["queue"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = {entry["citizensId"]: entry for entry in manifest["entries"]}
    changed = 0

    for item in queue:
        cid = item["citizensId"]
        entry = entries[cid]
        for state in item["states"]:
            source = TRANSPARENT / f"{cid:03d}_{state}.png"
            framed = FRAMED / f"{cid:03d}_{state}.png"
            if not source.exists() or not framed.exists():
                raise SystemExit(f"missing reviewed output for {cid} {state}")
            with Image.open(source) as raw:
                raw = raw.convert("RGBA")
                if raw.getchannel("A").getbbox() is None:
                    raise SystemExit(f"empty reviewed output for {cid} {state}")
                data = entry["states"][state]
                data["source"] = str(source)
                key = data["key"]
                frame_rgba(raw, *gen.CANVAS).save(ASSET / f"npc_{key}.png", optimize=True)
                for sid, scale in gen.SIZES:
                    dw = round(gen.CANVAS[0] * gen.PORTRAIT_SCALE * scale)
                    dh = round(gen.CANVAS[1] * gen.PORTRAIT_SCALE * scale)
                    hd = min(gen.HD, max(1.0, raw.width / max(1, dw)))
                    if round(1.0 / hd, 4) != round(1.0 / gen.HD, 4):
                        raise SystemExit(f"unexpected hd={hd} for {key}_{sid}")
                    gen.frame(raw, max(1, round(dw * hd)), max(1, round(dh * hd))).save(
                        ASSET / f"npc_{key}_{sid}.png", optimize=True
                    )
            changed += 1

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"rebuilt {changed} portrait states; manifest sources updated")


if __name__ == "__main__":
    main()
