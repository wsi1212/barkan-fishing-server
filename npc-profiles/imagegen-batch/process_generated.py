#!/usr/bin/env python3
"""Split ImageGen panels, remove chroma, and normalize a character's framing."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "npc-profiles" / "imagegen-batch" / "queue.json"
CHROMA = Path("/Users/user/.codex/skills/.system/imagegen/scripts/remove_chroma_key.py")
OUT_ROOT = ROOT / "npc-profiles" / "imagegen-out"


def safe(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", s).strip("_")


def remove_chroma(src: Path, dst: Path) -> None:
    subprocess.run([
        "python3", str(CHROMA), "--input", str(src), "--out", str(dst),
        "--auto-key", "border", "--soft-matte", "--transparent-threshold", "12",
        "--opaque-threshold", "220", "--despill",
    ], check=True, stdout=subprocess.DEVNULL)


def normalize(im: Image.Image, target_w: int = 1066, target_cx: int = 633, target_top: int = 37) -> Image.Image:
    im = im.convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        return im
    bw = bbox[2] - bbox[0]
    scale = target_w / bw
    scaled = im.resize((round(im.width * scale), round(im.height * scale)), Image.Resampling.LANCZOS)
    sb = scaled.getchannel("A").getbbox()
    sx = round(target_cx - (sb[0] + sb[2]) / 2)
    sy = round(target_top - sb[1])
    canvas = Image.new("RGBA", im.size, (0, 0, 0, 0))
    canvas.alpha_composite(scaled, (sx, sy))
    return canvas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=int, required=True)
    ap.add_argument("--source", type=Path, required=True)
    args = ap.parse_args()
    item = json.loads(QUEUE.read_text(encoding="utf-8"))["queue"][args.index]
    states = item["states"]
    out_dir = OUT_ROOT / f"{item['citizensId']:03d}_{safe(item['npc'])}"
    out_dir.mkdir(parents=True, exist_ok=True)
    work = out_dir / ".work"
    work.mkdir(exist_ok=True)
    source = Image.open(args.source).convert("RGBA")
    if item["layout"] == "grid2x2":
        w, h = source.size
        panels = [source.crop((0, 0, w // 2, h // 2)), source.crop((w // 2, 0, w, h // 2)),
                  source.crop((0, h // 2, w // 2, h)), source.crop((w // 2, h // 2, w, h))]
    else:
        panels = [source]
    for state, panel in zip(states, panels):
        chroma = work / f"{state}_chroma.png"
        raw = work / f"{state}_raw.png"
        panel.save(chroma)
        remove_chroma(chroma, raw)
        normalize(Image.open(raw), target_w=1066).save(out_dir / f"{state}.png")
    meta = {k: item[k] for k in ("citizensId", "npc", "displayName", "skin", "roles", "quests", "states", "dialogue_lines")}
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"npc": item["npc"], "out": str(out_dir), "states": states}, ensure_ascii=False))


if __name__ == "__main__":
    main()
