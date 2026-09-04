#!/usr/bin/env python3
"""농부 오스발트 — &a[Q], 스폰도시(섬상점 골목 실내), citizensId 207.

CHARACTER BRIEF  (npc_brief.py 오스발트 + prod saves.yml 반경 45m 실측)
  역할   퀘스트 전용(마인팜 8연작). 대사가 캐릭터의 전부다:
         "왔는가. 흙 냄새가 좋지 않나." / "밭은 거짓말을 안 해. 딱 손댄 만큼만 돌려주지."
         "나도 젊을 적에 해 보려다 못 했어. 무릎이 먼저 갔지."
         → 물가(낚시) 서버에서 «흙»을 대변하는 유일한 노인. 평생 밭을 못 늘려 본 사람이
           플레이어에게 만 칸을 시킨다. 가난하고, 무릎이 상했고, 씨앗을 나눠 준다.
  지역   스폰도시(유럽풍). 359.5/87/823.5 — 섬상점 골목 실내.
  이웃   브루노 4m(섬상점) · 지그프리트 8m · 클라우스 9m(상점) · 마리 18m.
  ★같은 마을에 이미 «밀짚모자 + 멜빵 + 맨발»의 강가 노인 하인리히(102)가 있다.
    노농의 1순위 실루엣이 통째로 점유돼 있으므로 **밀짚모자도 멜빵도 쓰지 않는다.**
    수염도 갈린다: 할아버지=full · 하겐=mutton · 하인리히=goatee → 오스발트=stubble.
    반돌리에는 하겐이 점유 → 쓰지 않는다.

DESIGN SPEC  (그리기 전에 전부 선언 — 이 표가 품질의 근본 레버)
  나이/체격  60대 후반, 어깨가 두껍고 무릎이 상한 몸
  실루엣     ★모자 없음(후퇴한 헤어라인 + 반백을 그대로 보여준다 — 마을 노인 중 유일)
             밭흙색 **작업 스모크**(어깨 요크 + 아래로 잡힌 주름) + 그 아래 리넨 셔츠
             + 가죽 허리띠 + **왼허리 씨앗 주머니** + **오른무릎 헝겊 덧댐** + 짧은 흙장화
  팔레트     스모크=밭흙 올리브 5f5c3e(무광, 상체는 «어두운» 슬롯)
             / 셔츠(팔에서만 보인다)=표백 안 한 리넨 b3a785 → 상하 2단 대비
             / 바지=마른 흙 캔버스 7a6a52 / 장화=진흙 갈 3a2f26
             / 허리띠·주머니=낡은 가죽 55402c / 무릎 덧댐=생캔버스 9a8b6a
             / 악센트=**철** 8f8a84 두 곳뿐(허리띠 버클 1 · 주머니 잠금 1).
             ★놋쇠 아님 — 놋쇠는 하겐·브루노 쪽 금속이고, 이 사람은 가난하다.
  비대칭     ① 오른소매만 걷어붙임(팔뚝 노출) ② 왼허리 씨앗 주머니
             ③ 오른무릎만 헝겊 덧댐 — 대사("무릎이 먼저 갔지")의 시각적 근거
  정체 모티프 가슴 로고 없음. 정체성은 스모크 재단 + 씨앗 주머니 + 무릎 덧댐.
  얼굴       그을리고 붉은 피부 · 반백 머리(램프 폭 0.26 — 넓으면 «머리 색이 반반») ·
             **stubble 회백 수염** · 이마+눈가 주름(모자가 없으므로 이마를 쓴다) ·
             갈색 눈 안쪽 응시(기본) · 코 생략(기본)
"""
import pathlib
import sys
import zlib

# ★스킬 본체는 심볼릭 링크 뒤에 있다(lessons.md 23장). 추적되는 레포 경로를 먼저 보고
#   없으면 홈을 본다 — 홈 링크 하나가 사라져 생성기 49개가 죽은 적이 있다.
for _cand in (pathlib.Path(__file__).resolve().parents[1]
              / '.claude/skills/npc-skin-forge/scripts',
              pathlib.Path.home() / '.claude/skills/npc-skin-forge/scripts'):
    if _cand.is_dir():
        sys.path.insert(0, str(_cand))
        break
else:
    raise SystemExit('npc-skin-forge/scripts 를 찾을 수 없다')

import garments as g                                  # noqa: E402
from skinlib import Skin, ramp, ramp_lit, rgba, mix   # noqa: E402

OUT = pathlib.Path(__file__).parent / 'out'
SEED = zlib.crc32(b'oswald') % 100000                 # ★hash() 금지 — 빌드가 비결정적이 된다


# ── 재질별 램프 (lessons.md 19장) ────────────────────────────────────────────
def matte(base, spread=0.22):
    """무광 직물 — 색상 회전 0, 채도 거의 고정, 명도 폭 좁게."""
    return ramp(base, spread=spread, hue=0.0, sat=0.03)


def leather(base, spread=0.34):
    """가죽 — 반사는 «완전 조금만»."""
    return ramp(base, spread=spread, hue=0.02, sat=0.06)


def _eye_guard(s, eye_y, who):
    """★lessons.md 13장 — 머리카락/수염 «뒤에» 둬야 의미가 있는 가드."""
    f = s.f('head', 'front')
    if sum(1 for x in (1, 2, 5, 6) if max(f.get(x, eye_y)[:3]) > 150) < 2:
        raise ValueError('%s: 눈이 지워졌다 (eye_y=%d)' % (who, eye_y))


def _hair_frame(s, hair_r, rows=6, part_x=None):
    """얼굴을 감싸는 옆머리 — 전부 **outer** 에 얹어 머리통을 넓힌다(lessons.md 3장).

    ★x0·x7 은 얼굴 «바깥 열»이라 눈(x1·x6)을 가리지 않는다. base 에 칠하면 얼굴이
      6px 로 깎여 «갈색 헬멧»이 된다. ★좌우 격차는 «한 단»까지(20장).
    """
    hf = s.f('head', 'front', 'outer')
    for y in range(rows):
        #   ★좌우를 «한 단»까지만 벌린다 — 두 단이면 «머리 색이 반반»으로 읽힌다(20장).
        #     1패스에서 왼쪽 [4]/[3] · 오른쪽 [3]/[2] 로 뒀더니 hair_lit 의 방사 감쇠가
        #     더해져 실제 픽셀이 [4] 대 [0] 까지 벌어졌다(실측 a09a92 vs 6a655b).
        for x, c in ((0, hair_r[3]), (7, hair_r[2])):
            if hf.get(x, y)[3] < 128:
                hf.px(x, y, c)
    if part_x is not None:
        for y in (0, 1):
            if hf.get(part_x, y)[3] >= 128:
                hf.px(part_x, y, hair_r[1])


def _seal_hairline(s, skin_r, hair_r, rows=2):
    """정수리 구간에 남은 «피부 픽셀»을 머리카락으로 메운다(lessons.md 22장).

    ★rows=2 로 좁게 잡는다 — 오스발트는 **후퇴한 헤어라인**이 설계이므로 y2 의 이마는
      피부로 남아야 한다. 여기서 3행까지 봉인하면 노인이 아니라 숱 많은 중년이 된다.
    ★얼굴 피처(주름 포함)를 전부 그린 «뒤»에 호출해야 한다.
    """
    hf, bf = s.f('head', 'front', 'outer'), s.f('head', 'front')
    skins = [rgba(c)[:3] for c in skin_r]
    hairs = [rgba(c)[:3] for c in hair_r]

    def near(px, pool):
        return min(sum((px[i] - c[i]) ** 2 for i in range(3)) for c in pool)

    for y in range(rows):
        for x in range(8):
            if hf.get(x, y)[3] >= 128:
                continue
            px = bf.get(x, y)[:3]
            if near(px, skins) < near(px, hairs):
                hf.px(x, y, hair_r[2])


def _knee_patch(s, part, r, seed=0):
    """무릎 헝겊 덧댐 — 앞·옆으로 이어져야 «천 조각»으로 읽힌다(앞면만 칠하면 그림)."""
    g.patch(s, part, 'front', r, x=0, y=4, w=3, h=3, layer='outer')
    f = s.f(part, 'right' if part == 'leg_r' else 'left', 'outer')
    f.rect(0, 4, 3, 6, r[2])
    for x in range(4):                                   # 성긴 시침질
        if x % 2 == 0:
            f.px(x, 4, r[4])


def build():
    P = dict(
        skin=ramp('b07c52'),                             # 그을리고 붉은 농부 피부
        hair=ramp('857e72', spread=0.26),                # 반백 — 폭이 넓으면 «머리 색이 반반»
        brow=ramp('6b6154'),
        beard=ramp('9a9287'),                            # 회백 — stubble 은 피부 위에 섞인다
        smock=matte('5f5c3e', 0.24),                     # 밭흙 올리브
        shirt=matte('b3a785', 0.24),                     # 표백 안 한 리넨 — 팔에서만 보인다
        pants=matte('7a6a52', 0.22),                     # 마른 흙 캔버스
        canvas=matte('9a8b6a', 0.22),                    # 무릎 덧댐
        boot=leather('3a2f26'),
        strap=leather('55402c'),
        iron=ramp_lit('8f8a84'),                         # 금속만 진짜 하이라이트
        iris=ramp(g.IRIS['brown']),
    )
    s = Skin()

    # ── 머리: 피부 → 머리카락 → 얼굴 피처 → 수염 → 주름 (나중에 그린 것이 이긴다)
    g.head_base(s, P['skin'], seed=SEED)
    g.ears(s, P['skin'], y=4)
    #   fringe=2 = 얇게 남은 앞머리. male_hair_style('sidepart') 은 이마를 피부로 열어
    #   앞머리를 1행까지 깎으므로 쓰지 않는다(lessons.md 20장) — 후퇴는 fringe 로 준다.
    g.hair(s, P['hair'], fringe=2, back=5, seed=SEED, part_x=2)
    _hair_frame(s, P['hair'], rows=6, part_x=2)
    g.face_shape(s, P['skin'], jaw='square', temple=True)
    g.face_marks(s, P['skin'], kind='ruddy', seed=SEED)
    #   ★stubble 은 «피부 위에 섞는» 방식이라 face_marks 뒤에 와야 한다(앞에 두면 볼 홍조가
    #     그루터기를 덮는다 — lessons.md 21장의 머튼촙과 같은 순서 문제).
    g.beard(s, P['beard'], style='stubble', y=4, seed=SEED)
    g.wrinkles(s, P['skin'], brow_y=2, crow=True, forehead=True)   # 모자 없음 → 이마를 쓴다
    g.eyes(s, 'c9c4b8', P['iris'], y=4, gaze=0, iris_idx=3)   # ★idx1 은 34190f = 사실상 검정. 1px 홍채는 축소되면 사라진다
    g.brow(s, P['brow'][2], y=3, weight=1)
    g.mouth(s, P['skin'], y=6, w=2)          # ★회백 수염색을 입에 쓰면 «회색 막대»가 된다
    _seal_hairline(s, P['skin'], P['hair'], rows=2)      # ★얼굴 피처 전부 뒤
    _eye_guard(s, 4, 'oswald')

    # ── base: 리넨 셔츠 → 바지 → 짧은 흙장화
    g.tunic(s, P['shirt'], y0=0, y1=11, collar=True, seed=SEED, fold_cols=(2, 5),
            grain=0.07)
    g.sleeves(s, P['shirt'], y0=0, y1=9, rolled=('arm_r', 6), skin_r=P['skin'],
              seed=SEED, grain=0.07)                     # 비대칭 ① 오른소매만 걷음
    g.hands(s, P['skin'], rows=2)
    g.pants(s, P['pants'], y0=0, y1=8, seed=SEED, grain=0.11)   # ★y8 을 비우면 다리 옆면에 구멍
    g.boots(s, P['boot'], rows=3, toe=True, cuff=True)

    # ── outer: 작업 스모크 → 허리띠 → 씨앗 주머니 → 무릎 덧댐
    g.smock(s, P['smock'], y0=0, hem=11, yoke=2, layer='outer', seed=SEED, grain=0.07)
    g.belt(s, P['strap'], y=8, accent=P['iron'], layer='outer')
    s.ao_row('body', 9, P['smock'], layer='outer', drop=2)
    g.pouch(s, P['strap'], part='leg_l', face='front', x=1, y=0, w=2, h=3,
            metal=P['iron'])                             # 비대칭 ② 왼허리 씨앗 주머니
    _knee_patch(s, 'leg_r', P['canvas'], seed=SEED)      # 비대칭 ③ 오른무릎만 덧댐
    for _p in ('arm_r', 'arm_l'):                        # 팔이 단색 판자가 되지 않게
        s.shade_col_falloff(_p, P['shirt'], 0, 9)
    s.folds('arm_l', 2, 8, P['shirt'], cols=(2,), seed=SEED + 1)

    OUT.mkdir(exist_ok=True)
    return s.save(str(OUT / 'oswald.png'))


if __name__ == '__main__':
    print(build())
