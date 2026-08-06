#!/usr/bin/env python3
"""손에 드는 커스텀 아이템 텍스처에 검은 외곽선을 넣는다 — 실루엣 통일.

## 왜
낚싯대·작살·부품마다 외곽선이 제각각(실측: 같은 낚싯대끼리도 가장자리 어두운 비율
0%~28%)이라 손에 들면 배경에 따라 어떤 건 묻히고 어떤 건 또렷했다. 전부 같은 규칙의
외곽선을 둘러 실루엣을 통일한다.

## 안전장치 (★리소스팩은 git이 아니다 — 덮어쓰면 되돌릴 수 없다)
원본을 팩 **바깥** 백업 디렉터리에 먼저 복사하고, 항상 그 백업을 소스로 삼아 산출한다.
→ 여러 번 돌려도 선이 겹쳐 두꺼워지지 않고(멱등), `--restore` 로 원복도 된다.
2026-08-05 에 생성기가 납품 원본을 덮어써 수작업 수정본이 날아간 사고가 있었다.

## 두께
아트가 64px(게임 표시 16px의 4배)라 1px 선은 게임에서 0.25픽셀이라 안 보인다.
캔버스 크기에 비례해 `size/32`(64→2, 128→4, 256→8) = 게임상 0.5픽셀로 맞춘다.
실측 비교(64px에서 2/3/4) 결과 3 이상은 가느다란 낚싯대 살 사이를 메워 뭉갠다.

사용: python3 add_outline.py --dry-run    # 대상만 확인
      python3 add_outline.py              # 적용
      python3 add_outline.py --restore    # 백업으로 원복
"""
import argparse
import glob
import os
import shutil

from PIL import Image, ImageFilter

RP = os.path.expanduser("~/development/barkan-resourcepack")
TEX = os.path.join(RP, "assets/minecraft/textures/item")
BACKUP = os.path.expanduser("~/development/barkan-rp-backup/outline-src")

# 손에 드는 아이템만 = ItemIconModel 이 실제 ItemStack 에 붙이는 catalog_* 뿐이다.
#   (낚싯대·릴·줄·바늘·미끼·찌·작살·통발·재료)
# 제외: skill_*/tree_rail_* = 특성트리 GUI 전용 — 외곽선을 두르면 트리 배경 위에서 지저분해진다.
#       recipe_* = 제작 GUI 슬롯 아이콘(카테고리+등급 조합), 손에 들리지 않는다.
#       card/chip/casino/slot/emblem = GUI 전용.
PATTERNS = [
    "barkan_icon/catalog_*.png",
]

# ★임계값 두 개 + 바깥 판정, 세 조건을 모두 만족하는 자리에만 칠한다.
#   2026-08-06 실패 두 번에서 나온 규칙이다:
#   ① 반투명(발광 오라·반짝임)을 덮었더니 후광 둘레에 검은 테가 생겼다 → ALPHA_EMPTY
#   ② 형체 **내부**의 미세 투명 픽셀(디더링)까지 칠해져 구슬이 점박이가 됐다 → 바깥 판정
#      (테두리에서 투명 영역을 타고 도달 가능한 곳만 '바깥'이다)
#   ③ 흐릿한 오라가 외곽선을 유발해 금빛 소용돌이에 검은 후광이 생겼다 → ALPHA_SOLID 를
#      높여 **진하게 불투명한 픽셀만** 외곽선의 씨앗으로 삼는다. 오라에 둘러싸인 본체는
#      바깥과 맞닿지 않으므로 선이 안 생기고, 오라 자체가 배경과 분리해준다.
ALPHA_SOLID = 200
ALPHA_EMPTY = 24
OUTLINE = (0, 0, 0, 255)


def thickness(size):
    """★size/32(64→2, 256→8)로 잡았다가 256px 정교한 아이콘이 검은 덩어리가 됐다.
    캔버스가 커도 아트 디테일은 픽셀 단위라 두께가 같이 커지면 장식 사이를 메운다.
    실측 스윕: 256px 에서 4까지 멀쩡, 6부터 뭉침 / 64px 은 2가 적정.
    """
    return max(2, round(size / 64))     # 64→2, 128→2, 256→4, 512→8


def outside_mask(alpha, W, H):
    """테두리에서 투명 영역을 타고 도달할 수 있는 '바깥'. 형체 내부 구멍은 제외된다."""
    ap = alpha.load()
    out = bytearray(W * H)
    from collections import deque
    dq = deque()
    for x in range(W):
        for y in (0, H - 1):
            if ap[x, y] < ALPHA_EMPTY and not out[y * W + x]:
                out[y * W + x] = 1
                dq.append((x, y))
    for y in range(H):
        for x in (0, W - 1):
            if ap[x, y] < ALPHA_EMPTY and not out[y * W + x]:
                out[y * W + x] = 1
                dq.append((x, y))
    while dq:
        x, y = dq.popleft()
        for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= a < W and 0 <= b < H and not out[b * W + a] and ap[a, b] < ALPHA_EMPTY:
                out[b * W + a] = 1
                dq.append((a, b))
    return out


def add_outline(im, t):
    """진하게 불투명한 실루엣 **바깥**에만 칠한다 — 원본 픽셀은 절대 건드리지 않는다."""
    W, H = im.size
    alpha = im.getchannel("A")
    # 씨앗: 진한 불투명 픽셀만. MaxFilter 로 t 만큼 팽창(파이썬 루프보다 훨씬 빠르다).
    seed = alpha.point(lambda v: 255 if v >= ALPHA_SOLID else 0)
    grown = seed.filter(ImageFilter.MaxFilter(2 * t + 1))
    gp, sp, apx = grown.load(), seed.load(), alpha.load()
    outside = outside_mask(alpha, W, H)
    out = im.copy()
    op = out.load()
    for y in range(H):
        row = y * W
        for x in range(W):
            if not outside[row + x]:
                continue                    # 형체 내부 구멍 — 건드리지 않는다
            if apx[x, y] >= ALPHA_EMPTY:
                continue                    # 반투명 발광 — 원본 유지
            if gp[x, y] and not sp[x, y]:
                op[x, y] = OUTLINE
    return out


def targets():
    out = []
    for pat in PATTERNS:
        for p in sorted(glob.glob(os.path.join(TEX, pat))):
            if os.path.exists(p + ".mcmeta"):
                continue          # 애니메이션 텍스처는 프레임이 세로로 쌓여 있어 별도 처리 필요
            out.append(p)
    return out


def backup_path(p):
    return os.path.join(BACKUP, os.path.relpath(p, TEX))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("--thickness", type=int, default=None, help="고정 두께(기본: 크기 비례)")
    a = ap.parse_args()

    files = targets()
    if a.dry_run:
        by = {}
        for p in files:
            s = Image.open(p).size[0]
            by[s] = by.get(s, 0) + 1
        print(f"대상 {len(files)}개")
        for s, n in sorted(by.items()):
            print(f"  {s}px {n:4}개 → 두께 {a.thickness or thickness(s)}")
        print(f"백업 위치: {BACKUP}")
        return

    if a.restore:
        n = 0
        for p in files:
            b = backup_path(p)
            if os.path.exists(b):
                shutil.copy2(b, p)
                n += 1
        print(f"원복 {n}개")
        return

    done = 0
    for p in files:
        b = backup_path(p)
        os.makedirs(os.path.dirname(b), exist_ok=True)
        if not os.path.exists(b):
            shutil.copy2(p, b)          # 첫 실행에서만 원본 보존
        im = Image.open(b).convert("RGBA")   # ★항상 백업(원본)에서 생성 → 멱등
        t = a.thickness or thickness(im.size[0])
        add_outline(im, t).save(p)
        done += 1
    print(f"외곽선 적용 {done}개 (원본 보존: {BACKUP})")


if __name__ == "__main__":
    main()
