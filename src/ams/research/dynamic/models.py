"""Immutable allowlisted events. IDs/provenance must come from the trusted harness."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import ClassVar, Literal

Verdict = Literal["unsafe", "safe_for_use", "unresolved"]
VERDICTS = ("unsafe", "safe_for_use", "unresolved")
SCHEMA = "dynamic-evidence-v1"


class LedgerError(ValueError):
    """Invalid evidence, provenance, accounting or journal; fail closed."""


def check(condition: bool, message: str) -> None:
    if not condition:
        raise LedgerError(message)


def name(value: str, field: str) -> None:
    check(isinstance(value, str) and bool(value.strip()), f"Missing {field}")


def integer(value: int, field: str, minimum: int = 0) -> None:
    check(type(value) is int and value >= minimum, f"Invalid {field}")


def content_hash(value: str) -> None:
    check(
        isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value)),
        "Content version must be a SHA-256 digest",
    )


def canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def fields_only(value: dict, cls: type) -> dict:
    check(type(value) is dict, "Expected an allowlisted object")
    expected = set(cls.__dataclass_fields__) - {"kind"}
    check(set(value) == expected, f"Unexpected/missing fields for {cls.__name__}")
    return dict(value)


@dataclass(frozen=True)
class Provenance:
    """One independent origin root, shared by its known copies, claims and chunks.

    batch/context are origin metadata, never inferred from the current query.
    Unknown/mixed attribution must use contributor_id=None. Principal statements
    have their own root and principal_id; an uploader is never the culpable origin.
    """

    root_id: str
    context_id: str
    batch_id: str | None
    contributor_id: str | None
    attribution: str
    uploader_id: str | None = None
    principal_id: str | None = None

    def __post_init__(self):
        for field in ("root_id", "context_id"):
            name(getattr(self, field), field)
        for field in ("batch_id", "contributor_id", "uploader_id", "principal_id"):
            if getattr(self, field) is not None:
                name(getattr(self, field), field)
        check(
            type(self.attribution) is str
            and self.attribution in {"authenticated_external", "unknown", "principal"},
            "Unsupported attribution",
        )
        if self.attribution == "authenticated_external":
            check(
                self.contributor_id is not None and self.batch_id is not None,
                "Authenticated external origin needs contributor and batch",
            )
            check(self.principal_id is None, "External origin cannot own principal statements")
        else:
            check(self.contributor_id is None, "Do not guess a contributor for unknown/principal")
            check(
                (self.principal_id is not None) == (self.attribution == "principal"),
                "Principal attribution needs a distinct principal_id",
            )


@dataclass(frozen=True)
class StoredRecord:
    record_id: str
    content_hash: str
    record_kind: str
    artifact_id: str

    def __post_init__(self):
        name(self.record_id, "record_id")
        name(self.artifact_id, "artifact_id")
        content_hash(self.content_hash)
        check(
            type(self.record_kind) is str and self.record_kind in {"claim", "evidence_chunk"},
            "Unsupported memory record kind",
        )


@dataclass(frozen=True)
class Finding:
    record_id: str
    content_hash: str
    verdict: Verdict
    evidence_ref: str

    def __post_init__(self):
        name(self.record_id, "record_id")
        content_hash(self.content_hash)
        check(self.verdict in VERDICTS, "Not an audit verdict (pending is not unresolved)")
        name(self.evidence_ref, "finding evidence_ref")


def event_fields(event) -> None:
    name(event.event_id, "event_id")
    integer(event.revealed_at, "revealed_at")


@dataclass(frozen=True)
class Register:
    """Reveal trusted provenance and record versions at ingestion, without labels."""

    kind: ClassVar[str] = "register"
    event_id: str
    revealed_at: int
    origin: Provenance
    records: tuple[StoredRecord, ...]

    def __post_init__(self):
        event_fields(self)
        check(type(self.origin) is Provenance, "Expected trusted Provenance")
        check(
            type(self.records) is tuple
            and bool(self.records)
            and all(type(r) is StoredRecord for r in self.records),
            "No registered records",
        )
        check(
            len({(r.record_id, r.content_hash) for r in self.records}) == len(self.records),
            "Duplicate record versions",
        )


@dataclass(frozen=True)
class Audit:
    """One spent ticket for a root/use. Findings concern only explicitly reviewed records.

    A complete safe bundle must cover every currently registered version of its
    root. Partial safe findings may be supplied with outcome=unresolved: they give
    exact local exceptions but no aggregate safe vote. The audit service, rather
    than the policy, is responsible for the evidence's validity and independence.
    """

    kind: ClassVar[str] = "audit"
    event_id: str
    revealed_at: int
    ticket_id: str
    root_id: str
    use_id: str
    policy_version: str
    outcome: Verdict
    findings: tuple[Finding, ...]
    complete_bundle: bool
    verifier_id: str
    verification_basis: str
    evidence_ref: str
    supersedes: str | None = None
    attempts: int = 1
    input_tokens: int = 0
    output_tokens: int = 0
    cost_microusd: int = 0

    def __post_init__(self):
        event_fields(self)
        for field in (
            "ticket_id",
            "root_id",
            "use_id",
            "policy_version",
            "verifier_id",
            "evidence_ref",
        ):
            name(getattr(self, field), field)
        check(self.outcome in VERDICTS, "Missing/invalid revealed verdict")
        check(type(self.complete_bundle) is bool, "Explicit completeness required")
        check(
            type(self.verification_basis) is str
            and self.verification_basis
            in {"artificial_fixture", "human_adjudication", "controlled_audit", "frozen_verifier"},
            "Warnings, case labels and task judges are not verified audits",
        )
        check(
            type(self.findings) is tuple and all(type(f) is Finding for f in self.findings),
            "Expected immutable findings",
        )
        check(
            len({(f.record_id, f.content_hash) for f in self.findings}) == len(self.findings),
            "Duplicate findings",
        )
        if self.outcome == "unsafe":
            check(
                any(f.verdict == "unsafe" for f in self.findings),
                "Unsafe audit needs an implicated record and evidence",
            )
        elif self.outcome == "safe_for_use":
            check(
                self.complete_bundle
                and bool(self.findings)
                and all(f.verdict == "safe_for_use" for f in self.findings),
                "Safe bundle must be completely reviewed, nonempty and resolved",
            )
        else:
            check(
                not any(f.verdict == "unsafe" for f in self.findings),
                "Confirmed unsafe finding cannot be an unresolved bundle",
            )
        if self.supersedes is not None:
            name(self.supersedes, "supersedes")
        integer(self.attempts, "attempts", 1)
        check(self.attempts <= 2, "At most two physical attempts per ticket")
        for field in ("input_tokens", "output_tokens", "cost_microusd"):
            integer(getattr(self, field), field)


@dataclass(frozen=True)
class Retract:
    """Trusted administrative invalidation, never a new safe vote or refunded audit."""

    kind: ClassVar[str] = "retract"
    event_id: str
    revealed_at: int
    target_event_id: str
    evidence_ref: str
    authority_id: str

    def __post_init__(self):
        event_fields(self)
        for field in ("target_event_id", "evidence_ref", "authority_id"):
            name(getattr(self, field), field)


Event = Register | Audit | Retract


def event_dict(event: Event) -> dict:
    check(type(event) in {Register, Audit, Retract}, "Unknown evidence event")
    return {"kind": event.kind, **asdict(event)}


def parse_event(value: dict) -> Event:
    """Reject extra gold fields, null verdicts and untyped raw case dictionaries."""
    check(type(value) is dict, "Expected event object")
    body = dict(value)
    kind = body.pop("kind", None)
    check(
        type(kind) is str and kind in {"register", "audit", "retract"},
        "Unknown evidence event kind",
    )
    cls = {"register": Register, "audit": Audit, "retract": Retract}[kind]
    body = fields_only(body, cls)
    if kind == "register":
        body["origin"] = Provenance(**fields_only(body["origin"], Provenance))
        check(type(body["records"]) is list, "Expected record array")
        body["records"] = tuple(
            StoredRecord(**fields_only(r, StoredRecord)) for r in body["records"]
        )
    elif kind == "audit":
        check(type(body["findings"]) is list, "Expected findings array")
        body["findings"] = tuple(Finding(**fields_only(f, Finding)) for f in body["findings"])
    return cls(**body)
