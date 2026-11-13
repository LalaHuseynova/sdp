#!/usr/bin/env python3
"""Versioned whitespace-only support recovery; no semantic paraphrase or new calls."""

import argparse
import json
import re
from pathlib import Path

from ams.research.dynamic.models import canonical, check, digest
from ams.research.execution.session import new_json
from ams.research.llm_followup.pipeline import verify_results
from ams.research.llm_review.validation import strict_json
from ams.research.pilot_finish.reviewer import verify
from ams.research.recovery.offline import no_network, sha_file


def normalized_with_spans(text):
    chars, spans = [], []
    for token in re.finditer(r"\S+|\s+", text):
        if token.group().isspace():
            if chars:
                chars.append(" ")
                spans.append((token.start(), token.end()))
        else:
            for i, c in enumerate(token.group(), token.start()):
                chars.append(c)
                spans.append((i, i + 1))
    if chars and chars[-1] == " ":
        chars.pop()
        spans.pop()
    return "".join(chars), spans


def find_normalized(text, answer):
    needle, _ = normalized_with_spans(answer)
    haystack, spans = normalized_with_spans(text)
    check(bool(needle), "Empty answer is not support")
    index = haystack.find(needle)
    if index < 0:
        return None
    return spans[index][0], spans[index + len(needle) - 1][1]


def recover(plans, out):
    check(not out.exists(), "Formatting-recovery version exists")
    proposals = []
    rejected = []
    seen = set()
    for plan in plans:
        _cfg, jobs = verify(plan)
        verify_results(plan)
        failed = {x["call_id"] for x in json.loads((plan / "review_failures.json").read_text())}
        for job in jobs:
            if (
                job.get("kind") != "generate"
                or job["call_id"] not in failed
                or job["call_id"] in seen
            ):
                continue
            seen.add(job["call_id"])
            raw = json.loads((plan / "responses" / (job["call_id"] + ".json")).read_text())
            body = strict_json(raw["response"]["text"])
            try:
                check(body["possible"] is True, "No candidate was proposed")
                memory = job["references"]["records"][body["record_ref"]]
                source = job["references"]["sources"][body["source_ref"]]
                am = find_normalized(memory["text"], body["answer"])
                ass = find_normalized(source["quote"], body["answer"])
                check(am is not None and ass is not None, "Not a whitespace-only support mismatch")
                check(
                    find_normalized(body["question"], body["answer"]) is None,
                    "Question gives the answer",
                )
                aliases = list(
                    dict.fromkeys(
                        [
                            body["answer"],
                            memory["text"][am[0] : am[1]],
                            source["quote"][ass[0] : ass[1]],
                        ]
                    )
                )
                candidate = {
                    "candidate_id": "qnorm_" + digest([job["call_id"], body])[:24],
                    "contribution_id": job["contribution_id"],
                    "question": body["question"],
                    "answers": aliases,
                    "support_record_id": memory["record_id"],
                    "support_record_kind": "claim",
                    "support_artifact_id": source["artifact_id"],
                    "quote": source["quote"],
                    "start": source["start"],
                    "end": source["end"],
                    "source_safety_status": "AI_proposed_only",
                    "human_validated": False,
                    "eligible_as_gold": False,
                    "validation_status": "pending_AI_check",
                    "format_normalization": "whitespace-only; other characters preserved",
                    "supporting_answer_span_in_record": {"start": am[0], "end": am[1]},
                    "supporting_answer_span_in_artifact": {
                        "start": source["start"] + ass[0],
                        "end": source["start"] + ass[1],
                    },
                    "supersedes_candidate_ids": job["supersedes_candidate_ids"],
                }
                proposals.append(
                    {
                        "annotation_source": "llm",
                        "human_validated": False,
                        "independent_human_review": False,
                        "eligible_as_gold": False,
                        "can_update_live_trust": False,
                        "records": [],
                        "questions": [],
                        "contribution_id": job["contribution_id"],
                        "call_id": job["call_id"],
                        "candidate_question": candidate,
                        "originating_response_sha256": sha_file(
                            plan / "responses" / (job["call_id"] + ".json")
                        ),
                    }
                )
            except (ValueError, TypeError, KeyError) as e:
                rejected.append({"call_id": job["call_id"], "reason": str(e)})
    out.mkdir(parents=True, mode=0o700)
    with (out / "automated_proposals.jsonl").open("x") as f:
        for p in proposals:
            f.write(canonical(p) + "\n")
    (out / "automated_proposals.jsonl").chmod(0o600)
    summary = {
        "formatting_recoveries": len(proposals),
        "other_failures_left_rejected": len(rejected),
        "new_API_calls": 0,
        "new_API_cost_usd": "0",
        "human_validated_questions": 0,
        "question_semantic_validation": "pending_explicit_presence_QA",
        "record_safety_labels_changed": 0,
        "original_source_texts_changed": 0,
    }
    new_json(out / "summary.json", summary)
    new_json(out / "remaining_failures.json", rejected)
    files = {
        n: sha_file(out / n)
        for n in ["automated_proposals.jsonl", "summary.json", "remaining_failures.json"]
    }
    new_json(
        out / "results_manifest.json",
        {"files": files, "hash": digest(files), "algorithm_sha256": sha_file(Path(__file__))},
    )
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plans", type=Path, nargs="+", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    with no_network():
        r = recover(a.plans, a.out)
    print(json.dumps(r, indent=2))
