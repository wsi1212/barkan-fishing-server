#!/usr/bin/env python3
"""Build compact dialogue portraits from the server's authoritative NPC skins.

The generated portraits are intentionally deterministic: every NPC is sourced from
the 64x64 skin produced by skin-forge, then presented in the warm, outlined pixel
portrait language of BetterHUD's grandfather sample.  Dialogue keywords only add
small expression variants; they never replace the character's clothing or palette.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "npc-profiles" / "out"
SKINS = ROOT / "skin-forge" / "out"
NPC_JSON = Path("/Users/user/development/blockship-plugin/npc.json")
DIALOGUE_JSON = Path("/Users/user/development/blockship-plugin/dialogue.json")

PREFIX_BY_MODULE = {
    "desertfolk.py": "df_",
    "crewmisc.py": "cm_",
    "townsfolk.py": "tf_",
    "tradetown.py": "tt_",
    "library_staff.py": "lib_",
    "royal_guards.py": "guard_",
    "rankers.py": "",
    "dealers.py": "",
}

STANDALONE = {
    3: "tf_grandpa", 14: "otto", 20: "yusuf", 44: "king", 45: "archivist",
    48: "bellringer", 49: "albis", 57: "gregor", 58: "valentin",
    59: "nina", 66: "goodwife", 68: "villager", 69: "fishwife", 70: "hagen",
    71: "tf_sergan", 74: "elder_fisher", 77: "crone", 82: "marco",
    93: "beatrice", 95: "aldo", 102: "heinrich", 117: "sieghardt", 118: "brandt",
    119: "lotte", 120: "fritz", 121: "albrecht", 122: "hilde",
    132: "gunnar", 143: "giovanni", 158: "albis", 161: "bartender",
    162: "hagen", 171: "valdemar", 172: "rainer", 173: "gerhardt",
    174: "tecla", 175: "hartmut",
}

SPECIAL = {154: "gm_whale", 155: "gm_sharp", 156: "gm_addict", 157: "gm_ruined",
           167: "ci_captain", 168: "ci_deckhand", 169: "ci_cook", 170: "ci_rigger"}


def parse_group_maps() -> dict[int, str]:
    result: dict[int, str] = {}
    for module, prefix in PREFIX_BY_MODULE.items():
        text = (ROOT / "skin-forge" / module).read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"(?:file|name)=['\"]([^'\"]+)['\"],\s*cid=(\d+)", text):
            result[int(m.group(2))] = prefix + m.group(1)
    return result


def skin_stem(cid: int) -> str | None:
    if cid in SPECIAL:
        return SPECIAL[cid]
    if cid in STANDALONE:
        return STANDALONE[cid]
    return parse_group_maps().get(cid)


def flatten_lines(body: object) -> list[str]:
    lines: list[str] = []
    if isinstance(body, dict):
        for node in body.values():
            if isinstance(node, dict):
                lines.extend(str(x) for x in (node.get("lines") or []))
    return lines


def expression_set(lines: Iterable[str], roles: list[str]) -> list[str]:
    text = " ".join(lines)
    expressions = ["base"]
    if lines:
        expressions.append("talk")
    if re.search(r"기쁘|좋아|환영|축하|고맙|하하|웃|멋지|다행|반갑", text):
        expressions.append("happy")
    if re.search(r"위험|조심|비밀|두렵|걱정|슬프|잃|죄송|미안|침묵|죽", text):
        expressions.append("worried")
    if re.search(r"!|당장|어서|감히|싫|화|분노|안 돼|금지", text):
        expressions.append("stern")
    if re.search(r"어\?|정말|뭐지|놀랍|처음|설마|…", text):
        expressions.append("surprised")
    if not lines and roles:
        expressions = ["base"]
    return list(dict.fromkeys(expressions))[:5]


def dominant_dark(im: Image.Image) -> tuple[int, int, int, int]:
    px = [p for p in im.getdata() if p[3] > 0]
    return min(px, key=lambda p: sum(p[:3])) if px else (45, 33, 28, 255)


def combine_tile(im: Image.Image, base_box: tuple[int, int, int, int], outer_box: tuple[int, int, int, int]) -> Image.Image:
    base = im.crop(base_box).convert("RGBA")
    outer = im.crop(outer_box).convert("RGBA")
    base.alpha_composite(outer)
    return base


def expression_face(face: Image.Image, expression: str, dark: tuple[int, int, int, int]) -> Image.Image:
    f = face.copy()
    original = face.tobytes()
    d = dark[:3] + (255,)
    ink = tuple(max(0, int(x * 0.65)) for x in dark[:3]) + (255,)
    if expression == "base":
        return f
    # Face pixels are only 8x8. Keep the change compact and place it in the
    # existing eye/mouth bands so the skin remains recognisable at HUD scale.
    if expression == "talk":
        for x in (2, 3, 4, 5):
            f.putpixel((x, 6), ink)
        f.putpixel((3, 7), d)
    elif expression == "happy":
        for x in (2, 3, 4, 5):
            f.putpixel((x, 6), d)
        f.putpixel((2, 5), ink); f.putpixel((5, 5), ink)
    elif expression == "worried":
        f.putpixel((1, 3), d); f.putpixel((2, 3), d)
        f.putpixel((5, 3), d); f.putpixel((6, 3), d)
        f.putpixel((3, 6), d); f.putpixel((4, 6), d)
    elif expression == "stern":
        f.putpixel((1, 3), d); f.putpixel((2, 3), ink)
        f.putpixel((5, 3), ink); f.putpixel((6, 3), d)
        for x in (2, 3, 4, 5): f.putpixel((x, 6), ink)
    elif expression == "surprised":
        for x in (1, 2, 5, 6): f.putpixel((x, 3), d)
        for x in (3, 4): f.putpixel((x, 6), d)
        f.putpixel((3, 7), d); f.putpixel((4, 7), d)
    if f.tobytes() == original:
        # Some skins already contain the requested mouth/brow colour. Force a
        # one-pixel expression cue so every manifest variant is a real variant.
        f.putpixel((3, 7), (dark[0] ^ 0x3F, dark[1] ^ 0x3F, dark[2] ^ 0x3F, 255))
    return f


def paste_scaled(dst: Image.Image, src: Image.Image, xy: tuple[int, int], scale: int) -> None:
    dst.alpha_composite(src.resize((src.width * scale, src.height * scale), Image.Resampling.NEAREST), xy)


def draw_prop(draw: ImageDraw.ImageDraw, roles: list[str], x: int, y: int, s: int, cid: int) -> None:
    role = set(roles)
    outline = (52, 31, 24, 255)
    brass = (183, 132, 50, 255)
    cream = (224, 204, 157, 255)
    teal = (52, 123, 125, 255)
    brown = (111, 65, 35, 255)
    if role & {"shop", "ferry", "market", "ranking"}:
        draw.line((x, y + 42*s, x + 18*s, y + 5*s), fill=outline, width=max(2, s))
        draw.line((x + 3*s, y + 42*s, x + 20*s, y + 5*s), fill=brass, width=max(1, s))
        draw.polygon([(x+18*s,y+5*s),(x+26*s,y+12*s),(x+18*s,y+18*s),(x+11*s,y+12*s)], fill=teal, outline=outline)
    elif role & {"smithy", "drillShop"}:
        draw.line((x + 15*s, y + 7*s, x + 15*s, y + 43*s), fill=brown, width=3*s)
        draw.rectangle((x + 4*s, y + 4*s, x + 27*s, y + 13*s), fill=brass, outline=outline, width=s)
    elif role & {"cooking"}:
        draw.ellipse((x + 4*s, y + 26*s, x + 27*s, y + 45*s), fill=brass, outline=outline, width=s)
        draw.line((x + 15*s, y + 28*s, x + 22*s, y + 4*s), fill=brown, width=2*s)
    elif role & {"casino"} or 154 <= cid <= 157:
        draw.polygon([(x+4*s,y+7*s),(x+22*s,y+4*s),(x+27*s,y+30*s),(x+9*s,y+34*s)], fill=cream, outline=outline)
        draw.rectangle((x+13*s,y+14*s,x+16*s,y+17*s), fill=(169,48,51,255))
    elif role & {"horseRental"}:
        draw.arc((x+4*s,y+8*s,x+30*s,y+38*s), 30, 330, fill=brass, width=2*s)
        draw.line((x+17*s,y+18*s,x+28*s,y+42*s), fill=brown, width=2*s)
    elif role & {"heal"}:
        draw.rectangle((x+10*s,y+14*s,x+24*s,y+42*s), fill=teal, outline=outline, width=s)
        draw.line((x+17*s,y+5*s,x+17*s,y+18*s), fill=brass, width=2*s)
        draw.line((x+11*s,y+11*s,x+23*s,y+11*s), fill=brass, width=2*s)
    else:
        draw.rectangle((x+5*s,y+12*s,x+28*s,y+39*s), fill=cream, outline=outline, width=s)
        draw.line((x+9*s,y+18*s,x+24*s,y+18*s), fill=brown, width=s)
        draw.line((x+9*s,y+24*s,x+20*s,y+24*s), fill=brown, width=s)


def build_one(cid: int, label: str, roles: list[str], lines: list[str], stem: str, expression: str) -> Path:
    src = Image.open(SKINS / f"{stem}.png").convert("RGBA")
    dark = dominant_dark(src.crop((8, 8, 16, 16)))
    face = combine_tile(src, (8, 8, 16, 16), (40, 8, 48, 16))
    face = expression_face(face, expression, dark)
    body = combine_tile(src, (20, 20, 28, 32), (20, 36, 28, 48))
    arm_r = combine_tile(src, (44, 20, 48, 32), (44, 36, 48, 48))
    arm_l = combine_tile(src, (36, 52, 40, 64), (52, 52, 56, 64))

    # Logical 128px portrait. The 6px blocks preserve the Minecraft skin's
    # pixel grammar, while the outline and prop echo the BetterHUD sample.
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    paste_scaled(im, body, (40, 53), 6)
    paste_scaled(im, arm_l, (16, 53), 6)
    paste_scaled(im, arm_r, (88, 53), 6)
    paste_scaled(im, face, (40, 4), 6)

    alpha = im.getchannel("A")
    outline = alpha.filter(ImageFilter.MaxFilter(9))
    ring = ImageChops.subtract(outline, alpha)
    ink = Image.new("RGBA", im.size, (54, 32, 24, 235))
    ink.putalpha(ring.point(lambda p: min(235, p)))
    final = Image.alpha_composite(ink, im)
    d = ImageDraw.Draw(final)
    draw_prop(d, roles, 91, 82, 1, cid)
    # A tiny warm highlight prevents flat atlas colours without changing the
    # authoritative outfit palette.
    d.rectangle((42, 59, 43, 60), fill=(255, 226, 171, 75))

    safe = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", label).strip("_")
    path = OUT / f"{cid:03d}_{safe}__{expression}.png"
    final.save(path)
    return path


def main() -> int:
    npcs = json.loads(NPC_JSON.read_text(encoding="utf-8"))["npcs"]
    dialogues = json.loads(DIALOGUE_JSON.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    mapping = parse_group_maps()
    manifest = []
    missing = []
    for name, data in npcs.items():
        cid = int(data["citizensId"])
        stem = SPECIAL.get(cid) or STANDALONE.get(cid) or mapping.get(cid)
        if not stem or not (SKINS / f"{stem}.png").exists():
            missing.append({"cid": cid, "name": name, "stem": stem})
            continue
        lines = flatten_lines(dialogues.get(name, {}))
        roles = [k for k, v in data.items() if v is True]
        exprs = expression_set(lines, roles)
        files = [str(build_one(cid, name, roles, lines, stem, e).relative_to(ROOT)) for e in exprs]
        manifest.append({"citizensId": cid, "npc": name, "displayName": data.get("name", name),
                         "skin": stem, "roles": roles, "dialogueLines": len(lines),
                         "expressions": exprs, "files": files})
    (OUT.parent / "manifest.json").write_text(json.dumps({"reference": "BetterHUD portrait-grandfather-hud.png", "npcs": manifest, "missing": missing}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"npcs": len(manifest), "missing": missing, "files": sum(len(x["files"]) for x in manifest)}, ensure_ascii=False, indent=2))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
