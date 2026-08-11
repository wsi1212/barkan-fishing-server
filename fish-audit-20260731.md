# Fish texture audit — 2026-07-31

## Scope

- Fish texture PNGs: 515
- Fish model registry entries: 503
- Registry entries without a texture: 0
- Unmapped PNGs: 12 (legacy/unclassified; not changed)
- Final texture format: all 515 files are now 256×256 RGBA

## Changes

### Regenerated (19)

`농어`, `항구고등어`, `고등어`, `도다리`, `참복`, `참놀래기`, `전갱이`, `열사의숭어`, `연어`, `타폰`, `참돌고래`, `밍크고래`, `고래상어`, `클리오네`, `그린란드상어`, `석순장어`, `피라냐`, `타이멘`, `수원 산천어`

The regenerated assets were checked for species silhouette, upper-left orientation, transparent background, pixel treatment, and white outline.

### Post-processed without generation (10)

The ten 512×512 assets were normalized to 256×256 with the same crop, pixel reduction, and outline treatment. No image-generation credits were used for this pass.

### Detached-fragment cleanup (48 active icons)

Removed disconnected leftover components from 48 active encyclopedia textures, including the detached fragment beneath `정어리`. This was a transparent-layer cleanup only; no image-generation credits were used. A second component scan found no remaining detached components of 30+ solid pixels among active registry textures.

### Long-bodied / billfish family follow-up

The family review covered `갈치`, `맹안갈치`, `청새치`, `돛새치`, `돗새치`, `흑새치`, `산갈치`, `학공치`, and `학꽁치`. `갈치` and `맹안갈치` were regenerated to share a correct cutlassfish silhouette; the other seven were retained as visually acceptable variants. The two new assets use online species references, 256×256 RGBA output, pixel treatment, and the standard white outline.

`맹안갈치` received a follow-up eye correction: the duplicate normal eye was removed, leaving exactly one cloudy blind eye.

## Notes

The original files are preserved in `.codex-backup/fish-icons-before-regenerate-20260731/`. The 12 unmapped PNGs were left untouched because they are not connected to the active encyclopedia registry.
