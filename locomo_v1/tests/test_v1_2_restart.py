"""Free tests for the v1.2 technical restart (no network): the frozen strict guard and the
frozen OpenAI client are real; only the OpenAI SDK object is a fake."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from locomo_v1 import config as K
from locomo_v1 import execute as E

from ams.llm.budget import BudgetExhausted, BudgetGuard
from ams.llm.pool import map_concurrent
from ams.llm.types import ChatRequest, Message


class FakeSDK:
    """Stands in for `openai.OpenAI`: records every request body, answers like OpenRouter."""

    base_url = "https://openrouter.ai/api/v1/"

    def __init__(self, model="openai/gpt-4o-mini", text="ok", fail_first=0, fail=None):
        self.model, self.text, self.fail_first, self.fail = model, text, fail_first, fail
        self.calls, self.lock = [], threading.Lock()
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def with_options(self, **kw):
        return self

    def _create(self, **kw):
        with self.lock:
            self.calls.append(kw)
            n = len(self.calls)
        if n <= self.fail_first or (self.fail and self.fail(kw)):
            raise RuntimeError("fake transport error")
        return SimpleNamespace(
            id=f"gen-{uuid.uuid4().hex[:12]}", model=self.model, error=None,
            usage=SimpleNamespace(prompt_tokens=120, completion_tokens=2, cost=0.00002,
                                  is_byok=False),
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.text),
                                     finish_reason="stop")])


def _prefill(path, n):
    """A ledger with n settled rows (consistent totals), like the real run's."""
    BudgetGuard(path, limit_usd="30")
    con = sqlite3.connect(path)
    now = datetime.now(UTC).isoformat()
    con.executemany("INSERT INTO reservations VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    [(uuid.uuid4().hex, "openai/gpt-4o-mini", 32, "chat", 19219200, 50,
                      "settled", "{}", "", now, now) for _ in range(n)])
    con.execute("UPDATE budget_config SET used_nanodollars=?", (str(50 * n),))
    con.commit()
    con.close()


# ----------------------------------------------------------------------------- guard


def test_fixed_ceiling_guard_16_workers_no_lock_errors(tmp_path):
    db = tmp_path / "g.sqlite"
    _prefill(db, 60_000)
    proxy = E.FixedCeilingGuard(BudgetGuard(db, limit_usd="30"))
    sdk = FakeSDK()
    client = E._strict_client(proxy, None, "agent_answer", sdk)

    def one(i):
        try:
            client.complete(ChatRequest(messages=(Message("user", f"q{i}"),),
                                        model=K.MODEL, temperature=0.0, max_tokens=32))
            return None
        except Exception as e:  # noqa: BLE001
            return repr(e)

    errs = [e for e in map_concurrent(one, range(800), workers=16) if e]
    assert errs == []
    snap = proxy.audit()  # the frozen full audit still passes
    assert snap["counts"]["settled"] == 60_000 + 800 and snap["counts"]["pending"] == 0
    assert proxy.audits == 2  # once at start, once here: never inside a call
    # the request body is the frozen client's: temperature and strict routing are sent
    assert all(c["temperature"] == 0.0 for c in sdk.calls)
    assert all(c["extra_body"]["provider"]["require_parameters"] for c in sdk.calls)


def test_proxy_keeps_cap_enforcement(tmp_path):
    g = BudgetGuard(tmp_path / "g.sqlite", limit_usd="0.05")  # < 3 GPT-4o-mini reservations
    proxy = E.FixedCeilingGuard(g)
    proxy.reserve(K.MODEL, 32)
    proxy.reserve(K.MODEL, 32)
    with pytest.raises(BudgetExhausted):
        proxy.reserve(K.MODEL, 32)


def test_proxy_audit_stops_on_a_blocked_guard(tmp_path):
    g = BudgetGuard(tmp_path / "g.sqlite", limit_usd="30")
    proxy = E.FixedCeilingGuard(g)
    g.halt("unverified_billing")
    with pytest.raises(Exception, match="blocked"):
        proxy.audit()


# ----------------------------------------------------------------------------- migration


def _run_dir_with_ledger(tmp_path, rows=500):
    rd = tmp_path / "locomo_v1_run"
    rd.mkdir()
    g = BudgetGuard(rd / "budget_guard.sqlite", limit_usd="30")
    for _ in range(rows // 2):
        g.settle(g.reserve(K.MODEL, 32), "0.00003")
    for _ in range(3):
        g.reserve(K.MODEL, 32)  # pending (like the 263 left by the S2 stop)
    return rd


def test_migration_copies_and_verifies_and_never_writes_the_original(tmp_path):
    rd = _run_dir_with_ledger(tmp_path)
    before = E.ledger_summary(rd / "budget_guard.sqlite")
    files = {p.name: E._sha(p) for p in rd.glob("budget_guard.sqlite*") if "shm" not in p.name and p.stat().st_size}
    state = tmp_path / "state"
    live = E.live_guard_path(rd, state)
    assert live == state / rd.name / "budget_guard.sqlite"
    assert E.ledger_summary(live) == before
    rec = json.loads((rd / K.GUARD_MIGRATION).read_text())
    assert rec["copy_verified"] and rec["summary"] == before
    assert {p.name: E._sha(p) for p in rd.glob("budget_guard.sqlite*") if "shm" not in p.name and p.stat().st_size} == files
    # the same live ledger keeps accumulating; the spend history is carried over
    g = BudgetGuard(E.live_guard_path(rd, state), limit_usd="30")
    s = g.snapshot()
    assert s["used_usd"] == pytest.approx(before["used_usd"]) and s["counts"]["pending"] == 3
    assert {p.name: E._sha(p) for p in rd.glob("budget_guard.sqlite*") if "shm" not in p.name and p.stat().st_size} == files


def test_migration_refuses_when_history_could_be_lost(tmp_path):
    rd = _run_dir_with_ledger(tmp_path)
    state = tmp_path / "state"
    live = E.live_guard_path(rd, state)
    live.unlink()
    with pytest.raises(SystemExit, match="spend history would be lost"):
        E.live_guard_path(rd, state)
    (rd / K.GUARD_MIGRATION).unlink()
    live.parent.mkdir(parents=True, exist_ok=True)
    BudgetGuard(live, limit_usd="30")  # a stray fresh ledger
    with pytest.raises(SystemExit, match="without"):
        E.live_guard_path(rd, state)


# ----------------------------------------------------------------------------- judge check


def _judgements(rd, n=30):
    from ams.data.locomo import load_locomo

    qs = [q for c in load_locomo(K.DATA) for q in c.qa if q.category in K.QA_CATEGORIES][:n]
    E._append(rd / "judgements.jsonl",
              [{"qid": q.qid, "prediction": f"p{i}", "correct": i % 2 == 0, "error": None}
               for i, q in enumerate(qs)])


def test_judge_check_drops_only_temperature_and_fits_every_haiku_endpoint(tmp_path):
    _judgements(tmp_path)
    sdk = FakeSDK(model=K.JUDGE_CHECK_MODEL, text="CORRECT")
    r = E.judge_check(tmp_path, "paid", sdk_client=sdk)
    assert r == {"n": 30, "failed": 0, "canary_failed": False}
    allowed = set(json.loads((K.REPO / K.MODEL_CHECK).read_text())[
        "haiku_parameters_supported_by_every_endpoint"])
    for body in sdk.calls:
        assert "temperature" not in body
        assert body["model"] == K.JUDGE_CHECK_MODEL
        assert set(body) - {"model", "messages", "extra_body"} <= allowed
        assert body["extra_body"]["provider"]["require_parameters"] is True
    assert len(sdk.calls) == 30
    g = E.ledger_summary(tmp_path / K.JUDGE_CHECK_GUARD)
    assert g["counts"] == {"settled": 30} and g["settings"]["allowed_model"] == K.JUDGE_CHECK_MODEL
    with pytest.raises(SystemExit, match="recorded once"):
        E.judge_check(tmp_path, "paid", sdk_client=sdk)


def test_judge_check_canary_sends_nothing_more_after_a_failure(tmp_path):
    _judgements(tmp_path)
    sdk = FakeSDK(model=K.JUDGE_CHECK_MODEL, fail_first=10**6)
    r = E.judge_check(tmp_path, "paid", sdk_client=sdk)
    assert r["canary_failed"] and len(sdk.calls) == 1
    assert not (tmp_path / K.JUDGE_CHECK_FILE).exists()


def test_judge_check_refuses_an_unexpected_response_model(tmp_path):
    _judgements(tmp_path)
    sdk = FakeSDK(model="anthropic/some-other-model", text="CORRECT")
    r = E.judge_check(tmp_path, "paid", sdk_client=sdk)
    assert r["canary_failed"] and len(sdk.calls) == 1
    assert E.ledger_summary(tmp_path / K.JUDGE_CHECK_GUARD)["blocked"] == 1


# ----------------------------------------------------------------------------- run


@pytest.fixture(scope="module")
def small(tmp_path_factory):
    from locomo_v1 import build as B
    from ams.data.locomo import load_locomo

    d = tmp_path_factory.mktemp("build")
    conv = {c.sample_id: c for c in load_locomo(K.DATA)}["conv-30"]
    qs = sorted(q.question for q in conv.qa if q.category in K.QA_CATEGORIES)
    B.build_conversation("conv-30", d, draws=1, shapes=("1s",), orientations=(0,),
                         verdicts={q: "ORDINARY" for q in qs})
    return d


def test_paid_path_end_to_end_with_fake_sdk(small, tmp_path):
    rd, state = tmp_path / "run", tmp_path / "state"
    rd.mkdir()
    sdk = FakeSDK(text="CORRECT")
    out = E.run(small, rd, "paid", draws=1, workers=16, convs=("conv-30",), state_dir=state,
                sdk_client=sdk)
    assert out["stopped"] is None and out["failed"] == 0
    assert out["missing_answers"] == 0 and out["missing_judgements"] == 0
    live = E.ledger_summary(state / rd.name / "budget_guard.sqlite")
    assert live["counts"] == {"settled": len(sdk.calls)} and not live["blocked"]
    assert json.loads((rd / K.GUARD_MIGRATION).read_text())["fresh"] is True
    prog = E._read(rd / "progress.jsonl")
    assert prog[0]["segment"] == K.PROTOCOL_ID and "segment_done" in prog[-1]
    # a second segment replays nothing and pays nothing
    n = len(sdk.calls)
    again = E.run(small, rd, "paid", draws=1, workers=16, convs=("conv-30",), state_dir=state,
                  sdk_client=sdk)
    assert again["calls"] == 0 and len(sdk.calls) == n


def test_retry_pass_completes_after_transient_errors(small, tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    seen, lock = set(), threading.Lock()

    def flaky(kw):  # every 60th distinct prompt fails once
        key = kw["messages"][0]["content"]
        with lock:
            first = key not in seen
            seen.add(key)
        return first and hash(key) % 60 == 0

    out = E.run(small, rd, "paid", draws=1, workers=8, convs=("conv-30",),
                state_dir=tmp_path / "state", sdk_client=FakeSDK(text="CORRECT", fail=flaky))
    assert out["stopped"] is None and out["missing_answers"] == 0
    errs = E._read(rd / "errors.jsonl")
    assert errs and all(e["pass"] == 0 and e["segment"] == K.PROTOCOL_ID for e in errs)


class _Failing(E.MockClient):
    def complete(self, req):
        if hash(req.messages[0].content) % 10 == 0:
            raise RuntimeError("down")
        return super().complete(req)


def test_s2_stop_is_recorded_and_blocks_analysis(small, tmp_path, monkeypatch):
    from locomo_v1 import __main__ as M

    out = E.run(small, tmp_path, "mock", draws=1, workers=4, convs=("conv-30",),
                client=_Failing())
    assert out["stopped"] == "S2 error rate"
    assert any(r.get("stop") == "S2 error rate" for r in E._read(tmp_path / "progress.jsonl"))
    monkeypatch.setattr(M, "BUILD", small)
    monkeypatch.setattr(M, "draws", lambda: 1)
    monkeypatch.setattr(E, "completeness",
                        lambda *a, **k: {"missing_answers": 1, "missing_judgements": 0})
    why = M._analysable(tmp_path)
    assert any("stopped" in w for w in why) and any("incomplete" in w for w in why)


def test_preservation_record_and_check(tmp_path):
    rd = tmp_path / "locomo_v1_run"
    rd.mkdir()
    E._append(rd / "answers.jsonl", [{"qid": "a", "ctx": "b", "prediction": "c"}])
    (rd / "judge_check.jsonl").write_text("x\n")
    con = sqlite3.connect(rd / "response_cache.sqlite")
    con.execute("CREATE TABLE responses(key TEXT PRIMARY KEY, provider, model, kind, payload, "
                "created_at)")
    con.execute("INSERT INTO responses VALUES('k1','p','m','chat','{}','t')")
    con.commit()
    con.close()
    rec = tmp_path / "rec.json"
    E.preservation(rd, rec)
    E._append(rd / "answers.jsonl", [{"qid": "d", "ctx": "e", "prediction": "f"}])
    assert E.preservation(rd, rec)["all_preserved"]
    (rd / "answers.jsonl").write_text('{"qid": "z"}\n' * 3)
    (rd / "judge_check.jsonl").write_text("y\n")
    assert set(E.preservation(rd, rec)["changed"]) == {"answers.jsonl", "judge_check.jsonl"}
