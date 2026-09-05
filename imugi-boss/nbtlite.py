import gzip, struct

def _rd(f):
    def u1(): return struct.unpack('>B', f.read(1))[0]
    def i1(): return struct.unpack('>b', f.read(1))[0]
    def i2(): return struct.unpack('>h', f.read(2))[0]
    def i4(): return struct.unpack('>i', f.read(4))[0]
    def i8(): return struct.unpack('>q', f.read(8))[0]
    def f4(): return struct.unpack('>f', f.read(4))[0]
    def f8(): return struct.unpack('>d', f.read(8))[0]
    def s():
        n = struct.unpack('>H', f.read(2))[0]
        return f.read(n).decode('utf-8')
    def payload(t):
        if t == 1: return i1()
        if t == 2: return i2()
        if t == 3: return i4()
        if t == 4: return i8()
        if t == 5: return f4()
        if t == 6: return f8()
        if t == 7:
            n = i4(); return list(f.read(n))
        if t == 8: return s()
        if t == 9:
            et = u1(); n = i4()
            return [payload(et) for _ in range(n)]
        if t == 10:
            d = {}
            while True:
                tt = u1()
                if tt == 0: break
                nm = s()
                d[nm] = payload(tt)
            return d
        if t == 11:
            n = i4(); return [i4() for _ in range(n)]
        if t == 12:
            n = i4(); return [i8() for _ in range(n)]
        raise ValueError('tag %d' % t)
    t = u1()
    if t == 0: return None, None
    name = s()
    return name, payload(t)

def load(path):
    with gzip.open(path, 'rb') as f:
        return _rd(f)
