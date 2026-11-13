#!/usr/bin/env python3
"""Audit stored AI proposals offline; this does not measure annotation accuracy."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from ams.research.dynamic.models import check, digest
from ams.research.execution.session import new_json
from ams.research.llm_review.validation import QA_KEYS
from ams.research.phase1_common import read_jsonl
from ams.research.pilot_finish.utility import collect, eligible_questions, verified_proposals
from ams.research.recovery.offline import no_network, sha_file


def audit(prepared, reviews, out):
    check(not out.exists(), "Audit output already exists")
    packets, records, assessments, candidates, bundles = collect(reviews, prepared)
    index = {
        row["contribution_id"]: row
        for row in read_jsonl(prepared / "private/evaluator_case_index.jsonl")
    }
    groups = json.loads((prepared / "private/group_selections.json").read_text())
    membership = {pid: group["bag_id"] for group in groups for pid in group["source_ids"]}
    development = {f"D{i:02d}" for i in range(8)}
    check(all(membership.get(pid) in development for pid in packets), "Reserved input reviewed")
    components = [index[pid]["group_id"] for pid in packets]
    check(len(components) == len(set(components)), "Repeated template/duplicate component")
    for directory in reviews:
        for proposal in verified_proposals(directory):
            check(proposal["annotation_source"] == "llm", "Non-AI proposal in AI view")
            for flag in ["human_validated", "eligible_as_gold", "can_update_live_trust"]:
                check(proposal[flag] is False, f"Unsafe annotation flag: {flag}")
    counts, recovery, labels, qa_labels = Counter(), Counter(), Counter(), Counter()
    source_checks = unsafe_checks = 0
    missing = []
    for pid, packet in packets.items():
        artifacts = {row["artifact_id"]: row for row in packet["artifacts"]}
        labels[(index[pid]["context_id"], index[pid]["stratum"], bundles[pid]["AI_label"])] += 1
        for record in packet["records"]:
            kind = record["record_kind"]
            counts[(kind, "expected")] += 1
            recovery[(kind, record["recovery_status"])] += 1
            row = records.get(record["record_id"])
            if row is None:
                missing.append({"contribution_id": pid, "record_id": record["record_id"]})
                continue
            counts[(kind, "AI_reviewed")] += 1
            counts[(kind, row["verdict"], row["origin"])] += 1
            check(row["content_hash"] == record["content_hash"], "Stale record proposal")
            check(row["source_identity_authenticated"] is False, "AI authenticated an identity")
            for span in row["source_spans"]:
                source = artifacts.get(span["artifact_id"])
                check(source is not None, "Unknown source reference")
                check(source["text"][span["start"] : span["end"]] == span["quote"], "Bad span")
                if row["origin"] != "ambiguous":
                    check(source["role"] == row["origin"], "Wrong principal/external role")
                source_checks += 1
            check(row["origin"] == "ambiguous" or row["source_spans"], "No origin evidence")
            if row["verdict"] == "unsafe":
                check(
                    row["evidence_quote"] and row["evidence_quote"] in record["text"], "No evidence"
                )
                unsafe_checks += 1
    for cid, assessment in assessments.items():
        check(cid in candidates, "Unknown question assessment")
        flags = [assessment[k] for k in QA_KEYS]
        status = (
            "AI_accepted"
            if all(v is True for v in flags)
            else ("AI_rejected" if any(v is False for v in flags) else "AI_uncertain")
        )
        qa_labels[status] += 1
    questions = eligible_questions(packets, records, assessments, candidates, bundles)
    summary = {
        "status": "passed_mechanical_checks_not_semantic_validation",
        "development_groups": dict(sorted(Counter(membership[pid] for pid in packets).items())),
        "reviewed_contributions": len(packets),
        "complete_AI_bundles": sum(b["complete"] for b in bundles.values()),
        "bundle_AI_labels": dict(Counter(b["AI_label"] for b in bundles.values())),
        "record_counts": {"/".join(key): value for key, value in sorted(counts.items())},
        "record_recovery_statuses": {
            "/".join(key): value for key, value in sorted(recovery.items())
        },
        "bundle_strata": [
            {"context": c, "original_stratum": s, "AI_label": label, "count": n}
            for (c, s, label), n in sorted(labels.items())
        ],
        "missing_record_reviews": missing,
        "exact_source_spans_checked": source_checks,
        "unsafe_record_evidence_checked": unsafe_checks,
        "distinct_template_components": len(set(components)),
        "reserved_reviewed_contributions": 0,
        "candidate_question_versions": len(candidates),
        "active_question_assessments": len(assessments),
        "active_question_statuses": dict(qa_labels),
        "AI_safe_bundles_with_accepted_claim_question": len(questions),
        "human_verified_labels": 0,
        "human_validated_questions": 0,
        "annotation_accuracy": "not_measured",
        "natural_source_authentication": "not_established",
        "defense_efficacy": "not_measured",
    }
    out.mkdir(parents=True, mode=0o700)
    new_json(out / "coverage.json", summary)
    dependencies = [
        Path(__file__),
        prepared / "private/review_packets.jsonl",
        prepared / "private/question_drafts.jsonl",
        prepared / "private/evaluator_case_index.jsonl",
        prepared / "private/group_selections.json",
        *[directory / "results_manifest.json" for directory in reviews],
    ]
    new_json(
        out / "manifest.json",
        {
            "coverage_sha256": sha_file(out / "coverage.json"),
            "dependencies": {str(path.resolve()): sha_file(path) for path in dependencies},
            "summary_hash": digest(summary),
        },
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prepared", type=Path, default=Path("research_data/mpbench_provisional_v1_20261029")
    )
    parser.add_argument("--reviews", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with no_network():
        report = audit(args.prepared, args.reviews, args.out)
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "status",
                    "reviewed_contributions",
                    "complete_AI_bundles",
                    "active_question_statuses",
                    "human_verified_labels",
                ]
            },
            indent=2,
        )
    )
