#!/usr/bin/env python3
"""Step 10 offline sequential/restart validation on invented data; no MPBench run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ams.research.dynamic.models import LedgerError, canonical, check, digest
from ams.research.recovery.offline import no_network
from ams.research.retrieval.fixture import SESSION
from ams.research.sequential import SequentialRun, Step
from ams.research.sequential.fixture import build_state, query, sequence, write_step


def write(path: Path, value):
    with path.open("x") as stream:
        stream.write(canonical(value) + "\n")


def example(out: Path) -> dict:
    check(not out.exists(), "Refuse to overwrite an existing output")
    out.mkdir(parents=True, mode=0o700)
    (out / ".gitignore").write_text("*\n!.gitignore\n")
    arms = {}
    for arm in "RCMS":
        parent = out / arm
        state, fixture = build_state(
            parent / "reference-input-evidence.jsonl", arm, classifier=True
        )
        actions = sequence(state, fixture)
        with SequentialRun.create(parent / "reference", state) as run:
            for step in actions:
                check(run.step(step)["status"] == "completed", "Fixture action failed")
            actions.append(write_step(run.state, at=9))
            check(run.step(actions[-1])["status"] == "completed", "Fixture write failed")
            actions.append(query("after-write", 10, answer=False))
            check(run.step(actions[-1])["status"] == "completed", "Post-write retrieval failed")
            actions.append(
                Step.query(
                    "intentional-cache-miss",
                    11,
                    session_id=SESSION,
                    query="Uncached artificial question",
                    use_id="fixture-unavailable-use",
                    answer=True,
                )
            )
            check(run.step(actions[-1])["status"] == "failed", "Replay miss should stay failed")
            expected, expected_state = run.results(), run.state.dump()
            write(parent / "reference-results.json", expected)
        state, _ = build_state(parent / "prefix-input-evidence.jsonl", arm, classifier=True)
        with SequentialRun.create(parent / "prefix", state) as run:
            for step in actions[:4]:
                run.step(step)
            run.checkpoint(parent / "checkpoint")
            # Advance the source AFTER checkpoint creation to test isolation from its later tail.
            for step in actions[4:]:
                run.step(step)
        with SequentialRun.restore(parent / "checkpoint", parent / "resumed") as run:
            check(run.cursor == 4, "Restored a later source tail")
            for step in actions[4:]:
                run.step(step)
            check(run.results() == expected, "Resumed outputs differ from uninterrupted execution")
            check(run.state.dump() == expected_state, "Resumed runtime state differs")
            write(parent / "resumed-results.json", run.results())
            arms[arm] = {
                "events": run.cursor,
                "state_hash": digest(run.state.dump()),
                "restart_matches": True,
                "completed_queries": sum(
                    r["kind"] == "query" and r["status"] == "completed" for r in expected
                ),
                "failed_queries": sum(
                    r["kind"] == "query" and r["status"] == "failed" for r in expected
                ),
                "resources": run.state.usage(),
            }
    summary = {
        "status": "ARTIFICIAL SOFTWARE VALIDATION ONLY; no empirical MPBench result",
        "usage_values": (
            "Artificial response metadata, not provider measurements or an API cost estimate"
        ),
        "arms": arms,
        "all_restart_comparisons_match": True,
        "paid_api_calls": 0,
        "paid_cost_usd": 0,
        "training_runs": 0,
        "human_reviews_created": 0,
        "final_scientific_pilot_generated": False,
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
        print(f"Offline sequence validation stopped: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
