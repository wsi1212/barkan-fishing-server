import struct, zlib, io, math
import nbtlite

def read_chunk(mca_path, cx, cz):
    with open(mca_path,'rb') as f:
        hdr = f.read(4096)
        i = ((cx & 31) + (cz & 31)*32)*4
        off = int.from_bytes(hdr[i:i+3],'big'); cnt = hdr[i+3]
        if off == 0: return None
        f.seek(off*4096)
        ln = struct.unpack('>i', f.read(4))[0]
        comp = f.read(1)[0]
        data = f.read(ln-1)
        if comp == 1: raw = __import__('gzip').decompress(data)
        elif comp == 2: raw = zlib.decompress(data)
        elif comp == 3: raw = data
        else: raise ValueError('comp %d'%comp)
        bio = io.BytesIO(raw)
        return nbtlite._rd(bio)[1]

def bstr(entry):
    n = entry['Name']
    p = entry.get('Properties')
    if not p: return n
    return n + '[' + ','.join(f'{k}={v}' for k,v in sorted(p.items())) + ']'

def section_blocks(sec):
    bs = sec.get('block_states')
    if bs is None: return None
    pal = [bstr(e) for e in bs['palette']]
    if len(pal) == 1: return lambda i: pal[0]
    data = bs.get('data')
    bits = max(4, (len(pal)-1).bit_length())
    per = 64 // bits
    mask = (1<<bits)-1
    def get(i):
        lo = data[i//per]
        sh = (i%per)*bits
        return pal[(lo >> sh) & mask]
    return get

def region_blocks(world, x1,y1,z1,x2,y2,z2):
    out = {}
    for cx in range(x1>>4, (x2>>4)+1):
        for cz in range(z1>>4, (z2>>4)+1):
            mca = f'{world}/region/r.{cx>>5}.{cz>>5}.mca'
            ch = read_chunk(mca, cx, cz)
            if ch is None: continue
            secs = {s['Y']: s for s in ch['sections']}
            for y in range(y1, y2+1):
                sy = y >> 4
                sec = secs.get(sy)
                if sec is None: continue
                get = section_blocks(sec)
                if get is None: continue
                for x in range(max(x1, cx*16), min(x2, cx*16+15)+1):
                    for z in range(max(z1, cz*16), min(z2, cz*16+15)+1):
                        i = ((y&15)*16 + (z&15))*16 + (x&15)
                        out[(x,y,z)] = get(i)
    return out
