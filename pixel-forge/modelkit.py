# modelkit — 박스 3D 모델의 품질을 "시스템"이 보장하는 레이어.
# 페인터는 모양(박스/프리미티브)+재질(램프)만 선언하면:
#   · 모든 면이 픽셀 노이즈+세로 그라데이션+스페큘러 (플랫 단색 금지)
#   · 아틀라스가 면 크기 1:1로 자동 패킹 (UV 수작업/밀도붕괴 제거)
#   · rounded_box/dome이 베벨 스택 자동 생성 + 겹면 자동 컬링 (z-fight 방지)
import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".claude", "skills", "pixel-art", "scripts"))
from palette import ramp, rgba
from PIL import Image, ImageDraw

class Mat:
    """재질 = 램프 + 스타일. spec=스페큘러 픽셀 수(윗면·밝은면에)."""
    def __init__(self, base, spec=0, marks=None, vgrad=True):
        self.r = ramp(base) if isinstance(base, str) else base
        self.spec = spec; self.marks = marks or []; self.vgrad = vgrad

class Kit:
    def __init__(self, seed=0):
        self.boxes = []; self.rnd = random.Random(seed)

    # ── 선언 API ──────────────────────────────
    def box(self, f, t, mat, cull=()):
        """cull: 렌더 생략할 면들 ('down','up',...) — 스택 내부면 제거용."""
        self.boxes.append((tuple(f), tuple(t), mat, set(cull)))

    def rounded_box(self, f, t, mat, bevel=1):
        """베벨 스택: 아랫굽(인셋) + 몸통 + 윗굽(인셋) = 둥근 실루엣."""
        x0, y0, z0 = f; x1, y1, z1 = t; b = bevel
        self.box((x0+b, y0, z0+b), (x1-b, y0+b, z1-b), mat, cull=("up",))
        self.box((x0, y0+b, z0), (x1, y1-b, z1), mat)
        self.box((x0+b, y1-b, z0+b), (x1-b, y1, z1-b), mat, cull=("down",))

    def dome(self, cx, y0, cz, w, h, mat):
        """돔 = 2단 캡 스택 (버섯갓/둥근머리)."""
        hw = w/2
        self.box((cx-hw, y0, cz-hw), (cx+hw, y0+h*0.6, cz+hw), mat)
        self.box((cx-hw+1.5, y0+h*0.6, cz-hw+1.5), (cx+hw-1.5, y0+h, cz+hw-1.5), mat, cull=("down",))

    # ── 빌드: 오토 아틀라스 + 모델 ──────────────
    def build(self, tex_ref):
        FACE_DIMS = {"up": (0, 2), "down": (0, 2), "north": (0, 1), "south": (0, 1), "west": (2, 1), "east": (2, 1)}
        regions = []                                   # (박스i, 면, w px, h px)
        for i, (f, t, mat, cull) in enumerate(self.boxes):
            dim = [t[k]-f[k] for k in range(3)]
            for face, (a, b) in FACE_DIMS.items():
                if face in cull: continue
                w = max(1, round(dim[a])); h = max(1, round(dim[b]))
                regions.append([i, face, w, h, None])
        # 셸프 패킹 (여백 1px)
        W = 64; x = y = shelf = 0
        for r in regions:
            if x + r[2] + 1 > W: x = 0; y += shelf + 1; shelf = 0
            r[4] = (x, y); shelf = max(shelf, r[3]); x += r[2] + 1
        H = 1 << max(3, (y + shelf + 1 - 1).bit_length())          # 2^n 높이
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        u, v = 16.0/W, 16.0/H
        els = []
        for i, (f, t, mat, cull) in enumerate(self.boxes):
            faces = {}
            for bi, face, w, h, (px, py) in regions:
                if bi != i: continue
                self._paint(d, px, py, w, h, mat, face)
                faces[face] = {"uv": [px*u, py*v, (px+w)*u, (py+h)*v], "texture": "#0"}
            els.append({"from": list(f), "to": list(t), "faces": faces})
        model = {"textures": {"0": tex_ref, "particle": tex_ref}, "elements": els,
                 "display": {"fixed": {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [1, 1, 1]}}}
        return im, model

    def _paint(self, d, px, py, w, h, mat, face):
        """면 채색 — 노이즈+그라데이션 기본, 윗면 밝게/아랫면 어둡게, 스페큘러/무늬."""
        r = mat.r
        shades = {"up": [r[4], r[3], r[2]], "down": [r[1], r[0], r[0]]}.get(face, [r[3], r[2], r[1]])
        for yy in range(h):
            tt = yy/max(1, h-1)
            wts = (5 + (3 if mat.vgrad and tt < 0.35 and face not in ("up", "down") else 0),
                   3, 2 + (3 if mat.vgrad and tt > 0.7 and face not in ("up", "down") else 0))
            for xx in range(w):
                d.point((px+xx, py+yy), fill=rgba(self.rnd.choices(shades, weights=wts)[0]))
        if mat.spec and face in ("up", "south", "north"):          # 좌상단 스페큘러
            for k in range(min(mat.spec, w*h//4)):
                d.point((px+1+(k % 2), py+1+(k // 2)), fill=rgba(r[4]))
        for mx, my, col in mat.marks:                              # 점박이 등 무늬 (면 비율 좌표)
            if face in ("up", "south", "north", "east", "west") and w > 2 and h > 2:
                d.point((px + int(mx*(w-1)), py + int(my*(h-1))), fill=col)
