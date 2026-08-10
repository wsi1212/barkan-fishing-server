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

# ★손에 드는 generated 아이템은 반투명 픽셀을 절대 보존하지 않는다.
# Minecraft는 layer0의 반투명 가장자리도 얇은 3D 옆면으로 만들어, 비스듬히 들면
# 검은 '구멍/찌꺼기'로 보인다. 먼저 원화를 1-bit alpha로 고정하고 그 마스크에서만
# 외곽선을 만든다. 후광·연기 같은 반투명 FX는 인벤 손아이콘이 아니라 별도 애니/GUI
# 텍스처로만 허용한다.
ALPHA_CUTOFF = 128
ALPHA_EMPTY = 1
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


def binary_alpha(im):
    """손에 드는 아이콘의 알파를 0/255만 남긴다.

    반투명 프린지를 남겨 둔 채 외곽선을 칠하면 해당 픽셀이 '이미 내용물'로 취급돼
    검은 테두리가 끊긴다. 그 끊긴 반투명 조각이 인게임에서 검은 압출면/투명 구멍이
    되는 것이므로, outline 이전에 반드시 이 단계가 선행돼야 한다.
    """
    out = im.convert("RGBA").copy()
    a = out.getchannel("A").point(lambda v: 255 if v >= ALPHA_CUTOFF else 0)
    out.putalpha(a)
    return out


def add_outline(im, t):
    """이진 실루엣 **바깥**에만 검은 테두리를 칠한다."""
    im = binary_alpha(im)
    W, H = im.size
    alpha = im.getchannel("A")
    # 씨앗은 이미 0/255인 불투명 실루엣 전체다.
    seed = alpha
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
                continue
            if gp[x, y] and not sp[x, y]:
                op[x, y] = OUTLINE
    # 회귀 방지: generated 아이템의 최종 PNG에는 중간 알파가 단 하나도 있으면 안 된다.
    assert not any(0 < a < 255 for a in out.getchannel("A").getdata())
    return out


def targets():
    out = []
    for pat in PATTERNS:
        for p in sorted(glob.glob(os.path.join(TEX, pat))):
            if os.path.exists(p + ".mcmeta"):
                continue          # 애니메이션 텍스처는 프레임이 세로로 쌓여 있어 별도 처리 필요
            out.append(p)
    return out


def is_new_art(live, backup, fixed_t=None):
    """live 가 backup 의 '외곽선 결과'가 아니면 새 그림으로 본다.

    mtime 비교로는 못 가른다 — 외곽선을 입히면 live 가 항상 backup 보다 새 파일이 된다.
    그래서 backup 으로 결과를 다시 만들어 live 와 바이트가 같은지 본다(같으면 파생물).
    """
    try:
        src = Image.open(backup).convert("RGBA")
        cur = Image.open(live).convert("RGBA")
    except Exception:
        return False
    if src.size != cur.size:
        return True
    t = fixed_t or thickness(src.size[0])
    return add_outline(src, t).tobytes() != cur.tobytes()


def backup_path(p):
    return os.path.join(BACKUP, os.path.relpath(p, TEX))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("--only", action="append", default=[],
                    help="상대 경로 또는 파일명으로 대상 제한(예: barkan_icon/catalog_rod_x.png)")
    ap.add_argument("--thickness", type=int, default=None, help="고정 두께(기본: 크기 비례)")
    a = ap.parse_args()

    files = targets()
    if a.only:
        wanted = set(a.only)
        files = [p for p in files if os.path.relpath(p, TEX) in wanted or os.path.basename(p) in wanted]
        if not files:
            ap.error("--only와 일치하는 텍스처가 없습니다")
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

    done = refreshed = 0
    for p in files:
        b = backup_path(p)
        os.makedirs(os.path.dirname(b), exist_ok=True)
        if not os.path.exists(b):
            shutil.copy2(p, b)          # 첫 실행에서만 원본 보존
        elif is_new_art(p, b, a.thickness):
            # ★새 그림이 들어왔으면 백업을 갱신한다. 안 하면 낡은 백업에서 다시 만들어
            #   **방금 넣은 새 아트를 옛 그림으로 되돌려 버린다**(2026-08-11 실제 사고:
            #   초보자 낚싯대·작살이 조용히 옛 아이콘으로 복구됐다).
            shutil.copy2(p, b)
            refreshed += 1
        im = Image.open(b).convert("RGBA")   # ★항상 백업(원본)에서 생성 → 멱등
        t = a.thickness or thickness(im.size[0])
        add_outline(im, t).save(p)
        done += 1
    print(f"외곽선 적용 {done}개"
          + (f" · 새 그림으로 백업 갱신 {refreshed}개" if refreshed else "")
          + f" (원본 보존: {BACKUP})")


if __name__ == "__main__":
    main()
