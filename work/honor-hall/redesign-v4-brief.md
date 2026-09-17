# honor_hall v4 — reference review, 2026-09-16

Status: research/design proposal only. No v4 world edits have been applied.

## User corrections

- Rear wall is flat and visually empty; all external elevations need architectural depth.
- Temple should feel substantially larger.
- Surrounding forest must be much denser.
- Accidental gaps between dome slabs must be sealed.
- Quartz and dark prismarine are acceptable on the dome, not on the floor.
- Preserve 4 staff statue plinths exactly 3×3×2 and the three exhibition directions.

## References actually viewed

1. xv12commander, Neoclassical Temple: https://www.planetminecraft.com/project/neoclassical-temple/
   AIBuilder reference 4030abe0d1/ref_005. Continuous exterior colonnade, deep shadows behind columns, layered cornices and a carved pediment. Borrow elevation hierarchy, not the complete design.
2. xv12commander, Neoclassical Temple 2 (mausoleum): https://www.planetminecraft.com/project/neoclassical-temple-2-mausoleum/
   Reference 4030abe0d1/ref_006. Recessed wall bays, a solid stepped vault and framed modular floor fields. Do not copy its dark red palette.
3. _UnknownEntity, Roman Hanging Garden: https://www.planetminecraft.com/project/roman-hanging-garden/
   Reference 4030abe0d1/ref_002. Neutral tiled floor fields bordered by pale stone, with planting separated from paths.
4. billoxiiboy, Exodus from Paradise: https://www.planetminecraft.com/project/exodus-from-paradise/
   Reference 4030abe0d1/ref_007. Overlapping large tree crowns, several vegetation heights, planted edges. Reference composition only; do not copy its Asian buildings, giant trees, custom texture pack or assets.

## Proposed implementation targets (our design choices, not measured from references)

- Footprint: about 1.4× current width/depth, roughly 155 blocks across vs current 112; about twice floor area. Increase column/ceiling height proportionally, not plinth size.
- Rear elevations: 2–3-block relief, repeated pilasters with bases/capitals, recessed arch niches, horizontal lower/middle/upper trim. Avoid oversized blank white panels.
- Floor: broad smooth-quartz fields, restrained polished-diorite tile panels and thin polished-andesite borders. No dark-prismarine or copper floor lines; very limited gold, mainly plaques/emblems. Avoid salt-and-pepper random block mixing and dense checkerboard everywhere.
- Dome: continuous full-block structural shell, decorative slabs/stairs outside it. Check diagonal and vertical joins from below. Distinguish deliberate central oculus from unintended tile gaps; preserve or explicitly redesign the oculus rather than silently treating it as a defect.
- Forest: clustered tall canopy + medium trees + shrubs/ferns; overlapping crowns, irregular spacing and heights. Aim for 70–80% outer forest canopy coverage while keeping entrance sightline and walking paths clear. This is a target, not current measured coverage.
- Next preview must include rear elevation, walking-height interior, and floor detail, not only flattering aerial views. Final quality must be checked in actual Minecraft with the user's resource pack, not inferred from the smooth Three.js model.

## Safe build follow-through

- Dev only, world honor_hall. No prod actions.
- Snapshot current occupied area before expansion. Existing native trees overlap proposed larger footprint; do not broadly clear user content.
- Keep v3 recipe and approved_geometry.json unchanged for deterministic old/new diffs and rollback.
- Verify all staff plinth dimensions and gallery access after rescaling.
