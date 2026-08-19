#!/usr/bin/env python3
"""Generate BetterHud portrait images/layouts/HUDs from the portrait manifest.

BetterHud's single-image provider cannot select a PNG from a string variable.  Each
portrait/state therefore gets its own HUD, and NpcDialogueHud selects that HUD.
"""
from pathlib import Path
import json
import re
from PIL import Image

HERE = Path(__file__).resolve().parent
ASSET = HERE / "assets" / "dialogue"
MANIFEST = HERE.parents[2] / "npc-profiles" / "npc-dialogue-portrait-manifest.json"
SIZES = [("sm", .75), ("md", 1.00), ("lg", 1.20), ("xl", 1.40)]
PORTRAIT_SCALE = .40

# ★HD 배수. 표시 크기의 이 배로 굽고 setting.scale 로 1/HD 만큼 줄여 표시한다.
#   MC 는 텍스처를 원본 해상도로 들고 그리므로 GUI 배율이 높을수록 원본 픽셀이 살아난다.
#   ★예전엔 매니페스트의 asset(128x154, 이미 축소된 것)에서 또 줄여 표시 크기와 1:1 이었다.
#     원본이 1254px 인데 51px 로 들어가서 화질 불만이 나왔다. 이제 source 에서 직접 뽑는다.
#   3 인 이유: 유저 클라가 GUI 배율 3 이라 그 이상은 눈에 안 보이면서 팩만 커진다.
HD = 3

# 매니페스트의 asset(128x154)이 source 에서 어떻게 나왔는지 실측으로 확정한 구도 공식:
#   알파 트림 -> visible_box 에 맞춤 -> 가로 가운데 · 세로 아래 정렬.
#   표본 18개 중 17개가 픽셀 단위로 일치했다(평균차이 0.00).
CANVAS = (128, 154)
VISIBLE = (118, 138)


def frame(src, cw, ch):
    """원본을 (cw x ch) 캔버스에 위 공식대로 배치한다."""
    box = src.split()[3].getbbox() or (0, 0, src.width, src.height)
    im = src.crop(box)
    vw = VISIBLE[0] / CANVAS[0] * cw
    vh = VISIBLE[1] / CANVAS[1] * ch
    k = min(vw / im.width, vh / im.height)
    w, h = max(1, round(im.width * k)), max(1, round(im.height * k))
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    out.alpha_composite(im.resize((w, h), Image.Resampling.LANCZOS), ((cw - w) // 2, ch - h))
    # ★256색 팔레트로 줄여 저장한다. HD 3배로 올리면 초상화만 52MB 가 되는데,
    #   양자화하면 13MB 로 떨어지고 평균오차는 1.85/255 라 눈으로 구분이 안 된다.
    #   (RGBA 는 FASTOCTREE 만 지원한다 — MEDIANCUT 은 알파에서 예외를 던진다.)
    return out.quantize(colors=256, method=Image.Quantize.FASTOCTREE)


def blocks(text: str, prefix: str):
    found = re.findall(rf"(?ms)^{re.escape(prefix)}.*?(?=^[A-Za-z0-9_]+:|\Z)", text)
    return {re.match(r"^([^:]+):", b).group(1): b.rstrip() for b in found}


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    image_src = (HERE / "npc-dialogue-image.yml").read_text(encoding="utf-8")
    layout_src = (HERE / "npc-dialogue-layout.yml").read_text(encoding="utf-8")
    layout_blocks = blocks(layout_src, "npc_dialogue_layout_")
    layout_templates = {}
    for sid, _ in SIZES:
        template_key = next(
            (key for key in layout_blocks if key.endswith(f"_base_{sid}")), None
        )
        if template_key is None:
            raise KeyError(f"npc_dialogue_layout_*_base_{sid}")
        layout_templates[sid] = (template_key, layout_blocks[template_key])

    image_extra = []
    layout_extra = []
    hud_extra = []
    count = 0
    for entry in manifest["entries"]:
        for state, data in entry["states"].items():
            key = data["key"]
            # ★source(원본 1254px)를 쓴다. asset 은 이미 128x154 로 줄어든 것이라
            #   거기서 또 줄이면 해상도를 두 번 버린다. 원본이 없을 때만 asset 으로 물러선다.
            source = Path(data.get("source") or data["asset"])
            if not source.exists():
                source = Path(data["asset"])
            with Image.open(source) as raw:
                raw = raw.convert("RGBA")
                for sid, scale in SIZES:
                    out_name = f"npc_{key}_{sid}.png"
                    out = ASSET / out_name
                    dw = round(CANVAS[0] * PORTRAIT_SCALE * scale)   # 표시 크기
                    dh = round(CANVAS[1] * PORTRAIT_SCALE * scale)
                    # 원본보다 크게는 못 만든다 — 없는 정보는 만들 수 없다.
                    hd = min(HD, max(1.0, raw.width / max(1, dw)))
                    frame(raw, max(1, round(dw * hd)), max(1, round(dh * hd))).save(out, optimize=True)
                    image_extra.append(
                        f"npc_dialogue_portrait_{key}_{sid}:\n"
                        f"  type: single\n"
                        f"  file: dialogue/{out_name}\n"
                        f"  setting:\n    scale: {round(1.0 / hd, 4)}\n"
                    )
                    template_key, base = layout_templates[sid]
                    block = base.replace(
                        f"{template_key}:",
                        f"npc_dialogue_layout_{key}_{sid}:", 1)
                    block = block.replace(
                        f"name: {template_key.replace('npc_dialogue_layout_', 'npc_dialogue_portrait_', 1)}",
                        f"name: npc_dialogue_portrait_{key}_{sid}", 1)
                    layout_extra.append(block)
                    hud_extra.append(
                        f"npc_dialogue_{key}_{sid}:\n"
                        f"  tick: 1\n"
                        f"  layouts:\n"
                        f"    1:\n"
                        f"      name: npc_dialogue_layout_{key}_{sid}\n"
                        f"      gui:\n"
                        f"        x: 50\n"
                        f"        y: 100\n"
                    )
                    count += 1

    (HERE / "npc-dialogue-image.yml").write_text(
        image_src.rstrip() + "\n\n" + "\n".join(image_extra) + "\n", encoding="utf-8")
    (HERE / "npc-dialogue-layout.yml").write_text(
        "\n\n".join(layout_extra) + "\n", encoding="utf-8")
    (HERE / "npc-dialogue-hud.yml").write_text(
        "\n".join(hud_extra) + "\n", encoding="utf-8")
    print(f"generated {count} portrait HUD variants")


if __name__ == "__main__":
    main()
