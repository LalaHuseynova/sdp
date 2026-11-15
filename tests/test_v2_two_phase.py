# ruff: noqa: F811  (pytest fixtures imported from test_v2_pipeline)
"""plan.md step 1.12, runtime fix 2 (owner-approved three-step version). Offline only.

The paid stage must give EXACTLY the rows of the original single-process pipeline
(`pipeline.evaluate(answer=True)`), while reading the contexts of the internal methods
from a free precompute instead of recomputing retrieval:

  1. free  : the placeholder precompute records every distinct conflict-check request
             (they do not depend on the replies: selection never does);
     paid  : those requests only are sent through the guarded v2_stage3 session;
  2. free  : the precompute is rerun replaying the REAL conflict replies, so contested
             marks, retrieved contexts and rendered prompts are the paid ones;
  3. paid  : answers, judges and published defences read those verified contexts.

The mock below answers "contradict" to about half of the conflict checks, so contested
labels really occur (with the old "compatible"-only mock this test would prove nothing).
"""

from __future__ import annotations

import json
import sqlite3
import zlib
from collections import Counter
from dataclasses import replace
from decimal import Decimal

import pytest

from ams.llm.types import ChatRequest, Message
from ams.research.dynamic.models import LedgerError
from ams.research.protocol_v2 import pipeline as PL
from ams.research.protocol_v2 import two_phase as TP
from ams.research.workload.mock import MockSession, PromptAwareMock
from ams.research.workload.stage2 import ConflictPlaceholderSession
from test_v2_pipeline import (  # noqa: F401 - fixtures
    CONDITIONS,
    approval,
    fakes,
    journal,
    offline,
    sensitive,
    wire,
    world,
)

METHODS = PL.MAIN_METHODS + PL.APPENDIX_METHODS
CONFLICT = "Answer with one word and nothing else."


class ContradictingMock(PromptAwareMock):
    """PromptAwareMock, but a deterministic half of the conflict checks contradict."""

    def complete(self, request):
        response = super().complete(request)
        body = request.messages[-1].content
        if CONFLICT in body and zlib.crc32(body.encode()) % 2 == 0:
            return replace(response, text="contradict")
        return response


class Contradicting(ConflictPlaceholderSession):
    """Placeholder that records requests but replies "contradict" to every check."""

    def __init__(self):
        super().__init__()
        self.keys = Counter()

    def dispatch(self, stage, request):
        call_id, result = super().dispatch(stage, request)
        self.keys[request.cache_key("openrouter")] += 1
        result["response"]["text"] = "contradict"
        return call_id, result


def three_steps(rows, ext, tmp_path, step1_session, step3_session, *, methods=METHODS,
                conditions=CONDITIONS, defences=None, sens=sensitive):  # fmt: skip
    rec = TP.ConflictRecorder()
    PL.evaluate(rows, [ext], rec, tmp_path / "pre", conditions=conditions,
                methods=TP.context_methods(methods), answer=False)  # fmt: skip
    TP.save_requests(tmp_path / "pre" / TP.REQUESTS, rec)
    requests = TP.load_requests([tmp_path / "pre" / TP.REQUESTS])
    replies = TP.send_conflicts(requests, step1_session)
    TP.save_replies(tmp_path / TP.REPLIES, replies)
    TP.build_contexts(rows, [ext], TP.load_replies(tmp_path / TP.REPLIES), tmp_path / "ctx",
                      conditions=conditions, methods=TP.context_methods(methods),
                      inputs={"bundle": "test"})  # fmt: skip
    ctx = TP.Contexts([tmp_path / "ctx"], inputs={"bundle": "test"})
    PL.evaluate(rows, [ext], step3_session, tmp_path / "three", conditions=conditions,
                methods=methods, defences=defences or fakes(), sensitive=sens,
                contexts=ctx)  # fmt: skip
    return journal(tmp_path / "three"), replies


def test_conflict_requests_do_not_depend_on_the_replies(world, tmp_path):
    rows, _, ext, _ = world
    rec, contra = TP.ConflictRecorder(), Contradicting()
    for name, session in (("a", rec), ("b", contra)):
        PL.evaluate(rows, [ext], session, tmp_path / name, conditions=CONDITIONS,
                    methods=TP.CONTEXT_METHODS, answer=False)  # fmt: skip
    assert set(rec.requests) == set(contra.keys) and len(rec.requests) > 0
    assert rec.conflicts == contra.conflicts  # the same checks, in the same number


def test_real_conflict_replies_do_change_prompts_in_this_fixture(world, tmp_path):
    """Why Fix 2 needs step 2: the placeholder precompute misses contested marks."""
    rows, _, ext, _ = world
    PL.evaluate(rows, [ext], ConflictPlaceholderSession(), tmp_path / "pre",
                conditions=CONDITIONS, methods=("static", "S"), answer=False)  # fmt: skip
    PL.evaluate(rows, [ext], MockSession(ContradictingMock()), tmp_path / "paid",
                conditions=CONDITIONS, methods=("static", "S"))  # fmt: skip
    key = lambda r: (r["condition"], r["method"], r["probe_id"])  # noqa: E731
    pre = {key(r): r["prompt_hash"] for r in journal(tmp_path / "pre")}
    paid = {key(r): r["prompt_hash"] for r in journal(tmp_path / "paid")}
    assert pre.keys() == paid.keys() and pre != paid


def test_three_steps_reproduce_the_paid_journal_exactly(world, tmp_path):
    rows, group, ext, _ = world
    mock = ContradictingMock()
    original = MockSession(mock)
    PL.evaluate(rows, [ext], original, tmp_path / "orig", conditions=CONDITIONS,
                methods=METHODS, defences=fakes(), sensitive=sensitive)  # fmt: skip
    step1, step3 = MockSession(mock), MockSession(mock)
    got, replies = three_steps(rows, ext, tmp_path, step1, step3)
    ref = journal(tmp_path / "orig")
    # every row identical: exposure, contexts sizes, prompt hashes, kept/flagged, answers,
    # outcomes, judges, finish reasons, audit tickets AND the model-call ids (conflicts)
    assert got == ref
    assert len(got) == len(CONDITIONS) * len(METHODS) * len(group["probes"])
    assert any("contradict" in r["response"]["text"] for r in replies)
    assert any(len(r["model_call_ids"]) > 1 for r in got)  # conflicts ran in those probes
    ctx = TP.Contexts([tmp_path / "ctx"], inputs={"bundle": "test"})
    assert ctx.contested_prompts() > 0  # contested labels reached rendered prompts
    # the same distinct requests were dispatched overall (each paid once in a guarded run)
    sent = lambda *ss: {(d["stage"], d["call_id"]) for s in ss for d in s.dispatches}  # noqa: E731
    assert sent(step1, step3) == sent(original)


def test_guarded_three_steps_match_and_send_each_request_once(world, tmp_path):
    rows, group, ext, _ = world
    mock = ContradictingMock()
    purposes = ["v2_stage3", "v2_published_memlineage"]
    methods = ("static", "R", "S", "SL", "memlineage", "memlineage+R", "S2-ID")
    conds = CONDITIONS[:2]
    results = {}
    for name in ("orig", "three"):
        transport, seen = wire(mock)
        root = tmp_path / name
        root.mkdir()
        open_ = lambda root=root, transport=transport: PL.open_paid(  # noqa: E731
            root / "s", "v2", approval(purposes), purposes, transport=transport, confirmed=True)
        if name == "orig":
            with open_() as paid:
                PL.evaluate(rows, [ext], paid.stage3, root / "three", conditions=conds,
                            methods=methods, sensitive=paid.sensitive,
                            defences={"memlineage": PL.memlineage(paid.sensitive)})  # fmt: skip
                spend = paid.spend()
        else:
            rec = TP.ConflictRecorder()
            PL.evaluate(rows, [ext], rec, root / "pre", conditions=conds,
                        methods=TP.context_methods(methods), answer=False)  # fmt: skip
            with open_() as paid:  # step 1 (paid): conflict checks only
                replies = TP.send_conflicts(list(rec.requests.values()), paid.stage3)
            assert all(b["max_tokens"] == 6 and CONFLICT in b["messages"][-1]["content"]
                       for b in seen)  # fmt: skip  (nothing but conflict checks)
            TP.build_contexts(rows, [ext], replies, root / "ctx", conditions=conds,
                              methods=TP.context_methods(methods),
                              inputs={"bundle": "v2"})  # fmt: skip
            with open_() as paid:  # step 3 (paid)
                PL.evaluate(rows, [ext], paid.stage3, root / "three", conditions=conds,
                            methods=methods, sensitive=paid.sensitive,
                            defences={"memlineage": PL.memlineage(paid.sensitive)},
                            contexts=TP.Contexts([root / "ctx"], inputs={"bundle": "v2"}))
                spend = paid.spend()
        bodies = [json.dumps(b, sort_keys=True) for b in seen]
        assert len(bodies) == len(set(bodies)) > 0  # each distinct request sent once
        results[name] = (journal(root / "three"), set(bodies), spend)
    (j1, b1, s1), (j2, b2, s2) = results["orig"], results["three"]
    assert j2 == j1 and len(j1) == len(conds) * len(methods) * len(group["probes"])
    assert b2 == b1  # exactly the same paid requests, no more, no fewer
    assert s2 == s1  # hence the same spend per purpose


def test_step_two_replays_only_known_conflict_replies(world, tmp_path):
    rows, _, ext, _ = world
    rec = TP.ConflictRecorder()
    PL.evaluate(rows, [ext], rec, tmp_path / "pre", conditions=CONDITIONS[:1],
                methods=("static",), answer=False)  # fmt: skip
    replies = TP.send_conflicts(list(rec.requests.values()), MockSession(ContradictingMock()))
    session = TP.ReplayConflictSession(replies)
    answer = ChatRequest((Message("user", "What you remember:\nRequest: x"),), "m",
                         max_tokens=200)  # fmt: skip
    with pytest.raises(LedgerError, match="only conflict"):
        session.dispatch("answer", answer)
    unknown = ChatRequest((Message("user", f"unseen pair. {CONFLICT}"),), "m", max_tokens=6)
    with pytest.raises(LedgerError, match="step 1"):
        session.dispatch("conflict", unknown)
    with pytest.raises(LedgerError, match="step 1"):  # a missing reply fails step 2 closed
        TP.build_contexts(rows, [ext], replies[:-1], tmp_path / "ctx",
                          conditions=CONDITIONS[:1], methods=("static",),
                          inputs={"bundle": "test"})  # fmt: skip


def _built(world, tmp_path, mock=None):
    rows, _, ext, _ = world
    rec = TP.ConflictRecorder()
    PL.evaluate(rows, [ext], rec, tmp_path / "pre", conditions=CONDITIONS[:1],
                methods=TP.CONTEXT_METHODS, answer=False)  # fmt: skip
    replies = TP.send_conflicts(list(rec.requests.values()),
                                MockSession(mock or ContradictingMock()))  # fmt: skip
    TP.build_contexts(rows, [ext], replies, tmp_path / "ctx", conditions=CONDITIONS[:1],
                      inputs={"bundle": "test"})  # fmt: skip
    return rows, ext


def test_step_three_validates_the_precompute(world, tmp_path):
    rows, ext = _built(world, tmp_path)
    run = lambda ctx, session=None, **kw: PL.evaluate(  # noqa: E731
        rows, [ext], session or MockSession(ContradictingMock()), tmp_path / "out",
        methods=kw.pop("methods", ("static", "S")), defences=fakes(), contexts=ctx,
        **{"conditions": CONDITIONS[:1], **kw})  # fmt: skip
    with pytest.raises(LedgerError, match="inputs"):  # another bundle / Stage 1
        TP.Contexts([tmp_path / "ctx"], inputs={"bundle": "other"})
    ctx = TP.Contexts([tmp_path / "ctx"], inputs={"bundle": "test"})
    with pytest.raises(LedgerError, match="conditions"):  # other conditions than built
        run(ctx, conditions=CONDITIONS[:2])
    with pytest.raises(LedgerError, match="conflict reply"):  # the live ledger disagrees
        run(ctx, session=MockSession(PromptAwareMock()))
    assert not (tmp_path / "out").exists()  # refused before anything was written
    db = sqlite3.connect(tmp_path / "ctx" / TP.CONTEXTS)  # tamper with one stored prompt
    h, body = db.execute("SELECT hash, body FROM blobs LIMIT 1").fetchone()
    db.execute("UPDATE blobs SET body=? WHERE hash=?", (body + " ", h))
    db.commit()
    db.close()
    with pytest.raises(LedgerError, match="hash"):
        run(TP.Contexts([tmp_path / "ctx"], inputs={"bundle": "test"}))


def test_guarded_step_three_never_pays_for_a_missing_conflict_reply(world, tmp_path):
    rows, ext = _built(world, tmp_path)
    transport, seen = wire(ContradictingMock())
    purposes = ["v2_stage3"]
    with PL.open_paid(tmp_path / "s", "v2", approval(purposes), purposes, transport=transport,
                      confirmed=True) as paid:  # fmt: skip  (a fresh ledger: step 1 not run)
        with pytest.raises(LedgerError, match="not in the paid ledger"):
            PL.evaluate(rows, [ext], paid.stage3, tmp_path / "out", conditions=CONDITIONS[:1],
                        methods=("static",),
                        contexts=TP.Contexts([tmp_path / "ctx"], inputs={"bundle": "test"}))
        assert Decimal(paid.spend()["v2_stage3"]) == 0
    assert seen == []


def test_contexts_shards_must_be_disjoint_and_consistent(world, tmp_path):
    _built(world, tmp_path)
    with pytest.raises(LedgerError, match="twice"):
        TP.Contexts([tmp_path / "ctx", tmp_path / "ctx"], inputs={"bundle": "test"})


def test_cli_step_one_is_gated_like_every_paid_stage(tmp_path):
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts/run_protocol_v2.py"
    spec = importlib.util.spec_from_file_location("run_protocol_v2", path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    with pytest.raises(LedgerError, match="confirm-paid"):
        cli.main(["conflicts", "--bundle", str(tmp_path / "none"), "--requests",
                  str(tmp_path / "r.json"), "--sessions", str(tmp_path / "s"),
                  "--approval", str(tmp_path / "a.json"), "--out", str(tmp_path / "x"),
                  "--freeze", str(tmp_path / "f.json")])
    (tmp_path / "a.json").write_text(json.dumps({"approved_by": "owner",
                                                 "protocol_v2_digest": "0" * 64}))
    (tmp_path / "f.json").write_text(json.dumps({"protocol": {}, "hashes": {},
                                                 "protocol_v2_digest": "1" * 64}))
    with pytest.raises(LedgerError, match="edited after"):  # step 2.2 freeze gate
        cli.main(["conflicts", "--bundle", str(tmp_path / "none"), "--requests",
                  str(tmp_path / "r.json"), "--sessions", str(tmp_path / "s"),
                  "--approval", str(tmp_path / "a.json"), "--out", str(tmp_path / "x"),
                  "--freeze", str(tmp_path / "f.json"), "--confirm-paid"])
    assert not (tmp_path / "s").exists() and not (tmp_path / "x").exists()
