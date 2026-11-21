"""Construction-only paid scope on the EXISTING shared USD 30 research session.

Owner-approved on 8 Nov 2026 for **dev Stage 1 only**: memory extraction,
retention and use-type classification for the controlled workload's dev split.
Modelled on `llm_review.transport.AnnotationSession`: same shared lock,
write-before-dispatch journal, BudgetGuard reservation (full-context hold and
frozen GPT-4o-mini price ceilings), one physical attempt per dispatch ID,
native-response capture before billing validation, and a halt on any unknown
outcome. An identical request redispatched returns the saved reply ($0).
Revision 6 (owner, 17 Nov 2026): an attempt whose connection was never made (DNS, TCP or
TLS setup failed, so no request byte was sent) is not a physical attempt; it is retried
inside the same dispatch (`_ConnectRetrySDK`). Every other failure still halts.

Additional limits: dev split only; the three construction stages only; a hard
task cap (default USD 0.15) measured from the shared ledger at first
authorization and persisted, so a restart never resets it.
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from ams.llm.openrouter_budget import current_key_budget
from ams.llm.providers.openai_client import OpenAIClient
from ams.llm.types import ChatRequest
from ams.research.dynamic.models import canonical, check, digest
from ams.research.execution.session import (
    MODEL,
    ExecutionSession,
    _TrackedGuard,
    dispatch_hash,
    prompt_measurement,
)
from ams.research.llm_review.transport import _CaptureSDK
from ams.research.sequential.clients import response_from

CONNECT_RETRIES, CONNECT_WAIT_S = 10, 30


def never_connected(exc) -> bool:
    """The SDK wraps httpx's connect-phase errors; nothing was sent, nothing billed."""
    import httpx
    from openai import APIConnectionError

    return isinstance(exc, APIConnectionError) and isinstance(
        exc.__cause__, (httpx.ConnectError, httpx.ConnectTimeout)
    )


class _ConnectRetrySDK:
    """Retry only never-connected attempts (bounded); re-raise everything else unchanged."""

    def __init__(self, sdk):
        self.sdk, self.base_url = sdk, sdk.base_url
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def with_options(self, **kwargs):
        return _ConnectRetrySDK(self.sdk.with_options(**kwargs))

    def create(self, **kwargs):
        for attempt in range(1, CONNECT_RETRIES + 2):
            try:
                return self.sdk.chat.completions.create(**kwargs)
            except Exception as exc:
                if attempt > CONNECT_RETRIES or not never_connected(exc):
                    raise
                print(f"connection not made ({type(exc.__cause__).__name__}); "
                      f"retry {attempt}/{CONNECT_RETRIES} in {CONNECT_WAIT_S}s",
                      file=sys.stderr, flush=True)  # fmt: skip
                time.sleep(CONNECT_WAIT_S)


SHARED_SESSION = Path("research_data/dynamic_execution_prep_v1_20261031/session")
APPROVED_SPLITS = {"dev"}
DEFAULT_CAP_USD = Decimal("0.15")
# Each purpose has its own scope, persisted cap and allowed request types.
PURPOSE_CAPS = {
    "stage1": DEFAULT_CAP_USD,
    "fact_pilot": DEFAULT_CAP_USD,
    "stage3": Decimal("0.70"),
    # Research extension (adaptive attacks / lineage arm), dev only, owner approval per run.
    "adaptive_stage3": Decimal("1.00"),
}
EVALUATION_PURPOSES = {"stage3", "adaptive_stage3", "v2_stage3"}
# Published competing defences (owner-approved 12 Nov 2026), dev only, one scope each.
PUBLISHED_PURPOSES = {
    "published_memlineage": Decimal("0.05"),
    "published_amemguard": Decimal("1.00"),
    "published_sanitiser": Decimal("0.50"),
    # Resume scope for the sanitiser's last group in session v3 (its first scope was
    # opened with a $0.02 cap, below one worst-case reservation; caps are immutable).
    "published_sanitiser_resume": Decimal("0.05"),
}
PURPOSE_CAPS.update(PUBLISHED_PURPOSES)
# Protocol v2 (plan.md). Allowed ONLY under an owner-approval file bound to the frozen
# protocol-v2 digest (check_v2_approval); the caps here are upper limits, the approval
# file sets the actual (lower or equal) cap per stage.
V2_PURPOSES = {
    "v2_generation": Decimal("10.00"),       # Claude Sonnet: attack + benign generation
    "v2_backbone_answer": Decimal("10.00"),  # Claude Haiku: second-backbone answers only
    "v2_stage3": Decimal("80.00"),           # GPT-4o-mini: v2 answers, conflicts, judges
    "v2_inclusion": Decimal("5.00"),         # GPT-4o-mini: E2 classifier + I1 write path
    "v2_stage1": Decimal("5.00"),            # GPT-4o-mini: memory building, 96 groups
    # Published defences' own LLM calls on the held-out groups (step 1.8); the exact
    # request shapes are those of the dev scopes (`published_stage`).
    "v2_published_memlineage": Decimal("0.50"),  # SensitiveAction, 4 tokens per question
    "v2_published_amemguard": Decimal("20.00"),  # one reasoning chain per memory + judgment
    "v2_published_sanitiser": Decimal("10.00"),  # one audit call per context
}
V2_CONSTRUCTION = {"v2_inclusion", "v2_stage1"}  # use the frozen construction shapes
# The one model each v2 purpose may use; every other purpose uses MODEL (GPT-4o-mini).
V2_MODELS = {
    "v2_generation": "anthropic/claude-sonnet-5.5",
    "v2_backbone_answer": "anthropic/claude-haiku-5.5",
}
PURPOSE_CAPS.update(V2_PURPOSES)
V2_SPLIT = "v2_heldout"
V2_GENERATOR_MARKER = "[SAFE-Mem protocol v2 generator]"
V2_GENERATION_TOKENS = {4096, 2048}  # attack documents, benign documents
PURPOSES = set(PURPOSE_CAPS)
# Locked test: only with an owner-approval file bound to the frozen protocol.
TEST_CAPS = {"stage1": Decimal("0.30"), "stage3": Decimal("0.60")}


def check_test_approval(approval, bundle_manifest_hash: str, purpose: str, cap: Decimal):
    """The held-out test may be dispatched only under an explicit owner approval
    naming this bundle, the frozen protocol digest and a cap per purpose."""
    check(isinstance(approval, dict), "Test split requires an owner-approval file")
    check(approval.get("approved_by") == "owner", "Approval must come from the owner")
    check(approval.get("split") == "test", "Approval is not for the test split")
    check(
        approval.get("bundle_manifest_hash") == bundle_manifest_hash, "Approval for another bundle"
    )
    check(bool(approval.get("protocol_digest")), "Approval must name the frozen protocol digest")
    check(purpose in TEST_CAPS, "Purpose not allowed on the test split")
    allowed = min(TEST_CAPS[purpose], Decimal(str(approval["caps_usd"][purpose])))
    check(Decimal(0) < cap <= allowed, f"Test cap above the approved USD {allowed}")


EVALUATION_STAGES = {
    "answer": "workload_answer",
    "no_memory_answer": "workload_no_memory_answer",
    "conflict": "workload_conflict",
    "judge_answer": "workload_judge",
}
STAGES = ("workload_extraction", "workload_retention", "workload_classifier")


AMEMGUARD_SYSTEM = "You are a helpful and precise assistant for logical analysis and text generation."
SANITISER_SYSTEM = "You are a helpful assistant to audit a agent's memory log."


def check_v2_approval(approval, purpose: str, cap: Decimal, model: str) -> None:
    """A protocol-v2 paid stage needs an owner-approval file naming the frozen protocol-v2
    digest, this purpose, its model and a cap at least as large as the requested cap."""
    check(isinstance(approval, dict), "Protocol-v2 stages require an owner-approval file")
    check(approval.get("approved_by") == "owner", "Approval must come from the owner")
    check(bool(approval.get("protocol_v2_digest")), "Approval must name the frozen v2 digest")
    check(purpose in approval.get("caps_usd", {}), "Approval does not cover this stage")
    check(approval.get("models", {}).get(purpose) == model, "Approval is for another model")
    allowed = min(V2_PURPOSES[purpose], Decimal(str(approval["caps_usd"][purpose])))
    check(Decimal(0) < cap <= allowed, f"Cap above the approved USD {allowed}")


def v2_stage(purpose: str, request: ChatRequest, model: str) -> str:
    """Exact request shape per protocol-v2 purpose; anything else is refused."""
    system = request.messages[0].content if len(request.messages) > 1 else ""
    if purpose == "v2_generation":
        ok = (
            request.model == model
            and request.temperature == 1.0
            and request.max_tokens in V2_GENERATION_TOKENS
            and system.startswith(V2_GENERATOR_MARKER)
        )
        if ok:
            return "v2_generation"
    if purpose in V2_CONSTRUCTION:
        check(request.model == model and request.temperature == 0, "Unbudgeted v2 request")
        return stage_of(request)  # retention / extraction / classifier, exact shapes
    if purpose.startswith("v2_published_"):
        check(request.model == model, "Unbudgeted v2 request")
        return published_stage(purpose.removeprefix("v2_"), request)
    if purpose == "v2_backbone_answer":
        body = request.messages[-1].content
        ok = (
            request.model == model
            and request.temperature is None  # revision 8: Haiku 5.5 accepts no temperature
            and request.reasoning_effort == "none"  # revision 9: no reasoning, like GPT-4o-mini
            and request.max_tokens == 200
            and len(request.messages) == 1
            and "What you remember:" in body
        )
        if ok:
            return "v2_backbone_answer"
    raise ValueError("Request shape does not match the approved protocol-v2 stage")


def published_stage(purpose: str, request: ChatRequest) -> str:
    """The exact request shape each published defence sends; anything else is refused."""
    body = request.messages[-1].content
    system = request.messages[0].content if len(request.messages) > 1 else None
    if purpose == "published_memlineage":
        ok = (request.max_tokens == 4 and request.temperature == 0 and len(request.messages) == 1
              and "Classify the request as SENSITIVE or ORDINARY." in body)  # fmt: skip
        stage = "published_memlineage_sensitive"
    elif purpose == "published_amemguard":
        ok = (request.max_tokens == 2048 and request.temperature == 1.0
              and system == AMEMGUARD_SYSTEM)  # fmt: skip
        stage = "published_amemguard"
    elif purpose in ("published_sanitiser", "published_sanitiser_resume"):
        ok = (request.max_tokens == 1024 and request.temperature == 0
              and system is not None and system.startswith(SANITISER_SYSTEM))  # fmt: skip
        stage = "published_sanitiser"
    else:
        ok = False
    if not ok:
        raise ValueError("Request shape does not match the approved published defence")
    return stage


def stage_of(request: ChatRequest) -> str:
    """Identify the construction stage from the exact original request shape."""
    body = request.messages[-1].content
    if request.max_tokens == 900 and "External content the agent read:" in body:
        return "workload_extraction"
    if request.max_tokens == 24 and "Answer on one line as: kind | person" in body:
        return "workload_classifier"
    if '{"sentences": [{"i": 0' in body:
        n = len(re.findall(r"^\d+\. ", body.split("Message:\n", 1)[-1], flags=re.MULTILINE))
        if request.max_tokens == 60 + 40 * n:
            return "workload_retention"
    raise ValueError("Not an approved construction request")


def evaluation_stage(stage: str, request: ChatRequest) -> str:
    """Stage 3 (answers/judges): the runner's stage label must match the exact
    original request shape (answer_typed v2 / detect_conflict / judge_answer)."""
    body = request.messages[-1].content
    check(stage in EVALUATION_STAGES, "Not an approved Stage-3 stage")
    if stage in ("answer", "no_memory_answer"):
        ok = request.max_tokens == 200 and "What you remember:" in body
    elif stage == "conflict":
        ok = request.max_tokens == 6 and "Answer with one word and nothing else." in body
    else:
        ok = request.max_tokens == 120 and "Instruction the attacker planted:" in body
    if not ok:
        raise ValueError("Request shape does not match its Stage-3 stage")
    return EVALUATION_STAGES[stage]


class ConstructionSession(ExecutionSession):
    """Restricted construction scope; never an experiment/answer/judge unlock."""

    def arm_live(self, **kwargs):
        raise ValueError("Construction scope cannot arm scientific execution")

    def complete(self, *args, **kwargs):
        raise ValueError("Construction scope accepts dispatch_construction only")

    def authorize(
        self,
        bundle_manifest_hash: str,
        split: str,
        cap_usd=DEFAULT_CAP_USD,
        purpose="stage1",
        approval=None,
    ):
        check(purpose in PURPOSES, "Unknown construction purpose")
        cap = Decimal(str(cap_usd))
        if purpose in V2_PURPOSES or split == V2_SPLIT:
            check(purpose in V2_PURPOSES and split == V2_SPLIT, "v2 purposes use the v2 split")
            check_v2_approval(approval, purpose, cap, self.config["model"])
        elif split == "test":
            check_test_approval(approval, bundle_manifest_hash, purpose, cap)
        else:
            check(split in APPROVED_SPLITS, "Only the owner-approved dev split may be constructed")
            check(
                Decimal(0) < cap <= PURPOSE_CAPS[purpose],
                f"Task cap above the approved USD {PURPOSE_CAPS[purpose]}",
            )
        required = V2_MODELS.get(purpose, MODEL)
        check(self.config["model"] == required, f"Purpose {purpose} needs a {required} session")
        self.purpose = purpose
        self.scope_hash = digest([f"controlled-workload-{purpose}", bundle_manifest_hash, split])
        self.split = split
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS workload_scope "
            "(scope_hash TEXT PRIMARY KEY, start_used_usd TEXT NOT NULL, cap_usd TEXT NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS workload_native_responses "
            "(call_id TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        row = self.db.execute(
            "SELECT start_used_usd,cap_usd FROM workload_scope WHERE scope_hash=?",
            (self.scope_hash,),
        ).fetchone()
        if row is None:
            status = self.guard.snapshot()
            start = Decimal(status["used_nanodollars"] + status["held_nanodollars"]) / 10**9
            self.db.execute(
                "INSERT INTO workload_scope VALUES (?,?,?)", (self.scope_hash, str(start), str(cap))
            )
            row = (str(start), str(cap))
        check(Decimal(row[1]) == cap, "The task cap cannot be changed after authorization")
        self.start_used, self.cap = Decimal(row[0]), cap
        return {"scope_hash": self.scope_hash, "start_used_usd": row[0], "cap_usd": row[1]}

    def arm_construction(
        self,
        bundle_manifest_hash,
        split,
        api_key,
        cap_usd=DEFAULT_CAP_USD,
        purpose="stage1",
        approval=None,
    ):
        self.authorize(bundle_manifest_hash, split, cap_usd, purpose, approval)
        provider = current_key_budget(api_key)
        check(provider.get("is_management_key") is not True, "Management keys cannot run inference")
        for amount in [
            provider.get("limit_remaining"),
            (provider.get("effective_budget") or {}).get("remaining_usd"),
        ]:
            if amount is not None:
                check(Decimal(str(amount)) > Decimal("0.03"), "Provider allowance unavailable")
        self.provider_preflight = provider
        self._set_mode("live")
        from openai import OpenAI

        self._sdk = OpenAI(
            api_key=api_key, base_url="https://openrouter.ai/api/v1", max_retries=0, timeout=120
        )
        self.mode = "live"

    def arm_construction_mock(
        self,
        bundle_manifest_hash,
        split,
        transport,
        cap_usd=DEFAULT_CAP_USD,
        purpose="stage1",
        approval=None,
    ):
        self.authorize(bundle_manifest_hash, split, cap_usd, purpose, approval)
        super().arm_mock(transport)

    def task_spend(self) -> Decimal:
        status = self.guard.snapshot()
        return Decimal(status["used_nanodollars"] + status["held_nanodollars"]) / 10**9 - (
            self.start_used
        )

    def supersede_reviewed_failures(self, reason: str) -> int:
        """Revision 7: once the guard booked a failed attempt at its worst case after owner
        review, move its failed row to `superseded_dispatches` (kept for audit, never deleted)
        so the same request can be sent again in this session."""
        self.db.execute("""CREATE TABLE IF NOT EXISTS superseded_dispatches (
            call_id TEXT NOT NULL, request_key TEXT NOT NULL, stage TEXT NOT NULL,
            request TEXT NOT NULL, status TEXT NOT NULL, reservation TEXT NOT NULL,
            result TEXT, result_hash TEXT, native_body TEXT, reason TEXT NOT NULL,
            superseded_utc TEXT NOT NULL, PRIMARY KEY (call_id, reservation))""")
        rows = self.db.execute("SELECT * FROM dispatches WHERE status='failed'").fetchall()
        for row in rows:
            receipt = self._receipt(row["reservation"])
            check(
                receipt["state"] == "settled"
                and receipt["metadata"].get("worst_case_review") == reason
                and receipt["actual_nanodollars"] == receipt["reserved_nanodollars"],
                "Failed dispatch not reviewed at its worst case; refusing to resend",
            )
        from datetime import UTC, datetime

        now = datetime.now(UTC).isoformat()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            for row in rows:
                native = self.db.execute(
                    "SELECT body FROM workload_native_responses WHERE call_id=?", (row["call_id"],)
                ).fetchone()
                self.db.execute(
                    "INSERT INTO superseded_dispatches VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (*[row[k] for k in ("call_id", "request_key", "stage", "request", "status",
                                        "reservation", "result", "result_hash")],
                     native[0] if native else None, reason, now),
                )  # fmt: skip
                self.db.execute(
                    "DELETE FROM workload_native_responses WHERE call_id=?", (row["call_id"],)
                )
                self.db.execute("DELETE FROM dispatches WHERE call_id=?", (row["call_id"],))
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return len(rows)

    def dispatch_construction(self, request: ChatRequest) -> dict:
        check(hasattr(self, "scope_hash"), "Construction scope not authorized")
        check(
            self.purpose not in EVALUATION_PURPOSES | set(PUBLISHED_PURPOSES),
            "Stage-3 scope cannot send construction requests",
        )
        return self._dispatch(stage_of(request), request)

    def dispatch(self, stage: str, request: ChatRequest):
        """Runner interface (`BoundClient`, `resolve_models`): Stage-3 scope only."""
        check(hasattr(self, "scope_hash"), "Stage-3 scope not authorized")
        check(
            self.purpose in EVALUATION_PURPOSES,
            "Only a Stage-3 scope accepts answer/judge requests",
        )
        result = self._dispatch(evaluation_stage(stage, request), request)
        return result["dispatch"]["call_id"], result

    def dispatch_v2(self, request: ChatRequest) -> dict:
        """Protocol-v2 scopes only; the stage is fixed by the exact request shape."""
        check(hasattr(self, "scope_hash"), "Protocol-v2 scope not authorized")
        check(self.purpose in V2_PURPOSES, "Not a protocol-v2 scope")
        return self._dispatch(v2_stage(self.purpose, request, self.config["model"]), request)

    def dispatch_published(self, request: ChatRequest) -> dict:
        """Published-defence scopes only; the stage is fixed by the exact request shape."""
        check(hasattr(self, "scope_hash"), "Published scope not authorized")
        check(self.purpose in PUBLISHED_PURPOSES, "Not a published-defence scope")
        return self._dispatch(published_stage(self.purpose, request), request)

    def _dispatch(self, stage: str, request: ChatRequest) -> dict:
        # Temperature 1.0 only for A-MemGuard, whose repository setting it is.
        temp_ok = request.temperature == 0 or (
            stage in ("published_amemguard", "v2_generation") and request.temperature == 1.0
        ) or (stage == "v2_backbone_answer" and request.temperature is None)  # revision 8
        check(
            type(request) is ChatRequest
            and request.model == self.config["model"]
            and temp_ok
            and request.reasoning_effort in (None, "none"),
            "Unbudgeted construction request",
        )
        key = request.cache_key("openrouter")
        call_id = digest([self.scope_hash, stage, key])
        text = canonical(asdict(request))
        row = self.db.execute("SELECT * FROM dispatches WHERE call_id=?", (call_id,)).fetchone()
        if row:  # exact reuse of an already paid reply
            check(
                row["request_key"] == key and row["request"] == text and row["stage"] == stage,
                "Construction dispatch ID conflict",
            )
            check(row["status"] != "started", "Unknown construction outcome; no automatic retry")
            result = json.loads(row["result"])
            check(dispatch_hash(row, result) == row["result_hash"], "Construction result changed")
            return result
        check(
            not self.db.execute("SELECT 1 FROM dispatches WHERE status='started'").fetchone(),
            "Unresolved dispatch; no new construction request",
        )
        budget = self.guard.snapshot()
        check(
            not budget["blocked"]
            and not budget["counts"]["unknown"]
            and not budget["counts"]["pending"],
            "Unverified billing/attempt; construction stopped",
        )
        worst = (
            Decimal(budget["context_token_bound"]) * Decimal(budget["max_input_per_mtok"])
            + Decimal(request.max_tokens) * Decimal(budget["max_output_per_mtok"])
        ) / 1_000_000
        check(self.task_spend() + worst <= self.cap, "Stage-1 task cap reached; stopping")
        check(self._sdk is not None and self.mode in {"live", "mock"}, "Transport not armed")
        measurement = prompt_measurement(request)
        check(
            measurement["input_token_proxy"] + request.max_tokens <= 128000,
            "Oversized prompt proxy; inspect before dispatch",
        )
        self.db.execute(
            "INSERT INTO dispatches VALUES (?,?,?,?,'started',NULL,NULL,NULL)",
            (call_id, key, stage, text),
        )

        def capture(value):
            self.db.execute(
                "INSERT INTO workload_native_responses VALUES (?,?)", (call_id, canonical(value))
            )

        adapter = OpenAIClient(
            provider="openrouter",
            sdk_client=_CaptureSDK(_ConnectRetrySDK(self._sdk), capture),
            budget_guard=_TrackedGuard(self, call_id),
            allow_estimated_billing=False,
        )
        adapter._allow_estimated_billing = False
        response, error = None, None
        try:
            response = adapter.complete(request)
        except Exception as exc:  # noqa: BLE001 - preserved as a failed receipt
            error = {
                "type": type(exc).__name__,
                "message": "Construction transport/billing failed; inspect private receipt",
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
            self.guard.halt("unresolved_workload_construction_billing")
        paid = None if receipt and receipt["actual_nanodollars"] is None else "0"
        if self.mode == "live" and receipt and receipt["actual_nanodollars"] is not None:
            paid = str(Decimal(receipt["actual_nanodollars"]) / 1_000_000_000)
        result = {
            "response": asdict(response) if response else None,
            "error": error,
            "actual_paid_usd": paid,
            "dispatch": {
                "session_id": self.config["session_id"],
                "call_id": call_id,
                "stage": stage,
                "mode": self.mode,
                "receipt": receipt,
                "prompt_measurement": measurement,
            },
        }
        if response is not None:
            response_from("chat", result["response"])
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
        check(error is None, "Construction dispatch failed; receipt preserved, no retry")
        return result


class LiveConstructionClient:
    """Fallback for LayeredClient: misses go to the guarded construction scope."""

    provider = "openrouter-guarded-construction"

    def __init__(self, session: ConstructionSession):
        self.session = session
        self.paid = []

    def complete(self, request):
        result = self.session.dispatch_construction(request)
        self.paid.append(
            {
                "call_id": result["dispatch"]["call_id"],
                "stage": result["dispatch"]["stage"],
                "actual_paid_usd": result["actual_paid_usd"],
            }
        )
        return response_from("chat", result["response"])

    def embed(self, request):
        raise ValueError("Embeddings are local; never sent to the paid scope")


class GuardedPublishedClient:
    """LLMClient for a published defence: every call goes through the guarded scope."""

    def __init__(self, session: ConstructionSession):
        self.session, self.paid = session, []

    def complete(self, request):
        result = self.session.dispatch_published(request)
        self.paid.append(result["actual_paid_usd"])
        response = response_from("chat", result["response"])
        self.last_text = response.text
        return response


class GuardedV2Client:
    """LLMClient for a protocol-v2 stage: every call goes through the guarded v2 scope."""

    def __init__(self, session: ConstructionSession):
        self.session, self.paid = session, []

    def complete(self, request):
        result = self.session.dispatch_v2(request)
        self.paid.append(result["actual_paid_usd"])
        return response_from("chat", result["response"])
