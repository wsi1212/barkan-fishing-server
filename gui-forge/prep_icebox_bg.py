#!/usr/bin/env python3
"""아이스박스 배경 손질 — 납품본(bg_raw.png) → bg_source.png.

납품본에 **제목 명판이 없다**(발주엔 넣으라고 했는데 고드름 장식만 왔다). 그런데 우리는
티어 이름을 제목으로 찍기로 했으므로(IceboxGui.titleFor) 글자가 고드름 위에 떨어져 안 읽힌다.

바닐라는 상자 제목을 **GUI y 6**(art y 24~56)에 그리고 그 세로 위치는 바꿀 수 없다 —
그 줄이 하필 고드름 자리다. 세로를 못 옮기니 **가로로 좁힌다**: 제목을 티어 이름만
남겨 가운데로 모으고(가장 긴 「다이아몬드 아이스박스」가 art 164~540), 딱 그만큼만
**성에 낀 유리판**을 깐다. 판을 창 전체로 늘리면 고드름 장식이 통째로 덮인다.

또 하나: 아이스박스 상점 버튼이 갈 자리가 없다. **오른쪽 아래(53)는 45번째 보관칸**이라
쓸 수 없다(9티어가 실제로 45칸을 다 쓴다). 그래서 0행 오른쪽 끝(슬롯 8)에 홈을 판다 —
0행은 장식이라 비어 있고, 가운데(4)는 물고기 그림이라 남겨 둔다.
홈은 **이 그림의 보관칸 소켓을 그대로 떠다 쓴다** — 같은 그림이라 광원·팔레트가 정확히 맞는다.

사용: python3 prep_icebox_bg.py
"""
import os

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "icebox")

S = 4
BAR = (146, 18, 558, 62)         # art px — 가장 긴 티어명(164~540) + 좌우 여백 18
FILL = (14, 32, 52, 168)         # 성에 낀 유리: 어둡게 깔되 뒤가 비치게
RIM = (150, 210, 245, 210)
SHOP_SLOT = 8            # 0행 오른쪽 끝 — 상점 버튼 홈
SOCKET_FROM = 13         # 떠올 소켓 (1행 col4, 깨끗한 보관칸)


def main():
    raw = os.path.join(SRC, "bg_raw.png")
    im = Image.open(raw).convert("RGBA").resize((704, 888), Image.Resampling.LANCZOS)

    # 띠 뒤쪽을 살짝 흐려 글자 대비를 올린다(고드름 끝이 글자에 찌르는 걸 눌러 준다).
    x0, y0, x1, y1 = BAR
    blur = im.crop(BAR).filter(ImageFilter.GaussianBlur(2.2))
    im.paste(blur, (x0, y0))

    plate = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(plate)
    d.rounded_rectangle(BAR, radius=14, fill=FILL, outline=RIM, width=3)
    d.line((x0 + 14, y0 + 6, x1 - 14, y0 + 6), fill=(210, 240, 255, 90), width=2)  # 윗면 반사
    im.alpha_composite(plate)

    # 상점 버튼 홈 — 이 그림의 보관칸 소켓을 그대로 옮겨 심는다.
    def cell(slot):
        r, c = divmod(slot, 9)
        x0, y0 = (7 + 18 * c) * S, (17 + 18 * r) * S
        return (x0, y0, x0 + 18 * S, y0 + 18 * S)
    src_box, dst_box = cell(SOCKET_FROM), cell(SHOP_SLOT)
    im.paste(im.crop(src_box), (dst_box[0], dst_box[1]))

    im.putalpha(255)
    out = os.path.join(SRC, "bg_source.png")
    im.save(out)
    print(f"  제목 띠 art y {y0}~{y1} · 상점 홈 슬롯 {SHOP_SLOT} → {out}")


if __name__ == "__main__":
    main()
