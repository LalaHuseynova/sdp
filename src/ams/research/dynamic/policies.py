"""Pure minimum-pilot R/C/M/S decisions; no retrieval, verification or new labels."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from fractions import Fraction

from .ledger import EvidenceSnapshot
from .models import check, content_hash, digest, name


@dataclass(frozen=True)
class Candidate:
    record_id: str
    content_hash: str
    use_id: str
    policy_version: str
    original_score: float
    acl_allowed: bool
    authority_allowed: bool

    def __post_init__(self):
        for key in ("record_id", "use_id", "policy_version"):
            name(getattr(self, key), key)
        content_hash(self.content_hash)
        check(
            type(self.original_score) in {int, float} and math.isfinite(self.original_score),
            "Expected a finite original relevance score",
        )
        check(
            type(self.acl_allowed) is bool and type(self.authority_allowed) is bool,
            "Explicit trusted ACL and original authority decisions are required",
        )


@dataclass(frozen=True)
class Decision:
    arm: str
    record_id: str
    content_hash: str
    use_id: str
    policy_version: str
    episode_id: str
    evidence_revision: str
    evidence_cursor: int
    available_at: int
    policy_hash: str
    eligible: bool
    reason: str
    local_status: str
    penalty: float
    adjusted_score: float | None
    active_scopes: tuple[str, ...]
    # scope, distinct unsafe roots, distinct safe roots; never new record labels
    counts: tuple[tuple[str, int, int], ...]
    consumed_tickets: int


@dataclass(frozen=True)
class Policy:
    arm: str
    weight: float = 0.5
    threshold: float | None = 0.25

    def __post_init__(self):
        check(self.arm in {"R", "C", "M", "S"}, "Unknown comparison arm")
        check(
            type(self.weight) in {float, int} and math.isfinite(self.weight) and self.weight >= 0,
            "Invalid risk weight",
        )
        check(
            self.threshold is None
            or (
                type(self.threshold) in {float, int}
                and math.isfinite(self.threshold)
                and self.threshold >= 0
            ),
            "Invalid risk gate",
        )
        if self.arm == "R":
            object.__setattr__(self, "weight", 0.0)
            object.__setattr__(self, "threshold", None)

    @property
    def fingerprint(self) -> str:
        return digest(
            {
                "version": "minimum-pilot-v1",
                **asdict(self),
                "prior": [1, 1],
                "support_gates": [1, 2, 4],
                "context_min_batches": 2,
                "source_min_contexts": 2,
            }
        )

    def decide(self, candidate: Candidate, snapshot: EvidenceSnapshot) -> Decision:
        check(
            type(candidate) is Candidate and type(snapshot) is EvidenceSnapshot,
            "Expected typed public candidate and immutable evidence snapshot",
        )
        key = candidate.record_id, candidate.content_hash
        check(key in snapshot.records, "Unknown/unavailable record version")
        root_id, _ = snapshot.records[key]
        origin = snapshot.roots[root_id]
        local = snapshot.local_status(*key, candidate.use_id, candidate.policy_version)
        scopes, counts = (), ()
        penalty = Fraction(0)
        eligible, reason = True, "no_source_penalty"
        if not candidate.acl_allowed:
            eligible, reason = False, "acl_denied"
        elif not candidate.authority_allowed:
            eligible, reason = False, "authority_denied"
        elif local == "unsafe":
            eligible, reason = False, "verified_unsafe_for_use"
        elif local == "safe_for_use":
            reason = "verified_safe_for_use"
        elif self.arm != "R" and origin.attribution == "authenticated_external":
            if self.arm == "C":
                scopes = ("context",)
            elif self.arm == "M":
                scopes = ("batch", "context", "source")
            else:
                scopes = snapshot.active_scopes(origin)
            summaries = [
                (
                    scope,
                    snapshot.group(
                        scope, origin.contributor_id, origin.context_id, origin.batch_id
                    ),
                )
                for scope in scopes
            ]
            penalty = max((stats.penalty for _, stats in summaries), default=Fraction(0))
            counts = tuple((scope, s.unsafe, s.safe) for scope, s in summaries)
            if self.threshold is not None and penalty >= Fraction(str(self.threshold)):
                eligible, reason = False, "source_risk_gate"
            elif penalty:
                reason = "source_ranking_penalty"
        elif origin.attribution == "unknown":
            reason = "unattributed_no_source_transfer"
        score = candidate.original_score - self.weight * float(penalty) if eligible else None
        return Decision(
            self.arm,
            candidate.record_id,
            candidate.content_hash,
            candidate.use_id,
            candidate.policy_version,
            snapshot.config.episode_id,
            snapshot.revision,
            snapshot.cursor,
            snapshot.as_of,
            self.fingerprint,
            eligible,
            reason,
            local,
            float(penalty),
            score,
            scopes,
            counts,
            snapshot.usage.tickets,
        )
