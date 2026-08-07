#!/usr/bin/env python3
"""사막마을(오아시스 상단 마을) 주민 세트 — 표 + 공용 빌더.

세 마을을 색으로 가른다
  왕도  = 진홍 · 강철 · 금 · 잉크 남보라      (권력과 기록)
  스폰  = 바랜 청록 · 오트밀 · 가죽 · 캔버스   (바다와 노동)
  ★사막 = 표백 리넨 · 테라코타 · 사막 인디고 · 황토 · 구리   (모래와 대상)

사막만의 재단 어휘 (CLAUDE.md 지역 규칙: 두건·터번은 사막/오아시스/상단 전용)
  thobe  발목까지 오는 긴 통옷. 사막 남성의 기본. 소매도 길다(햇빛 차단)
  bisht  그 위에 걸치는 트인 겉옷. 신분이 높을수록 색이 짙고 트림이 있다
  turban 머리에 감고 뒤로 꼬리를 늘어뜨린다. 노동자는 짧게, 상인은 크게
  veil   여성은 두건을 목까지 두른다(스폰마을 kerchief보다 넓게 감긴다)
  sash   허리를 감는 천. 사막에서는 벨트보다 새시가 흔하다

구스킨 실태 (2026-08-01 전수조사, 30명 중 28명 이질)
  76 나디아=검정+시안 발광(트론) · 112 아미라=파란 얼굴 · 114 파티마=분홍머리
  · 116 누르=붉은 판타지 갑옷 · 115 오마르=주황티+청바지 · 111 라시드=줄무늬티
  · 80 카림=데님 · 81 할릴=보라 셔츠 · 12 하산=고글 + 멜빵 (스팀펑크)
  · 카지노 딜러 12명 전원 현대 검정 턱시도(dealers.py에서 별도 처리)
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, mix, ramp, ramp_lit       # noqa: E402
import townsfolk as tf                    # noqa: E402  (여성 장신구 adorn)

OUT = pathlib.Path(__file__).parent / 'out'

C = dict(
    ecru='d8cbb0', linen='c6bba2', sand='b09a72', dune='97835f',
    terra='9c5a3c', clay='7d4a33', ochre='a8783a', mustard='8f7434',
    indigo='3a4a6b', indigo_d='2b3750', teal='3f6058', olive='585c3c',
    umber='6b5233', umber_d='4a3826', charcoal='3c352c', ash='6e675c',
    plum='5a3448', copper='a8683a', brass='b08d3c', iron='8a8e93',
)


def R(key, spread=0.52):
    """사막 색을 램프로. 표백 리넨 계열은 spread를 안 좁히면 위가 흰색으로 클리핑된다.

    2026-08-03: ramp_lit으로 교체 — form_fill(base_idx=3)이 앞면을 한 단 위로 칠해
    선언한 색보다 밝고 흐리게 렌더되던 문제(전 마을 공통, "다 파스텔톤" 지적)를 보정한다.
    """
    return ramp_lit(C[key], spread=spread)


# garb: thobe(긴 통옷) / thobe_bisht(통옷+겉옷) / apron(앞치마 직군) / veil_robe(여성)
# head: turban / turban_big / cloth(머리수건) / veil / None
VARIANTS = {
    # ── 기능 NPC (&b) ────────────────────────────────────────────────────
    '10': dict(file='farid', cid=10, label='파리드 — 잡화 상점',
               skin='9c7146', hair='241f1c', beard='full',
               garb='thobe_bisht', cloth='ecru', over='indigo', sash='terra',
               head='turban_big', headc='ecru', prop='pouch', accent='brass',
               eye_y=4, iris='dark', jaw='oval', marks='mole'),
    '12': dict(file='hasan', cid=12, label='하산 — 대장간',
               # ★80 카림(노장 대장장이)과 갈라야 한다: 하산=젊은 현역, 맨팔에 그을음
               skin='8f6339', hair='241d18', beard='stubble',
               garb='apron', cloth='dune', over='umber_d', legs='umber',
               head='cloth', headc='clay', prop='tools', roll=4, soot=True,
               eye_y=5, iris='brown', jaw='square', brow_w=2, marks='scar'),
    '15': dict(file='kasim', cid=15, label='카심 — 물고기 판매',
               # 오아시스 어물전. 스폰 어물전(가죽+청록)과 달리 표백 리넨 + 방수천
               skin='a87a4e', hair='241f1c', beard='goatee',
               garb='apron', cloth='ecru', over='teal', legs='sand',
               head='turban', headc='linen', prop='scales', roll=6,
               eye_y=4, iris='hazel', jaw='long'),
    '16': dict(file='jamal', cid=16, label='자말 — 길드 접수',
               # 마을에서 가장 격식. 짙은 인디고 비슈트 + 금 트림 한 줄
               skin='9c7146', hair='241f1c', beard='full',
               garb='thobe_bisht', cloth='linen', over='indigo_d', sash='ochre',
               head='turban_big', headc='indigo', prop='ledger', accent='brass',
               trim=True,
               eye_y=3, iris='dark', jaw='narrow', brow_a=1),
    '142': dict(file='rashid_inn', cid=142, label='라시드 — 여관 주인',
                skin='a87a4e', hair='4a3a2a', beard='mutton',
                garb='apron', cloth='terra', over='ecru', legs='umber',
                head='cloth', headc='ecru', prop='tankard', roll=6,
               eye_y=4, iris='amber', jaw='square', cheek=True, mouth_w=3),

    # ── 퀘스트 NPC (&a[Q]) ───────────────────────────────────────────────
    '76': dict(file='nadia', cid=76, label='나디아 — 사막마을 촌장',
               # "오아시스를 지키는 일, 도와주시겠소?" → 마을 최고 권위. 여성.
               #   ★구스킨은 검정+시안 발광(트론)이었다
               female=True, age=True, skin='a87a4e', hair='8a8378',
               garb='veil_robe', cloth='indigo_d', over='indigo', sash='ochre',
               head='veil', headc='indigo_d', prop='ledger', accent='brass',
               trim=True,
               eye_y=4, iris='grey', jaw='long', socket=True, brow_a=1),
    '78': dict(file='safir', cid=78, label='사피르 — 감정사',
               # appraisal. 물건을 들여다보는 사람 — 손저울과 확대경
               skin='9c7146', hair='a89a6f', beard='goatee',
               garb='thobe_bisht', cloth='ecru', over='ochre', sash='umber',
               head='turban', headc='ochre', prop='scaleset', accent='brass',
               eye_y=3, iris='green', jaw='narrow', marks='mole'),
    '79': dict(file='yusef', cid=79, label='유세프 — 오아시스 어장 관리',
               # "오아시스 어장을 관리하고 있소" → 걷어붙인 통옷 + 그물
               skin='a89055', hair='2f2721', beard='full',
               garb='thobe', cloth='teal', sash='sand', legs='sand',
               head='cloth', headc='ecru', prop='net', roll=5,
               eye_y=5, iris='brown', jaw='square', marks='ruddy'),
    '80': dict(file='karim', cid=80, label='카림 — 대장장이(노장)',
               # "모래 위의 대장간을 지키오" → 흰 수염 + 낡은 가죽 앞치마
               skin='6b4a30', hair='9a938a', beard='full', age=True,
               garb='apron', cloth='ash', over='umber_d', legs='charcoal',
               head='cloth', headc='umber', prop='tools', roll=4, soot=True,
               patch='leg_r',
               eye_y=4, iris='grey', jaw='long', socket=True, brow_w=2, marks='sunken'),
    '81': dict(file='halil', cid=81, label='할릴 — 지하수로 안내인',
               # "사막의 지하수로를 아는 이는 드물지" → 밧줄과 등불, 젖은 옷자락
               skin='8f6339', hair='a89a6f', beard='stubble',
               garb='thobe', cloth='olive', sash='umber', legs='olive',
               head='turban', headc='dune', prop='lantern', roll=7,
               eye_y=5, iris='hazel', jaw='oval', marks='freckles'),
    '114': dict(file='fatima', cid=114, label='파티마 — 직조공',
                # "직물에 물고기 무늬를 새기는 게 제 특기죠" → 무늬 있는 옷 + 실타래
                female=True, skin='b98a5c', hair='2b2118',
                garb='veil_robe', cloth='terra', over='mustard', sash='ecru',
                head='veil', headc='mustard', prop='yarn', pattern=True,
               eye_y=4, iris='amber', jaw='oval', cheek=True),
    '115': dict(file='omar', cid=115, label='오마르 — 대상(카라반) 대장',
                # "대상이 사막을 건너려면 든든한 양식이 필요하지" → 두꺼운 겉옷 + 물주머니
                skin='9c6b3f', hair='2f2721', beard='full',
                garb='thobe_bisht', cloth='sand', over='clay', sash='indigo',
                head='turban_big', headc='sand', prop='waterskin',
               eye_y=4, iris='dark', jaw='square', brow_w=2, marks='scar'),
    '116': dict(file='nur', cid=116, label='누르 — 향료상',
                # "좋은 향과 좋은 생선은 닮은 점이 있어요" → 향료병. 색을 조금 쓴다
                female=True, skin='b98a5c', hair='1b1a24',
                garb='veil_robe', cloth='plum', over='copper', sash='ecru',
                head='veil', headc='plum', prop='vials', accent='brass',
               eye_y=3, iris='green', jaw='narrow', cheek=True),

    # ── 일반 주민 ────────────────────────────────────────────────────────
    '111': dict(file='rashid', cid=111, label='라시드 — 주민',
                skin='a87a4e', hair='241f1c', beard='stubble',
                garb='thobe', cloth='dune', sash='clay', legs='dune',
                head='cloth', headc='linen', prop=None, roll=8,
               eye_y=5, iris='brown', jaw='oval', marks='freckles'),
    '112': dict(file='amira', cid=112, label='아미라 — 주민',
                # "사막의 밤은 낮보다 아름답답니다" → 저녁의 인디고
                female=True, skin='ba806a', hair='241f1c',
                garb='veil_robe', cloth='indigo_d', over=None, sash='ecru',
                head='veil', headc='indigo', prop='pouch',
               eye_y=4, iris='hazel', jaw='narrow', cheek=True),
    '113': dict(file='yunus', cid=113, label='유누스 — 우물지기',
                # "이 우물이 마르면 마을이 마릅니다" → 젖은 소매 + 두레박 밧줄
                skin='9c7146', hair='4a2f22', beard='goatee',
                garb='thobe', cloth='ecru', sash='teal', legs='linen',
                head='cloth', headc='teal', prop='rope', roll=6,
               eye_y=5, iris='blue', jaw='long', marks='ruddy'),
}


# ── 사막 전용 재단 ─────────────────────────────────────────────────────────
def turban(s, r, big=False, seed=0):
    """터번 — 머리에 감고 뒤로 꼬리를 늘어뜨린다.

    ★스폰마을 headscarf와 다른 점: 감은 '결'이 보여야 한다. 행마다 명도를 한 단씩
      번갈아 주면 천을 여러 번 두른 것으로 읽힌다. 얼굴 구멍은 절대 침범하지 않는다.
    """
    rows = 3 if big else 2
    for i in range(rows):
        tone = r[4] if i % 2 == 0 else r[2]
        for fname in ('front', 'right', 'left', 'back'):
            s.f('head', fname, 'outer').row(i, tone)
    s.f('head', 'top', 'outer').fill(r[4 if rows % 2 else 3])
    bk = s.f('head', 'back', 'outer')
    bk.rect(2, rows, 5, rows + 1, r[3])                  # 뒤로 넘긴 여분
    bk.row(rows + 1, r[1], 2, 5)
    if big:                                              # 어깨로 늘어뜨린 꼬리
        b = s.f('body', 'back', 'outer')
        b.rect(3, 0, 4, 3, r[3]); b.row(3, r[1], 3, 4)


def head_cloth(s, r, seed=0):
    """머리 수건 — 노동자용. 이마 2행만 덮고 옆으로 매듭이 나온다."""
    for fname in ('front', 'right', 'left', 'back'):
        s.f('head', fname, 'outer').rect(0, 0, 7, 1, r[3])
    s.f('head', 'top', 'outer').fill(r[4])
    s.f('head', 'front', 'outer').row(1, r[1])
    s.f('head', 'right', 'outer').px(0, 2, r[4])         # 옆 매듭(비대칭)
    s.f('head', 'right', 'outer').px(1, 2, r[2])


def veil(s, r, seed=0, hair=None):
    """여성 두건 — 머리부터 목까지 감싸고 어깨로 내려온다.

    ★스폰마을 kerchief는 정수리만 덮지만 사막 베일은 뺨과 목을 감싼다.
      그래서 앞면은 이마 2행 + 양 옆 기둥(x0·x7)만 남기고 얼굴을 연다.
    """
    for fname in ('right', 'left', 'back'):
        s.f('head', fname, 'outer').rect(0, 0, 7, 7, r[3])
    f = s.f('head', 'front', 'outer')
    f.rect(0, 0, 7, 1, r[3])
    for x in (0, 7):
        f.rect(x, 2, x, 7, r[2])
    f.row(1, r[1])
    s.f('head', 'top', 'outer').fill(r[4])
    if hair is not None:
        # 베일이 머리카락을 전부 덮으면 나이가 얼굴에만 남는다 — 관자놀이에
        # 몇 픽셀 드러내야 흰머리(=연륜)가 실루엣에서도 읽힌다(유저 지적: 촌장이 젊어 보임)
        f.px(1, 2, hair[3]); f.px(6, 2, hair[3])
        f.px(1, 3, hair[2]); f.px(6, 3, hair[2])
    b = s.f('body', 'back', 'outer')                     # 어깨로 내려온 자락
    b.rect(1, 0, 6, 3, r[2]); b.row(3, r[1], 1, 6)
    s.f('body', 'top', 'outer').rect(1, 0, 6, 3, r[3])


def build_head(s, v, seed):
    skin, hair = ramp(v['skin']), ramp(v['hair'])
    g.head_base(s, skin, seed=seed)
    g.ears(s, skin, y=4)
    g.hair(s, hair, fringe=3 if v.get('female') else 2,
           back=8 if v.get('female') else 6, seed=seed)
    # ★앞머리 모양 — hair() 직후. 자체 build_head를 가진 모듈이라 townsfolk의
    #   배선이 여기까진 안 닿는다(lessons 10장).
    if v.get('fstyle'):
        g.fringe_style(s, hair, style=v['fstyle'],
                       eye_y=max(4, min(v.get('eye_y', 5), 5)) if v.get('female')
                       else v.get('eye_y', 4),
                       seed=seed, skin_r=skin)
    if v.get('beard'):
        g.beard(s, hair, style=v['beard'], y=max(v.get('eye_y', 4) + 1, 6 if v['beard'] == 'mutton' else 5),
                seed=seed, ragged=False)
    if v.get('age'):
        g.wrinkles(s, skin, crow=True, forehead=True)
    # ★얼굴 개인차 (2026-08-03) — 전 마을 공통 처방. 눈높이·눈동자색·턱선·눈썹·표식을
    #   사람마다 달리한다. 이걸 안 하면 옷을 아무리 갈라도 '다 비슷하다'가 남는다.
    eye_y = v.get('eye_y', 5 if v.get('female') else 4)
    if v.get('female'):
        # ★4~5로 클램프 — 여성 앞머리를 낮췄고(fringe) 머리쓰개가 3행까지 덮는 경우가 있어
        #   eye_y=3이면 흰자가 먹힌다(실측: df_nur의 눈이 veil에 통째로 지워졌다).
        #   위로는 2행 눈이라 6 이상이면 eye_y+1이 턱을 침범한다.
        eye_y = max(4, min(eye_y, 5))
    g.face_shape(s, skin, jaw=v.get('jaw', 'oval'), cheek=v.get('cheek', False))
    g.face_marks(s, skin, kind=v.get('marks'), seed=seed)
    _ii = 1 if v.get('iris', 'brown') in ('blue', 'amber', 'hazel', 'grey') else 2
    if v.get('female'):
        # ★2행 눈 — 레퍼런스 실측에서 여성 스킨과의 유일한 결정적 차이였다(흰자 면적 5배).
        g.female_eyes_big(s, 'c9c4b8', ramp(g.IRIS[v.get('iris', 'brown')]), skin, hair,
                          eye_y=eye_y, gaze=v.get('gaze', 0), iris_idx=min(3, _ii + 1))
    else:
        g.eyes(s, 'c9c4b8', ramp(g.IRIS[v.get('iris', 'brown')]), y=eye_y,
               gaze=v.get('gaze', 0), socket=skin[1] if v.get('socket') else None,
               iris_idx=_ii)
    g.brow(s, hair[1], y=eye_y - 1, weight=v.get('brow_w', 1), angle=v.get('brow_a', 0))
    f = s.f('head', 'front')
    if v.get('female'):
        # ★입은 2행 눈 아래로. 레퍼런스 여성 스킨은 입이 대부분 없었고, 진한 입은
        #   남성적 인상을 강화한다 → 피부에 절반 섞어 암시만 남긴다.
        _my = min(7, eye_y + 2)
        _lip = mix(skin[1], ramp('8f5248')[2], 0.55)
        f.px(3, _my, _lip); f.px(4, _my, _lip)
    else:
        g.mouth(s, skin, y=6, w=2)
    if v.get('soot'):
        # ★그을음 자리는 눈 아래여야 한다 — 고정 5행이면 eye_y=5인 사람의 눈을 덮는다
        #   (실측: 하산의 왼쪽 눈이 그을음에 지워졌다)
        for x, y in ((1, min(6, eye_y + 1)), (6, 2)):
            f.px(x, y, mix(f.get(x, y), R('charcoal')[2], 0.5))
    hd = v.get('head')
    if hd == 'cloth' or hd is None:
        # 머리수건은 이마 2행만 덮으므로 나머지 머리카락에 겉레이어 볼륨이 필요하다.
        # 없으면 '모자를 안 씌운 것'처럼 납작해 보인다(유저 지적)
        g.hair_volume(s, hair, fringe=2, back=8, seed=seed)
    if hd in ('turban', 'turban_big'):
        turban(s, R(v['headc']), big=(hd == 'turban_big'), seed=seed)
    elif hd == 'cloth':
        head_cloth(s, R(v['headc']), seed=seed)
    elif hd == 'veil':
        veil(s, R(v['headc']), seed=seed, hair=hair)

    # ★눈 지워짐 검사는 <b>머리쓰개를 그린 뒤</b>여야 한다. 예전엔 brow 직후에 있어서
    #   veil()이 머리카락을 흰자 위에 덮는 걸 못 잡았다(실측: df_nur 눈이 통째로 사라짐).
    _ef = s.f('head', 'front')
    if sum(1 for x in (1, 2, 5, 6) if max(_ef.get(x, eye_y)[:3]) > 150) < 2:
        raise ValueError('%s: 눈이 지워졌다 (eye_y=%d, head=%s)'
                         % (v.get('file', '?'), eye_y, hd))


def build_body(s, v, seed):
    skin = ramp(v['skin'])
    cloth = R(v['cloth'])
    garb = v['garb']
    legs = R(v.get('legs') or v['cloth'])

    g.tunic(s, R('linen'), y0=0, y1=11, collar=True, seed=seed, grain=0.07, hem=False)
    g.sleeves(s, R('linen'), y0=0, y1=11, seed=seed, grain=0.07)
    g.hands(s, skin, rows=2)
    g.pants(s, legs, y0=0, y1=11, seed=seed)
    # 사막은 장화가 아니라 샌들 — 발목 아래만 가죽, 정강이는 옷자락이 덮는다
    g.boots(s, R('umber_d'), rows=2, toe=True, cuff=False)

    if garb in ('thobe', 'thobe_bisht'):
        # 통옷: 발목까지. robe()가 4대 결함(짧은소매·가로띠·판때기·단색)을 막아준다
        g.robe(s, cloth, y0=0, seed=seed, hem_row=11,
               sleeve_to=v.get('roll', 10), lining=R('ecru'))
    elif garb == 'veil_robe':
        # ★robe()를 그대로 부르고 있었다 — 사막 남성 thobe와 실루엣이 같아서 상반신만
        #   보이는 각도에서 성별이 사라졌다(2026-08-05 지적: 아미라). 베일은 얼굴을 감싸
        #   이미 여성 신호지만 몸이 남성과 동일하면 소용이 없다. 네크라인은 베일이 덮어
        #   못 쓰므로 하이웨이스트 절개 + 앞 중앙 자수로 가른다.
        g.robe(s, cloth, y0=0, seed=seed, hem_row=11, sleeve_to=10, lining=R('ecru'))
        g.high_waist(s, cloth, R('ecru'), band=v.get('band', 4), layer='outer')
    elif garb == 'apron':
        g.robe(s, cloth, y0=0, seed=seed, hem_row=11,
               sleeve_to=v.get('roll', 6), lining=R('ecru'))
        g.apron(s, R(v['over']), bib=(1, 6), bib_y=(1, 6), waist=7, hem=11,
                wrap=2, straps=True, tie=True, seed=seed)
        fa = s.f('body', 'front', 'outer')
        for x in (0, 7):                                 # 양옆을 비워 통옷이 흐르게
            fa.rect(x, 8, x, 11, (0, 0, 0, 0), 0)

    if garb in ('thobe_bisht', 'veil_robe') and v.get('over'):
        # ★비슈트: 통옷 위에 걸치는 트인 겉옷. 앞은 양쪽 기둥만 남기고 활짝 열려
        #   가운데로 통옷이 보여야 한다. 통짜로 덮으면 그냥 다른 색 로브다.
        ov = R(v['over'])
        for fname in ('right', 'left', 'back'):
            s.form_fill('body', ov, 0, 11, layer='outer', base_idx=3,
                        faces=(fname,))
        fb = s.f('body', 'front', 'outer')
        for x in (0, 1, 6, 7):
            fb.rect(x, 0, x, 11, ov[3 if x in (0, 7) else 2])
        fb.col(2, ov[1], 0, 11); fb.col(5, ov[1], 0, 11)  # 트임 두께
        s.f('body', 'top', 'outer').fill(ov[4])
        s.speckle('body', ov, 0, 11, layer='outer', density=0.08, seed=seed)
        s.folds('body', 2, 10, ov, layer='outer', cols=(2, 5), face='back', seed=seed)
        for part in ('arm_r', 'arm_l'):                  # 겉옷 소매는 팔꿈치까지
            s.form_fill(part, ov, 0, 5, layer='outer', base_idx=3)
            s.hem(part, 5, ov, layer='outer', base_idx=3)
        for part in ('leg_r', 'leg_l'):                  # 자락이 다리로 이어진다
            s.form_fill(part, ov, 0, 6, layer='outer', base_idx=2,
                        faces=('right', 'left', 'back'))
        if v.get('trim'):                                # 금 트림은 앞 기둥 한 줄만
            fb.col(1, R('brass')[4], 1, 10)

    if v.get('sash'):                                    # 허리 새시 — 사막의 벨트
        sa = R(v['sash'])
        s.band('body', 7, 7, sa[4], layer='outer')
        s.band('body', 8, 8, sa[2], layer='outer')
        s.f('body', 'front', 'outer').px(5, 9, sa[3])    # 늘어뜨린 끝(비대칭)
        s.f('body', 'front', 'outer').px(5, 10, sa[1])

    if v.get('pattern'):                                 # 직조공의 물고기 무늬
        fb = s.f('body', 'front', 'outer')
        for x, y in ((2, 3), (3, 3), (4, 4), (3, 5), (2, 5)):
            fb.px(x, y, R('ecru')[4])
        fb.px(5, 4, R('ecru')[2])


def build_props(s, v, seed):
    f = s.f('body', 'front', 'outer')
    p = v.get('prop')
    if p == 'pouch':
        g.pouch(s, R('umber'), part='leg_r', face='front', x=1, y=2, w=2, h=3,
                metal=R('brass') if v.get('accent') else None)
    elif p == 'tools':
        f.px(2, 9, R('iron')[4]); f.px(2, 10, R('umber_d')[2])
        f.px(5, 9, R('umber')[4]); f.px(5, 10, R('umber')[2])
    elif p == 'scales':                                  # 앞치마에 붙은 비늘
        for x, y in ((3, 4), (2, 9), (5, 8)):
            f.px(x, y, R('iron')[4]); f.px(min(7, x + 1), y, R('iron')[2])
    elif p == 'ledger':
        f.rect(6, 5, 7, 9, R('ecru')[1]); f.col(6, R('ecru')[3], 5, 9)
        f.row(9, R('umber_d')[1], 6, 7)
    elif p == 'scaleset':                                # 감정사의 손저울
        f.px(3, 6, R('brass')[4]); f.rect(2, 7, 4, 7, R('brass')[3])
        f.px(2, 8, R('brass')[2]); f.px(4, 8, R('brass')[2])
    elif p == 'net':
        for x, y in ((1, 3), (2, 4), (1, 5), (2, 6)):
            f.px(x, y, R('ecru')[4]); f.px(x + 1, y, R('ecru')[1])
        s.f('body', 'top', 'outer').rect(1, 0, 2, 3, R('ecru')[2])
    elif p == 'lantern':
        f.rect(6, 8, 7, 10, R('iron')[2])
        f.px(6, 9, ramp('c9a24a')[4]); f.px(7, 9, ramp('c9a24a')[3])
        f.px(6, 7, R('iron')[3])
    elif p == 'rope':
        for y in (2, 4, 6):
            f.px(1, y, R('ecru')[4]); f.px(2, y, R('ecru')[2])
        s.f('body', 'top', 'outer').rect(1, 0, 2, 3, R('ecru')[3])
    elif p == 'waterskin':                               # 카라반의 물주머니
        f.rect(5, 8, 7, 11, R('umber')[3])
        f.col(5, R('umber')[4], 8, 11); f.row(11, R('umber_d')[1], 5, 7)
        f.px(6, 8, R('umber_d')[2])
        g.bandolier(s, R('umber'), front_x=2, layer='outer')
    elif p == 'yarn':
        for i, key in enumerate(('terra', 'indigo', 'mustard')):
            f.px(6, 7 + i, R(key)[4]); f.px(7, 7 + i, R(key)[2])
        f.px(6, 6, R('umber')[2])
    elif p == 'vials':                                   # 향료병 세 개
        for i, key in enumerate(('copper', 'plum', 'ochre')):
            f.px(6, 7 + i * 2, R('ecru')[4]); f.px(7, 7 + i * 2, R(key)[3])
    elif p == 'tankard':
        f.rect(6, 8, 7, 10, R('iron')[2])
        f.px(6, 8, R('iron')[4]); f.px(7, 9, R('iron')[4])
    if v.get('patch'):
        g.patch(s, v['patch'], 'front', R('umber'), x=1, y=5, w=2, h=2, layer='outer')



def feminize(s, v, seed):
    """여성 실루엣·옆머리 패스 — townsfolk.feminize와 같은 처방(이 모듈은 townsfolk를
    import하지 않아 중복 정의한다).

    ★2026-08-05 오너 지적("근본적인 원인 중 하나가 여자스킨이 없어"): 그때까지 female=True가
      하던 일은 속눈썹 2px + 입술색뿐이라 여성 NPC가 남성 몸에 옷만 갈아입은 꼴이었다.
      바닐라 모델은 남녀 지오메트리가 같으므로 성별은 '칠해서' 만들어야 한다.
    ★반드시 옷을 다 그린 뒤 호출 — 먼저 부르면 옷이 덮어 무효다.
    """
    if not v.get('female') or v.get('child'):
        return
    g.female_form(s, seed=seed)
    # ★긴 머리 — 얼굴 앞면은 절대 안 건드린다(1차 실패 교훈: female_face가 앞면 x0·x7을
    #   머리로 덮어 얼굴이 6px로 좁아지고 눈이 검은 덩어리가 됐다. garments.female_hair_length
    #   주석 참고). 머리를 통째로 감싸는 머리쓰개면 건너뛴다.
    # ★머리 볼륨(옆·뒤·정수리)은 머리에 아무것도 안 쓴 사람만 — 이 패스는 모자를 그린
    #   뒤에 돌기 때문에 켜면 두건·모자·바이저 crown을 머리카락이 덮어쓴다.
    #   등으로 흘러내리는 길이(shoulders)는 머리쓰개와 무관하므로 항상 준다.
    g.female_hair_length(s, ramp(v['hair']), seed=seed,
                         # 뒷머리 길이 스펙(backhair 7~9)을 앞·어깨로 흘리는 길이와 연동한다
                         drop=max(3, min(6, v.get('backhair', 7) - 4)),
                         head_volume=(v.get('head') is None and not v.get('visor')),
                         shoulders=v.get('head') not in ('hood', 'coif', 'veil'))
    tf.adorn(s, v, seed)   # ★장신구·네크라인 — 머리 다음이어야 옆머리 위에 귀걸이가 얹힌다

def build(v):
    s = Skin()
    # ★여성 개정표 — 이 모듈만 배선이 빠져 있었다(2026-08-07 발견). FEM_RESTYLE에
    #   사막 여성 항목이 없어서 지금까지 증상이 안 보였을 뿐, 표에 뭘 넣어도 조용히
    #   무시되고 있었다. 자체 build()를 가진 모듈은 매번 전수 확인할 것(lessons 10장).
    v = tf.restyle(v)
    seed = v['cid']
    build_head(s, v, seed)
    build_body(s, v, seed)
    # ★치마 구조 — 자체 build_body를 가진 모듈이라 townsfolk의 배선이 안 닿는다
    #   (lessons 10장. 실측: 이번에도 사막 여성 4명이 조용히 빠져 있었다).
    #   베일 로브는 발목까지 한 덩어리라 벨트가 없고, 구조만 얹으면 된다.
    if v.get('skirt'):
        g.skirt_style(s, R(v.get('legs') or v['cloth']), style=v['skirt'],
                      hem=v.get('hem', 11), y0=v.get('skirty0', 2),
                      accent=R(v['skirtc']) if v.get('skirtc') else None, seed=seed)
    feminize(s, v, seed)     # ★여성 패스 — 옷 다음, 소품 앞
    build_props(s, v, seed)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / f"df_{v['file']}.png"))


if __name__ == '__main__':
    for k in sys.argv[1:] or VARIANTS:
        print(build(VARIANTS[k]))
