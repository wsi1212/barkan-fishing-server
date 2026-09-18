#!/usr/bin/env bash
# Geyser standalone 레이아웃을 «라이브를 건드리지 않고» 만든다. 몇 번 돌려도 안전하다.
#   - /home/ubuntu/mc-network/geyser/ 에 config·packs·custom_mappings·extensions·key.pem 배치
#   - Geyser-Standalone.jar 는 플러그인과 «같은 버전»을 받는다(확장 api 호환)
# 컷오버(cutover.sh)는 이 스크립트가 끝난 뒤에만 의미가 있다.
set -euo pipefail

NET=${BARKAN_NETWORK_ROOT:-/home/ubuntu/mc-network}
SRC="$NET/velocity/plugins/Geyser-Velocity"
DST="$NET/geyser"
FGKEY="$NET/velocity/plugins/floodgate/key.pem"
VELOCITY_PORT=${VELOCITY_PORT:-25565}

[ -d "$SRC" ] || { echo "Geyser 플러그인 레이아웃이 없다: $SRC" >&2; exit 2; }
[ -s "$FGKEY" ] || { echo "floodgate key.pem 이 없다: $FGKEY" >&2; exit 2; }

mkdir -p "$DST"/{packs,custom_mappings,extensions}

# 자산 복사 — .bak-* 는 가져가지 않는다(플러그인 쪽에 14벌씩 쌓여 있다).
for d in packs custom_mappings extensions locales; do
  [ -d "$SRC/$d" ] || continue
  mkdir -p "$DST/$d"
  find "$SRC/$d" -maxdepth 1 -type f ! -name '*.bak-*' -exec cp -f {} "$DST/$d/" \;
done
cp -f "$FGKEY" "$DST/key.pem"; chmod 600 "$DST/key.pem"

# config — 플러그인 config 를 그대로 쓰되 «원격 서버» 를 Velocity 로 박는다.
# 플러그인 모드에는 remote 개념이 없어서(같은 JVM) 이 블록이 standalone 의 유일한 추가분이다.
python3 - "$SRC/config.yml" "$DST/config.yml" "$VELOCITY_PORT" <<'PY'
import re, sys
src, dst, port = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(src, encoding="utf-8").read().splitlines()
top = re.compile(r'^[A-Za-z][A-Za-z0-9_-]*:')
try:
    start = next(i for i, l in enumerate(lines) if l.rstrip() == "java:")
except StopIteration:
    raise SystemExit("java: 블록을 찾지 못했다 — Geyser config 형식이 바뀌었다")
end = next((i for i in range(start + 1, len(lines)) if top.match(lines[i])), len(lines))
# ★검사 범위를 java: 블록 «안»으로 한정한다. 전체 문서를 훑으면 bedrock: 의 address 에
#   걸려서 주입을 건너뛴다(2026-09-19 첫 판이 정확히 그 버그였다).
block = lines[start + 1:end]
have = {re.match(r'^\s{2}([A-Za-z0-9_-]+):', l).group(1)
        for l in block if re.match(r'^\s{2}([A-Za-z0-9_-]+):', l)}
inject = []
if "address" not in have:
    inject.append("  address: 127.0.0.1")
if "port" not in have:
    inject.append("  port: %s" % port)
if inject:
    lines[start + 1:start + 1] = ["  # standalone 전용 — 플러그인 모드에는 없던 «원격 Java 서버» 지정."] + inject
open(dst, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("config 작성:", dst, "(주입:", ", ".join(inject) or "없음", ")")
PY

# 코어 jar — 플러그인과 같은 버전을 받는다. 버전이 어긋나면 확장 api(2.11.0)가 안 맞을 수 있다.
VER=$(unzip -p "$NET/velocity/plugins/Geyser-Velocity.jar" git.properties 2>/dev/null \
        | grep -oE 'git.build.version=[^[:space:]]+' | cut -d= -f2 || true)
echo "플러그인 Geyser 버전: ${VER:-알수없음}"
if [ ! -s "$DST/Geyser-Standalone.jar" ]; then
  echo "▶ Geyser-Standalone.jar 을 받는다 (버전 고정 없이 최신 standalone — 받은 뒤 버전 대조 필수)"
  curl -fsSL -o "$DST/.Geyser-Standalone.jar.tmp" \
    "https://download.geysermc.org/v2/projects/geyser/versions/latest/builds/latest/downloads/standalone" \
    && mv -f "$DST/.Geyser-Standalone.jar.tmp" "$DST/Geyser-Standalone.jar" \
    || { echo "다운로드 실패 — 수동으로 $DST/Geyser-Standalone.jar 배치" >&2; rm -f "$DST/.Geyser-Standalone.jar.tmp"; }
fi
if [ -s "$DST/Geyser-Standalone.jar" ]; then
  SVER=$(unzip -p "$DST/Geyser-Standalone.jar" git.properties 2>/dev/null \
          | grep -oE 'git.build.version=[^[:space:]]+' | cut -d= -f2 || true)
  echo "standalone Geyser 버전: ${SVER:-알수없음}"
  [ -n "$VER" ] && [ -n "$SVER" ] && [ "$VER" != "$SVER" ] \
    && echo "⚠️ 버전이 다르다($VER vs $SVER) — 확장 호환을 반드시 확인할 것" >&2
fi

echo
echo "준비 완료: $DST"
find "$DST" -maxdepth 2 -type f | sed "s|$DST/|  |" | sort | head -30
echo
echo "다음: cutover.sh (Velocity 1회 재기동 — 이때만 전원 끊김)"
