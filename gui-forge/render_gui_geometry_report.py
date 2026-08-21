#!/usr/bin/env python3
"""실제 GUI 크기표를 한 장으로 검증한다.

인벤토리 GUI는 Bukkit createInventory()의 행 수(2/3/4/6)를 그대로 사용하고,
BetterHud 대화 HUD는 110px 조각 4개를 표시 배율별로 붙인다. 이 렌더는 납품
리소스가 아니라 QA 전용이다.
"""

import os

from PIL import Image, ImageDraw, ImageFont


HERE = os.path.dirname(os.path.abspath(__file__))
SCALE = 4
GRID_X, GRID_Y, CELL = 7, 17, 18
INVENTORY = {
    "NPC 퀘스트 수락 · 18칸": ("questnpc", 2),
    "퀘스트 도감 메인 · 27칸": ("questlist", 3),
    "대화 기록/선택지 · 36칸": ("questjournal", 4),
    "주간/마을 목록 · 54칸": ("questpage", 6),
}
HUD = {
    "sm": (0.75, "dialogue-panel-1-sm.png", 0.7455),
    "md": (1.00, "dialogue-panel-1-md.png", 1.0),
    "lg": (1.20, "dialogue-panel-1-lg.png", 1.0),
    "xl": (1.40, "dialogue-panel-1-xl.png", 1.0),
}
HUD_ASSET_DIR = os.path.join(
    HERE, "..", "ops", "prod", "betterhud", "assets", "dialogue", "gen")


def font(size):
    for path in ("/System/Library/Fonts/Supplemental/Arial.ttf",
                 "/System/Library/Fonts/Supplemental/Helvetica.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_cell(draw, x, y, color, width=2):
    draw.rectangle((x * SCALE, y * SCALE,
                    (x + CELL) * SCALE - 1, (y + CELL) * SCALE - 1),
                   outline=color, width=width)


def inventory_debug(name, rows):
    path = os.path.join(HERE, "src", name, "_preview_full.png")
    im = Image.open(path).convert("RGBA")
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    inv_y = 30 + rows * CELL
    for row in range(rows):
        for col in range(9):
            draw_cell(draw, GRID_X + col * CELL, GRID_Y + row * CELL,
                      (255, 65, 65, 230), 2)
    for row in (inv_y, inv_y + CELL, inv_y + 2 * CELL, inv_y + 58):
        for col in range(9):
            draw_cell(draw, GRID_X + col * CELL, row,
                      (45, 230, 235, 235), 2)
    draw.line((0, inv_y * SCALE, im.width - 1, inv_y * SCALE),
              fill=(255, 220, 40, 255), width=3)
    draw.rectangle((GRID_X * SCALE, inv_y * SCALE,
                    (GRID_X + 9 * CELL) * SCALE - 1,
                    (inv_y + 3 * CELL) * SCALE - 1),
                   outline=(80, 255, 255, 255), width=3)
    draw.rectangle((GRID_X * SCALE, (inv_y + 58) * SCALE,
                    (GRID_X + 9 * CELL) * SCALE - 1,
                    (inv_y + 58 + CELL) * SCALE - 1),
                   outline=(80, 255, 255, 255), width=3)
    return Image.alpha_composite(im, overlay), inv_y


def hud_debug(sid, base_scale, filename, setting_scale):
    displayed_w = round(110 * base_scale)
    displayed_h = round(80 * base_scale)
    panels = []
    for i in range(1, 5):
        path = os.path.join(HUD_ASSET_DIR, f"dialogue-panel-{i}-{sid}.png")
        panel = Image.open(path).convert("RGBA")
        panel = panel.resize((displayed_w, displayed_h), Image.Resampling.LANCZOS)
        panels.append(panel)
    im = Image.new("RGBA", (displayed_w * 4, displayed_h + 58), (25, 25, 25, 255))
    for i, panel in enumerate(panels):
        im.alpha_composite(panel, (i * displayed_w, 0))
    draw = ImageDraw.Draw(im)
    # 110px 조각 경계(실제 표시 폭 기준)와 중앙 기준선.
    for i in range(5):
        x = i * displayed_w
        draw.line((x, 0, x, displayed_h), fill=(255, 70, 70, 255), width=2)
    draw.line((im.width // 2, 0, im.width // 2, displayed_h),
              fill=(255, 235, 55, 255), width=2)
    # 현재 layout의 대사 안전영역: 원본 x=122, y=10, 줄바꿈 기준 x=230.
    x0 = round(122 * base_scale)
    x1 = round((122 + 230) * base_scale)
    y0 = round(10 * base_scale)
    y1 = round((10 + 3 * 15 + 10) * base_scale)
    draw.rectangle((x0, y0, min(x1, im.width - 1), min(y1, displayed_h - 1)),
                   outline=(70, 220, 255, 255), width=2)
    draw.text((8, displayed_h + 8),
              f"HUD {sid}: {displayed_w * 4}×{displayed_h}  (4×{displayed_w}, scale={setting_scale})",
              fill=(245, 245, 245, 255), font=font(14))
    return im


def main():
    inv_imgs = []
    for label, (name, rows) in INVENTORY.items():
        im, inv_y = inventory_debug(name, rows)
        # 보고서에서는 폭을 통일해 비교하기 쉽게 두되, 원본은 각 폴더의 debug 파일로 보존한다.
        im.thumbnail((704, 300), Image.Resampling.LANCZOS)
        card = Image.new("RGBA", (740, im.height + 34), (20, 24, 25, 255))
        card.alpha_composite(im, (18, 30))
        ImageDraw.Draw(card).text((18, 8), f"{label} · 인벤 시작 GUI y={inv_y}",
                                   fill=(255, 235, 145, 255), font=font(16))
        inv_imgs.append(card)

    hud_imgs = []
    for sid, spec in HUD.items():
        hud_imgs.append(hud_debug(sid, *spec))

    width = 740 * 2
    height = max(sum(i.height for i in inv_imgs) + 20,
                 sum(i.height for i in hud_imgs) + 20)
    report = Image.new("RGBA", (width, height), (11, 14, 16, 255))
    draw = ImageDraw.Draw(report)
    draw.text((18, 12), "Inventory GUI geometry", fill=(255, 220, 120, 255), font=font(20))
    draw.text((758, 12), "BetterHud dialogue geometry", fill=(255, 220, 120, 255), font=font(20))
    y = 44
    for card in inv_imgs:
        report.alpha_composite(card, (0, y))
        y += card.height
    y = 44
    for hud in hud_imgs:
        report.alpha_composite(hud, (758 + (740 - hud.width) // 2, y))
        y += hud.height + 12

    out = os.path.join(HERE, "_gui_geometry_report.png")
    report.convert("RGB").save(out)
    print(out)
    for label, (name, rows) in INVENTORY.items():
        print(f"{label}: createInventory rows={rows}, size={rows * 9}, "
              f"canvas=704x{(114 + rows * 18) * 4}, inv-start={30 + rows * 18} GUI px")
    for sid, (scale, _, setting) in HUD.items():
        part_w, part_h = round(110 * scale), round(80 * scale)
        print(f"HUD {sid}: 4 x {part_w} x {part_h}, "
              f"display={part_w * 4}x{part_h}, setting.scale={setting}")


if __name__ == "__main__":
    main()
