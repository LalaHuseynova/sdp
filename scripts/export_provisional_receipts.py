#!/usr/bin/env python3
"""Export authoritative, settled physical calls for both experiment scopes privately."""

import argparse
import json
import sqlite3
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from ams.research.dynamic.models import canonical, check, digest
from ams.research.execution.session import dispatch_hash, new_json
from ams.research.provisional_extension import verify as verify_extension
from ams.research.provisional_run.preparation import verify
from ams.research.recovery.offline import no_network


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    check(not args.out.exists(), "Refuse to overwrite API receipt exports")
    repo = Path(__file__).resolve().parents[1]
    with no_network():
        cfg, spec = verify(repo / "research_data/provisional_comparison_freeze_v1_20261101")
        other, more = verify_extension(
            repo / "research_data/provisional_extension_freeze_v1_20261101"
        )
        scopes = {digest([cfg, spec]): "D00", digest([other, more]): "D01-D07"}
        session = Path(cfg["session_directory"])
        calls = []
        totals = defaultdict(lambda: defaultdict(int))
        with sqlite3.connect(
            f"file:{(session / 'dispatch.sqlite').resolve()}?mode=ro", uri=True
        ) as db:
            db.row_factory = sqlite3.Row
            for row in db.execute("SELECT * FROM dispatches"):
                scope = next(
                    (
                        name
                        for h, name in scopes.items()
                        if digest([h, row["stage"], row["request_key"]]) == row["call_id"]
                    ),
                    None,
                )
                if scope is None:
                    continue
                check(row["status"] == "completed", "Unfinished experiment call")
                result = json.loads(row["result"])
                check(dispatch_hash(row, result) == row["result_hash"], "Changed physical response")
                receipt = result["dispatch"]["receipt"]
                check(
                    receipt["state"] == "settled" and result["error"] is None,
                    "Unverified/failed experiment billing",
                )
                native = db.execute(
                    "SELECT body FROM provisional_native_responses WHERE call_id=?",
                    (row["call_id"],),
                ).fetchone()
                check(native is not None, "Native response missing")
                value = {
                    "scope": scope,
                    **dict(row),
                    "request": json.loads(row["request"]),
                    "result": result,
                    "native_response": json.loads(native[0]),
                }
                calls.append(value)
                stage = totals[row["stage"]]
                stage["physical_calls"] += 1
                stage["input_tokens"] += result["response"]["usage"]["input_tokens"]
                stage["output_tokens"] += result["response"]["usage"]["output_tokens"]
                stage["actual_nanodollars"] += receipt["actual_nanodollars"]
        with sqlite3.connect(
            f"file:{(session / 'budget.sqlite').resolve()}?mode=ro", uri=True
        ) as db:
            used, held, blocked = db.execute(
                "SELECT used_nanodollars,held_nanodollars,blocked FROM budget_config"
            ).fetchone()
            states = dict(db.execute("SELECT state,COUNT(*) FROM reservations GROUP BY state"))
        check(
            int(held) == 0 and blocked == 0 and not set(states) - {"settled"},
            "Unsettled project billing",
        )
        total = sum(v["actual_nanodollars"] for v in totals.values())
        check(
            Decimal(used) / 1_000_000_000 - Decimal(cfg["budget_start_used_usd"])
            == Decimal(total) / 1_000_000_000,
            "Task costs do not reconcile with the shared project ledger",
        )
        check(
            Decimal(total) / 1_000_000_000 <= 5 and Decimal(used) / 1_000_000_000 <= 30,
            "Spending ceiling exceeded",
        )
        args.out.mkdir(parents=True, mode=0o700)
        with (args.out / "physical_responses.jsonl").open("x") as stream:
            for value in calls:
                stream.write(canonical(value) + "\n")
        (args.out / "physical_responses.jsonl").chmod(0o600)
        summary = {
            "status": "settled_reconciled",
            "new_physical_calls": len(calls),
            "stage_totals": dict(totals),
            "new_task_cost_usd": str(Decimal(total) / 1_000_000_000),
            "project_used_usd": str(Decimal(used) / 1_000_000_000),
            "remaining_usd": str(Decimal(30) - Decimal(used) / 1_000_000_000),
            "held_usd": "0",
            "budget_blocked": False,
            "new_verification_inference_calls": 0,
            "human_verified_labels": 0,
            "cost_scope": (
                "actual shared physical charges; per-policy equivalent verification "
                "is in frozen episode manifests"
            ),
        }
        new_json(args.out / "summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "stage_totals"}, indent=2))


if __name__ == "__main__":
    main()
