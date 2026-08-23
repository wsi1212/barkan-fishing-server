#!/usr/bin/env python3
"""상단마을(이탈리아풍 무역 항구) 주민 세트.

townsfolk.py의 빌더를 그대로 재사용하고 팔레트만 갈아끼운다 — 같은 재단 어휘에서
나와야 서버 전체가 한 세계로 읽히고, 색으로 마을이 갈린다.

  왕도  = 진홍 · 강철 · 금 · 잉크 남보라
  스폰  = 바랜 청록 · 오트밀 · 가죽 · 캔버스
  사막  = 표백 리넨 · 테라코타 · 인디고 · 황토 · 구리
  ★상단 = 크림 · 버건디 · 황토금 · 올리브   (르네상스 무역항의 색)

구스킨 실태 (2026-08-02 유저 전수 지적)
  용납 불가  22 파올로=팀포2 스파이 · 83 레일라=사람 눈이 아님 · 84 안토니오=검은 머리통
             · 87 클라우디아 · 90 로사=옷에 자기 얼굴을 박은 닌자 · 92 잔니=서양 부자+선글라스
             · 94 도메니코=찢은 청바지 · 98 로베르토=장르가 다름 · 99 파비오=빨간 눈+방탄조끼
             · 100 테레사 / 86 프란체스코 = 현대 의사 복장
  이상함    88 빈센초·143 지오반니=머리가 해피 가스트 · 89 살바토레=스카우터
             · 91 마시모=안경 쓴 현대인 · 96 카를로=눈이 이상 · 85 줄리아=대장간 사람 같음
             · 97 실비아=그림체 다름 · 101 지오반나=요리와 안 맞음
  ★143 지오반니는 스킨을 만들어뒀는데 prod 미적용이라 88 빈센초와 텍스처가 겹쳐 있었다
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import townsfolk as tf                     # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'

# 상단마을 전용 색 추가 (townsfolk의 공용 팔레트에 얹는다)
tf.C.update(
    # ★'cream'으로 두면 townsfolk의 밝은 cream을 덮어써 상단마을 흰옷이
    #   전부 중간톤이 된다(실측: 테레사 0.61·실비아 0.49). 이름을 분리.
    sail='c0b193', burgundy='6e2f3a', wine2='7d3f42', ochre='a8813a',
    ink='3a3a4a', sea='41645f', umber2='6b503a', mocha='7a5f45',
)

V = {
    # ── 기능 NPC (&b) ────────────────────────────────────────────────────
    '22': dict(file='paolo', cid=22, label='파올로 — 물고기 판매',
               # 23 루카와 한 어물전. 공통=방수 앞치마+비늘 / 개인=나이와 색
               skin='b08b67', hair='241f1c', beard='goatee',
               garb='apron', cloth='sea', under='sail', extra='leather',
               legs='canvas', boot='boot', head=None, prop='scales', roll=5,
               eye_y=4, iris='dark', jaw='square', marks='ruddy', surface='pocket', surfc='linen', bootrows=3),
    '23': dict(file='luca', cid=23, label='루카 — 물고기 판매',
               skin='ad8156', hair='6b6154', beard='full', age=True,
               garb='apron', cloth='slate', under='sail', extra='leather',
               legs='canvas', boot='boot', head='cap', headc='sea',
               prop='scales', roll=5,
               eye_y=5, iris='hazel', jaw='long', surface='seams', surfc='slate', bootrows=5),
    '24': dict(file='lorenzo', cid=24, label='로렌초 — 길드 접수',
               # 마을에서 가장 격식. ★4 페리선장과 텍스처가 겹쳐 있었다
               skin='c99f76', hair='4a2f22', beard='goatee',
               garb='coat', cloth='burgundy', under='sail', legs='ink',
               boot='boot_d', head=None, prop='ledger', accent='brass',
               eye_y=3, iris='hazel', jaw='narrow', brow_a=1, surface=('placket', 'buttons'), surfc='brass', layer2='vest', l2c='burgundy'),
    '25': dict(file='vito', cid=25, label='비토 — 대장간',
               # 마을 대장장이 셋(군터9·지크하르트117·비토)을 앞치마와 머리로 가른다:
               #   군터=머리수건+흰수염 / 지크=민머리+검댕 / 비토=곱슬머리+구리빛 그을음
               skin='ab7748', hair='241f1c', beard='full',
               garb='apron', cloth='canvas', under='oat', extra='leather_d',
               legs='charcoal', boot='boot_d', head=None, prop='tools', roll=4,
               eye_y=4, iris='dark', jaw='square', brow_w=2, socket=True, surface='patchwork', surfc='soot', layer2='gloves', l2c='leather_d'),
    '26': dict(file='brock', cid=26, label='브록 — 드릴 상점',
               # 광산 장비를 판다 → 마을에서 유일한 '광부' 어휘: 챙모자 + 두꺼운 장갑
               skin='a87a4e', hair='4a3a2a', beard='mutton',
               garb='jerkin', cloth='leather_d', under='canvas', legs='grey',
               boot='boot_d', head='cap', headc='mustard', prop='tools',
               sleeved=True,
               eye_y=5, iris='dark', jaw='square', brow_w=2, marks='scar', surface='seams', surfc='iron', layer2='gloves', l2c='leather_d'),
    '27': dict(file='enzo', cid=27, label='엔초 — 일감 게시판',
               # ★[퀘스트] 태그지만 게시판=기능형. 관청 서기 어휘(디트리히19·프리츠120과 한 축)
               skin='b58f6a', hair='8f4a24',
               garb='tunic', cloth='ochre', under='sail', legs='ink',
               boot='boot', head='cap', headc='umber2', prop='satchel', roll=7,
               eye_y=4, iris='green', jaw='long', fringe=1, surface='placket', surfc='linen'),
    '101': dict(file='giovanna', cid=101, label='지오반나 — 요리',
                # "요리는 재료가 전부예요" → 여성 요리사. 그레고르57·프란츠21과 한 축이되
                #   여성 + 크림 앞치마 + 두건으로 갈린다
                female=True, skin='cfa47e', hair='b9903f', hem=10, sleeve=7,
                garb='kirtle', cloth='chalk', under='sail', extra='sail',
                legs='wine2', boot='boot', head='kerchief', headc='sail',
                prop='ladle', apron=True, roll=6,
               eye_y=5, iris='hazel', jaw='oval', cheek=True, backhair=7, surface='pocket', surfc='wine2'),

    # ── 퀘스트 NPC (&a[Q]) ───────────────────────────────────────────────
    '83': dict(file='leila', cid=83, label='레일라 — 밀정',
               # ★"...조용히. 벽에도 귀가 있어요. 교단에 대해 알고 싶다면" → 정보원.
               #   마을에서 유일하게 후드를 깊이 눌러쓰고 색을 뺀다
               female=True, skin='a89055', hair='241f1c', hem=11, sleeve=9,
               garb='kirtle', cloth='ink', under='grey', legs='ink',
               boot='boot_d', head='hood', headc='ink', prop='pouch',
               eye_y=5, iris='grey', jaw='narrow', backhair=9, brow_a=1, surface='lacing', surfc='ink'),
    '96': dict(file='carlo', cid=96, label='카를로 — 향신료·생선 사업',
               skin='b98a5c', hair='a89a6f', beard='goatee',
               garb='coat', cloth='ochre', under='sail', legs='umber2',
               boot='boot', head=None, prop='pouch', accent='brass',
               eye_y=4, iris='amber', jaw='oval', marks='mole', surface=('trim', 'buttons'), surfc='brass', layer2='sash', l2c='ochre'),
    '97': dict(file='silvia', cid=97, label='실비아 — 감정 견습',
               # "감정 일을 배우고 있어요" → 젊은 견습. 사피르78(사막 감정사)의 손저울과
               #   같은 소품이되 옷은 훨씬 수수하다
               female=True, skin='e0bcae', hair='c2a052', off=True, hem=11, sleeve=7,
               garb='kirtle', cloth='cream', under='sail', legs='sea',
               boot='boot', head=None, prop='ledger', braid=True,
               eye_y=5, iris='blue', jaw='narrow', backhair=8, marks='freckles', surface='placket', surfc='ink'),
    '98': dict(file='roberto', cid=98, label='로베르토 — 창고 관리',
               skin='c39a72', hair='4a3d2f', beard='stubble',
               garb='tunic', cloth='umber2', under='oat', legs='charcoal',
               boot='boot', head=None, prop='ledger', roll=7,
               eye_y=4, iris='brown', jaw='square', surface='pocket', surfc='canvas', layer2='vest', l2c='umber2'),
    '99': dict(file='fabio', cid=99, label='파비오 — 신참 선원',
               # "이제 막 배를 탄 신참입니다" → 가장 어리고 옷이 헐렁하다
               skin='ba946e', hair='a05a2a', child=True,
               garb='tunic', cloth='sea', under='sail', legs='canvas',
               boot='boot', head=None, prop='rope', roll=6, patch='leg_l',
               eye_y=5, iris='blue', jaw='narrow', fringe=3, marks='freckles', surface='seams', surfc='sea', bootrows=2),
    '100': dict(file='teresa', cid=100, label='테레사 — 시장 20년',
                # 110 아스트리드(스폰 20년 장사꾼)와 같은 이력 → 색과 소품으로 가른다
                female=True, age=True, skin='ba8f68', hair='7a6e5f', wrapshawl='moss', hem=11, sleeve=9,
                garb='kirtle', cloth='cream', under='sail', extra='sail',
                legs='ochre', boot='boot', head='kerchief', headc='wine2',
                prop='basket', apron=True,
               eye_y=5, iris='grey', jaw='long', backhair=6, marks='ruddy', surface='stripe_v', surfc='sail'),

    # ── 일반 주민 ────────────────────────────────────────────────────────
    '84': dict(file='antonio', cid=84, label='안토니오 — 짐꾼',
               # 랄프134(스폰 짐꾼)와 같은 직업 → 색·머리·소품으로 가른다
               skin='6b4a30', hair='2f2721', beard='stubble',
               garb='jerkin', cloth='mocha', under='sail', legs='grey',
               boot='boot', head='cap', headc='wine2', prop='sack', patch='leg_r',
               eye_y=5, iris='dark', jaw='square', brow_w=2, marks='scar', surface='seams', surfc='mocha', layer2='suspenders', l2c='canvas', bootrows=6),
    '85': dict(file='giulia', cid=85, label='줄리아 — 상단 회계',
               # ★"숫자는 거짓말을 하지 않아요. 장부만 보면 다 알 수 있죠"
               #   구스킨은 대장간에 있을 사람처럼 보였다(유저 지적) — 잉크빛 커틀 + 장부
               female=True, skin='d0a57f', hair='a83a1e', bootrows=2, bare=True, hem=7, sleeve=2, braid=True,
               garb='kirtle', cloth='ink', under='sail', legs='linen',
               boot='boot_d', head=None, prop='ledger', accent='brass',
               eye_y=5, iris='dark', jaw='narrow', backhair=8, surface='trim', surfc='brass'),
    '86': dict(file='francesco', cid=86, label='프란체스코 — 40년 노잡이',
               # "이 바다에서 40년을 저었지" → 늙은 뱃사람. 구스킨은 현대 의사 복장
               skin='b0855e', hair='9a938a', beard='full', age=True,
               garb='tunic', cloth='slate', under='oat', legs='grey',
               boot='boot', head='cap', headc='sea', prop='rope', roll=4,
               eye_y=4, iris='blue', jaw='long', socket=True, marks='ruddy', surface='seams', surfc='slate', bootrows=6),
    '87': dict(file='claudia', cid=87, label='클라우디아 — 향신료 상인',
               # "사막 건너 온 귀한 물건" → 사막과 거래하는 여성. 색을 조금 쓴다
               female=True, skin='c2856e', hair='c25a2a', hem=10, sleeve=7,
               garb='kirtle', cloth='burgundy', under='sail', legs='burgundy',
               boot='boot', head='kerchief', headc='ochre', prop='vialset',
               braid=True,
               eye_y=5, iris='green', jaw='oval', cheek=True, backhair=9, surface='trim', surfc='brass'),
    '88': dict(file='vincenzo', cid=88, label='빈센초 — 술집 주인',
               # "여행 끝에 한잔이 최고지" → 넉넉한 체구 + 앞치마 + 술잔
               skin='c99f76', hair='6b5540', beard='mutton',
               garb='apron', cloth='wine2', under='sail', extra='sail',
               legs='charcoal', boot='boot', head=None, prop='tankard', roll=6,
               eye_y=4, iris='amber', jaw='square', marks='ruddy', mouth_w=3, surface='quilt', surfc='wine2', layer2='vest', l2c='umber2'),
    '89': dict(file='salvatore', cid=89, label='살바토레 — 그물 수선',
               # 페더133(스폰 그물장이)과 같은 직업 → 색·나이·모자로 가른다
               skin='ab7748', hair='8f4a24', beard='stubble',
               garb='tunic', cloth='olive', under='oat', legs='canvas',
               boot='boot', head=None, prop='net', roll=4,
               eye_y=5, iris='green', jaw='square', brow_w=2, surface='patchwork', surfc='canvas', layer2='suspenders', l2c='leather'),
    '90': dict(file='rosa', cid=90, label='로사 — 생선 장수',
               female=True, skin='b08b6b', hair='9c7a4e', bootrows=2, bare=True, hem=7, sleeve=5, backhair=8,
               garb='kirtle', cloth='chalk', under='sail', extra='oat',
               legs='linen', boot='boot', head='kerchief', headc='rust',
               prop='scales', apron=True, roll=6,
               eye_y=5, iris='brown', jaw='oval', cheek=True, surface='pocket', surfc='sea'),
    '91': dict(file='massimo', cid=91, label='마시모 — 짐꾼(노년)',
               # "등이 다 나갔지" → 84 안토니오보다 늙고 굽었다
               skin='b0855e', hair='7a6e5f', beard='full', age=True,
               garb='jerkin', cloth='umber2', under='oat', legs='grey',
               boot='boot', head=None, prop='sack', patch='leg_l',
               eye_y=4, iris='grey', jaw='long', socket=True, marks='sunken', surface='patchwork', surfc='umber2'),
    '92': dict(file='gianni', cid=92, label='잔니 — 배 목수(조선공)',
               # "이 배들, 내가 다 손봤지" → 볼프강104(마을 목수)와 같은 어휘,
               #   다만 배 목수라 타르 얼룩과 굵은 팔
               skin='ab7748', hair='c2a052', beard='full',
               garb='apron', cloth='oat', under='oat', extra='umber2',
               legs='charcoal', boot='boot', head=None, prop='tools', roll=4,
               eye_y=5, iris='amber', jaw='square', marks='freckles', surface='pocket', surfc='oat', layer2='suspenders', l2c='leather_d'),
    '94': dict(file='domenico', cid=94, label='도메니코 — 은퇴한 뱃사람',
               # "이 다리로는 이제 배를 못 타지" → 가장 낡은 옷 + 지팡이 대신 담요 숄
               skin='b0855e', hair='9a938a', beard='full', age=True,
               garb='tunic', cloth='grey', under='oat', legs='charcoal',
               boot='boot', head='cap', headc='slate', prop='shawl',
               shawl='burgundy', roll=6, patch='leg_r',
               eye_y=4, iris='grey', jaw='long', socket=True, brow_w=2, surface='quilt', surfc='grey'),
}

# 소품 확장 — 향신료 병 세트(클라우디아)
_orig_props = tf.props


def props(s, v, seed):
    if v.get('prop') == 'vialset':
        f = s.f('body', 'front', 'outer')
        for i, key in enumerate(('ochre', 'burgundy', 'moss')):
            f.px(6, 7 + i * 2, tf.R('cream')[4]); f.px(7, 7 + i * 2, tf.R(key)[3])
        f.px(6, 6, tf.R('leather')[2])
        if v.get('patch'):
            import garments as g
            g.patch(s, v['patch'], 'front', tf.R('canvas'), x=1, y=5, w=2, h=2,
                    layer='outer')
        return
    _orig_props(s, v, seed)


def build(v):
    from skinlib import Skin
    s = Skin()
    v = tf.restyle(v)   # ★여성 개정표(두건축소·네크라인·장신구) — head()보다 먼저여야 한다
    seed = v['cid']
    tf.head(s, v, seed)
    tf.body(s, v, seed)
    tf.extra_cut(s, v, seed)    # 조끼·멜빵·새시 — 실루엣 한 겹
    tf.surface(s, v, seed)      # 옷 무늬 (소품보다 먼저)
    # ★'shawl'은 prop='shawl' 색 지정에 이미 쓰이는 키다(충돌 회귀 있었음) → wrapshawl
    if v.get('wrapshawl'):  # 노인 여성의 어깨 숄 — 옷 다음, feminize 앞
        tf.g.shawl(s, tf.R(v['wrapshawl']), y0=0, drop=v.get('shawldrop', 4), seed=seed)
    tf.feminize(s, v, seed)     # ★여성 실루엣·옆머리 — 옷 다음, 소품 앞
    props(s, v, seed)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / f"tt_{v['file']}.png"))


if __name__ == '__main__':
    for k in sys.argv[1:] or V:
        print(build(V[k]))
