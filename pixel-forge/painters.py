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
    k.box((6, 0, 6), (10, 6, 10), Mat("d9caa2", var=0.7, grain="v", ao_top=True), cull=("up",))
    k.dome(8, 5, 8, 10, 6, Mat(base, marks=SPOTS))
    return _build(k)

def table_mush(cap, stem, seed=0):
    k = Kit(seed)
    k.box((6, 0, 6), (10, 9, 10), Mat(stem, grain="v", ao_top=True), cull=("up",))
    k.rounded_box((3, 8, 3), (13, 12, 13), Mat(cap))
    return _build(k)

def shelf_mush(cap, stem, seed=0):
    k = Kit(seed)
    k.box((7, 0, 7), (9, 13, 9), Mat(stem, grain="v", ao_top=True))
    k.rounded_box((3, 4, 6), (10, 7, 12), Mat(cap))
    k.rounded_box((5, 10, 4), (13, 14, 11), Mat(cap))
    return _build(k)

def cluster_mush(cap, stem, seed=0):
    k = Kit(seed); cm, sm = Mat(cap), Mat(stem, grain="v", ao_top=True)
    for (sx, sz, sh, cw) in [(4, 8, 6, 6), (8, 7, 9, 6), (12, 9, 5, 6)]:
        k.box((sx-1, 0, sz-1), (sx+1, sh, sz+1), sm, cull=("up",))
        k.rounded_box((sx-cw/2, sh-1, sz-cw/2), (sx+cw/2, sh+2, sz+cw/2), cm)
    return _build(k)

def magic_flower(petal, center, seed=0):
    k = Kit(seed)
    g = Mat("4e8f3a"); p = Mat(petal, var=0.8); c = Mat(center, var=0.6)
    k.box((7, 0, 7), (9, 9, 9), g)                       # 줄기
    k.box((9, 3, 7), (12, 5, 9), g)                      # 잎
    k.box((6, 9, 6), (10, 12, 10), c)                    # 중심
    for f, t in [((3, 9, 6), (6, 12, 10)), ((10, 9, 6), (13, 12, 10)),
                 ((6, 9, 3), (10, 12, 6)), ((6, 9, 10), (10, 12, 13))]:
        k.box(f, t, p)                                   # 사방 꽃잎
    k.box((6, 12, 6), (10, 13, 10), p, cull=("down",))   # 윗꽃잎
    return _build(k)

def berry_bush(base="d12b47", seed=0):
    k = Kit(seed)
    k.box((7, 0, 7), (9, 8, 9), Mat("6b4a2a", var=0.7, grain="v"))                       # 가지
    k.rounded_box((5.5, 6.5, 5.5), (10.5, 10.5, 10.5), Mat("4e8f3a"))  # 잎뭉치
    bm = Mat(base, gloss=True)
    for f, t in [((4, 4, 6), (7, 7, 9)), ((9, 4, 7), (12, 7, 10)), ((6, 1, 5), (9, 4, 8))]:
        k.box(f, t, bm)                                  # 베리 3알
    return _build(k)

def apple(base="e11f2c", seed=0):
    k = Kit(seed)
    k.rounded_box((4, 0, 4), (12, 9, 12), Mat(base, gloss=True))          # 몸통(베벨)
    k.box((7.5, 9, 7.5), (8.5, 11.5, 8.5), Mat("6b4a2a", var=0.7, grain="v"))             # 꼭지
    k.box((8.5, 10, 6.5), (12.5, 12, 8.5), Mat("4e8f3a"))             # 잎
    return _build(k)

# id -> (함수, kwargs). build.py가 manifest의 painter 키로 찾음. 전부 modelkit 3D.
REGISTRY = {
    "mush_red":     (fairy, {"base": "cf3f31"}),
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

def tall_mush(cap, stem, seed=0):
    """톨캡: 긴 줄기 + 높은 원통캡 (ref 초록 버섯)."""
    k = Kit(seed)
    k.box((6.5, 0, 6.5), (9.5, 10, 9.5), Mat(stem, grain="v", ao_top=True))
    k.rounded_box((4.5, 9, 4.5), (11.5, 15, 11.5), Mat(cap))
    return _build(k)

def double_mush(cap, stem, seed=0):
    """2단캡: 아래 넓은 갓 + 위 좁은 갓 (ref 핑크 버섯)."""
    k = Kit(seed)
    k.box((6.5, 0, 6.5), (9.5, 7, 9.5), Mat(stem, grain="v", ao_top=True))
    k.rounded_box((3, 6, 3), (13, 9.5, 13), Mat(cap))
    k.rounded_box((5.5, 9.5, 5.5), (10.5, 13, 10.5), Mat(cap))
    return _build(k)

REGISTRY["mush_tallgreen"] = (tall_mush, {"cap": "8fae7a", "stem": "cfc39b"})
REGISTRY["mush_pinkdouble"] = (double_mush, {"cap": "d99aa8", "stem": "d9caa2"})

# ═══════ 지역별 채집물 신작 (2026-07-17 목표: 지역 특산 + 요리 연동) ═══════

def tuft(base="d8b23a", seed=0):
    """이삭 다발: 기울어진 줄기 3대 + 이삭머리 (평원 황금이삭)."""
    k = Kit(seed); st = Mat("b8a04e", var=0.7, grain="v"); hd = Mat(base, var=0.8)
    for i, (x, z, h) in enumerate([(5, 7, 8), (8, 8, 11), (11, 7, 9)]):
        k.box((x-0.5, 0, z-0.5), (x+0.5, h, z+0.5), st)
        k.rounded_box((x-1.5, h-1, z-1.5), (x+1.5, h+3, z+1.5), hd)
    return _build(k)

def fern(base="3f7a37", seed=0):
    """고사리: 중심 줄기 + 좌우 계단식 잎판 (깊은숲)."""
    k = Kit(seed); g = Mat(base, var=0.9); s = Mat("2e5d2a", var=0.7, grain="v")
    k.box((7.5, 0, 7.5), (8.5, 10, 8.5), s)
    for y, w in [(2, 5), (5, 4), (8, 3)]:
        k.box((8-w-0.5, y, 7), (7.5, y+1.5, 9), g)      # 왼잎
        k.box((8.5, y+1, 7), (8+w+0.5, y+2.5, 9), g)    # 오른잎(엇갈림)
    k.box((7, 10, 7), (9, 12, 9), g)                     # 새순
    return _build(k)

def cattail(seed=0):
    """부들: 긴 줄기 2대 + 갈색 소시지 이삭 (늪지대)."""
    k = Kit(seed); st = Mat("5f7a44", var=0.7, grain="v"); hd = Mat("6b4a2a", var=0.6, grain="v")
    lf = Mat("4e6e3a", var=0.8)
    k.box((5.5, 0, 7.5), (6.5, 9, 8.5), st); k.box((5, 9, 7), (7, 14, 9), hd)
    k.box((9.5, 0, 8), (10.5, 7, 9), st);   k.box((9, 7, 7.5), (11, 11, 9.5), hd)
    k.box((7, 0, 6.5), (8.5, 6, 7.5), lf)                # 잎풀
    return _build(k)

def prickly(seed=0):
    """가시배 선인장: 패들 2장 + 마젠타 열매 (사막 — 유저 요청 선인장열매)."""
    k = Kit(seed); c = Mat("5c8a4a", var=0.8); fr = Mat("c2447e", gloss=True)
    k.box((5, 0, 6.5), (11, 8, 9.5), c)                  # 본체 패들
    k.box((3.5, 5, 7), (7, 12, 9), c)                    # 윗 패들(좌)
    k.box((9, 6, 7.2), (12.5, 11, 8.8), c)               # 윗 패들(우)
    for f, t in [((4, 12, 7.2), (6, 14, 8.8)), ((10, 11, 7.3), (11.8, 12.8, 8.7)), ((6.5, 8, 6.2), (8, 9.5, 7.4))]:
        k.box(f, t, fr)                                  # 열매 3알
    return _build(k)

def sagebush(seed=0):
    """사막세이지: 은녹색 낮은 허브 덤불 (사막)."""
    k = Kit(seed); g = Mat("8ba07c", var=0.9); s = Mat("6d8060", var=0.8)
    k.rounded_box((3.5, 0, 4.5), (9, 5, 10), g)
    k.rounded_box((8, 0, 6.5), (12.5, 4, 11), s)
    k.box((6, 5, 6.5), (8, 7.5, 8.5), g); k.box((9.5, 4, 8), (11, 6, 9.5), s)  # 웃자란 순
    return _build(k)

def crystal(base="b03030", glow="e8d8ff", seed=0):
    """수정초: 기울기 느낌의 계단식 스파이크 3개 (붉은사막 핏빛/동굴 자수정)."""
    k = Kit(seed); c = Mat(base, gloss=True)
    k.box((4, 0, 6), (7, 6, 9), c)
    k.box((5, 6, 6.5), (6.5, 9, 8.5), c)                 # 계단 팁
    k.box((8, 0, 7), (11, 9, 10), c)
    k.box((8.8, 9, 7.8), (10.2, 13, 9.2), c)
    k.box((11, 0, 5.5), (13, 4, 7.5), c)
    k.box((11.5, 4, 6), (12.5, 6, 7), c)
    return _build(k)

def rosette(base="5e8a52", seed=0):
    """바위솔: 다육 로제트 — 중심 + 두꺼운 잎 4방 (절벽)."""
    k = Kit(seed); g = Mat(base, var=0.7); c = Mat("7fae6e", var=0.6)
    k.box((6, 0, 6), (10, 3.5, 10), c)                   # 중심
    for f, t in [((2.5, 0, 5.5), (6, 2.5, 10.5)), ((10, 0, 5.5), (13.5, 2.5, 10.5)),
                 ((5.5, 0, 2.5), (10.5, 2.5, 6)), ((5.5, 0, 10), (10.5, 2.5, 13.5))]:
        k.box(f, t, g)
    k.box((7, 3.5, 7), (9, 5.5, 9), c)                   # 꼭지순
    return _build(k)

def watercress(seed=0):
    """물냉이: 밝은 초록 낮은 물풀 다발 (강)."""
    k = Kit(seed); g = Mat("4e9e4e", var=0.9); d = Mat("3a7a3a", var=0.8)
    k.rounded_box((3.5, 0, 5), (8.5, 3, 10.5), g)
    k.rounded_box((7.5, 0, 6.5), (12.5, 3.8, 11), d)
    k.box((5.5, 3, 6.5), (7, 5, 8), g); k.box((9.5, 3.8, 8), (11, 5.5, 9.5), d)
    return _build(k)

REGISTRY.update({
    # 평원
    "tuft_gold":     (tuft,   {"base": "d8b23a"}),
    "flower_daisy":  (magic_flower, {"petal": "eeeae0", "center": "d8b23a"}),
    # 깊은 숲
    "fern_green":    (fern,   {}),
    "acorn_cluster": (berry_bush, {"base": "8a6134"}),
    # 늪지대
    "cattail":       (cattail, {}),
    "mush_poison":   (fairy,  {"base": "7a5b9e", "spot": "b8e08a"}) if False else (fairy, {"base": "7a5b9e"}),
    # 사막
    "prickly_pear":  (prickly, {}),
    "sage_desert":   (sagebush, {}),
    # 붉은사막
    "crystal_blood": (crystal, {"base": "b03030"}),
    "flower_ember":  (magic_flower, {"petal": "d97a2b", "center": "5c3a28"}),
    # 정상
    "flower_snow":   (magic_flower, {"petal": "f0f2ee", "center": "a8c8d8"}),
    "berry_frost":   (berry_bush, {"base": "6fb8d8"}),
    # 절벽
    "rosette_rock":  (rosette, {}),
    "flower_bell":   (magic_flower, {"petal": "6f8fd8", "center": "3a5aa8"}),
    # 동굴
    "mush_glow":     (fairy,  {"base": "3fbfae"}),
    "crystal_ame":   (crystal, {"base": "9a6fd8"}),
    # 강
    "watercress":    (watercress, {}),
})
