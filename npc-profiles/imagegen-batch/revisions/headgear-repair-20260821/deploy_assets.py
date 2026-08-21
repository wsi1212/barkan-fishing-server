#!/usr/bin/env python3
"""보정한 요한(162) 초상을 매니페스트 source 로 등록하고 배포 애셋을 «다시 뽑는다».

사본을 손으로 복사해 고정하지 않는다 — 128x154 애셋과 _sm/_md/_lg/_xl 은 모두
ops/prod/betterhud/gen_npc_portrait_huds.py 의 frame() 과 같은 식으로 원본에서 재생성한다.
HUD/layout/image yml 은 건드리지 않는다(파일명·개수·hd 가 그대로라 정의가 불변이다).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[3]
BETTERHUD = SCRIPTS / "ops" / "prod" / "betterhud"
ASSET = BETTERHUD / "assets" / "dialogue"
MANIFEST = SCRIPTS / "npc-profiles" / "npc-dialogue-portrait-manifest.json"
CID = 162
STATES = ("base", "progress", "complete")

spec = importlib.util.spec_from_file_location("gen", BETTERHUD / "gen_npc_portrait_huds.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def frame_rgba(src: Image.Image, cw: int, ch: int) -> Image.Image:
    """gen.frame() 과 같은 구도, 팔레트 양자화만 생략.

    ★128x154 «asset» 은 다른 NPC 전부 RGBA 다(_sm/_md/_lg/_xl 만 P 팔레트).
      여기서 양자화하면 이 NPC 하나만 규격이 달라진다.
    """
    box = src.split()[3].getbbox() or (0, 0, src.width, src.height)
    im = src.crop(box)
    vw = gen.VISIBLE[0] / gen.CANVAS[0] * cw
    vh = gen.VISIBLE[1] / gen.CANVAS[1] * ch
    k = min(vw / im.width, vh / im.height)
    w, h = max(1, round(im.width * k)), max(1, round(im.height * k))
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    out.alpha_composite(im.resize((w, h), Image.Resampling.LANCZOS), ((cw - w) // 2, ch - h))
    return out


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entry = next(e for e in manifest["entries"] if e["citizensId"] == CID)
    for state in STATES:
        src = HERE / "transparent" / f"162_{state}_v1.png"
        if not src.exists():
            raise SystemExit(f"missing {src} — repair_headgear.py 먼저 실행")
        entry["states"][state]["source"] = str(src)
        key = entry["states"][state]["key"]
        with Image.open(src) as raw:
            raw = raw.convert("RGBA")
            frame_rgba(raw, *gen.CANVAS).save(ASSET / f"npc_{key}.png", optimize=True)
            for sid, scale in gen.SIZES:
                dw = round(gen.CANVAS[0] * gen.PORTRAIT_SCALE * scale)
                dh = round(gen.CANVAS[1] * gen.PORTRAIT_SCALE * scale)
                hd = min(gen.HD, max(1.0, raw.width / max(1, dw)))
                if round(1.0 / hd, 4) != round(1.0 / gen.HD, 4):
                    raise SystemExit(
                        f"hd 가 {hd} 로 바뀌었다 — npc-dialogue-image.yml 의 scale 이 달라진다")
                gen.frame(raw, max(1, round(dw * hd)), max(1, round(dh * hd))).save(
                    ASSET / f"npc_{key}_{sid}.png", optimize=True)
        print(f"{key}: asset + {len(gen.SIZES)} sizes regenerated")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"manifest source updated for {CID}")


if __name__ == "__main__":
    main()
