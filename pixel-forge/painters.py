# 채집물 페인터 레지스트리 — modelkit 선언식.
# 페인터 = 모양(박스/rounded_box/dome) + 재질(Mat) 선언 몇 줄. 노이즈 텍스처·1:1 UV·베벨·컬링은 Kit이 보장.
# 팔레트 근거: refboard 추출(뮤트 톤) + palette.ramp 색조이동. 광원 top-left 고정.
from modelkit import Kit, Mat
from palette import ramp, rgba

WHITE = (242, 237, 226, 255)

def _build(kit):
    im, model = kit.build("_")                 # 텍스처 ref는 build.py가 바인딩
    return im, model["elements"]

SPOTS = [(0.2, 0.2, WHITE), (0.65, 0.15, WHITE), (0.4, 0.55, WHITE), (0.85, 0.5, WHITE)]

def fairy(base, seed=0):
    """요정버섯: 돔 캡(점박이) + 원통 줄기."""
    k = Kit(seed)
    k.box((6, 0, 6), (10, 6, 10), Mat("d9caa2"), cull=("up",))
    k.dome(8, 5, 8, 10, 6, Mat(base, spec=2, marks=SPOTS))
    return _build(k)

def table_mush(cap, stem, seed=0):
    k = Kit(seed)
    k.box((6, 0, 6), (10, 9, 10), Mat(stem), cull=("up",))
    k.rounded_box((3, 8, 3), (13, 12, 13), Mat(cap, spec=2))
    return _build(k)

def shelf_mush(cap, stem, seed=0):
    k = Kit(seed)
    k.box((7, 0, 7), (9, 13, 9), Mat(stem))
    k.rounded_box((3, 4, 6), (10, 7, 12), Mat(cap, spec=1))
    k.rounded_box((5, 10, 4), (13, 14, 11), Mat(cap, spec=2))
    return _build(k)

def cluster_mush(cap, stem, seed=0):
    k = Kit(seed); cm, sm = Mat(cap, spec=1), Mat(stem)
    for (sx, sz, sh, cw) in [(4, 8, 6, 6), (8, 7, 9, 6), (12, 9, 5, 6)]:
        k.box((sx-1, 0, sz-1), (sx+1, sh, sz+1), sm, cull=("up",))
        k.rounded_box((sx-cw/2, sh-1, sz-cw/2), (sx+cw/2, sh+2, sz+cw/2), cm)
    return _build(k)

def magic_flower(petal, center, seed=0):
    k = Kit(seed)
    g = Mat("4e8f3a"); p = Mat(petal, spec=1); c = Mat(center, vgrad=False)
    k.box((7, 0, 7), (9, 9, 9), g)                       # 줄기
    k.box((9, 3, 7), (12, 5, 9), g)                      # 잎
    k.box((6, 9, 6), (10, 12, 10), c)                    # 중심
    for f, t in [((3, 9, 6), (6, 12, 10)), ((10, 9, 6), (13, 12, 10)),
                 ((6, 9, 3), (10, 12, 6)), ((6, 9, 10), (10, 12, 13))]:
        k.box(f, t, p)                                   # 사방 꽃잎
    k.box((6, 12, 6), (10, 13, 10), p, cull=("down",))   # 윗꽃잎
    return _build(k)

def berry_bush(base="b8324a", seed=0):
    k = Kit(seed)
    k.box((7, 0, 7), (9, 8, 9), Mat("6b4a2a"))                       # 가지
    k.rounded_box((5.5, 6.5, 5.5), (10.5, 10.5, 10.5), Mat("4e8f3a"))  # 잎뭉치
    bm = Mat(base, spec=1)
    for f, t in [((4, 4, 6), (7, 7, 9)), ((9, 4, 7), (12, 7, 10)), ((6, 1, 5), (9, 4, 8))]:
        k.box(f, t, bm)                                  # 베리 3알
    return _build(k)

def apple(base="c0392b", seed=0):
    k = Kit(seed)
    k.rounded_box((4, 0, 4), (12, 9, 12), Mat(base, spec=3))          # 몸통(베벨)
    k.box((7.5, 9, 7.5), (8.5, 11.5, 8.5), Mat("6b4a2a"))             # 꼭지
    k.box((8.5, 10, 6.5), (12.5, 12, 8.5), Mat("4e8f3a"))             # 잎
    return _build(k)

# id -> (함수, kwargs). build.py가 manifest의 painter 키로 찾음. 전부 modelkit 3D.
REGISTRY = {
    "mush_red":     (fairy, {"base": "c0392b"}),
    "mush_blue":    (fairy, {"base": "3a7ca5"}),
    "mush_orange":  (fairy, {"base": "d97a2b"}),
    "herb_magic":   (magic_flower, {"petal": "b9a8e0", "center": "7a4aa8"}),
    "berry_wild":   (berry_bush, {}),
    "fruit_apple":  (apple, {}),
    # 레퍼런스 추출 팔레트 (refboard/paidpacks)
    "mush_table":   (table_mush, {"cap": "d6b151", "stem": "cfc39b"}),
    "mush_shelf":   (shelf_mush, {"cap": "ad95bb", "stem": "ac9d57"}),
    "mush_cluster": (cluster_mush, {"cap": "e8e2d2", "stem": "aca289"}),
}
