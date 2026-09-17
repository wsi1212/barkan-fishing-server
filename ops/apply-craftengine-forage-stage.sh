#!/usr/bin/env bash
# Apply the staged forage furniture source and its already-generated CraftEngine pack.
# This is only called by nightly-restart immediately before its scheduled restart.
set -euo pipefail

STAGING=${STAGING:-$HOME/mcserver/staging}
PAYLOAD="$STAGING/CraftEngine/forage-v1"
CE=${CE:-$HOME/mcserver/plugins/CraftEngine}
LIVE="$CE/resources/barkan_furniture"
SOURCE="$PAYLOAD/resources/barkan_furniture"
STAGED_PACK="$PAYLOAD/generated/resource_pack.zip"
LIVE_PACK="$CE/generated/resource_pack.zip"

[ -d "$PAYLOAD" ] || exit 3
[ -f "$SOURCE/configuration/forage_custom.yml" ] || {
  echo "채집물 설정 누락: $SOURCE/configuration/forage_custom.yml" >&2
  exit 1
}
[ -f "$STAGED_PACK" ] || { echo "생성된 CraftEngine 팩 누락: $STAGED_PACK" >&2; exit 1; }

python3 - "$SOURCE/configuration/forage_custom.yml" <<'PY'
import re
import sys

text = open(sys.argv[1], encoding="utf-8").read()
items = re.findall(r"^  barkan:forage_[^:\n]+:\s*$", text, re.M)
required = ("z_cliffhoney", "z_hanginghoney", "z_cliffginseng")
if len(items) != 34:
    raise SystemExit(f"forage_custom.yml 항목 수 불일치: {len(items)} (기대 34)")
for item in required:
    if f"barkan:forage_{item}:" not in text:
        raise SystemExit(f"forage_custom.yml 신규 항목 누락: {item}")
PY

required=(z_cliffhoney z_hanginghoney z_cliffginseng)
for id in "${required[@]}"; do
  for rel in \
    "models/item/furniture/forage/$id.json" \
    "models/item/furniture/forage/icon/$id.json" \
    "textures/furniture/forage/$id.png" \
    "textures/furniture/forage/icon/$id.png"; do
    [ -s "$SOURCE/resourcepack/assets/barkan/$rel" ] || {
      echo "채집물 에셋 누락: $rel" >&2
      exit 1
    }
  done
done
unzip -tqq "$STAGED_PACK" >/dev/null || { echo "생성된 CraftEngine 팩 ZIP 손상" >&2; exit 1; }
for id in "${required[@]}"; do
  unzip -Z1 "$STAGED_PACK" | grep -qx "assets/barkan/models/item/furniture/forage/$id.json" || {
    echo "생성된 CraftEngine 팩 모델 누락: $id" >&2
    exit 1
  }
done

tmp_config="$LIVE/configuration/forage_custom.yml.forage-stage.tmp"
cp "$SOURCE/configuration/forage_custom.yml" "$tmp_config"
mv -f "$tmp_config" "$LIVE/configuration/forage_custom.yml"

for id in "${required[@]}"; do
  for rel in \
    "models/item/furniture/forage/$id.json" \
    "models/item/furniture/forage/icon/$id.json" \
    "textures/furniture/forage/$id.png" \
    "textures/furniture/forage/icon/$id.png"; do
    mkdir -p "$(dirname "$LIVE/resourcepack/assets/barkan/$rel")"
    cp "$SOURCE/resourcepack/assets/barkan/$rel" "$LIVE/resourcepack/assets/barkan/$rel"
  done
done

mkdir -p "$(dirname "$LIVE_PACK")"
tmp_pack="$LIVE_PACK.forage-stage.tmp"
cp "$STAGED_PACK" "$tmp_pack"
mv -f "$tmp_pack" "$LIVE_PACK"
rm -rf "$PAYLOAD"
echo "CraftEngine 채집물 3종·생성팩 적용 준비"
