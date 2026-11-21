#!/bin/sh
# Freeze P-B2 rerun 3 (SIGSTOP) only at a moment when no paid call is in flight
# (no 'started' row in any session's dispatch ledger), so closing the lid cannot fail a call.
# Resume with resume_pb2.sh once the network is back.
cd /Users/ulkerhuseynova/Desktop/SAFE-Mem/research_data/protocol_v2_optionB_run_v1 || exit 1
PY=$(pgrep -f "Python.app/Contents/MacOS/Python scripts/run_protocol_v2.py paid .*gpt_rerun3" | head -1)
[ -n "$PY" ] || { echo "P-B2 python not found"; exit 1; }
echo $PY > logs/PB2_rerun3_python.pid
i=0
while [ $i -lt 200 ]; do
  kill -STOP $PY; sleep 0.5
  if python3 - <<'EOF'
import sqlite3, glob, sys
try:
    n = sum(sqlite3.connect(f"file:{p}?mode=ro&immutable=1", uri=True)
            .execute("select count(*) from dispatches where status='started'").fetchone()[0]
            for p in glob.glob("sessions_rerun3/*/dispatch.sqlite"))
except Exception:
    sys.exit(1)
sys.exit(0 if n == 0 else 1)
EOF
  then
    echo "$(date -u +%FT%TZ) paused pid $PY (no call in flight; try $i)" | tee -a logs/PB2_rerun3_pauses.txt
    ps -o pid,stat -p $PY
    exit 0
  fi
  kill -CONT $PY; sleep 1; i=$((i+1))
done
echo "could not find a moment without an in-flight call; P-B2 left running"; exit 1
