#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
GRADLE_RUNNER=${GRADLE_RUNNER:-/Users/user/development/blockship-plugin/gradlew}
JAVA25_ROOT=${JAVA25_ROOT:-}

if [ -z "$JAVA25_ROOT" ]; then
  for candidate in \
    /Library/Java/JavaVirtualMachines/jdk-25.jdk/Contents/Home \
    /Library/Java/JavaVirtualMachines/temurin-25.jdk/Contents/Home \
    /usr/lib/jvm/zulu25-ca-arm64; do
    if [ -x "$candidate/bin/java" ]; then JAVA25_ROOT="$candidate"; break; fi
  done
fi

if [ -z "$JAVA25_ROOT" ] || [ ! -x "$JAVA25_ROOT/bin/java" ]; then
  echo "Java 25 JDK가 필요합니다. JAVA25_ROOT=/path/to/jdk-25 로 지정하세요." >&2
  exit 2
fi
if [ ! -x "$GRADLE_RUNNER" ]; then
  echo "Gradle runner를 찾을 수 없습니다: $GRADLE_RUNNER" >&2
  exit 2
fi

JAVA_HOME="$JAVA25_ROOT" "$GRADLE_RUNNER" -p "$SCRIPT_DIR" clean build
echo "빌드 완료:"
find "$SCRIPT_DIR" -path '*/build/libs/*.jar' -type f -print
