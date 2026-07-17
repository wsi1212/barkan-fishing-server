#!/usr/bin/env python3
"""Palette ramp generator — the single biggest pixel-art quality lever.

Instead of eyeballing a light/base/dark trio (which comes out muddy), derive the
whole ramp from ONE base hue with two moves at once:
  • value spread  (light -> dark)
  • hue shift      (highlights drift WARM/toward yellow, shadows drift COOL/toward blue)
  • saturation     (shadows a touch MORE saturated, highlights less)
Hue-shifting is what makes pixel art look alive instead of like tinted greyscale.

Usage:
  python palette.py c0392b            # 5 hex, shadow..highlight
  python palette.py c0392b 7          # 7 steps
Import:
  from palette import ramp; r = ramp("c0392b")  # -> ['5c1a19',... ,'f0a89a']  dark..light
Convention: use r[0..1] for core shadow, r[2] base, r[3] light, r[4] highlight (1-2px specular).
"""
import colorsys, sys
def ramp(base, n=5, spread=0.62, hue=0.05, sat=0.16):
    base = base.lstrip('#')
    r, g, b = [int(base[i:i+2], 16)/255 for i in (0, 2, 4)]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    out = []
    for i in range(n):
        t = (i/(n-1)) - 0.5                     # -0.5 shadow .. +0.5 highlight
        vv = min(1, max(0.04, v + t*spread))
        hh = (h - t*hue) % 1.0                  # light warmer, shadow cooler
        ss = min(1, max(0, s - t*sat))
        rr, gg, bb = colorsys.hsv_to_rgb(hh, ss, vv)
        out.append('%02x%02x%02x' % (round(rr*255), round(gg*255), round(bb*255)))
    return out
def rgba(hexs, a=255):
    hexs = hexs.lstrip('#'); return (int(hexs[0:2],16), int(hexs[2:4],16), int(hexs[4:6],16), a)
if __name__ == '__main__':
    print(' '.join(ramp(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 5)))
