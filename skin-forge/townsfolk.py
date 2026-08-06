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
from skinlib import Skin, mix, ramp       # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'

# ── 마을 공용 색. 개인은 여기서 골라 쓰고, 새 색을 함부로 들이지 않는다 ──────────
C = dict(
    teal='4f6f6a', teal_d='39544f', slate='55606b', navy='3c4756',
    oat='a89880', linen='b0a793', canvas='6f6a5c', sand='8d7f66',
    leather='6b4f36', leather_d='45362a', boot='3f342a', boot_d='352c24',
    rust='8a5340', wine='6e3a3a', moss='5c6b4a', olive='4f5548',
    grey='6b665e', charcoal='413c36', flour='b6b0a2', mustard='9a8446',
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
    weld='b8912e',        # 웰드 노랑
    verdigris='2a6b5e',   # 녹청
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
                spread=sp)


# ── 변주 표 ────────────────────────────────────────────────────────────────
# garb: tunic(짧은 튜닉) / jerkin(가죽 조끼) / apron(앞치마 직군) / coat(롱코트)
#       / kirtle(여성 원피스) / robe(학자 가운)
# head: None / cap / kerchief / hood / coif
# prop: None / sack / net / ledger / lantern / tools / basket / yarn / pouch / book
VARIANTS = {
    # ── 항구 노동자 ──────────────────────────────────────────────────────
    '134': dict(file='ralf', cid=134, label='랄프 — 항구 짐꾼',
                # "짐이 무거워도 이 일이 좋아" → 등짐꾼. 소매 없는 튜닉 + 어깨 짐받이
                skin=SKIN['deep'], hair='4a3a2a', beard='stubble',
                garb='jerkin', cloth='leather', under='oat', legs='canvas', boot='boot',
                head=None, prop='sack', roll=2, patch='leg_r',
                surface=('patchwork', 'seams'), surfc='canvas',
                layer2='suspenders', l2c='canvas',
                eye_y=5, iris='dark', jaw='square', brow_w=2, mouth_w=3, marks='scar', bootrows=6),
    '133': dict(file='feder', cid=133, label='페더 — 그물 손질',
                # "그물 손질은 손끝 감각이 전부지" → 어망 수선공. 그물을 어깨에 건다
                skin=SKIN['olive'], hair='6b6154', beard='full', age=True,
                cloth='teal', under='oat', legs='grey', boot='boot',
                head='cap', headc='teal_d', prop='net', roll=3,
                surface='seams', surfc='oat',
                garb='wrap', cross=5,
                eye_y=4, iris='grey', jaw='long', fringe=1, marks='ruddy', bootrows=3),
    '106': dict(file='dirk', cid=106, label='디르크 — 부두 관리',
                # "부두 관리가 제 일입니다" → 관리자. 마을에서 가장 갖춰 입은 축
                # ★도란73(상단)과 코트+캡+염소수염이 겹쳐 사실상 쌍둥이였다(픽셀차 9.2).
                #   대청 파랑 관복 + 흑발로 갈라 놓는다(도란은 녹청).
                skin='b58f6a', hair='241f1c', beard='goatee',
                garb='coat', cloth='woad', under='linen', legs='ink', boot='boot_d',
                head='cap', headc='woad', prop='ledger', accent='brass',
                surface=('placket', 'buttons'), surfc='brass',
                eye_y=3, iris='hazel', jaw='narrow', brow_a=1, mouth_y=6, bootrows=5),
    '139': dict(file='walter', cid=139, label='발터 — 야경꾼',
                # "밤에도 누군가는 항구를 지켜야지" → 후드 망토 + 등불
                # ★마을의 '가장 어두운 사람' 자리 — 야경꾼이라 명분도 맞는다
                skin='b0855e', hair='4f4a42', beard='full', age=True,
                garb='coat', cloth='pitch', under='canvas', legs='soot',
                boot='boot_d', head='hood', headc='pitch', prop='lantern',
                accent='iron',
                surface='seams', surfc='iron',
                folds=(1, 5),
                eye_y=4, iris='amber', jaw='square', brow_w=2, socket=True, marks='sunken'),
    '104': dict(file='wolfgang', cid=104, label='볼프강 — 목수',
                # "이 마을 목재는 다 내 손을 거쳐 갔지" → 톱밥 앞치마 + 연장
                skin='b57f52', hair='5a4636', beard='mutton',
                garb='apron', cloth='oat', under='oat', extra='leather',
                legs='canvas', boot='boot', head=None, prop='tools', roll=4,
                surface='pocket', surfc='canvas',
                layer2='suspenders', l2c='leather_d',
                eye_y=5, iris='brown', jaw='square', mouth_w=3, marks='freckles', bootrows=3),
    '107': dict(file='helmut', cid=107, label='헬무트 — 방앗간',
                # "밀가루 먼지 마실 날이 없어요" → 온몸에 하얀 가루. 자루를 진다
                # ★마을의 '가장 밝은 사람' 자리 — 밀가루를 뒤집어쓰는 직업이라 명분도 맞는다
                skin=SKIN['pale'], hair='7a6a52', beard='stubble',
                # ★모자까지 흰색으로 하면 머리와 몸통이 한 덩어리가 된다(1패스 자기비평).
                #   모자는 밀가루 안 묻은 낡은 캔버스로 눌러 얼굴선을 살린다
                cloth='cream', under='oat', legs='canvas', boot='boot',
                head='cap', headc='sand', prop='sack', roll=3, dust=True,
                surface='stripe_v', surfc='sand',
                garb='smock', yoke=2,
                eye_y=4, iris='blue', jaw='long', fringe=3, cheek=True, bootrows=2),

    # ── 여성 주민 ────────────────────────────────────────────────────────
    '103': dict(file='gretchen', cid=103, label='그레첸 — 빵집',
                # "갓 구운 빵 냄새 좋지 않나요?" → 밀가루 앞치마 + 두건
                female=True, skin=SKIN['pale'], hair='a83a1e', backhair=8,
                # 두건까지 표백 흰색이면 창백한 얼굴과 붙는다 — 두건만 한 단 낮춘다
                garb='kirtle', cloth='rust', under='linen', extra='chalk',
                legs='rust', boot='boot', head='kerchief', headc='linen',
                prop='basket', apron=True,
                surface=('pocket', 'trim'), surfc='rust',
                eye_y=4, iris='green', jaw='oval', cheek=True, marks='freckles', mouth_y=6),
    '105': dict(file='inga', cid=105, label='잉가 — 물 긷는 여인',
                # "물 길으러 나왔어요" → 가장 소박한 차림. 금속 0곳
                female=True, skin='b58b65', hair='d9bb63',
                cloth='moss', under='oat', legs='moss', boot='boot',
                head=None, prop='pouch', braid=True,
                surface='seams', surfc='oat',
                garb='overdress', over='canvas',
                eye_y=5, iris='grey', jaw='narrow', backhair=9, marks='ruddy'),
    '136': dict(file='mia', cid=136, label='미아 — 생선 손질',
                # "생선은 손질이 반이랍니다" → 방수 앞치마 + 걷은 소매 + 비늘
                # 방수 앞치마는 타르를 먹인 검정이 실물에 맞다 — 어물전 3인(헬가·그레타)과
                # 앞치마 색으로 갈리고, 마을의 '어두운 사람' 쿼터도 여기서 하나 채운다
                female=True, skin='b58f6e', hair='c25a2a', braid=True,
                garb='kirtle', cloth='teal_d', under='linen', extra='pitch',
                legs='teal_d', boot='boot', head='kerchief', headc='teal',
                prop='scales', apron=True, roll=5,
                surface='pocket', surfc='teal',
                eye_y=4, iris='dark', jaw='narrow', backhair=9, brow_a=-1),
    '138': dict(file='frieda', cid=138, label='프리다 — 항구 가수',
                # "항구엔 늘 노랫거리가 있죠" → 마을에서 유일하게 색을 좀 쓴다
                # ★그 '색을 쓴다'가 말뿐이었다(와인색=채도 0.28). 꼭두서니 빨강 + 웰드
                #   노랑 숄로 실제 유채색 자리를 준다 — 무대에 서는 사람이니 명분도 맞다
                female=True, skin=SKIN['ruddy'], hair='1b1a24',
                garb='kirtle', cloth='madder', under='linen', legs='madder', boot='boot',
                head=None, prop='shawl', shawl='weld', braid=True,
                surface=('lacing', 'trim'), surfc='weld',
                layer2='sash', l2c='weld',
                eye_y=3, iris='green', jaw='oval', backhair=9, cheek=True, lip='a8484a'),

    # ── 아이 / 젊은이 ────────────────────────────────────────────────────
    '137': dict(file='leo', cid=137, label='레오 — 부두 아이',
                # "갈매기들이 자꾸 생선을 훔쳐가요!" → 헐렁한 물려받은 옷, 맨발
                skin='c29b6f', hair='8a6a3f', child=True,
                cloth='teal', under='oat', legs='canvas', boot=None,
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
               skin='d4b090', hair='9a938a', beard='full', age=True,
               garb='robe', cloth='bone', under='oat', legs='canvas', boot='boot',
               head=None, prop='book',
                surface='trim', surfc='leather',
                # ★눈이 3행짜리 덩어리로 보였다(2026-08-04 지적). 백발이라 눈썹색이
                #   hair[3]=c2bbb5 → 흰자 c9c4b8와 RGB 총차 19(=같은 색)로 붙어버려
                #   눈썹 2행 + 눈 1행이 하나로 읽혔다. 눈썹을 1행으로 줄이고 짙은 회색을
                #   직접 지정 → 그 1행이 눈꺼풀 구실을 해서 눈이 2×2로 읽힌다.
                #   (socket은 눈썹 y와 같은 행이라 항상 덮여 무의미했으므로 제거)
                eye_y=4, iris='grey', jaw='long', fringe=0,
                brow_w=1, brow_c='5b544c'),
    '72': dict(file='marie', cid=72, label='마리 — 조합 재료상',
               # "조합에 쓸 재료가 늘 부족해요" → 재료를 다루는 손. 도구 앞치마
               female=True, skin='cfa47e', hair='241f1c',
               garb='kirtle', cloth='olive', under='linen', extra='canvas',
               legs='olive', boot='boot', head=None, prop='tools',
               apron=True, roll=6, braid=True,
                surface='pocket', surfc='canvas',
                hem=11,
                eye_y=4, iris='brown', jaw='oval', backhair=8, marks='mole'),
    '73': dict(file='doran', cid=73, label='도란 — 상단 바르칸 지부',
               # "상단 바르칸 지부의 도란이라 하오" → 마르코82(상단마을)의 하급 동료.
               #   버건디는 마르코 몫이니 여기는 짙은 청록 + 놋쇠 한 곳
               skin='b98a5c', hair='3f3128', beard='goatee',
               garb='coat', cloth='verdigris', under='linen', legs='charcoal',
               boot='boot_d', head='cap', headc='verdigris', prop='pouch',
               accent='brass',
                surface=('placket', 'buttons'), surfc='brass',
                eye_y=3, iris='dark', jaw='narrow', brow_a=1, bootrows=5),
    '108': dict(file='brigitte', cid=108, label='브리기테 — 직조공',
                # "옷감을 짜는 게 제 일이에요" → 실타래와 부드러운 옷감
                # 적발 — 마을에 없던 머리색. 실타래를 다루는 사람이라 색이 붙어도 안 튄다
                female=True, skin='d0a57f', hair='8f4a24',
                cloth='slate', under='linen', legs='slate',
                boot='boot', head='kerchief', headc='oat', prop='yarn',
                surface='check', surfc='oat',
                garb='overdress', over='oat',
                eye_y=4, iris='amber', jaw='oval', backhair=9, cheek=True),
    '109': dict(file='siegfried', cid=109, label='지그프리트 — 사냥꾼',
                # "사냥이든 낚시든, 실력은 눈으로 봐야 알지" → 후드 + 가죽 + 화살통
                skin='b0855e', hair='4a3a2a', beard='stubble',
                garb='jerkin', cloth='moss_d', under='canvas', legs='leather_d',
                boot='boot_d', head='hood', headc='moss_d', prop='quiver', sleeved=True,
                surface='seams', surfc='leather',
                folds=(2,),
                eye_y=4, iris='green', jaw='square', brow_w=2, socket=True, bootrows=6),
    '110': dict(file='astrid', cid=110, label='아스트리드 — 20년 장사꾼',
                # "장사 20년, 단골들이 물고기를 찾는답니다" → 억센 상인 여성
                female=True, age=True, skin='ba8f68', hair='7a6e5f',
                cloth='rust', under='oat', extra='rust',
                legs='rust', boot='boot', head='kerchief', headc='mustard',
                prop='ledger', apron=True,
                surface='stripe_v', surfc='oat',
                garb='overdress', over='walnut',
                eye_y=5, iris='hazel', jaw='square', backhair=7, marks='ruddy'),
    '135': dict(file='sven', cid=135, label='스벤 — 낚싯배 선장',
                # "낚싯배를 몰려면 실력부터 보여야지" → 방수 코트 + 선장 모자 + 밧줄
                skin='ad7762', hair='6b6154', beard='full', age=True,
                garb='coat', cloth='ink', under='teal', legs='pitch',
                boot='boot_d', head='cap', headc='ink', prop='rope',
                accent='brass',
                surface=('buttons', 'trim'), surfc='brass',
                layer2='sash', l2c='brass',
                eye_y=4, iris='blue', jaw='square', brow_w=2, marks='ruddy', bootrows=6),
    '140': dict(file='rudi', cid=140, label='루디 — 전령',
                # "소식을 전하는 게 제 일인데, 배가 고파서 원..." → 마르고 젊다.
                #   달리기 좋은 짧은 튜닉 + 어깨 가방. 왕도 전령149의 화려함과 반대
                skin='b08b67', hair='4a3d2f',
                cloth='weld', under='oat', legs='canvas',
                boot='boot', head='cap', headc='canvas', prop='satchel', roll=6,
                surface='placket', surfc='canvas',
                garb='wrap', cross=3,
                eye_y=5, iris='brown', jaw='narrow', fringe=3, mouth_w=3, bootrows=2),
    '29': dict(file='marta', cid=29, label='마르타 — 시장 안내',
               # "싱싱한 건 제값 쳐주는 게 시장 인심이죠" → 활기찬 시장 상인
               female=True, skin='bf9878', hair='9c7a4e',
               # 앞치마는 크림이 아니라 표백 흰색이어야 금색 드레스와 값이 갈린다
               garb='kirtle', cloth='weld', under='linen', extra='chalk',
               legs='weld', boot='boot', head=None, prop='basket',
               apron=True, braid=True,
                surface='stripe_v', surfc='linen',
                eye_y=4, iris='brown', jaw='oval', backhair=8, cheek=True, mouth_w=3),
    '30': dict(file='bettina', cid=30, label='베티나 — 요리 안내',
               # "이 주방에선 잡은 걸로 근사한 요리를 만든답니다" → 주방 보조
               female=True, skin='cfa47e', hair='2b2118', braid=True,
               garb='kirtle', cloth='moss', under='linen', extra='chalk',
               legs='moss', boot='boot', head='kerchief', headc='chalk',
               prop='ladle', apron=True,
                surface='pocket', surfc='moss',
                eye_y=5, iris='hazel', jaw='oval', backhair=9, marks='freckles'),
    '28': dict(file='felix', cid=28, label='펠릭스 — 대장간 견습',
               # "여긴 대장간이에요. 좋은 장비가 좋은 어부를 만들죠!" → 젊고 들뜬 견습.
               #   군터9(마스터)보다 앞치마가 작고 그을음이 적어야 계급이 읽힌다
               skin='b58f6a', hair='8f4a24', child=False,
               garb='apron', cloth='canvas', under='oat', extra='leather',
               legs='canvas', boot='boot', head=None, prop='tools', roll=5,
               patch='leg_l',
                surface='patchwork', surfc='canvas',
                layer2='suspenders', l2c='leather',
                eye_y=5, iris='blue', jaw='narrow', fringe=3, marks='freckles', bootrows=3),
    '17': dict(file='ingrid', cid=17, label='잉그리드 — 길드 접수',
               # 길드 GUI 담당. 마을에서 가장 격식 있는 여성 — 장부와 인장
               # 대청 파랑 — 마을에서 가장 격식 있는 여성이라 비싼 염료가 명분이 된다
               female=True, skin='d0a57f', hair='b9903f',
               garb='kirtle', cloth='woad', under='linen', legs='ink',
               boot='boot_d', head=None, prop='ledger', accent='brass',
                surface=('trim', 'buttons'), surfc='brass',
                eye_y=3, iris='grey', jaw='narrow', backhair=9, brow_a=1),

    # ── 기능 NPC (&b) ────────────────────────────────────────────────────
    '9': dict(file='gunter', cid=9, label='군터 — 마을 대장간',
              # ★왕실 대장장이 지크하르트117과 갈라야 한다: 지크=검댕 가죽·민머리·불똥.
              #   군터는 시골 노장 — 낡은 앞치마 + 머리 동여맨 천 + 흰 수염
              # 앞치마를 그을음색으로 — 대장간 사람이 마을에서 가장 어두운 축이 되는 게 맞다
              skin='b57f52', hair='8a8378', beard='full', age=True,
              garb='apron', cloth='canvas', under='oat', extra='soot',
              legs='grey', boot='boot_d', head='kerchief', headc='rust',
              prop='tools', roll=4, patch='leg_r',
                surface='patchwork', surfc='leather',
                layer2='gloves', l2c='leather_d',
                eye_y=4, iris='dark', jaw='square', brow_w=2, socket=True, marks='scar'),
    '21': dict(file='franz', cid=21, label='프란츠 — 마을 요리',
               # ★왕실 요리장 그레고르57과 갈라야 한다: 그레고르=올리브+코이프+노장.
               #   프란츠는 젊고 소박 — 오트 튜닉 + 리넨 앞치마 + 맨머리 + 국자
               skin='cfa379', hair='4a3d2f', beard='stubble',
               garb='apron', cloth='teal', under='linen', extra='chalk',
               legs='canvas', boot='boot', head=None, prop='ladle', roll=5,
                surface='pocket', surfc='teal',
                eye_y=5, iris='brown', jaw='oval', fringe=3, cheek=True, mouth_w=3),
    '6': dict(file='helga', cid=6, label='헬가 — 물고기 판매',
              # 오토14·그레타13과 한 어물전. 공통=방수 가죽 앞치마+비늘 / 개인=색과 나이
              female=True, skin='b08762', hair='7a2f3a',
              garb='kirtle', cloth='slate', under='oat', extra='leather',
              legs='slate', boot='boot', head='kerchief', headc='mustard',
              prop='scales', apron=True, roll=6,
                surface='pocket', surfc='mustard',
                eye_y=4, iris='hazel', jaw='square', backhair=8, marks='ruddy'),
    '13': dict(file='greta', cid=13, label='그레타 — 물고기 판매',
               # 어물전 셋 중 최고령. 색을 가장 뺀다
               female=True, age=True, skin='a88c73', hair='9a938a',
               cloth='grey', under='oat', extra='leather',
               legs='grey', boot='boot', head='kerchief', headc='oat',
               prop='scales', apron=True, roll=6,
                surface='check', surfc='oat',
                garb='overdress', over='charcoal',
                eye_y=4, iris='grey', jaw='long', backhair=6, socket=True),
    '7': dict(file='klaus', cid=7, label='클라우스 — 잡화 상점',
              # ★모래색 코트+가죽 캡+파우치는 '사냥꾼'으로 읽힌다(유저 지적).
              #   가게를 지키는 사람은 앞치마와 장부로 말한다 — 모자를 벗기고
              #   와인색 조끼 위에 상점 앞치마를 두른다
              skin='c39a72', hair='a89a6f', beard='mutton',
              garb='apron', cloth='madder', under='linen', extra='oat',
              legs='canvas', boot='boot', head=None, prop='ledger',
              accent='brass', roll=7,
                surface='placket', surfc='oat',
                hem=11, folds=(2, 5),
                eye_y=4, iris='amber', jaw='square', mouth_w=3, marks='ruddy', bootrows=3),
    '8': dict(file='bruno', cid=8, label='브루노 — 섬상점',
              # 섬으로 배를 대는 사람. 항해 쪽 어휘(밧줄)로 클라우스와 갈린다
              skin='a87a4e', hair='3f3128', beard='full',
              garb='coat', cloth='teal', under='canvas', legs='navy',
              boot='boot_d', head=None, prop='rope',
                surface='buttons', surfc='brass',
                collar=False, folds=(3,),
                eye_y=5, iris='blue', jaw='square', brow_w=2, marks='scar', bootrows=6),
    '18': dict(file='raimund', cid=18, label='라이문트 — 유저마켓',
               # 경매·중개. 장부와 놋쇠 한 곳
               skin='b98a5c', hair='4a3d2f', beard='goatee',
               garb='coat', cloth='wine', under='linen', legs='charcoal',
               boot='boot_d', head=None, prop='ledger', accent='brass',
                surface='buttons', surfc='brass',
                folds=(1, 4, 6),
                eye_y=3, iris='dark', jaw='narrow', brow_a=1, mouth_w=1),
    '19': dict(file='dietrich', cid=19, label='디트리히 — 일감 게시판',
               # ★[퀘스트] 태그지만 게시판=기능형이다(대사로 퀘스트를 주는 [Q]가 아님).
               #   왕도 프리츠120과 같은 '관청 서기' 어휘를 쓰되 색으로 갈린다
               skin='c39a72', hair='6b5540',
               garb='tunic', cloth='olive_d', under='linen', legs='charcoal',
               boot='boot', head='cap', headc='olive_d', prop='satchel', roll=7,
                surface='placket', surfc='linen',
                layer2='vest', l2c='olive_d',
                eye_y=4, iris='green', jaw='long', fringe=1, brow_a=-1),
    '43': dict(file='oskar', cid=43, label='오스카 — 말 대여',
               # 마부. 가죽 저킨 + 밧줄. 왕도 알브레히트121과 색으로 갈린다
               skin='b0855e', hair='4a3a2a', beard='stubble',
               garb='jerkin', cloth='walnut', under='oat', legs='leather',
               boot='boot_d', head='cap', headc='leather', prop='rope',
               sleeved=True,
                surface='seams', surfc='leather',
                layer2='gloves', l2c='leather',
                eye_y=5, iris='brown', jaw='square', marks='ruddy', bootrows=6),
    '141': dict(file='ludwig', cid=141, label='루드비히 — 여관 주인',
                # "이 마을에서 하룻밤 쉬어가시겠어요?" → 술잔과 앞치마, 넉넉한 체구
                skin='cf9e73', hair='241f1c', beard='mutton',
                garb='apron', cloth='wine', under='linen', extra='cream',
                legs='charcoal', boot='boot', head=None, prop='tankard', roll=6,
                surface='quilt', surfc='wine',
                eye_y=4, iris='hazel', jaw='square', cheek=True, mouth_w=3, marks='ruddy'),
    # ── 신규: 스폰마을 회복 NPC (아직 서버에 없음 — 스킨 선제작) ──────────────
    'healer': dict(file='healer', cid=901, label='회복 NPC(신규) — 마을 약초사',
                   # ★왕도 회복 힐데122와 갈라야 한다: 힐데=회청 로브+흰 코이프+여성.
                   #   마을은 남성 노인 약초사 — 세이지 로브 + 약초 다발 + 붕대 감은 손
                   skin='bd8f61', hair='9a938a', beard='full', age=True,
                   garb='robe', cloth='moss', under='linen', legs='moss',
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
              skin='ab8055', hair='9a938a', beard='full', age=True,
              garb='tunic', cloth='oat', under='canvas', legs='grey', boot='boot',
              head='cap', headc='rust', prop='shawl', shawl='teal', roll=8,
                surface='quilt', surfc='rust',
                layer2='vest', l2c='rust',
                eye_y=4, iris='blue', jaw='oval', fringe=1, socket=True, marks='ruddy'),
    '146': dict(file='chief', cid=146, label='촌장',
                # ★구스킨은 바닐라 주민(빌리저) 텍스처 — 사람이 아니라 몹으로 읽힌다.
                #   마을에서 가장 격식 있는 평민: 긴 코트 + 놋쇠 직위 사슬 + 마을 장부
                skin='c39a72', hair='9a938a', beard='full', age=True,
                garb='coat', cloth='ink', under='oat', legs='charcoal',
                boot='boot_d', head='coif', headc='grey', prop='book',
                accent='brass',
                surface=('trim', 'buttons'), surfc='brass',
                layer2='tabard', l2c='ink',
                # ★eye_y=3으로 올리면 코이프(0~3행)가 눈을 덮는다 — lint가 잡음
                eye_y=4, iris='grey', jaw='long', socket=True, brow_w=2, brow_a=1),

    '75': dict(file='rina', cid=75, label='리나 — 어부 지망 소녀',
               # "저도 언젠가 훌륭한 어부가 되고 싶어요" → 어른 옷을 줄여 입은 소녀
               female=True, child=True, skin='c29a76', hair='7a5f3a',
               # ★브리기테108(슬레이트 커틀)과 쌍둥이가 돼서 어부색으로 바꾼다 —
               #   어부 지망 소녀가 어른 어부 옷을 줄여 입은 것으로 읽힌다
               garb='kirtle', cloth='teal', under='linen', legs='canvas', boot='boot',
               head=None, prop='basket', braid=True, patch='leg_r',
                surface='patchwork', surfc='linen',
                eye_y=5, iris='green', backhair=9, fringe=3, marks='freckles', bootrows=2),
}


# ── 빌더 ───────────────────────────────────────────────────────────────────
def head(s, v, seed):
    skin, hair = ramp(v['skin']), ramp(v['hair'])
    g.head_base(s, skin, seed=seed)
    g.ears(s, skin, y=4)
    # ★얼굴 개인차 (2026-08-03) — 부위별 측정에서 머리가 가장 닮은 부위로 나왔다
    #   (자카드 0.561 vs 몸통 0.415·팔 0.310). 37명 전원이 눈 y=4·gaze=0·홍채 하나·
    #   입 y=6 w=2·앞머리 2로 똑같았기 때문. 옷에 했던 것과 같은 처방을 얼굴에 한다.
    fringe = v.get('fringe', 3 if v.get('child') else 2)
    g.hair(s, hair, fringe=fringe, back=v.get('backhair', 7 if v.get('female') else 6),
           seed=seed, part_x=v.get('part', 3 if v.get('female') else None))
    g.face_shape(s, skin, jaw=v.get('jaw', 'oval'), cheek=v.get('cheek', False))
    if v.get('beard'):
        # ★수염 시작 행은 눈보다 반드시 아래여야 한다 — 눈 높이를 사람마다 다르게
        #   한 뒤로 eye_y=5인 사람은 고정값 5와 충돌해 눈이 지워졌다(실측 3명)
        g.beard(s, ramp(v['hair']), style=v['beard'],
                y=max(v.get('eye_y', 4) + 1, 6 if v['beard'] == 'mutton' else 5),
                seed=seed, ragged=False)
    if v.get('age'):
        g.wrinkles(s, skin, crow=True, forehead=v.get('head') is None)
    eye_y = v.get('eye_y', 4)
    # ★표식(흉터·주근깨)을 눈보다 먼저 찍는다 — 나중에 찍으면 흉터가 흰자를 덮어
    #   눈이 반쯤 사라진다(실측: 랄프의 흉터가 오른쪽 눈을 지웠다)
    g.face_marks(s, skin, kind=v.get('marks'), seed=seed)
    g.eyes(s, v.get('sclera', 'c9c4b8'), ramp(g.IRIS[v.get('iris', 'brown')]),
           y=eye_y, gaze=v.get('gaze', 0), socket=skin[1] if v.get('socket') else None,
           iris_idx=1 if v.get('iris', 'brown') in ('blue', 'amber', 'hazel', 'grey')
           else 2)
    # ★brow_c = 눈썹색 직접 지정. 백발(age=True→hair[3])은 흰자와 색이 겹쳐 눈썹이
    #   눈에 붙어 보이는데, 그 사람만 짙은 색으로 떼어내려면 예외구가 필요하다.
    # ★여성은 눈썹을 한 행 위로 올려 눈 바로 위(eye_y-1)를 속눈썹에 내준다.
    #   남성 [눈썹 eye_y-1][눈] / 여성 [눈썹 eye_y-2][속눈썹 eye_y-1][눈]
    #   — 이 구조 차이가 8x8에서 성별을 만드는 실제 지점이다(garments.female_eyes 주석 참고).
    #   eye_y<=3이면 눈썹 자리가 앞머리에 덮이므로 눈썹은 원래 자리에 두고 속눈썹만 넣는다.
    brow_up = bool(v.get('female')) and eye_y >= 4
    g.brow(s, ramp(v['brow_c'])[2] if v.get('brow_c')
           else (hair[2] if not v.get('age') else hair[3]),
           y=eye_y - (2 if brow_up else 1),
           weight=v.get('brow_w', 1), angle=v.get('brow_a', 0))
    f = s.f('head', 'front')
    if v.get('female'):
        # 속눈썹 — 머리색 한 단 밝게 섞어 '검은 줄'이 되지 않게 한다
        g.female_eyes(s, g.mix(skin[1], hair[2], 0.65), eye_y=eye_y, skin_r=skin)
        f.rect(3, v.get('mouth_y', 6), 4, v.get('mouth_y', 6),
               ramp(v.get('lip', '9b5a52'))[2])          # 입술
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
        g.robe(s, cloth, y0=0, seed=seed, hem_row=11, sleeve_to=v.get('roll', 9),
               lining=under)
        g.overdress(s, R(v.get('over', 'canvas')), y0=1, hem=11, layer='outer', seed=seed)
        g.belt(s, R('leather'), y=7, layer='outer')
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
        g.kirtle(s, cloth, under, y0=0, seed=seed, hem_row=11,
                 sleeve_to=v.get('roll', 9),
                 neckline=v.get('neckline', 'square'),
                 waist=v.get('waist', 7), lace=v.get('lace', True))
        if v.get('apron'):
            g.apron(s, R(v['extra']), bib=(2, 5), bib_y=(2, 6), waist=7, hem=11,
                    wrap=0, straps=True, tie=True, seed=seed)
            fa = s.f('body', 'front', 'outer')
            for x in (0, 7):                             # 양옆을 비워 커틀이 흐르게
                fa.rect(x, 7, x, 11, (0, 0, 0, 0), 0)
        else:
            g.belt(s, R('leather'), y=7, layer='outer')


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
    g.female_hair_length(s, ramp(v['hair']), seed=seed,
                         head_volume=(v.get('head') is None and not v.get('visor')),
                         shoulders=v.get('head') not in ('hood', 'coif', 'veil'))


def build(v):
    s = Skin()
    seed = v['cid']
    head(s, v, seed)
    body(s, v, seed)
    extra_cut(s, v, seed)   # ★조끼·멜빵·새시 — 무늬보다 실루엣이 먼저 읽힌다
    surface(s, v, seed)     # ★무늬는 옷 다음, 소품 앞 — 소품 위에 줄무늬가 얹히면 안 된다
    feminize(s, v, seed)    # ★여성 실루엣 — 반드시 옷·무늬 다음(옷이 덮으면 무효), 소품 앞
    props(s, v, seed)
    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / f"tf_{v['file']}.png"))


if __name__ == '__main__':
    for k in sys.argv[1:] or VARIANTS:
        print(build(VARIANTS[k]))
