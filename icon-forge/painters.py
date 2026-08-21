# 아이템 아이콘 페인터 레지스트리 — item-icons 스킬 iconlib 브러시 기반.
# 페인터 = 실루엣 하나. 팔레트 근거는 palette.ramp(icon-craft.md 재질 표준표).
# 광원 좌상단 고정, 낚싯대 축은 ↗ 대각(좌하 손잡이 → 우상 팁), 줄은 팁에서 처짐.
from iconlib import (canvas, put, qbez, polyline, cells, shaft, flat_colfn,
                     grade_colfn, ring_at, grip, hang_line, disk, sparkle, selout)
from palette import ramp


# ───────────────────────── 낚싯대 (tool) ─────────────────────────

def rod_twig(seed=0):
    """나뭇가지(E): 삐뚤빼뚤 폴리라인 + 옹이 가지 + 잎 하나 + 처진 삼베줄. 초라함이 정체성."""
    im = canvas()
    wood = ramp("6b4a2a")
    pts = polyline([(2, 14), (4, 12), (5, 12), (7, 9), (8, 9), (10, 6), (11, 4), (12, 3)])
    cl = cells(pts)
    shaft(im, cl, flat_colfn(wood), pair_until=0.55)
    put(im, 6, 9, wood[1]); put(im, 5, 8, wood[1])          # 옹이 가지(위로 뻗은 잔가지)
    put(im, 4, 7, "4e8f3a")                                  # 잎 한 장
    end = hang_line(im, (12, 3), drop=7, drift=0, col="d8cba8")  # 삼베줄(밝은 짚색)
    if end:
        put(im, end[0] - 1, end[1], "6a5a44")                # 구부린 핀 바늘
    return im


def rod_bamboo(seed=0):
    """대나무 막대기(D): 곧은 활 베지어 + 마디 3개 + 끈 그립. E보다 '정돈됨'이 등급 표현."""
    im = canvas()
    bam = ramp("b5a545")
    cl = cells(qbez((3, 13), (9, 8), (13, 2)))
    shaft(im, cl, flat_colfn(bam), pair_until=0.6)
    for t in (0.3, 0.55, 0.8):                               # 대나무 마디
        ring_at(im, cl, t, bam[0], bam[1] if t <= 0.6 else None)
    grip(im, cl, ramp("7a4a30"), upto=0.14)                  # 감은 끈 손잡이
    end = hang_line(im, (13, 2), drop=5, drift=0, col="ececec")  # 슬롯 회색 대비 확보
    if end:
        put(im, end[0] - 1, end[1] + 1, "9adceb")            # 물방울 루어
    return im


def rod_desert(seed=0):
    """사막 낚싯대(A): 사암 샤프트 + 금 페룰 2개 + 붉은 가죽 그립·태슬 + 태양 부적 루어."""
    im = canvas()
    sand, gold, leather = ramp("d8b56a"), ramp("d4a017"), ramp("a33b2e")
    cl = cells(qbez((2, 13), (10, 8), (13, 2)))
    shaft(im, cl, flat_colfn(sand), pair_until=0.6)
    for t in (0.34, 0.58):                                   # 금 페룰 링
        ring_at(im, cl, t, gold[4], gold[1])
    grip(im, cl, leather, upto=0.16)
    g0 = [c for c in cl if c[2] <= 0.16]
    if g0:                                                   # 그립 끝 붉은 태슬
        tx, ty = g0[-1][0] + 1, g0[-1][1] + 2
        put(im, tx, ty, leather[3]); put(im, tx, ty + 1, leather[1])
    end = hang_line(im, (13, 2), drop=5, drift=0, col="f4ead0")  # 슬롯 회색 대비 확보
    if end:                                                  # 태양 부적(+자 금 디스크)
        disk(im, end[0], end[1] + 1, 1, gold[2])
        put(im, end[0], end[1] + 1, gold[4])
    return im


def rod_dawn(seed=0):
    """여명의 낚싯대(A): 밤보라→새벽주황 그라데이션 샤프트 + 여명 오브 루어.
    (불 오오라 fx는 manifest에서 fire_aura로 얹는다 — 본체는 실루엣만 책임)"""
    im = canvas()
    dusk, dawn = ramp("3a2a55"), ramp("f2a14e")
    cl = cells(qbez((3, 14), (7, 8), (12, 2)))
    shaft(im, cl, grade_colfn(dusk, dawn), pair_until=0.58)
    grip(im, cl, ramp("332347"), upto=0.15)
    end = hang_line(im, (12, 2), drop=5, drift=0, col="eec8d4")  # 새벽 분홍 줄
    if end:                                                  # 떠오르는 해 오브
        disk(im, end[0], end[1] + 1, 1, dawn[2])
        put(im, end[0], end[1] + 1, "ffe9b0")
    return im


def rod_barkan(seed=0):
    """바르칸 낚싯대(S): 서버 상징 청록 + 금 와인딩 4줄 + 그립 보석 + 황금 물고기 참.
    S급 사다리 최상단 — 장식 밀도가 가장 높다."""
    im = canvas()
    teal, gold, navy = ramp("1f6f6b"), ramp("d4a017"), ramp("28324e")
    cl = cells(qbez((2, 13), (8, 6), (13, 2)))
    shaft(im, cl, flat_colfn(teal), pair_until=0.6)
    for t in (0.28, 0.44, 0.6, 0.76):                        # 금 와인딩(감은 금실)
        ring_at(im, cl, t, gold[3])
    grip(im, cl, navy, upto=0.14)
    g0 = [c for c in cl if c[2] <= 0.14]
    if g0:                                                   # 그립 위 청록 보석
        gx, gy = g0[-1][0], g0[-1][1] - 2
        put(im, gx, gy, "9ff0ea"); put(im, gx, gy + 1, "134f4c")
    end = hang_line(im, (13, 2), drop=5, drift=0, col="e8cf7a")
    if end:                                                  # 황금 물고기 참
        fx_, fy_ = end
        put(im, fx_, fy_ + 1, gold[3]); put(im, fx_ - 1, fy_ + 1, gold[2])
        put(im, fx_ - 2, fy_ + 2, gold[1])                   # 꼬리
        put(im, fx_, fy_ + 2, gold[1])                       # 배
    sparkle(im, 11, 1, "fff2c8", arm=0)                      # 팁 반짝이
    return im


# ───────────────────────── 미끼 (prop) ─────────────────────────

def bait_firefly(seed=0):
    """반딧불이 미끼(B): 코르크 단지 속 반딧불이 — 유리 2톤 + 안쪽 발광 픽셀.
    (바깥 글로우 헤일로는 manifest의 glow fx가 얹는다)"""
    im = canvas()
    glass, cork = ramp("9fb8bd"), ramp("8a5a34")
    for y in range(6, 14):                                   # 단지 몸통(어깨 넓음)
        for x in range(4, 12):
            put(im, x, y, glass[2])
    for x in range(5, 11):                                   # 목/입구 + 바닥 라운드
        put(im, x, 5, glass[1])
        put(im, x, 14, glass[1])
    for x in range(5, 11):                                   # 코르크 마개
        put(im, x, 2, cork[3]); put(im, x, 3, cork[2]); put(im, x, 4, cork[1])
    put(im, 5, 7, glass[4]); put(im, 5, 8, glass[4]); put(im, 5, 9, glass[4])  # 유리 스펙큘러(좌상)
    put(im, 8, 9, "ffd94a"); put(im, 8, 10, "e2a12c")        # 반딧불이 몸통
    put(im, 9, 9, glass[3])                                  # 날개 힌트
    put(im, 6, 11, "fff2b0"); put(im, 10, 7, "fff2b0")       # 잔광 점
    selout(im, glass[0], glass[3])
    for x in range(5, 11):                                   # 코르크는 셀아웃 후 재보정
        put(im, x, 2, cork[3]); put(im, x, 3, cork[2])
    return im


# ───────────────────────── 젖은 보물상자 현금 보상 (prop) ─────────────────────────

def money_small(seed=0):
    """작은 돈: 동전 하나가 보이는 작은 가죽 주머니. 낮은 보상용으로 가볍고 단순한 실루엣."""
    im = canvas()
    leather, copper = ramp("6a3d20"), ramp("b56b24")
    # 주머니 본체 — 아래로 살짝 벌어지는 10×10 실루엣
    for y, left, right in ((5, 5, 10), (6, 4, 11), (7, 4, 11), (8, 3, 12),
                           (9, 3, 12), (10, 4, 11), (11, 4, 11), (12, 5, 10), (13, 6, 9)):
        for x in range(left, right + 1):
            put(im, x, y, leather[2] if y < 10 else leather[1])
    # 끈과 매듭
    for x in range(5, 11):
        put(im, x, 4, leather[3] if x in (6, 9) else leather[1])
    put(im, 7, 3, leather[3]); put(im, 8, 3, leather[2]); put(im, 7, 4, leather[0])
    put(im, 6, 6, leather[3]); put(im, 9, 6, leather[1])
    # 주머니 안의 작은 구리 동전
    disk(im, 7, 9, 2, copper[2])
    put(im, 6, 8, copper[3]); put(im, 7, 8, copper[4]); put(im, 8, 9, copper[1])
    selout(im, leather[0], leather[3])
    return im


def money_medium(seed=0):
    """적당한 돈: 서로 겹친 은빛·금빛 동전 두 장. 작은 돈보다 넓고 밝은 보상 실루엣."""
    im = canvas()
    gold, copper = ramp("d4a017"), ramp("a9662a")
    # 뒤쪽 동전은 좌하로 밀어 깊이를 만든다.
    disk(im, 5, 10, 4, copper[2])
    put(im, 3, 9, copper[1]); put(im, 4, 8, copper[3]); put(im, 5, 7, copper[4])
    put(im, 5, 12, copper[1]); put(im, 7, 10, copper[1])
    # 앞쪽 금화는 우상에 크게 배치한다.
    disk(im, 10, 7, 4, gold[2])
    put(im, 8, 5, gold[3]); put(im, 9, 4, gold[4]); put(im, 10, 5, gold[3])
    put(im, 8, 8, gold[1]); put(im, 11, 9, gold[1]); put(im, 12, 7, gold[3])
    # 금화의 액면 표시 — 숫자 대신 보물상자 UI에 맞는 짧은 번뜩임
    put(im, 10, 6, gold[4]); put(im, 10, 7, gold[3]); put(im, 10, 8, gold[1])
    selout(im, copper[0], gold[4])
    return im


def money_large(seed=0):
    """큰 돈: 가득 찬 금화 주머니와 넘쳐나는 동전·반짝이. 최고 금액을 즉시 읽히게 한다."""
    im = canvas()
    leather, gold = ramp("5d351e"), ramp("d49b18")
    # 묵직한 주머니 본체 — 작은 돈과 달리 넓고 둥근 바닥
    for y, left, right in ((8, 3, 12), (9, 2, 13), (10, 2, 13), (11, 2, 13),
                           (12, 3, 12), (13, 4, 11), (14, 5, 10)):
        for x in range(left, right + 1):
            put(im, x, y, leather[2] if y < 12 else leather[1])
    # 주머니 입구와 굵은 끈
    for x in range(3, 13):
        put(im, x, 8, leather[3] if x % 3 else leather[1])
    put(im, 4, 7, leather[3]); put(im, 5, 6, leather[2]); put(im, 10, 6, leather[2]); put(im, 11, 7, leather[3])
    # 넘쳐난 금화 세 장 — 중앙 금화가 가장 크다.
    disk(im, 5, 6, 2, gold[2])
    disk(im, 8, 5, 4, gold[2])
    disk(im, 12, 6, 2, gold[2])
    put(im, 6, 4, gold[3]); put(im, 7, 3, gold[4]); put(im, 8, 4, gold[4]); put(im, 9, 5, gold[3])
    put(im, 7, 6, gold[1]); put(im, 8, 7, gold[1]); put(im, 10, 6, gold[3])
    put(im, 4, 5, gold[3]); put(im, 5, 4, gold[4]); put(im, 12, 5, gold[3])
    # 최고 보상 전용 보물 반짝이
    sparkle(im, 2, 4, gold[4], arm=1)
    sparkle(im, 14, 3, gold[4], arm=0)
    selout(im, leather[0], gold[4])
    return im


# ───────────────────────── 스킬 배지 (badge) ─────────────────────────

def skill_manseon(seed=0):
    """만선(낚시 특성 잭팟): 청록 배지 필드 + 물결 + 도약하는 황금 물고기 + 반짝이."""
    im = canvas()
    teal, gold = ramp("1f6f6b"), ramp("d4a017")
    for y in range(16):                                      # 원형 필드(위 밝고 아래 어두운 2톤)
        for x in range(16):
            if (x - 7.5) ** 2 + (y - 7.5) ** 2 <= 6.8 ** 2:
                put(im, x, y, teal[2] if y < 8 else teal[1])
    for i, x in enumerate(range(3, 13)):                     # 물결(지그재그)
        put(im, x, 11 + (i % 2), "7fd4d0")
    # 통통한 가로 물고기 글리프(한 형태 원칙): 등=라이트, 배=미드, 꼬리 삼각
    for x in range(5, 10):
        put(im, x, 6, gold[3])                               # 등
        put(im, x, 8, gold[1])                               # 배 그림자
    for x in range(4, 11):
        put(im, x, 7, gold[2])                               # 몸통 중심(양끝 뾰족)
    put(im, 7, 5, gold[3])                                   # 등지느러미
    put(im, 3, 6, gold[1]); put(im, 2, 7, gold[2]); put(im, 3, 8, gold[1])  # 꼬리 V
    put(im, 9, 6, "3a3140")                                  # 눈
    put(im, 10, 8, gold[4])                                  # 턱 하이라이트
    sparkle(im, 12, 4, "fff2c8", arm=0)
    put(im, 12, 9, "e8f8f6")                                 # 물방울
    selout(im, teal[0], teal[3])
    return im


REGISTRY = {
    "rod-twig":      (rod_twig, {}),
    "rod-bamboo":    (rod_bamboo, {}),
    "rod-desert":    (rod_desert, {}),
    "rod-dawn":      (rod_dawn, {}),
    "rod-barkan":    (rod_barkan, {}),
    "bait-firefly":  (bait_firefly, {}),
    "money-small":   (money_small, {}),
    "money-medium":  (money_medium, {}),
    "money-large":   (money_large, {}),
    "skill-manseon": (skill_manseon, {}),
}
