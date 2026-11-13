"""Develop one exact quote decoder on development; validate once without tuning."""

from __future__ import annotations

import json
import os
import sqlite3
from decimal import Decimal
from pathlib import Path

from ams.core.env import load_env
from ams.research.dynamic.models import canonical, check, digest
from ams.research.execution.session import dispatch_hash, new_json
from ams.research.llm_followup.pipeline import verify_results
from ams.research.llm_review.validation import strict_json
from ams.research.pilot_finish.reviewer import StructuredSDK, StructuredSession, freeze, verify
from ams.research.recovery.offline import sha_file

from . import calibration as base
from .quote_alignment import VERSION as ALIGNMENT_VERSION
from .quote_alignment import align

VERSION = "reference_blind_checker_quote_decoder_v2"


def parent_data(parent):
    cfg, jobs, rows, links = base.verify_study(parent)
    verify_results(parent)
    summary = json.loads((parent / "summary.json").read_text())
    check(
        summary["splits_run"] == ["development"] and not summary["certificate_issued"],
        "Parent validation must remain unused",
    )
    return cfg, jobs, rows, links, summary


def saved_development(parent, cfg, jobs):
    votes = {}
    dependencies = []
    dbpath = Path(cfg["session_directory"]) / "dispatch.sqlite"
    with sqlite3.connect(dbpath.as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        for j in jobs:
            row = db.execute("SELECT * FROM dispatches WHERE call_id=?", (j["call_id"],)).fetchone()
            if j["split"] == "validation":
                check(row is None, "Validation has already been used; no retuning on test outputs")
                continue
            check(
                row is not None and row["status"] == "completed",
                "Missing durable development reply",
            )
            result = json.loads(row["result"])
            check(dispatch_hash(row, result) == row["result_hash"], "Changed development dispatch")
            file = parent / "responses" / (j["call_id"] + ".json")
            check(
                json.loads(file.read_text()) == result,
                "Saved response differs from durable response",
            )
            check(
                result["error"] is None and result["dispatch"]["receipt"]["state"] == "settled",
                "Only complete settled responses can be reused",
            )
            check(
                result["response"] and result["response"]["raw_finish_reason"] == "stop",
                "Incomplete development response cannot enter a decoder amendment",
            )
            dependencies.append(file)
            v = {"valid": False, "call_id": j["call_id"]}
            try:
                raw = strict_json(result["response"]["text"])
                body = json.loads(j["request"]["messages"][1]["content"])
                extraction, proof = align(j["checker_task"], body, raw)
                v.update(valid=True, extraction=extraction, alignment=proof)
            except (ValueError, TypeError, KeyError) as e:
                v["error"] = str(e)
            votes[j["call_id"]] = v
    return votes, dependencies


def prepare(repo, parent, out):
    cfg, jobs, rows, links, summary = parent_data(parent)
    votes, responses = saved_development(parent, cfg, jobs)
    result = base.evaluate([r for r in rows if r["split"] == "development"], links, votes)
    check(result["passed"], "Decoder-adjusted development still fails; validation remains unused")
    selected = [j for j in jobs if j["split"] == "validation"]
    check(len(selected) == 54, "Unexpected validation request inventory")
    frozen = freeze(
        out,
        {
            "kind": VERSION,
            "session_id": cfg["session_id"],
            "session_directory": cfg["session_directory"],
            "parent_plan": str(parent.resolve()),
            "alignment_version": ALIGNMENT_VERSION,
            "thresholds": base.THRESHOLDS,
            "calibration_entry_nanodollars": base.ENTRY_NANODOLLARS,
            "calibration_cap_nanodollars": base.CALIBRATION_CAP_NANODOLLARS,
            "attempts": 1,
            "may_promote_questions": False,
            "development_new_calls": 0,
            "working_estimate_usd": ["0.01", "0.04"],
        },
        selected,
        [
            Path(__file__),
            Path(__file__).with_name("quote_alignment.py"),
            repo / "scripts/validate_question_checker.py",
            repo / "reports/QUESTION_CHECKER_CALIBRATION_20261101_QUOTE_AMENDMENT.md",
            parent / "review_manifest.json",
            parent / "results_manifest.json",
            parent / "constructed_manifest.json",
            parent / "constructed_cases.json",
            parent / "assignments.json",
            *responses,
        ],
    )
    new_json(
        out / "development_recheck.json",
        {
            "result": result,
            "votes": votes,
            "new_API_calls": 0,
            "new_API_cost_usd": "0",
            "parent_original_cost_usd": summary["actual_cost_usd"],
        },
    )
    new_json(
        out / "development_manifest.json",
        {"development_recheck_sha256": sha_file(out / "development_recheck.json")},
    )
    return frozen


def verify_plan(plan):
    cfg, jobs = verify(plan)
    check(
        cfg["kind"] == VERSION
        and cfg["alignment_version"] == ALIGNMENT_VERSION
        and cfg["attempts"] == 1,
        "Wrong decoder calibration version",
    )
    check(
        cfg["thresholds"] == base.THRESHOLDS
        and cfg["calibration_entry_nanodollars"] == base.ENTRY_NANODOLLARS
        and cfg["calibration_cap_nanodollars"] == base.CALIBRATION_CAP_NANODOLLARS,
        "Changed gates/budget",
    )
    check(cfg["may_promote_questions"] is False, "Calibration cannot promote a question")
    parent = Path(cfg["parent_plan"])
    _, alljobs, rows, links, summary = parent_data(parent)
    check(
        canonical(jobs) == canonical([j for j in alljobs if j["split"] == "validation"]),
        "Changed validation prompts or jobs",
    )
    h = json.loads((plan / "development_manifest.json").read_text())["development_recheck_sha256"]
    check(sha_file(plan / "development_recheck.json") == h, "Changed offline development recheck")
    check(
        json.loads((plan / "development_recheck.json").read_text())["result"]["passed"],
        "Development must pass before validation",
    )
    return cfg, jobs, rows, links, summary


def run(plan):
    cfg, jobs, rows, links, parent_summary = verify_plan(plan)
    if (plan / "results_manifest.json").exists():
        verify_results(plan)
        return json.loads((plan / "summary.json").read_text())
    (plan / "responses").mkdir(mode=0o700, exist_ok=True)
    votes = {}
    responses = []
    budget_stopped = False
    with StructuredSession(Path(cfg["session_directory"])) as session:
        load_env()
        session.arm_annotation(plan, os.environ["OPENROUTER_API_KEY"])
        session._sdk = StructuredSDK(session._sdk, session)
        check(
            session.mode == "mock"
            or session.guard.snapshot()["used_nanodollars"] >= base.ENTRY_NANODOLLARS,
            "Session spending predates calibration entry",
        )
        if not (plan / "provider_preflight.json").exists():
            new_json(plan / "provider_preflight.json", session.provider_preflight)
        for i, j in enumerate(jobs, 1):
            known = session.db.execute(
                "SELECT 1 FROM dispatches WHERE call_id=?", (j["call_id"],)
            ).fetchone()
            if (
                not known
                and session.guard.snapshot()["used_nanodollars"]
                - base.ENTRY_NANODOLLARS
                + base.RESERVATION_NANODOLLARS
                > base.CALIBRATION_CAP_NANODOLLARS
            ):
                budget_stopped = True
                break
            r = session.complete_review(j)
            responses.append(r)
            file = plan / "responses" / (j["call_id"] + ".json")
            if file.exists():
                check(json.loads(file.read_text()) == r, "Saved validation reply changed")
            else:
                new_json(file, r)
            v = {"valid": False, "call_id": j["call_id"]}
            try:
                check(
                    not r["error"] and r["response"]["raw_finish_reason"] == "stop",
                    "Incomplete validation request/billing",
                )
                body = json.loads(j["request"]["messages"][1]["content"])
                raw = strict_json(r["response"]["text"])
                extraction, proof = align(j["checker_task"], body, raw)
                v.update(valid=True, extraction=extraction, alignment=proof)
            except (ValueError, KeyError, TypeError) as error:
                v["error"] = str(error)
            votes[j["call_id"]] = v
            if i % 10 == 0 or i == len(jobs):
                print(
                    f"Checker locked validation {i}/{len(jobs)}; "
                    f"project ${session.guard.snapshot()['used_usd']:.6f}",
                    flush=True,
                )
            if r["error"]:
                break
        budget = session.guard.snapshot()
    result = base.evaluate([r for r in rows if r["split"] == "validation"], links, votes)
    passed = result["passed"] and not budget_stopped
    new_json(plan / "validation_votes.json", votes)
    new_json(plan / "validation_results.json", result)
    if passed:
        new_json(
            plan / "checker_certificate.json",
            {
                "checker_version": VERSION,
                "scope": "constructed_support_and_leakage_checks_only",
                "development_and_validation_passed": True,
                "development_decoder_revised_before_validation": True,
                "MPBench_validated": False,
                "human_validated": False,
                "may_promote_questions": False,
                "defense_execution_enabled": False,
            },
        )
    unknown = sum(r["actual_paid_usd"] is None for r in responses)
    known = str(sum((Decimal(r["actual_paid_usd"] or "0") for r in responses), Decimal(0)))
    summary = {
        "status": "constructed_validation_passed"
        if passed
        else ("validation_budget_stopped" if budget_stopped else "validation_failed"),
        "checker_version": VERSION,
        "validation_passed": passed,
        "certificate_issued": passed,
        "validation_requests": len(responses),
        "planned_requests": len(jobs),
        "actual_new_cost_usd": None if unknown else known,
        "known_paid_cost_usd": known,
        "unknown_cost_requests": unknown,
        "reused_development_calls": 54,
        "new_development_calls": 0,
        "historical_development_cost_usd": parent_summary["actual_cost_usd"],
        "budget": budget,
        "uses_MPBench": False,
        "human_verified_labels": 0,
        "human_validated_questions": 0,
        "questions_promoted": 0,
        "defense_experiments": 0,
    }
    new_json(plan / "summary.json", summary)
    with (plan / "automated_proposals.jsonl").open("x"):
        pass
    (plan / "automated_proposals.jsonl").chmod(0o600)
    names = [
        "validation_votes.json",
        "validation_results.json",
        "summary.json",
        "automated_proposals.jsonl",
    ] + (["checker_certificate.json"] if passed else [])
    files = {n: sha_file(plan / n) for n in names}
    new_json(plan / "results_manifest.json", {"files": files, "hash": digest(files)})
    return summary
