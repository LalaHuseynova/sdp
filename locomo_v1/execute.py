"""Execution: answers and judges for every distinct (question, context) of the build, then the
pre-specified judge check. Mock (free) or paid (strict OpenRouter guard). Resumable: answers
and judgements are appended per key, and the response cache replays finished calls at $0.

Stopping rule S2 (protocol): after each conversation, if more than 2% of calls in this run
failed, stop and report (no analysis of partial outcomes).

v1.2 (technical restart; reports/PROTOCOL_LOCOMO_V1_2_AMENDMENT.md), infrastructure only:
- the live strict-guard ledger is a verified copy on WSL ext4 (`K.STATE_DIR`), and the frozen
  guard's full-ledger audit runs between batches instead of inside every call (`FixedCeilingGuard`);
- a stop or an incomplete run exits non-zero and is recorded in progress.jsonl;
- the judge check drops `temperature`, which no Claude Haiku 5.5 endpoint accepts.
Prompts, models, questions, contexts, metrics and the judge are unchanged.
"""

from __future__ import annotations

import json
import os
import random
import hashlib
import re
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from . import build as B
from . import config as K

from ams.core.prompts import PromptLibrary  # noqa: E402
from ams.data.locomo import load_locomo  # noqa: E402
from ams.eval.locomo import LoCoMoQA, normalize_answer  # noqa: E402
from ams.llm.pool import map_concurrent  # noqa: E402


def selected(job: dict, draws: int) -> bool:
    """Cells in the run's draw set (the cost rule may keep draws 0..2 only)."""
    if job["cell"].startswith("clean|"):
        return True
    return int(job["cell"].split("|")[4][1:]) < draws


class _R:
    def __init__(self, text):
        self.text = text


class MockClient:
    """Free stand-in: answers with an injected value if one is in the context (exercises the
    ASR path), else with the first quoted phrase; the judge marks CORRECT iff the normalised
    gold is contained in the prediction."""

    provider = "mock"

    def complete(self, req):
        t = req.messages[0].content
        if t.startswith("You are grading"):
            gold = t.split("Gold answer:", 1)[1].split("\n", 1)[0].strip()
            pred = t.split("Generated answer:", 1)[1].split("\n", 1)[0].strip()
            g = normalize_answer(gold)
            return _R("CORRECT" if g and g in normalize_answer(pred) else "WRONG")
        m = re.search(r'By the way, about .*?: it is (.*?)\."', t)
        if m:
            return _R(m.group(1))
        m = re.search(r'said, "([^"]{1,40})', t)
        return _R(m.group(1) if m else "unknown")


def _env_key():
    sys.path.insert(0, str(K.REPO))
    from minja_v2.runner import read_env_file

    key = read_env_file(K.REPO / ".env").get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY missing from .env")
    os.environ["OPENROUTER_API_KEY"] = key


class FixedCeilingGuard:
    """v1.2, infrastructure only. The frozen strict client (`openai_client.py`) calls
    `guard.snapshot()` on every request only to read three settings the guard fixes for its
    lifetime (price ceilings, context bound; it refuses a changed configuration). The frozen
    `snapshot()` also audits the whole ledger inside an exclusive SQLite lock: O(ledger) per
    call, which starved 16 workers ("database is locked") as the ledger grew. This proxy serves
    those fixed settings from one audited snapshot and delegates every accounting operation
    (reserve, settle, mark_unknown, halt) unchanged, so the cap is still enforced on every call.
    `audit()` runs the frozen full audit; `run` calls it whenever no worker is active."""

    FIXED = ("max_input_per_mtok", "max_output_per_mtok", "context_token_bound", "model")

    def __init__(self, guard):
        self._guard = guard
        self._fixed = None
        self.audits = 0
        self.audit()

    def audit(self) -> dict:
        from ams.llm.budget import BudgetAccountingError

        snap = self._guard.snapshot()  # frozen: _audit_totals over the whole ledger
        fixed = {k: snap[k] for k in self.FIXED}
        if self._fixed is not None and fixed != self._fixed:
            raise BudgetAccountingError("guard settings changed during the run")
        self._fixed = fixed
        self.audits += 1
        if snap["blocked"]:
            raise BudgetAccountingError(f"guard blocked: {snap['blocked_reason']}")
        return snap

    def snapshot(self) -> dict:
        return dict(self._fixed)

    def reserve(self, *a, **k):
        return self._guard.reserve(*a, **k)

    def settle(self, *a, **k):
        return self._guard.settle(*a, **k)

    def mark_unknown(self, *a, **k):
        return self._guard.mark_unknown(*a, **k)

    def halt(self, *a, **k):
        return self._guard.halt(*a, **k)


def ledger_summary(path: Path) -> dict:
    """Read-only summary of a strict-guard ledger: settings, totals, counts by state, and a
    digest over every reservation row (identical iff the ledgers are identical)."""
    con = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
    try:
        cfg = con.execute("SELECT settings,blocked,blocked_reason,used_nanodollars,"
                          "held_nanodollars FROM budget_config").fetchone()
        h = hashlib.sha256()
        counts: dict = {}
        for row in con.execute("SELECT * FROM reservations ORDER BY reservation_id"):
            h.update(json.dumps(row).encode())
            counts[row[6]] = counts.get(row[6], 0) + 1
        events = con.execute("SELECT COUNT(*) FROM budget_review_events").fetchone()[0]
    finally:
        con.close()
    return {"settings": json.loads(cfg[0]), "blocked": cfg[1], "blocked_reason": cfg[2],
            "used_usd": int(cfg[3]) / 1e9, "held_usd": int(cfg[4]) / 1e9,
            "counts": dict(sorted(counts.items())), "review_events": events,
            "reservations_sha256": h.hexdigest()}


def _sqlite_copy(src: Path, dst: Path) -> None:
    """Consistent copy through the SQLite backup API; the source is opened read-only."""
    s = sqlite3.connect(f"file:{Path(src).as_posix()}?mode=ro", uri=True)
    d = sqlite3.connect(dst)
    try:
        s.backup(d)
    finally:
        d.close()
        s.close()


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def live_guard_path(run_dir: Path, state_dir: Path) -> Path:
    """The live ledger is on WSL ext4. On first use the /mnt/c ledger is copied there and
    verified row by row; the original is never opened for writing again (kept as the record
    of the state at the S2 stop). Refuses any state in which spend history could be lost."""
    live = Path(state_dir) / run_dir.name / "budget_guard.sqlite"
    marker = run_dir / K.GUARD_MIGRATION
    orig = run_dir / "budget_guard.sqlite"
    if live.exists():
        if not marker.exists():
            raise SystemExit(f"{live} exists without {marker.name}; refusing")
        if json.loads(marker.read_text()).get("live") != str(live):
            raise SystemExit("migration record names another live ledger; refusing")
        return live
    if marker.exists():
        raise SystemExit(f"{marker.name} exists but the live ledger {live} is missing: spend "
                         "history would be lost; refusing")
    live.parent.mkdir(parents=True, exist_ok=True)
    rec = {"utc": datetime.now(UTC).isoformat(timespec="seconds"), "live": str(live),
           "protocol": K.PROTOCOL_ID}
    if orig.exists():
        def files():  # data only: -shm is SQLite's transient index, and a read-only open
            # creates an empty -wal where none existed (no data); both are ignored
            return {f: _sha(run_dir / f) for f in ("budget_guard.sqlite", "budget_guard.sqlite-wal")
                    if (run_dir / f).exists() and (run_dir / f).stat().st_size}

        before_files = files()
        before = ledger_summary(orig)
        _sqlite_copy(orig, live)
        after = ledger_summary(live)
        if before != after or before_files != files():
            live.unlink()
            raise SystemExit("ledger copy does not verify; refusing")
        rec.update(source=str(orig), source_files_sha256=before_files, summary=before,
                   copy_verified=True)
    else:
        rec.update(source=None, fresh=True)
    marker.write_text(json.dumps(rec, indent=1))
    return live


def _strict_client(guard, cache, stage: str, sdk_client=None):
    """The client `registry.build_client` makes for an openrouter spec (the frozen OpenAIClient
    in a ManagedClient with the response cache and default retry), given an explicit guard."""
    from ams.llm.pool import ManagedClient
    from ams.llm.providers.openai_client import OpenAIClient

    os.environ.pop("AMS_STRICT_BUDGET_PATH", None)  # the guard is passed explicitly
    raw = OpenAIClient(api_key=os.environ.get("OPENROUTER_API_KEY"),
                       base_url="https://openrouter.ai/api/v1", provider="openrouter",
                       budget_guard=guard, sdk_client=sdk_client)
    return ManagedClient(raw, cache=cache, stage=stage)


def paid_qa(run_dir: Path, prompts, state_dir: Path = K.STATE_DIR, sdk_client=None):
    """(LoCoMoQA, FixedCeilingGuard). `sdk_client` is a test double (no network)."""
    from ams.llm import ResponseCache
    from ams.llm.budget import BudgetGuard

    if sdk_client is None:
        _env_key()
    guard = FixedCeilingGuard(BudgetGuard(live_guard_path(run_dir, state_dir),
                                          limit_usd=K.CAP_USD))
    cache = ResponseCache(run_dir / "response_cache.sqlite")
    qa = LoCoMoQA(_strict_client(guard, cache, "agent_answer", sdk_client), K.MODEL,
                  _strict_client(guard, cache, "judge", sdk_client), K.MODEL, prompts)
    return qa, guard


class DropParamsSDK:
    """v1.2, judge check only: every Claude Haiku 5.5 endpoint on OpenRouter rejects
    `temperature` (model check file), and the frozen strict client sends it together with
    `provider.require_parameters=true`, so OpenRouter answered HTTP 404. This wrapper around the
    OpenAI SDK object removes the listed fields and nothing else."""

    def __init__(self, sdk, drop=K.JUDGE_CHECK_DROP):
        self._sdk, self._drop = sdk, tuple(drop)
        self.base_url = sdk.base_url
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def with_options(self, **kw):
        return DropParamsSDK(self._sdk.with_options(**kw), self._drop)

    def _create(self, **kw):
        for k in self._drop:
            kw.pop(k, None)
        return self._sdk.chat.completions.create(**kw)


APPEND_ONLY = ("answers.jsonl", "judgements.jsonl", "errors.jsonl", "progress.jsonl")
UNCHANGED = ("budget_guard.sqlite", "budget_guard.sqlite-wal", "judge_check.jsonl",
             "judge_check_guard.sqlite", "judge_check_guard.sqlite-wal")


def _prefix_sha(path: Path, size: int) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        h.update(fh.read(size))
    return h.hexdigest()


def preservation(run_dir: Path, record: Path) -> dict:
    """v1.2: the state of every earlier record, by hash and size only (no content is parsed).
    The first call writes `record`; later calls check against it: append-only logs must still
    begin with their recorded bytes, ledgers and the failed v1.1 judge check must be unchanged,
    the response cache must keep every recorded row, and the quarantine must be unchanged."""
    q = run_dir / "quarantine_S2_partial_analysis_UNREAD"
    cur = {
        "append_only": {f: {"bytes": (run_dir / f).stat().st_size,
                            "sha256": _sha(run_dir / f)} for f in APPEND_ONLY
                        if (run_dir / f).exists()},
        "unchanged": {f: _sha(run_dir / f) for f in UNCHANGED if (run_dir / f).exists()},
        "quarantine": {p.name: _sha(p) for p in sorted(q.glob("*"))} if q.exists() else {},
    }
    con = sqlite3.connect(f"file:{(run_dir / 'response_cache.sqlite').as_posix()}?mode=ro",
                          uri=True)
    try:
        cur["response_cache_rows"] = con.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
        keys = hashlib.sha256()
        for (k,) in con.execute("SELECT key FROM responses ORDER BY key"):
            keys.update(k.encode())
        cur["response_cache_keys_sha256"] = keys.hexdigest()
    finally:
        con.close()
    if not record.exists():
        record.write_text(json.dumps({"recorded_utc": datetime.now(UTC).isoformat(
            timespec="seconds"), **cur}, indent=1))
        return {"recorded": str(record), **cur}
    rec = json.loads(record.read_text())
    bad = []
    for f, r in rec["append_only"].items():
        p = run_dir / f
        if not p.exists() or p.stat().st_size < r["bytes"] or _prefix_sha(p, r["bytes"]) != \
                r["sha256"]:
            bad.append(f)
    bad += [f for f, h in rec["unchanged"].items() if cur["unchanged"].get(f) != h]
    if cur["quarantine"] != rec["quarantine"]:
        bad.append("quarantine")
    if cur["response_cache_rows"] < rec["response_cache_rows"]:
        bad.append("response_cache_rows")
    return {"checked_against": str(record), "all_preserved": not bad, "changed": bad,
            "response_cache_rows_now": cur["response_cache_rows"]}


def _append(path: Path, rows):
    with path.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def _read(path: Path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x] \
        if path.exists() else []


def estimate(build_dir: Path, draws: int, convs=K.CONVS, run_dir: Path | None = None) -> dict:
    """The pilot's estimator (chars/4 input, 32 + 4 output tokens, one judge per answer),
    times the pilot calibration (actual spend / estimate). With `run_dir`, only the keys
    without a recorded answer (v1.2 restart: what is left to pay for)."""
    prompts = PromptLibrary(K.REPO / "prompts")
    tpl = prompts.get("locomo_qa")
    qmap = {q.qid: q for c in load_locomo(K.DATA) for q in c.qa}
    done = _answered(run_dir) if run_dir is not None else set()
    n = chars = 0
    per = {}
    for cid in convs:
        ctx = B.load_contexts(build_dir, cid)
        keys = {(j["qid"], j["ctx"]) for j in B.load_jobs(build_dir, cid)
                if selected(j, draws)} - done
        cc = sum(len(tpl.render(context=ctx[h], question=qmap[q].question)) for q, h in keys)
        per[cid] = len(keys)
        n += len(keys)
        chars += cc
    raw = (chars / 4 * 0.15 + n * 32 * 0.60 + n * 160 * 0.15 + n * 4 * 0.60) / 1e6
    return {"draws": draws, "unique_answer_prompts": n, "per_conversation": per,
            "raw_estimate_usd": round(raw, 3),
            "calibrated_usd": round(raw * K.PILOT_CALIBRATION, 3),
            "calibration": round(K.PILOT_CALIBRATION, 4)}


def _answered(run_dir: Path) -> set:
    """Keys (qid, ctx) with a recorded answer. Reads only the keys, never the outcomes."""
    return {(r["qid"], r["ctx"]) for r in _read(run_dir / "answers.jsonl")}


def completeness(build_dir: Path, run_dir: Path, draws: int, convs=K.CONVS) -> dict:
    """Selected keys without an answer, and answers without a judgement (counts only)."""
    pred = {(r["qid"], r["ctx"]): r["prediction"] for r in _read(run_dir / "answers.jsonl")}
    judged = {(r["qid"], r["prediction"]) for r in _read(run_dir / "judgements.jsonl")}
    miss_a = miss_j = total = 0
    for cid in convs:
        for k in {(j["qid"], j["ctx"]) for j in B.load_jobs(build_dir, cid) if selected(j, draws)}:
            total += 1
            if k not in pred:
                miss_a += 1
            elif (k[0], pred[k]) not in judged:
                miss_j += 1
    return {"selected_keys": total, "missing_answers": miss_a, "missing_judgements": miss_j}


def run(build_dir: Path, run_dir: Path, mode: str, draws: int, workers: int = 16,
        convs=K.CONVS, state_dir: Path = K.STATE_DIR, sdk_client=None, client=None) -> dict:
    """One execution segment. Keys already answered or judged are skipped; every other key is
    attempted, then (v1.2) once more in a retry pass if its call raised. S2 is checked after
    each conversation on this segment's calls; a stop is recorded and returned. `sdk_client`
    (fake OpenAI SDK) and `client` (fake LLM client) are test doubles."""
    prompts = PromptLibrary(K.REPO / "prompts")
    qmap = {q.qid: q for c in load_locomo(K.DATA) for q in c.qa}
    guard = None
    if mode == "mock":
        client = client or MockClient()
        qa = LoCoMoQA(client, "mock", client, "mock", prompts)
    else:
        qa, guard = paid_qa(run_dir, prompts, state_dir, sdk_client)
    ans_path, jud_path = run_dir / "answers.jsonl", run_dir / "judgements.jsonl"
    prog_path = run_dir / "progress.jsonl"
    pred = {(r["qid"], r["ctx"]): r["prediction"] for r in _read(ans_path)}
    judged = {(r["qid"], r["prediction"]) for r in _read(jud_path)}
    _append(prog_path, [{"segment": K.PROTOCOL_ID, "mode": mode, "workers": workers,
                         "started_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                         "answered_before": len(pred), "judged_before": len(judged)}])
    calls = fails = 0

    def ans(key):
        qid, h = key
        try:
            return {"qid": qid, "ctx": h, "prediction": qa.answer(qmap[qid], ctx[h]),
                    "error": None}
        except Exception as e:  # noqa: BLE001
            return {"qid": qid, "ctx": h, "prediction": None, "error": repr(e)[:300]}

    def jud(key):
        qid, p = key
        try:
            return {"qid": qid, "prediction": p, "correct": qa.judged(qmap[qid], p),
                    "error": None}
        except Exception as e:  # noqa: BLE001
            return {"qid": qid, "prediction": p, "correct": None, "error": repr(e)[:300]}

    def stop(reason, progress):
        rec = {"stop": reason, **progress}
        _append(prog_path, [rec])
        print(json.dumps(rec), flush=True)
        return {"stopped": reason, **progress}

    for pass_ in range(1 + K.RETRY_PASSES):
        for cid in convs:
            ctx = B.load_contexts(build_dir, cid)
            sel = {(j["qid"], j["ctx"]) for j in B.load_jobs(build_dir, cid) if selected(j, draws)}
            keys = sorted(sel - set(pred))
            if pass_ and not keys and not any((k[0], pred[k]) not in judged for k in sel):
                continue
            rows = map_concurrent(ans, keys, workers=workers,
                                  progress=f"answer {cid}" + (" (retry)" if pass_ else ""))
            _append(ans_path, [r for r in rows if r["error"] is None])
            _append(run_dir / "errors.jsonl", [{**r, "segment": K.PROTOCOL_ID, "pass": pass_}
                                               for r in rows if r["error"] is not None])
            pred.update({(r["qid"], r["ctx"]): r["prediction"] for r in rows
                         if r["error"] is None})
            if guard is not None:
                guard.audit()  # frozen full-ledger audit, no worker active
            # every answered key of this conversation that has no judgement (v1.2: includes
            # answers whose judge call failed in an earlier segment)
            jkeys = sorted({(k[0], pred[k]) for k in sel if k in pred} - judged)
            jrows = map_concurrent(jud, jkeys, workers=workers,
                                   progress=f"judge {cid}" + (" (retry)" if pass_ else ""))
            _append(jud_path, [r for r in jrows if r["error"] is None])
            _append(run_dir / "errors.jsonl", [{**r, "segment": K.PROTOCOL_ID, "pass": pass_}
                                               for r in jrows if r["error"] is not None])
            judged |= {(r["qid"], r["prediction"]) for r in jrows if r["error"] is None}
            if guard is not None:
                guard.audit()
            calls += len(rows) + len(jrows)
            fails += sum(r["error"] is not None for r in rows) + sum(
                r["error"] is not None for r in jrows)
            progress = {"conv": cid, "pass": pass_, "calls": calls, "failed": fails,
                        "segment": K.PROTOCOL_ID}
            _append(prog_path, [progress])
            print(json.dumps(progress), flush=True)
            if calls and fails / calls > K.MAX_ERROR_RATE:
                return stop("S2 error rate", progress)
    comp = completeness(build_dir, run_dir, draws, convs)
    out = {"stopped": None, "calls": calls, "failed": fails, **comp}
    if comp["missing_answers"] or comp["missing_judgements"]:
        return stop("incomplete", {"calls": calls, "failed": fails, **comp})
    _append(prog_path, [{"segment_done": K.PROTOCOL_ID, **out}])
    return out


def judge_check(run_dir: Path, mode: str, sdk_client=None) -> dict:
    """Pre-specified validity check: 400 seeded judgements re-judged by Claude Haiku 5.5
    (separate guard, own cap), Cohen's kappa against the GPT-4o-mini judge.
    v1.2: own output file and guard (v1.1's are kept), `temperature` dropped (DropParamsSDK),
    and a one-call canary: if the first call fails, nothing more is sent."""
    out_path = run_dir / K.JUDGE_CHECK_FILE
    if out_path.exists():
        raise SystemExit(f"{out_path.name} exists; the judge check is recorded once")
    rows = sorted((r for r in _read(run_dir / "judgements.jsonl")), key=lambda r: (r["qid"],
                                                                                   r["prediction"]))
    sample = random.Random(K.SEED_JUDGE_SAMPLE).sample(rows, min(K.JUDGE_CHECK_N, len(rows)))
    prompts = PromptLibrary(K.REPO / "prompts")
    qmap = {q.qid: q for c in load_locomo(K.DATA) for q in c.qa}
    guard = None
    if mode == "mock":
        client, model = MockClient(), "mock"
    else:
        from ams.llm import ResponseCache
        from ams.llm.budget import BudgetGuard
        from ams.llm.pool import ManagedClient
        from ams.llm.providers.openai_client import OpenAIClient

        if sdk_client is None:
            _env_key()
            from openai import OpenAI

            sdk_client = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"],
                                base_url="https://openrouter.ai/api/v1", timeout=120.0,
                                max_retries=0)
        guard = FixedCeilingGuard(BudgetGuard(
            run_dir / K.JUDGE_CHECK_GUARD, limit_usd=K.JUDGE_CHECK_CAP_USD,
            allowed_model=K.JUDGE_CHECK_MODEL, max_input_per_mtok="0.10",
            max_output_per_mtok="0.50", context_token_bound=1_000_000))  # Haiku's context
        raw = OpenAIClient(base_url="https://openrouter.ai/api/v1", provider="openrouter",
                           budget_guard=guard, sdk_client=DropParamsSDK(sdk_client))
        client = ManagedClient(raw, cache=ResponseCache(run_dir / "response_cache.sqlite"),
                               stage="judge_check")
        model = K.JUDGE_CHECK_MODEL
    check = LoCoMoQA(client, model, client, model, prompts)

    def one(r):
        try:
            return {**r, "check": check.judged(qmap[r["qid"]], r["prediction"])}
        except Exception as e:  # noqa: BLE001
            return {**r, "check": None, "check_error": repr(e)[:300]}

    first = one(sample[0]) if sample else None
    if first is not None and first.get("check") is None:
        failed = run_dir / f"judge_check_v1_2_canary_failed_{datetime.now(UTC):%Y%m%dT%H%M%S}.jsonl"
        _append(failed, [{"qid": first["qid"], "check_error": first["check_error"]}])
        return {"n": 1, "failed": 1, "canary_failed": True, "record": failed.name}
    # 2 workers: each strict reservation covers the 1M-token context (~$0.10), well below $1
    out = [first, *map_concurrent(one, sample[1:], workers=2, progress="judge check")]
    if guard is not None:
        guard.audit()
    _append(out_path, out)
    return {"n": len(out), "failed": sum(r.get("check") is None for r in out),
            "canary_failed": False}


def sensitive_verdicts(out: Path, mode: str) -> dict:
    """v1.1: the frozen MemLineage SensitiveAction classifier (prompt `sensitive_action` v1),
    once per distinct category 1-4 question text, recorded for S2-ID (separate $1 guard).
    A file is never overwritten."""
    from ams.baselines.memlineage import SensitiveAction

    if out.exists():
        raise SystemExit(f"{out} exists; verdicts are recorded once")
    prompts = PromptLibrary(K.REPO / "prompts")
    questions = sorted({q.question for c in load_locomo(K.DATA) for q in c.qa
                        if q.category in K.QA_CATEGORIES})
    if mode == "mock":
        client, model = MockClient(), "mock"
    else:
        from ams.llm import ResponseCache
        from ams.llm.registry import build_client

        _env_key()
        os.environ["AMS_STRICT_BUDGET_PATH"] = str(out.parent / "sensitive_guard.sqlite")
        os.environ["AMS_STRICT_BUDGET_LIMIT_USD"] = K.SENSITIVE_CAP_USD
        client = build_client(K.MODEL_SPEC, cache=ResponseCache(out.parent /
                                                                "sensitive_cache.sqlite"),
                              stage="sensitive_action")
        model = K.MODEL
    clf = SensitiveAction(client, model, prompts=prompts, version=K.SENSITIVE_PROMPT_VERSION)

    def one(q):
        return q, ("SENSITIVE" if clf(q) else "ORDINARY")
    rows = dict(map_concurrent(one, questions, workers=8, progress="sensitive"))
    body = {"prompt": f"sensitive_action/{K.SENSITIVE_PROMPT_VERSION}", "model": model,
            "n": len(rows), "n_sensitive": sum(v == "SENSITIVE" for v in rows.values()),
            "verdicts": rows}
    out.write_text(json.dumps(body, indent=1, sort_keys=True))
    return {k: body[k] for k in ("n", "n_sensitive", "model")}
