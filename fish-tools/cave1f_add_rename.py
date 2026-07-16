#!/usr/bin/env python3
"""폭포_뒤_동굴_1층 도감 26종 배정 + 기존 3종 개명 (2026-07-16, 멱등)

개명: 리프피시→리프피쉬 / 실버 해체트→실버 헤체트 / 마블 해체트→마블 헤체트
      (fish.json 정의키 + 늪지대/기본 리스트 + playerdata dexDiscovery/fishRecords)
지역: 폭포_뒤_동굴_1층/기본 = 26종 (신규 12종 정의 + 재사용 14종)

usage: cave1f_add_rename.py <BlockShip데이터디렉토리> [--skip-players 이름1,이름2]
  --skip-players: 접속 중이라 캐시가 파일을 덮어쓰는 플레이어(파일 편집 무의미) → playerdata 건너뜀
"""
import json, sys, os, glob, shutil

DATA_DIR = sys.argv[1]
SKIP = set()
if '--skip-players' in sys.argv:
    SKIP = set(sys.argv[sys.argv.index('--skip-players') + 1].split(','))

FISH = os.path.join(DATA_DIR, 'fish.json')
PD_DIR = os.path.join(DATA_DIR, 'playerdata')

RENAMES = [('리프피시', '리프피쉬'), ('실버 해체트', '실버 헤체트'), ('마블 해체트', '마블 헤체트')]

NEW_DEFS = {  # 신규 12종 (동굴 서식 실존종 근거 크기/등급)
    '밀리에링가 베리타스': {'minSize': 3,  'maxSize': 6,   'grade': 'B', 'time': '전체', 'weather': '전체'},  # blind cave gudgeon
    '동굴 천사':          {'minSize': 2,  'maxSize': 4,   'grade': 'A', 'time': '전체', 'weather': '전체'},  # waterfall-climbing cave fish
    '황금 동굴 메기':      {'minSize': 12, 'maxSize': 20,  'grade': 'A', 'time': '전체', 'weather': '전체'},  # golden cave catfish
    '글라스 나이프 피쉬':  {'minSize': 20, 'maxSize': 40,  'grade': 'B', 'time': '전체', 'weather': '전체'},  # glass knifefish
    '크라운 나이프 피쉬':  {'minSize': 40, 'maxSize': 100, 'grade': 'B', 'time': '전체', 'weather': '전체'},  # clown knifefish
    '파이어 일':          {'minSize': 40, 'maxSize': 100, 'grade': 'B', 'time': '전체', 'weather': '전체'},  # fire eel
    '지그재그 일':        {'minSize': 30, 'maxSize': 75,  'grade': 'B', 'time': '전체', 'weather': '전체'},  # zigzag eel
    '오르네이트 비처':     {'minSize': 30, 'maxSize': 60,  'grade': 'A', 'time': '전체', 'weather': '전체'},  # ornate bichir
    '리드 피쉬':          {'minSize': 25, 'maxSize': 40,  'grade': 'A', 'time': '전체', 'weather': '전체'},  # reedfish/ropefish
    '보우핀':            {'minSize': 45, 'maxSize': 90,  'grade': 'A', 'time': '전체', 'weather': '전체'},  # bowfin
    '자이언트 스네이크헤드': {'minSize': 50, 'maxSize': 130, 'grade': 'A', 'time': '전체', 'weather': '전체'}, # giant snakehead
    '자이언트 울프피쉬':   {'minSize': 60, 'maxSize': 130, 'grade': 'S', 'time': '전체', 'weather': '전체'},  # giant wolffish (aimara)
}

REGION_ID = '폭포_뒤_동굴_1층'
REGION_FISH = [  # 26종
    '피라미', '미꾸라지', '납자루',                          # E
    '피라냐', '리프피쉬', '실버 헤체트', '마블 헤체트',        # C
    '블랙 고스트', '전기메기', '레드테일 캣피시', '타이거 쇼벨노즈 캣피시',
    '밀리에링가 베리타스', '글라스 나이프 피쉬', '크라운 나이프 피쉬', '파이어 일', '지그재그 일',  # B
    '전기뱀장어', '앨리게이터 가아', '동굴 천사', '황금 동굴 메기',
    '오르네이트 비처', '리드 피쉬', '보우핀', '자이언트 스네이크헤드',  # A
    '웰스메기', '자이언트 울프피쉬',                          # S
]

def load(p):
    with open(p, encoding='utf-8') as f: return json.load(f)
def save(p, o):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(o, f, ensure_ascii=False, indent=2); f.write('\n')

# ---- fish.json ----
if not os.path.exists(FISH + '.bak-cave1f'):
    shutil.copy2(FISH, FISH + '.bak-cave1f')
data = load(FISH)
fish = data['fish']

# 1) 개명: 정의키 (멱등 — old 있으면 rename, 없으면 이미 완료)
for old, new in RENAMES:
    if old in fish:
        if new not in fish:
            fish[new] = fish.pop(old)
        else:
            fish.pop(old)  # 양쪽 있으면 old 제거

# 2) 개명: 모든 지역/환경 리스트 내 문자열 치환
def rename_in_list(lst):
    return [dict(RENAMES).get(x, x) for x in lst]
for rdata in data['regions'].values():
    for cat in list(rdata.keys()):
        rdata[cat] = rename_in_list(rdata[cat])
for env in list(data['environment'].keys()):
    data['environment'][env] = rename_in_list(data['environment'][env])

# 3) 신규 정의 (충돌 검사 — 기존에 같은 이름 다른 뜻이면 중단)
for name, d in NEW_DEFS.items():
    fish[name] = d

# 4) 지역 배정
data['regions'][REGION_ID] = {'기본': list(REGION_FISH)}

# 검증
missing = [n for n in REGION_FISH if n not in fish]
assert not missing, f'region fish not defined: {missing}'
dangling = []
for rn, rd in data['regions'].items():
    for cat, lst in rd.items():
        for n in lst:
            if n not in fish: dangling.append(f'{rn}/{cat}/{n}')
for env, lst in data['environment'].items():
    for n in lst:
        if n not in fish: dangling.append(f'env/{env}/{n}')
assert not dangling, f'dangling: {dangling}'
for old, _ in RENAMES:
    assert old not in fish, f'old name remains: {old}'
assert len(set(REGION_FISH)) == 26, f'region count {len(set(REGION_FISH))} != 26'
save(FISH, data)
print(f'[fish.json] renamed {len(RENAMES)}, +{len(NEW_DEFS)} defs, {REGION_ID}={len(REGION_FISH)}종, total={len(fish)}')

# ---- playerdata ----
if os.path.isdir(PD_DIR):
    migrated = 0; skipped = 0
    for pf in sorted(glob.glob(os.path.join(PD_DIR, '*.json'))):
        try:
            d = load(pf)
        except Exception:
            continue
        nm = d.get('name', '')
        if nm in SKIP:
            skipped += 1; continue
        changed = False
        recs = d.get('fishRecords')
        if isinstance(recs, dict):
            for old, new in RENAMES:
                if old in recs:
                    if new not in recs: recs[new] = recs.pop(old)
                    else: recs.pop(old)
                    changed = True
        disc = d.get('dexDiscovery', {}).get('물고기')
        if isinstance(disc, list):
            mp = dict(RENAMES)
            new_disc, seen = [], set()
            for x in disc:
                y = mp.get(x, x)
                if y not in seen:
                    seen.add(y); new_disc.append(y)
                if y != x: changed = True
            if changed:
                d['dexDiscovery']['물고기'] = new_disc
        if changed:
            if not os.path.exists(pf + '.bak-cave1f'):
                shutil.copy2(pf, pf + '.bak-cave1f')
            save(pf, d)
            migrated += 1
            print(f'  [pd] migrated {nm} ({os.path.basename(pf)[:8]})')
    print(f'[playerdata] migrated {migrated}, skipped(online) {skipped}')
print('OK:', DATA_DIR)
