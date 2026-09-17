#!/usr/bin/env bash
# Apply the one-shot CraftEngine dish base migration prepared in staging.
# CraftEngine reads this file on Paper boot, so this runs only from the scheduled
# maintenance path immediately before its normal restart — never against a live JVM.
set -euo pipefail

STAGING=${STAGING:-$HOME/mcserver/staging}
MARKER="$STAGING/CraftEngine/dish-cookie-v1"
DISHES=${DISHES:-$HOME/mcserver/plugins/CraftEngine/resources/barkan_furniture/configuration/dishes.yml}

[ -f "$MARKER" ] || exit 3
[ -f "$DISHES" ] || { echo "CraftEngine dishes.yml 없음: $DISHES" >&2; exit 1; }

python3 - "$DISHES" <<'PY'
import os
import re
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as handle:
    lines = handle.readlines()

current = None
changed = 0
food_defs = 0
for index, line in enumerate(lines):
    match = re.match(r"^  (barkan:dish_(?:cr|fd)_[^:]+):\s*$", line)
    if match:
        current = match.group(1)
        food_defs += 1
        continue
    if current is None:
        continue
    material = re.match(r"^(\s*material:\s*)(\S+)(\s*(?:#.*)?\n?)$", line)
    if material:
        if material.group(2) != "cookie":
            lines[index] = material.group(1) + "cookie" + material.group(3)
            changed += 1
        current = None

if food_defs != 58:
    raise SystemExit(f"expected 58 current dish definitions, found {food_defs}")

temporary = path + ".dish-cookie.tmp"
with open(temporary, "w", encoding="utf-8") as handle:
    handle.writelines(lines)
os.replace(temporary, path)
print(f"CraftEngine 요리 {food_defs}종 확인 · 베이스 {changed}종을 cookie로 정규화")
PY

rm -f "$MARKER"
