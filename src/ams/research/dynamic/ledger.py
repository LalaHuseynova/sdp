"""Append-only single-writer evidence journal, causal projections and snapshots.

No cache, SDK, network, embeddings or evaluator imports. Journal hashes detect
accidental corruption; they are not signatures against a hostile trusted host.
"""

from __future__ import annotations

import fcntl
import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from pathlib import Path
from types import MappingProxyType

from .models import (
    SCHEMA,
    Audit,
    Event,
    LedgerError,
    Provenance,
    Register,
    Retract,
    StoredRecord,
    canonical,
    check,
    digest,
    event_dict,
    fields_only,
    integer,
    name,
    parse_event,
)


@dataclass(frozen=True)
class LedgerConfig:
    episode_id: str
    mode: str
    audit_limit: int
    token_limit: int | None = None
    cost_limit_microusd: int | None = None

    def __post_init__(self):
        name(self.episode_id, "episode_id")
        check(
            type(self.mode) is str and self.mode in {"artificial_fixture", "verified_audits"},
            "Unknown ledger mode",
        )
        integer(self.audit_limit, "audit_limit")
        for key in ("token_limit", "cost_limit_microusd"):
            if getattr(self, key) is not None:
                integer(getattr(self, key), key)


@dataclass(frozen=True)
class Usage:
    tickets: int = 0
    attempts: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_microusd: int = 0


@dataclass(frozen=True)
class GroupStats:
    unsafe: int = 0
    safe: int = 0

    @property
    def risk(self) -> Fraction:
        return Fraction(1 + self.unsafe, 2 + self.unsafe + self.safe)

    @property
    def penalty(self) -> Fraction:
        return max(Fraction(0), self.risk - Fraction(1, 2))


@dataclass(frozen=True)
class _Projection:
    roots: Mapping[str, Provenance]
    records: Mapping[tuple[str, str], tuple[str, StoredRecord]]
    active_audits: tuple[Audit, ...]
    usage: Usage


def _project(config: LedgerConfig, events: tuple[Event, ...]) -> _Projection:
    roots, records, owners, active, tickets, ids = {}, {}, {}, {}, set(), set()
    spent = Usage()
    last_time = 0
    for event in events:
        check(type(event) in {Register, Audit, Retract}, "Unknown event class")
        check(event.event_id not in ids, "Repeated event ID in journal")
        check(event.revealed_at >= last_time, "Revealed events cannot be backdated")
        ids.add(event.event_id)
        last_time = event.revealed_at
        if isinstance(event, Register):
            origin = event.origin
            check(
                origin.root_id not in roots or roots[origin.root_id] == origin,
                "Conflicting trusted provenance for one incident root",
            )
            roots[origin.root_id] = origin
            for record in event.records:
                owner = (origin.root_id, record.record_kind, record.artifact_id)
                check(
                    record.record_id not in owners or owners[record.record_id] == owner,
                    "Record identity cannot change origin, type or artifact",
                )
                owners[record.record_id] = owner
                records[record.record_id, record.content_hash] = (origin.root_id, record)
        elif isinstance(event, Audit):
            check(event.root_id in roots, "Audit precedes trusted provenance registration")
            check(
                event.ticket_id not in tickets, "Ticket already consumed; use a new review ticket"
            )
            is_fixture = event.verification_basis == "artificial_fixture"
            check(
                is_fixture == (config.mode == "artificial_fixture"),
                "Fixture findings cannot become real verified audits (or vice versa)",
            )
            keys = {(f.record_id, f.content_hash) for f in event.findings}
            check(
                all(k in records and records[k][0] == event.root_id for k in keys),
                "Finding is not a registered version of this origin root",
            )
            if event.complete_bundle:
                bundle = {k for k, (root_id, _) in records.items() if root_id == event.root_id}
                check(keys == bundle, "Complete bundle must cover all registered record versions")
            if event.supersedes is not None:
                check(event.supersedes in active, "Correction must replace an active audit")
                old = active[event.supersedes]
                check(
                    (old.root_id, old.use_id, old.policy_version)
                    == (event.root_id, event.use_id, event.policy_version),
                    "Correction cannot replace another origin/use/policy",
                )
                check(
                    {(f.record_id, f.content_hash) for f in old.findings} <= keys,
                    "Repair/new content cannot erase a historical incident",
                )
                del active[event.supersedes]
            active[event.event_id] = event
            tickets.add(event.ticket_id)
            spent = Usage(
                spent.tickets + 1,
                spent.attempts + event.attempts,
                spent.input_tokens + event.input_tokens,
                spent.output_tokens + event.output_tokens,
                spent.cost_microusd + event.cost_microusd,
            )
            check(spent.tickets <= config.audit_limit, "Logical audit budget exhausted")
            if config.token_limit is not None:
                check(
                    spent.input_tokens + spent.output_tokens <= config.token_limit,
                    "Verification token budget exhausted",
                )
            if config.cost_limit_microusd is not None:
                check(
                    spent.cost_microusd <= config.cost_limit_microusd,
                    "Verification dollar budget exhausted",
                )
        else:
            check(event.target_event_id in active, "Retraction must name an active audit")
            del active[event.target_event_id]
    return _Projection(
        MappingProxyType(roots), MappingProxyType(records), tuple(active.values()), spent
    )


def _header(config: LedgerConfig) -> dict:
    return {"schema": SCHEMA, "config": asdict(config)}


def _envelopes(config: LedgerConfig, events: tuple[Event, ...]) -> tuple[list[dict], str]:
    previous = digest(_header(config))
    rows = []
    for i, event in enumerate(events, 1):
        body = {"sequence": i, "previous_hash": previous, "event": event_dict(event)}
        previous = digest(body)
        rows.append({**body, "event_hash": previous})
    return rows, previous


def _new_file(path: Path, payload: bytes) -> None:
    """Exclusive creation: never truncate an existing journal, snapshot or review."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _json(payload: str) -> dict:
    def pairs(items):
        obj = {}
        for key, value in items:
            check(key not in obj, "Duplicate JSON field")
            obj[key] = value
        return obj

    try:
        obj = json.loads(payload, object_pairs_hook=pairs)
    except (TypeError, ValueError) as error:
        raise LedgerError("Invalid evidence JSON") from error
    check(type(obj) is dict, "Expected evidence object")
    return obj


@dataclass(frozen=True)
class EvidenceSnapshot:
    """Immutable journal prefix: later events cannot alter an earlier decision.

    `as_of` is a logical event time, `cursor` the exact committed prefix (needed
    when several events share a time). Future schedules do not belong here.
    """

    config: LedgerConfig
    events: tuple[Event, ...]
    as_of: int
    _state: _Projection = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        check(
            type(self.config) is LedgerConfig and type(self.events) is tuple,
            "Expected immutable snapshot inputs",
        )
        integer(self.as_of, "as_of")
        check(
            all(e.revealed_at <= self.as_of for e in self.events),
            "Snapshot exposes feedback from the future",
        )
        object.__setattr__(self, "_state", _project(self.config, self.events))

    @property
    def cursor(self) -> int:
        return len(self.events)

    @property
    def revision(self) -> str:
        return _envelopes(self.config, self.events)[1]

    @property
    def roots(self) -> Mapping[str, Provenance]:
        return self._state.roots

    @property
    def records(self) -> Mapping[tuple[str, str], tuple[str, StoredRecord]]:
        return self._state.records

    @property
    def usage(self) -> Usage:
        return self._state.usage

    def local_status(self, record_id: str, version: str, use_id: str, policy_version: str) -> str:
        check((record_id, version) in self.records, "Unknown record version")
        found = {
            f.verdict
            for a in self._state.active_audits
            if (a.use_id, a.policy_version) == (use_id, policy_version)
            for f in a.findings
            if (f.record_id, f.content_hash) == (record_id, version)
        }
        # Another safe audit cannot silently clear an independently active unsafe one.
        if "unsafe" in found:
            return "unsafe"
        if "safe_for_use" in found:
            return "safe_for_use"
        return "unreviewed" if not found else "unresolved"

    def observations(self) -> tuple[tuple[Provenance, str], ...]:
        """At most one informative count per independent root, across all uses/versions."""
        outcomes = {}
        for audit in self._state.active_audits:
            if audit.outcome != "unresolved":
                outcomes.setdefault(audit.root_id, set()).add(audit.outcome)
        return tuple(
            (self.roots[root], "unsafe" if "unsafe" in values else "safe_for_use")
            for root, values in sorted(outcomes.items())
            if self.roots[root].attribution == "authenticated_external"
        )

    def group(
        self, scope: str, contributor: str, context: str | None = None, batch: str | None = None
    ) -> GroupStats:
        check(scope in {"source", "context", "batch"}, "Unknown scope")
        name(contributor, "contributor")
        if scope != "source":
            name(context, "context")
        if scope == "batch":
            name(batch, "batch")
        outcomes = [
            v
            for p, v in self.observations()
            if p.contributor_id == contributor
            and (scope == "source" or p.context_id == context)
            and (scope != "batch" or p.batch_id == batch)
        ]
        return GroupStats(outcomes.count("unsafe"), outcomes.count("safe_for_use"))

    def active_scopes(self, origin: Provenance) -> tuple[str, ...]:
        """Minimum-pilot S support gates, recomputed after every correction."""
        if origin.attribution != "authenticated_external":
            return ()
        bad = [
            p
            for p, v in self.observations()
            if v == "unsafe" and p.contributor_id == origin.contributor_id
        ]
        local = [p for p in bad if p.context_id == origin.context_id]
        scopes = []
        if any(p.batch_id == origin.batch_id for p in local):
            scopes.append("batch")
        if len(local) >= 2 and len({p.batch_id for p in local}) >= 2:
            scopes.append("context")
        qualifying_contexts = {
            p.context_id
            for p in bad
            if len([r for r in bad if r.context_id == p.context_id]) >= 2
            and len({r.batch_id for r in bad if r.context_id == p.context_id}) >= 2
        }
        if len(bad) >= 4 and len(qualifying_contexts) >= 2:
            scopes.append("source")
        return tuple(scopes)

    def save(self, path: str | Path) -> None:
        body = {
            "schema": SCHEMA,
            "config": asdict(self.config),
            "as_of": self.as_of,
            "cursor": self.cursor,
            "revision": self.revision,
            "events": [event_dict(e) for e in self.events],
        }
        _new_file(Path(path), (canonical({**body, "snapshot_hash": digest(body)}) + "\n").encode())

    @classmethod
    def load(cls, path: str | Path) -> EvidenceSnapshot:
        body = _json(Path(path).read_text(encoding="utf-8"))
        check(
            set(body)
            == {"schema", "config", "as_of", "cursor", "revision", "events", "snapshot_hash"},
            "Unexpected snapshot fields",
        )
        checksum = body.pop("snapshot_hash")
        check(body["schema"] == SCHEMA and digest(body) == checksum, "Corrupt snapshot")
        check(type(body["events"]) is list, "Expected snapshot event array")
        config = LedgerConfig(**fields_only(body["config"], LedgerConfig))
        snap = cls(config, tuple(parse_event(e) for e in body["events"]), body["as_of"])
        check(
            snap.cursor == body["cursor"] and snap.revision == body["revision"],
            "Snapshot cursor/revision mismatch",
        )
        return snap


class EvidenceLedger:
    """Single-process journal; stale writers fail instead of merging feedback order.

    Append only revealed events, never future jobs. Logical times must not move
    backwards. `snapshot(as_of, cursor)` can replay any available prefix; new audit
    findings and policy decisions cannot retroactively change that prefix.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        payload = self.path.read_bytes()
        check(payload.endswith(b"\n"), "Truncated journal: explicit recovery required")
        try:
            lines = payload.decode("utf-8").splitlines()
        except UnicodeError as error:
            raise LedgerError("Journal is not UTF-8") from error
        rows = [_json(line) for line in lines]
        check(
            rows and set(rows[0]) == {"schema", "config"} and rows[0]["schema"] == SCHEMA,
            "Unknown journal header",
        )
        self.config = LedgerConfig(**fields_only(rows[0]["config"], LedgerConfig))
        events = []
        previous = digest(rows[0])
        for i, row in enumerate(rows[1:], 1):
            check(
                set(row) == {"sequence", "previous_hash", "event", "event_hash"},
                "Unknown journal envelope fields",
            )
            check(
                type(row["sequence"]) is int
                and row["sequence"] == i
                and row["previous_hash"] == previous,
                "Journal chain/order mismatch",
            )
            body = {k: row[k] for k in ("sequence", "previous_hash", "event")}
            previous = digest(body)
            check(previous == row["event_hash"], "Journal event hash mismatch")
            events.append(parse_event(row["event"]))
        check(
            payload == ("".join(canonical(r) + "\n" for r in rows)).encode(),
            "Journal must use canonical JSONL; no silent repairs",
        )
        self._events = tuple(events)
        _project(self.config, self._events)
        self._payload = payload

    @classmethod
    def create(
        cls,
        path: str | Path,
        *,
        episode_id: str,
        audit_limit: int,
        mode: str = "verified_audits",
        token_limit: int | None = None,
        cost_limit_microusd: int | None = None,
    ) -> EvidenceLedger:
        config = LedgerConfig(episode_id, mode, audit_limit, token_limit, cost_limit_microusd)
        _new_file(Path(path), (canonical(_header(config)) + "\n").encode())
        return cls(path)

    @classmethod
    def restore(cls, snapshot_path: str | Path, new_journal: str | Path) -> EvidenceLedger:
        """Explicit restart into a NEW journal at exactly the saved cursor, without a tail."""
        snap = EvidenceSnapshot.load(snapshot_path)
        rows, _ = _envelopes(snap.config, snap.events)
        payload = "".join(canonical(row) + "\n" for row in [_header(snap.config), *rows])
        _new_file(Path(new_journal), payload.encode())
        return cls(new_journal)

    def append(self, event: Event) -> bool:
        # Round trip validates an explicit allowlist; never accepts raw evaluator dictionaries.
        event = parse_event(json.loads(canonical(event_dict(event))))
        duplicate = next((e for e in self._events if e.event_id == event.event_id), None)
        if duplicate is not None:
            check(duplicate == event, "Event ID reused with a different payload")
        proposed = self._events if duplicate else (*self._events, event)
        _project(self.config, proposed)  # validate BEFORE touching persistent or in-memory state
        rows, _ = _envelopes(self.config, proposed)
        with self.path.open("r+b") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            check(stream.read() == self._payload, "Journal changed: reload before another commit")
            if duplicate:
                return False
            addition = (canonical(rows[-1]) + "\n").encode()
            stream.write(addition)
            stream.flush()
            os.fsync(stream.fileno())
        self._events = tuple(proposed)
        self._payload += addition
        return True

    def snapshot(self, *, as_of: int | None = None, cursor: int | None = None) -> EvidenceSnapshot:
        if cursor is None:
            cursor = len(self._events)
        integer(cursor, "cursor")
        check(cursor <= len(self._events), "Snapshot cursor exceeds committed history")
        prefix = self._events[:cursor]
        if as_of is None:
            as_of = prefix[-1].revealed_at if prefix else 0
        integer(as_of, "as_of")
        prefix = tuple(e for e in prefix if e.revealed_at <= as_of)
        return EvidenceSnapshot(self.config, prefix, as_of)
