#!/usr/bin/env python3
"""상태/위치 HUD 정의를 크기 단계별로 생성한다.

★왜 생성기인가: BetterHud 는 크기를 리소스팩 빌드 시점에 글리프로 구워버린다. 런타임에
  플레이어마다 배율을 바꿀 수단이 없으므로, "크기 설정"을 만들려면 단계 수만큼 이미지·
  레이아웃·HUD 정의를 통째로 복제해야 한다. 4벌을 손으로 관리하면 반드시 한 벌만 고쳐지고
  어긋난다(오늘 하루에만 좌표를 열 번 넘게 만졌다). 그래서 좌표는 여기 한 곳에만 둔다.

★좌표는 전부 "원본(배율 1.0) 판 좌표"로 적는다. 실제 값은 배율을 곱해 여기서 계산한다.
  화면 모서리 여백(10/3)만은 배율과 무관한 화면 px 이다 — 작게 골랐다고 구석에서
  멀어지면 어색하다.

산출: status-·place-·buff-{image,layout,hud}.yml  (손으로 고치지 말 것)
사용:  python3 gen_hud_sizes.py              # 상태·장소·버프 판
       python3 gen_hud_sizes.py --dialogue   # 대화창까지(★뒤에 gen_npc_portrait_huds.py 필수)
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "assets")

# 단계 id 와 이름. ★Java 쪽 StatusHud.SIZE_IDS 와 순서·id 가 같아야 한다.
#   다르면 설정이 엉뚱한 HUD 를 붙인다.
SIZES = [("sm", "작게"), ("md", "보통"), ("lg", "크게"), ("xl", "아주 크게")]

# ★배율 사다리는 판마다 다르다. 기준은 "보통(md) = 지금 배포돼 있는 그 크기"다.
#   상태/위치 판은 원본 아트의 0.66 배로 쓰고 있었고, 대화창은 원본 그대로(1.0) 쓰고 있었다.
#   같은 사다리를 쓰면 대화창이 갑자기 34% 작아진다.
#   ★대화창 상한은 1.40 이다 — 조각 폭 110 x 1.45 = 160 이 글리프 아틀라스 한계라서
#     그 위로 올리면 판이 통째로 사라진다.
SCALE_STATUS = (0.50, 0.66, 0.85, 1.00)
SCALE_DIALOGUE = (0.75, 1.00, 1.20, 1.40)

MARGIN_X, MARGIN_Y = 10, 3      # 화면 모서리에서의 여백(배율 무관, 화면 px)
# ★폰트 raster 를 16 -> 32 로 올렸으므로 여기를 절반으로 내려 표시 크기를 유지한다.
#   (표시 높이 = 폰트 scale x 이 값. 32 x 0.31 = 9.9 ~ 예전 16 x 0.62 와 같다)
TEXT_SCALE = 0.31               # 배율 1.0 기준 글자 크기
TEXT_H = 10.6                   # 그 크기에서 글자 한 줄의 대략 높이(세로 가운데 맞춤용)
STATUS_ICON_DISPLAY = (16, 16)  # 128px 원본을 BetterHud가 이 표시 크기로 축소한다.

# 폰트도 화면 역할별로 나눈다. 파일은 npc-dialogue-font.yml 에서 선언한다.
FONT_HUD = "hud_font"                    # 나머지 HUD — 얇은 폰트
FONT_HUD_ORIGINAL = "hud_original_font"  # 레벨·지역·재화·요리버프 — 기존 폰트
FONT_DIALOGUE = "dialogue_font"          # 대화창 — Medium

STATUS = dict(
    plate=("status-plate.png", 124, 72),
    rows=(16, 34, 52),                        # 줄 중심 (판 좌표)
    # ★한 줄(레벨)은 "Lv.100 + 경험치바"가 판 폭을 꽉 채운다. 바를 왼쪽으로 당기려면
    #   아이콘/글자도 같이 당겨야 한다 — 바만 당기면 Lv.100 에 달라붙는다.
    icon_x=10, text_x=29,
    icons=["icon-coin.png", "icon-star.png", "icon-gem.png"],
    # ★split 단계수 = 바 폭(px). build_status_hud.BAR_W 와 같아야 1px 단위로 채워진다.
    bar=("exp-bar-empty.png", "exp-bar-fill.png", 76, 32),   # (빈, 채움, 판 x, split 단계수)
    texts=["hud_money", "hud_level", "hud_cash"],
    colors=["#5C3F0E", "#0E3E42", "#3A1A5C"],
)
# 대화창(하단 중앙). 판 440x80 이지만 글리프 아틀라스 상한(160) 때문에 110 짜리 4조각이다.
# 좌표는 "판 왼쪽 위 = (0,0)" 기준. 지금 배포된 값에서 역산해 넣었다.
DIALOGUE = dict(
    slices=["dialogue-panel-1.png", "dialogue-panel-2.png",
            "dialogue-panel-3.png", "dialogue-panel-4.png"],
    slice_w=110, panel_h=80,
    portrait=("portrait-grandfather-hud.png", 35, 10, 0.40),   # (파일, 판x, 판y, 배율)
    nameplate=("dialogue-nameplate.png", 9, 62, 0.8),
    # 긴 일일/사이드 퀘스트 문장이 3줄째에서 초상화 쪽으로 밀리지 않도록
    # split-width 를 230 -> 210 으로 낮춘다. BetterHud 는 공백 기준 줄바꿈에서
    # 이 값을 최대 1.25배까지 넘길 수 있으므로, 판 안쪽 여백을 포함해 잡는다.
    line=(122, 10, 0.425, 3, 15, 210),  # 대사: 판x, 판y, 배율, 줄수, 줄간격, split-width
    # 이름표 폭 안에 긴 NPC 이름도 들어오도록 좌우 중앙 정렬 + 약간 축소.
    name=(53.5, 68, 0.25),               # 이름: 명패 중심x, 판y, 배율
    hotbar=22,                          # 판 아래에 비워두는 화면 px (핫바 자리)
)
PLACE = dict(
    plate=("place-plate.png", 124, 42),
    rows=(14, 27),
    text_x=14,
    texts=["hud_place", "hud_env"],
    colors=["#4A3A22", "#4A3A22"],
)

# 버프 판(좌상단, 지역바 아래) — 먹은 요리 버프를 포션 효과처럼 상시 표시.
# ★스탯 줄 수(1~3)만큼 판이 따로 있다. 한 줄짜리 버프에 3줄 판을 붙이면 아래가 텅 빈다.
#   판 높이 계산식은 gui-forge/build_status_hud.py 의 buff_plate_h() 와 같아야 한다(아래서 검산).
# ★폭은 정보바·장소바와 같은 124 로 맞췄다. 왼쪽 위에 세로로 나란히 놓이므로 폭이 다르면
#   층이 어긋나 보인다. 그 안에 넣으려고 "이름 한 줄 / 게이지+남은시간 한 줄" 로 쪼갰다 —
#   가장 작은 단계(x0.5, 판 62px)에서 이름과 시간을 한 줄에 두면 최장 이름
#   ("야광베리 커스터드" 47px + "12:05" 18px)이 넘친다.
BUFF = dict(
    plate_w=124,
    # ★미리보기로 잡은 값들이다. row_dy 17 은 아이콘(16px)끼리 맞닿았고, name_y 13 은
    #   이름 글자 위쪽이 양피지 상단선에 2.7px 까지 붙었다(아래 여백은 6.7 로 남아 불균형).
    row0=45, row_dy=19,          # 스탯 줄 중심(판 좌표). 아이콘 16px + 위아래 숨통 3px
    bottom=18,                   # 마지막 줄 아래 여백. 지역바 판(42)에 맞춘 값
    name_y=15,                   # 요리 이름 줄 중심
    bar_y=29,                    # 시간 게이지 줄 중심
    bar=("buff-bar-empty.png", "buff-bar-fill.png", 10, 60, 8),  # (빈, 채움, 판x, 폭=split, 높이)
    name_x=10, time_x=112,       # 시간은 오른쪽 정렬이라 x 가 글자의 오른쪽 끝이다
    icon_x=10, icon_h=16, text_x=30,
    gap=3,                       # 지역바 아래 여백(배율 무관, 화면 px)
    name_color="#4A2D12",        # 짙은 갈색 — 판이 크림색이라 밝은 색은 안 보인다
    time_color="#123E42",
    stat_color="#1E5B22",        # 버프는 이득이니 초록 계열
    # ★파일 순서 = sequence 프레임 순서 = 자바 BuffStats.STATS 순서 = build_status_hud.BUFF_STAT_ICONS.
    #   네 곳이 어긋나면 경험치 버프에 판매가 아이콘이 뜬다.
    stats=["exp", "size", "gradeup", "escape", "crit", "double", "sell", "difficulty"],
    rows_max=3,
)


def buff_plate_h(rows):
    return BUFF["row0"] + BUFF["row_dy"] * (rows - 1) + BUFF["bottom"]


HEAD = """# ★★이 파일은 gen_hud_sizes.py 가 생성한다. 손으로 고치지 말 것 —
#   크기 단계가 {n} 벌이라 손으로 고치면 한 벌만 바뀌고 나머지가 어긋난다.
#   좌표를 바꾸려면 gen_hud_sizes.py 의 STATUS/PLACE 를 고치고 다시 돌린다.
"""


# ★★단계별로 "미리 축소한 별도 파일"을 만든다. setting.scale 로 같은 png 를 여러 배율로
#   참조하면 BetterHud 가 판(큰 이미지)을 조용히 누락시킨다 — 2026-08-09 실측:
#   place_plate 4단계 중 sm 만 폰트에 들어가고 md/lg/xl 은 통째로 빠졌다(경고도 없음).
#   아이콘처럼 작은 건 멀쩡해서 더 헷갈렸다. 파일을 나누면 그 경로를 아예 안 탄다.
GEN = "gen"          # assets/<원본폴더>/gen/ 에 산출

# ★HD 배수. 파일을 "표시 크기 x HD" 로 굽고 setting.scale 로 1/HD 만큼 줄여 표시한다.
#   MC 는 텍스처를 원본 해상도로 들고 있다가 표시 크기에 맞춰 그리므로, GUI 배율이 높을수록
#   원본 픽셀이 그대로 살아 선명해진다(HD 폰트 리소스팩과 같은 원리).
#   ★2026-08-10 실측으로 확정: 원본 496x288 을 height 72 로 표시해도 텍스처가 안 줄어든다.
#   ★★단 "같은 png 를 두 정의가 참조하면 먼저 나온 하나만 등록된다"(전역 파일 단위 등록).
#     그래서 HD 로 가더라도 단계마다 파일은 따로 있어야 한다. 한 파일로 배율만 달리하면
#     4단계 중 1개만 팩에 들어간다 — 예전에 판이 사라졌던 진짜 원인이 이것이다.
HD = 4


def scaled_file(folder, fname, sid, s, base=None, suffix=""):
    """원본을 s 배로 줄여 assets/<folder>/gen/<이름>-<단계><접미사>.png 로 저장하고 상대경로를 돌려준다.

    base=(폭,높이) 를 주면 "배율 1.0 에서의 표시 크기"를 원본 크기와 따로 정한다.
    ★HD 아이콘용이다. 스탯 아이콘은 원본이 128px 인데 표시는 16px 이라, 원본을 그대로
      표시 크기로 보면 xl 단계에서 128px 짜리 아이콘이 된다. base 를 주면 표시는 16 이고
      파일은 그 4배(64px)로 구워져 GUI 아이콘처럼 선명하게 나온다.
    suffix 는 "같은 원본을 여러 정의가 쓸 때" 파일을 갈라 두기 위한 것이다 —
    ★BetterHud 는 png 를 전역 파일 단위로 등록해서, 같은 파일을 두 정의가 참조하면
      먼저 나온 하나만 살아남고 나머지는 경고도 없이 빠진다.
    """
    src = os.path.join(ART, folder, fname)
    outdir = os.path.join(ART, folder, GEN)
    os.makedirs(outdir, exist_ok=True)
    stem = fname[:-4]
    out = f"{stem}-{sid}{suffix}.png"
    with Image.open(src) as im:
        im = im.convert("RGBA")
        bw, bh = base if base else (im.width, im.height)
        w, h = max(1, round(bw * s)), max(1, round(bh * s))            # 표시 크기
        # 표시 크기의 HD 배로 굽는다. 원본보다 크게는 만들지 않는다(없는 정보는 못 만든다).
        k = min(HD, max(1.0, im.width / max(1, w)))
        im.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS).save(
            os.path.join(outdir, out))
    assert out == out.lower(), out      # 대문자 하나면 폰트 전체가 거부된다
    # ★160 제한은 "표시 폭"에 걸린다(원본 496 을 표시 124 로 쓰는 건 실측으로 통과).
    assert w <= 160, f"{out} 표시폭 {w} — 160 넘으면 글리프 아틀라스에서 조용히 사라진다"
    return f"{folder}/{GEN}/{out}", w, h, round(1.0 / k, 4)


def png(name, s=1.0, base=None):
    """축소 후의 (폭, 높이). ★BetterHud 는 투명 여백을 잘라내므로 그 뒤 크기를 재야
    세로 가운데 맞춤이 맞는다.

    base는 HD 원본의 실제 화면 표시 크기다. 상태 아이콘은 원본이 128px이지만 16px로
    표시하므로, 배치 좌표도 이 값을 기준으로 계산해야 한다.
    """
    with Image.open(os.path.join(ART, "status", name)) as im:
        im = im.convert("RGBA")
        if base:
            im = im.resize(base, Image.LANCZOS)
        im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
        box = im.split()[3].getbbox() or (0, 0, im.width, im.height)
        return box[2] - box[0], box[3] - box[1]


def emit(path, text):
    with open(os.path.join(HERE, path), "w", encoding="utf-8") as f:
        f.write(HEAD.format(n=len(SIZES)) + text)
    print("  ", path)


def build_status():
    img, lay, hud = [], [], []
    pw, ph = STATUS["plate"][1], STATUS["plate"][2]
    for (sid, label), s in zip(SIZES, SCALE_STATUS):
        W = round(pw * s)
        # align:left · offset:center 이므로 왼쪽끝 = 앵커x - max/2 + x, max = 판 폭.
        # 앵커는 화면 오른쪽 끝이라 "오른쪽에서 N px" = x = W/2 - N.
        base_x = W / 2 - (MARGIN_X + W)
        f, _, _, sc = scaled_file("status", STATUS["plate"][0], sid, s)
        img.append(f"status_plate_{sid}:\n  type: single\n  file: {f}\n"
                   f"  setting:\n    scale: {sc}\n")
        lay_lines = [f"    1:\n      name: status_plate_{sid}\n      x: {base_x:g}\n      y: {MARGIN_Y}\n"]
        n = 2
        for i, icon in enumerate(STATUS["icons"]):
            key = f"status_icon_{i}_{sid}"
            iw, ih = png(icon, s, base=STATUS_ICON_DISPLAY)
            fi, _, _, sc = scaled_file("status", icon, sid, s, base=STATUS_ICON_DISPLAY)
            img.append(f"{key}:\n  type: single\n  file: {fi}\n"
                       f"  setting:\n    scale: {sc}\n")
            center = MARGIN_Y + STATUS["rows"][i] * s
            lay_lines.append(f"    {n}:\n      name: {key}\n"
                             f"      x: {base_x + round(STATUS['icon_x'] * s):g}\n"
                             f"      y: {round(center - round(ih * s) / 2)}\n")
            n += 1
        empty, fill, bx, split = STATUS["bar"]
        bh = png(empty, s)[1]
        bar_center = MARGIN_Y + STATUS["rows"][1] * s
        bar_y = round(bar_center - round(bh * s) / 2)
        fe, _, _, sce = scaled_file("status", empty, sid, s)
        img.append(f"exp_bar_empty_{sid}:\n  type: single\n  file: {fe}\n"
                   f"  setting:\n    scale: {sce}\n")
        # ★listener 는 리스너가 준 0.0~1.0 만큼 그림을 잘라 그린다(바닐라 체력바와 같은 방식).
        #   barkan_exp 는 BlockShip(StatusHud)이 BetterHud API 로 등록한다 — 그게 없으면 파싱 실패.
        ff, _, _, scf = scaled_file("status", fill, sid, s)
        img.append(f"exp_bar_{sid}:\n  type: listener\n  file: {ff}\n"
                   f"  split: {split}\n  split-type: left\n"
                   f"  setting:\n    scale: {scf}\n    listener:\n      class: barkan_exp\n")
        for key in (f"exp_bar_empty_{sid}", f"exp_bar_{sid}"):
            lay_lines.append(f"    {n}:\n      name: {key}\n"
                             f"      x: {base_x + round(bx * s):g}\n      y: {bar_y}\n")
            n += 1
        txt = []
        for i, var in enumerate(STATUS["texts"]):
            center = MARGIN_Y + STATUS["rows"][i] * s
            # 상단 상태 HUD의 세 항목(레벨 포함)은 모두 기존 굵은 폰트를 사용한다.
            font = FONT_HUD_ORIGINAL
            txt.append(f"    {i+1}:\n      name: {font}\n"
                       f"      pattern: \"[string:{var}]\"\n"
                       f"      color: \"{STATUS['colors'][i]}\"\n"
                       f"      x: {base_x + round(STATUS['text_x'] * s):g}\n"
                       f"      y: {round(center - round(TEXT_H * s) / 2)}\n"
                       f"      scale: {round(TEXT_SCALE * s, 3)}\n      align: left\n")
        lay.append(f"barkan_status_layout_{sid}:  # {label} (x{s})\n  align: left\n  images:\n"
                   + "".join(lay_lines) + "  texts:\n" + "".join(txt))
        hud.append(f"barkan_status_{sid}:\n  tick: 20\n  layouts:\n    1:\n"
                   f"      name: barkan_status_layout_{sid}\n      gui:\n        x: 100\n        y: 0\n")
    emit("status-image.yml", "\n".join(img))
    emit("status-layout.yml", "\n".join(lay))
    emit("status-hud.yml", "\n".join(hud))


def build_place():
    img, lay, hud = [], [], []
    pw = PLACE["plate"][1]
    for (sid, label), s in zip(SIZES, SCALE_STATUS):
        W = round(pw * s)
        base_x = W / 2 + MARGIN_X          # 앵커가 화면 왼쪽 끝이라 "왼쪽에서 N px" = x = W/2 + N
        f, _, _, sc = scaled_file("status", PLACE["plate"][0], sid, s)
        img.append(f"place_plate_{sid}:\n  type: single\n  file: {f}\n"
                   f"  setting:\n    scale: {sc}\n")
        txt = []
        for i, var in enumerate(PLACE["texts"]):
            center = MARGIN_Y + PLACE["rows"][i] * s
            # ★가운데 정렬. align: center 는 x 를 "글자의 중심"으로 해석하므로
            #   판의 가로 중심을 준다(왼쪽 끝이 아니다).
            txt.append(f"    {i+1}:\n      name: {FONT_HUD_ORIGINAL}\n"
                       f"      pattern: \"[string:{var}]\"\n"
                       f"      color: \"{PLACE['colors'][i]}\"\n"
                       f"      x: {base_x + W / 2:g}\n"
                       f"      y: {round(center - round(TEXT_H * s) / 2)}\n"
                       f"      scale: {round(TEXT_SCALE * s, 3)}\n      align: center\n")
        lay.append(f"barkan_place_layout_{sid}:  # {label} (x{s})\n  align: left\n  images:\n"
                   f"    1:\n      name: place_plate_{sid}\n      x: {base_x:g}\n      y: {MARGIN_Y}\n"
                   + "  texts:\n" + "".join(txt))
        hud.append(f"barkan_place_{sid}:\n  tick: 20\n  layouts:\n    1:\n"
                   f"      name: barkan_place_layout_{sid}\n      gui:\n        x: 0\n        y: 0\n")
    emit("place-image.yml", "\n".join(img))
    emit("place-layout.yml", "\n".join(lay))
    emit("place-hud.yml", "\n".join(hud))


def build_dialogue():
    """대화창 "기본 4벌"만 만든다. ★단독으로 돌리면 초상화 HUD 를 날린다.

    ★★2026-08-21 사고: 이 함수가 npc-dialogue-{hud,layout,image}.yml 를 통째로 덮어써서
      gen_npc_portrait_huds.py 가 만들어 둔 NPC별 초상화 정의 1160 벌(165KB)이 4벌로
      쪼그라들었다. 게다가 그 초상화 생성기는 **자기 이전 출력(_base_<단계> 블록)을 템플릿으로
      다시 읽는다** — 덮어쓰고 나면 "KeyError: npc_dialogue_layout_*_base_sm" 으로 재생성도
      안 된다(git 에서 되살려야 했다). 그래서 기본값은 "대화창 건드리지 않음"이다.
      대화창 좌표를 정말 바꿀 때만 --dialogue 로 명시하고, 끝나면 반드시
      python3 gen_npc_portrait_huds.py 를 이어서 돌려 초상화를 복원할 것.

    대화창을 크기 단계별로. 하단 중앙 앵커(gui x50 y100)라 계산이 위쪽 판들과 다르다."""
    D = DIALOGUE
    img, lay, hud = [], [], []
    for (sid, label), s in zip(SIZES, SCALE_DIALOGUE):
        W = round(D["slice_w"] * s)
        assert W <= 160, f"조각 폭 {W} — 160 넘으면 아틀라스에서 사라진다"          # 조각 하나 폭 = 이 레이아웃의 max
        top = -(round(D["panel_h"] * s) + D["hotbar"])   # 판 위쪽 끝(음수가 위)

        def px(panel_x, scale=1.0, trim=0):
            """판 좌표 -> layout x. 왼쪽끝 = 앵커 - max/2 + x 이므로 x = 판왼쪽offset + 판x + max/2.
            판 왼쪽은 화면 중앙에서 -2W (조각 4개의 절반)."""
            return -2 * W + round(panel_x * s) + W / 2 - trim

        lay_lines, n = [], 1
        for i, f in enumerate(D["slices"]):
            key = f"dialogue_panel_{i+1}_{sid}"
            fp, _, _, sc = scaled_file("dialogue", f, sid, s)
            img.append(f"{key}:\n  type: single\n  file: {fp}\n"
                       f"  setting:\n    scale: {sc}\n")
            # ★조각은 "i x 실제 조각폭(W)" 으로 놓아야 한다. round(i x 110 x 배율) 로 잡으면
            #   폭은 round(110 x 배율) 하나인데 위치만 따로 반올림돼 조각 사이가 1px 벌어진다
            #   (0.75배: 위치 0/82/165/248 인데 폭은 82 -> 3·4번째에서 틈).
            #   ★게다가 BetterHud 에 배율을 맡기면 반올림 규칙까지 갈린다 —
            #     Java Math.round(82.5)=83 인데 Python round(82.5)=82(짝수 반올림)다.
            #     그래서 폭을 여기서 직접 정해 파일로 굽고 위치도 같은 값으로 놓는다.
            lay_lines.append(f"    {n}:\n      name: {key}\n"
                             f"      x: {-2 * W + i * W + W / 2:g}\n      y: {top}\n")
            n += 1
        for key, (f, bx, by, sc) in (("portrait", D["portrait"]), ("nameplate", D["nameplate"])):
            # gen_npc_portrait_huds.py 가 초상화 블록을 NPC별 템플릿으로 재사용한다.
            # 이름표는 공용 이미지라 기존 키를 유지하고, 초상화 템플릿만 001_base 규약을 쓴다.
            k = f"npc_dialogue_{key}_{sid}"
            if key == "portrait":
                k = f"npc_dialogue_portrait_001_base_{sid}"
            fp, _, _, back = scaled_file("dialogue", f, sid, sc * s)
            # ★투명 왼쪽 여백은 BetterHud 가 잘라내고 x 에 되돌려 더한다 -> 그만큼 미리 빼둔다.
            #   ★축소 "후"의 여백을 재야 한다(원본 여백 x 배율 로 계산하면 반올림이 어긋난다).
            with Image.open(os.path.join(ART, "dialogue", GEN, os.path.basename(fp))) as im:
                box = im.split()[3].getbbox() or (0, 0, im.width, im.height)
            img.append(f"{k}:\n  type: single\n  file: {fp}\n"
                       f"  setting:\n    scale: {back}\n")
            if key == "portrait":
                # 매니페스트에 없는 NPC용 DEFAULT_PORTRAIT 폴백은 공용 키로 남긴다.
                # NPC별 생성 블록은 gen_npc_portrait_huds.py 가 이 템플릿을 교체한다.
                img.append(f"npc_dialogue_portrait_{sid}:\n  type: single\n  file: {fp}\n"
                           f"  setting:\n    scale: {back}\n")
            lay_lines.append(f"    {n}:\n      name: {k}\n"
                             f"      x: {px(bx, trim=round(box[0] * back)):g}\n"
                             f"      y: {top + round(by * s)}\n")
            n += 1
        lx, ly, lsc, lines, lw, sw = D["line"]
        nx, ny, nsc = D["name"]
        txt = (f"    1:\n      name: {FONT_DIALOGUE}\n      pattern: \"[string:npc_dialogue_text]\"\n"
               f"      color: \"#3D2840\"\n      x: {px(lx):g}\n      y: {top + round(ly * s)}\n"
               f"      scale: {round(lsc * s, 3)}\n      align: left\n      line-align: left\n"
               f"      line: {lines}\n      line-width: {round(lw * s)}\n"
               # ★split-width 는 상한이 아니라 "여기부터 줄바꿈을 노린다"이고 공백이 없으면
               #   1.25배까지 밀고 나간다. 그래서 가용폭/1.25 로 잡아 둔 값을 그대로 배율만 곱한다.
               f"      split-width: {round(sw * s)}\n      force-split: false\n"
               f"    2:\n      name: {FONT_DIALOGUE}\n      pattern: \"[string:npc_dialogue_name]\"\n"
               f"      color: \"#4A2D3D\"\n      x: {px(nx):g}\n      y: {top + round(ny * s)}\n"
               f"      scale: {round(nsc * s, 3)}\n      align: center\n")
        lay.append(f"npc_dialogue_layout_001_base_{sid}:  # {label} (x{s})\n  align: left\n  images:\n"
                   + "".join(lay_lines) + "  texts:\n" + txt)
        hud.append(f"npc_dialogue_001_base_{sid}:\n  tick: 1\n  layouts:\n    1:\n"
                   f"      name: npc_dialogue_layout_001_base_{sid}\n      gui:\n        x: 50\n        y: 100\n")
    emit("npc-dialogue-image.yml", "\n".join(img))
    emit("npc-dialogue-layout.yml", "\n".join(lay))
    emit("npc-dialogue-hud.yml", "\n".join(hud))


def build_buff():
    """버프 판 — 스탯 줄 수(1~3) x 크기 4단계 = 12 벌.

    구조:  요리 이름 / 남은시간 게이지 + mm:ss / 스탯 줄(아이콘 + 라벨 +수치)

    ★스탯 아이콘은 type: sequence 다. 리스너(barkan_buff_stat<N>)가 준 0.0~1.0 을
      round(값 x 마지막인덱스) 로 프레임 번호로 바꿔 8 종 중 하나를 그린다(BetterHud
      ImageType.SEQUENCE 바이트코드 확인). 그래서 조건문 없이 스탯별 아이콘이 갈린다.
    ★같은 png 를 두 정의가 참조하면 하나만 등록되므로, 줄마다 파일을 갈라 굽는다(suffix).
    """
    B = BUFF
    img, lay, hud = [], [], []
    place_h = PLACE["plate"][2]            # 지역바 판 높이 — 그 아래에 붙인다
    for (sid, label), s_ in zip(SIZES, SCALE_STATUS):
        W = round(B["plate_w"] * s_)
        base_x = W / 2 + MARGIN_X          # 지역바와 같은 왼쪽 정렬
        top = MARGIN_Y + round(place_h * s_) + B["gap"]

        # 판 3장
        for n in range(1, B["rows_max"] + 1):
            fname = f"buff-plate-{n}.png"
            with Image.open(os.path.join(ART, "status", fname)) as im:
                assert im.height == buff_plate_h(n), (
                    f"{fname} 높이 {im.height} != 계산값 {buff_plate_h(n)} — "
                    "build_status_hud.py 를 다시 돌릴 것")
            f, _, _, sc = scaled_file("status", fname, sid, s_)
            img.append(f"buff_plate_{n}_{sid}:\n  type: single\n  file: {f}\n"
                       f"  setting:\n    scale: {sc}\n")

        # 남은시간 게이지 (빈 홈 + 채움). 채움은 listener 가 비율만큼 잘라 그린다.
        empty, fill, bx, bw, bh = B["bar"]
        fe, _, _, sce = scaled_file("status", empty, sid, s_)
        img.append(f"buff_bar_empty_{sid}:\n  type: single\n  file: {fe}\n"
                   f"  setting:\n    scale: {sce}\n")
        ff, _, _, scf = scaled_file("status", fill, sid, s_)
        img.append(f"buff_bar_{sid}:\n  type: listener\n  file: {ff}\n"
                   f"  split: {round(bw * s_)}\n  split-type: left\n"
                   f"  setting:\n    scale: {scf}\n    listener:\n      class: barkan_buff_time\n")

        # 스탯 아이콘 sequence — 줄마다 한 벌(파일도 줄마다 따로)
        icon_scale = None
        for row in range(1, B["rows_max"] + 1):
            files = []
            for key in B["stats"]:
                fi, iw, ih, sci = scaled_file("status", f"icon-stat-{key}.png", sid, s_,
                                              base=(B["icon_h"], B["icon_h"]), suffix=f"-r{row}")
                files.append(fi)
                icon_scale = sci
            body = "".join(f"    - {f}\n" for f in files)
            img.append(f"buff_stat_icon_{row}_{sid}:\n  type: sequence\n  files:\n{body}"
                       f"  setting:\n    scale: {icon_scale}\n    listener:\n"
                       f"      class: barkan_buff_stat{row}\n")

        def ty(center_row, h):
            """판 좌표의 줄 중심 -> 그 높이 h 짜리 요소의 y (세로 가운데 맞춤)."""
            return round(top + center_row * s_ - round(h * s_) / 2)

        for n in range(1, B["rows_max"] + 1):
            images = [f"    1:\n      name: buff_plate_{n}_{sid}\n      x: {base_x:g}\n      y: {top}\n",
                      f"    2:\n      name: buff_bar_empty_{sid}\n"
                      f"      x: {base_x + round(bx * s_):g}\n      y: {ty(B['bar_y'], bh)}\n",
                      f"    3:\n      name: buff_bar_{sid}\n"
                      f"      x: {base_x + round(bx * s_):g}\n      y: {ty(B['bar_y'], bh)}\n"]
            k = 4
            for row in range(1, n + 1):
                center = B["row0"] + B["row_dy"] * (row - 1)
                images.append(f"    {k}:\n      name: buff_stat_icon_{row}_{sid}\n"
                              f"      x: {base_x + round(B['icon_x'] * s_):g}\n"
                              f"      y: {ty(center, B['icon_h'])}\n")
                k += 1
            texts = [f"    1:\n      name: {FONT_HUD_ORIGINAL}\n      pattern: \"[string:hud_buff_name]\"\n"
                     f"      color: \"{B['name_color']}\"\n"
                     f"      x: {base_x + round(B['name_x'] * s_):g}\n      y: {ty(B['name_y'], TEXT_H)}\n"
                     f"      scale: {round(TEXT_SCALE * s_, 3)}\n      align: left\n",
                     f"    2:\n      name: {FONT_HUD_ORIGINAL}\n      pattern: \"[string:hud_buff_time]\"\n"
                     f"      color: \"{B['time_color']}\"\n"
                     f"      x: {base_x + round(B['time_x'] * s_):g}\n      y: {ty(B['bar_y'], TEXT_H)}\n"
                     f"      scale: {round(TEXT_SCALE * s_, 3)}\n      align: right\n"]
            for row in range(1, n + 1):
                center = B["row0"] + B["row_dy"] * (row - 1)
                texts.append(f"    {row + 2}:\n      name: {FONT_HUD_ORIGINAL}\n"
                             f"      pattern: \"[string:hud_buff_stat{row}]\"\n"
                             f"      color: \"{B['stat_color']}\"\n"
                             f"      x: {base_x + round(B['text_x'] * s_):g}\n      y: {ty(center, TEXT_H)}\n"
                             f"      scale: {round(TEXT_SCALE * s_, 3)}\n      align: left\n")
            lay.append(f"barkan_buff_layout_{n}_{sid}:  # {label} (x{s_}) · 스탯 {n}줄\n"
                       f"  align: left\n  images:\n" + "".join(images) + "  texts:\n" + "".join(texts))
            hud.append(f"barkan_buff_{n}_{sid}:\n  tick: 20\n  layouts:\n    1:\n"
                       f"      name: barkan_buff_layout_{n}_{sid}\n      gui:\n        x: 0\n        y: 0\n")
    emit("buff-image.yml", "\n".join(img))
    emit("buff-layout.yml", "\n".join(lay))
    emit("buff-hud.yml", "\n".join(hud))


if __name__ == "__main__":
    import sys
    want_dialogue = "--dialogue" in sys.argv
    print("생성:")
    build_status()
    build_place()
    build_buff()
    if want_dialogue:
        build_dialogue()
    for (sid, label), a, b in zip(SIZES, SCALE_STATUS, SCALE_DIALOGUE):
        print(f"   {sid:3s} {label:6s} 상태/위치 x{a} ({round(124*a)}x{round(72*a)} / {round(150*a)}x{round(42*a)})"
              f"   대화창 x{b} (조각 {round(110*b)})")
    print(f"   버프 판 {BUFF['rows_max']}종 x {len(SIZES)}단계 "
          f"(높이 {[buff_plate_h(n) for n in range(1, BUFF['rows_max'] + 1)]})")
    print("★Java StatusHud.SIZES 의 id·순서가 위와 같은지 확인할 것.")
    print("★스탯 순서: " + " ".join(BUFF["stats"]) + "  (자바 BuffStats.STATS 와 같아야 한다)")
    if want_dialogue:
        print("\n★★대화창을 다시 만들었다 — 이어서 반드시 초상화를 복원할 것:")
        print("   python3 gen_npc_portrait_huds.py")
        print("   (안 돌리면 NPC별 초상화 정의 1160 벌이 기본 4벌로 남는다)")
    else:
        print("\n(대화창은 건드리지 않았다. 좌표를 바꿔야 하면 --dialogue,"
              " 그 뒤 gen_npc_portrait_huds.py 필수)")
