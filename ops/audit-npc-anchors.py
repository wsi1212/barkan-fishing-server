#!/usr/bin/env python3
"""npc.json 앵커 검산 — citizens-free 모드를 켜기 전 게이트(G1).

앵커가 하나라도 깨져 있으면 그 NPC 는 «보이지도 눌리지도 않는» 유령이 된다. Citizens 를
폴백으로 쓰던 시절엔 조용히 넘어갔지만 이제는 폴백이 없다.

  ops/audit-npc-anchors.py --npc-json ops/blockship-data/npc.json \
      [--saves /tmp/prod-citizens-saves.yml] [--world-uids /tmp/world-uids.json]

--saves 를 주면 Citizens 원본과 좌표를 대조한다(이관 사고 감지). 안 주면 자체 정합성만 본다.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from collections import Counter

REQUIRED = ("world", "x", "y", "z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--npc-json", required=True)
    ap.add_argument("--saves", help="Citizens saves.yml — 주면 좌표 대조까지")
    ap.add_argument("--world-uids", help="--saves 와 함께. {uuid: 월드이름}")
    ap.add_argument("--tolerance", type=float, default=1e-3)
    args = ap.parse_args()

    npcs = json.load(open(args.npc_json, encoding="utf-8"))["npcs"]
    errors: list[str] = []
    warns: list[str] = []

    # ① 필수 필드
    for key, d in npcs.items():
        missing = [f for f in REQUIRED if d.get(f) is None]
        if missing:
            errors.append(f"{key}: 앵커 필드 없음 {missing}")
        if not d.get("displayName"):
            warns.append(f"{key}: displayName 없음 → npc.json name 으로 폴백(표시 이름이 바뀔 수 있다)")

    # ② 스킨: 없으면 모델을 못 붙인다(= 안 보인다)
    for key, d in npcs.items():
        raw = d.get("skinRaw")
        if not raw:
            errors.append(f"{key}: skinRaw 없음 — 모델 미부착 = 투명 NPC")
            continue
        try:
            j = json.loads(base64.b64decode(raw).decode("utf-8"))
        except Exception as e:
            errors.append(f"{key}: skinRaw base64/JSON 파손 ({e})")
            continue
        if not (j.get("textures") or {}).get("SKIN", {}).get("url"):
            errors.append(f"{key}: skinRaw 에 textures.SKIN.url 없음")

    # ③ 좌표 중복 — 이관 사고(같은 값이 여러 NPC 에 복사됨) 조기 감지
    pos = Counter((d.get("world"), d.get("x"), d.get("z"))
                  for d in npcs.values() if d.get("world") and d.get("x") is not None)
    for (w, x, z), n in pos.items():
        if n > 1:
            who = [k for k, d in npcs.items() if (d.get("world"), d.get("x"), d.get("z")) == (w, x, z)]
            warns.append(f"좌표 중복 {w} {x},{z} — {n}명: {', '.join(who)}")

    # ④ Citizens 원본 대조(선택)
    if args.saves:
        if not args.world_uids:
            ap.error("--saves 를 쓰면 --world-uids 도 필요하다")
        import yaml
        worlds = json.load(open(args.world_uids, encoding="utf-8"))
        citizens = (yaml.safe_load(open(args.saves, encoding="utf-8")) or {}).get("npc") or {}
        for key, d in npcs.items():
            cid = str(d.get("citizensId") or "")
            cn = citizens.get(cid) or (citizens.get(int(cid)) if cid.isdigit() else None)
            if cn is None:
                warns.append(f"{key}: Citizens #{cid} 없음(원본 대조 생략)")
                continue
            loc = (cn.get("traits") or {}).get("location") or {}
            w = worlds.get(str(loc.get("worldid") or ""))
            if w != d.get("world"):
                errors.append(f"{key}: 월드 불일치 npc.json={d.get('world')} citizens={w}")
            for f in ("x", "y", "z"):
                a, b = d.get(f), loc.get(f)
                if a is None or b is None:
                    continue
                if abs(float(a) - float(b)) > args.tolerance:
                    errors.append(f"{key}: {f} 불일치 npc.json={a} citizens={b}")
        known = {str(d.get("citizensId") or "") for d in npcs.values()}
        orphans = [str(k) for k in citizens if str(k) not in known]
        if orphans:
            warns.append(f"npc.json 에 없는 Citizens NPC {len(orphans)}개: {', '.join(sorted(orphans))} "
                         f"— 이들은 citizens-free 에서도 Citizens 가 계속 그린다(의도된 동작)")

    anchored = sum(1 for d in npcs.values() if all(d.get(f) is not None for f in REQUIRED) and d.get("skinRaw"))
    print(f"NPC {len(npcs)}개 / 앵커 완비 {anchored}개")
    for w in warns:
        print("  ⚠", w)
    for e in errors:
        print("  ✗", e)
    if errors:
        print(f"\n실패: {len(errors)}건 — citizens-free 를 켜면 그만큼 유령 NPC 가 된다")
        return 1
    print("\n통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
