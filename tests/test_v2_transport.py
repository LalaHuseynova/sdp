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


# Revision 6 (owner, 17 Nov 2026): a call whose connection was never made (DNS/TCP/TLS setup
# failed, so no request byte left the machine) is retried; every other failure still halts.


def flaky_wire(failures, exc=httpx.ConnectError):
    good, seen = wire()
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) <= failures:
            raise exc("offline: connection not made", request=request)
        return good.handle_request(request)

    return httpx.MockTransport(handler), seen, calls


@pytest.fixture
def no_wait(monkeypatch):
    import ams.research.workload.transport as T

    monkeypatch.setattr(T, "CONNECT_WAIT_S", 0)
    return T


@pytest.mark.parametrize("exc", [httpx.ConnectError, httpx.ConnectTimeout])
def test_never_connected_call_is_retried_and_billed_once(sonnet_session, no_wait, exc):
    transport, seen, calls = flaky_wire(3, exc)
    with ConstructionSession(sonnet_session) as s:
        s.arm_construction_mock("v2-bundle", V2_SPLIT, transport, Decimal("1.00"),
                                purpose="v2_generation", approval=approval())  # fmt: skip
        assert GuardedV2Client(s).complete(gen_request()).text == '{"ok": true}'
        snap = s.guard.snapshot()
        assert len(calls) == 4 and len(seen) == 1  # three never-connected tries, one call
        assert not snap["blocked"] and snap["held_nanodollars"] == 0
        assert snap["used_nanodollars"] == 100_000  # billed once ($0.0001)
        rows = s.db.execute("SELECT status FROM dispatches").fetchall()
        assert [r[0] for r in rows] == ["completed"]


def test_connection_never_back_still_halts(sonnet_session, no_wait):
    transport, seen, calls = flaky_wire(10**6)
    with ConstructionSession(sonnet_session) as s:
        s.arm_construction_mock("v2-bundle", V2_SPLIT, transport, Decimal("1.00"),
                                purpose="v2_generation", approval=approval())  # fmt: skip
        with pytest.raises(LedgerError, match="no retry"):
            GuardedV2Client(s).complete(gen_request())
        assert len(calls) == no_wait.CONNECT_RETRIES + 1 and not seen
        assert s.guard.snapshot()["blocked"]  # unchanged behaviour after the bounded retries


def test_failure_after_sending_is_never_retried(sonnet_session, no_wait):
    transport, seen, calls = flaky_wire(1, httpx.ReadError)  # request sent, reply lost
    with ConstructionSession(sonnet_session) as s:
        s.arm_construction_mock("v2-bundle", V2_SPLIT, transport, Decimal("1.00"),
                                purpose="v2_generation", approval=approval())  # fmt: skip
        with pytest.raises(LedgerError, match="no retry"):
            GuardedV2Client(s).complete(gen_request())
        assert len(calls) == 1 and s.guard.snapshot()["blocked"]


# Revision 7 (owner, 19 Nov 2026): an owner-reviewed transport failure of unknown billing is
# booked at its full worst case (never lower), its failed row is kept in an audit table, and
# the same request can then be sent again in the same session.


def test_reviewed_timeout_is_booked_at_worst_case_and_resent(sonnet_session, no_wait):
    transport, seen, calls = flaky_wire(1, httpx.ReadTimeout)  # sent, no reply
    with ConstructionSession(sonnet_session) as s:
        s.arm_construction_mock("v2-bundle", V2_SPLIT, transport, Decimal("1.00"),
                                purpose="v2_generation", approval=approval())  # fmt: skip
        client = GuardedV2Client(s)
        with pytest.raises(LedgerError, match="no retry"):
            client.complete(gen_request())
        held = s.guard.snapshot()["held_nanodollars"]
        assert s.guard.snapshot()["blocked"] and held > 0
        with pytest.raises(LedgerError, match="reviewed"):
            s.supersede_reviewed_failures("owner_review")  # guard not reviewed yet
        assert len(s.guard.resolve_unknown_at_worst_case("owner_review")) == 1
        snap = s.guard.snapshot()
        assert not snap["blocked"] and snap["held_nanodollars"] == 0
        assert snap["used_nanodollars"] == held  # booked at the full worst case
        assert s.supersede_reviewed_failures("owner_review") == 1
        kept = s.db.execute("SELECT status, reason FROM superseded_dispatches").fetchall()
        assert [tuple(r) for r in kept] == [("failed", "owner_review")]
        assert client.complete(gen_request()).text == '{"ok": true}'  # sent again
        snap = s.guard.snapshot()
        assert len(calls) == 2 and len(seen) == 1
        assert snap["used_nanodollars"] == held + 100_000 and not snap["blocked"]
        assert [r[0] for r in s.db.execute("SELECT status FROM dispatches")] == ["completed"]


def test_worst_case_review_refuses_other_stops(tmp_path):
    g = BudgetGuard(tmp_path / "g.sqlite", "30.00")
    with pytest.raises(BudgetAccountingError, match="not active"):
        g.resolve_unknown_at_worst_case("owner_review")  # nothing to review
    r = g.reserve(MODEL, 100)
    g.mark_unknown(r, "IncompleteResponse")  # a reply came back: not a transport failure
    g.halt("unresolved_workload_construction_billing")
    with pytest.raises(BudgetAccountingError, match="transport"):
        g.resolve_unknown_at_worst_case("owner_review")
    g2 = BudgetGuard(tmp_path / "g2.sqlite", "30.00")
    r2 = g2.reserve(MODEL, 100)
    g2.mark_unknown(r2, "APITimeoutError")
    g2.halt("actual_cost_exceeded_reservation")  # a stronger stop is never cleared
    with pytest.raises(BudgetAccountingError, match="not active"):
        g2.resolve_unknown_at_worst_case("owner_review")
    with pytest.raises(BudgetAccountingError, match="reason"):
        g2.resolve_unknown_at_worst_case("bad reason with spaces")


# Revision 11 (owner, 23 Nov 2026): HTTP 429 (provider rate limit) refuses the request before
# any model runs. The identical request is sent again after a wait (bounded), billed once; if
# the limit never clears the run still halts, and an owner review may book that attempt at its
# full worst case like a revision-7 transport failure.


def limited_wire(failures, status=429):
    good, seen = wire()
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) <= failures:
            return httpx.Response(status, json={"error": {"code": status,
                                                          "message": "offline: rate limited"}})
        return good.handle_request(request)

    return httpx.MockTransport(handler), seen, calls


@pytest.fixture
def no_limit_wait(monkeypatch):
    import ams.research.workload.transport as T

    monkeypatch.setattr(T, "RATE_LIMIT_WAIT_S", 0)
    return T


def test_rate_limited_call_waits_and_is_billed_once(sonnet_session, no_limit_wait):
    transport, seen, calls = limited_wire(3)
    with ConstructionSession(sonnet_session) as s:
        s.arm_construction_mock("v2-bundle", V2_SPLIT, transport, Decimal("1.00"),
                                purpose="v2_generation", approval=approval())  # fmt: skip
        assert GuardedV2Client(s).complete(gen_request()).text == '{"ok": true}'
        snap = s.guard.snapshot()
        assert len(calls) == 4 and len(seen) == 1  # three refusals, one answered call
        assert not snap["blocked"] and snap["held_nanodollars"] == 0
        assert snap["used_nanodollars"] == 100_000 and snap["counts"]["settled"] == 1
        assert [r[0] for r in s.db.execute("SELECT status FROM dispatches")] == ["completed"]


def test_rate_limit_that_never_clears_still_halts(sonnet_session, no_limit_wait):
    transport, seen, calls = limited_wire(10**6)
    with ConstructionSession(sonnet_session) as s:
        s.arm_construction_mock("v2-bundle", V2_SPLIT, transport, Decimal("1.00"),
                                purpose="v2_generation", approval=approval())  # fmt: skip
        with pytest.raises(LedgerError, match="no retry"):
            GuardedV2Client(s).complete(gen_request())
        assert len(calls) == no_limit_wait.RATE_LIMIT_RETRIES + 1 and not seen
        assert s.guard.snapshot()["blocked"]


@pytest.mark.parametrize("status", [400, 402, 500, 503])
def test_other_http_errors_are_still_never_retried(sonnet_session, no_limit_wait, status):
    transport, seen, calls = limited_wire(1, status)
    with ConstructionSession(sonnet_session) as s:
        s.arm_construction_mock("v2-bundle", V2_SPLIT, transport, Decimal("1.00"),
                                purpose="v2_generation", approval=approval())  # fmt: skip
        with pytest.raises(LedgerError, match="no retry"):
            GuardedV2Client(s).complete(gen_request())
        assert len(calls) == 1


def test_reviewed_rate_limit_is_booked_at_worst_case_and_resent(sonnet_session, no_limit_wait,
                                                               monkeypatch):  # fmt: skip
    monkeypatch.setattr(no_limit_wait, "RATE_LIMIT_RETRIES", 0)  # the P-B4 halt (rev10 code)
    transport, seen, calls = limited_wire(1)
    with ConstructionSession(sonnet_session) as s:
        s.arm_construction_mock("v2-bundle", V2_SPLIT, transport, Decimal("1.00"),
                                purpose="v2_generation", approval=approval())  # fmt: skip
        client = GuardedV2Client(s)
        with pytest.raises(LedgerError, match="no retry"):
            client.complete(gen_request())
        held = s.guard.snapshot()["held_nanodollars"]
        assert s.guard.snapshot()["blocked"] and held > 0
        assert len(s.guard.resolve_unknown_at_worst_case("owner_review_rev11")) == 1
        assert s.supersede_reviewed_failures("owner_review_rev11") == 1
        assert client.complete(gen_request()).text == '{"ok": true}'
        snap = s.guard.snapshot()
        assert snap["used_nanodollars"] == held + 100_000 and not snap["blocked"]
        kept = s.db.execute("SELECT status, reason FROM superseded_dispatches").fetchall()
        assert [tuple(r) for r in kept] == [("failed", "owner_review_rev11")]
