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
"""
import pathlib
import sys
import zlib

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                                  # noqa: E402
from skinlib import Skin, ramp, ramp_lit              # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = zlib.crc32(b'wsi1212') % 100000                # ★hash() 금지: 빌드마다 달라진다

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
    # 짙은 잉크 남색. 기본 spread(0.62)로 뽑으면 [4]가 하늘색으로 튀어 '체육복'이 된다
    coat=ramp_lit('1e2a48', spread=0.42),
    lining=ramp_lit('c3b498'),
    shirt=ramp_lit('9a9382'),
    # ★1차 렌더 실패: 544c42 는 장화(3b2f26)와 두 단밖에 안 떨어져 하체가 갈색 한 덩어리로
    #   뭉쳤다(garments.md 값 분리 규칙). 캔버스를 회색 쪽으로 크게 올린다
    pants=ramp_lit('7a7060'),
    boot=ramp_lit('46362a'),
    strap=ramp_lit('4a3b2c'),
    rope=ramp_lit('8f7a52'),
    gold=ramp_lit('c19a3e'),
    iris=ramp(g.IRIS['grey']),
)


def stand_collar(s):
    """세운 칼라 + 안감 1px 숨구멍.

    ★안감을 앞섶 전체에 세우면 가슴에 흰 세로 줄무늬가 생긴다(garments.md 실측 v2).
      칼라 안쪽 한 줄 + 여밈 최상단 2px 까지만.
    """
    coat, lin = P['coat'], P['lining']
    for fname in ('front', 'back'):
        s.f('body', fname, 'outer').row(0, coat[4], 2, 5)   # 세운 칼라 윗면이 빛을 받음
        s.f('body', fname, 'outer').row(1, coat[1], 2, 5)   # 칼라가 드리우는 그림자
    s.f('body', 'top', 'outer').rect(2, 1, 5, 2, coat[1])
    f = s.f('body', 'front', 'outer')
    # ★1차 렌더에서 2px 로 넣었더니 목 밑에 «크림색 스티커»로 보였다 → 1px 숨구멍으로
    f.px(3, 1, lin[2])


def double_breasted(s):
    """이중여밈 금단추 2열 — 이 스킨을 다른 남청 코트 4명과 가르는 핵심 재단."""
    # ★1차 렌더 실패 2건을 여기서 고쳤다:
    #   ① 단추 3개×2열 + 벨트 버클이 가슴에서 «금 사다리»로 뭉쳤다 → 2개×2열로 줄이고
    #      벨트 행(y7)을 피한다. 악센트는 면적이 아니라 점이다(garments.md).
    #   ② x3·x4 에 접힘선을 덮어써서 coat() 가 만든 여밈 명암쌍(x3 밝음/x4 어둠)을
    #      지우고 가슴 중앙에 검은 띠를 만들었다 → 그 루프를 폐기
    g.buttons(s, P['gold'], x=2, ys=(3, 6))
    g.buttons(s, P['gold'], x=5, ys=(3, 6))


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
    for y in range(0, 7):
        if hf.get(0, y)[3]:
            hf.px(0, y, h[3])
        if hf.get(7, y)[3]:
            hf.px(7, y, h[2])
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
    g.hair(s, P['hair'], fringe=2, back=7, seed=SEED, part_x=5)
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

    # ---- outer 레이어: 롱코트 → 칼라/여밈 → 소매 → 벨트 → 소품
    g.coat(s, P['coat'], y0=0, hem=11, tails=3, lapel=True, seed=SEED)
    stand_collar(s)
    double_breasted(s)
    g.neck_shadow(s, P['coat'], layer='outer')

    g.sleeves(s, P['coat'], y0=0, y1=9, layer='outer', seed=SEED + 3, grain=0.08)
    for _i, _part in enumerate(('arm_r', 'arm_l')):
        #   ★소매가 «남색 판자»로 보이지 않게: 세로 폴오프(원통 곡률) + 비대칭 주름 1줄.
        #     팔에 톤이 없으면 무슨 짓을 해도 허접해 보인다(skin-craft.md 관측치)
        s.shade_col_falloff(_part, P['coat'], 0, 9, layer='outer')
        s.folds(_part, 2, 8, P['coat'], layer='outer', cols=(1,) if _i == 0 else (2,),
                seed=SEED + _i)
    #   비대칭 ①: 오른소매만 커프를 접어 안감이 보인다.
    #   ★커프를 밝은 안감으로 한 바퀴 두르면 '소매가 맨살로 끝난' 것처럼 보인다
    #     (garments.md 실측 v2) → 앞면 안쪽 2px 만.
    _cf = s.f('arm_r', 'front', 'outer')
    _cf.px(1, 9, P['lining'][2]); _cf.px(2, 9, P['lining'][1])
    s.shade_ring('arm_r', 8, layer='outer', amount=0.22)

    g.belt(s, P['strap'], y=7, accent=P['gold'], layer='outer')
    shoulder_rope(s)                                        # 비대칭 ②
    #   비대칭 ③: 오른 허벅지 파우치. 코트 자락(leg outer 0~2) 아래에 놓는다.
    #   ★파우치를 금속 램프로 전부 채우면 다리에 금괴를 붙인 꼴이 된다 → 가죽 + 버클 1px
    g.pouch(s, P['strap'], part='leg_r', face='front', x=1, y=3, w=2, h=3,
            metal=P['gold'])

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'player_wsi1212.png'))


if __name__ == '__main__':
    print(build())
