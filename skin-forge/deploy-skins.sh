#!/bin/bash
# NPC 스킨 대량 배포 — 재개 가능. 상태: /tmp/npcskins/state.tsv (cid<TAB>hash<TAB>applied)
cd ~/mcserver
DIR=/tmp/npcskins
STATE=$DIR/state.tsv
LOG=$DIR/deploy.log
touch "$STATE"
say(){ echo "[$(date +%H:%M:%S)] $*" >> "$LOG"; }
TOTAL=$(ls $DIR/*.png 2>/dev/null | wc -l | tr -d ' ')

say "=== 시작 · 대상 ${TOTAL}개 ==="
for f in $DIR/*.png; do
  cid=$(basename "$f" .png)
  if cut -f1 "$STATE" | grep -qx "$cid"; then continue; fi
  h=""
  for try in 1 2 3; do
    r=$(curl -s -m 90 -X POST https://api.mineskin.org/generate/upload -F "file=@$f" -F "variant=classic")
    h=$(printf '%s' "$r" | python3 $DIR/parse_hash.py)
    [ -n "$h" ] && break
    say "업로드 재시도 cid=$cid (${try}차)"
    sleep 15
  done
  if [ -z "$h" ]; then say "★업로드 실패 cid=$cid"; continue; fi
  printf '%s\t%s\t0\n' "$cid" "$h" >> "$STATE"
  say "업로드 $cid → ${h:0:16}  ($(wc -l < "$STATE" | tr -d ' ')/$TOTAL)"
  sleep 8
done
say "=== 업로드 끝: $(wc -l < "$STATE" | tr -d ' ')/$TOTAL ==="

i=0
while IFS=$'\t' read -r cid h dn; do
  [ "$dn" = "1" ] && continue
  python3 scripts/rcon.py "npc skin --id $cid --url https://textures.minecraft.net/texture/$h" >/dev/null 2>&1
  i=$((i+1)); say "적용 $cid  ($i)"
  sleep 10
done < "$STATE"
python3 scripts/rcon.py "citizens save" >/dev/null 2>&1
sleep 3

for round in 1 2 3; do
  fails=$(python3 $DIR/verify.py "$STATE")
  n=$(echo $fails | wc -w | tr -d ' ')
  say "검증 ${round}회차 — 미반영 ${n}건"
  [ "$n" -eq 0 ] && break
  for cid in $fails; do
    h=$(grep -P "^$cid\t" "$STATE" | cut -f2)
    [ -z "$h" ] && continue
    python3 scripts/rcon.py "npc skin --id $cid --url https://textures.minecraft.net/texture/$h" >/dev/null 2>&1
    sleep 10
  done
  python3 scripts/rcon.py "citizens save" >/dev/null 2>&1
  sleep 3
done

python3 scripts/rcon.py "citizens reload" >/dev/null 2>&1
sleep 6
python3 scripts/rcon.py "bm reload" >/dev/null 2>&1
sleep 5
python3 scripts/rcon.py "npc모델재부착" >/dev/null 2>&1
say "=== 완료 ==="
