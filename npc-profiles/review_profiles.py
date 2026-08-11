#!/usr/bin/env python3
"""Objective QA for the generated dialogue portrait pack."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "npc-profiles"
OUT = PACK / "review"


def main() -> int:
    manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    checks = []
    bases = []
    for npc in manifest["npcs"]:
        base_rel = next(x for x in npc["files"] if x.endswith("__base.png"))
        base_path = ROOT / base_rel
        im = Image.open(base_path).convert("RGBA")
        alpha = im.getchannel("A")
        nontransparent = sum(1 for p in alpha.getdata() if p)
        corners = [alpha.getpixel(p) for p in ((0, 0), (127, 0), (0, 127), (127, 127))]
        variant_diffs = []
        for rel in npc["files"]:
            if rel.endswith("__base.png"):
                continue
            other = Image.open(ROOT / rel).convert("RGBA")
            variant_diffs.append(sum(a != b for a, b in zip(im.getdata(), other.getdata())))
        checks.append({"cid": npc["citizensId"], "npc": npc["npc"], "size": im.size,
                       "mode": im.mode, "nontransparent": nontransparent,
                       "transparent_corners": corners == [0, 0, 0, 0],
                       "expression_diffs": variant_diffs})
        bases.append((npc, im))

    cols, cell_w, cell_h = 12, 112, 132
    rows = (len(bases) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell_w, rows * cell_h), (39, 37, 45, 255))
    draw = ImageDraw.Draw(sheet)
    for i, (npc, im) in enumerate(bases):
        x, y = (i % cols) * cell_w, (i // cols) * cell_h
        thumb = im.resize((96, 96), Image.Resampling.NEAREST)
        sheet.alpha_composite(thumb, (x + 8, y + 4))
        draw.text((x + 4, y + 104), str(npc["citizensId"]).zfill(3), fill=(232, 216, 180, 255))
    sheet.save(OUT / "base-contact-sheet.png")

    report = {
        "npc_count": len(checks),
        "missing_from_manifest": manifest.get("missing", []),
        "bad_dimensions": [x for x in checks if x["size"] != (128, 128)],
        "bad_mode": [x for x in checks if x["mode"] != "RGBA"],
        "bad_transparency": [x for x in checks if not x["transparent_corners"]],
        "blank": [x for x in checks if x["nontransparent"] < 500],
        "variants_without_change": [x for x in checks if any(d == 0 for d in x["expression_diffs"])],
        "assets_checked": sum(len(x["files"]) for x in manifest["npcs"]),
    }
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not any((report[k] for k in ("missing_from_manifest", "bad_dimensions", "bad_mode", "bad_transparency", "blank", "variants_without_change"))) else 1


if __name__ == "__main__":
    raise SystemExit(main())
