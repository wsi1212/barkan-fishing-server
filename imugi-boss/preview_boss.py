#!/usr/bin/env python3
"""구운 마디 모델을 오프라인 정사영으로 렌더 → 자기검수용 PNG (의존성 없음, zlib만).

리그의 pivot/scale 로 모델 엘리먼트를 월드 좌표로 역변환해 그린다 = 인게임에서 레스트
포즈로 소환했을 때 보일 형상. 마디별 색(--mode seg) 과 재질별 색(--mode mat) 두 장.

사용: python3 preview_boss.py <name> [scale_px]
"""
import json, os, struct, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
RP = os.path.expanduser("~/development/barkan-resourcepack")

MATCOL = {
    "amethyst_block": (150, 98, 191), "amethyst_cluster": (150, 98, 191),
    "purpur_block": (170, 122, 170),
    "white_concrete": (231, 231, 231), "black_concrete": (25, 25, 28),
    "black_wool": (40, 36, 40), "pale_moss_block": (186, 190, 168),
    "oak_leaves": (76, 132, 56), "magenta_stained_glass": (200, 72, 200),
    "magenta_stained_glass_pane": (200, 72, 200), "sea_lantern": (222, 240, 230),
    "smooth_quartz_stairs": (226, 220, 213), "polished_blackstone_stairs": (58, 54, 62),
}
SEGCOL = [(226, 92, 92), (226, 156, 76), (222, 208, 84), (140, 210, 90), (78, 200, 150),
          (80, 176, 226), (110, 128, 226), (168, 108, 220), (222, 108, 186), (240, 240, 240)]
BG = (22, 26, 36)


def png(path, w, h, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c))
    out = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    open(path, "wb").write(out)


def load(name):
    rig = json.load(open(os.path.join(HERE, f"{name}_rig.json")))
    boxes = []   # (x0,y0,z0,x1,y1,z1, seg, mat)
    for s in rig["segments"]:
        i, k, piv = s["seg"], s["scale"], s["pivot"]
        mdl = json.load(open(os.path.join(RP, "assets/barkan/models", name,
                                          f"seg_{i:02d}.json")))
        for e in mdl["elements"]:
            tex = next(iter(e["faces"].values()))["texture"].lstrip("#")
            w0 = [piv[a] + (e["from"][a] / 16 - 0.5) * k for a in range(3)]
            w1 = [piv[a] + (e["to"][a] / 16 - 0.5) * k for a in range(3)]
            boxes.append((*w0, *w1, i, tex))
    return rig, boxes


def render(boxes, face, mode, px, path):
    # 축: (가로, 세로, 깊이) — 세로는 화면 아래로 갈수록 증가하도록 부호 처리
    if face == "south":   ax = (0, 1, 2); flip_h = False; near = "max"
    elif face == "west":  ax = (2, 1, 0); flip_h = False; near = "min"
    elif face == "top":   ax = (0, 2, 1); flip_h = False; near = "max"
    else: raise ValueError(face)
    lo = [min(min(b[a], b[a + 3]) for b in boxes) for a in range(3)]
    hi = [max(max(b[a], b[a + 3]) for b in boxes) for a in range(3)]
    W = int((hi[ax[0]] - lo[ax[0]]) * px) + 1
    H = int((hi[ax[1]] - lo[ax[1]]) * px) + 1
    buf = [[BG] * W for _ in range(H)]
    depth = [[None] * W for _ in range(H)]
    dlo, dhi = lo[ax[2]], hi[ax[2]]
    for b in sorted(boxes, key=lambda b: (b[ax[2]] + b[ax[2] + 3]),
                    reverse=(near == "min")):
        seg, mat = b[6], b[7]
        col = SEGCOL[seg % len(SEGCOL)] if mode == "seg" else MATCOL.get(mat, (255, 0, 255))
        d = (b[ax[2]] + b[ax[2] + 3]) / 2
        t = 0.0 if dhi == dlo else (d - dlo) / (dhi - dlo)
        if near == "max": shade = 0.45 + 0.55 * t
        else:             shade = 1.0 - 0.55 * t
        c = tuple(max(0, min(255, int(v * shade))) for v in col)
        u0 = int((min(b[ax[0]], b[ax[0] + 3]) - lo[ax[0]]) * px)
        u1 = int((max(b[ax[0]], b[ax[0] + 3]) - lo[ax[0]]) * px)
        # 세로축은 y(위가 +) 또는 z — y 는 뒤집어야 위가 위로 온다
        v_lo, v_hi = min(b[ax[1]], b[ax[1] + 3]), max(b[ax[1]], b[ax[1] + 3])
        if ax[1] == 1:
            v0 = int((hi[1] - v_hi) * px); v1 = int((hi[1] - v_lo) * px)
        else:
            v0 = int((v_lo - lo[ax[1]]) * px); v1 = int((v_hi - lo[ax[1]]) * px)
        for v in range(max(0, v0), min(H, max(v1, v0 + 1))):
            for u in range(max(0, u0), min(W, max(u1, u0 + 1))):
                if depth[v][u] is None or (d > depth[v][u] if near == "max" else d < depth[v][u]):
                    depth[v][u] = d
                    buf[v][u] = c
    png(path, W, H, [[ch for c in row for ch in c] for row in buf])
    print(f"  {path}  {W}x{H}")


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__)
    px = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    rig, boxes = load(name)
    print(f"{name}: {len(rig['segments'])} segs, {len(boxes)} boxes, "
          f"{len(rig['extra_displays'])} extra displays")
    for face in ("south", "west", "top"):
        for mode in ("mat", "seg"):
            render(boxes, face, mode, px, os.path.join(HERE, f"{name}_{face}_{mode}.png"))


if __name__ == "__main__":
    main()
