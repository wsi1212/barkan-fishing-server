#!/bin/bash
# cron */5 + flock. 재개 가능. tmux 는 MC 재시작에 세션이 날아가서 못 쓴다(16:05 사고).
exec 9>/tmp/npcskins/.lock
flock -n 9 || exit 0
DIR=/tmp/npcskins
[ -f "$DIR/DONE" ] && { crontab -l 2>/dev/null | grep -v skindeploy_cron | crontab -; exit 0; }
/tmp/deploy_skins.sh
# ★DONE 조건 = «완료» 로그 + <b>업로드 수 == 대상 PNG 수</b>.
#   완료 로그만 보고 찍으면, 실행 중에 추가된 대상(도박꾼 4명·지오반니·유수프)이
#   업로드 전인데도 cron 이 해제돼 영구히 빠진다.
n_png=$(ls $DIR/*.png 2>/dev/null | wc -l | tr -d ' ')
n_up=$(wc -l < "$DIR/state.tsv" | tr -d ' ')
if grep -q "=== 완료 ===" "$DIR/deploy.log" && [ "$n_up" -ge "$n_png" ]; then
  touch "$DIR/DONE"
  echo "[$(date +%H:%M:%S)] DONE (업로드 $n_up/$n_png)" >> "$DIR/deploy.log"
else
  echo "[$(date +%H:%M:%S)] 아직 (업로드 $n_up/$n_png) — 다음 주기 계속" >> "$DIR/deploy.log"
fi
