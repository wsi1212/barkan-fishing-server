#!/usr/bin/env python3
"""은빛 갈매기호 승무원 6인 + 지역 미분류 NPC 10인.

승무원(51~56)은 '한 배를 탄 사람들'이라 소금 절은 캔버스·타르 검정·감청으로 묶고,
계급(선장>갑판장>포수장>화물지기>갑판원>견시)을 옷의 격식으로 세운다.

구스킨 실태 (2026-08-02 유저 지적)
  52 포수 엔리코 = 종족이 인간이 아님 / 65 행상인 = 바이킹 상남자
  / 147 현자 = 현자로 안 보임 / 148 항구장 = 사람이 반 얼어있음
  / 149 전령 = 마스크가 어색하고 배 선장 같은 옷
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import townsfolk as tf                     # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'

tf.C.update(
    tar='2f2c28', brine='47575c', deck='7a6f5c', crimson='8f2b32',
    gold='c2a13f', sage='7d8a6a', bloom='9c6a44',
)

V = {
    # ── 은빛 갈매기호 승무원 (계급이 옷의 격식으로 읽혀야 한다) ──────────────
    '55': dict(file='isabella', cid=55, label='이자벨라 — 선장',
               # "내 배에 오른 이상, 내 규칙을 따르도록" → ★여성 선장. 배에서 가장 갖춤
               female=True, skin='b58b65', hair='1b1a24',
               garb='coat', cloth='navy', under='linen', legs='tar',
               boot='boot_d', head='cap', headc='tar', prop='ledger',
               accent='brass',
               eye_y=3, iris='grey', jaw='narrow', backhair=9, brow_a=1, surface=('trim', 'buttons'), surfc='brass', layer2='sash', l2c='crimson'),
    '51': dict(file='matteo', cid=51, label='마테오 — 갑판장',
               # "이 갑판 위의 일은 전부 내 소관이지" → 팔뚝이 굵고 밧줄을 두른다
               skin='ab7748', hair='241f1c', beard='full',
               garb='jerkin', cloth='deck', under='linen', legs='brine',
               boot='boot', head=None, prop='rope', sleeved=True,
               eye_y=5, iris='dark', jaw='square', brow_w=2, marks='scar', surface='seams', surfc='deck', bootrows=6),
    '52': dict(file='enrico', cid=52, label='엔리코 — 포수장',
               # "화약은 농담을 모른다. 나도 그렇고" → 화약 그을음 + 두꺼운 가죽
               skin='6b4a30', hair='2f2721', beard='full',
               garb='apron', cloth='tar', under='canvas', extra='leather_d',
               legs='tar', boot='boot_d', head='cap', headc='leather_d',
               prop='tools', roll=4, dust=False,
               eye_y=4, iris='amber', jaw='square', brow_w=2, socket=True, marks='sunken', surface='patchwork', surfc='tar'),
    '54': dict(file='giovanni_hold', cid=54, label='조반니 — 화물지기',
               # "이 배의 짐은 전부 내 장부에 있소" → 장부와 열쇠. 뭔가 숨기고 있다
               skin='c39a72', hair='5a4636', beard='goatee',
               garb='tunic', cloth='brine', under='oat', legs='tar',
               boot='boot', head=None, prop='ledger', roll=7,
               eye_y=4, iris='brown', jaw='oval', surface='pocket', surfc='brine', layer2='suspenders', l2c='leather'),
    '53': dict(file='pino', cid=53, label='피노 — 갑판원(신참)',
               # "히익! 노, 놀랐잖아요..." → 가장 어리고 옷이 헐렁하다
               skin='c2a397', hair='6b5540', child=True,
               garb='tunic', cloth='oat', under='linen', legs='canvas',
               boot='boot', head=None, prop='rope', roll=5, patch='leg_r',
               eye_y=5, iris='blue', jaw='narrow', fringe=3, marks='freckles', surface='seams', surfc='oat', bootrows=2),
    '56': dict(file='niko', cid=56, label='니코 — 견시',
               # "이 망대에서 수평선을 지켜" → 바람 막는 후드 + 망원경
               skin='a89055', hair='a05a2a',
               garb='jerkin', cloth='brine', under='canvas', legs='tar',
               boot='boot', head='hood', headc='brine', prop='spyglass',
               sleeved=True,
               eye_y=5, iris='green', jaw='narrow', fringe=3, marks='freckles', surface='stripe_v', surfc='brine'),

    # ── 지역 미분류 / 기타 ────────────────────────────────────────────────
    '1': dict(file='old_angler', cid=1, label='낚시꾼할아버지 — 민물 낚시',
              # "바르칸 물길은 민물 낚시의 성지지" → 3 할아버지(길잡이)와 갈라야 한다:
              #   3=붉은 니트모+청록 목도리 / 1=밀짚 챙모자+낚시 도구
              skin='b98a5c', hair='9a938a', beard='full', age=True,
              garb='tunic', cloth='cream', under='oat', legs='grey', boot='boot',
              head='cap', headc='mustard', prop='net', roll=5,
               eye_y=4, iris='grey', jaw='long', socket=True, fringe=1, marks='ruddy', surface='patchwork', surfc='sand'),
    '2': dict(file='caver', cid=2, label='동굴탐험가',
              # "...누구야? 여긴 아무나 오는 곳이 아닌데" → 동굴. 등불 + 어두운 가죽
              skin='a87a4e', hair='2f2721', beard='stubble',
              garb='jerkin', cloth='leather_d', under='canvas', legs='charcoal',
              boot='boot_d', head='hood', headc='charcoal', prop='lantern',
              sleeved=True,
               eye_y=4, iris='dark', jaw='square', brow_w=2, marks='scar', surface='seams', surfc='iron', layer2='gloves', l2c='leather_d', bootrows=6),
    '4': dict(file='ferry_captain', cid=4, label='페리선장',
              # ★24 로렌초와 텍스처가 완전히 겹쳐 있었다. 감청 코트 + 선장 모자
              skin='b57c67', hair='6b6154', beard='full', age=True,
              garb='coat', cloth='navy', under='linen', legs='brine',
              boot='boot_d', head='cap', headc='navy', prop='rope',
              accent='brass',
               eye_y=4, iris='blue', jaw='square', marks='ruddy', surface=('buttons', 'trim'), surfc='brass', bootrows=5),
    # ── 도입부 뱃사람 (★게임에서 처음 만나는 NPC) ──────────────────────────
    '160': dict(file='sailor', cid=160, label='선원 — 도입부 배(2908,65,-3162)',
                # "다 왔다, 꼬맹아. / 곧 바르칸 항구에 닿을 거다."
                # ★모든 플레이어의 첫 NPC다 — 8초 안에 '뱃사람'으로 읽혀야 한다.
                #   지금까지 스킨이 아예 없어서(skinName=None) 기본 스티브로 서 있었다.
                # 차별화: 승무원 8명이 안 쓴 축만 골랐다
                #   머리   머릿수건 — cap(이자벨라·엔리코·페리선장) hood(니코) 없음(마테오·조반니·피노) 뿐이었다
                #   재단   wrap(교차 여밈) — 이 그룹 미사용 (coat/jerkin/apron/tunic만 있었다)
                #   무늬   lacing(앞 끈) — 미사용
                #   소품   노(oar) — rope는 이미 3명, net은 낚시꾼할아버지
                # 팔레트: 승무원 공통 소금빛(brine)을 몸에 써서 '한 배 사람'으로 묶고,
                #   유일한 유채색은 벽돌빛 머릿수건. crimson은 이자벨라 새시 몫이라 rust로 뺀다.
                # 억센 중년 — "꼬맹아"라 부르는 말투. age=True는 페리선장·할아버지 몫이라 안 쓰고
                #   턱수염 대신 짧은 구레나룻(stubble)+굵은 눈썹+햇볕에 튼 볼로 나이를 낸다.
                skin='a97a4f', hair='4a3a2c', beard='stubble',
                # ★바지를 tar(2f2c28)로 뒀더니 검정 부츠와 뭉쳐 하반신이 한 덩어리였다(1차).
                #   deck(카키)로 올려 셔츠(감청)-바지(카키)-부츠(검정) 3단 값이 갈리게 한다.
                garb='wrap', cloth='brine', under='canvas', legs='deck',
                boot='boot_d', head=None, bandana='rust', prop='coil',
                roll=5, sleeved=True,
                # ★surface='lacing'도 폐기했다(2차): wrap이 이미 교차 여밈 실루엣을 주는데
                #   끈을 겹치니 가슴이 검은 픽셀 얼룩이 됐다. 무늬를 더하는 대신 <b>깨끗한
                #   도형 한 겹</b>(허리 새시)을 얹는다 — 반다나와 같은 벽돌빛으로 묶어
                #   "붉은 천 두 곳"이 이 사람의 표식이 된다.
                layer2='sash', l2c='rust',
                eye_y=4, iris='grey', jaw='square', brow_w=2, socket=True,
                marks='ruddy', bootrows=6),
    '64': dict(file='pilgrim', cid=64, label='순례자',
               # "먼 길을 걸어 왕도의 대도서관을 보러 왔소" → 낡은 여행 로브 + 후드
               skin='b0855e', hair='7a6e5f', beard='full', age=True,
               garb='robe', cloth='bone', under='oat', legs='sand',
               boot='boot', head='hood', headc='umber2' if 'umber2' in tf.C else 'leather',
               prop='pouch',
               eye_y=4, iris='hazel', jaw='long', fringe=0, socket=True, surface='trim', surfc='leather'),
    '65': dict(file='peddler', cid=65, label='행상인',
               # ★구스킨은 바이킹 상남자. 봇짐장수는 커다란 등짐과 잡동사니로 말한다
               skin='b08b67', hair='c2a052', beard='goatee',
               garb='tunic', cloth='mustard', under='oat', legs='canvas',
               boot='boot', head='cap', headc='leather', prop='sack', roll=6,
               eye_y=5, iris='amber', jaw='oval', mouth_w=3, surface='patchwork', surfc='mustard', layer2='suspenders', l2c='leather'),
    '147': dict(file='sage', cid=147, label='현자',
                # ★"내가 아는 그 현자가 아닌가?" → 현자는 긴 수염 + 회백 가운 + 지팡이다.
                #   왕도 대사서45(잉크 남보라)와 달리 색을 완전히 뺀 은둔자
                skin='cfab8d', hair='a8a49c', beard='full', age=True,
                garb='robe', cloth='chalk', under='linen', legs='grey',
                boot='boot', head='hood', headc='grey', prop='book',
               eye_y=4, iris='grey', jaw='long', fringe=0, socket=True, brow_w=2, surface='trim', surfc='sage'),
    '148': dict(file='harbourmaster', cid=148, label='항구장',
                # ★구스킨은 사람이 반 얼어 있었다. 항구를 관리하는 사람 = 코트 + 장부 + 모자
                skin='b58f6a', hair='241f1c', beard='mutton',
                garb='coat', cloth='crimson', under='linen', legs='tar',
                boot='boot_d', head='cap', headc='crimson', prop='ledger',
                accent='brass',
               eye_y=5, iris='dark', jaw='square', brow_w=2, marks='ruddy', brow_a=1, surface=('placket', 'buttons'), layer2='vest', l2c='tar', surfc='brass', bootrows=5),
    '149': dict(file='herald', cid=149, label='전령',
                # ★구스킨은 마스크 + 배 선장 옷. 전령은 왕실 제복이다 —
                #   왕도 팔레트(진홍+금)의 짧은 튜닉 + 어깨 가방. 얼굴은 반드시 보인다
                skin='ba946e', hair='8f4a24',
                garb='tunic', cloth='crimson', under='linen', legs='tar',
                boot='boot_d', head='cap', headc='crimson', prop='satchel',
                roll=7, accent='gold',
               eye_y=4, iris='green', jaw='oval', surface='trim', surfc='gold', layer2='tabard', l2c='crimson'),
    '151': dict(file='rosa_garden', cid=151, label='정원사 로자',
                # "이 근처에 핀 노란 꽃들이 좀 신경 쓰여서" → 흙 묻은 앞치마 + 꽃
                female=True, age=True, skin='b58b65', hair='8a8378',
                garb='kirtle', cloth='sage', under='linen', extra='canvas',
                legs='sage', boot='boot', head='kerchief', headc='mustard',
                prop='bloom', apron=True, roll=6,
               eye_y=5, iris='green', jaw='oval', cheek=True, backhair=8, marks='freckles', surface='pocket', surfc='sage'),
    '153': dict(file='tavernkeep', cid=153, label='식당 주인',
                # "어서 오세요! 식당에 들어오신 걸 환영합니다" → 앞치마 + 국자
                female=True, skin='cfa47e', hair='a83a1e', braid=True, backhair=9,
                garb='kirtle', cloth='chalk', under='linen', extra='linen',
                legs='bloom', boot='boot', head='kerchief', headc='linen',
                prop='ladle', apron=True, roll=6,
               eye_y=4, iris='hazel', jaw='square', cheek=True, marks='ruddy', mouth_w=3, surface='pocket', surfc='bloom'),
}

_orig_props = tf.props


def bandana(s, r, seed=0):
    """뱃사람 반다나 — 정수리만 두르고 뒤에서 묶는다.

    ★garments.headscarf를 쓰면 안 된다(1차 실패): 그건 사막 두건이라 뺨까지 늘어지고
      등으로 꼬리가 내려가서, 머리가 통째로 벽돌색 상자가 되고 이마가 사라졌다.
      반다나는 <b>2행만</b> 덮어 이마를 남기는 게 정체성이다 — 덮는 면적이 곧 옷의 종류다.
    """
    import random
    rnd = random.Random(seed + 7)
    s.f('head', 'top', 'outer').fill(r[3])
    for x in range(8):                                   # 정수리 접힘 — 단색이면 플라스틱
        if rnd.random() < 0.45:
            s.f('head', 'top', 'outer').col(x, r[2], 0, 3)
    for fname in ('front', 'right', 'left', 'back'):
        f = s.f('head', fname, 'outer')
        f.rect(0, 0, 7, 1, r[3] if fname == 'front' else r[2])
        f.row(1, r[1])                                   # 아래 테두리 = 천이 접힌 선
    bk = s.f('head', 'back', 'outer')                    # 뒤통수 매듭 + 짧은 끝단
    bk.rect(3, 2, 4, 2, r[3])
    bk.px(2, 3, r[2]); bk.px(5, 3, r[2])
    bk.px(3, 3, r[1])


def props(s, v, seed):
    f = s.f('body', 'front', 'outer')
    p = v.get('prop')
    if p == 'spyglass':                                  # 견시의 망원경
        f.rect(6, 5, 7, 8, tf.R('leather')[3])
        f.px(6, 5, tf.R('brass')[4]); f.px(7, 8, tf.R('brass')[2])
        f.col(6, tf.R('leather')[4], 6, 8)
        return
    if p == 'coil':                                      # 도입부 선원 — 가슴에 걸친 밧줄 코일
        # ★두 번 실패하고 정한 위치·색이다.
        #   1차 긴 노(oar): 8x12 가슴에 대각 자루를 얹으면 대각선이 평평해져
        #      '베이지색 수직 띠'로 읽힌다 → 이 해상도의 소품은 컴팩트한 덩어리뿐.
        #   2차 밝은 밧줄(sand)을 허리(y6~8)에: roll=5라 그 높이의 팔은 맨살인데
        #      밧줄이 같은 살구색이라 팔의 일부로 보였다.
        #   → 결론: <b>어두운 밧줄</b>을 <b>소매가 아직 천인 높이(y3~5)</b>에 둔다.
        #      그러면 위(감청 셔츠)·아래(벽돌 새시)·옆(어두운 소매) 전부와 값이 갈린다.
        rope = tf.R('leather'); hi = tf.R('sand'); dk = tf.R('walnut')
        f.rect(5, 3, 7, 5, rope[2])                      # 코일 덩어리
        f.px(5, 3, hi[3]); f.px(7, 5, dk[1])             # 광원(좌상)·그늘(우하)
        f.px(6, 4, dk[0])                                # 가운데 구멍 = '감긴 것'의 핵심
        f.px(5, 5, hi[2]); f.px(7, 3, rope[3])           # 감긴 결 2점
        return
    if p == 'bloom':                                     # 정원사의 꽃다발
        for i, x in enumerate((5, 6, 7)):
            f.px(x, 7 + (i % 2), tf.R('mustard')[4])
            f.px(x, 8 + (i % 2), tf.R('sage')[2])
        f.px(6, 10, tf.R('sage')[3])
        return
    _orig_props(s, v, seed)


def build(v):
    from skinlib import Skin
    s = Skin()
    seed = v['cid']
    tf.head(s, v, seed)
    if v.get('bandana'):                  # ★사막 두건이 아닌 뱃사람 반다나 (위 bandana() 주석 참고)
        bandana(s, tf.R(v['bandana']), seed)
    tf.body(s, v, seed)
    tf.extra_cut(s, v, seed)    # 조끼·멜빵·새시 — 실루엣 한 겹
    tf.surface(s, v, seed)      # 옷 무늬 (소품보다 먼저)
    tf.feminize(s, v, seed)     # ★여성 실루엣·옆머리 — 옷 다음, 소품 앞
    props(s, v, seed)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / f"cm_{v['file']}.png"))


if __name__ == '__main__':
    for k in sys.argv[1:] or V:
        print(build(V[k]))
