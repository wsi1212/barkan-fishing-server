#!/usr/bin/env python3
"""붉은사막 물고기 도감 100% 교체 (2026-07-14)
- 옛 21종 삭제(fish dict + 붉은사막 지역리스트) / 신규 10종 정의 추가 / 지역리스트 23종 재구성
- 퀘스트 4건 리타겟(사막12, 붉은사막03, 사막13, 사사이드_노파03) + 붉은사막02 문구 1줄
- dev/prod 양쪽 데이터 디렉토리에 동일 적용 가능(멱등). usage: redesert_dex_swap.py <BlockShip데이터디렉토리>
"""
import json, sys, os, shutil

DATA_DIR = sys.argv[1]
FISH = os.path.join(DATA_DIR, 'fish.json')
QUESTS = os.path.join(DATA_DIR, 'quests.json')

OLD = ['재비늘어','홍탄어','용흔어','흑요어','연무어','화결어','사막펍피시','염','흑점',
       '사구미꾸라지','모래참붕어','모래속잉어','사구의망둥이','검은불꽃붕어','제단의불씨',
       '재투성이메기','이프리트의눈물','이프리트의분노','텍사스시클리드','사막전갈게','사막칠성장어',
       '블라인드케이프피쉬']  # 피쉬→피시 네이밍 규칙(fish-rework.md) — 1차 적용분 정리

NEW_DEFS = {
    '송사리':           {'minSize': 3,   'maxSize': 7,   'grade': 'E',   'time': '전체', 'weather': '전체'},
    '크라운로치':        {'minSize': 15,  'maxSize': 35,  'grade': 'D',   'time': '전체', 'weather': '전체'},
    '블라인드케이프피시': {'minSize': 6,   'maxSize': 12,  'grade': 'C',   'time': '전체', 'weather': '전체'},
    '나이프피시':        {'minSize': 30,  'maxSize': 55,  'grade': 'C',   'time': '전체', 'weather': '전체'},
    '전기메기':          {'minSize': 40,  'maxSize': 90,  'grade': 'B',   'time': '전체', 'weather': '전체'},
    '가아':             {'minSize': 60,  'maxSize': 180, 'grade': 'B',   'time': '전체', 'weather': '전체'},
    '아로와나':          {'minSize': 40,  'maxSize': 70,  'grade': 'B',   'time': '전체', 'weather': '전체'},
    '폐어':             {'minSize': 60,  'maxSize': 150, 'grade': 'A',   'time': '전체', 'weather': '전체'},
    '실러캔스':          {'minSize': 100, 'maxSize': 200, 'grade': 'S',   'time': '전체', 'weather': '전체'},
    '자하린':           {'minSize': 12,  'maxSize': 150, 'grade': 'E~S', 'time': '전체', 'weather': '전체'},
}

REGION_ENTRY = {
    '기본': ['피라미','미꾸라지','송사리','납자루','버들치','붕어','쉬리','크라운로치',
            '블라인드케이프피시','나이프피시','메기','전기메기','가아','아로와나',
            '전기뱀장어','실버 아로와나','폐어','피라루쿠','블랙 아로와나','웰스메기',
            '실러캔스','자하린'],
    '밤맑음': ['망둑어'],
    '밤비': ['망둑어'],
    '통발': [],
}

QUEST_EDITS = {
    '사막12': {
        '설명': ['&7제단 주변, 오직 &f붉은사막&7에서만 잡히는',
                '&f나이프피시&7를 &f1마리&7 낚아',
                '&7오염의 정체를 살피세요.'],
        '목표': ['fish|나이프피시|아무|1|0'],
    },
    '붉은사막02': {
        '설명': ['&7붉은사막 물줄기의 어종은 본토와 전혀 다릅니다.',
                '&7붉은사막의 물고기 도감을 &f12종&7 채워',
                '&7이 땅의 생태를 익히세요.'],
    },
    '붉은사막03': {
        '이름': '&d심층의 보석',
        '설명': ['&7붉은사막 가장 깊은 곳, 동굴의 자수정빛이',
                '&7물속에 어른거립니다.',
                '&d자하린&7을 &f1마리&7 낚아 보석의 비밀을 확인하세요.'],
        '목표': ['fish|자하린|아무|1|0'],
    },
    '사막13': {
        '이름': '&6살아있는 전설',
        '설명': ['&7태고의 어종이 붉은사막 깊은 물에',
                '&7아직 살아 숨쉰다는 소문이 있습니다.',
                '&f실러캔스&7를 &f1마리&7 낚으세요.'],
        '목표': ['fish|실러캔스|아무|1|0'],
    },
    '사사이드_노파03': {
        '설명': ['&7불의 제단 물가에 성난 &f전기메기&7가 숨어 삽니다.',
                '&f전기메기&7를 &f1마리&7 잡으세요.'],
        '목표': ['fish|전기메기|아무|1|0'],
    },
}

def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)

def save(p, obj):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')

# ---- fish.json ----
if not os.path.exists(FISH + '.bak-redesert'):
    shutil.copy2(FISH, FISH + '.bak-redesert')
data = load(FISH)
removed = [n for n in OLD if data['fish'].pop(n, None) is not None]
for name, d in NEW_DEFS.items():
    data['fish'][name] = d
data['regions']['붉은사막'] = REGION_ENTRY

# 검증 1: 모든 지역 리스트/환경 리스트의 어종이 fish dict에 존재
dangling = []
for rname, rdata in data['regions'].items():
    for cat, lst in rdata.items():
        for n in lst:
            if n not in data['fish']:
                dangling.append(f'{rname}/{cat}/{n}')
for env, lst in data['environment'].items():
    for n in lst:
        if n not in data['fish']:
            dangling.append(f'env/{env}/{n}')
assert not dangling, f'dangling refs: {dangling}'
# 검증 2: 옛 이름 완전 소거
raw = json.dumps(data, ensure_ascii=False)
leftover = [n for n in OLD if n in raw and n not in ('염', '흑점')]
# '염'/'흑점'은 한 글자·두 글자라 다른 단어 부분 문자열로 오탐 가능 → 키 존재만 검사
assert '염' not in data['fish'] and '흑점' not in data['fish']
assert not leftover, f'old names remain: {leftover}'
save(FISH, data)
print(f'[fish.json] removed {len(removed)}/{len(OLD)} old defs, added {len(NEW_DEFS)} new, region set to {sum(len(v) for v in REGION_ENTRY.values())} entries')

# ---- quests.json ----
if not os.path.exists(QUESTS + '.bak-redesert'):
    shutil.copy2(QUESTS, QUESTS + '.bak-redesert')
q = load(QUESTS)
qq = q['퀘스트']
for qid, edits in QUEST_EDITS.items():
    assert qid in qq, f'quest missing: {qid}'
    qq[qid].update(edits)
raw = json.dumps(q, ensure_ascii=False)
for bad in ['검은불꽃붕어', '이프리트의눈물', '이프리트의분노']:
    assert bad not in raw, f'quest still references {bad}'
save(QUESTS, q)
print(f'[quests.json] updated {len(QUEST_EDITS)} quests')
print('OK:', DATA_DIR)
