#!/usr/bin/env python3
"""Prepare the shared guild-management plate.

The generated art supplies only the guild frame, header plaque, lanterns and
quiet leather/wood content panel.  Different guild screens place different
items, so no screen-specific buttons, labels or sockets are baked into it.
The player inventory grid is added by ``build_plate.py`` at the shared exact
Minecraft coordinates.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SRC = HERE / "src" / "guild_manage"
RAW = SRC / "bg_raw.png"
OUT = SRC / "bg_source.png"
W, H = 704, 888


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"원화가 없습니다: {RAW}")
    raw = Image.open(RAW).convert("RGBA")
    if raw.size != (1122, 1402):
        raise SystemExit(f"길드 관리 원화 크기 {raw.size} != (1122, 1402)")

    # The generator already produced the same portrait proportions as the
    # established 54-slot plate source.  Keep the whole frame visible and let
    # the deterministic builder add the lower player-inventory grid.
    plate = raw.resize((W, H), Image.Resampling.LANCZOS)
    plate.convert("RGB").save(OUT)
    print(f"길드 관리 전용 판 → {OUT} (원화 {raw.size} → {W}x{H})")


if __name__ == "__main__":
    main()
