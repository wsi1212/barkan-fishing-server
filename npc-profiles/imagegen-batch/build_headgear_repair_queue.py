#!/usr/bin/env python3
"""Build the reviewed portrait-repair queue from CID-authoritative data."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "npc-profiles" / "npc-dialogue-portrait-manifest.json"
NPC = ROOT / "ops" / "blockship-data" / "npc.json"
STYLE = ROOT / "npc-profiles" / "references" / "otto-imagegen-style-reference.png"
OUT = ROOT / "npc-profiles" / "imagegen-batch" / "revisions" / "portrait-repair-20260824" / "queue.json"

TARGETS = {
    45: "elderly male archivist; short white-gray hair and white-gray beard; absolutely no hat, cap, veil, hood, or head covering; dark navy high-collared scholarly robe",
    58: "adult male court merchant; preserve the actual simple connected green cap/head covering from the skin; no broad straw brim, no dangling fringe, no separated strips; green and cream merchant uniform",
    64: "adult male pilgrim; brown hair and the actual face from the skin; no long veil or hood framing the face; cream pilgrim clothing with brown trim",
    71: "elderly male; gray hair and the actual cream-brown outfit from the skin; no tall brown hat and no dangling hat tassels",
    73: "adult male; preserve the actual connected simple green cap/head covering; no broad brim and no hanging fringe or piano-key strips; teal-green jacket with gold trim",
    74: "elderly male fisher; preserve the actual olive-green connected hood/cap; no white-and-brown cube hat and no detached brim pieces; brown field coat",
    78: "adult male desert traveler; preserve the actual simple brown/orange connected cap; no white tassel fringe or broad decorative brim; orange-brown and cream clothing",
    80: "adult male desert traveler; dark hair and the actual simple brown head covering; no white hanging fringe, no long veil; brown scarf and gray-beige clothing",
    81: "adult male desert traveler; preserve the actual simple tan connected cap; no white tassel fringe; olive robe and cream scarf",
    91: "adult male with gray hair; absolutely no straw hat; preserve the actual beige shirt and brown apron/work clothing from the skin",
    93: "adult woman matching the beatrice skin: warm brown hair with the small pink-red accent visible on the skin, green eyes, and the actual green-and-cream dress/waistcoat with brown sleeves; absolutely not an elderly white-haired bearded man",
    113: "adult male desert traveler; preserve the actual simple connected green cap/head covering; no wide straw brim and no hanging fringe; cream robe with green band",
    119: "adult male with long brown hair; no brown flat cap; preserve the actual purple coat and light shirt",
    121: "middle-aged male with brown hair and mustache; no black beret; preserve the actual brown military uniform and high collar",
    134: "adult male with brown hair; no baseball cap or other cap; preserve the actual brown-olive worker jacket and collar",
    136: "adult female with long vivid orange hair; no large orange wide-brim hat; preserve the actual dark green work dress/apron and face",
    142: "adult male with brown hair; preserve the actual simple light cloth cap/head covering; no dangling tassel ornament; red and cream uniform",
    146: "elderly male with gray hair and beard; absolutely no dark cylindrical hat; preserve the actual navy uniform with gold trim",
    151: "adult or elderly female with long white-gray hair and braids; no giant rectangular headpiece; preserve the actual green and red gardener clothing",
    154: "adult male gambler with brown hair; no brown cap; preserve the actual burgundy and cream gambler jacket",
    155: "adult male gambler with dark hair; no wide-brim black hat; preserve the actual burgundy and cream gambler clothing",
    156: "young adult male with brown hair; no straw hat; preserve the actual burgundy coat and light shirt",
    157: "adult male with gray-brown hair; no bucket hat; preserve the actual light jacket, pale shirt, and dark trousers",
    158: "elderly or mature character matching the skin exactly; preserve the actual connected dark navy head covering/hood and navy uniform; no giant white cylindrical hat, no detached rear ornament",
    172: "adult male guard with short brown hair; absolutely no hat or head covering; preserve the actual gray shoulder armor, green tabard, and small gold cross",
}

STATE_GUIDE = {
    "base": "natural neutral greeting expression",
    "progress": "attentive, explaining or concerned expression",
    "complete": "warm satisfied expression acknowledging the player's success",
}


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    npc_data = json.loads(NPC.read_text(encoding="utf-8"))["npcs"]
    by_cid = {int(e["citizensId"]): e for e in manifest["entries"]}
    queue = []
    for cid in sorted(TARGETS):
        entry = by_cid[cid]
        stem = entry["skin"]
        states = [s for s in ("base", "progress", "complete") if s in entry["states"]]
        # The existing portrait generator uses a 2x2 sheet for multi-state NPCs;
        # unused fourth tile must remain empty and is ignored by the splitter.
        layout = "single" if len(states) == 1 else "grid2x2"
        display = npc_data.get(entry["npc"], {}).get("name", entry["npc"])
        skin = ROOT / "skin-forge" / "out" / f"{stem}.png"
        current = Path(entry["states"]["base"]["asset"])
        identity = ROOT / "npc-profiles" / "imagegen-batch" / "identity" / f"{stem}.png"
        # Put the existing portrait first so ImageGen performs a style-preserving
        # object correction instead of translating the 64x64 skin into a blocky face.
        references = [str(current), str(identity if identity.exists() else skin), str(skin), str(STYLE)]
        state_text = "; ".join(f"{s}: {STATE_GUIDE[s]}" for s in states)
        prompt = f"""Use case: precise-object-edit. Asset type: Minecraft server BetterHUD dialogue portrait.

Image 1 is the current portrait edit target for NPC CID {cid} ({entry['npc']}, display label {display}). Preserve its rich hand-crafted pixel-art style, expressive face, detailed clustered pixels, three-quarter bust composition, outline quality, and readable clothing construction. Image 2 is the authoritative identity board when present, Image 3 is the authoritative 64x64 Minecraft skin, and Image 4 is the approved pixel-art style reference. The skin and identity board are factual authority for identity and headwear; Image 1 is the authority for the finished portrait language.

Character identity and correction: {TARGETS[cid]}.
Perform a targeted correction, not a generic Minecraft redraw. Preserve the detailed face and clothing style from Image 1 while correcting the wrong person/headwear using Images 2 and 3. Headwear, when present, must be one physically connected continuous object following the head silhouette: no floating strips, no broken brim, no piano-key teeth, no disconnected tassels, no accidental extra hat. If the skin has no headwear, reveal the actual hair and do not add any.

Output: {layout}. Create exactly {len(states)} portrait panel(s), in this order: {', '.join(states)}. For a grid2x2 sheet, place panels in reading order with the unused fourth tile completely empty. No labels, borders, text, UI, props, watermark, or extra characters. Each panel is a consistent three-quarter waist-up bust with shoulders visible, no feet, transparent-looking flat chroma background, and the same head size and framing across states. State directions: {state_text}.

Style: premium hand-crafted pixel-art game portrait, crisp clustered pixels, restrained medieval palette, clean dark outline, controlled material shading, readable at small HUD size. Do not simplify the face into a flat blocky Minecraft caricature. Backdrop: perfectly flat solid #00ff00 chroma-key only; no gradient, floor, shadow, reflection, or texture. Do not use #00ff00 in the character."""
        queue.append({
            "citizensId": cid,
            "npc": entry["npc"],
            "skin": stem,
            "states": states,
            "layout": layout,
            "references": references,
            "prompt": prompt,
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"version": 1, "queue": queue}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"targets": len(queue), "panels": sum(len(x["states"]) for x in queue), "queue": str(OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
