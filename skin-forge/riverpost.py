#!/usr/bin/env python3
"""강 건널목 대여소 4명 — 에크베르트202 · 요르크203 · 볼프람204 · 니클라스205.

CHARACTER BRIEF  (npc_brief.py --root <prod> --village 말대여_-171_-423 근거)
  역할   말 대여(horseRental) 2명 · 배 대여(boatRental) 2명. 대사 없음(기능형)
         → 역할 + 지역 + 건물이 컨셉의 전부다.
  지역   강 < 탄광 < 바르칸 < 바르칸 연안. 유럽풍. ★사막(토브·케피예) 요소 금지.
  위치   북쪽 초소(-171,-423 / -168,-409)와 남쪽 초소(-209,-375 / -214,-388).
         두 초소는 서로 55m, 가장 가까운 마을 NPC는 **380m** 밖이다 → 이 넷은
         사실상 «한 세트»로만 보인다. 그래서 서버 전체 중복보다 **넷끼리의
         구분**이 이 스킨셋의 최대 제약이다.
  건물   양쪽 다 같은 구조(거울상): 3x8 노점(카운터=반블록 벽·모루·대장간 작업대·
         종)과 3x3 말 우리(울타리+문). 모루가 실제로 있으므로 말 담당 한 명을
         **편자장이**로 잡을 근거가 된다.
  이웃   반경 40블록 안에 다른 NPC 없음 → 팔레트를 맞출 대상이 없고, 대신 이 넷이
         서로 다른 «축»을 가져야 한다.

DESIGN SPEC  (그리기 전에 전부 선언 — 이 표가 품질의 근본 레버)
  구분 축을 둘로 잡았다: 직업(말/배)이 실루엣을, 초소(북/남)가 팔레트 계열을 가른다.
  ┌ 에크베르트 202 — &b[말 대여] 북쪽 우리 · 50대 마부장
  │  실루엣  양털 칼라를 댄 **민소매 가죽 저킨** + 가슴을 가르는 **마구(馬具) 어깨끈**
  │          + 무릎 위까지 오는 **승마 장화(5행)**. 모자 없음(반백 머리를 보여준다)
  │  팔레트  저킨=산화갈 6b4a30(가죽) / 양털칼라=본 bfb39a / 셔츠=생리넨 a89880
  │          / 바지=이끼 모직 4f5540 / 장화=기름먹인 진갈 3a2c22 / 악센트=놋쇠 2곳
  │  비대칭  왼쪽 어깨의 마구끈 · 왼 허벅지 말빗 파우치
  │  얼굴    그을린 피부, 반백 머리(가르마 1px), **머튼촙 구레나룻**, 이마+눈가 주름,
  │          헤이즐 눈 안쪽 응시, 코 없음
  ├ 요르크 203 — &b[배 대여] 북쪽 노점 · 20대 후반 사공
  │  실루엣  **뜨개 어부 캡** + 어깨 요크가 있는 **기름칠 캔버스 스모크** + 걷어붙인
  │          오른소매 + **밧줄 벨트** + 짧은 젖은 장화(3행)
  │  팔레트  스모크=햇볕에 바랜 옅은 캔버스 c9bda2(무광, ★세트의 «밝은 옷» 슬롯)
  │          / 캡=강물 슬레이트블루 54606b(파랑은 캡·벨트에만 남긴다)
  │          / 셔츠=바랜 리넨 a9a290 / 바지=타르 진회 423d36 / 장화=거의 검정 221c16
  │          ★스모크(밝음) → 바지(어두움) 2단 대비 — 1패스에서 바지를 밝은 캔버스로
  │            뒀더니 스모크·셔츠·바지가 전부 크림색이라 «전신 한 덩어리»가 됐다
  │          ★파랑은 캡 + 칼라 트림 + 소매 커프에만 (밝은 천 위 1px 소품은 얼룩이 된다)
  │  비대칭  오른소매만 걷음 · 왼 허벅지 타르 주머니
  │  얼굴    젊은 피부, 짙은 금발(캡 아래), **무수염**(넷 중 유일), 파란 눈, 주름 없음
  ├ 볼프람 204 — &b[말 대여] 남쪽 우리 · 30대 편자장이
  │  실루엣  **무릎까지 오는 가죽 앞치마(hem 11)** + **양팔 다 걷은 맨팔** + 한 손만 장갑
  │          + 튼튼한 작업 장화. 노점의 모루가 이 직업의 근거다
  │  팔레트  앞치마=불에 그은 검은 가죽 2b241e(★세트의 «어두운 옷» 슬롯)
  │          / 셔츠=녹슨 적갈 8a4b34(세트의 유일한 채도
  │          앵커) / 바지=황토 캔버스 7a6b52 / 장화=재 3b332b / 악센트=**철** 8f8a84
  │          ★에크베르트의 놋쇠와 금속 종류로 갈린다
  │  비대칭  왼손만 가죽 장갑 · 오른 허벅지 망치 고리 · 앞치마 왼아래 헝겊 패치
  │  얼굴    붉게 튼 피부, 검은 머리, **짧은 턱수염(full·ragged 없음)**, 갈색 눈, 눈가 주름
  └ 니클라스 205 — &b[배 대여] 남쪽 노점 · 40대 뱃사공
     실루엣  **가죽 웨이스트코트(hem 9)** + 그 아래 **세로 줄무늬 리넨 셔츠** +
             **madder 목수건** + 걷어붙인 오른소매 + 짧은 장화
             ★가로 줄무늬는 금지(2026-08-03 오너 지시) — 세로만
             ★포니테일은 1패스에서 폐기: 베스트가 덮고, 색도 붙어 안 읽혔다
     팔레트  베스트=햇볕에 탄 가죽 4d3b2a / 셔츠=표백 리넨 b3a892 + 줄무늬 7a6a4a
             / 목수건=madder 7a3b30
             / 바지=인디고 캔버스 44506a / 장화=거의 검은 갈 2e2620 / 악센트=철 1곳
     비대칭  오른소매만 걷음 · 왼 허벅지 손질칼 파우치 · 목수건 매듭이 한쪽으로
     얼굴    햇볕에 탄 피부, 짙은 갈색 머리, **염소수염**, 회청 눈, 이마+눈가 주름
  정체 모티프  넷 다 가슴 로고·문장 없음(장인은 로고를 안 붙인다). 정체성은 재단과 소지품.

  넷의 «구분 축» 요약 — 하나라도 겹치면 세트로 봤을 때 닮아 보인다
     머리쓰개  없음 / 뜨개캡 / 없음 / 없음(목수건)
     수염      머튼촙 / 없음 / 턱수염 / 염소수염          ← 4/4 전부 다름
     상체      민소매 저킨 / 스모크 / 앞치마 / 웨이스트코트+줄무늬
     금속      놋쇠 / 놋쇠(토큰 1px) / 철 / 철
     팔        긴소매 / 오른쪽만 걷음 / 양쪽 맨팔 / 오른쪽만 걷음
"""
import pathlib
import sys
import zlib

# ★스킬 본체는 ~/.codex/skills/npc-skin-style-mirror 에 있고, 레포의
#   .claude/skills/npc-skin-forge 가 거기로 가는 «git 추적되는» 심볼릭이다.
#   기존 모듈 전부가 ~/.claude/skills/... 를 하드코딩하는데 그 링크가 사라져
#   2026-09-02 에 49/56 이 ModuleNotFoundError 로 죽어 있었다. 그래서 추적되는
#   레포 경로를 먼저 보고, 없으면 홈을 본다.
for _cand in (pathlib.Path(__file__).resolve().parents[1]
              / '.claude/skills/npc-skin-forge/scripts',
              pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'):
    if _cand.is_dir():
        sys.path.insert(0, str(_cand))
        break
else:
    raise SystemExit('npc-skin-forge/scripts 를 찾을 수 없다')

import garments as g                                  # noqa: E402
from skinlib import Skin, ramp, ramp_lit, rgba        # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'


def _seed(name):
    """★hash() 금지 — 프로세스마다 랜덤 시드가 달라 빌드가 비결정적이 된다."""
    return zlib.crc32(name.encode()) % 100000


# ── 재질별 램프 (lessons.md 19장) ────────────────────────────────────────────
# 기본 ramp() 는 노랑·황토를 그늘에서 구하려고 색상을 돌리고 하이라이트 채도를 깎는다.
# 무광 천(모직·리넨·캔버스)과 가죽에는 그 보정이 틀렸다 — 금속만 진짜 하이라이트를 갖는다.

def matte(base, spread=0.22):
    """무광 직물 — 색상 회전 0, 채도 거의 고정, 명도 폭 좁게."""
    return ramp(base, spread=spread, hue=0.0, sat=0.03)


def leather(base, spread=0.34):
    """가죽 — 무광보다 «완전 조금만» 반사한다."""
    return ramp(base, spread=spread, hue=0.02, sat=0.06)


def matte_reflectance(s, mid_hex, keep=0.35, sat_keep=0.55, hue_win=(0.50, 0.72),
                      sat_min=0.18):
    """무광 재질의 반사율을 «결과 픽셀»에 걸어 하이라이트를 눌러 준다.

    램프를 좁히는 것만으로는 부족하다 — form_fill·speckle·folds·shade_col_falloff 가
    램프 양끝을 향해 섞도록 강도가 하드코딩돼 있어서, 어두운 한색(寒色)의 밝은 픽셀이
    «남색에서 벗어난» 청록·하늘색으로 빠진다(lessons.md 19장 실측).
    ★이 패스는 micro_light() «뒤에» 와야 한다. save() 가 micro_light 를 자동 호출하므로
      호출부에서 미리 돌리고 _microed 플래그를 세운다.
    ★hue 창으로 «그 색만» 건드린다. 머리는 제외(눈동자 회청이 창에 걸린다).
    """
    import colorsys
    from skinlib import all_boxes
    _mh, _ms, mid = colorsys.rgb_to_hsv(*[int(mid_hex[i:i + 2], 16) / 255
                                          for i in (0, 2, 4)])
    for key, (bx, by, w, h) in all_boxes().items():
        if key.split('.')[0] == 'head':
            continue
        for j in range(h):
            for i in range(w):
                px = s.im.getpixel((bx + i, by + j))
                if not px[3]:
                    continue
                hh, ss, vv = colorsys.rgb_to_hsv(*[c / 255 for c in px[:3]])
                if not (hue_win[0] < hh < hue_win[1] and ss > sat_min):
                    continue
                vv = max(0.04, min(1.0, mid + (vv - mid) * keep))
                ss = max(0.0, min(1.0, _ms + (ss - _ms) * sat_keep))
                rr, gg, bb = colorsys.hsv_to_rgb(hh, ss, vv)
                s.im.putpixel((bx + i, by + j),
                              (round(rr * 255), round(gg * 255), round(bb * 255), px[3]))


def _eye_guard(s, eye_y, who):
    """★lessons.md 13장 — 머리쓰개/머리카락 «뒤에» 둬야 의미가 있는 가드."""
    f = s.f('head', 'front')
    if sum(1 for x in (1, 2, 5, 6) if max(f.get(x, eye_y)[:3]) > 150) < 2:
        raise ValueError('%s: 눈이 지워졌다 (eye_y=%d)' % (who, eye_y))


def _hair_frame(s, hair_r, rows=7, part_x=5):
    """얼굴을 감싸는 옆머리 + 가르마 1px — 전부 **outer** 에 얹어 머리통을 넓힌다.

    ★x0·x7 은 얼굴 «바깥 열»이라 눈(x1·x6)을 가리지 않는다. 같은 픽셀을 base 에
      칠하면 얼굴이 6px 로 깎여 «갈색 헬멧»이 된다(lessons.md 3장).
    ★좌우 격차는 «한 단»까지 — 두 단 벌리면 «머리 색이 반반»이 된다(20장).
    ★앞면 outer 는 빈 칸만 채우므로 캡·후드와 자동으로 공존한다.
    """
    hf = s.f('head', 'front', 'outer')
    for y in range(rows):
        for x, c in ((0, hair_r[4] if y < 3 else hair_r[3]),
                     (7, hair_r[3] if y < 3 else hair_r[2])):
            if hf.get(x, y)[3] < 128:
                hf.px(x, y, c)
    if part_x is not None:
        for y in (0, 1):
            if hf.get(part_x, y)[3] >= 128:
                hf.px(part_x, y, hair_r[1])


def _seal_hairline(s, skin_r, hair_r, rows=3):
    """앞머리 구간에 남은 «피부 픽셀»을 머리카락으로 메운다. ★얼굴 피처를 다 그린 뒤에 호출.

    왜 필요한가: g.hair 의 헤어라인 지그재그가 몇 칸을 비우고, 그 아래 base 에는
    head_base·face_marks·wrinkles(forehead=True) 가 칠한 피부가 있다. 8x8 에서 그
    고립된 밝은 1px 은 «머리카락 한가운데 주황 점»으로 읽힌다(1패스 에크베르트,
    2패스 니클라스 둘 다 이걸로 걸렸다).

    판정을 세 번 고쳤다 — 전부 렌더 실측이다:
      ① «피부 램프와 정확히 일치» → face_marks(ruddy) 가 mix 로 얹은 색은 램프에 없다
      ② «좌우 이웃이 둘 다 outer 머리카락일 때만» → 옆 칸이 base 머리카락이면 건너뛴다
      ③ «머리 램프 최상단보다 밝으면» → **백발에서 뒤집힌다**(에크베르트 머리 램프 [4]
         가 그을린 피부보다 밝아 하나도 안 걸렸다)
      확정: 그 픽셀이 피부 램프와 머리 램프 중 «어느 쪽에 더 가까운가»로 분류한다.
    ★호출 위치도 중요하다 — wrinkles(forehead=True) 가 봉인 «뒤»에 돌면 그 자리를 다시
      피부로 칠한다. 그래서 얼굴 피처 전부 뒤, 눈 가드 앞에 둔다.
    """
    hf, bf = s.f('head', 'front', 'outer'), s.f('head', 'front')
    skins = [rgba(c)[:3] for c in skin_r]
    hairs = [rgba(c)[:3] for c in hair_r]

    def near(px, pool):
        return min(sum((px[i] - c[i]) ** 2 for i in range(3)) for c in pool)

    for y in range(rows):
        for x in range(8):
            if hf.get(x, y)[3] >= 128:
                continue                          # outer 머리카락이 이미 덮었다
            px = bf.get(x, y)[:3]
            if near(px, skins) < near(px, hairs):
                hf.px(x, y, hair_r[2])


def _one_glove(s, r, part='arm_l', rows=3):
    """한 손만 장갑 — gloves() 는 양팔을 다 덮으므로 비대칭용으로는 못 쓴다."""
    for fname in ('front', 'back', 'right', 'left'):
        f = s.f(part, fname, 'base')
        for y in range(12 - rows, 12):
            f.row(y, r[3] if fname in ('front', 'right') else r[2])
    s.f(part, 'bottom', 'base').fill(r[1])
    for fname in ('front', 'back', 'right', 'left'):        # 커프 = 장갑 아가리
        s.f(part, fname, 'base').row(12 - rows, r[4])


# ══════════════════════════════════════════════════════════════════════════════
def build_ekbert():
    """에크베르트 202 — 마부장. 민소매 가죽 저킨 + 양털 칼라 + 마구 어깨끈."""
    name, SEED = 'ekbert', _seed('ekbert')
    P = dict(
        skin=ramp('b58256'),
        hair=ramp('6d6055', spread=0.26),               # 반백 — 폭을 좁혀야 «반반»이 안 된다
        brow=ramp('3a2f26'),
        beard=ramp('7a6c5c'),
        jerkin=leather('6b4a30'),
        fleece=matte('bfb39a', 0.20),                   # ★1패스에서 eae0c8 로 떠서 «흰 턱받이»로 읽혔다
        shirt=matte('a89880', 0.24),
        pants=matte('4f5540', 0.24),                    # 이끼 모직 — 저킨과 두 단 이상 차이
        boot=leather('3a2c22'),
        strap=leather('54402c'),
        brass=ramp_lit('b08d3c'),                       # 금속만 진짜 하이라이트
        iris=ramp(g.IRIS['hazel']),
    )
    s = Skin()

    # ---- 머리: 피부 → 머리카락 → 수염 → 얼굴 피처 (나중에 그린 것이 이긴다)
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    #   ★male_hair_style('sidepart'/'crop') 는 이마를 피부로 열어 앞머리를 1행으로
    #     깎는다(lessons.md 20장). 앞머리는 fringe 로 채우고 가르마 1px 만 낸다.
    g.hair(s, P['hair'], fringe=3, back=7, seed=SEED, part_x=5)
    _hair_frame(s, P['hair'], rows=6, part_x=5)
    g.face_shape(s, P['skin'], jaw='square', temple=True)
    g.face_marks(s, P['skin'], kind='ruddy', seed=SEED)
    #   ★머튼촙은 face_shape·face_marks «뒤»에 와야 한다 — 그 둘이 턱선 음영을 x0·x1·
    #     x6·x7 에 칠해서 앞에 그린 구레나룻을 지웠다(3패스 실측: row5~7 이 다시 피부색).
    #   ★g.beard(style='mutton', y=4) 은 x0·x1·x6·x7 을 y4 부터 칠하는데, y4 는 «눈 행»이라
    #     오른눈 흰자(x6)를 통째로 먹는다(2패스 얼굴 렌더 실측 — 오른눈이 검은 덩어리였다).
    #     _eye_guard 는 «4칸 중 2칸»만 보므로 통과해 버린다. 그래서 직접 재단한다:
    #     바깥 열(x0·x7)은 눈 행 위(y3)부터, 눈 옆 열(x1·x6)은 눈 아래(y5)부터.
    _bf = s.f('head', 'front')
    _br = [P['beard'][i] for i in range(5)]
    for _x in (0, 7):
        _bf.col(_x, _br[2], 3, 7)
    for _x in (1, 6):
        _bf.col(_x, _br[2], 5, 7)
    _bf.px(0, 3, _br[1]); _bf.px(7, 3, _br[1])           # 구레나룻 위끝은 한 단 어둡게
    for _fn in ('right', 'left'):                        # 옆면으로 이어져야 «구레나룻»이다
        s.f('head', _fn).rect(0, 3, 2, 7, _br[2])
        s.f('head', _fn).px(0, 3, _br[1])
    _bf.row(7, _br[1], 2, 5)                             # 턱 밑 그늘 — 머튼촙은 턱이 비어 있다
    g.wrinkles(s, P['skin'], brow_y=2, crow=True, forehead=True)   # 모자 없음 → 이마 주름 가능

    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, iris_idx=1)
    g.brow(s, P['brow'][2], y=3, weight=1)
    g.mouth(s, P['skin'], y=6, w=2)
    _seal_hairline(s, P['skin'], P['hair'], rows=3)   # ★얼굴 피처 전부 뒤
    _eye_guard(s, 4, name)

    # ---- base: 셔츠(긴소매) → 바지 → 승마 장화
    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, fold_cols=(2, 5),
            grain=0.07)
    g.sleeves(s, P['shirt'], y0=0, y1=9, seed=SEED, grain=0.07)
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['pants'], y0=0, y1=6, seed=SEED, grain=0.11)
    g.boots(s, P['boot'], rows=5, toe=True, cuff=True)           # 무릎 위까지 = 승마 장화

    # ---- outer: 민소매 저킨 → 양털 칼라 → 마구끈 → 벨트 → 파우치
    g.vest(s, P['jerkin'], y0=0, hem=10, gap=2, layer='outer', seed=SEED)
    for fname in ('front', 'back'):                              # 양털 칼라 — 저킨 위 2행
        f = s.f('body', fname, 'outer')
        f.row(0, P['fleece'][4], 1, 6)
        f.row(1, P['fleece'][2], 1, 6)
    for fname in ('right', 'left'):
        s.f('body', fname, 'outer').rect(1, 0, 2, 1, P['fleece'][3])
    s.f('body', 'top', 'outer').rect(1, 0, 6, 2, P['fleece'][4])
    s.speckle('body', P['fleece'], 0, 1, layer='outer', density=0.16, seed=SEED)
    #   칼라가 저킨에 드리우는 그늘 — outer y2 는 저킨이 있으니 거기 직접
    s.f('body', 'front', 'outer').row(2, P['jerkin'][1], 1, 6)
    #   비대칭 ①: 왼어깨에서 내려오는 마구끈. top·back 면까지 이어야 «끈»으로 읽힌다
    g.bandolier(s, P['strap'], front_x=2, layer='outer')
    g.belt(s, P['strap'], y=7, accent=P['brass'], layer='outer', ao=False)
    s.ao_row('body', 8, P['jerkin'], layer='outer', drop=2)
    #   비대칭 ②: 왼 허벅지 말빗 파우치. ★금속 램프로 다 채우면 «다리에 금괴»가 된다
    g.pouch(s, P['strap'], part='leg_l', face='front', x=1, y=1, w=2, h=3,
            metal=P['brass'])
    for _p in ('arm_r', 'arm_l'):                                # 팔이 단색 판자가 되지 않게
        s.shade_col_falloff(_p, P['shirt'], 0, 9)
    s.folds('arm_r', 2, 8, P['shirt'], cols=(1,), seed=SEED)
    s.folds('arm_l', 2, 8, P['shirt'], cols=(2,), seed=SEED + 1)

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / ('rp_%s.png' % name)))


# ══════════════════════════════════════════════════════════════════════════════
def build_jorg():
    """요르크 203 — 젊은 사공. 뜨개 캡 + 기름칠 캔버스 스모크 + 걷어붙인 오른소매."""
    name, SEED = 'jorg', _seed('jorg')
    P = dict(
        skin=ramp('c08f66'),
        hair=ramp('8a6a3f', spread=0.26),
        brow=ramp('4a3520'),
        smock=matte('c9bda2', 0.22),                    # 햇볕에 바랜 옅은 캔버스
        cap=matte('54606b', 0.22),
        seam=matte('9c8f74', 0.22),
        shirt=matte('a9a290', 0.24),
        # ★1패스 실측: 스모크·셔츠·바지가 전부 크림색이라 «전신 한 덩어리»로 읽혔다.
        #   하체를 타르 먹인 진회색으로 내려 밝은 스모크와 2단 대비를 만든다.
        pants=matte('423d36', 0.24),
        rope=matte('8a6f42', 0.26),
        boot=leather('221c16'),

        iris=ramp(g.IRIS['blue']),
    )
    s = Skin()

    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=3, back=6, seed=SEED, part_x=None)
    g.face_shape(s, P['skin'], jaw='oval', temple=True)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, iris_idx=1)
    g.brow(s, P['brow'][2], y=3, weight=1)
    g.mouth(s, P['skin'], y=6, w=2)
    #   ★캡은 맨 마지막. crown=3 이 «캡»의 최소선(2행은 머리띠로 읽힌다)
    g.cap(s, P['cap'], crown=3, band=P['boot'], seed=SEED)
    _hair_frame(s, P['hair'], rows=6, part_x=None)      # 캡 아래로 삐져나온 옆머리
    #   무수염 — 넷 중 유일. 주름 없음(20대). 코 없음(기본)
    _seal_hairline(s, P['skin'], P['hair'], rows=3)   # ★얼굴 피처 전부 뒤
    _eye_guard(s, 4, name)

    # ---- base: 셔츠 → 바지 → 짧은 젖은 장화
    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, grain=0.08)
    #   비대칭 ①: 오른소매만 걷음 → 팔뚝이 드러난다
    g.sleeves(s, P['shirt'], y0=0, y1=9, rolled=('arm_r', 6), skin_r=P['skin'],
              seed=SEED, grain=0.08)
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['pants'], y0=0, y1=8, seed=SEED, grain=0.12)
    g.boots(s, P['boot'], rows=3, toe=True, cuff=True)

    # ---- outer: 스모크(어깨 요크 + 세로 개더) → 밧줄 벨트 → 타르 주머니
    g.smock(s, P['smock'], y0=0, hem=11, yoke=2, layer='outer', seed=SEED, grain=0.11)
    #   스모크 소매도 같은 천이라야 «작업복 한 벌»로 읽힌다. 걷은 오른팔은 y6 까지만
    g.sleeves(s, P['smock'], y0=0, y1=5, layer='outer', cuff=True, seed=SEED + 2,
              grain=0.09)
    for _p, _to in (('arm_r', 5), ('arm_l', 8)):
        s.shade_col_falloff(_p, P['smock'], 0, _to, layer='outer')
    s.f('arm_l', 'front', 'outer').row(9, P['smock'][1])         # 왼소매 커프 그늘
    #   ★요크 이음선을 «따로» 어둡게. smock() 은 r[1] 을 쓰는데 밝은 램프에서는 r[1] 도
    #     밝아서 이음선이 사라진다(1패스 실측: 요크가 안 보였다).
    for _fn in ('front', 'back'):
        s.f('body', _fn, 'outer').row(2, P['seam'][2])
    #   ★파랑을 «칼라와 커프»로 옮긴다. 1패스에서는 옅은 스모크 위에 놋쇠 토큰 1px 을
    #     얹었더니 그냥 «얼룩»으로 보였다 — 밝은 천 위의 소품은 색이 아니라 자리로 읽힌다.
    g.trim(s, P['cap'], part='body', rows=(0,), layer='outer', x0=1, x1=6)
    for _p in ('arm_r', 'arm_l'):
        for _fn in ('front', 'back', 'right', 'left'):
            _f = s.f(_p, _fn, 'outer')
            _row = 5 if _p == 'arm_r' else 8              # 걷은 오른소매는 짧다
            if _f.get(0, _row)[3] >= 128:
                _f.row(_row, P['cap'][3])
    g.belt(s, P['rope'], y=7, accent=None, buckle=False, layer='outer', ao=False)
    s.band('body', 8, 8, P['rope'][1], layer='outer')     # 밧줄 아래 그림자 = 두께
    s.ao_row('body', 9, P['smock'], layer='outer', drop=2)
    #   비대칭 ②: 왼 허벅지 타르 주머니
    g.pouch(s, P['boot'], part='leg_l', face='front', x=1, y=2, w=2, h=3)

    # ---- 마지막: 미세 계조 → 재질 계수 (★순서 고정, lessons.md 19장)
    s.micro_light()
    s._microed = True
    matte_reflectance(s, '54606b', keep=0.38, sat_keep=0.60)   # 캡의 슬레이트만

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / ('rp_%s.png' % name)))


# ══════════════════════════════════════════════════════════════════════════════
def build_wolfram():
    """볼프람 204 — 편자장이. 짧은 가죽 앞치마 + 양팔 맨팔 + 한 손 장갑."""
    name, SEED = 'wolfram', _seed('wolfram')
    P = dict(
        skin=ramp('b07a52'),
        hair=ramp('2f2620', spread=0.26),
        brow=ramp('1f1a15'),
        # ★2패스: 4a3b30 은 흑발(2f2620)과 붙어 얼굴 아래 절반이 검은 덩어리였다
        beard=ramp('5c4a3a'),                           # 피부보다 어둡고 머리보다 «확실히» 밝게
        apron=leather('2b241e', 0.30),
        shirt=matte('8a4b34', 0.24),                    # 녹슨 적갈 — 세트의 채도 앵커
        pants=matte('7a6b52', 0.24),
        boot=leather('3b332b'),
        glove=leather('4c3a2a'),
        iron=ramp_lit('8f8a84'),                         # ★에크베르트의 놋쇠와 갈리는 금속
        iris=ramp(g.IRIS['brown']),
    )
    s = Skin()

    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=3, back=6, seed=SEED, part_x=2)
    _hair_frame(s, P['hair'], rows=5, part_x=2)
    g.beard(s, P['beard'], style='full', y=5, seed=SEED, ragged=False)  # 볼 행은 비워 둔다
    g.face_shape(s, P['skin'], jaw='square', temple=True)
    g.face_marks(s, P['skin'], kind='ruddy', seed=SEED)                 # 화덕 앞에서 튼 볼
    g.wrinkles(s, P['skin'], brow_y=2, crow=True, forehead=False)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, iris_idx=1)
    g.brow(s, P['brow'][2], y=3, weight=1, angle=1)
    g.mouth(s, P['skin'], y=6, w=2, color=P['beard'][1])   # 콧수염 «안»의 어두운 2px 선
    _seal_hairline(s, P['skin'], P['hair'], rows=3)   # ★얼굴 피처 전부 뒤
    _eye_guard(s, 4, name)

    # ---- base: 셔츠 → 양팔 걷어 맨팔 → 바지 → 작업 장화
    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, grain=0.09)
    g.sleeves(s, P['shirt'], y0=0, y1=6, seed=SEED, grain=0.09)
    #   ★소매만 짧게 하면 그 아래로 셔츠색이 남아 «긴 속옷»이 된다 → base 를 피부로 덮는다
    g.bare_arms(s, P['skin'], y0=7, y1=11)
    for _p in ('arm_r', 'arm_l'):
        s.f(_p, 'front').row(6, P['shirt'][4])             # 걷어올린 소매 아가리
        s.f(_p, 'back').row(6, P['shirt'][2])
    #   비대칭 ①: 왼손만 가죽 장갑 (gloves() 는 양팔을 다 덮어 비대칭이 안 된다)
    _one_glove(s, P['glove'], part='arm_l', rows=3)
    g.pants(s, P['pants'], y0=0, y1=7, seed=SEED, grain=0.11)
    g.boots(s, P['boot'], rows=4, toe=True, cuff=True)

    # ---- outer: 짧은 앞치마 → 철 버클 → 망치 고리 → 헝겊 패치
    #   ★앞치마를 «무릎까지»(hem 11) 내린다. 처음엔 hem 9 로 짧게 잘랐는데 그러면
    #     앞면 절반이 적갈 셔츠로 남아 세트의 «어두운 옷» 슬롯이 비었다
    #     (diversity_lint: 어두운 옷 0/4). 편자장이 앞치마는 원래 긴 게 맞다.
    g.apron(s, P['apron'], bib=(2, 5), bib_y=(1, 5), waist=6, hem=11,
            wrap=2, straps=True, tie=True, seed=SEED)
    s.buckle('body', 6, P['iron'], layer='outer')
    for x in (2, 5):                                       # bib 리벳 — 가슴 로고 대신
        s.f('body', 'front', 'outer').px(x, 1, P['iron'][4])
    #   비대칭 ②: 앞치마 왼아래 헝겊 패치 (낡음)
    g.patch(s, 'body', 'front', P['apron'], x=1, y=9, w=2, h=2, layer='outer')
    #   비대칭 ③: 오른 허벅지 망치 고리 — 가죽 고리 + 철 1px 만
    _lf = s.f('leg_r', 'front', 'outer')
    _lf.rect(1, 1, 2, 2, P['apron'][3])
    _lf.px(1, 3, P['apron'][1])
    _lf.px(2, 0, P['iron'][3])
    s.f('leg_r', 'right', 'outer').rect(2, 1, 3, 2, P['apron'][2])
    g.scuff(s, 'leg_r', P['pants'], 4, 7, layer='base', seed=SEED)   # 작업 흔적

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / ('rp_%s.png' % name)))


# ══════════════════════════════════════════════════════════════════════════════
def build_niklas():
    """니클라스 205 — 뱃사공. 가죽 웨이스트코트 + 세로 줄무늬 셔츠 + 포니테일."""
    name, SEED = 'niklas', _seed('niklas')
    P = dict(
        skin=ramp('b98455'),
        hair=ramp('4a3524', spread=0.26),
        brow=ramp('2b1f15'),
        beard=ramp('6a5039'),
        vest=leather('4d3b2a', 0.32),
        shirt=matte('b3a892', 0.24),
        stripe=matte('7a6a4a', 0.24),                   # ★세로만. 1패스의 93866d 는
        #                                                 셔츠와 값이 붙어 줄무늬가 안 보였다
        kerchief=matte('7a3b30', 0.24),
        pants=matte('44506a', 0.24),                    # 인디고 캔버스
        boot=leather('2e2620'),
        iron=ramp_lit('8f8a84'),
        iris=ramp(g.IRIS['grey']),
    )
    s = Skin()

    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    g.hair(s, P['hair'], fringe=3, back=7, seed=SEED, part_x=5)
    _hair_frame(s, P['hair'], rows=6, part_x=5)
    #   ★포니테일 폐기(1패스). 이유 두 개, 둘 다 실측이다:
    #     ① 그릴 자리(body back outer)를 뒤에 오는 vest() 가 통째로 덮는다
    #     ② 순서를 바꿔도 머리(4a3524)와 베스트(4d3b2a)가 사실상 같은 값이라
    #        «어두운색 위 어두운색»으로 안 읽힌다(lessons.md 9장)
    #     게다가 NPC 는 lookclose 로 늘 정면을 보므로 뒷면 장식은 체감이 0 이다(3장).
    #     대신 정면에서 읽히는 «목수건»으로 갈랐다 — 아래 outer 절.
    g.beard(s, P['beard'], style='goatee', y=5, seed=SEED)
    g.face_shape(s, P['skin'], jaw='oval', temple=True)
    g.face_marks(s, P['skin'], kind='ruddy', seed=SEED)
    g.wrinkles(s, P['skin'], brow_y=2, crow=True, forehead=True)
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, iris_idx=1)
    g.brow(s, P['brow'][2], y=3, weight=1)
    g.mouth(s, P['skin'], y=6, w=2)
    _seal_hairline(s, P['skin'], P['hair'], rows=3)   # ★얼굴 피처 전부 뒤
    _eye_guard(s, 4, name)

    # ---- base: 줄무늬 셔츠 → 바지 → 짧은 장화
    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, grain=0.08)
    #   비대칭 ②: 오른소매만 걷음
    g.sleeves(s, P['shirt'], y0=0, y1=9, rolled=('arm_r', 6), skin_r=P['skin'],
              seed=SEED, grain=0.08)
    #   세로 줄무늬는 «셔츠가 실제로 있는 행»에만 — 그 밖으로 나가면 곰팡이처럼 보인다
    g.stripes(s, 'body', P['stripe'], axis='v', period=4, width=1, y0=0, y1=11,
              layer='base')
    g.stripes(s, 'arm_l', P['stripe'], axis='v', period=4, width=1, y0=0, y1=8,
              layer='base')
    g.stripes(s, 'arm_r', P['stripe'], axis='v', period=4, width=1, y0=0, y1=5,
              layer='base')
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['pants'], y0=0, y1=8, seed=SEED, grain=0.12)
    g.boots(s, P['boot'], rows=3, toe=True, cuff=True)

    # ---- outer: 가죽 웨이스트코트 → 벨트(철 버클 1곳) → 손질칼 파우치
    g.vest(s, P['vest'], y0=0, hem=9, gap=2, layer='outer', seed=SEED)
    g.belt(s, P['vest'], y=7, accent=P['iron'], layer='outer', ao=False)
    s.ao_row('body', 8, P['vest'], layer='outer', drop=2)
    #   비대칭 ③: 왼 허벅지 손질칼 파우치
    g.pouch(s, P['vest'], part='leg_l', face='front', x=1, y=2, w=2, h=3,
            metal=P['iron'])
    #   목수건 — 컴팩트한 덩어리라 8x12 에서도 읽힌다. 옅은 셔츠 위 어두운 madder 라
    #   대비가 확보된다(밝은 천 위 밝은 소품이 안 읽히는 사고의 반대 처방)
    _kf = s.f('body', 'front', 'outer')
    for _x in range(2, 6):
        _kf.px(_x, 0, P['kerchief'][3])
    _kf.px(3, 1, P['kerchief'][4]); _kf.px(4, 1, P['kerchief'][2])
    _kf.px(3, 2, P['kerchief'][1])
    for _fn in ('right', 'left'):
        s.f('body', _fn, 'outer').rect(1, 0, 2, 0, P['kerchief'][2])
    s.f('body', 'back', 'outer').row(0, P['kerchief'][2], 2, 5)
    s.f('body', 'top', 'outer').rect(2, 1, 5, 2, P['kerchief'][3])
    for _p, _to in (('arm_r', 5), ('arm_l', 8)):
        s.shade_col_falloff(_p, P['shirt'], 0, _to)

    s.micro_light()
    s._microed = True
    matte_reflectance(s, '44506a', keep=0.40, sat_keep=0.62)

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / ('rp_%s.png' % name)))


ROSTER = (
    ('에크베르트', 202, build_ekbert),
    ('요르크', 203, build_jorg),
    ('볼프람', 204, build_wolfram),
    ('니클라스', 205, build_niklas),
)

if __name__ == '__main__':
    for nm, cid, fn in ROSTER:
        print('%-8s cid%-4d %s' % (nm, cid, fn()))
