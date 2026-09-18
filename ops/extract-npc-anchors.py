#!/usr/bin/env python3
"""Citizens saves.yml 의 위치·스킨을 BlockShip npc.json 으로 이관한다.

왜: NPC 런타임에서 Citizens 원본 Player 엔티티를 걷어내려면 Citizens 에만 있던 두 데이터
(좌표·스킨)가 BlockShip 영속으로 와야 한다. 자세한 배경은 npc-citizens-decoupling-plan.md.

★생성물을 고정 사본으로 두지 않는다 — 언제든 다시 돌릴 수 있는 이 스크립트가 권위다.
★saves.yml 은 **읽기 전용**으로만 다룬다. 롤백 경로를 남기기 위해 절대 쓰지 않는다.

사용:
  # 1) 월드 UUID→이름 맵 뽑기 (서버 루트에서, 로컬/원격 각각)
  ops/extract-npc-anchors.py --dump-world-uids ~/mcserver > /tmp/world-uids.json
  ssh prod 'python3 - ' < ops/extract-npc-anchors.py --dump-world-uids ...   # 원격은 아래 안내 참조

  # 2) 이관
  ops/extract-npc-anchors.py --saves /tmp/prod-citizens-saves.yml \
      --npc-json ops/blockship-data/npc.json --world-uids /tmp/world-uids.json

원격(prod)에서 월드 맵만 뽑는 한 줄:
  ssh prod 'cd ~/mcserver && python3 -c "
import struct,glob,uuid,json
m={}
for f in sorted(glob.glob(\"*/uid.dat\")):
    d=open(f,\"rb\").read()
    if len(d)!=16: continue
    hi,lo=struct.unpack(\">qq\",d)
    m[str(uuid.UUID(int=((hi&(2**64-1))<<64)|(lo&(2**64-1))))]=f.split(\"/\")[0]
print(json.dumps(m,indent=2))"'
"""
from __future__ import annotations

import argparse
import base64
import datetime
import glob
import json
import os
import struct
import sys
import uuid as uuidlib

try:
    import yaml
except ImportError:
    sys.exit("pyyaml 필요: python3 -m pip install pyyaml")


def dump_world_uids(server_root: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(glob.glob(os.path.join(server_root, "*", "uid.dat"))):
        raw = open(path, "rb").read()
        if len(raw) != 16:
            continue
        hi, lo = struct.unpack(">qq", raw)
        wid = uuidlib.UUID(int=((hi & (2**64 - 1)) << 64) | (lo & (2**64 - 1)))
        out[str(wid)] = os.path.basename(os.path.dirname(path))
    return out


def skin_url_of(texture_raw: str) -> str | None:
    """textureRaw(base64 JSON)에서 SKIN url 추출. NpcAnimator.buildSkinProfile 2차 경로와 같은 판정."""
    try:
        data = json.loads(base64.b64decode(texture_raw).decode("utf-8"))
    except Exception:
        return None
    return (data.get("textures") or {}).get("SKIN", {}).get("url")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump-world-uids", metavar="SERVER_ROOT",
                    help="서버 루트의 */uid.dat 를 읽어 {uuid: 월드이름} JSON 을 출력하고 종료")
    ap.add_argument("--saves", help="Citizens saves.yml (읽기 전용)")
    ap.add_argument("--npc-json", help="BlockShip npc.json")
    ap.add_argument("--world-uids", help="{uuid: 월드이름} JSON 파일")
    ap.add_argument("--out", help="출력 경로 (기본: --npc-json 제자리 수정)")
    ap.add_argument("--dry-run", action="store_true", help="쓰지 않고 요약만")
    args = ap.parse_args()

    if args.dump_world_uids:
        print(json.dumps(dump_world_uids(args.dump_world_uids), indent=2, ensure_ascii=False))
        return 0

    for need in ("saves", "npc_json", "world_uids"):
        if not getattr(args, need):
            ap.error(f"--{need.replace('_','-')} 필요")

    worlds: dict[str, str] = json.load(open(args.world_uids, encoding="utf-8"))
    saves = yaml.safe_load(open(args.saves, encoding="utf-8"))
    citizens = saves.get("npc") or {}
    root = json.load(open(args.npc_json, encoding="utf-8"))
    npcs: dict = root["npcs"]

    stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    filled, skipped, problems = 0, 0, []

    # citizensId 는 npc.json 에선 문자열, saves.yml 키도 문자열이다.
    for key, entry in npcs.items():
        cid = str(entry.get("citizensId") or "").strip()
        if not cid:
            problems.append(f"{key}: citizensId 없음")
            continue
        cn = citizens.get(cid) if cid in citizens else citizens.get(int(cid)) if cid.isdigit() else None
        if cn is None:
            problems.append(f"{key}: Citizens #{cid} 없음 (saves.yml 미등록)")
            continue
        traits = cn.get("traits") or {}
        loc = traits.get("location") or {}
        skin = traits.get("skintrait") or {}

        wid = str(loc.get("worldid") or "")
        world = worlds.get(wid)
        if not world:
            problems.append(f"{key}: worldid {wid or '(없음)'} 를 월드 이름으로 못 바꿈")
            continue
        if loc.get("x") is None or loc.get("y") is None or loc.get("z") is None:
            problems.append(f"{key}: 좌표 없음")
            continue

        raw = skin.get("textureRaw")
        if not raw:
            problems.append(f"{key}: skintrait.textureRaw 없음 (모델 부착 불가)")
        elif not skin_url_of(raw):
            problems.append(f"{key}: textureRaw 에서 SKIN url 을 못 읽음")

        # ★머리 위에 실제로 보이는 이름은 npc.json 의 name 이 아니라 Citizens saves.yml 의 name 이다
        #   (CLAUDE.md 「NPC 닉네임 색 규칙」). 앵커 customName 에 그대로 넣어야 [Q]/[상점] 태그와
        #   역할 색이 그대로 유지된다. 실측 2/197 이 다르다 — 이걸 npc.json name 으로 대신하면 그만큼 바뀐다.
        if cn.get("name"):
            entry["displayName"] = cn["name"]
        entry["world"] = world
        entry["x"] = round(float(loc["x"]), 4)
        entry["y"] = round(float(loc["y"]), 4)
        entry["z"] = round(float(loc["z"]), 4)
        # 정지 NPC 의 몸 방향. Citizens 는 head(yaw)/body(bodyYaw)를 따로 들고 있고
        # 앵커에 필요한 건 몸 방향이다. bodyYaw 가 없으면 yaw 로 폴백.
        entry["yaw"] = round(float(loc.get("bodyYaw", loc.get("yaw", 0.0))), 4)
        entry["pitch"] = round(float(loc.get("pitch", 0.0)), 4)
        if raw:
            entry["skinRaw"] = raw
            if skin.get("signature"):
                entry["skinSignature"] = skin["signature"]
        entry["anchorUpdatedAt"] = stamp
        filled += 1

    # saves.yml 에는 있는데 npc.json 에 없는 것 — 코드 생성 NPC(BPS·딜러 등)일 수 있다.
    known = {str(e.get("citizensId") or "") for e in npcs.values()}
    orphans = [str(k) for k in citizens.keys() if str(k) not in known]

    print(f"npc.json 항목 {len(npcs)}개 / Citizens {len(citizens)}개")
    print(f"이관 성공 {filled}개")
    if problems:
        print(f"\n문제 {len(problems)}건:")
        for p in problems:
            print("  -", p)
    if orphans:
        print(f"\nnpc.json 에 없는 Citizens NPC {len(orphans)}개: {', '.join(sorted(orphans, key=lambda s:(len(s),s)))}")
        for o in sorted(orphans, key=lambda s: (len(s), s)):
            print(f"    #{o}  name={citizens[o].get('name') if o in citizens else citizens.get(int(o),{}).get('name')}")

    if args.dry_run:
        print("\n[dry-run] 쓰지 않음")
        return 1 if problems else 0

    out = args.out or args.npc_json
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(root, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"\n기록: {out}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
