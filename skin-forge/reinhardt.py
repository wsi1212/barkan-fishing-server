#!/usr/bin/env python3
"""라인하르트 — &b[상점] 라인하르트, 왕도 장터(456.5, 90, 235.5), citizensId 177.

CHARACTER BRIEF  (prod npc.json / saves.yml / 이웃 실측에서 뽑은 근거)
  역할   shop=true. 대사 없음 → 역할 + 판매 목록 + 지역이 컨셉의 전부다.
  ★판매목록 16종이 곧 캐릭터다: 「근위 낚싯대/작살 · 왕립 순찰 낚싯대/작살 ·
    왕립 서고 낚싯대/작살 · 왕실 낚싯대/작살 · 왕도 상회 낚싯대/작살 ·
    바르칸 릴/미끼/바늘/줄/찌 · 다이아 작살」
    → 전 품목이 «왕실 지급품». 니콜로(교역·감별)와 달리 이 사람은 왕실에 물건을
      납품하고 그 물건을 검수해 내주는 «조달관»이다.
  지역   왕도(왕실·격식, 게르만풍). 이웃 실측 반경 40:
           120 프리츠(관청 서기) · 164 구스타프(랭킹·감청 코트+놋쇠·노인) ·
           60/61 성문 위병 로타르·쿠르트(강철 흉갑 + 진홍 타바드 + 왕실 문장) ·
           62/63 거리 위병 디터·오스발트(같은 제복) · 58 궁정 상인 발렌틴 ·
           47 금서고 지기 · 46 필경사 · 45 왕립 대사서(잉크 남보라 가운 + 케이프) ·
           44 바르칸 국왕(진홍 + 금 + 어민) · 149 전령(진홍 튜닉 + 금) ·
           117 지크하르트(대장간) · 122 힐데(회복) · 65 행상인
  ★최대 충돌 위험 = 58 발렌틴(같은 «왕도 상인»). 발렌틴은 청록 벨벳 가운 + 담비 모피
    숄칼라 + 벨벳 토크 + 장부 + 잘 먹은 40대. 라인하르트가 «격식 있는 부유한 상인»을
    또 하면 두 사람이 한 사람이 된다.
  ★발렌틴에서 이미 배운 것(그 파일 머리말): 무장·문장은 «권한»의 기호다. 상인에게
    갑옷·사슬·왕실 문장을 입히면 직업이 지워진다. 부유함은 천의 질로 말한다.

DESIGN SPEC (v2 — v1 반려 사유 4건을 구조적으로 못 하게 막은 개정판. 아래 REJECT 참조)
  나이/체격  50대, 마르고 곧다. 발렌틴(잘 먹은 40대 후반)과 체구·나이가 반대
  실루엣     ★왕실 조달관: 흑연 모직 격식 더블릿(엉덩이 길이, 스탠딩 칼라) +
             ★왼 어깨에서 오른 허리로 내려가는 «2px 버프 가죽 발드릭» +
             ★오른쪽으로 치우친 리넨 안깃 여밈(비대칭 여밈) +
             오른팔에만 버프 가죽 브레이서 / 왼팔에만 크림 리넨 커프(좌우가 서로 다른 손목) +
             무릎 위 승마 부츠 + 왼 허벅지 검수 도구 파우치
             ▸ 왕도 이웃과의 분리: 위병=강철+진홍 / 도서관=남보라 가운 / 발렌틴=청록
               벨벳+모피 / 구스타프=감청 코트 / 전령·국왕=진홍 → 라인하르트=흑연 + 버프
               가죽 + 크림. 왕도에서 안 쓰인 조합이고 «격식·절제»가 색만으로 읽힌다
  팔레트     ★명도 사다리를 «넓게» 깐다 — v1 이 저채도 회색 한 덩어리로 뭉친 이유가
             네 재질이 0.20~0.38 안에 다 몰려 있어서였다. v2 의 명도(HSV V):
               부츠·벨트 342a21  0.20  (제일 어두움)
               더블릿   36343c  0.24  (몸통 = 어두운 덩어리, 차가운 264°)
               호스     615a4a  0.38  (따뜻한 44° — 상·하의가 색상과 명도 둘로 갈린다)
               버프 가죽 8a6b45  0.54  (발드릭·브레이서. 흑연 위에서 «사선»이 살아난다)
               리넨     d6cfbc  0.84  (칼라 아님 — ★왼 손목 커프에만)
             ★금속은 «차가운 주석» 한 계열뿐 — 여밈 단추 3점 + 벨트 버클. 금 없음
               (국왕·전령이 진홍+금이고, 버프 가죽 옆에서 금은 따뜻한 색끼리 붐빈다).
               왕실 문장 없음
  비대칭     ① 발드릭 사선(왼 어깨 → 오른 허리) ② 오른팔 버프 브레이서 vs 왼팔 리넨 커프
             ③ 여밈이 중앙이 아니라 오른쪽(x6)으로 치우침 ④ 왼 허벅지 파우치
  정체 모티프 ★«검수하는 사람»의 장비 일습 — 발드릭 + 허리 도구함 + 한쪽 브레이서(자기가
             파는 물건의 견본). 가슴 로고·문장 없음
  얼굴       흰 피부 c2a184 · 회백 머리(앞머리 3행) + ★구레나룻(mutton, 콧수염 없음) ·
             눈동자 안쪽(gaze=0, 기본) · 코 생략(기본) · 회청 눈 · 눈가 주름(50대) ·
             표식 없음(노동 흔적은 조달관의 직업을 지운다) · 긴 턱 · 맨머리

REJECT LOG  (v1 렌더를 코디네이터가 직접 열고 반려. 원인 → 처방을 «구조»로 박았다)
  ① 자색 슬래시가 «분홍 점 얼룩 / 피 튄 자국»으로 읽혔다.
     → 원인은 색이 아니라 «점 흩뿌리기»다. 2px 짜리 마크를 행 간격으로 놓으면 어떤
       색이어도 얼룩이 된다. ★자색을 통째로 폐기하고, 계급은 «연속된 형태»로만
       표현한다: 세로로 이어진 리넨 안깃 + 그 위에 정렬된 주석 걸쇠 2점.
       (garments 에 점을 흩뿌리는 호출을 하나도 남기지 않는다)
  ② 발드릭 사선이 흑연 위에서 안 보였다(벨트 가로 띠만 보였다).
     → 가죽 54402c(0.33)와 흑연(0.24)의 명도 차가 0.09뿐이었고 폭이 1px 이었다.
       ★버프 8a6b45(0.54)로 두 단 올리고 «폭 2px + 밝은 쪽/그늘 쪽 두 열»로 그린다.
       그리고 벨트를 제일 어두운 가죽으로 분리해 사선과 가로 띠가 서로 안 먹는다.
  ★①의 재발 방지를 한 번 더: v2 1차의 «리넨 1px 기둥»도 결국 형태가 없어 이물질로
    읽혔다. 밝은 요소는 «부피가 있는 것»(2px 커프 링)이나 «정렬된 하드웨어»만 허용.
  ③ 턱 아래 크림 면이 «턱받이»로 읽혔다.
     → 스탠딩 칼라에 리넨을 대는 발상 자체를 폐기. ★가슴·목에 밝은 천을 한 픽셀도
       두지 않는다. 칼라는 «흑연 + 윗변 하이라이트 + 아래 그늘» 세 줄로만 세우고,
       밝은 리넨은 턱에서 멀리 떨어진 «손목»으로 전량 이전했다.
  ④ 전체가 저채도 회색 덩어리였다.
     → 위 팔레트 표의 명도 사다리(0.20/0.24/0.38/0.54/0.84) + 차가운 몸통 vs 따뜻한
       하의·가죽으로 색상까지 갈랐다.

재질/조명  (references/lessons.md 19장) 모직·리넨은 정반사가 거의 없다 → ramp_lit 대신
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
SEED = zlib.crc32(b'reinhardt') % 100000                    # ★hash() 금지: 빌드마다 달라진다


def matte(base, spread=0.22):
    """무광 직물(모직·리넨) — 색상 회전 0, 채도 거의 고정, 명도 폭 좁게."""
    return ramp(base, spread=spread, hue=0.0, sat=0.03)


def leather(base, spread=0.34):
    """가죽 — 무광보다 «완전 조금만» 반사한다."""
    return ramp(base, spread=spread, hue=0.02, sat=0.06)


# 값 뒤 인라인 주석은 쉼표를 삼켜 구문오류를 낸다 — 주석은 줄 위에
P = dict(
    skin=ramp('c2a184'),
    # 램프가 넓으면 hair_lit 의 방사 감쇠가 8px 안에서 전 구간을 써 «머리 색이 반반»이
    # 된다(lessons.md 20장). 회백은 특히 잘 티가 난다 → spread 0.24.
    hair=ramp('6e685e', spread=0.24),
    brow=ramp('4a453d'),
    # 몸통 = 어두운 덩어리. 채도 0.10 이라 «남색»(감청 3c4756 / 잉크 남보라 474468)과
    # 헷갈리지 않는다. v1 의 33313a(채도 0.155)는 렌더에서 남색으로 읽혔다.
    doublet=matte('36343c', 0.22),
    # ★밝은 리넨은 «손목과 안깃»에만. 목·가슴에 두면 턱받이가 된다(반려 ③)
    linen=matte('d6cfbc', 0.22),
    # ★버프(생가죽) — 흑연보다 두 단 밝다. 발드릭 사선이 읽히는 최소 조건(반려 ②)
    buff=leather('8a6b45', 0.30),
    # 벨트·부츠·도구함은 제일 어두운 가죽. 버프와 값을 벌려 사선과 가로 띠를 분리한다
    hide=leather('342a21'),
    # 따뜻한 44° — 차가운 흑연 몸통과 «색상»으로도 갈린다(반려 ④)
    hose=matte('615a4a', 0.24),
    # 금속만 진짜 하이라이트를 갖는다 — 유일하게 ramp_lit 유지.
    # ★금은 쓰지 않는다: 국왕44·전령149 가 진홍+금이고, 버프 가죽 옆에서 금은 따뜻한
    #   색끼리 붐빈다. 조달관의 금속은 차가운 주석 한 계열뿐.
    pewter=ramp_lit('9aa1a6'),
)

# 흑연(264°)만 잡는 창. 버프·호스·리넨(33~44°)은 건드리지 않는다.
HUE_TOL = 0.060


def compress_material(s, mid_hex, keep=0.55, sat_keep=0.65, tol=HUE_TOL, sat_min=0.02):
    """무광 재질의 «반사율»을 결과 픽셀에 실제로 계산해 넣는 마지막 패스.

    form_fill·speckle·shade_col_falloff·folds 가 램프 양끝을 향해 섞도록 강도가
    하드코딩돼 있어서, 램프를 좁혀도 명도 폭이 그대로 남는다(lessons.md 19장).
        v' = v_mid + (v - v_mid) x keep
        s' = s_mid + (s - s_mid) x sat_keep     ← speckle 의 «흰색 쪽 탈색»을 되돌린다
    ★흑연은 채도가 낮아(0.10) sat_min 을 0.02 까지 내려야 잡힌다. 그 대신 hue 창을
      좁게 유지해 다른 재질이 새어 들어오지 않게 한다. 머리는 제외(눈동자가 걸린다).
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


def standing_collar(s):
    """세운 칼라 — 밝은 천을 한 픽셀도 쓰지 않는다(반려 ③).

    «세워졌다»는 것은 색이 아니라 «윗변이 빛을 받고 그 아래가 그늘»이라는 사실로
    표현된다. 목을 한 바퀴 도는 요소라 4면 전부 같은 높이로 두른다.
    """
    db = P['doublet']
    ring = s.strip('body', 'outer')
    ring.band(0, 0, db[4])                 # 칼라 윗변이 빛을 받는다
    ring.band(1, 1, db[1])                 # 칼라가 가슴에 떨어뜨리는 그늘
    for fname in ('front', 'back'):        # 칼라 앞뒤 트임을 한 칸 낮춰 «세운 깃»으로
        s.f('body', fname, 'outer').px(3, 0, db[2])
        s.f('body', fname, 'outer').px(4, 0, db[2])


def asym_placket(s):
    """오른쪽으로 치우친 여밈 + 주석 단추 열 — 계급·격식을 «연속된 세로 형태»로 말한다.

    ★v2 1차는 이 자리를 «리넨 1px 밝은 기둥»으로 세웠다가 걷어냈다. 확대해서 보니
      옷의 안깃이 아니라 «가슴에 꽂은 종이 조각 / 온도계»로 읽혔고, 그 위에 얹은 주석
      2점은 밝은 기둥 안에서 청회색 얼룩으로 보였다(자기비평 1패스, 가슴 확대 크롭).
      8px 가슴에서 1px 짜리 짧은 세로 막대는 «형태»가 될 만한 부피가 없다.
    ★확정: 여밈 자체는 «천»(한 단 밝은 흑연 + 옆 이음 그늘)으로 세우고, 밝은 것은
      금속 단추 3점만 그 선 위에 2행 간격으로 «정렬»한다. 이 조합은 로렌초24·구스타프164
      가 이미 쓰고 승인된 어휘(surface=('placket','buttons'))다 — 흩뿌린 점이 아니라
      «여밈선 위의 하드웨어»로 읽히는 이유가 그 연속선이다.
    ★중앙(x3·x4)에 세우면 발렌틴의 «가슴 흰 띠» 사고를 재현하고 발드릭과도 겹친다.
      x6 은 발드릭(행 9~11에서 x3~4)과 한 번도 만나지 않는다.
    """
    fo = s.f('body', 'front', 'outer')
    db, pw = P['doublet'], P['pewter']
    fo.col(6, db[4], 2, 10)                # 여밈선 = 한 단 밝은 «천»(연속선)
    fo.col(5, db[1], 2, 10)                # 옆 이음 그늘 → 안깃이 위에 얹힌 것으로 보인다
    for y in (3, 5, 7):                    # 주석 단추 3점 — 2행 간격 정렬
        fo.px(6, y, pw[4])
        fo.px(6, y + 1, db[0])             # 단추가 천에 떨어뜨리는 그늘


def baldric(s):
    """왼 어깨 → 오른 허리 2px 버프 가죽 발드릭. 이 스킨의 유일한 실루엣 차별점이다.

    ★반려 ②: v1 은 폭 1px + 명도차 0.09 라 흑연에 묻혔다. 폭 2px(밝은 열 + 그늘 열)로
      «끈의 부피»를 만들고, 버프(0.54)와 흑연(0.24)의 명도차를 0.30 으로 벌렸다.
    ★어깨에서 끊기면 «뒷면을 안 봤다»는 증거다 → top 면과 back 면까지 잇는다.
    """
    bf = P['buff']
    fo = s.f('body', 'front', 'outer')
    for y in range(0, 12):
        x = (y * 4) // 12                  # 0,0,0,1,1,1,2,2,2,3,3,3
        fo.px(x, y, bf[4])                 # 빛을 받는 열
        fo.px(x + 1, y, bf[2])             # 그늘 열 → 두께가 생긴다
        if y % 4 == 3:
            fo.px(x, y, bf[1])             # 가죽 이음 스티치
    top = s.f('body', 'top', 'outer')
    for yy in range(top.h):                # 어깨 윗면을 넘어간다
        top.px(0, yy, bf[3]); top.px(1, yy, bf[2])
    bk = s.f('body', 'back', 'outer')
    for y in range(0, 12):                 # 등에서는 반대 방향으로 내려간다
        x = 7 - (y * 4) // 12
        bk.px(x, y, bf[3]); bk.px(x - 1, y, bf[1])


def build():
    s = Skin()
    skin, hair = P['skin'], P['hair']

    # ---- 머리 (0-2 앞머리 / 3 눈썹 / 4 눈 / 5-7 구레나룻·턱)
    g.head_base(s, skin, seed=SEED)
    g.ears(s, skin, y=4)
    # fringe=3 — 2 는 «앞머리가 없어 보인다»(lessons.md 20장). 나이는 회백 색과 주름으로
    g.hair(s, hair, fringe=3, back=6, seed=SEED, part_x=2)
    g.beard(s, hair, style='mutton', y=5, seed=SEED, ragged=False)
    g.face_shape(s, skin, jaw='long', temple=True)
    g.wrinkles(s, skin, crow=True, forehead=False)           # 이마는 앞머리에 덮인다
    # ★표식 없음: 'sunken' 의 어두운 점이 «검댕»으로 읽혀 조달관의 격식을 지웠다.
    #   마른 인상은 jaw='long' + 눈가 주름이 이미 만든다
    g.eyes(s, 'ece8dd', ramp(g.IRIS['grey']), y=4, gaze=0, iris_idx=1, socket=skin[1])
    g.brow(s, P['brow'][1], y=3)
    # ★입을 더 어둡게 하려고 전용 램프를 넘겨 봤지만 결과가 1값밖에 안 움직였다 —
    #   garments.mouth() 가 «피부보다 45 이상 어두워지지 않게» 의도적으로 깎는다
    #   (백발 노인 입이 검은 구멍이 되는 사고 대비). 라이브러리 규칙이므로 싸우지 않고
    #   기본값을 쓴다. 4배 축소 렌더에서 얼굴은 정상으로 읽힌다.
    g.mouth(s, skin, y=6, w=2)

    # ---- base 레이어는 6면 전부 불투명하게 끝낸다(구멍은 인게임에서 투명 덩어리)
    g.tunic(s, P['linen'], y0=0, y1=11, collar=True, seed=SEED, grain=0.06, hem=False)
    g.sleeves(s, P['linen'], y0=0, y1=9, seed=SEED, grain=0.06)
    g.hands(s, skin, rows=2)
    g.pants(s, P['hose'], y0=0, y1=7, seed=SEED)
    g.boots(s, P['hide'], rows=4, toe=True, cuff=True)       # 무릎 위 승마 부츠

    # ---- 더블릿: 엉덩이 길이. 자락이 다리 위 3행까지만 이어져 «코트»와 갈린다
    db = P['doublet']
    s.form_fill('body', db, 0, 11, layer='outer', base_idx=3, top=True)
    s.speckle('body', db, 0, 11, layer='outer', density=0.07, seed=SEED)
    s.shade_col_falloff('body', db, 0, 11, layer='outer')
    s.folds('body', 2, 10, db, layer='outer', cols=(1, 6), seed=SEED)
    s.folds('body', 3, 10, db, layer='outer', cols=(2, 5), face='back', seed=SEED + 3)
    for fname, cx in (('right', 1), ('left', 2)):
        s.folds('body', 2, 10, db, layer='outer', cols=(cx,), face=fname, seed=SEED + 5)
    s.hem('body', 11, db, layer='outer')
    for i, part in enumerate(('leg_r', 'leg_l')):            # 짧은 자락
        s.form_fill(part, db, 0, 2, layer='outer', base_idx=3)
        s.speckle(part, db, 0, 2, layer='outer', density=0.06, seed=SEED + i)
        s.hem(part, 2, db, layer='outer')

    # ---- 소매: 좌우가 서로 다른 손목(비대칭 ②) — 밝은 리넨은 전량 여기로 왔다(반려 ③)
    for i, part in enumerate(('arm_r', 'arm_l')):
        s.form_fill(part, db, 0, 9, layer='outer', base_idx=3, top=True)
        s.speckle(part, db, 0, 9, layer='outer', density=0.07, seed=SEED + i)
        s.hem(part, 9, db, layer='outer', base_idx=3)
    # 왼팔: 크림 리넨 커프 2행(팔뚝을 한 바퀴 — 앞면만 칠하면 옆에서 «붙인 종이»가 된다)
    s.form_fill('arm_l', P['linen'], 8, 9, layer='outer', base_idx=3)
    s.band('arm_l', 8, 8, P['linen'][4], layer='outer')
    s.shade_ring('arm_l', 9, layer='outer', amount=0.22)
    # 오른팔: 버프 가죽 브레이서(자기가 파는 장비의 견본)
    s.form_fill('arm_r', P['buff'], 6, 9, layer='outer', base_idx=3)
    s.band('arm_r', 6, 6, P['buff'][4], layer='outer')
    s.shade_ring('arm_r', 7, layer='outer', amount=0.28)
    s.f('arm_r', 'front', 'outer').px(1, 8, P['buff'][4])    # 조임 끈 2점
    s.f('arm_r', 'front', 'outer').px(2, 8, P['buff'][0])

    # ---- 정면 구성: 칼라 → 여밈 → 발드릭 → 벨트 → 도구함 (뒤에 그린 것이 이긴다)
    standing_collar(s)
    asym_placket(s)
    baldric(s)                          # 칼라·여밈 위로 끈이 지나간다(물리적으로 맞다)
    # ★버클도 주석으로. v2 1차의 금 버클은 버프 끈 바로 옆에서 «금 덩어리»로 튀어
    #   허리가 따뜻한 색으로 붐볐다(자기비평 1패스). 금속을 한 계열(차가운 주석)로
    #   묶으면 그 자체가 «격식·절제»를 말한다 — 금은 왕·전령이 이미 쓴다.
    g.belt(s, P['hide'], y=8, accent=P['pewter'], layer='outer')
    # ★검수 도구함(어두운 가죽 상자)은 폐기했다 — 흑연 위 어두운 가죽은 안 읽힌다
    #   (lessons.md 9장 «검정 위 검정»). 확대 크롭에서 물체가 아니라 그늘로 보였다.
    #   검수 도구는 왼 허벅지 파우치 하나로 충분하다.
    g.pouch(s, P['hide'], part='leg_l', face='front', x=1, y=3, w=2, h=3,
            metal=P['hide'])                                 # 금속은 이미 2곳이다
    # 등판이 민무늬면 모직이 아니라 페인트다
    s.folds('body', 3, 10, db, layer='outer', cols=(3,), face='back', seed=SEED + 11)

    # ---- 저장: micro_light 먼저, 그 «뒤»에 재질 압축(lessons.md 19장)
    s.micro_light()
    s._microed = True
    compress_material(s, '36343c', keep=0.55, sat_keep=0.65)

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'reinhardt.png'))


if __name__ == '__main__':
    print(build())
