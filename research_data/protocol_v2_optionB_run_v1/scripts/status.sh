#!/bin/sh
# Read-only status (rerun 3 since 17 Nov; halted first run: sessions/, gpt/ — $0.9486 + $0.0193 held) of the option-B paid run: process, spend per purpose (settled + pending), journal size, power.
cd /Users/ulkerhuseynova/Desktop/SAFE-Mem/research_data/protocol_v2_optionB_run_v1
date
kill -0 $(cat logs/PB2_rerun3.pid) 2>/dev/null && echo "P-B2 rerun3: RUNNING (started $(cat logs/PB2_rerun3_started.txt))" || echo "P-B2 rerun3: NOT RUNNING (launcher waits for AC if not started)"
python3 - <<'PY'
import sqlite3, glob
tot = 0
for p in sorted(glob.glob("sessions_rerun3/*")):
    b = sqlite3.connect(f"file:{p}/budget.sqlite?mode=ro", uri=True)
    s, n = b.execute("select coalesce(sum(actual_nanodollars),0), count(*) from reservations where state='settled'").fetchone()
    pend = b.execute("select count(*) from reservations where state!='settled'").fetchone()[0]
    d = sqlite3.connect(f"file:{p}/dispatch.sqlite?mode=ro&immutable=1", uri=True)
    cap = d.execute("select cap_usd from workload_scope").fetchone()
    tot += s
    print(f"  {p.split('/')[-1]:26s} ${s/1e9:9.4f} of cap ${cap[0] if cap else '?':>6}  calls {n} (+{pend} open)")
print(f"  TOTAL spent ${tot/1e9:.4f}")
PY
du -sh gpt_rerun3 2>/dev/null; grep -ciE "traceback|error" logs/PB2_rerun3.log | sed 's/^/  error lines in log: /'
pmset -g batt | head -1; df -h . | tail -1 | awk '{print "  disk free: "$4}'
# Count rows on an instant APFS clone (copy-on-write: no extra disk, no lock on the live file).
# A direct immutable=1 scan can read torn pages while the writer inserts ("malformed"); the clone cannot.
T=$(mktemp -d); cp -c gpt_rerun3/queries.sqlite "$T/q.sqlite" 2>/dev/null && { [ -e gpt_rerun3/queries.sqlite-journal ] && cp -c gpt_rerun3/queries.sqlite-journal "$T/q.sqlite-journal"; true; }
python3 - "$T/q.sqlite" <<'PY'
import sqlite3, collections, sys
try:
    db = sqlite3.connect(sys.argv[1])
    g = collections.Counter(r[0] for r in db.execute("select json_extract(body,'$.group_id') from outcomes"))
    done = sum(1 for v in g.values() if v == 152320)
    print(f"  groups complete: {done}/24 (152,320 rows each); in progress: " + ", ".join(f"{k} {v}" for k, v in sorted(g.items()) if v != 152320))
except Exception as e:
    print("  journal clone not readable:", e)
PY
rm -rf "$T"
