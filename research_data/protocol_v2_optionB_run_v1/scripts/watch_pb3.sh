#!/bin/sh
# Watcher for P-B3: every 5 min logs resources; safe-stops (stop_safe_pb3.sh) if on battery <= 30% or disk < 1.5 GB.
# Exits when P-B3 exits (prints the end of the log).
cd /Users/ulkerhuseynova/Desktop/SAFE-Mem/research_data/protocol_v2_optionB_run_v1
P=$(cat logs/PB3.pid)
while kill -0 $P 2>/dev/null; do
  PY=$(pgrep -f "Python.*run_protocol_v2.py paid .*--backbone haiku" | head -1)
  batt=$(pmset -g batt | grep -o '[0-9]*%' | tr -d %); src=$(pmset -g batt | head -1 | cut -d"'" -f2)
  freek=$(df -k . | tail -1 | awk '{print $4}')
  echo "$(date +%H:%M) rss=$(ps -o rss= -p $PY 2>/dev/null | awk '{printf "%dMB", $1/1024}') swap=$(sysctl -n vm.swapusage | awk '{print $6}') disk=$((freek/1048576))GB journal=$(du -m haiku/queries.sqlite 2>/dev/null | cut -f1)MB power=$(echo $src | tr ' ' _)_$batt%" >> logs/PB3_resources.log
  if [ "$src" = "Battery Power" ] && [ "$batt" -le 30 ]; then echo "LOW BATTERY ($batt%): safe stop"; sh scripts/stop_safe_pb3.sh; exit 0; fi
  if [ "$freek" -lt 1572864 ]; then echo "LOW DISK: safe stop"; sh scripts/stop_safe_pb3.sh; exit 0; fi
  sleep 300
done
date -u +%FT%TZ > logs/PB3_exited.txt
echo "P-B3 EXITED $(date)"; tail -25 logs/PB3.log
