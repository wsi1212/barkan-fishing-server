# Sprite → CraftEngine furniture

How to take a finished sprite PNG and make it a placeable CraftEngine furniture item.
(Barkan server paths; adapt the base path elsewhere.)

Base: `plugins/CraftEngine/resources/barkan_furniture/`
- models  → `resourcepack/assets/barkan/models/item/furniture/<group>/<id>.json`
- textures→ `resourcepack/assets/barkan/textures/furniture/<group>/<id>.png`
- config  → `configuration/<something>.yml` (top-level `items:`)

## ⛔ Model: cross — BANNED

Two crossed flat planes (vanilla-flower style) are **forbidden for our custom assets**
(owner decision 2026-07-17): no volume, reads as cheap "X 종이". `pixel-forge/build.py`
hard-fails on `model: cross`. Third-party sourced models that merely inherit
`block/cross` but carry real `elements` (e.g. Actually 3D flowers) are fine — the ban is
on flat 2-plane displays, not on the parent name.

## Model: boxes (default — modelkit)

Declare volume with `pixel-forge/modelkit.py`; the Kit guarantees the quality floor
(per-face pixel noise + gradient + specular, auto-packed 1:1 UV atlas, bevel primitives,
stack-face culling):

```python
from modelkit import Kit, Mat
k = Kit(seed)
k.rounded_box((4,0,4), (12,9,12), Mat("c0392b", spec=3))   # bevelled body
k.box((7.5,9,7.5), (8.5,11.5,8.5), Mat("6b4a2a"))          # stem
im, model = k.build("barkan:furniture/<group>/<id>")        # atlas PNG + model json
```
Primitives: `box(f,t,mat,cull=)`, `rounded_box(f,t,mat,bevel=1)`, `dome(cx,y,cz,w,h,mat)`.
`Mat(base_hex, spec=N, marks=[(fx,fy,rgba)], vgrad=)` — spots/speculars are material props.

## Model: voxel extrusion (sprite with depth)

`sprite_to_voxel.py` — per-pixel-run extrusion of a finished sprite. Use when a drawn
sprite already carries the detail. For item-style sources, bump `display.fixed.scale`
(e.g. `[2,2,2]`) so a small item is visible.

## Grounding — the key formula

A model is placed as an ItemDisplay whose coordinate center (8,8,8) sits at the furniture
entity; a 0–16 model therefore sinks half a block. Lift it so its bottom sits on the ground:

```
element translation_y = scale * (8 - y_min) / 16
```

where `y_min` = the lowest `from`/`to` Y across elements and `scale` = `display.fixed.scale`.
Cross model (y_min 0, scale 1) → translation_y = 0.5. This was verified in-game; skipping it
buries the sprite to its waist ("땅에 박힘").

## Furniture config block

```yaml
  barkan:<id>:
    data:
      item_name: "<!i><korean name>"
      lore:
        - "<!i><dark_gray>[채집]</dark_gray>"
    model: barkan:item/furniture/<group>/<id>
    behavior:
      type: furniture_item
      rules:
        ground: {rotation: any, alignment: center}
      furniture:
        events:
          - template: default:rotatable_furniture_8
        settings:
          item: barkan:<id>
          hit_times: 1
          sounds: {break: minecraft:block.grass.break, place: minecraft:block.grass.place, hit: minecraft:block.grass.hit}
        variants:
          ground:
            elements:
              - item: barkan:<id>
                display_transform: FIXED
                billboard: FIXED
                translation: 0,<ty>,0
                scale: 1.0
            hitboxes:
              - {position: 0,0,0, type: interaction, invisible: true, blocks_building: true, interactive: true, width: 0.8, height: 1.0}
        loot:
          template: default:loot_table/furniture
          arguments: {item: barkan:<id>}
```

★ Hitbox: use `type: interaction` (static AABB). Never `type: shulker` with `peek:` — the
shulker peek animation grows/shrinks the collider and wedges players.

## Deploy

- **dev:** `python3 ~/Downloads/craftengine-furniture-packs/devrcon.py "ce reload all"`
  then wait for the log line `Resource pack generated` (the generated pack mtime updates
  *before* compression finishes — trust the log line, not mtime). Verify the models are in
  `plugins/CraftEngine/generated/resource_pack.zip`.
- **give an item (player must be online):** `ce item give <player> barkan:<id> 1`
  (NOT `ce give`). Console/RCON works with `ce item give`.
- **prod:** full external-hosting pipeline — regenerate pack, scp `generated/resource_pack.zip`,
  `gh release upload latest ... barkan-furniture.zip --clobber`, update `config.yml`
  `hosting.sha1`, `ce reload config`, verify the 3-way sha1 match. Details:
  memory `project_craftengine_prod_deploy`.

Config/model/texture edits that don't add files → `ce reload config` (light, no client
reload). New models/textures or a changed pack → `ce reload all` (regenerates pack).

## GUI icons — 2D in inventory, 3D when placed (owner feedback 2026-07-17)

A 3D prop rendered at the vanilla GUI angle (30/225) turns thin stems and layered caps
into mush. The pro convention: **inventory shows a flat 2D icon, the 3D model appears only
when placed/held**. CraftEngine supports the modern item-model definition, so the item's
`model:` in the yml can be a `minecraft:select` on `minecraft:display_context`:

```yaml
model:
  type: minecraft:select
  property: minecraft:display_context
  cases:
    - when: gui
      model: {type: minecraft:model, model: barkan:item/furniture/<group>/icon/<id>}
  fallback: {type: minecraft:model, model: barkan:item/furniture/<group>/<id>}
```

The icon model is `item/generated` + a 32×32 sprite. Don't hand-draw 31 icons —
`pixel-forge/build.py` auto-renders each 3D model (render_textured, yaw 35 / pitch 25),
crops, downscales to 30px on a 32 canvas, and **binarizes alpha (>96)** so edges stay
crisp. Regenerating models regenerates icons — zero extra authoring.
