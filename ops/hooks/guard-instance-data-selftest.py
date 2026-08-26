#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guard-instance-data.py 회귀 검사. `python3 이파일` — 실패 0건이어야 한다.

케이스는 전부 **실제로 있었던 명령 모양**에서 뽑았다. 새 사고가 나면 그 명령을
BLOCK 에 한 줄 추가하고, 오탐이 나면 ALLOW 에 추가할 것.

★주의: 이 파일 자체를 Bash 히어독으로 만들려 하면 훅이 아래 문자열을 실제 명령으로
  보고 차단한다(문자열과 명령을 구분할 방법이 없으므로 그게 옳은 동작이다). 편집기로 쓸 것.
"""
import json
import subprocess
import sys

H = ("/Users/user/Library/Application Support/feather/player-server/servers/"
     "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Skript/scripts/ops/hooks/"
     "guard-instance-data.py")
D = ("/Users/user/Library/Application Support/feather/player-server/servers/"
     "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
PROD = "ubuntu@168.107.8.107"
LIVE = "~/mcserver/plugins/BlockShip"

BLOCK = [
    ('사고재현: dev regions.json → prod',
     'scp -i ~/.ssh/oracle-mc.key "%s/regions.json" %s:%s/regions.json' % (D, PROD, LIVE)),
    ('사고재현: 목적지 디렉터리 + 4개 묶음 (08-25 실제 모양)',
     'scp -i ~/.ssh/oracle-mc.key "%s/materials.json" "%s/quests.json" "%s/recipes.json" '
     '"%s/regions.json" %s:%s/' % (D, D, D, D, PROD, LIVE)),
    ('BlockShip 폴더 통째 rsync dev→prod',
     'rsync -a "%s/" %s:%s/' % (D, PROD, LIVE)),
    ('islands.json 단독',
     'scp islands.json %s:%s/islands.json' % (PROD, LIVE)),
    ('playerdata 통째',
     'rsync -a ~/pd/ %s:%s/playerdata/' % (PROD, LIVE)),
    ('guilds.json (vip-billing DB 와 짝이라 더 위험)',
     'scp guilds.json %s:%s/guilds.json' % (PROD, LIVE)),
    ('prod → dev 역방향도 차단 (목적지가 dev 라이브)',
     'scp -i ~/.ssh/oracle-mc.key %s:%s/regions.json "%s/regions.json"' % (PROD, LIVE, D)),
    ('원격 셸 안 cp',
     "ssh %s 'cp /tmp/regions.json %s/regions.json'" % (PROD, LIVE)),
    ('리다이렉션',
     "ssh %s 'cat /tmp/r.json > %s/regions.json'" % (PROD, LIVE)),
    ('tar 로 plugins 에 풀기 (내용물 불명)',
     "ssh %s 'tar xzf b.tar.gz -C %s'" % (PROD, LIVE)),
    ('cp 로 dev 라이브에 쓰기',
     'cp /tmp/regions.json "%s/regions.json"' % D),
    ('여러 줄 중간에 섞인 진짜 위반',
     'echo start\ncp /tmp/regions.json %s/regions.json\necho done' % LIVE),
]

ALLOW = [
    ('조사용: prod → /tmp 로 받아오기',
     'scp -i ~/.ssh/oracle-mc.key %s:%s/regions.json /tmp/r.json' % (PROD, LIVE)),
    ('조사용: prod → scratchpad',
     'scp -i ~/.ssh/oracle-mc.key %s:%s/islands.json /private/tmp/claude-501/x/scratchpad/i.json'
     % (PROD, LIVE)),
    ('백업: prod 안에서 backups/ 로',
     "ssh %s 'cp %s/regions.json ~/mcserver/backups/regions-before.json'" % (PROD, LIVE)),
    ('정상 sync 대상만 손으로 올림 (npc/dialogue)',
     'scp npc.json dialogue.json %s:%s/' % (PROD, LIVE)),
    ('정식 배포 스크립트',
     '~/deploy-blockship.sh'),
    ('그냥 읽기',
     'ssh %s \'python3 -c "import json;print(len(json.load(open(\\"regions.json\\"))))"\'' % PROD),
    ('grep',
     'grep -n regions.json ops/deploy-blockship.sh'),
    ('jar 배포 (guard-live-jar.py 소관)',
     'scp BlockShip.jar %s:~/mcserver/staging/' % PROD),
    ('탈출구',
     'ALLOW_INSTANCE_DATA_WRITE=1 scp /tmp/regions.json %s:%s/regions.json' % (PROD, LIVE)),
    ('오프사이트 복원을 /tmp 에',
     "ssh %s 'tar xzf blockship.tar.gz -C /tmp/restore'" % PROD),
    # ★오탐 회귀: 줄바꿈을 절 경계로 안 보면 앞줄 cp 와 뒷줄 라이브 경로가 짝지어져 차단됐다.
    ('여러 줄: 라이브에서 /tmp 로 받고 뒷줄에 라이브 경로 언급',
     'mkdir -p /tmp/st\n'
     'cp %s/regions.json /tmp/st/regions.json\n'
     'python3 validate-staged.py /tmp/st/regions.json %s/regions.json\n'
     'cp %s/islands.json /tmp/st/islands.json\n'
     'python3 validate-staged.py /tmp/st/islands.json %s/islands.json' % (LIVE, LIVE, LIVE, LIVE)),
    ('게이트 스크립트 자체를 prod scripts/ 로 배포',
     'scp -q validate-staged.py guard-instance-data.py %s:~/mcserver/scripts/' % PROD),
]

CHECK_LIST_OK = ['npc.json', 'dialogue.json', 'titles.json', 'parts.json', 'enhance.json',
                 'recipes.json', 'materials.json', 'quests.json', 'item-flavor.json']
CHECK_LIST_BAD = ['npc.json', 'regions.json', 'islands.json']


def run(cmd):
    p = subprocess.run([sys.executable, H], input=json.dumps({"tool_input": {"command": cmd}}),
                       capture_output=True, text=True)
    return p.returncode


def run_list(names):
    p = subprocess.run([sys.executable, H, '--check-list'] + names,
                       capture_output=True, text=True)
    return p.returncode


def main():
    fail = 0
    print("=== 차단돼야 하는 것 ===")
    for name, c in BLOCK:
        rc = run(c)
        ok = rc == 2
        print(("  ✓ " if ok else "  ✗ FAIL(rc=%d) " % rc) + name)
        fail += 0 if ok else 1

    print("=== 허용돼야 하는 것 ===")
    for name, c in ALLOW:
        rc = run(c)
        ok = rc == 0
        print(("  ✓ " if ok else "  ✗ FAIL(rc=%d) " % rc) + name)
        fail += 0 if ok else 1

    print("=== --check-list (배포 스크립트 sync 목록 검산) ===")
    for name, names, want in (("현행 DATA_FILES 통과", CHECK_LIST_OK, 0),
                              ("regions/islands 끼면 거부", CHECK_LIST_BAD, 2)):
        rc = run_list(names)
        ok = rc == want
        print(("  ✓ " if ok else "  ✗ FAIL(rc=%d, want=%d) " % (rc, want)) + name)
        fail += 0 if ok else 1

    print()
    print("실패 %d건" % fail)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
