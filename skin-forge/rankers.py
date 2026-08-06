#!/usr/bin/env python3
"""마을별 랭킹 NPC 4인 — 에르빈(스폰) · 구스타프(왕도) · 타리크(사막) · 마르첼로(상단).

역할  `&b[랭킹]` = 기능형(하늘색). 마을의 기록을 집계해 보여주는 사람.

SET ARCHITECTURE
  같은 역할 4명이므로 <b>하나로 묶는 공통 표식</b>이 먼저 필요하고, 그 위에 마을 팔레트로 갈린다.
  ★공통 표식 = <b>귀에 꽂은 깃펜</b> + <b>가슴에 든 기록판(tally)</b>
    - ledger(장부)는 이미 15명이 쓴다 — 구분자가 될 수 없어서 새로 만들었다.
    - 깃펜은 서버 전체에서 아무도 안 쓰는 축이고, "기록하는 사람"을 즉시 읽히게 한다.
    - 기록판은 눈금(tally mark)이 그려진 판 — 책(ledger)과 실루엣이 다르다.
  ★마을 팔레트·재단은 각 마을에서 실제로 안 쓰는 축으로만 골랐다(전수조사 기준):
      스폰  9 kirtle·7 coat·6 apron이 이미 포화 → tunic(2명뿐) + coif(1명뿐)
      상단  6 tunic·5 apron 포화 → coat(2명뿐) + cap
      사막  thobe/thobe_bisht/veil_robe만 있음 → thobe_bisht + turban(3명) 중 색으로 가름
      왕도  단일 파일 NPC들(브란트·프리츠·발렌틴)과 겹치지 않게 잉크 남보라를 피하고 감청+놋쇠

  ★나이·성별은 넷 다 다르게 — 같은 역할이 4명이면 얼굴부터 갈려야 한다.
      에르빈 중년 남 / 구스타프 노인 남 / 타리크 젊은 남 / 마르첼로 여성
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import townsfolk as tf                     # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'

tf.C.update(
    quill='e8e2d2',      # 깃펜 — 표백 깃털
    slate2='6b7078',     # 기록판 석판
    chalkmark='e3ded0',  # 눈금
    # ★sea·ochre·umber2·burgundy는 tradetown이 tf.C에 넣는 키다 — 이 파일은 townsfolk만
    #   import하므로 그대로 쓰면 KeyError가 난다(실측). 여기서 직접 정의한다.
    sea='3f5d66',
    ochre='9a7328',
    umber2='6b4a2e',
    burgundy='6e2733',
)

V = {
    '163': dict(file='r_erwin', cid=163, label='에르빈 — 스폰마을 랭킹',
                # 어촌의 기록관. 스폰마을은 kirtle 9·coat 7·apron 6으로 포화라
                # tunic(2명)+coif(1명)로 뺀다. 팔레트는 마을 공통 바다빛(sea)+삼베.
                skin='c09468', hair='6b5540', beard='stubble',
                garb='tunic', cloth='sea', under='linen', legs='slate',
                boot='boot', head='coif', headc='linen', prop='tally',
                quill=True, roll=7,
                surface=('pocket', 'trim'), surfc='oat',
                eye_y=4, iris='blue', jaw='oval', brow_w=2, marks='ruddy'),

    '164': dict(file='r_gustav', cid=164, label='구스타프 — 왕도 랭킹',
                # 왕립 기록관. 왕도 단일파일 NPC들(브란트·프리츠·발렌틴)의 잉크 남보라를
                # 피해 감청 코트 + 놋쇠. 노인으로 격을 세운다.
                skin='cfab8d', hair='9a938a', beard='full', age=True,
                garb='coat', cloth='navy', under='chalk', legs='charcoal',
                boot='boot_d', head='cap', headc='navy', prop='tally',
                quill=True, accent='brass',
                surface=('buttons', 'trim'), surfc='brass',
                eye_y=4, iris='grey', jaw='long', socket=True, fringe=1, bootrows=5),

    '165': dict(file='r_tariq', cid=165, label='타리크 — 사막마을 랭킹',
                # 대상(카라반) 기록인. 사막은 thobe 계열만 있어 재단으로는 못 가르므로
                # 색(황토+구리)과 젊은 나이로 뺀다. 터번은 3명이 쓰지만 색이 다르다.
                skin='a87a4e', hair='241f1c', beard='goatee',
                garb='tunic', cloth='ochre', under='oat', legs='umber2',
                boot='boot', head='cap', headc='rust', prop='tally',
                quill=True, roll=6,
                surface='trim', surfc='brass',
                eye_y=5, iris='amber', jaw='narrow', brow_a=1),

    '166': dict(file='r_marcello', cid=166, label='마르첼로 — 상단마을 랭킹',
                # ★넷 중 유일한 여성 — 같은 역할 4명이면 성별부터 갈려야 한다.
                #   상단마을은 tunic 6·apron 5로 포화, coat는 2명뿐이라 그쪽으로.
                #   회계라 소매 가터(칠부)로 손을 자유롭게 둔다.
                female=True, skin='cfa47e', hair='c25a2a',
                garb='coat', cloth='burgundy', under='chalk', legs='charcoal',
                boot='boot', head=None, prop='tally',
                quill=True, accent='brass', backhair=9, braid=True,
                sleeve=7, hem=11,
                surface=('placket', 'buttons'), surfc='brass',
                eye_y=5, iris='green', jaw='oval', cheek=True),
}

_orig_props = tf.props


def quill(s, seed=0):
    """귀 위에 꽂은 깃펜 — 랭킹 NPC 4인의 공통 표식.

    ★서버 전체에서 아무도 안 쓰는 축이라 '기록하는 사람'을 즉시 읽히게 한다.
      ledger(장부)는 이미 15명이 써서 구분자가 못 된다.
    ★머리 <b>옆면 겉층</b>에 그린다 — 얼굴 앞면에 그리면 8px 얼굴을 먹는다
      (female_face 실패 교훈: 앞면은 성별·표식을 넣을 자리가 아니다).
    """
    q = tf.R('quill')
    f = s.f('head', 'right', 'outer')          # 오른쪽 귀 위 — 한쪽만(비대칭)
    for i, (x, y) in enumerate(((1, 3), (2, 2), (3, 1), (4, 0))):
        f.px(x, y, q[4] if i % 2 else q[3])
    f.px(1, 4, tf.R('walnut')[2])               # 깃대 아래 촉(어두운 한 점)


def props(s, v, seed):
    f = s.f('body', 'front', 'outer')
    if v.get('prop') == 'tally':
        # 기록판 — 눈금이 그려진 석판. 책(ledger)과 실루엣이 다르게 <b>넓고 납작</b>하다.
        sl, mk = tf.R('slate2'), tf.R('chalkmark')
        f.rect(5, 4, 7, 8, sl[3])
        f.col(5, sl[4], 4, 8); f.row(8, sl[1], 5, 7)     # 테두리 — 판으로 읽히게
        for y in (5, 7):                                  # 눈금 두 줄
            f.px(6, y, mk[4]); f.px(7, y, mk[3])
        f.px(6, 6, mk[3])
        return
    _orig_props(s, v, seed)


def build(v):
    from skinlib import Skin
    s = Skin()
    seed = v['cid']
    tf.head(s, v, seed)
    tf.body(s, v, seed)
    tf.extra_cut(s, v, seed)
    tf.surface(s, v, seed)
    if v.get('wrapshawl'):
        tf.g.shawl(s, tf.R(v['wrapshawl']), y0=0, drop=v.get('shawldrop', 4), seed=seed)
    tf.feminize(s, v, seed)
    props(s, v, seed)
    if v.get('quill'):
        quill(s, seed)          # ★깃펜은 맨 마지막 — 머리 볼륨/모자에 덮이면 안 된다
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / f"{v['file']}.png"))


if __name__ == '__main__':
    for k in sys.argv[1:] or V:
        print(build(V[k]))
