"""Offline eligibility and review-priority diagnostics; never semantic validation."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ams.research.dynamic.models import check, digest
from ams.research.execution.session import new_json
from ams.research.llm_review.validation import QA_KEYS
from ams.research.phase1_common import read_jsonl
from ams.research.recovery.offline import sha_file

from .pipeline import verify_results
from .plan import verify


def analyse(review, prepared, out):
    check(not out.exists(), "Analysis version exists")
    _cfg, _jobs = verify(review)
    verify_results(review)
    proposals = read_jsonl(review / "automated_proposals.jsonl")
    bundles = json.loads((review / "automated_bundles.json").read_text())
    sources = {b["contribution_id"]: b for b in bundles}
    records = {r["record_id"]: r for p in proposals for r in p["records"]}
    questions = {q["candidate_id"]: q for p in proposals for q in p["questions"]}
    index = {
        p["contribution_id"]: p
        for p in read_jsonl(prepared / "private/evaluator_case_index.jsonl")
        if p["contribution_id"] in sources
    }
    packets = {
        p["contribution_id"]: p
        for p in read_jsonl(prepared / "private/review_packets.jsonl")
        if p["contribution_id"] in sources
    }
    candidates = {
        q["candidate_id"]: q
        for q in read_jsonl(prepared / "private/question_drafts.jsonl")
        if q["contribution_id"] in sources
    }
    check(set(index) == set(packets) == set(sources), "Missing evaluator/packet inputs")
    backed, flags = set(), []
    question_flags = Counter()
    for qid, candidate in candidates.items():
        review_q = questions.get(qid)
        if review_q is None:
            question_flags["missing_assessment"] += 1
            continue
        for key in QA_KEYS:
            if review_q[key] is not True:
                question_flags[key + ("_uncertain" if review_q[key] is None else "_failed")] += 1
        if not all(review_q[key] is True for key in QA_KEYS):
            continue
        pid, rid = candidate["contribution_id"], candidate["support_record_id"]
        record = records.get(rid)
        artifacts = {a["artifact_id"]: a for a in packets[pid]["artifacts"]}
        support = artifacts.get(candidate["support_artifact_id"])
        literal_support = (
            support
            and support["role"] == "external"
            and support["text"][candidate["start"] : candidate["end"]] == candidate["quote"]
        )
        if not literal_support:
            question_flags["literal_external_support_mismatch"] += 1
            continue
        if (
            sources[pid]["complete_automated_record_coverage"]
            and sources[pid]["AI_assessed_bundle"] == "safe_for_use"
            and candidate["support_record_kind"] == "claim"
            and record
            and record["origin"] == "external"
            and record["verdict"] == "safe_for_use"
        ):
            backed.add(pid)
    for packet in packets.values():
        roles = {a["artifact_id"]: a["role"] for a in packet["artifacts"]}
        for raw in packet["records"]:
            proposal = records.get(raw["record_id"])
            if proposal is None:
                flags.append({"record_id": raw["record_id"], "flag": "unassessed_record"})
                continue
            if proposal["origin"] == "ambiguous":
                flags.append({"record_id": raw["record_id"], "flag": "ambiguous_source_field"})
            if raw["record_kind"] == "evidence_chunk":
                construction_roles = {
                    roles[s["artifact_id"]] for s in raw["construction_source_spans"]
                }
                if construction_roles and proposal["origin"] not in construction_roles:
                    flags.append(
                        {"record_id": raw["record_id"], "flag": "chunk_source_field_disagreement"}
                    )
    contexts = {}
    for context in ("email", "file_and_doc"):
        pool = [p for p in index.values() if p["context_id"] == context]
        quotas = []
        for stratum, label, needed in [
            ("attack", "unsafe", 8),
            ("attack", "safe_for_use", 2),
            ("explicit_benign", "safe_for_use", 1),
            ("suggestive_benign", "safe_for_use", 5),
        ]:
            available = [
                p["contribution_id"]
                for p in pool
                if p["stratum"] == stratum
                and sources[p["contribution_id"]]["AI_assessed_bundle"] == label
            ]
            qa_ready = available if label == "unsafe" else [p for p in available if p in backed]
            quotas.append(
                {
                    "original_case_stratum": stratum,
                    "AI_bundle_label": label,
                    "needed": needed,
                    "available_complete_AI_labels": len(available),
                    "available_with_AI_checked_external_claim_QA": len(qa_ready),
                    "QA_conditioned_shortfall": max(0, needed - len(qa_ready)),
                }
            )
        contexts[context] = {"inputs": len(pool), "quotas": quotas}
    # A fixed hash sample is preparation for later independent quality checking.
    # Its packets deliberately omit this model's votes and all case-intent labels.
    sample = []
    for pid in sorted(packets, key=lambda k: digest(["followup-quality-sample-v1", k]))[:8]:
        packet = packets[pid]
        sample.append(
            {
                k: packet[k]
                for k in ("contribution_id", "task", "intended_use", "context_id", "artifacts")
            }
            | {
                "records": [
                    {k: r[k] for k in ("record_id", "record_kind", "text", "content_hash")}
                    for r in packet["records"]
                ],
                "quality_review_status": "pending_independent_assessment",
            }
        )
    result = {
        "status": "automated_followup_feasibility_only",
        "development_inputs": len(index),
        "complete_automated_bundles": sum(b["complete_automated_record_coverage"] for b in bundles),
        "AI_bundle_counts": dict(Counter(b["AI_assessed_bundle"] for b in bundles)),
        "per_context": contexts,
        "AI_safe_contributions_with_AI_accepted_claim_backed_QA": len(backed),
        "question_drafts": len(candidates),
        "question_assessments": len(questions),
        "question_review_flags": dict(question_flags),
        "record_review_flags": dict(Counter(f["flag"] for f in flags)),
        "independent_quality_sample_inputs": len(sample),
        "independent_quality_sample_completed": 0,
        "human_verified_labels": 0,
        "human_validated_questions": 0,
        "scientific_pilot_ready": False,
        "exploratory_label_and_QA_quotas_satisfied": all(
            q["QA_conditioned_shortfall"] == 0 for c in contexts.values() for q in c["quotas"]
        ),
        "automatic_execution_unlock": False,
        "accuracy_FPR_FNR_ASR": "not_measured",
        "notice": "AI proposals and structural diagnostics, not validated semantic quality.",
        "case_label_notice": "Original input intent and record/use safety are different labels.",
        "additional_API_cost_for_analysis_usd": "0",
    }
    out.mkdir(parents=True, mode=0o700)
    for name, value in [
        ("feasibility.json", result),
        ("record_review_flags.json", flags),
        ("blinded_quality_sample.json", sample),
    ]:
        new_json(out / name, value)
    new_json(
        out / "analysis_manifest.json",
        {
            "dependencies": {
                str(p.resolve()): sha_file(p)
                for p in (
                    review / "review_manifest.json",
                    review / "results_manifest.json",
                    prepared / "private/evaluator_case_index.jsonl",
                    prepared / "private/question_drafts.jsonl",
                    prepared / "private/review_packets.jsonl",
                    Path(__file__),
                )
            },
            "files": {
                n: sha_file(out / n)
                for n in (
                    "feasibility.json",
                    "record_review_flags.json",
                    "blinded_quality_sample.json",
                )
            },
        },
    )
    return result
