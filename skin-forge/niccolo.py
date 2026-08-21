#!/usr/bin/env python3
"""니콜로 — &b[상점] 니콜로, 상단마을 광장(1031.5, 67, -28.5), citizensId 176.

CHARACTER BRIEF  (prod npc.json / saves.yml / 이웃 실측에서 뽑은 근거)
  역할   shop=true. 대사 없음 → 역할 + 판매 목록 + 지역이 컨셉의 전부다.
  ★판매목록 31종이 곧 캐릭터다: 「감별사의 낚싯대 · 중개인의 낚싯대/작살 ·
    정산가의 낚싯대/작살 · 회계사의 낚싯대 · 무역상의 낚싯대 · 세공사의 작살 ·
    교역 릴/미끼/바늘/찌/합사줄 · 심해교역 작살 · 항해사의 · 행상인의 · 쾌속선 ·
    흑단목 · 용뼈 바늘 · 수정 찌 · 천공 와이어」
    → 「감별 · 중개 · 정산」. 물건을 만들지도 쓰지도 않고 «값을 매겨 넘기는» 사람.
  지역   상단마을(이탈리아풍 교역 도시). 이웃 실측 반경 40:
           24 로렌초(길드·버건디 코트+장부) · 88 빈센초(술집·와인 앞치마) ·
           166 마르첼로(랭킹·여성 버건디 코트) · 27 엔초(게시판·황토 튜닉) ·
           90 로사(생선·chalk 커틀) · 87 클라우디아(향신료·버건디 커틀) ·
           89 살바토레(그물·올리브 튜닉) · 143 지오반니(여관) · 91 마시모(짐꾼)
           + 82 마르코(버건디 더블릿+어깨망토+금브로치) · 97 실비아(감정 견습)
         ★사막 요소 금지. 유럽 르네상스 교역항이 맞다.
  포화   상단마을은 coat 3(로렌초·카를로·마르첼로) · apron 5 · tunic 6 · kirtle 다수,
         그리고 «버건디»가 4명. 니콜로가 코트나 버건디를 입으면 마을에 녹아 사라진다.

DESIGN SPEC  (그리기 전에 전부 선언)
  나이/체격  30대 후반, 마른 편. 짐꾼·대장장이(굵은 팔)와 마르코(잘 먹은 체구) 사이의
             «손이 깨끗하지만 물건은 직접 만지는» 체형
  실루엣     ★소매 없는 짙은 올리브 겉가운(무릎까지) + 그 아래 드러난 크림 리넨 소매
             + 오른팔은 팔꿈치 위까지 걷어 맨살 + 목에 놋쇠 확대경 + 가죽 벨트
             + 낮은 신발(2행, 부츠가 아니다 = 배를 타지 않는 사람)
             ▸ 마을 어느 NPC도 «소매 없는 겉옷 + 밝은 셔츠 소매»가 아니다. 정면 상반신에서
               어두운 몸통 / 밝은 두 팔 / 맨 오른 팔 = 세 값이 갈려 즉시 읽힌다
             ▸ 마르코와의 분리: 마르코=버건디 벨벳 + 한쪽 어깨 망토 + 모자(«부유한 무역주»)
               니콜로=올리브 무광 모직 + 맨머리 + 걷어붙인 소매(«실무 감별사»)
  팔레트     가운=짙은 올리브 모직 454a30(마을 팔레트 안, 짙은 쪽은 비어 있었다)
             / 셔츠=크림 리넨 c6bb9c / 앞섶 브레이드=황토금 a8813a(천, 금속 아님)
             / 호스=짙은 회갈 4a4238 / 신발·벨트·주머니=가죽 43352a
             ★금속 악센트는 정확히 2곳: 목 확대경 링 + 벨트 버클. 그 이상 금지
             ★가운(454a30)과 호스(4a4238)는 색상이 갈려(72° vs 40°) 하체가 한 덩어리로
               안 뭉친다. 명도만 다른 두 갈색을 겹치는 실패를 피한 것
  비대칭     ① 오른 소매만 팔꿈치 위까지 걷음(왼쪽은 손목까지 + 커프)
             ② 가운 오른쪽 자락만 벨트에 끼워 올림(오른 자락 3행 / 왼 자락 7행)
             ③ 걷어 올린 그 자리에 드러나는 오른 허벅지 저울추 주머니
             → ②와 ③이 인과로 묶인다: 주머니에 손이 닿게 자락을 걷은 것
  정체 모티프 ★목에 걸린 놋쇠 확대경(감별사의 도구). 가슴 로고 없음.
             장부는 마을에 이미 4명(로렌초·줄리아·실비아·로베르토)이라 쓰지 않는다
  얼굴       그을리지 않은 실내 피부 bd9068 · 밤갈색 머리(가르마 1px) · ★수염 없음
             (마르코=염소수염 / 로렌초=염소수염 / 빈센초=구레나룻 → 면도한 얼굴이 비어 있다)
             · 눈동자 안쪽(gaze=0, 기본) · 코 생략(기본) · 파란 눈 = 차가운 계산
             · 눈가 주름 없음(30대) · 좁은 턱

재질/조명  (references/lessons.md 19장) 모직·리넨은 정반사가 거의 없다 → ramp_lit 이 아니라
           matte(). 램프를 좁히는 것만으로는 부족해서 저장 직전 결과 픽셀의 명도·채도를
           기준색 쪽으로 압축한다. ★그 패스는 micro_light() «뒤»에 와야 한다.
"""
import colorsys
import pathlib
import sys
import zlib

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                                        # noqa: E402
from skinlib import Skin, all_boxes, ramp, ramp_lit         # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = zlib.crc32(b'niccolo') % 100000                      # ★hash() 금지: 빌드마다 달라진다


def matte(base, spread=0.22):
    """무광 직물(모직·리넨·캔버스) — 색상 회전 0, 채도 거의 고정, 명도 폭 좁게."""
    return ramp(base, spread=spread, hue=0.0, sat=0.03)


def leather(base, spread=0.34):
    """가죽 — 무광보다 «완전 조금만» 반사한다."""
    return ramp(base, spread=spread, hue=0.02, sat=0.06)


# 값 뒤 인라인 주석은 쉼표를 삼켜 구문오류를 낸다 — 주석은 줄 위에
P = dict(
    skin=ramp('bd9068'),
    # 램프가 넓으면 8px 머리 안에서 hair_lit 이 전 구간을 다 써 «머리 색이 반반»이 된다
    # (lessons.md 20장). spread 0.26 = 밝기비 1.6배.
    hair=ramp('5c4632', spread=0.26),
    brow=ramp('33261c'),
    gown=matte('454a30', 0.20),
    shirt=matte('c6bb9c', 0.24),
    braid=matte('a8813a', 0.26),
    hose=matte('4a4238', 0.24),
    strap=leather('43352a'),
    shoe=leather('3a2e24'),
    # 금속만 진짜 하이라이트를 갖는다 — 유일하게 ramp_lit 유지
    brass=ramp_lit('b08d3c'),
    glass=ramp_lit('9fb0ad'),
)

HUE_TOL = 0.055        # 올리브(72°)만 잡고 셔츠·황토·가죽(30~44°)은 건드리지 않는 폭


def compress_material(s, mid_hex, keep=0.36, sat_keep=0.60, tol=HUE_TOL, sat_min=0.10):
    """무광 재질의 «반사율»을 결과 픽셀에 실제로 계산해 넣는 마지막 패스.

    form_fill·speckle·shade_col_falloff·folds 는 램프 양끝을 향해 섞도록 강도가
    하드코딩돼 있어서, 램프를 좁혀도 명도 폭이 그대로 남는다(lessons.md 19장).
    그래서 램프가 아니라 결과 픽셀에 건다:
        v' = v_mid + (v - v_mid) x keep
        s' = s_mid + (s - s_mid) x sat_keep     ← speckle 의 «흰색 쪽 탈색»을 되돌린다
    hue 창으로 해당 재질만 고른다. 머리는 제외(눈동자가 창에 걸릴 수 있다).
    """
    mh, ms, mv = colorsys.rgb_to_hsv(*[int(mid_hex[i:i + 2], 16) / 255 for i in (0, 2, 4)])
    for key, (bx, by, w, h) in all_boxes().items():
        if key.split('.')[0] == 'head':
            continue
        for j in range(h):
            for i in range(w):
                px = s.im.getpixel((bx + i, by + j))
                if not px[3]:
                    continue
                hh, ss, vv = colorsys.rgb_to_hsv(*[c / 255 for c in px[:3]])
                d = abs(hh - mh)
                if min(d, 1.0 - d) > tol or ss < sat_min:
                    continue
                vv = max(0.04, min(1.0, mv + (vv - mv) * keep))
                ss = max(0.0, min(1.0, ms + (ss - ms) * sat_keep))
                rr, gg, bb = colorsys.hsv_to_rgb(hh, ss, vv)
                s.im.putpixel((bx + i, by + j),
                              (round(rr * 255), round(gg * 255), round(bb * 255), px[3]))


def lens_on_cord(s):
    """목에 걸린 놋쇠 확대경 — 감별사의 정체 모티프. 컴팩트한 덩어리라야 읽힌다
    (긴 대각 소품은 평평해져 '띠'로 보인다: lessons.md 9장)."""
    f = s.f('body', 'front', 'outer')
    st = P['strap']
    # 끈: 어깨 양쪽에서 가슴 가운데로 모이는 V. 목 뒤로도 이어야 «걸린 것»이 된다
    f.px(2, 1, st[2]); f.px(5, 1, st[2])
    f.px(3, 2, st[1]); f.px(4, 2, st[1])
    s.f('body', 'top', 'outer').px(2, 1, st[2])
    s.f('body', 'top', 'outer').px(5, 1, st[2])
    s.f('body', 'back', 'outer').px(2, 0, st[2])
    s.f('body', 'back', 'outer').px(5, 0, st[2])
    # 렌즈: 놋쇠 링 3px + 유리 1px. 4px 안에 링과 유리가 다 들어가야 «렌즈»다
    br = P['brass']
    f.px(3, 3, br[4]); f.px(4, 3, br[3])
    f.px(3, 4, br[2]); f.px(4, 4, P['glass'][4])
    # 렌즈 아래 한 줄 그늘 — 소품이 «천 위에 얹힌 것»으로 앉는다
    f.px(3, 5, P['gown'][1]); f.px(4, 5, P['gown'][1])


def build():
    s = Skin()
    skin, hair = P['skin'], P['hair']

    # ---- 머리: 피부 → 머리카락 → 얼굴 (뒤에 그린 것이 이긴다)
    g.head_base(s, skin, seed=SEED)
    g.ears(s, skin, y=4)
    # fringe=2 로 앞머리를 남긴다. 이마를 여는 스타일(crop/slick/sidepart)은 앞머리를
    # 포기하는 것과 같다(lessons.md 20장) — 단정함은 가르마 1px 로 낸다
    g.hair(s, hair, fringe=2, back=6, seed=SEED, part_x=5)
    g.face_shape(s, skin, jaw='narrow', temple=True)
    g.wrinkles(s, skin, crow=False, forehead=False)          # 30대 후반: 주름 없음
    g.face_marks(s, skin, kind='mole', seed=SEED)
    g.eyes(s, 'ece8dd', ramp(g.IRIS['blue']), y=4, gaze=0, iris_idx=1, socket=skin[1])
    g.brow(s, P['brow'][2], y=3)
    g.mouth(s, skin, y=6, w=2)
    # ★수염 없음 = 마을 남성들과 갈리는 지점. 대신 턱선을 face_shape 이 잡아 준다

    # ---- base 레이어는 6면 전부 불투명하게 끝낸다(구멍은 인게임에서 투명 덩어리)
    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07, hem=False)
    # 오른 소매만 팔꿈치 위까지 걷음 — 비대칭 ①. 걷은 아래는 맨살로 덮어야 «팔»이 된다
    g.sleeves(s, P['shirt'], y0=0, y1=9, rolled=('arm_r', 5), skin_r=skin,
              seed=SEED, grain=0.07)
    g.hands(s, skin, rows=2)
    g.pants(s, P['hose'], y0=0, y1=9, seed=SEED)
    g.boots(s, P['shoe'], rows=2, toe=True, cuff=True)       # 낮은 신발: 배를 타지 않는다

    # ---- 겉가운: 소매가 없다. 몸통과 자락만 outer, 팔은 base(셔츠)가 그대로 보인다
    gw = P['gown']
    s.form_fill('body', gw, 0, 11, layer='outer', base_idx=3, top=True)
    s.speckle('body', gw, 0, 11, layer='outer', density=0.07, seed=SEED)
    s.shade_col_falloff('body', gw, 0, 11, layer='outer')
    s.folds('body', 2, 10, gw, layer='outer', cols=(1, 6), seed=SEED)
    s.folds('body', 3, 10, gw, layer='outer', cols=(2, 5), face='back', seed=SEED + 3)
    for fname, cx in (('right', 1), ('left', 2)):            # 옆에서도 천으로 읽히게
        s.folds('body', 2, 10, gw, layer='outer', cols=(cx,), face=fname,
                seed=SEED + 5)
    s.hem('body', 11, gw, layer='outer')

    # 앞 V 트임: 어깨 바로 아래를 비워 크림 셔츠가 드러난다 = 겉가운으로 읽히는 열쇠
    fo = s.f('body', 'front', 'outer')
    for x in (2, 3, 4, 5):
        fo.px(x, 0, (0, 0, 0, 0), 0)
    fo.px(3, 1, (0, 0, 0, 0), 0); fo.px(4, 1, (0, 0, 0, 0), 0)
    # 진동(팔 구멍) 그늘 — 소매 없는 옷은 여기가 어두워야 어깨가 «끝난» 것으로 보인다
    fo.col(0, gw[1], 0, 3); fo.col(7, gw[1], 0, 3)
    fo.col(4, gw[1], 6, 11); fo.col(3, gw[4], 6, 11)         # 앞여밈은 «천»으로만

    # ★황토금 브레이드는 옷의 «테두리»로만 쓴다. 1차 시안은 가슴 한가운데에 세로 점선
    #   기둥을 세웠는데, 8px 가슴에 채도 높은 황토가 들어가자 «노란 지퍼»가 되고
    #   확대경까지 그 기둥의 일부로 먹혔다(실측 v1). 테두리로 돌리면 소매 없는 재단이
    #   오히려 더 또렷해지고 렌즈가 가슴에서 혼자 남는다.
    #   ★2차에서 V 칼라에도 브레이드를 둘렀다가 걷어냈다: 자락 테두리 2줄 + 칼라 3점
    #     + 벨트 버클 + 확대경 = 금빛이 다섯 곳으로 흩어져 산만했다(자기비평 3패스).
    #     지금은 자락 테두리 하나로 몰아 «옷단 장식»이라는 한 가지 사실만 말한다.
    br = P['braid']
    fo.px(2, 1, gw[4]); fo.px(5, 1, gw[4])                   # V 트임 가장자리는 «천»으로
    fo.px(3, 2, gw[4]); fo.px(4, 2, gw[1])

    lens_on_cord(s)

    # ---- 벨트 + 걷어 올린 자락(비대칭 ②) + 저울추 주머니(비대칭 ③)
    g.belt(s, P['strap'], y=7, accent=P['brass'], layer='outer')
    tails = {'leg_l': 7, 'leg_r': 3}                         # 오른쪽만 벨트에 끼워 올림
    for part, to in tails.items():
        s.form_fill(part, gw, 0, to, layer='outer', base_idx=3)
        s.speckle(part, gw, 0, to, layer='outer', density=0.07, seed=SEED + len(part))
        s.shade_col_falloff(part, gw, 0, to, layer='outer')
        s.hem(part, to, gw, layer='outer')
        # ★자락 끝에 황토 테두리 — 좌우 길이차(7행 vs 3행)가 «색이 있는 선»으로 갈려
        #   정면에서 비대칭 ②가 실제로 읽힌다(선 없이는 같은 올리브라 뭉친다)
        g.trim(s, br, part=part, rows=(to,), layer='outer', base_idx=2)
    # 걷어 올린 쪽 자락 끝을 접힌 것처럼 한 단 밝게(끼워 넣은 티)
    s.f('leg_r', 'front', 'outer').row(2, gw[4])
    g.pouch(s, P['strap'], part='leg_r', face='front', x=1, y=5, w=2, h=3,
            metal=P['strap'])                                 # 금속 악센트는 이미 2곳이다

    # ---- 저장: micro_light 먼저, 그 «뒤»에 재질 압축(lessons.md 19장)
    s.micro_light()
    s._microed = True
    compress_material(s, '454a30', keep=0.36, sat_keep=0.60)

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'niccolo.png'))


if __name__ == '__main__':
    print(build())
