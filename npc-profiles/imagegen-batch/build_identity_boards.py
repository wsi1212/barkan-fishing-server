#!/usr/bin/env python3
"""Build large identity references from the authoritative 64x64 NPC skins."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "npc-profiles" / "imagegen-batch" / "identity"
SKINS = ROOT / "skin-forge" / "out"
MANIFEST = ROOT / "npc-profiles" / "manifest.json"
RENDER = Path("/Users/user/.codex/skills/npc-skin-style-mirror/scripts/render_skin.py")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["npcs"]
    made = set()
    for item in manifest:
        stem = item["skin"]
        if stem in made:
            continue
        made.add(stem)
        skin_path = SKINS / f"{stem}.png"
        if not skin_path.exists():
            continue
        turn_path = OUT / f".{stem}_turn.png"
        subprocess.run(["python3", str(RENDER), str(skin_path), str(turn_path), "--scale", "12"], check=True, stdout=subprocess.DEVNULL)
        skin = Image.open(skin_path).convert("RGBA")
        turn = Image.open(turn_path).convert("RGBA")
        card = Image.new("RGB", (768, 768), (44, 47, 54))
        atlas = skin.resize((320, 320), Image.Resampling.NEAREST)
        card.paste(atlas, (32, 32), atlas)
        front_w = turn.width // 4
        front = turn.crop((0, min(32, turn.height // 10), front_w, turn.height))
        front = front.resize((400, round(front.height * 400 / front.width)), Image.Resampling.NEAREST)
        if front.height > 380:
            front = front.crop((0, 0, front.width, 380))
        card.paste(front, (352, 340), front)
        card.save(OUT / f"{stem}.png")
        turn_path.unlink(missing_ok=True)
    print(json.dumps({"identity_boards": len(made)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
