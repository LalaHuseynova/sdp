"""Validate human reviews without deriving memory safety from input-case labels."""

from __future__ import annotations

from ams.research.phase1_common import digest, require
from ams.research.phase1_data import normalized

VERDICTS = {"unsafe", "safe_for_use", "uncertain"}


def review_template(packet: dict) -> dict:
    return {
        "contribution_id": packet["contribution_id"],
        "use_id": packet["use_id"],
        "packet_hash": digest(packet),
        "reviewer_id": "",
        "status": "pending",
        "independent_human_review": False,
        "records": [
            {
                "record_id": r["record_id"],
                "content_hash": r["content_hash"],
                "origin": None,
                "source_spans": [],
                "verdict": None,
                "fully_reviewed": False,
                "evidence_quote": "",
                "rationale": "",
            }
            for r in packet["records"]
        ],
    }


def utility_template(packet: dict) -> dict:
    return {
        "contribution_id": packet["contribution_id"],
        "packet_hash": digest(packet),
        "question": "",
        "answers": [],
        "support_record_id": "",
        "support_artifact_id": "",
        "start": None,
        "end": None,
        "quote": "",
        "proposed_by": "",
        "validated_by": "",
        "status": "pending",
        "safe_descriptive_use_confirmed": False,
        "unique_support_in_bag_confirmed": False,
    }


def validate_review(packet: dict, review: dict) -> dict:
    require(review.get("contribution_id") == packet["contribution_id"], "Wrong review input")
    require(review.get("use_id") == packet["use_id"], "Wrong reviewed use")
    require(review.get("packet_hash") == digest(packet), "Stale review packet/content")
    require(review.get("status") == "complete", "Review is incomplete")
    require(review.get("independent_human_review") is True, "Human review attestation missing")
    require(
        isinstance(review.get("reviewer_id"), str) and bool(review["reviewer_id"].strip()),
        "Reviewer identity missing",
    )
    actual = {r["record_id"]: r for r in packet["records"]}
    rows = review.get("records", [])
    require(
        len(rows) == len(actual) and {r["record_id"] for r in rows} == set(actual),
        "Review must examine exactly the frozen records, without duplicates",
    )
    sources = {a["artifact_id"]: a for a in packet["artifacts"]}
    decisions = []
    for r in rows:
        record = actual[r["record_id"]]
        require(r.get("content_hash") == record["content_hash"], "Stale claim version")
        require(r.get("fully_reviewed") is True, "Partially reviewed claim")
        require(r.get("verdict") in VERDICTS, "Missing/invalid record-use verdict")
        require(r.get("origin") in {"principal", "external", "ambiguous"}, "Unknown origin")
        require(bool(r.get("rationale", "").strip()), "Missing review justification")
        spans = r.get("source_spans", [])
        if r["origin"] != "ambiguous":
            require(bool(spans), "Confirmed attribution requires source spans")
        for span in spans:
            source = sources.get(span.get("artifact_id"))
            require(source is not None, "Span references unknown artifact")
            lo, hi = span.get("start"), span.get("end")
            require(
                type(lo) is int and type(hi) is int and 0 <= lo < hi <= len(source["text"]),
                "Invalid artifact-local offsets",
            )
            require(source["text"][lo:hi] == span.get("quote"), "Source quote/offset mismatch")
            if r["origin"] != "ambiguous":
                require(source["role"] == r["origin"], "Principal/external role mismatch")
        if r["verdict"] == "unsafe":
            quote = r.get("evidence_quote", "")
            require(bool(quote) and quote in record["text"], "Unsafe claim needs actual evidence")
        decisions.append(
            {k: r[k] for k in ("record_id", "content_hash", "origin", "source_spans", "verdict")}
        )
    return {
        "reviewer_id": review["reviewer_id"],
        "decisions": sorted(decisions, key=lambda r: r["record_id"]),
        "audit_evidence": [
            {
                "record_id": r["record_id"],
                "evidence_quote": r["evidence_quote"],
                "rationale": r["rationale"],
            }
            for r in rows
        ],
    }


def bundle_verdict(decisions: list[dict]) -> str:
    external = [r for r in decisions if r["origin"] == "external"]
    if any(r["verdict"] == "unsafe" for r in external):
        return "unsafe"
    if (
        external
        and not any(r["origin"] == "ambiguous" for r in decisions)
        and all(r["verdict"] == "safe_for_use" for r in external)
    ):
        return "safe_for_use"
    return "uncertain"


def reconcile(
    packets: list[dict],
    reviews_a: list[dict],
    reviews_b: list[dict],
    adjudications: list[dict] | None = None,
) -> tuple[list[dict], dict]:
    """Incomplete reviews are reported; invalid completed ones fail explicitly."""
    indexes = []
    packet_ids = {p["contribution_id"] for p in packets}
    for rows in (reviews_a, reviews_b, adjudications or []):
        ix = {}
        for r in rows:
            pid = r.get("contribution_id")
            require(pid in packet_ids and pid not in ix, "Unknown/duplicate review contribution")
            ix[pid] = r
        indexes.append(ix)
    approved, missing, disagreements, resolutions = [], [], [], []
    for packet in packets:
        pid = packet["contribution_id"]
        pair = [index.get(pid) for index in indexes[:2]]
        if any(r is None or r.get("status") != "complete" for r in pair):
            missing.append(pid)
            continue
        a, b = [validate_review(packet, r) for r in pair]
        require(a["reviewer_id"] != b["reviewer_id"], "Two distinct human reviewers required")
        chosen = a
        if a["decisions"] != b["decisions"]:
            disagreements.append(pid)
            third = indexes[2].get(pid)
            if third is None or third.get("status") != "complete":
                continue
            chosen = validate_review(packet, third)
            require(
                chosen["reviewer_id"] not in {a["reviewer_id"], b["reviewer_id"]},
                "Adjudicator must be independent of both reviewers",
            )
            resolutions.append(pid)
        approved.append(
            {
                "contribution_id": pid,
                "use_id": packet["use_id"],
                "packet_hash": digest(packet),
                "Z_bundle": bundle_verdict(chosen["decisions"]),
                "records": chosen["decisions"],
                "audit_evidence": chosen["audit_evidence"],
                "reviewers": [a["reviewer_id"], b["reviewer_id"]],
                "adjudicator": chosen["reviewer_id"] if pid in resolutions else None,
            }
        )
    return approved, {
        "completed_consensus": len(approved),
        "missing_two_reviews": len(missing),
        "disagreements": len(disagreements),
        "adjudicated": len(resolutions),
        "unresolved_disagreements": sorted(set(disagreements) - set(resolutions)),
    }


def validate_utility(packet: dict, approval: dict, probe: dict) -> dict:
    require(approval["Z_bundle"] == "safe_for_use", "Utility source is not reviewed safe")
    require(probe.get("contribution_id") == packet["contribution_id"], "Wrong utility input")
    require(probe.get("packet_hash") == digest(packet), "Stale utility packet")
    require(probe.get("status") == "complete", "Utility probe not validated")
    author, checker = probe.get("proposed_by"), probe.get("validated_by")
    require(
        isinstance(author, str)
        and isinstance(checker, str)
        and bool(author.strip())
        and bool(checker.strip())
        and author != checker,
        "Utility question needs distinct author and validator",
    )
    require(
        probe.get("safe_descriptive_use_confirmed") is True,
        "New descriptive use must be independently checked",
    )
    require(
        probe.get("unique_support_in_bag_confirmed") is True,
        "Unique/disambiguated support must be checked again in the final bag",
    )
    question = probe.get("question", "").strip()
    answers = probe.get("answers", [])
    require(
        question and answers and all(isinstance(a, str) and a.strip() for a in answers),
        "Question/reference answers missing",
    )
    require(
        all(normalized(a) not in normalized(question) for a in answers),
        "Question contains a reference answer",
    )
    rid = probe.get("support_record_id")
    mapped = next((r for r in approval["records"] if r["record_id"] == rid), None)
    require(
        mapped is not None
        and mapped["origin"] == "external"
        and mapped["verdict"] == "safe_for_use",
        "Utility needs a safe external claim",
    )
    source = next(
        (a for a in packet["artifacts"] if a["artifact_id"] == probe.get("support_artifact_id")),
        None,
    )
    require(source is not None and source["role"] == "external", "External support missing")
    lo, hi = probe.get("start"), probe.get("end")
    require(
        type(lo) is int and type(hi) is int and 0 <= lo < hi <= len(source["text"]),
        "Invalid utility support span",
    )
    require(source["text"][lo:hi] == probe.get("quote"), "Utility quote mismatch")
    require(
        any(
            s["artifact_id"] == source["artifact_id"] and s["start"] <= lo < hi <= s["end"]
            for s in mapped["source_spans"]
        ),
        "Utility support falls outside confirmed record-source mapping",
    )
    return probe


def eligible_records(
    private: list[dict],
    packets: list[dict],
    reviews_a: list[dict],
    reviews_b: list[dict],
    adjudications: list[dict],
    utilities: list[dict],
) -> tuple[list[dict], dict]:
    approved, stats = reconcile(packets, reviews_a, reviews_b, adjudications)
    pp = {p["contribution_id"]: p for p in packets}
    original = {p["contribution_id"]: p for p in private}
    probes = {}
    for p in utilities:
        pid = p.get("contribution_id")
        require(pid in pp and pid not in probes, "Duplicate/unknown utility probe")
        probes[pid] = p
    eligible, missing_qa = [], 0
    for a in approved:
        pid = a["contribution_id"]
        if a["Z_bundle"] == "uncertain":
            continue
        if a["Z_bundle"] == "safe_for_use":
            utility = probes.get(pid)
            if utility is None or utility.get("status") != "complete":
                missing_qa += 1
                continue
            validate_utility(pp[pid], a, utility)
        else:
            utility = None
        # This is private construction input. It must never be given to a defense.
        eligible.append(
            {**original[pid], **a, "utility": utility, "frozen_records": original[pid]["records"]}
        )
    stats.update(
        {
            "eligible_with_required_utility": len(eligible),
            "safe_missing_utility": missing_qa,
            "unsafe_labels_inferred_from_case": 0,
        }
    )
    return eligible, stats
