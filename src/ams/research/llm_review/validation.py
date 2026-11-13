"""Mechanical validity of automated proposals, NOT accuracy or human agreement."""

from __future__ import annotations

import json

from ams.research.dynamic.models import check
from ams.research.phase1_annotations import bundle_verdict

QA_KEYS = (
    "supported_answer",
    "question_clear",
    "useful_for_task",
    "safe_descriptive_use",
    "no_answer_in_question",
)


def strict_json(text):
    def pairs(values):
        out = {}
        for k, v in values:
            check(k not in out, "Duplicate JSON field")
            out[k] = v
        return out

    body = text.strip()
    if body.startswith("```"):
        body = body.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(body, object_pairs_hook=pairs)


def validate(job, response):
    check(
        response is not None and response["raw_finish_reason"] not in {"length", "max_tokens"},
        "Missing/truncated reviewer response",
    )
    body = strict_json(response["text"])
    check(
        type(body) is dict and set(body) == {"records", "questions"}, "Unexpected review envelope"
    )
    data = json.loads(job["request"]["messages"][1]["content"])
    artifacts = {a["artifact_id"]: a for a in data["artifacts"]}
    original = {r["record_id"]: r for r in data["records"]}
    records = body["records"]
    check(
        type(records) is list
        and len(records) == len(original)
        and {r["record_id"] for r in records} == set(original),
        "Missing/repeated/unknown record IDs",
    )
    clean = []
    for row in records:
        check(
            set(row)
            == {"record_id", "verdict", "origin", "source_quotes", "evidence_quote", "rationale"},
            "Unexpected record-review fields",
        )
        check(
            row["verdict"] in {"safe_for_use", "unsafe", "uncertain"}
            and row["origin"] in {"principal", "external", "ambiguous"},
            "Invalid AI label/origin",
        )
        check(
            type(row["rationale"]) is str and row["rationale"].strip(), "Missing reviewer rationale"
        )
        spans = []
        check(type(row["source_quotes"]) is list, "Invalid source quote list")
        for quote in row["source_quotes"]:
            check(
                type(quote) is dict and set(quote) == {"artifact_id", "quote"},
                "Invalid quote fields",
            )
            artifact = artifacts.get(quote["artifact_id"])
            check(
                artifact is not None and type(quote["quote"]) is str and quote["quote"],
                "Missing source evidence",
            )
            if row["origin"] != "ambiguous":
                check(artifact["role"] == row["origin"], "Principal/external source role mismatch")
            start, matched = 0, 0
            while (index := artifact["text"].find(quote["quote"], start)) >= 0:
                end = index + len(quote["quote"])
                spans.append(
                    {
                        "artifact_id": quote["artifact_id"],
                        "start": index,
                        "end": end,
                        "quote": quote["quote"],
                    }
                )
                start, matched = index + 1, matched + 1
            check(matched > 0, "Quote is not an exact source substring")
        check(row["origin"] == "ambiguous" or spans, "Resolved origin needs source evidence")
        if row["verdict"] == "unsafe":
            check(
                type(row["evidence_quote"]) is str
                and row["evidence_quote"]
                and row["evidence_quote"] in original[row["record_id"]]["text"],
                "Unsafe label lacks record evidence",
            )
        clean.append(
            {
                **row,
                "content_hash": job["record_versions"][row["record_id"]],
                "source_spans": spans,
                "source_identity_authenticated": False,
            }
        )
    questions = body["questions"]
    check(
        type(questions) is list
        and len(questions) == len(job["candidate_versions"])
        and {q["candidate_id"] for q in questions} == set(job["candidate_versions"]),
        "Missing/repeated/unknown QA IDs",
    )
    for q in questions:
        check(set(q) == {"candidate_id", *QA_KEYS, "rationale"}, "Unexpected QA fields")
        check(all(type(q[k]) is bool or q[k] is None for k in QA_KEYS), "Invalid QA criterion")
        check(type(q["rationale"]) is str and q["rationale"].strip(), "QA rationale missing")
    return {
        "schema": "automated-memory-review-v1",
        "contribution_id": job["contribution_id"],
        "use_id": job["use_id"],
        "packet_hash": job["packet_hash"],
        "call_id": job["call_id"],
        "annotation_source": "llm",
        "independent_human_review": False,
        "human_validated": False,
        "eligible_as_gold": False,
        "can_update_live_trust": False,
        "status": "automated_proposal",
        "records": clean,
        "questions": questions,
        "AI_assessed_bundle": bundle_verdict(clean),
    }
