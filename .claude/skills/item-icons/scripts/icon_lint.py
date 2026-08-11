#!/usr/bin/env python3
"""아이템 아이콘 객관 린트 — 배포 전 통과 게이트. exit code = 경고 수.

lint_sprite.py(채집물용)와 별개인 이유: 아이콘은 '인벤토리 슬롯 회색(#8B8B8B) 위 18px'
이라는 고정 무대가 있다. 그래서 슬롯 대비/대각 구도/타일 점유율 같은 아이콘 전용
규칙이 붙는다.

사용: python3 icon_lint.py <png...> [--category tool|prop|badge] [--allow-semialpha N]
"""
import sys, colorsys, math
from PIL import Image

SLOT_LUMA = 139  # #8B8B8B


def _luma(p):
    return 0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]


def lint(path, category="prop", allow_semialpha=0):
    im = Image.open(path).convert("RGBA")
    W, H = im.size
    warns = []
    if W != H or W not in (16, 32):
        warns.append(f"크기 {W}x{H} — 아이콘은 16x16(예외적으로 32x32)")
    px = [(x, y, im.getpixel((x, y))) for y in range(H) for x in range(W)]
    op = [(x, y, p) for x, y, p in px if p[3] == 255]
    semi = [(x, y, p) for x, y, p in px if 0 < p[3] < 255]
    if not op:
        return [f"{path}: 불투명 픽셀 없음"]

    # 1. 색 수 (재질당 램프 4~5색 원칙)
    colors = {p[:3] for _, _, p in op}
    if len(colors) > 14:
        warns.append(f"불투명 색 {len(colors)}종 — 램프 이탈 의심(재질당 4~5색, 총 ~14 이하)")
    # 2. 퓨어 블랙/화이트 외곽선 금지
    if (0, 0, 0) in colors:
        warns.append("퓨어 블랙(#000) 사용 — 램프의 어두운 색으로 대체")
    # 3. 고아 픽셀 (스파클 1~2개는 의도일 수 있어 3개부터 경고)
    opset = {(x, y) for x, y, _ in op}
    orphans = [c for c in opset if not any((c[0]+dx, c[1]+dy) in opset
               for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0))]
    if len(orphans) > 2:
        warns.append(f"고아 픽셀 {len(orphans)}개 — 스파클 이상의 잡음")
    # 4. 타일 점유율 — 아이콘은 타일을 '차야' 한다
    xs = [x for x, _, _ in op]; ys = [y for _, y, _ in op]
    span = (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
    if span[0] < W * 0.56 or span[1] < H * 0.56:
        warns.append(f"바운딩 {span[0]}x{span[1]} — 타일 대비 왜소(≥{int(W*0.56)}px 권장)")
    occ = len(op) / (W * H)
    lo, hi = (0.10, 0.55) if category == "tool" else (0.18, 0.80)
    if not (lo <= occ <= hi):
        warns.append(f"점유율 {occ:.0%} — {category} 권장 {lo:.0%}~{hi:.0%}")
    # 5. 슬롯 회색에 묻힘 검사 (아이콘 전용 핵심 게이트)
    blend = 0
    for _, _, p in op:
        h, s, v = colorsys.rgb_to_hsv(p[0]/255, p[1]/255, p[2]/255)
        if abs(_luma(p) - SLOT_LUMA) < 16 and s < 0.14:
            blend += 1
    if blend / len(op) > 0.30:
        warns.append(f"불투명 픽셀 {blend/len(op):.0%}가 슬롯 회색(#8B8B8B)과 비슷 — GUI에서 묻힘")
    # 6. 대각 구도 (도구류) — 주성분 축이 25~65°인지
    if category == "tool":
        n = len(op)
        mx = sum(xs) / n; my = sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs) / n
        syy = sum((y - my) ** 2 for y in ys) / n
        sxy = sum((x - mx) * (my - y) for x, y, _ in op) / n  # y축 뒤집어 수학 좌표로
        ang = abs(math.degrees(0.5 * math.atan2(2 * sxy, sxx - syy)))
        if not (22 <= ang <= 68):
            warns.append(f"주축 {ang:.0f}° — 도구는 ↗ 대각(25~65°) 관례")
    # 7. 반투명 감사 (알파 사고 예방 — 가구 텍스처 깨짐=알파 교훈)
    if len(semi) > allow_semialpha:
        warns.append(f"반투명 픽셀 {len(semi)}개(허용 {allow_semialpha}) — 글로우 외 반투명 금지")
    return warns


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cat = "prop"; allow = 0
    for i, a in enumerate(sys.argv):
        if a == "--category":
            cat = sys.argv[i + 1]
        if a == "--allow-semialpha":
            allow = int(sys.argv[i + 1])
    total = 0
    for p in args:
        ws = lint(p, cat, allow)
        total += len(ws)
        print(f"{'✓' if not ws else '✗'} {p}")
        for w in ws:
            print(f"   - {w}")
    sys.exit(total)
