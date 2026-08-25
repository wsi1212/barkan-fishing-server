#!/usr/bin/env bash
# BarkanWorldWarp 빌드 — gradle 없이 javac 한 번으로 끝나는 미니 플러그인이다.
# 산출: /tmp/BarkanWorldWarp.jar
#
# ★paper-api 는 BlockShip 이 이미 받아 둔 gradle 캐시 것을 빌려 쓴다. 런타임(Paper 1.21.11)과
#   같은 버전이어야 한다 — 체스가 1.21.4 로 빌드하다 Material.CHAIN 을 그대로 내보낸 전례가 있다.
set -euo pipefail
cd "$(dirname "$0")"
JH=$(/usr/libexec/java_home -v 21)
OUT=/tmp/worldwarp-build
JAR=/tmp/BarkanWorldWarp.jar

CP=""
for pat in "paper-api-1.21.11*.jar" "adventure-api-*.jar" "adventure-key-*.jar" "examination-api-*.jar" "bungeecord-chat-*.jar" "annotations-*.jar"; do
  for j in $(find ~/.gradle/caches/modules-2 -name "$pat" 2>/dev/null | grep -vE 'sources|javadoc' | head -1); do
    CP="$CP:$j"
  done
done
[ -n "$CP" ] || { echo "❌ paper-api 를 gradle 캐시에서 못 찾음" >&2; exit 1; }

rm -rf "$OUT"; mkdir -p "$OUT/com/barkan/worldwarp"
"$JH/bin/javac" -nowarn -cp "${CP#:}" -d "$OUT" WorldWarp.java
cp plugin.yml config.yml "$OUT/"
rm -f "$JAR"
(cd "$OUT" && "$JH/bin/jar" cf "$JAR" .)
echo "✅ $JAR"
unzip -l "$JAR" | grep -E '\.class|\.yml' | awk '{print "   "$4}'
