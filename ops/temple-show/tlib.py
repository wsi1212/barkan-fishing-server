"""해저신전 후보 맵을 하나의 전시월드로 굽는 라이브러리."""
import logging, numpy as np, amulet, amulet_nbt as nbt, PyMCTranslate
from amulet.api.block import Block
from amulet.api.chunk import Chunk
logging.disable(logging.ERROR)

TM = PyMCTranslate.new_translation_manager()
# 물/수초는 빈 월드에서 흘러넘치거나 즉시 파괴되므로 공기로 치환한다.
STRIP = {"water","flowing_water","bubble_column","seagrass","tall_seagrass",
         "kelp","kelp_plant","air","cave_air","void_air"}
def bn(name): return name.split(":")[-1]

def u8(tag):
    """amulet_nbt ByteArray(부호있음) -> uint8 ndarray."""
    return np.asarray(tag, dtype=np.int8).view(np.uint8)

# ---------- varint ----------
def decode_varints(raw, count):
    b = np.asarray(raw, dtype=np.uint8).astype(np.int64)
    if b.size == count and not (b & 0x80).any():
        return b
    cont = (b & 0x80) != 0
    starts = np.empty(b.size, bool); starts[0] = True; starts[1:] = ~cont[:-1]
    gidx = np.cumsum(starts) - 1
    gstart = np.flatnonzero(starts)[gidx]
    shift = (np.arange(b.size) - gstart) * 7
    vals = np.bincount(gidx, weights=((b & 0x7F) << shift).astype(np.float64))
    return vals.astype(np.int64)

# ---------- schematic ----------
def parse_schematic(path):
    root = nbt.load(path).compound
    if len(root) == 1 and list(root.keys())[0] in ("Schematic", ""):
        root = root[list(root.keys())[0]]
    W = int(root["Width"]); H = int(root["Height"]); L = int(root["Length"])
    n = W * H * L
    if "Palette" in root or "Blocks" in root and hasattr(root["Blocks"], "keys"):
        if "Palette" in root:                       # sponge v2
            pal_c, data = root["Palette"], u8(root["BlockData"])
            dv = int(root["DataVersion"]) if "DataVersion" in root else -1
        else:                                       # sponge v3
            blk = root["Blocks"]; pal_c, data = blk["Palette"], u8(blk["Data"])
            dv = int(root["DataVersion"]) if "DataVersion" in root else -1
        if dv <= 0: dv = 2860
        pal = [None] * (max(int(v) for v in pal_c.values()) + 1)
        for k, v in pal_c.items(): pal[int(v)] = str(k)
        idx = decode_varints(data, n)[:n]
        blocks = [Block.from_string_blockstate(s if s else "minecraft:air") for s in
                  [p or "minecraft:air" for p in pal]]
        ver = TM.get_version("java", dv)
        uni = [ver.block.to_universal(b)[0] for b in blocks]
    else:                                           # mcedit legacy
        ids = u8(root["Blocks"]).astype(np.int64)
        dat = u8(root["Data"]).astype(np.int64) & 0x0F
        for key in ("AddBlocks", "Add"):
            if key in root:
                add = u8(root[key])
                hi = np.repeat(add >> 4, 1); lo = add & 0x0F
                nib = np.empty(add.size * 2, np.int64)
                nib[0::2] = hi; nib[1::2] = lo
                ids += nib[:ids.size] << 8
        combo = ids * 16 + dat
        uniq, idx = np.unique(combo, return_inverse=True)
        ver = TM.get_version("java", (1, 12, 2))
        uni = []
        for c in uniq:
            try: uni.append(ver.block.to_universal(ver.block.ints_to_block(int(c) // 16, int(c) % 16))[0])
            except Exception: uni.append(Block("universal_minecraft", "air"))
    vol = idx.reshape(H, L, W).transpose(2, 0, 1)   # -> (W,H,L)
    return vol, uni

# ---------- world ----------
def world_volume(path, bbox, dim=None):
    lv = amulet.load_level(path)
    dims = list(lv.dimensions)
    dim = dim or ("minecraft:overworld" if "minecraft:overworld" in dims else dims[0])
    x0, y0, z0, x1, y1, z1 = bbox
    W, H, L = x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1
    vol = np.zeros((W, H, L), np.int32)
    for cx in range(x0 // 16, x1 // 16 + 1):
        for cz in range(z0 // 16, z1 // 16 + 1):
            try: ch = lv.get_chunk(cx, cz, dim)
            except Exception: continue
            for cy in list(ch.blocks.sub_chunks):
                if cy * 16 > y1 or cy * 16 + 15 < y0: continue
                arr = ch.blocks.get_sub_chunk(cy)
                sx0, sx1 = max(x0, cx * 16), min(x1, cx * 16 + 15)
                sz0, sz1 = max(z0, cz * 16), min(z1, cz * 16 + 15)
                sy0, sy1 = max(y0, cy * 16), min(y1, cy * 16 + 15)
                vol[sx0-x0:sx1-x0+1, sy0-y0:sy1-y0+1, sz0-z0:sz1-z0+1] = \
                    arr[sx0-cx*16:sx1-cx*16+1, sy0-cy*16:sy1-cy*16+1, sz0-cz*16:sz1-cz*16+1]
    uni = [lv.block_palette[i] for i in range(len(lv.block_palette))]
    lv.close()
    return vol, uni

# ---------- trim / paste ----------
def normalize(vol, uni, extra_strip=()):
    """대상 레벨과 무관하게 «0 = 공기» 인 로컬 팔레트로 정규화한다.
    (대상 레벨을 열어 둔 채 소스를 열면 Amulet 세션락이 풀려서 저장이 실패한다 — 분리 필수)"""
    strip = STRIP
    substr = tuple(extra_strip)
    local = [Block("universal_minecraft", "air")]
    seen = {}
    lut = np.zeros(len(uni), np.int32)
    for i, b in enumerate(uni):
        if b is None or bn(b.namespaced_name) in strip:
            continue
        fb = b.full_blockstate
        if substr and any(t in fb for t in substr):
            continue
        k = b.full_blockstate
        if k not in seen:
            seen[k] = len(local); local.append(b)
        lut[i] = seen[k]
    used = np.unique(vol)
    if used.size and used.max() >= len(lut):
        lut = np.concatenate([lut, np.zeros(used.max() - len(lut) + 1, np.int32)])
    return lut[vol], local

def to_level(vol, local, lv):
    dlut = np.array([lv.block_palette.get_add_block(b) for b in local], np.int32)
    return dlut[vol], int(dlut[0])

def trim(vol, air):
    solid = vol != air
    if not solid.any(): return None, None
    xs, ys, zs = np.nonzero(solid)
    sl = (slice(xs.min(), xs.max()+1), slice(ys.min(), ys.max()+1), slice(zs.min(), zs.max()+1))
    return vol[sl], (int(xs.min()), int(ys.min()), int(zs.min()))

def paste(lv, dim, vol, origin, air):
    W, H, L = vol.shape
    ox, oy, oz = origin
    assert ox % 16 == 0 and oz % 16 == 0, "청크 정렬 필요"
    for cx in range(ox // 16, (ox + W - 1) // 16 + 1):
        for cz in range(oz // 16, (oz + L - 1) // 16 + 1):
            x0, x1 = max(cx*16, ox), min(cx*16+16, ox+W)
            z0, z1 = max(cz*16, oz), min(cz*16+16, oz+L)
            sub = vol[x0-ox:x1-ox, :, z0-oz:z1-oz]
            if not (sub != air).any(): continue
            try: ch = lv.get_chunk(cx, cz, dim)
            except Exception:
                ch = lv.create_chunk(cx, cz, dim)
            for cy in range((oy) // 16, (oy + H - 1) // 16 + 1):
                y0, y1 = max(cy*16, oy), min(cy*16+16, oy+H)
                if y1 <= y0: continue
                piece = sub[:, y0-oy:y1-oy, :]
                if not (piece != air).any(): continue
                if ch.blocks.has_sub_chunk(cy):
                    arr = ch.blocks.get_sub_chunk(cy).copy()
                else:
                    arr = np.zeros((16, 16, 16), np.int32)
                arr[x0-cx*16:x1-cx*16, y0-cy*16:y1-cy*16, z0-cz*16:z1-cz*16] = piece
                ch.blocks.add_sub_chunk(cy, arr)
            ch.status = "full"
            ch.changed = True

def platform(lv, dim, x0, z0, W, L, y, block="dark_prismarine", pad=2):
    b = lv.block_palette.get_add_block(Block("universal_minecraft", block))
    vol = np.full((W + pad*2, 1, L + pad*2), b, np.int32)
    paste(lv, dim, vol, (x0 - pad - ((x0-pad) % 16), y, z0 - pad - ((z0-pad) % 16)), -1)
