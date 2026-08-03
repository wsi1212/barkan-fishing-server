#!/usr/bin/env python3
"""퀘스트 마커 글리프 (! = 수락 가능 / ? = 완료 제출) — NPC 머리 위 표시용.

왜 리소스팩 글리프인가
  텍스트 문자 '!'/'?'는 폰트 획이 얇고, 이 프로젝트는 볼드(&l) 전면 금지라 굵게 만들
  방법이 없다. 또 "위가 굵고 아래로 갈수록 좁아지는" 게임형 마커 실루엣은 글꼴로는
  불가능하다 → 비트맵 글리프로 직접 그린다.

디자인 스펙
  실루엣   위가 넓고 아래로 갈수록 좁아지는 테이퍼(원근감). ! 는 쐐기형 몸통,
           ? 는 굵은 상단 후크 → 좁아지는 목 → 점
  팔레트   금색 3단 램프(하이라이트/본체/그늘) + 짙은 갈색 외곽선 1px
           → 밝은 배경(하늘·눈)에서도 실루엣이 죽지 않게 외곽선이 필수
  해상도   16x24 논리 → 4배(64x96)로 렌더해 계단 없이 선명하게
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

W, H = 16, 24


def _canvas():
    return [[CLEAR for _ in range(W)] for _ in range(H)]


def _rowspan(g, y, x0, x1, c):
    for x in range(max(0, x0), min(W - 1, x1) + 1):
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


def save(g, name):
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
