#!/usr/bin/env python3
"""사본 드리프트 감사 — «같아야 하는 두 벌»이 갈라졌는지 본다.

왜 있나 (2026-08-31)
────────────────────
이 프로젝트에서 반복해서 터지는 사고는 전부 한 가지 병이다:
**같은 사실이 여러 벌 있고, 어긋나도 아무도 모른다.**

한 세션에서 실제로 나온 것만:
  · 레포 `fish.json` 이 개명 전에 멈춰 감사가 유령 ERROR 21건을 뱉음
  · `quest_audit` 이 읽는 카탈로그 8종이 라이브보다 며칠 뒤처짐 (총 158건 중 157건이 유령)
  · prod jar 이 «낡은 체크아웃»에서 빌드돼 커밋된 기능 4개가 라이브에 없었음
  · `deploy-blockship.sh` 가 홈·레포에 두 벌, 206줄 차이
  · `sync-blockship-data.sh` 의 FILES(9) 와 배포의 DATA_FILES(10) 가 불일치
  · 레포 루트에 아무도 안 쓰는 `item-flavor.json` 네 번째 사본

각각을 손으로 고치는 건 소용이 없다 — 다음 달에 다른 파일에서 또 난다.
**어긋난 순간 시끄럽게 실패하는 것**만이 구조적 해결이다.

사용:  python3 ops/audit-copies.py          (검사, 어긋나면 exit 1)
       python3 ops/audit-copies.py --fix    (권위 → 사본으로 덮어 맞춤)
"""
import hashlib
import os
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
LIVE = pathlib.Path(
    "/Users/user/Library/Application Support/feather/player-server/servers/"
    "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip"
)
PLUGIN = pathlib.Path.home() / "development" / "blockship-plugin"
HOME = pathlib.Path.home()

FIX = "--fix" in sys.argv
problems: list[str] = []
fixed: list[str] = []


def sha(p: pathlib.Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:12]
    except OSError:
        return None


def fail(msg: str) -> None:
    problems.append(msg)
    print(f"  ✗ {msg}")


# ─────────────────────────────────────────────────────────────────────
# 1. DATA_FILES 목록이 «여러 곳»에 손으로 적혀 있다 — 전부 같은가?
#    목록이 갈라지면 어떤 파일은 sync 되고 어떤 파일은 안 되는데, 증상이 없다.
#    (fish.json 이 정확히 그렇게 sync 목록에서 빠진 채로 몇 달 있었다.)
# ─────────────────────────────────────────────────────────────────────
def parse_bash_array(path: pathlib.Path, var: str) -> set[str] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(rf"^{var}=\((.*?)\)", text, re.M | re.S)
    if not m:
        return None
    return set(re.findall(r"[\w.-]+\.json", m.group(1)))


print("1) BlockShip JSON 목록이 여러 곳에서 일치하는가")
LIST_SOURCES = {
    "ops/deploy-blockship.sh (DATA_FILES)": (REPO / "ops/deploy-blockship.sh", "DATA_FILES"),
    "~/deploy-blockship.sh (DATA_FILES)": (HOME / "deploy-blockship.sh", "DATA_FILES"),
    "ops/sync-blockship-data.sh (FILES)": (REPO / "ops/sync-blockship-data.sh", "FILES"),
}
lists = {}
for label, (path, var) in LIST_SOURCES.items():
    got = parse_bash_array(path, var)
    if got is None:
        print(f"  · {label}: 못 읽음(스킵)")
        continue
    lists[label] = got
    print(f"  · {label}: {len(got)}개")

if len(lists) > 1:
    union: set[str] = set().union(*lists.values())
    for label, got in lists.items():
        missing = union - got
        if missing:
            fail(f"{label} 에 빠진 파일: {sorted(missing)}")

# ─────────────────────────────────────────────────────────────────────
# 2. git 에 들어 있는 «두 벌»의 데이터 미러가 같은가.
#    ops/blockship-data/ = 히스토리·리뷰용 미러
#    blockship-plugin/   = quest_audit 의 load() 가 읽는 사본
#    ★둘이 갈라지면 «게이트가 검사한 파일»과 «배포되는 파일»이 다른 물건이 된다.
#    권위는 라이브(plugins/BlockShip) — 그래서 --fix 는 라이브에서 양쪽으로 덮는다.
# ─────────────────────────────────────────────────────────────────────
print("\n2) git 미러 두 벌(ops/blockship-data · blockship-plugin)이 라이브와 같은가")
data_files = sorted(set().union(*lists.values())) if lists else []
for f in data_files:
    live = LIVE / f
    if not live.exists():
        continue
    want = sha(live)
    for mirror in (REPO / "ops/blockship-data" / f, PLUGIN / f):
        if not mirror.exists():
            continue  # 그 사본을 안 두는 건 선택이다 — 있는데 다른 게 문제
        if sha(mirror) == want:
            continue
        rel = mirror.relative_to(mirror.parents[len(mirror.parts) - 4]) if False else mirror
        if FIX:
            mirror.write_bytes(live.read_bytes())
            fixed.append(str(rel))
            print(f"  ✔ 맞춤: {rel}")
        else:
            fail(f"라이브와 다름: {rel}")

# ─────────────────────────────────────────────────────────────────────
# 3. 아무도 안 쓰는 «떠도는 사본» — 레포 루트의 BlockShip 데이터 JSON.
#    배포도 감사도 여기를 안 본다. 남아 있으면 누군가 여기를 고치고 반영됐다고 믿는다.
# ─────────────────────────────────────────────────────────────────────
print("\n3) 레포 루트에 떠도는 BlockShip 데이터 사본이 있는가")
strays = [p for p in REPO.glob("*.json") if p.name in set(data_files)]
if not strays:
    print("  · 없음")
for p in strays:
    fail(f"레포 루트의 고아 사본 {p.name} — 배포·감사 어느 쪽도 이걸 안 읽는다 "
         f"(권위는 plugins/BlockShip/{p.name}, 미러는 ops/blockship-data/{p.name})")

# ─────────────────────────────────────────────────────────────────────
# 4. 홈의 배포 스크립트 — git 밖에 있거나, 레포본과 갈라져 있지 않은가.
#    git 밖 = 맥이 죽으면 사라진다. 갈라짐 = 어느 쪽이 도는지 아무도 모른다.
# ─────────────────────────────────────────────────────────────────────
print("\n4) 홈 배포 스크립트가 git 안에 있고 레포본과 같은가")
for name in ("deploy-blockship.sh", "deploy-dev.sh", "deploy-rp.sh", "stage-blockship.sh"):
    home = HOME / name
    if not home.exists():
        continue
    repo_copy = REPO / "ops" / name
    if home.is_symlink():
        print(f"  · {name}: 심볼릭링크 → {os.readlink(home)}")
        continue
    if not repo_copy.exists():
        fail(f"~/{name} 이 git 밖에 있다 — 맥이 죽으면 사라진다 (ops/{name} 로 옮길 것)")
        continue
    if sha(home) != sha(repo_copy):
        n = len(subprocess.run(["diff", str(home), str(repo_copy)],
                               capture_output=True, text=True).stdout.splitlines())
        fail(f"~/{name} 와 ops/{name} 가 갈라짐 ({n}줄) — 어느 쪽이 prod 에 도는지 불명")

# ─────────────────────────────────────────────────────────────────────
# 5. 게이트 스크립트가 «한 벌만» 있는가.
#    폰/웹(GitHub Actions) 승격 경로도 같은 검사를 받게 하려고, 플러그인 소스만 보는
#    게이트는 blockship-plugin/tools/ 로 «옮겼다»(복사가 아니다 — 복사하면 CI 와 맥이
#    서로 다른 규칙을 돌게 되고, 그게 이 파일이 존재하는 이유인 그 병이다).
# ─────────────────────────────────────────────────────────────────────
print("\n5) 게이트 스크립트가 한 벌만 있는가 (CI·맥 공용)")
SHARED_GATES = ("verify-no-bold-format.py", "verify-no-naive-time.py", "quest_audit.py")
for name in SHARED_GATES:
    canonical = PLUGIN / "tools" / name
    stray = REPO / "ops" / name
    if not canonical.exists():
        fail(f"게이트 원본이 없다: blockship-plugin/tools/{name} "
             f"(CI 워크플로가 이 경로를 부른다)")
        continue
    if stray.exists():
        fail(f"게이트가 두 벌이다: ops/{name} 와 blockship-plugin/tools/{name} — "
             f"CI 와 맥이 서로 다른 규칙을 돌게 된다. ops/ 쪽을 지울 것")
    else:
        print(f"  · {name}: blockship-plugin/tools/ 한 벌")

# ─────────────────────────────────────────────────────────────────────
# 6. 심볼릭링크로 실행되는 스크립트가 `dirname "$0"` 을 쓰고 있지 않은가.
#    홈 진입점을 링크로 만든 뒤 $0·BASH_SOURCE 가 홈을 가리켜, 같은 폴더의 스크립트를
#    못 찾는다. 2026-08-31: deploy-blockship.sh 가 sync-prod-staging.sh 를 못 찾아
#    **모든 배포가 staging 동기화를 조용히 건너뛰었다**(06:00 되돌림 위험). 경고 한 줄만
#    찍고 배포는 계속되니 눈에 안 띄었다.
# ─────────────────────────────────────────────────────────────────────
print("\n6) 링크로 실행되는 스크립트가 $0 상대경로를 쓰지 않는가")
LINKED = set()
for name in ("deploy-blockship.sh", "deploy-dev.sh", "deploy-rp.sh", "stage-blockship.sh"):
    home = HOME / name
    if home.is_symlink():
        LINKED.add(pathlib.Path(os.path.realpath(home)).name)
# 링크 대상 + 그것이 부르는 래퍼들
CHECK = LINKED | {"deploy-all-prod.sh", "preflight.sh"}
BAD_PAT = re.compile(r'dirname\s+"\$0"|dirname\s+"\$\{BASH_SOURCE\[0\]\}"')
for name in sorted(CHECK):
    f = REPO / "ops" / name
    if not f.exists():
        continue
    hits = [i + 1 for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines())
            if BAD_PAT.search(ln) and "_self_real" not in ln and "lib-self" not in ln]
    if hits:
        fail(f"ops/{name}:{hits} 가 링크에 취약한 $0/BASH_SOURCE 상대경로를 쓴다 — "
             f"_self_real 로 링크를 풀 것 (원본: ops/lib-self.sh)")
    else:
        print(f"  · {name}: 안전")

# ─────────────────────────────────────────────────────────────────────
print()
if fixed:
    print(f"맞춘 사본 {len(fixed)}개")
if problems:
    print(f"❌ 사본 드리프트 {len(problems)}건")
    print("   ★손으로 하나씩 맞추지 말 것 — 또 갈라진다. 사본을 «없애거나»(심볼릭링크·삭제)")
    print("     «파생시키거나»(권위를 직접 읽게) 해야 재발이 멈춘다.")
    sys.exit(1)
print("✓ 등록된 사본 전부 일치")
