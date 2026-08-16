#!/usr/bin/env python3
"""Lv70 베타 종점용 경험치 곡선 + 퀘스트 보상 재설계 생성기.

설계 파라미터 (유저 확정 2026-08-17):
  · Lv70 = 베타 종점, 목표 소요 약 60시간
  · 1회성 퀘스트 총 XP = cum[70] 의 50% (나머지 절반은 낚시)
  · Lv1~19 무변경 (온보딩 보존)

핵심 아이디어 — need(lv) = 2 × h(lv) × xph(lv).
  h(lv)  = 그 레벨에 쓰길 바라는 낚시 시간 (Lv20부터 완만한 기하 증가)
  xph(lv)= 그 레벨의 실측 시간당 경험치 (등급 해금 M30·L45·G60 반영, 단조 비감소)
  ×2     = 퀘스트가 절반을 담당하므로
둘 다 비감소이므로 need 의 단조증가가 구조적으로 보장된다 (구 구간별 기하급수는
경계에서 리셋되며 역전이 났다 — 그래서 이 방식으로 바꿨다).
"""
import json, os, collections

CUR = [500,521,534,546,556,566,575,583,591,599,607,614,621,628,635,642,649,655,662,668,
       831,997,1166,1338,1619,1884,2170,2480,2815,3180,3574,3998,4453,4945,5476,6049,6665,7327,8041,8806,
       9995,11322,12816,14480,16338,18416,20739,23331,26220,29432,31200,33072,35056,37160,39392,41760,44264,46920,49736,52720,
       57992,63792,70168,77184,84904,93392,102736,113008,124312,136744,150416,165456,182008,200208,220224,242248,266472,293120,322432,354680,
       390144,429160,472080,519288,571216,628336,691176,760288,836320,919952,1011952,1113144,1224456,1346904,1481600,1629760,1792736,1972008,2169208,2386128]

# ── 등급별 기본 EXP (RewardMath.baseExp) ──
BASE = {'E':2,'D':3,'C':4,'B':6,'A':12,'S':30,'M':200,'L':800,'G':3000}
# 종결 등급분포 (balance-audit stat_value.py 산출)
DIST = {'E':34.54,'D':33.25,'C':21.48,'B':6.01,'A':2.48,'S':1.02,'M':0.82,'L':0.37,'G':0.03}
SIZE_MULT = 0.5 + 65.6/100        # 크기점수 65.6
CATCH_PER_H = 220                 # 실측 포획/h
BONUS = 1 + (206 + 25)/100        # 장비 경험치 +206% · 환경 +25% (합연산)

def unlocked(lv):
    """GradeRoller.maxGradeNum 게이트: M30 · L45 · G60."""
    g = ['E','D','C','B','A','S']
    if lv >= 30: g.append('M')
    if lv >= 45: g.append('L')
    if lv >= 60: g.append('G')
    return g

def xph(lv):
    """그 레벨의 시간당 경험치. 미해금 등급 확률은 해금분에 재정규화."""
    g = unlocked(lv)
    tot = sum(DIST[k] for k in g)
    per = sum(BASE[k]*DIST[k] for k in g) / tot * SIZE_MULT
    gear = min(1.0, lv / 60.0)                     # 장비 보너스는 레벨과 함께 성장
    return per * CATCH_PER_H * (1 + (BONUS-1)*gear)

QUEST_SHARE = 0.50
TARGET_HOURS = 51.0        # Lv20→70 낚시 시간. Lv1~20 현행분이 9.1h 라 합 약 60h
SEED_NEED = 700            # Lv20→21 의 need. 온보딩 마지막(Lv19→20 = 662)에서 이어져야 한다
ONBOARD = 19               # need 인덱스 0..18 = Lv1→2 .. Lv19→20 고정

def solve_growth(base_h, n_lv, target):
    """base_h × Σr^i = target 을 만족하는 성장률 r 을 이분탐색."""
    lo, hi = 1.0001, 1.30
    for _ in range(200):
        r = (lo + hi) / 2
        s = base_h * (r**n_lv - 1) / (r - 1)
        if s < target: lo = r
        else: hi = r
    return (lo + hi) / 2

def build_need():
    n_lv = 50                                       # Lv20→21 .. Lv69→70
    # 시작 need 를 온보딩에 이어붙이도록 base_h 를 고정하고, 총 시간에 맞춰 성장률을 역산
    base_h = SEED_NEED * (1 - QUEST_SHARE) / xph(20)
    r = solve_growth(base_h, n_lv, TARGET_HOURS)
    need = CUR[:ONBOARD]
    for i in range(n_lv):
        lv = 20 + i
        need.append(int(round(base_h * (r**i) * xph(lv) / (1 - QUEST_SHARE))))
    globals()['_GROWTH'] = r
    # Lv70→100 꼬리: 기존 곡선의 레벨당 성장률을 그대로 이어붙인다
    v = need[-1]
    for i in range(69, 100):
        v *= CUR[i] / CUR[i-1]
        need.append(int(round(v)))
    return need

def cumulative(need):
    c = [0]*101
    for lv in range(2, 101):
        c[lv] = c[lv-1] + need[lv-2]
    return c

def level_of(xp, cum):
    l = 1
    while l < 100 and xp >= cum[l+1]:
        l += 1
    return l

def report(need, cum):
    cur = cumulative(CUR)
    print("═══ 새 곡선 (Lv70 = 베타 종점) ═══")
    print(f"{'구간':11} {'필요XP':>10} {'낚시분':>10} {'낚시h':>7} | {'현행':>11} {'배율':>6}")
    for a, b in [(1,20),(20,30),(30,40),(40,50),(50,60),(60,70)]:
        nd, cd = cum[b]-cum[a], cur[b]-cur[a]
        share = 1.0 if a == 1 else (1-QUEST_SHARE)
        h = sum(need[lv-1]*share/xph(lv) for lv in range(a, b))
        print(f"Lv{a:>2}→{b:<3}   {nd:10,} {nd*share:10,.0f} {h:7.1f} | {cd:11,} {nd/cd:5.2f}x")
    tot_h = sum(need[lv-1]*(1.0 if lv < 20 else 1-QUEST_SHARE)/xph(lv) for lv in range(1, 70))
    print(f"\nLv70 누적 {cum[70]:,}  (현행 {cur[70]:,} · {cum[70]/cur[70]*100:.0f}%)")
    print(f"→ 낚시 담당 {cum[70]*(1-QUEST_SHARE):,.0f} XP · 총 {tot_h:.1f}h")
    print(f"→ 퀘스트 담당 {cum[70]*QUEST_SHARE:,.0f} XP (현행 1회성 총합 965,082)")
    print(f"Lv50 누적 {cum[50]:,} = Lv70 의 {cum[50]/cum[70]*100:.0f}%   (현행 17%)")
    print(f"Lv100 누적 {cum[100]:,}  (현행 {cur[100]:,})")

BS = "/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip"

def rescale_quests(need, cum, write=False):
    """1회성 퀘스트 보상경험치를 need(필요레벨) 비례로 재배분.

    총합 = cum[70] × QUEST_SHARE. 게이트에 비례시키면 '게이트 도달 시점의 실제 레벨'이
    게이트 근처로 수렴한다(현행 일괄 ×3 은 램프를 무시해 최대 +22 오버슛).
    """
    q = json.load(open(os.path.join(BS, 'quests.json'), encoding='utf-8'))
    qs = q['퀘스트']
    one = [v for v in qs.values() if v.get('카테고리') in ('튜토','메인','사이드','히든')]
    # ── 구간예산 방식 ──
    # 게이트 G 의 퀘스트들은 "G 에서 다음 게이트까지 필요한 XP 의 QUEST_SHARE" 를 나눠 갖는다.
    # 이렇게 하면 모든 게이트에서 충당률이 정확히 QUEST_SHARE 로 균일해진다.
    # (일괄 배율이나 need 단순비례는 퀘스트 개수 분포가 앞에 쏠려 있어 초반 과잉이 남는다.)
    by_gate = collections.defaultdict(list)
    for v in one:
        by_gate[max(1, min(70, v.get('필요레벨', 1)))].append(v)
    gates = sorted(by_gate)
    changes = []
    for gi, g in enumerate(gates):
        nxt = gates[gi+1] if gi+1 < len(gates) else g + 2
        seg = cum[min(nxt,100)] - cum[g]
        # 마지막 게이트(=베타 종점 Lv70)는 뒤에 세그먼트가 없다. 종점 직전 2레벨분을
        # 예산으로 준다 — 더 크게 잡으면 최종 메인 하나가 수만 XP 를 뱉어 곡선이 무너진다.
        if seg <= 0: seg = cum[min(g+2,100)] - cum[min(g,98)]
        budget = seg * QUEST_SHARE
        grp = by_gate[g]
        ws = [1.0 + min(15, max(1, v.get('난이도',1)))/15.0 for v in grp]   # 난이도 1~15 → 1.0~2.0배
        tw = sum(ws)
        for v, w in zip(grp, ws):
            changes.append([v['id'], v.get('보상경험치', 0), budget * w / tw, v.get('필요레벨',1), v.get('카테고리'), v])
    # 총합을 정확히 QUEST_SHARE × cum[70] 로 정규화 (난이도 가중·최소치·마지막 게이트 보정 누적분 제거)
    norm = (cum[70] * QUEST_SHARE) / sum(c[2] for c in changes)
    out = []
    for c in changes:
        new = max(5, int(round(c[2] * norm)))
        if write: c[5]['보상경험치'] = new
        out.append((c[0], c[1], new, c[3], c[4]))
    changes = out
    # 주간 36건: 현재 전부 0 → 일일 전문(1,500/일)의 3.5배 = 주당 5,250 수준
    wk = [v for v in qs.values() if v.get('카테고리') == '주간']
    wk_each = []
    for v in wk:
        val = int(round(5250 / len(wk) * (1.0 + min(15, max(1, v.get('난이도',1)))/7.5)))
        wk_each.append((v['id'], v.get('보상경험치',0), val))
        if write: v['보상경험치'] = val
    # 일일 기부 4종: 같은 티어 다른 일일의 중앙값
    tiers = q['일일']
    dl_fix = []
    for tier, ids in tiers.items():
        vals = [qs[i].get('보상경험치',0) for i in ids if i in qs and qs[i].get('보상경험치',0) > 0]
        med = int(round(sum(vals)/len(vals))) if vals else 60
        for i in ids:
            if i in qs and qs[i].get('보상경험치', 0) == 0:
                dl_fix.append((i, 0, med))
                if write: qs[i]['보상경험치'] = med
    if write:
        with open(os.path.join(BS, 'quests.json'), 'w', encoding='utf-8') as f:
            json.dump(q, f, ensure_ascii=False, indent=2)
    return changes, wk_each, dl_fix

def verify_gates(need, cum, changes):
    """1회성 퀘스트를 필요레벨 순으로 소화할 때 게이트 도달 시점의 실제 레벨."""
    newxp = {c[0]: c[2] for c in changes}
    q = json.load(open(os.path.join(BS, 'quests.json'), encoding='utf-8'))['퀘스트']
    one = [v for v in q.values() if v.get('카테고리') in ('튜토','메인','사이드','히든')]
    one.sort(key=lambda v: (v.get('필요레벨',1), v.get('id','')))
    xp = 0; rows = []; seen = set()
    for v in one:
        g = v.get('필요레벨', 1)
        if g not in seen:
            seen.add(g); rows.append((g, level_of(xp, cum)))
        xp += newxp.get(v['id'], v.get('보상경험치',0))
    return rows, xp

if __name__ == '__main__':
    import sys
    need = build_need()
    assert len(need) == 100, len(need)
    bad = [(i, need[i], need[i+1]) for i in range(99) if need[i] >= need[i+1]]
    assert not bad, f"단조증가 위반: {bad[:5]}"
    print("단조증가 OK\n")
    cum = cumulative(need)
    report(need, cum)

    write = '--write' in sys.argv
    ch, wk, dl = rescale_quests(need, cum, write=write)
    print(f"\n═══ 퀘스트 보상경험치 재배분 ═══")
    print(f"1회성 {len(ch)}건 총합 {sum(c[2] for c in ch):,} (구 {sum(c[1] for c in ch):,})")
    print(f"주간 {len(wk)}건 총합 {sum(w[2] for w in wk):,} (구 0)  ·  일일 기부 {len(dl)}건 0→{[d[2] for d in dl]}")
    big = sorted(ch, key=lambda c: -c[2])[:5]
    print("최대 보상 5건:")
    for i, o, n, g, cat in big:
        print(f"  {n:>7,} (구 {o:>6,})  Lv{g:<3} {cat:4} {i}")

    # ── 게이트별 충당률: 그 게이트까지의 퀘스트 XP 합 / cum[게이트] ──
    newxp = {c[0]: c[2] for c in ch}
    qq = json.load(open(os.path.join(BS, 'quests.json'), encoding='utf-8'))['퀘스트']
    one = sorted([v for v in qq.values() if v.get('카테고리') in ('튜토','메인','사이드','히든')],
                 key=lambda v: v.get('필요레벨',1))
    print(f"\n═══ 게이트별 충당률 (목표 {QUEST_SHARE*100:.0f}%) ═══")
    print(f"{'게이트':>7} {'퀘XP누적':>11} {'필요누적':>11} {'충당률':>7}  {'낚시로 메울 시간':>14}")
    devs = []
    for g in (5,10,15,20,25,30,35,40,45,50,55,60,65,70):
        acc = sum(newxp.get(v['id'], 0) for v in one if v.get('필요레벨',1) <= g)
        cov = acc / cum[g] if cum[g] else 0
        devs.append(abs(cov - QUEST_SHARE))
        gap = max(0, cum[g] - acc)
        hrs = sum(need[l-1]/xph(l) for l in range(1, g)) * (gap/cum[g] if cum[g] else 0)
        print(f"  Lv{g:<4} {acc:11,} {cum[g]:11,} {cov*100:6.0f}% {hrs:13.1f}h")
    print(f"목표 이탈 최대 {max(devs)*100:.0f}%p  (현행 초반 +392~736%p 과잉)")
    if write:
        print("\n★ quests.json 에 기록했다 (dev)")

