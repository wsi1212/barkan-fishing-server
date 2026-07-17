#!/usr/bin/env python3
# 배포 패키지 빌더 — 판매/공유 가능한 형태(zip): config+models+textures+preview+README
import os, json, zipfile, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
BF = os.path.expanduser("~/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/CraftEngine/resources/barkan_furniture")
mf = json.load(open(os.path.join(HERE, "manifest.json")))
ids = ["z_" + i["id"] for i in mf["items"]]
dist = os.path.join(HERE, "dist"); os.makedirs(dist, exist_ok=True)
zp = os.path.join(dist, "barkan-forage-pack-v1.zip")
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(f"{BF}/configuration/forage_custom.yml", "configuration/forage_custom.yml")
    for iid in ids:
        z.write(f"{BF}/resourcepack/assets/barkan/models/item/furniture/forage/{iid}.json",
                f"resourcepack/assets/barkan/models/item/furniture/forage/{iid}.json")
        z.write(f"{BF}/resourcepack/assets/barkan/textures/furniture/forage/{iid}.png",
                f"resourcepack/assets/barkan/textures/furniture/forage/{iid}.png")
    if os.path.isfile("/tmp/forage_product.png"): z.write("/tmp/forage_product.png", "preview.png")
    z.writestr("README.md", f"""# Barkan Forage Pack v1 — {len(ids)} handcrafted 3D foraging props
CraftEngine furniture: mushrooms x8, apple, berry bush, magic herb.
Install: drop `configuration/` + `resourcepack/` into your CraftEngine pack namespace, `/ce reload all`.
Items: {", ".join("barkan:forage_"+i["id"] for i in mf["items"])}
Built with pixel-forge modelkit (zone shading / painted rounding / material gloss-matte / contact AO).
Original models & textures. Palette direction referenced from public product imagery. Server-use license.
""")
print("dist:", zp, os.path.getsize(zp), "bytes,", len(ids), "items")
