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
    """재질 = 램프 + 성질.
    gloss: 광택 재질(과일 껍질 등)만 True — 스페큘러 패치+풀 명암폭. 무광(버섯갓/줄기/잎)은 절대 반짝이지 않음.
    var: 존 내 변주 강도(0~1). marks: 점무늬 [(fx,fy,rgba)] — 2×2 덩어리로 찍힘."""
    def __init__(self, base, gloss=False, marks=None, var=1.0):
        self.r = ramp(base) if isinstance(base, str) else base
        self.gloss = gloss; self.marks = marks or []; self.var = var

class Kit:
    def __init__(self, seed=0):
        self.boxes = []; self.seed = seed; self.rnd = random.Random(seed)

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
        """존(zone) 기반 폼 셰이딩 — 랜덤 소금후추 금지.
        픽셀 밝기 L = 위치의 함수(광원 top-left: 위·좌=밝음, 아래·우=어두움) →
        램프 존으로 양자화. 변주는 2×2 덩어리 단위 ±1존(존 경계 디더링 효과)만 —
        밝은 존에 어두운 픽셀이 절대 안 떨어짐(썩은 느낌의 원인 제거)."""
        r = mat.r; n = len(r)
        for yy in range(h):
            for xx in range(w):
                u = xx/max(1, w-1); v = yy/max(1, h-1)
                if face == "up":     L = 0.80 - 0.12*v - 0.08*u   # 하늘 향해 전체 밝음
                elif face == "down": L = 0.10                     # 그늘
                else:                L = 0.82 - 0.50*v - 0.18*u   # 세로 주도 그라데이션
                j = random.Random(hash((self.seed, face, (px+xx)//2, (py+yy)//2))).random()
                L += (j - 0.5) * 0.18 * mat.var                   # 덩어리 변주(±1존 이내)
                idx = int(min(0.999, max(0.0, L)) * n)
                if not mat.gloss: idx = max(1, min(n-2, idx))     # 무광=명암폭 압축, 극단값 금지
                d.point((px+xx, py+yy), fill=rgba(r[idx]))
        if mat.gloss and face != "down" and w >= 4 and h >= 3:    # 광택 재질만: 응집 스페큘러 패치
            sx, sy = px+1, py+1
            for dx, dy in ((0, 0), (1, 0), (0, 1)):
                d.point((sx+dx, sy+dy), fill=rgba(r[n-1]))
            d.point((sx, sy), fill=(255, 244, 240, 255))
        for mx, my, col in mat.marks:                             # 점무늬 = 2×2 덩어리(1px는 노이즈로 보임)
            if face != "down" and w >= 5 and h >= 4:
                bx = px + 1 + int(mx*(w-3)); by = py + 1 + int(my*(h-3))
                d.rectangle((bx, by, bx+1, by+1), fill=col)
