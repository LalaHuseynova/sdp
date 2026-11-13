"""Explicit provisional scope on the existing shared budget; exact-request reuse."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ams.llm.openrouter_budget import current_key_budget
from ams.llm.providers.openai_client import OpenAIClient
from ams.research.dynamic.models import check, digest
from ams.research.execution.session import STAGE_LIMITS, ExecutionSession
from ams.research.llm_review.transport import _CaptureSDK

from .preparation import verify

STAGES = {"answer", "conflict", "no_memory_answer", "judge_entry", "judge_answer"}


class ProvisionalSession(ExecutionSession):
    def arm_live(self, **kwargs):
        raise ValueError("Use the explicit AI-provisional scope; scientific execution is unchanged")

    def complete(self, *args, **kwargs):
        raise ValueError("Only scope-bound dispatch is available")

    def authorize(self, plan):
        cfg, spec = verify(plan)
        check(
            cfg["session_id"] == self.config["session_id"]
            and Path(cfg["session_directory"]).resolve() == self.directory,
            "Cannot change research allowance",
        )
        self.scope, self.study = cfg, spec
        self.scope_hash = digest([cfg, spec])
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS provisional_native_responses "
            "(call_id TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        return cfg

    def arm_provisional(self, plan, api_key):
        self.authorize(plan)
        provider = current_key_budget(api_key)
        check(provider.get("is_management_key") is not True, "Cannot use a management key")
        for value in [
            provider.get("limit_remaining"),
            (provider.get("effective_budget") or {}).get("remaining_usd"),
        ]:
            if value is not None:
                check(Decimal(str(value)) >= Decimal("0.03"), "Provider allowance exhausted")
        self.provider_preflight = provider
        self._set_mode("live")
        adapter = OpenAIClient(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            provider="openrouter",
            budget_guard=self.guard,
            allow_estimated_billing=False,
            timeout=120,
        )
        self._sdk = adapter._client
        self.mode = "live"

    def arm_provisional_mock(self, plan, transport):
        self.authorize(plan)
        super().arm_mock(transport)

    def dispatch(self, stage, request):
        check(
            hasattr(self, "scope")
            and stage in STAGES
            and request.max_tokens == STAGE_LIMITS[stage],
            "Unplanned provisional stage or fallback",
        )
        call_id = digest([self.scope_hash, stage, request.cache_key("openrouter")])
        old = self.db.execute("SELECT 1 FROM dispatches WHERE call_id=?", (call_id,)).fetchone()
        if old is None:
            status = self.guard.snapshot()
            used = Decimal(status["used_nanodollars"] + status["held_nanodollars"]) / 1_000_000_000
            worst = (
                Decimal(status["context_token_bound"]) * Decimal(status["max_input_per_mtok"])
                + Decimal(request.max_tokens) * Decimal(status["max_output_per_mtok"])
            ) / 1_000_000
            check(
                used + worst
                <= Decimal(self.scope["budget_start_used_usd"])
                + Decimal(self.scope["additional_task_limit_usd"]),
                "Additional USD 5 task limit reached",
            )
        sdk = self._sdk
        if sdk is not None:
            from ams.research.dynamic.models import canonical

            def save(native):
                self.db.execute(
                    "INSERT INTO provisional_native_responses VALUES (?,?)",
                    (call_id, canonical(native)),
                )

            self._sdk = _CaptureSDK(sdk, save)
        try:
            result = ExecutionSession.complete(self, call_id, stage, request)
        finally:
            self._sdk = sdk
        check(
            result["error"] is None and result["response"] is not None,
            "Dispatch failed; preserve receipt and stop without automatic retry",
        )
        return call_id, result
