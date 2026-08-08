#!/usr/bin/env bash
# 26.1 클라용 셰이더를 현재 build.zip 에서 다시 뽑아 CraftEngine 강제 덮어쓰기 폴더를 갱신한다.
#
# 왜 필요한가:
#   BetterHud 2.1.0-447 은 26.1 클라에게 SHADER_VERSION 3 셰이더를 주는데 그게 실제로는
#   1.21.6 용이라 26.1 에서 HUD가 깨진다. 그래서 1_21_6(=v2) 셰이더를 26_1 자리에 덮어쓴다.
#
# ★반드시 매번 다시 뽑을 것:
#   이 셰이더에는 HUD별 좌표표(switch (id) { case N: xGui=..; })가 통째로 구워져 있다.
#   HUD 정의를 추가/삭제하면 id 배정이 바뀌는데, 사본을 고정해두면 서버는 새 id 로 보내고
#   클라 셰이더는 옛 표를 써서 HUD가 통째로 화면 밖으로 날아간다.
#   ("[] 네모도 안 보이고 아무것도 안 나옴" = 이 증상)
#   2026-08-08 에 사본을 한 번 만들어두고 방치했다가 정확히 이 사고를 냈다.
set -euo pipefail
B=~/mcserver/plugins/BetterHud/build.zip
DST=~/mcserver/plugins/CraftEngine/betterhud-26-1-fix/betterhud_26_1/assets/minecraft/shaders/core
[ -f "$B" ] || { echo "build.zip 없음 — 서버를 먼저 기동할 것" >&2; exit 1; }
mkdir -p "$DST"; rm -f "$DST"/*
for f in rendertype_text.vsh rendertype_text.fsh text.vsh text.fsh; do
  if unzip -p "$B" "betterhud_1_21_6/assets/minecraft/shaders/core/$f" > "$DST/$f" 2>/dev/null && [ -s "$DST/$f" ]; then
    :
  else
    rm -f "$DST/$f"
  fi
done
ls "$DST" | sed "s/^/  뽑음: /"
echo -n "  현재 좌표표: "; grep -oE "switch \(id\) \{.{0,80}" "$DST/rendertype_text.vsh" || echo "(없음)"
grep -q "SHADER_VERSION 2" "$DST/rendertype_text.vsh" && echo "  ✅ SHADER_VERSION 2 확인" || { echo "  ❌ v2 아님"; exit 1; }
