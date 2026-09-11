#!/usr/bin/env bash
# 길드 엠블럼 Java overlay pack을 06:00 재시작 직전에 공개/활성화한다.
# Geyser용 mcpack/mapping은 같은 nightly-restart.sh의 geyser staging 절이 이어서 승격한다.
set -euo pipefail

SERVER_ROOT=${SERVER_ROOT:-$HOME/mcserver}
STAGE_DIR=${STAGE_DIR:-$SERVER_ROOT/staging/guild-icons}
PLUGIN_DATA=${PLUGIN_DATA:-$SERVER_ROOT/plugins/BlockShip}
WEB_ROOT=${WEB_ROOT:-/var/www/barkan}
DRYRUN=${DRY:-0}
SUDO_CMD=${SUDO_CMD-sudo}
ZIP="$STAGE_DIR/guild-icons.zip"
MANIFEST="$STAGE_DIR/guild-icons.json"

# 3은 «대기 없음» — nightly가 오류로 보고하지 않는 정상 종료값이다.
[ -f "$ZIP" ] || [ -f "$MANIFEST" ] || exit 3
if [ ! -f "$ZIP" ] || [ ! -f "$MANIFEST" ]; then
  echo "길드 아이콘 staging 불완전(zip/manifest 한쪽 없음)"
  exit 1
fi

if ! unzip -tqq "$ZIP" >/dev/null 2>&1; then
  echo "길드 아이콘 ZIP 검증 실패"
  exit 1
fi

read -r sha public_name count < <(python3 - "$ZIP" "$MANIFEST" <<'PY'
import hashlib,json,pathlib,re,sys,uuid,zipfile
zpath=pathlib.Path(sys.argv[1]); mpath=pathlib.Path(sys.argv[2])
m=json.loads(mpath.read_text())
assert m.get("version") == 1
uuid.UUID(m["packId"])
sha=hashlib.sha1(zpath.read_bytes()).hexdigest()
assert re.fullmatch(r"[0-9a-f]{40}", m.get("sha1", ""))
assert m["sha1"] == sha
name=f"barkan-resourcepack-guild-icons-{sha}.zip"
assert m["url"] == "https://barkan.kr/" + name
models=m.get("models")
assert isinstance(models, dict)
assert all(re.fullmatch(r"g_[0-9a-f]{20}", k) and re.fullmatch(r"[0-9a-f]{64}", v)
           for k,v in models.items())
with zipfile.ZipFile(zpath) as z:
    assert "pack.mcmeta" in z.namelist()
    for key in models:
        assert f"assets/minecraft/textures/item/barkan_guild/{key}.png" in z.namelist()
        assert f"assets/barkan/models/guild/{key}.json" in z.namelist()
        assert f"assets/barkan/items/guild/{key}.json" in z.namelist()
print(sha, name, len(models))
PY
) || { echo "길드 아이콘 manifest/ZIP 교차검증 실패"; exit 1; }

if [ "$DRYRUN" = "1" ]; then
  echo "🚀 길드 아이콘 overlay ${count}개 승격 예정 (Java)"
  exit 0
fi

$SUDO_CMD install -d -m 0755 "$WEB_ROOT"
$SUDO_CMD install -m 0644 "$ZIP" "$WEB_ROOT/$public_name"
published_sha=$(sha1sum "$WEB_ROOT/$public_name" | awk '{print $1}')
if [ "$published_sha" != "$sha" ]; then
  echo "길드 아이콘 공개 파일 SHA-1 불일치"
  exit 1
fi

mkdir -p "$PLUGIN_DATA"
if [ -f "$PLUGIN_DATA/guild-icons.json" ]; then
  cp -f "$PLUGIN_DATA/guild-icons.json" "$PLUGIN_DATA/guild-icons.json.bak-$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)"
fi
install -m 0644 "$MANIFEST" "$PLUGIN_DATA/guild-icons.json.new"
mv -f "$PLUGIN_DATA/guild-icons.json.new" "$PLUGIN_DATA/guild-icons.json"
rm -f "$ZIP" "$MANIFEST"
rmdir "$STAGE_DIR" 2>/dev/null || true

# 콘텐츠 주소형 파일이라 롤백용 최신 5개만 남긴다. macOS 기본 Bash 3에서도
# PREVIEW/로컬 검산이 돌아가도록 mapfile·GNU find -printf는 쓰지 않는다.
while IFS= read -r old; do
  [ -n "$old" ] || continue
  case "$old" in "$WEB_ROOT"/barkan-resourcepack-guild-icons-*.zip) $SUDO_CMD rm -f -- "$old" ;; esac
done < <(ls -1t "$WEB_ROOT"/barkan-resourcepack-guild-icons-*.zip 2>/dev/null | tail -n +6)

echo "🚀 길드 아이콘 overlay ${count}개 승격 (Java, ${sha:0:8})"
