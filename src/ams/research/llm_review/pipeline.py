"""Run one disclosed automated development review; do not score a defense."""

from __future__ import annotations

import json
import os
from collections import Counter
from decimal import Decimal
from pathlib import Path

from ams.core.env import load_env
from ams.research.dynamic.models import canonical, check, digest
from ams.research.execution.session import new_json
from ams.research.recovery.offline import sha_file

from .design import verify
from .transport import AnnotationSession
from .validation import QA_KEYS, validate


def finish(out: Path, config, jobs, responses, session):
    proposals, failures = [], []
    for job, result in zip(jobs, responses, strict=False):
        try:
            check(not result["error"], "Transport/billing incomplete")
            proposal = validate(job, result["response"])
            proposals.append(proposal)
        except (ValueError, KeyError, TypeError, AttributeError, IndexError) as exc:
            failures.append(
                {
                    "call_id": job["call_id"],
                    "contribution_id": job["contribution_id"],
                    "type": type(exc).__name__,
                    "reason": str(exc),
                }
            )
    labels = Counter(r["verdict"] for p in proposals for r in p["records"])
    origins = Counter(r["origin"] for p in proposals for r in p["records"])
    bundles = Counter(p["AI_assessed_bundle"] for p in proposals)
    qa = [q for p in proposals for q in p["questions"]]
    accepted = sum(all(q[k] is True for k in QA_KEYS) for q in qa)
    cost = sum(
        (Decimal(r["actual_paid_usd"]) for r in responses if r["actual_paid_usd"] is not None),
        Decimal(0),
    )
    snapshot = session.summary()
    summary = {
        "status": "automated_development_review_complete"
        if len(responses) == 32 and not failures
        else "automated_development_review_partial",
        "scope": "first 32-case development bag; one LLM pass",
        "annotation_source": "llm",
        "model": config["model"],
        "planned_requests": 32,
        "responses_received": len(responses),
        "schema_valid_complete_packets": len(proposals),
        "invalid_or_failed_packets": len(failures),
        "mechanically_valid_record_proposals": sum(labels.values()),
        "record_verdict_counts": dict(labels),
        "record_origin_counts": dict(origins),
        "AI_assessed_bundle_counts": dict(bundles),
        "question_proposals_checked": len(qa),
        "AI_accepted_question_drafts": accepted,
        "human_validated_questions": 0,
        "human_verified_labels": 0,
        "annotation_accuracy": "not_measured",
        "annotation_source_identity_authenticated": False,
        "defense_ASR": "not_measured",
        "scientific_pilot_ready": False,
        "automatic_gold_or_trust_update": False,
        "actual_review_cost_usd": str(cost),
        "unknown_billing_responses": sum(r["actual_paid_usd"] is None for r in responses),
        "shared_project_budget": snapshot["budget"],
        "paid_inference_mode": session.mode,
        "no_defense_benchmark_or_training_performed": True,
    }
    with (out / "automated_proposals.jsonl").open("x", encoding="utf-8") as stream:
        for p in proposals:
            stream.write(canonical(p) + "\n")
    (out / "automated_proposals.jsonl").chmod(0o600)
    new_json(out / "review_failures.json", failures)
    new_json(out / "summary.json", summary)
    files = {
        n: sha_file(out / n)
        for n in ("automated_proposals.jsonl", "review_failures.json", "summary.json")
    }
    new_json(out / "results_manifest.json", {"files": files, "hash": digest(files)})
    return summary


def run(out: Path, *, mock_transport=None):
    config, jobs = verify(out)
    if (out / "results_manifest.json").exists():
        lock = json.loads((out / "results_manifest.json").read_text())
        check(lock["hash"] == digest(lock["files"]), "Review results manifest changed")
        for name, checksum in lock["files"].items():
            check(sha_file(out / name) == checksum, "Review result changed")
        return json.loads((out / "summary.json").read_text())
    response_dir = out / "responses"
    response_dir.mkdir(exist_ok=True, mode=0o700)
    with AnnotationSession(Path(config["session_directory"])) as session:
        if mock_transport is None:
            load_env()
            key = os.environ.get("OPENROUTER_API_KEY")
            check(bool(key), "OPENROUTER_API_KEY unavailable")
            session.arm_annotation(out, key)
            preflight = out / "provider_preflight.json"
            if not preflight.exists():
                new_json(preflight, session.provider_preflight)
        else:
            session.arm_annotation_mock(out, mock_transport)
        responses = []
        for number, job in enumerate(jobs, 1):
            result = session.complete_review(job)
            path = response_dir / (job["call_id"] + ".json")
            if path.exists():
                check(
                    json.loads(path.read_text()) == result,
                    "Saved response differs from dispatch transcript",
                )
            else:
                new_json(path, result)
            responses.append(result)
            print(
                f"LLM development review {number}/32 saved; "
                f"project charge ${session.guard.snapshot()['used_usd']:.6f}",
                flush=True,
            )
            if result["error"]:
                break
        return finish(out, config, jobs, responses, session)
