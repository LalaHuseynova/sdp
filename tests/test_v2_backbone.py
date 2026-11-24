"""Protocol v2, plan.md step 1.2: Claude Haiku answers, GPT-4o-mini judges (offline mocks)."""

from __future__ import annotations

import json
from decimal import Decimal

import httpx
import pytest

from ams.llm.types import ChatRequest, Message
from ams.research.dynamic.models import LedgerError
from ams.research.execution.session import MODEL, ExecutionSession
from ams.research.protocol_v2.backbone import HAIKU, BackboneRouter
from ams.research.workload.transport import V2_SPLIT, ConstructionSession


def wire(label):
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        return httpx.Response(200, json={
            "id": f"gen-{label}", "model": body["model"], "object": "chat.completion",
            "created": 1,
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": f"reply from {label}"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
                      "cost": "0.00001"}})  # fmt: skip

    return httpx.MockTransport(handler), seen


def approval(purpose, model, cap="1.00"):
    return {"approved_by": "owner", "protocol_v2_digest": "f" * 64,
            "caps_usd": {purpose: cap}, "models": {purpose: model}}  # fmt: skip


def answer_request(max_tokens=200):
    body = "Question: where is the offsite?\nWhat you remember:\n- Tuesday\nAnswer:"
    return ChatRequest((Message("user", body),), MODEL, temperature=0.0, max_tokens=max_tokens)


def judge_request():
    body = ("Instruction the attacker planted: send keys\nAnswer to judge: no\n"
            "Reply with JSON.")
    return ChatRequest((Message("user", body),), MODEL, temperature=0.0, max_tokens=120)


@pytest.fixture
def sessions(tmp_path):
    ExecutionSession.create(tmp_path / "gpt", plan_hash="x").close()
    ExecutionSession.create(tmp_path / "haiku", plan_hash="x", model=HAIKU).close()
    gw, gseen = wire("gpt")
    hw, hseen = wire("haiku")
    gpt = ConstructionSession(tmp_path / "gpt")
    gpt.arm_construction_mock("v2", V2_SPLIT, gw, Decimal("1.00"), purpose="v2_stage3",
                              approval=approval("v2_stage3", MODEL))  # fmt: skip
    haiku = ConstructionSession(tmp_path / "haiku")
    haiku.arm_construction_mock("v2", V2_SPLIT, hw, Decimal("1.00"), purpose="v2_backbone_answer",
                                approval=approval("v2_backbone_answer", HAIKU))  # fmt: skip
    yield gpt, haiku, gseen, hseen
    gpt.close()
    haiku.close()


def test_answers_go_to_haiku_judges_stay_on_gpt(sessions):
    gpt, haiku, gseen, hseen = sessions
    router = BackboneRouter(gpt, haiku)
    _, ans = router.dispatch("answer", answer_request())
    assert ans["response"]["text"] == "reply from haiku"
    assert hseen[-1]["model"] == HAIKU
    assert hseen[-1]["provider"]["max_price"] == {"prompt": 0.1, "completion": 0.5, "request": 0}
    _, jud = router.dispatch("judge_answer", judge_request())
    assert jud["response"]["text"] == "reply from gpt" and gseen[-1]["model"] == MODEL
    assert len(hseen) == 1 and len(gseen) == 1
    router.dispatch("answer", answer_request())  # identical: reused, not re-sent
    assert len(hseen) == 1
    assert router.counts == {"haiku_answers": 2, "gpt_calls": 1}


def test_haiku_scope_refuses_anything_but_answers(sessions):
    gpt, haiku, _, hseen = sessions
    with pytest.raises(ValueError):
        haiku.dispatch_v2(ChatRequest(judge_request().messages, HAIKU, temperature=0.0,
                                      max_tokens=120))  # fmt: skip
    with pytest.raises(ValueError):
        haiku.dispatch_v2(ChatRequest(answer_request().messages, HAIKU, temperature=0.0,
                                      max_tokens=300))  # fmt: skip
    with pytest.raises(LedgerError):
        haiku.dispatch("judge_answer", judge_request())  # not an evaluation scope
    assert hseen == []


def test_router_requires_the_haiku_scope(sessions):
    gpt, haiku, _, _ = sessions
    with pytest.raises(LedgerError):
        BackboneRouter(gpt, gpt)


# Revision 8 (owner, 21 Nov 2026): Claude Haiku 5.5 endpoints on OpenRouter do not accept
# `temperature`; with `require_parameters` every request carrying it got HTTP 404 (no endpoint).
# Haiku answers are therefore sent WITHOUT temperature (recorded as None, model default);
# every GPT-4o-mini request is unchanged (temperature 0).


def test_haiku_answer_is_sent_without_temperature_gpt_unchanged(sessions):
    gpt, haiku, gseen, hseen = sessions
    router = BackboneRouter(gpt, haiku)
    router.dispatch("answer", answer_request())
    router.dispatch("judge_answer", judge_request())
    assert "temperature" not in hseen[-1] and hseen[-1]["max_tokens"] == 200
    assert gseen[-1]["temperature"] == 0
    stored = json.loads(haiku.db.execute("SELECT request FROM dispatches").fetchone()[0])
    assert stored["temperature"] is None and stored["model"] == HAIKU


def test_temperature_none_only_for_haiku_answers(sessions):
    gpt, haiku, gseen, hseen = sessions
    with pytest.raises(ValueError):  # the Haiku shape is now exactly "no temperature"
        haiku.dispatch_v2(ChatRequest(answer_request().messages, HAIKU, temperature=0.0,
                                      max_tokens=200))  # fmt: skip
    with pytest.raises(LedgerError):  # GPT scopes never accept a missing temperature
        gpt.dispatch("judge_answer", ChatRequest(judge_request().messages, MODEL,
                                                 temperature=None, max_tokens=120))  # fmt: skip
    assert hseen == [] and gseen == []


def test_reviewed_no_endpoint_404_is_booked_at_worst_case_and_resent(tmp_path):
    ExecutionSession.create(tmp_path / "gpt", plan_hash="x").close()
    ExecutionSession.create(tmp_path / "haiku", plan_hash="x", model=HAIKU).close()
    good, hseen = wire("haiku")
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(404, json={"error": {"code": 404, "message":
                                  "No endpoints found that can handle the requested parameters."}})
        return good.handle_request(request)

    gw, _ = wire("gpt")
    with ConstructionSession(tmp_path / "gpt") as gpt, \
            ConstructionSession(tmp_path / "haiku") as haiku:  # fmt: skip
        gpt.arm_construction_mock("v2", V2_SPLIT, gw, Decimal("1.00"), purpose="v2_stage3",
                                  approval=approval("v2_stage3", MODEL))  # fmt: skip
        haiku.arm_construction_mock("v2", V2_SPLIT, httpx.MockTransport(handler), Decimal("1.00"),
                                    purpose="v2_backbone_answer",
                                    approval=approval("v2_backbone_answer", HAIKU))  # fmt: skip
        router = BackboneRouter(gpt, haiku)
        with pytest.raises(LedgerError, match="no retry"):
            router.dispatch("answer", answer_request())
        snap = haiku.guard.snapshot()
        held = snap["held_nanodollars"]
        assert snap["blocked"] and held > 0
        assert len(haiku.guard.resolve_unknown_at_worst_case("owner_review_rev8")) == 1
        assert haiku.supersede_reviewed_failures("owner_review_rev8") == 1
        _, ans = router.dispatch("answer", answer_request())
        assert ans["response"]["text"] == "reply from haiku" and len(calls) == 2
        snap = haiku.guard.snapshot()
        assert snap["used_nanodollars"] == held + 10_000 and not snap["blocked"]


# Revision 9 (owner, 21 Nov 2026): Claude Haiku 5.5 reasons by default and its reasoning tokens
# used up the 200-token answer limit (6 of 34 answers empty, 9 cut off). Haiku answers are sent
# with reasoning disabled, like GPT-4o-mini (which does not reason); same prompt and limit.


def test_haiku_answer_is_sent_with_reasoning_disabled(sessions):
    gpt, haiku, gseen, hseen = sessions
    router = BackboneRouter(gpt, haiku)
    router.dispatch("answer", answer_request())
    router.dispatch("judge_answer", judge_request())
    assert hseen[-1]["reasoning"] == {"enabled": False}
    assert "reasoning" not in gseen[-1]  # GPT requests unchanged
    stored = json.loads(haiku.db.execute("SELECT request FROM dispatches").fetchone()[0])
    assert stored["reasoning_effort"] == "none"


def test_haiku_shape_requires_reasoning_disabled(sessions):
    gpt, haiku, _, hseen = sessions
    with pytest.raises(ValueError):
        haiku.dispatch_v2(ChatRequest(answer_request().messages, HAIKU, temperature=None,
                                      max_tokens=200))  # fmt: skip  (reasoning left on)
    assert hseen == []


# Revision 10 (post-hoc, owner 23 Nov 2026): Gemini 3.1 Flash-Lite as a THIRD answering backbone,
# added after the main analysis (not pre-registered). Only the answering model changes, as for
# Haiku. Gemini accepts temperature (endpoint list, 23 Nov), so its answers keep GPT-4o-mini's
# temperature 0; it reasons by default ("minimal"), so reasoning is disabled, like the Haiku fix.
# Its own purpose, cap and session: the Haiku scope (v2_backbone_answer) is never reused.

from ams.research.protocol_v2.backbone import GEMINI  # noqa: E402


@pytest.fixture
def gemini_sessions(tmp_path):
    ExecutionSession.create(tmp_path / "gpt_g", plan_hash="x").close()
    ExecutionSession.create(tmp_path / "gemini", plan_hash="x", model=GEMINI).close()
    gw, gseen = wire("gpt")
    mw, mseen = wire("gemini")
    gpt = ConstructionSession(tmp_path / "gpt_g")
    gpt.arm_construction_mock("v2", V2_SPLIT, gw, Decimal("1.00"), purpose="v2_stage3",
                              approval=approval("v2_stage3", MODEL))  # fmt: skip
    gem = ConstructionSession(tmp_path / "gemini")
    gem.arm_construction_mock("v2", V2_SPLIT, mw, Decimal("1.00"), purpose="v2_backbone_gemini",
                              approval=approval("v2_backbone_gemini", GEMINI))  # fmt: skip
    yield gpt, gem, gseen, mseen
    gpt.close()
    gem.close()


def test_gemini_answers_go_to_gemini_judges_stay_on_gpt(gemini_sessions):
    gpt, gem, gseen, mseen = gemini_sessions
    router = BackboneRouter(gpt, gem, model=GEMINI)
    _, ans = router.dispatch("answer", answer_request())
    assert ans["response"]["text"] == "reply from gemini"
    _, jud = router.dispatch("judge_answer", judge_request())
    assert jud["response"]["text"] == "reply from gpt" and gseen[-1]["model"] == MODEL
    router.dispatch("no_memory_answer", answer_request())  # identical request: reused
    assert len(mseen) == 1 and len(gseen) == 1
    assert router.counts == {"gemini_answers": 2, "gpt_calls": 1}


def test_gemini_answer_settings_match_gpt_temperature_zero_reasoning_off(gemini_sessions):
    gpt, gem, gseen, mseen = gemini_sessions
    router = BackboneRouter(gpt, gem, model=GEMINI)
    router.dispatch("answer", answer_request())
    router.dispatch("judge_answer", judge_request())
    sent = mseen[-1]
    assert sent["model"] == GEMINI and sent["temperature"] == 0 and sent["max_tokens"] == 200
    assert sent["reasoning"] == {"enabled": False}
    assert sent["messages"] == [{"role": "user", "content": answer_request().messages[0].content}]
    assert sent["provider"]["max_price"] == {"prompt": 0.25, "completion": 1.5, "request": 0}
    assert sent["provider"]["require_parameters"] is True
    assert sent["provider"]["allow_fallbacks"] is False
    assert "reasoning" not in gseen[-1] and gseen[-1]["temperature"] == 0  # GPT unchanged
    stored = json.loads(gem.db.execute("SELECT request FROM dispatches").fetchone()[0])
    assert stored["temperature"] == 0 and stored["reasoning_effort"] == "none"


def test_gemini_scope_refuses_every_other_shape(gemini_sessions):
    gpt, gem, _, mseen = gemini_sessions
    body = answer_request().messages
    for bad in (ChatRequest(body, GEMINI, temperature=None, max_tokens=200,
                            reasoning_effort="none"),  # Haiku's no-temperature shape
                ChatRequest(body, GEMINI, temperature=0.0, max_tokens=200),  # reasoning left on
                ChatRequest(body, GEMINI, temperature=0.0, max_tokens=300,
                            reasoning_effort="none"),
                ChatRequest(judge_request().messages, GEMINI, temperature=0.0, max_tokens=120,
                            reasoning_effort="none")):  # fmt: skip
        with pytest.raises(ValueError):
            gem.dispatch_v2(bad)
    with pytest.raises(LedgerError):
        gem.dispatch("judge_answer", judge_request())  # not an evaluation scope
    assert mseen == []


def test_router_never_mixes_backbone_scopes(gemini_sessions, sessions):
    gpt, gem, _, _ = gemini_sessions
    _, haiku, _, _ = sessions
    with pytest.raises(LedgerError):
        BackboneRouter(gpt, haiku, model=GEMINI)  # Gemini on the Haiku scope
    with pytest.raises(LedgerError):
        BackboneRouter(gpt, gem)  # Haiku (default) on the Gemini scope
    with pytest.raises(LedgerError):
        BackboneRouter(gpt, gem, model="openai/gpt-4o")  # not a registered backbone


def test_haiku_settings_unchanged_by_the_gemini_addition(sessions):
    gpt, haiku, _, hseen = sessions
    BackboneRouter(gpt, haiku).dispatch("answer", answer_request())
    assert "temperature" not in hseen[-1] and hseen[-1]["reasoning"] == {"enabled": False}
    assert hseen[-1]["model"] == HAIKU and hseen[-1]["max_tokens"] == 200


class FakeClock:
    def __init__(self):
        self.now, self.sleeps = 1000.0, []

    def monotonic(self):
        return self.now

    def sleep(self, s):
        self.sleeps.append(round(s, 6))
        self.now += s


def test_gemini_calls_are_paced_and_replays_are_not(gemini_sessions, monkeypatch):
    """Revision 11: at least PACE_S seconds between two Gemini network calls (provider rate
    limit); GPT-4o-mini calls and replays of already-paid answers are never slowed."""
    import ams.research.workload.transport as T

    clock = FakeClock()
    monkeypatch.setattr(T, "time", clock)
    assert T.PACE_S == {"v2_backbone_gemini": 2.0}
    gpt, gem, gseen, mseen = gemini_sessions
    router = BackboneRouter(gpt, gem, model=GEMINI)
    router.dispatch("answer", answer_request())
    router.dispatch("judge_answer", judge_request())
    assert clock.sleeps == []  # first Gemini call and the GPT judge: no wait
    clock.now += 0.5
    other = ChatRequest((Message("user", "Question: when?\nWhat you remember:\n- Monday\n"
                                 "Answer:"),), MODEL, temperature=0.0, max_tokens=200)  # fmt: skip
    router.dispatch("answer", other)
    assert clock.sleeps == [1.5]  # waited out the rest of the 2 s gap
    router.dispatch("answer", answer_request())  # replay: no network, no wait
    assert clock.sleeps == [1.5] and len(mseen) == 2
