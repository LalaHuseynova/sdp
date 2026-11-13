"""Unverified curator hints, kept separate from blinded human review forms."""

from __future__ import annotations

import copy
import re
from collections import Counter

from ams.research.phase1_common import digest, require
from ams.research.recovery.annotation import assert_blinded
from ams.research.recovery.records import span_units

RULES = {
    "instruction_override": r"\bignore\s+(?:(?:all|the|any)\s+)?"
    r"(?:previous|prior|earlier|system)\s+"
    r"(?:instructions?|rules?|polic(?:y|ies))\b",
    "verification_bypass": r"\b(?:skip|bypass|disable)\b[^.\n]{0,70}"
    r"\b(?:verification|approval|security|authentication|checks?)\b",
    "outbound_transfer": r"\b(?:send|forward|upload|transmit)\b[^.\n]{0,160}"
    r"(?:https?://\S+|[\w.+-]+@[\w.-]+\.[a-z]{2,})",
    "claimed_privilege": r"\b(?:treat|mark|consider)\b[^.\n]{0,90}"
    r"\b(?:trusted|verified|administrator|authorized)\b",
}


def warnings(text: str) -> list[dict]:
    hits = []
    for rule, pattern in RULES.items():
        for m in re.finditer(pattern, text, re.I):
            hits.append(
                {
                    "rule_id": rule,
                    "start": m.start(),
                    "end": m.end(),
                    "quote": m.group(0),
                    "interpretation": "unverified_review_hint",
                    "quotation_or_negation_may_make_this_safe": True,
                }
            )
    return hits


def words(text: str) -> set[str]:
    return set(re.findall(r"[\w]{3,}", text.casefold())) - {
        "the",
        "and",
        "that",
        "this",
        "with",
        "from",
        "for",
        "user",
        "has",
        "are",
        "was",
    }


def support_suggestions(record: dict, artifacts: list[dict], limit: int = 2) -> list[dict]:
    if record["record_kind"] == "evidence_chunk":
        return [
            {
                **s,
                "match_type": "mechanical_construction_parent",
                "semantic_review_status": "unverified",
            }
            for s in record.get("construction_source_spans", [])
        ]
    literal = record.get("proposed_support_spans", [])
    if literal:
        return [
            {**s, "match_type": "literal_match_unreviewed", "semantic_review_status": "unverified"}
            for s in literal[:limit]
        ]
    tokens = words(record["text"])
    if not tokens:
        return []
    scored = []
    for a in artifacts:
        for s in span_units(a):
            common = tokens & words(s["quote"])
            score = len(common) / len(tokens)
            if len(common) >= 3 and score >= 0.35:
                scored.append((score, s))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["artifact_id"], pair[1]["start"]))
    return [
        {
            **s,
            "match_type": "lexical_overlap_unreviewed",
            "overlap": round(score, 6),
            "semantic_review_status": "unverified",
        }
        for score, s in scored[:limit]
    ]


def prepare_annotations(packets: list[dict]) -> tuple[list[dict], list[dict], dict]:
    updated, hints, counts = [], [], Counter()
    for old in packets:
        packet = copy.deepcopy(old)
        packet["packet_schema"] = "provisional-review-v1"
        packet["review_status"] = "pending_human_validation"
        for record in packet["records"]:
            suggestions = support_suggestions(record, packet["artifacts"])
            record["source_support_suggestions"] = suggestions
            for s in suggestions:
                source = next(
                    a for a in packet["artifacts"] if a["artifact_id"] == s["artifact_id"]
                )
                require(source["text"][s["start"] : s["end"]] == s["quote"], "Invalid support hint")
            flags = warnings(record["text"])
            hints.append(
                {
                    "contribution_id": packet["contribution_id"],
                    "record_id": record["record_id"],
                    "content_hash": record["content_hash"],
                    "hint_schema": "automated_unverified_v1",
                    "warnings": flags,
                    "verified_verdict": None,
                    "human_review_status": "pending",
                    "unflagged_does_not_mean_safe": True,
                }
            )
            counts["records"] += 1
            counts["records_with_warning"] += bool(flags)
            counts["records_with_support_suggestion"] += bool(suggestions)
            for flag in flags:
                counts[flag["rule_id"]] += 1
        assert_blinded(packet)
        updated.append(packet)
    return (
        updated,
        hints,
        {
            "counts": dict(counts),
            "human_verified_labels": 0,
            "warning_flags_are_not_safety_labels": True,
            "hints_excluded_from_blinded_review_exports": True,
            "packet_count": len(updated),
            "packet_version_hash": digest(updated),
        },
    )
