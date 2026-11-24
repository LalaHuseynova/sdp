#!/bin/sh
# P-B4 Gemini 3.1 Flash-Lite, post-hoc third backbone (revision 10; revision 11 = 429 retry + pacing). Needs the
# OWNER-APPROVED owner_approval_optionB_rev11.json; without it the paid gate refuses before any call. The halted
# 429 attempt must be reviewed first (review_unknown_rev7.py), else the ledger check below refuses.
# First start AND resume after a safe stop (same sessions_rerun3, same gemini/ folder; finished calls replay at $0).
# Refuses unless: on AC, OpenRouter reachable, rev11 freeze verifies, locked archive verifies, snapshot = changed 0 /
# missing 25, ledgers clean, >= 3 GB disk free, P-B4 not already running, P-B2 not running.
R=/Users/ulkerhuseynova/Desktop/SAFE-Mem/research_data/protocol_v2_optionB_run_v1
cd $R || exit 1
pgrep -f "Python.*run_protocol_v2.py paid .*--backbone gemini" >/dev/null && { echo "P-B4 is already running"; exit 1; }
pgrep -f "Python.*run_protocol_v2.py paid .*gpt_rerun3" >/dev/null && { echo "P-B2 is running; not starting P-B4"; exit 1; }
pgrep -f "Python.*run_protocol_v2.py paid .*--backbone haiku" >/dev/null && { echo "P-B3 is running; not starting P-B4"; exit 1; }
A=/Users/ulkerhuseynova/Desktop/SAFE-Mem/research_data/protocol_v2_freeze_optionB_20261115/owner_approval_optionB_rev11.json
[ -f $A ] || { echo "No owner approval for P-B4 yet ($A): not starting"; exit 1; }
pmset -g batt | grep -q "AC Power" || { echo "NOT on AC power: plug in the charger first"; exit 1; }
free=$(df -g . | tail -1 | awk '{print $4}'); [ "$free" -ge 3 ] || { echo "only ${free} GB disk free (need 3)"; exit 1; }
code=$(curl -s -m 15 -o /dev/null -w "%{http_code}" https://openrouter.ai/api/v1/models)
[ "$code" = "200" ] || { echo "OpenRouter not reachable (HTTP $code): check Wi-Fi"; exit 1; }
I=logs/integrity_before_PB4.txt; [ -d gemini ] && I=logs/integrity_resume_PB4.txt
( cd /Users/ulkerhuseynova/Desktop/SAFE-Mem && date -u && \
  uv run python scripts/freeze_protocol_v2.py verify --protocol research_data/protocol_v2_freeze_optionB_20261115/protocol_v2_optionB_rev11.json && \
  uv run python scripts/archive_locked_protocol.py verify --protocol research_data/workload_freeze_v4_20261108/locked_protocol_v1.json ; \
  uv run python scripts/archive_snapshot.py verify --out research_data/archive_pre_protocol_v2_20261113 ) > $I 2>&1
python3 - $I <<'PY' || { echo "integrity checks failed; see $I"; exit 1; }
import json, re, sys
t, objs, dec = open(sys.argv[1]).read(), [], json.JSONDecoder()
i = t.find("{")
while i != -1:
    o, j = dec.raw_decode(t, i); objs.append(o); i = t.find("{", j)
ok = (len(objs) == 3 and objs[0]["status"] == "verified" and objs[0]["files"] == 321
      and objs[1]["status"] == "verified" and objs[1]["files"] == 224
      and objs[2].get("changed") == 0 and objs[2].get("missing") == 25)
print("integrity: freeze 321 verified, locked 224 verified, snapshot changed 0 missing 25 ->", "OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
PY
sh scripts/stop_safe_pb4.sh --check || { echo "ledgers not clean: not starting"; exit 1; }
if [ -d gemini ]; then
  python3 -c "import sqlite3;r=sqlite3.connect('gemini/queries.sqlite').execute('pragma quick_check').fetchone()[0];print('result journal check:',r);exit(r!='ok')" || exit 1
  echo "=== resumed $(date -u +%FT%TZ) (same session; finished calls replay at \$0) ===" >> logs/PB4.log
else
  date -u +%FT%TZ > logs/PB4_started.txt
fi
nohup python3 -c 'import os,sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' \
  caffeinate -ims sh scripts/paid.sh PB4 >> logs/PB4.log 2>&1 < /dev/null &
echo $! > logs/PB4.pid
echo "$(date -u +%FT%TZ) started (pgid $(cat logs/PB4.pid))" | tee -a logs/PB4_stops.txt
sleep 20; PY=$(pgrep -f "Python.*run_protocol_v2.py paid .*--backbone gemini" | head -1); echo $PY > logs/PB4_python.pid
[ -n "$PY" ] && echo "P-B4 running (python pid $PY)" || { echo "P-B4 did not start; see logs/PB4.log"; tail -20 logs/PB4.log; exit 1; }
