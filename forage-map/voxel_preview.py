"""후보 좌표 하나당 mc_get_region으로 받은 로컬 블록 스냅샷 -> forage_map.html의
'미리보기' 3D 팝업이 바로 그릴 수 있는 voxel dict.

사용법 (실제 배치 요청을 처리할 때):
    1. 후보점 (x, y, z) 주변 cuboid를 mc_get_region으로 스캔
       (예: x-5..x+5, y-3..y+3, z-5..z+5 — HALF_X/HALF_Z/HALF_Y 상수 참고)
    2. build_voxel(blocks, x0, y0, z0, sx, sy, sz) 호출 -> voxel dict
    3. 그 dict를 preview_nodes[i]["voxel"]에 넣고 build_map_data.py가 만든
       forage_map_data.json의 preview_nodes를 이 값들로 교체한 뒤 render_map.py 재실행
"""
from terrain_colors import color_for

HALF_X, HALF_Z, HALF_Y_DOWN, HALF_Y_UP = 5, 5, 3, 4


def region_bounds(x, y, z):
    """mc_get_region 호출용 바운딩박스 (x1,y1,z1,x2,y2,z2)."""
    return (int(x) - HALF_X, int(y) - HALF_Y_DOWN, int(z) - HALF_Z,
            int(x) + HALF_X, int(y) + HALF_Y_UP, int(z) + HALF_Z)


def build_voxel(blocks, x0, y0, z0, sx, sy, sz):
    """blocks: mc_get_region 결과의 block 리스트, 각 {"x","y","z","material"} (world 좌표, non-air만).
    x0,y0,z0: 그 cuboid의 최소 모서리(world 좌표). sx,sy,sz: 각 축 크기."""
    legend = ["minecraft:air"]
    legend_index = {"minecraft:air": 0}
    idx = [[[0] * sx for _ in range(sz)] for _ in range(sy)]

    for b in blocks:
        lx, ly, lz = b["x"] - x0, b["y"] - y0, b["z"] - z0
        if not (0 <= lx < sx and 0 <= ly < sy and 0 <= lz < sz):
            continue
        mat = b["material"]
        if mat not in legend_index:
            legend_index[mat] = len(legend)
            legend.append(mat)
        idx[int(ly)][int(lz)][int(lx)] = legend_index[mat]

    colors = [list(color_for(m)) for m in legend]
    return {
        "x0": x0, "y0": y0, "z0": z0, "sx": sx, "sy": sy, "sz": sz,
        "legend": legend, "colors": colors, "idx": idx,
    }
