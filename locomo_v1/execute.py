"""Execution: answers and judges for every distinct (question, context) of the build, then the
pre-specified judge check. Mock (free) or paid (strict OpenRouter guard). Resumable: answers
and judgements are appended per key, and the response cache replays finished calls at $0.

Stopping rule S2 (protocol): after each conversation, if more than 2% of calls in this run
failed, stop and report (no analysis of partial outcomes).
"""

from __future__ import annotations

import json
import os
import random
import re
import sys
from pathlib import Path

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


def paid_qa(run_dir: Path, prompts) -> LoCoMoQA:
    from ams.llm import ResponseCache
    from ams.llm.registry import build_client

    _env_key()
    os.environ["AMS_STRICT_BUDGET_PATH"] = str(run_dir / "budget_guard.sqlite")
    os.environ["AMS_STRICT_BUDGET_LIMIT_USD"] = K.CAP_USD
    cache = ResponseCache(run_dir / "response_cache.sqlite")
    return LoCoMoQA(build_client(K.MODEL_SPEC, cache=cache, stage="agent_answer"), K.MODEL,
                    build_client(K.MODEL_SPEC, cache=cache, stage="judge"), K.MODEL, prompts)


def _append(path: Path, rows):
    with path.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def _read(path: Path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x] \
        if path.exists() else []


def estimate(build_dir: Path, draws: int, convs=K.CONVS) -> dict:
    """The pilot's estimator (chars/4 input, 32 + 4 output tokens, one judge per answer),
    times the pilot calibration (actual spend / estimate)."""
    prompts = PromptLibrary(K.REPO / "prompts")
    tpl = prompts.get("locomo_qa")
    qmap = {q.qid: q for c in load_locomo(K.DATA) for q in c.qa}
    n = chars = 0
    per = {}
    for cid in convs:
        ctx = B.load_contexts(build_dir, cid)
        keys = {(j["qid"], j["ctx"]) for j in B.load_jobs(build_dir, cid) if selected(j, draws)}
        cc = sum(len(tpl.render(context=ctx[h], question=qmap[q].question)) for q, h in keys)
        per[cid] = len(keys)
        n += len(keys)
        chars += cc
    raw = (chars / 4 * 0.15 + n * 32 * 0.60 + n * 160 * 0.15 + n * 4 * 0.60) / 1e6
    return {"draws": draws, "unique_answer_prompts": n, "per_conversation": per,
            "raw_estimate_usd": round(raw, 3),
            "calibrated_usd": round(raw * K.PILOT_CALIBRATION, 3),
            "calibration": round(K.PILOT_CALIBRATION, 4)}


def run(build_dir: Path, run_dir: Path, mode: str, draws: int, workers: int = 16,
        convs=K.CONVS) -> dict:
    prompts = PromptLibrary(K.REPO / "prompts")
    qmap = {q.qid: q for c in load_locomo(K.DATA) for q in c.qa}
    if mode == "mock":
        client = MockClient()
        qa = LoCoMoQA(client, "mock", client, "mock", prompts)
    else:
        qa = paid_qa(run_dir, prompts)
    ans_path, jud_path = run_dir / "answers.jsonl", run_dir / "judgements.jsonl"
    done = {(r["qid"], r["ctx"]) for r in _read(ans_path)}
    judged = {(r["qid"], r["prediction"]) for r in _read(jud_path)}
    calls = fails = 0
    for cid in convs:
        ctx = B.load_contexts(build_dir, cid)
        keys = sorted({(j["qid"], j["ctx"]) for j in B.load_jobs(build_dir, cid)
                       if selected(j, draws)} - done)

        def ans(key):
            qid, h = key
            try:
                return {"qid": qid, "ctx": h, "prediction": qa.answer(qmap[qid], ctx[h]),
                        "error": None}
            except Exception as e:  # noqa: BLE001
                return {"qid": qid, "ctx": h, "prediction": None, "error": repr(e)[:300]}

        rows = map_concurrent(ans, keys, workers=workers, progress=f"answer {cid}")
        _append(ans_path, [r for r in rows if r["error"] is None])
        _append(run_dir / "errors.jsonl", [r for r in rows if r["error"] is not None])
        done |= {(r["qid"], r["ctx"]) for r in rows if r["error"] is None}
        jkeys = sorted({(r["qid"], r["prediction"]) for r in rows if r["error"] is None} - judged)

        def jud(key):
            qid, pred = key
            try:
                return {"qid": qid, "prediction": pred, "correct": qa.judged(qmap[qid], pred),
                        "error": None}
            except Exception as e:  # noqa: BLE001
                return {"qid": qid, "prediction": pred, "correct": None, "error": repr(e)[:300]}

        jrows = map_concurrent(jud, jkeys, workers=workers, progress=f"judge {cid}")
        _append(jud_path, [r for r in jrows if r["error"] is None])
        _append(run_dir / "errors.jsonl", [r for r in jrows if r["error"] is not None])
        judged |= {(r["qid"], r["prediction"]) for r in jrows if r["error"] is None}
        calls += len(rows) + len(jrows)
        fails += sum(r["error"] is not None for r in rows) + sum(
            r["error"] is not None for r in jrows)
        progress = {"conv": cid, "calls": calls, "failed": fails}
        _append(run_dir / "progress.jsonl", [progress])
        print(json.dumps(progress), flush=True)
        if calls and fails / calls > K.MAX_ERROR_RATE:
            print(json.dumps({"stop": "S2 error rate", **progress}), flush=True)
            return {"stopped": "S2", **progress}
    return {"stopped": None, "calls": calls, "failed": fails}


def judge_check(run_dir: Path, mode: str) -> dict:
    """Pre-specified validity check: 400 seeded judgements re-judged by Claude Haiku 5.5
    (separate guard, own cap), Cohen's kappa against the GPT-4o-mini judge."""
    rows = sorted((r for r in _read(run_dir / "judgements.jsonl")), key=lambda r: (r["qid"],
                                                                                   r["prediction"]))
    sample = random.Random(K.SEED_JUDGE_SAMPLE).sample(rows, min(K.JUDGE_CHECK_N, len(rows)))
    prompts = PromptLibrary(K.REPO / "prompts")
    qmap = {q.qid: q for c in load_locomo(K.DATA) for q in c.qa}
    if mode == "mock":
        client, model = MockClient(), "mock"
    else:
        from ams.llm import ResponseCache
        from ams.llm.budget import BudgetGuard
        from ams.llm.pool import ManagedClient
        from ams.llm.providers.openai_client import OpenAIClient

        _env_key()
        guard = BudgetGuard(run_dir / "judge_check_guard.sqlite", limit_usd=K.JUDGE_CHECK_CAP_USD,
                            allowed_model=K.JUDGE_CHECK_MODEL, max_input_per_mtok="0.10",
                            max_output_per_mtok="0.50",
                            context_token_bound=1_000_000)  # Haiku's advertised context
        raw = OpenAIClient(api_key=os.environ["OPENROUTER_API_KEY"],
                           base_url="https://openrouter.ai/api/v1", provider="openrouter",
                           budget_guard=guard)
        client = ManagedClient(raw, cache=ResponseCache(run_dir / "response_cache.sqlite"),
                               stage="judge_check")
        model = K.JUDGE_CHECK_MODEL
    check = LoCoMoQA(client, model, client, model, prompts)

    def one(r):
        try:
            return {**r, "check": check.judged(qmap[r["qid"]], r["prediction"])}
        except Exception as e:  # noqa: BLE001
            return {**r, "check": None, "check_error": repr(e)[:300]}

    # 2 workers: each strict reservation covers the 1M-token context (~$0.10), well below $1
    out = map_concurrent(one, sample, workers=2, progress="judge check")
    _append(run_dir / "judge_check.jsonl", out)
    return {"n": len(out), "failed": sum(r.get("check") is None for r in out)}


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
