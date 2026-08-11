#!/usr/bin/env python3
"""
stats-lab/seed_sandbox.py — statsweb 대시보드 로컬 샌드박스용 가짜 텔레메트리 생성기.

실제 prod 데이터는 절대 건드리지 않는다 — 이 스크립트는 sandbox-data/ 밑에 별도의
stats-latest.db + events-YYYY-MM.db를 새로 만들 뿐이다(TeleDb.java의 스키마와 동일하게
직접 구성, 실제 서버는 안 거침). statsweb을 이 폴더로 가리키면(STATSLAB_DATA_DIR)
①~⑩ 전 페이지가 실 데이터 없이도 그럴듯한 값으로 채워져 UI/차트를 자유롭게 테스트할 수 있다.

사용법:
    python3 seed_sandbox.py                 # sandbox-data/ 새로 생성(기존 있으면 삭제 후 재생성)
    python3 seed_sandbox.py --days 30       # 롤업 일수 조절(기본 14)
    python3 seed_sandbox.py --players 20    # 가짜 플레이어 수(기본 12)
"""
import argparse
import gzip
import json
import os
import random
import shutil
import sqlite3
import uuid as uuidlib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "sandbox-data")

NAMES = ["가짜낚시왕", "테스트유저1", "동해바다", "춘천호수", "바르칸초보", "고인물123",
         "물고기헌터", "초보낚시꾼", "황금잉어", "은빛도미", "바다사나이", "낚시달인",
         "섬주민A", "섬주민B", "길드마스터", "신규유저", "복귀유저", "핵과금러",
         "무과금유저", "이벤트헌터"]
RODS = ["나무낚싯대", "강철낚싯대", "은빛낚싯대", "황금낚싯대", "S등급낚싯대", "레전드낚싯대"]
ENHS = ["+0", "+3", "+5", "+7", "+9", "+12"]
GRADES = ["E", "D", "C", "B", "A", "S", "M", "L", "G"]

# money.txn reason별 현실적 가중치/방향/금액대(2026-07-28 피드백: "페리요금이 1위로 나오는 게 말이
# 안 됨" — 완전 랜덤이 아니라 실제 게임 경제 구조를 흉내낸 분포로 교체). weight는 rng.choices 상대
# 가중치, sign은 +(소스)/-(싱크)/±(양방향, 대체로 상쇄됨 — 이관·송금·카지노), amount는 건당 금액대.
REASON_PROFILE = {
    "판매":     {"sign": "+", "weight": 40, "amount": (5000, 300000)},   # 압도적 주 수입원
    "퀘스트보상": {"sign": "+", "weight": 15, "amount": (500, 50000)},
    "제출":     {"sign": "+", "weight": 6,  "amount": (1000, 20000)},
    "카지노":    {"sign": "±", "weight": 10, "amount": (1000, 100000)},   # 변동성 크지만 총합은 하우스가 근소 우위
    "이관":     {"sign": "±", "weight": 5,  "amount": (1000, 50000)},   # p2p 성격 — 합산은 0에 수렴해야 정상
    "송금":     {"sign": "±", "weight": 5,  "amount": (1000, 50000)},
    "부품구매":  {"sign": "-", "weight": 8,  "amount": (1000, 80000)},
    "강화비용":  {"sign": "-", "weight": 6,  "amount": (500, 30000)},
    "낚시대구매": {"sign": "-", "weight": 3,  "amount": (5000, 200000)},
    "여관숙박":  {"sign": "-", "weight": 1.5, "amount": (100, 2000)},
    "페리요금":  {"sign": "-", "weight": 0.5, "amount": (50, 500)},      # 의도적으로 가장 작은 싱크
}
MONEY_REASONS = list(REASON_PROFILE.keys())
QUEST_IDS = [f"일퀘_{i}" for i in range(1, 9)] + [f"주간_{i}" for i in range(1, 5)] + ["메인_1", "메인_2"]
CASINO_GAMES = ["블랙잭", "슬롯", "룰렛", "바카라"]
CROPS = ["감자", "당근", "황금옥수수", "수박", "특수토마토"]
PART_NAMES = ["기본릴", "강화릴", "S등급릴", "기본낚싯줄", "탄소낚싯줄", "기본미끼", "고급미끼"]
FORAGE_TYPES = ["산열매", "약초", "버섯", "조개", "고대유물"]
TRAP_REGIONS = ["동쪽만", "서쪽항구", "심해", "하구", "산호초"]
DRILL_TIERS = ["기본드릴", "강화드릴", "마스터드릴"]
ORE_NAMES = ["돌", "석탄", "철", "금", "다이아몬드", "흑정석"]
# shop.buy/sell 품목 — shop 필드로 구분(섬상점=island, 드릴상점=drill), 가격대는 대략 현실감 있게.
ISLAND_SHOP_ITEMS = {"나무울타리": (500, 2000), "보더확장권": (50000, 200000), "작물비료": (200, 1000),
                     "가구세트A": (3000, 15000), "가구세트B": (5000, 25000), "호퍼업그레이드": (20000, 80000)}
DRILL_SHOP_ITEMS = {"드릴연료": (300, 1500), "드릴필터": (1000, 5000), "드릴강화키트": (8000, 30000)}
# 추천상점(shopId="추천") 품목 — 2026-07-28까지 shop.buy가 island로 뭉뚱그려 로깅되던 버그 재현/검증용.
RECOMMEND_SHOP_ITEMS = {"신호기": (30000, 60000), "전달체": (15000, 35000)}
# 유저마켓 등록 품목 — 물고기/조합재료류만 거래 가능(§8-6 tradeable() 게이트와 동일 전제).
MARKET_ITEMS = {"S등급 물고기": (15000, 40000), "M등급 물고기": (40000, 90000), "고급낚싯줄뭉치": (2000, 8000),
                "조합재료뭉치": (1000, 5000), "희귀조개껍질": (5000, 20000)}
GENERIC_MATS = ["철괴", "다이아몬드블록", "레드스톤블록"]  # 직거래에서 가치 unknown 케이스 생성용(가격 카탈로그 없음)


def rand_uuid(rng):
    return str(uuidlib.UUID(int=rng.getrandbits(128), version=4))


def build_stats_db(rng, days, players):
    path = os.path.join(OUT_DIR, "export", "stats-latest.db")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = sqlite3.connect(path)
    c.executescript("""
    CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);
    CREATE TABLE day_type (date TEXT NOT NULL, type TEXT NOT NULL, n INTEGER NOT NULL, players INTEGER NOT NULL,
        PRIMARY KEY(date, type));
    CREATE TABLE day_player (date TEXT NOT NULL, uuid TEXT NOT NULL, name TEXT,
        playtime_s INTEGER, afk_s INTEGER, casts INTEGER, catches INTEGER, best_grade TEXT,
        xp_fish REAL, money_in INTEGER, money_out INTEGER, casino_net INTEGER,
        quests_done INTEGER, crafts INTEGER, submits INTEGER, PRIMARY KEY(date, uuid));
    CREATE TABLE player_snapshot (date TEXT NOT NULL, uuid TEXT NOT NULL, name TEXT,
        level INTEGER, cur_exp REAL, money INTEGER, cash INTEGER, coins INTEGER,
        max_combo INTEGER, total_fish INTEGER, dex_fish INTEGER, skills TEXT, extra TEXT,
        PRIMARY KEY(date, uuid));
    CREATE TABLE guild_snapshot (date TEXT NOT NULL, guild_id TEXT NOT NULL, name TEXT,
        members INTEGER, treasury INTEGER, submit_total INTEGER, submit_season INTEGER,
        score INTEGER, level INTEGER, PRIMARY KEY(date, guild_id));
    """)

    people = [(rand_uuid(rng), NAMES[i % len(NAMES)] + (str(i) if i >= len(NAMES) else ""))
              for i in range(players)]

    import datetime
    today = datetime.date.today()
    for d in range(days):
        date = (today - datetime.timedelta(days=d)).isoformat()
        active = rng.sample(people, k=max(1, int(len(people) * rng.uniform(0.4, 0.9))))
        type_counts = {}
        for u, name in active:
            playtime = rng.randint(300, 14400)
            afk = int(playtime * rng.uniform(0, 0.15))
            casts = rng.randint(5, 400)
            catches = int(casts * rng.uniform(0.5, 0.9))
            grade = rng.choices(GRADES, weights=[30, 25, 18, 12, 8, 4, 1.5, 0.4, 0.1])[0]
            money_in = rng.randint(0, 500000)
            money_out = rng.randint(0, 300000)
            casino_net = rng.randint(-50000, 50000) if rng.random() < 0.3 else 0
            quests = rng.randint(0, 5)
            crafts = rng.randint(0, 8)
            submits = rng.randint(0, 3)
            c.execute("""INSERT INTO day_player(date,uuid,name,playtime_s,afk_s,casts,catches,best_grade,
                xp_fish,money_in,money_out,casino_net,quests_done,crafts,submits)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (date, u, name, playtime, afk, casts, catches, grade,
                       rng.uniform(100, 5000), money_in, money_out, casino_net, quests, crafts, submits))
            for t in ["fish.cast", "fish.result", "money.txn", "quest.done", "sess.end"]:
                type_counts[t] = type_counts.get(t, 0) + rng.randint(1, casts if t.startswith("fish") else 5)
        for t, n in type_counts.items():
            c.execute("INSERT INTO day_type(date,type,n,players) VALUES(?,?,?,?)",
                      (date, t, n, len(active)))

    for u, name in people:
        c.execute("""INSERT INTO player_snapshot(date,uuid,name,level,cur_exp,money,cash,coins,
            max_combo,total_fish,dex_fish,skills,extra) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (today.isoformat(), u, name, rng.randint(1, 100), rng.uniform(0, 1000),
                   rng.randint(1000, 50_000_000), rng.randint(0, 5000), rng.randint(0, 200),
                   rng.randint(1, 40), rng.randint(10, 3000), rng.randint(5, 683), "{}", "{}"))

    for i, gname in enumerate(["춘천길드", "바르칸원정대", "물고기조합"]):
        c.execute("""INSERT INTO guild_snapshot(date,guild_id,name,members,treasury,submit_total,
            submit_season,score,level) VALUES(?,?,?,?,?,?,?,?,?)""",
                  (today.isoformat(), f"guild_{i}", gname, rng.randint(2, 15), rng.randint(0, 10_000_000),
                   rng.randint(0, 500), rng.randint(0, 80), rng.randint(0, 10000), rng.randint(1, 20)))

    c.execute("INSERT INTO meta(k,v) VALUES('last_player_snapshot_date', ?)", (today.isoformat(),))
    c.execute("INSERT INTO meta(k,v) VALUES('last_rollup_date', ?)", ((today - datetime.timedelta(days=1)).isoformat(),))
    c.execute("INSERT INTO meta(k,v) VALUES('last_export_date', ?)", (today.isoformat(),))
    c.commit()
    c.close()
    return people


def build_events_db(rng, people, month_key, n_events):
    path = os.path.join(OUT_DIR, f"events-{month_key}.db")
    c = sqlite3.connect(path)
    c.executescript("""
    CREATE TABLE ev (id INTEGER PRIMARY KEY, ts INTEGER NOT NULL, type TEXT NOT NULL,
        uuid TEXT, name TEXT, world TEXT, region TEXT, ctx TEXT);
    CREATE INDEX ix_ev_type_ts ON ev(type, ts);
    CREATE INDEX ix_ev_uuid_ts ON ev(uuid, ts);
    CREATE TABLE loadout (hash TEXT PRIMARY KEY, json TEXT NOT NULL, first_ts INTEGER);
    CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);
    """)

    import time
    now_ms = int(time.time() * 1000)
    span_ms = 30 * 86400 * 1000

    # 로드아웃 사전(각 rod x enh 조합 1개씩)
    loadouts = []
    for rod in RODS:
        for enh in ENHS:
            h = f"{abs(hash((rod, enh))) % 10_000_000:07x}"
            loadouts.append((h, rod, enh))
            c.execute("INSERT OR IGNORE INTO loadout(hash,json,first_ts) VALUES(?,?,?)",
                      (h, json.dumps({"rod": rod, "enh": enh}, ensure_ascii=False), now_ms - span_ms))

    def ins(ts, etype, u, name, ctx, op=0):
        ctx = dict(ctx)
        ctx["op"] = op
        c.execute("INSERT INTO ev(ts,type,uuid,name,world,region,ctx) VALUES(?,?,?,?,?,?,?)",
                  (ts, etype, u, name, "world", "바르칸", json.dumps(ctx, ensure_ascii=False)))

    for _ in range(n_events):
        ts = now_ms - rng.randint(0, span_ms)
        u, name = rng.choice(people)
        op = 1 if rng.random() < 0.03 else 0  # 3%는 OP 테스트 행동 섞음(필터 검증용)
        kind = rng.choices(
            ["fish", "money", "quest", "casino", "crop", "part", "enh", "level",
             "forage", "trap_place", "trap_collect", "trap_break", "mine", "imine",
             "shop_buy_island", "shop_sell_island", "shop_buy_drill", "shop_buy_recommend",
             "market_listing", "trade_done", "check_issue", "check_deposit", "xfer"],
            weights=[35, 20, 10, 10, 8, 7, 5, 5, 8, 3, 4, 1, 6, 4, 6, 3, 3, 3,
                     7, 5, 4, 3, 4])[0]

        if kind == "fish":
            h, rod, enh = rng.choice(loadouts)
            # ★2026-07-29: 실제 Java(GradeRoller.Result.matchedProb)는 0~100 퍼센트 스케일로
            # ctx.prd.p에 저장한다 — 여기서 0~1 소수로 만들었더니 샌드박스가 실제 스케일 버그를
            # 재현 못 해서 prod에 나가서야 발견됐다(7000%대 표시 사고). 반드시 퍼센트 스케일 유지.
            p_pct = round(rng.uniform(2, 95), 2)
            gu = 1 if rng.random() < p_pct / 100.0 else 0
            res = rng.choices(["성공", "도주", "대기"], weights=[70, 20, 10])[0]
            ins(ts, "fish.cast", u, name, {"lo": h})
            ins(ts, "fish.result", u, name, {
                "res": res, "g": rng.choice(GRADES) if res == "성공" else None,
                "lo": h, "price": rng.randint(100, 200000),
                "prd": {"p": p_pct}, "gu": gu,
            }, op=op)
        elif kind == "money":
            # ★2026-07-28 유저 발견 버그 재현용 — 골드 말고도 캐시/잠수포인트가 실제로 존재하는
            # 별개 재화라(cur 필드로 구분), 샌드박스도 세 종류 다 섞어서 만들어야 economy 페이지의
            # 재화별 분리 섹션을 제대로 검증할 수 있다.
            cur_roll = rng.random()
            if cur_roll < 0.08:
                cur, reason = "cash", rng.choice(["캐시상점", "이벤트지급"])
                delta = rng.choice([-1, 1]) * rng.randint(100, 5000)
            elif cur_roll < 0.14:
                cur, reason = "afkp", rng.choice(["잠수적립", "잠수상점"])
                delta = rng.randint(1, 60) if reason == "잠수적립" else -rng.randint(10, 300)
            else:
                cur = "money"
                reason = rng.choices(MONEY_REASONS, weights=[REASON_PROFILE[r]["weight"] for r in MONEY_REASONS])[0]
                profile = REASON_PROFILE[reason]
                amount = rng.randint(*profile["amount"])
                sign = profile["sign"]
                if sign == "+":
                    delta = amount
                elif sign == "-":
                    delta = -amount
                else:
                    delta = amount * rng.choice([1, -1])  # ± 방향(이관/송금/카지노) — 개별은 랜덤, 총합은 대략 상쇄
            ins(ts, "money.txn", u, name, {"cur": cur, "d": delta, "after": rng.randint(0, 50_000_000),
                                           "r": reason}, op=op)
        elif kind == "quest":
            ins(ts, "quest.done", u, name, {"qid": rng.choice(QUEST_IDS),
                                            "rw": {"money": rng.randint(500, 50000)},
                                            "dur_s": rng.randint(30, 3600)}, op=op)
        elif kind == "casino":
            bet = rng.randint(1000, 100000)
            net = int(bet * rng.uniform(-1, 0.9))
            ins(ts, "casino.round", u, name, {"game": rng.choice(CASINO_GAMES), "bet": bet,
                                              "net": net, "rake": int(bet * 0.02)}, op=op)
        elif kind == "crop":
            ins(ts, "crop.harvest", u, name, {"crop": rng.choice(CROPS), "qty": rng.randint(1, 20),
                                              "grow_actual_s": rng.randint(60, 7200)}, op=op)
        elif kind == "part":
            ins(ts, "part.buy", u, name, {"name": rng.choice(PART_NAMES)}, op=op)
        elif kind == "enh":
            # 강화 레벨(from)이 높을수록 성공확률이 낮아지는 현실적 곡선(0강→11강, C10 "몇강" 집계용).
            # res는 실제 스키마대로 success/keep(유지)/down(하락) 3종(§8-3) — "fail" 문자열은 쓰지 않음.
            enh_from = rng.randint(0, 11)
            # ★2026-07-29: 실제 Java(EnhanceManager.doEnhance의 succ)도 0~100 퍼센트 스케일 —
            # fish.result와 같은 이유로 여기도 퍼센트로 유지(0~1 소수 아님).
            p_succ_pct = round(max(12.0, 95.0 - enh_from * 7.0) + rng.uniform(-3, 3), 2)
            if rng.random() < p_succ_pct / 100.0:
                res, enh_to = "success", enh_from + 1
            else:
                res, enh_to = rng.choices(["keep", "down"], weights=[75, 25])[0], enh_from
                if res == "down":
                    enh_to = max(0, enh_from - 1)
            ins(ts, "enh.attempt", u, name, {"p_succ": p_succ_pct, "res": res, "from": enh_from, "to": enh_to}, op=op)
        elif kind == "level":
            to = rng.randint(2, 100)
            ins(ts, "level.up", u, name, {"sys": "낚시", "from": to - 1, "to": to}, op=op)
        elif kind == "forage":
            # 타입별로 성공률에 살짝 차이를 둬서(고대유물이 제일 희소) C11에서 뭔가 비교할 거리가 생기게.
            ftype = rng.choice(FORAGE_TYPES)
            ok_p = {"고대유물": 0.35, "조개": 0.55}.get(ftype, 0.7)
            ok = 1 if rng.random() < ok_p else 0
            rare = 1 if (ok and rng.random() < 0.08) else 0
            ins(ts, "forage.do", u, name, {
                "type": ftype, "ok": ok, "rare": rare,
                "qty": rng.randint(1, 5) if ok else 0,
                "strikes": rng.randint(1, 8), "dur_ms": rng.randint(2000, 15000),
                "cool_skip": 1 if rng.random() < 0.05 else 0,
            }, op=op)
        elif kind == "trap_place":
            ins(ts, "trap.place", u, name, {"region": rng.choice(TRAP_REGIONS),
                                            "dur_left": rng.randint(600, 3600)}, op=op)
        elif kind == "trap_collect":
            n_caught = rng.randint(1, 6)
            by_g = {}
            for _ in range(n_caught):
                g = rng.choice(GRADES[:5])  # 통발은 저등급 위주(E~A)로 현실적으로 제한
                by_g[g] = by_g.get(g, 0) + 1
            ins(ts, "trap.collect", u, name, {"region": rng.choice(TRAP_REGIONS), "n": n_caught,
                                              "by_g": by_g, "dur_left": rng.randint(0, 1800),
                                              "wait_s": rng.randint(600, 7200)}, op=op)
        elif kind == "trap_break":
            ins(ts, "trap.break", u, name, {"region": rng.choice(TRAP_REGIONS)}, op=op)
        elif kind == "mine":
            tier = rng.choice(DRILL_TIERS)
            tier_mult = {"기본드릴": 1.0, "강화드릴": 1.6, "마스터드릴": 2.4}[tier]
            ores = {}
            for ore in rng.sample(ORE_NAMES, k=rng.randint(1, 3)):
                ores[ore] = int(rng.randint(2, 12) * tier_mult)
            n_total = sum(ores.values())
            ins(ts, "mine.min", u, name, {"tier": tier, "ores": ores, "n": n_total,
                                          "chain": rng.randint(1, 20), "vein": rng.randint(0, 5),
                                          "xp": round(n_total * rng.uniform(0.8, 1.5), 1)}, op=op)
        elif kind == "imine":
            ores = {}
            for ore in rng.sample(ORE_NAMES, k=rng.randint(1, 2)):
                ores[ore] = rng.randint(1, 8)
            n_total = sum(ores.values())
            ins(ts, "imine.min", u, name, {"ores": ores, "n": n_total,
                                           "xp": round(n_total * rng.uniform(0.5, 1.0), 1),
                                           "capped": 1 if rng.random() < 0.15 else 0}, op=op)
        elif kind == "shop_buy_island":
            item = rng.choice(list(ISLAND_SHOP_ITEMS.keys()))
            unit_lo, unit_hi = ISLAND_SHOP_ITEMS[item]
            n_buy = rng.randint(1, 5)
            unit = rng.randint(unit_lo, unit_hi)
            ins(ts, "shop.buy", u, name, {"shop": "island", "item": item, "n": n_buy, "price": unit * n_buy}, op=op)
        elif kind == "shop_sell_island":
            # IslandShopGui는 되팔기도 지원(§조사) — 되팔 때는 원가의 절반 수준으로.
            item = rng.choice(list(ISLAND_SHOP_ITEMS.keys()))
            unit_lo, unit_hi = ISLAND_SHOP_ITEMS[item]
            n_sell = rng.randint(1, 3)
            unit = int(rng.randint(unit_lo, unit_hi) * 0.5)
            ins(ts, "shop.sell", u, name, {"shop": "island", "item": item, "n": n_sell, "price": unit * n_sell}, op=op)
        elif kind == "shop_buy_drill":
            item = rng.choice(list(DRILL_SHOP_ITEMS.keys()))
            unit_lo, unit_hi = DRILL_SHOP_ITEMS[item]
            n_buy = rng.randint(1, 4)
            unit = rng.randint(unit_lo, unit_hi)
            ins(ts, "shop.buy", u, name, {"shop": "drill", "item": item, "n": n_buy, "price": unit * n_buy}, op=op)
        elif kind == "shop_buy_recommend":
            # 추천상점(shopId="추천") — IslandShopGui.shopTag() 수정 전엔 이것도 "island"로 찍혀서
            # 섬상점과 안 구분됐던 버그를 재현/검증(2026-07-28 유저 발견+수정).
            item = rng.choice(list(RECOMMEND_SHOP_ITEMS.keys()))
            unit_lo, unit_hi = RECOMMEND_SHOP_ITEMS[item]
            n_buy = rng.randint(1, 3)
            unit = rng.randint(unit_lo, unit_hi)
            ins(ts, "shop.buy", u, name, {"shop": "recommend", "item": item, "n": n_buy, "price": unit * n_buy}, op=op)
        elif kind == "market_listing":
            # list + 결과(판매/취소/만료)를 같은 id로 묶어서 한 번에 생성 — C17의 시간조인 검증용.
            # list_ts에 여유(최소 3일)를 둬서 48시간 뒤 만료여도 지금(now_ms) 이전에 들어오게 함.
            item = rng.choice(list(MARKET_ITEMS.keys()))
            price = rng.randint(*MARKET_ITEMS[item])
            qty = rng.randint(1, 5)
            listing_id = f"m{rng.getrandbits(32):08x}"
            list_ts = now_ms - rng.randint(3 * 86400_000, span_ms)
            ins(list_ts, "market.list", u, name, {"id": listing_id, "item": item, "price": price, "qty": qty}, op=op)
            fate = rng.choices(["sold", "cancelled", "expired"], weights=[55, 20, 25])[0]
            if fate == "sold":
                buyer_u, buyer_name = rng.choice(people)
                outcome_ts = list_ts + rng.randint(60_000, 47 * 3600_000)
                fee = int(price * 0.10)
                ins(outcome_ts, "market.buy", buyer_u, buyer_name, {
                    "id": listing_id, "item": item, "price": price, "fee": fee, "qty": qty,
                    "seller_uuid": u, "seller_online": rng.choice([0, 1]),
                }, op=op)
            elif fate == "cancelled":
                outcome_ts = list_ts + rng.randint(60_000, 24 * 3600_000)
                ins(outcome_ts, "market.cancel", u, name, {"id": listing_id, "item": item, "price": price, "qty": qty}, op=op)
            else:
                outcome_ts = list_ts + 48 * 3600_000
                ins(outcome_ts, "market.expire", u, name, {"id": listing_id, "item": item, "price": price,
                                                           "qty": qty, "to_mail": rng.choice([0, 1])}, op=op)
        elif kind == "trade_done":
            # 대부분은 수표/물고기끼리(가치를 아는) 거래라 fully-priced, 가끔 일반 아이템을 섞어 unknown 케이스도 생성.
            buyer_u, buyer_name = rng.choice([pp for pp in people if pp[0] != u] or people)

            def _rand_items(fair_bias):
                items = []
                for _ in range(rng.randint(1, 3)):
                    r = rng.random()
                    if r < 0.5:
                        face = rng.choice([1000, 5000, 10000, 50000, 100000, 500000])
                        items.append({"mat": "PAPER", "n": 1, "value": face, "value_src": "check"})
                    elif r < 0.85:
                        grade = rng.choice(GRADES)
                        price = {"E": 100, "D": 250, "C": 600, "B": 2000, "A": 6000,
                                 "S": 20000, "M": 65000, "L": 170000, "G": 450000}[grade]
                        items.append({"mat": "COD", "n": 1, "value": price, "value_src": "fish"})
                    else:
                        items.append({"mat": rng.choice(GENERIC_MATS), "n": rng.randint(1, 8)})  # value 없음(unknown)
                return items

            items_a = _rand_items(True)
            items_b = _rand_items(True)
            # 가끔(15%) 의도적으로 편측 거래를 만들어 C18 탐지기가 실제로 뭔가 잡아내게 함.
            if rng.random() < 0.15 and items_a and items_b:
                items_a[0]["value"] = (items_a[0].get("value") or 1000) * rng.randint(20, 80)
                items_a[0]["value_src"] = items_a[0].get("value_src", "check")
            value_a = sum(it.get("value", 0) for it in items_a)
            value_b = sum(it.get("value", 0) for it in items_b)
            unknown_a = sum(1 for it in items_a if "value" not in it)
            unknown_b = sum(1 for it in items_b if "value" not in it)
            ins(ts, "trade.done", u, name, {
                "a": name, "b": buyer_name, "items_a": items_a, "items_b": items_b,
                "value_a": value_a, "value_b": value_b, "unknown_a": unknown_a, "unknown_b": unknown_b,
            }, op=op)
        elif kind == "check_issue":
            face = rng.choice([1000, 5000, 10000, 50000, 100000, 500000, 1000000])
            n_notes = rng.randint(1, 10)
            fee = int(face * n_notes * 0.10 + 0.999)
            ins(ts, "check.issue", u, name, {"face": face, "n": n_notes, "fee": fee}, op=op)
        elif kind == "check_deposit":
            face = rng.choice([1000, 5000, 10000, 50000, 100000, 500000, 1000000])
            n_notes = rng.randint(1, 10)
            ins(ts, "check.deposit", u, name, {"face": face, "n": n_notes}, op=op)
        elif kind == "xfer":
            target_u, target_name = rng.choice(people)
            amt = rng.randint(1000, 2_000_000)
            via = rng.choices(["transfer_cmd", "money_cmd"], weights=[40, 60])[0]  # money_cmd(수수료0%)가 더 흔함=우회 유인
            fee = int(amt * 0.10) if via == "transfer_cmd" else 0
            ins(ts, "xfer.send", u, name, {"to": target_name, "amt": amt, "fee": fee, "via": via}, op=op)

    # 세션 종료(성장곡선 C1 조인용) — 플레이어별로 몇 개씩
    for u, name in people:
        for _ in range(rng.randint(3, 15)):
            ts = now_ms - rng.randint(0, span_ms)
            dur = rng.randint(300, 10800)
            ins(ts, "sess.end", u, name, {"dur_s": dur, "afk_s": int(dur * rng.uniform(0, 0.1))})

    c.commit()
    c.close()


def main():
    ap = argparse.ArgumentParser(description="statsweb 샌드박스용 가짜 텔레메트리 생성")
    ap.add_argument("--days", type=int, default=14, help="day_player/day_type 롤업 일수")
    ap.add_argument("--players", type=int, default=12, help="가짜 플레이어 수")
    ap.add_argument("--events-per-month", type=int, default=4000, help="월별 ev 이벤트 개수")
    ap.add_argument("--seed", type=int, default=42, help="난수 시드(재현성)")
    args = ap.parse_args()

    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)

    rng = random.Random(args.seed)
    people = build_stats_db(rng, args.days, args.players)

    import datetime
    today = datetime.date.today()
    months = {today.strftime("%Y-%m"), (today.replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m")}
    for mk in months:
        build_events_db(rng, people, mk, args.events_per_month)

    print(f"샌드박스 데이터 생성 완료: {OUT_DIR}")
    print(f"  플레이어 {len(people)}명 · {args.days}일 롤업 · 월별 이벤트 {args.events_per_month}건 x {len(months)}개월")
    print("실행: cd ../statsweb && ./run_sandbox.sh")


if __name__ == "__main__":
    main()
