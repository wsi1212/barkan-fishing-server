"""universal 팔레트 이름 기준 «자연 블록» 판별. 나머지는 사람이 지은 것으로 본다."""
import re
NATURAL = r"""^(air|cave_air|void_air|water|flowing_water|lava|flowing_lava|bedrock|stone|granite|diorite|andesite|
deepslate|tuff|calcite|dirt|coarse_dirt|rooted_dirt|podzol|mycelium|grass_block|grass|tall_grass|fern|large_fern|dead_bush|
sand|red_sand|gravel|clay|sandstone|red_sandstone|snow|snow_layer|snow_block|ice|packed_ice|blue_ice|frosted_ice|magma_block|
obsidian|moss_block|mud|ore|.*_ore|log|.*_log|wood|.*_wood|leaves|.*_leaves|sapling|.*_sapling|plant|double_plant|tall_plant|
vine|sugar_cane|cactus|bamboo|seagrass|tall_seagrass|kelp|kelp_plant|bubble_column|.*coral.*|sea_pickle|dripstone_block|
pointed_dripstone|terracotta|.*_terracotta|flower|.*_flower|mushroom|.*_mushroom|lily_pad|infested_.*|amethyst.*|
smooth_basalt|basalt|glow_lichen|sculk.*|cobweb|turtle_egg|farmland|dirt_path|nether.*|soul_.*|end_stone|chorus.*|
fire|torch|light|barrier|structure_void|moving_block|piston_head|.*_concrete_powder)$"""
NAT = re.compile("".join(NATURAL.split()))
def bn(n): return n.split(":")[-1]
