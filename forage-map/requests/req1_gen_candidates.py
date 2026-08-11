import json, math

pts = json.load(open('/tmp/req1_points.json'))
TARGET = 20
OVERSAMPLE = 26

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

xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
minx, maxx = min(xs), max(xs)
minz, maxz = min(zs), max(zs)

def shoelace(poly):
    a = 0
    for i in range(len(poly)):
        x1, z1 = poly[i]; x2, z2 = poly[(i + 1) % len(poly)]
        a += x1 * z2 - x2 * z1
    return abs(a) / 2

area = shoelace(pts)
spacing = math.sqrt(area / OVERSAMPLE)

candidates = []
z = minz
row = 0
while z <= maxz:
    x0 = minx + (spacing / 2 if row % 2 else 0)
    x = x0
    while x <= maxx:
        candidates.append((x, z))
        x += spacing
    z += spacing
    row += 1

inside_candidates = [(round(x), round(z)) for x, z in candidates if point_in_poly(x, z, pts)]
print("spacing", round(spacing, 1), "raw candidates", len(candidates), "inside", len(inside_candidates))
json.dump(inside_candidates, open('/tmp/req1_candidates.json', 'w'))
print(inside_candidates)
