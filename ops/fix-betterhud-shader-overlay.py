#!/usr/bin/env python3
"""BetterHud 셰이더 오버레이 경계 교정 — 1.21.9+ 클라에서 팩 전체가 버려지는 문제.

## 증상
클라 로그:
    Couldn't compile fragment shader (minecraft:core/rendertype_text):
      ERROR: 'FogColor' already declared within an interface block
      ERROR: Invalid call of undeclared identifier 'linear_fog'
    Failed to load required shader programs: minecraft:pipeline/text, .../gui_text
    Caught error loading resourcepacks, removing all selected resourcepacks
→ **모든** 리소스팩이 해제된다. CE 가구·BetterHud·글리프 GUI 가 전멸하고, 바닐라로
  그려지는 것(플레이어 스킨 NPC 등)만 정상으로 보인다.

## 원인
BetterHud 2.1.0-SNAPSHOT-447 이 CE 생성팩에 심는 오버레이 경계가 틀렸다:
    betterhud_1_21_6 : format 56..83  → #define SHADER_VERSION 2 (linear_fog, 구 fog API)
    betterhud_26_1   : format 84..99  → #define SHADER_VERSION 3 (apply_fog, fog UBO)
그런데 fog UBO 전환은 1.21.9 부터다:
    1.21.8 = format 64 (v2 필요)  ·  1.21.10 = 69  ·  1.21.11 = 75  (v3 필요)
즉 65..83 구간이 v2 를 받아서 컴파일이 깨진다.

## 하는 일
65..83 을 덮는 브리지 오버레이를 만든다 = 26_1 의 v3 셰이더 4개
+ 1_21_6 의 `sample_lightmap.glsl`(★바닐라 1.21.10 에 없다 — 26_1 만 쓰면 include 누락).
경계는 1_21_6 → 56..64, 브리지 → 65..83, 26_1 → 84..99.

## 짝으로 확인할 것 — CE supported-version (별개 원인, 증상이 비슷하다)
`plugins/CraftEngine/config.yml` 의 `supported-version.min` 이 `"server"` 면 CE 는 서버
버전 이상만 커버하는 오버레이를 굽는다. 서버가 1.21.11(format 75)이고 클라가 1.21.10(69)
이면 atlas 오버레이를 하나도 못 받아 **가구가 전부 보라색 실루엣**이 된다. prod 처럼
`min: "1.21.4"` 로 두면 `ce_overlay_46-72/atlases/blocks.json`(구 클라)과
`ce_overlay_73-88/atlases/items.json`(신 클라)을 둘 다 굽는다 — 1.21.11 에서 아이템
텍스처가 blocks→items 아틀라스로 옮겨졌기 때문이다. (2026-09-04 dev 에서 실측)

## ★재실행 필요
CE 가 팩을 다시 생성하면(`/ce reload all`, 가구 추가 등) 이 패치는 사라진다.
그때 다시 돌릴 것. 근본 대책은 BetterHud 를 1.21.9+ 지원 빌드로 올리는 것이다.

사용: python3 ops/fix-betterhud-shader-overlay.py <resource_pack.zip> [--check]
"""
import json, os, shutil, subprocess, sys, tempfile, zipfile

BRIDGE = "betterhud_bridge_65_83"
LO, HI = 65, 83
V3_SRC = "betterhud_26_1"
INC_SRC = "betterhud_1_21_6"
SHADERS = ["assets/minecraft/shaders/core/rendertype_text.fsh",
           "assets/minecraft/shaders/core/rendertype_text.vsh",
           "assets/minecraft/shaders/core/text.fsh",
           "assets/minecraft/shaders/core/text.vsh"]
INCLUDE = "assets/minecraft/shaders/include/sample_lightmap.glsl"


def set_range(e, lo, hi):
    e["min_format"] = [lo, 0]
    e["max_format"] = [hi, 0]
    e["formats"] = [lo, hi]


def unzip_read(path, member):
    """★CE 가 쓴 zip 은 로컬 헤더가 비표준이라 python zipfile 이 못 읽는다(BadZipFile:
    Bad magic number for file header). unzip CLI 는 central directory 로 읽어 넘긴다."""
    r = subprocess.run(["unzip", "-p", path, member], capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(f"unzip -p 실패: {member}")
    return r.stdout


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = os.path.abspath(sys.argv[1])
    check = "--check" in sys.argv

    meta = json.loads(unzip_read(path, "pack.mcmeta"))
    ent = meta.setdefault("overlays", {}).setdefault("entries", [])
    by = {e["directory"]: e for e in ent}
    print("현재 경계: " + " · ".join(f"{e['directory']}={e.get('formats')}"
                                   for e in ent if e["directory"].startswith("betterhud")))
    have = BRIDGE in by
    if check:
        ok = have and by.get(INC_SRC, {}).get("formats") == [56, LO - 1]
        print("패치 상태:", "적용됨" if ok else "미적용")
        return 0 if ok else 1

    for d in (V3_SRC, INC_SRC):
        if d not in by:
            sys.exit(f"❌ 오버레이 {d} 가 없다 — BetterHud 버전이 바뀌었으면 이 스크립트를 다시 볼 것")
    v3 = unzip_read(path, f"{V3_SRC}/{SHADERS[0]}").decode()
    if "#define SHADER_VERSION 3" not in v3:
        sys.exit(f"❌ {V3_SRC} 셰이더가 SHADER_VERSION 3 이 아니다 — 전제가 깨졌다")

    work = tempfile.mkdtemp(prefix="cebridge-")
    d_bridge = os.path.join(work, BRIDGE)
    for s in SHADERS + [INCLUDE]:
        src = f"{V3_SRC}/{s}" if s in SHADERS else f"{INC_SRC}/{s}"
        dst = os.path.join(d_bridge, s)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(unzip_read(path, src))

    set_range(by[INC_SRC], 56, LO - 1)
    bridge = by.get(BRIDGE) or {"directory": BRIDGE}
    set_range(bridge, LO, HI)
    if not have:
        ent.insert(ent.index(by[INC_SRC]) + 1, bridge)
    open(os.path.join(work, "pack.mcmeta"), "w").write(json.dumps(meta, indent=2))

    bak = path + ".bak-preshaderfix"
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    # ★기존 아카이브에 «덮어쓰기»로 넣는다 — 전체 재압축을 피해 CE 가 쓴 나머지
    #   엔트리를 그대로 둔다(재압축하면 python 이 못 읽는 엔트리에서 깨진다).
    r = subprocess.run(["zip", "-q", "-X", "-r", path, BRIDGE, "pack.mcmeta"],
                       cwd=work, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"❌ zip 실패: {r.stderr}")
    shutil.rmtree(work, ignore_errors=True)

    after = json.loads(unzip_read(path, "pack.mcmeta"))
    got = {e["directory"]: e.get("formats") for e in after["overlays"]["entries"]}
    assert got.get(BRIDGE) == [LO, HI] and got.get(INC_SRC) == [56, LO - 1], got
    n = len(subprocess.run(["unzip", "-l", path, f"{BRIDGE}/*"],
                           capture_output=True, text=True).stdout.splitlines())
    print(f"✅ {BRIDGE} 오버레이 기록 · 경계 {INC_SRC}=56..{LO-1} / {BRIDGE}={LO}..{HI} / {V3_SRC}=84..99")
    print(f"   브리지 파일 {len(SHADERS)+1}개 · 원본 백업 {bak}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
