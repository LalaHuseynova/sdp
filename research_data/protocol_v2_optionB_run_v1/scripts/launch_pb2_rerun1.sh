#!/bin/sh
# P-B2 rerun 1 (owner, 17 Nov 2026): wait for AC power, then start paid.sh PB2 detached
# (own process group, caffeinate -ims) and log resources every 5 min until it exits.
R=/Users/ulkerhuseynova/Desktop/SAFE-Mem/research_data/protocol_v2_optionB_run_v1
cd $R || exit 1
until pmset -g batt | grep -q "AC Power"; do sleep 30; done
if [ -e gpt_rerun1 ]; then echo "gpt_rerun1 already exists; not starting" > logs/PB2_rerun1_launcher.txt; exit 1; fi
date -u +%FT%TZ > logs/PB2_rerun1_started.txt
nohup python3 -c 'import os,sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' \
  caffeinate -ims sh scripts/paid.sh PB2 > logs/PB2_rerun1.log 2>&1 < /dev/null &
P=$!
echo $P > logs/PB2_rerun1.pid
sleep 20
pgrep -f "run_protocol_v2.py paid .*gpt_rerun1" | head -1 > logs/PB2_rerun1_python.pid
while kill -0 $P 2>/dev/null; do
  PY=$(cat logs/PB2_rerun1_python.pid)
  echo "$(date +%H:%M) rss=$(ps -o rss= -p $PY 2>/dev/null | awk '{printf "%dMB", $1/1024}')" \
    "swap=$(sysctl -n vm.swapusage | awk '{print $6}')" \
    "disk=$(df -h . | tail -1 | awk '{print $4}')" \
    "journal=$(du -m gpt_rerun1/queries.sqlite 2>/dev/null | cut -f1)MB" \
    "power='$(pmset -g batt | head -1 | cut -d"'" -f2)'" >> logs/PB2_rerun1_resources.log
  sleep 300
done
date -u +%FT%TZ > logs/PB2_rerun1_exited.txt
