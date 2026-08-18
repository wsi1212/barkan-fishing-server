#!/usr/bin/env python3
"""하이픽셀 기준 파일럿 v2 — 클라우스·군터·그레첸.

근거: skin-forge/references/hypixel/ 73장 실측 (2026-08-18 수집).
  ★1차 시도(bold_pilot.py)는 「하이픽셀 = 플랫」으로 오독해 grain 을 걷어냈다가
    디테일이 통째로 사라져 기각됐다. 실물을 확대해 보니 정반대다 —
    하이픽셀 몸통엔 «부드러운 그라데이션 음영»이 제대로 들어가 있다.

실측한 격차 4가지와 그 처방
  ① 얼굴 공식 (레퍼런스 10장 확대 대조로 확정)
       [눈썹] eye_y-1, x1~2 / x5~6 을 «두꺼운 어두운 바»
       [눈]   x1=거의 흰색, x2=채도 있는 홍채  (반대쪽 미러, gaze=0)
       [코]   x3~4 를 한 단 «밝게» — 얼굴이 입체로 읽히는 핵심
       [볼]   x0,x7 과 턱 행을 한 단 어둡게
       [입]   행 6 에 2~4px 덩어리 (또는 콧수염 블록)
     우리 기존: 1px 점 두 개 + 무표정 → 축소하면 아무것도 안 남는다.
  ② 음영: 저쪽=부드러운 그라데이션(천으로 읽힘) / 우리=speckle 랜덤 점(때로 읽힘).
     ★밀도를 줄이는 게 아니라 «음영의 종류»를 바꾼다.
  ③ 채도 있는 악센트 3~5곳(금 트림·넥타이·새시·버클). 기존 룰의 「최대 2곳」을 푼다.
  ④ 머리카락에 결 — 단색 캡 금지. 열마다 값을 흔들되 «결정적»으로.

유지: base 6면 불투명 · 순수검정 금지 · outer 가 눈을 안 덮음 · 비대칭 1개 이상
     · 부피는 outer · 몸을 감는 건 strip · 결정적 빌드(crc32) · 중세 항구 팔레트
"""
import pathlib, sys, zlib

sys.path.insert(0, '/Users/user/.claude/skills/npc-skin-forge/scripts')
import skinlib as S
from skinlib import mix

OUT = pathlib.Path(__file__).parent / 'out'
SIDES = ('front', 'back', 'left', 'right')


def dk(c, t): return mix(c, (0, 0, 0), t)
def lt(c, t): return mix(c, (255, 255, 255), t)
def jit(name, x, y, n=3):
    """결정적 흔들림 0..n-1 (crc32 — hash() 는 프로세스마다 달라져 빌드가 비결정적이 된다)"""
    return zlib.crc32(('%s:%d:%d' % (name, x, y)).encode()) % n


def grad(sk, part, y0, y1, c, layer='base', top=False, bottom=False,
         span=0.30, light='left', tag=''):
    """부드러운 세로 그라데이션 + 가로 라이팅. speckle 없음 — 이게 '천'으로 읽히는 이유."""
    h = max(1, y1 - y0)
    for f in SIDES:
        fc = sk.f(part, f, layer)
        w = fc.w if hasattr(fc, 'w') else 8
        side = {'front': 0.0, 'back': 0.10, 'left': 0.18, 'right': 0.18}[f]
        for y in range(y0, y1 + 1):
            t = (y - y0) / h                       # 위=밝고 아래=어둡게
            base = mix(lt(c, span * 0.45), dk(c, span * 0.55), t)
            base = dk(base, side)
            for x in range(w):
                px = base
                if f == 'front':
                    if (x == 0 if light == 'left' else x == w - 1):
                        px = lt(base, 0.10)        # 광원쪽 모서리
                    elif (x == w - 1 if light == 'left' else x == 0):
                        px = dk(base, 0.14)        # 반대쪽 그림자
                if tag and jit(tag + part, x, y, 7) == 0:
                    px = dk(px, 0.05)              # 아주 옅은 직조감(반스텝)
                fc.px(x, y, px)
    if top:
        sk.f(part, 'top', layer).fill(lt(c, 0.12))
    if bottom:
        sk.f(part, 'bottom', layer).fill(dk(c, 0.34))


def trim(sk, part, y, c, layer='base'):
    """채도 있는 트림 — 몸을 한 바퀴 감는다."""
    sk.strip(part, layer).band(y, y, c)


def seam(sk, part, y, c, layer='base'):
    sk.strip(part, layer).band(y, y, dk(c, 0.45))


# ── 얼굴 (레퍼런스 공식) ─────────────────────────────────────────────────────
def face(sk, skin, hair, *, eye_y=4, iris=(0x35, 0x62, 0xa8), fringe=2,
         beard=None, beard_y=6, moustache=None, mouth=True, tag='n',
         sidehair=True, cap=None):
    WHITE = (0xf6, 0xf3, 0xea)
    for f in SIDES:
        sk.f('head', f).fill(skin if f == 'front' else dk(skin, 0.10))
    sk.f('head', 'top').fill(hair)
    sk.f('head', 'bottom').fill(dk(skin, 0.30))
    hd = sk.f('head', 'front')
    # 볼·턱 음영 + 코 기둥(밝게) — 얼굴이 입체로 읽히게
    for y in range(fringe, 8):
        hd.px(0, y, dk(skin, 0.16)); hd.px(7, y, dk(skin, 0.16))
    for y in range(7, 8):
        hd.row(y, dk(skin, 0.13), 1, 7)
    for y in range(eye_y, min(8, eye_y + 3)):
        hd.px(3, y, lt(skin, 0.09)); hd.px(4, y, lt(skin, 0.09))
    # 머리카락(base 상단) + 결
    for y in range(0, fringe):
        for x in range(8):
            hd.px(x, y, dk(hair, 0.06 * jit(tag, x, y)))
    # 눈썹 — 두꺼운 어두운 바
    brow = dk(hair, 0.30)
    hd.rect(1, eye_y - 1, 2, eye_y - 1, brow); hd.rect(5, eye_y - 1, 6, eye_y - 1, brow)
    # 눈 — 흰자 바깥 + 채도 홍채 안쪽
    hd.px(1, eye_y, WHITE); hd.px(2, eye_y, iris)
    hd.px(5, eye_y, iris); hd.px(6, eye_y, WHITE)
    # 입 / 콧수염 / 수염
    if moustache:
        hd.rect(2, beard_y - 1, 5, beard_y - 1, moustache)
    if beard:
        for y in range(beard_y, 8):
            for x in range(1, 7):
                hd.px(x, y, dk(beard, 0.05 * jit(tag + 'b', x, y)))
        for f in ('left', 'right'):
            ff = sk.f('head', f)
            for y in range(beard_y, 8):
                ff.row(y, dk(beard, 0.14), 2, 8)
    elif mouth:
        hd.rect(3, 6, 4, 6, dk(skin, 0.40))
    # outer: 옆머리 + 정수리 (부피는 outer 에)
    ho = sk.f('head', 'front', 'outer')
    for y in range(0, fringe + 1):
        for x in range(8):
            ho.px(x, y, dk(hair, 0.06 * jit(tag + 'o', x, y)))
    if sidehair:
        for y in range(fringe + 1, 7):
            ho.px(0, y, dk(hair, 0.04 * jit(tag + 's', 0, y)))
            ho.px(7, y, dk(hair, 0.04 * jit(tag + 's', 7, y)))
    for f2 in ('left', 'right', 'back'):
        fo = sk.f('head', f2, 'outer')
        for y in range(0, fringe + 2):
            for x in range(8):
                fo.px(x, y, dk(hair, 0.10 if f2 != 'back' else 0.04 * jit(tag + f2, x, y)))
    sk.f('head', 'top', 'outer').fill(hair)
    if cap:
        for y in range(0, 2):
            ho.row(y, cap)
        sk.f('head', 'top', 'outer').fill(lt(cap, 0.05))
        for f2 in ('left', 'right', 'back'):
            for y in range(0, 2):
                sk.f('head', f2, 'outer').row(y, cap if f2 == 'back' else dk(cap, 0.09))


def arms(sk, skin, tag):
    for p in ('arm_r', 'arm_l'):
        grad(sk, p, 0, 11, skin, top=True, bottom=True, span=0.22, tag=tag)


def legs(sk, c, boot, bootrows, tag):
    for p in ('leg_r', 'leg_l'):
        grad(sk, p, 0, 11 - bootrows, c, top=True, span=0.26, tag=tag)
        grad(sk, p, 12 - bootrows, 11, boot, bottom=True, span=0.20, tag=tag)
        trim(sk, p, 12 - bootrows, lt(boot, 0.26))


def build(name, fn):
    sk = S.new(); fn(sk); sk.save(str(OUT / f'{name}.png')); print('  ✓', name)


# ── 7 클라우스 — 잡화 상점 ───────────────────────────────────────────────────
def klaus(sk):
    SKIN=(0xd0,0xa1,0x78); HAIR=(0x5c,0x46,0x2c)
    LINEN=(0xdd,0xd4,0xbc); WINE=(0x86,0x2f,0x35); APRON=(0xc9,0xb4,0x8a)
    TROUS=(0x50,0x47,0x3c); BOOT=(0x2f,0x28,0x22); BRASS=(0xd8,0xa8,0x3a)
    face(sk, SKIN, HAIR, eye_y=4, iris=(0x3a,0x6a,0x9c), fringe=2,
         moustache=dk(HAIR,0.18), tag='klaus')
    grad(sk,'body',0,11,LINEN,top=True,bottom=True,span=0.28,tag='klaus')
    fa=sk.f('body','front')
    for y in range(1,8):                                     # 조끼
        for x in range(8):
            fa.px(x,y, mix(lt(WINE,0.10), dk(WINE,0.18), (y-1)/7))
    fa.rect(3,1,4,2,LINEN); fa.px(3,3,LINEN); fa.px(4,3,LINEN)   # V넥
    fa.col(0,dk(WINE,0.38),1,8); fa.col(7,dk(WINE,0.38),1,8)     # 라펠
    for y in range(1,8):
        for f in ('left','right','back'):
            sk.f('body',f).row(y, dk(WINE,0.22))
    trim(sk,'body',0,LINEN)                                   # 칼라
    fa.px(2,2,BRASS); fa.px(2,5,BRASS)                        # 단추 2개(채도 악센트)
    for y in range(8,12):                                     # 앞치마
        for x in range(1,7):
            fa.px(x,y, mix(lt(APRON,0.08), dk(APRON,0.16), (y-8)/4))
    fa.rect(2,10,5,10,dk(APRON,0.24))                         # 주머니 입구
    trim(sk,'body',7,dk(TROUS,0.20)); fa.rect(3,7,4,7,BRASS)  # 벨트 + 버클
    arms(sk,SKIN,'klaus')
    for p in ('arm_r','arm_l'): grad(sk,p,0,7,LINEN,top=True,span=0.24,tag='klaus')
    grad(sk,'arm_r',0,9,LINEN,top=True,span=0.24,tag='klaus') # 비대칭
    for p,cy in (('arm_r',9),('arm_l',7)): grad(sk,p,cy-1,cy,WINE,span=0.16)
    legs(sk,TROUS,BOOT,4,'klaus')
    sk.f('leg_r','front').rect(1,5,2,6,dk(TROUS,0.26))        # 무릎 패치


# ── 9 군터 — 대장간 ─────────────────────────────────────────────────────────
def gunter(sk):
    SKIN=(0xc6,0x8f,0x66); HAIR=(0x46,0x41,0x3a); BEARD=(0xd9,0xd3,0xc6)
    RUST=(0xb4,0x52,0x2e); LEATH=(0x46,0x30,0x21); STRAP=(0x74,0x4f,0x2e)
    TROUS=(0x74,0x67,0x55); BOOT=(0x2c,0x25,0x1e); IRON=(0xb0,0xb6,0xbc)
    face(sk, SKIN, HAIR, eye_y=4, iris=(0x2f,0x6f,0x86), fringe=2,
         beard=BEARD, beard_y=6, moustache=dk(BEARD,0.12), tag='gunter')
    grad(sk,'body',0,11,RUST,top=True,bottom=True,span=0.30,tag='gunter')
    fa=sk.f('body','front')
    for y in range(2,12):                                     # 가죽 앞치마
        for x in range(1,7):
            fa.px(x,y, mix(lt(LEATH,0.12), dk(LEATH,0.14), (y-2)/10))
    fa.row(2,None,0,0) if False else None
    for x in (1,2,5,6):                                       # 가슴받이 사다리꼴
        if x in (1,2,5,6) and x not in (2,5): fa.px(x,2, dk(RUST,0.10))
    fa.px(1,2,dk(RUST,0.10)); fa.px(6,2,dk(RUST,0.10))
    for y in (0,1): fa.px(2,y,STRAP); fa.px(5,y,STRAP)        # 어깨끈
    sk.f('body','top').rect(2,0,2,3,STRAP); sk.f('body','top').rect(5,0,5,3,STRAP)
    sk.f('body','back').rect(2,0,2,5,STRAP); sk.f('body','back').rect(5,0,5,5,STRAP)
    fa.row(11,lt(LEATH,0.20),1,7)                             # 밑단 하이라이트
    trim(sk,'body',7,dk(LEATH,0.42)); fa.rect(3,6,4,7,IRON)   # 벨트 + 큰 쇠버클
    fa.px(1,9,IRON); fa.px(6,4,IRON)                          # 리벳(악센트)
    arms(sk,SKIN,'gunter')
    grad(sk,'arm_l',0,4,RUST,top=True,span=0.24,tag='gunter') # 비대칭: 오른팔 맨팔
    grad(sk,'arm_r',0,2,RUST,top=True,span=0.24,tag='gunter')
    for p in ('arm_r','arm_l'): grad(sk,p,8,10,STRAP,span=0.18)  # 가죽 팔목보호대
    legs(sk,TROUS,BOOT,5,'gunter')
    sk.f('leg_l','front').rect(1,3,2,4,dk(TROUS,0.26))


# ── 103 그레첸 — 빵집 ───────────────────────────────────────────────────────
def gretchen(sk):
    SKIN=(0xe6,0xbc,0x9e); HAIR=(0xbe,0x52,0x2f)
    DRESS=(0x40,0x5e,0x7c); APRON=(0xf1,0xeb,0xdd); BODICE=(0x96,0x3b,0x36)
    BOOT=(0x3c,0x32,0x2a); CAP=(0xf6,0xf2,0xe8); GOLD=(0xd4,0xa8,0x44)
    face(sk, SKIN, HAIR, eye_y=5, iris=(0x38,0x6e,0x4a), fringe=3,
         mouth=True, tag='gretchen', cap=CAP)
    ho=sk.f('head','front','outer')
    for y in range(4,8):                                      # 긴 머리(앞면 outer)
        ho.px(0,y,dk(HAIR,0.05*jit('gr',0,y))); ho.px(7,y,dk(HAIR,0.05*jit('gr',7,y)))
    bo=sk.f('body','front','outer')
    for y in range(0,4):
        bo.px(0,y,dk(HAIR,0.06*jit('gr2',0,y))); bo.px(7,y,dk(HAIR,0.06*jit('gr2',7,y)))
    grad(sk,'body',0,11,DRESS,top=True,bottom=True,span=0.30,tag='gretchen')
    fa=sk.f('body','front')
    fa.rect(2,0,5,1,SKIN)                                     # 네크라인=피부
    for y in range(2,6):
        for x in range(2,6):
            fa.px(x,y, mix(lt(BODICE,0.10), dk(BODICE,0.16), (y-2)/4))
    fa.col(2,dk(BODICE,0.36),2,6); fa.col(5,dk(BODICE,0.36),2,6)
    fa.px(3,3,GOLD); fa.px(4,4,GOLD)                          # 보디스 끈 고리(악센트)
    for y in range(6,12):                                     # 앞치마
        for x in range(2,6):
            fa.px(x,y, mix(lt(APRON,0.04), dk(APRON,0.14), (y-6)/6))
    fa.px(2,4,APRON); fa.px(5,4,APRON); fa.px(2,5,APRON); fa.px(5,5,APRON)
    sk.f('body','top').rect(2,0,2,3,APRON); sk.f('body','top').rect(5,0,5,3,APRON)
    trim(sk,'body',6,dk(APRON,0.40))
    arms(sk,SKIN,'gretchen')
    grad(sk,'arm_l',0,7,DRESS,top=True,span=0.24,tag='gretchen')
    grad(sk,'arm_r',0,4,DRESS,top=True,span=0.24,tag='gretchen')   # 비대칭
    for p,cy in (('arm_r',5),('arm_l',8)): grad(sk,p,cy-1,cy,APRON,span=0.12)
    legs(sk,DRESS,BOOT,3,'gretchen')
    for p in ('leg_r','leg_l'):
        grad(sk,p,4,6,APRON,span=0.14)                        # 앞치마 자락(가로 띠)
        seam(sk,p,7,APRON)
    sk.f('leg_r','front').rect(1,8,2,8,dk(DRESS,0.22))


if __name__ == '__main__':
    print('하이픽셀 기준 파일럿 v2')
    build('hyx_klaus', klaus)
    build('hyx_gunter', gunter)
    build('hyx_gretchen', gretchen)
