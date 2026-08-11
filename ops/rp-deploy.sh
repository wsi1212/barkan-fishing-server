#!/usr/bin/env bash
# 메인 리소스팩 배포 — ★진입점은 이 파일 하나다.
#
# 이미지 하나 추가하는 절차는 이게 전부다:
#   1) ~/development/barkan-resourcepack/ 에 파일을 넣는다 (필요하면 font/gui.json 등록)
#   2) ops/rp-deploy.sh prod
#   3) 안내대로 재시작 (또는 06:00 유지보수에 태운다)
# 마인크래프트를 켜서 눈으로 확인할 필요 없다 — 아래 검증이 대신한다.
#
# ## 왜 이 파일이 생겼나 (2026-08-11)
# 배포 경로가 다섯 갈래여서 세션마다 다른 걸 골랐고, 그때마다 사고가 났다. 특히 이날
# 다른 세션이 소스가 아닌 낡은 스냅샷을 zip 해서 올려 **gui 텍스처 761개와 글리프
# provider 228개가 빠진 팩**이 prod 에 올라갔다(메뉴 이미지 전멸 + pack.mcmeta 의
# min_format 소실로 26.1+ 클라는 overlays 까지 무시). 아래 "회귀 가드"가 그걸 잡는다.
#
# ## 이 스크립트가 지키는 원칙
#  * 대상을 하드코딩하지 않는다 — server.properties 의 resource-pack URL 이 권위다.
#  * 팩은 매번 build-prod-rp.py 로 새로 굽는다 (사본을 고정하지 않는다).
#  * 업로드는 항상 **새 태그**로 한다. `--clobber` 를 쓰지 않으므로 CDN 이 옛 바이트를
#    돌려주는 사고가 원천적으로 없고, 구 URL 이 살아있어 재시작 전까지 접속이 안 깨진다.
#  * ★공개 URL 을 다시 내려받아 sha1 이 일치할 때만 server.properties 를 건드린다.
#  * ★릴리스 태그 `latest` 는 절대 건드리지 않는다 — prod CraftEngine 가구팩
#    (barkan-furniture.zip)이 그 태그에 얹혀 있다. 이 스크립트는 새 태그만 만든다.
#
# ## 범위 밖 (다른 도구를 쓸 것)
#  * CraftEngine 가구팩(barkan-furniture.zip) → CE `reload all` + config sha1 갱신 절차
#  * BetterHud HUD 정의 변경 → ops/prod/betterhud/deploy-prod.sh
#    (BetterHud 에셋은 메인팩이 아니라 CE 팩을 타고 간다)
#
# 사용:
#   ops/rp-deploy.sh <dev|prod> [--restart] [--dry-run]
#     --dry-run : 굽고 검증만 한다. 업로드·설정변경·재시작 없음.
#     --restart : 검증 통과 후 재시작까지 한다(생략하면 안내만 — 재시작해야 클라가 받는다).

set -euo pipefail

REPO="wsi1212/minecraft-fish-resource-pack"
KEY="$HOME/.ssh/oracle-mc.key"
PROD_HOST="ubuntu@168.107.8.107"
DEV_PROPS="$HOME/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/server.properties"
BUILD="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/build-prod-rp.py"
ZIP="/tmp/barkan-resourcepack-slim.zip"
ASSET="barkan-resourcepack.zip"          # ★자산 이름은 고정 (URL 이 이 이름을 찾는다)
# 파일 수가 이 비율보다 줄면 중단. 정상적인 정리(백업 제외 등)는 몇십 개 수준이다.
MIN_KEEP_RATIO="0.97"

TARGET="${1:-}"; shift || true
DRY=0; RESTART=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --restart) RESTART=1 ;;
    *) echo "알 수 없는 인자: $a" >&2; exit 2 ;;
  esac
done
case "$TARGET" in
  dev|prod) ;;
  *) echo "사용: $0 <dev|prod> [--restart] [--dry-run]" >&2; exit 2 ;;
esac

# 동시 실행 금지 — 병렬 세션이 서로의 URL 을 덮어쓰는 사고가 실제로 있었다.
# macOS 에 flock 이 없어서 mkdir(원자적)로 잠근다. 죽은 락은 PID 로 판별해 걷어낸다.
LOCK="/tmp/rp-deploy-$TARGET.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  OLD=$(cat "$LOCK/pid" 2>/dev/null || echo "")
  if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then
    echo "❌ 다른 rp-deploy($TARGET) 가 돌고 있다 (pid $OLD). 끝나고 다시." >&2; exit 1
  fi
  echo "⚠️ 죽은 락을 걷어낸다 (${OLD:-pid 미기록})" >&2
  rm -rf "$LOCK"; mkdir "$LOCK"
fi
echo "$$" > "$LOCK/pid"
# ★정리는 이 함수 하나로 모은다. 뒤에서 trap 을 다시 걸면 락이 안 풀린다.
TMPS=()
cleanup() { rm -rf "$LOCK"; [ ${#TMPS[@]} -gt 0 ] && rm -rf "${TMPS[@]}" || true; }
trap cleanup EXIT

say() { printf '\n▶ %s\n' "$1"; }

# ── 현재 배포 상태를 읽는다 (하드코딩 금지) ────────────────────────────────
read_props() {                     # $1=key → 값
  if [ "$TARGET" = prod ]; then
    ssh -i "$KEY" -o ConnectTimeout=12 "$PROD_HOST" \
      "sed -n 's/^$1=//p' ~/mcserver/server.properties | head -n1"
  else
    sed -n "s/^$1=//p" "$DEV_PROPS" | head -n1
  fi
}
CUR_URL=$(read_props resource-pack | sed 's|\\:|:|g')
CUR_SHA=$(read_props resource-pack-sha1)
say "현재 $TARGET 배포 상태"
echo "   URL : ${CUR_URL:-(없음)}"
echo "   sha1: ${CUR_SHA:-(없음)}"

case "$CUR_URL" in
  https://github.com/*) MODE=github ;;
  https://barkan.kro.kr/*)
    cat >&2 <<EOF
❌ 이 대상은 Caddy 자체 호스팅을 쓰고 있다 — 이 스크립트는 GitHub 릴리스 경로만 검증했다.
   Caddy 로 올릴 때의 순서(구 URL 을 살려둔 무중단 방식):
     1) 새 파일명으로 업로드:  scp $ZIP $PROD_HOST:/tmp/ && ssh … sudo cp /tmp/$(basename $ZIP) /var/www/barkan/barkan-resourcepack-<날짜시각>.zip
     2) server.properties 의 resource-pack URL·sha1 을 그 새 파일로
     3) ~/mcserver/scripts/resourcepack-guard.sh --check
     4) 재시작
   ※ Caddy 는 /barkan-resourcepack*.zip 글롭으로 열려 있으니 새 파일명이 그대로 서빙된다.
EOF
    exit 1 ;;
  *) echo "❌ 알 수 없는 배포 경로: $CUR_URL" >&2; exit 1 ;;
esac

# ── 1. 매번 새로 굽는다 ───────────────────────────────────────────────────
say "팩 빌드 (build-prod-rp.py — 백업 제외 + 아이템 128px 상한 + PNG 재압축)"
python3 "$BUILD"
[ -s "$ZIP" ] || { echo "❌ 빌드 산출물이 없다: $ZIP" >&2; exit 1; }
NEW_SHA=$(shasum "$ZIP" | awk '{print $1}')
echo "   $(wc -c < "$ZIP")b · sha1 $NEW_SHA"

# ── 2. 팩 자체 건강검진 ───────────────────────────────────────────────────
say "팩 자체 검증"
python3 - "$ZIP" <<'PY'
import json, sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
names = [n for n in z.namelist() if not n.endswith('/')]
assert z.testzip() is None, "zip 손상"

# 26.1+ 클라는 supported_formats 상한이 64를 넘으면 min/max_format 을 의무로 요구한다.
# 없으면 팩은 fallback 으로 읽히지만 overlays 가 조용히 무시된다 — 증상이 "일부만 안 나옴"
# 이라 원인을 찾기 어렵다. 그래서 여기서 막는다.
mc = json.loads(z.read('pack.mcmeta'))['pack']
assert 'min_format' in mc and 'max_format' in mc, \
    "pack.mcmeta 에 min_format/max_format 이 없다 — 26.1+ 클라가 overlays 를 무시한다"

gui = json.loads(z.read('assets/barkan/font/gui.json')).get('providers', [])
assert len(gui) > 200, f"font/gui.json provider 가 {len(gui)}개뿐 — 글리프 정의가 빠졌다"

# 글리프가 가리키는 텍스처가 실제로 들어있는지 (정의는 있는데 그림이 없으면 []네모가 뜬다)
have = set(names)
missing = []
for e in gui:
    f = e.get('file')
    if not f:
        continue
    ns, _, path = f.partition(':')
    if not path:
        ns, path = 'minecraft', ns
    p = f"assets/{ns}/textures/{path}"
    if p not in have:
        missing.append(p)
assert not missing, f"글리프 텍스처 {len(missing)}개 누락: {missing[:5]}"

junk = [n for n in names if any(j in n for j in ('.bak', '_prepad', 'backup', 'pf_reference', 'tools/'))]
assert not junk, f"잡동사니가 실렸다: {junk[:5]}"

# 사운드는 경고만 — 없는 sounds.json 항목은 조용히 안 울릴 뿐 팩을 깨뜨리지 않는다.
# (2026-08-11 기준 weather 6종이 등록만 되고 파일이 없다. 오래된 상태이지 이번 배포의 문제 아님)
snd = json.loads(z.read('assets/barkan/sounds.json'))
bad = []
for k, v in snd.items():
    for s in v.get('sounds', []):
        nm = s['name'] if isinstance(s, dict) else s
        ns, _, path = nm.partition(':')
        if not path:
            ns, path = 'minecraft', ns
        if ns != 'minecraft' and f"assets/{ns}/sounds/{path}.ogg" not in have:
            bad.append(k)

print(f"   ✅ 항목 {len(names)} · glyph provider {len(gui)} · sounds {len(snd)}키 · 잡동사니 0")
if bad:
    print(f"   ⚠️ 파일 없는 사운드 {len(bad)}개 (안 울림, 배포는 계속): {sorted(set(bad))}")
PY

# ── 3. ★회귀 가드 — 지금 서빙 중인 팩보다 내용이 줄면 중단 ────────────────
say "회귀 가드 (현재 서빙본과 대조)"
CUR_LIST=$(mktemp); NEW_LIST=$(mktemp); CUR_ZIP=$(mktemp /tmp/rp-current.XXXXXX.zip)
TMPS+=("$CUR_LIST" "$NEW_LIST" "$CUR_ZIP")
if curl --fail --location --silent --show-error --retry 2 --retry-delay 2 \
       --connect-timeout 15 --max-time 300 "$CUR_URL" --output "$CUR_ZIP"; then
  unzip -Z1 "$CUR_ZIP" | grep -v '/$' | sort > "$CUR_LIST"
  unzip -Z1 "$ZIP"     | grep -v '/$' | sort > "$NEW_LIST"
  CUR_N=$(wc -l < "$CUR_LIST"); NEW_N=$(wc -l < "$NEW_LIST")
  LOST=$(comm -23 "$CUR_LIST" "$NEW_LIST" | grep -vE '\.bak|_prepad|backup|pf_reference|^tools/' || true)
  LOST_N=$(printf '%s' "$LOST" | grep -c . || true)
  echo "   현재 $CUR_N개 → 신규 $NEW_N개 · 잡동사니 제외 순손실 ${LOST_N}개"
  if [ "$LOST_N" -gt 0 ]; then
    printf '%s\n' "$LOST" | head -20 | sed 's/^/     - /'
    [ "$LOST_N" -gt 20 ] && echo "     … 외 $((LOST_N - 20))개"
  fi
  if ! python3 -c "import sys; sys.exit(0 if $NEW_N >= $CUR_N * $MIN_KEEP_RATIO else 1)"; then
    echo "❌ 파일 수가 ${MIN_KEEP_RATIO} 배 미만으로 줄었다 — 낡은 스냅샷을 굽고 있을 가능성이 크다. 중단." >&2
    echo "   (의도한 대량 삭제라면 MIN_KEEP_RATIO 를 낮춰 다시 실행)" >&2
    rm -f "$CUR_ZIP"; exit 1
  fi
  rm -f "$CUR_ZIP"
else
  echo "   ⚠️ 현재 서빙본을 못 받았다 — 대조를 건너뛴다 (첫 배포이거나 URL 이 죽은 상태)"
  rm -f "$CUR_ZIP"
fi

if [ "$DRY" = 1 ]; then
  say "--dry-run — 여기서 멈춘다. 업로드·설정변경·재시작 없음."
  echo "   산출물: $ZIP (sha1 $NEW_SHA)"
  exit 0
fi

# ── 4. 새 태그로 업로드 (clobber 안 씀 → CDN 옛 바이트 문제 없음) ──────────
TAG="pack-$(date +%Y%m%d-%H%M%S)"
say "업로드 — 새 태그 $TAG (★latest 태그는 건드리지 않는다)"
UP=$(mktemp -d)/"$ASSET"; cp "$ZIP" "$UP"     # 자산 이름을 고정하기 위해 사본 경로로
gh release create "$TAG" --repo "$REPO" --title "Resource Pack $TAG" --notes "ops/rp-deploy.sh $TARGET" >/dev/null
gh release upload "$TAG" "$UP" --repo "$REPO" >/dev/null
NEW_URL="https://github.com/$REPO/releases/download/$TAG/$ASSET"
echo "   $NEW_URL"

# ── 5. ★공개 URL 이 정확히 이 바이트를 주는지 확인한 뒤에만 설정을 건드린다 ─
say "공개 URL 반영 대기·검증"
ok=0
for i in $(seq 1 30); do
  V=$(mktemp /tmp/rp-verify.XXXXXX.zip)
  if curl --fail --location --silent --show-error --connect-timeout 15 --max-time 300 \
         "$NEW_URL" --output "$V"; then
    LIVE=$(shasum "$V" | awk '{print $1}')
    if [ "$LIVE" = "$NEW_SHA" ]; then rm -f "$V"; ok=1; break; fi
    echo "   아직 다른 바이트 ($LIVE, $i/30)"
  else
    echo "   아직 못 받음 ($i/30)"
  fi
  rm -f "$V"; sleep 3
done
[ "$ok" = 1 ] || { echo "❌ 공개 URL 이 새 팩 바이트를 안 준다 — 설정을 건드리지 않고 중단." >&2
                   echo "   현재 서빙 URL 은 그대로라 접속은 안 깨진 상태다." >&2; exit 1; }
echo "   ✅ 일치 $NEW_SHA"

# ── 6. server.properties 갱신 (URL + sha1 을 원자적으로) ──────────────────
say "$TARGET server.properties 갱신"
WRITE_PY='
import io, os, sys
props, url, sha = sys.argv[1:4]
esc = url.replace(":", "\\:", 1)          # properties 규약: 스킴 콜론을 이스케이프
out, seen_u, seen_s = [], False, False
for line in io.open(props, encoding="utf-8"):
    if line.startswith("resource-pack="):
        out.append("resource-pack=" + esc + "\n"); seen_u = True
    elif line.startswith("resource-pack-sha1="):
        out.append("resource-pack-sha1=" + sha + "\n"); seen_s = True
    else:
        out.append(line)
assert seen_u and seen_s, "resource-pack / resource-pack-sha1 항목을 못 찾았다"
tmp = props + ".tmp"
io.open(tmp, "w", encoding="utf-8").write("".join(out))
os.replace(tmp, props)
print("  갱신 완료")
'
if [ "$TARGET" = prod ]; then
  ssh -i "$KEY" -o ConnectTimeout=12 "$PROD_HOST" \
    "python3 - ~/mcserver/server.properties '$NEW_URL' '$NEW_SHA' <<'PY'
$WRITE_PY
PY"
  say "기동 전 가드"
  ssh -i "$KEY" -o ConnectTimeout=12 "$PROD_HOST" '~/mcserver/scripts/resourcepack-guard.sh --check'
else
  python3 - "$DEV_PROPS" "$NEW_URL" "$NEW_SHA" <<PY
$WRITE_PY
PY
fi

# ── 7. 재시작 (sha1·URL 은 기동 때만 읽힌다) ──────────────────────────────
if [ "$RESTART" = 1 ]; then
  say "재시작"
  if [ "$TARGET" = prod ]; then
    ssh -i "$KEY" -o ConnectTimeout=12 "$PROD_HOST" 'sudo systemctl restart mcserver'
  else
    "$HOME/dev-mc.sh" restart
  fi
  echo "✅ 배포+재시작 완료 — $TAG"
else
  cat <<EOF

✅ 팩 업로드·검증·설정 갱신까지 끝났다 — $TAG
⏸  ★재시작해야 클라가 새 팩을 받는다. 구 URL 은 살아있으니 그때까지 접속은 안 깨진다.
     prod: ssh -i ~/.ssh/oracle-mc.key $PROD_HOST 'sudo systemctl restart mcserver'
           (또는 06:00 데일리 유지보수에 태운다 — jar 배포와 묶으면 재시작 한 번)
     dev : ~/dev-mc.sh restart
EOF
fi
