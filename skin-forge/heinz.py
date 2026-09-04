#!/usr/bin/env python3
"""하인츠 — &b[조선소] 조선공, 부두(스폰도시 항구), citizensId 206.

CHARACTER BRIEF  (npc_brief.py 조선소 --village)
  역할   조선소 NPC = 커스텀 배(범선)를 파는 배목수. 튜토 중반 [1-20]~[1-22] 담당.
  대사   "발밑 조심해, 대패밥이 미끄럽거든" / "나는 하인츠, 이 부두에서 배를 깎는다"
         → 뱃사람이 아니라 **목수**다. 말투가 무뚝뚝하고 손이 거칠다.
  지역   부두 < 바르칸 항구 < 스폰도시. 유럽풍 중세 항구 — 사막/아라비안 요소 금지.
  이웃   ★페리선장이 7m(!)  · 도란 26m · 레오 38m · 마르타 40m · (같은 항구에 어물전 오토)
         페리선장과 붙어 있으므로 «뱃사람 실루엣»(선장 코트·선원 모자)은 절대 금지.
         오토는 «가슴받이 가죽 앞치마»가 전담이라 그것도 피한다.

DESIGN SPEC  (그리기 전에 전부 선언)
  나이/체격  50대, 어깨 두꺼운 목수. 팔뚝이 굵어 보이도록 소매를 걷는다.
  실루엣     [머리쓰개 없음, 헝클어진 머리] + 리넨 셔츠 + **짧은 가죽 저킨(조끼)**
             + **허리에만 두르는 캔버스 작업 앞치마(가슴받이 없음)** + 도구 벨트
             + 무릎까지 오는 캔버스 바지 + 낮은 작업화
             ↳ 오토(가슴받이 앞치마)·페리선장(뱃사람)과 실루엣이 겹치지 않는 조합
  팔레트     셔츠=바랜 회녹 리넨(matte) / 저킨=탄 가죽(leather) / 앞치마=표백 안 한 캔버스
             (matte, 바지보다 두 단 밝게 — 안 그러면 하체가 한 덩어리) / 바지=짙은 캔버스
             / 신발=진갈색 가죽 / 악센트=놋쇠 2곳(벨트 버클·도구 고리)뿐
  정체 모티프 **톱밥** — 앞치마·팔뚝·신발에 밝은 나무색 점. 로고 대신 «방금 대패질하던 사람».
  비대칭     ① 오른팔만 소매를 걷음(오토는 왼팔 → 반대로) ② 왼쪽 허리에 끌·나무못 주머니
             ③ 앞치마 오른쪽 아래 검게 탄 헝겊 패치(타르 솥 자국)
  얼굴       그을린 피부, 회갈 머리(램프 좁게 — 반반 방지), 짧은 턱수염+콧수염,
             이마·눈가 주름 깊게, 회녹 눈, gaze=0(기본), 코 생략(기본)
"""
import pathlib
import sys
import zlib

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                                   # noqa: E402
from skinlib import Skin, ramp, ramp_lit               # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = zlib.crc32(b'heinz') % 100000


def matte(base, spread=0.22):
    """모직·리넨·캔버스 — 색상 회전 0, 반사 거의 없음."""
    return ramp(base, spread=spread, hue=0.0, sat=0.03)


def leather(base, spread=0.32):
    """가죽 — 아주 조금만 반사."""
    return ramp(base, spread=spread, hue=0.02, sat=0.06)


P = dict(
    skin=ramp('c08a5e'),                    # 바닷바람에 그을린 피부
    hair=ramp('6a5b4c', spread=0.26),       # 회갈 — 좁은 램프(머리 반반 방지)
    beard=ramp('7a6a58', spread=0.24),
    shirt=matte('8e9484', 0.22),            # 바랜 회녹 리넨(페리·오토와 다른 색상대)
    jerkin=leather('5a3f28', 0.30),         # 짧은 가죽 저킨
    apron=matte('a8926a', 0.24),            # 표백 안 한 캔버스 — 바지보다 두 단 밝게
    pants=matte('4f4a41', 0.22),            # 짙은 캔버스
    boot=leather('3a2f26', 0.28),
    brass=ramp_lit('b08d3c'),               # 악센트 — 벨트 버클 + 도구 고리, 그 이상 금지
    dust=ramp('dcc48f', spread=0.18),       # 톱밥
    iris=ramp('5b6b52'),                    # 회녹 눈
)


def build():
    s = Skin()
    skin, hair = P['skin'], P['hair']

    # ---- 얼굴: 피부 → 머리 → 수염 → 피처 (뒤에 그린 것이 이긴다)
    g.head_base(s, skin, seed=SEED)
    g.ears(s, skin, y=4)
    #   ★가르마·ragged·ruddy·이마주름을 같이 쓰면 8x8 얼굴이 노이즈로 뭉친다(1패스 실측).
    #     남기는 건 «구조»뿐 — 앞머리 3행, 고른 수염, 눈가 주름.
    g.hair(s, hair, fringe=3, back=6, seed=SEED)             # 두건 없음, 가르마 없음
    #   헤어라인 지그재그가 남긴 빈칸으로 «밝은 이마 픽셀 한 점»이 튀어나온다 → 봉인.
    _hf, _hb = s.f('head', 'front', 'outer'), s.f('head', 'front')
    for _x in range(8):
        if max(_hb.get(_x, 2)[:3]) > 190 and _hf.get(_x, 2)[3] == 0:
            _hf.px(_x, 2, hair[2])
    g.beard(s, P['beard'], style='full', y=5, seed=SEED, ragged=False)
    g.face_shape(s, skin, jaw='square')
    g.wrinkles(s, skin, crow=True, forehead=False)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, iris_idx=1)
    g.brow(s, hair[1], y=3)
    g.mouth(s, skin, y=6, w=2, color=P['beard'][1])          # 콧수염 안쪽의 입선

    # ---- 상체: 리넨 셔츠(base) → 짧은 가죽 저킨(outer)
    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, fold_cols=(2, 5),
            grain=0.07)
    g.vest(s, P['jerkin'], y0=0, hem=7, gap=2, seed=SEED)    # 짧다 — 허리 앞치마가 이어받는다
    g.lacing(s, P['boot'], x=(3, 4), y0=1, y1=5)             # 저킨 앞 끈
    _jb = s.f('body', 'back', 'outer')                       # 등판 요크선 — 없으면 갈색 판때기
    _jb.row(3, P['jerkin'][2], 0, 7)
    _jb.row(4, P['jerkin'][4], 0, 7)

    # ---- 허리 앞치마: 가슴받이·어깨끈 없음(오토와 갈리는 지점), 허리에서 무릎까지
    #   bib_y 를 허리(7)에 두면 벨트가 그 위를 덮는다 = 가슴받이 없는 허리 앞치마.
    g.apron(s, P['apron'], bib=(3, 4), bib_y=(7, 7), waist=7, hem=11,
            straps=False, tie=True, wrap=2, seed=SEED)
    #   앞치마가 몸통에서 끝나면 «넓은 벨트»로 읽힌다 — 허벅지까지 내려야 앞치마가 된다.
    #   가로 패널이라 다리 세로줄 함정(lessons 5-3)에 안 걸린다.
    for part in ('leg_r', 'leg_l'):
        for face in ('front',):
            f = s.f(part, face, 'outer')
            for y in range(0, 4):
                for x in range(4):
                    f.px(x, y, P['apron'][3] if y < 3 else P['apron'][2])
        s.hem(part, 3, P['apron'], layer='outer')
    g.belt(s, P['boot'], y=7, accent=P['brass'], buckle=True, layer='outer')
    g.patch(s, 'body', 'front', P['boot'], x=5, y=10, w=2, h=2, layer='outer')  # 타르 자국

    # ---- 팔: 오른팔만 걷어붙임(비대칭 ①)
    g.sleeves(s, P['shirt'], y0=0, y1=9, rolled=('arm_r', 5), skin_r=skin,
              seed=SEED, grain=0.07)
    g.hands(s, skin, rows=2)
    s.band('arm_l', 5, 5, P['jerkin'][3], layer='outer')     # 왼팔은 가죽 토시로 마감

    # ---- 다리: 캔버스 바지 + 낮은 작업화 + 왼쪽 도구 주머니(비대칭 ②)
    g.pants(s, P['pants'], y0=0, y1=9, seed=SEED)
    g.boots(s, P['boot'], rows=3, toe=True, cuff=True)
    #   ★앞치마 패널(0~3행) «아래»에 달아야 보인다 — 겹치면 놋쇠 한 점만 튀어나와
    #     앞치마에 찍힌 정체불명의 점이 된다(2패스 실측).
    g.pouch(s, P['boot'], part='leg_l', face='front', x=1, y=4, w=2, h=3,
            metal=P['brass'])                                # 끌·나무못 주머니 = 놋쇠 2번째이자 마지막

    # ---- 톱밥 (정체 모티프): 앞치마와 그 아래 패널에만. 팔·다리에 흩뿌리면
    #      density 0.07 은 1px 미만이라 «없는 것»이고, 피부 위 점은 때로 읽힌다.
    s.speckle('body', P['dust'], 8, 11, layer='outer', density=0.16, seed=SEED,
              faces=('front',), base_idx=4)
    for part in ('leg_r', 'leg_l'):
        s.speckle(part, P['dust'], 0, 3, layer='outer', density=0.14, seed=SEED + 1,
                  faces=('front',), base_idx=4)

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'heinz.png'))


if __name__ == '__main__':
    print(build())
