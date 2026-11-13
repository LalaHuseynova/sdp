"""Versioned cache-only native stores. Preparation, never benchmark execution."""

from __future__ import annotations

import gzip
import json
from collections import Counter, defaultdict
from dataclasses import asdict, fields, replace
from pathlib import Path

from ams.core import sentinel
from ams.core.prompts import PromptLibrary
from ams.eval.use_type import UseTypeClassifier
from ams.llm.types import ChatRequest, EmbedRequest, Message
from ams.memory.typed import TypedStandingMemory
from ams.research.dynamic import EvidenceSnapshot, Policy
from ams.research.dynamic.ledger import LedgerConfig
from ams.research.dynamic.models import canonical, check, digest
from ams.research.execution.session import new_json, prompt_measurement
from ams.research.phase1_common import read_jsonl, rng
from ams.research.provisional.pipeline import validate as validate_provisional
from ams.research.recovery.offline import (
    CHAT_MODEL,
    EMBED_MODEL,
    OfflineMiss,
    ReadOnlyCache,
    sha_file,
)
from ams.research.retrieval.replay import ExactReplayClient
from ams.research.sequential.runner import environment, fingerprints
from ams.research.sequential.state import RuntimeState

from .cache import ConstructionCache, cached_response, validate_embedding
from .construction import ObservedMemory, compare_and_bind, sidecars

SCHEMA = "dynamic-native-cache-preparation-v1"


def grouped_rows(path, ids):
    out = defaultdict(list)
    for row in read_jsonl(path):
        if row["contribution_id"] in ids:
            out[row["contribution_id"]].append(row)
    return out


def make_memory(chat, embed, prompts):
    return ObservedMemory(
        chat,
        CHAT_MODEL,
        embed,
        EMBED_MODEL,
        UseTypeClassifier(chat, CHAT_MODEL, prompts, version="v2"),
        mode="withhold",
        source_cap=None,
        hops=0,
        coreference=False,
        scoped=True,
        max_claims=6,
        detect_conflicts=True,
        prompts=prompts,
        extract_version="v1",
        conflict_version="v1",
        endorsement="sentence",
        retention_sentence_version="v1",
        evidence_slots=4,
        index="flat",
        external_evidence=False,
    )


def freeze_clients(memory, chat, embed, queries, cache):
    """Future runtime has only exact tables; construction transcripts stay separate."""
    query_receipts, missing = [], []
    for query in sorted(set(queries)):
        req = ChatRequest(
            (
                Message(
                    "user",
                    memory.prompts.get("classify_use_type", "v2").render(query=query.strip()),
                ),
            ),
            CHAT_MODEL,
            temperature=0.0,
            max_tokens=24,
        )
        for kind, request, provider, model, table in (
            ("chat", req, "openrouter", CHAT_MODEL, chat.chats),
            ("embed", EmbedRequest((query,), EMBED_MODEL), "local", EMBED_MODEL, embed.embeddings),
        ):
            key = request.cache_key(provider)
            try:
                payload, receipt = cache.get(key, kind, provider, model)
                response = cached_response(kind, payload)
                if kind == "embed":
                    validate_embedding(response, request)
                else:
                    check(type(response.text) is str, "Cached classifier text is not a string")
                table[key] = response
                query_receipts.append({"kind": kind, "request_key": key, "receipt": receipt})
            except OfflineMiss:
                missing.append({"kind": kind, "request_key": key})
    check(not missing, "Original-query replay catalog incomplete; no API fallback")
    chat_replay = ExactReplayClient(key_provider="openrouter", chats=chat.chats)
    embed_replay = ExactReplayClient(key_provider="local", embeddings=embed.embeddings)
    memory.client, memory.embed_client = chat_replay, embed_replay
    memory.use_type.client = chat_replay
    return query_receipts


def prompt_envelope(state, queries):
    """Inspect maximum rendered field lengths without retrieval or model execution."""
    memory = state.memory
    rendered_claims = []
    for graph in memory._graphs.values():
        for claim in graph.claims():
            rendered_claims.append(memory._entry(replace(claim, contested=True), graph).text)
    rendered_chunks = [
        sentinel.render(
            c.chunk_id,
            f"source: {c.label} | verbatim\n{c.text}",
            usable=c.standing.level.name.lower(),
        )
        for rows in memory._chunks.values()
        for c in rows
    ]

    def longest(rows, k):
        return sorted(rows, key=lambda s: len(s.encode()), reverse=True)[:k]

    context = longest(rendered_claims, 4) + longest(rendered_chunks, 4)
    text = "\n".join(f"- {v}" for v in context) or "(nothing)"
    query = longest(queries, 1)[0] if queries else ""
    body = memory.prompts.get("answer_typed", "v2").render(
        query=query, memory=text, required="permission_trust"
    )
    answer = prompt_measurement(
        ChatRequest((Message("user", body),), CHAT_MODEL, temperature=0.0, max_tokens=200)
    )
    top = longest([c.text for g in memory._graphs.values() for c in g.claims()], 2)
    conflict = None
    if len(top) == 2:
        body = memory.prompts.get("detect_conflict", "v1").render(claim_a=top[0], claim_b=top[1])
        conflict = prompt_measurement(
            ChatRequest((Message("user", body),), CHAT_MODEL, temperature=0.0, max_tokens=6)
        )
    return {
        "answer_maximum_rendered_field_proxy": answer,
        "conflict_maximum_rendered_field_proxy": conflict,
        "selection": "longest fields across current store; no relevance/eligibility assumption",
        "actual_retrieval_executed": False,
        "native_gpt_tokens_measured": False,
        "applies_to": "initial constructed store and supplied original questions only",
    }


def build_bag(bag, sources, claims, chunks, written, queries, cache, prompts):
    """One independent new graph, current cached extraction, verified frozen content."""
    order = sorted(bag["source_ids"])
    rng(bag["bag_id"], "provisional-ingestion").shuffle(order)
    session = "store_" + digest(bag["bag_token"])[:24]
    chat, embed = ConstructionCache(cache, "openrouter"), ConstructionCache(cache, "local")
    memory = make_memory(chat, embed, prompts)
    sb, rb, events, links, span_map, verifications = [], [], [], [], {}, []
    for pid in order:
        source = sources[pid]
        memory.begin_contribution(session, source)
        start = len(memory._chunks.get(session, ()))
        result = memory.write(
            session_id=session,
            user_query=source["user_query"],
            context=source["context"],
            principal="user",
        )
        new_chunks = memory._chunks.get(session, ())[start:]
        s, r, e, record_links, spans = compare_and_bind(
            memory,
            session,
            source,
            result.written,
            new_chunks,
            claims[pid],
            chunks[pid],
            written[pid],
        )
        sb.extend(s)
        rb.extend(r)
        events.extend(e)
        links.extend(record_links)
        span_map.update(spans)
        verifications.append(
            {
                "contribution_id": pid,
                "claims": len(result.written),
                "chunks": len(new_chunks),
                "status": "native_constructed_frozen_records_matched",
            }
        )
    evidence = EvidenceSnapshot(LedgerConfig(session, "verified_audits", 5), tuple(events), 0)
    bindings, access = sidecars(session, sb, rb, [sources[p] for p in order])
    query_receipts = freeze_clients(memory, chat, embed, queries, cache)
    # The retrieval boundary intentionally accepts only the exact original type.
    # Remove construction observers without re-running or altering any decision.
    memory = TypedStandingMemory(
        **{f.name: getattr(memory, f.name) for f in fields(memory) if f.init}
    )
    state = RuntimeState.create(memory, bindings, access, evidence, Policy("R"), seed=20261028)
    check(state.evidence.usage.tickets == 0, "Construction must not reveal an audit")
    snapshot = state.dump()
    check(
        RuntimeState.load(snapshot).dump() == snapshot, "Native state is not losslessly restartable"
    )
    return snapshot, {
        "session_id": session,
        "ingestion_order": order,
        "contributions": verifications,
        "record_links": links,
        "source_spans": span_map,
        "construction_receipts": chat.receipts + embed.receipts,
        "original_query_receipts": query_receipts,
        "prompt_envelope": prompt_envelope(state, queries),
        "frozen_query_count": len(set(queries)),
        "unresolved_external_origins": sum(e.origin.attribution == "unknown" for e in events),
        "principal_origins": sum(e.origin.attribution == "principal" for e in events),
    }


def write_gzip(path: Path, body):
    text = (canonical(body) + "\n").encode()
    with path.open("xb") as stream:
        with gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0) as zipped:
            zipped.write(text)
    path.chmod(0o600)


def prepare(repo: Path, prepared: Path, recovered: Path, out: Path):
    check(not out.exists(), "Native preparation output exists; choose a new version")
    prior = validate_provisional(prepared)
    manifest = json.loads((recovered / "recovery_manifest.json").read_text())
    dependencies = {}
    for root, filename in (
        (prepared, "provisional_manifest.json"),
        (recovered, "recovery_manifest.json"),
    ):
        deps = json.loads((root / filename).read_text())
        dependencies[str((root / filename).resolve())] = sha_file(root / filename)
        for name, expected in deps["files"].items():
            path = root / name
            check(sha_file(path) == expected, "Existing preparation output changed")
            dependencies[str(path.resolve())] = expected
    for folder in ("src/ams/research", "src/ams/memory", "src/ams/core"):
        dependencies.update({str(p.resolve()): sha_file(p) for p in (repo / folder).rglob("*.py")})
    dependencies.update({str(p.resolve()): sha_file(p) for p in (repo / "prompts").rglob("*.txt")})
    dependencies[str((repo / "scripts/prepare_dynamic_native.py").resolve())] = sha_file(
        repo / "scripts/prepare_dynamic_native.py"
    )
    for p in (
        repo / "configs/openrouter_mpbench_safemem.yaml",
        repo / "reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md",
    ):
        dependencies[str(p.resolve())] = sha_file(p)
    bags = json.loads((prepared / "private/group_selections.json").read_text())
    ids = {p for b in bags for p in b["source_ids"]}
    check(len(ids) == 640 and len(bags) == 20, "Unexpected provisional coverage")
    source_path = repo / "research_data/mpbench_phase1/public/candidate_inputs.jsonl"
    dependencies[str(source_path.resolve())] = sha_file(source_path)
    sources = {
        r["contribution_id"]: r for r in read_jsonl(source_path) if r["contribution_id"] in ids
    }
    claims = grouped_rows(recovered / "private/claims.jsonl", ids)
    chunks = grouped_rows(recovered / "private/evidence_chunks.jsonl", ids)
    written_path = next(
        Path(p) for p in manifest["input_sha256"] if p.endswith("written_memories-no_defence.jsonl")
    )
    check(
        sha_file(written_path) == manifest["input_sha256"][str(written_path)],
        "Historical write journal changed",
    )
    dependencies[str(written_path.resolve())] = sha_file(written_path)
    private_index = {
        r["original_case_key"]: r["contribution_id"]
        for r in read_jsonl(recovered / "private/evaluator_case_index.jsonl")
    }
    written = {
        private_index[r["cid"]]: r["written"]
        for r in read_jsonl(written_path)
        if private_index[r["cid"]] in ids
    }
    query_index = {
        r["contribution_id"]: r["retrieval_query"]
        for r in read_jsonl(prepared / "private/evaluator_case_index.jsonl")
        if r["contribution_id"] in ids
    }
    caches = [repo / "reports/safemem_full_mpbench/cache/responses.sqlite"]
    for p in caches:
        dependencies[str(p.resolve())] = sha_file(p)
    out.mkdir(parents=True, mode=0o700)
    (out / ".gitignore").write_text("*\n!.gitignore\n")
    native = out / "private"
    native.mkdir(mode=0o700)
    cache, prompts = ReadOnlyCache(caches), PromptLibrary(repo / "prompts")
    results, totals = [], Counter()
    try:
        for bag in bags:
            token = bag["bag_token"]
            try:
                snapshot, crosswalk = build_bag(
                    bag,
                    sources,
                    claims,
                    chunks,
                    written,
                    [query_index[p] for p in bag["source_ids"]],
                    cache,
                    prompts,
                )
            except (ValueError, KeyError) as error:
                # No partial graph is published or silently substituted.
                results.append(
                    {
                        "bag_token": token,
                        "status": "unavailable_offline",
                        "reason": str(error),
                        "error_type": type(error).__name__,
                    }
                )
                print(
                    "Native store unavailable: " + token + " (" + type(error).__name__ + ")",
                    flush=True,
                )
                continue
            target = native / token
            target.mkdir(mode=0o700)
            write_gzip(target / "initial_state.json.gz", snapshot)
            write_gzip(target / "construction_crosswalk.json.gz", crosswalk)
            checksum = sha_file(target / "initial_state.json.gz")
            new_json(
                target / "arms.json",
                {
                    a: {
                        "base_snapshot_sha256": checksum,
                        "policy": asdict(Policy(a)),
                        "separate_graph_instance_required": True,
                    }
                    for a in "RCMS"
                },
            )
            count_claims = sum(v["claims"] for v in crosswalk["contributions"])
            count_chunks = sum(v["chunks"] for v in crosswalk["contributions"])
            results.append(
                {
                    "bag_token": token,
                    "status": "native_preparation_ready_not_scientific_pilot",
                    "session_id": crosswalk["session_id"],
                    "contributions": 32,
                    "claims": count_claims,
                    "chunks": count_chunks,
                    "unresolved_external_origins": crosswalk["unresolved_external_origins"],
                    "principal_origins": crosswalk["principal_origins"],
                    "frozen_original_queries": crosswalk["frozen_query_count"],
                }
            )
            totals.update(
                contributions=32,
                claims=count_claims,
                chunks=count_chunks,
                source_bindings=len(snapshot["bindings"]["sources"]),
                record_bindings=len(snapshot["bindings"]["records"]),
                unknown_origins=crosswalk["unresolved_external_origins"],
                principal_origins=crosswalk["principal_origins"],
            )
            print(
                "Prepared native store "
                + token
                + ": "
                + str(count_claims)
                + " claims / "
                + str(count_chunks)
                + " chunks",
                flush=True,
            )
    finally:
        cache.close()
    report = {
        "schema": SCHEMA,
        "status": "offline_native_preparation_complete"
        if len(results) == 20 and all(r["status"] != "unavailable_offline" for r in results)
        else "partial_offline_native_preparation",
        "stores_prepared": sum(r["status"] != "unavailable_offline" for r in results),
        "stores_unavailable": sum(r["status"] == "unavailable_offline" for r in results),
        "totals": dict(totals),
        "stores": results,
        "previous_provisional_validation": prior,
        "paid_api_calls": 0,
        "new_api_cost_usd": "0",
        "new_audit_verdicts": 0,
        "new_human_annotations": 0,
        "scientific_pilot_ready": False,
        "final_Z_balanced_pilot_generated": False,
        "paid_execution_enabled": False,
        "historical_full_graph_replayed": False,
        "relation_and_object_fields": (
            "from exact cached extraction; not independently verified against historical graph"
        ),
        "attribution_policy": (
            "separate principal roots; unknown external roots; no unverified contributor penalties"
        ),
        "native_gpt_tokenization_performed": False,
        "outcomes_scored": 0,
        "training_runs": 0,
        "model_downloads": 0,
    }
    new_json(out / "preparation_report.json", report)
    for path, checksum in dependencies.items():
        check(sha_file(Path(path)) == checksum, "Input/code changed during native construction")
    files = {str(p.relative_to(out)): sha_file(p) for p in out.rglob("*") if p.is_file()}
    lock = {
        "schema": SCHEMA,
        "files": files,
        "dependencies": dependencies,
        "runtime_fingerprints": fingerprints(),
        "environment": environment(),
        "execution_enabled": False,
    }
    new_json(out / "native_manifest.json", {**lock, "manifest_hash": digest(lock)})
    return report


def verify(out: Path):
    lock = json.loads((out / "native_manifest.json").read_text())
    checksum = lock.pop("manifest_hash")
    check(
        digest(lock) == checksum
        and lock["schema"] == SCHEMA
        and lock["execution_enabled"] is False,
        "Native manifest changed",
    )
    check(
        lock["runtime_fingerprints"] == fingerprints() and lock["environment"] == environment(),
        "Native store runtime environment/code changed",
    )
    for name, expected in lock["files"].items():
        p = out / name
        check(
            p.resolve().is_relative_to(out.resolve()) and sha_file(p) == expected,
            "Native payload modified",
        )
    for name, expected in lock["dependencies"].items():
        check(sha_file(Path(name)) == expected, "Native dependency changed; prepare a new version")
    return {
        "status": "passed",
        "payloads_checked": len(lock["files"]),
        "dependencies_checked": len(lock["dependencies"]),
        "scientific_pilot_ready": False,
    }


def load_store(out: Path, token: str, arm: str):
    """New graph/clients per call. No SDK, run dispatch, policy feedback or paid calls."""
    check(arm in "RCMS" and len(arm) == 1, "Unknown arm")
    check(token and Path(token).name == token and token not in {".", ".."}, "Invalid store token")
    lock = json.loads((out / "native_manifest.json").read_text())
    checksum = lock.pop("manifest_hash")
    check(
        digest(lock) == checksum
        and lock["runtime_fingerprints"] == fingerprints()
        and lock["environment"] == environment(),
        "Native runtime lock changed",
    )
    path = out / "private" / token / "initial_state.json.gz"
    name = str(path.relative_to(out))
    check(
        name in lock["files"] and sha_file(path) == lock["files"][name], "Native snapshot changed"
    )
    descriptor = path.with_name("arms.json")
    check(
        sha_file(descriptor) == lock["files"][str(descriptor.relative_to(out))],
        "Arm descriptor changed",
    )
    check(
        json.loads(descriptor.read_text())[arm]["base_snapshot_sha256"] == sha_file(path),
        "Arm/base mismatch",
    )
    with gzip.open(path, "rt") as stream:
        state = RuntimeState.load(json.load(stream))
    state.policy = Policy(arm)
    state.validate()
    return state
