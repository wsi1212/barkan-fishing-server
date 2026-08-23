#!/usr/bin/env python3
"""베아트리체 — 상단마을 안내인, citizensId 93.

CHARACTER BRIEF
  대사   "처음 오셨나요? 상단마을은 넓으니 길 잃지 않게 조심하세요."
         "궁금한 게 있으면 언제든 물어보세요."
         → 마을을 안내하는 친절한 주민. 상인도 노동자도 아닌 '동네 사람'.
  역할   없음(대화 전용). 표시명에 색코드 없음 — 규칙상 &f여야 함(별건).
  구스킨 흰 탱크톱 + 데님 반바지 = 현대 캐주얼(B급 테마 파괴).

DESIGN SPEC
  나이/체격  30대 여성
  실루엣     중세 마을 여성: 머릿수건 + 보디스(끈 조끼) + ★발목까지 오는 치마
             + 앞치마 + 한쪽으로 넘긴 땋은 머리. 마을 남자들(더블릿·조끼·저킨)과
             하반신 실루엣부터 갈린다
  팔레트     보디스=세이지 그린 / 블라우스=오프화이트 / 치마=흙갈 / 앞치마=바랜 리넨
             (마르코=버건디, 조반니=회녹, 알도=머스터드와 전부 분리)
  비대칭     땋은 머리가 한쪽 어깨 앞으로 + 앞치마 끈 매듭은 뒤 + 왼쪽 치마에 기운 자국
  얼굴       눈동자 안쪽(기본) · 코 없음(기본) · ★수염 없음(여성) · 속눈썹 1px + 입술 톤
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))
import garments as g                      # noqa: E402
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = 93
P = dict(skin=ramp('d0a57f'), hair=ramp('6b4a2f'), bodice=ramp_lit('6f7d5c'),
         blouse=ramp_lit('c2b9a3'), skirt=ramp_lit('6e5844'), apron=ramp_lit('cfc7b4'),   # 치마(흙갈)와 확실히 갈리게 밝은 리넨
         kerchief=ramp_lit('8a8f7a'), lip=ramp('9b5a52'), iris=ramp('4a5a3f'))


def build():
    s = Skin()
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=2, back=7, seed=SEED, part_x=3)
    g.face_shape(s, P['skin'], jaw='oval')
    g.female_eyes_big(s, 'c9c4b8', ramp(g.IRIS['green']), P['skin'], P['hair'], eye_y=5, gaze=0, iris_idx=3)
    g.brow(s, P['hair'][1], y=3)
    f = s.f('head', 'front')
    f.rect(3, 7, 4, 7, P['lip'][2])                              # 입술
    g.ponytail(s, P['hair'], x0=2, w=2, y0=6, y1=11)             # 땋은 머리

    # 블라우스 → 치마 → 보디스 → 앞치마
    g.tunic(s, P['blouse'], y0=0, y1=11, collar=True, seed=SEED, grain=0.07, hem=False)
    g.sleeves(s, P['blouse'], y0=0, y1=9, seed=SEED, grain=0.07)
    g.hands(s, P['skin'], rows=2)
    for part in ('leg_r', 'leg_l'):                              # ★긴 치마
        s.form_fill(part, P['skirt'], 0, 11, base_idx=3, top=True, bottom=True)
        s.form_fill(part, P['skirt'], 0, 10, layer='outer', base_idx=3)
        s.hem(part, 10, P['skirt'], layer='outer', base_idx=3)
        s.folds(part, 1, 9, P['skirt'], layer='outer', cols=(1,), seed=SEED)
    s.form_fill('body', P['skirt'], 8, 11, layer='outer', base_idx=3)

    g.vest(s, P['bodice'], y0=1, hem=7, gap=2, seed=SEED, buttons=P['skirt'])
    fr = s.f('body', 'front', 'outer')
    for y in range(2, 7):                                        # 보디스 끈
        fr.px(3, y, P['skirt'][1] if y % 2 == 0 else P['skirt'][3])
        fr.px(4, y, P['skirt'][3] if y % 2 == 0 else P['skirt'][1])
    g.apron(s, P['apron'], bib=(3, 4), bib_y=(3, 6), waist=7, hem=11,
            wrap=1, straps=False, tie=True, seed=SEED)
    g.patch(s, 'leg_l', 'front', P['skirt'], x=1, y=5, w=2, h=2, layer='outer')
    # ★긴 머리 — 반드시 <b>옷·머리쓰개를 다 그린 뒤</b>, 그리고 outer 레이어에.
    #   NPC는 lookclose로 늘 플레이어를 마주보므로 뒷머리는 볼 일이 없다 → 얼굴 옆과
    #   가슴 앞으로 내려와야 '길다'가 읽힌다. 머리쓰개는 함수가 알아서 비켜간다.
    g.female_hair_length(s, P['hair'], seed=SEED)
    # 두건을 뺀다 — 안내인은 머리를 싸맬 역할 근거가 없다. 대신 꽃 한 송이.
    g.decollete(s, P['skin'], style='scoop')
    g.necklace(s, P['bodice'], style='beads')
    g.hair_ornament(s, P['lip'], kind='flower', seed=SEED)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'beatrice.png'))


if __name__ == '__main__':
    print(build())
