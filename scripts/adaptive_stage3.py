#!/usr/bin/env python3
"""Stage 3 (answers + judges) for adaptive-attack conditions and lineage arms. DEV ONLY.

    # free: exact count of NEW paid requests (mock answers, paid replies replayed)
    adaptive_stage3.py --estimate --out <dir> [--conditions ...] [--arms ...]
    # paid: only after the owner's explicit approval of the estimate
    adaptive_stage3.py --confirm-paid-adaptive-dev --cap 0.50 --out <dir> ...

Stores: real dev v3 Stage-1 stores, extended in memory by `adaptive.extend_store`
(relabelled provenance/audits only). Every request already answered in the shared
guarded ledger (dev Stage 3) is served from it at $0 (`EvaluationReplaySession`);
only new requests go to the guarded `adaptive_stage3` scope (own hard cap, one
attempt per request, identical requests sent once). No-memory answers are not
repeated (they do not depend on the condition). The frozen answer prompt, model,
judge and grading are unchanged.
"""

import argparse
import gzip
import json
import os
import sqlite3
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from ams.research.dynamic.models import check, digest
from ams.research.workload import adaptive as AD
from ams.research.workload import lineage as LN
from ams.research.workload.generator import read_rows, validate
from ams.research.workload.replay import CountingMockSession, EvaluationReplaySession
from ams.research.workload.runner import MEMORY_ARMS, run

REPO = Path(__file__).resolve().parents[1]
BUNDLE = REPO / "research_data/controlled_workload_v3_20261108"
STAGE1 = REPO / "research_data/controlled_workload_stage1_dev_v3_20261108"
SESSION = REPO / "research_data/controlled_workload_session_v2_20261108"
BASE = ("localized", "distributed", "uninformative")


def load_store(path):
    with gzip.open(path, "rt") as f:
        return json.load(f)


def mean_cost_per_stage(db_path):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    out = defaultdict(list)
    for stage, result in conn.execute(
        "SELECT stage,result FROM dispatches WHERE stage LIKE 'workload_%' AND status='completed'"
    ):
        out[stage].append(Decimal(json.loads(result)["actual_paid_usd"]))
    conn.close()
    return {s: sum(v) / len(v) for s, v in out.items() if v}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--conditions",
        nargs="*",
        default=[*BASE, *AD.all_conditions(8), *AD.followup_conditions(8)],
    )
    ap.add_argument("--arms", nargs="*", default=[*MEMORY_ARMS, "SL", "RL"])
    ap.add_argument("--tau", type=float, default=LN.DEFAULT_TAU)
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--confirm-paid-adaptive-dev", action="store_true")
    ap.add_argument("--cap", default="0.50")
    ap.add_argument("--groups", nargs="*", help="subset of dev groups (estimate sharding)")
    args = ap.parse_args()
    check(args.estimate != args.confirm_paid_adaptive_dev, "Pass exactly one mode")
    rows = read_rows(BUNDLE)
    validate(rows)
    manifest_hash = digest(json.loads((BUNDLE / "manifest.json").read_text()))
    stores = [load_store(p) for p in sorted((STAGE1 / "stores").glob("*.json.gz"))]
    check(all(s["group_id"].startswith("G-D") for s in stores), "Dev split only")
    if args.groups:
        check(args.estimate, "Paid runs cover every dev group")
        stores = [s for s in stores if s["group_id"] in args.groups]
    adaptive = [c for c in args.conditions if c not in BASE]
    stores = [AD.extend_store(rows, s, adaptive) for s in stores]
    conditions = tuple(args.conditions)
    lineage_needed = any(a in LN.LINEAGE_ARMS for a in args.arms)
    kwargs = dict(
        split="dev",
        conditions=conditions,
        arms=tuple(args.arms),
        no_memory=False,
        lineage_tau=args.tau if lineage_needed else None,
    )
    db = SESSION / "dispatch.sqlite"
    dev_scope = digest(["controlled-workload-stage3", manifest_hash, "dev"])
    if args.estimate:
        from ams.research.workload.mock import PromptAwareMock

        check(not args.out.exists(), "Estimate directory exists")
        inner = CountingMockSession(PromptAwareMock())
        session = EvaluationReplaySession(db, inner, dev_scope)
        result = run(rows, stores, session, args.out / "mock_journal", **kwargs)
        tally = inner.tally()
        means = mean_cost_per_stage(db)
        expected = sum(
            means.get(s, Decimal(0)) * tally.get(f"{s}:requests", 0)
            for s in ("workload_answer", "workload_conflict", "workload_judge")
        )
        estimate = {
            "status": "estimate_only_no_paid_call",
            "conditions": list(conditions),
            "arms": args.arms,
            "tau": args.tau,
            "outcome_rows": result["rows"],
            "replayed_from_paid_ledger": dict(session.counts),
            "new_distinct_requests": tally,
            "mean_actual_cost_per_request_usd": {k: str(v) for k, v in means.items()},
            "expected_cost_usd": str(expected.quantize(Decimal("0.0001"))),
            "expected_cost_with_30pct_allowance_usd": str(
                (expected * Decimal("1.3")).quantize(Decimal("0.0001"))
            ),
            "note": "Judge requests follow mock answers here; real answers can differ, so "
            "the judge count is approximate. Answers and conflicts are exact.",
        }
        (args.out / "cost_estimate.json").write_text(json.dumps(estimate, indent=2) + "\n")
        (args.out / "new_request_keys.json").write_text(
            json.dumps(sorted([s, k, c] for (s, k), c in inner.seen.items())) + "\n"
        )
        print(json.dumps(estimate, indent=2))
        return
    from ams.core.env import load_env
    from ams.research.workload.transport import ConstructionSession

    load_env()
    key = os.environ.get("OPENROUTER_API_KEY")
    check(bool(key), "Missing OpenRouter credential")
    with ConstructionSession(SESSION) as live:
        before = live.summary()["budget"]
        check(not before["blocked"], "Session is blocked (unresolved billing); not running")
        live.arm_construction(manifest_hash, "dev", key, Decimal(args.cap),
                              purpose="adaptive_stage3")  # fmt: skip
        session = EvaluationReplaySession(db, live, dev_scope)
        result = run(rows, stores, session, args.out, **kwargs)
        spend = live.task_spend()
        after = live.summary()["budget"]
    summary = {
        "status": "adaptive_stage3_complete",
        "conditions": list(conditions),
        "arms": args.arms,
        "tau": args.tau,
        "outcome_rows": result["rows"],
        "replay_counts": dict(session.counts),
        "task_cap_usd": args.cap,
        "actual_task_spend_usd": str(spend),
        "budget_before": {k: before[k] for k in ("used_usd", "remaining_usd", "held_usd")},
        "budget_after": {k: after[k] for k in ("used_usd", "remaining_usd", "held_usd")},
    }
    (args.out / "stage3_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
