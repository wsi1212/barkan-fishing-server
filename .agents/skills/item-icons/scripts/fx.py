#!/usr/bin/env python3
"""아이콘 이펙트(오오라) 시스템 — 정적 글로우 + 바닐라 .mcmeta 프레임 애니메이션.

원칙:
  * 오오라는 실루엣 '바깥'에만 찍는다(본체를 절대 덮지 않음 — 실루엣이 먼저).
  * 오오라 픽셀 예산 ≤ 본체 불투명 픽셀의 ~25%. 넘으면 아이템이 아니라 이펙트로 보임.
  * 애니메이션 = 세로 스트립 PNG + <이름>.png.mcmeta {"animation":{"frametime":N}}.
    인벤토리/핫바/손 모두에서 실제로 일렁인다(바닐라 기능, 모드 불필요).
  * 앵커(불꽃 뿌리)는 프레임 간 고정, 높이/드리프트만 흔들어야 '한 불꽃이 일렁이는' 느낌이
    난다. 프레임마다 앵커를 새로 뽑으면 노이즈로 보임.
"""
import json, random
from PIL import Image
from iconlib import hx, put, edge_cells


def fire_aura(base, ramp5, seed=1, frames=4, density=5, y_max=11):
    """불꽃 오오라 프레임 생성. base(합성 전 스프라이트)는 건드리지 않고 프레임 사본을 반환.

    ramp5: palette.ramp(불 기본색) — 뿌리=r2(주황), 중간=r3, 혀끝=r4(밝은 노랑).
    density: 불꽃 혀 개수. y_max: 이보다 아래(손잡이 쪽)에는 불꽃을 안 붙임.
    """
    rng = random.Random(seed)
    cand = sorted({(x, y) for x, y in edge_cells(base) if y <= y_max})
    anchors = rng.sample(cand, min(density, len(cand))) if cand else []
    out = []
    for f in range(frames):
        im = base.copy()
        fr = random.Random(seed * 97 + f * 13)
        for ax, ay in anchors:
            h = fr.choice((1, 2, 2, 3))
            drift = fr.choice((-1, 0, 0, 1))
            for k in range(h):
                px_, py_ = ax + (drift if k >= 2 else 0), ay - 1 - k
                if 0 <= px_ < 16 and 0 <= py_ < 16 and base.getpixel((px_, py_))[3] == 0:
                    put(im, px_, py_, ramp5[min(2 + k, 4)])
        # 떠오르는 불티 1~2개 — 프레임마다 위치가 바뀌며 깜빡임
        for _ in range(fr.choice((1, 2))):
            if anchors:
                ax, ay = fr.choice(anchors)
                ex, ey = ax + fr.choice((-2, -1, 1, 2)), ay - fr.choice((2, 3, 4))
                if 0 <= ex < 16 and 0 <= ey < 16 and base.getpixel((ex, ey))[3] == 0:
                    put(im, ex, ey, ramp5[4])
        out.append(im)
    return out


def glow_halo(base, col, alpha=80, seed=1, sparkles=2, spark_col=None):
    """정적 글로우 — 실루엣 밖 1px 헤일로(반투명) + 반짝이 픽셀 약간.
    GUI에선 반투명이 잘 먹지만 남용 금지: lint가 반투명 픽셀 수를 감사한다."""
    im = base.copy()
    halo = hx(col, alpha)
    W, H = base.size
    for x, y in edge_cells(base):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and base.getpixel((nx, ny))[3] == 0 \
                    and im.getpixel((nx, ny))[3] == 0:
                im.putpixel((nx, ny), halo)
    rng = random.Random(seed)
    ec = edge_cells(base)
    for _ in range(sparkles):
        if not ec:
            break
        x, y = rng.choice(ec)
        sx, sy = x + rng.choice((-2, 2)), y + rng.choice((-2, -1))
        if 0 <= sx < W and 0 <= sy < H and base.getpixel((sx, sy))[3] == 0:
            put(im, sx, sy, spark_col or col)
    return im


def save_anim(frames, out_png, frametime=3):
    """세로 스트립 + .mcmeta 저장 — 리소스팩에 이 두 파일을 그대로 배치하면 애니메이션."""
    w, h = frames[0].size
    strip = Image.new("RGBA", (w, h * len(frames)), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        strip.paste(f, (0, i * h))
    strip.save(out_png)
    with open(out_png + ".mcmeta", "w") as fp:
        json.dump({"animation": {"frametime": frametime}}, fp)


def save_gif(frames, out_gif, scale=8, bg="8B8B8B", duration=140):
    """리뷰용 GIF(슬롯 회색 배경 + 니어리스트 업스케일). 게임 밖에서 애니를 눈으로 확인."""
    big = []
    for f in frames:
        b = Image.new("RGBA", f.size, hx(bg))
        b.alpha_composite(f)
        big.append(b.resize((f.size[0] * scale, f.size[1] * scale), Image.NEAREST).convert("P"))
    big[0].save(out_gif, save_all=True, append_images=big[1:], duration=duration, loop=0)
