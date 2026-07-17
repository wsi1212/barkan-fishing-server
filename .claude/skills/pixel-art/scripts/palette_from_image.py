#!/usr/bin/env python3
"""Extract a palette from a reference image, then build hue-shifted ramps from it.

Removes the last eyeballed decision in the pipeline: instead of guessing a base hex,
quantize the reference, take its dominant hues, and feed those into palette.ramp().

Usage:
  python palette_from_image.py ref.png            # top-8 dominant colors (hex + share)
  python palette_from_image.py ref.png --ramps 3  # cluster to 3 hue groups, print a ramp each
Import:
  from palette_from_image import dominant, ramps_from_image
"""
import sys, os, colorsys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palette import ramp

def dominant(path, n=8):
    im = Image.open(path).convert("RGBA")
    if max(im.size) > 128: im.thumbnail((128, 128), Image.NEAREST)
    px = [p for p in im.getdata() if p[3] > 128]           # opaque only
    if not px: return []
    q = Image.new("RGB", (len(px), 1)); q.putdata([p[:3] for p in px])
    q = q.quantize(colors=min(n*3, 48), method=Image.MEDIANCUT)
    pal = q.getpalette(); counts = sorted(q.getcolors(), reverse=True)
    out, seen = [], []
    for cnt, idx in counts:
        r, g, b = pal[idx*3:idx*3+3]
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        if v < 0.08 or (s < 0.08 and not 0.25 < v < 0.9):   # drop near-black & flat greys
            continue
        if any(abs(h-h2) % 1 < 0.04 and abs(v-v2) < 0.15 for h2, v2 in seen):
            continue                                        # drop near-duplicates
        seen.append((h, v)); out.append(('%02x%02x%02x' % (r, g, b), cnt/len(px)))
        if len(out) >= n: break
    return out

def ramps_from_image(path, k=3):
    """k ramps built from the k most dominant, hue-distinct colors."""
    return {hexc: ramp(hexc) for hexc, _ in dominant(path, k)}

if __name__ == "__main__":
    p = sys.argv[1]
    if "--ramps" in sys.argv:
        k = int(sys.argv[sys.argv.index("--ramps")+1])
        for base, r in ramps_from_image(p, k).items():
            print(base, "->", ' '.join(r))
    else:
        for hexc, share in dominant(p):
            print(f"{hexc}  {share*100:4.1f}%")
