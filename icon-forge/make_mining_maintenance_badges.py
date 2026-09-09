#!/usr/bin/env python3
"""정비 계열 채굴 스킬 배지 4종과 상태별 파생 아이콘을 만든다.

ImageGen 콘셉트(그라인드스톤/왁스 곡괭이/수리 망치/장인의 모루)를 32px 네이티브
픽셀로 다시 그린 뒤 64px로 nearest 확장한다. 그래야 기존 스킬 트리 배지의 64px
규격 및 16px GUI 가독성을 그대로 지킨다.

생성 대상(각각 기본·_locked·_avail·_maxed):
  skill_mining_maintenance
  skill_mining_protective_coating
  skill_mining_emergency_repair
  skill_mining_artisan_touch
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from make_skill_states import avail, locked, maxed


RP = Path("~/development/barkan-resourcepack").expanduser()
TEX = RP / "assets/minecraft/textures/item/barkan_icon"
MODELS = RP / "assets/barkan/models/barkan_icon"
ITEMS = RP / "assets/barkan/items/barkan_icon"
TEMPLATE = "skill_mining_vein_scan"
OUT = Path(__file__).resolve().parent / "out"

INK = "#10151d"
STEEL_DARK = "#27313b"
STEEL = "#81919d"
STEEL_LIGHT = "#d8e6ec"
WOOD_DARK = "#3f271a"
WOOD = "#8b5833"
WOOD_LIGHT = "#c28a50"
GOLD_DARK = "#9a560d"
GOLD = "#e99a1e"
GOLD_LIGHT = "#fff0a3"
CYAN_DARK = "#126e79"
CYAN = "#4bd8df"
CYAN_LIGHT = "#c8ffff"


def hexrgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def badge(rim: tuple[str, str, str], field: tuple[str, str, str]) -> Image.Image:
    """투명 바탕 위에 기존 배지처럼 한 단계씩 끊긴 원형 금속 테두리를 만든다."""
    im = Image.new("RGBA", (32, 32))
    px = im.load()
    for y in range(32):
        for x in range(32):
            dx, dy = x - 15.5, y - 15.5
            d2 = dx * dx + dy * dy
            if d2 > 14.1 * 14.1:
                continue
            # 바깥 검은 셀아웃 → 세 톤 링 → 어두운 중앙 필드.
            if d2 > 13.2 * 13.2:
                color = INK
            elif d2 > 11.15 * 11.15:
                color = rim[2] if x + y < 25 else rim[1]
                if x + y > 43:
                    color = rim[0]
            else:
                color = field[2] if x + y < 24 else field[1]
                if y > 23:
                    color = field[0]
            px[x, y] = (*hexrgb(color), 255)
    # 상단 볼트와 좌상단 림 하이라이트: 모든 정비 배지의 공통 문법.
    draw = ImageDraw.Draw(im)
    draw.rectangle((13, 1, 18, 2), fill=rim[2])
    draw.point((7, 5), fill=rim[2])
    draw.point((5, 7), fill=rim[1])
    draw.point((25, 24), fill=rim[0])
    return im


def outlined_polygon(draw: ImageDraw.ImageDraw, points, fill: str, width: int = 1) -> None:
    draw.polygon(points, fill=fill)
    draw.line([*points, points[0]], fill=INK, width=width, joint="curve")


def outlined_line(draw: ImageDraw.ImageDraw, points, fill: str, width: int) -> None:
    draw.line(points, fill=INK, width=width + 2, joint="curve")
    draw.line(points, fill=fill, width=width, joint="curve")


def sparkle(draw: ImageDraw.ImageDraw, x: int, y: int, color: str) -> None:
    draw.point((x, y - 1), fill=color)
    draw.point((x - 1, y), fill=color)
    draw.point((x, y), fill=GOLD_LIGHT if color == GOLD else color)
    draw.point((x + 1, y), fill=color)
    draw.point((x, y + 1), fill=color)


def maintenance() -> Image.Image:
    """정비 수련: 받침이 있는 그라인드스톤 + 대각 렌치."""
    im = badge(("#34414a", "#768792", "#c8d9df"), ("#14202a", "#1c2b35", "#293a45"))
    draw = ImageDraw.Draw(im)
    # 나무 받침은 금속 원반과 대비되어 '정비대'로 읽힌다.
    outlined_polygon(draw, [(8, 18), (19, 18), (22, 25), (6, 25)], WOOD)
    draw.line((9, 20, 19, 20), fill=WOOD_LIGHT, width=1)
    # 그라인드스톤 원반 — 중앙이 밝고 하단이 무거운 돌 재질.
    draw.ellipse((8, 6, 21, 19), fill=INK)
    draw.ellipse((9, 7, 20, 18), fill=STEEL)
    draw.arc((9, 7, 20, 18), 190, 355, fill=STEEL_DARK, width=2)
    draw.ellipse((13, 11, 17, 15), fill=STEEL_DARK)
    draw.point((11, 9), fill=STEEL_LIGHT)
    draw.point((12, 8), fill=STEEL_LIGHT)
    # 대각 렌치: 손잡이 하나와 벌어진 턱이 명확해야 16px에서도 정비로 보인다.
    outlined_line(draw, [(7, 26), (19, 14), (23, 10)], STEEL_LIGHT, 3)
    outlined_polygon(draw, [(21, 7), (26, 5), (28, 7), (25, 11), (22, 11), (24, 8)], STEEL_LIGHT)
    draw.line((9, 25, 19, 15), fill=STEEL, width=1)
    sparkle(draw, 6, 8, GOLD)
    return im


def protective_coating() -> Image.Image:
    """보호 코팅: 청강 곡괭이에 씌워진 황금 왁스와 벌집 두 칸."""
    im = badge(("#214667", "#4c91b7", "#a8dcf4"), ("#0d1d30", "#122a42", "#173653"))
    draw = ImageDraw.Draw(im)
    # 손잡이와 곡괭이 머리.
    outlined_line(draw, [(10, 25), (17, 18), (22, 10)], WOOD, 3)
    draw.line((11, 24, 21, 11), fill=WOOD_LIGHT, width=1)
    outlined_polygon(draw, [(14, 12), (18, 8), (24, 8), (27, 11), (23, 13), (18, 12), (15, 16), (12, 16)], STEEL)
    draw.line((16, 11, 23, 10), fill=STEEL_LIGHT, width=1)
    # 금빛 코팅이 '방패'처럼 머리 위에서 흘러내린다.
    outlined_polygon(draw, [(20, 7), (26, 8), (27, 12), (24, 15), (21, 13), (19, 10)], GOLD)
    draw.line((21, 8, 25, 9), fill=GOLD_LIGHT, width=1)
    draw.line((23, 10, 22, 13), fill=GOLD_DARK, width=1)
    # 벌집 셀 2개: 꿀 코팅이라는 단서를 과하지 않게 한쪽에만 둔다.
    for x, y in ((24, 17), (27, 19)):
        outlined_polygon(draw, [(x, y - 2), (x + 2, y - 1), (x + 2, y + 1),
                                 (x, y + 2), (x - 2, y + 1), (x - 2, y - 1)], GOLD)
        draw.point((x - 1, y - 1), fill=GOLD_LIGHT)
    sparkle(draw, 8, 9, GOLD)
    return im


def emergency_repair() -> Image.Image:
    """응급 보수: 갈라진 곡괭이 머리를 망치가 두드리는 순간."""
    im = badge(("#1a5462", "#4da4ac", "#b7f3ed"), ("#0b242a", "#12363d", "#164850"))
    draw = ImageDraw.Draw(im)
    # 아래의 갈라진 곡괭이 머리(수리 대상).
    outlined_polygon(draw, [(5, 20), (9, 16), (19, 17), (24, 21), (20, 23), (14, 21), (10, 24), (6, 23)], STEEL)
    draw.line((7, 21, 12, 20, 15, 22, 19, 20), fill=STEEL_LIGHT, width=1)
    draw.line((15, 18, 14, 20, 16, 21), fill=INK, width=1)
    # 망치: 대각 손잡이와 넓은 타격면 하나로 응급 보수의 행동을 읽힌다.
    outlined_line(draw, [(22, 8), (17, 15)], WOOD, 3)
    outlined_polygon(draw, [(18, 5), (25, 7), (24, 11), (17, 10), (15, 8)], STEEL_LIGHT)
    draw.line((18, 7, 23, 8), fill=STEEL, width=1)
    # 충격점은 작고 차가운 시안: 수리는 보상/골드가 아니라 기술 효과다.
    sparkle(draw, 15, 16, CYAN)
    draw.point((13, 15), fill=CYAN_LIGHT)
    draw.point((17, 14), fill=CYAN_LIGHT)
    draw.point((18, 17), fill=CYAN)
    return im


def artisan_touch() -> Image.Image:
    """장인의 손길: 모루 위에 닿는 금빛 손과 단 한 번의 불꽃."""
    im = badge(("#43365f", "#7b6aa7", "#d1c3f2"), ("#171126", "#251c3b", "#33284d"))
    draw = ImageDraw.Draw(im)
    # 모루는 하단에 넓고 무겁게 배치해 종결 특성의 안정감을 만든다.
    outlined_polygon(draw, [(7, 19), (24, 19), (27, 21), (23, 23), (20, 23),
                             (22, 27), (10, 27), (12, 23), (8, 23), (5, 21)], STEEL_DARK)
    draw.line((8, 20, 24, 20), fill=STEEL_LIGHT, width=1)
    draw.line((12, 24, 20, 24), fill=STEEL, width=1)
    # 위에서 내려오는 손은 손가락 3개만 남겨 작은 사이즈에서도 '손길'로 읽힌다.
    outlined_line(draw, [(22, 7), (19, 11), (17, 15)], GOLD, 3)
    for x, y in ((20, 8), (23, 9), (24, 11)):
        draw.line((x, y, x - 3, y + 4), fill=GOLD_LIGHT, width=1)
    draw.point((18, 14), fill=GOLD_LIGHT)
    # 단발성 구조는 작은 별 두 개로만 암시한다. 화염/항상 발동처럼 과장하지 않는다.
    sparkle(draw, 15, 17, GOLD)
    sparkle(draw, 8, 11, GOLD)
    return im


ICONS = {
    "skill_mining_maintenance": maintenance,
    "skill_mining_protective_coating": protective_coating,
    "skill_mining_emergency_repair": emergency_repair,
    "skill_mining_artisan_touch": artisan_touch,
}


def write_definition(icon_id: str) -> None:
    """검증된 기존 채굴 배지의 GUI 배율과 아이템 정의를 복사한다."""
    with (MODELS / f"{TEMPLATE}.json").open(encoding="utf-8") as handle:
        model = json.load(handle)
    model["textures"]["layer0"] = f"minecraft:item/barkan_icon/{icon_id}"
    with (MODELS / f"{icon_id}.json").open("w", encoding="utf-8") as handle:
        json.dump(model, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    with (ITEMS / f"{TEMPLATE}.json").open(encoding="utf-8") as handle:
        item = json.load(handle)
    item["model"]["model"] = f"barkan:barkan_icon/{icon_id}"
    with (ITEMS / f"{icon_id}.json").open("w", encoding="utf-8") as handle:
        json.dump(item, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main() -> None:
    missing = [p for p in (TEX, MODELS, ITEMS, MODELS / f"{TEMPLATE}.json", ITEMS / f"{TEMPLATE}.json") if not p.exists()]
    if missing:
        raise SystemExit("리소스팩 기준 파일을 찾을 수 없습니다:\n" + "\n".join(map(str, missing)))
    OUT.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (128, 128))
    for index, (icon_id, painter) in enumerate(ICONS.items()):
        base = painter().resize((64, 64), Image.Resampling.NEAREST)
        variants = {
            icon_id: base,
            icon_id + "_locked": locked(base),
            icon_id + "_avail": avail(base),
            icon_id + "_maxed": maxed(base),
        }
        for variant_id, image in variants.items():
            image.save(TEX / f"{variant_id}.png")
            write_definition(variant_id)
        sheet.alpha_composite(base, ((index % 2) * 64, (index // 2) * 64))
        print(f"✓ {icon_id}: 기본/locked/avail/maxed + 모델/아이템 정의")
    sheet.save(OUT / "mining_maintenance_badges.png")
    print(f"리뷰 시트: {OUT / 'mining_maintenance_badges.png'}")


if __name__ == "__main__":
    main()
