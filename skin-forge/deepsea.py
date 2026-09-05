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

═══ 2패스 전면 재제작 (2026-09-06, 오너 지적: "물고기 npc의 느낌을 못살림") ═══
1패스는 «청록으로 칠한 사람»이었다. 실측으로 원인을 셋 짚었다:

  ① **역광음영(countershading)이 없었다 — 이게 1순위 실패.** 어류가 어류로 읽히는 가장
     큰 단서는 «등이 어둡고 배가 하얗다»인데, 몸통 앞뒤 밝기차가 **10**밖에 없었다
     (면 조명 기본 오프셋 그대로 = 아무 처리도 안 한 것). 지금은 **+30**.
     ★+44 까지 밀어 봤고 **되돌렸다** — 배가 «하얀 판»이 되고 비늘·배비늘이 전부 날아가
       전신이 뿌예졌다(렌더 실측). 이 해상도에서 쓸 수 있는 상한이 대략 +30~35 다.
  ② **겉레이어가 실루엣을 안 만들었다.** 볏이 정수리에 얹힌 «얇은 판»이라 인게임 배율에서
     사라졌다. 고친 건 **점유율이 아니라 프로필**이다 — 옆에서 봤을 때 앞이 낮고 가운데~뒤가
     높은 «돛» 곡선. (head.outer 점유율은 지금도 20~42% 로 캐릭터마다 다르다. 비늘 짜는 이·
     일곱-셋은 **설계상** 볏이 낮다 — 그 둘의 낮은 수치는 결함이 아니다.)
  ③ **얼굴이 사람 배치였다.** 눈이 x1~x6 안쪽 2px. 물고기 눈은 **머리 옆에 크게 붙어**
     있고 그게 «사람이 아니다»를 한 번에 만든다.

SPECIES KIT — 다섯 전부에 같은 순서로 적용한다 (`_species()` 한 함수가 권위)
  1. `_countershade`  등(back)→배(front) 연속 그라데이션. 옆면은 **뒤→앞** 방향으로
     보간한다(Strip 언랩이 right→front→left→back 이므로 right 는 x=마지막이 앞,
     left 는 x=0 이 앞이다 — 이걸 뒤집으면 명암이 좌우로 갈라진다).
     세로 계수를 곱해 «아래로 갈수록 더 하얀 배»를 만든다. 목표 등배차 60~90.
  2. `_scales`        어긋난 벽돌 격자(2px 주기 half-offset). 1패스의 대각선은
     «비늘»이 아니라 «빗금»으로 읽혔다.
  3. `_belly_plates`  배비늘(腹鱗) — 배 쪽 **가로** 띠. 세로는 금지(lessons 5-3).
  4. `_lateral_line`  ★측선. 몸통 옆면을 앞뒤로 가로지르는 점선. 물고기에만 있는 기관이라
     하나만으로도 종이 갈린다. 허리띠로 안 읽히게 **y=4(가슴 높이)** 에 점선으로.
  5. `_gills`         아가미 — 어두운 슬릿 + 들린 살 하이라이트, 머리 옆→몸통 옆 연속.
  6. `_fish_eyes`     ★**측면 눈**. 소켓 3px(x0~x2 / x5~x7) 2행 + 홍채는 **바깥**(x1·x6).
     사람 기본값 `gaze=0`(안쪽)을 일부러 어긴다 — 어류의 눈은 측면에 있고, 그 배치가
     정면 8x8 에서 «사람 아님»을 만드는 가장 싼 수단이다. 소켓은 **머리 옆면까지
     감싸서** 옆에서도 눈이 튀어나온 것으로 보이게 한다.
  7. `_dorsal`        ★**등지느러미**(오너 요청). 정수리 볏 → 뒤통수 → 등 척추선까지
     **한 줄로 이어진다.** 능선 중앙 2열이 밝고 양옆이 어둡고 그 바깥에 그림자 —
     정면·뒤·옆 세 방향에서 전부 능선으로 읽힌다. 옆면은 몸통 겉레이어의 **뒤쪽 끝 열**
     에 얹어 실루엣 가장자리를 만든다.
     ★★한계 고지: 바닐라 스킨은 **상자 표면 텍스처**다. 겉레이어는 머리 0.5px·몸통
       0.25px 부풀림뿐이라 **진짜로 튀어나온 지느러미는 불가능하다.** 여기서 하는 건
       «능선으로 읽히게 칠하는 것»이 한계다. 진짜 3D 지느러미가 필요하면 BetterModel
       커스텀 모델이나 CraftEngine 헬멧 경로 — 별개 작업이다.
  8. `_finray`        팔뚝·종아리 지느러미. 1패스 1~2px → **살(ray) 줄무늬 + 톱니 뒷단**.

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
│  추가  ★수염 대신 **입가 수염돌기(barbel)** 2가닥 — 늙은 저서어의 표식. 하만 가진다
└ 울지 않는 것 213 — 수조에서 «그릇»으로 개조되다 만 개체. 소리를 못 낸다. &f 대화 전용
   피부  병약한 창백 회분홍 8c7f80 ★네 명의 «바다색»에서 유일하게 벗어난다 —
         그 이탈 자체가 「개조되다 만」의 시각적 근거다
   볏    ★없다. **잘려 나간 밑동**만 남았다(2px 어두운 자국). 등지느러미도 **중간에서
         끊긴다** — 척추선을 따라가다 뚝 끊긴 흉터로 끝난다(다른 넷은 이어진다)
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

import garments as g                                        # noqa: E402
from skinlib import PARTS, SIDES, Skin, ramp, ramp_lit, mix, rgba  # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
LIMBS = ('arm_r', 'arm_l', 'leg_r', 'leg_l')
BLACK = (0, 0, 0, 255)


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


def _at(r, f):
    """램프의 연속 보간 — 역광음영은 5단 계단이 아니라 그라데이션이어야 한다."""
    f = max(0.0, min(4.0, f))
    i = int(f)
    return mix(r[i], r[min(4, i + 1)], f - i)


# ══ 종족 공통 =================================================================
def _eye_guard(s, eye_y, who):
    """★lessons 13 — 볏·붕대를 다 그린 «뒤에» 둬야 의미가 있다."""
    f = s.f('head', 'front')
    if sum(1 for x in (1, 2, 5, 6) if max(f.get(x, eye_y)[:3]) > 150) < 2:
        raise ValueError('%s: 눈이 지워졌다 (eye_y=%d)' % (who, eye_y))


def _body_skin(s, r):
    """맨몸 채우기 — base 6면 전부 불투명. ★bottom 을 빼먹으면 인게임에서 구멍이 뚫린다."""
    for part in ('body',) + LIMBS:
        s.form_fill(part, r, 0, None, base_idx=3, top=True, bottom=True)


def _frontness(part, fname, x):
    """이 픽셀이 «배 쪽»에 얼마나 가까운가 (0=등, 1=배).

    ★Strip 언랩은 right → front → left → back 순서로 **연속**이다. 그래서
      right 면은 마지막 열이 앞(front 면과 맞닿는 쪽), left 면은 **첫 열**이 앞이다.
      이걸 뒤집으면 역광음영이 좌우로 갈라져 «반쪽만 하얀 몸»이 된다.
    """
    d = PARTS[part]['d']
    if fname == 'front':
        return 1.0
    if fname == 'back':
        return 0.06
    if fname == 'top':
        return 0.0
    if fname == 'bottom':
        return 1.0
    t = x / max(1, d - 1)
    return t if fname == 'right' else 1.0 - t


def _countershade(s, base_hex, parts=('head', 'body') + LIMBS, amount=0.60):
    """★어류의 1순위 신호 — 등은 어둡고 배는 하얗다.

    1패스 실측: 몸통 앞/뒤 평균 밝기차가 **10**(면 조명 기본 오프셋 그대로 = 미처리).
    실제 어류 도색은 60~90 이 난다. 이 함수 하나가 «청록 사람»과 «물고기»를 가른다.

    ★목표색을 피부 램프에서 뽑으면 안 된다(2패스 1차 실패, 결과 +15). `scaleskin` 의
      spread 0.30 은 5색 폭이 54밖에 안 돼 **가능한 최대 대비가 애초에 없다.** 램프는
      «한 재질의 조명»이고 역광음영은 «도색»이라 축이 다르다 → 전용 색쌍을 따로 만든다.
      배는 밝기만 올리는 게 아니라 **채도도 빠져야** 한다(물고기 배는 창백하다).

    세로 계수를 곱하는 이유: 물고기 배는 아래로 갈수록 더 하얗다. 머리는 곡선을 따로
    쓴다 — 이마 0.05 → 턱 1.0 이라야 **눈두덩이 어두운 띠**가 되어 어류 얼굴이 된다.
    """
    dorsal = mix(base_hex, BLACK, 0.45)
    belly = mix(base_hex, (238, 242, 240, 255), 0.62)
    mid = rgba(base_hex)

    def target(t):
        return mix(dorsal, mid, t * 2) if t < 0.5 else mix(mid, belly, (t - 0.5) * 2)

    for part in parts:
        head = part == 'head'
        for fname in SIDES + ('top', 'bottom'):
            f = s.f(part, fname)
            hh = max(1, f.h - 1)
            for y in range(f.h):
                if fname not in SIDES:
                    v = 0.5
                elif head:
                    v = 0.05 + 0.95 * (y / hh)
                else:
                    v = 0.25 + 0.75 * (y / hh)
                for x in range(f.w):
                    c = f.get(x, y)
                    if not c[3]:
                        continue
                    f.px(x, y, mix(c, target(_frontness(part, fname, x) * v), amount))


def _scales(s, r, seed, parts=('head', 'body') + LIMBS):
    """비늘 결 — **어긋난 벽돌 격자**.

    ★1패스는 `(x*2+y)%5` 대각선이었다. 대각선은 «비늘»이 아니라 «빗금»으로 읽힌다.
      비늘은 한 줄씩 어긋난 반원 배열이다 — 2px 주기 + 행마다 half-offset 이 그 최소형이고,
      각 비늘의 «아래 테두리»만 어둡게 하고 그 위 칸을 살짝 밝히면 겹쳐진 판으로 보인다.
    ★세로 반복은 금지(lessons 5-3, 다리가 줄무늬 바지가 된다) — half-offset 이 그걸 막는다.
    """
    for part in parts:
        h = 8 if part == 'head' else 12
        y0 = 4 if part == 'head' else 0      # 얼굴 위쪽은 이마·눈 자리라 건드리지 않는다
        for fname in SIDES:
            if part == 'head' and fname == 'front':
                continue        # ★얼굴 앞면 제외 — 눈·입 위에 격자가 겹치면 얼룩 죽이 된다
            f = s.f(part, fname)
            for y in range(y0, min(h, f.h)):
                off = 0 if (y % 4) < 2 else 2
                for x in range(f.w):
                    c = f.get(x, y)
                    if not c[3]:
                        continue
                    if (x + off) % 4 == 0:                 # 비늘 아래 테두리
                        f.px(x, y, mix(c, r[0], 0.30))
                    elif (x + off) % 4 == 1:               # 그 판의 배부른 쪽
                        f.px(x, y, mix(c, r[4], 0.20))
        faces = tuple(f for f in SIDES if not (part == 'head' and f == 'front'))
        s.speckle(part, r, y0, h - 1, density=0.04, seed=seed, faces=faces)


def _belly_plates(s, r, part='body', y0=5, y1=11, span=(1, 6)):
    """배비늘(腹鱗) — 배 쪽 **가로** 띠. 사람 배엔 없는 것이라 종을 가른다.

    ★가로여야 한다. 세로 반복은 다리를 줄무늬 바지로 만든다(lessons 5-3).
    """
    f = s.f(part, 'front')
    for y in range(y0, y1 + 1, 2):
        for x in range(span[0], span[1] + 1):
            c = f.get(x, y)
            if c[3]:
                f.px(x, y, mix(c, r[1], 0.26))
            c = f.get(x, y - 1)
            if y - 1 >= y0 and c[3]:
                f.px(x, y - 1, mix(c, r[4], 0.22))


def _lateral_line(s, r, y=4, parts=('body',)):
    """★측선(側線) — 물고기에만 있는 감각 기관. 옆구리를 앞뒤로 가로지른다.

    이거 하나로 «물고기»가 확정된다. 단 실선으로 허리께에 그으면 **허리띠**로 읽히므로
    ① 가슴 높이(y=4) ② 점선 ③ 바로 위에 들린 살 하이라이트 — 셋을 지킨다.
    """
    dark = mix(r[0], BLACK, 0.25)
    for part in parts:
        for fname in ('right', 'left'):
            f = s.f(part, fname)
            for x in range(f.w):
                if (x + (0 if fname == 'right' else 1)) % 2 == 0:
                    f.px(x, y, dark)
                    f.px(x, y - 1, mix(f.get(x, y - 1), r[4], 0.45))
        # 등·배 쪽으로 반 칸씩 물려 «몸을 감은 선»으로 이어지게
        for fname, cols in (('front', (0, 7)), ('back', (0, 7))):
            f = s.f(part, fname)
            for x in cols:
                f.px(x, y, mix(f.get(x, y), dark, 0.55))


def _gills(s, r, rows=(3, 5, 7)):
    """목 아가미 — 머리 옆면 아래 + 몸통 옆면 위로 이어진다.

    ★1패스는 (5,6,7) 연속 3행을 어둡게 칠했더니 «턱 밑의 검은 얼룩»이 됐다.
      슬릿이 슬릿으로 읽히려면 **어두운 줄 위에 밝은 줄**이 있어야 한다 — 살이 접혀
      들린 자리다. 그래서 한 줄 띄어 3줄로 놓고 바로 위 행에 하이라이트를 준다.
    ★한쪽 면에만 그리면 «얼굴의 흠집»이다. 머리 옆 → 몸통 옆으로 이어져야
      «목을 감은 기관»으로 읽힌다.
    """
    dark = mix(r[0], BLACK, 0.45)
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
    #   ★아가미 뚜껑 가장자리 — 옆면 슬릿만 그리면 **정면에서 아가미가 안 보인다.**
    #     얼굴 양 끝 열(x0·x7)의 턱께에 뚜껑 경계선을 물려 정면에서도 읽히게 한다.
    hf = s.f('head', 'front')
    for x in (0, 7):
        for y in (5, 6):
            hf.px(x, y, mix(hf.get(x, y), dark, 0.55))
        hf.px(x, 7, mix(hf.get(x, 7), r[4], 0.35))


# ── 등지느러미 ────────────────────────────────────────────────────────────────
#   ★한계 고지(위 docstring 참조): 겉레이어는 머리 0.5px·몸통 0.25px 부풀림뿐이라
#     «진짜로 튀어나온» 지느러미는 바닐라 스킨으로 불가능하다. 능선으로 «읽히게» 칠한다.
def _dorsal_head(s, fin, height=3, span=(2, 5), back=4, front=2, sweep=0.0,
                 layer='outer'):
    """정수리 볏 — 겉레이어(=머리보다 0.5px 큰 상자)에 얹어 실루엣을 키운다(lessons 3).

    ★2패스 1차 실패: 옆면을 `rect(1, y, 6, y)` 로 «전 폭 × height 행» 칠했더니 머리를
      통째로 감는 **수영모**가 됐다. 옆에서 본 지느러미는 판이 아니라 **돛 프로필**이다 —
      앞이 낮고 가운데~뒤가 높은 곡선. 그래서 열마다 높이를 따로 준다.
    ★`sweep` 이 봉우리를 뒤로 민다(하 = 뒤로 넘어간 관모).
    ★능선으로 읽히려면 «중앙 밝음 → 양옆 어두움 → 바깥 그림자» 3단이 필요하다.
      1패스는 한 색 판이라 «머리에 붙은 네모»였다.
    """
    x0, x1 = span
    cx = ((x0 + x1) // 2, (x0 + x1 + 1) // 2)
    shade = mix(fin[0], BLACK, 0.25)

    def ridge(f, y, x_lo, x_hi):
        for x in range(x_lo, x_hi + 1):
            f.px(x, y, fin[4] if x in cx else fin[2])
        if x_lo - 1 >= 0:
            f.px(x_lo - 1, y, shade)                       # 바깥 그림자 = 솟은 근거
        if x_hi + 1 < f.w:
            f.px(x_hi + 1, y, shade)

    top = s.f('head', 'top', layer)
    for y in range(8):
        ridge(top, y, x0, x1)
        if y % 3 == 2:                                     # 톱니 뒷단 — 판이 아니라 지느러미
            top.px(x0, y, fin[1])
            top.px(x1, y, fin[1])
    bk = s.f('head', 'back', layer)
    for y in range(back):
        ridge(bk, y, x0, x1)
    #   ★옆면 = 돛 프로필. i 는 «앞(0) → 뒤(7)» 순서이고, right 면은 마지막 열이 앞이라
    #     좌우에서 인덱스를 뒤집어야 봉우리가 같은 쪽에 선다(_frontness 와 같은 근거).
    peak = 3.0 + sweep * 2.5
    prof = [max(0, min(height, round(height * (1.0 - abs(i - peak) / 4.2))))
            for i in range(8)]
    for fname in ('right', 'left'):
        f = s.f('head', fname, layer)
        for i, h in enumerate(prof):
            x = 7 - i if fname == 'right' else i
            for y in range(h):
                f.px(x, y, fin[3] if y == h - 1 else fin[2])
    fr = s.f('head', 'front', layer)                       # ★정면 능선
    for y in range(front):
        ridge(fr, y, x0, x1)
    if front >= 2:
        #   ★1행짜리 볏에 이 그림자를 넣으면 볏을 통째로 먹어 이마에 «검은 구멍»이 된다
        #     (1패스 2차 실측). 2행 이상일 때만 판다.
        fr.rect(x0, front, x1, front, mix(fin[0], BLACK, 0.20))


def _dorsal_body(s, fin, y0=0, y1=8, layer='outer', cut=None):
    """등 척추선 지느러미 — 뒤통수 볏에서 **이어져 내려온다**.

    옷 위에 그린다(옷보다 뒤에 호출). 사역어의 옷은 지느러미가 나오게 등을 튼 것이다 —
    그래서 옷 위로 능선이 지나가는 게 오히려 근거가 된다.

    ★2패스 1차 실패: 4px 폭을 밝은 막색으로 채웠더니 등판 한가운데 **흰 띠 = 망토**가
      됐다. 능선은 **좁아야** 능선이다 — 심 2px(x3·x4) + 어깨 1px(위쪽만) + 양옆에
      진한 그림자. 밝은 건 심의 한 열뿐이고, 나머지는 피부보다 반 단 밝은 정도다.
    ★옆면 **뒤쪽 끝 열**(right=x0 / left=x마지막)에도 얹는다 — 겉레이어가 0.25px 밖에
      렌더되므로 옆에서 보면 등 가장자리에 지느러미 선이 생긴다. 실루엣에 실제로 기여하는
      유일한 자리다.
    """
    bk = s.f('body', 'back', layer)
    shadow = mix(fin[0], BLACK, 0.42)
    for y in range(y0, y1 + 1):
        if cut is not None and y >= cut:                   # 울지 않는 것 — 중간에서 끊긴다
            break
        #   ★폭을 3↔2 로 번갈아 «물결 가장자리»를 만든다. 폭이 일정한 2px 세로선은
        #     지느러미가 아니라 **지퍼**로 읽힌다(2패스 3차 실측). 끝으로 갈수록 좁아진다.
        wide = (y <= y0 + 2) or (y % 2 == 0 and y < y1 - 2)
        lo, hi = (2, 5) if wide else (3, 4)
        for x in range(lo, hi + 1):
            bk.px(x, y, fin[4] if x == 3 else fin[2] if x == 4 else fin[1])
        if y % 3 == 2:                                     # 톱니
            bk.px(hi, y, fin[1])
        if lo - 1 >= 0:
            bk.px(lo - 1, y, shadow)
        if hi + 1 < bk.w:
            bk.px(hi + 1, y, shadow)
    end = y1 if cut is None else cut - 1
    for fname, x in (('right', 0), ('left', PARTS['body']['d'] - 1)):
        f = s.f('body', fname, layer)
        for y in range(y0, end + 1):
            f.px(x, y, fin[3] if y % 2 else fin[1])
    if cut is not None:                                    # 잘린 끝 = 흉터
        for x in range(2, 6):
            bk.px(x, cut, mix(fin[0], BLACK, 0.45))


#   팔·다리에서 «바깥쪽»이 어느 면·어느 열인가 — Strip 언랩(right→front→left→back)에서
#   right 면의 마지막 열이 front 면의 첫 열과 맞닿고, front 의 마지막 열이 left 의 첫 열과
#   맞닿는다. 그래서 _r 파츠는 front 의 x0 이, _l 파츠는 front 의 x(마지막)이 바깥이다.
_OUTER = {'arm_r': ('right', 0), 'arm_l': ('left', -1),
          'leg_r': ('right', 0), 'leg_l': ('left', -1)}


def _finray(s, part, r, y0=4, y1=9, layer='outer', width=2):
    """팔뚝·종아리 지느러미 — 살(ray) 줄무늬 + 톱니 뒷단.

    ★1패스는 1~2px 민짜라 «팔에 붙은 얼룩»이었다. 지느러미로 읽히려면 ① 살이 보이고
      ② 뒷단이 톱니여야 한다. 팔·다리는 4px 기둥이라 이게 유일한 형태 장치다.
    ★2패스 3차 보강: 옆면에만 그리면 **정면에서 안 보인다.** NPC 는 lookclose 로 늘
      플레이어를 마주보므로 정면에서 안 보이는 장식은 없는 것과 같다(lessons 3 과 같은
      실수). 앞면·뒷면의 **바깥쪽 끝 열**까지 톱니로 물려 어느 각도에서도 팔 가장자리가
      들쭉날쭉하게 만든다 — 그 실루엣이 «사람 팔이 아니다»의 근거다.
    """
    side, edge_dir = _OUTER[part]
    f = s.f(part, side, layer)
    for i, y in enumerate(range(y0, y1 + 1)):
        w = width if i % 3 != 2 else max(1, width - 1)     # 톱니
        for x in range(w):
            f.px(x, y, r[4] if x == 0 else r[2])
    for fname in ('front', 'back'):                        # ★정면·배면에서도 보이는 가장자리
        g_ = s.f(part, fname, layer)
        col = 0 if edge_dir == 0 else g_.w - 1
        for i, y in enumerate(range(y0, y1 + 1)):
            if i % 3 == 2:                                 # 톱니 — 한 칸 건너뛴다
                continue
            g_.px(col, y, r[3] if i % 2 else r[1])


def _webbed(s, r, parts=('arm_r', 'arm_l')):
    """물갈퀴 손 — 손 2행을 한 단 밝히고 손가락 사이에 막을 넣는다."""
    for part in parts:
        for fname in SIDES:
            f = s.f(part, fname)
            for y in (10, 11):
                for x in range(f.w):
                    c = f.get(x, y)
                    if c[3]:
                        f.px(x, y, mix(c, r[4], 0.30))
        fr = s.f(part, 'front')
        fr.px(1, 11, mix(fr.get(1, 11), r[1], 0.45))
        fr.px(2, 10, mix(fr.get(2, 10), r[1], 0.30))


def _fish_eyes(s, y, socket, glow, dim=False, wrap=True):
    """★심해어 눈 — 얼굴 **바깥 모서리**에 붙은 발광 안구 2x2.

    2패스 2차 실패(얼굴 확대 실측): 홍채 1px 과 눈구멍 1px 을 번갈아 놨더니 밝은 점 2개 +
    검은 점 2개가 **같은 크기**로 늘어서 «눈이 네 개인 벌레»가 됐다. 8x8 에서 «눈»으로
    읽히려면 **덩어리**여야 한다 — 1px 교차는 무늬지 형태가 아니다.

    확정형: `x0~x1`·`x6~x7` 2x2 를 통째로 발광 안구로 채우고, **동공은 바깥 위 1px**
    (측면 눈이라 동공이 옆을 본다 — 해부학적으로도 맞다), 안쪽 `x2`·`x5` 한 열만 어두운
    테두리. 가운데 `x3~x4` 는 피부로 남겨 «눈 사이가 좁은 주둥이»가 생긴다.

    ★_eye_guard 는 x1·x2·x5·x6 중 «두 칸»의 밝기를 요구한다. 동공을 x0·x7 로 밀었으므로
      x1·x6 이 안구 최고 광도를 받는다 — 가드가 그대로 성립한다.
    """
    f = s.f('head', 'front')
    hi, mid, lo = (4, 3, 2) if not dim else (3, 2, 1)
    pupil = mix(socket, BLACK, 0.55)
    rim = mix(socket, BLACK, 0.25)
    for ox, ix in ((0, 1), (7, 6)):                 # 바깥 열, 안쪽 열
        f.px(ox, y, pupil)                          # ★동공은 바깥 위
        f.px(ix, y, glow[hi])
        f.px(ox, y + 1, glow[lo])
        f.px(ix, y + 1, glow[mid])
    for x in (2, 5):                                # 안쪽 테두리 한 열 = 안구가 튀어나온 근거
        f.px(x, y, rim)
        f.px(x, y + 1, mix(rim, BLACK, 0.20))
    if not wrap:
        return
    #   ★안구가 머리 옆면까지 넘어간다 — 옆에서 봐도 눈알이 튀어나온 것으로 보인다.
    #     옆면의 «앞쪽 끝 열»은 right=마지막, left=0 이다(_frontness 와 같은 근거).
    for fname, x in (('right', 7), ('left', 0)):
        sf = s.f('head', fname, 'base')
        sf.px(x, y, glow[mid])
        sf.px(x, y + 1, glow[lo])


def _fish_face(s, r, eye_y=4, mouth_y=6, mouth_w=6, barbel=None):
    """어류 얼굴 — 눈두덩 **그늘** + 콧구멍 + 넓고 얇은 입.

    ★2패스 2차 실패: 눈 위 행을 `r[4]` 로 **밝히니** 이마를 가로지르는 «머리띠»가 됐다.
      눈두덩은 눈 위로 튀어나온 뼈 선반이라 그 아래가 **그늘**이다 — 밝히는 게 아니라
      눈 바깥쪽만 어둡게 눌러야 눈이 깊어 보인다. 가운데는 건드리지 않는다(주둥이).
    ★입은 «넓고 얇게». 사람 입은 좁고 두껍다 — 이 차이 하나로도 종이 갈린다.
    """
    f = s.f('head', 'front')
    for x in (0, 1, 2, 5, 6, 7):                            # 눈두덩 그늘 (가운데는 제외)
        f.px(x, eye_y - 1, mix(f.get(x, eye_y - 1), r[0], 0.42))
    for x in (3, 4):                                        # 콧구멍 슬릿
        f.px(x, mouth_y - 1, mix(f.get(x, mouth_y - 2), r[0], 0.40))
    if mouth_w:
        x0 = (8 - mouth_w) // 2                             # 넓고 얇은 입
        line = mix(r[0], BLACK, 0.30)
        f.rect(x0, mouth_y, x0 + mouth_w - 1, mouth_y, line)
        for x in range(x0 + 1, x0 + mouth_w - 1):           # 아랫입술 = 밝은 한 단
            f.px(x, mouth_y + 1, mix(f.get(x, mouth_y + 1), r[4], 0.45))
        for x in (x0, x0 + mouth_w - 1):                    # 아래로 처진 입꼬리
            f.px(x, mouth_y, mix(line, r[1], 0.35))
            f.px(x, mouth_y + 1, mix(f.get(x, mouth_y + 1), line, 0.40))
    if barbel:                                              # 수염돌기 — 늙은 저서어
        for x in (0, 7):
            f.px(x, mouth_y, mix(f.get(x, mouth_y), barbel[3], 0.75))
            f.px(x, mouth_y - 1, mix(f.get(x, mouth_y - 1), barbel[2], 0.55))


def _brand(s, part, face, marks, color, layer='outer'):
    """비늘에 새긴 번호 낙인 / 흉터. ★4px 이하 — 가슴 로고는 금지 규칙이다."""
    f = s.f(part, face, layer)
    for (x, y) in marks:
        f.px(x, y, color)


def _species(s, P, seed, gill_rows=(3, 5, 7), belly=True, lateral=True, cs=0.60):
    """★다섯 전부가 통과하는 단일 경로 — «한 종족»은 여기서 만들어진다.

    순서가 중요하다: 채우기 → **역광음영** → 비늘 → 배비늘 → 측선 → 아가미.
    역광음영을 비늘 뒤에 돌리면 비늘 결이 뭉개지고, 앞에 안 돌리면 아무 효과가 없다.
    """
    g.head_base(s, P['skin'], seed=seed)
    _body_skin(s, P['skin'])
    _countershade(s, P['base'], amount=cs)
    _scales(s, P['skin'], seed)
    if belly:
        _belly_plates(s, P['skin'])
        for part in ('leg_r', 'leg_l'):                    # 다리도 민짜 기둥이 되지 않게
            _belly_plates(s, P['skin'], part=part, y0=4, y1=11, span=(0, 3))
    if lateral:
        _lateral_line(s, P['skin'])
    _gills(s, P['skin'], rows=gill_rows)
    _webbed(s, P['skin'])


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
        base='2f5a58',
        skin=scaleskin('2f5a58'),                   # 짙은 청록 — 세트에서 가장 어둡다
        glow=glowramp('9fe0d2'),                    # 발광 청록
        fin=scaleskin('48807a', 0.30),              # 지느러미 막 = 피부보다 밝고 반투명하게
        cloak=matte('7e8b78', 0.24),                # ★1패스 3c4a3e 는 피부와 값이 붙어
        #                                             전신이 «청록 기둥» 하나로 읽혔다
        strap=leather('4a3b2c'),
        scar=ramp('b9a58c'),                        # 비늘째 뜯어낸 자리 = 밝은 흉터
    )
    s = Skin()
    _species(s, P, SEED)
    _dorsal_head(s, P['fin'], height=3, span=(2, 5), back=4, front=2)  # 넓고 낮은 관(冠)
    g.face_shape(s, P['skin'], jaw='square', temple=True)
    _fish_eyes(s, 4, mix(P['skin'][0], BLACK, 0.45), P['glow'])
    _fish_face(s, P['skin'], eye_y=4, mouth_y=6, mouth_w=6)   # 촌장 = 가장 넓은 입

    #   어깨 비늘 망토 — 앞뒤 + 어깨 top 까지 이어야 «걸친 것»이 된다
    g.mantle(s, P['cloak'], front=5, back=10, layer='outer', seed=SEED,
             clasp=P['scar'])                              # 잠금쇠 = 뼈. 금속을 가질 수 없다
    #   ★망토도 «비늘로 짠 것»이다 — 민짜 판이면 그냥 천이고, 촌장의 권위가 안 선다.
    for fname in SIDES:
        mf = s.f('body', fname, 'outer')
        for y in range(0, 11):
            off = 0 if (y % 4) < 2 else 2
            for x in range(mf.w):
                if not mf.get(x, y)[3]:
                    continue
                if (x + off) % 4 == 0:
                    mf.px(x, y, mix(mf.get(x, y), P['cloak'][1], 0.32))
                elif (x + off) % 4 == 1:
                    mf.px(x, y, mix(mf.get(x, y), P['cloak'][4], 0.20))
    g.belt(s, P['strap'], y=8, layer='outer', ao=False)
    _dorsal_body(s, P['fin'], y0=0, y1=8)                  # ★망토를 뚫고 나온 등지느러미
    for part in ('arm_r', 'arm_l'):
        _finray(s, part, P['fin'], y0=4, y1=9)
    for part in ('leg_r', 'leg_l'):
        _finray(s, part, P['fin'], y0=6, y1=11)
    #   ★지워진 번호 — 왼팔 바깥. 비늘째 뜯겨 색이 빠진 자리
    _brand(s, 'arm_l', 'left', [(1, 2), (2, 2), (1, 3), (3, 3)], P['scar'][3])
    _brand(s, 'arm_l', 'left', [(2, 3)], P['scar'][1])
    _eye_guard(s, 4, name)
    return _finish(s, str(OUT / ('ds_%s.png' % name)))


# ══ 2. 비늘 짜는 이 210 — 손일하는 자 ==========================================
def build_weaver():
    name, SEED = 'weaver', _seed('weaver')
    P = dict(
        base='4a5748',
        skin=scaleskin('4a5748'),                   # 자갈빛 갈청 — 유일한 «녹슨» 계열
        glow=glowramp('e0c98a'),                    # ★세트에서 유일한 «따뜻한» 눈 = 작업등
        fin=scaleskin('667a5f', 0.30),
        apron=matte('9a917c', 0.22),                # 뼈빛 비늘 앞치마 = 세트의 밝은 옷 슬롯
        thread=matte('c2b9a4', 0.20),
        strap=leather('43372a'),
    )
    s = Skin()
    _species(s, P, SEED)
    _dorsal_head(s, P['fin'], height=2, span=(3, 4), back=3, front=1)  # 뒤로 눕힌 낮은 볏
    for fname in ('right', 'left'):                        # 옆으로 늘어진 뺨 지느러미
        f = s.f('head', fname, 'outer')
        f.rect(0, 4, 1, 6, P['fin'][2])
        f.px(0, 5, P['fin'][4])
    g.face_shape(s, P['skin'], jaw='round', temple=True)
    _fish_eyes(s, 4, mix(P['skin'][0], BLACK, 0.45), P['glow'])
    _fish_face(s, P['skin'], eye_y=4, mouth_y=6, mouth_w=4)

    g.apron(s, P['apron'], bib=(2, 5), bib_y=(1, 5), waist=6, hem=11,
            wrap=2, straps=True, tie=True, seed=SEED)
    #   ★앞치마도 «비늘로 짠 것»이다 — 민짜 뼈빛 판이면 그냥 캔버스 앞치마다
    af = s.f('body', 'front', 'outer')
    for y in range(1, 12):
        off = 0 if (y % 4) < 2 else 2
        for x in range(8):
            if af.get(x, y)[3] and (x + off) % 4 == 0:
                af.px(x, y, mix(af.get(x, y), P['apron'][1], 0.32))
    g.pouch(s, P['strap'], part='leg_l', face='front', x=1, y=1, w=2, h=3)
    _dorsal_body(s, P['fin'], y0=0, y1=7)
    for part in ('arm_r', 'arm_l'):
        _finray(s, part, P['fin'], y0=4, y1=9)
    for part in ('leg_r', 'leg_l'):
        _finray(s, part, P['fin'], y0=6, y1=11)
    #   ★번호를 «가린» 사람 — 오른팔에 실을 감았다(지운 모르와 짝)
    f = s.f('arm_r', 'right', 'outer')
    for y in (2, 3, 4):
        f.rect(0, y, 3, y, P['thread'][3] if y % 2 else P['thread'][2])
    _eye_guard(s, 4, name)
    return _finish(s, str(OUT / ('ds_%s.png' % name)))


# ══ 3. 일곱-셋 211 — 어린 개체 =================================================
def build_seven3():
    name, SEED = 'seven3', _seed('seven3')
    P = dict(
        base='6d92a0',
        skin=scaleskin('6d92a0'),                   # 창백한 연청 — 세트에서 가장 밝고 어리다
        glow=glowramp('bff0ff'),
        fin=scaleskin('8fb6c4', 0.30),              # 어린 개체 = 가장 여린 지느러미
        wrap=matte('5b6b63', 0.22),                 # 허리 천 조각
        brand=ramp('a8927a'),   # ★1패스 d8c9a8 은 가슴의 흰 얼룩이 됐다
    )
    s = Skin()
    #   ★밝은 피부(가장 어린 개체)라 기본 세기로 역광음영을 걸면 전신이 뿌예진다
    _species(s, P, SEED, cs=0.48)
    _dorsal_head(s, P['fin'], height=2, span=(3, 4), back=2, front=1)  # 아직 덜 자란 볏
    g.face_shape(s, P['skin'], jaw='round')
    _fish_eyes(s, 4, mix(P['skin'][0], BLACK, 0.40), P['glow'])
    _fish_face(s, P['skin'], eye_y=4, mouth_y=6, mouth_w=3)   # 어린 개체 = 작은 입

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
    #   ★어린 개체라 등지느러미도 아직 짧다 — 볏과 같은 근거로 «덜 자랐다»
    _dorsal_body(s, P['fin'], y0=0, y1=6)
    for part in ('arm_r', 'arm_l'):
        _finray(s, part, P['fin'], y0=5, y1=9, width=2)
    for part in ('leg_r', 'leg_l'):
        _finray(s, part, P['fin'], y0=7, y1=11, width=2)
    #   ★아직 «남아 있는» 번호 — 가슴 오른쪽 낙인(모르의 흉터와 짝)
    _brand(s, 'body', 'front', [(5, 3), (6, 3), (5, 4), (6, 5)], P['brand'][3],
           layer='base')
    _brand(s, 'body', 'front', [(6, 4)], P['brand'][1], layer='base')
    _eye_guard(s, 4, name)
    return _finish(s, str(OUT / ('ds_%s.png' % name)))


# ══ 4. 가라앉은 하 212 — 옛 파수 ===============================================
def build_ha():
    name, SEED = 'ha', _seed('ha')
    P = dict(
        base='56666b',
        skin=scaleskin('56666b', 0.26),             # 납빛 회청 — 백 해를 서 있어 바랬다
        glow=glowramp('9ab6bd'),                    # 흐린 발광(백내장)
        fin=scaleskin('6e8288', 0.28),              # 바랜 지느러미 — 채도 최저
        robe=matte('1e4448', 0.24),                 # ★1패스 2c5f63 은 피부와 값이 붙었다
        coral=matte('c9b98a', 0.22),                # 산호빛 견장 — 금속이 아니다
    )
    s = Skin()
    _species(s, P, SEED)
    _dorsal_head(s, P['fin'], height=4, span=(2, 5), back=6, front=3, sweep=0.9)  # 가장 높은 관모
    g.face_shape(s, P['skin'], jaw='square', temple=True)
    g.wrinkles(s, P['skin'], brow_y=2, crow=True, forehead=True)   # 백 해의 나이
    _fish_eyes(s, 4, mix(P['skin'][0], BLACK, 0.45), P['glow'], dim=True)
    #   ★수염 대신 수염돌기(barbel) — 늙은 저서어의 표식. 다섯 중 하만 가진다
    _fish_face(s, P['skin'], eye_y=4, mouth_y=6, mouth_w=4, barbel=P['fin'])

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
    #   목의 옛 교단 링 — 번호가 아니라 «자리»의 표식
    for fname in SIDES:
        s.f('body', fname, 'outer').row(0, P['coral'][1], 2, 5)
    _dorsal_body(s, P['fin'], y0=0, y1=9)                  # 제복을 튼 등지느러미
    for part in ('arm_r', 'arm_l'):
        _finray(s, part, P['fin'], y0=7, y1=11)
    for part in ('leg_r', 'leg_l'):
        _finray(s, part, P['fin'], y0=6, y1=11)
    _eye_guard(s, 4, name)
    return _finish(s, str(OUT / ('ds_%s.png' % name)))


# ══ 5. 울지 않는 것 213 — 개조되다 만 개체 =====================================
def build_mute():
    name, SEED = 'mute', _seed('mute')
    P = dict(
        base='8c7f80',
        skin=scaleskin('8c7f80', 0.34),             # ★유일하게 «바다색»이 아니다
        glow=glowramp('b9b2ad'),                    # 빛이 꺼진 눈
        fin=scaleskin('9c8d8e', 0.28),
        wrap=matte('a89f8c', 0.20),                 # 낡은 붕대
        iron=ramp_lit('7d7a75'),                    # 수조 기구의 잔재
    )
    s = Skin()
    #   ★측선도 잘못 자랐다 — 이 개체만 없다(개조되다 만 몸)
    _species(s, P, SEED, gill_rows=(5, 6), lateral=False, cs=0.50)
    #   ★볏이 «없다» — 잘려 나간 밑동만 남았다. 다른 넷과 실루엣이 근본적으로 갈린다
    top = s.f('head', 'top', 'outer')
    for x in range(2, 6):
        top.px(x, 3, mix(P['skin'][0], BLACK, 0.35))
        top.px(x, 4, mix(P['skin'][2], BLACK, 0.20))
    fr = s.f('head', 'front', 'outer')          # ★정면에서도 «없다»가 보여야 한다
    for x in range(2, 6):                       #   — 다른 넷은 여기에 볏이 솟아 있다
        fr.px(x, 0, mix(P['skin'][0], BLACK, 0.40))
    g.face_shape(s, P['skin'], jaw='round')
    _fish_eyes(s, 4, mix(P['skin'][0], BLACK, 0.60), P['glow'], dim=True)
    #   ★입이 없다 — 입 자리가 잘못 자란 아가미 흉터(세로 3줄)
    #   1패스 실측: 비늘 격자 + 흉터가 겹쳐 아래 얼굴이 «얼룩 죽»이 됐다.
    #   슬릿이 읽히려면 먼저 «평평한 바탕»을 만들어야 한다.
    hf = s.f('head', 'front')
    hf.rect(2, 6, 5, 8, P['skin'][3])
    _fish_face(s, P['skin'], eye_y=4, mouth_y=6, mouth_w=0)
    for x in (2, 4):
        hf.px(x, 6, mix(P['skin'][0], BLACK, 0.35))
        hf.px(x, 7, mix(P['skin'][0], BLACK, 0.45))
        hf.px(x + 1, 6, P['skin'][4])

    #   몸에 감긴 낡은 붕대 — 가로로 감긴다(세로 반복 금지)
    ring = s.strip('body', 'outer')
    for y in (3, 4, 8, 9):
        ring.band(y, y, P['wrap'][3] if y % 2 else P['wrap'][2])
    for y in (5, 6):                                       # 성기게 감긴 구간
        for x in range(0, 32, 3):
            ring.px(x, y, P['wrap'][2])
    s.stitch('body', 7, P['wrap'], layer='outer', base_idx=1)   # 개조 봉합선
    #   ★등지느러미가 «중간에서 끊긴다» — 다른 넷은 이어지는데 이 개체만 흉터로 끝난다
    _dorsal_body(s, P['fin'], y0=0, y1=8, cut=4)
    _finray(s, 'leg_l', P['fin'], y0=6, y1=11)             # ★지느러미도 한쪽만 남았다
    for y in (4, 5):                                       # 팔 붕대(한쪽만 = 비대칭)
        for fname in SIDES:
            s.f('arm_r', fname, 'outer').row(y, P['wrap'][3], 0, 3)
    #   목의 철 구속 밴드
    for fname in SIDES:
        s.f('body', fname, 'outer').row(0, P['iron'][2], 1, 6)
    s.f('body', 'front', 'outer').px(3, 0, P['iron'][4])
    _eye_guard(s, 4, name)
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
