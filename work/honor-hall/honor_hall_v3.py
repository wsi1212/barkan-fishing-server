"""Voxelized approved 3D preview. Origin (-96,63,-96), world honor_hall.

Base plane in preview = world feet Y65. Surface of temple = feet Y67.
Only block-grid rounding and Minecraft stairs/slabs replace fractional geometry.
Forest is planted separately with native tree generators, never cube crowns.
"""
import json
import math
from pathlib import Path

ORIGIN=(-96,63,-96)
WORLD='honor_hall'


def build(api):
    s=api.create(193,43,193)
    records=json.loads(Path(__file__).with_name('approved_geometry.json').read_text())
    pal={'ivory':'smooth_quartz','marble':'quartz_block','shadow-stone':'polished_andesite',
         'jade':'waxed_oxidized_cut_copper','deep-jade':'dark_prismarine','gold':'gold_block',
         'lawn':'grass_block','leaf':'oak_leaves[persistent=true]','leaf-light':'azalea_leaves[persistent=true]',
         'trunk':'oak_log','water':'water[level=0]','flower':'oxeye_daisy','light':'sea_lantern'}

    def put(x,y,z,mat):
        api.set(s,(x+96,y-63,z+96),mat)

    def cub(x1,y1,z1,x2,y2,z2,mat):
        api.fill(s,(x1+96,y1-63,z1+96),(x2+96,y2-63,z2+96),mat)

    def rnd(n):
        return math.floor(n+.5)

    # 1. Reuse exact architecture boxes in original authoring order.
    for b in records:
        if b['group'] in ('forest','glass'):
            continue
        x,y,z,w,h,d=[b[k] for k in ('x','y','z','w','h','d')]
        mat=pal[b['material']]
        x1,z1=rnd(x),rnd(z)
        x2,z2=max(x1,rnd(x+w)-1),max(z1,rnd(z+d)-1)
        y1=65+math.floor(y+.0001)
        y2=max(y1,65+math.ceil(y+h-.0001)-1)
        # Floor inlays and lawns are embedded, not a raised obstacle course.
        if h<=.16 and y<=2.1:
            y1=y2=64 if y<1 else 66
        if b['material']=='lawn':
            if h>.15: mat='short_grass'; y1=y2=67
            else: y1=y2=66
        if b['material']=='leaf' and h<1:
            mat='short_grass'; y1=y2=67
        if b['material']=='flower':
            y1=y2=67
        # Thin lamps/chains and sculpted quartz slabs are native block states.
        if b['material']=='gold' and w<.4 and d<.4:
            mat='end_rod[facing=up]'
        if h<=.65 and y>2.1 and w>=.7 and d>=.7 and b['material'] in ('ivory','marble','shadow-stone','jade','deep-jade'):
            slabs={'ivory':'smooth_quartz_slab','marble':'quartz_slab','shadow-stone':'polished_andesite_slab',
                   'jade':'waxed_oxidized_cut_copper_slab','deep-jade':'dark_prismarine_slab'}
            mat=slabs[b['material']]+'[type='+('top' if y%1>=.45 else 'bottom')+']'
            y2=y1
        # Repeated gallery roof tiles: slight pitch uses stairs with correct facings.
        if b['group']=='roof' and h==.65 and w==1 and d==1 and y>=16 and (abs(x)>23 or abs(z)>23):
            facing=('north' if z>0 else 'south') if abs(x)>23 else ('west' if x>0 else 'east')
            stairs={'ivory':'smooth_quartz_stairs','marble':'quartz_stairs','jade':'waxed_oxidized_cut_copper_stairs','deep-jade':'dark_prismarine_stairs'}
            mat=stairs.get(b['material'],'smooth_quartz_stairs')+f'[facing={facing},half=bottom]'
        cub(x1,y1,z1,x2,y2,z2,mat)

    # 2. Resolve sub-block column fluting into actual quartz pillar shafts.
    columns=[]
    for b in records:
        if b['group']=='base' and b['material']=='ivory' and b['w']==2 and b['d']==2 and b['h']>8:
            x,z=rnd(b['x']),rnd(b['z'])
            y1=65+math.ceil(b['y']); y2=65+math.floor(b['y']+b['h'])-1
            cub(x,y1,z,x+1,y2,z+1,'quartz_pillar[axis=y]')
            columns.append((x,z))

    # 3. Four exact staff plinths + eighteen exhibition plinths.
    # The preview has microscopic gold seams. Use a one-block plaque instead.
    podiums=[]
    for b in records:
        if b['group']=='base' and b['material']=='shadow-stone' and b['w']==3 and b['d']==3 and b['y']==2 and b['h']==.5:
            podiums.append((rnd(b['x']),rnd(b['z'])))
    assert len(podiums)==22, len(podiums)
    for x,z in podiums:
        cub(x,67,z,x+2,67,z+2,'chiseled_quartz_block')
        cub(x,68,z,x+2,68,z+2,'smooth_quartz')
        put(x+1,67,z,'gold_block')
        # No vegetation or rounding artefacts on top of a display base.
        for xx in range(x,x+3):
            for zz in range(z,z+3):
                for yy in (69,70):
                    api.unset(s,(xx+96,yy-63,zz+96))

    # 4. Fill support below gallery floors, where rounded caps expose the plinth.
    for (lx,ly,lz),material in list(s.blocks.items()):
        x,y,z=lx-96,ly+63,lz-96
        if y==66 and material in ('minecraft:smooth_quartz','minecraft:quartz_block','minecraft:grass_block',
                                   'minecraft:dark_prismarine','minecraft:gold_block'):
            if api.get(s,(lx,65-63,lz)) is None:
                put(x,65,z,'dirt' if material.endswith('grass_block') else 'quartz_bricks')

    # 5. Real 2-level entry steps, resolving fractional model steps into half blocks.
    # Keeps a nine-block-wide walkable center from the ground-level forest path.
    for x in range(-17,18):
        for z in range(39,45):
            if z<=40:
                put(x,65,z,'smooth_quartz')
                put(x,66,z,'smooth_quartz_stairs[facing=north,half=bottom]' if z==40 else 'smooth_quartz')
            elif z<=42:
                put(x,65,z,'smooth_quartz_stairs[facing=north,half=bottom]' if z==42 else 'smooth_quartz')
            else:
                put(x,64,z,'quartz_bricks')

    # 6. Waterproof reflecting ponds, not active flooding fountains.
    for x0 in (-33,23):
        cub(x0,64,29,x0+9,64,46,'polished_andesite')
        for x in range(x0,x0+10):
            for z in range(29,47):
                edge=x in (x0,x0+9) or z in (29,46)
                put(x,65,z,'smooth_quartz' if edge else 'water[level=0]')
        # Replace fractional liquid spout by contained basin pedestal and crystal light.
        cub(x0+3,65,36,x0+6,66,39,'quartz_bricks')
        cub(x0+4,67,37,x0+5,67,38,'sea_lantern')
        cub(x0+4,68,37,x0+5,68,38,'quartz_slab[type=bottom]')
        for x in range(x0+3,x0+7):
            for z in range(36,40):
                for y in (69,70):
                    api.unset(s,(x+96,y-63,z+96))

    # 7. Do not leave foliage on stone: crop the decorative grass to live lawn.
    plants=('minecraft:short_grass','minecraft:oxeye_daisy','minecraft:azure_bluet')
    for p,material in list(s.blocks.items()):
        if material in plants and api.get(s,(p[0],p[1]-1,p[2]))!='minecraft:grass_block':
            api.unset(s,p)
    return s
