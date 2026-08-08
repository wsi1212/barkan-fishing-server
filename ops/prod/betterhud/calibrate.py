#!/usr/bin/env python3
"""실제 게임 화면(스샷·화면기록)에서 대화창 부품의 위치를 픽셀로 재는 도구.

★왜 필요한가: preview.py 는 BetterHud 소스를 옮긴 "예측"이고, 이건 "실측"이다.
  2026-08-08 유저가 "렌더러는 딱 맞는데 실제는 다르다"고 했을 때, 말로 다투는 대신
  화면기록에서 프레임을 뽑아 판 그림을 템플릿 매칭해 좌표를 확정지어 끝냈다.
  앞으로 렌더러와 실제가 다르다는 얘기가 나오면 이 스크립트를 먼저 돌릴 것.

원리: 판 조각 4장을 붙인 440x80 원본을 GUI 배율만큼 확대해 화면에서 최소오차 위치를
  찾는다(배율도 같이 탐색). 판 위치가 잡히면 나머지는 판 기준 상대좌표로 환산한다.

필요: numpy (없으면 `python3 -m venv venv && ./venv/bin/pip install numpy pillow`)
사용법:
  python3 calibrate.py <스샷.png>
  python3 calibrate.py <화면기록.mov>      # ffmpeg 로 프레임 뽑아 대화창 있는 것 자동 선택
"""
import os, subprocess, sys, tempfile
from PIL import Image
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "assets", "dialogue")

# 판 그림에서 실측한 기준선 (판 왼쪽 위 = 0,0). 열별 밝기 프로파일로 뽑은 값.
#   x 7~9 · 97~99 = 깊은 이음매(홈), 11~15 · 92~96 = 금테 세로바, 16~91 = 액자 홈 안쪽
FRAME_GOLD = (11, 96)      # 금테 바깥 좌우
FRAME_SLOT = (16, 91)      # 금테 안쪽 홈 좌우
FRAME_MID = (FRAME_GOLD[0] + FRAME_GOLD[1]) / 2   # 53.5 — 초상화·명패는 여기에 맞춘다


def panel_image():
    im = Image.new("RGBA", (440, 80))
    for i in range(4):
        im.alpha_composite(Image.open(os.path.join(ART, f"dialogue-panel-{i+1}.png")).convert("RGBA"),
                           (i * 110, 0))
    return im


def frames_from(path):
    if path.lower().endswith((".png", ".jpg", ".jpeg")):
        return [path]
    d = tempfile.mkdtemp(prefix="bhcal")
    subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "fps=2", os.path.join(d, "f%03d.png")],
                   check=True)
    return sorted(os.path.join(d, f) for f in os.listdir(d))


def locate(scr, tmpl, scales=(2, 3, 4, 5, 6)):
    """(오차, 배율, x, y) — 성긴 격자로 찾고 주변을 정밀 보정."""
    H, W = scr.shape[:2]
    best = None
    for S in scales:
        t = np.asarray(tmpl.convert("RGB").resize((tmpl.width * S, tmpl.height * S), Image.NEAREST),
                       dtype=np.float32)
        th, tw = t.shape[:2]
        if tw > W or th > H:
            continue
        ts, cur = t[::8, ::8], None
        for y in range(max(0, H - th - 450), H - th, 4):
            for x in range(0, W - tw, 4):
                d = np.abs(scr[y:y + th:8, x:x + tw:8] - ts).mean()
                if cur is None or d < cur[0]:
                    cur = (d, x, y)
        d0, x0, y0 = cur
        for y in range(y0 - 5, y0 + 6):
            for x in range(x0 - 5, x0 + 6):
                if y < 0 or x < 0 or y + th > H or x + tw > W:
                    continue
                d = np.abs(scr[y:y + th, x:x + tw] - t).mean()
                if d < d0:
                    d0, x0, y0 = d, x, y
        if best is None or d0 < best[0]:
            best = (d0, S, x0, y0)
    return best


def find_part(scr, fname, scale, S, px, py):
    im = Image.open(os.path.join(ART, fname)).convert("RGBA")
    im = im.crop(im.split()[3].getbbox())          # BetterHud 와 똑같이 투명 여백을 잘라낸다
    w, h = max(1, round(im.width * scale)), max(1, round(im.height * scale))
    im = im.resize((w, h), Image.LANCZOS)
    alpha = np.asarray(im.resize((w * S, h * S), Image.NEAREST), dtype=np.float32)[:, :, 3:4] / 255.0
    t = np.asarray(im.convert("RGB").resize((w * S, h * S), Image.NEAREST), dtype=np.float32)
    th, tw = t.shape[:2]
    H, W = scr.shape[:2]
    best = None
    for y in range(py - 40, min(H - th, py + 80 * S + 40)):
        for x in range(max(0, px - 40), min(W - tw, px + 160 * S)):
            d = (np.abs(scr[y:y + th:3, x:x + tw:3] - t[::3, ::3]) * alpha[::3, ::3]).mean()
            if best is None or d < best[0]:
                best = (d, x, y)
    d, x, y = best
    return (x - px) / S, w, (y - py) / S, h


def main(path):
    panel = panel_image()
    for f in frames_from(path):
        scr = np.asarray(Image.open(f).convert("RGB"), dtype=np.float32)
        got = locate(scr, panel)
        if got is None or got[0] > 30:
            continue                                # 대화창이 안 열린 프레임
        err, S, px, py = got
        H, W = scr.shape[:2]
        sw, sh = int(np.ceil(W / S)), int(np.ceil(H / S))
        print(f"{os.path.basename(f)}  오차 {err:.1f}  GUI배율 {S}  가상화면 {sw}x{sh}")
        print(f"  판 왼쪽위 = 화면 GUI ({px/S:.2f}, {py/S:.2f})")
        print(f"  판 위끝이 화면 바닥에서 {sh - py/S:.2f}px 위  (layout y=-102 이면 예측 102"
              f" -> 세로 보정상수 {sh - py/S - 102:.2f})")
        for label, fn, sc in (("초상화", "portrait-grandfather-hud.png", 0.40),
                              ("명패", "dialogue-nameplate.png", 0.8)):
            lx, w, ty, h = find_part(scr, fn, sc, S, px, py)
            mid = lx + w / 2
            print(f"  {label:5s} 판기준 x {lx:6.2f}~{lx+w:6.2f} (폭 {w})  y {ty:6.2f}~{ty+h:6.2f}"
                  f"   중심 {mid:6.2f}  액자중심({FRAME_MID}) 대비 {mid-FRAME_MID:+.2f}")
        return
    print("대화창이 열린 프레임을 못 찾았다.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1])
