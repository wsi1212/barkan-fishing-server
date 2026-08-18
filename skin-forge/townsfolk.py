#!/usr/bin/env python3
"""스폰도시(항구 마을) 주민 세트 — 한 파일에서 표로 관리한다.

왜 한 파일인가
  왕도가 '제복 세트'(위병·도서관)라면 스폰마을은 ★한 마을에 사는 서로 다른 직업들이다.
  같은 옷을 입히면 안 되지만, 같은 팔레트·같은 재단 어휘에서 나와야 '한 마을'로 읽힌다.
  그래서 옷 종류·머리쓰개·소품은 사람마다 다르게, 색은 마을 팔레트 안에서만 고른다.

마을 팔레트 (왕도와 대비되는 축)
  왕도  = 진홍 · 강철 · 금 · 잉크 남보라   (권력과 기록의 색)
  스폰  = 바랜 청록 · 오트밀 리넨 · 가죽 갈색 · 캔버스 회갈   (바다와 노동의 색)
  ★원색·네온·검정 정장·청바지 전면 금지. 금속 악센트는 있어도 1곳.

구스킨 실태 (2026-08-01 전수조사, 41명 중 30명이 이질)
  애니/포켓몬  134 랄프 · 139 발터(분홍 장발) · 136 미아 · 138 프리다 · 110 아스트리드
  현대 복장    103 그레첸(정장+선글라스) · 105 잉가(후디+청바지) · 106 디르크(체크셔츠)
               · 107 헬무트(멜빵+안경) · 140 루디(검정 정장) · 141 루드비히(넥타이)
  게임 스킨    133 페더(파란 몸+다이아 무늬) · 75 리나(노란 이모지 얼굴) · 71 세르간(왕관)
"""
import colorsys
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'))

import garments as g                      # noqa: E402
from skinlib import Skin, mix, ramp, hair_ramp       # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'

# ── 마을 공용 색. 개인은 여기서 골라 쓰고, 새 색을 함부로 들이지 않는다 ──────────
C = dict(
    teal='4f6f6a', teal_d='39544f', slate='55606b', navy='3c4756',
    oat='c2b298', linen='c8c0ac', canvas='847e6e', sand='ab967a',
    leather='6b4f36', leather_d='45362a', boot='3f342a', boot_d='352c24',
    rust='8a5340', wine='6e3a3a', moss='6f8358', olive='616a58',
    grey='837d73', charcoal='413c36', flour='b6b0a2', mustard='c4a44f',
    brass='b08d3c', iron='8a8e93',
    # ── 2026-08-03 다양성 패스 추가분 ─────────────────────────────────────
    # 왜: 위 색만으로 37명을 입혔더니 명도가 전부 한 구간(0.36~0.82)에 몰려
    #     "다 비슷비슷하다"는 지적을 받았다(실측: 어두운 옷 0명·갈색 76%).
    #     세트를 구분하는 건 색상보다 ★명도 대비다 → 진짜 어두운 값과 진짜
    #     밝은 값을 팔레트에 넣고, 마을 안에서 쿼터로 배분한다.
    #     게이트: diversity_lint.py (위반 시 빌드 실패)
    # (1) 진짜 어두움 — 기존 charcoal조차 form_fill 밝기 보정 뒤엔 중간톤이 된다
    pitch='23211f', soot='2c2823', walnut='33241a', ink='232c3a',
    moss_d='2f3a28', olive_d='2f3327',
    # (2) 진짜 밝음 — 표백 리넨/밀가루. 요리·제빵·방앗간·학자에만
    # ★LIT_COMP가 한 단 내리므로 흰 계열은 선언값을 그만큼 올려 둔다
    chalk='e6e2d6', cream='ded7c2', bone='d0c9b0',
    # (3) 시대 염료 — '원색 금지'의 예외가 아니라 실재한 천연염료다. 비싼 물건이라
    #     소수에게만 주면 오히려 '이 사람은 좀 산다'가 읽힌다(가수·길드·전령·상단)
    madder='9c3a2c',      # 꼭두서니 빨강
    woad='2f4f7e',        # 대청 파랑
    weld='d6aa3c',        # 웰드 노랑
    verdigris='2a6b5e',   # 녹청
    # (4) 장신구 전용 (2026-08-07) — 옷 색과 같은 값을 쓰면 목걸이가 옷에
    #     묻힌다. 금속·보석은 <b>주변보다 확실히 밝거나 확실히 어두워야</b> 읽힌다.
    silver='c8ccd2', pearl='e8e2d4', copper='a8622f',
    # ── 2026-08-18 중복 분해용 ─────────────────────────────────────────────
    # 겉옷을 «색 계열»로 묶어 세니 청록 7·주황갈 8 로 몰리고 보라 계열은 0 이었다.
    # 게다가 slate 를 브리기테·헬가가 같이 써서 오너가 "둘이 똑같아 보인다"고 지적.
    # 같은 계열 안에서 갈라 줄 중간 색조 + 비어 있던 보라를 채운다.
    seafoam='6f9a8a', pine='3a5a4a', dusk='5a6480', fern='7a8f52',
    plum='6a4560', ochre='b8873a', brick='9c5340',
    lagoon='3f7d78', mulberry='7d3f58', straw='c8b06a',
    coral='c2564e', amber='c8892c', jet='2a2622',
)

# 피부톤 — 색상각이 23~30°에 전원 몰려 있어 '전부 같은 살색'이었다(실측 폭 5.6°).
# 항구 마을이니 뱃사람·내륙 상인·실내직이 섞인다. 붉은기/올리브기/창백 셋을 더해
# 색상 폭을 넓힌다(게이트 하한 18°).
SKIN = dict(
    ruddy='c98a72',    # 붉은기 — 바닷바람에 익은 얼굴
    olive='a89055',    # 올리브·황색기 — 남쪽 항로를 오간 사람
    pale='e0bcae',     # 창백 — 실내에서 일하는 사람
    deep='6b4a30',     # 짙은 갈색
)


# ── 렌더 보정 (2026-08-03 v3, "다 파스텔톤" 지적) ──────────────────────────
# 실측: 옛 NameMC 원본 34명 = 채도평균 0.43·명도평균 0.43 / 우리 v2 = 0.33·0.56.
# 즉 우리 옷은 원본보다 ★밝고 흐리다 = 파스텔. 원인은 팔레트가 아니라 렌더 규약이다:
#   garments가 쓰는 form_fill(base_idx=3)은 앞면을 ramp[2](선언한 색)가 아니라
#   ramp[3](한 단 위)으로 칠한다 → 선언값보다 명도 +spread/4, 게다가 ramp()가 위로
#   갈수록 채도를 깎는다(sat=0.16) → 모든 옷이 자동으로 밝고 흐려진다.
# 대응: 램프를 한 단 내려서 ★선언한 hex가 앞면에 그대로 나오게 하고, 위로 가며 깎이는
# 채도만큼 미리 얹는다. 팔레트 hex를 안 건드리고 마을 전체가 원본 대비로 내려온다.
# (garments.py의 base_idx를 고치는 게 근본이지만 그건 전 마을 143명 재빌드가 걸린다)
LIT_COMP = True     # 앞면 = 선언색 (끄면 v2 동작)
SAT_LIFT = 1.22     # 램프 상단 채도 손실 + 뮤트 과다 보정


_DEEP = False   # ★현재 빌드 중인 NPC 가 '진짜 더러워야 하는' 사람인가
                #   (spec 의 grime=True). True 면 옛 대칭 램프를 그대로 쓴다.


def R(key, spread=0.55):
    """마을 색을 램프로. ★spread를 명도에 맞춰 자동으로 좁힌다(양끝 클리핑 방지) +
    앞면에 선언색이 그대로 나오도록 한 단 내리고 채도를 보정한다.

    2026-08-03(1차): 고정 spread로는 팔레트 양끝을 못 쓴다 — chalk(0.84)는 위가
    순백으로 잘리고(실측: helmut 순백 56px = audit ERROR), pitch(0.14)는 아래가
    검정으로 잘린다. 램프 양끝이 [0.06, 0.95] 안에 들어오도록 spread를 깎는다.
    2026-08-03(2차): 위 LIT_COMP/SAT_LIFT 보정 추가.
    """
    h, s, v = colorsys.rgb_to_hsv(*[int(C[key][i:i + 2], 16) / 255 for i in (0, 2, 4)])
    sp = min(spread, 2 * (0.95 - v), 2 * (v - 0.06))
    if LIT_COMP:
        v = max(0.06, v - sp / 4)          # ramp[3]이 원래 선언값이 되도록 한 단 내림
        s = min(1.0, s * SAT_LIFT + 0.04)  # 램프가 위로 가며 깎는 채도만큼 미리 얹음
        sp = min(sp, 2 * (0.95 - v), 2 * (v - 0.06))
    r, g_, b = colorsys.hsv_to_rgb(h, s, v)
    return ramp('%02x%02x%02x' % (round(r * 255), round(g_ * 255), round(b * 255)),
                spread=sp, deep=_DEEP)


# ── 변주 표 ────────────────────────────────────────────────────────────────
# garb: tunic(짧은 튜닉) / jerkin(가죽 조끼) / apron(앞치마 직군) / coat(롱코트)
#       / kirtle(여성 원피스) / robe(학자 가운)
# head: None / cap / kerchief / hood / coif
# prop: None / sack / net / ledger / lantern / tools / basket / yarn / pouch / book
VARIANTS = {
    # ── 항구 노동자 ──────────────────────────────────────────────────────
    '134': dict(file='ralf', grime=True, cid=134, label='랄프 — 항구 짐꾼',
                # "짐이 무거워도 이 일이 좋아" → 등짐꾼. 소매 없는 튜닉 + 어깨 짐받이
                skin='6b4a30', hair='4a3a2a', beard='stubble',
                garb='jerkin', cloth='leather', under='oat', legs='slate', boot='boot',
                head=None, prop='sack', roll=2, patch='leg_r',
                surface=('patchwork', 'seams'), surfc='canvas',
                layer2='suspenders', l2c='canvas',
                eye_y=5, iris='dark', jaw='square', brow_w=2, mouth_w=3, marks='scar', bootrows=6),
    '133': dict(file='feder', grime=True, cid=133, label='페더 — 그물 손질',
                # "그물 손질은 손끝 감각이 전부지" → 어망 수선공. 그물을 어깨에 건다
                skin='6b4a30', hair='6b6154', beard='full', age=True,
                cloth='teal', under='walnut', legs='sand', boot='boot',
                head='cap', headc='teal_d', prop='net', roll=3,
                surface='seams', surfc='oat',
                garb='wrap', cross=5,
                eye_y=4, iris='grey', jaw='long', fringe=1, marks='ruddy', bootrows=3),
    '106': dict(file='dirk', grime=True, cid=106, label='디르크 — 부두 관리',
                # "부두 관리가 제 일입니다" → 관리자. 마을에서 가장 갖춰 입은 축
                # ★도란73(상단)과 코트+캡+염소수염이 겹쳐 사실상 쌍둥이였다(픽셀차 9.2).
                #   대청 파랑 관복 + 흑발로 갈라 놓는다(도란은 녹청).
                skin='ab835c', hair='241f1c', beard='goatee',
                garb='coat', cloth='woad', under='canvas', legs='ink', boot='boot_d',
                head='cap', headc='woad', prop='ledger', accent='brass',
                surface=('placket', 'buttons'), surfc='brass',
                eye_y=3, iris='hazel', jaw='narrow', brow_a=1, mouth_y=6, bootrows=5),
    '139': dict(file='walter', grime=True, cid=139, label='발터 — 야경꾼',
                # "밤에도 누군가는 항구를 지켜야지" → 후드 망토 + 등불
                # ★마을의 '가장 어두운 사람' 자리 — 야경꾼이라 명분도 맞는다
                skin='8a6440', hair='4f4a42', beard='full', age=True,
                garb='coat', cloth='pitch', under='sand', legs='olive_d',
                boot='boot_d', head='hood', headc='pitch', prop='lantern',
                accent='iron',
                surface='seams', surfc='iron',
                folds=(1, 5),
                eye_y=4, iris='amber', jaw='square', brow_w=2, socket=True, marks='sunken'),
    '104': dict(file='wolfgang', cid=104, label='볼프강 — 목수',
                # "이 마을 목재는 다 내 손을 거쳐 갔지" → 톱밥 앞치마 + 연장
                skin='ab835c', hair='5a4636', beard='mutton',
                garb='apron', cloth='straw', under='linen', extra='leather',
                legs='walnut', boot='boot', head=None, prop='tools', roll=4,
                surface='pocket', surfc='canvas',
                layer2='suspenders', l2c='leather_d',
                eye_y=5, iris='brown', jaw='square', mouth_w=3, marks='freckles', bootrows=3),
    '107': dict(file='helmut', cid=107, label='헬무트 — 방앗간',
                # "밀가루 먼지 마실 날이 없어요" → 온몸에 하얀 가루. 자루를 진다
                # ★마을의 '가장 밝은 사람' 자리 — 밀가루를 뒤집어쓰는 직업이라 명분도 맞는다
                skin='f0dac6', hair='7a6a52', beard='stubble',
                # ★모자까지 흰색으로 하면 머리와 몸통이 한 덩어리가 된다(1패스 자기비평).
                #   모자는 밀가루 안 묻은 낡은 캔버스로 눌러 얼굴선을 살린다
                cloth='cream', under='cream', legs='linen', boot='boot',
                head='cap', headc='sand', prop='sack', roll=3, dust=True,
                surface='stripe_v', surfc='sand',
                garb='smock', yoke=2,
                eye_y=4, iris='blue', jaw='long', fringe=3, cheek=True, bootrows=2),

    # ── 여성 주민 ────────────────────────────────────────────────────────
    '103': dict(file='gretchen', hstyle='bob', cid=103, label='그레첸 — 빵집',
                # "갓 구운 빵 냄새 좋지 않나요?" → 밀가루 앞치마 + 두건
                female=True, skin='f0dac6', hair='a83a1e', bootrows=2, bare=True, hem=7, sleeve=5, backhair=8,
                # 두건까지 표백 흰색이면 창백한 얼굴과 붙는다 — 두건만 한 단 낮춘다
                garb='kirtle', cloth='rust', under='pearl', extra='chalk',
                legs='charcoal', boot='boot', head='kerchief', headc='linen',
                prop='basket', apron=True,
                surface=('pocket', 'trim'), surfc='rust',
                eye_y=4, iris='green', jaw='oval', cheek=True, marks='freckles', mouth_y=6),
    '105': dict(file='inga', hstyle='wave', cid=105, label='잉가 — 물 긷는 여인',
                # "물 길으러 나왔어요" → 가장 소박한 차림. 금속 0곳
                female=True, skin='ab835c', hair='d9bb63', bare=True, hem=10, sleeve=2,
                cloth='moss', under='chalk', legs='pitch', boot='boot',
                head=None, prop='pouch', braid=True,
                surface='seams', surfc='oat',
                garb='overdress', over='canvas',
                eye_y=5, iris='grey', jaw='narrow', backhair=9, marks='ruddy'),
    '136': dict(file='mia', hstyle='sideswept', cid=136, label='미아 — 생선 손질',
                # "생선은 손질이 반이랍니다" → 방수 앞치마 + 걷은 소매 + 비늘
                # 방수 앞치마는 타르를 먹인 검정이 실물에 맞다 — 어물전 3인(헬가·그레타)과
                # 앞치마 색으로 갈리고, 마을의 '어두운 사람' 쿼터도 여기서 하나 채운다
                female=True, skin='b58c64', hair='c25a2a', bootrows=2, bare=True, hem=7, sleeve=2, braid=True,
                garb='kirtle', cloth='teal_d', under='bone', extra='pitch',
                legs='soot', boot='boot', head='kerchief', headc='teal',
                prop='scales', apron=True, roll=5,
                surface='pocket', surfc='teal',
                eye_y=4, iris='dark', jaw='narrow', backhair=9, brow_a=-1),
    '138': dict(file='frieda', hstyle='sideswept', cid=138, label='프리다 — 항구 가수',
                # "항구엔 늘 노랫거리가 있죠" → 마을에서 유일하게 색을 좀 쓴다
                # ★그 '색을 쓴다'가 말뿐이었다(와인색=채도 0.28). 꼭두서니 빨강 + 웰드
                #   노랑 숄로 실제 유채색 자리를 준다 — 무대에 서는 사람이니 명분도 맞다
                female=True, skin='d8b490', hair='1b1a24', off=True, bare=True, hem=11, sleeve=5,
                garb='kirtle', cloth='madder', under='flour', legs='navy', boot='boot',
                head=None, prop='shawl', shawl='weld', braid=True,
                surface=('lacing', 'trim'), surfc='weld',
                layer2='sash', l2c='weld',
                eye_y=3, iris='green', jaw='oval', backhair=9, cheek=True, lip='a8484a'),

    # ── 아이 / 젊은이 ────────────────────────────────────────────────────
    '137': dict(file='leo', cid=137, label='레오 — 부두 아이',
                # "갈매기들이 자꾸 생선을 훔쳐가요!" → 헐렁한 물려받은 옷, 맨발
                skin='cba37c', hair='8a6a3f', child=True,
                cloth='seafoam', under='cream', legs='moss_d', boot=None,
                head=None, prop=None, roll=4, patch='leg_l',
                surface='patchwork', surfc='oat',
                garb='smock', yoke=3,
                eye_y=5, iris='hazel', fringe=4, marks='freckles', bootrows=0),
    # ── 퀘스트를 주는 주민 (&a[Q]) ────────────────────────────────────────
    '71': dict(file='sergan', cid=71, label='세르간 — 은퇴한 학자',
               # "나는 은퇴한 학자일세. 이 물길의 옛이야기를 좇지"
               # ★왕도 도서관(잉크 남보라)과 달라야 한다 — 시골로 물러난 학자의
               #   바랜 흙갈 가운. 구스킨은 빨간 왕관을 쓴 광대였다
               # ★가운을 바랜 흰색으로 — 마을에서 '밝은 사람' 한 자리를 학자가 맡는다
               skin='ead0b6', hair='9a938a', beard='full', age=True,
               garb='robe', cloth='bone', under='flour', legs='leather_d', boot='boot',
               head=None, prop='book',
                surface='trim', surfc='leather',
                # ★눈이 3행짜리 덩어리로 보였다(2026-08-04 지적). 백발이라 눈썹색이
                #   hair[3]=c2bbb5 → 흰자 c9c4b8와 RGB 총차 19(=같은 색)로 붙어버려
                #   눈썹 2행 + 눈 1행이 하나로 읽혔다. 눈썹을 1행으로 줄이고 짙은 회색을
                #   직접 지정 → 그 1행이 눈꺼풀 구실을 해서 눈이 2×2로 읽힌다.
                #   (socket은 눈썹 y와 같은 행이라 항상 덮여 무의미했으므로 제거)
                eye_y=4, iris='grey', jaw='long', fringe=0,
                brow_w=1, brow_c='5b544c'),
    '72': dict(file='marie', hstyle='twin', cid=72, label='마리 — 조합 재료상',
               # "조합에 쓸 재료가 늘 부족해요" → 재료를 다루는 손. 도구 앞치마
               female=True, skin='debd9c', hair='241f1c', bare=True, sleeve=5,
               garb='kirtle', cloth='olive', under='bone', extra='canvas',
               legs='grey', boot='boot', head=None, prop='tools',
               apron=True, roll=6, braid=True,
                surface='pocket', surfc='canvas',
                hem=10,
                eye_y=4, iris='brown', jaw='oval', backhair=8, marks='mole'),
    '73': dict(file='doran', cid=73, label='도란 — 상단 바르칸 지부',
               # "상단 바르칸 지부의 도란이라 하오" → 마르코82(상단마을)의 하급 동료.
               #   버건디는 마르코 몫이니 여기는 짙은 청록 + 놋쇠 한 곳
               skin='bd946c', hair='3f3128', beard='goatee',
               garb='coat', cloth='verdigris', under='chalk', legs='olive',
               boot='boot_d', head='cap', headc='verdigris', prop='pouch',
               accent='brass',
                surface=('placket', 'buttons'), surfc='brass',
                eye_y=3, iris='dark', jaw='narrow', brow_a=1, bootrows=5),
    '108': dict(file='brigitte', hstyle='sideswept', cid=108, label='브리기테 — 직조공',
                # "옷감을 짜는 게 제 일이에요" → 실타래와 부드러운 옷감
                # 적발 — 마을에 없던 머리색. 실타래를 다루는 사람이라 색이 붙어도 안 튄다
                female=True, skin='e4c6a8', hair='8f4a24', hem=10, sleeve=7,
                cloth='slate', under='canvas', legs='canvas',
                boot='boot', head='kerchief', headc='oat', prop='yarn',
                surface='check', surfc='oat',
                garb='overdress', over='oat',
                eye_y=4, iris='amber', jaw='oval', backhair=9, cheek=True),
    '109': dict(file='siegfried', cid=109, label='지그프리트 — 사냥꾼',
                # "사냥이든 낚시든, 실력은 눈으로 봐야 알지" → 후드 + 가죽 + 화살통
                skin='96704a', hair='4a3a2a', beard='stubble',
                garb='jerkin', cloth='moss_d', under='linen', legs='olive_d',
                boot='boot_d', head='hood', headc='moss_d', prop='quiver', sleeved=True,
                surface='seams', surfc='leather',
                folds=(2,),
                eye_y=4, iris='green', jaw='square', brow_w=2, socket=True, bootrows=6),
    '110': dict(file='astrid', hstyle='centerpart', cid=110, label='아스트리드 — 20년 장사꾼',
                # "장사 20년, 단골들이 물고기를 찾는답니다" → 억센 상인 여성
                female=True, age=True, skin='c49b74', hair='7a6e5f', wrapshawl='wine', hem=11, sleeve=9,
                cloth='brick', under='sand', extra='rust',
                legs='grey', boot='boot', head='kerchief', headc='mustard',
                prop='ledger', apron=True,
                surface='stripe_v', surfc='oat',
                garb='overdress', over='walnut',
                eye_y=5, iris='hazel', jaw='square', backhair=7, marks='ruddy'),
    '135': dict(file='sven', cid=135, label='스벤 — 낚싯배 선장',
                # "낚싯배를 몰려면 실력부터 보여야지" → 방수 코트 + 선장 모자 + 밧줄
                skin='8a6440', hair='6b6154', beard='full', age=True,
                garb='coat', cloth='ink', under='oat', legs='slate',
                boot='boot_d', head='cap', headc='ink', prop='rope',
                accent='brass',
                surface=('buttons', 'trim'), surfc='brass',
                layer2='sash', l2c='brass',
                eye_y=4, iris='blue', jaw='square', brow_w=2, marks='ruddy', bootrows=6),
    '140': dict(file='rudi', cid=140, label='루디 — 전령',
                # "소식을 전하는 게 제 일인데, 배가 고파서 원..." → 마르고 젊다.
                #   달리기 좋은 짧은 튜닉 + 어깨 가방. 왕도 전령149의 화려함과 반대
                skin='96704a', hair='4a3d2f',
                cloth='weld', under='pearl', legs='sand',
                boot='boot', head='cap', headc='canvas', prop='satchel', roll=6,
                surface='placket', surfc='canvas',
                garb='wrap', cross=3,
                eye_y=5, iris='brown', jaw='narrow', fringe=3, mouth_w=3, bootrows=2),
    '29': dict(file='marta', hstyle='centerpart', cid=29, label='마르타 — 시장 안내',
               # "싱싱한 건 제값 쳐주는 게 시장 인심이죠" → 활기찬 시장 상인
               female=True, skin='cba37c', hair='9c7a4e', bootrows=2, bare=True, hem=7, sleeve=2,
               # 앞치마는 크림이 아니라 표백 흰색이어야 금색 드레스와 값이 갈린다
               garb='kirtle', cloth='ochre', under='canvas', extra='chalk',
               legs='navy', boot='boot', head=None, prop='basket',
               apron=True, braid=True,
                surface='stripe_v', surfc='linen',
                eye_y=4, iris='brown', jaw='oval', backhair=8, cheek=True, mouth_w=3),
    '30': dict(file='bettina', hstyle='bob', cid=30, label='베티나 — 요리 안내',
               # "이 주방에선 잡은 걸로 근사한 요리를 만든답니다" → 주방 보조
               female=True, skin='debd9c', hair='2b2118', bootrows=2, bare=True, hem=7, sleeve=5, braid=True,
               garb='kirtle', cloth='fern', under='pearl', extra='chalk',
               legs='pitch', boot='boot', head='kerchief', headc='chalk',
               prop='ladle', apron=True,
                surface='pocket', surfc='moss',
                eye_y=5, iris='hazel', jaw='oval', backhair=9, marks='freckles'),
    '28': dict(file='felix', cid=28, label='펠릭스 — 대장간 견습',
               # "여긴 대장간이에요. 좋은 장비가 좋은 어부를 만들죠!" → 젊고 들뜬 견습.
               #   군터9(마스터)보다 앞치마가 작고 그을음이 적어야 계급이 읽힌다
               skin='b58c64', hair='8f4a24', child=False,
               garb='apron', cloth='canvas', under='linen', extra='leather',
               legs='ink', boot='boot', head=None, prop='tools', roll=5,
               patch='leg_l',
                surface='patchwork', surfc='canvas',
                layer2='suspenders', l2c='leather',
                eye_y=5, iris='blue', jaw='narrow', fringe=3, marks='freckles', bootrows=3),
    '17': dict(file='ingrid', hstyle='pulled', cid=17, label='잉그리드 — 길드 접수',
               # 길드 GUI 담당. 마을에서 가장 격식 있는 여성 — 장부와 인장
               # 대청 파랑 — 마을에서 가장 격식 있는 여성이라 비싼 염료가 명분이 된다
               female=True, skin='ead0b6', hair='b9903f', hem=10, sleeve=7,
               garb='kirtle', cloth='navy', under='cream', legs='charcoal',
               boot='boot_d', head=None, prop='ledger', accent='brass',
                surface=('trim', 'buttons'), surfc='brass',
                eye_y=3, iris='grey', jaw='narrow', backhair=9, brow_a=1),

    # ── 기능 NPC (&b) ────────────────────────────────────────────────────
    '9': dict(file='gunter', grime=True, cid=9, label='군터 — 마을 대장간',
              # ★왕실 대장장이 지크하르트117과 갈라야 한다: 지크=검댕 가죽·민머리·불똥.
              #   군터는 시골 노장 — 낡은 앞치마 + 머리 동여맨 천 + 흰 수염
              # 앞치마를 그을음색으로 — 대장간 사람이 마을에서 가장 어두운 축이 되는 게 맞다
              skin='bd946c', hair='8a8378', beard='full', age=True,
              garb='apron', cloth='canvas', under='walnut', extra='soot',
              legs='olive', boot='boot_d', head='kerchief', headc='rust',
              prop='tools', roll=4, patch='leg_r',
                surface='patchwork', surfc='leather',
                layer2='gloves', l2c='leather_d',
                eye_y=4, iris='dark', jaw='square', brow_w=2, socket=True, marks='scar'),
    '21': dict(file='franz', cid=21, label='프란츠 — 마을 요리',
               # ★왕실 요리장 그레고르57과 갈라야 한다: 그레고르=올리브+코이프+노장.
               #   프란츠는 젊고 소박 — 오트 튜닉 + 리넨 앞치마 + 맨머리 + 국자
               skin='debd9c', hair='4a3d2f', beard='stubble',
               garb='apron', cloth='pine', under='sand', extra='chalk',
               legs='linen', boot='boot', head=None, prop='ladle', roll=5,
                surface='pocket', surfc='teal',
                eye_y=5, iris='brown', jaw='oval', fringe=3, cheek=True, mouth_w=3),
    '6': dict(file='helga', hstyle='wave', cid=6, label='헬가 — 물고기 판매',
              # 오토14·그레타13과 한 어물전. 공통=방수 가죽 앞치마+비늘 / 개인=색과 나이
              female=True, skin='a17a52', hair='b0505e', bootrows=2, bare=True, hem=7, sleeve=5,
              garb='kirtle', cloth='dusk', under='oat', extra='leather',
              legs='leather_d', boot='boot', head='kerchief', headc='mustard',
              prop='scales', apron=True, roll=6,
                surface='pocket', surfc='mustard',
                eye_y=4, iris='hazel', jaw='square', backhair=8, marks='ruddy'),
    '13': dict(file='greta', hstyle='straight', cid=13, label='그레타 — 물고기 판매',
               # 어물전 셋 중 최고령. 색을 가장 뺀다
               female=True, age=True, skin='7a5638', hair='9a938a', wrapshawl='woad', hem=10, sleeve=7,
               cloth='grey', under='bone', extra='leather',
               legs='moss_d', boot='boot', head='kerchief', headc='oat',
               prop='scales', apron=True, roll=6,
                surface='check', surfc='oat',
                garb='overdress', over='charcoal',
                eye_y=4, iris='grey', jaw='long', backhair=6, socket=True),
    '7': dict(file='klaus', cid=7, label='클라우스 — 잡화 상점',
              # ★모래색 코트+가죽 캡+파우치는 '사냥꾼'으로 읽힌다(유저 지적).
              #   가게를 지키는 사람은 앞치마와 장부로 말한다 — 모자를 벗기고
              #   와인색 조끼 위에 상점 앞치마를 두른다
              skin='d2ab86', hair='a89a6f', beard='mutton',
              garb='apron', cloth='coral', under='chalk', extra='oat',
              legs='soot', boot='boot', head=None, prop='ledger',
              accent='brass', roll=7,
                surface='placket', surfc='oat',
                hem=11, folds=(2, 5),
                eye_y=4, iris='amber', jaw='square', mouth_w=3, marks='ruddy', bootrows=3),
    '8': dict(file='bruno', cid=8, label='브루노 — 섬상점',
              # 섬으로 배를 대는 사람. 항해 쪽 어휘(밧줄)로 클라우스와 갈린다
              skin='7a5638', hair='3f3128', beard='full',
              garb='coat', cloth='lagoon', under='flour', legs='canvas',
              boot='boot_d', head=None, prop='rope',
                surface='buttons', surfc='brass',
                collar=False, folds=(3,),
                eye_y=5, iris='blue', jaw='square', brow_w=2, marks='scar', bootrows=6),
    '18': dict(file='raimund', cid=18, label='라이문트 — 유저마켓',
               # 경매·중개. 장부와 놋쇠 한 곳
               skin='c49b74', hair='4a3d2f', beard='goatee',
               garb='coat', cloth='wine', under='pearl', legs='walnut',
               boot='boot_d', head=None, prop='ledger', accent='brass',
                surface='buttons', surfc='brass',
                folds=(1, 4, 6),
                eye_y=3, iris='dark', jaw='narrow', brow_a=1, mouth_w=1),
    '19': dict(file='dietrich', cid=19, label='디트리히 — 일감 게시판',
               # ★[퀘스트] 태그지만 게시판=기능형이다(대사로 퀘스트를 주는 [Q]가 아님).
               #   왕도 프리츠120과 같은 '관청 서기' 어휘를 쓰되 색으로 갈린다
               skin='d2ab86', hair='6b5540',
               garb='tunic', cloth='olive_d', under='chalk', legs='grey',
               boot='boot', head='cap', headc='olive_d', prop='satchel', roll=7,
                surface='placket', surfc='linen',
                layer2='vest', l2c='olive_d',
                eye_y=4, iris='green', jaw='long', fringe=1, brow_a=-1),
    '43': dict(file='oskar', cid=43, label='오스카 — 말 대여',
               # 마부. 가죽 저킨 + 밧줄. 왕도 알브레히트121과 색으로 갈린다
               skin='a17a52', hair='4a3a2a', beard='stubble',
               garb='jerkin', cloth='walnut', under='oat', legs='canvas',
               boot='boot_d', head='cap', headc='leather', prop='rope',
               sleeved=True,
                surface='seams', surfc='leather',
                layer2='gloves', l2c='leather',
                eye_y=5, iris='brown', jaw='square', marks='ruddy', bootrows=6),
    '141': dict(file='ludwig', cid=141, label='루드비히 — 여관 주인',
                # "이 마을에서 하룻밤 쉬어가시겠어요?" → 술잔과 앞치마, 넉넉한 체구
                skin='e4c6a8', hair='241f1c', beard='mutton',
                garb='apron', cloth='mulberry', under='cream', extra='cream',
                legs='charcoal', boot='boot', head=None, prop='tankard', roll=6,
                surface='quilt', surfc='wine',
                eye_y=4, iris='hazel', jaw='square', cheek=True, mouth_w=3, marks='ruddy'),
    # ── 신규: 스폰마을 회복 NPC (아직 서버에 없음 — 스킨 선제작) ──────────────
    'healer': dict(file='healer', cid=901, label='회복 NPC(신규) — 마을 약초사',
                   # ★왕도 회복 힐데122와 갈라야 한다: 힐데=회청 로브+흰 코이프+여성.
                   #   마을은 남성 노인 약초사 — 세이지 로브 + 약초 다발 + 붕대 감은 손
                   skin='c49b74', hair='9a938a', beard='full', age=True,
                   garb='robe', cloth='plum', under='linen', legs='olive',
                   boot='boot', head='hood', headc='moss', prop='herbs',
                surface='trim', surfc='linen',
                eye_y=4, iris='green', jaw='long', fringe=0, socket=True, brow_w=2),

    '3': dict(file='grandpa', cid=3, label='할아버지 — 튜토리얼 길잡이',
              # "바르칸의 물은 정직하단다 — 던진 만큼 돌려주지."
              # ★새 플레이어가 서버에서 처음 만나는 NPC. 구스킨은 분홍 만화 얼굴 +
              #   연보라 머리였다. 따뜻하고 기억에 남아야 하므로 마을에서 유일하게
              #   붉은 니트 모자를 씌운다(멀리서도 '그 할아버지'로 식별)
              # ★인게임에서 얼굴이 너무 밝다는 지적(2026-08-03) — 학자 세르간·어물전
              #   그레타와 같은 살색이었다. 평생 배를 탄 노인이라 한 단 그을린 톤으로.
              skin='8a6440', hair='9a938a', beard='full', age=True,
              garb='tunic', cloth='oat', under='bone', legs='pitch', boot='boot',
              head='cap', headc='rust', prop='shawl', shawl='teal', roll=8,
                surface='quilt', surfc='rust',
                layer2='vest', l2c='rust',
                eye_y=4, iris='blue', jaw='oval', fringe=1, socket=True, marks='ruddy'),
    '146': dict(file='chief', cid=146, label='촌장',
                # ★구스킨은 바닐라 주민(빌리저) 텍스처 — 사람이 아니라 몹으로 읽힌다.
                #   마을에서 가장 격식 있는 평민: 긴 코트 + 놋쇠 직위 사슬 + 마을 장부
                skin='d8b490', hair='9a938a', beard='full', age=True,
                garb='coat', cloth='jet', under='sand', legs='sand',
                boot='boot_d', head='coif', headc='grey', prop='book',
                accent='brass',
                surface=('trim', 'buttons'), surfc='brass',
                layer2='tabard', l2c='ink',
                # ★eye_y=3으로 올리면 코이프(0~3행)가 눈을 덮는다 — lint가 잡음
                eye_y=4, iris='grey', jaw='long', socket=True, brow_w=2, brow_a=1),

    '75': dict(file='rina', hstyle='wave', cid=75, label='리나 — 어부 지망 소녀',
               # "저도 언젠가 훌륭한 어부가 되고 싶어요" → 어른 옷을 줄여 입은 소녀
               female=True, child=True, skin='d2ab86', hair='7a5f3a',
               # ★브리기테108(슬레이트 커틀)과 쌍둥이가 돼서 어부색으로 바꾼다 —
               #   어부 지망 소녀가 어른 어부 옷을 줄여 입은 것으로 읽힌다
               garb='kirtle', cloth='teal_d', under='flour', legs='soot', boot='boot',
               head=None, prop='basket', braid=True, patch='leg_r',
                surface='patchwork', surfc='linen',
                eye_y=5, iris='green', backhair=9, fringe=3, marks='freckles', bootrows=2),
}


# ── 빌더 ───────────────────────────────────────────────────────────────────
def _set_deep(v):
    """'진짜 더러워야 하는' 직군만 옛 진흙 램프를 유지한다(오너 지시 2026-08-18)."""
    global _DEEP
    _DEEP = bool(v.get('grime'))


def head(s, v, seed):
    _set_deep(v)
    skin, hair = ramp(v['skin']), hair_ramp(v['hair'])
    g.head_base(s, skin, seed=seed)
    g.ears(s, skin, y=4)
    # ★얼굴 개인차 (2026-08-03) — 부위별 측정에서 머리가 가장 닮은 부위로 나왔다
    #   (자카드 0.561 vs 몸통 0.415·팔 0.310). 37명 전원이 눈 y=4·gaze=0·홍채 하나·
    #   입 y=6 w=2·앞머리 2로 똑같았기 때문. 옷에 했던 것과 같은 처방을 얼굴에 한다.
    # ★여성 앞머리는 한 단 낮춘다 — 레퍼런스 실측에서 잘 만든 여성 스킨은 이마가 거의
    #   없고 앞머리가 눈 바로 위까지 내려온다. 눈을 아래로 내리는 것과 짝으로 가야 한다.
    fringe = v.get('fringe', 3 if (v.get('child') or v.get('female')) else 2)
    g.hair(s, hair, fringe=fringe, back=v.get('backhair', 7 if v.get('female') else 6),
           seed=seed, part_x=v.get('part', 3 if v.get('female') else None))
    g.face_shape(s, skin, jaw=v.get('jaw', 'oval'), cheek=v.get('cheek', False))
    if v.get('beard'):
        # ★수염 시작 행은 눈보다 반드시 아래여야 한다 — 눈 높이를 사람마다 다르게
        #   한 뒤로 eye_y=5인 사람은 고정값 5와 충돌해 눈이 지워졌다(실측 3명)
        g.beard(s, hair_ramp(v['hair']), style=v['beard'],
                y=max(v.get('eye_y', 4) + 1, 6 if v['beard'] == 'mutton' else 5),
                seed=seed, ragged=False)
    if v.get('age'):
        g.wrinkles(s, skin, crow=True, forehead=v.get('head') is None)
    # ★여성 기본 눈높이 5 — 레퍼런스 여성 스킨은 눈이 얼굴 아래쪽(행 5~7)에 있다.
    #   위쪽(3~4)은 성인 남성 비율이다. 스펙에 eye_y를 명시했으면 그걸 존중한다.
    eye_y = v.get('eye_y', 5 if v.get('female') else 4)
    if v.get('female'):
        # ★4~5로 클램프한다. 위: 여성 앞머리를 fringe=3으로 낮췄기 때문에 eye_y=3이면
        #   앞머리가 눈을 덮어 <b>한쪽 눈이 사라진다</b>(실측: 잉그리드 왼쪽 눈이 먹혔다).
        #   아래: 2행 눈이라 6 이상이면 eye_y+1이 턱을 침범한다.
        eye_y = max(4, min(eye_y, 5))
    # ★표식(흉터·주근깨)을 눈보다 먼저 찍는다 — 나중에 찍으면 흉터가 흰자를 덮어
    #   눈이 반쯤 사라진다(실측: 랄프의 흉터가 오른쪽 눈을 지웠다)
    g.face_marks(s, skin, kind=v.get('marks'), seed=seed)
    iris_i = 1 if v.get('iris', 'brown') in ('blue', 'amber', 'hazel', 'grey') else 2
    if v.get('female'):
        # ★레퍼런스 실측: 눈동자가 채도 높은 색으로 또렷하다(보라·파랑). 우리는 거의
        #   검정(0e0f11·221910)이라 흰자만 남고 '흰 얼룩'으로 보였다. 한 단 밝게 올린다.
        iris_i = min(3, iris_i + 1)
    if v.get('female'):
        # ★2행 눈 — 흰자 면적이 남성용 eyes()의 4배. 레퍼런스와의 유일한 결정적 차이였다
        #   (우리 2px vs 레퍼런스 10~11px). garments.female_eyes_big 주석 참고.
        g.female_eyes_big(s, v.get('sclera', 'ece8dd'), ramp(g.IRIS[v.get('iris', 'brown')]),
                          skin, hair, eye_y=eye_y, gaze=v.get('gaze', 0), iris_idx=iris_i)
    else:
        g.eyes(s, v.get('sclera', 'ece8dd'), ramp(g.IRIS[v.get('iris', 'brown')]),
               y=eye_y, gaze=v.get('gaze', 0), socket=skin[1] if v.get('socket') else None,
               iris_idx=iris_i)
    # ★코 기둥(2026-08-18) — 하이픽셀 얼굴 공통 구조. x3~4 를 눈 행부터 한 단 밝게 해
    #   볼(어두움)과 갈라 준다. 이게 없으면 얼굴이 평평한 살색 판으로 읽힌다.
    _fh = s.f('head', 'front')
    for _y in range(eye_y, min(8, eye_y + 3)):
        for _x in (3, 4):
            _cur = _fh.get(_x, _y)
            if _cur[3]:
                _fh.px(_x, _y, mix(_cur, skin[4], 0.45))

    # ★눈 지워짐 검사 — desertfolk/dealers엔 있었는데 townsfolk엔 없어서 잉그리드의
    #   먹힌 눈을 빌드가 조용히 통과시켰다. 같은 가드를 여기도 둔다.
    _ef = s.f('head', 'front')
    if sum(1 for x in (1, 2, 5, 6) if max(_ef.get(x, eye_y)[:3]) > 150) < 2:
        raise ValueError('%s: 눈이 지워졌다 (eye_y=%d, fringe=%d)' % (v['file'], eye_y, fringe))

    # ★brow_c = 눈썹색 직접 지정. 백발(age=True→hair[3])은 흰자와 색이 겹쳐 눈썹이
    #   눈에 붙어 보이는데, 그 사람만 짙은 색으로 떼어내려면 예외구가 필요하다.
    # ★여성은 눈썹을 한 행 위로 올려 눈 바로 위(eye_y-1)를 속눈썹에 내준다.
    #   남성 [눈썹 eye_y-1][눈] / 여성 [눈썹 eye_y-2][속눈썹 eye_y-1][눈]
    #   — 이 구조 차이가 8x8에서 성별을 만드는 실제 지점이다(garments.female_eyes 주석 참고).
    #   eye_y<=3이면 눈썹 자리가 앞머리에 덮이므로 눈썹은 원래 자리에 두고 속눈썹만 넣는다.
    brow_up = bool(v.get('female')) and eye_y >= 4   # 속눈썹(eye_y-1) 자리를 비운다
    g.brow(s, ramp(v['brow_c'])[2] if v.get('brow_c')
           else (hair[2] if not v.get('age') else hair[3]),
           y=eye_y - (2 if brow_up else 1),
           weight=v.get('brow_w', 1), angle=v.get('brow_a', 0))
    f = s.f('head', 'front')
    if v.get('female'):
        # ★입술 — 2행 눈이 eye_y+1까지 차지하므로 그 아래 행에 놓는다. 그리고 아주 연하게:
        #   레퍼런스 여성 스킨은 대부분 입이 아예 없었고, 우리 입은 진한 갈색 사각형이라
        #   남성적 인상을 강화하고 있었다(실측). 피부에 절반 섞어 '암시'만 남긴다.
        my = v.get('mouth_y', min(7, eye_y + 2))
        lip = g.mix(skin[1], ramp(v.get('lip', '9b5a52'))[2], 0.55)
        f.px(3, my, lip); f.px(4, my, lip)
    else:
        # ★수염이 있으면 입을 더 어둡게 — 기본 skin[1]은 수염 톤과 명도가 붙어 입이
        #   사라진다(2026-08-05 선원 실측: 그루터기 886145 옆의 입 816037이 안 보였다).
        #   수염 속의 입은 '어두운 틈'이라 머리색을 절반 섞은 값이 맞다.
        g.mouth(s, skin, y=v.get('mouth_y', 6), w=v.get('mouth_w', 2),
                color=g.mix(skin[1], hair[1], 0.5) if v.get('beard') else None)
    if v.get('braid'):
        g.ponytail(s, hair, x0=3, w=2, y0=0, y1=5)
    # ★모자가 눈을 덮으면 안 된다(스킬 하드룰). eye_y를 아는 여기서 검사한다 —
    #   PNG만 보고 눈 행을 추정하는 방식은 후드 챙·머리 하이라이트에 오탐이 났다.
    if v.get('head') in ('hood', 'coif') and v.get('eye_y', 4) < 4:
        raise ValueError(f"{v['file']}: {v['head']}는 3행까지 덮는다 — eye_y를 4 이상으로")

    # ★눈이 살아 있는지 빌드 시점에 확인한다. 눈썹·모자·수염이 눈 행을 덮는 사고가
    #   반복됐고(굵은 눈썹 5명 소실), 렌더를 눈으로 훑는 것만으로는 놓친다.
    fchk = s.f('head', 'front')
    if sum(1 for x in (1, 2, 5, 6) if max(fchk.get(x, eye_y)[:3]) > 150) < 2:
        raise ValueError(f"{v['file']}: 눈이 지워졌다 (eye_y={eye_y}) — "
                         f"눈썹 두께/모자/수염이 눈 행을 덮는지 확인")

    hd = v.get('head')
    # ★맨머리 NPC의 hat 레이어를 비워두면 인게임에서 '모자를 안 씌운 것'처럼 보인다
    #   (유저 지적, 2026-08-02). 실제 유저 스킨은 거의 전부 머리카락에 겉레이어를 쓴다.
    if hd is None:
        g.hair_volume(s, hair, fringe=fringe, back=8, seed=seed)
    if hd == 'cap':
        g.hair_volume(s, hair, fringe=fringe, back=8, seed=seed)
        g.cap(s, R(v['headc']), crown=3, brim=False, seed=seed)
    elif hd == 'kerchief':
        # ★tail=False면 매끈한 돔이 되어 '겨울 니트 비니'로 읽힌다(유저 지적).
        #   뒤로 늘어뜨린 자락 + 관자놀이에 드러난 앞머리가 있어야 '천'으로 보이고,
        #   여성 NPC의 성별도 그때 읽힌다.
        g.headscarf(s, R(v['headc']), rows=2, tail=True, seed=seed)
        fo = s.f('head', 'front', 'outer')
        fo.rect(0, 2, 0, 3, hair[3]); fo.rect(7, 2, 7, 3, hair[3])
        fo.px(0, 4, hair[2]); fo.px(7, 4, hair[2])
    elif hd == 'hood':
        g.hood(s, R(v['headc']), opening=5, seed=seed)
    elif hd == 'coif':
        g.hair_volume(s, hair, fringe=fringe, back=8, seed=seed)
        g.cap(s, R(v['headc']), crown=4, brim=False, seed=seed)

    # ★앞머리 모양 — 반드시 <b>머리쓰개 분기 다음</b>이어야 한다. hair() 직후에 뒀더니
    #   위 hd 분기의 hair_volume() 재호출이 통째로 덮어써서 <b>아무 효과가 없었다</b>
    #   (실측: outer 알파가 개정 전후 완전히 동일). 렌더만 보고 "미묘하다"고 넘겼으면
    #   기능이 죽은 걸 모른 채 배포할 뻔했다.
    # ★맨머리만 — 두건·후드는 앞머리를 천이 가리므로 모양을 줘봐야 안 보인다.
    if v.get('fstyle') and hd is None:
        g.fringe_style(s, hair, style=v['fstyle'], eye_y=eye_y, seed=seed, skin_r=skin)
        # 앞머리를 다시 깎았으니 눈 검사도 다시 한다 — 가드는 마지막 상태를 봐야 한다
        fchk2 = s.f('head', 'front')
        if sum(1 for x in (1, 2, 5, 6) if max(fchk2.get(x, eye_y)[:3]) > 150) < 2:
            raise ValueError(f"{v['file']}: fringe_style '{v['fstyle']}'가 눈을 덮었다 "
                             f"(eye_y={eye_y})")


def body(s, v, seed):
    skin = ramp(v['skin'])
    cloth, under = R(v['cloth']), R(v['under'])
    legs = R(v['legs'])
    garb = v['garb']

    # base — 6면 전부 불투명하게 끝낸다(안 그러면 인게임에 구멍)
    g.tunic(s, under, y0=0, y1=11, collar=True, seed=seed, grain=0.07, hem=False)
    g.sleeves(s, under, y0=0, y1=11, seed=seed, grain=0.07)
    g.hands(s, skin, rows=2)
    # ★바지는 부츠가 시작되는 행까지 내려와야 한다 — 부츠 목을 낮추면(bootrows<4)
    #   그 사이가 투명하게 뚫린다(실측: 발목부츠 6명 audit ERROR)
    boot_rows = v.get('bootrows', 4) if v.get('boot') else 0
    g.pants(s, legs, y0=0, y1=11 if garb == 'kirtle' else 11 - boot_rows, seed=seed)
    if v.get('boot'):
        g.boots(s, R(v['boot']), rows=v.get('bootrows', 4), toe=True,
                cuff=v.get('bootcuff', True))
    else:                                                # 맨발(아이)
        # ★바지가 7행에서 끝나므로 8행부터 채워야 한다. 9부터 채우면 정강이에
        #   투명 링이 생겨 인게임에서 다리가 잘려 보인다(실측)
        for part in ('leg_r', 'leg_l'):
            s.form_fill(part, skin, 8, 11, base_idx=3, bottom=True)
            s.shade_col_falloff(part, skin, 8, 11)

    # ★다리 비대칭 (2026-08-18, 오너 지적 "다리가 둘 다 똑같은 게 맘에 안 든다")
    #   기존에도 무릎 패치 같은 게 있었지만 1~2px라 인게임 배율에서 좌우가 같아 보였다.
    #   레퍼런스 73장은 «전원» 좌우가 다르다. 읽히는 크기(가로 띠 2행 또는 무릎 블록)로
    #   한쪽 다리에만 넣는다. 무엇을 넣을지는 이름 해시로 정해 결정적이다.
    import zlib as _z
    _pick = _z.crc32(v['file'].encode()) % 3
    _side = 'leg_l' if (_z.crc32((v['file'] + 'side').encode()) % 2) else 'leg_r'
    _lr = legs
    if _pick == 0:                      # 한쪽만 바짓단을 접어 올림 = 밝은 가로 띠 2행
        _y = max(2, 11 - boot_rows - 1)
        s.band(_side, _y - 1, _y, _lr[4])
        s.band(_side, _y + 1, _y + 1, _lr[1])
    elif _pick == 1:                    # 한쪽 무릎에 덧댄 천 (3x3)
        s.f(_side, 'front').rect(0, 4, 2, 6, _lr[1])
        s.f(_side, 'front').rect(0, 4, 2, 4, _lr[3])
    else:                               # 한쪽 정강이에 끈 각반 2줄
        for _y in (5, 8):
            s.band(_side, _y, _y, _lr[0])

    # ★재단 개인차 (2026-08-03) — 지금까지 같은 재단이면 칼라·헴·주름 열이 코드
    #   수준에서 동일했다(주름은 전원 cols=(1,6)). 사람마다 옷을 다시 재단한다.
    fold_sets = ((1, 6), (2, 5), (1, 5), (2, 6), (3,), (1, 4, 6))
    fc = v.get('folds') or fold_sets[seed % len(fold_sets)]
    hem_y = v.get('hem', 10)

    if garb == 'wrap':                                   # 여며 입는 튜닉
        g.wrap_tunic(s, cloth, y0=0, hem=hem_y, layer='outer', seed=seed,
                     cross=v.get('cross', 4), lining=under)
        for part in ('arm_r', 'arm_l'):
            s.form_fill(part, cloth, 0, v.get('roll', 8), layer='outer', base_idx=3)
            s.hem(part, v.get('roll', 8), cloth, layer='outer', base_idx=3)
        g.belt(s, R('leather'), y=9, layer='outer')
    elif garb == 'smock':                                # 헐렁한 작업 스목
        g.smock(s, cloth, y0=0, hem=11, yoke=v.get('yoke', 2), layer='outer', seed=seed)
        for part in ('arm_r', 'arm_l'):
            s.form_fill(part, cloth, 0, v.get('roll', 6), layer='outer', base_idx=3)
            s.hem(part, v.get('roll', 6), cloth, layer='outer', base_idx=3)
    elif garb == 'overdress':                            # 커틀 위 소매 없는 겉드레스
        # ★커틀은 그 사람의 정체성 색(cloth) 그대로 두고, 겉드레스만 대비색(over).
        #   반대로 하면 붉은 커틀이 통째로 덮여 사람이 베이지 덩어리가 된다(v5 자기비평)
        _sleeve = v.get('sleeve', v.get('roll', 9))
        _hem = v.get('hem', 11)
        g.robe(s, cloth, y0=0, seed=seed, hem_row=_hem, sleeve_to=_sleeve, lining=under)
        g.overdress(s, R(v.get('over', 'canvas')), y0=1, hem=_hem, layer='outer', seed=seed)
        g.belt(s, R('leather'), y=7, layer='outer')
        if v.get('bare') and _sleeve < 9:
            g.bare_arms(s, skin, _sleeve + 1, 11)
    elif garb == 'jerkin':                                 # 소매 없는 가죽 저킨
        # ★vest()는 가운데를 넓게 터서 셔츠를 보여주는 '조끼'다. 짐꾼처럼 통짜로
        #   껴입는 저킨에 쓰면 가슴 한가운데가 창백한 판때기가 된다(실측).
        s.form_fill('body', cloth, 0, 10, layer='outer', base_idx=3, top=True)
        s.speckle('body', cloth, 0, 10, layer='outer', density=0.09, seed=seed)
        s.folds('body', 2, 9, cloth, layer='outer', cols=(1, 6), seed=seed)
        s.folds('body', 2, 9, cloth, layer='outer', cols=(2, 5), face='back', seed=seed + 3)
        s.f('body', 'front', 'outer').col(4, cloth[1], 0, 10)
        s.f('body', 'front', 'outer').col(3, cloth[4], 0, 10)
        s.hem('body', 10, cloth, layer='outer', base_idx=3)
        if v.get('sleeved'):                             # 저킨 안에 셔츠를 남긴다
            for part in ('arm_r', 'arm_l'):
                s.form_fill(part, under, 0, 9, layer='outer', base_idx=3)
                s.speckle(part, under, 0, 9, layer='outer', density=0.08, seed=seed)
                s.hem(part, 9, under, layer='outer', base_idx=3)
            g.belt(s, R('leather'), y=9, accent=None, layer='outer')
            return
        for part in ('arm_r', 'arm_l'):                  # 맨팔 — 짐꾼의 굵은 팔뚝
            # 살색 한 톤으로 채우면 '마네킹 팔'이 된다. 원통 음영 + 그레인 필수
            s.form_fill(part, skin, 0, 11, base_idx=3, top=True, bottom=True)
            s.shade_col_falloff(part, skin, 0, 11)
            s.speckle(part, skin, 1, 10, density=0.10, seed=seed + ord(part[-1]))
        for part, y in (('arm_r', 3), ('arm_l', 5)):     # 비대칭 팔 근육 하이라이트
            s.f(part, 'front').col(1, skin[4], y, y + 2)
        g.belt(s, R('leather'), y=9, accent=None, layer='outer')
    elif garb == 'tunic':
        g.tunic(s, cloth, y0=0, y1=hem_y, layer='outer', collar=v.get('collar', True),
                seed=seed, grain=0.08, fold_cols=fc, hem=False)
        s.hem('body', hem_y, cloth, layer='outer', base_idx=3)
        s.folds('body', 2, hem_y - 1, cloth, layer='outer', cols=fc, seed=seed)
        s.folds('body', 2, hem_y - 1, cloth, layer='outer',
                cols=fc[::-1], face='back', seed=seed + 3)
        for part in ('arm_r', 'arm_l'):
            s.form_fill(part, cloth, 0, v.get('roll', 8), layer='outer', base_idx=3)
            s.hem(part, v.get('roll', 8), cloth, layer='outer', base_idx=3)
        g.belt(s, R('leather'), y=9, layer='outer')
    elif garb == 'coat':
        g.coat(s, cloth, y0=0, hem=11, tails=3, seed=seed, lapel=True)
        for part in ('arm_r', 'arm_l'):
            s.form_fill(part, cloth, 0, 9, layer='outer', base_idx=3)
            s.speckle(part, cloth, 0, 9, layer='outer', density=0.08, seed=seed)
            s.hem(part, 9, cloth, layer='outer', base_idx=3)
        g.belt(s, R('leather_d'), y=8,
               accent=R(v['accent']) if v.get('accent') else None, layer='outer')
    elif garb == 'apron':
        g.tunic(s, cloth, y0=0, y1=11, layer='outer', collar=True, seed=seed, grain=0.08)
        for part in ('arm_r', 'arm_l'):
            s.form_fill(part, cloth, 0, v.get('roll', 6), layer='outer', base_idx=3)
            s.hem(part, v.get('roll', 6), cloth, layer='outer', base_idx=3)
        g.apron(s, R(v['extra']), bib=(1, 6), bib_y=(1, 6), waist=7, hem=11,
                wrap=2, straps=True, tie=True, seed=seed)
    elif garb == 'robe':                                 # 학자 가운(발목까지)
        g.robe(s, cloth, y0=0, seed=seed, hem_row=11, sleeve_to=10, lining=under)
        # 가운 하나만 입히면 전신이 한 색이다 — 어깨에 한 단 짙은 숄을 얹어 무게를 준다
        g.mantle(s, R('leather_d'), front=3, back=8, seed=seed, lining=under)
        g.belt(s, R('leather'), y=8, layer='outer')
    elif garb == 'kirtle':
        # ★robe()를 그대로 부르고 있었다(2026-08-05 지적 "복장자체가 여자같지 않음") —
        #   순례자·현자가 쓰는 그 함수라 남성 로브와 실루엣이 같았다. kirtle()은
        #   네크라인·보디스 끈·허리 조임·치마 음영을 얹어 여성 재단으로 가른다.
        # ★길이 변주 (2026-08-05 지적 "옷이 다 무조건 소매까지만 온다"):
        #   sleeve = 소매 끝 행(0 민소매 / 2 캡 / 5 팔꿈치 / 7 칠부 / 9 손목)
        #   hem    = 치마 끝 행(8 종아리 / 10 발목 / 11 바닥)
        #   bare   = 소매 아래를 맨팔로(안 주면 속옷이 드러나 '긴 속옷 입은 사람'이 된다)
        #   off    = 오프숄더
        _sleeve = v.get('sleeve', v.get('roll', 9))
        _hem = v.get('hem', 11)
        g.kirtle(s, cloth, under, y0=0, seed=seed, hem_row=_hem,
                 sleeve_to=_sleeve,
                 neckline=v.get('neckline', 'square'),
                 waist=v.get('waist', 7), lace=v.get('lace', True))
        if v.get('bare') and _sleeve < 9:
            g.bare_arms(s, skin, _sleeve + 1, 11)
        if v.get('off'):
            g.off_shoulder(s, cloth, under, y0=0, drop=v.get('offdrop', 2), skin_r=skin)
        if v.get('apron'):
            g.apron(s, R(v['extra']), bib=(2, 5), bib_y=(2, 6), waist=7, hem=11,
                    wrap=0, straps=True, tie=True, seed=seed)
            fa = s.f('body', 'front', 'outer')
            for x in (0, 7):                             # 양옆을 비워 커틀이 흐르게
                fa.rect(x, 7, x, 11, (0, 0, 0, 0), 0)
        elif v.get('belt', True):
            # ★belt=False면 벨트를 안 채운다 — 가슴부터 발목까지 <b>한 덩어리로 흐르는
            #   드레스</b>가 된다. 레퍼런스의 허리 밴드는 33%인데 우리는 80%였고,
            #   벨트로 허리를 끊으면 남성 튜닉과 실루엣이 비슷해진다.
            g.belt(s, R('leather'), y=7, layer='outer')

    # ★치마 구조 — 하의를 다 그린 뒤. 색은 이미 17종으로 갈렸는데도 치마 동일률이
    #   3.4%(얼굴 다음)였던 원인은 <b>레시피가 하나뿐</b>이었다는 것이다:
    #   33명 전원이 '균일 그라데이션 + 접힘선 1개'. 4x12 두 짝이면 구조를 넣을 자리가 있다.
    if v.get('skirt'):
        g.skirt_style(s, R(v['legs']) if v.get('legs') else cloth,
                      style=v['skirt'], hem=v.get('hem', 11), y0=v.get('skirty0', 2),
                      accent=R(v['skirtc']) if v.get('skirtc') else None, seed=seed)



def extra_cut(s, v, seed):
    """이미 garments.py에 있었지만 마을 파일이 한 번도 안 쓰던 재단을 얹는다.

    조끼·멜빵·새시·장갑 — 실루엣을 한 겹 더 만들어 '같은 튜닉에 색만 다른 사람들'을
    갈라 놓는다. 무늬(표면)보다 이쪽이 훨씬 크게 읽힌다.
    """
    k = v.get('layer2')
    if not k:
        return
    r = R(v.get('l2c', 'leather'))
    if k == 'vest':
        g.vest(s, r, y0=0, hem=9, gap=2, layer='outer', seed=seed)
    elif k == 'suspenders':
        g.suspenders(s, r, cols=(1, 6), waist=7, layer='outer')
    elif k == 'sash':
        g.sash(s, r, y=5, drop=2, layer='outer')
    elif k == 'gloves':
        g.gloves(s, r, rows=3, layer='outer')
    elif k == 'tabard':
        g.tabard(s, r, y0=0, hem=10, panel=(2, 5), layer='outer', seed=seed)


def props(s, v, seed):
    f = s.f('body', 'front', 'outer')
    p = v.get('prop')
    if p == 'sack':                                      # 어깨에 진 자루
        g.bandolier(s, R('canvas'), front_x=2, layer='outer')
        bk = s.f('body', 'back', 'outer')
        bk.rect(1, 1, 6, 8, R('sand')[3])
        bk.row(1, R('sand')[4], 1, 6); bk.row(8, R('sand')[1], 1, 6)
        s.speckle('body', R('sand'), 1, 8, layer='outer', density=0.12, seed=seed,
                  faces=('back',))
    elif p == 'net':                                     # 어깨에 건 그물
        for x, y in ((1, 2), (2, 3), (1, 4), (2, 5), (1, 6)):
            f.px(x, y, R('oat')[4]); f.px(x + 1, y, R('oat')[1])
        s.f('body', 'top', 'outer').rect(1, 0, 2, 3, R('oat')[2])
        bk = s.f('body', 'back', 'outer')
        for y in range(1, 9, 2):
            bk.row(y, R('oat')[2], 1, 4)
    elif p == 'ledger':
        f.rect(6, 5, 7, 9, R('linen')[1]); f.col(6, R('linen')[3], 5, 9)
        f.row(9, R('leather_d')[1], 6, 7)
    elif p == 'lantern':                                 # 허리에 매단 등불
        f.rect(6, 8, 7, 10, R('iron')[2])
        f.px(6, 9, ramp('c9a24a')[4]); f.px(7, 9, ramp('c9a24a')[3])
        f.px(6, 7, R('iron')[3])
    elif p == 'tools':                                   # 앞치마 주머니의 연장
        f.px(2, 8, R('iron')[4]); f.px(2, 9, R('leather_d')[2])
        f.px(5, 8, R('leather')[4]); f.px(5, 9, R('leather')[2]); f.px(5, 10, R('leather')[1])
    elif p == 'basket':
        f.rect(5, 8, 7, 11, R('sand')[2])
        f.row(8, R('sand')[4], 5, 7)
        for x in (5, 7):
            f.col(x, R('sand')[1], 8, 11)
    elif p == 'pouch':
        g.pouch(s, R('leather'), part='leg_r', face='front', x=1, y=2, w=2, h=3)
    elif p == 'scales':                                  # 앞치마에 붙은 생선 비늘
        for x, y in ((3, 4), (2, 9), (5, 8)):
            f.px(x, y, R('iron')[4]); f.px(min(7, x + 1), y, R('iron')[2])
    elif p == 'book':                                    # 겨드랑이에 낀 책
        f.rect(6, 5, 7, 9, R('leather')[2])
        f.col(6, R('leather')[4], 5, 9)
        f.px(7, 6, R('linen')[4]); f.px(7, 7, R('linen')[3])
        f.row(9, R('leather_d')[1], 6, 7)
    elif p == 'yarn':                                    # 허리에 매단 실타래
        for i, key in enumerate(('rust', 'moss', 'mustard')):
            f.px(6, 7 + i, R(key)[4]); f.px(7, 7 + i, R(key)[2])
        f.px(6, 6, R('leather')[2])
    elif p == 'quiver':                                  # 등에 멘 화살통
        bk = s.f('body', 'back', 'outer')
        bk.rect(4, 1, 6, 8, R('leather_d')[3])
        bk.col(4, R('leather_d')[4], 1, 8)
        for x in (4, 5, 6):                              # 삐져나온 화살깃
            bk.px(x, 0, R('oat')[4] if x % 2 else R('oat')[2])
        g.bandolier(s, R('leather'), front_x=5, layer='outer')
    elif p == 'rope':                                    # 어깨에 감은 밧줄
        for y in (2, 4, 6):
            f.px(1, y, R('oat')[4]); f.px(2, y, R('oat')[2])
        s.f('body', 'top', 'outer').rect(1, 0, 2, 3, R('oat')[3])
        bk = s.f('body', 'back', 'outer')
        for y in (2, 4, 6):
            bk.px(5, y, R('oat')[3]); bk.px(6, y, R('oat')[1])
    elif p == 'satchel':                                 # 어깨 가방(전령)
        g.bandolier(s, R('leather'), front_x=2, layer='outer')
        f.rect(5, 8, 7, 11, R('leather')[3])
        f.row(8, R('leather')[4], 5, 7)
        f.row(11, R('leather_d')[1], 5, 7)
        f.px(6, 9, R('linen')[4])                        # 삐져나온 서찰
    elif p == 'ladle':                                   # 허리에 꽂은 국자
        f.px(6, 6, R('oat')[4]); f.px(6, 7, R('oat')[3]); f.px(6, 8, R('oat')[2])
        f.rect(6, 9, 7, 10, R('iron')[3]); f.px(7, 10, R('iron')[1])
    elif p == 'herbs':                                   # 허리에 매단 약초 다발 + 붕대
        for i, key in enumerate(('moss', 'mustard', 'moss')):
            f.px(6, 6 + i, R(key)[4]); f.px(7, 6 + i, R(key)[2])
        f.px(6, 9, R('leather')[2]); f.px(7, 9, R('leather')[1])
        for part in ('arm_r',):                          # 한쪽 손목에만 감은 붕대
            s.band(part, 9, 9, R('linen')[4], layer='outer')
            s.band(part, 10, 10, R('linen')[2], layer='outer')
    elif p == 'tankard':                                 # 허리에 건 술잔(여관)
        f.rect(6, 8, 7, 10, R('iron')[2])
        f.px(6, 8, R('iron')[4]); f.px(7, 9, R('iron')[4])
        f.px(6, 7, R('leather')[2])
    elif p == 'shawl':                                   # 어깨 숄(가수)
        sh = R(v['shawl'])
        s.f('body', 'top', 'outer').rect(0, 0, 7, 2, sh[3])
        for fn in ('front', 'back'):
            s.f('body', fn, 'outer').rect(0, 0, 7, 1, sh[3])
            s.f('body', fn, 'outer').row(1, sh[1])
        for fn in ('right', 'left'):
            s.f('body', fn, 'outer').rect(0, 0, 3, 3, sh[2])
        f.rect(6, 2, 6, 5, sh[2]); f.px(6, 5, sh[1])     # 한쪽으로 흘러내린 자락

    if v.get('patch'):
        g.patch(s, v['patch'], 'front', R('canvas'), x=1, y=5, w=2, h=2, layer='outer')
    if v.get('dust'):                                    # 밀가루가 앉은 어깨·팔
        for part, y0, y1 in (('body', 0, 3), ('arm_r', 0, 3), ('arm_l', 0, 3)):
            s.speckle(part, R('flour'), y0, y1, layer='outer', density=0.30,
                      seed=v['cid'], strength=0.7)
        fh = s.f('head', 'front')
        for x, y in ((1, 5), (6, 5)):
            fh.px(x, y, mix(fh.get(x, y), R('flour')[4], 0.45))


def surface(s, v, seed):
    """옷 위의 무늬·재봉 디테일 (2026-08-03 신설).

    왜: 색을 고친 뒤에도 "옷 무늬가 다 비슷하다"는 지적을 받았다. 실측해 보니 무늬가
    비슷한 게 아니라 ★아예 없었다 — garments.py 함수 40개가 전부 옷의 '형태'였고
    표면 어휘(stripe/check/panel/trim/quilt/button/lacing/seam) 사용 횟수는 0.
    모든 옷이 단색 면 + 그레인 노이즈 + 같은 자리 주름 두 줄이었다.

    ★가로 줄무늬는 금지(2026-08-03 오너 지시) — 현대 스포츠 셔츠로 읽힌다.
    garments.stripes가 axis='h'를 예외로 막는다.

    규칙: 한 사람당 최대 2개, 배역에 명분이 있을 때만 — 직조공은 자기가 짠 격자천,
    짐꾼·아이는 기운 조각천, 뱃사람은 가로줄, 관리·상단은 앞섶 패널과 단추,
    앞치마 직군은 주머니.
    """
    kinds = v.get('surface')
    if not kinds:
        return
    if isinstance(kinds, str):
        kinds = (kinds,)
    r2 = R(v.get('surfc', 'linen'))
    L = 'outer'
    roll = v.get('roll', 8)
    for k in kinds:
        if k == 'stripe_v':
            g.stripes(s, 'body', r2, axis='v', period=4, y0=0, y1=10, layer=L,
                      offset=seed % 3)
        elif k == 'check':
            g.check(s, 'body', r2, period=2, y0=0, y1=10, layer=L)
        elif k == 'placket':
            g.placket(s, r2, x=(3, 4), y0=0, y1=9, layer=L)
        elif k == 'buttons':
            g.buttons(s, r2, x=4, ys=(2, 4, 6), layer=L)
        elif k == 'trim':
            g.trim(s, r2, rows=(0,), layer=L)
            for part in ('arm_r', 'arm_l'):
                g.trim(s, r2, part=part, rows=(roll,), layer=L)
        elif k == 'quilt':
            g.quilt(s, 'body', r2, y0=1, y1=9, layer=L)
        elif k == 'lacing':
            g.lacing(s, r2, x=(3, 4), y0=1, y1=6, layer=L)
        elif k == 'seams':
            g.seams(s, 'body', r2, y0=0, y1=10, layer=L)
        elif k == 'patchwork':
            g.patchwork(s, 'body', r2, n=2, seed=seed, y0=2, y1=10, layer=L)
        elif k == 'pocket':
            g.pocket(s, r2, x=(1, 3), y=(7, 9), layer=L)


def feminize(s, v, seed):
    """여성 NPC 실루엣·얼굴 패스. 남성/아이에겐 아무 일도 하지 않는다.

    ★2026-08-05 오너 지적("근본적인 원인 중 하나가 여자스킨이 없어")에 대한 처방.
      그때까지 female=True가 하던 일은 뒷머리 1행 + 가르마 + 속눈썹 2px + 입술색뿐이라
      여성 31명이 남성 몸에 치마만 입은 꼴이었다. 지오메트리가 남녀 동일한 모델에서
      성별은 '칠해서' 만들어야 하고, 그 패스가 여기다.
    ★옆머리(locks) 게이팅 — 1차에 "머리에 아무것도 안 쓴 사람만"으로 잡았더니 여성 13명 중
      12명이 제외됐다(7명 두건·5명 braid). 옆머리는 이 해상도에서 성별을 만드는 가장 강한
      신호라 그렇게 좁히면 처방 자체가 무효다. 지금은 <b>머리가 실제로 안 보이는 경우만</b> 끈다:
        None/kerchief/cap → 옆머리 O (두건·모자는 천 아래 3행부터 시작해 위로 안 뜨게)
        hood/coif         → 옆머리 X (머리를 통째로 감싼다)
      braid는 배제 사유가 아니다 — 뒤로 묶은 머리와 얼굴 옆 머리는 실제로 공존한다.
    ★아이(child)는 제외 — 체형 성별 신호를 아이에게 넣지 않는다.
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
    _drop = max(5, min(9, v.get('backhair', 7) - 1))
    # ★머리 «볼륨»(정수리·옆·뒤)만 이쪽에서. 앞머리·흘러내림은 스타일 함수가 그린다.
    g.female_hair_length(s, hair_ramp(v['hair']), seed=seed, drop=_drop,
                         head_volume=(v.get('head') is None and not v.get('visor')),
                         shoulders=False, front=False)
    # 스타일 6종 — 하이픽셀 여성 10명 분류에서 뽑았다(garments.female_hair_style 주석 참고).
    #   머리쓰개로 앞이 막힌 사람(hood/coif/veil)은 스타일을 그리지 않는다.
    if v.get('head') not in ('hood', 'coif', 'veil'):
        g.female_hair_style(s, hair_ramp(v['hair']), style=v.get('hstyle', 'straight'),
                            drop=_drop, seed=seed)
    adorn(s, v, seed)


def adorn(s, v, seed):
    """장신구·네크라인 패스 (2026-08-07 신설). ★반드시 feminize의 머리 다음에 온다.

    순서가 의미를 갖는다:
      decollete  → 옷을 파서 <b>살</b>을 낸다. necklace가 걸릴 자리를 먼저 만든다.
      necklace   → 파낸 살 위에 얹는다. 먼저 그리면 옷에 덮인다.
      earrings   → 옆머리 <b>위에</b> 얹는다. female_hair_length보다 뒤여야 보인다.
      hair_ornament → 두건을 뺀 자리를 메운다. 머리를 안 가려서 길이 신호를 안 죽인다.

    ★레퍼런스 60장 대비 우리의 최대 격차가 네크라인(65% vs 12.5%)이었다.
      kirtle이 가슴을 <b>속옷색</b>으로 채우고 있어서 '천 한 겹 더'로 읽힌 게 원인이다.
    """
    if not v.get('female') or v.get('child'):
        return
    # 베일·후드는 목까지 감싸므로 네크라인·목걸이가 성립하지 않는다
    covered = v.get('head') in ('hood', 'coif', 'veil') or v.get('garb') == 'veil_robe'
    # ★앞으로 넘긴 땋은 머리 — female_hair_length 다음, 장신구 앞.
    #   feminize에 두면 dealers·desertfolk가 빠진다(자체 feminize를 갖고 있다,
    #   lessons 10장). adorn은 7개 모듈 전부에 배선돼 있으므로 여기가 맞다.
    #   ponytail()은 뒤로 가서 인게임에서 볼 일이 없다(lookclose).
    if v.get('fbraid'):
        g.braid_front(s, hair_ramp(v['hair']), side=v.get('fbraidside'),
                      drop=v.get('fbraiddrop', 6), seed=seed,
                      tie=R(v['fbraidtie']) if v.get('fbraidtie') else None)
    # ★피부는 팔레트 키가 아니라 hex다 — R()이 아니라 ramp()를 쓴다
    if v.get('neck') and not covered:
        g.decollete(s, ramp(v['skin']), style=v['neck'])
    if v.get('jewel') and not covered:
        g.necklace(s, R(v.get('jewelc', 'brass')), style=v['jewel'])
    if v.get('earring'):
        # ★eye_y를 넘긴다 — 안 넘기면 눈 옆에 찍혀 상처처럼 보인다(실측 6명)
        g.earrings(s, R(v.get('jewelc', 'brass')), eye_y=v.get('eye_y', 4))
    if v.get('hairpin'):
        g.hair_ornament(s, R(v.get('hairpinc', 'madder')), kind=v['hairpin'], seed=seed)
    if v.get('bangle') and v.get('bare'):
        g.bracelet(s, R(v.get('jewelc', 'brass')))


def build(v):
    s = Skin()
    v = restyle(v)   # ★여성 개정표(두건축소·네크라인·장신구) — head()보다 먼저여야 한다
    seed = v['cid']
    head(s, v, seed)
    body(s, v, seed)
    extra_cut(s, v, seed)   # ★조끼·멜빵·새시 — 무늬보다 실루엣이 먼저 읽힌다
    surface(s, v, seed)     # ★무늬는 옷 다음, 소품 앞 — 소품 위에 줄무늬가 얹히면 안 된다
    # ★키 이름이 'shawl'이면 안 된다 — 이미 prop='shawl'(담요 숄 소품)의 색 지정용으로
    #   쓰이고 있어서 도메니코(남성)·프리다에게 원치 않는 어깨 숄이 얹혔다(실측 회귀).
    if v.get('wrapshawl'):  # 노인 여성의 어깨 숄 — 옷·무늬 다음에 얹는다
        g.shawl(s, R(v['wrapshawl']), y0=0, drop=v.get('shawldrop', 4), seed=seed)
    feminize(s, v, seed)    # ★여성 실루엣 — 반드시 옷·무늬 다음(옷이 덮으면 무효), 소품 앞
    props(s, v, seed)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / f"tf_{v['file']}.png"))




# ─────────────────────────────────────────────────────────────────────────────
# 여성 개정표 (2026-08-07) — 두건 축소 + 네크라인 + 장신구
#
# 왜 표를 따로 두나: 스펙 dict 리터럴 20개를 정규식으로 고치는 건 사고가 난다.
# 개정 내용만 한 곳에 모아 build() 진입점에서 병합하면 <b>무엇을 왜 바꿨는지</b>가
# 한눈에 보이고, 되돌리기도 이 표만 지우면 된다.
#
# 근거(레퍼런스 60장 실측 대비):
#   머리쓰개  30.0% vs 우리 70.0%  → 20명 → 10명 (베일4·후드1·모자1 유지 + 두건 4명만)
#   네크라인  65.0% vs 우리 12.5%  → 가려진 6명 빼고 전원에 부여  ★최대 격차
#
# ★두건을 뺀 자리는 hairpin(꽃·리본·핀)으로 메운다. 두건과 달리 머리카락을 안 가려서
#   길이 신호를 죽이지 않고, 유저 요청("여성들이 흔히 하는 치장")에도 정확히 맞는다.
# ★역할상 머리를 싸매야 하는 사람만 두건을 남긴다 — 주방 3명(베티나·지오반나·취사)과
#   생선 손질(미아). 빵집·직조·장사꾼은 위생 근거가 없어 뺀다.
# ★장신구 색은 옷 색과 겹치면 묻힌다. 금속(silver/brass/copper/iron)과 보석
#   (amber/coral/pearl/jet)에서 골라 <b>주변보다 확실히 밝거나 어둡게</b> 간다.
FEM_RESTYLE = {
    # ── 스폰 마을 ────────────────────────────────────────────────────────────
    'gretchen':  dict(head=None, hairpin='ribbon', hairpinc='chalk',
                      neck='square', jewel='beads', jewelc='copper'),
    'mia':       dict(neck=None, earring=True, jewelc='iron'),          # 두건 유지(생선 손질)
    'bettina':   dict(neck='scoop', earring=True, jewelc='brass'),      # 두건 유지(주방)
    'brigitte':  dict(head=None, hairpin='pin', hairpinc='woad',
                      neck='scoop', jewel='beads', jewelc='amber'),
    'astrid':    dict(head=None, hairpin='ribbon', hairpinc='wine',
                      neck='square', jewel='pendant', jewelc='silver'),
    'helga':     dict(head=None, hairpin='pin', hairpinc='verdigris',
                      neck='scoop', jewel='beads', jewelc='coral'),
    'greta':     dict(head=None, hairpin='pin', hairpinc='teal',
                      neck='scoop', jewel='beads', jewelc='iron'),
    # 항구 가수 — 마을에서 가장 치장이 많아도 되는 배역. 초커+귀걸이+꽃
    'frieda':    dict(neck='v', jewel='choker', jewelc='jet', earring=True,
                      hairpin='flower', hairpinc='madder'),
    'inga':      dict(neck='scoop', jewel='beads', jewelc='copper', hairpin='ribbon',
                      hairpinc='woad'),
    'ingrid':    dict(neck='square', jewel='pendant', jewelc='brass', earring=True),
    'marie':     dict(neck='scoop', jewel='pendant', jewelc='iron'),
    'marta':     dict(neck='square', jewel='beads', jewelc='amber',
                      hairpin='flower', hairpinc='coral'),
    # ── 상단 마을 ────────────────────────────────────────────────────────────
    'claudia':   dict(head=None, neck='v', jewel='pendant', jewelc='amber',
                      earring=True, hairpin='pin', hairpinc='madder'),
    'giovanna':  dict(neck='scoop', earring=True, jewelc='copper'),     # 두건 유지(주방)
    'giulia':    dict(neck='square', jewel='pendant', jewelc='silver'),
    'rosa':      dict(head=None, neck='scoop', jewel='beads', jewelc='pearl',
                      hairpin='pin', hairpinc='verdigris'),
    'silvia':    dict(neck='scoop', jewel='beads', jewelc='copper', earring=True),
    'teresa':    dict(head=None, neck='square', jewel='pendant', jewelc='copper',
                      hairpin='ribbon', hairpinc='moss'),
    # ── 배·기타 ──────────────────────────────────────────────────────────────
    'isabella':  dict(jewel='pendant', jewelc='silver', earring=True),  # 선장모 유지
    'rosa_garden': dict(head=None, hairpin='flower', hairpinc='coral',
                        neck='scoop', jewel='beads', jewelc='verdigris'),
    'tavernkeep': dict(head=None, hairpin='ribbon', hairpinc='madder',
                       neck='square', jewel='beads', jewelc='brass'),
    'ci_cook':   dict(neck='scoop', earring=True, jewelc='brass'),      # 두건 유지(배 취사)
    # ── 카지노 딜러 ──────────────────────────────────────────────────────────
    # ★검정 정장 위에서는 색으로 성별을 못 낸다(2026-08-05 실패: 검정 리본이 안 보였다).
    #   해법은 <b>명도 대비</b> — 은/진주 목걸이는 검정 위에서 확실히 읽힌다.
    'd_blackjack2': dict(neck='v', jewel='pendant', jewelc='silver', earring=True),
    'd_holdem2':    dict(neck='v', jewel='choker', jewelc='pearl', earring=True),
    'd_slot2':      dict(neck='v', jewel='pendant', jewelc='pearl', earring=True),
    'd_threecard2': dict(neck='v', jewel='choker', jewelc='silver', earring=True),
    # ── 랭킹 ────────────────────────────────────────────────────────────────
    'r_marcello': dict(neck='square', jewel='pendant', jewelc='brass', earring=True),
    # ── 사막(베일)·밀정(후드) ────────────────────────────────────────────────
    # 베일·후드는 목까지 감싸므로 네크라인·목걸이가 성립하지 않는다. 개정 없음.
    #   amira · fatima · nadia · nur · leila
    # ── 아이 ────────────────────────────────────────────────────────────────
    #   rina — child. 체형·장신구 처방을 아이에게 넣지 않는다.
}


def restyle(v):
    """FEM_RESTYLE을 스펙에 병합한 <b>사본</b>을 준다. 원본 dict는 안 건드린다.

    ★build() 맨 앞에서 불러야 한다 — head()가 v['head']를 읽기 <b>전</b>이어야
      두건 제거가 반영된다. adorn()에서 처리하면 이미 두건이 그려진 뒤다.
    """
    f = v.get('file')
    parts = (FEM_RESTYLE.get(f), FEM_HAIR.get(f), FEM_SKIRT.get(f))
    if not any(parts):
        return v
    out = dict(v)
    for pt in parts:
        out.update(pt or {})
    return out


# 머리 <b>모양</b> 축 (2026-08-07) — FEM_RESTYLE과 함께 restyle()에서 합쳐진다.
#
# 왜: 색은 이미 15종으로 갈라놨는데 <b>모양이 33명 전원 같았다</b>(fringe=3 · part=3).
# 얼굴 8x8 픽셀 동일률이 4.8%로 몸통 다음으로 닮은 부위였던 실제 원인이 이것이다.
# 앞머리 5종 × 가르마 위치 × 앞으로 넘긴 땋은머리로 얼굴 인상을 가른다.
#
# ★배분 원칙: 같은 마을 <b>이웃끼리 같은 fstyle을 주지 않는다</b>. 스킨은 혼자 볼 때가
#   아니라 옆에 나란히 섰을 때 닮아 보이는 게 문제다.
# ★사막(베일 4명)·밀정 레일라(후드)는 앞머리가 천에 가려 의미가 없어 제외했다.
# ★리나(아이)는 앞머리만 준다 — fbraid는 adorn 안에 있고 adorn은 child를 건너뛴다.
# ★fstyle은 <b>blunt / curtain / swept</b> 셋뿐이다.
#   pulled(올백)과 wispy(숱 적음)는 <b>폐기</b>했다 — 8px 얼굴에서 이마는 4행뿐이라
#   앞머리를 걷거나 성기게 만들면 예외 없이 '탈모·듬성한 헤어라인'으로 읽힌다.
#   세 번 고쳐보고 내린 결론이다(합성 얼굴 실측). 자세한 경위는 garments.fringe_style 주석.
FEM_HAIR = {
    # ── 스폰 마을 ────────────────────────────────────────────────────────────
    'gretchen':    dict(fstyle='blunt',   part=2),
    'mia':         dict(fstyle='blunt',   part=5),
    'bettina':     dict(fstyle='curtain', part=4, fbraid=True, fbraidside='r', fbraiddrop=5),
    'brigitte':    dict(fstyle='swept',   part=1),
    'astrid':      dict(fstyle='curtain', part=6),
    'helga':       dict(fstyle='curtain', part=3),
    'greta':       dict(fstyle='blunt',   part=5),
    'frieda':      dict(fstyle='swept',   part=6, fbraid=True, fbraidside='l',
                        fbraiddrop=7, fbraidtie='madder'),      # 가수 — 가장 화려해도 되는 배역
    'inga':        dict(fstyle='swept',   part=2),
    'ingrid':      dict(fstyle='blunt',   part=4),              # 접수 — 단정한 일자
    'marie':       dict(fstyle='blunt',   part=4, fbraid=True, fbraidside='r', fbraiddrop=5),
    'marta':       dict(fstyle='curtain', part=2),
    'rina':        dict(fstyle='blunt',   part=5),              # 아이 — 앞머리만
    # ── 상단 마을 ────────────────────────────────────────────────────────────
    'claudia':     dict(fstyle='swept',   part=1, fbraid=True, fbraidside='l', fbraiddrop=6),
    'giovanna':    dict(fstyle='blunt',   part=4),
    'giulia':      dict(fstyle='blunt',   part=6),              # 회계 — 단정한 일자
    'rosa':        dict(fstyle='blunt',   part=2),
    'silvia':      dict(fstyle='curtain', part=5, fbraid=True, fbraidside='r', fbraiddrop=6),
    'teresa':      dict(fstyle='curtain', part=3),              # 20년차
    # ── 배·기타 ──────────────────────────────────────────────────────────────
    'isabella':    dict(fstyle='swept',   part=2),              # 선장 (모자라 앞머리는 안 보임)
    'rosa_garden': dict(fstyle='curtain', part=6, fbraid=True, fbraidside='l', fbraiddrop=5),
    'tavernkeep':  dict(fstyle='blunt',   part=3),
    'ci_cook':     dict(fstyle='blunt',   part=4),
    # ── 카지노 딜러 ──────────────────────────────────────────────────────────
    # 제복이라 단정한 쪽으로 몰되, 넷이 한 테이블에 서므로 서로는 반드시 달라야 한다
    'd_blackjack2': dict(fstyle='curtain', part=1),
    'd_holdem2':    dict(fstyle='blunt',   part=3),
    'd_slot2':      dict(fstyle='curtain', part=4),
    'd_threecard2': dict(fstyle='swept',   part=2, fbraid=True, fbraidside='r', fbraiddrop=5),
    # ── 랭킹 ────────────────────────────────────────────────────────────────
    'r_marcello':   dict(fstyle='swept',   part=5),
}


# 치마 <b>구조</b> + 벨트 (2026-08-07) — restyle()에서 함께 합쳐진다.
#
# 왜: 실제로 보이는 면 기준 부위별 동일률에서 <b>치마가 3.4%로 얼굴 다음</b>이었다.
# (앞서 "몸통 11.8%"라고 봤던 건 base 레이어만 잰 잘못된 값이었다 — outer 합성으로
#  다시 재니 몸통은 2.3%로 3위였고 치마가 더 닮아 있었다.)
# 색은 이미 17종으로 갈렸다. 문제는 <b>레시피가 하나</b>였다는 것 — 전원이
# '균일 그라데이션 + 접힘선 1개'였다.
#
# ★belt=False는 '가슴~발목 한 덩어리로 흐르는 드레스'를 만든다. 레퍼런스 허리 밴드는
#   33%인데 우리는 80%였다. 앞치마를 두른 사람은 어차피 허리끈이 있으니 제외.
# ★역할과 맞춰 고른다: 격식(pleats) · 장식(banded/panel) · 노동(patched) · 서민(tiered)
# ★pleats(세로 주름)는 폐기했다 — 다리 두 짝에 세로 줄이 반복되면 예외 없이
#   '줄무늬 바지'로 읽힌다(오너 지적). 구조는 가로(banded·tiered)이거나
#   중앙 하나(panel)여야 치마로 보인다.
FEM_SKIRT = {
    # ── 스폰 마을 ────────────────────────────────────────────────────────────
    'gretchen':    dict(skirt='banded',  skirtc='chalk'),
    'mia':         dict(skirt='patched'),
    'bettina':     dict(skirt='tiered'),
    'brigitte':    dict(skirt='panel',   skirtc='oat',    belt=False),
    'astrid':      dict(skirt='tiered',  belt=False),
    'helga':       dict(skirt='patched'),
    'greta':       dict(skirt='tiered'),
    'frieda':      dict(skirt='panel',   skirtc='chalk',  belt=False),   # 가수 — 가장 화려
    'inga':        dict(skirt='banded',  skirtc='canvas'),
    'ingrid':      dict(skirt='banded',  skirtc='iron',   belt=False),   # 접수 — 격식
    'marie':       dict(skirt='tiered'),
    'marta':       dict(skirt='banded',  skirtc='linen'),
    'rina':        dict(skirt='patched'),                                # 아이 — 기운 옷
    # ── 상단 마을 ────────────────────────────────────────────────────────────
    'claudia':     dict(skirt='panel',   skirtc='amber',  belt=False),
    'giovanna':    dict(skirt='tiered'),
    'giulia':      dict(skirt='banded',  skirtc='silver', belt=False),   # 회계 — 격식
    'rosa':        dict(skirt='patched'),
    'silvia':      dict(skirt='banded',  skirtc='pearl'),
    'teresa':      dict(skirt='panel',   skirtc='copper', belt=False),
    # ── 배·기타 ──────────────────────────────────────────────────────────────
    'rosa_garden': dict(skirt='patched'),
    'tavernkeep':  dict(skirt='banded',  skirtc='brass'),
    'ci_cook':     dict(skirt='tiered'),
    # ── 사막(veil_robe) — 로브가 발목까지 한 덩어리라 이미 벨트가 없다 ──────────
    # ★사막 4명은 desertfolk의 팔레트를 쓴다(chalk·pearl 등 스폰마을 키는 KeyError)
    'amira':       dict(skirt='banded',  skirtc='ecru'),
    'fatima':      dict(skirt='tiered'),
    'nadia':       dict(skirt='panel',   skirtc='brass'),
    'nur':         dict(skirt='banded',  skirtc='linen'),
    # ── 밀정 ────────────────────────────────────────────────────────────────
    'leila':       dict(skirt='tiered'),
    # ── 카지노 딜러·랭킹은 정장 바지/코트라 치마 구조가 성립하지 않는다 ─────────
}


if __name__ == '__main__':
    for k in sys.argv[1:] or VARIANTS:
        print(build(VARIANTS[k]))
