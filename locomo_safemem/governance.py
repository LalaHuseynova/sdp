"""Policy-governance layer for SAFE-Mem's *dialogue* writes (the only new semantics of the study).

The frozen research layer (`ams.research.retrieval`, `ams.research.sequential.state`) was built for
MPBench's write path, where every non-principal source is an `external_body`. SAFE-Mem's LoCoMo
ingestion (`TypedStandingMemory.write_dialogue`) stores the other speaker's turns as
`counterpart_turn` sources (standing ATTRIBUTE about that person, not DESCRIPTION/GLOBAL), which the
frozen catalog rejects ("narrow MPBench path") and whose validation treats every non-`external_body`
source as a principal source.

This module subclasses the frozen classes with exactly one semantic generalization:

    a source is a *principal* source iff its role is principal_turn / authenticated_principal;
    every other role (external_body, counterpart_turn) is an *external* source.

On MPBench data (roles principal_turn / external_body only) the rule is identical to the frozen
one, which `tests/test_governance.py` checks on a frozen Option B Stage-1 store: identical
retrieval for every arm and probe. Nothing else changes: retrieval (`GovernedRetrieval.
retrieve_with_trace`), policies, ledger, lineage and S2-ID composition are inherited unchanged.
"""

from __future__ import annotations

import copy
import functools
import random
from dataclasses import dataclass
from types import MappingProxyType

from ams.core.standing import SpanRole
from ams.memory.typed import TypedStandingMemory
from ams.research.dynamic import EvidenceSnapshot, Policy
from ams.research.dynamic.ledger import LedgerConfig
from ams.research.dynamic.models import check, content_hash, fields_only, name, parse_event
from ams.research.retrieval import BindingCatalog, GovernedRetrieval, RecordBinding
from ams.research.retrieval.metadata import names
from ams.research.sequential import state as ST

GOVERNANCE_VERSION = "locomo-safemem-governance-v1"
PRINCIPAL_ROLES = frozenset({str(SpanRole.PRINCIPAL_TURN), str(SpanRole.AUTHENTICATED_PRINCIPAL)})
EXTERNAL_ROLES = frozenset({str(SpanRole.EXTERNAL_BODY), str(SpanRole.COUNTERPART_TURN)})


@dataclass(frozen=True)
class DialogueSourceBinding:
    """`SourceBinding` (frozen) plus the `counterpart_turn` role; same fields and checks."""

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
        check(self.role in PRINCIPAL_ROLES | EXTERNAL_ROLES, "Unsupported source role")
        if self.principal_id is not None:
            name(self.principal_id, "principal_id")
        # external_body has no owner; principal and counterpart turns name their speaker
        check((self.principal_id is not None) == (self.role != str(SpanRole.EXTERNAL_BODY)),
              "Principal and external ownership must stay separate")


@dataclass(frozen=True)
class DialogueBindingCatalog(BindingCatalog):
    """Frozen `BindingCatalog` with dialogue sources; `validate` differs only in which roles count
    as principal sources (see module docstring)."""

    def __post_init__(self):
        name(self.episode_id, "episode_id")
        check(type(self.sources) is tuple
              and all(type(s) is DialogueSourceBinding for s in self.sources),
              "Expected immutable source bindings")
        check(type(self.records) is tuple and all(type(r) is RecordBinding for r in self.records),
              "Expected immutable record bindings")
        sources = {(s.session_id, s.source_id): s for s in self.sources}
        records = {(r.session_id, r.native_id): r for r in self.records}
        check(len(sources) == len(self.sources) and len(records) == len(self.records),
              "Duplicate native source/record bindings")
        check(len({r.record_id for r in self.records}) == len(self.records),
              "Logical record IDs must be unique across stores")
        for r in self.records:
            check(all((r.session_id, sid) in sources for sid in r.source_ids), "Unmapped record source")
            check({sources[r.session_id, sid].artifact_id for sid in r.source_ids} <= set(r.artifact_ids),
                  "Record must inherit every structural source policy")
        object.__setattr__(self, "_sources", MappingProxyType(sources))
        object.__setattr__(self, "_records", MappingProxyType(records))

    def validate(self, memory, session: str, evidence: EvidenceSnapshot, access) -> None:
        """The frozen `BindingCatalog.validate`, line for line, except `principal_sources`."""
        from ams.research.dynamic.models import digest

        check(self.episode_id == evidence.config.episode_id, "Episode provenance mismatch")
        graph = memory._graphs.get(session)
        claims = list(graph.claims()) if graph is not None else []
        chunks = list(memory._chunks.get(session, ()))
        actual = {(c.claim_id, "claim") for c in claims} | {(c.chunk_id, "evidence_chunk") for c in chunks}
        expected = {(r.native_id, r.record_kind) for r in self.records if r.session_id == session}
        check(actual == expected, "Missing/stale bindings or future record metadata")
        for source in self.sources:
            if source.session_id != session:
                continue
            check(graph is not None and source.source_id in graph._sources, "Missing/future source binding")
            live = graph.source(source.source_id)
            check((digest(live.text), str(live.role), live.principal_id)
                  == (source.content_hash, source.role, source.principal_id),
                  "Stale source content/role/ownership")
            check(access.contains(source.artifact_id), "Source lacks current artifact policy")
        for item, kind in [*((c, "claim") for c in claims), *((c, "evidence_chunk") for c in chunks)]:
            native = item.claim_id if kind == "claim" else item.chunk_id
            binding = self.record(session, native)
            if kind == "claim":
                check(not item.derived_from, "Claim derivation requires a later supported adapter")
                source_ids = tuple(dict.fromkeys((*((item.source_id,) if item.source_id else ()),
                                                  *item.endorsed_by)))
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
            check(stored.record_kind == kind and stored.artifact_id in binding.artifact_ids,
                  "Ledger record type/artifact mismatch")
            principal_sources = [self._sources[session, sid] for sid in primary_ids
                                 if self._sources[session, sid].role in PRINCIPAL_ROLES]  # <- the change
            if binding.origin_class == "principal":
                check(len(principal_sources) == len(primary_ids) and bool(primary_ids)
                      and origin.attribution == "principal"
                      and all(s.principal_id == origin.principal_id for s in principal_sources),
                      "External records cannot be attributed to the principal")
            elif binding.origin_class == "external":
                check(not principal_sources and bool(primary_ids)
                      and origin.attribution in {"unknown", "authenticated_external"},
                      "Principal records cannot become contributor evidence")
            else:
                check(origin.attribution == "unknown", "Ambiguous attribution cannot propagate")
            check(all(access.contains(a) for a in binding.artifact_ids),
                  "Record lacks a current parent artifact policy")

    @functools.cached_property
    def fingerprint(self) -> str:  # same value as the frozen property; the catalog is immutable
        return BindingCatalog.fingerprint.fget(self)

    def validate_once(self, memory, session, evidence, access) -> None:
        """`validate`, skipped when this exact (memory structure, evidence, access) was validated.
        Retrieval never writes records; only SAFE-Mem's `contested` flags change, which validate
        does not read."""
        graph = memory._graphs.get(session)
        key = (id(memory), session, len(list(graph.claims())) if graph else 0, len(memory._chunks.get(session, ())),
               evidence.revision, access.fingerprint)
        done = self.__dict__.setdefault("_validated", set())
        if key not in done:
            self.validate(memory, session, evidence, access)
            done.add(key)

    @classmethod
    def from_dict(cls, value: dict) -> DialogueBindingCatalog:
        check(type(value) is dict and set(value) == {"episode_id", "sources", "records"},
              "Unexpected catalog fields")
        sources = tuple(DialogueSourceBinding(**fields_only(s, DialogueSourceBinding)) for s in value["sources"])
        records = []
        for row in value["records"]:
            body = fields_only(row, RecordBinding)
            body["source_ids"], body["artifact_ids"] = tuple(body["source_ids"]), tuple(body["artifact_ids"])
            records.append(RecordBinding(**body))
        return cls(value["episode_id"], sources, tuple(records))

    @classmethod
    def from_frozen(cls, catalog: BindingCatalog) -> DialogueBindingCatalog:
        """An MPBench catalog re-typed (for the equivalence test); content unchanged."""
        return cls.from_dict(ST.catalog_dump(catalog))


@dataclass(frozen=True)
class DialogueGovernedRetrieval(GovernedRetrieval):
    """The frozen `GovernedRetrieval`; only its constructor type check admits the dialogue catalog.
    `retrieve_with_trace` (SAFE-Mem's admission, cap, conflict handling, policy hooks) is inherited."""

    def __post_init__(self):
        check(type(self.memory) is TypedStandingMemory, "Expected Original TypedStandingMemory")
        check(type(self.bindings) is DialogueBindingCatalog and type(self.policy) is Policy,
              "Explicit trusted bindings and comparison policy required")
        check(type(self.effects_enabled) is bool, "Explicit research-effects flag required")
        self._supported()
        for key in ("claim_candidate_cap", "chunk_candidate_cap"):
            check(getattr(self, key) is None, "Candidate caps are not used in this study")


class _OnceCatalog:
    """Catalog view whose `validate` is `validate_once` (everything else delegated)."""

    def __init__(self, catalog):
        self._c = catalog

    def __getattr__(self, item):
        return getattr(self._c, item)

    def validate(self, memory, session, evidence, access):
        self._c.validate_once(memory, session, evidence, access)


class DialogueRuntimeState(ST.RuntimeState):
    """Frozen `RuntimeState` whose reader and snapshot loader use the dialogue catalog."""

    def reader(self):
        r = DialogueGovernedRetrieval(self.memory, self.bindings, self.policy, self.effects_enabled,
                                      self.claim_candidate_cap, self.chunk_candidate_cap)
        if getattr(self, "fast_validation", False):
            object.__setattr__(r, "bindings", _OnceCatalog(self.bindings))
        return r

    @classmethod
    def load(cls, body: dict, *, verify: bool = True):
        """Frozen `RuntimeState.load` with `DialogueBindingCatalog.from_dict`. `verify=False` skips
        only the final lossless dump-compare (an integrity re-check of an already verified body)."""
        check(body["schema"] == ST.SCHEMA, "Unsupported runtime snapshot")
        clients = [ST.RecordedReplayClient.load(c) for c in body["clients"]]
        libraries = [ST.prompt_load(v) for v in body["libraries"]]
        u = body["use_type"]
        if u["kind"] == "fixed":
            use = ST.FixedUse(ST.Rung(u["rung"]), u["n_unparsed"])
        else:
            check(u["kind"] == "classifier", "Unknown classifier")
            use = ST.UseTypeClassifier(clients[u["client"]], u["model"], libraries[u["prompts"]], u["version"])
            use._cache = {k: ST.Rung(v) for k, v in u["cache"].items()}
            use._subjects, use.n_unparsed = dict(u["subjects"]), u["n_unparsed"]
        memory = TypedStandingMemory(clients[body["client"]], embed_client=clients[body["embed_client"]],
                                     use_type=use, prompts=libraries[body["memory_prompts"]], **body["settings"])
        memory._graphs = {key: ST.graph_load(v) for key, v in body["graphs"]}
        memory._vectors = {key: ST.index_load(v) for key, v in body["vectors"]}
        memory._chunk_vecs = {key: ST.index_load(v) for key, v in body["chunk_vectors"]}
        memory._chunks = {key: [ST.Chunk(c["chunk_id"], c["text"], ST.standing(c["standing"]),
                                         tuple(c["source_ids"]), c["label"]) for c in chunks]
                          for key, chunks in body["chunks"]}
        memory._entity_names = {key: (list(n), ST.index_load(v)) for key, n, v in body["entity_names"]}

        def tuples(value):
            return tuple(tuples(v) for v in value) if isinstance(value, list) else value

        rng = random.Random()
        rng.setstate(tuples(body["rng"]))
        e = body["evidence"]
        result = cls(memory, DialogueBindingCatalog.from_dict(body["bindings"]), ST.access_load(body["access"]),
                     EvidenceSnapshot(LedgerConfig(**e["config"]), tuple(parse_event(v) for v in e["events"]),
                                      e["as_of"]),
                     Policy(**body["policy"]), rng, clients[body["answer_client"]], body["answer_model"], clients,
                     body["clock"], body["effects_enabled"], body["claim_candidate_cap"],
                     body["chunk_candidate_cap"], tuple(body["writers"]), tuple(body["policy_history"]))
        result.validate()
        if verify:
            check(result.dump() == body, "Lossy or extra runtime snapshot fields")
        return result


def prepare_state(snapshot: dict, audits: list, arm: str, tickets: int, revealed: bool = True,
                  verify: bool = False) -> DialogueRuntimeState:
    """`ams.research.workload.runner.prepare_state` with the condition's own ticket budget (MPBench
    fixes it at 5; LoCoMo conditions have 1-12 tickets). Identical for every arm of a condition."""
    from ams.research.dynamic.models import parse_event as pe

    state = DialogueRuntimeState.load(snapshot, verify=verify)
    state.policy = Policy("R" if arm == "static" else arm)
    state.effects_enabled = arm != "static"
    with_audits = arm != "static" and revealed
    if with_audits:
        state.evidence = EvidenceSnapshot(state.evidence.config,
                                          (*state.evidence.events, *(pe(a) for a in audits)), tickets)
        state.clock = tickets
    state.validate()
    check(state.evidence.usage.tickets == (tickets if with_audits else 0), "Unequal audit budget")
    return state


def check_names(values, label):  # re-export for the store builder
    names(tuple(values), label)


def fast_revisions():
    """MPBench's tested `memoized_evidence_revisions()` (caches the hash of an immutable evidence
    snapshot; no decision changes), unless LoCoMo's feasibility module (imported by the v1/v2
    scenario generator) has already installed its equivalent per-instance cache on the class."""
    import contextlib

    from ams.research.evidence_memoization import memoized_evidence_revisions

    if isinstance(EvidenceSnapshot.__dict__["revision"], property):
        return memoized_evidence_revisions()
    return contextlib.nullcontext()


DECIDE_SENTINEL_EVERY = 500  # every 500th cached decision is recomputed by the frozen decide (fail-closed)
_DECIDE_STATS = {"calls": 0, "hits": 0, "checked": 0}


def fast_runtime():
    """Runtime-only caches of pure functions of immutable frozen objects, restored on exit; no
    decision changes (tests compare against uncached runs, and sentinels re-check during runs):
      * the evidence revision (MPBench's `memoized_evidence_revisions`);
      * `Policy.fingerprint`, keyed by object identity with the object retained (no id reuse);
      * `Policy.decide`: everything except the score is a function of (policy, snapshot, record,
        use, policy version, ACL, authority); for a record without any active audit finding,
        `EvidenceSnapshot.local_status` is "unreviewed" for every use, so the use drops out of the
        key. The score is the frozen formula `original_score - weight * penalty` (None if ineligible)."""
    import contextlib
    from dataclasses import replace

    @contextlib.contextmanager
    def ctx():
        orig_fp, orig_decide = Policy.fingerprint, Policy.decide
        fps, decisions, found = {}, {}, {}

        def fingerprint(policy):
            key = id(policy)
            if key not in fps:
                if len(fps) >= 4096:
                    fps.clear()
                fps[key] = (policy, orig_fp.fget(policy))
            return fps[key][1]

        def findings_of(snapshot):
            sid = id(snapshot)
            if sid not in found:
                if len(found) >= 512:
                    found.clear()
                found[sid] = (snapshot, frozenset((f.record_id, f.content_hash)
                                                  for a in snapshot._state.active_audits for f in a.findings))
            return found[sid][1]

        def decide(policy, candidate, snapshot):
            _DECIDE_STATS["calls"] += 1
            rec = (candidate.record_id, candidate.content_hash)
            use = candidate.use_id if rec in findings_of(snapshot) else None
            key = (id(policy), id(snapshot), *rec, use, candidate.policy_version, candidate.acl_allowed,
                   candidate.authority_allowed)
            hit = decisions.get(key)
            if hit is None:
                if len(decisions) >= 400_000:
                    decisions.clear()
                d = orig_decide(policy, candidate, snapshot)
                decisions[key] = (policy, snapshot, d)
                return d
            _DECIDE_STATS["hits"] += 1
            d0 = hit[2]
            d = replace(d0, use_id=candidate.use_id,
                        adjusted_score=(candidate.original_score - policy.weight * d0.penalty) if d0.eligible else None)
            if _DECIDE_STATS["hits"] % DECIDE_SENTINEL_EVERY == 0:
                check(d == orig_decide(policy, candidate, snapshot), "Cached decision differs from the frozen decide")
                _DECIDE_STATS["checked"] += 1
            return d

        Policy.fingerprint = property(fingerprint)
        Policy.decide = decide
        try:
            with fast_revisions():
                yield _DECIDE_STATS
        finally:
            Policy.fingerprint, Policy.decide = orig_fp, orig_decide

    return ctx()


def derive_state(base: DialogueRuntimeState, audits: list, arm: str, tickets: int, revealed: bool = True,
                 fast: bool = True) -> DialogueRuntimeState:
    """`prepare_state` without re-loading the snapshot: a shallow copy of the store's base state that
    shares the (read-only) memory, bindings and access. SAFE-Mem's per-claim `contested` flags (the
    only memory state retrieval mutates) are restored to the base values and replay histories are
    cleared, so every arm starts exactly where a fresh `RuntimeState.load` would (tested)."""
    from ams.research.dynamic.models import parse_event as pe

    initial = base.__dict__.setdefault("_contested0", {(k, c.claim_id): c.contested
                                                       for k, g in base.memory._graphs.items() for c in g.claims()})
    for k, g in base.memory._graphs.items():
        for c in g.claims():
            c.contested = initial[(k, c.claim_id)]
    for client in base.clients:
        client.history.clear()
    state = copy.copy(base)
    state.__dict__.pop("reader", None)
    state.policy = Policy("R" if arm == "static" else arm)
    state.effects_enabled = arm != "static"
    state.fast_validation = fast
    with_audits = arm != "static" and revealed
    state.evidence = base.evidence
    state.clock = base.clock
    if with_audits:
        state.evidence = EvidenceSnapshot(base.evidence.config, (*base.evidence.events, *(pe(a) for a in audits)),
                                          tickets)
        state.clock = tickets
    state.validate()
    check(state.evidence.usage.tickets == (tickets if with_audits else 0), "Unequal audit budget")
    return state


# ----------------------------------------------------------------------------- exact fast path
def fast_retrieve(state, session_id: str, query: str, use_id: str, k: int, principal: str):
    """`GovernedRetrieval.retrieve_with_trace(...).retrieval` step for step, minus the bookkeeping
    that cannot change the context in this study: ACL evaluation (every artifact is granted to the
    reader by construction, asserted per store by `assert_all_allow`) and the per-candidate trace
    objects. Every decision-relevant call is the frozen one: SAFE-Mem's `use_type.required/subject`,
    `_admits`, `_cap`, `_resolve_conflicts`, `_entry`, the embedding index scores, and the state's
    policy `decide` (frozen Policy, or the frozen lineage / sv2 wrappers). Equality with the frozen
    path is tested on whole stores and re-checked on a sample of every real run (fail-closed).
    Returns (entries, required) exactly as `RetrievalResult` would hold them."""
    from ams.core import sentinel
    from ams.core.lattice import Rung, coarsen
    from ams.core.lattice import principal as principal_domain
    from ams.memory.base import MemoryEntry
    from ams.research.dynamic import Audit, Candidate

    reader = state.reader()
    inner = getattr(reader, "inner", reader)  # sv2 _GatedReader wraps the governed reader
    memory, evidence, access, bindings = inner.memory, state.evidence, state.access, state.bindings
    policy, effects = inner.policy, inner.effects_enabled
    graph = memory._graphs.get(session_id)
    claims = list(graph.claims()) if graph is not None else []
    chunks = list(memory._chunks.get(session_id, ()))
    if not claims and not chunks:
        entries, required_name = (), memory.mode
        return _gate(reader, query, entries), required_name
    required = coarsen(memory.use_type.required(query), memory.granularity)
    asked_in = principal_domain(principal)
    about = (getattr(memory.use_type, "subject", None) or (lambda q: ""))(query)
    from ams.llm.types import EmbedRequest

    qv = memory.embed_client.embed(EmbedRequest((query,), memory.embed_model)).vectors[0]
    claim_index, chunk_index = memory._vectors.get(session_id), memory._chunk_vecs.get(session_id)
    csims = claim_index.scores(qv) if claim_index is not None else {}
    esims = chunk_index.scores(qv) if chunk_index is not None else {}
    prior = {a.policy_version for a in evidence.events
             if type(a) is Audit and a.use_id == use_id and a.policy_version != access.version}

    def assess(native, raw, authority, source_allowed):
        b = bindings.record(session_id, native)
        cand = Candidate(b.record_id, b.content_hash, use_id, access.version, raw, True,
                         bool(authority and source_allowed))
        d = policy.decide(cand, evidence)
        eligible, adjusted = d.eligible, d.adjusted_score
        if (effects and d.eligible and d.local_status != "safe_for_use"
                and any(evidence.local_status(b.record_id, b.content_hash, use_id, v) == "unsafe" for v in prior)):
            eligible, adjusted = False, None
        if not effects:
            eligible = bool(authority and source_allowed)
            adjusted = raw if eligible else None
        return (raw, bool(authority), bool(source_allowed), eligible, adjusted)

    ct = {c.claim_id: assess(c.claim_id, csims.get(c.claim_id, -1.0),
                             memory._admits(c.claim_type, c.standing, required, asked_in, about), True) for c in claims}
    et = ({c.chunk_id: assess(c.chunk_id, esims.get(c.chunk_id, -1.0),
                              memory._admits(c.standing.level, c.standing, required, asked_in, about),
                              memory.external_evidence or c.standing.level > Rung.DESCRIPTION) for c in chunks}
          if memory.evidence_slots else {})

    def pool(items, key, lookup):
        visible = sorted((i for i in items if lookup[key(i)][1] and lookup[key(i)][2]),
                         key=lambda i: lookup[key(i)][0], reverse=True)
        return sorted((i for i in visible if lookup[key(i)][3]), key=lambda i: lookup[key(i)][4], reverse=True)

    ranked_claims = pool(claims, lambda c: c.claim_id, ct)
    ranked_chunks = pool(chunks if et else [], lambda c: c.chunk_id, et)
    order = ranked_claims[:k] if not effects else ranked_claims  # static all-allow top-k quirk
    served = memory._cap(order, k, {}) if k else []
    selected_chunks = ranked_chunks[: memory.evidence_slots]
    if memory.detect_conflicts:
        memory._resolve_conflicts(graph, served)
    entries = [memory._entry(c, graph, required=required) for c in served]
    for chunk in selected_chunks:
        usable = required if required > Rung.DESCRIPTION else Rung.DESCRIPTION
        entries.append(MemoryEntry(chunk.chunk_id, sentinel.render(
            chunk.chunk_id, f"source: {chunk.label} | verbatim\n{chunk.text}", usable=usable.name.lower()),
            chunk.source_ids, {"evidence": True, "standing": str(chunk.standing),
                               "usable_as": usable.name.lower(), "raw_text": chunk.text}))
    return _gate(reader, query, tuple(entries)), required.name.lower()


def _gate(reader, query, entries):
    """The frozen S2-ID gate (`sv2._GatedReader`) when the reader carries it."""
    if hasattr(reader, "sensitive") and hasattr(reader, "owner") and hasattr(reader, "inner"):
        untrusted = any(reader.owner.get(e.entry_id, {}).get("kind") != "principal" for e in entries)
        if untrusted and reader.sensitive(query):
            reader.denied += 1
            return ()
    return entries


def assert_all_allow(state) -> None:
    """Every bound artifact readable by the requester ("user", "read"): the fast path may skip ACLs."""
    arts = {a for r in state.bindings.records for a in r.artifact_ids}
    check(all(state.access.allows((a,), "user", "read") for a in sorted(arts)), "Non-trivial ACLs: use the frozen path")
