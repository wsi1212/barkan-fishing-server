#!/usr/bin/env python3
"""BlockShip 낚시 카탈로그 아이콘 일괄 생성기.

권위 데이터:
  - plugins/BlockShip/parts.json: 낚싯대/릴/줄/바늘/미끼/찌/작살
  - BlockShip Java TrapSpecs.java: 지역 통발 12종 × 4변종

권위 카탈로그의 모든 아이템을 공통 팔레트/광원/픽셀 문법으로 렌더링하고, 리소스팩의
textures + models + items를 함께 생성한다. Java의 ItemIconModel과 같은 SHA-1
규칙을 사용하므로 별도 매핑 파일 없이 아이템 이름에서 모델 ID가 결정된다.

★★ 기본 모드는 catalog_* 텍스처를 **전부 덮어쓴다.** 기존 수작업/ImageGen 보정본을
보존하면서 누락만 채우려면 반드시 `--missing-only`를 사용한다. 두 가지를 기억할 것:
 ① 손으로 고친 아이콘이 있으면 그대로 날아간다(2026-08-05 실제 사고).
     모델 JSON만 바꿀 일이면 이 생성기 말고 텍스처를 안 건드리는 스크립트를 쓸 것.
 ② 기본 모드로 돌린 뒤에는 **반드시 `python3 add_outline.py` 를 다시 실행**할 것 —
검은 외곽선이 여기서 생성되지 않으므로 재생성하면 사라진다.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
SERVER = Path("/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a")
PARTS = SERVER / "plugins/BlockShip/parts.json"
TRAP_JAVA = Path("/Users/user/development/blockship-plugin/src/main/java/com/blockship/trap/TrapSpecs.java")
RP = Path(os.path.expanduser("~/development/barkan-resourcepack"))
OUT = HERE / "out/catalog"

TYPE_KEY = {
    "낚싯대": "rod", "릴": "reel", "줄": "line", "바늘": "hook",
    "미끼": "bait", "찌": "bobber", "작살": "harpoon", "통발": "trap",
}
GRADE = {
    "E": ("8e969c", "56616a"), "D": ("67b06b", "315c43"),
    "C": ("62a8dc", "285a8a"), "B": ("b477dc", "623d8b"),
    "A": ("f1c75b", "95621d"), "S": ("72e8df", "146f75"),
    "G": ("d06b92", "542339"), "M": ("e8e6ff", "6a5ea8"),
    "Q": ("f4a34a", "874327"), "L": ("e9dc65", "7d6b1a"),
}
SERIES = {
    "wood": ("9a6338", "5a3424", "d5a45a"),
    "bamboo": ("b7a34f", "68592c", "e8d77a"),
    "sand": ("c68b50", "75412c", "e9b75a"),
    "navy": ("395b86", "18283d", "67d8d7"),
    "royal": ("76548e", "272746", "e1a64d"),
    "copper": ("b56e4b", "4f3340", "efc26b"),
    "storm": ("344f74", "111d32", "51d7d8"),
    "green": ("5d9b62", "263e2c", "d2bd64"),
    "red": ("b6544d", "4b2730", "f0be58"),
}


def sha_key(*parts: str) -> str:
    return hashlib.sha1("\0".join(parts).encode("utf-8")).hexdigest()[:10]


def icon_id(kind: str, name: str, variant: str | None = None) -> str:
    if kind == "통발":
        key = sha_key("통발", name, variant or "표준")
    else:
        key = sha_key(kind, name)
    return f"catalog_{TYPE_KEY[kind]}_{key}"


def grade_for(raw: str) -> str:
    fields = raw.split("|", -1)
    return fields[1] if len(fields) > 1 and fields[1] else "E"


def origin_for(raw: str) -> str:
    fields = raw.split("|", -1)
    return fields[6] if len(fields) > 6 else "공용"


def palette_for(name: str, origin: str, grade: str):
    text = f"{name} {origin}"
    if any(x in text for x in ("사막", "모래", "오아시스", "전갈", "열풍", "사구")):
        series = SERIES["sand"]
    elif any(x in text for x in ("왕도", "왕실", "근위", "교역", "대상", "행상", "무역", "회계")):
        series = SERIES["royal"]
    elif any(x in text for x in ("바르칸", "천공", "심해", "대양", "해류", "급류", "파도")):
        series = SERIES["storm"]
    elif any(x in text for x in ("붉은", "핏빛", "섬광", "번개", "독")):
        series = SERIES["red"]
    elif any(x in text for x in ("대나무", "나무", "참나무", "버들", "야자", "수련", "늪", "수렁")):
        series = SERIES["green"] if "나무" not in text else SERIES["wood"]
    else:
        choices = ["navy", "copper", "bamboo", "wood"]
        series = SERIES[choices[int(sha_key(name)[0:4], 16) % len(choices)]]
    hi, dark, accent = series
    g_hi, g_dark = GRADE.get(grade, GRADE["E"])
    # 등급은 재질을 덮지 않고 링/테두리/보석에만 반영한다.
    return hi, dark, accent, g_hi, g_dark


def rgba(hexv: str, alpha=255):
    h = hexv.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha


class Painter:
    def __init__(self, size: int, name: str, grade: str, origin: str):
        self.n = size
        self.name = name
        self.grade = grade
        self.origin = origin
        self.rng = random.Random(int(sha_key(name, origin, grade), 16))
        self.hi, self.dark, self.accent, self.g_hi, self.g_dark = palette_for(name, origin, grade)
        self.im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def x(self, v): return round(v * self.n / 64)

    def pts(self, points): return [(self.x(x), self.x(y)) for x, y in points]

    def line(self, points, fill, width=1, joint="curve"):
        self.d.line(self.pts(points), fill=rgba(fill), width=max(1, self.x(width)), joint=joint)

    def polygon(self, points, fill, outline=None, width=1):
        p = self.pts(points)
        self.d.polygon(p, fill=rgba(fill))
        if outline:
            self.d.line(p + [p[0]], fill=rgba(outline), width=max(1, self.x(width)), joint="curve")

    def ellipse(self, box, fill, outline=None, width=1):
        b = tuple(self.x(v) for v in box)
        self.d.ellipse(b, fill=rgba(fill), outline=rgba(outline) if outline else None, width=max(1, self.x(width)))

    def rect(self, box, fill, outline=None, width=1):
        b = tuple(self.x(v) for v in box)
        self.d.rectangle(b, fill=rgba(fill), outline=rgba(outline) if outline else None, width=max(1, self.x(width)))

    def dot(self, x, y, color, radius=1):
        self.ellipse((x-radius, y-radius, x+radius, y+radius), color)

    def glow(self, x, y, color):
        ov = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        r = self.x(5 if self.grade in ("S", "G") else 3)
        od.ellipse((self.x(x)-r, self.x(y)-r, self.x(x)+r, self.x(y)+r), fill=rgba(color, 105))
        ov = ov.filter(ImageFilter.GaussianBlur(max(1, self.x(1))))
        self.im.alpha_composite(ov)
        self.d = ImageDraw.Draw(self.im)

    def finish(self):
        # 고해상도 원본도 외곽은 픽셀 계단을 보존한다.
        return self.im


def draw_rod(p: Painter):
    n = p.name
    bend = p.rng.choice([-4, -2, 0, 2, 4])
    pts = [(8, 55), (23, 43 + bend / 2), (39, 26 + bend), (56, 9)]
    p.line(pts, "1b1c29", 6)
    p.line(pts, p.dark, 4)
    p.line(pts, p.hi, 2)
    p.line([(9, 54), (20, 45)], p.g_dark, 6)
    for t in (0.18, 0.34):
        x = 8 + (56-8)*t; y = 55 + (9-55)*t
        p.ellipse((x-3, y-3, x+3, y+3), p.g_dark)
        p.ellipse((x-2, y-2, x+2, y+2), p.g_hi)
    # 릴은 작살/릴 부품과 구분되도록 낚싯대에 붙어 있는 형태로만 표현한다.
    p.ellipse((19, 39, 31, 51), "101a27", "161622", 1)
    p.ellipse((21, 40, 29, 48), p.g_dark, p.g_hi, 1)
    p.line([(28, 47), (34, 52)], p.g_hi, 2)
    p.dot(35, 53, p.accent, 2)
    if "대나무" in n:
        for x, y in [(18, 45), (28, 35), (39, 24)]: p.line([(x-2, y+2), (x+2, y-2)], p.g_hi, 1)
    if any(x in n for x in ("나뭇가지", "초보", "참나무")):
        p.line([(16, 44), (13, 38)], p.hi, 2); p.dot(12, 37, "6ca65b", 2)
    if "여명" in n or "불" in n:
        p.glow(55, 12, "e97942")
        p.dot(55, 12, "f0a34f", 2)
    if p.grade in ("A", "S", "G"):
        for x, y in [(27, 34), (35, 25), (44, 18)]: p.line([(x-1, y+1), (x+1, y-1)], p.g_hi, 2)
        p.dot(47, 17, p.accent, 2)
    p.line([(56, 9), (58, 18), (54, 27), (57, 35)], "d9e7df", 1)
    p.line([(57, 35), (55, 38), (53, 36)], "9aa7a9", 1)


def draw_reel(p: Painter):
    cx, cy = 31, 32
    p.ellipse((10, 11, 52, 53), "111827", "1a1c29", 2)
    p.ellipse((14, 14, 48, 49), p.dark, p.g_dark, 2)
    p.ellipse((20, 20, 43, 43), p.hi, p.g_hi, 2)
    p.ellipse((25, 25, 37, 37), p.dark, p.g_hi, 1)
    for i in range(6):
        a = i * math.pi / 3
        p.line([(31, 31), (31 + math.cos(a)*16, 32 + math.sin(a)*16)], p.g_dark, 1)
    p.line([(45, 38), (54, 48), (60, 48)], p.g_hi, 3)
    p.dot(60, 48, p.accent, 3)
    p.rect((25, 7, 38, 14), p.g_dark, "161622", 1)
    p.dot(31, 10, p.accent, 2)
    if "고속" in p.name or "전기" in p.name:
        p.line([(15, 21), (19, 18), (17, 25)], p.accent, 2)
    if p.grade in ("A", "S", "G"):
        p.glow(31, 31, p.accent)
        p.dot(31, 31, p.g_hi, 2)


def draw_line(p: Painter):
    cx, cy = 32, 32
    p.ellipse((11, 11, 53, 53), "151923", p.g_dark, 3)
    p.ellipse((17, 17, 47, 47), p.dark, p.hi, 4)
    p.ellipse((23, 23, 41, 41), "101722", p.g_dark, 2)
    for off in (-3, 0, 3):
        p.line([(15+off, 31), (20+off, 20), (33+off, 16), (45+off, 24)], p.accent, 1)
    p.line([(44, 44), (54, 54)], p.g_hi, 3)
    if "쌍줄" in p.name:
        p.line([(10, 48), (23, 58)], p.g_hi, 2)
        p.line([(15, 53), (27, 59)], p.accent, 2)
    if "모래" in p.name or "사막" in p.name: p.dot(49, 16, "e3ac5c", 2)


def draw_hook(p: Painter):
    x = 32 + p.rng.choice([-2, 0, 2])
    p.line([(x, 8), (x, 43), (x-2, 51), (x-11, 56), (x-19, 53), (x-20, 47)], "121822", 7)
    p.line([(x, 8), (x, 43), (x-2, 51), (x-11, 56), (x-19, 53), (x-20, 47)], p.dark, 4)
    p.line([(x-1, 10), (x-1, 40), (x-4, 49)], p.hi, 2)
    p.line([(x-20, 47), (x-16, 44)], p.g_hi, 2)
    p.ellipse((x-5, 5, x+5, 15), p.g_dark, "11151c", 2)
    if any(z in p.name for z in ("독", "전갈")):
        p.dot(x-13, 52, "9dce47", 3); p.glow(x-13, 52, "86b84a")
    if p.grade in ("A", "S", "G"):
        p.line([(x-5, 20), (x+2, 20)], p.g_hi, 2)


def draw_bait(p: Painter):
    n = p.name
    if "지렁이" in n:
        pts = [(9, 39), (18, 25), (28, 39), (39, 24), (53, 39)]
        p.line(pts, "361c39", 7); p.line(pts, p.hi, 4)
        for x in (18, 29, 40): p.line([(x, 29), (x+3, 34)], p.g_dark, 1)
    elif "새우" in n:
        p.line([(12, 38), (22, 27), (36, 26), (48, 37)], "5b222d", 8)
        p.line([(12, 38), (22, 27), (36, 26), (48, 37)], p.hi, 5)
        p.line([(22, 27), (17, 18), (28, 24), (35, 16)], p.accent, 2)
        p.dot(22, 27, p.g_hi, 2)
    elif "반딧불" in n or "빛나는" in n or "번개" in n:
        p.rect((15, 15, 49, 53), p.dark, p.g_dark, 2)
        p.rect((19, 18, 45, 49), p.hi, p.g_dark, 1)
        p.rect((20, 10, 44, 18), p.g_dark, "24191b", 2)
        p.glow(32, 34, p.accent); p.dot(32, 34, p.g_hi, 4)
    else:
        p.ellipse((11, 24, 53, 47), p.dark, "151821", 2)
        p.ellipse((17, 27, 48, 43), p.hi, p.g_hi, 1)
        p.polygon([(49, 34), (59, 25), (57, 38)], p.accent, "151821", 1)
        p.dot(22, 32, p.g_hi, 2)
        if "거대" in n: p.line([(14, 24), (50, 24)], p.g_hi, 2)
    if p.grade in ("A", "S", "G"): p.glow(32, 34, p.accent)


def draw_bobber(p: Painter):
    x = 32
    p.line([(x, 7), (x, 57)], "202533", 3)
    if "전자" in p.name or "수정" in p.name:
        p.rect((27, 17, 37, 39), p.dark, p.g_dark, 2)
        p.polygon([(32, 18), (38, 28), (32, 39), (26, 28)], p.accent, p.g_hi, 1)
        p.glow(32, 28, p.accent)
    else:
        p.ellipse((21, 25, 43, 46), p.hi, p.g_dark, 2)
        p.ellipse((25, 29, 39, 42), p.g_hi, p.hi, 1)
        p.rect((29, 10, 35, 28), p.g_dark, "161822", 1)
        p.rect((30, 11, 34, 22), p.accent)
    if "코르크" in p.name or "나무" in p.name: p.dot(27, 31, "e1b77b", 2)
    if p.grade in ("A", "S", "G"): p.dot(32, 10, p.g_hi, 2)


def draw_harpoon(p: Painter):
    # 긴 낚시용 작살: 창날은 짧고 자루가 전체 길이 대부분을 차지한다.
    pts = [(8, 55), (28, 35), (52, 11)]
    p.line(pts, "111723", 6); p.line(pts, p.dark, 4); p.line(pts, p.hi, 2)
    p.line([(8, 55), (19, 44)], p.g_dark, 8)
    for x, y in [(19, 44), (32, 30), (44, 18)]: p.line([(x-2, y+2), (x+2, y-2)], p.g_dark, 2)
    p.polygon([(48, 15), (57, 5), (61, 7), (55, 18), (51, 17)], p.dark, "0c1119", 2)
    p.polygon([(49, 15), (57, 7), (54, 17)], p.hi)
    p.polygon([(52, 14), (48, 20), (55, 17)], p.g_hi)
    p.rect((42, 17, 51, 24), p.g_dark, "121923", 1)
    p.dot(47, 20, p.accent, 2)
    p.line([(8, 55), (3, 58), (9, 61), (18, 57)], p.g_dark, 3)
    if any(z in p.name for z in ("전갈", "독")):
        p.dot(55, 17, "88c24b", 2); p.glow(55, 17, "88c24b")
    if "사막" in p.name or "사구" in p.name: p.line([(53, 9), (58, 5)], "e8bd5b", 2)
    if p.grade in ("A", "S", "G"):
        p.line([(28, 35), (30, 33)], p.g_hi, 2); p.glow(47, 20, p.accent)


def draw_trap(p: Painter):
    n = p.name
    # 지역 통발은 사각 cage, 변종은 장식과 강조색으로 구별한다.
    p.polygon([(13, 22), (45, 18), (55, 28), (52, 52), (18, 55), (9, 43)], p.dark, "101720", 3)
    p.polygon([(13, 22), (45, 18), (52, 27), (19, 32)], p.hi, p.g_dark, 2)
    p.line([(19, 32), (18, 54), (52, 51), (52, 27)], p.g_dark, 2)
    for x in (18, 26, 34, 42, 50): p.line([(x, 30), (x, 52)], p.hi, 2)
    for y in (36, 43, 50): p.line([(14, y), (52, y-3)], p.g_dark, 2)
    p.polygon([(18, 32), (26, 36), (26, 46), (19, 43)], p.dark, p.g_hi, 1)
    p.line([(20, 28), (12, 12), (18, 8), (28, 25)], p.g_dark, 4)
    if "튼튼" in n:
        p.line([(12, 23), (53, 48)], p.g_hi, 3)
        p.line([(53, 23), (12, 49)], p.g_hi, 3)
    if "속성" in n:
        p.polygon([(43, 7), (49, 16), (43, 16), (50, 27), (38, 15), (44, 15)], p.g_hi)
    if "행운" in n:
        p.dot(44, 23, p.g_hi, 3); p.glow(44, 23, p.accent)
    if any(z in n for z in ("모래", "야자", "버들")): p.dot(29, 40, p.accent, 2)
    if any(z in n for z in ("심해", "심연", "종유석", "원양")): p.glow(29, 40, p.accent)


DRAWERS = {
    "낚싯대": draw_rod, "릴": draw_reel, "줄": draw_line, "바늘": draw_hook,
    "미끼": draw_bait, "찌": draw_bobber, "작살": draw_harpoon, "통발": draw_trap,
}


def size_for(grade: str) -> int:
    # 저등급은 슬롯에서 충분히 읽히는 64px, 중간 등급은 128px,
    # 고등급/특수 변형은 256px, 최상위 등급은 512px 원본으로 보존한다.
    if grade in ("S", "G"):
        return 512
    if grade in ("A", "Q", "L"):
        return 256
    if grade in ("B", "M"):
        return 128
    return 64


def load_catalog():
    data = json.loads(PARTS.read_text(encoding="utf-8"))
    rows = []
    for kind, values in data["parts"].items():
        for name, raw in values.items():
            rows.append({"kind": kind, "name": name, "grade": grade_for(raw), "origin": origin_for(raw), "variant": None})
    java = TRAP_JAVA.read_text(encoding="utf-8")
    bases = re.findall(r'put\(new Spec\("([^"]+)",\s*"([^"]+)",\s*"([^"]+)"', java)
    for region, label, coded in bases:
        plain = re.sub(r"&[0-9a-fk-orA-FK-OR]", "", coded)
        for variant, prefix, grade in (("표준", "", "E"), ("튼튼", "튼튼한 ", "D"), ("속성", "속성 ", "Q"), ("행운", "행운의 ", "L")):
            rows.append({"kind": "통발", "name": prefix + plain, "grade": grade, "origin": label, "variant": variant, "region": region})
    return rows


def save_models(rows, missing_only=False):
    tex = RP / "assets/minecraft/textures/item/barkan_icon"
    models = RP / "assets/barkan/models/barkan_icon"
    items = RP / "assets/barkan/items/barkan_icon"
    for d in (tex, models, items): d.mkdir(parents=True, exist_ok=True)
    meta = []
    paths = []
    for row in rows:
        iid = icon_id(row["kind"], row["region"] if row["kind"] == "통발" else row["name"], row.get("variant"))
        target = tex / f"{iid}.png"
        model_path = models / f"{iid}.json"
        item_path = items / f"{iid}.json"
        # 신규 부품만 채울 때는 기존 아이콘을 절대 덮어쓰지 않는다.
        # 기존 수작업 보정본/이미지 생성 후처리본을 보존하기 위한 안전 모드다.
        if missing_only and target.exists() and model_path.exists() and item_path.exists():
            continue
        p = Painter(size_for(row["grade"]), row["name"], row["grade"], row["origin"])
        DRAWERS[row["kind"]](p)
        image = p.finish()
        image.save(target)
        # ★낚싯대는 부모가 item/generated(평면 아이콘용, 손모양 없음)라서 마크 기본
        #   낚싯대처럼 앞으로 들지 않고 평평하게 들렸다. 진짜 낚싯대는 item/handheld_rod
        #   (→item/handheld) 를 부모로 써서 3인칭/1인칭 들기 각도가 정의돼 있다
        #   (1.21.11 클라이언트 jar에서 실측: thirdperson rotation.y=90 등).
        #   텍스처만 우리 걸로 바꾸고 부모는 유지해 각도를 물려받는다.
        parent = "minecraft:item/handheld_rod" if row["kind"] == "낚싯대" else "minecraft:item/generated"
        model = {"parent": parent, "textures": {"layer0": f"minecraft:item/barkan_icon/{iid}"}}
        model_path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
        definition = {"model": {"type": "minecraft:model", "model": f"barkan:barkan_icon/{iid}"}}
        item_path.write_text(json.dumps(definition, ensure_ascii=False), encoding="utf-8")
        row = dict(row); row.update({"id": iid, "resolution": image.width, "path": str(target)})
        meta.append(row); paths.append(target)
    return meta, paths


def make_review(meta, paths):
    review = OUT
    review.mkdir(parents=True, exist_ok=True)
    # 카테고리별 contact sheet: 슬롯 목업과 구분되는 원본 품질 검수용이다.
    for kind in DRAWERS:
        group = [(m, p) for m, p in zip(meta, paths) if m["kind"] == kind]
        cols = 8; cell = 128; rows = math.ceil(len(group) / cols)
        sheet = Image.new("RGBA", (cols*cell, rows*cell), (196,196,196,255))
        sd = ImageDraw.Draw(sheet)
        for i, (m, path) in enumerate(group):
            im = Image.open(path).convert("RGBA")
            im.thumbnail((96, 96), Image.Resampling.NEAREST)
            x = (i % cols)*cell + (cell-im.width)//2; y = (i//cols)*cell + 4
            sheet.alpha_composite(im, (x,y))
            sd.text(((i%cols)*cell+4, (i//cols)*cell+104), f'{m["grade"]} · {m["resolution"]}px', fill=(20,20,20,255))
        sheet.convert("RGB").save(review / f"{TYPE_KEY[kind]}_quality.png")
    # 전체 원본 품질 미리보기. 16px 슬롯 목업(catalog_slots.png)과 별개다.
    cols = 16; cell = 128; rows = math.ceil(len(paths) / cols)
    quality = Image.new("RGBA", (cols*cell, rows*cell), (196,196,196,255))
    qd = ImageDraw.Draw(quality)
    for i, (m, path) in enumerate(zip(meta, paths)):
        im = Image.open(path).convert("RGBA")
        im.thumbnail((96, 96), Image.Resampling.NEAREST)
        x = (i % cols)*cell + (cell-im.width)//2; y = (i//cols)*cell + 4
        quality.alpha_composite(im, (x,y))
        qd.text(((i%cols)*cell+4, (i//cols)*cell+104), f'{m["grade"]} {m["resolution"]}', fill=(20,20,20,255))
    quality.convert("RGB").save(review / "catalog_quality.png")
    # 실제 슬롯 목업: 18px 슬롯, 8배 확대해서 눈으로 검수한다.
    cols = 16; slot = 18; scale = 8
    slots = Image.new("RGBA", (cols*slot*scale, math.ceil(len(paths)/cols)*slot*scale), (198,198,198,255))
    for i, path in enumerate(paths):
        im = Image.open(path).convert("RGBA").resize((16,16), Image.Resampling.LANCZOS)
        cell = Image.new("RGBA", (slot,slot), (139,139,139,255)); cell.alpha_composite(im, (1,1))
        slots.alpha_composite(cell.resize((slot*scale,slot*scale), Image.Resampling.NEAREST), ((i%cols)*slot*scale, (i//cols)*slot*scale))
    slots.convert("RGB").save(review / "catalog_slots.png")
    (review / "catalog_manifest.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def validate(meta, paths):
    ids = [m["id"] for m in meta]
    # ★254 하드코딩이 실사고 원인 — parts.json/TrapSpecs.java에 새 아이템이 추가되면
    #   즉시 스테일해진다. 개수 자체를 검증할 근거가 없으니 ID 무결성만 확인한다.
    assert len(meta) == len(ids), "meta/ids 개수 불일치(내부 버그)"
    assert len(ids) == len(set(ids)), "아이콘 ID 충돌"
    for m, path in zip(meta, paths):
        im = Image.open(path).convert("RGBA")
        assert im.getpixel((0,0))[3] == 0, f"투명 모서리 실패: {path}"
        assert path.stat().st_size > 100, f"빈 PNG: {path}"
    print(f"검증 통과: {len(meta)}개 / 고유 ID {len(set(ids))}개")


def existing_catalog():
    """현재 RP에 설치된 전체 카탈로그를 읽어 리뷰 시트만 다시 만든다."""
    meta, paths = [], []
    tex = RP / "assets/minecraft/textures/item/barkan_icon"
    for row in load_catalog():
        iid = icon_id(row["kind"], row["region"] if row["kind"] == "통발" else row["name"], row.get("variant"))
        path = tex / f"{iid}.png"
        if not path.exists():
            raise SystemExit(f"리뷰 대상 텍스처가 없습니다: {path}")
        current = dict(row)
        current.update({"id": iid, "resolution": Image.open(path).width, "path": str(path)})
        meta.append(current)
        paths.append(path)
    return meta, paths


def main():
    import argparse
    ap = argparse.ArgumentParser(description="장비/부품 카탈로그 아이콘 생성")
    ap.add_argument("--missing-only", action="store_true",
                    help="textures/models/items 3종이 모두 있는 기존 아이콘은 건너뜀")
    ap.add_argument("--review-all", action="store_true",
                    help="기존 RP 파일은 건드리지 않고 전체 카탈로그 리뷰 시트만 재생성")
    args = ap.parse_args()
    if args.review_all:
        meta, paths = existing_catalog()
    else:
        rows = load_catalog()
        meta, paths = save_models(rows, missing_only=args.missing_only)
    validate(meta, paths)
    make_review(meta, paths)
    print("리소스팩 생성:", RP)
    print("리뷰:", OUT / "catalog_slots.png")
    print("카탈로그:", OUT / "catalog_manifest.json")
    by_kind = {}
    for m in meta: by_kind[m["kind"]] = by_kind.get(m["kind"], 0) + 1
    print("분류:", by_kind)


if __name__ == "__main__":
    main()
