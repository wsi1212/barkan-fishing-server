#!/usr/bin/env python3
"""튜토리얼 인트로 배 승무원 — 선장 1 + 선원 3.

맥락  TutorialIntroManager가 신규 플레이어를 망망대해 배에 떨어뜨리고 "나는 고아다..."
      독백 3줄 뒤 3막 입항 컷씬으로 바르칸에 도착시킨다. 즉 <b>게임에서 처음 보는 사람들</b>이다.
      기존 선원(cid 160, crewmisc '160')이 이미 이 배에 있고, 그와 <b>같은 배 소속</b>으로 읽혀야 한다.

SET ARCHITECTURE
  묶는 축(같은 배)   소금 절은 감청(brine)·카키(deck)·벽돌(rust) — 기존 선원 160의 팔레트를 공유.
  가르는 축(개인)    나이 · 재단 · 머리쓰개 · 소품. 넷이 서로, 그리고 아래 8명과도 안 겹쳐야 한다.

  ★반드시 피해야 할 기존 뱃사람 8명 (전수 확인)
      이자벨라55  여성 선장 · navy coat + tar cap + 장부 + 진홍 새시
      페리선장4   노인 · navy coat + navy cap + 놋쇠 + 밧줄
      마테오51    jerkin deck + 밧줄 + 굵은 팔 + 흉터
      엔리코52    apron tar + leather_d + 화약 그을음 + 공구
      조반니54    tunic brine + 멜빵 + 장부
      피노53      아이 · tunic oat + 밧줄 + 주근깨
      니코56      jerkin brine + hood + 망원경
      선원160     wrap brine + 벽돌 반다나 + 밧줄 코일 + 구레나룻
    → coat(선장 2명)·jerkin(2명)·hood(1명)·밧줄(4명)·장부(2명)는 이미 포화다.

  ★소품 2종 신설: compass(선장의 황동 나침반) · sailneedle(돛 수선용 큰 바늘+실)
    기존 소품(rope·ledger·spyglass·tools)은 전부 이미 쓰이고 있어 구분자가 못 된다.
"""
import pathlib
import zlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import townsfolk as tf                     # noqa: E402
import crewmisc as cmisc                   # noqa: E402  (bandana() 재사용)

OUT = pathlib.Path(__file__).parent / 'out'

tf.C.update(
    tar='2f2c28', brine='47575c', deck='7a6f5c', crimson='8f2b32',
    seagreen='4a6b63',      # 인트로 배만의 색 — 승무원 8명 중 아무도 안 쓴다
    twine='b8a678',         # 삼끈·돛실
)

V = {
    # ── 선장 ──────────────────────────────────────────────────────────────
    'captain': dict(file='ci_captain', cid=None, label='인트로 배 선장',
                    # ★navy coat + cap은 이자벨라·페리선장이 이미 쓴다 → 짙은 청록(seagreen)
                    #   코트 + 검댕 모자로 뺀다. 노인이지만 페리선장(full beard)과 갈리게
                    #   mutton(구레나룻형) 수염 + 안대 대신 굵은 눈썹·흉터로 연륜을 준다.
                    skin='b0855e', hair='9a938a', beard='mutton', age=True,
                    garb='coat', cloth='seagreen', under='linen', legs='tar',
                    boot='boot_d', head='cap', headc='soot', prop='compass',
                    accent='brass',
                    surface=('buttons', 'trim'), surfc='brass',
                    layer2='sash', l2c='crimson',
                    eye_y=4, iris='grey', jaw='square', brow_w=2,
                    marks='scar', socket=True, bootrows=6),

    # ── 선원 3 ────────────────────────────────────────────────────────────
    'deck': dict(file='ci_deckhand', cid=None, label='인트로 배 갑판원',
                 # 젊고 팔을 걷은 갑판원. 피노(아이)와 달리 성인이고, 마테오(jerkin)와 달리
                 # wrap 없는 소박한 튜닉 + 맨팔. 소품은 신설 sailneedle(돛 수선).
                 skin='c09468', hair='a05a2a', beard=None,
                 garb='tunic', cloth='deck', under='canvas', legs='brine',
                 boot='boot', head=None, prop='sailneedle',
                 roll=4, sleeved=True,
                 surface='seams', surfc='canvas',
                 eye_y=4, iris='green', jaw='narrow', marks='freckles', bootrows=3),

    'cook': dict(file='ci_cook', cid=None, label='인트로 배 취사',
                 # ★넷 중 유일한 여성 — 같은 배 4명이면 성별부터 갈려야 한다.
                 #   엔리코(apron tar)와 달리 밝은 앞치마 + 두건, 소품은 식량 자루.
                 female=True, skin='cfa47e', hair='5f4636',
                 garb='kirtle', cloth='brine', under='linen', extra='linen',
                 legs='linen', boot='boot', head='kerchief', headc='rust',
                 prop='sack', apron=True,
                 sleeve=5, hem=7, bare=True, bootrows=2,
                 surface='pocket', surfc='linen',
                 eye_y=5, iris='hazel', jaw='oval', cheek=True, backhair=8, braid=True),

    'rigger': dict(file='ci_rigger', cid=None, label='인트로 배 돛 담당',
                   # 기존 선원160도 반다나지만 색이 다르다(160=rust / 이쪽=twine 삼끈색).
                   #   재단은 wrap이 160 몫이니 jerkin 대신 smock(승무원 중 미사용)으로.
                   skin='9c7146', hair='2f2721', beard='stubble',
                   garb='smock', cloth='brine', under='oat', legs='deck',
                   boot='boot', head=None, bandana='twine', prop='rope',
                   yoke=3, roll=6,
                   surface='patchwork', surfc='deck',
                   eye_y=5, iris='dark', jaw='square', brow_a=1, bootrows=4),
}

_orig_props = tf.props


def props(s, v, seed):
    f = s.f('body', 'front', 'outer')
    p = v.get('prop')
    if p == 'compass':
        # 선장의 황동 나침반 — 목에 건 줄 + 둥근 몸통. 아무도 안 쓰는 소품이라 선장 표식이 된다
        # ★가슴 중앙(x3~4)에 두면 진홍 새시와 겹쳐 묻힌다(실측) → 오른쪽으로 뺀다.
        br, gl = tf.R('brass'), tf.R('chalk')
        f.px(6, 1, br[2]); f.px(6, 2, br[1])              # 목줄(비대칭으로 한 줄만)
        f.rect(6, 3, 7, 5, br[3])                         # 케이스
        f.px(6, 3, br[4]); f.px(7, 5, br[1])              # 광원 좌상 / 그늘 우하
        f.px(7, 4, gl[4]); f.px(6, 4, br[2])              # 유리면 반사 + 눈금
        return
    if p == 'sailneedle':
        # 돛 수선 — 큰 바늘 + 감은 실. 세로로 세우면 지팡이로 보이니 짧고 굵게
        ir, tw = tf.R('iron'), tf.R('twine')
        f.rect(6, 4, 6, 7, ir[4])                         # 바늘대
        f.px(6, 4, ir[2])                                 # 바늘귀
        f.px(7, 5, tw[4]); f.px(7, 6, tw[3])              # 감긴 실
        f.px(5, 7, tw[2])
        return
    _orig_props(s, v, seed)


def build(v):
    from skinlib import Skin
    s = Skin()
    # ★파이썬 hash()는 문자열에 프로세스별 랜덤 시드가 붙어 <b>빌드마다 결과가 달라진다</b>
    #   (실측: 두 번 빌드에 339픽셀 차이). 스킨 생성기는 반드시 결정적이어야 하므로
    #   crc32로 고정한다 — 같은 파일명이면 언제 빌드해도 같은 스킨이 나온다.
    seed = zlib.crc32(v['file'].encode()) % 9973
    tf.head(s, v, seed)
    if v.get('bandana'):
        cmisc.bandana(s, tf.R(v['bandana']), seed)
    tf.body(s, v, seed)
    tf.extra_cut(s, v, seed)
    tf.surface(s, v, seed)
    tf.feminize(s, v, seed)
    props(s, v, seed)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / f"{v['file']}.png"))


if __name__ == '__main__':
    for k in sys.argv[1:] or V:
        print(build(V[k]))
