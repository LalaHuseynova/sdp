#!/usr/bin/env python3
"""P-B4 first-answers check (revision 10), read-only. Usage: check_first_answers_pb4.py N
Reads the first N Gemini answers in sessions_rerun3/v2_backbone_gemini and checks the settings
work as intended: every answer non-empty, 0 reasoning tokens, at most 10% cut off at the
200-token limit, returned model = google/gemini-3.1-flash-lite, no failed call.
Exit 0 = passed, 1 = FAILED (stop and review), 2 = fewer than N answers yet (check again later)."""
import json
import sqlite3
import sys
from collections import Counter

N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
DB = "sessions_rerun3/v2_backbone_gemini/dispatch.sqlite"
try:
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = db.execute("SELECT d.status, d.result, n.body FROM dispatches d LEFT JOIN "
                      "workload_native_responses n USING(call_id) WHERE d.status != 'started' "
                      "ORDER BY d.rowid LIMIT ?", (N,)).fetchall()  # finished calls only
except sqlite3.Error as e:
    print("not readable yet:", e)
    sys.exit(2)
if len(rows) < N:
    print(f"{len(rows)}/{N} Gemini answers so far")
    sys.exit(2)
empty = reasoning = cut = failed = 0
models, providers = Counter(), Counter()
for status, result, body in rows:
    res = json.loads(result) if result else {}
    nat = json.loads(body) if body else {}
    if status != "completed" or res.get("error"):
        failed += 1
        continue
    text = ((res.get("response") or {}).get("text") or "").strip()
    empty += not text
    ch = (nat.get("choices") or [{}])[0]
    cut += ch.get("finish_reason") == "length"
    det = (nat.get("usage") or {}).get("completion_tokens_details") or {}
    reasoning += (det.get("reasoning_tokens") or 0) > 0
    models[nat.get("model")] += 1
    providers[nat.get("provider")] += 1
ok = (failed == 0 and empty == 0 and reasoning == 0 and cut <= N // 10
      and set(models) == {"google/gemini-3.1-flash-lite"})
print(json.dumps({"answers": N, "failed": failed, "empty": empty,
                  "with_reasoning_tokens": reasoning,
                  "cut_at_200_tokens": cut, "models": dict(models), "providers": dict(providers),
                  "result": "PASSED" if ok else "FAILED"}, indent=1))
sys.exit(0 if ok else 1)
