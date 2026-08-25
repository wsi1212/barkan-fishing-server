#!/usr/bin/env python3
"""퀘스트 마커 글리프 (! = 수락 가능 / ? = 완료 제출 / … = 진행 중) — NPC 머리 위 표시용.

왜 리소스팩 글리프인가
  텍스트 문자 '!'/'?'는 폰트 획이 얇고, 이 프로젝트는 볼드(&l) 전면 금지라 굵게 만들
  방법이 없다. 또 "위가 굵고 아래로 갈수록 좁아지는" 게임형 마커 실루엣은 글꼴로는
  불가능하다 → 비트맵 글리프로 직접 그린다.

디자인 스펙
  실루엣   위가 넓고 아래로 갈수록 좁아지는 테이퍼(원근감). ! 는 쐐기형 몸통,
           ? 는 굵은 상단 후크 → 좁아지는 목 → 점
  팔레트   !/? 는 금색 3단 램프, … 는 흰색 3단 램프(하이라이트/본체/그늘)
           + 짙은 외곽선 1px → 밝은 배경(하늘·눈)에서도 실루엣이 죽지 않게 외곽선이 필수
  해상도   논리 캔버스 → 4배로 렌더해 계단 없이 선명하게. 세로는 24행 고정(폰트
           height/ascent 를 셋이 공유), 가로는 글리프마다 다르다 — … 는 점 셋을
           떼어놓을 자리가 필요해 25폭이다(16폭에 3개는 물리적으로 안 들어간다).
  ★볼드 금지 정책과 무관 (텍스트가 아니라 이미지)
"""
import pathlib

from PIL import Image

RP = pathlib.Path.home() / 'development/barkan-resourcepack'
OUT = RP / 'assets/barkan/textures/font/gui'
SCALE = 4                      # 논리 픽셀 → 실제 픽셀 배율

# 금색 램프: 그늘 / 본체 / 하이라이트, 그리고 외곽선
SHADE = (176, 116, 20, 255)
BODY = (240, 190, 48, 255)
LIGHT = (255, 232, 132, 255)
EDGE = (74, 44, 8, 255)
CLEAR = (0, 0, 0, 0)

# 진행 중(…)은 흰색 램프 — 금색 !/? 가 "지금 눌러라"는 신호라서, 할 일이 없는
# 진행 중까지 금색이면 정작 눌러야 하는 마커가 마을 전체에서 묻힌다.
DOT_SHADE = (158, 166, 180, 255)
DOT_BODY = (226, 232, 242, 255)
DOT_LIGHT = (255, 255, 255, 255)
DOT_EDGE = (46, 54, 68, 255)

W, H = 16, 24                   # !/? 기본 캔버스. … 는 자기 폭을 따로 쓴다(PROGRESS_W)


def _canvas(w=None, h=None):
    return [[CLEAR for _ in range(w or W)] for _ in range(h or H)]


def _dims(g):
    """캔버스 크기는 그리드에서 읽는다 — 글리프마다 폭이 다르므로 전역 W를 믿지 않는다."""
    return len(g[0]), len(g)


def _rowspan(g, y, x0, x1, c):
    w, _ = _dims(g)
    for x in range(max(0, x0), min(w - 1, x1) + 1):
        g[y][x] = c


def _taper_body(g, rows):
    """rows = [(y, x0, x1)] 몸통 스팬. 각 행 안에서 좌→우로 하이라이트/본체/그늘 배분."""
    for y, x0, x1 in rows:
        w = x1 - x0 + 1
        for x in range(x0, x1 + 1):
            rel = (x - x0) / max(1, w - 1)
            g[y][x] = LIGHT if rel < 0.34 else (BODY if rel < 0.72 else SHADE)


def _outline(g):
    """불투명 픽셀의 바깥 테두리에 1px 외곽선. 대각선 포함(8방향)."""
    W, H = _dims(g)
    solid = [[g[y][x][3] > 0 for x in range(W)] for y in range(H)]
    for y in range(H):
        for x in range(W):
            if solid[y][x]:
                continue
            touch = False
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and solid[ny][nx]:
                        touch = True
                        break
                if touch:
                    break
            if touch:
                g[y][x] = EDGE


# ── 레이아웃 규약 (1차 검수에서 나온 결함 3개를 구조로 막는다) ────────────────
#   ① 몸통은 y=1에서 시작한다 — y=0에서 시작하면 위쪽 외곽선을 그릴 행이 없어
#      마커 상단만 테두리가 빠진다.
#   ② 모든 폭은 홀수, 중심은 x=CENTER 고정 — 짝수 폭을 섞으면 중심이 x.5로 밀려
#      몸통 하단이 점보다 왼쪽으로 치우친다(1차 결함).
#   ③ 몸통 끝과 점 사이에 최소 4행을 비운다 — 외곽선이 각각 1행을 먹으므로
#      간격이 2행이면 테두리끼리 붙어 '점과 몸통이 이어진' 것처럼 보인다.
CENTER = 7
BODY_Y0 = 1
DOT_Y = (18, 20)          # 몸통(…13) 과 4행 간격


def _centered(y, w):
    """중심 x=CENTER에 맞춘 홀수 폭 스팬."""
    if w % 2 == 0:
        w += 1
    return (y, CENTER - w // 2, CENTER + w // 2)


def _dot(g):
    """아래 점 — 몸통과 같은 중심(x=CENTER), 폭 3."""
    _taper_body(g, [_centered(y, 3) for y in range(DOT_Y[0], DOT_Y[1] + 1)])


def build_bang():
    """! — 위가 넓은 쐐기 몸통 + 아래 점. 폭 7 → 3 (홀수만, 중심 고정)."""
    g = _canvas()
    widths = [7, 7, 7, 7, 7, 5, 5, 5, 5, 3, 3, 3, 3]     # y=1..13
    _taper_body(g, [_centered(BODY_Y0 + i, w) for i, w in enumerate(widths)])
    _dot(g)
    _outline(g)
    return g


def build_question():
    """? — 굵은 상단 후크 → 좁아지는 목 → 점. 목/점은 중심 x=CENTER 고정."""
    g = _canvas()
    # 상단 후크: 넓고 굵게 (위가 큰 느낌의 핵심). y=1에서 시작해 위 테두리 공간 확보
    hook = [
        (1, 4, 11), (2, 3, 12), (3, 2, 13),
        (4, 2, 5), (4, 10, 13),
        (5, 2, 5), (5, 10, 13),
        (6, 3, 5), (6, 10, 13),
        (7, 9, 13),
        (8, 8, 12),
    ]
    _taper_body(g, hook)
    # 목: 후크에서 내려오며 좁아진다 (폭 5 → 3, 중심 고정)
    neck_w = [5, 5, 3, 3, 3]                              # y=9..13
    _taper_body(g, [_centered(9 + i, w) for i, w in enumerate(neck_w)])
    _dot(g)
    _outline(g)
    return g


# ── … (진행 중) 레이아웃 ────────────────────────────────────────────────────────
#   점 사이는 «빈 칸 5개» 를 둔다. 외곽선이 점마다 좌우 1칸씩 먹으므로 빈 칸 5개 =
#   실제로 눈에 보이는 투명 간격 3칸. (빈 칸 2개면 외곽선끼리 맞닿아 한 덩어리가 된다.)
#   ★2026-08-26 사고: 중심 2·7·12 · 반폭 2 로 잡아 x 0~4 / 5~9 / 10~14 가 서로
#     닿았고, 결과물은 점 셋이 아니라 16x6 통짜 슬래브였다. 폭 16 에 외곽선까지
#     붙은 점 3개는 물리적으로 안 들어간다 → 캔버스를 25폭으로 넓혔다.
PROGRESS_W = 27
DOT_W = 5                  # 점 지름(홀수 — 중심이 정수여야 음영이 안 틀어진다)
DOT_X0 = (1, 11, 21)       # 각 점의 왼쪽 끝. 간격 = 5칸(외곽선 2 + 진짜 여백 3)
DOT_Y0 = 9                 # 점 윗행. 24행 캔버스의 시각 중심에 맞춘다


def _ball(g, x0, y0):
    """구체형 점 하나 — 가로 램프(_taper_body)가 아니라 좌상단 광원 기준 방사 음영.

    가로 램프를 쓰면 점이 세로 줄무늬 3개로 보인다(1차 결함). 점은 공이므로
    빛은 좌상단에서 오고 그늘은 우하단에 깔려야 둥글게 읽힌다.
    """
    r = DOT_W // 2
    for dy in range(DOT_W):
        # 위·아래 끝행은 모서리를 깎아 사각형이 아닌 원으로 만든다
        inset = 1 if dy in (0, DOT_W - 1) else 0
        for dx in range(inset, DOT_W - inset):
            tone = (dx - r) + (dy - r)
            g[y0 + dy][x0 + dx] = DOT_LIGHT if tone <= -2 else (DOT_BODY if tone <= 1 else DOT_SHADE)


def _round_outline(g, x0, y0):
    """점 외곽선의 계단 모서리를 깎아 사각형이 아닌 원으로 만든다.

    _outline 은 8방향 팽창이라 5x5 점을 감싸면 결과가 7x7 «둥근 사각형» 이 된다.
    바깥 모서리 8칸을 지워야 비로소 7px 원(..###.. / .#####. / #######) 이 된다.
    """
    for dx, dy in ((-1, 0), (DOT_W, 0), (-1, DOT_W - 1), (DOT_W, DOT_W - 1),
                   (0, -1), (DOT_W - 1, -1), (0, DOT_W), (DOT_W - 1, DOT_W)):
        g[y0 + dy][x0 + dx] = CLEAR


def build_progress():
    """… — 같은 높이에 떨어져 놓인 둥근 점 3개. 진행 중이지만 지금 할 일은 없다는 표시."""
    g = _canvas(PROGRESS_W)
    for x0 in DOT_X0:
        _ball(g, x0, DOT_Y0)
    # 외곽선 색만 흰 점용으로 바꿔 끼운다(금색 마커의 갈색 테두리는 흰 점에 안 어울린다)
    global EDGE
    old, EDGE = EDGE, DOT_EDGE
    try:
        _outline(g)
    finally:
        EDGE = old
    for x0 in DOT_X0:
        _round_outline(g, x0, DOT_Y0)
    return g


def save(g, name):
    W, H = _dims(g)
    img = Image.new('RGBA', (W, H), CLEAR)
    for y in range(H):
        for x in range(W):
            img.putpixel((x, y), g[y][x])
    img = img.resize((W * SCALE, H * SCALE), Image.NEAREST)
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    img.save(p)
    return p


if __name__ == '__main__':
    print(save(build_bang(), 'quest_bang.png'))
    print(save(build_question(), 'quest_question.png'))
    print(save(build_progress(), 'quest_progress.png'))
