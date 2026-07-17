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

# ═══════ 종별 실루엣 리워크 (2026-07-17: "색만 다르고 모양이 같다" 피드백) + 희귀종 ═══════
# 회전(rot) 지원으로 각짐 탈피 — 기울인 갓, 아치 고사리, 매달린 종꽃.

def squat_fairy(base, seed=0):
    """뚱뚱 땅딸보 버섯: 낮고 넓은 갓을 살짝 기울임 (파랑)."""
    k = Kit(seed)
    k.box((5.5, 0, 5.5), (10.5, 4, 10.5), Mat("d9caa2", var=0.7, grain="v"), cull=("up",))
    k.dome(8, 3, 8, 13, 5.5, Mat(base, marks=SPOTS), rot=("z", -22.5))
    return _build(k)

def slim_fairy(base, seed=0):
    """홀쭉 낭창 버섯: 가는 키다리 줄기 + 작은 뾰족갓 틸트 (주황)."""
    k = Kit(seed)
    k.box((7, 0, 7), (9, 9, 9), Mat("d9caa2", var=0.7, grain="v"), cull=("up",))
    k.box((7.6, 4, 6.2), (8.4, 8, 7.0), Mat("cfc39b", var=0.6, grain="v"), rot=("z", 22.5))   # 곁줄기
    k.dome(8, 8.5, 8, 8, 5, Mat(base, marks=SPOTS[:2]), rot=("x", 22.5))
    k.box((6.8, 12.5, 6.8), (9.2, 14.5, 9.2), Mat(base), rot=("x", 22.5))                     # 뾰족 꼭지
    return _build(k)

def poison_mush(base="7a5b9e", seed=0):
    """독그늘버섯: 우산처럼 층층이 처진 갓 (위로 갈수록 좁아지는 3단 스커트, 늪)."""
    k = Kit(seed); st = Mat("9a8f77", var=0.7, grain="v", ao_top=True)
    cap = Mat(base, marks=[(0.25, 0.4, (184, 224, 138, 255)), (0.7, 0.3, (184, 224, 138, 255))])
    k.box((6.5, 0, 6.5), (9.5, 6, 9.5), st)
    k.box((2.5, 5.5, 2.5), (13.5, 7, 13.5), cap, cull=("up",))                 # 최하단 스커트(가장 넓음)
    k.box((4, 7, 4), (12, 8.8, 12), cap)                                       # 중단
    k.box((5.5, 8.8, 5.5), (10.5, 10.6, 10.5), cap, cull=("down",))            # 상단 봉우리
    k.box((7, 10.6, 7), (9, 12, 9), cap, cull=("down",))                       # 꼭지
    return _build(k)

def glow_trio(base="3fbfae", seed=0):
    """야광버섯: 제각각 기운 삼발 다발 (동굴) — 발광 팔레트."""
    k = Kit(seed); st = Mat("bfd8cf", var=0.6, grain="v")
    specs = [(4.5, 8, 6, 7, ("z", 22.5)), (8.5, 7.5, 9, 8.5, ("x", -22.5)), (11.5, 9, 4.5, 6, ("z", -22.5))]
    for x, z, h, w, rr in specs:
        k.box((x-1, 0, z-1), (x+1, h, z+1), st, cull=("up",))
        k.dome(x, h-0.5, z, w, 3.5, Mat(base), layers=2, rot=rr)
    return _build(k)

def fern_arch(base="3f7a37", seed=0):
    """물결고사리 v3: 완만한 아치 줄기 + 아래로 갈수록 긴 수평 깃잎(끝만 살짝 처짐) + 말린 새순."""
    k = Kit(seed); g = Mat(base, var=0.9); gl = Mat("57944a", var=0.8); s = Mat("2e5d2a", var=0.7, grain="v")
    k.box((7.5, 0, 7.6), (8.5, 6.5, 8.4), s)
    k.box((7.8, 6.2, 7.6), (8.8, 10.5, 8.4), s, rot=("z", -22.5))               # 위쪽만 완만히 휨
    for y, w in [(1.6, 5.0), (3.4, 4.2), (5.2, 3.2)]:                           # 아래가 긴 깃잎 = 고사리 실루엣
        k.box((8-w-0.4, y, 7.5), (7.9, y+1.1, 8.5), g, rot=("z", -22.5, [7.9, y+0.5, 8]))   # 왼잎 끝처짐
        k.box((8.1, y+0.7, 7.5), (8+w+0.4, y+1.8, 8.5), gl, rot=("z", 22.5, [8.1, y+1.2, 8]))  # 오른잎 끝처짐(엇갈림)
    k.box((8.6, 9.2, 7.5), (10.8, 10.3, 8.5), g, rot=("z", -45))                # 휜 끝잎
    k.box((10, 9.9, 7.4), (11.6, 11.5, 8.6), gl, rot=("z", -22.5))              # 말린 새순
    return _build(k)

def flower_flat(petal="eeeae0", center="d8b23a", seed=0):
    """흰들국화: 활짝 핀 납작 꽃 — 수평 꽃잎 4장 + 노란 심 (평원)."""
    k = Kit(seed); g = Mat("4e8f3a", var=0.8); p = Mat(petal, var=0.6); c = Mat(center, var=0.5)
    k.box((7.5, 0, 7.5), (8.5, 7, 8.5), g)
    k.box((9, 2.5, 7.5), (11, 4, 8.5), g, rot=("z", -22.5))                    # 잎
    for f, t, rr in [((3, 7, 6.5), (8, 8.2, 9.5), ("z", 22.5)), ((8, 7, 6.5), (13, 8.2, 9.5), ("z", -22.5)),
                     ((6.5, 7, 3), (9.5, 8.2, 8), ("x", -22.5)), ((6.5, 7, 8), (9.5, 8.2, 13), ("x", 22.5))]:
        k.box(f, t, p, rot=rr)                                                 # 살짝 벌어진 꽃잎
    k.box((6.8, 7.6, 6.8), (9.2, 9, 9.2), c)                                   # 심
    return _build(k)

def flower_cup(petal="d97a2b", center="5c3a28", seed=0):
    """잿불꽃: 튤립형 컵 — 안으로 오므린 꽃잎 4면 + 이글대는 심 (붉은사막)."""
    k = Kit(seed); g = Mat("6e5844", var=0.8, grain="v"); p = Mat(petal, var=0.7); c = Mat("e8b23a", gloss=True)
    k.box((7.5, 0, 7.5), (8.5, 7, 8.5), g)
    for f, t, rr in [((4.5, 7, 6.5), (7.5, 12, 9.5), ("z", 22.5)), ((8.5, 7, 6.5), (11.5, 12, 9.5), ("z", -22.5)),
                     ((6.5, 7, 4.5), (9.5, 12, 7.5), ("x", -22.5)), ((6.5, 7, 8.5), (9.5, 12, 11.5), ("x", 22.5))]:
        k.box(f, t, p, rot=rr)                                                 # 컵 꽃잎
    k.box((7, 8, 7), (9, 11, 9), c)                                            # 불씨 심
    return _build(k)

def flower_star(petal="f0f2ee", center="a8c8d8", seed=0):
    """설화: 눈결정 별꽃 — 십자+대각(45°) 꽃잎 8방 (정상)."""
    k = Kit(seed); g = Mat("7a9a88", var=0.7, grain="v"); p = Mat(petal, var=0.5); c = Mat(center, var=0.5)
    k.box((7.5, 0, 7.5), (8.5, 6, 8.5), g)
    k.box((4.5, 6.5, 7.2), (11.5, 7.9, 8.8), p)                                # 가로 꽃잎
    k.box((7.2, 6.5, 4.5), (8.8, 7.9, 11.5), p)                                # 세로 꽃잎
    k.box((5.6, 6.7, 7.3), (10.4, 7.8, 8.7), p, rot=("y", 45))                 # 대각 꽃잎(짧게) = 육각 별
    k.box((5.6, 6.7, 7.3), (10.4, 7.8, 8.7), p, rot=("y", -45))
    k.box((7, 7.3, 7), (9, 8.9, 9), c)                                         # 심
    return _build(k)

def flower_bell(petal="6f8fd8", center="3a5aa8", seed=0):
    """벼랑초롱꽃: 굽은 줄기 끝에 매달린 종 + 종추 (절벽)."""
    k = Kit(seed); g = Mat("55755a", var=0.8, grain="v"); p = Mat(petal, var=0.7); c = Mat(center, var=0.6)
    k.box((6, 0, 7.5), (7, 8, 8.5), g)
    k.box((6.2, 7.5, 7.4), (7.2, 11, 8.4), g, rot=("z", -45))                  # 크게 휜 목
    k.box((8, 10.2, 7.4), (10.5, 11.2, 8.4), g, rot=("z", -22.5))              # 처진 끝
    k.box((8.7, 6.5, 6.6), (11.5, 10, 9.4), p, rot=("z", -22.5))               # 매달린 종 몸통
    k.box((9.2, 5.2, 7.1), (11, 6.6, 8.9), p, rot=("z", 22.5))                 # 종 입구(벌어짐)
    k.box((9.7, 4.4, 7.6), (10.5, 5.4, 8.4), c)                                # 종추
    return _build(k)

# ── 희귀종 ──
def truffle(seed=0):
    """트러플: 울퉁불퉁 검은 덩이 (깊은 숲 낙엽 밑, 희귀)."""
    k = Kit(seed)
    m = Mat("4a3a30", var=1.0, marks=[(0.3, 0.3, (30, 22, 18, 255)), (0.7, 0.55, (30, 22, 18, 255))])
    d = Mat("3a2d24", var=0.9)
    k.box((4.5, 0, 5), (10.5, 5, 11), m, rot=("y", 22.5))
    k.box((7.5, 0.5, 4.5), (12, 4.2, 9), d, rot=("y", -22.5))
    k.box((6, 4, 6.5), (10, 6.5, 10), d, rot=("y", 45))
    lf = Mat("6a5636", var=0.9)
    k.box((3.5, 0, 8.5), (6, 0.9, 11), lf, rot=("y", -22.5))                   # 낙엽 흔적
    return _build(k)

def desert_rose(seed=0):
    """사막장미: 결정 꽃판이 교차한 로제트 (사막, 희귀) — 석고 결정."""
    k = Kit(seed); p = Mat("d8a890", gloss=True); q = Mat("c08a72", gloss=True)
    k.box((3.5, 0, 6), (12.5, 3.5, 10), p, rot=("y", 22.5))
    k.box((3.5, 0.5, 6), (12.5, 4, 10), q, rot=("y", -45))
    k.box((5, 1, 5.5), (11, 5.5, 9.5), p, rot=("y", -22.5))
    k.box((6, 2, 6.5), (10, 7, 9.5), q, rot=("y", 45))                          # 중심 꽃판(높음)
    return _build(k)

def frost_lotus(seed=0):
    """서리연꽃: 눈밭에 피는 얼음 연꽃 (정상, 희귀) — 벌어진 잎 + 빙심."""
    k = Kit(seed); outer = Mat("cfe4ec", var=0.5); inner = Mat("eef6fa", var=0.4); core = Mat("7fc4e8", gloss=True)
    for f, t, rr in [((2.5, 0, 6), (7, 5, 10), ("z", 22.5)), ((9, 0, 6), (13.5, 5, 10), ("z", -22.5)),
                     ((6, 0, 2.5), (10, 5, 7), ("x", -22.5)), ((6, 0, 9), (10, 5, 13.5), ("x", 22.5))]:
        k.box(f, t, outer, rot=rr)                                             # 바깥 잎(벌어짐)
    k.box((5.5, 1, 5.5), (10.5, 5.5, 10.5), inner)                             # 안잎
    k.box((6.8, 3, 6.8), (9.2, 7, 9.2), core)                                  # 얼음 심
    return _build(k)

REGISTRY.update({
    "mush_blue":     (squat_fairy, {"base": "3a7ca5"}),
    "mush_orange":   (slim_fairy,  {"base": "d97a2b"}),
    "mush_poison":   (poison_mush, {}),
    "mush_glow":     (glow_trio,   {}),
    "fern_green":    (fern_arch,   {}),
    "flower_daisy":  (flower_flat, {}),
    "flower_ember":  (flower_cup,  {}),
    "flower_snow":   (flower_star, {}),
    "flower_bell":   (flower_bell, {}),
    "truffle":       (truffle,     {}),
    "desert_rose":   (desert_rose, {}),
    "frost_lotus":   (frost_lotus, {}),
})

# ═══════ 색칠놀이 린트 해소 — 도토리/서리열매/수정 2종 실루엣 분화 ═══════

def acorn_real(seed=0):
    """도토리: 진짜 도토리 2알(모자 쓴 알맹이, 제각각 기움) + 잔가지 (깊은 숲)."""
    k = Kit(seed)
    nut = Mat("b98a4e", var=0.7); cap = Mat("6e4f2e", var=0.8); twig = Mat("5c452c", var=0.7, grain="v")
    k.box((4.5, 0, 6), (8.5, 4.5, 10), nut, rot=("z", 22.5))                   # 알맹이1(기움)
    k.box((4.2, 4, 5.7), (8.8, 6, 10.3), cap, rot=("z", 22.5), cull=("down",)) # 모자1(챙 넓게)
    k.box((6, 6, 7.4), (7, 7.2, 8.4), twig, rot=("z", 22.5))                   # 꼭지1
    k.box((9, 0, 7), (12.5, 3.8, 10.5), nut, rot=("z", -22.5))                 # 알맹이2(반대 기움, 작음)
    k.box((8.7, 3.4, 6.7), (12.8, 5.2, 10.8), cap, rot=("z", -22.5), cull=("down",))
    k.box((3.5, 0, 9.5), (10, 1, 10.5), twig, rot=("y", -22.5))                # 떨어진 잔가지
    return _build(k)

def frost_mound(seed=0):
    """서리열매: 서리 낀 낮은 둔덕 덤불 + 박힌 얼음 베리 + 고드름 (정상)."""
    k = Kit(seed)
    bush = Mat("9fb8ac", var=0.8); frost = Mat("dceef2", var=0.5); br = Mat("6fb8d8", gloss=True)
    k.rounded_box((3, 0, 4), (13, 4.5, 12), bush)                              # 둔덕
    k.box((4, 3.8, 5), (12, 5, 11), frost, cull=("down",), rot=("y", 22.5))    # 서리막
    for f, t in [((4.5, 3.5, 5.5), (6.8, 5.8, 7.8)), ((8.5, 4, 7.5), (10.8, 6.3, 9.8)), ((6.5, 3.2, 9), (8.5, 5.2, 11))]:
        k.box(f, t, br)                                                        # 박힌 베리 3알
    k.box((11.5, 0, 6.5), (12.5, 3.5, 7.5), Mat("cfe4ec", gloss=True), rot=("z", -22.5))   # 얼음 스파이크
    return _build(k)

def blood_spikes(seed=0):
    """핏빛수정초: 풀처럼 돋아난 낮은 삐죽 군집 (붉은사막, 희귀)."""
    k = Kit(seed); c = Mat("b03030", gloss=True); d = Mat("7e1f1f", gloss=True)
    for f, t, rr, m in [((3.5, 0, 6), (6, 5, 8.5), ("z", 22.5), c), ((6.5, 0, 7.5), (9, 7.5, 10), ("y", 45), c),
                        ((9.5, 0, 5.5), (12, 4, 8), ("z", -22.5), d), ((5.5, 0, 4.5), (7.5, 3, 6.5), ("x", -22.5), d),
                        ((8.5, 0, 9.5), (10.5, 2.6, 11.5), ("x", 22.5), c)]:
        k.box(f, t, m, rot=rr)                                                 # 제각각 기운 삐죽 5개
    return _build(k)

def ame_spire(seed=0):
    """자수정새싹: 큰 첨탑 하나 + 곁싹 둘 (동굴, 희귀) — 수직 위엄."""
    k = Kit(seed); c = Mat("9a6fd8", gloss=True); d = Mat("6e4aa8", gloss=True)
    k.box((6.5, 0, 6.5), (9.5, 9, 9.5), c, rot=("y", 45))                      # 본탑(45°=다이아 단면)
    k.box((7.2, 9, 7.2), (8.8, 13.5, 8.8), c, rot=("y", 45), cull=("down",))   # 첨두
    k.box((4.5, 0, 8.5), (6.3, 3.5, 10.3), d, rot=("y", 22.5))                 # 곁싹1
    k.box((9.7, 0, 5.7), (11.2, 2.8, 7.2), d, rot=("y", -22.5))                # 곁싹2
    return _build(k)

REGISTRY.update({
    "acorn_cluster": (acorn_real, {}),
    "berry_frost":   (frost_mound, {}),
    "crystal_blood": (blood_spikes, {}),
    "crystal_ame":   (ame_spire, {}),
})
