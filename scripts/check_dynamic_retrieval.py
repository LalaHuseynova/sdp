#!/usr/bin/env python3
"""Inspect Step 9 using invented records and exact offline replay; no benchmark run."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

from ams.research.dynamic import Policy
from ams.research.dynamic.models import LedgerError, canonical, check
from ams.research.recovery.offline import no_network
from ams.research.retrieval import AccessSnapshot, GovernedRetrieval
from ams.research.retrieval.fixture import QUERY, SESSION, build_fixture


def write(path: Path, value: object):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(canonical(value) + "\n")


def example(out: Path) -> dict:
    check(not out.exists(), "Refuse to overwrite existing outputs")
    out.mkdir(parents=True, mode=0o700)
    (out / ".gitignore").write_text("*\n!.gitignore\n")
    original = build_fixture(out / "original/events.jsonl", external_evidence=True)
    expected = original.memory.retrieve(session_id=SESSION, query=QUERY)
    write(out / "original_result.json", asdict(expected))
    fixtures = {
        arm: build_fixture(out / arm / "events.jsonl", external_evidence=True) for arm in "RCMS"
    }
    rows = []
    parity = True
    for arm, fixture in fixtures.items():
        write(
            out / arm / "bindings.json",
            {
                "episode_id": fixture.bindings.episode_id,
                "sources": [asdict(s) for s in fixture.bindings.sources],
                "records": [asdict(r) for r in fixture.bindings.records],
            },
        )
        reader = GovernedRetrieval(fixture.memory, fixture.bindings, Policy(arm))
        for stage in ("initial", "one-incident", "two-incidents", "corrected", "revoked"):
            if stage == "one-incident":
                fixture.ledger.append(fixture.audit("root-0"))
            elif stage == "two-incidents":
                fixture.ledger.append(fixture.audit("root-1", event="a2", at=2))
            elif stage == "corrected":
                fixture.ledger.append(
                    fixture.audit("root-0", "safe_for_use", event="review", at=3, supersedes="a1")
                )
            access = fixture.access
            if stage == "revoked":
                access = AccessSnapshot(
                    "v2",
                    tuple(
                        replace(g, readers=("user", "audit_service"))
                        if g.artifact_id == "artifact-0"
                        else g
                        for g in access.grants
                    ),
                )
            context = fixture.context(access=access, requester="R1")
            outcome = reader.retrieve_with_trace(session_id=SESSION, query=QUERY, context=context)
            if stage == "initial":
                parity &= outcome.retrieval == expected
            fixture.ledger.snapshot().save(out / arm / f"snapshot-{stage}.json")
            write(
                out / arm / f"access-{stage}.json",
                {"version": access.version, "grants": [asdict(g) for g in access.grants]},
            )
            rows.append(
                {
                    "status": "ARTIFICIAL FIXTURE ONLY",
                    "arm": arm,
                    "stage": stage,
                    "retrieval": asdict(outcome.retrieval),
                    "trace": asdict(outcome.trace),
                }
            )
    with (out / "retrieval_traces.jsonl").open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(canonical(row) + "\n")
    check(parity, "Initial fixture contexts differ from Original SAFE-Mem")
    summary = {
        "status": "ARTIFICIAL FIXTURE ONLY; not MPBench efficacy or human annotations",
        "fixture_settings": (
            "external_evidence=True for path coverage; frozen MPBench setting unchanged"
        ),
        "invented_roots_per_arm": 10,
        "invented_records_per_arm": 20,
        "retrieval_checks": len(rows),
        "initial_original_parity": parity,
        "audit_tickets_per_arm": {
            a: f.ledger.snapshot().usage.tickets for a, f in fixtures.items()
        },
        "model_api_requests": 0,
        "paid_cost_usd": 0,
        "training_runs": 0,
        "mpbench_cases_used": 0,
        "human_reviews_created": 0,
        "scientific_pilot_generated": False,
    }
    write(out / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        with no_network():
            result = example(args.out)
        print(json.dumps(result, indent=2))
        return 0
    except (LedgerError, OSError) as error:
        print(f"Offline retrieval check stopped: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
