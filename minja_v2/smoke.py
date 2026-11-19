"""Offline end-to-end check of the whole pipeline with the mock agent (no API call).

Small counts (allowed in mock mode only), one pair of demo patients, every stage through
the real MINJA main.py, the patched seam, the adapter and the scorer, on both written
memories (rev 3: MINJA's attack memory and the mixed-history memory) and every condition.
Rows that need a main-environment LLM worker (MemLineage, LLM sanitiser) are skipped: the
mock cannot reach that process. Not evidence about any method; a plumbing test.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from . import protocol as P
from .gorule import evaluate
from .runner import Runner

# rev 3: the protocol's 15 attack queries (45 attacker records) so that every condition has
# redirected records in each session and Sybil forms its real 1 / 5 / 15 identities; small
# benign, history and test counts keep the mock run short
SMALL = {"attack": 15, "benign": 9, "victim_test": 3, "benign_test": 4, "history": 4}
ROWS = ["clean", "undefended", "static", "safemem_strict", "pub:A-MemGuard", "pub:RandEC",
        "R", "C", "M", "S", "SL", "S2-ID"]  # fmt: skip


def _brief(rows: dict) -> dict:
    return {k: {m: v.get(m) for m in P.METRICS if v.get(m) is not None} for k, v in rows.items()}


def smoke(base: Path, jobs: int = 8) -> dict:
    subprocess.run([sys.executable, str(P.REPO / "scripts" / "minja_patch.py")], check=True,
                   stdout=subprocess.DEVNULL)  # fmt: skip
    # resume: passing an existing smoke folder reuses it; finished runs (.done) are skipped and
    # unfinished ones are renamed .incomplete-<time> and rerun by the Runner
    if base.name.startswith("minja_v2_smoke_") and base.is_dir():
        root = base
    else:
        root = base.parent / f"minja_v2_smoke_{time.strftime('%Y%m%dT%H%M%S')}"
    r = Runner(root, mock=True, counts=SMALL, jobs=jobs)
    pair = {"pair_id": "SMOKE00", "role": "smoke", "victim": 10006, "target": 10011, "seed": 7}
    t0 = time.time()
    r.bench(pair)
    r.precompute(pair)
    w = r.write(pair)
    a = r.audits(pair)
    reads = r.read(pair, rows=ROWS)
    s = r.score(pair)
    hist = s.get("hist", {})
    return {
        "root": str(root), "seconds": round(time.time() - t0, 1), "write": w,
        "audit_shortfall": a, "isr": s["isr"], "isr_hist": hist.get("isr"),
        "read_runs": len(reads),
        "unfinished": [x for x in reads if not (x["victim"] and x["benign"])],
        "same_tickets_across_arms": {**s["same_tickets_across_arms"],
                                     **hist.get("same_tickets_across_arms", {})},
        "malicious_attacker_records": s["malicious_attacker_records"],
        "malicious_attack_phase_records_hist": hist.get("malicious_attacker_records"),
        "history_records": hist.get("history_records"),
        "laundered_records": s["laundered_records"],
        "stale_code_records": {"attack": s["stale_code_records"],
                               "hist": hist.get("stale_code_records")},
        "technical": {k: v for k, v in s["technical"].items() if k != "per_run"},
        "gorule_on_smoke_pair": evaluate([s]),
        "rows": _brief(s["rows"]), "rows_hist": _brief(hist.get("rows", {})),
        "ledger_usd": r.spent(),
    }  # fmt: skip


if __name__ == "__main__":
    print(json.dumps(smoke(Path(sys.argv[1])), indent=1))
