"""Protocol v2, plan.md step 1.1: approved-model allowlist and the guarded generation scope.

Offline only: the real OpenAI SDK wire runs against httpx.MockTransport and the real
BudgetGuard does the accounting; no request can reach a real endpoint.
"""

from __future__ import annotations

import json
from decimal import Decimal

import httpx
import pytest

from ams.llm.budget import APPROVED_MODELS, BudgetAccountingError, BudgetGuard
from ams.llm.types import ChatRequest, Message
from ams.research.dynamic.models import LedgerError
from ams.research.execution.session import MODEL, ExecutionSession
from ams.research.workload.transport import (
    V2_GENERATOR_MARKER,
    V2_SPLIT,
    ConstructionSession,
    GuardedV2Client,
)

SONNET = "anthropic/claude-sonnet-5.5"


def wire(model_reply=SONNET):
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        return httpx.Response(200, json={
            "id": "gen-offline-v2", "model": model_reply, "object": "chat.completion",
            "created": 1,
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": '{"ok": true}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
                      "cost": "0.0001"}})  # fmt: skip

    return httpx.MockTransport(handler), seen


def gen_request(max_tokens=4096, temperature=1.0, model=SONNET, marker=True):
    system = (V2_GENERATOR_MARKER + " generate one attack") if marker else "hello"
    return ChatRequest((Message("system", system), Message("user", "family: planted fact")),
                       model, temperature=temperature, max_tokens=max_tokens)  # fmt: skip


def approval(cap="1.00", model=SONNET):
    return {"approved_by": "owner", "protocol_v2_digest": "f" * 64,
            "caps_usd": {"v2_generation": cap}, "models": {"v2_generation": model}}  # fmt: skip


@pytest.fixture
def sonnet_session(tmp_path):
    path = tmp_path / "gen_session"
    ExecutionSession.create(path, plan_hash="invented", model=SONNET).close()
    return path


@pytest.fixture
def gpt_session(tmp_path):
    path = tmp_path / "gpt_session"
    ExecutionSession.create(path, plan_hash="invented").close()
    return path


def test_guard_allowlist_and_price_ceilings(tmp_path):
    with pytest.raises(BudgetAccountingError, match="approved models"):
        BudgetGuard(tmp_path / "a.sqlite", "30.00", allowed_model="openai/gpt-4o")
    with pytest.raises(BudgetAccountingError, match="approved list prices"):
        BudgetGuard(tmp_path / "b.sqlite", "30.00", allowed_model=SONNET)  # gpt prices
    g = BudgetGuard(tmp_path / "c.sqlite", "30.00", allowed_model=SONNET,
                    max_input_per_mtok="2.00", max_output_per_mtok="10.00")  # fmt: skip
    snap = g.snapshot()
    assert snap["model"] == SONNET and Decimal(snap["max_input_per_mtok"]) == Decimal("2.00")
    with pytest.raises(BudgetAccountingError):
        g.reserve(MODEL, 100)  # a Sonnet guard never reserves for another model


def test_default_gpt_guard_unchanged(tmp_path):
    g = BudgetGuard(tmp_path / "d.sqlite", "30.00")
    assert g.snapshot()["model"] == MODEL
    assert APPROVED_MODELS[MODEL] == ("0.15", "0.60")


def test_v2_generation_requires_frozen_protocol_approval(sonnet_session):
    transport, _ = wire()
    with ConstructionSession(sonnet_session) as s:
        with pytest.raises(LedgerError, match="owner-approval"):
            s.arm_construction_mock("v2-bundle", V2_SPLIT, transport, Decimal("1.00"),
                                    purpose="v2_generation")  # fmt: skip
    with ConstructionSession(sonnet_session) as s:
        with pytest.raises(LedgerError, match="Cap above"):
            s.arm_construction_mock("v2-bundle", V2_SPLIT, transport, Decimal("2.00"),
                                    purpose="v2_generation", approval=approval("1.00"))


def test_v2_generation_dispatch_shape_cap_and_routing(sonnet_session):
    transport, seen = wire()
    with ConstructionSession(sonnet_session) as s:
        s.arm_construction_mock("v2-bundle", V2_SPLIT, transport, Decimal("1.00"),
                                purpose="v2_generation", approval=approval())  # fmt: skip
        client = GuardedV2Client(s)
        assert client.complete(gen_request()).text == '{"ok": true}'
        # Routing cap sent to OpenRouter uses the approved Sonnet list prices.
        assert seen[-1]["model"] == SONNET
        assert seen[-1]["provider"]["max_price"] == {"prompt": 2.0, "completion": 10.0,
                                                     "request": 0}  # fmt: skip
        # Identical request: reused, not re-sent.
        client.complete(gen_request())
        assert len(seen) == 1
        for bad in (gen_request(temperature=0.0), gen_request(max_tokens=999),
                    gen_request(marker=False), gen_request(model=MODEL)):  # fmt: skip
            with pytest.raises((ValueError, LedgerError)):
                client.complete(bad)
        assert len(seen) == 1  # refused requests never reached the wire


def test_purpose_model_pairing(sonnet_session, gpt_session):
    transport, _ = wire()
    with ConstructionSession(gpt_session) as s:  # generation never in a GPT-4o-mini session
        with pytest.raises(LedgerError, match="Approval is for another model"):
            s.arm_construction_mock("v2-bundle", V2_SPLIT, transport, Decimal("1.00"),
                                    purpose="v2_generation", approval=approval())
        # Even an approval naming the session's own model cannot pair generation with GPT.
        with pytest.raises(LedgerError, match="needs a anthropic/claude-sonnet-5.5 session"):
            s.arm_construction_mock("v2-bundle", V2_SPLIT, transport, Decimal("1.00"),
                                    purpose="v2_generation", approval=approval(model=MODEL))
    with ConstructionSession(sonnet_session) as s:  # GPT purposes never in a Sonnet session
        with pytest.raises(LedgerError, match="openai/gpt-4o-mini session"):
            s.arm_construction_mock("bundle", "dev", transport, Decimal("0.10"), purpose="stage1")
