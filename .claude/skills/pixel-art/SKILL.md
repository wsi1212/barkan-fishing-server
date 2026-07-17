---
name: pixel-art
description: >-
  Create high-quality Minecraft-style pixel-art game assets — mushrooms, herbs, flowers,
  fruits, berries, food, crops, and decorative item sprites — and convert them into
  CraftEngine furniture. Use this whenever making custom pixel-art textures, item icons,
  sprites, or building 3D furniture from hand-drawn art for a Minecraft server, especially
  foraging / food / plant items, even if the user only says "draw a mushroom", "make a
  custom fruit", or "I need a foraging item" without the words "pixel art". It enforces a
  reference → palette → silhouette → shade → render → critique loop with proper color ramps
  so the output is consistently good instead of muddy.
---

# Minecraft pixel-art assets

Good pixel art is craft, not talent. Muddy results almost always come from skipping
technique — picking colors by eye, shading with no light direction, adding detail before
the shape reads. Follow the loop and the principles below and the output climbs from
"amateur" to "clearly deliberate" without needing a bigger model. The single most
important habit: **you must render what you make and look at it, then fix it.** You cannot
pixel-push blind.

## The loop — do this every time

1. **Reference first — and gather them, don't wait for them.** Keep a persistent reference
   board at `pixel-forge/refboard/<category>/` (record sources in `sources.md`). Great
   sources: **paid-pack product pages** (MCModels/BuiltByBit product images are public —
   referencing their look to make your own art is fine; never redistribute their files),
   Modrinth gallery images (`api.modrinth.com/v2/project/<slug>` → `gallery[].url`), and
   game-art wikis. Download with curl, view with `view.py`/`contact.py`, and *study the
   reference before drawing*: what silhouettes do they use? how saturated are they? are
   they flat sprites or chunky box models? (The MCModels mushroom pack taught us: pro
   Minecraft props are muted-palette **box models** with varied silhouettes — not smooth
   saturated domes.)

2. **Palette from the reference, ramps from the palette.** Run
   `scripts/palette_from_image.py <ref.png>` to extract the reference's dominant colors
   (crop to the subject and blank the background first if it's a product shot), then feed
   the best 1–3 hexes into `scripts/palette.py <hex>` for hue-shifted 5-step ramps. Use
   ~4–5 colors per material — no more. This removes the last eyeballed decision: even the
   base hue now comes from evidence, not taste.

3. **Silhouette.** Block the shape in the base color at the target resolution first. If the
   flat silhouette doesn't read as the thing, no shading will save it — fix the shape now.

4. **Shade the form.** Commit to one light source (default: top-left). Light the surfaces
   facing it, shadow the surfaces turned away, **following the 3-D form** — a mushroom cap
   is a dome (bright over the crown, dark under the rim), a berry is a sphere (specular dot
   top-left, core shadow bottom-right). See `references/technique.md`.

5. **Render & critique — offline first, then in-game.** Save the PNG, upscale with
   `view.py`, `lint_sprite.py` it (objective checks: color count, pure black, orphans,
   margins, ground anchor, background contrast), and `compare.py ref.png sprite.png out.png`
   to sit it next to the reference. For furniture, `render_model.py` previews the model
   shape. Then the ground truth: deploy to dev and run
   `ingame_verify.py place barkan:<id>...` — it summons item_displays of your actual models
   on a sky plot via console (no player needed) — and shoot it with `mc_screenshot`
   (needs one player online on dev as the camera). The game's own render is the only
   render that counts; offline previews miss lighting, backgrounds, and angles.
   `ingame_verify.py clean` tears the plot down.

6. **Iterate.** Fix that one named thing, re-render, look again. 2–4 passes is normal and
   expected — the first pass is never the last.

## Principles (the why)

- **Ramps + hue-shift.** A material's colors should be one ramp, not three eyeballed
  swatches. `palette.py` shifts highlights warm and shadows cool; that tiny hue drift reads
  as light and reflected color, which is most of what separates pro pixel art from tinted
  greyscale.
- **One light source.** Pick a direction and obey it everywhere. Inconsistent lighting is
  subtle but makes everything feel "off".
- **Form, not pillow.** Pillow-shading — lighter in the center, darker at every edge like a
  stuffed cushion — is the #1 amateur tell. Shade to describe the object's form and the
  light direction instead.
- **Silhouette carries readability.** Players identify an item by its outline shape at small
  size before they see any interior detail. Spend effort there first.
- **Outline selectively.** Pure black outlines on every edge flatten and darken the sprite.
  Use a dark *ramp* color, and drop the outline where a lit surface meets empty space.
- **Dither for gradients.** At 16px you can't blend; a checkerboard of two adjacent ramp
  steps fakes a midtone across a transition. Use sparingly — it's seasoning, not a base.
- **Resolution.** 16×16 is the vanilla default and reads fastest; it fits almost everything.
  Reach for 32×32 only for a hero/detailed item — more pixels means more decisions to get
  right, not automatically better.

## Tooling (scripts/)

- `palette.py <hex> [n]` — hue-shifted ramp (shadow..highlight). In code:
  `from palette import ramp, rgba` → `r = ramp("c0392b")`, `rgba(r[4])` for a fill.
- `palette_from_image.py <ref.png> [--ramps k]` — extract dominant colors / ready ramps
  from a reference image (opaque pixels only — blank the background first).
- `view.py <in.png> <out.png> [scale]` — nearest-neighbor upscale. Always view before judging.
- `contact.py <png...> <out.png>` — labeled review grid (small sprites upscale, big
  renders/refs downscale automatically).
- `compare.py <ref> <sprite> <out> [...]` — REF vs MINE side-by-side at matched height.
- `lint_sprite.py <png> [--plant]` — objective pre-ship checks; exit code = warning count.
- `render_model.py <model.json> <tex.png> <outbase>` — offline model render (flat per-face
  color; shape/proportion check only — not a lighting truth).
- `sprite_to_voxel.py <png> <out.json> <tex_ref>` — extrude a sprite into a per-pixel-run
  voxel model (dropped-item look) for solid objects.
- `ingame_verify.py place|clean <model_ids...>` — console-only summon of your models on a
  dev sky plot for a real in-game screenshot. Prints the camera position for `mc_screenshot`.

Draw with PIL on a 16×16 RGBA canvas, pulling every fill from `ramp()`. Keep painters as
small parametric functions (seed → variants) in a **git-tracked registry** — see
`pixel-forge/painters.py` + `manifest.json` + `build.py`, the manifest-driven pipeline that
paints, lints, models, and writes the CraftEngine config in one idempotent run. Never leave
painter code in /tmp: the PNG survives but the source dies.

## Turning sprites into CraftEngine furniture

Model routes, per subject — **the X-cross (two crossed flat planes) is BANNED** (owner
decision, 2026-07-17: crossed planes have no volume and read as cheap; `build.py` hard-fails
on `model: cross`). Everything placeable gets real volume:
- **boxes** (default) — declare shapes with `pixel-forge/modelkit.py`: `Kit` + `Mat` +
  `rounded_box`/`dome` primitives. The kit auto-paints every face with pixel noise +
  gradient + specular, auto-packs a 1:1 atlas, and culls stacked faces. Quality lives in
  the system, not per-item effort — a painter is 3-8 declaration lines.
- **voxel** (`sprite_to_voxel.py`) — per-pixel extrusion of a finished sprite; use when a
  drawn sprite already carries the detail and just needs depth.

The grounding formula `translation_y = scale*(8 - y_min)/16`, config template, and
`ce reload` deploy steps are in `references/craftengine.md`.

## Deeper craft

`references/technique.md` — step-by-step form shading worked on real examples, dithering,
hue-shift theory, and a checklist of amateur tells to self-audit against before you ship.
