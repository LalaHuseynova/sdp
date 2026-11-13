#!/usr/bin/env python3
"""Fixed development continuation with the explicit question-presence contract."""

import argparse
import importlib.util
import json
from pathlib import Path

from ams.research.execution.session import new_json
from ams.research.pilot_finish.reviewer import PREPARED, prepare_review, run, verify
from ams.research.pilot_finish.selection import freeze_exploratory, readiness
from ams.research.pilot_finish.utility import prepare_generation
from ams.research.recovery.offline import no_network


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def question_review(qa, parents, folder):
    plan = folder / "qa_contract_plan"
    if not plan.exists():
        with no_network():
            qa.prepare(Path.cwd(), PREPARED, parents, plan)
    cfg, jobs = verify(plan)
    print(
        json.dumps(
            {
                "QA_contract_requests": len(jobs),
                "working_estimate_usd": ["0.05", "0.20"],
                "maximum_reservation_sum_usd": cfg["reservation_sum_usd"],
            }
        ),
        flush=True,
    )
    qa.run(plan)
    combined = folder / "qa_contract_view"
    if not combined.exists():
        with no_network():
            qa.view(parents, plan, combined)
    return combined


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--initial-reviews", type=Path, nargs="+", required=True)
    p.add_argument("--start", type=int, default=3, choices=range(3, 8))
    p.add_argument("--through", type=int, default=7, choices=range(3, 8))
    a = p.parse_args()
    a.out.mkdir(mode=0o700, exist_ok=True)
    helper = load("prefix", "scripts/finish_development_prefix.py")
    resolution = load("resolution", "scripts/resolve_ai_review_items.py")
    qa = load("qa_contract", "scripts/recheck_ai_questions.py")
    parents = a.initial_reviews
    for i in range(a.start, a.through + 1):
        folder = a.out / f"D{i:02d}"
        folder.mkdir(mode=0o700, exist_ok=True)
        if i > a.start:
            plain = folder / "unrun_record_plan"
            paired = folder / "paired_record_review"
            if not plain.exists():
                with no_network():
                    prepare_review(Path.cwd(), PREPARED, None, plain, [f"D{i:02d}"])
            if not paired.exists():
                with no_network():
                    resolution.upgrade(plain, paired)
            print(
                f"Next fixed group D{i:02d}: estimate $0.10-$0.40; task cap unchanged.",
                flush=True,
            )
            run(paired)
            saved = folder / "saved_items"
            if not saved.exists():
                with no_network():
                    resolution.resolve(paired, saved)
            parents = [*parents, saved]
            if json.loads((saved / "pending_items.json").read_text()):
                pending = folder / "pending_items_review"
                if not pending.exists():
                    with no_network():
                        resolution.prepare_pending(saved, paired, pending)
                run(pending)
                parents.append(pending)
        raw = folder / "before_qa"
        if not raw.exists():
            with no_network():
                helper.consolidate(parents, raw)
        print(
            "Checking question-presence polarity; working estimate $0.05-$0.20.",
            flush=True,
        )
        current = question_review(qa, [raw], folder)
        for stage in ["initial", "after_new_questions"]:
            ready = folder / (stage + "_readiness")
            if not ready.exists():
                with no_network():
                    result = readiness(PREPARED, [current], ready)
            else:
                result = json.loads((ready / "readiness.json").read_text())
            print(
                json.dumps(
                    {
                        "stage": stage,
                        "prefix_end": i,
                        "inputs": result["reviewed_development_inputs"],
                        "eligible_QA_sources": result["AI_safe_sources_with_checked_claim_QA"],
                        "ready": result["exploratory_data_ready"],
                        "strata": result["strata"],
                    }
                ),
                flush=True,
            )
            if result["exploratory_data_ready"]:
                frozen = a.out / "frozen_AI_exploratory_dataset"
                if not frozen.exists():
                    with no_network():
                        freeze_exploratory(PREPARED, [current], ready, frozen)
                new_json(
                    a.out / "completion.json",
                    {
                        "status": "AI_dataset_ready_no_defense_run",
                        "prefix_end": i,
                        "frozen": str(frozen.resolve()),
                        "review": str(current.resolve()),
                        "human_verified_labels": 0,
                    },
                )
                return
            if stage == "initial":
                genplan = folder / "unrun_generation_plan"
                fresh = folder / "new_generation_requests"
                if not genplan.exists():
                    with no_network():
                        prepare_generation(Path.cwd(), PREPARED, [current], genplan)
                with no_network():
                    helper.only_undispatched(genplan, fresh)
                run(fresh)
                generated = folder / "with_new_candidates"
                if not generated.exists():
                    with no_network():
                        helper.consolidate([current, fresh], generated)
                nested = folder / "new_candidate_checks"
                nested.mkdir(mode=0o700, exist_ok=True)
                current = question_review(qa, [generated], nested)
        parents = [current]
    new_json(
        a.out / "completion.json",
        {
            "status": "development_prefix_exhausted_data_not_ready",
            "prefix_end": a.through,
            "review": str(current.resolve()),
            "defense_experiments": 0,
            "human_verified_labels": 0,
        },
    )


if __name__ == "__main__":
    main()
