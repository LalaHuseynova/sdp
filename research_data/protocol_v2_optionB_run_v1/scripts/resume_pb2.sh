#!/bin/sh
# Unfreeze P-B2 rerun 3 (SIGCONT), but only once OpenRouter is reachable (no paid call; public endpoint).
cd /Users/ulkerhuseynova/Desktop/SAFE-Mem/research_data/protocol_v2_optionB_run_v1 || exit 1
PY=$(cat logs/PB2_rerun3_python.pid)
code=$(curl -s -m 15 -o /dev/null -w "%{http_code}" https://openrouter.ai/api/v1/models)
[ "$code" = "200" ] || { echo "OpenRouter not reachable (HTTP $code): connect to Wi-Fi first; P-B2 stays paused"; exit 1; }
kill -CONT $PY && echo "$(date -u +%FT%TZ) resumed pid $PY" | tee -a logs/PB2_rerun3_pauses.txt
ps -o pid,stat,pcpu -p $PY
pmset -g batt | head -1
