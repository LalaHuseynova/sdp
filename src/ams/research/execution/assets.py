"""Read-only availability audit; no reconstruction of an imagined historical graph."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from ams.core.prompts import PromptLibrary
from ams.llm.types import ChatRequest, EmbedRequest, Message
from ams.research.dynamic.models import check, digest
from ams.research.phase1_common import read_jsonl
from ams.research.recovery.offline import (
    CHAT_MODEL,
    EMBED_MODEL,
    OfflineMiss,
    ReadOnlyCache,
)
from ams.research.sequential.clients import response_from

from .session import prompt_measurement


def text_hash(text):
    # Recovery uses SHA-256 of the canonical JSON string, including quotes.
    return digest(text)


def audit_assets(repo: Path, prepared: Path, recovered: Path, caches: list[Path]):
    """Inspect existing provisional inputs only; never assert Z-balanced eligibility.

    Cache-derived classifier replies are frozen candidates for a NEW comparison,
    not asserted to be the reply used historically. Exact request keys are required.
    Native graph/source IDs must be assigned and bound at future construction.
    """
    selected = json.loads((prepared / "private/group_selections.json").read_text())
    ids = {x for bag in selected for x in bag["source_ids"]}
    check(len(ids) == sum(len(b["source_ids"]) for b in selected), "Repeated provisional source")
    bundles = {
        b["contribution_id"]: b
        for b in read_jsonl(recovered / "private/bundle_index.jsonl")
        if b["contribution_id"] in ids
    }
    check(set(bundles) == ids, "Missing recovered bundle")
    claims, chunks = defaultdict(list), defaultdict(list)
    statuses, structural, spans = Counter(), Counter(), Counter()
    for name, dest in (("claims", claims), ("evidence_chunks", chunks)):
        for row in read_jsonl(recovered / f"private/{name}.jsonl"):
            pid = row["contribution_id"]
            if pid not in ids:
                continue
            check(text_hash(row["text"]) == row["content_hash"], "Recovered record content changed")
            dest[pid].append(row)
            statuses[f"{name}:{row['recovery_status']}"] += 1
            structural[row["structural_parent_status"]] += 1
    public = {
        r["contribution_id"]: r
        for r in read_jsonl(repo / "research_data/mpbench_phase1/public/candidate_inputs.jsonl")
        if r["contribution_id"] in ids
    }
    artifacts = {a["artifact_id"]: a for r in public.values() for a in r["artifacts"]}
    for records in (claims, chunks):
        for rows in records.values():
            for row in rows:
                evidence = row.get("source_spans", row.get("proposed_support_spans", []))
                for span in evidence:
                    artifact = artifacts[span["artifact_id"]]
                    check(
                        artifact["text"][span["start"] : span["end"]] == span["quote"],
                        "Source span no longer matches",
                    )
                    spans["checked_exact_source_spans"] += 1
    cache = ReadOnlyCache(caches)
    counts, catalog, missing = Counter(), {"chats": {}, "embeddings": {}}, []
    receipt_keys = set()
    try:
        for pid, b in bundles.items():
            check(
                [r["record_id"] for r in claims[pid]] == b["claim_ids"],
                "Claim order/coverage mismatch",
            )
            check(
                [r["record_id"] for r in chunks[pid]] == b["chunk_ids"],
                "Chunk order/coverage mismatch",
            )
            receipts = [b["retention_receipt"]] if b.get("retention_receipt") else []
            for group in b["cache_groups"]:
                receipts += [
                    v for v in group.values() if isinstance(v, dict) and "request_key" in v
                ]
            for receipt in receipts:
                key = receipt["request_key"]
                if key in receipt_keys:
                    continue
                receipt_keys.add(key)
                kind = "chat" if receipt is b.get("retention_receipt") else "embed"
                try:
                    _, actual = cache.get(
                        key,
                        kind,
                        "openrouter" if kind == "chat" else "local",
                        CHAT_MODEL if kind == "chat" else EMBED_MODEL,
                    )
                    check(
                        actual["response_hash"] == receipt["response_hash"],
                        "Frozen cache receipt changed",
                    )
                    counts["historical_receipts_verified"] += 1
                except OfflineMiss:
                    counts["historical_receipts_missing"] += 1
                    missing.append({"contribution_id": pid, "kind": kind, "request_key": key})
            texts = [r["text"] for r in claims[pid]]
            if texts:
                try:
                    cache.vectors(texts)
                    counts["claim_vector_batches_available"] += 1
                except OfflineMiss:
                    counts["claim_vector_batches_missing"] += 1
        index = {
            r["contribution_id"]: r
            for r in read_jsonl(prepared / "private/evaluator_case_index.jsonl")
            if r["contribution_id"] in ids
        }
        drafts = [
            r
            for r in read_jsonl(prepared / "private/question_drafts.jsonl")
            if r["contribution_id"] in ids
        ]
        queries = sorted(
            {r["retrieval_query"].strip() for r in index.values()}
            | {r["question"].strip() for r in drafts}
        )
        prompts = PromptLibrary(repo / "prompts")
        measurements = []
        for query in queries:
            request = ChatRequest(
                (Message("user", prompts.get("classify_use_type", "v2").render(query=query)),),
                CHAT_MODEL,
                temperature=0.0,
                max_tokens=24,
            )
            measurements.append(prompt_measurement(request))
            for kind, req, provider, model in (
                ("chat", request, "openrouter", CHAT_MODEL),
                ("embed", EmbedRequest((query,), EMBED_MODEL), "local", EMBED_MODEL),
            ):
                key = req.cache_key(provider)
                try:
                    payload, _ = cache.get(key, kind, provider, model)
                    # Historical cache omits dataclass defaults. Add only those
                    # defaults; do not infer missing usage, model, text or vectors.
                    payload = {**payload, "cached": True}
                    if kind == "chat":
                        payload.setdefault("raw_finish_reason", None)
                    response_from(kind, payload)
                    catalog["chats" if kind == "chat" else "embeddings"][key] = payload
                    counts[f"query_{kind}_available"] += 1
                except OfflineMiss:
                    counts[f"query_{kind}_missing"] += 1
                    missing.append(
                        {
                            "kind": kind,
                            "request_key": key,
                            "stage": "query_classifier" if kind == "chat" else "query_embedding",
                        }
                    )
    finally:
        cache.close()
    report = {
        "scope": "existing provisional 20 bags; no scientific selection or evaluation",
        "groups": len(selected),
        "distinct_contributions": len(ids),
        "claims_checked": sum(map(len, claims.values())),
        "chunks_checked": sum(map(len, chunks.values())),
        "recovery_status_counts": dict(statuses),
        "structural_parent_counts": dict(structural),
        "source_span_checks": dict(spans),
        "availability": dict(counts),
        "fully_recovered_text_bundles": sum(b["record_text_complete"] for b in bundles.values()),
        "candidate_queries_checked": len(queries),
        "unvalidated_grounded_drafts_in_scope": len(drafts),
        "classifier_prompt_proxy_min": min(
            (r["input_token_proxy"] for r in measurements), default=0
        ),
        "classifier_prompt_proxy_max": max(
            (r["input_token_proxy"] for r in measurements), default=0
        ),
        "native_gpt_token_counts_measured": False,
        "answer_conflict_prompt_sizes": (
            "unavailable until actual bound native stores and probe contexts exist"
        ),
        "catalog_origin": (
            "exact current cache snapshot; not a historical call-transcript assertion"
        ),
        "semantic_attribution_human_verified": 0,
        "native_runtime_bindings_created": 0,
        "native_runtime_stores_ready": False,
        "legacy_ids_must_not_be_used_as_new_native_bindings": True,
        "scientific_pilot_ready": False,
        "missing_entries": len(missing),
    }
    return report, catalog, missing


def validate_runtime_assets(state) -> dict:
    """Revalidate the actual graph/index/binding triple, not just a ready flag."""
    state.validate()
    graph_claims = sum(len(g._claims) for g in state.memory._graphs.values())
    chunks = sum(len(v) for v in state.memory._chunks.values())
    return {
        "native_claims": graph_claims,
        "native_chunks": chunks,
        "binding_records": len(state.bindings.records),
        "binding_hash": state.bindings.fingerprint,
        "access_hash": state.access.fingerprint,
        "valid_at_current_event_cursor": True,
        "independent_human_labels_certified": False,
    }
