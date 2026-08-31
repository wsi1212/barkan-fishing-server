#!/bin/bash
# ★폐지된 진입점. 리소스팩 배포는 ops/rp-deploy.sh 하나다.
#   옛 ~/deploy-rp.sh 는 검증 없는 생 zip 이었고, 2026-08-11 에 낡은 스냅샷을 구워
#   gui 텍스처 761개·글리프 provider 228개가 빠진 팩을 prod 에 올렸다(메뉴 이미지 전멸).
#   그 사고 때문에 회귀 가드 20종이 들어간 ops/rp-deploy.sh 가 만들어졌다.
R="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Skript/scripts/ops/rp-deploy.sh"
echo "⛔ ~/deploy-rp.sh 는 폐지됐습니다 (검증 없는 생 zip — 2026-08-11 prod 사고)." >&2
echo "   대신:  ops/rp-deploy.sh <dev|prod> [--restart] [--dry-run]" >&2
echo "   실체:  $R" >&2
exit 2
