#!/usr/bin/env python3
"""하이브리드 애니메이션 — AI 도트 아이콘의 '불꽃 픽셀만' 골라 코드로 일렁이게.

AI는 정지 이미지라 애니가 안 됨. 그래서 로드 본체(나무/금속)는 고정하고, 밝은 warm
픽셀(불꽃)만 흐름파(sin)로 밝기 변조 + 팁 불티 = 진짜 불처럼 일렁임. 출력은 바닐라
.mcmeta 세로 스트립(인벤/핫바/손에서 재생) + 리뷰용 GIF.

사용: animate_fire.py <dot.png> [frames] [frametime]
"""
import sys, math, random
from PIL import Image


def is_fire(px):
    r, g, b, a = px
    if a == 0:
        return False
    mx = max(r, g, b)
    return mx >= 185 and r >= 150 and g >= 95 and b <= g + 12   # 밝은 주황~노랑(빨간밴드·갈색나무 제외)


def clamp(v):
    return max(0, min(255, int(v)))


def main():
    path = sys.argv[1]
    frames = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    frametime = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    base = Image.open(path).convert("RGBA")
    W, H = base.size
    p0 = base.load()
    fire = [(x, y) for y in range(H) for x in range(W) if is_fire(p0[x, y])]
    fireset = set(fire)
    tips = [(x, y) for (x, y) in fire if y == 0 or (x, y - 1) not in fireset]  # 불꽃 윗가장자리

    outs = []
    for f in range(frames):
        fr = base.copy()
        fp = fr.load()
        # 불꽃 밝기 흐름파(위로 타오름): 마루=밝고 골=어둡게
        for (x, y) in fire:
            w = math.sin(y * 0.55 - f * (2 * math.pi / frames) * 1.6 + x * 0.3)
            m = 0.68 + 0.5 * max(0.0, w) + 0.14
            r, g, b, a = p0[x, y]
            fp[x, y] = (clamp(r * m), clamp(g * m), clamp(b * m), 255)
        # 팁 불티: 윗가장자리 일부에서 1~2px 위로 튀는 불꽃
        rng = random.Random(f * 131 + 7)
        for (x, y) in tips:
            if rng.random() < 0.30:
                for k in (1, 2):
                    ny = y - k
                    if 0 <= ny < H and p0[x, ny][3] == 0 and (k == 1 or rng.random() < 0.4):
                        col = (255, 210, 110) if k == 1 else (255, 170, 70)
                        fp[x, ny] = (*col, 255)
        outs.append(fr)

    # 바닐라 애니 스트립 + .mcmeta
    strip = Image.new("RGBA", (W, H * frames), (0, 0, 0, 0))
    for i, im in enumerate(outs):
        strip.paste(im, (0, i * H))
    strip.save(path.replace(".png", "_anim.png"))
    open(path.replace(".png", "_anim.png.mcmeta"), "w").write(
        '{"animation":{"frametime":%d}}' % frametime)
    # 리뷰 GIF(회색 슬롯 배경, 6배)
    gif = []
    for im in outs:
        b = Image.new("RGBA", (W, H), (139, 139, 139, 255))
        b.alpha_composite(im)
        gif.append(b.resize((W * 6, H * 6), Image.NEAREST).convert("P"))
    gif[0].save(path.replace(".png", "_anim.gif"), save_all=True,
                append_images=gif[1:], duration=frametime * 50, loop=0)
    print(f"fire px={len(fire)}  →  {path.replace('.png','_anim.gif')}")


if __name__ == "__main__":
    main()
