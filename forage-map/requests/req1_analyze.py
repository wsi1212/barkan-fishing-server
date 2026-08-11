import json

D = "/Users/user/.claude/projects/-Users-user-Library-Application-Support-feather-player-server-servers-07de2d81-991a-47e2-b62d-06c0d1b5150a-plugins-Skript-scripts/ecbf89fa-45dc-4be4-a866-2c02c57cdf6d/tool-results/"

files = [
    "mcp-minecraft-ai-builder-mc_get_region-1785201540819.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201541902.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201542639.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201543743.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201544804.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201545922.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201546656.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201547747.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201548817.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201549970.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201550663.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201551738.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201552843.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201553913.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201554648.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201555757.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201556830.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201557566.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201558662.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201559760.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201560823.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201561560.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201562652.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201563778.txt",
    "mcp-minecraft-ai-builder-mc_get_region-1785201564387.txt",
]

candidates = json.load(open("/tmp/req1_candidates.json"))
assert len(candidates) == len(files), (len(candidates), len(files))

PASSABLE = {"air", "cave_air", "void_air", "short_grass", "grass", "tall_grass", "fern", "large_fern",
            "snow", "vine", "water", "seagrass"}
FLOWER_KEYWORDS = ["poppy", "dandelion", "allium", "orchid", "bluet", "tulip", "daisy",
                   "cornflower", "lily_of_the_valley", "peony", "lilac", "rose_bush", "sunflower", "wither_rose"]
WATER_LAVA = {"water", "lava", "flowing_water", "flowing_lava"}

results = []
for (cx, cz), fname in zip(candidates, files):
    data = json.load(open(D + fname))
    blocks = data["blocks"]
    by_col = {}
    for b in blocks:
        m = b["material"].replace("minecraft:", "")
        by_col.setdefault((b["x"], b["z"]), []).append((b["y"], m))
    # surface at center column: topmost non-passable block
    col = sorted(by_col.get((cx, cz), []), key=lambda t: -t[0])
    surface_y = None
    surface_mat = None
    for y, m in col:
        if m not in PASSABLE:
            surface_y = y
            surface_mat = m
            break
    has_flower = any(
        any(k in m for k in FLOWER_KEYWORDS)
        for (y, m) in [(b["y"], b["material"].replace("minecraft:", "")) for b in blocks]
    )
    is_water = surface_mat in WATER_LAVA if surface_mat else True
    results.append({
        "x": cx, "z": cz, "surface_y": surface_y, "surface_mat": surface_mat,
        "has_flower_nearby": has_flower, "valid_ground": (surface_mat is not None and not is_water),
    })

for r in results:
    print(r)

json.dump(results, open("/tmp/req1_analysis.json", "w"))
print("\nvalid:", sum(1 for r in results if r["valid_ground"]))
print("with flower:", sum(1 for r in results if r["valid_ground"] and r["has_flower_nearby"]))
