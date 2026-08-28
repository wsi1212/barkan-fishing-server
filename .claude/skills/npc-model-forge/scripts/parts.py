#!/usr/bin/env python3
"""NPC 리그에 얹는 <b>3D 소품 부품</b> — steve.bbmodel(플레이어 리그) 위에 큐브를 더한다.

설계 근거는 `references/reference-study.md`. 그중 <b>실측으로 확정된 규칙</b>만 코드에 박는다.

★규칙 1 — <b>모델단위 1 = 텍스처 1픽셀</b> (레퍼런스 8종 전원 0.125 UV/unit, 변동계수 0.00~0.12)
  면마다 크기가 다른데 같은 UV 사각형을 주면 텍셀이 직사각형이 되어 <b>그래픽을 억지로
  늘린 티</b>가 난다(오너 지적). 그래서 `cube()`가 면의 실제 크기에서 UV를 계산한다.
  재질 텍스처는 <b>타일 가능</b>해야 이게 성립한다(props_texture.py가 그렇게 만든다).

★규칙 2 — 소품은 과장한다. 챙은 머리 폭의 1.4~1.8배.
★규칙 3 — 부피가 필요한 곳은 실체, 실제로 납작한 것만 평면.
★규칙 4 — 곡선(손잡이)은 회전 큐브로. 축 정렬만 쓰면 계단이 된다.

★steve 리그 실측(이 파일이 의존하는 좌표):
    머리   h_ph_head  피벗 [0,22.5,0] · 큐브 y22.5~30.0, x/z ±3.75
    왼팔   y16.88~22.5 · 왼<b>팔뚝</b> y11.25~16.87, x -7.5~-3.75  → <b>손은 y≈11.25</b>
    왼손 슬롯 pli_left_item 피벗 [-5.625, 10.875, 0]
"""
import uuid as _uuid

HEAD_TOP = 30.0
HEAD_BOT = 22.5
HEAD_HALF = 3.75
# ★★머리 <b>겉레이어</b>는 inflate=0.50이 걸려 실효 반폭이 4.234다(리그 실측).
#   모자·머리장식은 이 값을 넘겨야 머리에 파묻히지 않는다. 3.97로 잡았다가
#   크라운이 통째로 겉레이어 뒤에 가려 <b>머리카락이 그대로 보였다</b>(오너 지적).
#   렌더로 원인을 못 찾다가 픽셀 하나를 추적해서야 잡혔다 — inflate는 좌표만 봐선 안 보인다.
HEAD_OUTER_HALF = 4.234
HAND_Y = 11.25          # 팔뚝 아래끝 = 손 위치
HAND_X = 5.625
TEX_PROPS = 1

# ── 재질 영역 (64x64 props 아틀라스). 각 영역은 타일 가능해야 한다 ──────────────
MAT = {
    'straw':  (0, 0, 32, 32),
    'wicker': (32, 0, 32, 32),
    'cloth':  (0, 32, 32, 32),
    'veg':    (32, 32, 16, 16),
    'fruit':  (48, 32, 16, 16),
}
# 면 이름 → (가로에 대응하는 축, 세로에 대응하는 축)
FACE_AXES = {'north': (0, 1), 'south': (0, 1), 'east': (2, 1),
             'west': (2, 1), 'up': (0, 2), 'down': (0, 2)}


def _uid():
    return str(_uuid.uuid4())


def cube(name, a, b, mat, rot=None, origin=None, tex=TEX_PROPS, density=1.0):
    """큐브 하나. ★UV를 <b>면 크기에서 계산</b>한다 — 이게 늘어남을 막는 유일한 방법이다.

    density = 모델단위당 텍셀. 1.0이 바닐라 규약(1블록 16유닛 = 16텍셀)이고
    레퍼런스 8종도 전원 이 값이다. 재질 영역보다 큰 면은 영역 크기로 잘라 타일링한다.
    """
    mx, my, mw, mh = MAT[mat]
    d = [abs(b[i] - a[i]) for i in range(3)]
    faces = {}
    for f, (ax, ay) in FACE_AXES.items():
        w = min(mw, max(0.5, d[ax] * density))
        h = min(mh, max(0.5, d[ay] * density))
        faces[f] = {'uv': [mx, my, mx + w, my + h], 'texture': tex}
    return {'name': name, 'from': list(a), 'to': list(b), 'faces': faces,
            'type': 'cube', 'uuid': _uid(), 'box_uv': False,
            'origin': list(origin or a), 'rotation': list(rot or [0, 0, 0])}


def bone(name, origin, children, rot=None):
    u = _uid()
    return ({'uuid': u, 'name': name, 'origin': list(origin),
             'rotation': list(rot or [0, 0, 0]), 'children': [c['uuid'] for c in children]},
            {'uuid': u, 'children': [c['uuid'] for c in children]})


def straw_hat(tilt=-2.0):
    """밀짚모자 — <b>머리를 감싼다</b>. 정수리에 얹는 게 아니다.

    ★1차 실패: 챙 가장자리에 45° 판 4장 → 정면에서 뾰족한 날개 4개.
    ★2차 실패: 챙을 y29.4(머리 꼭대기 30 바로 아래)에 뒀더니 <b>모자가 정수리에만
      얹혀</b> 머리 대부분이 챙 아래로 노출되고, 챙과 크라운 사이로 머리카락이 보였다
      (오너 지적). 모자는 이마에 걸치는 물건이다 —
      <b>챙을 이마 높이(머리 위에서 1/3 지점)에 두고 크라운이 그 위 전부를 덮어야</b> 한다.
    """
    brim_y = HEAD_BOT + (HEAD_TOP - HEAD_BOT) * 0.62      # 이마 높이 ≈ y27.2
    top = HEAD_TOP + 2.2
    hh = HEAD_OUTER_HALF + 0.25            # ★겉레이어(4.234)보다 확실히 크게
    els = [
        # 챙 — 평면 한 장(실제로 납작하다). 머리 폭의 1.76배
        cube('brim', (-7.9, brim_y, -7.9), (7.9, brim_y + 0.32, 7.9), 'straw'),
        # 크라운 — 챙부터 머리 꼭대기 <b>위</b>까지 통째로 덮는다. 머리가 샐 틈이 없다
        cube('crown', (-hh, brim_y, -hh), (hh, top - 1.1, hh), 'straw'),
        cube('crown_top', (-hh + 0.7, top - 1.1, -hh + 0.7), (hh - 0.7, top - 0.35, hh - 0.7),
             'straw'),
        cube('crown_cap', (-hh + 1.5, top - 0.35, -hh + 1.5), (hh - 1.5, top, hh - 1.5),
             'straw'),
        # 리본 — 크라운 밑동을 감는 띠
        cube('band', (-hh - 0.1, brim_y + 0.35, -hh - 0.1),
             (hh + 0.1, brim_y + 1.15, hh + 0.1), 'cloth'),
    ]
    grp, out = bone('hat', (0, brim_y, 0), els, rot=[0, 0, tilt])
    return els, grp, out


def basket(side='left'):
    """바구니 — <b>손에서 매달린다</b>. 손잡이 꼭대기가 손 위치다.

    ★1~3차 실패: 손 피벗 한가운데(팔 속에 박힘) → 옆구리(팔·치마와 겹침) →
      몸 앞 z-4.6(손과 분리돼 <b>공중에 뜸</b>). 오너 지적: "손잡이가 손에 잡혀있지
      않고 팔이 붙어있어".
    ★해법: 손잡이 <b>꼭대기를 손 좌표(y≈11.25)에 맞추고</b> 바구니 몸통을 그 아래로
      늘어뜨린다. 팔뚝은 y11.25에서 <b>위로</b> 올라가므로 아래쪽엔 겹칠 것이 없다.
    """
    x = -HAND_X if side == 'left' else HAND_X
    grip = HAND_Y - 0.1        # 손잡이 꼭대기 = 손
    rim = grip - 2.9           # 테두리
    bot = rim - 4.0            # 바닥
    r = 2.85
    els = [
        # 손잡이 아치 — 꼭대기 가로대 + 좌우 기둥(회전으로 벌린다)
        cube('hnd_top', (x - 1.5, grip - 0.55, -0.42), (x + 1.5, grip, 0.42), 'wicker'),
        cube('hnd_l', (x - 2.5, rim, -0.42), (x - 1.75, grip - 0.2, 0.42), 'wicker',
             rot=[0, 0, 20], origin=(x - 2.1, rim, 0)),
        cube('hnd_r', (x + 1.75, rim, -0.42), (x + 2.5, grip - 0.2, 0.42), 'wicker',
             rot=[0, 0, -20], origin=(x + 2.1, rim, 0)),
        # 테두리 — 살짝 내밀어 그림자 선을 만든다
        cube('rim', (x - r - 0.35, rim - 0.55, -r - 0.35), (x + r + 0.35, rim, r + 0.35),
             'wicker'),
        # 몸통 — 아래로 좁아진다(실체 2단, 크기 섞기)
        cube('body_up', (x - r, bot + 1.6, -r), (x + r, rim - 0.5, r), 'wicker'),
        cube('body_low', (x - r + 0.7, bot, -r + 0.7), (x + r - 0.7, bot + 1.7, r - 0.7),
             'wicker'),
        # 내용물 — ★바구니와 색을 확실히 벌린다. 두 덩이를 어긋나게 얹어 비대칭
        cube('veg', (x - 2.2, rim - 1.5, -2.2), (x + 0.5, rim + 0.3, 1.3), 'veg'),
        cube('fruit', (x - 0.3, rim - 1.5, -1.1), (x + 2.3, rim + 0.1, 2.0), 'fruit'),
    ]
    # 세로 살 — 이게 '짜인 바구니'를 만든다(레퍼런스 basket이 22큐브였던 이유)
    for k, t in enumerate((-1.5, 0.0, 1.5)):
        els += [
            cube('slat_n%d' % k, (x + t - 0.38, bot + 1.5, -r - 0.16),
                 (x + t + 0.38, rim - 0.4, -r + 0.16), 'wicker'),
            cube('slat_s%d' % k, (x + t - 0.38, bot + 1.5, r - 0.16),
                 (x + t + 0.38, rim - 0.4, r + 0.16), 'wicker'),
            cube('slat_w%d' % k, (x - r - 0.16, bot + 1.5, t - 0.38),
                 (x - r + 0.16, rim - 0.4, t + 0.38), 'wicker'),
            cube('slat_e%d' % k, (x + r - 0.16, bot + 1.5, t - 0.38),
                 (x + r + 0.16, rim - 0.4, t + 0.38), 'wicker'),
        ]
    grp, out = bone('basket_' + side, (x, HAND_Y, 0), els)
    return els, grp, out
