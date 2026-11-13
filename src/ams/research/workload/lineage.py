"""Content-lineage extension (research arm, not part of locked protocol v1).

Provenance-based propagation (R/C/M/S) cannot see a copy whose source is
unknown or different: on the locked test, unlinked relays leaked 15-16/24
under every arm. Content lineage adds one rule on top of any base policy:

    a stored claim whose embedding is near-identical (cosine >= tau) to a claim
    of a root with an active *unsafe* audit is withheld, for every use, unless
    that claim itself is verified safe for this use.

It uses only the original local MiniLM claim vectors already in the store, the
audited roots already in the evidence snapshot, and the base policy's own
decision; it never creates an audit, a finding or an unsafe observation, so it
cannot raise any contributor's risk (no framing amplification). Evidence
chunks are excluded: external chunks are not shown to the answerer in the
reproduced configuration, and chunk text is shared with benign base documents.

Wired in by replacing `state.reader` on one RuntimeState instance; the frozen
GovernedRetrieval, Policy and RuntimeState code is unchanged.
"""

from __future__ import annotations

from dataclasses import replace

from ams.research.dynamic import Audit
from ams.research.dynamic.models import check, digest

LINEAGE_VERSION = "content-lineage-v1"
DEFAULT_TAU = 0.8
LINEAGE_ARMS = {"RL": "R", "CL": "C", "ML": "M", "SL": "S"}


class LineagePolicy:
    """Base policy decision, then the lineage rule. Duck-types `Policy`."""

    def __init__(self, base, blocked: frozenset, tau: float):
        self.base, self.blocked, self.tau = base, blocked, tau

    def __getattr__(self, item):
        return getattr(self.base, item)

    @property
    def fingerprint(self) -> str:
        return digest(
            {
                "base": self.base.fingerprint,
                "lineage": LINEAGE_VERSION,
                "tau": self.tau,
                "blocked": sorted(map(list, self.blocked)),
            }
        )

    def decide(self, candidate, snapshot):
        d = self.base.decide(candidate, snapshot)
        key = (candidate.record_id, candidate.content_hash)
        if d.eligible and d.local_status != "safe_for_use" and key in self.blocked:
            return replace(d, eligible=False, adjusted_score=None, reason="content_lineage_unsafe")
        return d


def blocked_records(state, session_id: str, tau: float = DEFAULT_TAU) -> tuple[frozenset, dict]:
    """(record keys withheld by lineage, diagnostics) for the state's current evidence."""
    import numpy as np

    ev = state.evidence
    unsafe_roots = {
        e.root_id for e in ev.events if type(e) is Audit and e.outcome == "unsafe"
    }
    index = state.memory._vectors.get(session_id)
    if index is None or not unsafe_roots:
        return frozenset(), {"unsafe_roots": len(unsafe_roots), "blocked": 0}
    ids = list(index._ids)
    X = np.asarray(index._rows, dtype=float)
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    keys, root_of = [], []
    for native in ids:
        b = state.bindings.record(session_id, native)
        key = (b.record_id, b.content_hash)
        keys.append(key)
        root = ev.records.get(key)
        root_of.append(root[0] if root else None)
    src = [i for i, r in enumerate(root_of) if r in unsafe_roots]
    if not src:
        return frozenset(), {"unsafe_roots": len(unsafe_roots), "blocked": 0}
    sims = (X @ X[src].T).max(axis=1)
    principal = {
        i
        for i, r in enumerate(root_of)
        if r is not None and ev.roots[r].attribution == "principal"
    }
    blocked = frozenset(
        keys[i] for i in range(len(keys)) if sims[i] >= tau and i not in principal
    )
    return blocked, {
        "unsafe_roots": len(unsafe_roots),
        "source_claims": len(src),
        "blocked": len(blocked),
        "blocked_outside_unsafe_roots": sum(
            1 for i in range(len(keys)) if keys[i] in blocked and root_of[i] not in unsafe_roots
        ),
    }


def apply(state, session_id: str, tau: float = DEFAULT_TAU) -> dict:
    """Make `state.reader()` use the lineage-wrapped policy; returns diagnostics."""
    check(state.effects_enabled, "Lineage applies to governed arms only")
    blocked, info = blocked_records(state, session_id, tau)
    original = type(state).reader.__get__(state)

    def reader():
        r = original()
        object.__setattr__(r, "policy", LineagePolicy(state.policy, blocked, tau))
        return r

    state.reader = reader
    return info
