"""Strict one-item decoding and append-only paid annotation follow-up."""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from ams.core.env import load_env
from ams.research.dynamic.models import canonical, check, digest
from ams.research.execution.session import new_json
from ams.research.llm_review.transport import AnnotationSession
from ams.research.llm_review.validation import QA_KEYS, strict_json, validate
from ams.research.phase1_annotations import bundle_verdict
from ams.research.recovery.offline import sha_file

from .plan import SCHEMA, completed_parent, verify


def decode(job, response):
    check(
        response and response["raw_finish_reason"] not in {"length", "max_tokens"},
        "Missing or truncated follow-up response",
    )
    parsed = strict_json(response["text"])
    check(type(parsed) is dict, "Expected one JSON object")
    data = json.loads(job["request"]["messages"][1]["content"])
    expanded = {"records": [], "questions": []}
    if job["kind"] == "record":
        check(
            set(parsed) == {"verdict", "origin", "source_units", "evidence_units", "reason"},
            "Unexpected single-record fields",
        )
        indices = parsed["source_units"]
        evidence = parsed["evidence_units"]
        for values, allowed in [
            (indices, data["source_units"]),
            (evidence, data["record_evidence_units"]),
        ]:
            check(
                type(values) is list
                and all(type(i) is int and 0 <= i < len(allowed) for i in values)
                and len(values) == len(set(values)),
                "Unknown, duplicated or noninteger reference index",
            )
        expanded["records"].append(
            {
                "record_id": data["record"]["record_id"],
                "verdict": parsed["verdict"],
                "origin": parsed["origin"],
                "source_quotes": [
                    {k: data["source_units"][i][k] for k in ("artifact_id", "quote")}
                    for i in indices
                ],
                "evidence_quote": data["record_evidence_units"][evidence[0]]["quote"]
                if evidence
                else "",
                "rationale": parsed["reason"],
            }
        )
    else:
        check(job["kind"] == "question", "Unknown follow-up job type")
        check(
            set(parsed) == {"checks", "reason"}
            and type(parsed["checks"]) is list
            and len(parsed["checks"]) == 5,
            "Unexpected single-question fields",
        )
        expanded["questions"].append(
            {
                "candidate_id": data["question"]["candidate_id"],
                **dict(zip(QA_KEYS, parsed["checks"], strict=True)),
                "rationale": parsed["reason"],
            }
        )
    original_job = {
        **job,
        "request": {
            **job["request"],
            "messages": [
                job["request"]["messages"][0],
                {"role": "user", "content": json.dumps(job["validation_view"], ensure_ascii=False)},
            ],
        },
    }
    proposal = validate(original_job, {**response, "text": json.dumps(expanded)})
    proposal.update(
        schema=SCHEMA,
        status="automated_single_item",
        AI_assessed_bundle="not_assessed_in_partial_item",
        whole_bundle_complete=False,
        replaces_failed_batch=job["replaces_failed_batch"],
    )
    return proposal


class FollowupSession(AnnotationSession):
    def authorize(self, plan):
        cfg, jobs = verify(plan)
        check(
            cfg["session_id"] == self.config["session_id"]
            and Path(cfg["session_directory"]).resolve() == self.directory,
            "Follow-up cannot switch the shared allowance",
        )
        self.jobs = {j["call_id"]: j for j in jobs}
        check(len(self.jobs) == len(jobs), "Repeated follow-up request")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS annotation_native_responses "
            "(call_id TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        return cfg


def verify_results(out):
    lock = json.loads((out / "results_manifest.json").read_text())
    check(lock["hash"] == digest(lock["files"]), "Follow-up result manifest changed")
    for name, expected in lock["files"].items():
        check(
            (out / name).resolve().is_relative_to(out.resolve())
            and sha_file(out / name) == expected,
            "Follow-up output changed",
        )


def finish(out, cfg, jobs, responses, session):
    _cfg, parents, reused, _failed = completed_parent(Path(cfg["parent_review"]))
    new, failures = [], []
    for j, r in zip(jobs, responses, strict=False):
        try:
            check(not r["error"], "Follow-up transport/billing error")
            new.append(decode(j, r["response"]))
        except (ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
            failures.append(
                {
                    "call_id": j["call_id"],
                    "contribution_id": j["contribution_id"],
                    "kind": j["kind"],
                    "reason": str(exc),
                    "type": type(exc).__name__,
                }
            )
    proposals = [*reused, *new]
    rows = [r for p in proposals for r in p["records"]]
    questions = [q for p in proposals for q in p["questions"]]
    check(len(rows) == len({r["record_id"] for r in rows}), "Repeated merged memory vote")
    check(
        len(questions) == len({q["candidate_id"] for q in questions}),
        "Repeated merged question assessment",
    )
    expected, seen = defaultdict(set), defaultdict(list)
    for j in parents:
        expected[j["contribution_id"]].update(j["record_versions"])
    for p in proposals:
        seen[p["contribution_id"]].extend(p["records"])
    bundles = []
    for pid, ids in expected.items():
        complete = {r["record_id"] for r in seen[pid]} == ids
        bundles.append(
            {
                "contribution_id": pid,
                "complete_automated_record_coverage": complete,
                "AI_assessed_bundle": bundle_verdict(seen[pid]) if complete else "incomplete",
                "human_validated": False,
                "eligible_as_gold": False,
            }
        )
    total = sum(
        (Decimal(r["actual_paid_usd"]) for r in responses if r["actual_paid_usd"] is not None),
        Decimal(0),
    )
    summary = {
        "schema": SCHEMA,
        "status": "automated_followup_complete"
        if len(responses) == len(jobs) and not failures
        else "automated_followup_partial",
        "planned_requests": len(jobs),
        "responses_received": len(responses),
        "accepted_followup_items": len(new),
        "rejected_followup_items": len(failures),
        "previous_accepted_records_reused": sum(len(p["records"]) for p in reused),
        "previous_accepted_questions_reused": sum(len(p["questions"]) for p in reused),
        "memory_records_in_scope": sum(map(len, expected.values())),
        "mechanically_valid_record_proposals": len(rows),
        "record_verdict_counts": dict(Counter(r["verdict"] for r in rows)),
        "record_origin_counts": dict(Counter(r["origin"] for r in rows)),
        "complete_automated_bundles": sum(b["complete_automated_record_coverage"] for b in bundles),
        "AI_assessed_bundle_counts": dict(Counter(b["AI_assessed_bundle"] for b in bundles)),
        "question_proposals_checked": len(questions),
        "AI_accepted_question_drafts": sum(all(q[k] is True for k in QA_KEYS) for q in questions),
        "followup_actual_cost_usd": str(total),
        "shared_project_budget": session.summary()["budget"],
        "human_verified_labels": 0,
        "human_validated_questions": 0,
        "scientific_pilot_ready": False,
        "automatic_gold_or_trust_update": False,
        "annotation_accuracy": "not_measured",
        "defense_ASR": "not_measured",
        "versions_are_independent_reviewers": False,
    }
    with (out / "automated_proposals.jsonl").open("x") as f:
        for p in proposals:
            f.write(canonical(p) + "\n")
    (out / "automated_proposals.jsonl").chmod(0o600)
    for name, value in [
        ("automated_bundles.json", bundles),
        ("review_failures.json", failures),
        ("summary.json", summary),
    ]:
        new_json(out / name, value)
    files = {
        n: sha_file(out / n)
        for n in (
            "automated_proposals.jsonl",
            "automated_bundles.json",
            "review_failures.json",
            "summary.json",
        )
    }
    new_json(out / "results_manifest.json", {"files": files, "hash": digest(files)})
    return summary


def run(out, mock_transport=None):
    cfg, jobs = verify(out)
    if (out / "results_manifest.json").exists():
        verify_results(out)
        return json.loads((out / "summary.json").read_text())
    directory = out / "responses"
    directory.mkdir(mode=0o700, exist_ok=True)
    with FollowupSession(Path(cfg["session_directory"])) as session:
        if mock_transport is None:
            load_env()
            key = os.environ.get("OPENROUTER_API_KEY")
            check(bool(key), "Missing OpenRouter credential")
            session.arm_annotation(out, key)
            target = out / "provider_preflight.json"
            if not target.exists():
                new_json(target, session.provider_preflight)
        else:
            session.arm_annotation_mock(out, mock_transport)
        responses = []
        for i, job in enumerate(jobs, 1):
            r = session.complete_review(job)
            target = directory / (job["call_id"] + ".json")
            if target.exists():
                check(json.loads(target.read_text()) == r, "Saved follow-up differs from dispatch")
            else:
                new_json(target, r)
            responses.append(r)
            if i % 10 == 0 or i == len(jobs):
                print(
                    f"Follow-up {i}/{len(jobs)} saved; combined project charge "
                    f"${session.guard.snapshot()['used_usd']:.6f}",
                    flush=True,
                )
            if r["error"]:
                break
        return finish(out, cfg, jobs, responses, session)
