"""Immutable, trusted sidecars. No inference from display labels or case gold."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from types import MappingProxyType

from ams.core.standing import SpanRole
from ams.research.dynamic.ledger import EvidenceSnapshot
from ams.research.dynamic.models import check, content_hash, digest, fields_only, name


def names(values: tuple[str, ...], label: str, *, nonempty: bool = True) -> None:
    check(type(values) is tuple and (bool(values) or not nonempty), f"Expected {label} tuple")
    for value in values:
        name(value, label)
    check(len(set(values)) == len(values), f"Duplicate {label}")


@dataclass(frozen=True)
class ArtifactGrant:
    artifact_id: str
    readers: tuple[str, ...]
    operations: tuple[str, ...]
    parents: tuple[str, ...] = ()

    def __post_init__(self):
        name(self.artifact_id, "artifact_id")
        names(self.readers, "readers", nonempty=False)
        names(self.operations, "operations", nonempty=False)
        names(self.parents, "artifact parents", nonempty=False)


@dataclass(frozen=True)
class AccessSnapshot:
    """Intersection of explicit grants over all trusted parents; no permissive default."""

    version: str
    grants: tuple[ArtifactGrant, ...]
    _grants: object = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        name(self.version, "policy version")
        check(
            type(self.grants) is tuple and all(type(g) is ArtifactGrant for g in self.grants),
            "Expected immutable artifact grants",
        )
        index = {g.artifact_id: g for g in self.grants}
        check(len(index) == len(self.grants), "Duplicate artifact grants")
        done = set()

        def visit(key, visiting):
            check(key in index, "Missing parent artifact policy")
            check(key not in visiting, "Cyclic artifact policy inheritance")
            if key not in done:
                for parent in index[key].parents:
                    visit(parent, visiting | {key})
                done.add(key)

        for key in index:
            visit(key, set())
        object.__setattr__(self, "_grants", MappingProxyType(index))

    @property
    def fingerprint(self) -> str:
        return digest({"version": self.version, "grants": [asdict(g) for g in self.grants]})

    def contains(self, artifact_id: str) -> bool:
        return artifact_id in self._grants

    def allows(self, artifacts: tuple[str, ...], requester: str, operation: str) -> bool:
        names(artifacts, "record artifacts")
        name(requester, "requester")
        name(operation, "operation")
        seen, todo = set(), list(artifacts)
        allowed = True
        while todo:
            key = todo.pop()
            check(key in self._grants, "Missing current artifact policy")
            if key in seen:
                continue
            seen.add(key)
            grant = self._grants[key]
            allowed &= (
                requester in grant.readers
                and "read" in grant.operations
                and operation in grant.operations
            )
            todo.extend(grant.parents)
        return bool(allowed)


@dataclass(frozen=True)
class SourceBinding:
    session_id: str
    source_id: str
    artifact_id: str
    content_hash: str
    role: str
    principal_id: str | None

    def __post_init__(self):
        for key in ("session_id", "source_id", "artifact_id", "role"):
            name(getattr(self, key), key)
        content_hash(self.content_hash)
        check(
            self.role in {"principal_turn", "authenticated_principal", "external_body"},
            "Unsupported source role on the narrow MPBench path",
        )
        if self.principal_id is not None:
            name(self.principal_id, "principal_id")
        check(
            (self.principal_id is not None) == (self.role != "external_body"),
            "Principal and external ownership must stay separate",
        )


@dataclass(frozen=True)
class RecordBinding:
    session_id: str
    native_id: str
    record_id: str
    content_hash: str
    record_kind: str
    source_ids: tuple[str, ...]
    artifact_ids: tuple[str, ...]
    origin_class: str

    def __post_init__(self):
        for key in ("session_id", "native_id", "record_id"):
            name(getattr(self, key), key)
        content_hash(self.content_hash)
        check(self.record_kind in {"claim", "evidence_chunk"}, "Invalid record kind")
        names(self.source_ids, "record source IDs")
        names(self.artifact_ids, "record artifact IDs")
        check(
            self.origin_class in {"external", "principal", "ambiguous"},
            "Explicit origin class required",
        )


@dataclass(frozen=True)
class BindingCatalog:
    """Native IDs are store-local; logical IDs are episode-wide. All mappings are trusted.

    Structural source links do not authenticate authorship. In particular, the
    original lexical `_overlap` assignment alone cannot justify an authenticated
    external root. Ambiguous claims need an unknown root and all plausible ACL
    parents. A curated sidecar is required before an actual annotated pilot.
    """

    episode_id: str
    sources: tuple[SourceBinding, ...]
    records: tuple[RecordBinding, ...]
    _sources: object = field(init=False, repr=False, compare=False)
    _records: object = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        name(self.episode_id, "episode_id")
        check(
            type(self.sources) is tuple and all(type(s) is SourceBinding for s in self.sources),
            "Expected immutable source bindings",
        )
        check(
            type(self.records) is tuple and all(type(r) is RecordBinding for r in self.records),
            "Expected immutable record bindings",
        )
        sources = {(s.session_id, s.source_id): s for s in self.sources}
        records = {(r.session_id, r.native_id): r for r in self.records}
        check(
            len(sources) == len(self.sources) and len(records) == len(self.records),
            "Duplicate native source/record bindings",
        )
        check(
            len({r.record_id for r in self.records}) == len(self.records),
            "Logical record IDs must be unique across stores",
        )
        for r in self.records:
            check(
                all((r.session_id, sid) in sources for sid in r.source_ids),
                "Unmapped record source",
            )
            check(
                {sources[r.session_id, sid].artifact_id for sid in r.source_ids}
                <= set(r.artifact_ids),
                "Record must inherit every structural source policy",
            )
        object.__setattr__(self, "_sources", MappingProxyType(sources))
        object.__setattr__(self, "_records", MappingProxyType(records))

    @property
    def fingerprint(self) -> str:
        return digest(
            {
                "episode_id": self.episode_id,
                "sources": [asdict(s) for s in self.sources],
                "records": [asdict(r) for r in self.records],
            }
        )

    def record(self, session: str, native_id: str) -> RecordBinding:
        check((session, native_id) in self._records, "Missing record provenance binding")
        return self._records[session, native_id]

    def validate(
        self, memory, session: str, evidence: EvidenceSnapshot, access: AccessSnapshot
    ) -> None:
        """Check every available record BEFORE query classification/embedding/model calls."""
        check(self.episode_id == evidence.config.episode_id, "Episode provenance mismatch")
        graph = memory._graphs.get(session)
        claims = list(graph.claims()) if graph is not None else []
        chunks = list(memory._chunks.get(session, ()))
        actual = {(c.claim_id, "claim") for c in claims} | {
            (c.chunk_id, "evidence_chunk") for c in chunks
        }
        expected = {(r.native_id, r.record_kind) for r in self.records if r.session_id == session}
        check(actual == expected, "Missing/stale bindings or future record metadata")
        for source in self.sources:
            if source.session_id != session:
                continue
            check(
                graph is not None and source.source_id in graph._sources,
                "Missing/future source binding",
            )
            live = graph.source(source.source_id)
            check(
                (digest(live.text), str(live.role), live.principal_id)
                == (source.content_hash, source.role, source.principal_id),
                "Stale source content/role/ownership",
            )
            check(access.contains(source.artifact_id), "Source lacks current artifact policy")
        for item, kind in [
            *((c, "claim") for c in claims),
            *((c, "evidence_chunk") for c in chunks),
        ]:
            native = item.claim_id if kind == "claim" else item.chunk_id
            binding = self.record(session, native)
            if kind == "claim":
                check(not item.derived_from, "Claim derivation requires a later supported adapter")
                source_ids = tuple(
                    dict.fromkeys(
                        (*((item.source_id,) if item.source_id else ()), *item.endorsed_by)
                    )
                )
                primary_ids = (item.source_id,) if item.source_id else ()
            else:
                source_ids = tuple(dict.fromkeys(item.source_ids))
                primary_ids = source_ids
            check(set(source_ids) == set(binding.source_ids), "Stale/incomplete source parent map")
            check(digest(item.text) == binding.content_hash, "Stale memory content version")
            key = binding.record_id, binding.content_hash
            check(key in evidence.records, "Record not yet registered in evidence snapshot")
            root_id, stored = evidence.records[key]
            origin = evidence.roots[root_id]
            check(
                stored.record_kind == kind and stored.artifact_id in binding.artifact_ids,
                "Ledger record type/artifact mismatch",
            )
            principal_sources = [
                self._sources[session, sid]
                for sid in primary_ids
                if self._sources[session, sid].role != str(SpanRole.EXTERNAL_BODY)
            ]
            if binding.origin_class == "principal":
                check(
                    len(principal_sources) == len(primary_ids)
                    and bool(primary_ids)
                    and origin.attribution == "principal"
                    and all(s.principal_id == origin.principal_id for s in principal_sources),
                    "External records cannot be attributed to the principal",
                )
            elif binding.origin_class == "external":
                check(
                    not principal_sources
                    and bool(primary_ids)
                    and origin.attribution in {"unknown", "authenticated_external"},
                    "Principal records cannot become contributor evidence",
                )
            else:
                check(origin.attribution == "unknown", "Ambiguous attribution cannot propagate")
            check(
                all(access.contains(a) for a in binding.artifact_ids),
                "Record lacks a current parent artifact policy",
            )

    @classmethod
    def from_dict(cls, value: dict) -> BindingCatalog:
        """Allowlisted import; evaluator case dictionaries and extra gold fields fail."""
        check(
            type(value) is dict and set(value) == {"episode_id", "sources", "records"},
            "Unexpected catalog fields",
        )
        check(
            type(value["sources"]) is list and type(value["records"]) is list,
            "Expected source/record arrays",
        )
        sources = tuple(SourceBinding(**fields_only(s, SourceBinding)) for s in value["sources"])
        records = []
        for row in value["records"]:
            body = fields_only(row, RecordBinding)
            check(
                type(body["source_ids"]) is list and type(body["artifact_ids"]) is list,
                "Expected source/artifact ID arrays",
            )
            body["source_ids"], body["artifact_ids"] = (
                tuple(body["source_ids"]),
                tuple(body["artifact_ids"]),
            )
            records.append(RecordBinding(**body))
        return cls(value["episode_id"], sources, tuple(records))
