#!/usr/bin/env python3
"""wsi1212 — 플레이어 본인 스킨. 바르칸 열도 선주(船主).

CHARACTER BRIEF
  NPC 가 아니라 플레이어 스킨이므로 npc_brief 근거는 없다. 대신 '서버 주인의 아바타'라는
  자리 자체가 컨셉이다: 열도의 배를 소유한 사람 — 노동하는 어부도, 칼을 쥔 병사도 아니다.
  ★기존 코트 NPC 와의 충돌 회피가 이 스킨의 최대 제약이다(전부 남청 롱코트다):
    발데마르171 남청 모직 롱코트 + 포도주 새시 + 낡은 은
    군나르132  네이비 오일스킨(항만장)
    하르트무트175 검푸른 방수코트 + 녹청 목보호대 / 테클라174 먹청 방수코트 + 표본가방
  → 색으로는 못 가른다. **재단**으로 가른다: 세운 칼라 + 이중여밈 금단추 2열 +
    어깨 밧줄 코일. 위 넷 중 누구도 이중여밈·금단추·밧줄이 없다.
  ★갑옷·문장·투구 금지(발렌틴58 사고): 선주는 권력자가 아니라 소유자다. 부유함은
    금의 양이 아니라 '천의 질'(안감 노출·정돈된 재단)로 말한다.

DESIGN SPEC
  나이/체격  30대, 단정하고 날렵한 체격. 노동 흔적(패치·얼룩) 없음 — 배를 타지만 그물을
             당기는 사람은 아니다
  실루엣     세운 칼라의 짙은 잉크 남색 이중여밈 롱코트(무릎 자락) + 왼어깨 밧줄 코일
             + 허리 가죽 벨트 + 방수 장화. 모자 없음(얼굴이 보여야 한다 = 유저 요청)
  팔레트     코트=잉크 남색 1e2a48(발데마르 35475b·군나르 2b3a52 보다 어둡고 청자 쪽으로
             빼서 나란히 서도 갈린다) / 안감=크림 c3b498(어두운 단색의 숨구멍, 1px 만)
             / 셔츠=바랜 리넨 / 바지=캔버스 회갈 544c42 / 장화=젖은 진갈 3b2f26
             ★악센트는 금 2곳뿐 — 이중여밈 단추열 + 벨트 버클. 그 외 금 금지
             ★코트(남색) → 바지(회갈) → 장화(진갈) 3단 값 분리: 하체가 한 덩어리로
               뭉치는 사고(garments.md) 차단
  비대칭     왼어깨 밧줄 코일 · 오른소매만 커프 접어 안감 노출 · 오른 허벅지 가죽 파우치
  얼굴       그을린 피부, 짙은 흑갈 옆가르마(sidepart), **무수염**(마을 어부 노인들이
             전부 수염이라 이것만으로 갈린다), 회청 눈동자 안쪽 응시(gaze=0),
             코 없음(기본), 주름 없음(젊다)
  정체 모티프 가슴 로고·문장 없음. 정체성은 이중여밈 재단 + 밧줄 + 금단추 2열

LAYER 정책 (2026-08-21 유저 지시: "머리카락·장식은 위쪽 레이어 적극 활용")
  이 해상도에서 «부피를 더한다» = outer 레이어에 얹는다(lessons.md 3장). outer 박스는
  1.125배로 부풀려 렌더되므로, 같은 픽셀이라도 base 에 칠하면 «그림»이고 outer 에 얹으면
  «두께»가 된다. 그래서 파트마다 옷감과 장식의 레이어를 갈랐다:
    head  base = 두상·얼굴·머리카락 밑칠 / outer = 머리카락 부피 전부(앞머리 3행·정수리·
          옆·뒤) + 얼굴을 감싸는 옆머리 프레임(x0·x7, 6행까지)
    body  base = 코트 본체(속옷 위에) / outer = 세운 칼라·라펠·금단추·밧줄·벨트·옷단
    arm   base = 코트 소매          / outer = 왼어깨 밧줄 코일 · 오른소매 접힘 커프
    leg   base = 바지·장화          / outer = 코트 자락(coat() 가 여기 올린다)·파우치
  ★그림자는 반대다 — 벨트·칼라가 드리우는 그늘은 그 «아래 옷»(base)에 shade_ring 으로
    넣는다. outer 에 걸면 투명 픽셀은 건너뛰므로(skinlib.shade_ring) 조용히 사라진다.
"""
import pathlib
import sys
import zlib

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                                  # noqa: E402
from skinlib import Skin, ramp, ramp_lit              # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = zlib.crc32(b'wsi1212') % 100000                # ★hash() 금지: 빌드마다 달라진다

# ── 재질별 램프 (2026-08-21 유저 지적) ────────────────────────────────────────
# "조명 효과가 너무 쎄다. 빛받은곳은 남색에서 벗어남. 남색 코트는 원래 빛 반사를 안 하는
#  재질인데(완전 조금만) 그 계산이 빠졌다."
# 원인은 팔레트가 아니라 램프의 «조명 모델»이었다. 기본 ramp(hue=0.05, sat=0.16) 은
#   ① 그늘 쪽 색상을 hue×DARK_HUE_TURN(2.6) 만큼 «따뜻한 쪽»으로 돌린다 → 남색(222°)이
#      200° 청록으로 빠진다(실측: 현행 코트 램프의 색상 폭 22°)
#   ② 하이라이트에서 채도를 깎는다 → 밝은 쪽이 «바랜 하늘색»
# 노랑·황토를 진흙에서 구하려고 넣은 보정이라 그쪽에는 맞지만, 무광 남색 모직에는 틀렸다.
# 재질을 반사율로 갈라 쓴다 — 금속만 진짜 하이라이트를 갖는다.


def matte(base, spread=0.22):
    """무광 직물(모직·오일천·리넨·캔버스·마) — 색상 회전 0, 채도 거의 고정, 명도 폭 좁게."""
    return ramp(base, spread=spread, hue=0.0, sat=0.03)


def leather(base, spread=0.34):
    """가죽 — 무광보다 조금만 반사한다(«완전 조금만»). 색상은 2°대만 움직인다."""
    return ramp(base, spread=spread, hue=0.02, sat=0.06)


# 값 뒤 인라인 주석은 쉼표를 삼켜 구문오류를 낸다 — 주석은 줄 위에
P = dict(
    skin=ramp('bb8a63'),
    # ★머리색은 두 번 올렸다. 이유는 취향이 아니라 «조명 모델»이다: hair() 는 옆·뒤를
    #   광원(2,1)에서 6px 이상 떨어진 것으로 계산해 램프 [0]~[1] 에 박아 넣는다. 어두운
    #   갈색(33291f·48382a)을 넣으면 그 두 단이 281a19 급이 되어 머리 옆·뒤가 «검은 헬멧»이
    #   된다(head zoom 실측). 밤색 6b5233 이면 [0]=4b2d27 로 갈색으로 읽힌다.
    hair=ramp('6b5233', spread=0.46),
    # 눈썹은 얼굴에서 가장 어두운 선이어야 한다 — 밤색 머리 램프로 그리면 흐려진다
    brow=ramp('35251b'),
    # 무광 모직 남색. ramp_lit 이 아니라 matte 다 — 앞면에 보이는 색은 한 단 위인 [3]
    #   (26345b) 이고, 다섯 단이 전부 224° 남색에 머문다(색상 폭 1°, 명도 폭 16)
    coat=matte('202c4e', 0.20),
    lining=matte('b3a488', 0.22),
    shirt=matte('8e8778', 0.24),
    # ★캔버스 바지는 장화와 두 단 이상 벌려야 하체가 한 덩어리로 안 뭉친다(garments.md)
    pants=matte('6d6455', 0.24),
    rope=matte('7e6c4c', 0.26),
    boot=leather('3f3225'),
    strap=leather('463726'),
    # 금속만 진짜 하이라이트를 갖는다 — 유일하게 ramp_lit 유지
    gold=ramp_lit('c19a3e'),
    iris=ramp(g.IRIS['grey']),
)


def matte_reflectance(s, mid_hex, keep=0.35, sat_keep=0.55, hue_win=(0.52, 0.74),
                      sat_min=0.25):
    """무광 재질의 «반사율»을 실제로 계산해 넣는 마지막 패스.

    램프를 좁혀도 조명이 센 건 그대로였다(실측: 색상 폭은 22°→3° 로 잡혔는데 명도 폭은
    24 그대로 — 가장 밝은 코트 픽셀이 기준색보다 +48%). 이유는 그림자·그레인·폴오프를
    넣는 함수들(form_fill·speckle·shade_col_falloff·folds)이 램프 양끝을 향해 섞도록
    «강도가 하드코딩»돼 있어서다. 그래서 램프가 아니라 «결과 픽셀»에 재질 계수를 건다:

        v' = v_mid + (v - v_mid) × keep        (확산반사만 남기는 비율)
        s' = s_mid + (s - s_mid) × sat_keep    (★채도도 되돌린다)

    ★채도까지 손대는 이유: speckle 이 «흰색 쪽»으로 섞어서 밝은 픽셀의 채도를 깎는다
      (실측: 어깨 윗면 명도 52·채도 43 vs 기준 31·58). 유저 지적 "빛받은곳은 남색에서
      벗어남"의 절반은 명도가 아니라 이 «탈색»이었다. 무광 천의 하이라이트는 그냥
      «조금 밝은 남색»이어야 한다.
    무광 모직은 정반사가 거의 없다 → keep 0.30(최대 +20% 선). 가죽·금속은 이 패스를
    통과시키지 않는다(hue 창으로 남색만 — 서버 팔레트에 남색은 코트뿐이다).
    ★머리는 제외한다: 회청 눈동자(200°)가 창에 걸린다.
    """
    import colorsys
    from skinlib import all_boxes
    _mh, _ms, mid = colorsys.rgb_to_hsv(*[int(mid_hex[i:i + 2], 16) / 255
                                          for i in (0, 2, 4)])
    for key, (bx, by, w, h) in all_boxes().items():
        if key.split('.')[0] == 'head':
            continue
        for j in range(h):
            for i in range(w):
                px = s.im.getpixel((bx + i, by + j))
                if not px[3]:
                    continue
                r, g, b = [c / 255 for c in px[:3]]
                hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
                if not (hue_win[0] < hh < hue_win[1] and ss > sat_min):
                    continue
                vv = max(0.04, min(1.0, mid + (vv - mid) * keep))
                ss = max(0.0, min(1.0, _ms + (ss - _ms) * sat_keep))
                rr, gg, bb = colorsys.hsv_to_rgb(hh, ss, vv)
                s.im.putpixel((bx + i, by + j),
                              (round(rr * 255), round(gg * 255), round(bb * 255), px[3]))


def stand_collar(s):
    """세운 칼라 + 라펠 + 안감 1px 숨구멍 — 전부 outer 에 얹어 «두께»로 세운다.

    ★칼라를 링 전체(8폭)에 그리면 몸을 감는 줄무늬가 된다(garments.md) → 목 주변만.
      front/back x2~5 + 좁은 옆면 x1~2 = 목을 한 바퀴. 그 그림자는 base 에 넣는다.
    ★안감을 앞섶 전체에 세우면 가슴에 흰 세로 줄무늬가 생긴다(실측 v2) → 1px 숨구멍.
    """
    coat, lin = P['coat'], P['lining']
    for fname in ('front', 'back'):
        f = s.f('body', fname, 'outer')
        f.row(0, coat[4], 2, 5)                             # 세운 칼라 — 윗행이 빛을 받는다
        f.row(1, coat[2], 2, 5)                             # 칼라 몸통(두 행이라 '섰다'로 읽힘)
    for fname in ('right', 'left'):                         # 좁은 옆면으로 목을 한 바퀴
        s.f('body', fname, 'outer').rect(1, 0, 2, 1, coat[3])
    s.f('body', 'top', 'outer').rect(2, 1, 5, 2, coat[4])
    f = s.f('body', 'front', 'outer')
    for i in range(3):                                      # 라펠 — outer 라서 접힌 두께가 산다
        f.px(3 - i, i, coat[4]); f.px(4 + i, i, coat[3])
    #   ★안감 숨구멍은 턱 밑 중앙에 놓으면 «베이지 이름표»로 보인다(렌더 실측)
    #     → 라펠 접힘 모서리(x2)에 1px = 겹친 앞판 안쪽이 살짝 드러난 것
    f.px(2, 2, lin[2])
    #   ★칼라가 드리우는 그늘은 «아래 옷»에 — outer 는 여기가 비어 있어 그냥 사라진다.
    #     ring 전체가 아니라 칼라가 실제로 덮은 폭(x2~5)만. 8폭을 다 칠하면 가슴을
    #     감는 줄무늬가 된다. 색은 코트 자기 램프에서 뽑아 팔레트가 안 늘어나게 한다
    #     (mix 기반 AO 를 남발하면 «눈대중 색조»가 쌓여 audit 이 경고한다 — 실측 249색)
    for fname in ('front', 'back'):
        s.f('body', fname).row(2, coat[1], 2, 5)


def double_breasted(s):
    """이중여밈 앞판 + 금단추 2열 — 다른 남청 코트 4명과 가르는 핵심 재단.

    ★앞판을 outer 에 얹는 이유: 이중여밈은 실제로 «천이 한 겹 겹쳐 덮이는» 재단이다.
      outer 박스가 1.125배라 겹친 두께가 인게임에서 그대로 보인다(base 에 칠하면 무늬).
    ★렌더 실패 2건 기록:
      ① 단추 3개×2열 + 벨트 버클이 가슴에서 «금 사다리»로 뭉쳤다 → 2개×2열 + 벨트 행 회피
      ② 코트를 base 로 내린 뒤 g.buttons() 가 «아무것도 안 찍었다» — 그 함수는 대상
         픽셀의 알파를 보고 건너뛴다(빈 outer 였다). 앞판을 먼저 깔아야 단추가 얹힌다.
    """
    coat = P['coat']
    f = s.f('body', 'front', 'outer')
    for y in range(0, 12):                                  # 겹쳐 덮은 앞판
        for x in range(2, 6):
            f.px(x, y, coat[3] if (x + y) % 5 else coat[2])  # 결 — 규칙적 줄이 안 생기게
    f.col(2, coat[4], 0, 11)                                 # 덮은 쪽 접힘 — 빛을 받는 모서리
    f.col(5, coat[1], 0, 11)                                 # 덮인 쪽 — 그늘로 두께를 만든다
    s.f('body', 'top', 'outer').rect(2, 0, 5, 1, coat[4])    # 어깨 위로 이어짐
    #   단추 배치는 세 번 고쳤다(전부 렌더 실측):
    #     y3·y6 → 아래 단추가 벨트 버클과 붙어 «금 뭉치»
    #     y3·y5 를 g.buttons 로 → 금·그늘·금·그늘이 연속돼 «금 사슬 두 줄»
    #     확정: 위 단추만 그늘을 달고(입체), 아래 단추는 그늘 없이 한 점 → 금 4px 뿐
    gold = P['gold']
    for x in (2, 5):
        f.px(x, 3, gold[4]); f.px(x, 4, gold[1])            # 위 단추 + 그늘
        f.px(x, 6, gold[3])                                 # 아래 단추 (그늘 없음)


def shoulder_rope(s):
    """왼어깨에 걸친 밧줄 코일.

    ★긴 대각 소품(노)은 8x12 가슴에서 평평해져 '베이지색 띠'로 읽힌다(lessons.md 9장).
      컴팩트한 덩어리로만 읽힌다 → 어깨에 얹힌 코일.
    ★끈·밧줄은 top 면과 back 면까지 이어져야 한다. 어깨에서 끊기면 즉시 가짜.
    ★body front 는 x0=캐릭터 오른쪽, x7=왼쪽. back 은 좌우가 뒤집힌다(x0=왼쪽).
    """
    r = P['rope']
    s.f('arm_l', 'top', 'outer').fill(r[4])
    #   ★1차 렌더 실패: 4면을 꽉 찬 2행 사각으로 채워 «어깨에 얹은 갈색 각목»이 됐다.
    #     꼬임 대비를 [4]↔[2] 로 벌리고, 바깥쪽 아래 코너를 비워 둥글게 깎는다.
    for fname in ('front', 'back', 'right', 'left'):
        f = s.f('arm_l', fname, 'outer')
        for x in range(f.w):
            f.px(x, 0, r[4] if x % 2 == 0 else r[2])        # 꼬임 = 한 픽셀씩 교차
            f.px(x, 1, r[2] if x % 2 == 0 else r[1])        # 아래 가닥 + 접지 그림자
        if fname in ('front', 'back'):                      # 코너를 깎아 각목 방지
            f.px(f.w - 1 if fname == 'front' else 0, 1, (0, 0, 0, 0))
    bf = s.f('body', 'front', 'outer')                      # 가슴 왼쪽으로 넘어옴
    for y in range(0, 3):
        bf.px(7, y, r[3] if y % 2 == 0 else r[2])
    bf.px(6, 0, r[3]); bf.px(6, 1, r[1])
    bb = s.f('body', 'back', 'outer')                       # 등 왼쪽(back 은 x0)
    for y in range(0, 3):
        bb.px(0, y, r[2] if y % 2 == 0 else r[1])
    s.f('body', 'top', 'outer').px(7, 0, r[4])


def soften_sideframe(s):
    """옆머리 프레임(x0·x7)이 «검은 기둥»이 되는 것을 막는다.

    ★2차 렌더 실측: male_hair_style 의 sideframe 은 hair_lit 을 쓰는데, 광원 반대편(x7)에서
      281a19(최대채널 40 = 거의 검정)까지 떨어져 얼굴 옆에 검은 막대 두 개가 섰다.
      얼굴·피부에 닿는 것은 램프 [2]~[4] 만 쓴다(lessons.md 1장). 광원측(x0)을 한 단
      밝게 둬서 좌우 대칭도 피한다.
    """
    h = P['hair']
    hf = s.f('head', 'front', 'outer')
    #   ★유저 지시(2026-08-21)대로 프레임을 «채운다» — 예전엔 이미 칠해진 픽셀의 색만
    #     고쳤다. x0·x7 은 얼굴 바깥 열이라 눈(x1·x6)을 가리지 않으면서 outer 에 얹히면
    #     머리통이 실제로 넓어진다(base 에 칠하면 반대로 얼굴이 깎인다 — lessons.md 3장).
    for y in range(0, 7):
        hf.px(0, y, h[3] if y < 4 else h[2])                # 광원측은 밝게
        hf.px(7, y, h[2] if y < 4 else h[1])                # 반대편은 한 단 어둡게
    # ★sidepart 는 가벼운 쪽 깊이를 0 까지 떨어뜨려(depth = safe - |x-heavy|//2) x6·x7 의
    #   0~2 행을 통째로 피부로 만든다 → 8x8 에서 «한쪽만 벗겨진 이마»로 읽혔다(head zoom
    #   실측). 맨 윗행 하나는 항상 머리로 남겨 헤어라인이 3→1 행으로 «사선»으로 흐르게 한다.
    for x, idx in ((4, 3), (5, 3), (6, 2), (7, 2)):
        hf.px(x, 0, h[idx])


def build():
    s = Skin()

    # ---- 머리: 피부 → 머리카락 → 얼굴 피처 (나중에 그린 것이 이긴다)
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    #   fringe=3 → 앞머리가 outer 3행(눈썹 행 위까지). hair() 가 hair_volume 으로
    #   정수리·옆·뒤 부피를 전부 outer 에 얹는다(volume=True 가 기본)
    g.hair(s, P['hair'], fringe=3, back=7, seed=SEED, part_x=5)
    g.male_hair_style(s, P['hair'], P['skin'], style='sidepart', seed=SEED, eye_y=4)
    soften_sideframe(s)
    g.face_shape(s, P['skin'], jaw='square', temple=True)
    g.face_marks(s, P['skin'], kind='ruddy', seed=SEED)     # 바닷바람에 튼 볼
    #   흰자는 off-white — 순백에 가까우면 8x8 에서 번져 «왕눈이»가 된다(skin-craft.md)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, iris_idx=1)
    g.brow(s, P['brow'][2], y=3, weight=1, angle=1)         # 살짝 내려간 눈썹 = 단호함
    g.mouth(s, P['skin'], y=6, w=2)
    # 무수염 · 무주름 · 코 없음 — 마을 어부 노인들과 갈리는 지점이므로 의도적으로 비운다

    # ★눈 지워짐 가드 (lessons.md 13장) — 머리쓰개/머리카락 뒤에 둬야 의미가 있다
    _ef = s.f('head', 'front')
    if sum(1 for x in (1, 2, 5, 6) if max(_ef.get(x, 4)[:3]) > 150) < 2:
        raise ValueError('눈이 지워졌다 (eye_y=4)')

    # ---- base 레이어: 속옷 → 바지 → 장화 (6면 전부 불투명하게 끝낸다)
    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, grain=0.08)
    g.sleeves(s, P['shirt'], y0=0, y1=11, seed=SEED, grain=0.08)
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['pants'], y0=0, y1=7, seed=SEED, grain=0.12)
    g.boots(s, P['boot'], rows=4, toe=True, cuff=True)

    # ---- 코트 «옷감»은 base 로. outer 는 장식 전용으로 비워 둔다(LAYER 정책)
    #   ★coat() 는 몸통을 layer 인자대로 그리지만 «자락(tails)»은 항상 다리 outer 에
    #     올린다 — 그게 원래 의도(자락이 부피로 떠야 코트로 읽힌다)라 그대로 쓴다.
    g.coat(s, P['coat'], y0=0, hem=11, tails=3, lapel=True, seed=SEED, layer='base')
    s.f('body', 'bottom').fill(P['coat'][1])                # base 6면 불투명 유지
    g.neck_shadow(s, P['coat'], layer='base')

    g.sleeves(s, P['coat'], y0=0, y1=9, layer='base', seed=SEED + 3, grain=0.08)
    for _i, _part in enumerate(('arm_r', 'arm_l')):
        #   ★소매가 «남색 판자»로 보이지 않게: 세로 폴오프(원통 곡률) + 비대칭 주름 1줄.
        #     팔에 톤이 없으면 무슨 짓을 해도 허접해 보인다(skin-craft.md 관측치)
        s.shade_col_falloff(_part, P['coat'], 0, 9, layer='base')
        s.folds(_part, 2, 8, P['coat'], layer='base', cols=(1,) if _i == 0 else (2,),
                seed=SEED + _i)
    g.hands(s, P['skin'], rows=2)                           # 소매를 base 로 덮은 뒤 손 복구

    # ---- outer 레이어: 전부 «얹히는 것»만 (칼라·라펠·단추·밧줄·벨트·커프·파우치)
    double_breasted(s)                                      # 앞판 → 칼라 순서(칼라가 위)
    stand_collar(s)
    #   비대칭 ①: 오른소매만 커프를 접어 안감이 보인다.
    #   ★커프를 밝은 안감으로 한 바퀴 두르면 '소매가 맨살로 끝난' 것처럼 보인다
    #     (garments.md 실측 v2) → 앞면 안쪽 2px 만.
    #   커프를 outer 에 얹으면 «접어 올린 두께»가 실제로 튀어나온다
    _cf = s.f('arm_r', 'front', 'outer')
    for _x in range(4):
        _cf.px(_x, 8, P['coat'][4] if _x % 2 == 0 else P['coat'][3])
    _cf.px(1, 9, P['lining'][2]); _cf.px(2, 9, P['lining'][1])
    for _fn in ('right', 'left', 'back'):
        s.f('arm_r', _fn, 'outer').row(8, P['coat'][2])
    s.ao_row('arm_r', 9, P['coat'], layer='base', drop=2)   # 커프가 소매에 드리우는 그늘

    #   벨트·옷단은 outer 에 얹어 실제로 «둘러진» 두께가 생긴다. ao=False 로 두고
    #   그늘은 base(코트)에 직접 — outer y8 은 비어 있어 shade_ring 이 건너뛴다
    g.belt(s, P['strap'], y=7, accent=P['gold'], layer='outer', ao=False)
    s.band('body', 8, 8, P['strap'][1], layer='outer')      # 벨트 아래 가죽 두께
    s.ao_row('body', 9, P['coat'], layer='base', drop=2)    # 벨트가 코트에 드리우는 그늘
    s.band('body', 11, 11, P['coat'][4], layer='outer')     # 코트 옷단 립(아래에서 보인다)
    shoulder_rope(s)                                        # 비대칭 ②
    #   비대칭 ③: 오른 허벅지 파우치. 코트 자락(leg outer 0~2) 아래에 놓는다.
    #   ★파우치를 금속 램프로 전부 채우면 다리에 금괴를 붙인 꼴이 된다 → 가죽 + 버클 1px
    g.pouch(s, P['strap'], part='leg_r', face='front', x=1, y=3, w=2, h=3,
            metal=P['gold'])

    # ---- 마지막: 미세 계조 → 재질 계수 (순서가 중요하다)
    #   ★skinlib.save() 는 micro_light() 를 «자동으로» 부른다. 그게 재질 압축 뒤에 오면
    #     눌러 놓은 하이라이트를 다시 올려 버린다 — 실측: 어깨 윗면이 압축 결과 243156
    #     에서 3a4667(명도 +14) 로 되살아나 «압축이 안 먹는» 것처럼 보였다. 원인을 찾는 데
    #     제일 오래 걸린 대목이다. _microed 플래그가 save() 의 중복 호출을 막아 준다.
    s.micro_light()
    s._microed = True
    matte_reflectance(s, '202c4e', keep=0.35, sat_keep=0.55)

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'player_wsi1212.png'))


if __name__ == '__main__':
    print(build())
