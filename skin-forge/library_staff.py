#!/usr/bin/env python3
"""왕립 대도서관 4인 세트 — 차석사서(50)·금서고지기(47)·필경사(46)·필경생(67).

CHARACTER BRIEF (대사 그대로가 캐릭터다)
  50 차석사서   "…차석 사서요." / ★"기록은 이미 다 정리되었소. 더 들출 것은 없을 텐데……"
                → 뭔가를 덮으려는 인물. 조반니처럼 곁눈질(gaze≠0)이 정당한 예외.
  47 금서고지기 "여기서부터는 봉인된 서고. 금서고 열쇠 없이는 아무도 들일 수 없소."
                "어둠 속 진실을 마주할 각오는 되었소?" → 문지기. 열쇠와 후드.
  46 필경사     "원본을 베껴 쓰는 게 제 일." ★"누군가 기록을 위조하고 낱장을 뜯어간 흔적이…"
                → 필사 노동자. 잉크 얼룩과 앞치마.
  67 필경생     막내. 가장 수수하고 잉크를 제일 많이 묻힌다.
  구스킨 50 검정+보라 네온(엔더맨풍) · 47 전신 회흑 유령 · 46 남색+주황 세로줄
         · 67 흰 티셔츠+청바지(현대)

SET ARCHITECTURE (위병 세트와 같은 구조: 제복 통일, 사람 구분)
  공통  잉크 남보라 가운 + 회백 안감 + 계급에 따른 어깨 케이프 — 대사서(45)와 한 팔레트
  변주  ①계급(케이프 길이·금속 유무) ②머리 장비 ③소품(두루마리/열쇠/깃펜) ④잉크 얼룩 양
  ★계급 사다리가 실루엣으로 읽혀야 한다: 대사서(긴 케이프+두루마리) > 차석사서(짧은 케이프)
    > 금서고지기(후드+열쇠) > 필경사(앞치마) > 필경생(맨 가운, 소매 걷음)
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))
import garments as g                      # noqa: E402
from skinlib import Skin, ramp            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
L = dict(
    gown=ramp('3d3a5c'),
    cape=ramp('2a2841'),
    lining=ramp('9a9488'),
    apron=ramp('a89c85'),
    ink=ramp('2b2f4a'),
    brass=ramp('a8863a'),
    iron=ramp('8a8e93'),
    scroll=ramp('bfb49a'),
)
VARIANTS = {
    '50': dict(name='subarchivist', cid=50, cape=6, hood=False, gaze=-1,
               skin='c2a184', hair='6b6154', beard='mutton', prop='ledger', ink=2),
    '47': dict(name='vaultkeeper', cid=47, cape=4, hood=True, gaze=0,
               skin='a8845f', hair='3f3128', beard='full', prop='keys', ink=1),
    '46': dict(name='scribe', cid=46, cape=0, hood=False, gaze=0,
               skin='c9a480', hair='4a3d2f', beard='goatee', prop='quill', ink=5),
    '67': dict(name='apprentice', cid=67, cape=0, hood=False, gaze=0,
               skin='d0a97f', hair='7a5f3a', beard=None, prop='none', ink=7),
}


def build(v):
    s = Skin(); seed = v['cid']
    skin = ramp(v['skin']); hair = ramp(v['hair'])
    g.head_base(s, skin, seed=seed)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=2, back=6, seed=seed)
    if v['beard']:
        g.beard(s, hair, style=v['beard'], y=6 if v['beard'] == 'mutton' else 5,
                seed=seed, ragged=False)
    g.wrinkles(s, skin, crow=True, forehead=not v['hood'])
    g.eyes(s, 'c9c4b8', ramp('4a4a58'), y=4, gaze=v['gaze'], brow=hair[2], brow_y=3)
    g.mouth(s, skin, y=6, w=2)
    if v['hood']:
        g.hood(s, L['cape'], opening=5, seed=seed)

    for part in ('arm_r', 'arm_l'):
        s.form_fill(part, skin, 0, 11, base_idx=3, top=True, bottom=True)
    g.tunic(s, L['gown'], y0=0, y1=11, collar=True, seed=seed, grain=0.07, hem=False)
    g.robe(s, L['gown'], y0=0, seed=seed, hem_row=11, sleeve_to=9)
    g.pants(s, L['gown'], y0=0, y1=11, seed=seed)
    g.hands(s, skin, rows=2)
    s.f('body', 'front', 'outer').row(0, L['lining'][3], 2, 5)      # 안감 칼라

    if v['cape']:                                                    # 계급 = 케이프 길이
        s.form_fill('body', L['cape'], 0, v['cape'] - 2, layer='outer', base_idx=3, top=True)
        s.f('body', 'back', 'outer').rect(0, 0, 7, v['cape'], L['cape'][2])
        s.f('body', 'back', 'outer').row(v['cape'], L['cape'][1])
        s.f('body', 'front', 'outer').row(v['cape'] - 2, L['cape'][1])
        for part in ('arm_r', 'arm_l'):
            s.form_fill(part, L['cape'], 0, 2, layer='outer', base_idx=3)
            s.hem(part, 2, L['cape'], layer='outer', base_idx=3)
    if v['prop'] == 'ledger':                                        # 겨드랑이 장부
        f = s.f('body', 'front', 'outer'); f.rect(6, 6, 7, 9, L['scroll'][3])
        f.row(6, L['scroll'][4], 6, 7); f.row(9, L['scroll'][1], 6, 7)
        s.band('body', 5, 5, L['brass'][2], layer='outer')
    elif v['prop'] == 'keys':                                        # ★금서고 열쇠 꾸러미
        f = s.f('body', 'front', 'outer')
        for x, y in ((6, 7), (7, 8), (6, 9)):
            f.px(x, y, L['iron'][4])
        f.px(7, 7, L['iron'][2]); f.px(6, 8, L['iron'][1])
        s.band('body', 6, 6, L['iron'][2], layer='outer')
    elif v['prop'] == 'quill':                                       # 앞치마 + 깃펜
        g.apron(s, L['apron'], bib=(2, 5), bib_y=(2, 6), waist=7, hem=11,
                wrap=1, straps=True, tie=True, seed=seed)
        f = s.f('body', 'front', 'outer')
        f.px(6, 4, L['lining'][4]); f.px(6, 5, L['lining'][3]); f.px(6, 6, L['ink'][1])
    if v['prop'] in ('quill', 'none'):                               # 소매 걷음(노동자)
        s.clear_rows('arm_r', 8, 11, layer='outer')
        s.hem('arm_r', 7, L['gown'], layer='outer', base_idx=3, lip=False)
    # ★잉크 얼룩 — 계급이 낮을수록 많다. 이 세트의 개인차이자 서사
    import random as _r
    rnd = _r.Random(seed)
    for _ in range(v['ink']):
        part = rnd.choice(('arm_r', 'arm_l', 'body'))
        fa = s.f(part, 'front', 'outer' if part == 'body' else 'base')
        x = rnd.randrange(fa.w); y = rnd.randrange(4, 11)
        fa.px(x, y, L['ink'][1])
        if rnd.random() < 0.5:
            fa.px(min(fa.w - 1, x + 1), y, L['ink'][2])
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / f"lib_{v['name']}.png"))


if __name__ == '__main__':
    for k in sys.argv[1:] or VARIANTS:
        print(build(VARIANTS[k]))
