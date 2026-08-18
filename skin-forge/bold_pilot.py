#!/usr/bin/env python3
"""[기각됨 2026-08-18] 볼드(그래픽) 스타일 파일럿 — 쓰지 말 것.

  결과: 오너 판정 「훨씬 구려짐, 디테일이 다 사라졌잖아」. 산출물 삭제함.
  무엇이 틀렸나: 하이픽셀이 좋아 보이는 이유를 «플랫» 으로 요약하고 grain·folds·
  1px 악센트를 전부 걷어냈다. 그 결과 거리 판독성은 올랐지만 근접 밀도가 사라져
  전체적으로 더 나빠졌다. 밀도는 문제가 아니었다 — 유지한 채로 고쳤어야 했다.
  이 파일은 같은 실수를 반복하지 않으려고 기록으로만 남긴다.

  (원래 설명)
볼드(그래픽) 스타일 파일럿 — 클라우스·군터·그레첸 3명.

왜 새로 쓰나 (2026-08-18 오너 지적: "NPC 생긴 게 안 이쁘다, 기준은 하이픽셀")
  하이픽셀 NPC와 우리를 같은 배율로 나란히 놓고 보니 격차가 실력이 아니라 «룰» 이었다.
  하이픽셀 = 넓은 플랫 면 + 큰 명도 대비 + 큰 이목구비 = «그래픽».
  우리      = 전 면 grain/folds + 뮤트 + 1px 악센트 = «질감».
  NPC 는 3~10블록 밖에서 보이므로 질감은 전부 뭉개져 회갈색 덩어리가 된다.

  townsfolk 계열이 강제하는 form_fill(+speckle/folds)·뮤트 팔레트·악센트 2곳 제한이
  정확히 그 원인이라, 그 파이프라인 안에서는 다시 그려도 같은 결과가 나온다.
  그래서 이 파일은 «렌더 원칙만» 바꾼 별도 빌더다. 세계관 색(중세 항구)은 유지한다.

DESIGN DOCTRINE (기존 룰 대비 무엇을 뒤집었나)
  유지 : base 6면 불투명 · 순수검정 금지 · outer 가 눈을 덮지 않음 · 비대칭 1개 이상
       · 부피는 outer 에 · 몸을 감는 것은 strip · 결정적 빌드(crc32)
  폐기 : form_fill 강제  → block() 플랫 채움(면당 1색, 옆면만 한 단 어둡게)
        speckle/grain   → 전면 제거 (축소 시 노이즈로 뭉개지는 주범)
        뮤트 강제        → 채도는 유지하되 «인접 영역 명도차 ≥ 0.22» 를 강제
        1px 악센트       → 악센트는 최소 2px 폭, 띠는 최소 1행 전체
  신설 : seam()  두 의복이 맞닿는 곳에 1px 어두운 분리선 — 그래픽 룩의 핵심
        얼굴 이목구비를 크게: 흰자 2px + 눈동자 2px, 눈썹 1행 전체, 수염은 덩어리
"""
import pathlib, sys, zlib

sys.path.insert(0, '/Users/user/.claude/skills/npc-skin-forge/scripts')
import skinlib as S
from skinlib import mix

OUT = pathlib.Path(__file__).parent / 'out'
SIDES = ('front', 'back', 'left', 'right')


def dark(c, t):
    return mix(c, (0, 0, 0), t)


def lite(c, t):
    return mix(c, (255, 255, 255), t)


def block(sk, part, y0, y1, c, layer='base', top=False, bottom=False):
    """플랫 블록 채움. 앞=선언색 그대로, 옆=한 단 어둡게, 뒤=중간.
    form_fill 과 달리 세로 폴오프도 그레인도 없다 — 축소해도 색이 살아남는다."""
    tone = {'front': c, 'back': dark(c, 0.10), 'left': dark(c, 0.20), 'right': dark(c, 0.20)}
    for f in SIDES:
        fc = sk.f(part, f, layer)
        for y in range(y0, y1 + 1):
            fc.row(y, tone[f])
    if top:
        sk.f(part, 'top', layer).fill(lite(c, 0.08))
    if bottom:
        sk.f(part, 'bottom', layer).fill(dark(c, 0.28))


def seam(sk, part, y, c, layer='base'):
    """의복 경계 1px 분리선 — 몸을 한 바퀴 감는다."""
    st = sk.strip(part, layer)
    st.band(y, y, dark(c, 0.42))


def ring(sk, part, y0, y1, c, layer='base'):
    sk.strip(part, layer).band(y0, y1, c)


# ── 얼굴 ────────────────────────────────────────────────────────────────────
def face(sk, skin, hair, *, eye_y=4, iris=(0x2a, 0x36, 0x50), brow=None,
         beard=None, beard_y=6, moustache=False, fringe=2, sidehair=True):
    """이목구비를 «크게». 흰자 2px + 눈동자 2px = 눈 하나가 2x1 → 축소해도 남는다."""
    hd = sk.f('head', 'front')
    for f in SIDES:
        sk.f('head', f).fill(skin if f == 'front' else dark(skin, 0.12))
    sk.f('head', 'top').fill(hair)
    sk.f('head', 'bottom').fill(dark(skin, 0.30))
    # 머리카락: 정수리~이마. outer 에 얹어 머리통을 넓힌다(base 를 깎지 않는다)
    for y in range(0, fringe):
        hd.row(y, hair)
    ho = sk.f('head', 'front', 'outer')
    for y in range(0, fringe + 1):
        ho.row(y, hair)
    if sidehair:
        for y in range(fringe + 1, 7):
            ho.px(0, y, dark(hair, 0.10)); ho.px(7, y, dark(hair, 0.10))
    for f in ('left', 'right', 'back'):
        fo = sk.f('head', f, 'outer')
        for y in range(0, fringe + 2):
            fo.row(y, hair if f == 'back' else dark(hair, 0.12))
    sk.f('head', 'top', 'outer').fill(hair)
    # 눈썹 — 한 행 통째(1px 점 아님)
    bc = brow or dark(hair, 0.18)
    hd.rect(1, eye_y - 1, 2, eye_y - 1, bc); hd.rect(5, eye_y - 1, 6, eye_y - 1, bc)
    # 눈 — 흰자 바깥 + 눈동자 안쪽 (gaze=0, 오너 규칙)
    white = (0xf2, 0xef, 0xe6)
    hd.px(1, eye_y, white); hd.px(2, eye_y, iris)
    hd.px(5, eye_y, iris); hd.px(6, eye_y, white)
    # 입/수염 — 덩어리로
    if beard:
        for y in range(beard_y, 8):
            hd.row(y, beard, 1, 7)
        for f in ('left', 'right'):
            ff = sk.f('head', f)
            for y in range(beard_y, 8):
                ff.row(y, dark(beard, 0.12), 2, 8)
    if moustache:
        hd.rect(2, beard_y - 1, 5, beard_y - 1, beard or dark(hair, 0.05))
    if not beard:
        hd.rect(3, 6, 4, 6, dark(skin, 0.34))


def arms_skin(sk, skin, y0=0):
    for part in ('arm_r', 'arm_l'):
        block(sk, part, y0, 11, skin, top=True, bottom=True)


def legs(sk, c, boot, bootrows=3):
    for part in ('leg_r', 'leg_l'):
        block(sk, part, 0, 11 - bootrows, c, top=True)
        block(sk, part, 12 - bootrows, 11, boot, bottom=True)
        seam(sk, part, 12 - bootrows, c)


def build(name, fn):
    sk = S.new()
    fn(sk)
    sk.save(str(OUT / f'{name}.png'))
    print('  ✓', name)


# ── 7 클라우스 — 잡화 상점 ───────────────────────────────────────────────────
def klaus(sk):
    SKIN=(0xc9,0x9c,0x74); HAIR=(0x8a,0x7a,0x55)
    LINEN=(0xdc,0xd4,0xbe); WINE=(0x74,0x2b,0x30); APRON=(0xd6,0xc6,0xa2)
    TROUS=(0x4e,0x46,0x3c); BOOT=(0x2c,0x25,0x20); BRASS=(0xd4,0xa5,0x3c)
    face(sk, SKIN, HAIR, eye_y=4, moustache=True, fringe=2)
    block(sk,'body',0,11,LINEN,top=True,bottom=True)
    fa=sk.f('body','front')
    # ① 조끼 — 몸통 전체가 아니라 «어깨~허리», 가운데 V 트임으로 셔츠를 남긴다
    for y in range(1,8): fa.row(y,WINE,0,8)
    fa.rect(3,1,4,2,LINEN); fa.px(3,3,LINEN); fa.px(4,3,LINEN)   # V넥
    fa.col(0,dark(WINE,0.35),1,8); fa.col(7,dark(WINE,0.35),1,8) # 라펠 모서리
    block(sk,'body',1,7,WINE,layer='base')                        # 옆·뒤도 조끼
    for y in range(1,8): fa.row(y,WINE,0,8)
    fa.rect(3,1,4,2,LINEN); fa.px(3,3,LINEN); fa.px(4,3,LINEN)
    fa.col(0,dark(WINE,0.35),1,8); fa.col(7,dark(WINE,0.35),1,8)
    # ② 칼라 — 맨 위 1행 밝은 띠
    ring(sk,'body',0,0,LINEN)
    # ③ 앞치마 — «아래 절반만». 위까지 덮으면 색 이야기가 사라진다
    for y in range(8,12): fa.row(y,APRON,1,7)
    fa.px(1,7,APRON); fa.px(6,7,APRON)
    fa.rect(2,10,5,10,dark(APRON,0.22))          # 주머니 입구
    # ④ 허리 벨트 — 몸을 감는 진한 띠 + 2px 놋쇠 버클
    ring(sk,'body',7,7,dark(TROUS,0.25)); fa.rect(3,7,4,7,BRASS)
    arms_skin(sk,SKIN)
    for part in ('arm_r','arm_l'): block(sk,part,0,7,LINEN,top=True)
    block(sk,'arm_r',0,9,LINEN,top=True)                          # 비대칭: 왼쪽만 걷음
    for part,cy in (('arm_r',9),('arm_l',7)):                     # ⑤ 커프 — 대비 2px
        block(sk,part,cy-1,cy,WINE)
    legs(sk,TROUS,BOOT,bootrows=4)
    for part in ('leg_r','leg_l'): block(sk,part,7,7,lite(BOOT,0.30))   # 부츠 커프 = 밝은 띠
    sk.f('leg_r','front').rect(1,5,2,6,dark(TROUS,0.28))          # 무릎 패치(비대칭)


# ── 9 군터 — 대장간 ─────────────────────────────────────────────────────────
def gunter(sk):
    SKIN=(0xc0,0x8a,0x62); HAIR=(0x6b,0x60,0x55); BEARD=(0x8d,0x84,0x78)
    RUST=(0xb0,0x4e,0x2c); LEATH=(0x40,0x2c,0x1e); STRAP=(0x6a,0x48,0x2c)
    TROUS=(0x77,0x6a,0x58); BOOT=(0x2a,0x23,0x1c); IRON=(0xa8,0xae,0xb4)
    face(sk, SKIN, HAIR, eye_y=4, beard=BEARD, beard_y=7, moustache=True, fringe=2)
    block(sk,'body',0,11,RUST,top=True,bottom=True)
    fa=sk.f('body','front')
    # ① 가죽 앞치마 — 폭을 좁혀(x1~6) 양옆에 셔츠를 남긴다 = 세로 프레이밍
    for y in range(2,12): fa.row(y,LEATH,1,7)
    # ② 가슴받이 위쪽은 더 좁게 — 사다리꼴 실루엣
    fa.row(2,RUST,1,2); fa.row(2,RUST,5,7)
    # ③ 어깨끈 2px — top·back 까지 이어짐
    for y in (0,1): fa.px(2,y,STRAP); fa.px(5,y,STRAP)
    sk.f('body','top').rect(2,0,2,3,STRAP); sk.f('body','top').rect(5,0,5,3,STRAP)
    sk.f('body','back').rect(2,0,2,5,STRAP); sk.f('body','back').rect(5,0,5,5,STRAP)
    # ④ 허리 벨트 + 큰 쇠버클
    ring(sk,'body',7,7,dark(LEATH,0.40)); fa.rect(3,6,4,7,IRON)
    fa.row(11,lite(LEATH,0.22),1,7)              # 앞치마 밑단 하이라이트
    arms_skin(sk,SKIN)
    block(sk,'arm_l',0,4,RUST,top=True)                            # 비대칭: 오른팔만 맨팔
    block(sk,'arm_r',0,2,RUST,top=True)
    for part in ('arm_r','arm_l'):                                 # ⑤ 가죽 팔목 보호대
        block(sk,part,8,10,STRAP)
    legs(sk,TROUS,BOOT,bootrows=5)
    for part in ('leg_r','leg_l'): block(sk,part,6,6,lite(BOOT,0.32))
    sk.f('leg_l','front').rect(1,3,2,4,dark(TROUS,0.28))


# ── 103 그레첸 — 빵집 ───────────────────────────────────────────────────────
def gretchen(sk):
    SKIN=(0xe2,0xb8,0x9a); HAIR=(0xb8,0x4e,0x2e)
    DRESS=(0x3c,0x58,0x76); APRON=(0xf0,0xea,0xdc); BODICE=(0x8e,0x38,0x34)
    BOOT=(0x3a,0x30,0x28); CAP=(0xf4,0xf0,0xe6)
    face(sk, SKIN, HAIR, eye_y=5, fringe=3, iris=(0x35,0x5a,0x3e))
    # ① 제빵사 흰 캡 — 정수리 outer 를 덮는 큰 형태(역할이 실루엣으로 읽힌다)
    ho=sk.f('head','front','outer')
    for y in range(0,2): ho.row(y,CAP)
    sk.f('head','top','outer').fill(CAP)
    for f2 in ('left','right','back'):
        for y in range(0,2): sk.f('head',f2,'outer').row(y,dark(CAP,0.10) if f2!='back' else CAP)
    for y in range(4,8): ho.px(0,y,HAIR); ho.px(7,y,HAIR)          # 긴 머리(앞면 outer)
    bo=sk.f('body','front','outer')
    for y in range(0,4): bo.px(0,y,HAIR); bo.px(7,y,HAIR)
    block(sk,'body',0,11,DRESS,top=True,bottom=True)
    fa=sk.f('body','front')
    fa.rect(2,0,5,1,SKIN)                                          # ② 네크라인 = 피부
    fa.rect(2,2,5,5,BODICE); fa.col(2,dark(BODICE,0.35),2,6); fa.col(5,dark(BODICE,0.35),2,6)
    for y in range(6,12): fa.row(y,APRON,2,6)                      # ③ 앞치마 — 폭 x2~5
    fa.px(2,4,APRON); fa.px(5,4,APRON); fa.px(2,5,APRON); fa.px(5,5,APRON)
    sk.f('body','top').rect(2,0,2,3,APRON); sk.f('body','top').rect(5,0,5,3,APRON)
    ring(sk,'body',6,6,dark(APRON,0.42))                           # ④ 허리끈
    arms_skin(sk,SKIN)
    block(sk,'arm_l',0,7,DRESS,top=True)                           # 비대칭
    block(sk,'arm_r',0,4,DRESS,top=True)
    for part,cy in (('arm_r',5),('arm_l',8)): block(sk,part,cy-1,cy,APRON)
    legs(sk,DRESS,BOOT,bootrows=3)
    for part in ('leg_r','leg_l'):
        block(sk,part,4,6,APRON)                                   # ⑤ 앞치마 자락 = 가로 띠만
        seam(sk,part,7,APRON)
    sk.f('leg_r','front').rect(1,8,2,8,dark(DRESS,0.25))


if __name__ == '__main__':
    print('볼드 파일럿 빌드')
    build('bold_klaus', klaus)
    build('bold_gunter', gunter)
    build('bold_gretchen', gretchen)
