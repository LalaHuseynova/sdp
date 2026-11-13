"""Mechanical screening and versioning; no automatic ground-truth validation."""

from __future__ import annotations

import copy
import re
from collections import Counter

from ams.research.phase1_common import digest, opaque, require
from ams.research.phase1_data import normalized
from ams.research.recovery.annotation import draft_questions, validate_candidate


def quality_flags(candidate: dict) -> list[str]:
    q = candidate["question"]
    flags = []
    if any(normalized(a) in normalized(q) for a in candidate["answers"]):
        flags.append("answer_in_question")
    if "what description is given" in q.casefold():
        flags.append("broad_description_question")
    if any(len(a.split()) == 1 for a in candidate["answers"]):
        flags.append("short_reference_needs_context_review")
    if re.search(r"\b(?:no|not|never|all|every|none)\b", q, re.I):
        flags.append("negation_or_quantifier_needs_review")
    if candidate["support_record_kind"] != "claim":
        flags.append("external_chunk_blocked_by_frozen_baseline")
    if len(q) > 240:
        flags.append("long_question")
    return flags


def refined_question(candidate: dict, record: dict) -> str:
    q = candidate["question"]
    if candidate.get("generated_by") == "offline_existing_claim_clause_v1":
        m = re.match(r"^(.{3,100}?)\s+(is|are|was|were)\s+", record["text"].strip(), re.I)
        if m and not re.search(r"\b(?:no|not|never|none)\b", m.group(1), re.I):
            entity = re.sub(r"^The\b", "the", m.group(1))
            return f"According to the note, how {m.group(2).lower()} {entity} described?"
    return q


def literal_statement_questions(packet: dict, parents: dict) -> list[dict]:
    """Additional broad drafts only when a whole existing claim is literally sourced."""
    out = []
    for r in packet["records"]:
        if r["record_kind"] != "claim" or not 20 <= len(r["text"]) <= 220:
            continue
        source = next(
            (
                a
                for a in packet["artifacts"]
                if a["role"] == "external" and a["artifact_id"] == parents.get(r["record_id"])
            ),
            None,
        )
        if not source:
            continue
        lo = source["text"].find(r["text"])
        if lo < 0 or source["text"].find(r["text"], lo + 1) >= 0:
            continue
        entity = re.match(r"(?:The\s+)?[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,2}", r["text"])
        if not entity or entity.group(0).casefold() in {"the", "user", "unknown", "this", "it"}:
            continue
        question = f"According to the note, what is stated about {entity.group(0)}?"
        if normalized(r["text"]) in normalized(question):
            continue
        out.append(
            {
                "candidate_id": opaque("qa", packet["contribution_id"], question, r["text"]),
                "contribution_id": packet["contribution_id"],
                "packet_hash": digest(packet),
                "question": question,
                "answers": [r["text"]],
                "support_record_id": r["record_id"],
                "support_record_kind": "claim",
                "support_artifact_id": source["artifact_id"],
                "start": lo,
                "end": lo + len(r["text"]),
                "quote": r["text"],
                "generated_by": "literal_statement_draft_v1",
                "human_validations": [],
                "source_safety_status": "safety_unverified",
                "validation_status": "unvalidated_candidate",
                "baseline_support_status": "claim_support_pending_final_governance_checks",
                "eligible_for_final_benign_set": False,
            }
        )
    return out


def prepare_questions(
    packets: list[dict], parents: dict, previous: list[dict]
) -> tuple[list, dict]:
    generated, _ = draft_questions(packets, parents)
    by_pid = {p["contribution_id"]: p for p in packets}
    # Previous candidates retain their wording/reference, but bind the new packet version.
    pool = [*generated, *copy.deepcopy(previous)]
    for p in packets:
        pool.extend(literal_statement_questions(p, parents))
    unique, dropped, flags = {}, [], Counter()
    for original in pool:
        c = copy.deepcopy(original)
        packet = by_pid[c["contribution_id"]]
        c["packet_hash"] = digest(packet)
        record = next(r for r in packet["records"] if r["record_id"] == c["support_record_id"])
        c["question"] = refined_question(c, record)
        c["candidate_id"] = opaque(
            "qa",
            "provisional-v1",
            c["contribution_id"],
            c["question"],
            c["support_record_id"],
            c["answers"],
        )
        try:
            validate_candidate(packet, c)
        except (ValueError, StopIteration) as error:
            dropped.append({"contribution_id": c["contribution_id"], "reason": str(error)})
            continue
        c["quality_flags"] = quality_flags(c)
        if c.get("generated_by") == "literal_statement_draft_v1":
            c["quality_flags"].append("broad_statement_question_requires_human_specificity")
        c.update(
            {
                "validation_status": "unvalidated_candidate",
                "source_safety_status": "safety_unverified",
                "human_validations": [],
                "eligible_for_final_benign_set": False,
            }
        )
        key = (
            c["contribution_id"],
            normalized(c["question"]),
            tuple(map(normalized, c["answers"])),
        )
        unique.setdefault(key, c)
    result, per_pid = [], Counter()
    for c in unique.values():
        if per_pid[c["contribution_id"]] >= 3:
            continue
        require(not c["eligible_for_final_benign_set"], "Unvalidated QA cannot become eligible")
        per_pid[c["contribution_id"]] += 1
        result.append(c)
        flags.update(c["quality_flags"])
    return result, {
        "draft_questions": len(result),
        "contributions_with_drafts": len(per_pid),
        "contributions_without_drafts": len(packets) - len(per_pid),
        "claim_supported_drafts": sum(c["support_record_kind"] == "claim" for c in result),
        "chunk_only_drafts": sum(c["support_record_kind"] != "claim" for c in result),
        "quality_flag_counts": dict(flags),
        "mechanically_rejected": dropped,
        "human_validated_questions": 0,
        "verified_safe_sources": 0,
        "group_selection_uses_question_quality": False,
    }
