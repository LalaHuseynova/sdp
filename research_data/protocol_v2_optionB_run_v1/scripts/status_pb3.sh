#!/bin/sh
# Read-only status of P-B3 (Claude Haiku): process, spend per purpose, journal size, rows per group, power, disk.
cd /Users/ulkerhuseynova/Desktop/SAFE-Mem/research_data/protocol_v2_optionB_run_v1
date
kill -0 $(cat logs/PB3.pid 2>/dev/null) 2>/dev/null && echo "P-B3 Haiku: RUNNING (started $(cat logs/PB3_started.txt))" || echo "P-B3 Haiku: NOT RUNNING"
python3 - <<'PY'
import sqlite3, glob, os
tot = 0
for p in sorted(glob.glob("sessions_rerun3/*")):
    if not os.path.exists(f"{p}/budget.sqlite"): continue
    b = sqlite3.connect(f"file:{p}/budget.sqlite?mode=ro", uri=True)
    s, n = b.execute("select coalesce(sum(actual_nanodollars),0), count(*) from reservations where state='settled'").fetchone()
    pend = b.execute("select count(*) from reservations where state!='settled'").fetchone()[0]
    d = sqlite3.connect(f"file:{p}/dispatch.sqlite?mode=ro&immutable=1", uri=True)
    cap = d.execute("select cap_usd from workload_scope").fetchone()
    tot += s
    print(f"  {p.split('/')[-1]:26s} ${s/1e9:9.4f} of cap ${cap[0] if cap else '?':>6}  calls {n} (+{pend} open)")
print(f"  TOTAL spent ${tot/1e9:.4f}  (P-B2 ended at $3.2507)")
PY
du -sh haiku 2>/dev/null; grep -ciE "traceback|error" logs/PB3.log | sed 's/^/  error lines in log: /'
pmset -g batt | head -1; df -h . | tail -1 | awk '{print "  disk free: "$4}'
[ -e haiku/queries.sqlite ] || exit 0
T=$(mktemp -d); cp -c haiku/queries.sqlite "$T/q.sqlite" 2>/dev/null && { [ -e haiku/queries.sqlite-journal ] && cp -c haiku/queries.sqlite-journal "$T/q.sqlite-journal"; true; }
python3 - "$T/q.sqlite" <<'PY'
import sqlite3, collections, sys
try:
    db = sqlite3.connect(sys.argv[1])
    g = collections.Counter(r[0] for r in db.execute("select json_extract(body,'$.group_id') from outcomes"))
    print(f"  groups started: {len(g)}/24; rows: " + ", ".join(f"{k} {v}" for k, v in sorted(g.items())))
except Exception as e:
    print("  journal clone not readable:", e)
PY
rm -rf "$T"
