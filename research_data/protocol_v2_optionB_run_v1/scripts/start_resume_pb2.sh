#!/bin/sh
# Owner rule (17 Nov 2026): when the owner writes "start" after a safe stop, run this. It continues P-B2 rerun 3 in the
# SAME session and output folder: finished calls replay from the ledger at $0, then new calls continue.
# Refuses unless: on AC, OpenRouter reachable, freeze revision 6 verifies, ledgers clean, P-B2 not already running.
R=/Users/ulkerhuseynova/Desktop/SAFE-Mem/research_data/protocol_v2_optionB_run_v1
cd $R || exit 1
pgrep -f "Python.app/Contents/MacOS/Python scripts/run_protocol_v2.py paid .*gpt_rerun3" >/dev/null && { echo "P-B2 is already running"; exit 1; }
[ -d gpt_rerun3 ] || { echo "gpt_rerun3 missing; this script only continues rerun 3"; exit 1; }
pmset -g batt | grep -q "AC Power" || { echo "NOT on AC power: plug in the charger first"; exit 1; }
code=$(curl -s -m 15 -o /dev/null -w "%{http_code}" https://openrouter.ai/api/v1/models)
[ "$code" = "200" ] || { echo "OpenRouter not reachable (HTTP $code): check Wi-Fi"; exit 1; }
(cd /Users/ulkerhuseynova/Desktop/SAFE-Mem && uv run python scripts/freeze_protocol_v2.py verify --protocol research_data/protocol_v2_freeze_optionB_20261115/protocol_v2_optionB_rev7.json) > logs/freeze_verify_resume.txt 2>&1 || { echo "freeze revision 7 does not verify; see logs/freeze_verify_resume.txt"; exit 1; }
sh scripts/stop_safe_pb2.sh --check || { echo "ledgers not clean: not starting"; exit 1; }
python3 -c "import sqlite3;r=sqlite3.connect('gpt_rerun3/queries.sqlite').execute('pragma quick_check').fetchone()[0];print('result journal check:',r);exit(r!='ok')" || exit 1
echo "=== resumed $(date -u +%FT%TZ) (same session; finished calls replay at \$0) ===" >> logs/PB2_rerun3.log
nohup python3 -c 'import os,sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' \
  caffeinate -ims sh scripts/paid.sh PB2 >> logs/PB2_rerun3.log 2>&1 < /dev/null &
echo $! > logs/PB2_rerun3.pid
echo "$(date -u +%FT%TZ) resumed (pgid $(cat logs/PB2_rerun3.pid))" | tee -a logs/PB2_rerun3_stops.txt
sleep 20; PY=$(pgrep -f "Python.app/Contents/MacOS/Python scripts/run_protocol_v2.py paid .*gpt_rerun3" | head -1); echo $PY > logs/PB2_rerun3_python.pid
[ -n "$PY" ] && echo "P-B2 running again (python pid $PY)" || { echo "P-B2 did not start; see logs/PB2_rerun3.log"; exit 1; }
