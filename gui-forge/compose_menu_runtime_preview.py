#!/usr/bin/env python3
"""메뉴 배경 프리뷰에 Java 런타임 하단 아이콘 9개를 얹는다.

실제 메뉴는 하단 45~53번 슬롯에 아이템을 올리고, 타일 배경은 글리프로 그린다.
이 파일은 production 배경(bg_source.png)을 바꾸지 않고, 눈으로 확인할 프리뷰만 만든다.
"""
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
BASE = HERE / "src" / "menu" / "_preview_full.png"
RP_ICONS = Path.home() / "development" / "barkan-resourcepack" / \
    "assets" / "minecraft" / "textures" / "item" / "barkan_icon"
OUT = HERE / "src" / "menu" / "_preview_with_runtime_icons.png"

# MenuManager.java의 실제 45~53번 슬롯 순서.
RUNTIME_ICONS = [
    "ui_menu_shop",
    "ui_menu_icebox",
    "ui_menu_recommend",
    "ui_menu_hub",
    "ui_menu_trash",
    "ui_menu_afk",
    "ui_menu_mailbox",
    "ui_menu_emote",
    "ui_menu_settings",
]

SCALE = 4
GRID_X = 7
GRID_Y = 17
CELL = 18
COLS = 9
SLOT_ROW = 5


def main():
    base = Image.open(BASE).convert("RGBA")
    for col, icon_id in enumerate(RUNTIME_ICONS):
        src = RP_ICONS / f"{icon_id}.png"
        if not src.exists():
            raise FileNotFoundError(src)
        # Minecraft item 텍스처는 16px 슬롯에 그려진다. 프리뷰는 4배 확대이므로 64px.
        icon = Image.open(src).convert("RGBA").resize((16 * SCALE, 16 * SCALE), Image.Resampling.NEAREST)
        x0 = (GRID_X + CELL * col) * SCALE
        y0 = (GRID_Y + CELL * SLOT_ROW) * SCALE
        # 18px 슬롯 안의 16px 아이템처럼 가운데 정렬.
        base.alpha_composite(icon, (x0 + 1 * SCALE, y0 + 1 * SCALE))
    base.save(OUT)
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
