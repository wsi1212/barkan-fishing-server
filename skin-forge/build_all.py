#!/usr/bin/env python3
"""스펙 모듈 전체를 돌려 out/ 을 다시 뽑는다.

★모듈마다 자기 build() 를 갖고 있어서(48개) 하나만 고치고 «다 됐다» 고 착각하기 쉽다.
  전체 재생성은 반드시 이 러너로 한다.

★모듈을 import 해서 build() 를 부르면 안 된다 — 시그니처가 셋이다:
    build()            단일 스킨
    build(v)           VARIANTS 표를 도는 것 (townsfolk 등 9개)
    build(name, fn)    이름+함수 쌍 (bold_pilot, hyx_pilot)
  각 모듈의 __main__ 이 자기 표를 알고 있으므로 **스크립트로 실행**한다.
"""
import pathlib, subprocess, sys, collections

HERE = pathlib.Path(__file__).parent
SKIP = {'build_all'}

def main():
    mods = sorted(p for p in HERE.glob('*.py') if p.stem not in SKIP)
    before = {p.name: p.stat().st_mtime for p in (HERE/'out').glob('*.png')}
    ok = []; fail = []
    for p in mods:
        r = subprocess.run([sys.executable, str(p)], capture_output=True, text=True)
        (ok if r.returncode == 0 else fail).append((p.stem, r))
    print('모듈 %d개 — 성공 %d · 실패 %d' % (len(mods), len(ok), len(fail)))
    for stem, r in fail:
        last = (r.stderr.strip().splitlines() or ['?'])[-1]
        print('  ✗ %-22s %s' % (stem, last[:110]))
    after = {p.name: p.stat().st_mtime for p in (HERE/'out').glob('*.png')}
    touched = [n for n, t in after.items() if before.get(n) != t]
    print('갱신된 png %d개 / 전체 %d개' % (len(touched), len(after)))
    return 1 if fail else 0

if __name__ == '__main__':
    sys.exit(main())
