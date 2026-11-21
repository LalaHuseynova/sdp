#!/bin/sh
# P-B2 rerun 2 (owner, 17 Nov 2026). Run only at home on a stable network:
# checks AC + OpenRouter, re-sends P-B1 into sessions_rerun2, requires all 60 replies identical
# to conflict_replies.json, then starts paid.sh PB2 detached with a 5-min resource log.
R=/Users/ulkerhuseynova/Desktop/SAFE-Mem/research_data/protocol_v2_optionB_run_v1
cd $R || exit 1
pmset -g batt | grep -q "AC Power" || { echo "NOT on AC power: plug in the charger first"; exit 1; }
code=$(curl -s -m 15 -o /dev/null -w "%{http_code}" https://openrouter.ai/api/v1/models)
[ "$code" = "200" ] || { echo "OpenRouter not reachable (HTTP $code)"; exit 1; }
[ -e gpt_rerun2 ] && { echo "gpt_rerun2 already exists; not starting"; exit 1; }
if [ ! -e conflict_replies_rerun2.json ]; then
  caffeinate -ims sh scripts/paid.sh PB1 > logs/PB1_rerun2.log 2>&1 || { echo "P-B1 failed; see logs/PB1_rerun2.log"; exit 1; }
fi
python3 - <<'EOF' || exit 1
import json, sys
a = {r["call_id"]: r for r in json.load(open("conflict_replies.json"))}
b = {r["call_id"]: r for r in json.load(open("conflict_replies_rerun2.json"))}
ok = set(a) == set(b) and all(a[k] == b[k] for k in a)
print("P-B1 replies identical to the stored ones:", ok, len(b))
sys.exit(0 if ok else 1)
EOF
date -u +%FT%TZ > logs/PB2_rerun2_started.txt
nohup python3 -c 'import os,sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' \
  caffeinate -ims sh scripts/paid.sh PB2 > logs/PB2_rerun2.log 2>&1 < /dev/null &
echo $! > logs/PB2_rerun2.pid
echo "P-B2 rerun 2 started (pgid $(cat logs/PB2_rerun2.pid))"
nohup python3 -c 'import os,sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' sh -c '
  cd '"$R"'; P=$(cat logs/PB2_rerun2.pid); sleep 30
  while kill -0 $P 2>/dev/null; do
    PY=$(pgrep -f "Python.*run_protocol_v2.py paid .*gpt_rerun2" | head -1)
    echo "$(date +%H:%M) rss=$(ps -o rss= -p $PY 2>/dev/null | awk "{printf \"%dMB\", \$1/1024}") swap=$(sysctl -n vm.swapusage | awk "{print \$6}") disk=$(df -h . | tail -1 | awk "{print \$4}") journal=$(du -m gpt_rerun2/queries.sqlite 2>/dev/null | cut -f1)MB power=$(pmset -g batt | head -1 | cut -d"'"'"'" -f2 | tr " " _)" >> logs/PB2_rerun2_resources.log
    sleep 300
  done; date -u +%FT%TZ > logs/PB2_rerun2_exited.txt' > /dev/null 2>&1 < /dev/null &
