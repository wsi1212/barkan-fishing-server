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
    cream='c0b193', burgundy='6e2f3a', wine2='7d3f42', ochre='a8813a',
    ink='3a3a4a', sea='41645f', umber2='6b503a', mocha='7a5f45',
)

V = {
    # ── 기능 NPC (&b) ────────────────────────────────────────────────────
    '22': dict(file='paolo', cid=22, label='파올로 — 물고기 판매',
               # 23 루카와 한 어물전. 공통=방수 앞치마+비늘 / 개인=나이와 색
               skin='c39a72', hair='3f3128', beard='goatee',
               garb='apron', cloth='sea', under='cream', extra='leather',
               legs='canvas', boot='boot', head=None, prop='scales', roll=5),
    '23': dict(file='luca', cid=23, label='루카 — 물고기 판매',
               skin='b98a5c', hair='6b6154', beard='full', age=True,
               garb='apron', cloth='slate', under='cream', extra='leather',
               legs='canvas', boot='boot', head='cap', headc='sea',
               prop='scales', roll=5),
    '24': dict(file='lorenzo', cid=24, label='로렌초 — 길드 접수',
               # 마을에서 가장 격식. ★4 페리선장과 텍스처가 겹쳐 있었다
               skin='c39a72', hair='3f3128', beard='goatee',
               garb='coat', cloth='burgundy', under='cream', legs='ink',
               boot='boot_d', head=None, prop='ledger', accent='brass'),
    '25': dict(file='vito', cid=25, label='비토 — 대장간',
               # 마을 대장장이 셋(군터9·지크하르트117·비토)을 앞치마와 머리로 가른다:
               #   군터=머리수건+흰수염 / 지크=민머리+검댕 / 비토=곱슬머리+구리빛 그을음
               skin='ab7748', hair='2f2721', beard='full',
               garb='apron', cloth='canvas', under='oat', extra='leather_d',
               legs='charcoal', boot='boot_d', head=None, prop='tools', roll=4),
    '26': dict(file='brock', cid=26, label='브록 — 드릴 상점',
               # 광산 장비를 판다 → 마을에서 유일한 '광부' 어휘: 챙모자 + 두꺼운 장갑
               skin='a87a4e', hair='4a3a2a', beard='mutton',
               garb='jerkin', cloth='leather_d', under='canvas', legs='grey',
               boot='boot_d', head='cap', headc='mustard', prop='tools',
               sleeved=True),
    '27': dict(file='enzo', cid=27, label='엔초 — 일감 게시판',
               # ★[퀘스트] 태그지만 게시판=기능형. 관청 서기 어휘(디트리히19·프리츠120과 한 축)
               skin='c39a72', hair='5a4636',
               garb='tunic', cloth='ochre', under='cream', legs='ink',
               boot='boot', head='cap', headc='umber2', prop='satchel', roll=7),
    '101': dict(file='giovanna', cid=101, label='지오반나 — 요리',
                # "요리는 재료가 전부예요" → 여성 요리사. 그레고르57·프란츠21과 한 축이되
                #   여성 + 크림 앞치마 + 두건으로 갈린다
                female=True, skin='cfa47e', hair='3f2f24',
                garb='kirtle', cloth='wine2', under='cream', extra='cream',
                legs='wine2', boot='boot', head='kerchief', headc='cream',
                prop='ladle', apron=True, roll=6),

    # ── 퀘스트 NPC (&a[Q]) ───────────────────────────────────────────────
    '83': dict(file='leila', cid=83, label='레일라 — 밀정',
               # ★"...조용히. 벽에도 귀가 있어요. 교단에 대해 알고 싶다면" → 정보원.
               #   마을에서 유일하게 후드를 깊이 눌러쓰고 색을 뺀다
               female=True, skin='b98a5c', hair='2f2721',
               garb='kirtle', cloth='ink', under='grey', legs='ink',
               boot='boot_d', head='hood', headc='ink', prop='pouch'),
    '96': dict(file='carlo', cid=96, label='카를로 — 향신료·생선 사업',
               skin='b98a5c', hair='3f3128', beard='goatee',
               garb='coat', cloth='ochre', under='cream', legs='umber2',
               boot='boot', head=None, prop='pouch', accent='brass'),
    '97': dict(file='silvia', cid=97, label='실비아 — 감정 견습',
               # "감정 일을 배우고 있어요" → 젊은 견습. 사피르78(사막 감정사)의 손저울과
               #   같은 소품이되 옷은 훨씬 수수하다
               female=True, skin='d0a57f', hair='5a4230',
               garb='kirtle', cloth='sea', under='cream', legs='sea',
               boot='boot', head=None, prop='ledger', braid=True),
    '98': dict(file='roberto', cid=98, label='로베르토 — 창고 관리',
               skin='c39a72', hair='4a3d2f', beard='stubble',
               garb='tunic', cloth='umber2', under='oat', legs='charcoal',
               boot='boot', head=None, prop='ledger', roll=7),
    '99': dict(file='fabio', cid=99, label='파비오 — 신참 선원',
               # "이제 막 배를 탄 신참입니다" → 가장 어리고 옷이 헐렁하다
               skin='c9a077', hair='4a3a2a', child=True,
               garb='tunic', cloth='sea', under='cream', legs='canvas',
               boot='boot', head=None, prop='rope', roll=6, patch='leg_l'),
    '100': dict(file='teresa', cid=100, label='테레사 — 시장 20년',
                # 110 아스트리드(스폰 20년 장사꾼)와 같은 이력 → 색과 소품으로 가른다
                female=True, age=True, skin='c99a70', hair='7a6e5f',
                garb='kirtle', cloth='ochre', under='cream', extra='cream',
                legs='ochre', boot='boot', head='kerchief', headc='wine2',
                prop='basket', apron=True),

    # ── 일반 주민 ────────────────────────────────────────────────────────
    '84': dict(file='antonio', cid=84, label='안토니오 — 짐꾼',
               # 랄프134(스폰 짐꾼)와 같은 직업 → 색·머리·소품으로 가른다
               skin='ab7748', hair='2f2721', beard='stubble',
               garb='jerkin', cloth='mocha', under='cream', legs='grey',
               boot='boot', head='cap', headc='wine2', prop='sack', patch='leg_r'),
    '85': dict(file='giulia', cid=85, label='줄리아 — 상단 회계',
               # ★"숫자는 거짓말을 하지 않아요. 장부만 보면 다 알 수 있죠"
               #   구스킨은 대장간에 있을 사람처럼 보였다(유저 지적) — 잉크빛 커틀 + 장부
               female=True, skin='d0a57f', hair='4f3b2a',
               garb='kirtle', cloth='ink', under='cream', legs='ink',
               boot='boot_d', head=None, prop='ledger', accent='brass'),
    '86': dict(file='francesco', cid=86, label='프란체스코 — 40년 노잡이',
               # "이 바다에서 40년을 저었지" → 늙은 뱃사람. 구스킨은 현대 의사 복장
               skin='b0855e', hair='9a938a', beard='full', age=True,
               garb='tunic', cloth='slate', under='oat', legs='grey',
               boot='boot', head='cap', headc='sea', prop='rope', roll=4),
    '87': dict(file='claudia', cid=87, label='클라우디아 — 향신료 상인',
               # "사막 건너 온 귀한 물건" → 사막과 거래하는 여성. 색을 조금 쓴다
               female=True, skin='c99a70', hair='3f2f24',
               garb='kirtle', cloth='burgundy', under='cream', legs='burgundy',
               boot='boot', head='kerchief', headc='ochre', prop='vialset',
               braid=True),
    '88': dict(file='vincenzo', cid=88, label='빈센초 — 술집 주인',
               # "여행 끝에 한잔이 최고지" → 넉넉한 체구 + 앞치마 + 술잔
               skin='c39a72', hair='6b5540', beard='mutton',
               garb='apron', cloth='wine2', under='cream', extra='cream',
               legs='charcoal', boot='boot', head=None, prop='tankard', roll=6),
    '89': dict(file='salvatore', cid=89, label='살바토레 — 그물 수선',
               # 페더133(스폰 그물장이)과 같은 직업 → 색·나이·모자로 가른다
               skin='ab7748', hair='4a3a2a', beard='stubble',
               garb='tunic', cloth='olive', under='oat', legs='canvas',
               boot='boot', head=None, prop='net', roll=4),
    '90': dict(file='rosa', cid=90, label='로사 — 생선 장수',
               female=True, skin='cfa47e', hair='5a4230',
               garb='kirtle', cloth='sea', under='cream', extra='oat',
               legs='sea', boot='boot', head='kerchief', headc='rust',
               prop='scales', apron=True, roll=6),
    '91': dict(file='massimo', cid=91, label='마시모 — 짐꾼(노년)',
               # "등이 다 나갔지" → 84 안토니오보다 늙고 굽었다
               skin='b0855e', hair='7a6e5f', beard='full', age=True,
               garb='jerkin', cloth='umber2', under='oat', legs='grey',
               boot='boot', head=None, prop='sack', patch='leg_l'),
    '92': dict(file='gianni', cid=92, label='잔니 — 배 목수(조선공)',
               # "이 배들, 내가 다 손봤지" → 볼프강104(마을 목수)와 같은 어휘,
               #   다만 배 목수라 타르 얼룩과 굵은 팔
               skin='ab7748', hair='4a3d2f', beard='full',
               garb='apron', cloth='oat', under='oat', extra='umber2',
               legs='charcoal', boot='boot', head=None, prop='tools', roll=4),
    '94': dict(file='domenico', cid=94, label='도메니코 — 은퇴한 뱃사람',
               # "이 다리로는 이제 배를 못 타지" → 가장 낡은 옷 + 지팡이 대신 담요 숄
               skin='b0855e', hair='9a938a', beard='full', age=True,
               garb='tunic', cloth='grey', under='oat', legs='charcoal',
               boot='boot', head='cap', headc='slate', prop='shawl',
               shawl='burgundy', roll=6, patch='leg_r'),
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
    seed = v['cid']
    tf.head(s, v, seed)
    tf.body(s, v, seed)
    props(s, v, seed)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / f"tt_{v['file']}.png"))


if __name__ == '__main__':
    for k in sys.argv[1:] or V:
        print(build(V[k]))
