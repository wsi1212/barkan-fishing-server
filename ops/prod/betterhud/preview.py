#!/usr/bin/env python3
"""BetterHud 대화창을 배포 전에 오프라인으로 그려보는 미리보기.

배포 -> 접속 -> 스샷 왕복이 한 번에 10분씩 걸려서, 좌표를 눈으로 확인하려면 이게 필요하다.
배치 수식은 추측이 아니라 BetterHud 소스에서 그대로 옮겼다.

  LayoutComponentContainer.kt
    move = align==LEFT ? 0 : align==CENTER ? (max - W)/2 : (max - W)
    build() 앞에 offset==CENTER 이면 -max/2 를 붙인다
  HudParser.kt
    max = 레이아웃 안 "이미지" 중 가장 넓은 것의 폭 (텍스트는 세지 않는다)
  LayoutGroup.kt
    align 기본값 = LEFT, offset 기본값 = CENTER

따라서 요소의 왼쪽 끝 = anchor_x + (-max/2) + x + move.
  align: left   -> 왼쪽끝 = x - max/2   ← max 종속. 다른 이미지 크기만 바꿔도 전부 움직인다
  align: center -> 왼쪽끝 = x - W/2     ← x가 그 요소 자신의 중심. max와 무관 (권장)

★화면은 320x240으로 잡는다. 마크는 GUI 배율을 아무리 올려도 가상 화면을 최소
  320x240으로 보정하므로, 여기서 안 잘리면 모든 유저에게 보인다.
★이미지 폭은 160을 넘기지 말 것. 폰트 글리프 아틀라스에 못 들어가면 에러 없이 조용히
  사라진다(실측: 52·110·144는 나오고 217·300은 안 나옴). 넓은 판은 조각내서 붙인다.

사용법:  python3 preview.py [출력.png] [--zoom x0,y0,x1,y1]

  --zoom 은 화면 좌표로 잘라서 크게 그린다. 초상화가 액자 홈 안에 가운데인지,
  명패가 액자와 좌우로 맞는지 같은 몇 px 차이는 전체 그림으로는 절대 안 보인다.
  예) 액자+명패만 크게:  python3 preview.py /tmp/p.png --zoom -10,130,115,235
"""
import os, sys, yaml
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

# ★실제 클라 실측값(Feather 26.1.2 / GUI배율 3).
#   ★★세로는 "창 높이"가 아니라 "마크 프레임버퍼 높이"다. 화면기록이 macOS 타이틀바까지
#     담아 1462 였는데 실제 프레임버퍼는 1394 다. 1462/3=488 로 잡았다가 23px 어긋났고,
#     그걸 셰이더 상수(Y_BIAS)로 오해해서 위쪽 앵커 HUD 를 전부 23px 아래로 밀어버렸다.
#     검산: 대화창(gui.y=100, layout y=-102) -> 465-102 = 363, 실측 362.67. 보정 없음.
SCREEN_W, SCREEN_H = 891, 465
HOTBAR_H = 22
SAFE_W, SAFE_H = 320, 240       # 마크가 보장하는 최소 가상 화면 — 여기서 벗어나면 잘리는 유저가 생긴다

# ★세로 보정은 없다(0). 한때 23 을 넣었는데 그건 위 SCREEN_H 를 타이틀바 포함으로
#   잘못 잡아서 생긴 착시였다. 셰이더에도 그런 상수는 없다 —
#   `yGui = ui.y * gui.y/100` 이 전부이고, 가로는 `pos.x -= 0.5*ui.x` 와 상쇄된다.
#   ※상수를 넣고 싶어지면 먼저 SCREEN_H 가 프레임버퍼 높이인지부터 확인할 것.
Y_BIAS = 0

# 서버 폰트. 대사를 실제로 그려서 양피지 밖으로 넘치는지 잡는다.
# 16px은 인게임 스샷 실측으로 보정한 값. 13px일 때 141px로 나왔는데 실제는 167px이라
# 18% 과소평가였고, 그래서 글자 넘침을 못 잡았다.
FONT_TTF = os.path.expanduser("~/development/barkan-resourcepack/assets/barkan/font/aggro_medium.ttf")
# ★npc-dialogue-font.yml 의 scale 과 같아야 한다. 폰트 raster 를 16 -> 32 로 올렸으면
#   여기도 32 로. 안 맞추면 글자 폭을 절반으로 계산해 넘침을 못 잡는다.
FONT_PX = 32

# 패널 그림에서 실측한 영역. 패널 왼쪽 위를 (0,0)으로 본 좌표. (판 440x80 기준)
# ★눈대중이 아니라 조각 4장을 붙여 픽셀을 스캔해서 뽑은 값이다.
#   금테 = 금색 픽셀(r>90,g>70,b<0.75r)이 한 열/행에 40개 이상인 구간.
# ★calibrate.py 와 같은 값을 쓸 것. 어긋나면 "예측은 가운데인데 실측은 아니다"가 또 난다.
PARCHMENT = (112, 6, 427, 63)     # 대사 자리
FRAME_OUTER = (11, 6, 96, 71)     # 금테 바깥 — 명패는 이 좌우 중심(53.5)에 맞춘다
PORTRAIT_SLOT = (16, 10, 91, 68)  # 금테 안쪽 홈 — 초상화도 중심 53.5

SAMPLE_TEXT = "바르칸의 물은 정직하단다 — 던진 만큼 돌려주지."
SAMPLE_NAME = "[길잡이] 할아버지"

# HUD 세트별 (hud파일, layout파일, image파일, 텍스트 샘플들).
# ★샘플은 "가장 긴 현실값"으로 둘 것 — 짧은 값으로 확인하면 넘침을 못 잡는다.
SETS = {
    "npc-dialogue": ("npc-dialogue-hud.yml", "npc-dialogue-layout.yml", "npc-dialogue-image.yml",
                     [SAMPLE_TEXT, SAMPLE_NAME]),
    "status": ("status-hud.yml", "status-layout.yml", "status-image.yml",
               # ★Num.compact 적용 후의 실제 최댓값이다. 축약 전 값(999,999,999원)으로 두면
               #   과대평가해서 멀쩡한 배치를 넘친다고 오판한다.
               ["999,999원", "Lv.100", "999,999캐시"]),
    # 버프 판 — 줄 수 변형이 있어서 HUD_KEY 로 고른다(예: HUD_KEY=_3_sm 이면 3줄·작게).
    # ★샘플은 최장 현실값: 요리 이름은 "야광베리 커스터드"(9자), 스탯은 두 자리 수치.
    "buff": ("buff-hud.yml", "buff-layout.yml", "buff-image.yml",
             ["야광베리 커스터드", "12:05", "경험치 +16%", "도망감소 +42", "판매가 +6%"]),
    "place": ("place-hud.yml", "place-layout.yml", "place-image.yml",
              # ★14글자를 넘으면 자바(shortPlace)가 상위 지역을 떼므로, 이게 실제 최댓값이다.
              ["폭포_뒤_동굴_2층", "☀ 낮 ☁ 모래바람"]),
}


def load(name):
    return yaml.safe_load(open(os.path.join(HERE, name), encoding="utf-8"))


def main(out_path, zoom=None, setname="npc-dialogue"):
    hf, lf, imf, samples = SETS[setname]
    # 상태/위치 HUD 는 크기 단계별로 여러 벌이다 — 환경변수 HUD_SIZE 로 고른다(기본 md).
    want = os.environ.get("HUD_KEY") or ("_" + os.environ.get("HUD_SIZE", "md"))
    def pick(d):
        for k, v in d.items():
            if k.endswith(want):
                return v
        return next(iter(d.values()))
    hud = pick(load(hf))
    layout = pick(load(lf))
    images = load(imf)

    align = str(layout.get("align", "left")).lower()
    offset = str(layout.get("offset", "center")).lower()
    gui = hud["layouts"][1]["gui"]
    ax = SCREEN_W * gui["x"] / 100.0
    ay = SCREEN_H * gui["y"] / 100.0 - Y_BIAS

    # ★type: sequence 는 file 이 아니라 files 다. 리스너 값으로 프레임을 갈아끼우는 것이라
    #   미리보기에서는 HUD_FRAME 번째(기본 0)를 그린다.
    # HUD_FRAME=0,4,6 처럼 콤마로 주면 스탯 줄마다 다른 아이콘을 그린다(같은 그림 3개면
    # 아이콘이 실제로 갈리는지 눈으로 확인할 수 없다).
    frames = [int(v) for v in os.environ.get("HUD_FRAME", "0").split(",")]
    sized = {}
    for key, spec in images.items():
        files = spec.get("files")
        if files:
            row = int((key.split("_icon_")[1].split("_")[0]) if "_icon_" in key else 1)
            f = frames[min(row - 1, len(frames) - 1)]
            path = files[min(f, len(files) - 1)]
        else:
            path = spec["file"]
        im = Image.open(os.path.join(ASSETS, path)).convert("RGBA")
        bbox = im.split()[3].getbbox()               # BetterHud는 투명 여백을 잘라낸다
        im = im.crop(bbox)
        s = float((spec.get("setting") or {}).get("scale", 1.0))
        w, h = max(1, round(im.width * s)), max(1, round(im.height * s))
        # ★잘라낸 왼쪽 여백은 x에 다시 더해진다 (HudImageParser.kt):
        #     toPixelComponent(finalPixel.x + (image.xOffset * scale))
        #   이걸 빼먹으면 투명 여백이 있는 그림(초상화 등)이 실제보다 왼쪽에 그려진다.
        sized[key] = (im.resize((w, h), Image.LANCZOS), w, h, round(bbox[0] * s))

    used = [e["name"] for e in layout.get("images", {}).values()]
    mx = max((sized[n][1] for n in used if n in sized), default=0)

    def left_edge(x, w):
        base = {"left": 0, "center": -mx / 2, "right": -mx}[offset]
        move = {"left": 0, "center": (mx - w) / 2, "right": mx - w}[align]
        return ax + base + x + move

    canvas = Image.new("RGBA", (SCREEN_W, SCREEN_H), (60, 90, 130, 255))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, SCREEN_H - HOTBAR_H, SCREEN_W, SCREEN_H], fill=(35, 35, 40, 255))
    d.line([(SCREEN_W // 2, 0), (SCREEN_W // 2, SCREEN_H)], fill=(255, 80, 80, 120))

    print(f"화면 {SCREEN_W}x{SCREEN_H}  앵커 ({ax:.0f},{ay:.0f})  "
          f"align={align} offset={offset}  max={mx}")

    panel_l, panel_t = None, None
    rect = {}
    for idx in sorted(layout.get("images", {})):
        e = layout["images"][idx]; name = e["name"]
        if name not in sized:
            print(f"  ! 이미지 정의 없음: {name}"); continue
        im, w, h, xoff = sized[name]
        lx, ty = left_edge(e.get("x", 0) + xoff, w), ay + e.get("y", 0)
        canvas.alpha_composite(im, (round(lx), round(ty)))
        warn = ""
        if lx < 0 or lx + w > SCREEN_W:
            warn = "   ← ★화면 밖!"
        if w > 160:
            warn += "   ← ★폭 160 초과: 렌더 안 될 수 있음"
        # ★잘림 검사는 "화면 가운데 기준" HUD 에만 의미가 있다. gui.x 가 0/100 이면 화면
        #   모서리에 붙는 HUD 라 해상도가 달라도 항상 보인다 — 여기서 경고하면 오탐이다.
        if 0 < gui["x"] < 100 and (lx < (SCREEN_W-SAFE_W)/2 or lx + w > (SCREEN_W+SAFE_W)/2):
            warn += f"   (가상화면 {SAFE_W} 인 유저는 잘림)"
        if name.startswith("dialogue_panel"):
            panel_l = lx if panel_l is None else min(panel_l, lx)
            panel_t = ty if panel_t is None else min(panel_t, ty)
        rect[name] = (lx, ty, lx + w, ty + h)
        print(f"  {name:24s} x {lx:6.0f}~{lx+w:<6.0f} (폭 {w:3d}, 잘린여백 {xoff})  y {ty:.0f}~{ty+h:.0f}{warn}")

    parch = None
    if panel_l is not None:                       # 대화창 세트에만 있는 액자 정렬 검사
        def to_screen(box):
            return (panel_l + box[0], panel_t + box[1], panel_l + box[2], panel_t + box[3])
        parch = to_screen(PARCHMENT)
        slot, frame = to_screen(PORTRAIT_SLOT), to_screen(FRAME_OUTER)
        d.rectangle(list(parch), outline=(0, 220, 0, 200))

        # ★몇 px 어긋남은 전체 그림으로 안 보인다. 숫자로 찍어서 판정한다.
        def gap(label, box, ref):
            if box is None:
                return
            print(f"  · {label:10s} 왼쪽 {box[0]-ref[0]:+.0f}  오른쪽 {ref[2]-box[2]:+.0f}"
                  f"  위 {box[1]-ref[1]:+.0f}  아래 {ref[3]-box[3]:+.0f}"
                  f"   (좌우 차 {abs((box[0]-ref[0])-(ref[2]-box[2])):.0f})")
        print("  ── 액자 정렬 (좌우 차가 0이어야 가운데) ──")
        print("     ※예측과 실제는 요소마다 1~2px 다르다(반올림). 최종 확정은 calibrate.py 로.")
        gap("초상화", rect.get("npc_dialogue_portrait"), slot)
        gap("명패", rect.get("dialogue_nameplate"), frame)
        if zoom:
            for box, col in ((slot, (0, 200, 255, 255)), (frame, (255, 0, 220, 255))):
                d.rectangle(list(box), outline=col)

    # 상태/위치 HUD — 글자가 판(양피지) 밖으로 나가는지만 본다.
    # ★판 크기를 scale 로 줄이므로 안쪽 여백도 판 크기에 비례해서 잡는다(고정 px 로 두면 틀린다).
    for key in [k for k in rect if k.startswith(("status_plate", "place_plate", "buff_plate"))]:
        plate = rect.get(key)
        if not plate:
            continue
        pad = max(3, round((plate[2] - plate[0]) * 0.05))
        parch = (plate[0] + pad, plate[1] + pad, plate[2] - pad, plate[3] - pad)
        d.rectangle(list(parch), outline=(0, 220, 0, 200))

    def wrap(text, limit, font, force=False):
        """BetterHud Adventures.kt 의 split 판정을 그대로 옮긴 것.
             if (i >= sw && (i >= 1.25*sw || ch == ' ') || forceSplit) end()
        ★연산자 우선순위 때문에 forceSplit 은 전체 조건과 OR 로 묶인다 -> 켜면 매 글자 줄바꿈.
        ★공백이 없으면 1.25*sw 까지 밀고 나간다 -> 실제 상한은 split-width 의 1.25배."""
        out, cur, i = [], "", 0.0
        for ch in text:
            i += d.textlength(ch, font=font)
            cur += ch
            if (i >= limit and (i >= 1.25 * limit or ch == " ")) or force:
                out.append(cur); cur = ""; i = 0.0
        if cur: out.append(cur)
        return out

    for idx in sorted(layout.get("texts", {})):
        t = layout["texts"][idx]
        sample = samples[min(idx - 1, len(samples) - 1)]
        fs = max(6, round(FONT_PX * float(t.get("scale", 1.0))))
        font = ImageFont.truetype(FONT_TTF, fs)
        sw = t.get("split-width")
        force = bool(t.get("force-split", False))
        lines = (wrap(sample, sw, font, force) if sw else [sample])[: t.get("line", 99)]
        lw = t.get("line-width", 10)
        widest = max((d.textlength(l, font=font) for l in lines), default=0)
        # ★BetterHud는 텍스트의 '실제 렌더 폭'으로 move를 계산한다. split-width가 아니다.
        #   (align:left 면 move=0 이라 폭과 무관하지만, center/right 면 결정적으로 다르다)
        lx = left_edge(t.get("x", 0), widest)
        # ★텍스트 자체의 align. center 면 x 가 "글자의 중심"이다(인게임으로 확인함).
        ta = str(t.get("align", "left")).lower()
        if ta == "center": lx -= widest / 2
        elif ta == "right": lx -= widest
        ty = ay + t.get("y", 0)
        warn = ""
        for i, line in enumerate(lines):
            y = ty + i * lw
            col = str(t.get("color", "#3D2840")).lstrip("#")
            fill = tuple(int(col[i:i+2], 16) for i in (0, 2, 4)) + (255,) if len(col) == 6 else (61, 40, 64, 255)
            d.text((lx, y), line, font=font, fill=fill)
            if parch and idx == 1:
                if lx < parch[0] or lx + d.textlength(line, font=font) > parch[2]:
                    warn = "   ← ★양피지 좌우로 넘침!"
                elif y < parch[1] or y + FONT_PX > parch[3]:
                    warn = "   ← ★양피지 위아래로 넘침!"
        print(f"  [text{idx}] {len(lines)}줄  x {lx:6.0f}~{lx+widest:<6.0f} "
              f"(가장 긴 줄 {widest:.0f})  y {ty:.0f}~{ty+len(lines)*lw:.0f}{warn}")
    if parch:
        print(f"  (양피지 x {parch[0]:.0f}~{parch[2]:.0f}  y {parch[1]:.0f}~{parch[3]:.0f})")

    if zoom:
        x0, y0, x1, y1 = zoom
        canvas = canvas.crop((x0, y0, x1, y1))
        k = max(1, min(12, 1400 // max(1, x1 - x0)))
    else:
        k = 3
    canvas.convert("RGB").resize((canvas.width * k, canvas.height * k), Image.NEAREST).save(out_path)
    print(f"\n미리보기 저장: {out_path}  (x{k})")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    z = next((a for a in sys.argv[1:] if a.startswith("--zoom")), None)
    st = next((a for a in sys.argv[1:] if a.startswith("--set")), None)
    main(args[0] if args else "/tmp/hud-preview.png",
         tuple(int(v) for v in z.split("=", 1)[1].split(",")) if z and "=" in z else None,
         st.split("=", 1)[1] if st and "=" in st else "npc-dialogue")
