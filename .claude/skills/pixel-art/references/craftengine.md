# Sprite → CraftEngine furniture

How to take a finished sprite PNG and make it a placeable CraftEngine furniture item.
(Barkan server paths; adapt the base path elsewhere.)

Base: `plugins/CraftEngine/resources/barkan_furniture/`
- models  → `resourcepack/assets/barkan/models/item/furniture/<group>/<id>.json`
- textures→ `resourcepack/assets/barkan/textures/furniture/<group>/<id>.png`
- config  → `configuration/<something>.yml` (top-level `items:`)

## Model: cross (plants — mushrooms, flowers, herbs, bushes)

Two crossed planes, sprite on both sides — the vanilla-flower look. Sprite reads standing up.

```json
{
  "textures": {"0": "barkan:furniture/<group>/<id>", "particle": "barkan:furniture/<group>/<id>"},
  "elements": [
    {"from":[0.8,0,8],"to":[15.2,16,8],"rotation":{"origin":[8,8,8],"axis":"y","angle":45,"rescale":true},"shade":false,
     "faces":{"north":{"uv":[0,0,16,16],"texture":"#0"},"south":{"uv":[0,0,16,16],"texture":"#0"}}},
    {"from":[8,0,0.8],"to":[8,16,15.2],"rotation":{"origin":[8,8,8],"axis":"y","angle":45,"rescale":true},"shade":false,
     "faces":{"west":{"uv":[0,0,16,16],"texture":"#0"},"east":{"uv":[0,0,16,16],"texture":"#0"}}}],
  "display": {"fixed": {"rotation":[0,0,0],"translation":[0,0,0],"scale":[1,1,1]}}
}
```

## Model: cuboid / drawn item (fruits, solid objects)

If you drew a proper item model (boxes) reuse its `elements`. If you only have a flat
sprite and want a small standing item, a single thin plane also works. For item-style
sources, bump `display.fixed.scale` (e.g. `[2,2,2]`) so a small item is visible.

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
