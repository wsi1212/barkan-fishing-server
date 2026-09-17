#!/usr/bin/env python3
"""산벽 석청·백년 산삼 오프라인 3D 프리뷰.

실제 CraftEngine 모델/아틀라스를 render_textured로 그린 뒤, 절벽 흙포켓과
암벽 균열이라는 배치 의도가 한 장에서 읽히도록 작은 야간 산 비네트에 합성한다.
"""
from pathlib import Path
import json, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve().parent
CE = Path("/Users/user/Library/Application Support/feather/player-server/servers/"
          "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/CraftEngine/resources/"
          "barkan_furniture/resourcepack/assets/barkan")
sys.path.insert(0, str(HERE.parent / ".claude" / "skills" / "pixel-art" / "scripts"))
sys.path.insert(0, str(HERE))
from render_textured import render
from painters import REGISTRY

W, H = 1800, 1050

def font(size, bold=False):
    # Apple SD Gothic Neo는 굵기 요청에서도 한글 글리프를 보장한다. Arial Bold는
    # 한글이 없는 환경에서 네모(□)로 떨어지므로 제목 폴백으로 쓰지 않는다.
    candidates = ["/System/Library/Fonts/AppleSDGothicNeo.ttc",
                  "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()

def slope(draw, points, colors):
    draw.polygon(points, fill=colors[0])
    # 절벽의 층리선: 매끈한 일러스트보다 MC 암벽의 계단진 질감을 암시한다.
    x0 = min(x for x, _ in points); x1 = max(x for x, _ in points)
    for i, y in enumerate(range(430, H, 44)):
        off = (i % 3) * 23
        draw.line((x0 + off, y, x1 - 40, y - 80), fill=colors[1], width=8)
        draw.line((x0 + off + 14, y + 12, x1 - 26, y - 68), fill=colors[2], width=3)

def preview_painter(painter, iid):
    """프리뷰 전용 변주도 실제 modelkit 3D 모델·UV로 렌더한다(리소스팩엔 미등록)."""
    fn, kwargs = REGISTRY[painter]
    texture, elements = fn(**kwargs, seed=0)
    tex_path = HERE / "out" / f"preview_{iid}.png"
    model_path = HERE / "out" / f"preview_{iid}.json"
    texture.save(tex_path)
    with open(model_path, "w") as f:
        json.dump({"textures": {"0": "preview", "particle": "preview"}, "elements": elements}, f)
    return model_path, tex_path

def model_card(canvas, iid, model, texture, x, y, label, desc, tint):
    raw = HERE / "out" / f"preview_{iid}_raw.png"
    render(str(model), str(texture), str(raw), yaw=35, pitch=27, size=620)
    prop = Image.open(raw).convert("RGBA")
    bbox = prop.getbbox()
    prop = prop.crop(bbox) if bbox else prop
    prop.thumbnail((440, 440), Image.Resampling.LANCZOS)
    # 카드 → 그림자 → 실제 UV 렌더 순서. 이전에는 카드가 마지막에 그려져 모델을 가렸다.
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((x, y, x + 500, y + 570), radius=26, fill=(8, 15, 22, 205), outline=tint, width=3)
    # 얕은 땅그림자 뒤에 실제 UV 렌더를 얹는다.
    shadow = Image.new("RGBA", (460, 58), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse((40, 12, 420, 46), fill=(0, 0, 0, 125))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    canvas.alpha_composite(shadow, (x + 12, y + 415))
    canvas.alpha_composite(prop, (x + (480 - prop.width) // 2, y + 36))
    d.text((x + 34, y + 475), label, font=font(40, True), fill=tint)
    d.text((x + 36, y + 526), desc, font=font(23), fill=(220, 226, 220))

def main():
    out = HERE / "out" / "cliff_rares_preview.png"
    image = Image.new("RGBA", (W, H), (5, 10, 18, 255))
    d = ImageDraw.Draw(image)
    # 월광 하늘과 산 능선
    for yy in range(H):
        t = yy / H
        d.line((0, yy, W, yy), fill=(int(5 + 13*t), int(10 + 20*t), int(20 + 26*t), 255))
    d.ellipse((1420, 94, 1514, 188), fill=(226, 236, 221, 220))
    slope(d, [(0, 540), (440, 250), (780, 470), (1050, 300), (1320, 560), (1800, 350), (1800, H), (0, H)],
          ((41, 52, 66, 255), (69, 81, 91, 190), (25, 34, 45, 170)))
    title = font(62, True); sub = font(28)
    d.text((W // 2, 68), "절벽 희귀 채집품 · 3종", anchor="ma", font=title, fill=(243, 237, 218))
    d.text((W // 2, 145), "바닥 석청 · 천장 석청 · 백년 산삼  |  실제 3D 모델 프리뷰", anchor="ma", font=sub, fill=(175, 194, 187))
    ground = preview_painter("ground_honey", "ground_honey")
    hanging = preview_painter("hanging_honey", "hanging_honey")
    ginseng = (CE / "models/item/furniture/forage/z_cliffginseng.json",
               CE / "textures/furniture/forage/z_cliffginseng.png")
    model_card(image, "ground_honey", *ground, 65, 278, "바닥 석청", "바위 균열 안에서 굳어 솟은 석청", (244, 190, 79, 255))
    model_card(image, "hanging_honey", *hanging, 650, 278, "천장 석청", "절벽 처마 아래로 굳어 매달린 석청", (244, 190, 79, 255))
    model_card(image, "cliffginseng", *ginseng, 1235, 278, "백년 산삼", "절벽의 작은 흙포켓에서 자라는 산삼", (154, 210, 112, 255))
    image.convert("RGB").save(out)
    print(out)

if __name__ == "__main__":
    main()
