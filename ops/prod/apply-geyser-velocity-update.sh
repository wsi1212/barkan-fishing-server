#!/usr/bin/env bash
# Scheduled-only Geyser core updater for the public Velocity proxy.
#
# A live Velocity plugin JAR must never be overwritten: Velocity has already
# loaded its classes.  This helper is deliberately called only by the 06:00
# nightly maintenance after Paper has returned from its own restart.  It stops
# the public proxy once, promotes the verified .next JAR, and restores the
# previous JAR automatically if Velocity fails its health check.
set -euo pipefail

NETWORK_ROOT=${BARKAN_NETWORK_ROOT:-/home/ubuntu/mc-network}
VELOCITY_DIR=${BARKAN_VELOCITY_DIR:-$NETWORK_ROOT/velocity}
GEYSER_JAR=${BARKAN_GEYSER_JAR:-$VELOCITY_DIR/plugins/Geyser-Velocity.jar}
NEXT_JAR=${GEYSER_JAR}.next
BACKUP_DIR=${BARKAN_GEYSER_BACKUPS:-/home/ubuntu/mcserver/backups/geyser-velocity}
STATUS_FILE=${BARKAN_MAINTENANCE_STATUS:-$NETWORK_ROOT/control/status.json}
KEEP_BACKUPS=${BARKAN_GEYSER_KEEP_BACKUPS:-7}
STAGING_DIR=${BARKAN_GEYSER_STAGING:-/home/ubuntu/mcserver/staging/geyser}
EXTENSIONS_DIR=${BARKAN_GEYSER_EXTENSIONS:-$VELOCITY_DIR/plugins/Geyser-Velocity/extensions}

[ -s "$NEXT_JAR" ] || { echo "Geyser core staging 없음"; exit 3; }
[ -s "$GEYSER_JAR" ] || { echo "현재 Geyser JAR 없음: $GEYSER_JAR" >&2; exit 5; }
systemctl is-active --quiet barkan-velocity || {
  echo "Velocity 비활성 — Geyser 교체 보류" >&2; exit 5;
}

# Do not promote an arbitrary JAR merely because it happens to be named .next.
version=$(unzip -p "$NEXT_JAR" velocity-plugin.json | python3 -c '
import json, sys
d = json.load(sys.stdin)
if d.get("id") != "geyser" or "Geyser" not in d.get("name", ""):
    raise SystemExit("not a Geyser Velocity plugin")
print(d.get("version", "unknown"))
') || { echo "Geyser staging JAR 검증 실패" >&2; exit 6; }

# Extension JARs require the same full Velocity restart as the core JAR.  Keep
# their staging copies until the new proxy passes health checks, so a failed
# start can be retried at the following maintenance window.
declare -a extension_sources=()
while IFS= read -r extension; do extension_sources+=("$extension"); done \
  < <(find "$STAGING_DIR" -maxdepth 1 -type f -name '*.jar' 2>/dev/null | sort)
for extension in "${extension_sources[@]}"; do
  unzip -p "$extension" extension.yml | python3 -c '
import re, sys
t = sys.stdin.read()
if not re.search(r"^id:\s*\S+\s*$", t, re.M) or not re.search(r"^main:\s*\S+\s*$", t, re.M):
    raise SystemExit("invalid Geyser extension.yml")
' || { echo "Geyser extension 검증 실패: $(basename "$extension")" >&2; exit 6; }
done

stamp=$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP_DIR"
backup="$BACKUP_DIR/Geyser-Velocity.jar.$stamp"
cp -p "$GEYSER_JAR" "$backup"
extension_backup="$BACKUP_DIR/extensions-$stamp"
mkdir -p "$extension_backup"
declare -a extension_destinations=()
declare -a extension_created=()

sudo systemctl stop barkan-velocity
for _wait in $(seq 1 30); do
  systemctl is-active --quiet barkan-velocity || break
  sleep 1
done
if systemctl is-active --quiet barkan-velocity; then
  echo "Velocity 정지 시간 초과 — Geyser 교체 취소" >&2
  sudo systemctl start barkan-velocity || true
  exit 7
fi

# The former active file is retained for diagnosis, while the backup above is
# the known-good rollback source.  mv is atomic on this filesystem.
failed_candidate="$BACKUP_DIR/Geyser-Velocity.jar.failed-$stamp"
mv -f "$GEYSER_JAR" "$failed_candidate"
mv -f "$NEXT_JAR" "$GEYSER_JAR"
for extension in "${extension_sources[@]}"; do
  name=$(basename "$extension")
  destination="$EXTENSIONS_DIR/$name"
  mkdir -p "$EXTENSIONS_DIR"
  if [ -f "$destination" ]; then
    cp -p "$destination" "$extension_backup/$name"
    extension_destinations+=("$destination")
  else
    extension_created+=("$destination")
  fi
  temporary="$destination.new-$stamp"
  cp -p "$extension" "$temporary"
  mv -f "$temporary" "$destination"
done

rollback(){
  local reason="$1"
  echo "Geyser 기동 실패($reason) — 이전 JAR 자동 복구" >&2
  sudo systemctl stop barkan-velocity || true
  cp -p "$backup" "$GEYSER_JAR"
  for destination in "${extension_destinations[@]}"; do
    cp -p "$extension_backup/$(basename "$destination")" "$destination"
  done
  for destination in "${extension_created[@]}"; do rm -f "$destination"; done
  sudo systemctl start barkan-velocity || true
}

if ! sudo systemctl start barkan-velocity; then
  rollback "start 명령"
  exit 8
fi

healthy=0
for _wait in $(seq 1 45); do
  if systemctl is-active --quiet barkan-velocity \
      && python3 - "$STATUS_FILE" <<'PY' >/dev/null 2>&1
import json, sys, time
d = json.load(open(sys.argv[1], encoding="utf-8"))
assert time.time() * 1000 - int(d.get("updatedEpochMs", 0)) < 8000
PY
  then
    healthy=1
    break
  fi
  sleep 2
done
if [ "$healthy" != 1 ]; then
  rollback "health check"
  exit 8
fi

# Keep rollback copies bounded.  The failed candidate remains for this run.
ls -1t "$BACKUP_DIR"/Geyser-Velocity.jar.[0-9]* 2>/dev/null | tail -n +$((KEEP_BACKUPS + 1)) | xargs -r rm -f
if [ "${#extension_sources[@]}" -gt 0 ]; then
  rm -f "${extension_sources[@]}"
  echo "Geyser Velocity ${version} + extension ${#extension_sources[@]}개 적용 및 재기동 확인"
else
  echo "Geyser Velocity ${version} 적용 및 재기동 확인"
fi
