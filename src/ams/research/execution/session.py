"""One durable USD 30 allowance and write-before-dispatch response journal.

Unknown outcomes stop the complete session. A pending response is never retried
merely because a process restarted. This is intentionally stricter than the
protocol's maximum of two attempts. No SDK, token or callable is serialized.
"""

from __future__ import annotations

import fcntl
import json
import os
import sqlite3
import uuid
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from ams.llm.budget import APPROVED_MODELS, BudgetGuard
from ams.llm.types import ChatRequest
from ams.research.dynamic.models import LedgerError, canonical, check, digest
from ams.research.sequential.clients import response_from

MODEL = "openai/gpt-4o-mini"
LIMIT = "30.00"
STAGE_LIMITS = {
    "answer": 200,
    "conflict": 6,
    "no_memory_answer": 200,
    "judge_entry": 120,
    "judge_answer": 120,
    "classifier_catalog": 24,
}


def dispatch_hash(row, result):
    return digest([row["call_id"], row["request_key"], row["stage"], row["request"], result])


def new_json(path: Path, value):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(canonical(value) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def prompt_measurement(request: ChatRequest) -> dict:
    """A reproducible byte proxy, NOT measured native tokenizer usage.

    The billing guard reserves the full 128k context independently of this proxy.
    No tokenizer download, dependency installation or paid counting call occurs.
    """
    size = sum(len(m.content.encode("utf-8")) for m in request.messages)
    proxy = size + 64 * len(request.messages) + 1024
    return {
        "utf8_content_bytes": size,
        "message_count": len(request.messages),
        "input_token_proxy": proxy,
        "method": "utf8_bytes_plus_64_per_message_plus_1024_scaffold",
        "native_tokens_measured": False,
        "guaranteed_token_bound": False,
    }


class _TrackedGuard:
    def __init__(self, session, call_id):
        self.session, self.call_id = session, call_id

    def reserve(self, *args, **kwargs):
        reservation = self.session.guard.reserve(*args, **kwargs)
        self.session.db.execute(
            "UPDATE dispatches SET reservation=? WHERE call_id=? AND status='started'",
            (reservation, self.call_id),
        )
        return reservation

    def __getattr__(self, name):
        return getattr(self.session.guard, name)


class ExecutionSession:
    """All arms/jobs/controls share this directory; copying it is not a new allowance.

    A fresh directory is explicitly initialized once. It contains no credentials.
    Live transport must be explicitly armed with a scientific preflight; current
    engineering plans cannot pass that gate. MockTransport is a separate test mode.
    """

    @classmethod
    def create(cls, directory: Path, *, plan_hash: str, model: str = MODEL):
        directory = Path(directory).resolve()
        check(not directory.exists(), "Execution session exists; reopen without resetting it")
        directory.mkdir(parents=True, mode=0o700)
        new_json(
            directory / "session.json",
            {
                "schema": "dynamic-shared-execution-session-v1",
                "session_id": uuid.uuid4().hex,
                "limit_usd": LIMIT,
                "model": model,
                "plan_hash": plan_hash,
            },
        )
        (directory / ".gitignore").write_text("*\n!.gitignore\n")
        result = cls(directory)
        return result

    def __init__(self, directory: Path):
        self.directory = Path(directory).resolve()
        check((self.directory / "session.json").is_file(), "No initialized execution session")
        self.config = json.loads((self.directory / "session.json").read_text())
        check(
            set(self.config) == {"schema", "session_id", "limit_usd", "model", "plan_hash"}
            and self.config["schema"] == "dynamic-shared-execution-session-v1"
            and self.config["limit_usd"] == LIMIT
            and self.config["model"] in APPROVED_MODELS,
            "Unsupported or increased execution allowance",
        )
        self._lock = (self.directory / "dispatch.lock").open("a+b")
        try:
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._lock.close()
            raise LedgerError("Another dispatcher owns this shared session") from exc
        self.db = None
        try:
            model = self.config["model"]
            prices = APPROVED_MODELS[model]
            self.guard = BudgetGuard(
                self.directory / "budget.sqlite",
                LIMIT,
                allowed_model=model,
                max_input_per_mtok=prices[0],
                max_output_per_mtok=prices[1],
            )
            self.db = sqlite3.connect(self.directory / "dispatch.sqlite", isolation_level=None)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS dispatches (
                    call_id TEXT PRIMARY KEY, request_key TEXT NOT NULL,
                    stage TEXT NOT NULL, request TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('started','completed','failed')),
                    reservation TEXT, result TEXT, result_hash TEXT);
            """)
            saved = self.db.execute("SELECT value FROM metadata WHERE key='session'").fetchone()
            if saved is None:
                self.db.execute(
                    "INSERT INTO metadata VALUES ('session',?)", (canonical(self.config),)
                )
            else:
                check(saved[0] == canonical(self.config), "Session identity changed")
            check(
                self.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                "Corrupt dispatch journal",
            )
            for row in self.db.execute("SELECT * FROM dispatches WHERE result IS NOT NULL"):
                check(
                    dispatch_hash(row, json.loads(row["result"])) == row["result_hash"],
                    "Dispatch result changed",
                )
            for name in ("budget.sqlite", "dispatch.sqlite", "dispatch.lock"):
                (self.directory / name).chmod(0o600)
        except BaseException:
            self.close()
            raise
        self._sdk = None
        self.mode = None

    def close(self):
        sdk = getattr(self, "_sdk", None)
        if sdk is not None:
            sdk.close()
        if self.db is not None:
            self.db.close()
        self._lock.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def arm_live(self, *, scientific_plan: Path, api_key: str):
        # Refuse engineering-only/provisional plans BEFORE reading/using a credential.
        from ams.research.planning.pipeline import require_scientific_freeze

        require_scientific_freeze(scientific_plan)
        self._set_mode("live")
        # A future scientific-manifest promotion must implement the gate above.
        from openai import OpenAI

        self._sdk = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1", max_retries=0)
        self.mode = "live"

    def arm_mock(self, transport):
        """Test-only real SDK/wire integration; requires httpx.MockTransport exactly."""
        import httpx
        from openai import OpenAI

        check(type(transport) is httpx.MockTransport, "Only MockTransport in offline test mode")
        self._set_mode("mock")
        self._sdk = OpenAI(
            api_key="offline-fixture-key",
            base_url="https://openrouter.ai/api/v1",
            max_retries=0,
            http_client=httpx.Client(transport=transport),
        )
        self.mode = "mock"

    def _set_mode(self, mode):
        saved = self.db.execute("SELECT value FROM metadata WHERE key='transport_mode'").fetchone()
        check(saved is None or saved[0] == mode, "Mock and live billing cannot share a session")
        check(self._sdk is None, "Close/reopen before attaching a different transport")
        if saved is None:
            self.db.execute("INSERT INTO metadata VALUES ('transport_mode',?)", (mode,))

    def _receipt(self, reservation):
        if reservation is None:
            return None
        with sqlite3.connect(self.guard.path.resolve().as_uri() + "?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM reservations WHERE reservation_id=?", (reservation,)
            ).fetchone()
        check(row is not None, "Missing dispatch reservation")
        return {
            "reservation_id": reservation,
            "state": row["state"],
            "reserved_nanodollars": row["reserved_nanodollars"],
            "actual_nanodollars": row["actual_nanodollars"],
            "metadata": json.loads(row["metadata"]),
        }

    def complete(self, call_id: str, stage: str, request: ChatRequest, *, fault=None):
        check(
            type(request) is ChatRequest and request.model == MODEL, "Unbudgeted request model/type"
        )
        check(stage in STAGE_LIMITS, "Unplanned dispatch stage")
        check(
            request.max_tokens == STAGE_LIMITS[stage]
            and request.temperature == 0
            and request.reasoning_effort in (None, "none"),
            "Request differs from frozen stage limits",
        )
        key = request.cache_key("openrouter")
        if stage == "classifier_catalog":
            check(
                call_id == digest([stage, key]),
                "Classifier responses must use one shared exact key",
            )
        request_text = canonical(asdict(request))
        row = self.db.execute("SELECT * FROM dispatches WHERE call_id=?", (call_id,)).fetchone()
        if row:
            check(
                row["request_key"] == key
                and row["stage"] == stage
                and row["request"] == request_text,
                "Dispatch ID reused with changed request",
            )
            check(
                row["status"] != "started",
                "Unknown dispatch outcome; automatic redispatch forbidden",
            )
            check(
                dispatch_hash(row, json.loads(row["result"])) == row["result_hash"],
                "Dispatch result changed",
            )
            return json.loads(row["result"])
        check(
            not self.db.execute("SELECT 1 FROM dispatches WHERE status='started'").fetchone(),
            "Unresolved dispatch exists; review before any further paid request",
        )
        budget = self.guard.snapshot()
        check(
            not budget["blocked"]
            and not budget["counts"]["unknown"]
            and not budget["counts"]["pending"],
            "Unresolved billing/attempt; all new dispatch stopped",
        )
        check(self._sdk is not None and self.mode in {"live", "mock"}, "Transport is not armed")
        measurement = prompt_measurement(request)
        check(
            measurement["input_token_proxy"] + request.max_tokens <= 128000,
            "Oversized prompt proxy; inspect before dispatch",
        )
        self.db.execute(
            "INSERT INTO dispatches VALUES (?,?,?,?,'started',NULL,NULL,NULL)",
            (call_id, key, stage, request_text),
        )
        if fault:
            fault("after_dispatch_intent")
        from ams.llm.providers.openai_client import OpenAIClient

        adapter = OpenAIClient(
            provider="openrouter",
            sdk_client=self._sdk,
            budget_guard=_TrackedGuard(self, call_id),
            allow_estimated_billing=False,
        )
        # Reject environment switches that permit unverified billing.
        adapter._allow_estimated_billing = False
        response, error = None, None
        try:
            response = adapter.complete(request)
        except Exception as exc:
            error = {
                "type": type(exc).__name__,
                "message": "Guarded dispatch failed; inspect the private billing journal",
            }
        row = self.db.execute(
            "SELECT reservation FROM dispatches WHERE call_id=?", (call_id,)
        ).fetchone()
        receipt = self._receipt(row[0])
        if receipt and receipt["state"] in {"pending", "unknown", "breach"}:
            self.guard.halt("unresolved_execution_dispatch")
        if fault:
            fault("after_provider_before_response_save")
        paid = None if receipt and receipt["actual_nanodollars"] is None else "0"
        if self.mode == "live" and receipt and receipt["actual_nanodollars"] is not None:
            paid = str(Decimal(receipt["actual_nanodollars"]) / 1_000_000_000)
        result = {
            "response": asdict(response) if response is not None else None,
            "error": error,
            "actual_paid_usd": paid,
            "dispatch": {
                "session_id": self.config["session_id"],
                "call_id": call_id,
                "mode": self.mode,
                "receipt": receipt,
                "prompt_measurement": measurement,
            },
        }
        if response is not None:
            response_from("chat", result["response"])
        text = canonical(result)
        row = self.db.execute("SELECT * FROM dispatches WHERE call_id=?", (call_id,)).fetchone()
        self.db.execute(
            "UPDATE dispatches SET status=?,result=?,result_hash=? WHERE call_id=?",
            ("failed" if error else "completed", text, dispatch_hash(row, result), call_id),
        )
        return json.loads(text)

    def complete_shared_classifier(self, request: ChatRequest):
        """Controller preparation only; never a classifier miss fallback in an arm."""
        return self.complete(
            digest(["classifier_catalog", request.cache_key("openrouter")]),
            "classifier_catalog",
            request,
        )

    def summary(self):
        budget = self.guard.snapshot()
        rows = self.db.execute("SELECT status,COUNT(*) FROM dispatches GROUP BY status").fetchall()
        return {
            "session_id": self.config["session_id"],
            "budget": budget,
            "dispatches": dict(rows),
            "transport_armed": self._sdk is not None,
            "transport_mode": self.mode,
            "paid_dispatch_enabled": self.mode == "live",
        }
