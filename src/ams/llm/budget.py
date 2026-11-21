"""Durable pre-dispatch reservations for the approved GPT-4o-mini experiment.

The invariant is ``recorded charges + unresolved reservations <= allowance``
before dispatch. Each reservation covers the full advertised context plus the
requested completion ceiling at provider-enforced maximum token rates. This is
a conditional software accounting bound, not a guarantee about taxes,
purchasing credits, undisclosed services, or a provider violating those bounds.
It does not create or change any provider-side account or key limit.

Every physical HTTP attempt needs its own reservation. Disable hidden SDK
retries or intercept each attempt. Unknown outcomes keep their entire reserve;
restarting a process never releases money or resets the allowance.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation
from pathlib import Path

_NANO = Decimal(1_000_000_000)
_MILLION = Decimal(1_000_000)
_MAX_SQLITE_INTEGER = (1 << 63) - 1
_MAX_OUTPUT_TOKENS = 16_384
_MIN_CONTEXT_BOUND = 128_000
_MODEL = "openai/gpt-4o-mini"
# Explicit allowlist of models a guard may be configured for, with the maximum list
# prices (USD per million tokens) that every reservation and routing cap must use.
# GPT-4o-mini stays the default; the Claude entries are owner decisions for protocol v2
# (configs/research/pricing_claude_*_20261114.json). Adding a model is a code change.
APPROVED_MODELS = {
    "openai/gpt-4o-mini": ("0.15", "0.60"),
    "anthropic/claude-sonnet-5.5": ("2.00", "10.00"),
    "anthropic/claude-haiku-5.5": ("0.10", "0.50"),
}
_LABEL = re.compile(r"[A-Za-z0-9_.:/-]{1,128}\Z")
# Exceptions raised before any reply arrived (revision 7 review only).
_TRANSPORT_FAILURES = ("APITimeoutError", "APIConnectionError")
_METADATA_KEYS = frozenset(
    {
        "generation_id",
        "request_id",
        "model",
        "requested_model",
        "response_model",
        "provider",
        "input_tokens",
        "output_tokens",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "reasoning_tokens",
        "cost",
        "cost_usd",
        "actual_cost_usd",
        "provider_cost_usd",
        "estimated_cost_usd",
        "cost_missing",
        "billing_verified",
        "usage",
        "provider_usage",
        "usage_details",
        "http_status",
    }
)
_FORBIDDEN_KEYS = frozenset(
    {
        "messages",
        "prompt",
        "content",
        "authorization",
        "api_key",
        "apikey",
        "request_body",
        "response_body",
        "secret",
        "headers",
    }
)
_IDENTIFIER_KEYS = frozenset(
    {
        "generation_id",
        "request_id",
        "model",
        "requested_model",
        "response_model",
        "provider",
    }
)


class BudgetExhausted(RuntimeError):
    """No further request can be safely reserved within the allowance."""


class BudgetAccountingError(RuntimeError):
    """Accounting cannot be verified; callers must stop rather than retry."""


def _decimal(value, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool):
        raise BudgetAccountingError("Boolean amounts are invalid")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise BudgetAccountingError("Invalid monetary amount") from exc
    if not amount.is_finite() or amount < 0 or (positive and amount == 0):
        raise BudgetAccountingError("Amounts must be finite and nonnegative")
    return amount


def _nanodollars(value: Decimal, *, floor: bool = False) -> int:
    mode = ROUND_FLOOR if floor else ROUND_CEILING
    try:
        units = int((value * _NANO).to_integral_value(rounding=mode))
    except (InvalidOperation, ValueError, OverflowError) as exc:
        raise BudgetAccountingError("Amount cannot be represented safely") from exc
    if not 0 <= units <= _MAX_SQLITE_INTEGER:
        raise BudgetAccountingError("Amount exceeds the accounting integer range")
    return units


def _usd(units: int) -> float:
    return float(Decimal(units) / _NANO)


def _metadata(value: dict | None) -> str:
    """Only billing identifiers and usage belong in this database."""
    if value is None:
        return "{}"
    if not isinstance(value, dict) or not set(value) <= _METADATA_KEYS:
        raise BudgetAccountingError("Metadata must contain billing fields only")

    def clean(item, *, root: bool = False, identifier: bool = False):
        if isinstance(item, dict):
            out = {}
            for key, child in item.items():
                if not isinstance(key, str) or key.lower() in _FORBIDDEN_KEYS:
                    raise BudgetAccountingError("Sensitive or invalid billing metadata field")
                out[key] = clean(child, identifier=root and key in _IDENTIFIER_KEYS)
            return out
        if item is None or isinstance(item, bool):
            return item
        if isinstance(item, int):
            if item < 0:
                raise BudgetAccountingError("Negative billing usage metadata")
            return item
        if isinstance(item, (float, Decimal)):
            number = _decimal(item)
            result = float(number)
            if not math.isfinite(result):
                raise BudgetAccountingError("Billing metadata exceeds JSON numeric range")
            return result
        if isinstance(item, str):
            if not identifier or not _LABEL.fullmatch(item) or "sk-" in item.lower():
                raise BudgetAccountingError("Sensitive or oversized billing metadata value")
            return item
        raise BudgetAccountingError("Unsupported billing metadata value")

    return json.dumps(
        clean(value, root=True), sort_keys=True, separators=(",", ":"), allow_nan=False
    )


class BudgetGuard:
    """One SQLite-backed allowance shared by threads, processes, and restarts."""

    def __init__(
        self,
        path: str | Path,
        limit_usd,
        allowed_model: str = _MODEL,
        max_input_per_mtok="0.15",
        max_output_per_mtok="0.60",
        context_token_bound: int = _MIN_CONTEXT_BOUND,
    ) -> None:
        if allowed_model not in APPROVED_MODELS:
            raise BudgetAccountingError("This guard is restricted to the approved models")
        approved_in, approved_out = (Decimal(v) for v in APPROVED_MODELS[allowed_model])
        if (_decimal(max_input_per_mtok, positive=True) != approved_in
                or _decimal(max_output_per_mtok, positive=True) != approved_out):  # fmt: skip
            raise BudgetAccountingError("Price ceilings must equal the approved list prices")
        if (
            isinstance(context_token_bound, bool)
            or not isinstance(context_token_bound, int)
            or context_token_bound < _MIN_CONTEXT_BOUND
        ):
            raise BudgetAccountingError("Context bound must cover at least 128000 tokens")
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._limit = _nanodollars(_decimal(limit_usd, positive=True), floor=True)
        if not self._limit:
            raise BudgetAccountingError("Allowance is below the accounting precision")
        self._input_price = _decimal(max_input_per_mtok, positive=True)
        self._output_price = _decimal(max_output_per_mtok, positive=True)
        self._context_bound = context_token_bound
        self._model = allowed_model
        self._settings = json.dumps(
            {
                "schema_version": 1,
                "limit_nanodollars": self._limit,
                "allowed_model": allowed_model,
                "max_input_per_mtok": str(self._input_price.normalize()),
                "max_output_per_mtok": str(self._output_price.normalize()),
                "context_token_bound": context_token_bound,
                "max_output_tokens": _MAX_OUTPUT_TOKENS,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        self._reservation_amount(_MAX_OUTPUT_TOKENS)
        with self._transaction(initialize=True) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS budget_config (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                settings TEXT NOT NULL, blocked INTEGER NOT NULL DEFAULT 0,
                blocked_reason TEXT NOT NULL DEFAULT '',
                used_nanodollars TEXT NOT NULL DEFAULT '0',
                held_nanodollars TEXT NOT NULL DEFAULT '0')""")
            conn.execute("""CREATE TABLE IF NOT EXISTS reservations (
                reservation_id TEXT PRIMARY KEY, model TEXT NOT NULL,
                max_output_tokens INTEGER NOT NULL, stage TEXT NOT NULL,
                reserved_nanodollars INTEGER NOT NULL CHECK(reserved_nanodollars>=0),
                actual_nanodollars INTEGER CHECK(actual_nanodollars>=0),
                state TEXT NOT NULL CHECK(state IN ('pending','unknown','settled','breach')),
                metadata TEXT NOT NULL DEFAULT '{}', error_type TEXT NOT NULL DEFAULT '',
                created_utc TEXT NOT NULL, updated_utc TEXT NOT NULL)""")
            conn.execute("CREATE INDEX IF NOT EXISTS reservations_state ON reservations(state)")
            conn.execute("""CREATE TABLE IF NOT EXISTS budget_review_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL CHECK(event_type IN ('halt','resume_after_review')),
                reason TEXT NOT NULL, previous_blocked_reason TEXT NOT NULL,
                resulting_blocked_reason TEXT NOT NULL,
                used_nanodollars TEXT NOT NULL, held_nanodollars TEXT NOT NULL,
                created_utc TEXT NOT NULL)""")
            row = conn.execute("SELECT settings FROM budget_config WHERE singleton=1").fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO budget_config(singleton,settings) VALUES(1,?)", (self._settings,)
                )
            elif row["settings"] != self._settings:
                raise BudgetAccountingError(
                    "Existing allowance configuration differs; it cannot be reset"
                )
            self._audit_totals(conn)

    @contextmanager
    def _transaction(self, *, initialize: bool = False) -> Iterator[sqlite3.Connection]:
        conn = None
        try:
            conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
            conn.row_factory = sqlite3.Row
            if initialize:
                conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("BEGIN IMMEDIATE")
            if not initialize:
                row = conn.execute(
                    "SELECT settings FROM budget_config WHERE singleton=1"
                ).fetchone()
                if row is None or row["settings"] != self._settings:
                    raise BudgetAccountingError("Persisted allowance configuration changed")
            yield conn
            conn.commit()
        except sqlite3.Error as exc:
            if conn is not None:
                conn.rollback()
            raise BudgetAccountingError("Budget database operation failed") from exc
        except BaseException:
            if conn is not None:
                conn.rollback()
            raise
        finally:
            if conn is not None:
                conn.close()

    def _reservation_amount(self, max_output_tokens: int) -> int:
        return _nanodollars(
            (self._input_price * self._context_bound + self._output_price * max_output_tokens)
            / _MILLION
        )

    @staticmethod
    def _totals(conn: sqlite3.Connection) -> tuple[int, int]:
        row = conn.execute(
            "SELECT used_nanodollars,held_nanodollars FROM budget_config WHERE singleton=1"
        ).fetchone()
        try:
            used, held = int(row["used_nanodollars"]), int(row["held_nanodollars"])
        except (ValueError, TypeError) as exc:
            raise BudgetAccountingError("Invalid persisted accounting totals") from exc
        if min(used, held) < 0:
            raise BudgetAccountingError("Negative persisted accounting total")
        return used, held

    @staticmethod
    def _store_totals(conn: sqlite3.Connection, used: int, held: int) -> None:
        if min(used, held) < 0:
            raise BudgetAccountingError("Negative accounting total")
        conn.execute(
            "UPDATE budget_config SET used_nanodollars=?,held_nanodollars=? WHERE singleton=1",
            (str(used), str(held)),
        )

    @classmethod
    def _audit_totals(cls, conn: sqlite3.Connection) -> None:
        used, held = 0, 0
        for row in conn.execute(
            "SELECT state,reserved_nanodollars,actual_nanodollars FROM reservations"
        ):
            if row["state"] in ("settled", "breach"):
                if row["actual_nanodollars"] is None:
                    raise BudgetAccountingError("Settled attempt lacks an authoritative charge")
                used += row["actual_nanodollars"]
            else:
                if row["actual_nanodollars"] is not None:
                    raise BudgetAccountingError(
                        "Unresolved attempt unexpectedly has an actual charge"
                    )
                held += row["reserved_nanodollars"]
        if (used, held) != cls._totals(conn):
            raise BudgetAccountingError(
                "Persisted accounting totals disagree with the attempt ledger"
            )

    @classmethod
    def _record_review_event(
        cls,
        conn: sqlite3.Connection,
        event_type: str,
        reason: str,
        previous: str,
        resulting: str,
    ) -> None:
        used, held = cls._totals(conn)
        conn.execute(
            """INSERT INTO budget_review_events
            (event_type,reason,previous_blocked_reason,resulting_blocked_reason,
            used_nanodollars,held_nanodollars,created_utc) VALUES(?,?,?,?,?,?,?)""",
            (
                event_type,
                reason,
                previous,
                resulting,
                str(used),
                str(held),
                datetime.now(UTC).isoformat(),
            ),
        )

    @classmethod
    def _block(cls, conn: sqlite3.Connection, reason: str) -> None:
        prior = conn.execute(
            "SELECT blocked,blocked_reason FROM budget_config WHERE singleton=1"
        ).fetchone()
        previous = prior["blocked_reason"] if prior["blocked"] else ""
        # Missing billing can be reviewed, but must never overwrite a stronger stop.
        resulting = previous if previous and previous != "unverified_billing" else reason
        conn.execute(
            "UPDATE budget_config SET blocked=1,blocked_reason=? WHERE singleton=1", (resulting,)
        )
        cls._record_review_event(conn, "halt", reason, previous, resulting)

    def reserve(self, model: str, max_output_tokens: int, stage: str = "chat") -> str:
        if model != self._model:
            raise BudgetAccountingError("Requested model is outside the approved allowance")
        if (
            isinstance(max_output_tokens, bool)
            or not isinstance(max_output_tokens, int)
            or not 1 <= max_output_tokens <= _MAX_OUTPUT_TOKENS
        ):
            raise BudgetAccountingError("Completion ceiling must be an integer from 1 to 16384")
        if not isinstance(stage, str) or not _LABEL.fullmatch(stage):
            raise BudgetAccountingError("Invalid billing stage identifier")
        reserved = self._reservation_amount(max_output_tokens)
        reservation = uuid.uuid4().hex
        now = datetime.now(UTC).isoformat()
        with self._transaction() as conn:
            config = conn.execute("SELECT blocked FROM budget_config WHERE singleton=1").fetchone()
            if config["blocked"]:
                raise BudgetAccountingError("Allowance is blocked by an accounting discrepancy")
            used, held = self._totals(conn)
            if used + held + reserved > self._limit:
                raise BudgetExhausted("Insufficient uncommitted allowance for another HTTP attempt")
            conn.execute(
                """INSERT INTO reservations
                (reservation_id,model,max_output_tokens,stage,reserved_nanodollars,state,created_utc,updated_utc)
                VALUES(?,?,?,?,?,'pending',?,?)""",
                (reservation, model, max_output_tokens, stage, reserved, now, now),
            )
            self._store_totals(conn, used, held + reserved)
        return reservation

    def settle(self, reservation: str, actual_cost_usd, metadata: dict | None = None) -> None:
        try:
            actual = _nanodollars(_decimal(actual_cost_usd))
            billing_metadata = _metadata(metadata)
        except BudgetAccountingError:
            with self._transaction() as conn:
                self._block(conn, "invalid_settlement")
                conn.execute(
                    """UPDATE reservations SET state='unknown',error_type='InvalidSettlement',
                    updated_utc=?
                    WHERE reservation_id=? AND state IN ('pending','unknown')""",
                    (datetime.now(UTC).isoformat(), reservation),
                )
            raise
        error = None
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT * FROM reservations WHERE reservation_id=?", (reservation,)
            ).fetchone()
            if row is None:
                raise BudgetAccountingError("Unknown budget reservation")
            if row["state"] in ("settled", "breach"):
                if row["actual_nanodollars"] != actual:
                    used, held = self._totals(conn)
                    actual = max(actual, row["actual_nanodollars"])
                    conn.execute(
                        """UPDATE reservations SET state='breach',actual_nanodollars=?,
                        error_type='ConflictingSettlement',updated_utc=? WHERE reservation_id=?""",
                        (actual, datetime.now(UTC).isoformat(), reservation),
                    )
                    self._store_totals(conn, used + actual - row["actual_nanodollars"], held)
                    self._block(conn, "conflicting_settlement")
                    error = "Conflicting authoritative charges; allowance blocked"
                elif row["state"] == "breach":
                    error = "A previously recorded charge breached its reservation"
            else:
                used, held = self._totals(conn)
                breach = actual > row["reserved_nanodollars"]
                conn.execute(
                    """UPDATE reservations SET state=?,actual_nanodollars=?,metadata=?,updated_utc=?
                    WHERE reservation_id=?""",
                    (
                        "breach" if breach else "settled",
                        actual,
                        billing_metadata,
                        datetime.now(UTC).isoformat(),
                        reservation,
                    ),
                )
                self._store_totals(conn, used + actual, held - row["reserved_nanodollars"])
                if breach:
                    self._block(conn, "actual_cost_exceeded_reservation")
                    error = "Authoritative charge exceeded its reservation; allowance blocked"
        if error:
            raise BudgetAccountingError(error)

    def mark_unknown(self, reservation: str, error_type: str, metadata: dict | None = None) -> None:
        if not isinstance(error_type, str) or not _LABEL.fullmatch(error_type):
            raise BudgetAccountingError("Pass an exception type, not its message")
        billing_metadata = json.loads(_metadata(metadata)) if metadata is not None else None
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT state,metadata FROM reservations WHERE reservation_id=?", (reservation,)
            ).fetchone()
            if row is None:
                raise BudgetAccountingError("Unknown budget reservation")
            if row["state"] in ("pending", "unknown"):
                merged = json.loads(row["metadata"])
                if billing_metadata is not None:
                    merged.update(billing_metadata)
                conn.execute(
                    """UPDATE reservations SET state='unknown',error_type=?,metadata=?,updated_utc=?
                    WHERE reservation_id=?""",
                    (
                        error_type,
                        json.dumps(merged, sort_keys=True, separators=(",", ":")),
                        datetime.now(UTC).isoformat(),
                        reservation,
                    ),
                )

    def halt(self, reason: str) -> None:
        """Persist a stop for all workers without releasing unresolved attempts."""
        if not isinstance(reason, str) or not _LABEL.fullmatch(reason):
            raise BudgetAccountingError("Pass a short reason identifier, not response content")
        with self._transaction() as conn:
            self._block(conn, reason)

    def resume_after_review(
        self, reason: str, expected_blocked_reason: str = "unverified_billing"
    ) -> None:
        """Review only a missing-billing halt; never erase holds or repair a breach.

        The caller must explicitly review a stopped run before switching to
        permitted software-estimate handling. This is not a general unlock:
        monetary discrepancies and unexpected-model stops cannot be cleared.
        """
        if not isinstance(reason, str) or not _LABEL.fullmatch(reason) or "sk-" in reason.lower():
            raise BudgetAccountingError("Pass a short review reason identifier")
        if expected_blocked_reason != "unverified_billing":
            raise BudgetAccountingError("Only an unverified-billing stop can be reviewed")
        with self._transaction() as conn:
            self._audit_totals(conn)
            config = conn.execute(
                "SELECT blocked,blocked_reason FROM budget_config WHERE singleton=1"
            ).fetchone()
            if not config["blocked"] or config["blocked_reason"] != expected_blocked_reason:
                raise BudgetAccountingError("The expected reviewable billing stop is not active")
            protected = conn.execute("""SELECT COUNT(*) FROM reservations WHERE state='breach'
                OR error_type IN ('InvalidSettlement','ConflictingSettlement')""").fetchone()[0]
            if protected:
                raise BudgetAccountingError("A financial accounting discrepancy cannot be resumed")
            used, held = self._totals(conn)
            if used + held > self._limit:
                raise BudgetAccountingError("Committed charges exceed the unchanged allowance")
            conn.execute("UPDATE budget_config SET blocked=0,blocked_reason='' WHERE singleton=1")
            self._record_review_event(
                conn, "resume_after_review", reason, expected_blocked_reason, ""
            )

    def resolve_unknown_at_worst_case(self, reason: str) -> list[str]:
        """Revision 7 (owner, 19 Nov 2026): after an owner review, book every unresolved
        transport-failure attempt (no reply received) as charged at its FULL reserved worst
        case, then clear the `unresolved_workload_construction_billing` stop.

        Never lowers a charge. A breach, a settlement discrepancy, a reply-bearing unknown or
        any other stop cannot be cleared. Recorded as a review event `worst_case:<reason>`.
        """
        if not isinstance(reason, str) or not _LABEL.fullmatch(reason) or len(reason) > 100:
            raise BudgetAccountingError("Pass a short review reason identifier")
        stop = "unresolved_workload_construction_billing"
        with self._transaction() as conn:
            self._audit_totals(conn)
            config = conn.execute(
                "SELECT blocked,blocked_reason FROM budget_config WHERE singleton=1"
            ).fetchone()
            if not config["blocked"] or config["blocked_reason"] != stop:
                raise BudgetAccountingError("The reviewable unknown-billing stop is not active")
            protected = conn.execute("""SELECT COUNT(*) FROM reservations WHERE state='breach'
                OR error_type IN ('InvalidSettlement','ConflictingSettlement')""").fetchone()[0]
            if protected:
                raise BudgetAccountingError("A financial accounting discrepancy cannot be resumed")
            rows = conn.execute(
                "SELECT * FROM reservations WHERE state IN ('pending','unknown')"
            ).fetchall()
            if not rows or any(
                r["state"] != "unknown" or r["error_type"] not in _TRANSPORT_FAILURES for r in rows
            ):
                raise BudgetAccountingError("Only unknown transport failures can be reviewed")
            used, held = self._totals(conn)
            booked = sum(r["reserved_nanodollars"] for r in rows)
            now = datetime.now(UTC).isoformat()
            for r in rows:
                merged = json.loads(r["metadata"])
                merged.update(worst_case_review=reason, billing_verified=False)
                conn.execute(
                    """UPDATE reservations SET state='settled',actual_nanodollars=?,metadata=?,
                    updated_utc=? WHERE reservation_id=?""",
                    (
                        r["reserved_nanodollars"],
                        json.dumps(merged, sort_keys=True, separators=(",", ":")),
                        now,
                        r["reservation_id"],
                    ),
                )
            self._store_totals(conn, used + booked, held - booked)
            conn.execute("UPDATE budget_config SET blocked=0,blocked_reason='' WHERE singleton=1")
            self._record_review_event(conn, "resume_after_review", f"worst_case:{reason}", stop, "")
            self._audit_totals(conn)
        return [r["reservation_id"] for r in rows]

    def snapshot(self) -> dict:
        with self._transaction() as conn:
            self._audit_totals(conn)
            used, held = self._totals(conn)
            config = conn.execute(
                "SELECT blocked,blocked_reason FROM budget_config WHERE singleton=1"
            ).fetchone()
            counts = dict.fromkeys(("pending", "unknown", "settled", "breach"), 0)
            for row in conn.execute("SELECT state,COUNT(*) AS n FROM reservations GROUP BY state"):
                counts[row["state"]] = row["n"]
            counts["total"] = sum(counts.values())
            settled = conn.execute(
                "SELECT COALESCE(SUM(actual_nanodollars),0) FROM reservations WHERE state='settled'"
            ).fetchone()[0]
            values = {
                "limit": self._limit,
                "used": used,
                "held": held,
                "committed": used + held,
                "settled": int(settled),
                "remaining": max(0, self._limit - used - held),
                "overrun": max(0, used + held - self._limit),
            }
            return {
                **{f"{key}_usd": _usd(amount) for key, amount in values.items()},
                **{f"{key}_nanodollars": amount for key, amount in values.items()},
                "counts": counts,
                "blocked": bool(config["blocked"]),
                "blocked_reason": config["blocked_reason"],
                "model": self._model,
                "context_token_bound": self._context_bound,
                "max_input_per_mtok": str(self._input_price),
                "max_output_per_mtok": str(self._output_price),
                "review_events": conn.execute(
                    "SELECT COUNT(*) FROM budget_review_events "
                    "WHERE event_type='resume_after_review'"
                ).fetchone()[0],
                "halt_events": conn.execute(
                    "SELECT COUNT(*) FROM budget_review_events WHERE event_type='halt'"
                ).fetchone()[0],
            }
