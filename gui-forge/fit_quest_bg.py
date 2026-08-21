#!/usr/bin/env python3
"""퀘스트·대화 GUI 원화를 실제 컨테이너 행 수에 맞춰 자른다.

Minecraft 인벤토리 글리프는 제목 영역을 포함한 176x(114+18*rows) GUI px
캔버스다. 원화는 한 장만 관리하고, 2/3/4/6행 화면은 각각 플레이어 인벤토리
시작선에서 정확히 끊어 별도 배경으로 만든다.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageEnhance


HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 704, 888
SCALE = 4
INV_Y = {
    "questnpc": (2, 30 + 2 * 18),
    "questlist": (3, 30 + 3 * 18),
    "questjournal": (4, 30 + 4 * 18),
    "questpage": (6, 30 + 6 * 18),
}
DEFAULT_INPUT = os.path.join(HERE, "src", "questpage", "bg_raw.png")


def fit(raw: Image.Image, rows: int, inv_y_gui: int) -> Image.Image:
    """원화를 704px 폭으로 맞추고, 실제 인벤토리 시작선 아래를 평평하게 만든다."""
    full = raw.convert("RGB").resize((W, H), Image.Resampling.LANCZOS)

    # 원화의 질감은 유지하되 아이템·한글 로어가 우선되도록 전체 명도를 낮춘다.
    full = ImageEnhance.Brightness(full).enhance(0.68)
    full = ImageEnhance.Contrast(full).enhance(0.92)

    # 제목 명판의 그림자·음영은 ImageGen 원화에 이미 포함되어 있다.
    # 별도 암부 마스크를 덧씌우면 명판 아래에 둥근 네모 그림자가 중복되므로
    # 코드에서 명판을 다시 칠하지 않는다.

    final_h = (114 + rows * 18) * SCALE
    inv_y = inv_y_gui * SCALE
    top = full.crop((0, 0, W, inv_y))

    # 플레이어 인벤토리 영역은 ImageGen 원화의 하단 트레이를 그대로 재사용한다.
    # 원화 기준 640 art px부터가 구분대+목재 트레이다. 이 구간만 3줄+핫바 높이에
    # 맞추므로, 어떤 상단 행 수에서도 구분대가 슬롯에 잘리지 않는다.
    tray_source_y = 640
    separator_h = 10 * SCALE
    # ImageGen 원화의 구분대 픽셀을 슬롯 시작선 바로 위에 이식한다.
    # 선을 새로 그리지 않고 원화의 목재/놋쇠/청록 레일을 그대로 쓴다.
    separator = full.crop((0, tray_source_y, W, tray_source_y + separator_h))
    top.paste(separator, (0, max(0, inv_y - separator_h)))
    tray = full.crop((0, tray_source_y, W, H))
    panel = tray.resize((W, max(1, final_h - inv_y)), Image.Resampling.LANCZOS)
    panel = ImageEnhance.Brightness(panel).enhance(0.86)
    panel = ImageEnhance.Contrast(panel).enhance(0.95)

    out = Image.new("RGB", (W, final_h), (16, 22, 20))
    out.paste(top, (0, 0))
    out.paste(panel, (0, inv_y))

    result = out.convert("RGBA")
    assert result.getchannel("A").getextrema() == (255, 255)
    return result


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    if not os.path.isfile(source):
        raise SystemExit(f"퀘스트 원화가 없다: {source}")
    raw = Image.open(source)
    for name, (rows, inv_y_gui) in INV_Y.items():
        out_dir = os.path.join(HERE, "src", name)
        os.makedirs(out_dir, exist_ok=True)
        result = fit(raw, rows, inv_y_gui)
        result.save(os.path.join(out_dir, "bg_source.png"))
        result.save(os.path.join(out_dir, "_preview_full.png"))
        print(f"  {name}: {raw.size} -> {result.size}, inventory y={inv_y_gui} GUI px")


if __name__ == "__main__":
    main()
