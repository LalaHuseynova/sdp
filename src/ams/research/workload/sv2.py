"""S v2 candidates (experimental research arms; original S is unchanged).

Owner-approved on 12 Nov 2026 for design and free dev evaluation. Every candidate
is a *composition on top of* the frozen `Policy("S")` decision, applied by
replacing `state.reader` on one RuntimeState instance, exactly like the content-
lineage arm. The frozen Policy / ledger / GovernedRetrieval code is not edited.

Shared by all candidates (kept from the earlier plan):
  * content lineage (`lineage.py`, tau = 0.8): claims near-identical to a claim
    of an unsafe-audited root are withheld for every use;
  * boundary-verification auditing is an *audit protocol*, not a policy: it is
    evaluated through the `..._fu` conditions (adaptive.py), which every arm sees.

Candidates
----------
S2-ID   "identity-blind gate". S + lineage, then MemLineage's sensitive-action gate
        on the final context: if the query is SENSITIVE (the paper classifier's
        recorded verdict) and the context holds an untrusted (externally derived)
        memory, the context is emptied (MemLineage's Deny). Rationale: the free and
        paid dev comparison showed MemLineage's protection is identity-blind and
        flat in Sybil-k / laundering-r, while S's is ~0 at low k/r and ~none at high
        k/r; composing them should give the better of both curves at no utility cost
        (MemLineage changed no utility probe). Coarse MemLineage labels reduce to
        "external record => untrusted, principal => trusted" (tested in
        test_published_adapters).
S2-BS   "batch scope, any contributor". S + lineage + one extra support scope:
        verified outcomes of *any* authenticated contributor in the same
        (context, batch of arrival). Same prior, risk, penalty and 0.25 gate as S,
        and the same activation rule as S's batch gate (>= 1 unsafe in the batch).
        Rationale: identity splitting changes the contributor label but not the
        arrival unit. Risk: penalises innocent items that share an arrival batch
        with detected poison (framing) and is defeated by an attacker who spreads
        Sybil items over batches; both are measured.
S2-ALL  exploratory: both of the above.
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from ams.research.dynamic.ledger import GroupStats
from ams.research.dynamic.models import check, digest
from ams.research.workload import lineage as LN

SV2_VERSION = "sv2-candidates-v1"
CANDIDATES = {
    "S2-ID": {"batch_any": False, "id_gate": True},
    "S2-BS": {"batch_any": True, "id_gate": False},
    "S2-ALL": {"batch_any": True, "id_gate": True},
}


class BatchAnyContributorPolicy:
    """Base decision, then an identity-independent (context, batch) support scope."""

    def __init__(self, base):
        self.base = base

    def __getattr__(self, item):
        return getattr(self.base, item)

    @property
    def fingerprint(self) -> str:
        return digest({"base": self.base.fingerprint, "extension": "batch-any-contributor-v1"})

    def decide(self, candidate, snapshot):
        d = self.base.decide(candidate, snapshot)
        if not d.eligible or d.local_status == "safe_for_use":
            return d
        key = (candidate.record_id, candidate.content_hash)
        origin = snapshot.roots[snapshot.records[key][0]]
        if origin.attribution != "authenticated_external" or origin.batch_id is None:
            return d
        outcomes = [
            v
            for p, v in snapshot.observations()
            if p.context_id == origin.context_id and p.batch_id == origin.batch_id
        ]
        stats = GroupStats(outcomes.count("unsafe"), outcomes.count("safe_for_use"))
        if stats.unsafe == 0:  # S's batch-gate activation rule, any contributor
            return d
        penalty = max(Fraction(str(d.penalty)), stats.penalty)
        threshold = self.base.threshold
        if threshold is not None and penalty >= Fraction(str(threshold)):
            return replace(d, eligible=False, adjusted_score=None, penalty=float(penalty),
                           reason="batch_any_contributor_gate")  # fmt: skip
        if penalty > Fraction(str(d.penalty)):
            return replace(d, penalty=float(penalty), reason="batch_any_contributor_penalty",
                           adjusted_score=candidate.original_score
                           - self.base.weight * float(penalty))  # fmt: skip
        return d


class _GatedReader:
    """MemLineage Deny on the final context: SENSITIVE query + any untrusted memory."""

    def __init__(self, inner, sensitive, record_owner):
        self.inner, self.sensitive, self.owner = inner, sensitive, record_owner
        self.denied = 0

    def __getattr__(self, item):
        return getattr(self.inner, item)

    def retrieve_with_trace(self, *, session_id, query, context, k=4, principal="user"):
        out = self.inner.retrieve_with_trace(
            session_id=session_id, query=query, context=context, k=k, principal=principal
        )
        untrusted = any(
            self.owner.get(e.entry_id, {}).get("kind") != "principal"
            for e in out.retrieval.entries
        )
        if untrusted and self.sensitive(query):
            self.denied += 1
            return replace(out, retrieval=replace(out.retrieval, entries=()))
        return out


class RecordedVerdicts:
    """SensitiveAction verdicts recorded by the paid MemLineage run; a miss raises."""

    def __init__(self, verdicts: dict[str, str]):
        self.verdicts = verdicts

    def __call__(self, query: str) -> bool:
        check(query in self.verdicts, "No recorded SensitiveAction verdict for this query")
        return "SENSITIVE" in self.verdicts[query].upper()


def apply(state, store: dict, candidate: str, *, tau: float = LN.DEFAULT_TAU,
          sensitive=None) -> dict:  # fmt: skip
    """Turn an S state into an S v2 candidate (state.policy must be S)."""
    check(candidate in CANDIDATES, f"Unknown S v2 candidate {candidate}")
    check(state.effects_enabled and state.policy.arm == "S", "S v2 composes on top of S")
    spec = CANDIDATES[candidate]
    blocked, info = LN.blocked_records(state, store["session_id"], tau)
    base = state.policy
    policy = BatchAnyContributorPolicy(base) if spec["batch_any"] else base
    policy = LN.LineagePolicy(policy, blocked, tau)
    original = type(state).reader.__get__(state)
    if spec["id_gate"]:
        check(sensitive is not None, "S2-ID needs recorded SensitiveAction verdicts")

    def reader():
        r = original()
        object.__setattr__(r, "policy", policy)
        return _GatedReader(r, sensitive, store["record_owner"]) if spec["id_gate"] else r

    state.reader = reader
    return {"candidate": candidate, "version": SV2_VERSION, **info}
