"""One fresh confirmation after development-only deterministic span mapping."""

from __future__ import annotations

import copy
import json
import os
import re
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
from . import calibration_v2 as previous
from .whitespace_alignment import VERSION as ALIGNMENT_VERSION
from .whitespace_alignment import align

VERSION = "reference_blind_checker_fresh_confirmation_v3"


def fresh_cases():
    rows = copy.deepcopy(base.corpus("validation"))
    weekdays = ["Sunday", "Tuesday", "Thursday"]
    for row in rows:
        i = next(
            i
            for i in range(3)
            if row["case_id"] == "cc_" + digest([base.VERSION, "validation", row["family"], i])[:24]
        )
        entity = "Note-" + digest([20261101, VERSION, row["family"], i])[:10]
        mapping = {
            "Turin": "Tartu",
            "Kyoto": "Bergen",
            "Nantes": "Graz",
            "Perth": "Nancy",
            "7.3\u00a0kg": "9.6\u2009MB",
            "7.3 kg": "9.6 MB",
            "7.3 g": "9.6 Mb",
        }

        def replace(text, entity=entity, mapping=mapping):
            text = re.sub(r"Note-[0-9a-f]{10}", entity, text)
            for a, b in mapping.items():
                text = text.replace(a, b)
            return text

        for field in ["source", "memory", "question"]:
            row[field] = replace(row[field])
        row["aliases"] = [replace(a) for a in row["aliases"]]
        if row["family"] == "indirect":
            row["question"] = row["question"].replace(
                "day immediately after", "day immediately before"
            )
            row["source"] = row["memory"] = f"The {entity} handoff is on {weekdays[i]}."
            row["aliases"] = [weekdays[i]]
        row["split"] = "fresh_confirmation"
        row["case_id"] = "cf_" + digest([VERSION, row["family"], i])[:24]
    return rows


def parents_data(parent, decoder):
    cfg, jobs, rows, links = base.verify_study(parent)
    verify_results(parent)
    _, validation_jobs, _, _, _ = previous.verify_plan(decoder)
    verify_results(decoder)
    summary = json.loads((decoder / "summary.json").read_text())
    check(
        not summary["certificate_issued"]
        and summary["validation_requests"] == len(validation_jobs),
        "Fresh redesign requires the preserved failed completed predecessor",
    )
    votes = {}
    dependencies = []
    with sqlite3.connect(
        (Path(cfg["session_directory"]) / "dispatch.sqlite").as_uri() + "?mode=ro", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        for j in jobs:
            folder = parent if j["split"] == "development" else decoder
            file = folder / "responses" / (j["call_id"] + ".json")
            result = json.loads(file.read_text())
            durable = db.execute(
                "SELECT * FROM dispatches WHERE call_id=?", (j["call_id"],)
            ).fetchone()
            check(
                durable
                and durable["status"] == "completed"
                and dispatch_hash(durable, result) == durable["result_hash"]
                and json.loads(durable["result"]) == result,
                "Response provenance mismatch",
            )
            check(
                not result["error"]
                and result["response"]["raw_finish_reason"] == "stop"
                and result["dispatch"]["receipt"]["state"] == "settled",
                "Only complete settled replies can be development data",
            )
            dependencies.append(file)
            v = {"valid": False, "call_id": j["call_id"]}
            try:
                raw = strict_json(result["response"]["text"])
                body = json.loads(j["request"]["messages"][1]["content"])
                extraction, proof = align(j["checker_task"], body, raw)
                v.update(valid=True, extraction=extraction, alignment=proof)
            except (ValueError, TypeError, KeyError) as error:
                v["error"] = str(error)
            votes[j["call_id"]] = v
    reports = {
        split: base.evaluate([r for r in rows if r["split"] == split], links, votes)
        for split in ["development", "validation"]
    }
    check(
        all(r["passed"] for r in reports.values()),
        "Consumed development sets still fail; no new confirmation",
    )
    return cfg, jobs, rows, reports, votes, dependencies


def prepare(repo, parent, decoder, out):
    cfg, oldjobs, oldrows, reports, votes, responses = parents_data(parent, decoder)
    rows = fresh_cases()
    jobs, links = base.make_jobs(rows)
    check(
        {(r["source"], r["memory"], r["question"]) for r in rows}.isdisjoint(
            (r["source"], r["memory"], r["question"]) for r in oldrows
        ),
        "Reused confirmation example",
    )
    check(
        {j["call_id"] for j in jobs}.isdisjoint(j["call_id"] for j in oldjobs),
        "Reused model request",
    )
    with sqlite3.connect(
        (Path(cfg["session_directory"]) / "dispatch.sqlite").as_uri() + "?mode=ro", uri=True
    ) as db:
        check(
            all(
                db.execute("SELECT 1 FROM dispatches WHERE call_id=?", (j["call_id"],)).fetchone()
                is None
                for j in jobs
            ),
            "Fresh confirmation has already been consumed",
        )
    result = freeze(
        out,
        {
            "kind": VERSION,
            "session_id": cfg["session_id"],
            "session_directory": cfg["session_directory"],
            "parent_plan": str(parent.resolve()),
            "previous_decoder_plan": str(decoder.resolve()),
            "alignment_version": ALIGNMENT_VERSION,
            "thresholds": base.THRESHOLDS,
            "attempts": 1,
            "calibration_entry_nanodollars": base.ENTRY_NANODOLLARS,
            "calibration_cap_nanodollars": base.CALIBRATION_CAP_NANODOLLARS,
            "may_promote_questions": False,
            "working_estimate_usd": ["0.01", "0.04"],
        },
        jobs,
        [
            Path(__file__),
            Path(__file__).with_name("whitespace_alignment.py"),
            repo / "scripts/confirm_question_checker.py",
            repo / "reports/QUESTION_CHECKER_CALIBRATION_20261101_FRESH_CONFIRMATION.md",
            parent / "review_manifest.json",
            parent / "results_manifest.json",
            decoder / "review_manifest.json",
            decoder / "results_manifest.json",
            *responses,
        ],
    )
    new_json(out / "fresh_cases.json", rows)
    new_json(out / "assignments.json", links)
    new_json(
        out / "development_recheck.json",
        {
            "consumed_sets_are_development_only": True,
            "results": reports,
            "votes": votes,
            "new_API_calls": 0,
        },
    )
    new_json(
        out / "constructed_manifest.json",
        {
            n: sha_file(out / n)
            for n in ["fresh_cases.json", "assignments.json", "development_recheck.json"]
        },
    )
    return result


def verify_plan(plan):
    cfg, jobs = verify(plan)
    check(
        cfg["kind"] == VERSION
        and cfg["alignment_version"] == ALIGNMENT_VERSION
        and cfg["attempts"] == 1,
        "Wrong final checker version",
    )
    check(
        cfg["thresholds"] == base.THRESHOLDS
        and cfg["calibration_entry_nanodollars"] == base.ENTRY_NANODOLLARS
        and cfg["calibration_cap_nanodollars"] == base.CALIBRATION_CAP_NANODOLLARS,
        "Changed final gates or budget",
    )
    check(cfg["may_promote_questions"] is False, "Calibration cannot authorize real annotation")
    for n, h in json.loads((plan / "constructed_manifest.json").read_text()).items():
        check(sha_file(plan / n) == h, "Changed fresh corpus or development report")
    rows = json.loads((plan / "fresh_cases.json").read_text())
    links = json.loads((plan / "assignments.json").read_text())
    newjobs, newlinks = base.make_jobs(fresh_cases())
    check(
        rows == fresh_cases() and canonical(jobs) == canonical(newjobs) and links == newlinks,
        "Changed fresh confirmation tasks",
    )
    return cfg, jobs, rows, links


def run(plan):
    cfg, jobs, rows, links = verify_plan(plan)
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
            "Budget entry mismatch",
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
                check(json.loads(file.read_text()) == r, "Changed fresh response")
            else:
                new_json(file, r)
            v = {"valid": False, "call_id": j["call_id"]}
            try:
                check(
                    not r["error"] and r["response"]["raw_finish_reason"] == "stop",
                    "Incomplete fresh request/billing",
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
                    f"Fresh checker confirmation {i}/{len(jobs)}; "
                    f"project ${session.guard.snapshot()['used_usd']:.6f}",
                    flush=True,
                )
            if r["error"]:
                break
        budget = session.guard.snapshot()
    result = base.evaluate(rows, links, votes)
    passed = result["passed"] and not budget_stopped
    new_json(plan / "confirmation_votes.json", votes)
    new_json(plan / "confirmation_results.json", result)
    if passed:
        new_json(
            plan / "checker_certificate.json",
            {
                "checker_version": VERSION,
                "scope": "constructed_reference_support_and_question_exposure_only",
                "fresh_confirmation_passed": True,
                "previous_failed_validation_reused_as_development": True,
                "MPBench_validated": False,
                "human_validated": False,
                "may_promote_questions": False,
                "defense_execution_enabled": False,
            },
        )
    unknown = sum(r["actual_paid_usd"] is None for r in responses)
    known = str(sum((Decimal(r["actual_paid_usd"] or "0") for r in responses), Decimal(0)))
    summary = {
        "status": "fresh_constructed_confirmation_passed"
        if passed
        else (
            "fresh_confirmation_budget_stopped" if budget_stopped else "fresh_confirmation_failed"
        ),
        "checker_version": VERSION,
        "certificate_issued": passed,
        "fresh_requests": len(responses),
        "planned_requests": len(jobs),
        "actual_new_cost_usd": None if unknown else known,
        "known_paid_cost_usd": known,
        "unknown_cost_requests": unknown,
        "reused_development_responses": 108,
        "new_development_calls": 0,
        "budget": budget,
        "uses_MPBench": False,
        "questions_promoted": 0,
        "human_verified_labels": 0,
        "human_validated_questions": 0,
        "defense_experiments": 0,
    }
    new_json(plan / "summary.json", summary)
    with (plan / "automated_proposals.jsonl").open("x"):
        pass
    (plan / "automated_proposals.jsonl").chmod(0o600)
    names = [
        "confirmation_votes.json",
        "confirmation_results.json",
        "summary.json",
        "automated_proposals.jsonl",
    ] + (["checker_certificate.json"] if passed else [])
    files = {n: sha_file(plan / n) for n in names}
    new_json(plan / "results_manifest.json", {"files": files, "hash": digest(files)})
    return summary
