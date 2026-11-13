"""Invented, offline sequence fixtures. These never supply human or MPBench gold labels."""

from __future__ import annotations

import itertools
import json
from dataclasses import replace
from pathlib import Path

from ams.core.spans import segment
from ams.eval.use_type import UseTypeClassifier
from ams.llm.types import ChatRequest, ChatResponse, EmbedRequest, EmbedResponse, Message, Usage
from ams.research.dynamic import Policy, Provenance, Register, StoredRecord
from ams.research.dynamic.models import digest, event_dict
from ams.research.retrieval import ArtifactGrant, BindingCatalog, RecordBinding, SourceBinding
from ams.research.retrieval.fixture import QUERY, SESSION, build_fixture
from ams.research.retrieval.replay import ExactReplayClient

from .actions import Step
from .state import RuntimeState, access_dump, catalog_dump

INCOMING = "Artificial incoming project has fixture color blue."


def build_state(path: Path, arm="S", *, classifier=False, conflicting=True, incoming_text=INCOMING):
    f = build_fixture(path, evidence_slots=0, external_evidence=False, conflicting=conflicting)
    memory = f.memory
    memory._graph(SESSION)._ids = itertools.count(1000)
    chats = dict(memory.client._chats)
    if classifier:
        prompt = memory.prompts.get("classify_use_type", "v2").render(query=QUERY)
        req = ChatRequest((Message("user", prompt),), memory.model, temperature=0.0, max_tokens=24)
        chats[req.cache_key("fixture")] = ChatResponse(
            "description | none",
            memory.model,
            "fixture",
            Usage(11, 2, 0.000001),
            cached=True,
            raw_finish_reason="stop",
        )
    for claim in memory._graph(SESSION).claims():
        for contested in (False, True):
            entry = memory._entry(replace(claim, contested=contested), memory._graph(SESSION))
            prompt = memory.prompts.get("answer_typed", "v2").render(
                query=QUERY, memory=f"- {entry.text}", required="description"
            )
            req = ChatRequest(
                (Message("user", prompt),), memory.model, temperature=0.0, max_tokens=200
            )
            chats[req.cache_key("fixture")] = ChatResponse(
                f"Artificial answer for {claim.claim_id}.",
                memory.model,
                "fixture",
                Usage(17, 3, 0.0000024),
                cached=True,
                raw_finish_reason="length" if claim.claim_id == "c0" else "stop",
            )
    extraction = memory.prompts.get("extract_typed_claims", memory.extract_version).render(
        query="", context=incoming_text, max_claims=memory.max_claims
    )
    req = ChatRequest((Message("user", extraction),), memory.model, temperature=0.0, max_tokens=900)
    chats[req.cache_key("fixture")] = ChatResponse(
        json.dumps(
            {"claims": [{"text": incoming_text, "type": "description", "subject": "incoming"}]}
        ),
        memory.model,
        "fixture",
        Usage(23, 7, 0.000003),
        cached=True,
        raw_finish_reason="stop",
    )
    memory.client = ExactReplayClient(key_provider="fixture", chats=chats)
    embeddings = dict(memory.embed_client._embeddings)
    req = EmbedRequest((incoming_text,), memory.embed_model)
    embeddings[req.cache_key("fixture")] = EmbedResponse(
        ((1.0, 0.0),), memory.embed_model, "fixture", cached=True
    )
    sentences = tuple(s.text for s in segment(incoming_text))
    for texts in (sentences, ("\n".join(sentences),)):
        req = EmbedRequest(texts, memory.embed_model)
        embeddings[req.cache_key("fixture")] = EmbedResponse(
            tuple((1.0, 0.0) for _ in texts), memory.embed_model, "fixture", cached=True
        )
    memory.embed_client = ExactReplayClient(key_provider="fixture", embeddings=embeddings)
    if classifier:
        memory.use_type = UseTypeClassifier(
            memory.client, memory.model, memory.prompts, version="v2"
        )
    state = RuntimeState.create(
        memory, f.bindings, f.access, f.ledger.snapshot(), Policy(arm), writers=("user", "u1")
    )
    return state, f


def write_step(state: RuntimeState, at: int = 5, *, incoming_text=INCOMING) -> Step:
    """Prepare trusted single-artifact fixture bindings using a disposable offline clone.

    No review, safety inference or real corpus selection is done. The real runner
    repeats original write at the dispatched event and validates these exact IDs.
    """
    copy = RuntimeState.load(state.dump())
    graph = copy.memory._graph(SESSION)
    previous_sources, previous_claims = set(graph._sources), set(graph._claims)
    previous_chunks = {c.chunk_id for c in copy.memory._chunks.get(SESSION, ())}
    copy.memory.write(session_id=SESSION, user_query="", context=incoming_text)
    source_bindings, record_bindings = list(state.bindings.sources), list(state.bindings.records)
    for source in graph._sources.values():
        if source.source_id not in previous_sources:
            artifact = (
                "incoming-external" if source.role == "external_body" else "incoming-principal"
            )
            source_bindings.append(
                SourceBinding(
                    SESSION,
                    source.source_id,
                    artifact,
                    digest(source.text),
                    str(source.role),
                    source.principal_id,
                )
            )
    stored = []
    for item, kind in [
        *((c, "claim") for c in graph.claims() if c.claim_id not in previous_claims),
        *(
            (c, "evidence_chunk")
            for c in copy.memory._chunks.get(SESSION, ())
            if c.chunk_id not in previous_chunks
        ),
    ]:
        native = item.claim_id if kind == "claim" else item.chunk_id
        parents = (item.source_id,) if kind == "claim" else item.source_ids
        logical = f"incoming-{native}"
        stored.append(StoredRecord(logical, digest(item.text), kind, "incoming-external"))
        record_bindings.append(
            RecordBinding(
                SESSION,
                native,
                logical,
                digest(item.text),
                kind,
                parents,
                ("incoming-external",),
                "external",
            )
        )
    access = replace(
        state.access,
        grants=(
            *state.access.grants,
            ArtifactGrant("incoming-external", ("user", "R1"), ("read", "describe")),
            ArtifactGrant("incoming-principal", ("user",), ("read",)),
        ),
    )
    register = Register(
        "incoming-registration",
        at,
        Provenance("incoming-root", "email", "new-batch", "u1", "authenticated_external"),
        tuple(stored),
    )
    return Step.make(
        "incoming-write",
        at,
        "write",
        {
            "session_id": SESSION,
            "user_query": "",
            "context": incoming_text,
            "principal": "user",
            "writer": "u1",
            "bindings": catalog_dump(
                BindingCatalog(
                    state.bindings.episode_id, tuple(source_bindings), tuple(record_bindings)
                )
            ),
            "access": access_dump(access),
            "registrations": [event_dict(register)],
        },
    )


def query(event_id, at, *, answer=True, k=1):
    return Step.query(
        event_id,
        at,
        session_id=SESSION,
        query=QUERY,
        use_id="artificial-descriptive-use",
        k=k,
        answer=answer,
    )


def sequence(state: RuntimeState, fixture) -> list[Step]:
    access = replace(
        state.access,
        version="v2",
        grants=tuple(
            replace(g, readers=("R1",)) if g.artifact_id == "artifact-0" else g
            for g in state.access.grants
        ),
    )
    return [
        query("before", 0),
        query("conflict", 0, answer=False, k=2),
        Step.reveal("audit-reveal", 4, fixture.audit("root-0", at=4)),
        query("after", 4),
        Step.make("random-probe", 4, "draw", {"choices": ["probe-a", "probe-b", "probe-c"]}),
        Step.reveal(
            "correction",
            7,
            fixture.audit("root-0", "safe_for_use", event="review", at=7, supersedes="a1"),
        ),
        query("recovered", 7),
        Step.make("revoke", 8, "policy", {"access": access_dump(access)}),
        query("after-revocation", 8),
    ]
