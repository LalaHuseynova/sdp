#!/bin/sh
# Watcher for P-B4: every 5 min logs resources; safe-stops (stop_safe_pb4.sh) if on battery <= 30% or disk < 1.5 GB.
# Once, after the first 30 Gemini answers: check_first_answers_pb4.py (no empty answers, no reasoning tokens,
# few cut-offs, the requested model); if that check fails it safe-stops P-B4 for the owner's review.
# Exits when P-B4 exits (prints the end of the log).
cd /Users/ulkerhuseynova/Desktop/SAFE-Mem/research_data/protocol_v2_optionB_run_v1
P=$(cat logs/PB4.pid)
FIRST=0
while kill -0 $P 2>/dev/null; do
  if [ $FIRST = 0 ]; then
    python3 scripts/check_first_answers_pb4.py 30 >> logs/PB4_first_answers.txt 2>&1; rc=$?
    [ $rc = 0 ] && FIRST=1
    if [ $rc = 1 ]; then echo "FIRST-ANSWERS CHECK FAILED: safe stop for review"; sh scripts/stop_safe_pb4.sh; exit 0; fi
  fi
  PY=$(pgrep -f "Python.*run_protocol_v2.py paid .*--backbone gemini" | head -1)
  batt=$(pmset -g batt | grep -o '[0-9]*%' | tr -d %); src=$(pmset -g batt | head -1 | cut -d"'" -f2)
  freek=$(df -k . | tail -1 | awk '{print $4}')
  echo "$(date +%H:%M) rss=$(ps -o rss= -p $PY 2>/dev/null | awk '{printf "%dMB", $1/1024}') swap=$(sysctl -n vm.swapusage | awk '{print $6}') disk=$((freek/1048576))GB journal=$(du -m gemini/queries.sqlite 2>/dev/null | cut -f1)MB power=$(echo $src | tr ' ' _)_$batt%" >> logs/PB4_resources.log
  if [ "$src" = "Battery Power" ] && [ "$batt" -le 30 ]; then echo "LOW BATTERY ($batt%): safe stop"; sh scripts/stop_safe_pb4.sh; exit 0; fi
  if [ "$freek" -lt 1572864 ]; then echo "LOW DISK: safe stop"; sh scripts/stop_safe_pb4.sh; exit 0; fi
  [ $FIRST = 0 ] && sleep 60 || sleep 300
done
date -u +%FT%TZ > logs/PB4_exited.txt
echo "P-B4 EXITED $(date)"; tail -25 logs/PB4.log
