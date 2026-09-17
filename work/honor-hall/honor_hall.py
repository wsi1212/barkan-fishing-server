"""Approved honor_hall blueprint v02, quartz temple garden.

World honor_hall ONLY. Origin (-55,64,-56); floor top block Y66.
Four 3x3x2 staff plinths; 6 provisional exhibition plinths per wing.
Sparse deterministic recipe: no air clearing, no entities, no player data.
"""
import math

ORIGIN = (-55, 64, -56)
F = 66
STAFF = [(x, z) for x in (-7, 4) for z in (-7, 4)]
EXHIBIT = [(x, z) for x in (-45, -36, -27, 26, 35, 44) for z in (-7, 5)]
EXHIBIT += [(x, z) for z in (-46, -37, -28) for x in (-7, 5)]


def build(api):
    s = api.create(111, 30, 110)

    def put(x, y, z, material):
        api.set(s, (x + 55, y - 64, z + 56), material)

    def cub(x1, y1, z1, x2, y2, z2, material):
        api.fill(s, (x1 + 55, y1 - 64, z1 + 56),
                 (x2 + 55, y2 - 64, z2 + 56), material)

    def column(x, z):
        # Wider base/capital on a two-block fluted shaft.
        cub(x - 1, F + 1, z - 1, x + 2, F + 1, z + 2, 'quartz_bricks')
        cub(x, F + 2, z, x + 1, F + 10, z + 1, 'quartz_pillar[axis=y]')
        cub(x - 1, F + 11, z - 1, x + 2, F + 11, z + 2, 'chiseled_quartz_block')
        cub(x - 1, F + 12, z - 1, x + 2, F + 12, z + 2, 'smooth_quartz')

    def plinth(x, z):
        # EXACT overall footprint 3x3, height 2; top is ready for a statue.
        cub(x, F + 1, z, x + 2, F + 1, z + 2, 'chiseled_quartz_block')
        cub(x, F + 2, z, x + 2, F + 2, z + 2, 'smooth_quartz')

    # 1. Foundation + patterned quartz pavement, matching the approved cross plan.
    footprint = set()
    for x in range(-53, 53):
        for z in range(-54, 52):
            horizontal = -14 <= z <= 13
            vertical = -14 <= x <= 13 and z <= 36
            circle = x*x + z*z <= 18*18
            approach = abs(x) <= 4 and z >= 37
            if horizontal or vertical or circle or approach:
                footprint.add((x, z))
    for x, z in sorted(footprint):
        # Narrow southern approach meets the existing grass at Y64.
        if z >= 43:
            put(x, 64, z, 'smooth_quartz' if abs(x) < 4 else 'quartz_bricks')
            continue
        cub(x, 65, z, x, F, z, 'smooth_quartz')
        radius = math.hypot(x, z)
        rim = any((x+dx, z+dz) not in footprint for dx,dz in [(1,0),(-1,0),(0,1),(0,-1)])
        axial_trim = (abs(z) == 4 and abs(x) >= 18) or (abs(x) == 4 and abs(z) >= 18)
        if rim or 16 <= radius < 17 or axial_trim:
            put(x, F, z, 'quartz_bricks')
        elif (x % 6 == 0 and z % 6 == 0) and radius > 18:
            put(x, F, z, 'chiseled_quartz_block')
        else:
            put(x, F, z, api.pick(x, F, z, [(8,'smooth_quartz'),(2,'quartz_block')], scale=6, seed=19))

    # 2. South entrance stairs. No vertical lip from the grass to the forecourt.
    for z in range(37, 43):
        level = 65 if z >= 40 else 66
        width = 16 if z >= 40 else 15
        for x in range(-width, width):
            if level == 66:
                put(x,65,z,'smooth_quartz')
            put(x,level,z,'smooth_quartz_stairs[facing=north,half=bottom]' if z in (39,42) else 'smooth_quartz')

    # 3. Three colonnaded exhibition galleries.
    for x in (-49,-41,-33,-25,24,32,40,48):
        for z in (-12,10):
            column(x,z)
    for z in (-50,-42,-34,-26):
        for x in (-12,10):
            column(x,z)
    for x1,x2 in [(-51,-23),(23,51)]:
        for z in (-13,9):
            cub(x1,F+13,z,x2,F+13,z+3,'quartz_bricks')
            cub(x1,F+14,z,x2,F+14,z+3,'smooth_quartz_slab[type=bottom]')
            for x in range(x1+1,x2,3):
                put(x,F+12,z+1,'quartz_slab[type=top]')
    for x in (-13,9):
        cub(x,F+13,-52,x+3,F+13,-23,'quartz_bricks')
        cub(x,F+14,-52,x+3,F+14,-23,'smooth_quartz_slab[type=bottom]')
        for z in range(-49,-23,3):
            put(x+1,F+12,z,'quartz_slab[type=top]')

    # 4. Recessed terminal walls: smooth panels in a fluted quartz frame.
    # transform(u, depth) maps the common north-facing module to each wing.
    transforms = [lambda u,d:(u,-53+d),lambda u,d:(-52+d,u),lambda u,d:(51-d,u)]
    for transform in transforms:
        for u in range(-13,14):
            for y in range(F+1,F+14):
                edge = u in (-13,13) or y in (F+1,F+12,F+13)
                pilaster = u in (-9,-8,-1,0,7,8)
                depth = 1 if edge or pilaster else 0
                for d in range(depth+1):
                    x,z=transform(u,d)
                    material='quartz_bricks' if y in (F+1,F+12) else 'quartz_pillar[axis=y]' if pilaster else 'smooth_quartz'
                    put(x,y,z,material)
        for u in range(-14,15):
            for d in (0,1,2):
                x,z=transform(u,d)
                put(x,F+14,z,'smooth_quartz_slab[type=bottom]')
        for u in (-5,4):
            x,z=transform(u,1)
            put(x,F+8,z,'chiseled_quartz_block')
            x,z=transform(u,2)
            put(x,F+8,z,'quartz_slab[type=top]')
            put(x,F+9,z,'lantern[hanging=false]')

    # 5. Monumental southern portico with a stepped triangular pediment.
    for x in (-12,-5,3,10):
        column(x,32)
    cub(-14,F+13,30,13,F+13,35,'quartz_bricks')
    for i in range(7):
        y=F+14+i
        lo,hi=-14+2*i,13-2*i
        cub(lo,y,30,hi,y,35,'smooth_quartz')
        for z in range(30,36):
            put(lo,y,z,'smooth_quartz_stairs[facing=east,half=bottom]')
            put(hi,y,z,'smooth_quartz_stairs[facing=west,half=bottom]')
    cub(-2,F+16,35,1,F+17,35,'chiseled_quartz_block')
    for x in range(-12,13,3):
        put(x,F+12,35,'quartz_slab[type=top]')
    for x in (-8,7):
        put(x,F+12,33,'lantern[hanging=true]')

    # 6. Low meadow beds, leaving a six-block cross and open outer ring.
    for bx in (-11,3):
        for bz in (-11,3):
            for x in range(bx,bx+8):
                for z in range(bz,bz+8):
                    if x in (bx,bx+7) and z in (bz,bz+7):
                        continue
                    put(x,65,z,'dirt')
                    put(x,F,z,'grass_block')
                    near_plinth=any(px-1<=x<=px+3 and pz-1<=z<=pz+3 for px,pz in STAFF)
                    if not near_plinth:
                        val=api.hash01(x,0,z,seed=73)
                        if val < .23:
                            put(x,F+1,z,'short_grass')
                        elif val < .32:
                            put(x,F+1,z,'oxeye_daisy')
                        elif val < .37:
                            put(x,F+1,z,'azure_bluet')
    # A few low shrubs against the OUTER bed edges, never in statue sightlines.
    for x,z in [(-10,-9),(-9,-10),(9,-10),(10,-9),(-10,9),(-9,10),(9,10),(10,9)]:
        put(x,F+1,z,'oak_leaves[persistent=true]')
    for x,z in STAFF:
        plinth(x,z)
        # Two stepping stones link each pedestal to the center cross path.
        for zz in (z+3,z+4) if z<0 else (z-1,z-2):
            for xx in range(x,x+3):
                put(xx,F,zz,'smooth_quartz')
                # Clear our own generated planting only; no world-air sweep.
                api.unset(s,(xx+55,F+1-64,zz+56))
    for x,z in EXHIBIT:
        plinth(x,z)

    # 7. Low quartz garden benches and inset lighting, with broad paths open.
    for x in (-10,7):
        for z in (-14,13):
            for xx in range(x,x+3):
                put(xx,F+1,z,'quartz_stairs[facing='+('north' if z<0 else 'south')+',half=bottom]')
    for x,z in [(-13,-8),(13,-8),(-13,8),(13,8)]:
        put(x,F+1,z,'chiseled_quartz_block')
        put(x,F+2,z,'lantern[hanging=false]')
    for x in (-45,-36,-27,27,36,45):
        for z in (-4,4):
            put(x,F,z,'sea_lantern')
    for z in (-46,-37,-28,22,28):
        for x in (-4,4):
            put(x,F,z,'sea_lantern')
    return s
