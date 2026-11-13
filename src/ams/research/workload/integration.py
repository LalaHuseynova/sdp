"""Load a controlled-workload bundle into native Original SAFE-Mem stores.

Everything here reuses the original write/extraction/chunking/indexing code
(`native.pipeline.make_memory` -> `ObservedMemory`), the research binding
catalog, the evidence ledger and `RuntimeState`. Nothing changes a policy,
prompt, retrieval rule or the original memory code.

Construction calls go through `LayeredClient`: the frozen reproduction cache
first (verbatim MPBench text is expected to hit), then an explicitly supplied
fallback. The fallback is a mock in tests/dry runs and `None` in cache-audit
mode, where a miss is recorded and nothing is sent anywhere.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import fields

from ams.core.prompts import PromptLibrary
from ams.llm.types import ChatRequest, EmbedRequest, Message
from ams.memory.typed import TypedStandingMemory
from ams.research.dynamic import (
    Audit,
    EvidenceSnapshot,
    Finding,
    Policy,
    Provenance,
    Register,
    StoredRecord,
)
from ams.research.dynamic.ledger import LedgerConfig
from ams.research.dynamic.models import canonical, check, digest, event_dict
from ams.research.native.cache import cached_response, validate_embedding
from ams.research.native.construction import sidecars
from ams.research.native.pipeline import make_memory
from ams.research.phase1_data import source_parts
from ams.research.recovery.offline import CHAT_MODEL, EMBED_MODEL, OfflineMiss
from ams.research.retrieval import RecordBinding, SourceBinding
from ams.research.retrieval.replay import ExactReplayClient
from ams.research.sequential.state import RuntimeState
from ams.research.workload import design as D

ORACLE_BASIS = "controlled_audit"  # simulated perfect auditor; verifier_id names the oracle
AUDIT_POLICY_VERSION = "native-all-allow-v1"  # the access version sidecars() creates


class LayeredClient:
    """Frozen cache first, then an explicit fallback; every request is logged.

    `fallback=None` means cache-only: a miss raises OfflineMiss and is logged,
    so the miss count is the exact number of requests a paid stage would need.
    """

    def __init__(self, cache, provider, fallback=None):
        check(provider in {"openrouter", "local"}, "Unexpected provider role")
        self.cache, self.provider, self.fallback = cache, provider, fallback
        self.chats, self.embeddings, self.log = {}, {}, []

    def _request(self, kind, request):
        model = CHAT_MODEL if kind == "chat" else EMBED_MODEL
        check(request.model == model, "Unfrozen construction model")
        key = request.cache_key(self.provider)
        table = self.chats if kind == "chat" else self.embeddings
        if key in table:
            return table[key]
        chars = (
            sum(len(m.content) for m in request.messages)
            if kind == "chat"
            else sum(len(t) for t in request.texts)
        )
        source, response = "cache", None
        if self.cache is not None:
            try:
                payload, _ = self.cache.get(key, kind, self.provider, model)
                response = cached_response(kind, payload)
            except OfflineMiss:
                response = None
        if response is None:
            if self.fallback is None:
                self.log.append(
                    {
                        "kind": kind,
                        "key": key,
                        "source": "miss",
                        "chars": chars,
                        "max_tokens": getattr(request, "max_tokens", None),
                    }
                )
                raise OfflineMiss(f"{kind} cache miss (cache-only mode)") from None
            response = (
                self.fallback.complete(request) if kind == "chat" else self.fallback.embed(request)
            )
            source = "fallback"
        if kind == "embed":
            validate_embedding(response, request)
        table[key] = response
        self.log.append(
            {
                "kind": kind,
                "key": key,
                "source": source,
                "chars": chars,
                "max_tokens": getattr(request, "max_tokens", None),
            }
        )
        return response

    def complete(self, request):
        return self._request("chat", request)

    def embed(self, request):
        return self._request("embed", request)


def classifier_request(prompts: PromptLibrary, query: str) -> ChatRequest:
    """Exactly the request `native.pipeline.freeze_clients` freezes."""
    return ChatRequest(
        (Message("user", prompts.get("classify_use_type", "v2").render(query=query.strip())),),
        CHAT_MODEL,
        temperature=0.0,
        max_tokens=24,
    )


def use_id(group_id: str, question: str) -> str:
    """One use per question. A copy probe asks its seed's question, so it shares
    the use under which that seed was audited; scored siblings do not."""
    return "use_" + digest([group_id, question.strip()])[:24]


def group_rows(rows: dict, group_id: str) -> dict:
    pick = lambda name: [r for r in rows[name] if r["group_id"] == group_id]  # noqa: E731
    return {
        "public": sorted(pick("public/contributions.jsonl"), key=lambda r: r["ingestion_index"]),
        "private": {r["contribution_id"]: r for r in pick("private/contributions.jsonl")},
        "probes": pick("public/probes.jsonl"),
        "private_probes": {r["probe_id"]: r for r in pick("private/probes.jsonl")},
        "overlays": {
            c: {r["contribution_id"]: r for r in pick(f"public/overlays/{c}.jsonl")}
            for c in D.CONDITIONS
        },
        "audits": sorted(pick("private/audit_schedule.jsonl"), key=lambda a: a["order"]),
    }


def construct(group: dict, group_id: str, chat, embed, prompts):
    """Write every contribution with the original code; bind every record.

    Returns the plain original memory plus construction metadata. Attribution
    is by construction: artifact-derived records belong to their contribution's
    external root; principal-turn records to a principal root; a declared
    linked copy shares its original's incident root.
    """
    memory = make_memory(chat, embed, prompts)
    session = "store_" + digest([D.VERSION, group_id])[:24]
    copy_of = {
        cid: p["copy_of"] for cid, p in group["private"].items() if p["role"] == "linked_copy"
    }
    source_bindings, record_bindings, root_members, record_owner = [], [], defaultdict(list), {}
    contributions, sources = [], []
    for row in group["public"]:
        cid = row["contribution_id"]
        priv = group["private"][cid]
        source = {
            "contribution_id": cid,
            "context_id": priv["domain"] or "principal",
            "user_query": row["user_query"],
            "context": row["context"],
            "artifacts": source_parts(cid, row["user_query"], row["context"]),
            "payload_hash": digest([row["user_query"], row["context"]]),
        }
        sources.append(source)
        memory.begin_contribution(session, source)
        start = len(memory._chunks.get(session, ()))
        result = memory.write(
            session_id=session,
            user_query=row["user_query"],
            context=row["context"],
            principal="user",
        )
        mapping, _ = memory.finish_contribution(session)
        graph = memory._graph(session)
        for sid, aid in mapping.items():
            node = graph.source(sid)
            source_bindings.append(
                SourceBinding(
                    session, sid, aid, digest(node.text), str(node.role), node.principal_id
                )
            )
        all_artifacts = tuple(a["artifact_id"] for a in source["artifacts"])
        n_claims = n_chunks = 0
        for entry in result.written:
            claim = graph.claim(entry.entry_id)
            principal = graph.source(claim.source_id).principal_id is not None
            parent_ids = tuple(dict.fromkeys((claim.source_id, *claim.endorsed_by)))
            parents = (
                tuple(dict.fromkeys(mapping[s] for s in parent_ids)) if principal else all_artifacts
            )
            kind = "principal" if principal else "external"
            rid = "r_" + digest([session, cid, claim.claim_id])[:24]
            record_bindings.append(
                RecordBinding(
                    session,
                    claim.claim_id,
                    rid,
                    digest(claim.text),
                    "claim",
                    parent_ids,
                    parents,
                    kind,
                )
            )
            root_cid = copy_of.get(cid, cid) if kind == "external" else cid
            root_members[(root_cid, kind)].append(
                StoredRecord(rid, digest(claim.text), "claim", mapping[claim.source_id])
            )
            record_owner[claim.claim_id] = {
                "record_id": rid,
                "contribution_id": cid,
                "kind": kind,
                "record_kind": "claim",
                "text": claim.text,
                "standing": str(claim.standing),
                "usable_as": entry.metadata.get("usable_as"),
            }
            n_claims += 1
        for chunk in memory._chunks.get(session, ())[start:]:
            principal = all(graph.source(s).principal_id == "user" for s in chunk.source_ids)
            parents = tuple(dict.fromkeys(mapping[s] for s in chunk.source_ids))
            kind = "principal" if principal else "external"
            rid = "r_" + digest([session, cid, chunk.chunk_id])[:24]
            record_bindings.append(
                RecordBinding(
                    session,
                    chunk.chunk_id,
                    rid,
                    digest(chunk.text),
                    "evidence_chunk",
                    chunk.source_ids,
                    parents,
                    kind,
                )
            )
            root_cid = copy_of.get(cid, cid) if kind == "external" else cid
            root_members[(root_cid, kind)].append(
                StoredRecord(rid, digest(chunk.text), "evidence_chunk", parents[0])
            )
            record_owner[chunk.chunk_id] = {
                "record_id": rid,
                "contribution_id": cid,
                "kind": kind,
                "record_kind": "evidence_chunk",
                "text": chunk.text,
                "standing": str(chunk.standing),
                "usable_as": None,
            }
            n_chunks += 1
        contributions.append({"contribution_id": cid, "claims": n_claims, "chunks": n_chunks})
    bindings, access = sidecars(session, source_bindings, record_bindings, sources)
    check(access.version == AUDIT_POLICY_VERSION, "Unexpected access version")
    # Remove the construction observer; the retrieval boundary needs the exact type.
    plain = TypedStandingMemory(
        **{f.name: getattr(memory, f.name) for f in fields(memory) if f.init}
    )
    return plain, {
        "session_id": session,
        "bindings": bindings,
        "access": access,
        "root_members": dict(root_members),
        "record_owner": record_owner,
        "contributions": contributions,
    }


def root_id(group_id: str, cid: str, kind: str) -> str:
    return "root_" + digest([D.VERSION, group_id, cid, kind])[:24]


def registers(group: dict, group_id: str, built: dict, condition: str) -> tuple:
    overlay = group["overlays"][condition]
    events = []
    for (cid, kind), members in sorted(built["root_members"].items()):
        ov = overlay[cid]
        rid = root_id(group_id, cid, kind)
        if kind == "external":
            check(ov["origin"] == "external", "External records from a principal-only input")
            origin = Provenance(
                rid,
                ov["context_id"],
                ov["batch_id"],
                ov["contributor_id"],
                "authenticated_external",
            )
        else:
            origin = Provenance(
                rid,
                ov["context_id"] or "ctx_principal",
                None,
                None,
                "principal",
                principal_id="user",
            )
        events.append(Register("reg_" + digest(rid)[:24], 0, origin, tuple(members)))
    return tuple(events)


def oracle_audits(group: dict, group_id: str, built: dict, evidence: EvidenceSnapshot) -> list:
    """Fixed tickets, verdicts known by construction, complete-bundle findings.

    The reviewed use is the audited contribution's own probe question (its
    MPBench question for an attack seed, its fact question for a benign input).
    Every record registered under the root, including a linked copy's, is
    reviewed, so the ledger's complete-bundle rule holds.
    """
    audits = []
    for n, ticket in enumerate(group["audits"], 1):
        cid = ticket["contribution_id"]
        rid = root_id(group_id, cid, "external")
        members = [r for (_, (root, r)) in evidence.records.items() if root == rid]
        check(bool(members), f"Audited input {cid} produced no external records")
        question = audit_question(group, cid)
        verdict = ticket["verdict"]
        audits.append(
            Audit(
                "audit_" + digest([ticket["ticket_id"], rid])[:24],
                n,
                ticket["ticket_id"],
                rid,
                use_id(group_id, question),
                AUDIT_POLICY_VERSION,
                verdict,
                tuple(
                    Finding(r.record_id, r.content_hash, verdict, "oracle_" + digest([cid])[:16])
                    for r in members
                ),
                True,
                "oracle_by_construction",
                ORACLE_BASIS,
                "oracle_" + digest([group_id, cid, verdict])[:24],
            )
        )
    return audits


def audit_question(group: dict, cid: str) -> str:
    """The audited use: the seed's own MPBench question, or a benign input's fact question."""
    priv = group["private"][cid]
    if priv["role"] == "attack_seed":
        # The copy probes reuse exactly this question.
        for p in group["private_probes"].values():
            if p["kind"].startswith("copy") and cid in p["carriers"]:
                return next(
                    q["question"] for q in group["probes"] if q["probe_id"] == p["probe_id"]
                )
        return "audit:" + cid  # seed without a copy probe: its own (unprobed) use
    sentence = priv["fact"]["sentence"]
    return "audit-benign:" + sentence


def freeze_queries(memory, prompts, chat, embed, questions) -> None:
    """Freeze classifier replies and query embeddings, then swap to exact replay."""
    for q in sorted(set(questions)):
        chat.complete(classifier_request(prompts, q))
        embed.embed(EmbedRequest((q,), EMBED_MODEL))
    replay_chat = ExactReplayClient(key_provider="openrouter", chats=chat.chats)
    memory.client = replay_chat
    memory.embed_client = ExactReplayClient(key_provider="local", embeddings=embed.embeddings)
    memory.use_type.client = replay_chat


def build_states(rows: dict, group_id: str, chat, embed, prompts=None) -> dict:
    """One construction per group; one initial RuntimeState snapshot per condition."""
    prompts = prompts or PromptLibrary()
    group = group_rows(rows, group_id)
    memory, built = construct(group, group_id, chat, embed, prompts)
    freeze_queries(memory, prompts, chat, embed, [q["question"] for q in group["probes"]])
    base = RuntimeState.create(
        memory,
        built["bindings"],
        built["access"],
        EvidenceSnapshot(
            LedgerConfig(built["session_id"], "verified_audits", D.AUDIT_TICKETS),
            registers(group, group_id, built, D.CONDITIONS[0]),
            0,
        ),
        Policy("R"),
        seed=20261108,
    ).dump()
    snapshots, audits = {}, {}
    for condition in D.CONDITIONS:
        state = RuntimeState.load(base)
        evidence = EvidenceSnapshot(
            LedgerConfig(built["session_id"], "verified_audits", D.AUDIT_TICKETS),
            registers(group, group_id, built, condition),
            0,
        )
        state.evidence = evidence
        state.validate()
        check(state.evidence.usage.tickets == 0, "Initial state cannot reveal a finding")
        events = oracle_audits(group, group_id, built, evidence)
        # Validate the full audited prefix now; the runner re-applies it per arm.
        EvidenceSnapshot(evidence.config, (*evidence.events, *events), D.AUDIT_TICKETS)
        audits[condition] = [json.loads(canonical(event_dict(a))) for a in events]
        snapshots[condition] = state.dump()
    return {
        "group_id": group_id,
        "session_id": built["session_id"],
        "snapshots": snapshots,
        "audits": audits,
        "record_owner": built["record_owner"],
        "contributions": built["contributions"],
        "construction_log": {"chat": list(chat.log), "embed": list(embed.log)},
    }
