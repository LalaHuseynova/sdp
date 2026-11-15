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
