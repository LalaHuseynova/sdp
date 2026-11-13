"""Reconstruct chunk text from historical vectors; saved write records remain authoritative."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from ams.core import sentinel
from ams.core.prompts import PromptLibrary
from ams.core.spans import segment
from ams.research.phase1_common import digest, opaque, require
from ams.research.recovery.offline import CHAT_MODEL, STATUSES, OfflineMiss, request_key


def retention(cache, query: str, prompts: PromptLibrary) -> tuple[list[dict], dict]:
    sentences = [s.text for s in segment(query)]
    if not sentences:
        return [], {"empty_principal": True}
    numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(sentences))
    payload = {
        "provider": "openrouter",
        "model": CHAT_MODEL,
        "temperature": 0.0,
        "max_tokens": 60 + 40 * len(sentences),
        "stop": [],
        "sample_index": 0,
        "messages": [
            {
                "role": "user",
                "content": prompts.get("retention_sentence", "v1").render(sentences=numbered),
            }
        ],
    }
    data, receipt = cache.get(request_key(payload), "chat", "openrouter", CHAT_MODEL)
    match = re.search(r"\{.*\}", data["text"], re.S)
    try:
        labels = (
            {
                d["i"]: d
                for d in json.loads(match.group(0)).get("sentences", [])
                if isinstance(d, dict) and isinstance(d.get("i"), int)
            }
            if match
            else {}
        )
    except (json.JSONDecodeError, AttributeError):
        labels = {}
    return [
        {
            "text": s,
            "keep": labels.get(i, {}).get("keep") is True
            and labels.get(i, {}).get("scope") in {"self", "referential"},
            "scope": labels.get(i, {}).get("scope", ""),
        }
        for i, s in enumerate(sentences)
    ], receipt


def span_units(artifact: dict) -> list[dict]:
    """Track discontiguous source spans exactly; never substitute guessed offsets."""
    result, cursor = [], 0
    for sp in segment(artifact["text"]):
        lo = artifact["text"].find(sp.text, cursor)
        require(lo >= 0, "Segment cannot be aligned literally to original artifact")
        hi = lo + len(sp.text)
        result.append(
            {"artifact_id": artifact["artifact_id"], "start": lo, "end": hi, "quote": sp.text}
        )
        cursor = hi
    return result


def saved_chunk_observations(path: Path) -> dict:
    observed = {}
    with path.open() as f:
        for line, raw in enumerate(f, 1):
            row = json.loads(raw)
            for rendered in row.get("retrieved_texts", []):
                for attrs, body in sentinel.blocks(rendered):
                    legacy = attrs.get("entry_id", "")
                    if not re.fullmatch(r"ec\d+", legacy):
                        continue
                    header, sep, text = body.partition("\n")
                    require(sep and header.endswith(" | verbatim"), "Unexpected evidence rendering")
                    label = header.removeprefix("source: ").removesuffix(" | verbatim")
                    if legacy in observed:
                        require(observed[legacy]["text"] == text, "Conflicting saved chunk text")
                    else:
                        observed[legacy] = {
                            "text": text,
                            "source_label": label,
                            "first_journal_line": line,
                            "exposures": 0,
                        }
                    observed[legacy]["exposures"] += 1
    return observed


class CounterReplay:
    """Replay only allocation order, not extraction, graph decisions or evaluation."""

    def __init__(self):
        self.value = 0
        self.known = True

    def take(self, prefix: str) -> str | None:
        if not self.known:
            return None
        result = f"{prefix}{self.value}"
        self.value += 1
        return result


def support_candidates(text: str, artifacts: list[dict], hinted: str | None) -> list[dict]:
    """Literal candidates are NOT expert support/attribution decisions."""
    result = []
    for artifact in artifacts:
        start = 0
        while (lo := artifact["text"].find(text, start)) >= 0:
            result.append(
                {
                    "artifact_id": artifact["artifact_id"],
                    "start": lo,
                    "end": lo + len(text),
                    "quote": text,
                    "match_type": "literal_unreviewed",
                    "legacy_parent_agrees": artifact["artifact_id"] == hinted,
                }
            )
            start = lo + max(1, len(text))
    return result


def reconstruct(
    journal: list[dict],
    public: dict,
    private: dict,
    cache,
    cut,
    prompts,
    observed: dict,
    expected_chunks: int,
) -> tuple[list[dict], dict]:
    allocation = CounterReplay()
    bundles, id_checks, source_checks, misses = [], [], [], []
    for row in journal:
        cid = row["cid"]
        catalog = private[cid]
        pid = catalog["contribution_id"]
        source = public[pid]
        artifacts = source["artifacts"]
        turn = next(a for a in artifacts if a["role"] == "principal")
        external = [a for a in artifacts if a["role"] == "external"]
        roots = [(allocation.take("s"), turn)]
        roots += [(allocation.take("s"), a) for a in external]
        root_lookup = {legacy: a for legacy, a in roots if legacy is not None}
        chunks, groups, problems = [], [], []

        def index(
            artifact, label, pid=pid, cid=cid, chunks=chunks, groups=groups, problems=problems
        ):
            units = span_units(artifact)
            unit_ids = [allocation.take("s") for _ in units]
            if not units:
                return
            texts = [s["quote"] for s in units]
            try:
                vectors, sentence_receipt = cache.vectors(texts)
            except OfflineMiss as e:
                problems.append(str(e))
                misses.append(
                    {
                        "contribution_id": pid,
                        "artifact_id": artifact["artifact_id"],
                        "stage": "sentence_vectors",
                        "error": str(e),
                    }
                )
                allocation.known = False
                return
            runs = cut(texts, vectors)
            bodies = ["\n".join(texts[i] for i in run) for run in runs]
            try:
                _, chunk_receipt = cache.vectors(bodies)
            except OfflineMiss as e:
                chunk_receipt = None
                misses.append(
                    {
                        "contribution_id": pid,
                        "artifact_id": artifact["artifact_id"],
                        "stage": "chunk_text_commitment",
                        "error": str(e),
                    }
                )
            group = {
                "artifact_id": artifact["artifact_id"],
                "source_role": artifact["role"],
                "sentence_vectors": sentence_receipt,
                "chunk_batch": chunk_receipt,
                "sentence_count": len(units),
                "chunk_count": len(runs),
            }
            groups.append(group)
            for n, (run, text) in enumerate(zip(runs, bodies, strict=True)):
                legacy = allocation.take("ec")
                rid = (
                    opaque("e", cid, legacy, digest(text))
                    if legacy
                    else opaque("e", cid, artifact["artifact_id"], n, digest(text))
                )
                chunks.append(
                    {
                        "record_id": rid,
                        "record_kind": "evidence_chunk",
                        "text": text,
                        "content_hash": digest(text),
                        "legacy_entry_id": legacy,
                        "legacy_source_ids": [unit_ids[i] for i in run],
                        "source_artifact_id": artifact["artifact_id"],
                        "source_spans": [units[i] for i in run],
                        "source_role": artifact["role"],
                        "source_label": label,
                        "structural_parent_status": "reconstructed_pending_id_validation",
                        "authorship_status": "not_authenticated_by_document_text",
                        "attributable_origin_id": None,
                        "uploader_id": None,
                        "chunk_batch_committed": chunk_receipt is not None,
                        "recovery_status": "reconstructed_unverified",
                        "safety_label": None,
                    }
                )

        for n, artifact in enumerate(external):
            index(artifact, f"{row['session_id']}:art{n}")
        try:
            labels, receipt = retention(cache, source["user_query"], prompts)
            if any(s["keep"] for s in labels):
                index(turn, f"{row['session_id']}:turn")
        except OfflineMiss as e:
            receipt = None
            allocation.known = False
            problems.append(str(e))
            misses.append(
                {"contribution_id": pid, "stage": "retention_membership", "error": str(e)}
            )
        saved = {r["legacy_entry_id"]: r for r in catalog["records"]}
        claims = []
        for entry in row["written"]:
            actual = entry["entry_id"]
            predicted = allocation.take("c")
            id_checks.append(
                {
                    "actual": actual,
                    "predicted": predicted,
                    "contribution_id": pid,
                    "matches": predicted == actual,
                }
            )
            source_id = entry.get("metadata", {}).get("source_id")
            parent = root_lookup.get(source_id)
            source_checks.append(parent is not None)
            record = saved[actual]
            require(record["text"] == entry["metadata"]["raw_text"], "Saved claim text drift")
            claims.append(
                {
                    **record,
                    "recovery_status": "directly_recovered",
                    "safety_label": None,
                    "legacy_parent_artifact_id": parent["artifact_id"] if parent else None,
                    "legacy_parent_source_role": parent["role"] if parent else None,
                    "structural_parent_status": "reconstructed_pending_id_validation",
                    "semantic_attribution_status": "requires_independent_review",
                    "attributable_origin_id": None,
                    "uploader_id": None,
                    "proposed_support_spans": support_candidates(
                        record["text"], artifacts, parent["artifact_id"] if parent else None
                    ),
                }
            )
        bundles.append(
            {
                "contribution_id": pid,
                "original_case_key": cid,
                "claims": claims,
                "evidence_chunks": chunks,
                "cache_groups": groups,
                "retention_receipt": receipt,
                "issues": problems,
                "record_text_complete": not problems,
                "safety_annotation_status": "pending_human_review",
            }
        )

    all_chunks = [c for b in bundles for c in b["evidence_chunks"]]
    all_ids = bool(id_checks) and all(c["matches"] for c in id_checks)
    source_ok = bool(source_checks) and all(source_checks)
    counts_match = len(all_chunks) == expected_chunks
    rendered_mismatches, matched, direct, used = [], 0, 0, set()
    for ch in all_chunks:
        observation = observed.get(ch["legacy_entry_id"])
        if observation:
            used.add(ch["legacy_entry_id"])
            if (
                sentinel.defang(ch["text"]) != observation["text"]
                or ch["source_label"] != observation["source_label"]
            ):
                rendered_mismatches.append(ch["legacy_entry_id"])
            else:
                ch["saved_observation"] = observation
                matched += 1
    unused = sorted(set(observed) - used)
    verified_chain = (
        all_ids
        and source_ok
        and counts_match
        and not rendered_mismatches
        and not unused
        and not any(b["issues"] for b in bundles)
    )
    for b in bundles:
        for claim in b["claims"]:
            claim["structural_parent_status"] = (
                "legacy_allocation_verified" if verified_chain else "legacy_allocation_unverified"
            )
            if not verified_chain:
                claim["legacy_parent_artifact_id"] = None
                claim["legacy_parent_source_role"] = None
        for ch in b["evidence_chunks"]:
            obs = ch.get("saved_observation")
            if verified_chain and obs and obs["text"] == ch["text"]:
                ch["recovery_status"] = "directly_recovered"
                direct += 1
            elif verified_chain and ch["chunk_batch_committed"]:
                ch["recovery_status"] = "reconstructed_verified"
            ch["structural_parent_status"] = (
                "legacy_allocation_verified" if verified_chain else "reconstructed_unverified"
            )
        statuses = [r["recovery_status"] for r in [*b["claims"], *b["evidence_chunks"]]]
        if not b["record_text_complete"]:
            b["recovery_status"] = "unavailable_offline"
            b["bundle_completeness"] = "partial"
        elif "reconstructed_unverified" in statuses or not verified_chain:
            b["recovery_status"] = "reconstructed_unverified"
            b["bundle_completeness"] = "text_complete_historical_identity_unverified"
        elif "reconstructed_verified" in statuses:
            b["recovery_status"] = "reconstructed_verified"
            b["bundle_completeness"] = "complete_text_and_structural_provenance"
        else:
            b["recovery_status"] = "directly_recovered"
            b["bundle_completeness"] = "complete_text_and_structural_provenance"
    chunk_counts = Counter(c["recovery_status"] for c in all_chunks)
    chunk_counts["unavailable_offline"] = max(0, expected_chunks - len(all_chunks))
    result = {
        "claims": {
            s: sum(c["recovery_status"] == s for b in bundles for c in b["claims"])
            for s in STATUSES
        },
        "evidence_chunks": {s: chunk_counts[s] for s in STATUSES},
        "contribution_bundles": {
            s: sum(b["recovery_status"] == s for b in bundles) for s in STATUSES
        },
        "verification": {
            "claim_id_anchors": len(id_checks),
            "claim_id_matches": sum(c["matches"] for c in id_checks),
            "claim_id_mismatches": [c for c in id_checks if not c["matches"]][:30],
            "legacy_parent_references": len(source_checks),
            "legacy_parent_matches": sum(source_checks),
            "expected_historical_chunks": expected_chunks,
            "reconstructed_chunks": len(all_chunks),
            "counts_match": counts_match,
            "unique_saved_chunk_observations": len(observed),
            "observed_render_matches": matched,
            "direct_plaintext_matches": direct,
            "render_mismatches": rendered_mismatches,
            "unmatched_observed_ids": unused,
            "historical_verification_chain_passed": verified_chain,
        },
        "misses": misses,
        "partial_bundles": sum(not b["record_text_complete"] for b in bundles),
        "verification_scope": "Text, allocation and construction parents; not a full graph-state "
        "replay or authenticated natural authorship. Cache commitments can originate in prefetch.",
    }
    return bundles, result
