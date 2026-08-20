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
from skinlib import Skin, ramp, ramp_lit            # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
# ★2026-08-01 리워크: 로브 4대 결함 제거(짧은 소매·몸통 가로 띠·판때기 자락·침침한 단색).
#   가운을 한 단 밝게(3d3a5c→474468), 양피지 안감을 칼라·앞섶·커프에 1px 노출,
#   케이프 앞 옷단은 직선 대신 어깨 곡선(mantle)으로 끝낸다. 45 대사서와 같은 팔레트.
L = dict(
    gown=ramp_lit('474468'),
    cape=ramp_lit('2e2b47'),
    lining=ramp_lit('a8a08e'),
    apron=ramp_lit('a89c85'),
    ink=ramp_lit('2b2f4a'),
    brass=ramp_lit('a8863a'),
    iron=ramp_lit('8a8e93'),
    scroll=ramp_lit('bfb49a'),
)
# cape = (앞 곡선 옷단 높이, 등 자락 길이). 계급 사다리가 실루엣으로 읽혀야 한다.
VARIANTS = {
    '50': dict(name='subarchivist', cid=50, cape=(3, 8), hood=False, gaze=-1,
               skin='c2a184', hair='6b6154', beard='mutton', prop='ledger', ink=2,
               sleeve=10, roll=False,
               eye_y=4, iris='grey', jaw='long', socket=True, brow_w=2),
    '47': dict(name='vaultkeeper', cid=47, cape=(2, 11), hood=True, gaze=0,
               skin='c99e72', hair='3f3128', beard='full', prop='keys', ink=1,
               sleeve=10, roll=False,
               # ★eye_y=3 이면 <b>후드가 눈을 통째로 덮는다.</b> 후드의 얼굴 구멍은 행 4 부터
               #   열리는데 눈을 행 3 에 그려서, 베이스에는 흰자·눈동자가 멀쩡히 있는데도
               #   화면에는 <b>눈 없는 얼굴</b>이 나왔다(실측 2026-08-17). 형제 NPC(필경사·
               #   견습)는 eye_y=5 다. 후드 쓴 NPC 는 구멍 안쪽에 눈을 둬야 한다.
               eye_y=4, iris='dark', jaw='narrow', brow_a=1),
    '46': dict(name='scribe', cid=46, cape=None, hood=False, gaze=0,
               skin='c9a480', hair='4a3d2f', beard='goatee', prop='quill', ink=5,
               sleeve=9, roll=False,
               eye_y=5, iris='green', jaw='oval', marks='freckles'),
    '67': dict(name='apprentice', cid=67, cape=None, hood=False, gaze=0,
               skin='d0a97f', hair='7a5f3a', beard=None, prop='none', ink=7,
               sleeve=10, roll=True,
               eye_y=5, iris='blue', jaw='narrow', marks='mole'),
}


def build(v):
    s = Skin(); seed = v['cid']
    skin = ramp(v['skin']); hair = ramp(v['hair'])
    g.head_base(s, skin, seed=seed)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=2, back=6, seed=seed)
    if v['beard']:
        g.beard(s, hair, style=v['beard'], y=max(v.get('eye_y', 4) + 1, 6 if v['beard'] == 'mutton' else 5),
                seed=seed, ragged=False)
    g.wrinkles(s, skin, crow=True, forehead=not v['hood'])
    # ★얼굴 개인차 (2026-08-03) — 전 마을 공통 처방. 눈높이·눈동자색·턱선·눈썹·표식을
    #   사람마다 달리한다. 이걸 안 하면 옷을 아무리 갈라도 '다 비슷하다'가 남는다.
    eye_y = v.get('eye_y', 4)
    g.face_shape(s, skin, jaw=v.get('jaw', 'oval'), cheek=v.get('cheek', False))
    g.face_marks(s, skin, kind=v.get('marks'), seed=seed)
    g.eyes(s, 'c9c4b8', ramp(g.IRIS[v.get('iris', 'brown')]), y=eye_y,
           gaze=v.get('gaze', 0), socket=skin[1] if v.get('socket') else None,
           iris_idx=1 if v.get('iris', 'brown') in ('blue', 'amber', 'hazel', 'grey') else 2)
    g.brow(s, hair[1], y=eye_y - 1, weight=v.get('brow_w', 1), angle=v.get('brow_a', 0))
    if sum(1 for x in (1, 2, 5, 6)
           if max(s.f('head', 'front').get(x, eye_y)[:3]) > 150) < 2:
        raise ValueError(f"{v.get('file', v.get('name'))}: 눈이 지워졌다 (eye_y={eye_y})")
    g.mouth(s, skin, y=6, w=2)
    if v['hood']:
        g.hood(s, L['cape'], opening=5, seed=seed)

    for part in ('arm_r', 'arm_l'):
        s.form_fill(part, skin, 0, 11, base_idx=3, top=True, bottom=True)
    g.tunic(s, L['gown'], y0=0, y1=11, collar=True, seed=seed, grain=0.07, hem=False)
    g.pants(s, L['gown'], y0=0, y1=11, seed=seed)
    g.robe(s, L['gown'], y0=0, seed=seed, hem_row=11, sleeve_to=v['sleeve'],
           lining=L['lining'])
    g.hands(s, skin, rows=1)

    if v['cape']:                                        # 계급 = 케이프 등자락 길이
        front, back = v['cape']
        g.mantle(s, L['cape'], front=front, back=back, seed=seed, lining=L['lining'],
                 clasp=L['brass'] if back >= 8 else None, sleeve=2)
    if v['prop'] == 'ledger':                                        # 겨드랑이 장부
        # 어두운 가운 위의 밝은 소품은 쉽게 형광 막대가 된다 — 중간값 + 모서리 한 줄
        f = s.f('body', 'front', 'outer'); f.rect(6, 6, 7, 10, L['scroll'][1])
        f.col(6, L['scroll'][2], 6, 10); f.row(10, L['gown'][0], 6, 7)
    elif v['prop'] == 'keys':                                        # ★금서고 열쇠 꾸러미
        # 가로 띠(구버전 s.band)는 로브 흐름을 끊는다 — 열쇠고리만 세로로 매단다
        f = s.f('body', 'front', 'outer')
        for x, y in ((6, 7), (7, 8), (6, 9)):
            f.px(x, y, L['iron'][4])
        f.px(7, 7, L['iron'][2]); f.px(6, 8, L['iron'][1])
        f.px(6, 6, L['iron'][2]); f.px(6, 10, L['iron'][1])
    elif v['prop'] == 'quill':                                       # 앞치마 + 깃펜
        g.apron(s, L['apron'], bib=(2, 5), bib_y=(2, 6), waist=7, hem=11,
                wrap=1, straps=True, tie=True, seed=seed)
        f = s.f('body', 'front', 'outer')
        f.px(6, 4, L['lining'][4]); f.px(6, 5, L['lining'][3]); f.px(6, 6, L['ink'][1])
    if v['roll']:                                        # 막내만 한쪽 소매를 걷는다
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
