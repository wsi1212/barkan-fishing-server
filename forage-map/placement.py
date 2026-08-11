"""배치 요청(다각형+품목+개수)을 실제 좌표 후보로 바꾸는 공용 모듈.
매번 이 함수들을 가져다 쓸 것 — 예전처럼 반올림된 순수 격자를 그대로 심지 말 것
(사용자 피드백: 너무 규칙적/기계적으로 보임 → 반드시 노이즈 적용)."""
import math
import random


def point_in_poly(x, z, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, zi = poly[i]
        xj, zj = poly[j]
        if ((zi > z) != (zj > z)) and (x < (xj - xi) * (z - zi) / (zj - zi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def shoelace_area(poly):
    a = 0
    for i in range(len(poly)):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % len(poly)]
        a += x1 * z2 - x2 * z1
    return abs(a) / 2


def generate_candidates(poly, oversample_count, jitter_frac=0.45, seed=0):
    """poly 내부에 oversample_count개 안팎의 후보 (x,z)를 뿌린다.
    브릭패턴 격자 + 셀 크기의 jitter_frac만큼 무작위 오프셋 → 사람이 흩뿌린 것처럼 보이게.
    최소 간격 보장을 위해 격자를 쓰되, jitter로 기계적인 느낌을 없앤다."""
    rng = random.Random(seed)
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    minx, maxx = min(xs), max(xs)
    minz, maxz = min(zs), max(zs)
    area = shoelace_area(poly)
    spacing = math.sqrt(area / max(1, oversample_count))

    candidates = []
    row = 0
    z = minz
    while z <= maxz:
        x0 = minx + (spacing / 2 if row % 2 else 0)
        x = x0
        while x <= maxx:
            jx = x + rng.uniform(-spacing * jitter_frac, spacing * jitter_frac)
            jz = z + rng.uniform(-spacing * jitter_frac, spacing * jitter_frac)
            candidates.append((jx, jz))
            x += spacing
        z += spacing
        row += 1

    inside = [(round(x), round(z)) for x, z in candidates if point_in_poly(x, z, poly)]
    rng.shuffle(inside)
    return inside
