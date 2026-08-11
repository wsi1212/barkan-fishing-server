#!/usr/bin/env python3
"""Patch a prod Citizens saves.yml with the approved lord-castle NPCs.

Usage: apply_lord_castle_citizens.py saves.yml mineskin.jsonl
The YAML is changed textually to preserve Citizens' existing serialized layout.
"""
import json
import re
import sys
import uuid
from pathlib import Path

save_path, skins_path = map(Path, sys.argv[1:3])
text = save_path.read_text(encoding="utf-8")
if any(f"  '{cid}':" in text for cid in (171, 172, 173)):
    raise SystemExit("lord-castle Citizens IDs already exist; refusing a duplicate spawn")

for old, new in {
    "name: '&a[Q] 하겐'": "name: '&a[Q] 길드장 하겐'",
    "name: '&f성문 위병 로타르'": "name: '&a[Q] 성문 위병 로타르'",
    "name: '&f성문 위병 쿠르트'": "name: '&a[Q] 성문 위병 쿠르트'",
    "name: 유누스": "name: '&a[Q] 유누스'",
    "name: '&a[Q] 파티마'": "name: '&a[Q] 파티마'",
}.items():
    if old not in text:
        raise SystemExit(f"expected Citizens name missing: {old}")
    text = text.replace(old, new)

# Keep the guildmaster clearly inside the guild hall, not against its exterior wall.
old_loc = "x: 443.6597\n        y: 85.0\n        yaw: 178.0255\n        z: 820.3"
new_loc = "x: 443.5\n        y: 85.0\n        yaw: 180.0\n        z: 817.5"
if old_loc not in text:
    raise SystemExit("Hagen location drifted; refusing an unverified move")
text = text.replace(old_loc, new_loc, 1)

skin_rows = [json.loads(line) for line in skins_path.read_text(encoding="utf-8").splitlines() if line.strip()]
if len(skin_rows) != 3:
    raise SystemExit("expected exactly 3 MineSkin responses")

specs = [
    (171, "&a[Q] 영주 발데마르", 365.0, 99.0, 710.0, skin_rows[0]),
    (172, "&a[Q] 근위병 라이너", 365.0, 99.0, 774.0, skin_rows[1]),
    (173, "&a[Q] 사관 게르하르트", 367.0, 102.0, 740.0, skin_rows[2]),
]
world_id = "732d5003-d5d5-4c86-9810-70b14ecef350"
owner = "9b2e2922-47cb-4db6-8e44-a736d9c13358"
blocks = []
for cid, name, x, y, z, data in specs:
    tex = data["data"]["texture"]
    npc_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"barkan-lord-castle-{cid}")
    blocks.append(f"""  '{cid}':
    traits:
      location:
        x: {x}
        y: {y}
        z: {z}
        pitch: 0.0
        yaw: 180.0
        worldid: {world_id}
        bodyYaw: 180.0
      owner:
        uuid: {owner}
      type: PLAYER
      scoreboardtrait:
        tags:
        - CITIZENS_NPC
      skintrait:
        signature: {tex['signature']}
        skinName: {data['uuid']}
        textureRaw: {tex['value']}
    traitnames: owner,spawned,scoreboardtrait,skintrait,lookclose,location,type,inventory
    name: '{name}'
    navigator:
      usedefaultstuckaction: false
      speedmodifier: 1.0
      avoidwater: false
    uuid: {npc_uuid}
    metadata:
      cached-skin-uuid-name: {data['uuid']}
      nameplate-visible: true
""")

text = re.sub(r"^last-created-npc-id: \d+$", "last-created-npc-id: 173", text, count=1, flags=re.M)
save_path.write_text(text.rstrip() + "\n" + "".join(blocks), encoding="utf-8")

try:
    import yaml
    parsed = yaml.safe_load(save_path.read_text(encoding="utf-8"))
except Exception as exc:
    raise SystemExit(f"resulting saves.yml is invalid: {exc}")
for cid, name, x, y, z, _ in specs:
    node = parsed["npc"].get(str(cid))
    if not node or node["name"] != name or (node["traits"]["location"]["x"], node["traits"]["location"]["y"], node["traits"]["location"]["z"]) != (x, y, z):
        raise SystemExit(f"new NPC {cid} did not survive YAML verification")
print("Citizens NPC count:", len(parsed["npc"]))
