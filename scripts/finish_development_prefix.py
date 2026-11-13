#!/usr/bin/env python3
"""Complete a fixed development prefix, then freeze only if all AI-data gates pass.

New API scopes must be disclosed before invoking this explicit paid controller.
The shared parent guard and finishing-task cap remain authoritative.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
from pathlib import Path

from ams.research.dynamic.models import canonical, check, digest
from ams.research.execution.session import new_json
from ams.research.llm_followup.pipeline import verify_results
from ams.research.pilot_finish.reviewer import (
    PREPARED,
    freeze,
    prepare_review,
    run,
    verify,
)
from ams.research.pilot_finish.selection import freeze_exploratory, readiness
from ams.research.pilot_finish.utility import prepare_checks, prepare_generation, verified_proposals
from ams.research.recovery.offline import no_network, sha_file


def resolver():
    spec = importlib.util.spec_from_file_location(
        "ai_resolution", "scripts/resolve_ai_review_items.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def consolidate(parents, out):
    if out.exists():
        verify_results(out)
        return
    rows, questions, generated, accepted = {}, {}, {}, []
    for parent in parents:
        for proposal in verified_proposals(parent):
            p = {**proposal, "records": [], "questions": []}
            for row in proposal["records"]:
                rid = row["record_id"]
                if rid in rows:
                    check(
                        rows[rid] == row,
                        "Conflicting accepted record versions; no winner selection",
                    )
                else:
                    rows[rid] = row
                    p["records"].append(row)
            for row in proposal["questions"]:
                cid = row["candidate_id"]
                if cid in questions:
                    check(questions[cid] == row, "Conflicting question checks; no winner selection")
                else:
                    questions[cid] = row
                    p["questions"].append(row)
            if proposal.get("candidate_question"):
                q = proposal["candidate_question"]
                cid = q["candidate_id"]
                if cid in generated:
                    check(generated[cid] == q, "Conflicting generated reference version")
                    p["candidate_question"] = None
                else:
                    generated[cid] = q
            if p["records"] or p["questions"] or p.get("candidate_question"):
                accepted.append(p)
    out.mkdir(parents=True, mode=0o700)
    with (out / "automated_proposals.jsonl").open("x") as f:
        for p in accepted:
            f.write(canonical(p) + "\n")
    (out / "automated_proposals.jsonl").chmod(0o600)
    new_json(
        out / "summary.json",
        {
            "accepted_records": len(rows),
            "question_assessments": len(questions),
            "generated_candidates": len(generated),
            "human_verified_labels": 0,
            "selection_rule": "retain each unique accepted item; exact duplicates only",
            "parents": [str(p.resolve()) for p in parents],
            "new_API_cost_usd": "0",
        },
    )
    files = {n: sha_file(out / n) for n in ["automated_proposals.jsonl", "summary.json"]}
    new_json(
        out / "results_manifest.json",
        {
            "files": files,
            "hash": digest(files),
            "parent_manifests": {
                str(p.resolve()): sha_file(p / "results_manifest.json") for p in parents
            },
            "algorithm_sha256": sha_file(Path(__file__)),
        },
    )


def only_undispatched(parent, out):
    if out.exists():
        return verify(out)
    cfg, jobs = verify(parent)
    db = Path(cfg["session_directory"]) / "dispatch.sqlite"
    with sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        existing = {r[0] for r in conn.execute("SELECT call_id FROM dispatches")}
    selected = [j for j in jobs if j["call_id"] not in existing]
    freeze(
        out,
        {**cfg, "duplicate_completed_requests_excluded": len(jobs) - len(selected)},
        selected,
        [parent / "review_manifest.json", Path(__file__)],
    )
    return verify(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--through", type=int, default=7, choices=range(2, 8))
    p.add_argument("--start", type=int, default=2, choices=range(2, 8))
    p.add_argument("--initial-reviews", type=Path, nargs="+", required=True)
    args = p.parse_args()
    check(args.start <= args.through, "Invalid development prefix")
    root = args.out
    root.mkdir(mode=0o700, exist_ok=True)
    r = resolver()
    parents = list(args.initial_reviews)
    for index in range(args.start, args.through + 1):
        tag = f"D{index:02d}"
        folder = root / tag
        folder.mkdir(mode=0o700, exist_ok=True)
        # D02 may have been dispatched before this controller was started.
        existing = Path(f"research_data/pilot_finish_review_d{index:02d}_paired_v1_20261031")
        if existing.exists():
            review = existing
        else:
            plain = folder / "unrun_original_plan"
            review = folder / "paired_review"
            if not plain.exists():
                with no_network():
                    prepare_review(Path.cwd(), PREPARED, None, plain, [tag])
            if not review.exists():
                with no_network():
                    r.upgrade(plain, review)
        scope, planned = verify(review)
        print(
            canonical(
                {
                    "development_group": tag,
                    "planned_review_requests": len(planned),
                    "advance_working_estimate_usd": ["0.10", "0.40"],
                    "maximum_rate_reservation_sum_usd": scope["reservation_sum_usd"],
                }
            ),
            flush=True,
        )
        run(review)
        resolved = folder / "saved_items"
        if not resolved.exists():
            with no_network():
                r.resolve(review, resolved)
        pending = json.loads((resolved / "pending_items.json").read_text())
        parents.append(resolved)
        if pending:
            correction = folder / "pending_review"
            if not correction.exists():
                with no_network():
                    r.prepare_pending(resolved, review, correction)
            run(correction)
            parents.append(correction)
        combined = folder / "before_questions"
        with no_network():
            consolidate(parents, combined)
        generation = folder / "unrun_generation_plan"
        if not generation.exists():
            with no_network():
                prepare_generation(Path.cwd(), PREPARED, [combined], generation)
        fresh = folder / "new_generation_requests"
        with no_network():
            only_undispatched(generation, fresh)
        run(fresh)
        parents.append(fresh)
        check_plan = folder / "unrun_question_checks"
        if not check_plan.exists():
            with no_network():
                prepare_checks(Path.cwd(), PREPARED, fresh, check_plan)
        checks = folder / "new_question_checks"
        with no_network():
            only_undispatched(check_plan, checks)
        run(checks)
        parents.append(checks)
        final = folder / "combined_reviews"
        with no_network():
            consolidate(parents, final)
        ready = folder / "readiness"
        if not ready.exists():
            with no_network():
                result = readiness(PREPARED, [final], ready)
        else:
            result = json.loads((ready / "readiness.json").read_text())
        print(
            canonical(
                {
                    "development_prefix_end": tag,
                    "inputs": result["reviewed_development_inputs"],
                    "complete_bundles": result["complete_automated_bundles"],
                    "eligible_QA_sources": result["AI_safe_sources_with_checked_claim_QA"],
                    "ready": result["exploratory_data_ready"],
                    "strata": result["strata"],
                }
            ),
            flush=True,
        )
        parents = [final]
        if result["exploratory_data_ready"]:
            frozen = root / "frozen_AI_exploratory_dataset"
            if not frozen.exists():
                with no_network():
                    freeze_exploratory(PREPARED, [final], ready, frozen)
            new_json(
                root / "completion.json",
                {
                    "status": "AI_dataset_ready_no_defense_run",
                    "last_development_group": tag,
                    "frozen": str(frozen.resolve()),
                    "review": str(final.resolve()),
                    "human_verified_labels": 0,
                },
            )
            return
    new_json(
        root / "completion.json",
        {
            "status": "development_prefix_exhausted_data_not_ready",
            "last_development_group": f"D{args.through:02d}",
            "review": str(parents[0].resolve()),
            "human_verified_labels": 0,
            "defense_experiments": 0,
        },
    )


if __name__ == "__main__":
    main()
