"""topdown map(2D)와 voxel 미리보기(3D) 둘 다 쓰는 재질→색상 매핑. 단일 출처."""


def color_for(material):
    m = material.replace("minecraft:", "")
    if m == "air":
        return (40, 46, 58)
    if "water" in m:
        return (46, 98, 168)
    if "ice" in m:
        return (176, 214, 230)
    if "snow" in m:
        return (238, 242, 245)
    if "leaves" in m:
        return (58, 110, 54)
    if any(k in m for k in ("grass_block", "moss", "farmland", "dirt_path")):
        return (86, 138, 58)
    if m == "dirt" or "coarse_dirt" in m or "mud" in m or "podzol" in m:
        return (110, 82, 54)
    if "terracotta" in m:
        if "white" in m or "light_gray" in m:
            return (214, 180, 150)
        return (176, 108, 60)
    if any(k in m for k in ("sandstone", "sand")):
        return (222, 196, 130) if "red" not in m else (188, 104, 58)
    if "cactus" in m:
        return (74, 120, 62)
    if m in ("wheat", "carrots", "potatoes", "beetroots"):
        return (196, 168, 66)
    if any(k in m for k in ("log", "wood", "planks", "fence", "stairs", "slab",
                             "trapdoor", "stripped", "hyphae", "shelf")):
        return (150, 108, 68)
    if any(k in m for k in ("netherrack", "nether_brick", "crimson", "soul_sand", "basalt")):
        return (120, 58, 58)
    if any(k in m for k in ("stone", "deepslate", "cobble", "andesite", "granite",
                             "tuff", "gravel", "brick", "quartz", "bedrock",
                             "blackstone", "dripstone")):
        return (128, 128, 132)
    if any(k in m for k in ("lantern", "iron_bars", "glass", "wool", "concrete")):
        return (150, 150, 150)
    if any(k in m for k in ("poppy", "dandelion", "allium", "orchid", "bluet", "tulip",
                             "daisy", "cornflower", "lily_of_the_valley", "peony", "lilac", "rose")):
        return (196, 90, 120)
    h = sum(ord(c) for c in m)
    return (90 + h % 100, 90 + (h * 3) % 100, 90 + (h * 7) % 100)
