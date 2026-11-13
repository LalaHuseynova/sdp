#!/usr/bin/env python3
"""Capture a durable completed request prefix after an administrative dispatch gate."""

import argparse
import json
import sqlite3
from decimal import Decimal
from pathlib import Path

from ams.research.dynamic.models import canonical, check, digest
from ams.research.execution.session import dispatch_hash, new_json
from ams.research.pilot_finish.reviewer import decode, freeze, verify
from ams.research.recovery.offline import no_network, sha_file


def capture(parent, out):
    cfg, jobs = verify(parent)
    db = Path(cfg["session_directory"]) / "dispatch.sqlite"
    completed = []
    results = []
    gap = False
    with sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True) as c:
        c.row_factory = sqlite3.Row
        check(
            c.execute("SELECT count(*) FROM dispatches WHERE status='started'").fetchone()[0] == 0,
            "Wait for the active request to finish before capturing",
        )
        for j in jobs:
            row = c.execute("SELECT * FROM dispatches WHERE call_id=?", (j["call_id"],)).fetchone()
            if row is None:
                gap = True
                continue
            check(
                not gap and row["status"] == "completed",
                "Completed requests must form a clean prefix",
            )
            result = json.loads(row["result"])
            check(dispatch_hash(row, result) == row["result_hash"], "Changed dispatch result")
            check(
                result["error"] is None and result["dispatch"]["receipt"]["state"] == "settled",
                "Only settled authoritative replies can be captured",
            )
            completed.append(j)
            results.append(result)
    freeze(
        out,
        {
            **cfg,
            "scope_status": "interrupted_completed_prefix_only",
            "original_planned_requests": len(jobs),
            "captured_completed_requests": len(completed),
        },
        completed,
        [parent / "review_manifest.json", Path(__file__)],
    )
    (out / "responses").mkdir(mode=0o700)
    proposals = []
    for j, r in zip(completed, results, strict=True):
        new_json(out / "responses" / (j["call_id"] + ".json"), r)
        proposals.append(decode(j, r["response"]))
    with (out / "automated_proposals.jsonl").open("x") as f:
        for p in proposals:
            f.write(canonical(p) + "\n")
    (out / "automated_proposals.jsonl").chmod(0o600)
    summary = {
        "status": "durable_completed_prefix_captured",
        "completed_requests": len(completed),
        "original_planned_requests": len(jobs),
        "new_API_calls": 0,
        "new_API_cost_usd": "0",
        "originating_API_usage_cost_usd": str(
            sum((Decimal(r["actual_paid_usd"]) for r in results), Decimal(0))
        ),
        "accepted_records": sum(len(p["records"]) for p in proposals),
        "accepted_questions": sum(len(p["questions"]) for p in proposals),
        "human_verified_labels": 0,
    }
    new_json(out / "summary.json", summary)
    files = {n: sha_file(out / n) for n in ["automated_proposals.jsonl", "summary.json"]}
    new_json(out / "results_manifest.json", {"files": files, "hash": digest(files)})
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--parent", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    with no_network():
        s = capture(a.parent, a.out)
    print(json.dumps(s, indent=2))
