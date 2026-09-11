#!/usr/bin/env python3
"""자바 아이템/블록 모델(elements) → 베드락 geometry(.geo.json) 변환 — 실험용."""
import json
from pathlib import Path

def java_to_geo(model: dict, ident: str, tex_w: int, tex_h: int) -> dict:
    cubes = []
    for el in model.get("elements", []):
        f, t = el["from"], el["to"]
        # ★from > to 인 축이 있으면 정규화한다 — 자바는 뒤집힌 element 도 그려 주지만
        #   베드락 지오메트리는 «size 가 음수» 면 그 모델을 통째로 못 읽고 블록이 기본 모양으로
        #   떨어진다(2026-09-12 팩 검사에서 밀 2종이 이 상태였다). 손으로 만든 모델에 섞여 든다.
        f = [min(a, b) for a, b in zip(f, t)]
        t = [max(a, b) for a, b in zip(el["from"], el["to"])]
        size = [t[0]-f[0], t[1]-f[1], t[2]-f[2]]
        # 베드락은 x 축이 자바와 반대, 원점이 블록 중앙(x,z ∈ [-8,8])
        origin = [8 - t[0], f[1], f[2] - 8]
        uv = {}
        for face, fd in (el.get("faces") or {}).items():
            u1, v1, u2, v2 = fd.get("uv", [0, 0, 16, 16])
            # 자바 uv 는 텍스처 크기와 무관한 0~16 정규화 좌표
            px = lambda u, w: u / 16.0 * w
            bface = {"north": "north", "south": "south", "up": "up", "down": "down",
                     "east": "west", "west": "east"}[face]   # x 반전 → 동/서 교환
            uv[bface] = {"uv": [px(u1, tex_w), px(v1, tex_h)],
                         "uv_size": [px(u2-u1, tex_w), px(v2-v1, tex_h)]}
        cube = {"origin": origin, "size": size, "uv": uv}
        rot = el.get("rotation")
        if rot:
            ax = {"x": 0, "y": 1, "z": 2}[rot["axis"]]
            ang = rot["angle"]
            r = [0, 0, 0]
            # 베드락 회전은 자바와 부호가 반대인 축이 있다(x 반전의 결과)
            r[ax] = -ang if rot["axis"] in ("y", "z") else ang
            o = rot.get("origin", [8, 8, 8])
            cube["pivot"] = [8 - o[0], o[1], o[2] - 8]
            cube["rotation"] = r
        cubes.append(cube)
    return {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {
                "identifier": ident,
                "texture_width": tex_w,
                "texture_height": tex_h,
                "visible_bounds_width": 2,
                "visible_bounds_height": 2.5,
                "visible_bounds_offset": [0, 0.75, 0],
            },
            "bones": [{"name": "root", "pivot": [0, 0, 0], "cubes": cubes}],
        }],
    }

if __name__ == "__main__":
    import sys
    from PIL import Image
    src = Path(sys.argv[1]); tex = Path(sys.argv[2]); ident = sys.argv[3]
    m = json.loads(src.read_text())
    w, h = Image.open(tex).size
    print(json.dumps(java_to_geo(m, ident, w, h), indent=1)[:1200])
