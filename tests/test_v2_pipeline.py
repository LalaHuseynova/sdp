"""Protocol v2, plan.md step 1.8: the paid-run pipeline, built and tested OFFLINE only.

Mock LLMs and httpx.MockTransport only; no request can reach a real endpoint.
"""

from __future__ import annotations

import json
import socket
import sqlite3
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal

import httpx
import pytest

from ams.llm.types import ChatRequest, Message
from ams.research.dynamic.models import LedgerError
from ams.research.execution.session import MODEL, ExecutionSession
from ams.research.protocol_v2 import pipeline as PL
from ams.research.workload import adaptive as AD
from ams.research.workload.generator import build
from ams.research.workload.integration import LayeredClient, build_states, group_rows
from ams.research.workload.mock import MockSession, PromptAwareMock
from ams.research.workload.runner import run
from ams.research.workload.stage2 import ConflictPlaceholderSession
from ams.research.workload.transport import V2_SPLIT, ConstructionSession
from test_controlled_workload import sources

CONDITIONS = ("localized", "imp_localized_late_d0", "imp_localized_fp1_d0")


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    real = socket.socket.connect

    def deny(self, address, *args, **kwargs):
        if isinstance(address, str):  # local unix sockets only
            return real(self, address, *args, **kwargs)
        raise AssertionError("Pipeline tests forbid networking")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: deny(None, ("x", 0)))


@pytest.fixture(scope="module")
def world():
    rows, _ = build(sources(), dev_groups=1, test_groups=1)
    gid = sorted({r["group_id"] for r in rows["public/contributions.jsonl"]})[0]
    mock = PromptAwareMock()
    store = build_states(
        rows, gid, LayeredClient(None, "openrouter", mock), LayeredClient(None, "local", mock)
    )
    ext = AD.extend_store(rows, store, [c for c in CONDITIONS if c != "localized"])
    return rows, group_rows(rows, gid), ext, mock


@dataclass
class Result:
    kept: list
    flagged: list
    reason: str = "fake"


class KeepAll:
    def filter(self, question, mems):
        return Result(list(mems), [])


class DropFirst:
    def filter(self, question, mems):
        return Result(list(mems)[1:], list(mems)[:1])


def sensitive(question):
    return "remember" in question.lower()


def fakes():
    return {"a_memguard": KeepAll(), "llm_sanitiser": DropFirst(), "randec": KeepAll(),
            "memlineage": PL.memlineage(sensitive)}  # fmt: skip


def journal(path):
    with sqlite3.connect(path / "queries.sqlite") as db:
        return [json.loads(b) for (b,) in db.execute("SELECT body FROM outcomes ORDER BY rowid")]


def test_method_lists_follow_the_protocol():
    assert PL.MAIN_METHODS == ("static", "R", "C", "M", "a_memguard", "memlineage",
                               "llm_sanitiser", "randec", "S", "SL", "S2-ID")  # fmt: skip
    assert PL.APPENDIX_METHODS == ("S2-BS", "a_memguard+R", "memlineage+R",
                                   "llm_sanitiser+R", "randec+R")  # fmt: skip
    assert PL.required_purposes(["S", "randec"]) == {"v2_stage3"}
    assert PL.required_purposes(["S2-ID", "a_memguard+R", "llm_sanitiser"]) == {
        "v2_stage3", "v2_published_memlineage", "v2_published_amemguard",
        "v2_published_sanitiser"}  # fmt: skip
    assert PL.required_purposes(["S"], backbone="haiku") == {"v2_stage3", "v2_backbone_answer"}
    # Revision 10 (post-hoc third backbone): Gemini has its own purpose, never Haiku's.
    assert PL.required_purposes(["S"], backbone="gemini") == {"v2_stage3", "v2_backbone_gemini"}


def test_internal_methods_reproduce_the_runner_exactly(world, tmp_path):
    rows, group, ext, mock = world
    arms = ("static", "R", "C", "M", "S", "SL")
    run(rows, [ext], MockSession(mock), tmp_path / "runner", split="dev", conditions=CONDITIONS,
        arms=arms, no_memory=False, lineage_tau=0.8)  # fmt: skip
    PL.evaluate(rows, [ext], MockSession(mock), tmp_path / "pipe", conditions=CONDITIONS,
                methods=arms)  # fmt: skip
    keep = ("answer", "outcome", "exposure", "audit_tickets", "stratum")
    ref = {(r["condition"], r["arm"], r["probe_id"]): {k: r[k] for k in keep}
           for r in journal(tmp_path / "runner")}  # fmt: skip
    got = {(r["condition"], r["method"], r["probe_id"]): {k: r[k] for k in keep}
           for r in journal(tmp_path / "pipe")}  # fmt: skip
    assert got == ref and len(got) == len(CONDITIONS) * len(arms) * len(group["probes"])


def test_every_method_end_to_end_with_mocks(world, tmp_path):
    rows, group, ext, mock = world
    methods = PL.MAIN_METHODS + PL.APPENDIX_METHODS
    PL.evaluate(rows, [ext], MockSession(mock), tmp_path, conditions=CONDITIONS,
                methods=methods, defences=fakes(), sensitive=sensitive)  # fmt: skip
    out = journal(tmp_path)
    assert len(out) == len(CONDITIONS) * len(methods) * len(group["probes"])
    by = {(r["condition"], r["method"], r["probe_id"]): r for r in out}
    for (cond, method, pid), r in by.items():
        assert r["answer"] is not None and r["outcome"] in (True, False)
        if method == "a_memguard":  # keeps everything -> exactly the static prompt
            assert r["prompt_hash"] == by[(cond, "static", pid)]["prompt_hash"]
        if method == "llm_sanitiser" and by[(cond, "static", pid)]["context_size"]:
            assert r["context_size"] == by[(cond, "static", pid)]["context_size"] - 1
    late = [r for r in out if r["condition"] == "imp_localized_late_d0" and r["method"] == "S"]
    assert Counter(r["audits_revealed"] for r in late) == {
        False: len(group["probes"]) // 2, True: len(group["probes"]) - len(group["probes"]) // 2}


def test_precompute_is_free_and_predicts_the_paid_prompts(world, tmp_path):
    rows, _, ext, mock = world
    methods = ("static", "R", "S", "SL", "S2-BS", "randec", "randec+R")
    PL.evaluate(rows, [ext], ConflictPlaceholderSession(), tmp_path / "pre",
                conditions=CONDITIONS, methods=methods, defences=fakes(), answer=False)  # fmt: skip
    PL.evaluate(rows, [ext], MockSession(mock), tmp_path / "paid", conditions=CONDITIONS,
                methods=methods, defences=fakes())  # fmt: skip
    pre, paid = journal(tmp_path / "pre"), journal(tmp_path / "paid")
    assert all(r["answer"] is None and r["outcome"] is None for r in pre)
    key = lambda r: (r["condition"], r["method"], r["probe_id"])  # noqa: E731
    assert {key(r): (r["prompt_hash"], r["exposure"]) for r in pre} == {
        key(r): (r["prompt_hash"], r["exposure"]) for r in paid}
    assert PL.distinct_prompts(pre) < len(pre)  # identical prompts are sent once


def test_resume_replays_exactly(world, tmp_path):
    rows, _, ext, mock = world
    kw = dict(conditions=CONDITIONS[:1], methods=("S", "randec"), defences=fakes())
    first = PL.evaluate(rows, [ext], MockSession(mock), tmp_path, **kw)
    again = PL.evaluate(rows, [ext], MockSession(mock), tmp_path, **kw)  # restart
    assert first == again
    with pytest.raises(LedgerError, match="another experiment journal"):
        PL.evaluate(rows, [ext], MockSession(mock), tmp_path, conditions=CONDITIONS[:1],
                    methods=("C",))  # fmt: skip


def test_paid_stage_is_a_single_writer(tmp_path):
    transport, _ = wire(PromptAwareMock())
    args = (tmp_path / "sessions", "v2", approval(["v2_stage3"]), ["v2_stage3"])
    with PL.open_paid(*args, transport=transport, confirmed=True):
        with pytest.raises(LedgerError, match="Another dispatcher"):  # the session's own lock
            with PL.open_paid(*args, transport=transport, confirmed=True):
                pass
    with PL.open_paid(*args, transport=transport, confirmed=True):  # released on exit
        pass


# ----------------------------------------------------------------- guarded paid path (mocked)


def approval(purposes, cap="0.50"):
    return {"approved_by": "owner", "protocol_v2_digest": "f" * 64,
            "caps_usd": {p: cap for p in purposes},
            "models": {p: MODEL for p in purposes}}  # fmt: skip


def wire(mock):
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        req = ChatRequest(tuple(Message(m["role"], m["content"]) for m in body["messages"]),
                          body["model"], temperature=body.get("temperature", 0.0),
                          max_tokens=body.get("max_tokens")
                          or body.get("max_completion_tokens"))  # fmt: skip
        prompt = req.messages[-1].content
        if "Classify the request as SENSITIVE or ORDINARY." in prompt:  # SensitiveAction
            text = "SENSITIVE" if "remember" in prompt.lower() else "ORDINARY"
        else:
            text = mock.complete(req).text
        return httpx.Response(200, json={
            "id": "gen-offline", "model": body["model"], "object": "chat.completion",
            "created": 1, "choices": [{"index": 0, "finish_reason": "stop",
                                       "message": {"role": "assistant", "content": text}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11,
                      "cost": "0.00001"}})  # fmt: skip (<= every request's max_tokens)

    return httpx.MockTransport(handler), seen


def test_paid_stages_need_an_owner_approval_each(tmp_path):
    transport, seen = wire(PromptAwareMock())
    cases = [("confirm", approval(["v2_stage3"]), ["v2_stage3"], False),
             ("does not cover", approval(["v2_stage3"]), ["v2_stage3", "v2_published_amemguard"],
              True),
             ("owner-approval", None, ["v2_stage3"], True)]  # fmt: skip
    for match, appr, purposes, confirmed in cases:
        with pytest.raises(LedgerError, match=match):
            with PL.open_paid(tmp_path / "s", "v2", appr, purposes, transport=transport,
                              confirmed=confirmed):  # fmt: skip
                pass
    assert seen == [] and not (tmp_path / "s").exists()  # nothing opened, nothing sent


def test_guarded_end_to_end_sends_each_request_once_and_resumes_free(world, tmp_path):
    rows, group, ext, mock = world
    transport, seen = wire(mock)
    purposes = ["v2_stage3", "v2_published_memlineage"]
    kw = dict(conditions=CONDITIONS[:2], methods=("S", "S2-ID", "memlineage"))
    for attempt in range(2):
        with PL.open_paid(tmp_path / "s", "v2", approval(purposes), purposes,
                          transport=transport, confirmed=True) as paid:  # fmt: skip
            PL.evaluate(rows, [ext], paid.stage3, tmp_path / "out", **kw,
                        defences={"memlineage": PL.memlineage(paid.sensitive)},
                        sensitive=paid.sensitive)  # fmt: skip
            spend = paid.spend()
        if attempt == 0:
            sent = len(seen)
            keys = {json.dumps(b, sort_keys=True) for b in seen}
            assert sent == len(keys) > 0  # identical requests went to the wire once
            assert Decimal(spend["v2_stage3"]) >= 0
    assert len(seen) == sent  # the restart was served entirely from the guarded ledger
    stages = Counter(b["max_tokens"] for b in seen)
    assert set(stages) <= {200, 6, 120, 4}  # answers, conflicts, judges, SensitiveAction
    assert len(journal(tmp_path / "out")) == 2 * 3 * len(group["probes"])


def test_v2_published_scopes_accept_only_their_exact_shape(tmp_path):
    ExecutionSession.create(tmp_path / "s", plan_hash="x").close()
    transport, seen = wire(PromptAwareMock())
    with ConstructionSession(tmp_path / "s") as s:
        s.arm_construction_mock("v2", V2_SPLIT, transport, Decimal("0.10"),
                                purpose="v2_published_memlineage",
                                approval=approval(["v2_published_memlineage"]))  # fmt: skip
        bad = ChatRequest((Message("user", "What you remember: x"),), MODEL, temperature=0.0,
                          max_tokens=200)  # an answer request is not this stage's shape
        with pytest.raises(ValueError):
            s.dispatch_v2(bad)
    assert seen == []


def test_cli_refuses_paid_runs_before_loading_anything(tmp_path):
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts/run_protocol_v2.py"
    spec = importlib.util.spec_from_file_location("run_protocol_v2", path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    missing = ["--bundle", str(tmp_path / "none"), "--stage1", str(tmp_path / "none"),
               "--out", str(tmp_path / "out")]  # fmt: skip
    paid = ["paid", *missing, "--sessions", str(tmp_path / "s"), "--approval",
            str(tmp_path / "a.json"), "--freeze", str(tmp_path / "f.json")]  # fmt: skip
    with pytest.raises(LedgerError, match="confirm-paid"):
        cli.main(paid)
    with pytest.raises(LedgerError, match="no paid call"):
        cli.main(["precompute", *missing, "--methods", "a_memguard"])
    # Claude Haiku answers are run on the original path (the stored-context path checks the
    # replayed answer model, which the backbone router changes): refused, never mixed.
    with pytest.raises(LedgerError, match="Haiku"):
        cli.main([*paid, "--confirm-paid", "--backbone", "haiku", "--contexts",
                  str(tmp_path / "ctx")])  # fmt: skip
    with pytest.raises(LedgerError, match="Gemini"):  # revision 10: the same rule for Gemini
        cli.main([*paid, "--confirm-paid", "--backbone", "gemini", "--contexts",
                  str(tmp_path / "ctx")])  # fmt: skip
    # Step 2.2: a paid stage needs a valid freeze manifest named by the owner's approval.
    (tmp_path / "a.json").write_text(json.dumps({"approved_by": "owner",
                                                 "protocol_v2_digest": "0" * 64}))
    (tmp_path / "f.json").write_text(json.dumps({"protocol": {}, "hashes": {},
                                                 "protocol_v2_digest": "1" * 64}))
    with pytest.raises(LedgerError, match="edited after"):
        cli.main([*paid, "--confirm-paid"])
    with pytest.raises(SystemExit):  # --freeze is required
        cli.main([x for x in paid if x not in ("--freeze", str(tmp_path / "f.json"))]
                 + ["--confirm-paid"])  # fmt: skip
    assert not (tmp_path / "s").exists() and not (tmp_path / "out").exists()


def test_approved_cap_above_the_code_ceiling_is_rejected(tmp_path):
    transport, seen = wire(PromptAwareMock())
    too_high = approval(["v2_stage3", "v2_published_memlineage"])
    too_high["caps_usd"]["v2_published_memlineage"] = "0.51"  # code ceiling is $0.50
    with pytest.raises(LedgerError, match="exceeds the code ceiling"):
        with PL.open_paid(tmp_path / "s", "v2", too_high,
                          ["v2_stage3", "v2_published_memlineage"], transport=transport,
                          confirmed=True):  # fmt: skip
            pass
    assert seen == [] and not (tmp_path / "s").exists()  # nothing lowered, opened or sent
    both = ["v2_stage3", "v2_published_memlineage"]  # every run needs v2_stage3
    at_ceiling = approval(both)  # exactly $0.50 is allowed
    with PL.open_paid(tmp_path / "s", "v2", at_ceiling, both, transport=transport,
                      confirmed=True) as paid:  # fmt: skip
        assert paid.sessions["v2_published_memlineage"].cap == Decimal("0.50")


def test_randec_cache_leaves_every_row_identical(world, tmp_path):
    """Runtime fix 1 (step 1.12): the cached RandEC gives byte-identical journals, free
    and paid (mock), for every method, including those evaluated after RandEC."""
    from ams.research.protocol_v2.randec_cache import cached_randec
    from test_v2_randec_cache import FakeRandEC

    rows, _, ext, mock = world
    methods = ("static", "randec", "R", "randec+R", "S", "a_memguard", "SL")

    def run_with(randec, out, session):
        PL.evaluate(rows, [ext], session, out, conditions=CONDITIONS, methods=methods,
                    defences={**fakes(), "randec": randec}, answer=False)  # fmt: skip
        PL.evaluate(rows, [ext], MockSession(mock), out.with_name(out.name + "_paid"),
                    conditions=CONDITIONS, methods=methods,
                    defences={**fakes(), "randec": randec})  # fmt: skip
        return journal(out), journal(out.with_name(out.name + "_paid"))

    plain_fake, fake = FakeRandEC(), FakeRandEC()
    plain = run_with(plain_fake, tmp_path / "plain", ConflictPlaceholderSession())
    cached = run_with(cached_randec(fake), tmp_path / "cached", ConflictPlaceholderSession())
    assert cached == plain  # every field of every row, free and paid
    assert any(r["flagged"] for r in plain[0] if r["method"].startswith("randec"))  # it acts
    assert 0 < fake.calls < plain_fake.calls  # and the cache did avoid repeated model runs


def test_guarded_haiku_run_after_the_gpt_run_reuses_every_gpt_call(world, tmp_path):
    """Stage P-B3 readiness (step 2.3): the second-backbone run through real guarded sessions
    and the original pipeline path, after the GPT run on the same sessions. Answers go to
    Claude Haiku; judges stay on GPT-4o-mini; every GPT request the GPT run already sent
    (conflict checks, MemLineage) is replayed from the ledger, never re-sent."""
    from ams.research.protocol_v2.backbone import HAIKU

    rows, group, ext, mock = world
    transport, seen = wire(mock)
    gpt = ["v2_stage3", "v2_published_memlineage"]
    both = [*gpt, "v2_backbone_answer"]
    appr = approval(both)
    appr["models"]["v2_backbone_answer"] = HAIKU
    kw = dict(conditions=CONDITIONS[:2], methods=("S", "memlineage"))
    for purposes, out in ((gpt, "gpt"), (both, "haiku")):
        with PL.open_paid(tmp_path / "s", "v2", appr, purposes, transport=transport,
                          confirmed=True) as paid:  # fmt: skip
            PL.evaluate(rows, [ext], paid.stage3, tmp_path / out, **kw,
                        defences={"memlineage": PL.memlineage(paid.sensitive)},
                        sensitive=paid.sensitive)  # fmt: skip
        if out == "gpt":
            n_gpt = len(seen)
    new = seen[n_gpt:]
    answers = [b for b in new if b["max_tokens"] == 200]
    assert answers and all(b["model"] == HAIKU for b in answers)
    assert all(b["model"] == MODEL for b in new if b["max_tokens"] != 200)  # judges
    assert not [b for b in new if b["max_tokens"] in (6, 4)]  # conflicts, MemLineage replayed
    haiku = journal(tmp_path / "haiku")
    assert len(haiku) == 2 * 2 * len(group["probes"])
    assert all(r["outcome"] is not None for r in haiku)  # every Haiku answer was judged


def test_guarded_gemini_run_after_the_gpt_run_reuses_every_gpt_call(world, tmp_path):
    """Revision 10 (post-hoc third backbone): the Gemini run goes through the same guarded
    sessions and original pipeline path as the Haiku run. Answers go to Gemini 3.1 Flash-Lite
    with GPT-4o-mini's temperature 0 and reasoning disabled; judges stay on GPT-4o-mini; every
    GPT request the GPT run already sent (conflict checks, MemLineage) is replayed, not re-sent."""
    from ams.research.protocol_v2.backbone import GEMINI

    rows, group, ext, mock = world
    transport, seen = wire(mock)
    gpt = ["v2_stage3", "v2_published_memlineage"]
    both = [*gpt, "v2_backbone_gemini"]
    appr = approval(both)
    appr["models"]["v2_backbone_gemini"] = GEMINI
    kw = dict(conditions=CONDITIONS[:2], methods=("S", "memlineage"))
    for purposes, out in ((gpt, "gpt"), (both, "gemini")):
        with PL.open_paid(tmp_path / "s", "v2", appr, purposes, transport=transport,
                          confirmed=True) as paid:  # fmt: skip
            PL.evaluate(rows, [ext], paid.stage3, tmp_path / out, **kw,
                        defences={"memlineage": PL.memlineage(paid.sensitive)},
                        sensitive=paid.sensitive)  # fmt: skip
        if out == "gpt":
            n_gpt = len(seen)
    new = seen[n_gpt:]
    answers = [b for b in new if b["max_tokens"] == 200]
    assert answers and all(b["model"] == GEMINI for b in answers)
    assert all(b["temperature"] == 0 and b["reasoning"] == {"enabled": False} for b in answers)
    assert all(b["model"] == MODEL for b in new if b["max_tokens"] != 200)  # judges
    assert not [b for b in new if b["max_tokens"] in (6, 4)]  # conflicts, MemLineage replayed
    gem = journal(tmp_path / "gemini")
    assert len(gem) == 2 * 2 * len(group["probes"])
    assert all(r["outcome"] is not None for r in gem)  # every Gemini answer was judged
    gpt_rows = journal(tmp_path / "gpt")  # same probes, conditions and methods as the GPT run
    assert sorted((r["condition"], r["method"], r["probe_id"]) for r in gem) == sorted(
        (r["condition"], r["method"], r["probe_id"]) for r in gpt_rows)


def test_one_run_never_opens_two_answer_backbones(tmp_path):
    from ams.research.protocol_v2.backbone import GEMINI, HAIKU

    transport, seen = wire(PromptAwareMock())
    purposes = ["v2_stage3", "v2_backbone_answer", "v2_backbone_gemini"]
    appr = approval(purposes)
    appr["models"].update({"v2_backbone_answer": HAIKU, "v2_backbone_gemini": GEMINI})
    with pytest.raises(LedgerError, match="one answer backbone"):
        with PL.open_paid(tmp_path / "s", "v2", appr, purposes, transport=transport,
                          confirmed=True):  # fmt: skip
            pass
    assert seen == [] and not (tmp_path / "s").exists()
