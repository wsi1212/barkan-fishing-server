#!/usr/bin/env python3
"""슬롯 GUI 릴 심볼 아이콘 = 배당표 아트(ChatGPT, slot_paytable.png)에서 6종 크롭 (2026-07-14 v3).

바닐라 Material 대신 배당표와 통일된 커스텀 아이콘. 출력:
RP assets/{minecraft/textures/item,barkan/models,barkan/items}/slot/sym_*.
CasinoManager.slotSymbolItem()이 barkan:slot/sym_<symbol>로 참조.

v3 재작성 배경(유저 신고: 위 가로선 잔존·아래 잘림·검은 얼룩·심볼 틈 잔점):
- 행 경계는 추측이 아니라 실측 — 디바이더 선 y=405/507/607/707/809
  (열 x105~262 행별 평균밝기·분산 스캔으로 검출). 크롭은 디바이더±4 안쪽.
- 디바이더 선은 배경보다 '밝아서' 배경제거(배경색 후보만 제거)에 안 걸리고
  전경으로 살아남던 것 — 크롭 범위에서 원천 배제 + 잔여 전경 잔점 제거로 이중 방어.
- 심볼 주변 드롭섀도우(거의 검정)는 felt와의 색거리 48을 살짝 넘어 전경으로 남아
  검은 얼룩이 됨 — '어두움(max채널≤60)'도 배경 후보에 포함하되 연결성 유지
  (BAR 안쪽 검정은 금테에 막혀 보존, 바깥 그림자만 flood로 제거).
- 마스크를 1px 침식 후 블러 — 경계 알파 램프가 심볼 자기 색 위에 놓여
  검은 그림자색 반투명 헤일로가 안 생김.
"""

import os
from PIL import Image, ImageFilter
import numpy as np
from collections import deque

RP = os.path.expanduser("~/development/barkan-resourcepack")
SRC = os.path.join(RP, "assets/barkan/textures/painting/slot_paytable.png")

# (x0, x1, y0, y1) — y는 디바이더(405/507/607/707/809) ±4 안쪽, x1은 행별 1번째 심볼 오른쪽 끝 실측
BOXES = {
    "cherry": (100, 245, 300, 400),
    "lemon":  (100, 245, 410, 502),
    "bell":   (100, 240, 512, 602),
    "bar":    (100, 235, 612, 702),
    "diamond":(95, 245, 712, 804),
    "seven":  (100, 230, 814, 895),
}

TEX_OUT = os.path.join(RP, "assets/minecraft/textures/item/slot")
MODEL_OUT = os.path.join(RP, "assets/barkan/models/slot")
ITEM_OUT = os.path.join(RP, "assets/barkan/items/slot")
for d in (TEX_OUT, MODEL_OUT, ITEM_OUT):
    os.makedirs(d, exist_ok=True)


def components(mask):
    """bool 마스크의 4방향 연결요소 — (픽셀리스트, 테두리접촉여부) 목록."""
    h, w = mask.shape
    labeled = np.zeros((h, w), dtype=bool)
    out = []
    for sy in range(h):
        for sx in range(w):
            if not mask[sy, sx] or labeled[sy, sx]:
                continue
            comp, touches = [], False
            q = deque([(sy, sx)])
            labeled[sy, sx] = True
            while q:
                y, x = q.popleft()
                comp.append((y, x))
                if y == 0 or y == h - 1 or x == 0 or x == w - 1:
                    touches = True
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not labeled[ny, nx]:
                        labeled[ny, nx] = True
                        q.append((ny, nx))
            out.append((comp, touches))
    return out


def foreground_mask(rgb):
    """True=심볼.

    1단계(안전한 코어): felt 색거리≤48 픽셀만 후보로 테두리 flood — 심볼은 절대 안 먹지만
      진한 그림자 얼룩이 남는다(v2에서 확인).
    2단계(제한 확장): 코어 배경에 '인접'한 그림자성 픽셀로 최대 6회(≈6px)만 팽창.
      그림자성 = felt 색조 레이(p≈t·ref)에 가깝거나 색거리≤80. 심볼의 어두운 외곽선도
      일부 후보가 되지만 확장 깊이 제한 때문에 안쪽까지 못 파먹는다(v3에서 무제한
      연결성으로 심볼에 구멍 뚫린 실패의 교훈).
    3단계: 갇힌 잔점(felt색 ≤40px) 제거 + 전경 잔점(디바이더 부스러기) 제거.
    """
    h, w, _ = rgb.shape
    corners = np.concatenate([
        rgb[0:8, 0:8].reshape(-1, 3), rgb[0:8, -8:].reshape(-1, 3),
        rgb[-8:, 0:8].reshape(-1, 3), rgb[-8:, -8:].reshape(-1, 3),
    ], axis=0).astype(int)
    ref = corners.mean(axis=0)
    rgb_i = rgb.astype(int)
    diff = np.abs(rgb_i - ref).sum(axis=2)

    # felt 레이 적합: 그림자 = felt를 어둡게 한 색(같은 색조) → p ≈ t·ref
    denom = float(np.dot(ref, ref))
    t = np.clip(np.tensordot(rgb_i, ref, axes=([2], [0])) / denom, 0.0, 1.3)
    resid = np.abs(rgb_i - t[..., None] * ref).sum(axis=2)
    shadowlike = ((resid <= 30) & (rgb.max(axis=2) <= 120)) | (diff <= 80)

    core = diff <= 48
    bg = np.zeros((h, w), dtype=bool)
    for comp, touches in components(core):
        if touches:
            for y, x in comp:
                bg[y, x] = True

    # 제한 팽창: bg 경계에서 그림자성 픽셀로 최대 5px
    for _ in range(5):
        grown = np.zeros_like(bg)
        grown[1:, :] |= bg[:-1, :]
        grown[:-1, :] |= bg[1:, :]
        grown[:, 1:] |= bg[:, :-1]
        grown[:, :-1] |= bg[:, 1:]
        new = grown & shadowlike & ~bg
        if not new.any():
            break
        bg |= new

    # 갇힌 felt색 잔점(심볼 틈새 점) — ★'진짜 felt색'(diff≤25)만. 48 기준을 그대로 쓰면
    #   BAR 안쪽 어두운 면(felt와 색거리 30~48)의 픽셀들이 잔점으로 오폭돼 구멍이 났다(v4).
    strict_felt = diff <= 25
    for comp, touches in components(strict_felt & ~bg):
        if len(comp) <= 60:
            for y, x in comp:
                bg[y, x] = True

    fg = ~bg
    comps = components(fg)
    if comps:
        main = max(comps, key=lambda c: len(c[0]))
        keep = np.zeros((h, w), dtype=bool)
        for comp, touches in comps:
            if comp is main[0] or (len(comp) >= 120 and not touches):
                for y, x in comp:
                    keep[y, x] = True
        fg = keep
    return fg


def write_rp_json(symbol):
    with open(os.path.join(MODEL_OUT, f"sym_{symbol}.json"), "w") as f:
        f.write('{"parent":"minecraft:item/generated","textures":{"layer0":"minecraft:item/slot/sym_%s"}}' % symbol)
    with open(os.path.join(ITEM_OUT, f"sym_{symbol}.json"), "w") as f:
        f.write('{"model":{"type":"minecraft:model","model":"barkan:slot/sym_%s"}}' % symbol)


im = Image.open(SRC).convert("RGBA")
arr = np.array(im)

for name, (x0, x1, y0, y1) in BOXES.items():
    crop = arr[y0:y1, x0:x1].copy()
    fg = foreground_mask(crop[:, :, :3])
    mask = Image.fromarray((fg * 255).astype(np.uint8), "L")
    # 1px 침식(경계를 심볼 안쪽으로) 후 가벼운 블러(AA) — 그림자색 헤일로 방지
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    crop[:, :, 3] = np.minimum(crop[:, :, 3], np.array(mask))
    out_img = Image.fromarray(crop, "RGBA")

    bbox = out_img.getbbox(alpha_only=True)
    if bbox:
        out_img = out_img.crop(bbox)
    side = max(out_img.size) + 14
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(out_img, ((side - out_img.width) // 2, (side - out_img.height) // 2), out_img)
    canvas = canvas.resize((128, 128), Image.LANCZOS)
    canvas.save(os.path.join(TEX_OUT, f"sym_{name}.png"))
    write_rp_json(name)
    print(name, "bbox", bbox)

print(f"완료: {len(BOXES)}종 → {TEX_OUT}")
