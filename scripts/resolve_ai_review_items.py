#!/usr/bin/env python3
"""Preserve individually valid saved items and freeze explicit failed-item reviews."""

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from pathlib import Path

from ams.research.dynamic.models import canonical, check, digest
from ams.research.execution.session import new_json, prompt_measurement
from ams.research.llm_followup.pipeline import verify_results
from ams.research.llm_review.validation import strict_json
from ams.research.pilot_finish.reviewer import (
    SCHEMA,
    decode,
    freeze,
    obj,
    request_job,
    verify,
)
from ams.research.recovery.offline import no_network, sha_file
from ams.research.sequential.clients import request_from


def paired_attribution(job):
    job = copy.deepcopy(job)
    schema = job["response_schema"]
    sources = job["references"]["sources"]
    for role in ("principal", "external"):
        allowed = [k for k, s in sources.items() if s["role"] == role]
        if allowed:
            schema["$defs"][role + "_source_ref"] = {"type": "string", "enum": allowed}
    for mid in job["references"]["records"]:
        original = schema["properties"][mid]["properties"]
        optional = original["evidence_ref"]
        allowed_evidence = [v for v in optional["enum"] if v is not None]
        schema["$defs"]["optional_" + mid] = optional
        if allowed_evidence:
            schema["$defs"]["required_" + mid] = {"type": "string", "enum": allowed_evidence}
        branches = []
        for role in ("principal", "external", "ambiguous"):
            if role != "ambiguous" and role + "_source_ref" not in schema["$defs"]:
                continue
            for verdict in ("safe_for_use", "unsafe", "uncertain"):
                if verdict == "unsafe" and not allowed_evidence:
                    continue
                fields = {
                    **original,
                    "origin": {"type": "string", "enum": [role]},
                    "verdict": {"type": "string", "enum": [verdict]},
                    "evidence_ref": {
                        "$ref": "#/$defs/"
                        + ("required_" if verdict == "unsafe" else "optional_")
                        + mid
                    },
                }
                if role != "ambiguous":
                    fields["source_ref"] = {"$ref": "#/$defs/" + role + "_source_ref"}
                branches.append(obj(fields))
        schema["properties"][mid] = {"anyOf": branches}
    job["request"]["messages"][0]["content"] = (
        job["request"]["messages"][0]["content"].split("\nExact output schema:\n")[0]
        + "\nOrigin and source reference must be jointly consistent; unclear origin is ambiguous."
        + "\nExact output schema:\n"
        + canonical(schema)
    )
    key = request_from("chat", job["request"]).cache_key("openrouter")
    req = request_from("chat", job["request"])
    check(
        prompt_measurement(req)["input_token_proxy"] + req.max_tokens < 128000,
        "Paired schema makes input too large; no dispatch",
    )
    job["request_key"] = key
    job["call_id"] = digest([SCHEMA, key])
    return job


def single_item(job, alias, question):
    j = copy.deepcopy(job)
    refs = j["references"]
    if question:
        cid = refs["questions"][alias]
        refs["records"] = {}
        refs["evidence"] = {}
        refs["questions"] = {alias: cid}
        j["record_versions"] = {}
        j["candidate_versions"] = {cid: j["candidate_versions"][cid]}
        j["validation_view"]["records"] = []
        j["validation_view"]["questions"] = [
            q for q in j["validation_view"]["questions"] if q["candidate_id"] == cid
        ]
    else:
        rid = refs["records"][alias]
        refs["records"] = {alias: rid}
        refs["questions"] = {}
        refs["evidence"] = {alias: refs["evidence"][alias]}
        j["record_versions"] = {rid: j["record_versions"][rid]}
        j["candidate_versions"] = {}
        j["validation_view"]["records"] = [
            r for r in j["validation_view"]["records"] if r["record_id"] == rid
        ]
        j["validation_view"]["questions"] = []
    return j


def resolve(parent, out):
    check(not out.exists(), "Resolution version exists")
    cfg, jobs = verify(parent)
    verify_results(parent)
    accepted, failures = [], []
    for job in jobs:
        path = parent / "responses" / (job["call_id"] + ".json")
        response = json.loads(path.read_text())
        body = strict_json(response["response"]["text"]) if response["response"] else {}
        for question, aliases in (
            (False, job["references"]["records"]),
            (True, job["references"]["questions"]),
        ):
            for alias in aliases:
                item = single_item(job, alias, question)
                try:
                    check(not response["error"] and alias in body, "Missing original response item")
                    p = decode(
                        item, {**response["response"], "text": canonical({alias: body[alias]})}
                    )
                    p.update(
                        validation_scope="single_saved_item_no_label_change",
                        originating_response_sha256=sha_file(path),
                    )
                    accepted.append(p)
                except (ValueError, KeyError, TypeError) as exc:
                    failures.append(
                        {
                            "job": item,
                            "alias": alias,
                            "question": question,
                            "reason": str(exc),
                            "raw_response": str(path.resolve()),
                        }
                    )
    out.mkdir(parents=True, mode=0o700)
    with (out / "automated_proposals.jsonl").open("x") as f:
        for p in accepted:
            f.write(canonical(p) + "\n")
    (out / "automated_proposals.jsonl").chmod(0o600)
    summary = {
        "status": "individual_saved_item_validation",
        "parent": str(parent.resolve()),
        "accepted_records": sum(len(p["records"]) for p in accepted),
        "accepted_questions": sum(len(p["questions"]) for p in accepted),
        "rejected_items": len(failures),
        "rejection_reasons": dict(Counter(f["reason"] for f in failures)),
        "new_API_calls": 0,
        "new_API_cost_usd": "0",
        "human_verified_labels": 0,
        "notice": "Same saved choices; valid neighbors retained; invalid roles remain rejected.",
    }
    new_json(out / "summary.json", summary)
    new_json(out / "pending_items.json", failures)
    files = {
        n: sha_file(out / n)
        for n in ["automated_proposals.jsonl", "summary.json", "pending_items.json"]
    }
    new_json(
        out / "results_manifest.json",
        {
            "files": files,
            "hash": digest(files),
            "algorithm_sha256": sha_file(Path(__file__)),
            "parent_results_manifest": sha_file(parent / "results_manifest.json"),
        },
    )
    return summary


def prepare_pending(resolved, parent, out):
    verify_results(resolved)
    cfg, _ = verify(parent)
    pending = json.loads((resolved / "pending_items.json").read_text())
    jobs = []
    for row in pending:
        old = row["job"]
        meta = {
            k: old[k]
            for k in [
                "contribution_id",
                "use_id",
                "packet_hash",
                "record_versions",
                "candidate_versions",
            ]
        }
        jobs.append(paired_attribution(request_job(old["validation_view"], meta)))
    return freeze(
        out,
        {
            "kind": "paired_attribution_rereview",
            "session_id": cfg["session_id"],
            "session_directory": cfg["session_directory"],
            "parent": str(resolved.resolve()),
            "prior_votes_visible": False,
        },
        jobs,
        [resolved / "results_manifest.json", parent / "review_manifest.json", Path(__file__)],
    )


def upgrade(parent, out):
    cfg, jobs = verify(parent)
    check(not (parent / "results_manifest.json").exists(), "Upgrade only an unrun new plan")
    return freeze(
        out,
        {**cfg, "contract": "paired_attribution_before_first_dispatch"},
        [paired_attribution(j) for j in jobs],
        [parent / "review_manifest.json", Path(__file__)],
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ["resolve", "upgrade"]:
        a = sub.add_parser(name)
        a.add_argument("--parent", type=Path, required=True)
        a.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("pending-plan")
    a.add_argument("--resolved", type=Path, required=True)
    a.add_argument("--parent", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    with no_network():
        if args.command == "resolve":
            result = resolve(args.parent, args.out)
        elif args.command == "upgrade":
            result = upgrade(args.parent, args.out)
        else:
            result = prepare_pending(args.resolved, args.parent, args.out)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
