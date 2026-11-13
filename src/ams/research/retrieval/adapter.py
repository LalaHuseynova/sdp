"""Narrow retrieval integration without changing Original SAFE-Mem.

Uses a preconstructed original memory and explicit per-request immutable sidecars.
Only selected, currently allowed claims reach the original conflict checker.
No transport/client factories, audits, detector calls or answering are added.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ams.core import sentinel
from ams.core.lattice import Rung, coarsen
from ams.core.lattice import principal as principal_domain
from ams.memory.base import MemoryEntry, RetrievalResult
from ams.memory.typed import TypedStandingMemory
from ams.research.dynamic import Audit, Candidate, Decision, EvidenceSnapshot, Policy
from ams.research.dynamic.models import check, digest, integer, name

from .metadata import AccessSnapshot, BindingCatalog


@dataclass(frozen=True)
class RetrievalContext:
    evidence: EvidenceSnapshot
    access: AccessSnapshot
    use_id: str
    requester: str
    operation: str = "read"

    def __post_init__(self):
        check(
            type(self.evidence) is EvidenceSnapshot and type(self.access) is AccessSnapshot,
            "Explicit immutable evidence and policy snapshots required",
        )
        for key in ("use_id", "requester", "operation"):
            name(getattr(self, key), key)


@dataclass(frozen=True)
class CandidateTrace:
    native_id: str
    record_id: str
    record_kind: str
    original_score: float
    original_authority_allowed: bool
    original_source_allowed: bool
    artifact_ids: tuple[str, ...]
    decision: Decision
    in_candidate_pool: bool = False
    selected: bool = False


@dataclass(frozen=True)
class RetrievalTrace:
    episode_id: str
    session_id: str
    query_hash: str
    use_id: str
    principal: str
    requester: str
    operation: str
    policy_version: str
    access_hash: str
    binding_hash: str
    configuration_hash: str
    evidence_revision: str
    evidence_cursor: int
    available_at: int
    effects_enabled: bool
    claim_limit: int
    evidence_limit: int
    candidates: tuple[CandidateTrace, ...]
    selected_ids: tuple[str, ...]
    supplied_context: tuple[str, ...]
    # Filled slots whose item was beyond the original cosine top-k/top-m.
    claim_replacements: int
    chunk_replacements: int
    contested_before: tuple[tuple[str, bool], ...]
    contested_after: tuple[tuple[str, bool], ...]


@dataclass(frozen=True)
class RetrievalOutcome:
    retrieval: RetrievalResult
    trace: RetrievalTrace


@dataclass(frozen=True)
class GovernedRetrieval:
    """Single-threaded adapter over one arm's own original graph/index state.

    No default context or cached eligibility: every call rechecks current versions.
    `effects_enabled=False` is the static diagnostic: disables audit/risk effects,
    while ACLs remain binding. With all-allow ACLs it preserves original selection,
    including the original pre-cap top-k behavior. Research arms share full-pool
    refill under source caps. The reproduced default source_cap=None has no such
    original underfill difference.
    """

    memory: TypedStandingMemory
    bindings: BindingCatalog
    policy: Policy
    effects_enabled: bool = True
    claim_candidate_cap: int | None = None
    chunk_candidate_cap: int | None = None

    def __post_init__(self):
        check(type(self.memory) is TypedStandingMemory, "Expected Original TypedStandingMemory")
        check(
            type(self.bindings) is BindingCatalog and type(self.policy) is Policy,
            "Explicit trusted bindings and comparison policy required",
        )
        check(type(self.effects_enabled) is bool, "Explicit research-effects flag required")
        self._supported()
        for key in ("claim_candidate_cap", "chunk_candidate_cap"):
            if getattr(self, key) is not None:
                integer(getattr(self, key), key)
        check(
            self.effects_enabled
            or (self.claim_candidate_cap is None and self.chunk_candidate_cap is None),
            "Static parity mode requires uncapped original candidate universe",
        )

    def _supported(self) -> None:
        m = self.memory
        check(
            m.index == "flat" and m.mode == "withhold" and m.hops == 0,
            "Research retrieval supports flat + withhold + hops=0 only",
        )
        integer(m.evidence_slots, "evidence_slots")
        if m.source_cap is not None:
            integer(m.source_cap, "source_cap", 1)

    @property
    def configuration_hash(self) -> str:
        return digest(
            {
                "version": "governed-flat-withhold-v1",
                "policy": self.policy.fingerprint,
                "effects_enabled": self.effects_enabled,
                "claim_candidate_cap": self.claim_candidate_cap,
                "chunk_candidate_cap": self.chunk_candidate_cap,
                "mode": self.memory.mode,
                "index": self.memory.index,
                "hops": self.memory.hops,
                "source_cap": self.memory.source_cap,
                "evidence_slots": self.memory.evidence_slots,
                "external_evidence": self.memory.external_evidence,
                "granularity": self.memory.granularity,
                "scoped": self.memory.scoped,
                "detect_conflicts": self.memory.detect_conflicts,
                "chat_model": self.memory.model,
                "embedding_model": self.memory.embed_model,
                "temperature": self.memory.temperature,
                "conflict_version": self.memory.conflict_version,
                "query_classifier": type(self.memory.use_type).__qualname__,
                "query_classifier_version": getattr(self.memory.use_type, "version", None),
                "fixed_required_rung": getattr(self.memory.use_type, "rung", None),
                "used_memory_prompts": self.memory.prompts.fingerprint(),
                "used_classifier_prompts": (
                    self.memory.use_type.prompts.fingerprint()
                    if hasattr(self.memory.use_type, "prompts")
                    else {}
                ),
            }
        )

    def retrieve(
        self,
        *,
        session_id: str,
        query: str,
        context: RetrievalContext,
        k: int = 4,
        principal: str = "user",
    ) -> RetrievalResult:
        return self.retrieve_with_trace(
            session_id=session_id, query=query, context=context, k=k, principal=principal
        ).retrieval

    def retrieve_with_trace(
        self,
        *,
        session_id: str,
        query: str,
        context: RetrievalContext,
        k: int = 4,
        principal: str = "user",
    ) -> RetrievalOutcome:
        self._supported()  # mutable original settings must not open an unguarded fallback
        integer(k, "k")
        name(session_id, "session_id")
        name(principal, "task principal")
        check(
            isinstance(query, str) and type(context) is RetrievalContext,
            "Expected query and explicit retrieval context",
        )
        memory, evidence, access = self.memory, context.evidence, context.access
        self.bindings.validate(memory, session_id, evidence, access)
        graph = memory._graphs.get(session_id)
        claims = list(graph.claims()) if graph is not None else []
        chunks = list(memory._chunks.get(session_id, ()))
        before = tuple((c.claim_id, c.contested) for c in claims)
        traces = []

        def finish(result, claim_replacements=0, chunk_replacements=0):
            ids = tuple(entry.entry_id for entry in result.entries)
            trace = RetrievalTrace(
                evidence.config.episode_id,
                session_id,
                digest(query),
                context.use_id,
                principal,
                context.requester,
                context.operation,
                access.version,
                access.fingerprint,
                self.bindings.fingerprint,
                self.configuration_hash,
                evidence.revision,
                evidence.cursor,
                evidence.as_of,
                self.effects_enabled,
                k,
                memory.evidence_slots,
                tuple(replace(t, selected=t.native_id in ids) for t in traces),
                ids,
                tuple(entry.text for entry in result.entries),
                claim_replacements,
                chunk_replacements,
                before,
                tuple((c.claim_id, c.contested) for c in claims),
            )
            return RetrievalOutcome(result, trace)

        if not claims and not chunks:
            return finish(RetrievalResult(mode=memory.mode))
        # These original calls consume query text only, never memory records.
        required = coarsen(memory.use_type.required(query), memory.granularity)
        asked_in = principal_domain(principal)
        about = (getattr(memory.use_type, "subject", None) or (lambda q: ""))(query)
        # Reuse the original request type/model; no provider is constructed here.
        from ams.llm.types import EmbedRequest

        qv = memory.embed_client.embed(EmbedRequest((query,), memory.embed_model)).vectors[0]
        claim_index = memory._vectors.get(session_id)
        chunk_index = memory._chunk_vecs.get(session_id)
        csims = claim_index.scores(qv) if claim_index is not None else {}
        esims = chunk_index.scores(qv) if chunk_index is not None else {}
        prior_policy_versions = {
            a.policy_version
            for a in evidence.events
            if type(a) is Audit
            and a.use_id == context.use_id
            and a.policy_version != access.version
        }

        def assess(native, raw, authority, source_allowed):
            binding = self.bindings.record(session_id, native)
            allowed = access.allows(binding.artifact_ids, context.requester, context.operation)
            candidate = Candidate(
                binding.record_id,
                binding.content_hash,
                context.use_id,
                access.version,
                raw,
                allowed,
                bool(authority and source_allowed),
            )
            decision = self.policy.decide(candidate, evidence)
            if (
                self.effects_enabled
                and decision.eligible
                and decision.local_status != "safe_for_use"
                and any(
                    evidence.local_status(
                        binding.record_id, binding.content_hash, context.use_id, version
                    )
                    == "unsafe"
                    for version in prior_policy_versions
                )
            ):
                # A changed policy does not prove that an earlier unsafe use is safe.
                # This is shared containment pending review, not a new unsafe label/vote.
                decision = replace(
                    decision,
                    eligible=False,
                    adjusted_score=None,
                    reason="policy_changed_recheck_required",
                )
            if not self.effects_enabled:
                eligible = allowed and authority and source_allowed
                reason = (
                    "acl_denied"
                    if not allowed
                    else "authority_denied"
                    if not (authority and source_allowed)
                    else "research_effects_disabled"
                )
                decision = replace(
                    decision,
                    eligible=bool(eligible),
                    reason=reason,
                    penalty=0.0,
                    adjusted_score=raw if eligible else None,
                    active_scopes=(),
                    counts=(),
                )
            trace = CandidateTrace(
                native,
                binding.record_id,
                binding.record_kind,
                raw,
                bool(authority),
                bool(source_allowed),
                binding.artifact_ids,
                decision,
            )
            traces.append(trace)
            return trace

        ctrace = {
            c.claim_id: assess(
                c.claim_id,
                csims.get(c.claim_id, -1.0),
                memory._admits(c.claim_type, c.standing, required, asked_in, about),
                True,
            )
            for c in claims
        }
        etrace = (
            {
                c.chunk_id: assess(
                    c.chunk_id,
                    esims.get(c.chunk_id, -1.0),
                    memory._admits(c.standing.level, c.standing, required, asked_in, about),
                    memory.external_evidence or c.standing.level > Rung.DESCRIPTION,
                )
                for c in chunks
            }
            if memory.evidence_slots
            else {}
        )

        def pool(items, key, lookup, cap):
            original = sorted(
                (
                    item
                    for item in items
                    if lookup[key(item)].original_authority_allowed
                    and lookup[key(item)].original_source_allowed
                ),
                key=lambda item: lookup[key(item)].original_score,
                reverse=True,
            )
            # ACLs precede the common, risk-independent candidate cap.
            visible = [
                item for item in original if lookup[key(item)].decision.reason != "acl_denied"
            ]
            universe = visible if cap is None else visible[:cap]
            ids = {key(item) for item in universe}
            ranked = sorted(
                (item for item in universe if lookup[key(item)].decision.eligible),
                key=lambda item: lookup[key(item)].decision.adjusted_score,
                reverse=True,
            )
            return original, ranked, ids

        original_claims, ranked_claims, cp = pool(
            claims, lambda c: c.claim_id, ctrace, self.claim_candidate_cap
        )
        original_chunks, ranked_chunks, ep = pool(
            chunks if etrace else [], lambda c: c.chunk_id, etrace, self.chunk_candidate_cap
        )
        traces = [replace(t, in_candidate_pool=t.native_id in (cp | ep)) for t in traces]
        order = ranked_claims
        # Preserve the original top-k-before-source-cap quirk only in the static,
        # all-allow diagnostic. Every active research arm uses identical refill.
        if not self.effects_enabled and all(t.decision.reason != "acl_denied" for t in traces):
            order = order[:k]
        served = memory._cap(order, k, {}) if k else []
        selected_chunks = ranked_chunks[: memory.evidence_slots]
        verdicts = {
            c.claim_id: {
                "type": c.claim_type.name.lower(),
                "standing": str(c.standing),
                "usable_as": c.usable.name.lower(),
                "eligible": True,
                "source": c.source_id,
            }
            for c in served
        }
        # The only memory-text model calls here see the final authorized claims.
        if memory.detect_conflicts:
            for verdict in memory._resolve_conflicts(graph, served):
                for cid in verdict.contested:
                    verdicts.setdefault(cid, {})["contested"] = verdict.detail
        entries = [memory._entry(c, graph, required=required) for c in served]
        for chunk in selected_chunks:
            usable = required if required > Rung.DESCRIPTION else Rung.DESCRIPTION
            entries.append(
                MemoryEntry(
                    chunk.chunk_id,
                    sentinel.render(
                        chunk.chunk_id,
                        f"source: {chunk.label} | verbatim\n{chunk.text}",
                        usable=usable.name.lower(),
                    ),
                    chunk.source_ids,
                    {
                        "evidence": True,
                        "standing": str(chunk.standing),
                        "usable_as": usable.name.lower(),
                        "raw_text": chunk.text,
                    },
                )
            )
        result = RetrievalResult(
            tuple(entries), required.name.lower(), not ranked_claims, memory.mode, verdicts
        )
        first_claims = {c.claim_id for c in original_claims[:k]}
        first_chunks = {c.chunk_id for c in original_chunks[: memory.evidence_slots]}
        return finish(
            result,
            sum(c.claim_id not in first_claims for c in served),
            sum(c.chunk_id not in first_chunks for c in selected_chunks),
        )
