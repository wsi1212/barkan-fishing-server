#!/usr/bin/env python3
"""날씨 사운드 3자 일치 검사 — 자바 ↔ sounds.json ↔ .ogg 파일.

## 왜 필요한가
사운드는 **어긋나도 아무도 에러를 안 낸다.** 서버는 있는 줄 알고 재생 요청을 보내고,
클라는 없는 키를 조용히 무시한다. 그래서 2026-08-11 발견 당시 weather 6종
(rain/thunder/blizzard/fog/typhoon/wind_light)이 sounds.json 에 등록만 된 채
파일이 없었고, 게다가 자바는 `playSound` 를 아예 안 걸고 `stopSound` 만 하고 있었다.
즉 **아무 날씨에서도 소리가 안 났는데 몇 달간 아무 신호가 없었다.**

`ops/rp-deploy.sh` 는 배포 때 sounds.json ↔ .ogg 를 하드 검사한다.
이 스크립트는 거기서 볼 수 없는 **자바 쪽 선언**까지 묶어서 본다(저장소가 다르다).

사용: python3 ops/check-weather-sounds.py     (실패하면 exit 1)
"""
import json
import os
import re
import sys

RP = os.path.expanduser("~/development/barkan-resourcepack")
JAVA = os.path.expanduser(
    "~/development/blockship-plugin/src/main/java/com/blockship/region/WeatherManager.java")
SOUNDS_JSON = os.path.join(RP, "assets", "barkan", "sounds.json")
SOUNDS_DIR = os.path.join(RP, "assets", "barkan", "sounds")

CALL = re.compile(
    r'setWeatherSound\(\s*"([^"]+)"\s*,\s*("[^"]*"|null)\s*,\s*("[^"]*"|null)\s*\)')


def main():
    for p in (JAVA, SOUNDS_JSON):
        if not os.path.isfile(p):
            sys.exit(f"❌ 경로가 없다: {p}")

    src = open(JAVA, encoding="utf-8").read()
    sj = json.load(open(SOUNDS_JSON, encoding="utf-8"))
    problems = []
    declared = set()

    calls = CALL.findall(src)
    if not calls:
        sys.exit("❌ 자바에서 setWeatherSound 호출을 못 찾았다 — 이름이 바뀌었는지 확인")

    print(f"자바 선언 {len(calls)}건")
    for weather, snd, gust in calls:
        for role, raw in (("사운드", snd), ("돌풍", gust)):
            if raw == "null":
                continue
            key = raw.strip('"')
            declared.add(key)
            ns, _, name = key.partition(":")
            if ns != "barkan":
                problems.append(f"{weather} {role}: 네임스페이스가 barkan 이 아니다 ({key})")
                continue
            entry = sj.get(name)
            if entry is None:
                problems.append(f"{weather} {role}: sounds.json 에 '{name}' 없음")
                continue
            for s in entry.get("sounds", []):
                nm = s["name"] if isinstance(s, dict) else s
                f = os.path.join(SOUNDS_DIR, nm.split(":", 1)[-1] + ".ogg")
                if not os.path.isfile(f):
                    problems.append(f"{weather} {role}: 파일 없음 {os.path.relpath(f, RP)}")
        print(f"  {weather:8s} {snd.strip('\"'):32s}"
              + (f" +돌풍 {gust.strip('\"')}" if gust != "null" else ""))

    # 반대 방향 — 등록만 되고 아무 날씨도 안 쓰는 항목(고아 자산)
    orphans = [k for k in sj if k.startswith("weather.") and f"barkan:{k}" not in declared]
    if orphans:
        problems.append(f"자바가 안 쓰는 weather 항목(고아): {orphans}")

    if problems:
        print("\n❌ 3자 불일치")
        for p in problems:
            print("   -", p)
        sys.exit(1)
    print(f"\n✅ 자바 ↔ sounds.json ↔ .ogg 3자 일치 (키 {len(declared)}개, 고아 0)")


if __name__ == "__main__":
    main()
