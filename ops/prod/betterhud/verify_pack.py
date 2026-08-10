#!/usr/bin/env python3
"""배포 뒤 서버 상태를 검증한다. prod 박스에서 실행된다(deploy-prod.sh 9단계).

★따로 파일로 뺀 이유: 배포 스크립트 안에 파이썬을 heredoc 으로 끼워 넣었더니 셸 인용이
  꼬여서 검증문이 통째로 깨진 채 배포가 "성공"으로 끝났다(2026-08-10). 검증이 안 도는
  검증은 없느니만 못하다.

핵심 판정 두 가지:
  1. CE 설정 sha1 == 실제 팩 sha1  — 어긋나면 클라가 가구팩 다운로드에 실패한다.
  2. build.zip 폰트 == 배포팩 폰트 — 어긋나면 서버는 새 글리프 폭으로 좌표를 보내는데
     클라는 옛 글리프를 써서 "새 그림은 [] 로 뜨고 글자가 아이콘 위로 겹친다".
"""
import hashlib
import json
import subprocess
import sys
import zipfile

BH = "/home/ubuntu/mcserver/plugins/BetterHud/build.zip"
PACK = "/home/ubuntu/mcserver/plugins/CraftEngine/generated/resource_pack.zip"
CFG = "/home/ubuntu/mcserver/plugins/CraftEngine/config.yml"
LOG = "/home/ubuntu/mcserver/logs/latest.log"


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fonts(path):
    """폰트 정의를 {파일: [(텍스처, height, ascent)]} 로 뽑는다.

    ★CE 팩은 난독화돼 local header 의 이름이 비어 있다. zipfile 이 이름 불일치로 거부하므로
      orig_filename 을 비워 그 검사를 끈다. (unzip -Z1 로는 아예 못 읽는다)
    """
    z = zipfile.ZipFile(path)
    out = {}
    for info in z.infolist():
        if not (info.filename.startswith("assets/betterhud/font/")
                and info.filename.endswith(".json")):
            continue
        try:
            raw = z.read(info)
        except zipfile.BadZipFile:
            info.orig_filename = ""
            raw = z.read(info)
        data = json.loads(raw)
        out[info.filename] = [(p.get("file", "space"), p.get("height"), p.get("ascent"))
                              for p in data["providers"]]
    return out


def main():
    fail = []
    active = subprocess.run(["systemctl", "is-active", "mcserver"],
                            capture_output=True, text=True).stdout.strip()
    print(f"  서버   : {active}")
    if active != "active":
        fail.append("서버가 active 가 아니다")

    cfg_sha = ""
    with open(CFG, encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("sha1:"):
                cfg_sha = line.split('"')[1] if '"' in line else ""
                break
    pack_sha = sha1(PACK)
    print(f"  CE설정 : {cfg_sha}")
    print(f"  서버팩 : {pack_sha}")
    if cfg_sha != pack_sha:
        fail.append("CE설정 != 서버팩 (클라가 가구팩 다운로드에 실패한다)")

    a, b = fonts(BH), fonts(PACK)
    bad = [k for k in a if a[k] != b.get(k)]
    print(f"  폰트   : {'OK 전부 일치 (%d개)' % len(a) if not bad else '불일치 ' + str(bad[:3])}")
    if bad:
        fail.append("build.zip 과 배포팩의 폰트가 다르다")

    with open(LOG, encoding="utf-8", errors="ignore") as f:
        exc = sum(1 for line in f if "xception" in line)
    print(f"  예외   : {exc}")

    if fail:
        print("\n❌ " + "\n❌ ".join(fail))
        sys.exit(1)
    print("  ✅ 검증 통과")


if __name__ == "__main__":
    main()
