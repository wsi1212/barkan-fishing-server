#!/usr/bin/env python3
"""알브레히트 — &b[말 대여] 알브레히트, 왕도 왕실 마구간, citizensId 121.

CHARACTER BRIEF
  대사   "왕실 마구간을 관리하고 있소." / "좋은 말이 필요하면 말하시오."
  지역   왕도 → 방금 만든 위병 4인(강철+진홍 왕실색)과 같은 세계관이어야 한다.
         다만 그는 병사가 아니므로 ★왕실 십자 문장은 쓰지 않는다(문장은 병사 것).
         소속감은 진홍 트림으로만 표현.
  구스킨 ★레거시 64x32 + "TF C" 빨간 로고가 박힌 검은 후드티 = 현대 브랜드 의류.
         중세 왕도 한복판에서 테마를 가장 크게 깨고 있던 스킨.

DESIGN SPEC
  나이/체격  50대, 말을 다루는 단단한 체구
  실루엣     승마 복장: 가죽 저킨 + 무릎 위 승마부츠 + ★어깨에 걸친 굴레(고삐 가죽끈)
             + 한쪽 장갑만 착용(말을 잡는 손). 위병의 판금 실루엣과 확실히 다르게
  팔레트     갈색 가죽 + 오트밀 리넨 + 놋쇠 버클 한 곳
             ★진홍 트림 폐기 — 갈색 저킨에 붉은 트림을 두르니 '군복'으로 읽혔다(유저 지적).
               마구간지기는 병사가 아니다. 소속은 색이 아니라 일(굴레·솔)로 드러내면 된다
  비대칭     굴레가 한쪽 어깨 + 오른 허리 솔 주머니 + ★왼손만 장갑
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · 짧은 수염 · 챙 없는 가죽 모자
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))
import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 121
P = dict(skin=ramp('bd9068'), hair=ramp('5f5145'), jerkin=ramp_lit('7a5a3a'),
         linen=ramp_lit('b5a98d'), boot=ramp_lit('4a3a2b'), brass=ramp_lit('b08d3c'),
         rein=ramp_lit('5c4630'), iris=ramp('4a3a2c'))


def build():
    s = Skin()
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=6, seed=SEED)
    g.beard(s, P['hair'], style='full', y=6, seed=SEED, ragged=False)
    g.wrinkles(s, P['skin'], crow=True, forehead=False)
    g.face_shape(s, P['skin'], jaw='square')
    g.face_marks(s, P['skin'], kind='ruddy', seed=SEED)
    g.eyes(s, 'c9c4b8', ramp(g.IRIS['brown']), y=5, gaze=0, iris_idx=2)
    g.brow(s, P['hair'][1], y=4)
    g.mouth(s, P['skin'], y=6, w=2, color=P['hair'][1])
    g.cap(s, P['boot'], crown=2, brim=False, seed=SEED)   # 가죽 모자(밴드 없음)

    g.tunic(s, P['linen'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07, hem=False)
    g.sleeves(s, P['linen'], y0=0, y1=9, seed=SEED, grain=0.07)
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['jerkin'], y0=0, y1=6, seed=SEED)
    g.boots(s, P['boot'], rows=6, toe=True, cuff=True)          # 무릎 위 승마부츠

    g.vest(s, P['jerkin'], y0=0, hem=9, gap=0, seed=SEED, buttons=P['brass'])  # 가죽 저킨
    for part in ('arm_r', 'arm_l'):      # 소매를 짧게 두면 진홍이 팔에 가로 띠로 남아 산만
        s.form_fill(part, P['jerkin'], 0, 7, layer='outer', base_idx=3)
        s.hem(part, 7, P['jerkin'], layer='outer', base_idx=3)
    s.form_fill('arm_l', P['boot'], 8, 11, layer='outer', base_idx=3)          # ★왼손만 장갑
    s.band('arm_l', 8, 8, P['boot'][4], layer='outer')
    g.belt(s, P['boot'], y=9, accent=P['brass'], layer='outer')

    g.bandolier(s, P['rein'], front_x=2, layer='outer')                        # 어깨 굴레
    f = s.f('body', 'front', 'outer')
    for y in (3, 6):                                                            # 고삐 고리
        f.px(3 + y // 3, y, P['brass'][3])
    g.pouch(s, P['boot'], part='leg_r', face='front', x=1, y=1, w=2, h=3,
            metal=P['brass'])                                                   # 솔 주머니
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'albrecht.png'))


if __name__ == '__main__':
    print(build())
