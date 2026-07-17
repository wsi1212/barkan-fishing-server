# Pixel-art technique (depth)

Read this when shading feels flat or a sprite looks amateur and you can't say why.

## Form shading, worked

The mistake is shading regions ("cap = red, make edges darker"). Instead shade the
**surface's angle to the light**. Light default = top-left, slightly above.

**Dome (mushroom cap):** the crown faces up-left → highlight (`ramp[4]`, 1–3 px near the
top-left of the curve). The front face → base (`ramp[2]`). The underside/rim, turned away →
shadow (`ramp[1]`), a darker band along the bottom edge of the cap. One or two `ramp[0]`
pixels only in the deepest crevice (where cap meets stem). Result reads as a rounded 3-D
cap, not a red blob.

**Sphere (berry, fruit):** specular highlight = a 1–2 px dot of `ramp[4]` (or near-white)
offset toward the light, NOT centered. Terminator (where light rolls off) is a curved band
of base→`ramp[1]`. Core shadow `ramp[0]` sits *inside* the bottom-right edge, with a thin
rim of `ramp[1]` below it (reflected bounce light) so the edge doesn't die into black.

**Stalk/stem (cylinder):** a vertical strip of highlight on the lit side, base in the
middle, one shadow column on the dark side. Never a flat single color — that's what makes
stems look like popsicle sticks.

## The amateur tells — self-audit before shipping

- **Pillow-shading:** lighter center, darker on all sides. Fix: pick a light direction; the
  side away from it stays dark even in the "middle".
- **No light direction:** highlights scattered on all sides. Fix: every highlight should be
  explainable by the one light.
- **Pure-black everything:** black outline + black shadows crushes the art. Fix: outlines
  and shadows come from the ramp's dark end (`ramp[0]`/`ramp[1]`), which is a dark *hue*,
  not `000000`.
- **Too many colors:** 9 barely-different reds. Fix: one 5-step ramp per material.
- **Noise instead of form:** random darker/lighter pixels ("hue-noise") to fake texture.
  Fix: pixels should sit where the form or a real feature (a spot, a vein) is.
- **Banding:** long diagonal stair-steps of single-width jaggies. Fix: vary run lengths
  (1,2,3,2,1) or dither the transition.
- **Floating parts:** a stem not connected to the cap, a leaf hovering. Fix: overlap by a
  pixel; anchor to the ground row.

## Hue-shift, why it works

Real shadows aren't just "the color, darker" — ambient sky light tints them cool, and
highlights pick up the warm light source. Shifting hue ~15–30° cool into shadow and warm
into highlight (which `palette.py` does automatically) simulates this. Skip it and the ramp
looks like a greyscale gradient someone colored in.

## Dithering

At 16px there's no room to blend two colors, so alternate them in a checkerboard to imply a
midtone: use it on a *transition* between two ramp steps (e.g. base→light across a broad
curve), 2–4 px wide. Full-sprite dither looks noisy — keep it to the seams.

## Resolution & canvas

- 16×16: vanilla parity, reads instantly, forgiving. Default for items and small plants.
- 32×32: only when the subject genuinely needs detail (a detailed creature, a hero prop).
  Everything takes ~4× the work to keep clean.
- Keep a 1 px empty margin so the sprite doesn't jam the edge; center the visual mass.
- Transparent background; anchor plant/foraging sprites to the bottom rows so they sit on
  the ground when placed as a cross model.

## Palette starting points (bases to feed palette.py)

- Reds/berries `c0392b` · warm orange `d97a2b` · golden `e0b53b` · leaf green `4e8f3a`
- Deep green `2e6b34` · sky/ice blue `3a7ca5` · violet/magic `7a5cb0` · cream/stem `e8dcc0`
- Brown/wood `7a5230` · mushroom tan `caa26a`. Always run these through `ramp()` — never
  fill with the flat base alone.
