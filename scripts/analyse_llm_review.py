#!/usr/bin/env python3
"""Offline feasibility analysis of completed automated review; no accuracy/ASR claim."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from ams.research.dynamic.models import check, digest
from ams.research.execution.session import new_json
from ams.research.llm_review.batches import verify
from ams.research.llm_review.validation import QA_KEYS
from ams.research.phase1_common import read_jsonl
from ams.research.recovery.offline import no_network, sha_file


def analyse(review: Path, prepared: Path, out: Path):
    check(not out.exists(), "Analysis output exists; choose a new version")
    config, jobs = verify(review)
    lock = json.loads((review / "results_manifest.json").read_text())
    check(lock["hash"] == digest(lock["files"]), "Review results manifest changed")
    for name, expected in lock["files"].items():
        check(sha_file(review / name) == expected, "Completed review result changed")
    summary = json.loads((review / "summary.json").read_text())
    bundles = json.loads((review / "automated_bundles.json").read_text())
    proposals = read_jsonl(review / "automated_proposals.jsonl")
    by_source = {b["contribution_id"]: b for b in bundles}
    check(len(by_source) == len(bundles) == 32, "Wrong development contribution coverage")
    records = {r["record_id"]: r for p in proposals for r in p["records"]}
    check(
        len(records)
        == sum(len(p["records"]) for p in proposals)
        == summary["mechanically_valid_record_proposals"],
        "Repeated/inconsistent record proposals",
    )
    questions = {q["candidate_id"]: q for p in proposals for q in p["questions"]}
    index = {
        r["contribution_id"]: r
        for r in read_jsonl(prepared / "private/evaluator_case_index.jsonl")
        if r["contribution_id"] in by_source
    }
    candidates = {
        r["candidate_id"]: r for r in read_jsonl(prepared / "private/question_drafts.jsonl")
    }
    backed = set()
    for cid, q in questions.items():
        if not all(q[k] is True for k in QA_KEYS):
            continue
        candidate = candidates[cid]
        pid, rid = candidate["contribution_id"], candidate["support_record_id"]
        memory = records.get(rid)
        if (
            by_source[pid]["complete_automated_record_coverage"]
            and by_source[pid]["AI_assessed_bundle"] == "safe_for_use"
            and candidate["support_record_kind"] == "claim"
            and memory
            and memory["origin"] == "external"
            and memory["verdict"] == "safe_for_use"
        ):
            backed.add(pid)
    by_context = {}
    for context in ("email", "file_and_doc"):
        rows = [p for p in index.values() if p["context_id"] == context]
        check(len(rows) == 16, "Unexpected development context coverage")
        cross = Counter(
            (p["stratum"], by_source[p["contribution_id"]]["AI_assessed_bundle"]) for p in rows
        )
        requirements = [
            ("attack", "unsafe", 8),
            ("attack", "safe_for_use", 2),
            ("explicit_benign", "safe_for_use", 1),
            ("suggestive_benign", "safe_for_use", 5),
        ]
        quotas = []
        for stratum, label, needed in requirements:
            nominal = [
                p
                for p in rows
                if p["stratum"] == stratum
                and by_source[p["contribution_id"]]["AI_assessed_bundle"] == label
            ]
            utility_ready = (
                nominal
                if label == "unsafe"
                else [p for p in nominal if p["contribution_id"] in backed]
            )
            quotas.append(
                {
                    "original_case_stratum": stratum,
                    "AI_bundle_label": label,
                    "needed": needed,
                    "available_complete_AI_labels": len(nominal),
                    "available_with_AI_checked_external_claim_QA": len(utility_ready),
                    "nominal_shortfall": max(0, needed - len(nominal)),
                    "QA_conditioned_shortfall": max(0, needed - len(utility_ready)),
                }
            )
        by_context[context] = {
            "input_count": 16,
            "case_stratum_vs_AI_bundle_counts": [
                {"original_case_stratum": s, "AI_bundle": b, "count": n}
                for (s, b), n in sorted(cross.items())
            ],
            "quotas": quotas,
        }
    result = {
        "status": "automated_annotation_feasibility_only",
        "development_inputs": 32,
        "review_summary": summary,
        "per_context": by_context,
        "AI_safe_contributions_with_AI_accepted_claim_backed_QA": len(backed),
        "human_verified_labels": 0,
        "human_validated_questions": 0,
        "scientific_pilot_ready": False,
        "exploratory_pilot_automatically_unlocked": False,
        "accuracy_FPR_FNR_ASR": "not_measured",
        "crosstab_notice": (
            "Original input-case strata and AI record/use risk are different constructs; "
            "not a confusion matrix."
        ),
        "extra_API_calls_for_analysis": 0,
    }
    out.mkdir(parents=True, mode=0o700)
    new_json(out / "feasibility.json", result)
    deps = [
        review / "review_manifest.json",
        review / "results_manifest.json",
        prepared / "private/evaluator_case_index.jsonl",
        prepared / "private/question_drafts.jsonl",
        Path(__file__),
    ]
    new_json(
        out / "analysis_manifest.json",
        {
            "dependencies": {str(p.resolve()): sha_file(p) for p in deps},
            "files": {"feasibility.json": sha_file(out / "feasibility.json")},
            "scientific_ready": False,
        },
    )
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--review", type=Path, required=True)
    p.add_argument(
        "--prepared", type=Path, default=Path("research_data/mpbench_provisional_v1_20261029")
    )
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    with no_network():
        result = analyse(a.review, a.prepared, a.out)
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "status",
                    "development_inputs",
                    "AI_safe_contributions_with_AI_accepted_claim_backed_QA",
                    "scientific_pilot_ready",
                )
            },
            indent=2,
        )
    )
