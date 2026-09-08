#!/usr/bin/env python3
"""BarkanChess(보드게임) 업스트림 jar 의 «번들 기본 config» 에서 board-resource-pack 을 끈다.

## 왜 필요한가 (2026-09-09)
1.8.0 번들 config.yml 기본값이 이렇게 왔다:

    board-resource-pack:
      enabled: true
      url: http://25.25.82.193:8123/BarkanBoardGames-ResourcePack-1.21.11.zip
      required: true
      delay-ticks: 80

25.0.0.0/8 은 원저자 개인망(하마치)이다 — 우리 플레이어는 절대 못 받는다. 그런데
`required: true` 라서 다운로드가 실패하면 **클라이언트가 스스로 연결을 끊는다**(플러그인에
킥 코드가 있는 게 아니라 바닐라 동작). 접속 80틱 후에 걸리니 전원 접속 직후 튕김이 된다.

★라이브 `plugins/BarkanChess/config.yml` 에 이 섹션이 «없다»는 건 안전장치가 아니다 —
JavaPlugin.reloadConfig() 가 jar 리소스를 `setDefaults` 로 항상 뒤에 깔기 때문에 없는 키는
번들 기본값으로 해석된다. 그래서 라이브 config 를 고치는 대신(구 jar 이 종료 때 saveConfig
하면 내 편집이 메모리에 없어 날아간다) **기본값 자체를 끈다.**

우리 보드게임 말 모델은 이미 메인 리소스팩에 있다(CLAUDE.md: PAPER custom_model_data
21001~22301). 팩을 3개로 늘리지 않는 것이 이 서버 규칙이다.

바이트코드는 건드리지 않는다 — config.yml 엔트리 하나만 교체하고 나머지는 원본 그대로
복사한다. 그래서 tools/check-upstream-constants.sh 결과가 바뀌지 않는다.

사용: ops/patch-boardgames-pack-default.py <jar> [출력jar]
"""
import re, shutil, sys, zipfile
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src
tmp = dst.with_name(dst.name + '.patching')

with zipfile.ZipFile(src) as z:
    names = z.namelist()
    if 'config.yml' not in names:
        sys.exit('🔴 jar 에 config.yml 이 없다 — 업스트림 구조가 바뀌었다. 수동 확인할 것.')
    cfg = z.read('config.yml').decode('utf-8')

    if not re.search(r'^board-resource-pack:', cfg, re.M):
        sys.exit('🔴 board-resource-pack 섹션이 없다 — 이미 사라졌거나 이름이 바뀌었다.')
    # 그 섹션의 enabled 만 끈다 (다른 섹션의 enabled 를 건드리면 엔진이 꺼진다)
    new, n = re.subn(
        r'(^board-resource-pack:\n(?:[ \t]+.*\n)*?[ \t]+enabled:[ \t]*)true',
        r'\1false', cfg, flags=re.M)
    if n != 1:
        sys.exit(f'🔴 board-resource-pack.enabled: true 를 정확히 1곳 못 찾았다 (찾은 수 {n})')

    with zipfile.ZipFile(tmp, 'w') as out:
        for info in z.infolist():                    # 순서·압축방식 보존
            data = new.encode('utf-8') if info.filename == 'config.yml' else z.read(info.filename)
            ni = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            ni.compress_type = info.compress_type
            # ★권한 비트를 그대로 베끼면 안 된다. 업스트림 jar 은 create_system=0(DOS)이라
            #   external_attr 이 0 인데, writestr 은 0 을 보면 «0o600» 을 박아 넣는다
            #   → 디렉터리에 실행권한이 없어져 `unzip` 한 트리를 못 들어간다. 그래서
            #   tools/check-upstream-constants.sh 가 판정도 못 내리고 죽었다(2026-09-09).
            ni.create_system = info.create_system
            if info.external_attr:
                ni.external_attr = info.external_attr
            elif info.filename.endswith('/'):
                ni.external_attr = (0o755 << 16) | 0x10
            else:
                ni.external_attr = 0o644 << 16
            out.writestr(ni, data)

# 검산: config.yml 외 모든 엔트리가 바이트 동일해야 한다
with zipfile.ZipFile(src) as a, zipfile.ZipFile(tmp) as b:
    assert a.namelist() == b.namelist(), '엔트리 목록이 변했다'
    for nm in a.namelist():
        if nm == 'config.yml':
            continue
        assert a.read(nm) == b.read(nm), f'{nm} 이 변했다'
    got = b.read('config.yml').decode('utf-8')
diff = [(x, y) for x, y in zip(cfg.splitlines(), got.splitlines()) if x != y]
assert len(diff) == 1, f'config.yml 이 {len(diff)}줄 변했다 (1줄이어야 함)'
shutil.move(tmp, dst)
print(f'✓ board-resource-pack 기본값 차단: {diff[0][0].strip()} → {diff[0][1].strip()}')
print(f'  {dst}')
