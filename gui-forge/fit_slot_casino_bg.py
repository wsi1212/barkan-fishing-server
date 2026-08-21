#!/usr/bin/env python3
"""카지노 슬롯 GUI 배경 원화를 정확한 54칸 캔버스에 맞춘다.

원화는 생성기가 만든 도박장풍 아트데코 판이고, 최종 캔버스는 Minecraft 54칸
GUI의 실제 활성 영역인 176x222 GUI px (= 704x888 art px)이다.

상단 6행 컨테이너(176x138 GUI px)에는 원화의 금색 프레임과 에메랄드/루비
패널을 그대로 배치한다. 하단 플레이어 인벤토리 영역은 별도 저대비 패널로
채워서 슬롯 아이콘이 묻히지 않게 한다. 슬롯 그리드와 버튼 홈은 배경에 굽지
않으며, 최종 타일 빌더/게임 아이템이 담당한다.

사용:
    python3 fit_slot_casino_bg.py [원화 경로]
"""

import os
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "src", "slot_casino")
BET_DIR = os.path.join(HERE, "src", "slot_bet")
HUB_DIR = os.path.join(HERE, "src", "casino_hub")

W, H = 704, 888
CONTAINER_H = 552  # 138 GUI px, 6 rows

DEFAULT_INPUT = os.path.join(OUT_DIR, "bg_raw.png")


def make_background(raw: Image.Image, height: int, container_h: int) -> Image.Image:
    """원화를 주어진 행수의 704px 불투명 배경판으로 변환한다."""
    raw = raw.convert("RGB")

    # 54칸 판은 원화의 가로 비율과 거의 같으므로 프레임을 자르지 않고
    # 상단 판에 정확히 맞춘다. 4행 베팅판은 같은 원화의 위쪽 4행만 사용해
    # 인벤토리 영역에 하단 보석 장식이 내려오지 않도록 한다.
    full_top = raw.resize((W, CONTAINER_H), Image.Resampling.LANCZOS)
    top = full_top.crop((0, 0, W, container_h))

    # 게임 슬롯과 결과 아이콘이 올라오는 중앙 판은 프레임보다 한 톤 어둡게
    # 눌러서 금색 장식과 아이콘의 대비를 확보한다. 장식 프레임은 유지한다.
    panel_bottom = max(78, container_h - 32)
    panel = top.crop((52, 78, W - 52, panel_bottom))
    panel = ImageEnhance.Brightness(panel).enhance(0.72)
    panel = ImageEnhance.Contrast(panel).enhance(0.92)
    panel = panel.filter(ImageFilter.GaussianBlur(0.15))
    top.paste(panel, (52, 78))

    # 슬롯 칸/아이콘의 안전 외곽은 4x 기준 x=16..688, y=52..516이다.
    # 원화의 좌우 루비와 내부 금선이 이 범위까지 들어오면 맨 바깥 릴이
    # 장식 위에 올라가 크기가 어긋난 것처럼 보인다. 중앙의 아트데코 패턴만
    # 저대비로 재사용해 안전 영역을 다시 깔고, 화려한 장식은 안전 영역 밖에
    # 남긴다. (4행 베팅판은 실제 컨테이너 높이에 맞춰 아래를 줄인다.)
    safe_x0, safe_x1 = 16, W - 16
    safe_y0, safe_y1 = 52, min(container_h - 32, 516)
    if safe_y1 > safe_y0:
        # 4행 베팅판의 top은 y=408에서 잘렸으므로, 패턴 원본은 전체 6행 판에서
        # 뽑아야 crop 바깥이 검은색으로 패딩되지 않는다.
        pattern = full_top.crop((108, 130, 596, 474)).resize(
            (safe_x1 - safe_x0, safe_y1 - safe_y0), Image.Resampling.LANCZOS
        )
        pattern = ImageEnhance.Brightness(pattern).enhance(0.78)
        pattern = ImageEnhance.Contrast(pattern).enhance(0.90)
        top.paste(pattern, (safe_x0, safe_y0))

    out = Image.new("RGB", (W, height), (8, 18, 18))
    out.paste(top, (0, 0))

    # 플레이어 인벤토리는 같은 카지노 팔레트를 공유하되, 상단의 보석 장식이
    # 내려오지 않도록 평평한 저대비 패널로 분리한다.
    px = out.load()
    for y in range(container_h, height):
        t = (y - container_h) / max(1, height - container_h - 1)
        r = int(10 + 3 * (1 - t))
        g = int(24 + 6 * (1 - t))
        b = int(25 + 5 * (1 - t))
        for x in range(W):
            # 중앙은 더 평평하게, 가장자리만 아주 약한 에메랄드 광택.
            edge = min(x, W - 1 - x) / (W / 2)
            glow = max(0.0, 1.0 - edge) * 2.0
            px[x, y] = (min(255, int(r + glow)), min(255, int(g + glow)), min(255, int(b + glow)))

    draw = ImageDraw.Draw(out)
    # 당첨 기준선은 게임판에만 아주 얇게 표시한다. 예전 ORANGE_STAINED_GLASS_PANE
    # 아이템처럼 16px 사각형을 크게 채우지 않고, 실제 슬롯 위치의 바깥 림에만
    # 어두운 앰버 선을 구워서 '가운데 줄이 기준'이라는 정보만 남긴다.
    if container_h == CONTAINER_H:
        # 당첨 라인은 슬롯 18/19/21/23/25/26 = 세 번째 컨테이너 행
        # (GUI top 53, 셀 중심 62)이다. 첫 번째 릴 노출 행(35)의 중심 44가 아니다.
        payline_y = (17 + 2 * 18 + 9) * 4
        for col in (0, 1, 3, 5, 7, 8):
            x0 = (7 + 18 * col + 1) * 4
            x1 = (7 + 18 * col + 17) * 4 - 1
            draw.line((x0, payline_y + 3, x1, payline_y + 3), fill=(45, 30, 17), width=3)
            draw.line((x0, payline_y, x1, payline_y), fill=(126, 67, 18), width=3)

    # 영역 경계는 1 GUI px = 4 art px. 인벤토리 칸 자체는 그리지 않는다.
    draw.line((0, container_h, W - 1, container_h), fill=(55, 92, 72), width=2)
    draw.line((0, container_h + 3, W - 1, container_h + 3), fill=(18, 42, 34), width=2)

    # 하단 가장자리의 아주 얇은 아트데코 선만 넣는다. 아이콘/슬롯과 충돌하지
    # 않으며, 전체가 generic chest에서 분리된 카지노 화면이라는 인상을 준다.
    for inset, color, width in ((8, (40, 67, 50), 2), (12, (18, 39, 32), 2)):
        draw.rectangle((inset, container_h + 12, W - 1 - inset, height - 10), outline=color, width=width)

    result = out.convert("RGBA")
    alpha = result.getchannel("A")
    assert alpha.getextrema() == (255, 255), "배경판은 완전 불투명해야 한다"
    return result


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    if not os.path.isfile(source):
        raise SystemExit(f"원화 파일이 없다: {source}")
    raw = Image.open(source)
    screens = (
        (OUT_DIR, 888, 552, "54칸 게임"),
        (BET_DIR, 744, 408, "36칸 베팅"),
        # 3행 상자에서는 플레이어 인벤토리 첫 줄이 GUI y=84(art y=336)에서
        # 시작한다. 예전 432px은 슬롯 행 하나 안쪽으로 경계선이 내려가던 값이다.
        (HUB_DIR, 672, 336, "27칸 딜러 허브"),
    )
    for out_dir, height, container_h, label in screens:
        os.makedirs(out_dir, exist_ok=True)
        result = make_background(raw, height, container_h)
        result.save(os.path.join(out_dir, "bg_source.png"))
        result.save(os.path.join(out_dir, "_preview_full.png"))
        print(f"카지노 슬롯 {label} 배경: {raw.size} → {W}x{height}")
        print(f"  {os.path.join(out_dir, 'bg_source.png')}")


if __name__ == "__main__":
    main()
