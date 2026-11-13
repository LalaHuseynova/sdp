"""Annotation-only paid scope on the EXISTING shared USD 30 accounting session."""

from __future__ import annotations

import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from ams.llm.openrouter_budget import current_key_budget
from ams.llm.providers.openai_client import OpenAIClient
from ams.research.dynamic.models import canonical, check
from ams.research.execution.session import ExecutionSession, _TrackedGuard, dispatch_hash
from ams.research.sequential.clients import request_from

from .design import OUTPUT_LIMIT, STAGE, verify


class _CaptureSDK:
    """Save received native JSON before billing validation can stop consumption."""

    def __init__(self, sdk, save):
        self.sdk, self.save, self.base_url = sdk, save, sdk.base_url
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def with_options(self, **kwargs):
        return _CaptureSDK(self.sdk.with_options(**kwargs), self.save)

    def create(self, **kwargs):
        response = self.sdk.chat.completions.create(**kwargs)
        self.save(response.model_dump(mode="json"))
        return response


class AnnotationSession(ExecutionSession):
    """Separate annotation authorization, never a scientific-execution unlock.

    Inherited experiment methods are explicitly unavailable. Paid annotation is
    restricted to the 32 exact allowlisted jobs; every arm/control/annotation
    still shares the same parent budget, lock, dispatch journal and unknown holds.
    """

    def arm_live(self, **kwargs):
        raise ValueError("Annotation scope cannot arm scientific execution")

    def complete(self, *args, **kwargs):
        raise ValueError("Annotation scope accepts complete_review only")

    def authorize(self, plan: Path):
        config, jobs = verify(plan)
        check(
            config["session_id"] == self.config["session_id"]
            and Path(config["session_directory"]).resolve() == self.directory,
            "Annotation cannot switch the shared allowance",
        )
        check(
            Decimal(config["review_task_reservation_ceiling_usd"]) <= 1,
            "Annotation reservation exceeds the disclosed USD 1 task bound",
        )
        self.jobs = {j["call_id"]: j for j in jobs}
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS annotation_native_responses "
            "(call_id TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        return config

    def arm_annotation(self, plan: Path, api_key: str):
        self.authorize(plan)
        provider = current_key_budget(api_key)
        check(provider.get("is_management_key") is not True, "Management keys cannot run inference")
        for amount in [
            provider.get("limit_remaining"),
            (provider.get("effective_budget") or {}).get("remaining_usd"),
        ]:
            if amount is not None:
                check(Decimal(str(amount)) > Decimal("0.03"), "Provider allowance unavailable")
        self.provider_preflight = provider
        check(
            self.guard.snapshot()["remaining_usd"] >= 1,
            "Insufficient shared allowance for review reservation",
        )
        self._set_mode("live")
        from openai import OpenAI

        self._sdk = OpenAI(
            api_key=api_key, base_url="https://openrouter.ai/api/v1", max_retries=0, timeout=120
        )
        self.mode = "live"

    def arm_annotation_mock(self, plan: Path, transport):
        self.authorize(plan)
        super().arm_mock(transport)

    def complete_review(self, job):
        call_id = job["call_id"]
        check(
            call_id in self.jobs and canonical(job) == canonical(self.jobs[call_id]),
            "Unplanned/changed annotation job",
        )
        request = request_from("chat", job["request"])
        check(request.max_tokens == OUTPUT_LIMIT, "Unbudgeted annotation output ceiling")
        key = request.cache_key("openrouter")
        text = canonical(asdict(request))
        row = self.db.execute("SELECT * FROM dispatches WHERE call_id=?", (call_id,)).fetchone()
        if row:
            check(
                row["request_key"] == key and row["request"] == text and row["stage"] == STAGE,
                "Annotation dispatch ID conflict",
            )
            check(row["status"] != "started", "Unknown annotation outcome; no automatic retry")
            result = json.loads(row["result"])
            check(dispatch_hash(row, result) == row["result_hash"], "Annotation result changed")
            return result
        check(
            not self.db.execute("SELECT 1 FROM dispatches WHERE status='started'").fetchone(),
            "Unresolved dispatch; no new annotation request",
        )
        budget = self.guard.snapshot()
        check(
            not budget["blocked"]
            and not budget["counts"]["unknown"]
            and not budget["counts"]["pending"],
            "Unverified billing/attempt; review stopped",
        )
        check(
            self._sdk is not None and self.mode in {"live", "mock"},
            "Annotation transport not armed",
        )
        self.db.execute(
            "INSERT INTO dispatches VALUES (?,?,?,?,'started',NULL,NULL,NULL)",
            (call_id, key, STAGE, text),
        )

        def capture(value):
            self.db.execute(
                "INSERT INTO annotation_native_responses VALUES (?,?)", (call_id, canonical(value))
            )

        adapter = OpenAIClient(
            provider="openrouter",
            sdk_client=_CaptureSDK(self._sdk, capture),
            budget_guard=_TrackedGuard(self, call_id),
            allow_estimated_billing=False,
        )
        adapter._allow_estimated_billing = False
        response, error = None, None
        try:
            response = adapter.complete(request)
        except Exception as exc:
            error = {
                "type": type(exc).__name__,
                "message": "Annotation transport/billing failed; inspect private receipt",
            }
        reservation = self.db.execute(
            "SELECT reservation FROM dispatches WHERE call_id=?", (call_id,)
        ).fetchone()[0]
        receipt = self._receipt(reservation)
        if (
            receipt
            and receipt["state"] in {"pending", "unknown", "breach"}
            and not self.guard.snapshot()["blocked"]
        ):
            self.guard.halt("unresolved_annotation_billing")
        paid = None if receipt and receipt["actual_nanodollars"] is None else "0"
        if self.mode == "live" and receipt and receipt["actual_nanodollars"] is not None:
            paid = str(Decimal(receipt["actual_nanodollars"]) / 1_000_000_000)
        result = {
            "response": asdict(response) if response else None,
            "error": error,
            "actual_paid_usd": paid,
            "annotation_source": "llm",
            "human_validated": False,
            "dispatch": {
                "session_id": self.config["session_id"],
                "call_id": call_id,
                "mode": self.mode,
                "receipt": receipt,
            },
        }
        row = self.db.execute("SELECT * FROM dispatches WHERE call_id=?", (call_id,)).fetchone()
        self.db.execute(
            "UPDATE dispatches SET status=?,result=?,result_hash=? WHERE call_id=?",
            (
                "failed" if error else "completed",
                canonical(result),
                dispatch_hash(row, result),
                call_id,
            ),
        )
        return result
