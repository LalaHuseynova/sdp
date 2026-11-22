#!/bin/sh
# Owner rule (17 Nov 2026): when the owner writes "stop", run this. It stops P-B3 (Claude Haiku) ONLY when it is safe:
#  1) freeze at a moment with no paid call in flight, 2) check every ledger is clean (all calls completed and
#  settled, nothing held, no session blocked), 3) only then end the process and check the result journal.
# If anything is not clean, it un-freezes and leaves P-B3 running. Continue later with start_pb3.sh.
# Use --check to run step 2 only (nothing is paused or stopped).
cd /Users/ulkerhuseynova/Desktop/SAFE-Mem/research_data/protocol_v2_optionB_run_v1 || exit 1
clean() { python3 - "$1" <<'PY'
import sqlite3, glob, sys
ok = True
for p in sorted(glob.glob("sessions_rerun3/*")):
    import os
    if not os.path.exists(f"{p}/budget.sqlite"): continue
    d = sqlite3.connect(f"file:{p}/dispatch.sqlite?mode=ro&immutable=1", uri=True)
    bad = d.execute("select count(*) from dispatches where status!='completed'").fetchone()[0]
    b = sqlite3.connect(f"file:{p}/budget.sqlite?mode=ro", uri=True)
    open_ = b.execute("select count(*) from reservations where state!='settled'").fetchone()[0]
    blocked, reason, held = b.execute("select blocked, blocked_reason, held_nanodollars from budget_config").fetchone()
    good = bad == 0 and open_ == 0 and blocked == 0 and int(held) == 0
    ok &= good
    if sys.argv[1] == "show" or not good:
        print(f"  {p.split('/')[-1]:26s} not-completed={bad} open-reservations={open_} blocked={blocked} {reason} held={held} -> {'OK' if good else 'NOT CLEAN'}")
sys.exit(0 if ok else 1)
PY
}
if [ "${1:-}" = "--check" ]; then clean show && echo "ledgers clean (check only; nothing stopped)"; exit $?; fi
PY=$(pgrep -f "Python.app/Contents/MacOS/Python scripts/run_protocol_v2.py paid .*--backbone haiku" | head -1)
[ -n "$PY" ] || { echo "P-B3 is not running; nothing to stop"; clean show; exit 0; }
trap 'kill -CONT $PY 2>/dev/null; echo "interrupted: P-B3 left running"; exit 1' INT TERM HUP
i=0
while [ $i -lt 200 ]; do
  kill -STOP $PY; sleep 0.5
  if clean quiet >/dev/null 2>&1 && clean show; then
    kill -KILL $PY; sleep 2
    pkill -f "sh scripts/paid.sh PB3" 2>/dev/null; pkill -f "caffeinate -ims sh scripts/paid.sh PB3" 2>/dev/null
    trap - INT TERM HUP
    [ -e haiku/queries.sqlite ] && python3 -c "import sqlite3;print('  result journal check:', sqlite3.connect('haiku/queries.sqlite').execute('pragma quick_check').fetchone()[0])"
    echo "$(date -u +%FT%TZ) stopped safely (pid $PY, try $i; ledgers clean)" | tee -a logs/PB3_stops.txt
    sh scripts/status_pb3.sh | sed -n '2,$p'
    echo "SAFE TO SHUT DOWN. Continue later with: sh scripts/start_pb3.sh"
    exit 0
  fi
  kill -CONT $PY; sleep 1; i=$((i+1))
done
trap - INT TERM HUP
echo "NOT STOPPED: no clean moment found; P-B3 left running"; clean show; exit 1
