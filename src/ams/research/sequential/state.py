"""Explicit JSON state codec. No pickle, model construction or implicit graph replay."""

from __future__ import annotations

import itertools
import json
import math
import random
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from ams.core.lattice import Domain, Rung, Standing
from ams.core.prompts import PromptLibrary
from ams.core.standing import SpanRole
from ams.eval.use_type import FixedUse, UseTypeClassifier
from ams.memory.evidence import Chunk
from ams.memory.graph import Claim, ClaimGraph, Entity, Source
from ams.memory.index import VectorIndex
from ams.memory.typed import TypedStandingMemory
from ams.research.dynamic import EvidenceSnapshot, Policy
from ams.research.dynamic.ledger import LedgerConfig
from ams.research.dynamic.models import canonical, check, digest, event_dict, parse_event
from ams.research.retrieval import AccessSnapshot, ArtifactGrant, BindingCatalog, GovernedRetrieval

from .clients import RecordedReplayClient, accounting

SCHEMA = "sequential-offline-v1"


def standing(data):
    return Standing(Rung(data["level"]), Domain(**data["domain"]))


def index_dump(index: VectorIndex) -> dict:
    check(type(index) is VectorIndex, "Only flat VectorIndex can be checkpointed")
    with index._lock:
        rows = [[float(v) for v in row] for row in index._rows]
        check(all(math.isfinite(v) for row in rows for v in row), "Nonfinite vector")
        return {"ids": list(index._ids), "rows": rows}


def index_load(body: dict) -> VectorIndex:
    check(
        set(body) == {"ids", "rows"} and len(body["ids"]) == len(body["rows"]),
        "Invalid flat-index state",
    )
    check(
        not body["rows"] or (len({len(v) for v in body["rows"]}) == 1 and len(body["rows"][0]) > 0),
        "Inconsistent vector dimensions",
    )
    result = VectorIndex()
    result.add(body["ids"], body["rows"])
    check(index_dump(result) == body, "Invalid vector state")
    return result


def graph_dump(graph: ClaimGraph) -> dict:
    counter = graph._ids.__reduce__()[1]
    check(
        type(graph._ids) is itertools.count
        and len(counter) in {1, 2}
        and (len(counter) == 1 or counter[1] == 1),
        "Unsupported graph ID generator",
    )
    return {
        "coreference": graph.coreference,
        "next_id": counter[0],
        "claims": [asdict(v) for v in graph._claims.values()],
        "sources": [asdict(v) for v in graph._sources.values()],
        "entities": [asdict(v) for v in graph._entities.values()],
        **{
            key: list(getattr(graph, key).items())
            for key in ("_by_entity", "_by_source", "_after", "_prev")
        },
    }


def graph_load(body: dict) -> ClaimGraph:
    check(
        set(body)
        == {
            "coreference",
            "next_id",
            "claims",
            "sources",
            "entities",
            "_by_entity",
            "_by_source",
            "_after",
            "_prev",
        },
        "Unknown graph fields",
    )
    graph = ClaimGraph(coreference=body["coreference"])
    for value in body["sources"]:
        row = dict(value)
        row["role"] = SpanRole(row["role"])
        graph._sources[row["source_id"]] = Source(**row)
    for value in body["claims"]:
        row = dict(value)
        row["claim_type"], row["standing"] = Rung(row["claim_type"]), standing(row["standing"])
        for key in ("derived_from", "endorsed_by"):
            row[key] = tuple(row[key])
        graph._claims[row["claim_id"]] = Claim(**row)
    graph._entities = {r["entity_id"]: Entity(**r) for r in body["entities"]}
    for key in ("_by_entity", "_by_source", "_after", "_prev"):
        setattr(graph, key, dict(body[key]))
    graph._ids = itertools.count(body["next_id"])
    check(json.loads(canonical(graph_dump(graph))) == body, "Lossy graph restoration")
    return graph


def access_dump(value: AccessSnapshot) -> dict:
    return {"version": value.version, "grants": [asdict(g) for g in value.grants]}


def access_load(body: dict) -> AccessSnapshot:
    check(set(body) == {"version", "grants"}, "Unknown access fields")
    return AccessSnapshot(
        body["version"],
        tuple(
            ArtifactGrant(
                v["artifact_id"], tuple(v["readers"]), tuple(v["operations"]), tuple(v["parents"])
            )
            for v in body["grants"]
        ),
    )


def catalog_dump(value: BindingCatalog) -> dict:
    return {
        "episode_id": value.episode_id,
        "sources": [asdict(s) for s in value.sources],
        "records": [asdict(r) for r in value.records],
    }


def evidence_dump(value: EvidenceSnapshot) -> dict:
    return {
        "config": asdict(value.config),
        "events": [event_dict(e) for e in value.events],
        "as_of": value.as_of,
    }


def prompt_dump(lib: PromptLibrary) -> dict:
    root = lib.root.resolve()
    return {
        "root": str(root),
        "used": lib.fingerprint(),
        "files": {
            str(p.relative_to(root)): digest(p.read_text()) for p in sorted(root.rglob("*.txt"))
        },
    }


def prompt_load(body: dict) -> PromptLibrary:
    check(set(body) == {"root", "used", "files"}, "Unknown prompt-library fields")
    lib = PromptLibrary(Path(body["root"]))
    current = prompt_dump(lib)
    check(current["files"] == body["files"], "Prompt files changed since checkpoint")
    lib._used = dict(body["used"])
    return lib


@dataclass
class RuntimeState:
    memory: TypedStandingMemory
    bindings: BindingCatalog
    access: AccessSnapshot
    evidence: EvidenceSnapshot
    policy: Policy
    rng: random.Random
    answer_client: RecordedReplayClient
    answer_model: str
    clients: list[RecordedReplayClient]
    clock: int = 0
    effects_enabled: bool = True
    claim_candidate_cap: int | None = None
    chunk_candidate_cap: int | None = None
    writers: tuple[str, ...] = ("user",)
    policy_history: tuple[str, ...] = ()

    @classmethod
    def create(
        cls,
        memory,
        bindings,
        access,
        evidence,
        policy,
        *,
        seed=20261028,
        answer_client=None,
        answer_model=None,
        writers=("user",),
        **options,
    ):
        originals, clients = {}, []

        def capture(client):
            if id(client) not in originals:
                originals[id(client)] = RecordedReplayClient.capture(client)
                clients.append(originals[id(client)])
            return originals[id(client)]

        answer = capture(answer_client or memory.client)
        memory.client, memory.embed_client = capture(memory.client), capture(memory.embed_client)
        if type(memory.use_type) is UseTypeClassifier:
            memory.use_type.client = capture(memory.use_type.client)
        result = cls(
            memory,
            bindings,
            access,
            evidence,
            policy,
            random.Random(seed),
            answer,
            answer_model or memory.model,
            clients,
            clock=evidence.as_of,
            writers=tuple(writers),
            policy_history=(access.version,),
            **options,
        )
        result.validate()
        return result

    def reader(self):
        return GovernedRetrieval(
            self.memory,
            self.bindings,
            self.policy,
            self.effects_enabled,
            self.claim_candidate_cap,
            self.chunk_candidate_cap,
        )

    def validate(self):
        self.reader()
        check(
            type(self.rng) is random.Random and self.clock >= self.evidence.as_of,
            "Invalid runtime clock/RNG",
        )
        for session in set(self.memory._graphs) | {r.session_id for r in self.bindings.records}:
            self.bindings.validate(self.memory, session, self.evidence, self.access)
        check(
            not (self.memory._parts or self.memory._chunk_parts or self.memory._chunk_by_id),
            "Partitioned/auxiliary indexes cannot be silently omitted",
        )
        for i, client in enumerate(self.clients):
            check(type(client) is RecordedReplayClient, "Only offline recorded clients supported")
            client.client_id = str(i)

    def usage(self) -> dict:
        return {"audit": asdict(self.evidence.usage), "inference": accounting(self.clients)}

    def dump(self) -> dict:
        self.validate()
        m = self.memory
        refs = {id(c): i for i, c in enumerate(self.clients)}
        libraries, plibs = {}, []

        def library(lib):
            if id(lib) not in libraries:
                libraries[id(lib)] = len(plibs)
                plibs.append(prompt_dump(lib))
            return libraries[id(lib)]

        if type(m.use_type) is FixedUse:
            use = {"kind": "fixed", **asdict(m.use_type)}
        else:
            check(type(m.use_type) is UseTypeClassifier, "Unsupported query classifier")
            u = m.use_type
            use = {
                "kind": "classifier",
                "client": refs[id(u.client)],
                "model": u.model,
                "version": u.version,
                "prompts": library(u.prompts),
                "cache": u._cache,
                "subjects": u._subjects,
                "n_unparsed": u.n_unparsed,
            }
        settings = {
            f.name: getattr(m, f.name)
            for f in fields(m)
            if not f.name.startswith("_")
            and f.name not in {"client", "embed_client", "use_type", "prompts"}
        }
        body = {
            "schema": SCHEMA,
            "settings": settings,
            "clients": [c.dump() for c in self.clients],
            "client": refs[id(m.client)],
            "embed_client": refs[id(m.embed_client)],
            "answer_client": refs[id(self.answer_client)],
            "answer_model": self.answer_model,
            "memory_prompts": library(m.prompts),
            "libraries": plibs,
            "use_type": use,
            "graphs": [[key, graph_dump(g)] for key, g in m._graphs.items()],
            "vectors": [[key, index_dump(v)] for key, v in m._vectors.items()],
            "chunk_vectors": [[key, index_dump(v)] for key, v in m._chunk_vecs.items()],
            "chunks": [[key, [asdict(c) for c in chunks]] for key, chunks in m._chunks.items()],
            "entity_names": [
                [key, names, index_dump(index)] for key, (names, index) in m._entity_names.items()
            ],
            "bindings": catalog_dump(self.bindings),
            "access": access_dump(self.access),
            "evidence": evidence_dump(self.evidence),
            "policy": asdict(self.policy),
            "rng": self.rng.getstate(),
            "clock": self.clock,
            "effects_enabled": self.effects_enabled,
            "claim_candidate_cap": self.claim_candidate_cap,
            "chunk_candidate_cap": self.chunk_candidate_cap,
            "writers": self.writers,
            "policy_history": self.policy_history,
        }
        return json.loads(canonical(body))

    @classmethod
    def load(cls, body: dict):
        check(body["schema"] == SCHEMA, "Unsupported runtime snapshot")
        clients = [RecordedReplayClient.load(c) for c in body["clients"]]
        libraries = [prompt_load(v) for v in body["libraries"]]
        u = body["use_type"]
        if u["kind"] == "fixed":
            use = FixedUse(Rung(u["rung"]), u["n_unparsed"])
        else:
            check(u["kind"] == "classifier", "Unknown classifier")
            use = UseTypeClassifier(
                clients[u["client"]], u["model"], libraries[u["prompts"]], u["version"]
            )
            use._cache = {k: Rung(v) for k, v in u["cache"].items()}
            use._subjects, use.n_unparsed = dict(u["subjects"]), u["n_unparsed"]
        memory = TypedStandingMemory(
            clients[body["client"]],
            embed_client=clients[body["embed_client"]],
            use_type=use,
            prompts=libraries[body["memory_prompts"]],
            **body["settings"],
        )
        memory._graphs = {key: graph_load(v) for key, v in body["graphs"]}
        memory._vectors = {key: index_load(v) for key, v in body["vectors"]}
        memory._chunk_vecs = {key: index_load(v) for key, v in body["chunk_vectors"]}
        memory._chunks = {
            key: [
                Chunk(
                    c["chunk_id"],
                    c["text"],
                    standing(c["standing"]),
                    tuple(c["source_ids"]),
                    c["label"],
                )
                for c in chunks
            ]
            for key, chunks in body["chunks"]
        }
        memory._entity_names = {
            key: (list(names), index_load(v)) for key, names, v in body["entity_names"]
        }

        def tuples(value):
            return tuple(tuples(v) for v in value) if isinstance(value, list) else value

        rng = random.Random()
        rng.setstate(tuples(body["rng"]))
        e = body["evidence"]
        result = cls(
            memory,
            BindingCatalog.from_dict(body["bindings"]),
            access_load(body["access"]),
            EvidenceSnapshot(
                LedgerConfig(**e["config"]), tuple(parse_event(v) for v in e["events"]), e["as_of"]
            ),
            Policy(**body["policy"]),
            rng,
            clients[body["answer_client"]],
            body["answer_model"],
            clients,
            body["clock"],
            body["effects_enabled"],
            body["claim_candidate_cap"],
            body["chunk_candidate_cap"],
            tuple(body["writers"]),
            tuple(body["policy_history"]),
        )
        result.validate()
        check(result.dump() == body, "Lossy or extra runtime snapshot fields")
        return result
