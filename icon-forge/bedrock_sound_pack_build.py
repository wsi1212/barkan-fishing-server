#!/usr/bin/env python3
"""
베드락(Geyser) «소리» 팩 빌더 — barkan_bedrock_sounds.mcpack

  왜 별도 팩인가
    베드락 유저는 2026-09-06 까지 우리 커스텀 사운드를 «단 하나도» 못 들었다. 원인 둘:
      ① BGM 은 ItemDisplay 스피커 부착 사운드라 Geyser 가 패킷째로 버린다
         (Geyser 에 ItemDisplay 번역기가 없다 → BgmManager.tickBedrock 이 위치 사운드로 우회)
      ② 베드락 팩에 소리 파일이 0개였다 (barkan_bedrock.mcpack = 아이콘 텍스처 + ui 뿐)
    ②를 고치는 게 이 스크립트다. ★기존 아이콘 팩에 합치지 않는다 — 그쪽은 Geyser 인밴드
    (RakNet) 전송이고 15MB 에서 베드락 접속 자체가 깨진 전례가 있다. 소리는 덩치가 커서
    prod 에서는 원격 URL 전송(config.yml resource-pack-urls)으로 내보낼 것.

  용량 (실측, 2026-09-06)
    원본 BGM 18곡 = 23MB (96kbps mono 48kHz). --quality low(기본) = q0 @24kHz → 약 8MB.
    효과음(weather/ui/enhance/camera/npc/chess/siren_head)은 다 합쳐 1.3MB 라 원본 그대로 넣는다.
    피아노 49건반(4.2MB)은 기본 제외 — 실연주는 클라이언트 모드 전제라 베드락에서 못 친다.

  ★페이드는 없다 (되살리려 하지 말 것)
    PlaySoundPacket 은 좌표가 재생 시점에 «고정» 된다. 자바의 상승-페이드는 클라가 움직이는
    엔티티와의 거리를 매틱 갱신해 주는 데 기댄 트릭이라 베드락에 옮길 수 없다. 대신 거리
    감쇠 자체를 max_distance 로 무력화해서(사실상 전역) 걸어다녀도 볼륨이 안 변하게 한다.
    바닐라 선례: ambient.weather.thunder 가 max_distance 10000 을 쓴다.

  ★키를 둘 쓴다
    Geyser SoundUtils.translatePlaySound 는 "minecraft:" 만 벗기므로 클라에는
    "barkan:bgm.spawn_city_clear" 가 «그대로» 간다. 콜론 키가 베드락 파서에서 문제가 될
    경우를 대비해 점 표기 별칭("barkan.bgm.…")도 같은 파일을 가리키게 정의해 둔다
    (파일 공유라 용량 0). 실기기에서 콜론이 안 먹으면 서버가 보내는 이름만 바꾸면 된다.

  사용법
    python3 bedrock_sound_pack_build.py [--quality low|mid|orig] [--include-piano] [--dry-run]
    ./bedrock_sound_pack_deploy.sh dev
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RP = Path.home() / "development/barkan-resourcepack"
SOUNDS_JSON = RP / "assets/barkan/sounds.json"
SOUNDS_DIR = RP / "assets/barkan/sounds"
OUT = HERE / "out/bedrock"
CACHE = OUT / "sndcache"

# ★uuid 는 «고정». 아이콘 팩(2af7a31c…)과 반드시 달라야 한다 — 같으면 Geyser 가 한쪽을 버린다.
PACK_UUID = "5c1d9a44-2b7e-4f61-9a0c-7d3e6b8f1042"
MODULE_UUID = "9f2b6e17-8c34-4a55-bd21-0e7a4c9d5f83"

# 이벤트 접두사 → (베드락 사운드 카테고리, 전역화 여부, 스트리밍 여부)
#   category = 클라 볼륨 슬라이더 소속. global=True 면 max_distance 를 크게 줘 감쇠를 없앤다.
CATEGORY = {
    "bgm":        ("music",   True,  True),
    "weather":    ("ambient", True,  True),
    "ui":         ("ui",      False, False),
    "enhance":    ("player",  False, False),
    "camera":     ("player",  False, False),
    "npc":        ("player",  False, False),
    "chess":      ("player",  False, False),
    "siren_head": ("hostile", False, False),
    "piano":      ("player",  False, False),
}
FAR = 10000.0

QUALITY = {   # oggenc 인자 (mono 변환은 ffmpeg 이 먼저 한다)
    "low": ["-q", "0", "--resample", "24000"],   # 실측 0.52MB/160초 → BGM 전체 ≈ 8.0MB
    "mid": ["-q", "0"],                          # 실측 0.87MB/160초 → BGM 전체 ≈ 13.4MB
}


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} 실패: {r.stderr.strip()[:300]}")


def encode(src: Path, quality: str) -> bytes:
    """BGM 재인코딩(모노 유지 + 저비트레이트). 결과는 내용 해시로 캐시한다."""
    if quality == "orig":
        return src.read_bytes()
    key = hashlib.sha1(src.read_bytes() + quality.encode()).hexdigest()[:16]
    cached = CACHE / f"{key}.ogg"
    if cached.is_file():
        return cached.read_bytes()
    CACHE.mkdir(parents=True, exist_ok=True)
    wav = CACHE / f"{key}.wav"
    try:
        # ffmpeg 은 디코드·모노 다운믹스만. libvorbis 인코더가 이 맥의 ffmpeg 에 없어서
        # 인코딩은 oggenc(vorbis-tools) 가 한다 — CLAUDE.md 「커스텀 사운드」 절과 같은 이유.
        run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1", str(wav)])
        run(["oggenc", "-Q", *QUALITY[quality], "-o", str(cached), str(wav)])
    finally:
        wav.unlink(missing_ok=True)
    return cached.read_bytes()


def build(quality: str, include_piano: bool, dry: bool) -> int:
    if not SOUNDS_JSON.is_file():
        print(f"❌ 자바 팩 sounds.json 이 없습니다: {SOUNDS_JSON}")
        return 1
    for tool in ("ffmpeg", "oggenc"):
        if quality != "orig" and shutil.which(tool) is None:
            print(f"❌ {tool} 가 없습니다 (brew install ffmpeg vorbis-tools)")
            return 1

    events = json.loads(SOUNDS_JSON.read_text(encoding="utf-8"))
    stage = OUT / "stage-sounds"
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "sounds").mkdir(parents=True)

    definitions: dict[str, dict] = {}
    missing: list[str] = []
    written: dict[str, int] = {}      # 팩 내 상대경로 → 바이트
    per_group: dict[str, int] = {}

    for event, spec in events.items():
        group = event.split(".", 1)[0]
        if group == "piano" and not include_piano:
            continue
        category, is_global, stream = CATEGORY.get(group, ("player", False, False))

        entries = []
        for snd in spec.get("sounds", []):
            name = snd["name"] if isinstance(snd, dict) else snd
            rel = name.split(":", 1)[-1]                  # barkan:bgm/xxx → bgm/xxx
            src = SOUNDS_DIR / f"{rel}.ogg"
            if not src.is_file():
                missing.append(f"{event} → {src.name}")
                continue
            dst_rel = f"sounds/{rel}.ogg"
            if dst_rel not in written:
                data = encode(src, quality) if group == "bgm" else src.read_bytes()
                dst = stage / dst_rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(data)
                written[dst_rel] = len(data)
                per_group[group] = per_group.get(group, 0) + len(data)
            entries.append({
                # ★확장자 없이, 팩 루트 기준 경로 — 베드락 규약이다.
                "name": dst_rel[:-4],
                "stream": stream,
                "volume": 1.0,
            })
        if not entries:
            continue

        d = {"category": category, "sounds": entries}
        if is_global:
            # 거리 감쇠 무력화 = 걸어다녀도 볼륨이 변하지 않는다(위 ★페이드 절 참조)
            d["min_distance"] = 0.0
            d["max_distance"] = FAR
        definitions[f"barkan:{event}"] = d
        definitions[f"barkan.{event}"] = dict(d)   # 콜론 미지원 대비 별칭(파일 공유 → 용량 0)

    if missing:
        print(f"❌ sounds.json 이 가리키는 파일 {len(missing)}개가 없습니다 — 팩을 만들지 않습니다")
        for m in missing[:10]:
            print(f"     · {m}")
        return 1

    (stage / "sounds/sound_definitions.json").write_text(json.dumps({
        "format_version": "1.14.0",
        "sound_definitions": definitions,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── manifest ────────────────────────────────────────────────────────────
    #   ★version 은 «내용이 바뀌면 반드시» 올라야 한다. 베드락 클라는 (uuid, version) 으로
    #     캐시하므로 둘 다 같으면 팩을 다시 받지 않는다 — 아이콘 팩에서 이걸로 세 번 데였다.
    stamp = hashlib.sha256()
    for rel in sorted(written):
        stamp.update(rel.encode())
        stamp.update((stage / rel).read_bytes())
    stamp.update((stage / "sounds/sound_definitions.json").read_bytes())
    rev = int(stamp.hexdigest()[:6], 16) % 100000
    (stage / "manifest.json").write_text(json.dumps({
        "format_version": 2,
        "header": {
            "name": "바르칸 열도 (소리)",
            "description": "지역 BGM + 날씨·UI·강화 효과음",
            "uuid": PACK_UUID,
            "version": [1, 0, rev],
            "min_engine_version": [1, 21, 0],
        },
        "modules": [{
            "type": "resources",
            "uuid": MODULE_UUID,
            "version": [1, 0, rev],
        }],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 자기검증 ────────────────────────────────────────────────────────────
    #   정의가 가리키는 파일이 팩 안에 실제로 있는가. 이 사슬이 끊기면 «소리만 조용히 안 남»
    #   — 서버 로그엔 아무것도 안 남아서 폰을 켜 보기 전엔 모른다.
    broken = [f"{k} → {e['name']}" for k, d in definitions.items() for e in d["sounds"]
              if not (stage / f"{e['name']}.ogg").is_file()]
    if broken:
        print(f"❌ 정의↔파일 사슬이 끊긴 항목 {len(broken)}개")
        for b in broken[:10]:
            print(f"     · {b}")
        return 1

    total = sum(written.values())
    print(f"▶ 이벤트 {len(definitions)//2}종 / 파일 {len(written)}개 / 품질 {quality}")
    for g, n in sorted(per_group.items(), key=lambda x: -x[1]):
        print(f"     · {g:<10} {n/1048576:6.2f} MB")
    print(f"▶ 합계 {total/1048576:.2f} MB (압축 전) — 팩 버전 1.0.{rev}")

    if dry:
        print("… --dry-run: mcpack 을 만들지 않았습니다")
        return 0

    mcpack = OUT / "barkan_bedrock_sounds.mcpack"
    mcpack.unlink(missing_ok=True)
    with zipfile.ZipFile(mcpack, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(stage.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(stage))
    sz = mcpack.stat().st_size
    print(f"✅ {mcpack}  ({sz/1048576:.2f} MB)")
    if sz > 6_500_000:
        print("⚠️  6.5MB 초과 — Geyser 인밴드(packs/) 전송은 15MB 에서 베드락 접속이 깨진 전례가")
        print("    있다. prod 는 원격 URL(resource-pack-urls)로 내보낼 것. dev 는 인밴드로 시험.")
    print("\n배포: ./bedrock_sound_pack_deploy.sh dev")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quality", choices=["low", "mid", "orig"], default="low",
                    help="BGM 재인코딩 품질. low=q0@24kHz(≈8MB, 기본) mid=q0(≈13.4MB) orig=원본(23MB)")
    ap.add_argument("--include-piano", action="store_true",
                    help="피아노 49건반(4.2MB)도 넣는다 — 실연주는 클라 모드 전제라 기본 제외")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sys.exit(build(a.quality, a.include_piano, a.dry_run))
