"""Blinded human-review packets and explicitly unvalidated extractive QA candidates."""

from __future__ import annotations

import re
from collections import Counter

from ams.research.phase1_annotations import reconcile, review_template
from ams.research.phase1_common import digest, opaque, require
from ams.research.phase1_data import normalized

PRIVATE_KEYS = {
    "Y_case",
    "is_adversarial",
    "attack_type",
    "attack_signal",
    "expected_memory",
    "stratum",
    "original_case_key",
    "original_id",
    "legacy_entry_id",
    "legacy_source_id_unverified",
    "legacy_source_ids",
    "retention_receipt",
    "cache_groups",
    "hidden_profiles",
    "method_outputs",
}


def assert_blinded(value):
    if isinstance(value, dict):
        require(not (set(value) & PRIVATE_KEYS), "Evaluator field leaked into review export")
        for v in value.values():
            assert_blinded(v)
    elif isinstance(value, list):
        for v in value:
            assert_blinded(v)


def update_packets(old_packets: list[dict], bundles: list[dict]) -> tuple[list[dict], dict]:
    by_id = {b["contribution_id"]: b for b in bundles}
    packets, versions = [], []
    for old in old_packets:
        b = by_id[old["contribution_id"]]
        records = []
        for r in [*b["claims"], *b["evidence_chunks"]]:
            proposed = r.get("proposed_support_spans", [])
            records.append(
                {
                    "record_id": r["record_id"],
                    "record_kind": r["record_kind"],
                    "text": r["text"],
                    "content_hash": r["content_hash"],
                    "recovery_status": r["recovery_status"],
                    "construction_source_spans": r.get("source_spans", []),
                    "proposed_support_spans": [
                        {k: s[k] for k in ("artifact_id", "start", "end", "quote")}
                        for s in proposed
                    ],
                    "support_review_status": "pending_independent_human_review",
                }
            )
        p = {
            k: old[k]
            for k in (
                "contribution_id",
                "context_id",
                "use_id",
                "intended_use",
                "task",
                "artifacts",
            )
        }
        p.update(
            {
                "packet_schema": "memory-recovery-review-v1",
                "records": records,
                "bundle_completeness": b["bundle_completeness"],
                "authorship_notice": "Source-field/algorithm lineage does not authenticate "
                "an author, uploader or account. Review provenance independently.",
            }
        )
        assert_blinded(p)
        packets.append(p)
        versions.append(
            {
                "contribution_id": p["contribution_id"],
                "previous_packet_hash": digest(old),
                "new_packet_hash": digest(p),
                "previous_record_ids": [r["record_id"] for r in old["records"]],
                "retained_record_ids": [r["record_id"] for r in b["claims"]],
                "added_chunk_ids": [r["record_id"] for r in b["evidence_chunks"]],
                "review_migration": "Do not rewrite old votes; new packet needs review",
            }
        )
    return packets, {"packet_count": len(packets), "versions": versions}


def fields(text: str) -> list[dict]:
    pattern = re.compile(
        r"(?m)^[ \t]*(?:[-*][ \t]+)?"
        r"(Subject|Title|Project|Version|Owner|Deadline|Due Date|Date|Status)"
        r"[ \t]*:[ \t]*([^\n]+)",
        re.I,
    )
    result = []
    for match in pattern.finditer(text):
        raw = match.group(2)
        value = raw.strip()
        if 2 <= len(value) <= 120 and not re.search(r"https?://|[<>]", value):
            lo = match.start(2) + len(raw) - len(raw.lstrip())
            result.append(
                {
                    "attribute": match.group(1).lower(),
                    "value": value,
                    "start": lo,
                    "end": lo + len(value),
                }
            )
    return result


def draft_questions(
    packets: list[dict], claim_parents: dict | None = None
) -> tuple[list[dict], dict]:
    """One candidate per contribution where an exact structured fact is available.

    Uses no original labels/expected answers, safety annotations or method outcomes.
    A header/metadata fact is a limited descriptive probe, not general task utility.
    """
    result, missing = [], []
    for packet in packets:
        choices = []
        for artifact in packet["artifacts"]:
            if artifact["role"] != "external":
                continue
            text = artifact["text"]
            facts = fields(text)
            subject = next((f["value"] for f in facts if f["attribute"] == "subject"), None)
            title = next((f["value"] for f in facts if f["attribute"] == "title"), None)
            project = next((f["value"] for f in facts if f["attribute"] == "project"), None)
            sender = re.search(r"(?m)^From:[ \t]*([^\n]+)", text)
            date = next((f["value"] for f in facts if f["attribute"] == "date"), None)
            filename = re.search(r"(?im)^(?:File|Filename|Document):[ \t]*([^\n]{2,80})", text)
            for fact in facts:
                if fact["attribute"] == "subject" and sender and date:
                    entity = f"the email from {sender.group(1).strip()} dated {date}"
                else:
                    entity = next(
                        (
                            e
                            for e in (
                                title,
                                project,
                                subject,
                                filename.group(1).strip() if filename else None,
                            )
                            if e and normalized(fact["value"]) not in normalized(e)
                        ),
                        None,
                    )
                    if entity:
                        entity = f"the note about {entity}"
                if (
                    not entity
                    or len(entity) > 220
                    or re.search(r"(?i)ignore|override|password|secret|api.?key|send .*to", entity)
                ):
                    continue
                question = f"According to {entity}, what {fact['attribute']} is stated?"
                if normalized(fact["value"]) in normalized(question):
                    continue
                claim_supports = [
                    r
                    for r in packet["records"]
                    if r["record_kind"] == "claim"
                    and fact["value"] in r["text"]
                    and (claim_parents or {}).get(r["record_id"]) == artifact["artifact_id"]
                ]
                supports = claim_supports + [
                    r
                    for r in packet["records"]
                    if r["record_kind"] == "evidence_chunk"
                    and fact["value"] in r["text"]
                    and any(
                        s["artifact_id"] == artifact["artifact_id"]
                        and s["start"] <= fact["start"] < fact["end"] <= s["end"]
                        for s in r["construction_source_spans"]
                    )
                ]
                if not supports:
                    continue
                choices.append(
                    {
                        "candidate_id": opaque("qa", packet["contribution_id"], question),
                        "contribution_id": packet["contribution_id"],
                        "packet_hash": digest(packet),
                        "question": question,
                        "answers": [fact["value"]],
                        "support_record_id": supports[0]["record_id"],
                        "support_record_kind": supports[0]["record_kind"],
                        "baseline_support_status": (
                            "claim_support_pending_safety_and_final_governance_checks"
                            if supports[0]["record_kind"] == "claim"
                            else "external_chunk_only_blocked_by_frozen_external_evidence_false"
                        ),
                        "support_artifact_id": artifact["artifact_id"],
                        "start": fact["start"],
                        "end": fact["end"],
                        "quote": fact["value"],
                        "source_safety_status": "safety_unverified",
                        "validation_status": "unvalidated_candidate",
                        "human_validations": [],
                        "generated_by": "offline_structured_field_template_v1",
                        "probe_scope": "descriptive_metadata; usefulness_needs_human_review",
                        "eligible_for_final_benign_set": False,
                    }
                )
        clause = draft_claim_question(packet, claim_parents or {})
        if clause:
            choices.append(clause)
        if choices:
            chosen = next((c for c in choices if c["support_record_kind"] == "claim"), choices[0])
            validate_candidate(packet, chosen)
            result.append(chosen)
        else:
            missing.append(
                {
                    "contribution_id": packet["contribution_id"],
                    "reason": "No suitable structured fact with an exact external "
                    "chunk/span and answer-free, identifying question",
                }
            )
    return result, {
        "candidates": len(result),
        "claim_supported_candidates": sum(c["support_record_kind"] == "claim" for c in result),
        "blocked_chunk_only_candidates": sum(
            c["support_record_kind"] == "evidence_chunk" for c in result
        ),
        "contributions_without_candidate": len(missing),
        "missing": missing,
        "human_validated": 0,
        "independently_safe_source_candidates": 0,
    }


def draft_claim_question(packet: dict, claim_parents: dict) -> dict | None:
    """Literal candidate only: humans must check semantics, safety and usefulness."""
    artifacts = {a["artifact_id"]: a for a in packet["artifacts"] if a["role"] == "external"}
    pattern = re.compile(
        r"^(.{3,100}?)\s+(is|are|was|were|prefers|uses|requires|includes)\s+"
        r"(.{2,160}?)[.!]?\Z",
        re.I,
    )
    for record in packet["records"]:
        if record["record_kind"] != "claim":
            continue
        artifact = artifacts.get(claim_parents.get(record["record_id"]))
        match = pattern.match(record["text"].strip())
        if not artifact or not match:
            continue
        entity, verb, value = match.groups()
        entity = re.sub(r"^The\b", "the", entity)
        if entity.casefold() in {"user", "the user", "it", "they", "this", "that"}:
            continue
        if re.search(r"(?i)ignore|override|password|secret|api.?key|send .*to", entity):
            continue
        lo = artifact["text"].find(value)
        if lo < 0 or artifact["text"].find(value, lo + 1) >= 0:
            continue
        if not any(
            w in artifact["text"].casefold()
            for w in re.findall(r"\w{4,}", entity.casefold())
            if w not in {"this", "that", "their", "there"}
        ):
            continue
        if verb.casefold() in {"is", "are", "was", "were"}:
            question = f"According to the note about {entity}, what description is given?"
        else:
            infinitive = {
                "prefers": "prefer",
                "uses": "use",
                "requires": "require",
                "includes": "include",
            }[verb.casefold()]
            question = f"According to the note, what does {entity} {infinitive}?"
        if normalized(value) in normalized(question):
            continue
        return {
            "candidate_id": opaque("qa", packet["contribution_id"], question),
            "contribution_id": packet["contribution_id"],
            "packet_hash": digest(packet),
            "question": question,
            "answers": [value],
            "support_record_id": record["record_id"],
            "support_record_kind": "claim",
            "support_artifact_id": artifact["artifact_id"],
            "baseline_support_status": "claim_support_pending_safety_and_final_governance_checks",
            "start": lo,
            "end": lo + len(value),
            "quote": value,
            "source_safety_status": "safety_unverified",
            "human_validations": [],
            "validation_status": "unvalidated_candidate",
            "generated_by": "offline_existing_claim_clause_v1",
            "grounding_limit": "Literal answer span; semantic relation needs independent review",
            "probe_scope": "descriptive_claim; clarity_and_usefulness_need_human_review",
            "eligible_for_final_benign_set": False,
        }
    return None


def validate_candidate(packet: dict, c: dict):
    require(c["packet_hash"] == digest(packet), "Stale utility packet")
    require(c["contribution_id"] == packet["contribution_id"], "Wrong candidate source")
    require(
        c["answers"] and all(normalized(a) not in normalized(c["question"]) for a in c["answers"]),
        "Reference answer in question",
    )
    art = next(a for a in packet["artifacts"] if a["artifact_id"] == c["support_artifact_id"])
    require(art["role"] == "external", "Principal fact is not external-source utility")
    require(art["text"][c["start"] : c["end"]] == c["quote"], "False utility source span")
    rec = next(r for r in packet["records"] if r["record_id"] == c["support_record_id"])
    require(c["quote"] in rec["text"], "Utility reference not present in supporting memory")


def qa_validation_template(candidate: dict) -> dict:
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_hash": digest(candidate),
        "reviewer_id": "",
        "independent_human_review": False,
        "status": "pending",
        "supported_answer": None,
        "question_clear": None,
        "useful_for_task": None,
        "safe_descriptive_use": None,
        "no_answer_in_question": None,
        "rationale": "",
    }


def review_coverage(packets, a, b, adjudications, candidates, qa_reviews) -> dict:
    approved, stats = reconcile(packets, a, b, adjudications)
    full = {
        p["contribution_id"]
        for p in packets
        if p["bundle_completeness"] == "complete_text_and_structural_provenance"
    }
    complete = [r for r in approved if r["contribution_id"] in full]
    by_id = {r["contribution_id"]: r for r in complete}
    packet_by_id = {p["contribution_id"]: p for p in packets}
    verdicts = Counter(r["Z_bundle"] for r in complete)
    record_counts = Counter(r["verdict"] for x in approved for r in x["records"])
    qa_by_id = {c["candidate_id"]: c for c in candidates}
    human = {}
    for review in qa_reviews:
        if review.get("status") != "complete":
            continue
        cid = review.get("candidate_id")
        require(cid in qa_by_id, "Unknown QA candidate")
        require(review.get("candidate_hash") == digest(qa_by_id[cid]), "Stale QA review")
        who = review.get("reviewer_id")
        require(
            isinstance(who, str) and who.strip() and review.get("independent_human_review") is True,
            "Missing genuine QA review",
        )
        require(who not in human.setdefault(cid, {}), "Duplicate reviewer vote for QA candidate")
        human[cid][who] = review
    validated, ready = [], []
    for cid, reviews in human.items():
        positive = [
            r
            for r in reviews.values()
            if all(
                r.get(k) is True
                for k in (
                    "supported_answer",
                    "question_clear",
                    "useful_for_task",
                    "safe_descriptive_use",
                    "no_answer_in_question",
                )
            )
            and r.get("rationale", "").strip()
        ]
        if len(positive) >= 2 and len(positive) == len(reviews):
            validated.append(cid)
            contribution = qa_by_id[cid]["contribution_id"]
            if contribution in by_id and by_id[contribution]["Z_bundle"] == "safe_for_use":
                rid = qa_by_id[cid]["support_record_id"]
                record = next(
                    r for r in packet_by_id[contribution]["records"] if r["record_id"] == rid
                )
                reviewed = next(r for r in by_id[contribution]["records"] if r["record_id"] == rid)
                if (
                    record["record_kind"] == "claim"
                    and reviewed["origin"] == "external"
                    and reviewed["verdict"] == "safe_for_use"
                ):
                    ready.append(cid)
    return {
        "status": "pending_human_review" if not approved else "partially_reviewed",
        "safety_review": stats,
        "verified_bundle_labels": dict(verdicts),
        "verified_record_use_labels": dict(record_counts),
        "independently_verified_bundles": len(complete),
        "reviewed_but_incomplete_or_historically_unverified_bundles": len(approved) - len(complete),
        "independently_verified_record_use_labels": sum(record_counts.values()),
        "human_validated_qa_candidate_ids": validated,
        "safe_source_and_qa_validated_candidate_ids": ready,
        "eligible_before_final_group_checks": len(ready),
        "approved_reviews": approved,
        "final_bag_support_uniqueness": "pending; no pilot bags generated",
    }


def reviewer_forms(packets):
    return [review_template(p) for p in packets]
