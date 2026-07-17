# 채집물 페인터 레지스트리 — 아이템 = 파라메트릭 함수(seed로 변형 생성).
# 모든 색은 palette.ramp()에서. 광원 = top-left 고정 (STYLE 참조).
import sys, os, random
SKILL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".claude", "skills", "pixel-art", "scripts")
sys.path.insert(0, SKILL)
from palette import ramp, rgba
from PIL import Image, ImageDraw

STYLE = {"light": "top-left", "canvas": 16, "margin": 1}

def C():
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)

def mushroom(base, spot="f2ede2", seed=0):
    rnd = random.Random(seed)
    r = ramp(base); st = ramp("d9caa2")
    im, d = C()
    d.pieslice((1, 2, 14, 12), 180, 360, fill=rgba(r[2]))
    d.pieslice((1, 2, 10, 9), 180, 360, fill=rgba(r[3]))
    d.pieslice((2, 2, 7, 6), 180, 360, fill=rgba(r[4]))
    d.line((1, 7, 14, 7), fill=rgba(r[1]))
    for x, y in [(11, 5), (12, 4)]: d.point((x, y), fill=rgba(r[1]))
    spots = rnd.sample([(4, 4), (7, 3), (5, 6), (9, 4), (10, 6), (6, 5)], 3)
    for x, y in spots: d.point((x, y), fill=rgba(spot))
    d.rectangle((6, 8, 9, 14), fill=rgba(st[2]))
    d.line((6, 8, 6, 14), fill=rgba(st[3]))
    d.line((9, 8, 9, 14), fill=rgba(st[1]))
    d.line((6, 14, 9, 14), fill=rgba(st[0]))
    return im

def apple(base="c0392b", seed=0):
    r = ramp(base); lf = ramp("4e8f3a"); wd = ramp("6b4a2a")
    im, d = C()
    d.ellipse((3, 4, 13, 14), fill=rgba(r[2]))
    d.ellipse((3, 4, 10, 11), fill=rgba(r[3]))
    d.ellipse((9, 9, 13, 14), fill=rgba(r[1]))
    for p in [(12, 12), (11, 13)]: d.point(p, fill=rgba(r[0]))
    d.line((4, 12, 6, 13), fill=rgba(r[2]))
    for p in [(5, 6), (6, 6), (5, 7)]: d.point(p, fill=(255, 241, 236, 255))
    d.line((8, 2, 8, 4), fill=rgba(wd[1]))
    d.polygon([(9, 2), (12, 1), (12, 4), (9, 4)], fill=rgba(lf[2])); d.line((9, 2, 11, 2), fill=rgba(lf[3]))
    return im

def berry(base="b8324a", seed=0):
    rnd = random.Random(seed)
    r = ramp(base); g = ramp("4e8f3a"); wd = ramp("6b4a2a")
    im, d = C()
    d.line((8, 3, 8, 7), fill=rgba(wd[1]))
    d.polygon([(8, 4), (11, 2), (13, 4), (10, 6)], fill=rgba(g[2])); d.line((9, 3, 11, 3), fill=rgba(g[3]))
    pts = [(6, 9), (10, 9), (8, 12)] if seed == 0 else rnd.sample([(6, 9), (10, 9), (8, 12), (6, 12), (10, 12)], 3)
    for cx, cy in pts:
        d.ellipse((cx-2, cy-2, cx+2, cy+2), fill=rgba(r[2]))
        d.ellipse((cx-2, cy-2, cx+1, cy+1), fill=rgba(r[3]))
        d.ellipse((cx+1, cy+1, cx+2, cy+2), fill=rgba(r[0]))
        d.point((cx-1, cy-1), fill=(255, 225, 225, 255))
    return im

def flower(petal="b9a8e0", center="7a4aa8", seed=0):
    p = ramp(petal); g = ramp("4e8f3a"); ctr = ramp(center)
    im, d = C()
    d.line((8, 8, 8, 15), fill=rgba(g[2]))
    d.polygon([(8, 12), (4, 11), (5, 14), (8, 13)], fill=rgba(g[2])); d.line((5, 12, 7, 13), fill=rgba(g[3]))
    for dx, dy in [(0, -3), (-3, -1), (3, -1), (-2, 2), (2, 2)]:
        cx, cy = 8+dx, 5+dy
        d.ellipse((cx-2, cy-2, cx+1, cy+1), fill=rgba(p[3]))
        d.ellipse((cx-1, cy, cx+1, cy+1), fill=rgba(p[1]))
        d.point((cx-1, cy-2), fill=rgba(p[4]))
    d.ellipse((6, 3, 9, 6), fill=rgba(ctr[2])); d.point((7, 4), fill=rgba(ctr[3]))
    return im

# ── 박스 조합형(청키 복셀) 버섯 — MCModels Foraging Pack 레퍼런스 방식 ──
# 스프라이트가 아니라 (아틀라스 텍스처, 모델 elements)를 반환. 캡=넓은 박스, 줄기=좁은 박스.
# 팔레트는 refboard에서 추출한 뮤트 톤(d6b151 황토·ad95bb 라벤더·ac9d57 황토줄기·aca289 크림).
def _atlas(cap, stem):
    r, st = ramp(cap), ramp(stem)
    im, d = C()
    d.rectangle((0, 0, 15, 3), fill=rgba(r[3]))            # cap top (밝음, 위를 봄)
    for x, y in [(2, 1), (6, 2), (11, 1), (13, 2), (4, 3)]: d.point((x, y), fill=rgba(r[4]))
    d.rectangle((0, 4, 15, 7), fill=rgba(r[2]))            # cap side
    d.line((0, 7, 15, 7), fill=rgba(r[1]))
    d.rectangle((0, 8, 15, 9), fill=rgba(r[1]))            # cap under (그늘)
    d.rectangle((0, 10, 15, 15), fill=rgba(st[2]))         # stem
    d.rectangle((0, 10, 1, 15), fill=rgba(st[3]))
    d.rectangle((14, 10, 15, 15), fill=rgba(st[1]))
    return im

def _box(f, t, kind):
    w = min(16, t[0]-f[0]); dz = min(16, t[2]-f[2]); h = min(6, t[1]-f[1])
    top   = {"uv": [0, 0, w, min(4, dz)], "texture": "#0"}
    side  = {"uv": [0, 4, w, 4+min(4, h)], "texture": "#0"} if kind == "cap" else {"uv": [0, 10, w, 10+min(6, h)], "texture": "#0"}
    under = {"uv": [0, 8, w, 9], "texture": "#0"} if kind == "cap" else side
    sz    = {"uv": [0, side["uv"][1], dz, side["uv"][3]], "texture": "#0"}
    return {"from": list(f), "to": list(t),
            "faces": {"up": top, "down": under, "north": side, "south": side, "west": sz, "east": sz}}

def voxel_mushroom(shape, cap, stem, seed=0):
    els = []
    if shape == "table":                                    # 낮은 테이블캡 (ref 황토)
        els = [_box((6, 0, 6), (10, 7, 10), "stem"), _box((3, 6, 3), (13, 10, 13), "cap")]
    elif shape == "shelf":                                  # 2단 선반 (ref 라벤더)
        els = [_box((7, 0, 7), (9, 13, 9), "stem"),
               _box((3, 4, 6), (10, 7, 12), "cap"), _box((5, 10, 4), (13, 14, 11), "cap")]
    elif shape == "cluster":                                # 3발 다발 (ref 상아)
        els = [_box((3, 0, 7), (5, 6, 9), "stem"),  _box((1, 5, 5), (7, 8, 11), "cap"),
               _box((7, 0, 6), (9, 9, 8), "stem"),  _box((5, 8, 4), (11, 12, 10), "cap"),
               _box((11, 0, 8), (13, 5, 10), "stem"), _box((9, 4, 6), (15, 7, 12), "cap")]
    return _atlas(cap, stem), els

# id -> (함수, kwargs). build.py가 manifest의 painter 키로 찾음.
REGISTRY = {
    "mush_red":     (mushroom, {"base": "c0392b"}),
    "mush_blue":    (mushroom, {"base": "3a7ca5"}),
    "mush_orange":  (mushroom, {"base": "d97a2b"}),
    "herb_magic":   (flower,   {"petal": "b9a8e0", "center": "7a4aa8"}),
    "berry_wild":   (berry,    {}),
    "fruit_apple":  (apple,    {}),
    # 레퍼런스 추출 팔레트 (refboard/paidpacks — 참조용)
    "mush_table":   (voxel_mushroom, {"shape": "table",   "cap": "d6b151", "stem": "cfc39b"}),
    "mush_shelf":   (voxel_mushroom, {"shape": "shelf",   "cap": "ad95bb", "stem": "ac9d57"}),
    "mush_cluster": (voxel_mushroom, {"shape": "cluster", "cap": "e8e2d2", "stem": "aca289"}),
}
