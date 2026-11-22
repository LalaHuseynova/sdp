#!/bin/sh
# Guard for the final analysis (owner, 22 Nov 2026): on battery <= 10% PAUSE it (SIGSTOP: no CPU, memory kept;
# survives the Mac's low-battery hibernation, hibernatemode 3); on AC again RESUME it (SIGCONT) where it paused.
# Disk < 0.7 GB: pause too and report (plugging in does not free disk). Exits when the analysis exits.
cd /Users/ulkerhuseynova/Desktop/SAFE-Mem/research_data/protocol_v2_optionB_run_v1
PY=$(pgrep -f "Python.*analyse_protocol_v2.py --journal" | head -1); [ -n "$PY" ] || { echo "analysis not running"; exit 1; }
paused=0; last=""
while kill -0 $PY 2>/dev/null; do
  src=$(pmset -g batt | head -1 | cut -d"'" -f2); b=$(pmset -g batt | grep -o '[0-9]*%' | head -1 | tr -d %)
  fk=$(df -k . | tail -1 | awk '{print $4}')
  echo "$(date +%H:%M) power=$(echo $src | tr ' ' _) $b% disk=$((fk/1048576))GB swap=$(sysctl -n vm.swapusage | awk '{print $6}') paused=$paused" >> logs/analysis_final_resources.log
  [ "$src" != "$last" ] && { echo "POWER: $src ($b%) at $(date +%H:%M)"; last=$src; }
  if [ $paused = 0 ] && { { [ "$src" = "Battery Power" ] && [ "$b" -le 10 ]; } || [ "$fk" -lt 734003 ]; }; then
    kill -STOP $PY; paused=1
    echo "$(date -u +%FT%TZ) PAUSED analysis (battery $b%, disk $((fk/1024))MB)" | tee -a logs/analysis_final_pauses.txt
  elif [ $paused = 1 ] && [ "$src" = "AC Power" ] && [ "$fk" -ge 734003 ]; then
    kill -CONT $PY; paused=0
    echo "$(date -u +%FT%TZ) RESUMED analysis (AC, $b%)" | tee -a logs/analysis_final_pauses.txt
  fi
  sleep 60
done
echo "analysis process ended $(date +%H:%M)"
