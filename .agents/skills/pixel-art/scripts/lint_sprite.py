#!/usr/bin/env python3
"""Objective pre-ship checks for a sprite. Catches the measurable amateur tells
so subjective critique can focus on form. Warnings, not a hard gate — but treat
each warning as something you must consciously accept.

Checks:
  colors   — distinct opaque colors (>12 = ramp discipline broke down)
  black    — pure #000/#fff pixels (use ramp ends, not pure)
  orphan   — opaque pixel with no opaque 4-neighbor (noise)
  margin   — sprite jammed against side/top canvas edge
  anchor   — (plants) nothing in bottom 2 rows = will float when placed
  contrast — mean luminance vs grass/dirt/sand/dark backgrounds (<25 = invisible)

Usage: python lint_sprite.py sprite.png [--plant]
Exit code = number of warnings (0 = clean).
"""
import sys
from PIL import Image

BGS = {"grass": (110, 156, 88), "dirt": (134, 96, 67), "sand": (219, 211, 160), "dark": (26, 26, 26)}

def lint(path, plant=False):
    im = Image.open(path).convert("RGBA"); W, H = im.size; px = im.load()
    op = lambda x, y: 0 <= x < W and 0 <= y < H and px[x, y][3] > 8
    warns = []
    cols = {px[x, y][:3] for y in range(H) for x in range(W) if op(x, y)}
    if not cols: return ["empty sprite"]
    if len(cols) > 12: warns.append(f"colors: {len(cols)} distinct (>12 — ramps broke down?)")
    if (0, 0, 0) in cols: warns.append("black: pure #000000 present — use ramp[0] instead")
    if (255, 255, 255) in cols: warns.append("white: pure #ffffff present — use ramp[4] instead")
    orph = [(x, y) for y in range(H) for x in range(W) if op(x, y)
            and not any(op(x+dx, y+dy) for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)))]
    if orph: warns.append(f"orphan: {len(orph)} isolated px {orph[:4]} — noise or intentional?")
    if any(op(0, y) for y in range(H)) or any(op(W-1, y) for y in range(H)):
        warns.append("margin: touches left/right edge (keep 1px)")
    if any(op(x, 0) for x in range(W)):
        warns.append("margin: touches top edge")
    if plant and not any(op(x, y) for y in (H-1, H-2) for x in range(W)):
        warns.append("anchor: nothing in bottom 2 rows — plant will float")
    lum = lambda c: 0.299*c[0] + 0.587*c[1] + 0.114*c[2]
    mean = sum(lum(c) for c in cols) / len(cols)
    for name, bg in BGS.items():
        if abs(mean - lum(bg)) < 25:
            warns.append(f"contrast: low vs {name} (Δ{abs(mean-lum(bg)):.0f}) — check visibility")
    return warns

if __name__ == "__main__":
    plant = "--plant" in sys.argv
    w = lint(sys.argv[1], plant)
    print(f"{sys.argv[1]}: " + ("CLEAN" if not w else f"{len(w)} warning(s)"))
    for x in w: print("  ⚠", x)
    sys.exit(len(w))
