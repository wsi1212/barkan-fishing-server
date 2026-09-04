#!/usr/bin/env python3
"""심해 탈주자 5인 — 모르209 · 비늘 짜는 이210 · 일곱-셋211 · 가라앉은 하212 · 울지 않는 것213.

CHARACTER BRIEF  (dialogue.json 전문 + build_ch7_side.py 설정 근거)
  무대   deep_sea 63/146/20 광장 — 「무명의 성소」 **밖**. 교단이 기른 사역어(使役魚) 중
         **탈주한 것들**이 모여 산다. 지상으로는 못 나간다(물 밖에서 못 산다).
  핵심   교단은 이들에게 **이름 대신 번호**를 줬고, 그 번호를 **비늘에 새겼다**.
         "지우려면 비늘째 뜯어야 한다"(모르). 옷은 **죽은 동족의 비늘로 짠 것**이고,
         그걸 짜는 자가 비늘 짜는 이다. 플레이어는 «동족의 비늘로 만든 가면»을 쓰고 온다.
  ★다섯이 한 광장에 4~6m 간격으로 서 있다 → 서버 전체 중복보다 **다섯끼리의 구분**이
    이 세트의 최대 제약이다. 그리고 동시에 **한 종족으로 읽혀야** 한다.

세트 공통 언어 (다섯 전부 — 이게 «한 종족»을 만든다)
  · 머리카락 없음 · 맨발(장화 없음, 물속이라 신을 이유가 없다)
  · **목 아가미 슬릿 3줄** — 머리 옆면 아래 + 몸통 옆면 위. 종족 표식 1순위
  · **비늘 결** — 대각 격자(세로 반복 금지: 다리가 줄무늬 바지가 된다, lessons 5-3)
  · **발광 눈** — 인간 공식(흰 흰자 + 어두운 홍채)의 «반대». 어두운 눈구멍에 창백한
    발광 홍채. 이 반전 하나가 축소 배율에서 «사람이 아니다»를 즉시 만든다
    (단 울지 않는 것만 빛이 꺼져 있다 — 그게 그 캐릭터다)
  · 팔뚝 바깥 지느러미 주름

DESIGN SPEC — 다섯의 구분축 (피부색 / 볏 / 옷 / 번호 표식, 넷 다 안 겹치게)
┌ 모르 209 — 촌장 격. 옛 번호 사-일. 스스로 이름을 붙인 첫 개체
│  피부  짙은 청록 2f5a58 (세트에서 가장 어둡고 채도 있는 «바다색»)
│  볏    넓고 낮은 등볏 — 관(冠)처럼 좌우로 벌어진다. 권위
│  옷    **어깨 비늘 망토** + 허리 가죽끈. 죽은 동족의 비늘로 짠 것(비늘 짜는 이의 작품)
│  표식  ★**지워진 번호** — 왼팔 바깥에 비늘째 뜯어낸 흉터 3px(밝은 흉터색).
│        "지우려면 비늘째 뜯어야 한다"의 시각적 근거. 다섯 중 유일한 흉터
├ 비늘 짜는 이 210 — 손일하는 자. 장비·가면 제작
│  피부  자갈빛 갈청 4a5748 (유일하게 «녹슨» 계열 — 물색에서 반보 벗어난다)
│  볏    뒤로 눕힌 낮은 볏(작업에 걸리지 않게) + 옆으로 늘어진 뺨 지느러미
│  옷    **뼈빛 비늘 앞치마**(9a917c — 세트의 유일한 «밝은 옷» 슬롯) + 왼허리 도구 주머니
│  표식  오른팔에 감긴 실 — 번호 자리를 실로 덮었다(지운 게 아니라 «가린» 사람)
├ 일곱-셋 211 — 어리다. 아직 번호로만 불린다
│  피부  창백한 연청 6d92a0 (세트에서 가장 밝고 어린 톤)
│  볏    아직 덜 자란 짧은 볏 2행
│  옷    ★거의 없음 — 허리 천 조각 하나 + 어깨 끈. 다섯 중 유일하게 «맨몸»
│  표식  ★**아직 남아 있는 번호** — 가슴 왼쪽 낙인 3px. 모르의 흉터와 정확히 짝을 이룬다
├ 가라앉은 하 212 — 옛 파수. 수조 곁에서 백 해. 교단 격식체를 쓰는 유일한 개체
│  피부  납빛 회청 56666b (백 해를 서 있어 색이 바랬다 — 채도 최저)
│  볏    길고 뾰족하게 뒤로 넘어간 볏 — 관모(冠帽) 실루엣. 다섯 중 가장 높다
│  옷    **교단 파수 제복의 잔재** — 프리즈머린 청록 2c5f63 튜닉 + 산호빛 견장 c9b98a
│        + 가슴 세로 트임. 다섯 중 유일한 «제복»(재단이 갖춰져 있다)
│  표식  번호 없음 — 파수는 번호가 아니라 «자리»였다. 대신 목에 옛 교단 링
└ 울지 않는 것 213 — 수조에서 «그릇»으로 개조되다 만 개체. 소리를 못 낸다. &f 대화 전용
   피부  병약한 창백 회분홍 8c7f80 ★네 명의 «바다색»에서 유일하게 벗어난다 —
         그 이탈 자체가 「개조되다 만」의 시각적 근거다
   볏    ★없다. **잘려 나간 밑동**만 남았다(2px 어두운 자국)
   옷    없음. **몸에 감긴 낡은 붕대** + 목의 **철 구속 밴드**(수조 기구의 잔재)
   얼굴  ★**입이 없다** — 입 자리가 잘못 자란 아가미 흉터. 눈은 발광이 꺼진 흐린 흰색
   표식  개조 봉합선 — 가슴 세로 시침질

  다섯 다 가슴 로고·문장 없다. 정체성은 재단·표식·볏 실루엣.
  악센트 금속은 «하»의 견장(산호빛, 금속 아님)과 «울지 않는 것»의 철 밴드뿐 —
  나머지 셋은 금속을 가질 수 없는 처지다(도망친 것들이다).
"""
import pathlib
import sys
import zlib

# ★스킬 본체는 심볼릭 링크 뒤에 있다(lessons.md 23장). 추적되는 레포 경로를 먼저 본다.
for _cand in (pathlib.Path(__file__).resolve().parents[1]
              / '.claude/skills/npc-skin-forge/scripts',
              pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'):
    if _cand.is_dir():
        sys.path.insert(0, str(_cand))
        break
else:
    raise SystemExit('npc-skin-forge/scripts 를 찾을 수 없다')

import garments as g                                  # noqa: E402
from skinlib import Skin, ramp, ramp_lit, mix         # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
LIMBS = ('arm_r', 'arm_l', 'leg_r', 'leg_l')


def _seed(name):
    """★hash() 금지 — 프로세스마다 랜덤 시드가 달라 빌드가 비결정적이 된다(lessons 12)."""
    return zlib.crc32(name.encode()) % 100000


def matte(base, spread=0.22):
    """무광 직물 — 색상 회전 0(lessons 19)."""
    return ramp(base, spread=spread, hue=0.0, sat=0.03)


def leather(base, spread=0.34):
    return ramp(base, spread=spread, hue=0.02, sat=0.06)


def glowramp(base, spread=0.35):
    """발광 홍채 램프. ★`ramp_lit` 을 쓰면 안 된다 — sat_lift 가 «거의 흰 청록»의 색상을
    돌려 **형광 연두**(bff0ff → d8fa25)로 만든다(1패스 일곱-셋의 눈이 네온이 된 원인).
    발광체는 색상이 돌면 안 되므로 hue 회전 0 으로 뽑는다."""
    return ramp(base, spread=spread, hue=0.0, sat=0.05)


def scaleskin(base, spread=0.30):
    """비늘 피부 — 젖어 있으니 무광 천보다는 반사하지만 금속은 아니다."""
    return ramp(base, spread=spread, hue=0.03, sat=0.08)


# ══ 종족 공통 =================================================================
def _eye_guard(s, eye_y, who):
    """★lessons 13 — 볏·붕대를 다 그린 «뒤에» 둬야 의미가 있다."""
    f = s.f('head', 'front')
    if sum(1 for x in (1, 2, 5, 6) if max(f.get(x, eye_y)[:3]) > 150) < 2:
        raise ValueError('%s: 눈이 지워졌다 (eye_y=%d)' % (who, eye_y))


def _body_skin(s, r, seed):
    """맨몸 채우기 — base 6면 전부 불투명. ★bottom 을 빼먹으면 인게임에서 구멍이 뚫린다."""
    for part in ('body',) + LIMBS:
        s.form_fill(part, r, 0, None, base_idx=3, top=True, bottom=True)
        s.shade_col_falloff(part, r, 0, 11)


def _scales(s, r, seed, parts=('head', 'body') + LIMBS):
    """비늘 결 — **대각 격자**. 세로 반복은 다리를 줄무늬 바지로 만든다(lessons 5-3).

    speckle 만 쓰면 «먼지»로 읽히고, 격자만 쓰면 «그물»로 읽힌다. 둘을 겹쳐야
    «비늘»이 된다 — 격자가 결을 만들고 speckle 이 그 결을 흐트러뜨린다.
    """
    for part in parts:
        h = 8 if part == 'head' else 12
        y0 = 4 if part == 'head' else 0          # 얼굴 위쪽은 이마·눈 자리라 건드리지 않는다
        for fname in ('front', 'back', 'right', 'left'):
            f = s.f(part, fname)
            for y in range(y0, h):
                for x in range(f.w):
                    if (x * 2 + y) % 5 == 0 and f.get(x, y)[3]:
                        f.px(x, y, mix(f.get(x, y), r[1], 0.30))
                    elif (x * 2 + y) % 5 == 2 and f.get(x, y)[3]:
                        f.px(x, y, mix(f.get(x, y), r[4], 0.18))
        s.speckle(part, r, y0, h - 1, density=0.05, seed=seed,
                  faces=('front', 'back', 'right', 'left'))


def _gills(s, r, seed, rows=(3, 5, 7)):
    """목 아가미 — 머리 옆면 아래 + 몸통 옆면 위로 이어진다.

    ★1패스는 (5,6,7) 연속 3행을 어둡게 칠했더니 «턱 밑의 검은 얼룩»이 됐다.
      슬릿이 슬릿으로 읽히려면 **어두운 줄 위에 밝은 줄**이 있어야 한다 — 살이 접혀
      들린 자리다. 그래서 한 줄 띄어 3줄로 놓고 바로 위 행에 하이라이트를 준다.
    ★한쪽 면에만 그리면 «얼굴의 흠집»이다. 머리 옆 → 몸통 옆으로 이어져야
      «목을 감은 기관»으로 읽힌다.
    """
    dark = mix(r[1], (0, 0, 0, 255), 0.45)
    for fname in ('right', 'left'):
        f = s.f('head', fname)
        for y in rows:
            if y - 1 >= 0:
                f.rect(1, y - 1, 4, y - 1, r[4])          # 들린 살 = 하이라이트
            f.rect(1, y, 4, y, dark)                       # 슬릿
            f.px(0, y, mix(f.get(0, y), dark, 0.5))        # 얼굴쪽으로 반 칸 물린다
        b = s.f('body', fname)
        for y in (0, 2):
            b.rect(0, y, 3, y, dark)
            if y + 1 < 12:
                b.rect(0, y + 1, 3, y + 1, r[4])


def _crest(s, r, height=3, width=(2, 5), back=3, front=2, layer='outer'):
    """등볏 — 정수리 outer 에 얹어 **머리통 밖으로** 부피를 준다(lessons 3).

    base 에 칠하면 머리가 깎이고, outer 에 얹으면 실루엣이 실제로 커진다.
    ★1패스는 top·back 에만 얹었다 — NPC 는 lookclose 로 **늘 플레이어를 마주보므로**
      정면에서 안 보이는 볏은 없는 것과 같다(여성 긴 머리에서 똑같이 틀렸던 실수,
      lessons 3). `front` 행만큼 이마 위 outer 에도 얹어 정면 실루엣을 만든다.
    """
    top = s.f('head', 'top', layer)
    x0, x1 = width
    top.rect(x0, 0, x1, 7, r[3])
    for x in range(x0, x1 + 1):                    # 볏의 결 — 세로 갈래
        if (x - x0) % 2 == 0:
            top.col(x, r[4], 0, 7)
    bk = s.f('head', 'back', layer)
    bk.rect(x0, 0, x1, back - 1, r[3])
    for x in range(x0, x1 + 1):
        if (x - x0) % 2 == 0:
            bk.col(x, r[2], 0, back - 1)
    for fname in ('right', 'left'):                # 옆에서 봐도 볏이 보이게 한 열만
        f = s.f('head', fname, layer)
        f.rect(2, 0, 3, height - 1, r[2])
    fr = s.f('head', 'front', layer)               # ★정면 볏 — 이마 위로 솟은 능선
    for x in range(x0, x1 + 1):
        for y in range(front):
            fr.px(x, y, r[4] if (x - x0) % 2 == 0 else r[2])
    if front >= 2:                                 # 능선 밑 그림자 = 이마와 분리
        #   ★1행짜리 볏(비늘 짜는 이·일곱-셋)에 이걸 넣으면 그림자가 볏을 통째로 먹어
        #     이마 한가운데 «검은 구멍»이 된다(2패스 실측). 2행 이상일 때만 판다.
        fr.rect(x0, front, x1, front, mix(r[1], (0, 0, 0, 255), 0.18))


def _armfin(s, part, r, y0=4, y1=8):
    """팔뚝 바깥 지느러미 — 종족 표식. outer 에 얹어 «붙어 있는 것»으로 보이게."""
    fname = 'right' if part == 'arm_r' else 'left'
    f = s.f(part, fname, 'outer')
    for i, y in enumerate(range(y0, y1 + 1)):
        w = 1 if i % 2 else 2
        f.rect(0, y, w - 1, y, r[3] if i % 2 else r[2])


def _fish_eyes(s, y, socket, glow, dim=False):
    """심해어 눈 — 어두운 눈구멍 + 창백한 발광 홍채(인간 공식의 반대).

    ★_eye_guard 는 x1·x2·x5·x6 중 «두 칸»이 밝기를 요구한다. 발광 홍채를 x2·x5(안쪽)에
      두면 그 둘이 밝은 칸이 된다 — 인간 스킨의 «흰자»가 하던 역할을 홍채가 대신한다.
    """
    f = s.f('head', 'front')
    for x in (1, 2, 5, 6):                          # 눈구멍 2행 — 크고 어둡게
        f.px(x, y, socket)
        f.px(x, y + 1, mix(socket, (0, 0, 0, 255), 0.25))
    for x in (2, 5):                                # 발광 홍채는 «안쪽»(gaze=0 과 같은 배치)
        #   ★dim 을 [2]/[1] 로 뒀더니 «눈이 없는 얼굴»이 됐다 — 빛이 꺼진 것과 눈이
        #     안 보이는 것은 다르다. 한 단씩 올려 형태는 남기고 광량만 줄인다.
        f.px(x, y, glow[4] if not dim else glow[3])
        f.px(x, y + 1, glow[3] if not dim else glow[2])
    for x in (1, 6):                                # 눈구멍 바깥은 한 단 더 깊게
        f.px(x, y + 1, mix(socket, (0, 0, 0, 255), 0.40))


def _fish_face(s, r, eye_y=4, mouth_y=7, mouth_w=4):
    """어류 얼굴 — 눈두덩 능선 + 콧구멍 슬릿 + 넓고 얇은 입.

    ★1패스는 눈 말고 아무것도 없어서 «민무늬 가면»으로 읽혔다. 사람 얼굴의 코·입술을
      그대로 쓸 수는 없으니(어류다) 대응물을 놓는다: 눈두덩(눈 위 능선) · 콧구멍 2px ·
      입은 «넓고 얇게»(사람 입은 좁고 두껍다 — 이 차이만으로도 종이 갈린다).
    """
    f = s.f('head', 'front')
    for x in range(1, 7):                                   # 눈두덩 능선
        f.px(x, eye_y - 1, mix(f.get(x, eye_y - 1), r[4], 0.55))
    f.px(0, eye_y - 1, r[2]); f.px(7, eye_y - 1, r[2])
    for x in (3, 4):                                        # 콧구멍 슬릿
        f.px(x, mouth_y - 1, mix(f.get(x, mouth_y - 1), r[0], 0.45))
    if not mouth_w:                                         # 입이 없는 개체(울지 않는 것)
        return
    x0 = (8 - mouth_w) // 2                                 # 넓고 얇은 입
    f.rect(x0, mouth_y, x0 + mouth_w - 1, mouth_y, mix(r[1], (0, 0, 0, 255), 0.20))
    f.px(x0, mouth_y, r[1]); f.px(x0 + mouth_w - 1, mouth_y, r[1])


def _legfin(s, part, r, y0=6, y1=10):
    """종아리 지느러미 — 맨다리가 4x12 민짜 기둥이 되지 않게 하는 유일한 장치."""
    fname = 'right' if part == 'leg_r' else 'left'
    f = s.f(part, fname, 'outer')
    for i, y in enumerate(range(y0, y1 + 1)):
        w = 2 if i % 2 else 1
        f.rect(0, y, w - 1, y, r[4] if i % 2 else r[2])


def _brand(s, part, face, marks, color, layer='outer'):
    """비늘에 새긴 번호 낙인 / 흉터. ★4px 이하 — 가슴 로고는 금지 규칙이다."""
    f = s.f(part, face, layer)
    for (x, y) in marks:
        f.px(x, y, color)


def _finish(s, path):
    """★micro_light 를 먼저 돌리고 저장한다 — save() 가 자동 호출하므로 후처리를
    넣고 싶으면 여기서 플래그를 세워야 한다(lessons 19)."""
    s.micro_light()
    s._microed = True
    OUT.mkdir(exist_ok=True)
    return s.save(path)


# ══ 1. 모르 209 — 촌장 =========================================================
def build_mor():
    name, SEED = 'mor', _seed('mor')
    P = dict(
        skin=scaleskin('2f5a58'),                   # 짙은 청록 — 세트에서 가장 어둡다
        glow=glowramp('9fe0d2'),                    # 발광 청록
        cloak=matte('7e8b78', 0.24),                # ★1패스 3c4a3e 는 피부와 값이 붙어
        #                                             전신이 «청록 기둥» 하나로 읽혔다
        strap=leather('4a3b2c'),
        scar=ramp('b9a58c'),                        # 비늘째 뜯어낸 자리 = 밝은 흉터
    )
    s = Skin()
    g.head_base(s, P['skin'], seed=SEED)
    _body_skin(s, P['skin'], SEED)
    _scales(s, P['skin'], SEED)
    _gills(s, P['skin'], SEED)
    _crest(s, P['skin'], height=3, width=(1, 6), back=3, front=2)   # 넓고 낮은 볏 = 관(冠)
    g.face_shape(s, P['skin'], jaw='square', temple=True)
    _fish_eyes(s, 4, mix(P['skin'][0], (0, 0, 0, 255), 0.45), P['glow'])
    _fish_face(s, P['skin'], eye_y=4, mouth_y=7, mouth_w=6)   # 촌장 = 가장 넓은 입
    _eye_guard(s, 4, name)

    #   어깨 비늘 망토 — 앞뒤 + 어깨 top 까지 이어야 «걸친 것»이 된다
    g.mantle(s, P['cloak'], front=5, back=10, layer='outer', seed=SEED,
             clasp=P['scar'])                              # 잠금쇠 = 뼈. 금속을 가질 수 없다
    #   ★망토도 «비늘로 짠 것»이다 — 민짜 판이면 그냥 천이고, 촌장의 권위가 안 선다.
    for fname in ('front', 'back', 'right', 'left'):
        mf = s.f('body', fname, 'outer')
        for y in range(0, 11):
            for x in range(mf.w):
                if mf.get(x, y)[3] and (x * 2 + y) % 5 == 0:
                    mf.px(x, y, mix(mf.get(x, y), P['cloak'][1], 0.35))
                elif mf.get(x, y)[3] and (x * 2 + y) % 5 == 2:
                    mf.px(x, y, mix(mf.get(x, y), P['cloak'][4], 0.20))
    g.belt(s, P['strap'], y=8, layer='outer', ao=False)
    for part in ('arm_r', 'arm_l'):
        _armfin(s, part, P['skin'])
    for part in ('leg_r', 'leg_l'):
        _legfin(s, part, P['skin'])
    #   ★지워진 번호 — 왼팔 바깥. 비늘째 뜯겨 색이 빠진 자리
    _brand(s, 'arm_l', 'left', [(1, 2), (2, 2), (1, 3), (3, 3)], P['scar'][3])
    _brand(s, 'arm_l', 'left', [(2, 3)], P['scar'][1])
    return _finish(s, str(OUT / ('ds_%s.png' % name)))


# ══ 2. 비늘 짜는 이 210 — 손일하는 자 ==========================================
def build_weaver():
    name, SEED = 'weaver', _seed('weaver')
    P = dict(
        skin=scaleskin('4a5748'),                   # 자갈빛 갈청 — 유일한 «녹슨» 계열
        glow=glowramp('e0c98a'),                    # ★세트에서 유일한 «따뜻한» 눈 = 작업등
        apron=matte('9a917c', 0.22),                # 뼈빛 비늘 앞치마 = 세트의 밝은 옷 슬롯
        thread=matte('c2b9a4', 0.20),
        strap=leather('43372a'),
    )
    s = Skin()
    g.head_base(s, P['skin'], seed=SEED)
    _body_skin(s, P['skin'], SEED)
    _scales(s, P['skin'], SEED)
    _gills(s, P['skin'], SEED)
    _crest(s, P['skin'], height=2, width=(3, 4), back=2, front=1)  # 뒤로 눕힌 낮은 볏
    for fname in ('right', 'left'):                        # 옆으로 늘어진 뺨 지느러미
        f = s.f('head', fname, 'outer')
        f.rect(0, 4, 1, 6, P['skin'][2])
        f.px(0, 5, P['skin'][3])
    g.face_shape(s, P['skin'], jaw='round', temple=True)
    _fish_eyes(s, 4, mix(P['skin'][0], (0, 0, 0, 255), 0.45), P['glow'])
    _fish_face(s, P['skin'], eye_y=4, mouth_y=7, mouth_w=4)
    _eye_guard(s, 4, name)

    g.apron(s, P['apron'], bib=(2, 5), bib_y=(1, 5), waist=6, hem=11,
            wrap=2, straps=True, tie=True, seed=SEED)
    #   ★앞치마도 «비늘로 짠 것»이다 — 민짜 뼈빛 판이면 그냥 캔버스 앞치마다
    af = s.f('body', 'front', 'outer')
    for y in range(1, 12):
        for x in range(8):
            if af.get(x, y)[3] and (x * 2 + y) % 5 == 0:
                af.px(x, y, mix(af.get(x, y), P['apron'][1], 0.35))
    g.pouch(s, P['strap'], part='leg_l', face='front', x=1, y=1, w=2, h=3)
    for part in ('arm_r', 'arm_l'):
        _armfin(s, part, P['skin'])
    for part in ('leg_r', 'leg_l'):
        _legfin(s, part, P['skin'])
    #   ★번호를 «가린» 사람 — 오른팔에 실을 감았다(지운 모르와 짝)
    f = s.f('arm_r', 'right', 'outer')
    for y in (2, 3, 4):
        f.rect(0, y, 3, y, P['thread'][3] if y % 2 else P['thread'][2])
    return _finish(s, str(OUT / ('ds_%s.png' % name)))


# ══ 3. 일곱-셋 211 — 어린 개체 =================================================
def build_seven3():
    name, SEED = 'seven3', _seed('seven3')
    P = dict(
        skin=scaleskin('6d92a0'),                   # 창백한 연청 — 세트에서 가장 밝고 어리다
        glow=glowramp('bff0ff'),
        wrap=matte('5b6b63', 0.22),                 # 허리 천 조각
        brand=ramp('a8927a'),   # ★1패스 d8c9a8 은 가슴의 흰 얼룩이 됐다
    )
    s = Skin()
    g.head_base(s, P['skin'], seed=SEED)
    _body_skin(s, P['skin'], SEED)
    _scales(s, P['skin'], SEED)
    _gills(s, P['skin'], SEED)
    _crest(s, P['skin'], height=2, width=(3, 4), back=2, front=1)  # 아직 덜 자란 볏
    g.face_shape(s, P['skin'], jaw='round')
    _fish_eyes(s, 4, mix(P['skin'][0], (0, 0, 0, 255), 0.40), P['glow'])
    _fish_face(s, P['skin'], eye_y=4, mouth_y=7, mouth_w=3)   # 어린 개체 = 작은 입
    _eye_guard(s, 4, name)

    #   ★옷이 «거의» 없다 — 허리 천 한 겹 + 어깨 한쪽 끈(비대칭)
    s.form_fill('body', P['wrap'], 7, 11, layer='outer', base_idx=3)
    s.hem('body', 11, P['wrap'], layer='outer', base_idx=3)
    #   ★1패스는 세로 한 열이라 «가슴에 꽂힌 막대»로 읽혔다 — 어깨에서 허리로 «비스듬히»
    #     내려와야 천으로 읽힌다. 어깨(top)와 등까지 이어야 끈이 끊기지 않는다.
    fb = s.f('body', 'front', 'outer')
    for i, y in enumerate(range(0, 7)):
        x = min(6, 1 + i)
        fb.px(x, y, P['wrap'][3])
        fb.px(min(7, x + 1), y, P['wrap'][2])
    s.f('body', 'top', 'outer').rect(1, 0, 2, 3, P['wrap'][2])
    bb = s.f('body', 'back', 'outer')
    for i, y in enumerate(range(0, 7)):
        bb.px(max(1, 6 - i), y, P['wrap'][2])
    for part in ('arm_r', 'arm_l'):
        _armfin(s, part, P['skin'], y0=5, y1=8)
    #   ★아직 «남아 있는» 번호 — 가슴 오른쪽 낙인(모르의 흉터와 짝)
    _brand(s, 'body', 'front', [(5, 3), (6, 3), (5, 4), (6, 5)], P['brand'][3],
           layer='base')
    _brand(s, 'body', 'front', [(6, 4)], P['brand'][1], layer='base')
    return _finish(s, str(OUT / ('ds_%s.png' % name)))


# ══ 4. 가라앉은 하 212 — 옛 파수 ===============================================
def build_ha():
    name, SEED = 'ha', _seed('ha')
    P = dict(
        skin=scaleskin('56666b', 0.26),             # 납빛 회청 — 백 해를 서 있어 바랬다
        glow=glowramp('9ab6bd'),                    # 흐린 발광(백내장)
        robe=matte('1e4448', 0.24),                 # ★1패스 2c5f63 은 피부와 값이 붙었다
        coral=matte('c9b98a', 0.22),                # 산호빛 견장 — 금속이 아니다
    )
    s = Skin()
    g.head_base(s, P['skin'], seed=SEED)
    _body_skin(s, P['skin'], SEED)
    _scales(s, P['skin'], SEED)
    _gills(s, P['skin'], SEED)
    _crest(s, P['skin'], height=4, width=(2, 5), back=5, front=3)  # 가장 높은 볏 = 관모
    g.face_shape(s, P['skin'], jaw='square', temple=True)
    g.wrinkles(s, P['skin'], brow_y=2, crow=True, forehead=True)   # 백 해의 나이
    _fish_eyes(s, 4, mix(P['skin'][0], (0, 0, 0, 255), 0.45), P['glow'], dim=True)
    _fish_face(s, P['skin'], eye_y=4, mouth_y=7, mouth_w=4)
    _eye_guard(s, 4, name)

    #   유일한 «제복» — 재단이 갖춰져 있다(가슴 세로 트임 + 견장)
    g.tunic(s, P['robe'], y0=1, y1=11, collar=True, layer='outer', seed=SEED,
            fold_cols=(2, 5), grain=0.06)
    g.placket(s, P['coral'], x=(3, 4), y0=2, y1=9, layer='outer')
    for fname in ('front', 'back'):                        # 견장 — 어깨 2행
        f = s.f('body', fname, 'outer')
        f.rect(0, 0, 1, 1, P['coral'][3])
        f.rect(6, 0, 7, 1, P['coral'][2])
    s.f('body', 'top', 'outer').rect(0, 0, 1, 3, P['coral'][3])
    s.f('body', 'top', 'outer').rect(6, 0, 7, 3, P['coral'][2])
    g.sleeves(s, P['robe'], y0=0, y1=6, seed=SEED, grain=0.06, layer='outer')
    for part in ('arm_r', 'arm_l'):
        _armfin(s, part, P['skin'], y0=7, y1=10)
    for part in ('leg_r', 'leg_l'):
        _legfin(s, part, P['skin'])
    #   목의 옛 교단 링 — 번호가 아니라 «자리»의 표식
    for fname in ('front', 'back', 'right', 'left'):
        s.f('body', fname, 'outer').row(0, P['coral'][1], 2, 5)
    return _finish(s, str(OUT / ('ds_%s.png' % name)))


# ══ 5. 울지 않는 것 213 — 개조되다 만 개체 =====================================
def build_mute():
    name, SEED = 'mute', _seed('mute')
    P = dict(
        skin=scaleskin('8c7f80', 0.26),             # ★유일하게 «바다색»이 아니다
        glow=glowramp('b9b2ad'),                        # 빛이 꺼진 눈
        wrap=matte('a89f8c', 0.20),                 # 낡은 붕대
        iron=ramp_lit('7d7a75'),                    # 수조 기구의 잔재
    )
    s = Skin()
    g.head_base(s, P['skin'], seed=SEED)
    _body_skin(s, P['skin'], SEED)
    _scales(s, P['skin'], SEED)
    _gills(s, P['skin'], SEED, rows=(5, 6))                # 아가미도 두 줄뿐 — 잘못 자랐다
    #   ★볏이 «없다» — 잘려 나간 밑동만 남았다. 다른 넷과 실루엣이 근본적으로 갈린다
    top = s.f('head', 'top', 'outer')
    for x in range(2, 6):
        top.px(x, 3, mix(P['skin'][1], (0, 0, 0, 255), 0.35))
        top.px(x, 4, mix(P['skin'][2], (0, 0, 0, 255), 0.20))
    fr = s.f('head', 'front', 'outer')          # ★정면에서도 «없다»가 보여야 한다
    for x in range(2, 6):                       #   — 다른 넷은 여기에 볏이 솟아 있다
        fr.px(x, 0, mix(P['skin'][1], (0, 0, 0, 255), 0.40))
    g.face_shape(s, P['skin'], jaw='round')
    _fish_eyes(s, 4, mix(P['skin'][0], (0, 0, 0, 255), 0.35), P['glow'], dim=True)
    #   ★입이 없다 — 입 자리가 잘못 자란 아가미 흉터(세로 3줄)
    #   2패스 실측: 비늘 격자 + 흉터가 겹쳐 아래 얼굴이 «얼룩 죽»이 됐다.
    #   슬릿이 읽히려면 먼저 «평평한 바탕»을 만들어야 한다.
    _fish_face(s, P['skin'], eye_y=4, mouth_y=7, mouth_w=0)   # 눈두덩만, 입은 없다
    hf = s.f('head', 'front')
    hf.rect(1, 6, 6, 7, P['skin'][3])
    for x in (2, 4, 6):
        hf.px(x, 6, mix(P['skin'][1], (0, 0, 0, 255), 0.35))
        hf.px(x, 7, mix(P['skin'][1], (0, 0, 0, 255), 0.20))
    for x in (1, 3, 5):                                    # 슬릿 사이 살은 밝게
        hf.px(x, 6, P['skin'][4])
    _eye_guard(s, 4, name)

    #   몸에 감긴 낡은 붕대 — strip 으로 «감아야» 한 줄로 이어진다(4면 개별 fill 금지)
    ring = s.strip('body', 'outer')
    for y in (3, 4, 8, 9):
        ring.band(y, y, P['wrap'][3] if y % 2 else P['wrap'][2])
    for y in (5, 6):                                       # 성기게 감긴 구간
        for x in range(0, 32, 3):
            ring.px(x, y, P['wrap'][2])
    s.stitch('body', 7, P['wrap'], layer='outer', base_idx=1)   # 개조 봉합선
    _legfin(s, 'leg_l', P['skin'])                         # ★지느러미도 한쪽만 남았다
    for part in ('arm_r', 'arm_l'):                        # 팔 붕대(한쪽만 = 비대칭)
        if part == 'arm_r':
            for y in (4, 5):
                for fname in ('front', 'back', 'right', 'left'):
                    s.f(part, fname, 'outer').row(y, P['wrap'][3], 0, 3)
    #   목의 철 구속 밴드
    for fname in ('front', 'back', 'right', 'left'):
        s.f('body', fname, 'outer').row(0, P['iron'][2], 1, 6)
    s.f('body', 'front', 'outer').px(3, 0, P['iron'][4])
    return _finish(s, str(OUT / ('ds_%s.png' % name)))


ROSTER = (
    ('모르', 209, build_mor),
    ('비늘 짜는 이', 210, build_weaver),
    ('일곱-셋', 211, build_seven3),
    ('가라앉은 하', 212, build_ha),
    ('울지 않는 것', 213, build_mute),
)

if __name__ == '__main__':
    for nm, cid, fn in ROSTER:
        print('%-12s cid%-4d %s' % (nm, cid, fn()))
