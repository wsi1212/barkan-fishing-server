#!/usr/bin/env python3
"""Split, chroma-key, and frame portrait-repair sheets without touching prod."""
from __future__ import annotations

import argparse
from collections import Counter
from collections import deque
import json
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "npc-profiles" / "imagegen-batch" / "revisions" / "portrait-repair-20260824" / "queue.json"
OUT = ROOT / "npc-profiles" / "imagegen-batch" / "revisions" / "portrait-repair-20260824"
CHROMA = Path("/Users/user/.codex/skills/.system/imagegen/scripts/remove_chroma_key.py")
CANVAS = (128, 154)
VISIBLE = (118, 138)


def dominant_green_key(src: Path) -> str:
    """Find ImageGen's actual neon-green key, including near-#00ff00 variants."""
    im = Image.open(src).convert("RGB")
    counts: Counter[tuple[int, int, int]] = Counter()
    for r, g, b in im.getdata():
        if g >= 150 and g - max(r, b) >= 80:
            counts[(round(r / 4) * 4, round(g / 4) * 4, round(b / 4) * 4)] += 1
    if not counts:
        return "#00ff00"
    r, g, b = counts.most_common(1)[0][0]
    return f"#{r:02x}{g:02x}{b:02x}"


def remove_chroma(src: Path, dst: Path) -> None:
    key = dominant_green_key(src)
    subprocess.run([
        "python3", str(CHROMA), "--input", str(src), "--out", str(dst),
        "--auto-key", "none", "--key-color", key, "--tolerance", "32",
        "--soft-matte", "--transparent-threshold", "12",
        "--opaque-threshold", "220", "--despill", "--force",
    ], check=True)


def frame(src: Image.Image) -> Image.Image:
    src = src.convert("RGBA")
    bbox = src.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("empty alpha")
    crop = src.crop(bbox)
    vw, vh = VISIBLE
    cw, ch = CANVAS
    k = min(vw / crop.width, vh / crop.height)
    scaled = crop.resize((max(1, round(crop.width * k)), max(1, round(crop.height * k))), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    out.alpha_composite(scaled, ((cw - scaled.width) // 2, ch - scaled.height))
    return out


def segments(values: list[int], threshold: int = 100) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    start = None
    for i, value in enumerate(values + [0]):
        if value > threshold and start is None:
            start = i
        elif value <= threshold and start is not None:
            if i - start > 3:
                out.append((start, i))
            start = None
    return out


def strip_connected_white_frame(panel: Image.Image) -> Image.Image:
    """Remove ImageGen's white panel/grid frame without erasing white garments."""
    im = panel.convert("RGBA")
    w, h = im.size
    px = im.load()

    def is_frame_white(x: int, y: int) -> bool:
        r, g, b, a = px[x, y]
        return a > 20 and min(r, g, b) >= 220 and max(r, g, b) - min(r, g, b) <= 45

    seen: set[tuple[int, int]] = set()
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            if is_frame_white(x, y) and (x, y) not in seen:
                seen.add((x, y)); q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if is_frame_white(x, y) and (x, y) not in seen:
                seen.add((x, y)); q.append((x, y))
    while q:
        x, y = q.popleft()
        px[x, y] = (0, 0, 0, 0)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and is_frame_white(nx, ny):
                seen.add((nx, ny)); q.append((nx, ny))
    return im


def detect_panels(im: Image.Image, count: int) -> list[Image.Image]:
    """Extract subjects whether ImageGen used 2x2 or a horizontal strip."""
    rgba = im.convert("RGBA")
    w, h = rgba.size
    alpha = rgba.getchannel("A")
    x_counts = [0] * w
    y_counts = [0] * h
    px = alpha.load()
    for y in range(h):
        row = 0
        for x in range(w):
            if px[x, y] > 20:
                x_counts[x] += 1
                row += 1
        y_counts[y] = row
    xs = segments(x_counts)
    ys = segments(y_counts)
    # Ignore thin white gutters/frame remnants; a real panel is substantially larger.
    wide_x = [seg for seg in xs if seg[1] - seg[0] > 100]
    wide_y = [seg for seg in ys if seg[1] - seg[0] > 100]
    boxes: list[tuple[int, int, int, int]] = []
    if len(wide_x) >= count and len(wide_y) == 1:
        boxes = [(x0, wide_y[0][0], x1, wide_y[0][1]) for x0, x1 in wide_x[:count]]
    elif len(wide_x) >= 2 and len(wide_y) >= 2:
        for y0, y1 in wide_y:
            for x0, x1 in wide_x:
                tile = alpha.crop((x0, y0, x1, y1))
                if tile.getbbox() is not None:
                    boxes.append((x0, y0, x1, y1))
        boxes = boxes[:count]
    elif len(wide_x) == 1 and len(wide_y) == 1:
        boxes = [(wide_x[0][0], wide_y[0][0], wide_x[0][1], wide_y[0][1])]
    if len(boxes) != count:
        raise ValueError(f"could not detect {count} panels: x={xs}, y={ys}")
    return [strip_connected_white_frame(rgba.crop(box)) for box in boxes]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cid", type=int, required=True)
    ap.add_argument("--source", type=Path, required=True)
    args = ap.parse_args()
    item = next(x for x in json.loads(QUEUE.read_text(encoding="utf-8"))["queue"] if x["citizensId"] == args.cid)
    raw_dir = OUT / "raw"
    transparent_dir = OUT / "transparent"
    framed_dir = OUT / "framed"
    for d in (raw_dir, transparent_dir, framed_dir):
        d.mkdir(parents=True, exist_ok=True)
    raw_sheet = raw_dir / f"{args.cid:03d}_sheet.png"
    transparent_sheet = transparent_dir / f"{args.cid:03d}_sheet.png"
    source = Image.open(args.source).convert("RGBA")
    source.save(raw_sheet)
    remove_chroma(raw_sheet, transparent_sheet)
    panels = detect_panels(Image.open(transparent_sheet), len(item["states"]))
    for state, panel in zip(item["states"], panels):
        transparent = transparent_dir / f"{args.cid:03d}_{state}.png"
        framed = framed_dir / f"{args.cid:03d}_{state}.png"
        panel.save(transparent)
        frame(panel).save(framed)
    print(json.dumps({"cid": args.cid, "states": item["states"], "source": str(args.source)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
