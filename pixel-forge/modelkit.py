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
    def __init__(self, base, gloss=False, marks=None, var=1.0, grain=None, ao_top=False, stripe=None, stripe_w=2):
        self.r = ramp(base) if isinstance(base, str) else base
        self.gloss = gloss; self.marks = marks or []; self.var = var
        self.grain = grain      # "v"=세로 결(줄기/나무 — 컬럼 고정 변주)
        self.ao_top = ao_top    # 위 요소(갓 등) 밑 그늘 — 윗행을 어둡게
        self.stripe = ramp(stripe) if isinstance(stripe, str) else stripe   # 세로 줄무늬 램프(수박 등) — 모든 측면+윗면
        self.stripe_w = stripe_w

class Kit:
    def __init__(self, seed=0):
        self.boxes = []; self.seed = seed; self.rnd = random.Random(seed)

    # ── 선언 API ──────────────────────────────
    ANGLES = (-45.0, -22.5, 0.0, 22.5, 45.0)   # MC 요소 회전 허용값

    def box(self, f, t, mat, cull=(), rot=None):
        """cull: 렌더 생략할 면들. rot: ("x"|"y"|"z", 각도[, origin]) — 각짐 해독제.
        기울인 갓·휘는 줄기·매달린 꽃이 여기서 나온다. 각도는 ±22.5/±45로 스냅."""
        if rot:
            axis, ang = rot[0], min(self.ANGLES, key=lambda a: abs(a - rot[1]))
            org = list(rot[2]) if len(rot) > 2 else [(f[i]+t[i])/2 for i in range(3)]
            rot = (axis, ang, org)
        self.boxes.append((tuple(f), tuple(t), mat, set(cull), rot))

    def rounded_box(self, f, t, mat, bevel=1, rot=None):
        """베벨 스택: 아랫굽(인셋) + 몸통 + 윗굽(인셋) = 둥근 실루엣."""
        x0, y0, z0 = f; x1, y1, z1 = t; b = bevel
        org = [(x0+x1)/2, (y0+y1)/2, (z0+z1)/2]
        rr = (rot[0], rot[1], org) if rot else None        # 스택 전체가 한 원점으로 같이 기울게
        self.box((x0+b, y0, z0+b), (x1-b, y0+b, z1-b), mat, cull=("up",), rot=rr)
        self.box((x0, y0+b, z0), (x1, y1-b, z1), mat, rot=rr)
        self.box((x0+b, y1-b, z0+b), (x1-b, y1, z1-b), mat, cull=("down",), rot=rr)

    def dome(self, cx, y0, cz, w, h, mat, layers=3, rot=None):
        """돔 = 다단 캡 스택 (기본 3단 — 2단의 '네모 위 네모' 각짐 완화)."""
        hw = w/2
        org = [cx, y0+h/2, cz]
        rr = (rot[0], rot[1], org) if rot else None
        if layers <= 2:
            self.box((cx-hw, y0, cz-hw), (cx+hw, y0+h*0.6, cz+hw), mat, rot=rr)
            self.box((cx-hw+1.5, y0+h*0.6, cz-hw+1.5), (cx+hw-1.5, y0+h, cz+hw-1.5), mat, cull=("down",), rot=rr)
        else:
            self.box((cx-hw+0.8, y0, cz-hw+0.8), (cx+hw-0.8, y0+h*0.3, cz+hw-0.8), mat, cull=("up",), rot=rr)   # 밑단(살짝 인셋=오므림)
            self.box((cx-hw, y0+h*0.3, cz-hw), (cx+hw, y0+h*0.72, cz+hw), mat, rot=rr)                            # 최광폭 중단
            self.box((cx-hw+1.8, y0+h*0.72, cz-hw+1.8), (cx+hw-1.8, y0+h, cz+hw-1.8), mat, cull=("down",), rot=rr)  # 크라운

    # ── 자동 컬링: "완전히 덮인" 면만 제거 (부분 덮임 컬링 = 투명 구멍의 원인이었음, 2026-07-17) ──
    _FACE_AXIS = {"up": (1, True), "down": (1, False), "east": (0, True), "west": (0, False),
                  "south": (2, True), "north": (2, False)}

    def _face_covered(self, i, face):
        """i번 박스의 face가 다른 무회전 박스에 완전히 덮이면 True. 회전 박스는 컬링 대상/제공자 모두 제외.
        (허용오차 0.05 = 지터 ±0.015보다 넉넉히 — 지터 후에도 스택 컬링 유지)"""
        f, t, _, _, rot = self._built[i]
        if rot: return False
        ax, positive = self._FACE_AXIS[face]
        plane = t[ax] if positive else f[ax]
        oa = [k for k in range(3) if k != ax]           # 면의 2D 축
        e = 0.05
        for j, (f2, t2, _, _, rot2) in enumerate(self._built):
            if j == i or rot2: continue
            if not (f2[ax] - e <= plane <= t2[ax] + e): continue          # 그 평면을 관통/접촉
            if f2[ax] > plane - e and t2[ax] < plane + e: continue        # 두께 0 접촉 아님 보장
            if all(f2[k] - e <= f[k] and t2[k] + e >= t[k] for k in oa):  # 면 전체를 포함
                return True
        return False

    def _jitter(self):
        """★z-fight 원천 봉쇄(유저 지시 2026-07-18): 서로 다른 박스가 정확히 같은 x/z 평면을 공유할 수 없게
        박스마다 결정적 미세 오프셋(±0.015, 시드 고정)을 x/z에 주입. y는 접지 보존을 위해 불변.
        0.015블록(≈0.24px)은 육안 불가지만 깊이버퍼는 구분 → 교차/코플레너 z-fight 소멸."""
        out = []
        for i, (f, t, mat, cull, rot) in enumerate(self.boxes):
            rnd = random.Random(hash((self.seed, i, "jit")))
            dx = (rnd.random() - 0.5) * 0.03
            dz = (rnd.random() - 0.5) * 0.03
            f2 = (f[0] + dx, f[1], f[2] + dz); t2 = (t[0] + dx, t[1], t[2] + dz)
            rot2 = (rot[0], rot[1], [rot[2][0] + dx, rot[2][1], rot[2][2] + dz]) if rot else None
            out.append((f2, t2, mat, cull, rot2))
        return out

    # ── 빌드: 오토 아틀라스 + 모델 ──────────────
    def build(self, tex_ref):
        FACE_DIMS = {"up": (0, 2), "down": (0, 2), "north": (0, 1), "south": (0, 1), "west": (2, 1), "east": (2, 1)}
        self._built = self._jitter()                   # ★코플레너 봉쇄: 박스별 x/z 미세 오프셋
        regions = []                                   # (박스i, 면, w px, h px)
        for i, (f, t, mat, cull, rot) in enumerate(self._built):
            dim = [t[k]-f[k] for k in range(3)]
            for face, (a, b) in FACE_DIMS.items():
                if self._face_covered(i, face): continue   # ★선언(cull) 무시 — 증명된 면만 자동 제거
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
        for i, (f, t, mat, cull, rot) in enumerate(self._built):
            faces = {}
            for bi, face, w, h, (px, py) in regions:
                if bi != i: continue
                self._paint(d, px, py, w, h, mat, face)
                faces[face] = {"uv": [px*u, py*v, (px+w)*u, (py+h)*v], "texture": "#0"}
            if not faces: continue   # 완전히 파묻힌 박스(전면 컬링) — 빈 faces 요소는 MC 클라가 모델 전체를 거부(체커)
            el = {"from": list(f), "to": list(t), "faces": faces}
            if rot: el["rotation"] = {"origin": rot[2], "axis": rot[0], "angle": rot[1]}
            els.append(el)
        # display 풀세트 — 판매팩 필수: GUI 아이콘(블록식 3/4뷰)·손·바닥 전부 정의 (fixed=CE 가구 배치용)
        model = {"textures": {"0": tex_ref, "particle": tex_ref}, "elements": els,
                 "display": {
                     "fixed":  {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [1, 1, 1]},
                     "gui":    {"rotation": [30, 225, 0], "translation": [0, 0, 0], "scale": [0.625, 0.625, 0.625]},
                     "ground": {"rotation": [0, 0, 0], "translation": [0, 3, 0], "scale": [0.25, 0.25, 0.25]},
                     "head":   {"rotation": [0, 0, 0], "translation": [0, 14.25, 0], "scale": [1, 1, 1]},
                     "thirdperson_righthand": {"rotation": [75, 45, 0], "translation": [0, 2.5, 0], "scale": [0.375, 0.375, 0.375]},
                     "thirdperson_lefthand":  {"rotation": [75, 45, 0], "translation": [0, 2.5, 0], "scale": [0.375, 0.375, 0.375]},
                     "firstperson_righthand": {"rotation": [0, 45, 0], "translation": [0, 0, 0], "scale": [0.4, 0.4, 0.4]},
                     "firstperson_lefthand":  {"rotation": [0, 225, 0], "translation": [0, 0, 0], "scale": [0.4, 0.4, 0.4]}}}
        return im, model

    def _paint(self, d, px, py, w, h, mat, face):
        """존 기반 폼 셰이딩 v3 — 프로 규칙(MC Style Guide/Faithful) 반영:
        · 밴딩 금지: 존 경계를 컬럼별 위상 오프셋 + (무광만) 체커 디더링으로 분산
        · 재질 대비: 광택=고대비·디더 금지·코어섀도·스페큘러 / 무광=저대비·디더 허용
        · 페인티드 라운딩: 측면 좌우 가장자리 컬럼에 명암 턴(둥근 건 텍스처가 만든다)
        · 접촉 AO: 측면 바닥행 어둡게, ao_top 재질(줄기)은 윗행도(갓 그늘)
        · grain="v": 컬럼 고정 변주 = 세로 결(줄기/가지)"""
        r = mat.r; n = len(r)
        side = face not in ("up", "down")

        def light(u, v, xx, yy, j):
            if face == "up":     L = 0.80 - 0.12*v - 0.08*u
            elif face == "down": L = 0.10
            elif mat.gloss:      L = 0.85 - 0.34*v - 0.14*u       # 광택: 밝음 유지(그림자는 코어풀이 담당 — 프로 사과 실측: 암부 ≤16%)
            else:                L = 0.82 - 0.50*v - 0.18*u
            if side and w >= 4:                                    # 페인티드 라운딩(형태 턴)
                if xx == 0: L += 0.07
                elif xx == w-1: L -= 0.13
            if side and h >= 3:
                if yy == h-1: L -= 0.11                            # 바닥 접촉 AO
                elif yy == 0: L += (-0.14 if mat.ao_top else 0.05) # 갓 그늘 or 림라이트
            if mat.gloss:                                          # 구형 코어섀도(우하단 웅덩이)
                L -= max(0.0, (u+v)/2 - 0.55) * 0.5
            return L + j

        amp = (0.09 if mat.gloss else 0.16) * mat.var
        for yy in range(h):
            for xx in range(w):
                u = xx/max(1, w-1); v = yy/max(1, h-1)
                if mat.grain == "v":                               # 세로 결: 컬럼 고정
                    j = random.Random(hash((self.seed, face, px+xx))).random()
                else:
                    j = random.Random(hash((self.seed, face, (px+xx)//2, (py+yy)//2))).random()
                # 줄무늬 재질(수박): down 뺀 전 면에 세로 밴드 — 밴드 안은 stripe 램프로 채색
                rr = r
                if mat.stripe and face != "down" and (xx // mat.stripe_w) % 2 == 1:
                    rr = mat.stripe
                L = light(u, v, xx, yy, (j-0.5)*amp)
                idx = int(min(0.999, max(0.0, L)) * n)
                if not mat.gloss:
                    idx = max(1, min(n-2, idx))
                    if h >= 4 and yy+1 < h:                        # 무광: 존 경계 체커 디더
                        L2 = light(u, (yy+1)/max(1, h-1), xx, yy+1, (j-0.5)*amp)
                        i2 = max(1, min(n-2, int(min(0.999, max(0.0, L2)) * n)))
                        if i2 != idx and (xx + yy) % 2 == 0: idx = i2
                d.point((px+xx, py+yy), fill=rgba(rr[idx]))
        if mat.gloss and face != "down" and w >= 4 and h >= 3:     # 응집 스페큘러(광택 전용)
            sx, sy = px+1, py+1
            for dx, dy in ((0, 0), (1, 0), (0, 1)):
                d.point((sx+dx, sy+dy), fill=rgba(r[n-1]))
            d.point((sx, sy), fill=(255, 244, 240, 255))
        placed = []                                                # 점무늬: 간격 강제(뭉침=얼룩 방지)
        for mx, my, col in mat.marks:
            if face == "down" or w < 7 or h < 3: continue          # 좁은 면엔 무늬 생략
            mh = 2 if h >= 6 else 1                                # 낮은 면은 2×1
            bx = px + 1 + int(mx*(w-4)); by = py + 1 + int(my*max(0, h-2-mh))
            if any(abs(bx-ox) < 4 and abs(by-oy) < 3 for ox, oy in placed): continue
            d.rectangle((bx, by, bx+1, by+mh-1), fill=col); placed.append((bx, by))
