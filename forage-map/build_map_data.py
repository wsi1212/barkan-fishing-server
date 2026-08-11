"""forage-nodes.json / forage-types.json / region-topdown-barkan.json (data/) ->
forage_map_data.json — 지도 아티팩트가 그대로 embed할 압축 데이터.
data/ 안의 원본 3개는 prod에서 새로 받아와야 최신 상태(SSH로 수동 갱신, 이 스크립트는 가공만)."""
import json, base64, io, colorsys, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

from PIL import Image
from terrain_colors import color_for

topdown = json.load(open(f"{DATA}/region-topdown-barkan.json"))
nodes = json.load(open(f"{DATA}/forage-nodes.json"))
types = json.load(open(f"{DATA}/forage-types.json"))

grid = topdown["grid"]
legend = topdown["legend"]
mask = topdown["in_region_mask"]
heights = topdown["heights"]
gw, gd = topdown["grid_width"], topdown["grid_depth"]
cell_size = topdown["cell_size"]

img = Image.new("RGB", (gw, gd))
px = img.load()
for z in range(gd):
    row = grid[z]
    mrow = mask[z]
    for x in range(gw):
        r, g, b = color_for(legend[row[x]])
        if mrow[x] == 0:
            r, g, b = int(r * 0.45 + 20), int(g * 0.45 + 22), int(b * 0.45 + 28)
        px[x, z] = (r, g, b)

buf = io.BytesIO()
img.save(buf, format="PNG", optimize=True)
png_b64 = base64.b64encode(buf.getvalue()).decode()

# per-species color: golden-angle hue spacing for max distinctness
type_ids = list(types.keys())
GOLDEN = 137.508
species_color = {}
for i, tid in enumerate(type_ids):
    hue = (i * GOLDEN) % 360
    rr, gg, bb = colorsys.hls_to_rgb(hue / 360.0, 0.58, 0.62)
    species_color[tid] = "#%02x%02x%02x" % (int(rr * 255), int(gg * 255), int(bb * 255))

node_list = []
for n in nodes.values():
    t = types.get(n["typeId"], {})
    node_list.append({
        "x": n["x"], "z": n["z"], "typeId": n["typeId"],
        "name": t.get("name", n["typeId"]),
        "region": t.get("region", "?"),
        "rarity": t.get("rarity", "흔함"),
        "color": species_color.get(n["typeId"], "#999999"),
    })

region_order, species_catalog, counts = [], [], {}
for n in node_list:
    counts[n["typeId"]] = counts.get(n["typeId"], 0) + 1
for tid, t in types.items():
    if t["region"] not in region_order:
        region_order.append(t["region"])
    species_catalog.append({
        "typeId": tid, "name": t["name"], "region": t["region"],
        "rarity": t["rarity"], "color": species_color[tid],
        "count": counts.get(tid, 0),
    })

meta = {
    "x_origin": topdown["x_origin"], "z_origin": topdown["z_origin"],
    "region_width": topdown["region_width"], "region_depth": topdown["region_depth"],
    "grid_width": gw, "grid_depth": gd,
}

# 클라이언트 사이드 후보 생성용 대략 지형 조회 그리드 (배경 PNG보다 훨씬 성글게 —
# 파일 크기 절약. DS칸(예 4x4 원본셀)마다 1개 대표값만 samples — 정밀 배치는 항상
# 서버에서(3D 조회/설치 확정 시) 실제 블록으로 다시 확인하므로 근사치면 충분.
DS = 4  # downsample factor: lookup cell = DS * cell_size 블록
lw, ld = (gw + DS - 1) // DS, (gd + DS - 1) // DS
leaf_idx = {i for i, m in enumerate(legend) if "leaves" in m}
lookup_material = []
lookup_height = []
lookup_canopy = []  # true면 이 성긴 칸 범위 안 원본 셀 중 나뭇잎이 하나라도 있음
# (열매=under_leaves 후보를 나무 근처로 편향시키는 용도 — 대표점 1개만 보면 작은
#  나무는 놓치므로 DS x DS 범위 전체를 훑어서 판정. leaves 그 자체가 목적이므로 이건 유지)
for lz in range(ld):
    mrow, hrow, crow = [], [], []
    for lx in range(lw):
        sx, sz = min(lx * DS, gw - 1), min(lz * DS, gd - 1)
        mrow.append(grid[sz][sx] if mask[sz][sx] else -1)  # -1 = 지역 밖
        hrow.append(heights[sz][sx])
        has_leaf = False
        for dz in range(DS):
            zz = lz * DS + dz
            if zz >= gd:
                break
            row = grid[zz]
            for dx in range(DS):
                xx = lx * DS + dx
                if xx >= gw:
                    break
                if row[xx] in leaf_idx:
                    has_leaf = True
                    break
            if has_leaf:
                break
        crow.append(1 if has_leaf else 0)
    lookup_material.append(mrow)
    lookup_height.append(hrow)
    lookup_canopy.append(crow)

# ---- 원목(log/wood) 전용 정밀 인덱스 (2026-07-28 신설) ----
# 기존 canopy(나뭇잎) 그리드가 adjacent_log 후보 생성에도 재사용되고 있었는데,
# 나뭇잎 캐노피는 실제 몸통(log)보다 훨씬 넓게 퍼져 있어서(가지 끝 나뭇잎이 몸통에서
# 여러 블록 떨어짐 + DS=4로 16블록 칸 3x3 = 48블록 반경까지 "근처" 판정) "나뭇잎 있음"이
# "반경1 원목 인접"의 대용 지표로 너무 부정확함 — 실사용 33개 중 31개가 이 캐노피 체크는
# 통과했지만 실제로는 최인접 원목까지 8~21블록이나 떨어져 있었음(전수조사로 확인).
# 원목은 잔디밭에 비해 훨씬 희소하므로(이 지역 기준 base grid 443,435칸 중 3,173칸=0.7%)
# DS 다운샘플 없이 base cell_size(4블록) 그대로, 게다가 dense grid가 아니라 sparse
# [lx,lz] 좌표 리스트로만 저장 — 정밀도는 최대, 파일 크기 증가는 미미(수만자 수준).
def is_log_material(m):
    m = m.split(":", 1)[-1]
    return "log" in m or m.endswith("_wood")

log_idx = {i for i, m in enumerate(legend) if is_log_material(m)}
log_cells = []
for z in range(gd):
    row = grid[z]
    mrow = mask[z]
    for x in range(gw):
        if mrow[x] and row[x] in log_idx:
            log_cells.append([x, z])

terrain_lookup = {
    "x_origin": topdown["x_origin"], "z_origin": topdown["z_origin"],
    "cell_size": cell_size * DS, "grid_width": lw, "grid_depth": ld,
    "legend": legend, "material": lookup_material, "height": lookup_height,
    "canopy": lookup_canopy,
    # log_cells는 base cell_size(4블록) 그리드 좌표(다운샘플 없음) — x_origin/z_origin은
    # 위와 동일하게 topdown 기준 재사용, 칸 크기만 log_cell_size로 별도 표기.
    "log_cell_size": cell_size,
    "log_cells": log_cells,
}

habitat = json.load(open(os.path.join(HERE, "habitat-rules.json")))
habitat.pop("_readme", None)

out = {
    "png_b64": png_b64, "nodes": node_list, "meta": meta,
    "species_catalog": species_catalog, "region_order": region_order,
    "habitat_rules": habitat, "terrain_lookup": terrain_lookup,
    "preview_nodes": [],  # 배치 요청 처리 후 voxel_preview.py로 채워서 다시 republish
}
with open(os.path.join(HERE, "forage_map_data.json"), "w") as f:
    json.dump(out, f)

print("nodes:", len(node_list), "species:", len(species_catalog),
      "grid:", gw, "x", gd, "cell_size", topdown["cell_size"],
      "lookup:", lw, "x", ld, "cell", cell_size * DS,
      "log_cells:", len(log_cells))
