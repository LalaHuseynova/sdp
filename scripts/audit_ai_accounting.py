#!/usr/bin/env python3
"""Reconcile completed annotation calls, native replies and durable receipts offline."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from decimal import Decimal
from pathlib import Path

from ams.research.dynamic.models import canonical, check
from ams.research.execution.session import dispatch_hash, new_json
from ams.research.pilot_finish.reviewer import BASELINE_NANODOLLARS, TASK_CAP_NANODOLLARS
from ams.research.recovery.annotation import assert_blinded
from ams.research.recovery.offline import no_network


def audit(root, out):
    check(not out.exists(), "Accounting report already exists")
    data = root / "research_data"
    session = data / "dynamic_execution_prep_v1_20261031/session"
    old_ids = set()
    for name in [
        "llm_review_dev_v2_20261031",
        "llm_review_small_batches_v2_20261031",
        "llm_review_followup_v3_1_20261031",
    ]:
        old_ids.update(
            job["call_id"] for job in json.loads((data / name / "jobs.json").read_text())
        )
    check(len(old_ids) == 306, "Unexpected starting annotation scope")
    with sqlite3.connect((session / "dispatch.sqlite").as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM dispatches").fetchall()
        check(all(row["status"] == "completed" for row in rows), "Unfinished or failed dispatch")
        check(
            not db.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall(),
            "Maintenance gate still installed",
        )
        calls = {row["call_id"] for row in rows} - old_ids
        jobs = {}
        for folder in sorted(data.glob("pilot_finish*")):
            for file in sorted(folder.rglob("jobs.json")):
                for job in json.loads(file.read_text()):
                    if job["call_id"] not in calls:
                        continue
                    identity = canonical(
                        {"request": job["request"], "schema": job["response_schema"]}
                    )
                    check(
                        job["call_id"] not in jobs or jobs[job["call_id"]][0] == identity,
                        "Conflicting frozen call identity",
                    )
                    jobs[job["call_id"]] = (identity, job)
        check(set(jobs) == calls, "Unplanned paid call")
        old_cost = new_cost = Decimal(0)
        tokens, finishes, native_models = Counter(), Counter(), Counter()
        receipt_ids = set()
        for row in rows:
            result = json.loads(row["result"])
            check(dispatch_hash(row, result) == row["result_hash"], "Changed dispatch response")
            check(result["error"] is None, "Transport/billing failure")
            paid = Decimal(result["actual_paid_usd"])
            receipt = result["dispatch"]["receipt"]
            check(receipt["state"] == "settled", "Unsettled receipt")
            check(
                Decimal(receipt["actual_nanodollars"]) / 1_000_000_000 == paid,
                "Receipt cost mismatch",
            )
            check(receipt["reservation_id"] not in receipt_ids, "Repeated paid receipt")
            receipt_ids.add(receipt["reservation_id"])
            if row["call_id"] in old_ids:
                old_cost += paid
                continue
            new_cost += paid
            job = jobs[row["call_id"]][1]
            body = json.loads(
                db.execute(
                    "SELECT body FROM structured_actual_requests WHERE call_id=?", (row["call_id"],)
                ).fetchone()[0]
            )
            check(
                body["response_format"]["json_schema"]["schema"] == job["response_schema"],
                "Actual HTTP schema differs",
            )
            for key in ["model", "messages", "max_tokens", "temperature"]:
                check(body[key] == job["request"][key], "Actual HTTP request differs")
            assert_blinded(json.loads(body["messages"][1]["content"]))
            provider = body["extra_body"]["provider"]
            check(
                provider["require_parameters"] is True and provider["allow_fallbacks"] is False,
                "Unrestricted provider routing",
            )
            check(
                Decimal(str(provider["max_price"]["prompt"])) == Decimal("0.15"),
                "Input rate changed",
            )
            check(
                Decimal(str(provider["max_price"]["completion"])) == Decimal("0.60"),
                "Output rate changed",
            )
            native = json.loads(
                db.execute(
                    "SELECT body FROM annotation_native_responses WHERE call_id=?",
                    (row["call_id"],),
                ).fetchone()[0]
            )
            check(Decimal(str(native["usage"]["cost"])) == paid, "Native cost differs from receipt")
            choice = native["choices"][0]
            check(
                choice["message"]["content"] == result["response"]["text"],
                "Saved text differs from native response",
            )
            check(
                choice["finish_reason"] == result["response"]["raw_finish_reason"],
                "Finish reason changed",
            )
            finishes[choice["finish_reason"]] += 1
            native_models[native["model"]] += 1
            tokens["input"] += native["usage"]["prompt_tokens"]
            tokens["output"] += native["usage"]["completion_tokens"]
    check(old_cost == Decimal(BASELINE_NANODOLLARS) / 1_000_000_000, "Starting cost changed")
    check(new_cost <= Decimal(TASK_CAP_NANODOLLARS) / 1_000_000_000, "Finishing-task cap exceeded")
    check(old_cost + new_cost <= Decimal(30), "Project ceiling exceeded")
    with sqlite3.connect((session / "budget.sqlite").as_uri() + "?mode=ro", uri=True) as db:
        states = dict(
            db.execute("SELECT state,count(*) FROM reservations GROUP BY state").fetchall()
        )
        check(set(states) == {"settled"}, "Pending, unknown or breach accounting")
        receipt_total = db.execute("SELECT sum(actual_nanodollars) FROM reservations").fetchone()[0]
        check(Decimal(receipt_total) / 1_000_000_000 == old_cost + new_cost, "Guard total differs")
    summary = {
        "status": "passed",
        "starting_requests": len(old_ids),
        "starting_project_cost_usd": str(old_cost),
        "new_paid_requests": len(calls),
        "new_paid_cost_usd": str(new_cost),
        "total_project_requests": len(rows),
        "total_project_cost_usd": str(old_cost + new_cost),
        "remaining_project_usd": str(Decimal(30) - old_cost - new_cost),
        "finishing_task_added_limit_usd": "5.00",
        "project_limit_usd": "30.00",
        "new_native_tokens": dict(tokens),
        "new_finish_reasons": dict(finishes),
        "new_native_reported_models": dict(native_models),
        "settled_receipts": states["settled"],
        "pending_unknown_breach_receipts": 0,
        "actual_schema_request_response_and_cost_checks": len(calls),
        "actual_serialized_inputs_blinded": True,
        "annotation_accuracy": "not_measured",
        "defense_experiments": 0,
    }
    new_json(out, summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with no_network():
        result = audit(Path.cwd(), args.out)
    print(json.dumps(result, indent=2))
