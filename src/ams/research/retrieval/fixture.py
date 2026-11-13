"""Invented graph/sidecars for software checks only; no MPBench cases or annotations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from ams.core.lattice import Rung
from ams.core.standing import SpanRole
from ams.eval.use_type import FixedUse
from ams.llm.types import ChatRequest, ChatResponse, EmbedRequest, EmbedResponse, Message
from ams.memory.evidence import Chunk
from ams.memory.graph import Claim, Source
from ams.memory.index import VectorIndex
from ams.memory.typed import TypedStandingMemory
from ams.research.dynamic import Audit, EvidenceLedger, Finding, Provenance, Register, StoredRecord
from ams.research.dynamic.models import digest

from .adapter import RetrievalContext
from .metadata import AccessSnapshot, ArtifactGrant, BindingCatalog, RecordBinding, SourceBinding
from .replay import ExactReplayClient

QUERY = "What do the fixture notes state?"
SESSION = "artificial-store"
EPISODE = "artificial-retrieval-episode"
USE = "artificial-descriptive-use"


@dataclass
class Fixture:
    memory: TypedStandingMemory
    bindings: BindingCatalog
    access: AccessSnapshot
    ledger: EvidenceLedger
    records: dict[str, tuple[StoredRecord, ...]]

    def context(self, *, access=None, evidence=None, requester="user"):
        return RetrievalContext(
            evidence or self.ledger.snapshot(), access or self.access, USE, requester
        )

    def audit(self, root: str, verdict="unsafe", *, event="a1", at=1, supersedes=None):
        return Audit(
            event,
            at,
            f"ticket-{event}",
            root,
            USE,
            "v1",
            verdict,
            tuple(
                Finding(r.record_id, r.content_hash, verdict, "fixture://span")
                for r in self.records[root]
            ),
            True,
            "artificial-reviewer",
            "artificial_fixture",
            "fixture://invented-review",
            supersedes,
        )


def build_fixture(
    path: Path, *, external_evidence=False, conflicting=False, source_cap=None, evidence_slots=4
) -> Fixture:
    ledger = EvidenceLedger.create(
        path, episode_id=EPISODE, audit_limit=20, mode="artificial_fixture"
    )
    client = ExactReplayClient(
        key_provider="fixture",
        embeddings={
            EmbedRequest((QUERY,), "fixture-embed").cache_key("fixture"): EmbedResponse(
                ((1.0, 0.0),), "fixture-embed", "fixture", cached=True
            )
        },
    )
    memory = TypedStandingMemory(
        client,
        "fixture-chat",
        client,
        "fixture-embed",
        FixedUse(Rung.DESCRIPTION),
        mode="withhold",
        hops=0,
        evidence_slots=evidence_slots,
        external_evidence=external_evidence,
        source_cap=source_cap,
        detect_conflicts=conflicting,
    )
    graph = memory._graph(SESSION)
    sources, bindings, grants, records = [], [], [], {}
    texts = []
    for i in range(10):
        root, art, sid = f"root-{i}", f"artifact-{i}", f"s{i}"
        text = f"Artificial note {i} reports fixture value {i + 17}."
        texts.append(text)
        principal = i >= 6
        source = graph.add_source(
            Source(
                sid,
                "repeated-display-label",
                SpanRole.PRINCIPAL_TURN if principal else SpanRole.EXTERNAL_BODY,
                text,
                "user" if principal else None,
            )
        )
        context = "file_and_doc" if i == 3 else "email"
        batch = "batch-2" if i == 2 else "batch-1"
        unknown = i == 5
        origin = Provenance(
            root,
            context,
            batch,
            None if principal or unknown else "u2" if i == 4 else "u1",
            "principal" if principal else "unknown" if unknown else "authenticated_external",
            "innocent-uploader",
            "user" if principal else None,
        )
        logical = (
            StoredRecord(f"logical-c{i}", digest(text), "claim", art),
            StoredRecord(f"logical-e{i}", digest(text), "evidence_chunk", art),
        )
        records[root] = logical
        ledger.append(Register(f"register-{i}", 0, origin, logical))
        graph.add_claim(
            Claim(
                f"c{i}",
                text,
                Rung.DESCRIPTION,
                source.standing(),
                sid,
                subject_id="fixture-entity" if i < 2 else f"entity-{i}",
                relation="status" if conflicting and i < 2 else "",
            )
        )
        chunk = Chunk(f"e{i}", text, source.standing(), (sid,), source.artifact)
        memory._chunks.setdefault(SESSION, []).append(chunk)
        score = 0.99 - 0.07 * i
        vector = (score, math.sqrt(1 - score * score))
        memory._vectors.setdefault(SESSION, VectorIndex()).add([f"c{i}"], [vector])
        memory._chunk_vecs.setdefault(SESSION, VectorIndex()).add([f"e{i}"], [vector])
        sources.append(
            SourceBinding(SESSION, sid, art, digest(text), str(source.role), source.principal_id)
        )
        for native, record in zip((f"c{i}", f"e{i}"), logical, strict=True):
            bindings.append(
                RecordBinding(
                    SESSION,
                    native,
                    record.record_id,
                    record.content_hash,
                    record.record_kind,
                    (sid,),
                    (art,),
                    "principal" if principal else "external",
                )
            )
        grants.append(ArtifactGrant(art, ("user", "R1", "audit_service"), ("read", "describe")))
    if conflicting:
        prompt = memory.prompts.get("detect_conflict", memory.conflict_version).render(
            claim_a=texts[0], claim_b=texts[1]
        )
        req = ChatRequest((Message("user", prompt),), "fixture-chat", temperature=0.0, max_tokens=6)
        memory.client = ExactReplayClient(
            key_provider="fixture",
            chats={
                req.cache_key("fixture"): ChatResponse(
                    "contradict", "fixture-chat", "fixture", cached=True, raw_finish_reason="stop"
                )
            },
        )
    return Fixture(
        memory,
        BindingCatalog(EPISODE, tuple(sources), tuple(bindings)),
        AccessSnapshot("v1", tuple(grants)),
        ledger,
        records,
    )
