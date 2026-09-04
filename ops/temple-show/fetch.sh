#!/usr/bin/env bash
# 후보 해저신전 원본 내려받기. PMC 본체는 Cloudflare 로 curl 403 이지만
# 다운로드 엔드포인트가 s3.amazonaws.com/static.planetminecraft.com 으로 302 되고
# 그 오브젝트는 서명 없이도 공개라 curl 로 바로 받힌다.
set -euo pipefail
DL=${1:-dl}; mkdir -p "$DL"; cd "$DL"
B=https://s3.amazonaws.com/static.planetminecraft.com/files/resource_media/schematic
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
dl(){ [ -s "$1" ] || curl -sS -f -o "$1" "$2"; printf "%-30s %9s\n" "$1" "$(stat -f%z "$1")"; }
dl 01_emersion.schematic       "$B/1726/emersionetemplebluvetro-1498738975.schematic"
dl 02_shadow_monument.schem    "$B/oceanmonument.schem"
dl 04_jedi_temple.schem        "$B/jedi-temple.schem"
dl 05_natural_temple.schem     "$B/oceantemplenatural.schem"
dl 06_underwater_city.schem    "$B/underwater.schem"
dl 07_mini_atlantis.schem      "$B/seaproject.schem"
dl 08_kraken.schematic         "$B/1909/kraken-1551235259.schematic"
dl 09_water_monument.schematic "$B/1811/water-monument-1521052019.schematic"
dl 10_monument_redone.zip      "$B/ocean-e170.zip"
dl 11_water_palace.zip         "$B/water-palace.zip"
dl 13_ic_ocean_heartlands.zip  "$B/ic-ocean.zip"
dl 14_uw_castle_lobby.zip      "$B/underwatercastlelobby1122.zip"
# mediafire 는 다운로드 페이지에서 직링크를 긁는다(★http 스킴도 있으니 https? 로 받을 것)
mf(){ n=$1; p=$2; curl -sSL -A "$UA" "$p" -o /tmp/mf_$n.html
  l=$(grep -o 'href="https\?://download[0-9]*\.mediafire\.com[^"]*"' /tmp/mf_$n.html | head -1 | sed 's/href="//;s/"$//')
  [ -n "$l" ] || { echo "$n: 직링크 못 찾음"; return; }
  [ -s "$n" ] || curl -sS -f -L -A "$UA" -o "$n" "$l"; printf "%-30s %9s\n" "$n" "$(stat -f%z "$n")"; }
mf 16_temple_of_conduit.zip "https://www.mediafire.com/file/xorm0bd5xsemdbn/Temple_of_Conduit.zip/file"
mf 17_artazan_guardian.rar  "https://www.mediafire.com/?chj1pc41pxlnj2r"
mf 18_seatemple.zip         "http://www.mediafire.com/download/8muwdv96w7lo0qe/Seatemple.zip"
mf 19_platreon_temple.zip   "http://www.mediafire.com/download/mr43o5ctrr33aq2/Platreon-The+Time+Temple+%5BContest%5D.zip"
echo "압축 해제: zip=unzip, 17번은 RAR 이라 bsdtar -xf (macOS libarchive 가 읽는다)"
