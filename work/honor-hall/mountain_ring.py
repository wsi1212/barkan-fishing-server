"""Deterministic mountain-ring terrain profile for the prod Honor Hall enclosure.

The inner face is deliberately sheer and 4 blocks thick. The outer face is a
noise-shaped mountain slope. No placement happens in this module.
"""
import math

CX, CZ = -769, -769
GROUND = -61
BOUND = 208


def _hash(i, seed):
    value = math.sin(i * 12.9898 + seed * 78.233) * 43758.5453
    return value - math.floor(value)


def _smooth(t):
    return t * t * (3 - 2 * t)


def _noise1(value, scale, seed):
    q = value / scale
    lo = math.floor(q)
    t = _smooth(q - lo)
    return _hash(lo, seed) * (1 - t) + _hash(lo + 1, seed) * t


def _noise2(x, z, scale, seed):
    qx, qz = x / scale, z / scale
    ix, iz = math.floor(qx), math.floor(qz)
    tx, tz = _smooth(qx - ix), _smooth(qz - iz)
    def value(a, b):
        return _hash(a * 73856093 + b * 19349663, seed)
    a = value(ix, iz) * (1 - tx) + value(ix + 1, iz) * tx
    b = value(ix, iz + 1) * (1 - tx) + value(ix + 1, iz + 1) * tx
    return a * (1 - tz) + b * tz


def profile(x, z):
    """Return (height above grass, innerDistance, outerDistance) or None."""
    dx, dz = x - CX, z - CZ
    # p=4 rounded square keeps the visual as one enclosing range, not a box wall.
    distance = (abs(dx) ** 4 + abs(dz) ** 4) ** 0.25
    tangent = dz if abs(dx) >= abs(dz) else dx
    inner = 164 + round((_noise1(tangent, 18, 17) - .5) * 9)
    outer = inner + 40 + round((_noise1(tangent + 29, 23, 31) - .5) * 8)
    if distance < inner or distance > outer:
        return None
    peak = 76 + round((_noise1(tangent - 11, 14, 47) - .5) * 20)
    inward = distance - inner
    if inward <= 4:
        height = peak
    else:
        slope = max(0.0, 1 - (inward - 4) / max(1, outer - inner - 4))
        height = peak * (slope ** .78)
        height += (_noise2(x, z, 9, 71) - .5) * 5 * slope
    return max(1, int(round(height))), inner, outer


def material_at(x, z, y, height, inner):
    """Natural strata with an intentionally dark, unclimbable inner face."""
    local = y - GROUND
    inward = ((abs(x - CX) ** 4 + abs(z - CZ) ** 4) ** .25) - inner
    h = _hash(x * 31 + y * 7 + z * 13, 97)
    # At the summit and outer face: dirt cap / grass; at the inner face: exposed rock.
    grassy = inward > 7 and local >= height - 2
    if local == height:
        if grassy:
            return 'minecraft:grass_block'
        return 'minecraft:deepslate' if h < .55 else 'minecraft:tuff'
    if grassy:
        return 'minecraft:dirt'
    if inward <= 7:
        if h < .55:
            return 'minecraft:deepslate'
        if h < .78:
            return 'minecraft:tuff'
        return 'minecraft:polished_andesite'
    if h < .62:
        return 'minecraft:stone'
    if h < .80:
        return 'minecraft:andesite'
    if h < .93:
        return 'minecraft:tuff'
    return 'minecraft:cobblestone'


def columns():
    for x in range(CX - BOUND, CX + BOUND + 1):
        for z in range(CZ - BOUND, CZ + BOUND + 1):
            result = profile(x, z)
            if result:
                yield x, z, result
