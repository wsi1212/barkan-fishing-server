#!/usr/bin/env python3
"""Patch the BarkanAquarium display-scale constants in a verified JAR copy.

The plugin source is not retained locally.  This intentionally changes only
four double constants in AquariumManager.class and rejects any unexpected JAR
revision, rather than attempting an unverified class rewrite.
"""

from __future__ import annotations

import argparse
import struct
import sys
import zipfile
from pathlib import Path


CLASS = "kr/barkan/aquarium/AquariumManager.class"
# Current formula: clamp(0.36 + sizeCm / 280, 0.36, 0.82)
# New formula:     clamp(0.42 + sizeCm / 500, 0.42, 1.75)
# The JVM constant pool interns repeated literals, so 0.36 appears once even
# though both the base and lower-clamp operands reference it.
REPLACEMENTS = ((0.36, 0.42, 1), (280.0, 500.0, 1), (0.82, 1.75, 1))


def replace_double(blob: bytes, old: float, new: float, expected: int) -> bytes:
    old_bytes = struct.pack(">d", old)
    new_bytes = struct.pack(">d", new)
    found = blob.count(old_bytes)
    if found != expected:
        raise ValueError(
            f"{CLASS}: expected {expected} occurrences of {old}, found {found}; "
            "the JAR revision is not the validated target"
        )
    return blob.replace(old_bytes, new_bytes)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.source.resolve() == args.output.resolve():
        parser.error("output must be a new file; the original JAR is preserved")

    with zipfile.ZipFile(args.source) as source:
        if CLASS not in source.namelist():
            raise ValueError(f"missing {CLASS}")
        patched = source.read(CLASS)
        for old, new, expected in REPLACEMENTS:
            patched = replace_double(patched, old, new, expected)

        with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as output:
            for info in source.infolist():
                payload = patched if info.filename == CLASS else source.read(info.filename)
                output.writestr(info, payload)

    with zipfile.ZipFile(args.output) as check:
        check.testzip()
        verified = check.read(CLASS)
    for old, new, expected in REPLACEMENTS:
        if verified.count(struct.pack(">d", old)) != 0:
            raise ValueError(f"verification failed: old constant {old} remains")
        if verified.count(struct.pack(">d", new)) != expected:
            raise ValueError(f"verification failed: new constant {new} count is wrong")

    print("Verified display scale: clamp(0.42 + size_cm / 500, 0.42, 1.75)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"Patch aborted: {error}", file=sys.stderr)
        raise SystemExit(1)
