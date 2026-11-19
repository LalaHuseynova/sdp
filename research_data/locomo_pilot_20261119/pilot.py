"""LoCoMo real-LLM pilot (PREREGISTRATION.md). Modes: dry (free), mock (free), paid (guarded).

Reuses unchanged: the feasibility generator (hijacks, poison, auditors, frozen decisions),
`ams.data.locomo`, `ams.eval.locomo.LoCoMoQA` (prompts locomo_qa/locomo_judge v1),
`ams.llm.build_client` + ResponseCache + the strict OpenRouter BudgetGuard.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import random
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
spec = importlib.util.spec_from_file_location(
    "feas", REPO / "research_data" / "locomo_feasibility_20261119" / "feasibility.py")
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)

from ams.core.prompts import PromptLibrary  # noqa: E402
from ams.data.locomo import load_locomo  # noqa: E402
from ams.eval.locomo import LoCoMoQA, normalize_answer, official_score  # noqa: E402
from ams.llm.pool import map_concurrent  # noqa: E402

CONVS = ("conv-48", "conv-49")
PIDX = 0  # speaker_a = principal; speaker_b hijacked
HIJACKS = ("1s", "2s", "spread")
AUDITORS = {"A1": (2, 0), "A2": (2, 10)}
ARMS = ("static", "C", "M", "S")
TOPK = 10
MODEL_SPEC = "openrouter:openai/gpt-4o-mini"
MODEL = "openai/gpt-4o-mini"
LIMIT_USD = "5"
DRAWS_RULE_USD = 3.00
WRONG = re.compile(r'it is (.*)\."$')


def sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


# ----------------------------------------------------------------------------- contexts
def ranked_contexts(conv, mem, S, qs, arm, snap, audited_unsafe, poison_of, start):
    recs = mem["records"]
    if arm in ("static", "clean"):
        elig, pen = np.ones(len(recs), bool), np.zeros(len(recs))
    else:
        elig, pen = F.generic_decisions(arm, snap, mem, conv.sample_id, frozenset(), 5,
                                        random.Random(f"check|{arm}"))
    score = np.where(elig[None, :], S - 0.5 * pen[None, :], -np.inf)
    if arm not in ("static", "clean"):
        for qi, q in enumerate(qs):
            i = poison_of.get(q.qid)
            if i is not None and i in audited_unsafe:
                score[qi, i] = -np.inf
    dates = [s.date_time for s in conv.sessions]
    head = start.render(a=conv.speakers[0], b=conv.speakers[1])
    out = []
    for qi in range(len(qs)):
        order = np.argsort(-score[qi], kind="stable")[:TOPK]
        kept = [int(i) for i in order if np.isfinite(score[qi, i])]
        body = "\n".join(f"- [{dates[recs[i]['session']]}] {recs[i]['text']}" for i in kept)
        out.append((kept, head + "\n\n" + (body or "(nothing)")))
    return out, elig


def strata_of(q, mem, by_dia):
    hs = set(mem["hijack_sessions"])
    kinds = set()
    for e in q.evidence:
        i = by_dia.get(e.strip())
        if i is None:
            continue
        r = mem["records"][i]
        kinds.add("principal" if r["speaker"] == mem["principal"]
                  else "in" if r["session"] in hs else "out")
    if not kinds:
        return None
    return {"out": "U_out", "in": "U_in", "principal": "U_principal"}[kinds.pop()] \
        if len(kinds) == 1 else "U_mixed"


def build_cells(convs_by_id, draws, encode):
    """Every (cell, question) job with its context, plus scenario metadata."""
    prompts = PromptLibrary(REPO / "prompts")
    start = prompts.get("locomo_memory_start")
    pool_answers = defaultdict(list)
    for c in convs_by_id.values():
        for q in c.qa:
            if q.category in (1, 2, 3, 4) and q.answer:
                pool_answers[q.category].append((c.sample_id, q.answer))
    jobs, scen = [], {}
    for cid in CONVS:
        c = convs_by_id[cid]
        qs = [q for q in c.qa if q.category in (1, 2, 3, 4)]
        Q = encode([q.question for q in qs])
        # clean reference: the conversation without poison
        clean = {"principal": c.speakers[PIDX], "hijacked": c.speakers[1 - PIDX],
                 "hijack_sessions": [], "targets": [],
                 "records": [{"text": t.render(), "speaker": t.speaker, "session": si,
                              "dia_id": t.dia_id, "target": None}
                             for si, s in enumerate(c.sessions) for t in s.turns]}
        Rc = encode([r["text"] for r in clean["records"]])
        ctx, _ = ranked_contexts(c, clean, Q @ Rc.T, qs, "clean", None, set(), {}, start)
        for q, (kept, text) in zip(qs, ctx):
            jobs.append({"cell": f"{cid}|clean", "conv": cid, "qid": q.qid, "context": text,
                         "kept": kept})
        for hijack in HIJACKS:
            for draw in range(draws):
                rng = random.Random(f"{F.SEED}|{cid}|{PIDX}|{hijack}|{draw}")
                mem = F.build_memory(c, PIDX, hijack, rng, pool_answers)
                recs = mem["records"]
                R = encode([r["text"] for r in recs])
                S = Q @ R.T
                by_dia = {r["dia_id"]: i for i, r in enumerate(recs) if r["dia_id"]}
                poison_of = {r["target"]: i for i, r in enumerate(recs) if r["target"]}
                wrong = {r["target"]: WRONG.search(r["text"]).group(1)
                         for r in recs if r["target"]}
                sid = f"{cid}|{hijack}|d{draw}"
                scen[sid] = {"conv": cid, "hijack": hijack, "draw": draw,
                             "hijack_sessions": mem["hijack_sessions"], "wrong": wrong,
                             "poison_index": poison_of,
                             "strata": {q.qid: strata_of(q, mem, by_dia) for q in qs
                                        if q.qid not in poison_of},
                             "evidence_idx": {q.qid: [by_dia[e.strip()] for e in q.evidence
                                                      if e.strip() in by_dia] for q in qs},
                             "audits": {}}
                ctx, _ = ranked_contexts(c, mem, S, qs, "static", None, set(), poison_of, start)
                for q, (kept, text) in zip(qs, ctx):
                    jobs.append({"cell": f"{sid}|-|static", "conv": cid, "qid": q.qid,
                                 "context": text, "kept": kept})
                for aname, (m, k) in AUDITORS.items():
                    arng = random.Random(f"{F.SEED}|{cid}|{PIDX}|{hijack}|{draw}|{m}|{k}")
                    audits = F.choose_audits(cid, mem, m, k, arng)
                    snap = F.ledger_events(cid, mem, audits)
                    unsafe = {i for i, v, _ in audits if v == "unsafe"}
                    scen[sid]["audits"][aname] = {"unsafe": sorted(unsafe),
                                                  "safe": len(audits) - len(unsafe)}
                    for arm in ("C", "M", "S"):
                        ctx, elig = ranked_contexts(c, mem, S, qs, arm, snap, unsafe, poison_of,
                                                    start)
                        for q, (kept, text) in zip(qs, ctx):
                            jobs.append({"cell": f"{sid}|{aname}|{arm}", "conv": cid,
                                         "qid": q.qid, "context": text, "kept": kept})
    return jobs, scen, prompts


# ----------------------------------------------------------------------------- clients
@dataclass
class _Resp:
    text: str


class MockClient:
    """Free: answers with the poison value if a poison line is in the context, else with the
    first quoted phrase; the judge says CORRECT iff the normalised gold is in the prediction."""

    provider = "mock"

    def complete(self, req):
        t = req.messages[0].content
        if t.startswith("You are grading"):
            gold = t.split("Gold answer:", 1)[1].split("\n", 1)[0].strip()
            pred = t.split("Generated answer:", 1)[1].split("\n", 1)[0].strip()
            ok = normalize_answer(gold) and normalize_answer(gold) in normalize_answer(pred)
            return _Resp("CORRECT" if ok else "WRONG")
        m = re.search(r'By the way, about .*?: it is (.*?)\."', t)
        if m:
            return _Resp(m.group(1))
        m = re.search(r'said, "([^"]{1,40})', t)
        return _Resp(m.group(1) if m else "unknown")


def paid_clients(run_dir: Path):
    from ams.llm import ResponseCache
    from ams.llm.registry import build_client
    sys.path.insert(0, str(REPO))
    from minja_v2.runner import read_env_file

    key = read_env_file(REPO / ".env").get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY missing from .env")
    os.environ["OPENROUTER_API_KEY"] = key
    os.environ["AMS_STRICT_BUDGET_PATH"] = str(run_dir / "budget_guard.sqlite")
    os.environ["AMS_STRICT_BUDGET_LIMIT_USD"] = LIMIT_USD
    cache = ResponseCache(run_dir / "response_cache.sqlite")
    return (build_client(MODEL_SPEC, cache=cache, stage="agent_answer"),
            build_client(MODEL_SPEC, cache=cache, stage="judge"))


# ----------------------------------------------------------------------------- run
def estimate(jobs, prompts, convs_by_id):
    qa_tpl = prompts.get("locomo_qa")
    qmap = {q.qid: q for c in convs_by_id.values() for q in c.qa}
    uniq = {(j["qid"], sha(j["context"])): j for j in jobs}

    def cost(js):
        tok = sum(len(qa_tpl.render(context=j["context"], question=qmap[j["qid"]].question)) / 4
                  for j in js)
        n = len(js)
        return (tok * 0.15 + n * 32 * 0.60 + n * 160 * 0.15 + n * 4 * 0.60) / 1e6
    return {"jobs": len(jobs), "unique_answer_prompts": len(uniq),
            "nominal_usd": round(cost(jobs), 3), "unique_usd": round(cost(list(uniq.values())), 3),
            "note": "chars/4 token estimate; judge prompt ~160 tokens; 32/4 output tokens"}


def run(jobs, qa: LoCoMoQA, convs_by_id, workers):
    qmap = {q.qid: q for c in convs_by_id.values() for q in c.qa}
    uniq = {}
    for j in jobs:
        uniq.setdefault((j["qid"], sha(j["context"])), j)
    keys = list(uniq)

    def ans(key):
        j = uniq[key]
        try:
            return qa.answer(qmap[j["qid"]], j["context"]), None
        except Exception as e:  # noqa: BLE001
            return None, repr(e)[:300]
    answers = dict(zip(keys, map_concurrent(ans, keys, workers=workers, progress="answer")))
    jkeys = sorted({(qid, a[0]) for (qid, _), a in answers.items() if a[0] is not None})

    def jud(key):
        qid, pred = key
        try:
            return qa.judged(qmap[qid], pred), None
        except Exception as e:  # noqa: BLE001
            return None, repr(e)[:300]
    judged = dict(zip(jkeys, map_concurrent(jud, jkeys, workers=workers, progress="judge")))
    rows = []
    for j in jobs:
        q = qmap[j["qid"]]
        pred, err = answers[(j["qid"], sha(j["context"]))]
        jc, jerr = judged.get((j["qid"], pred), (None, None)) if pred is not None else (None, None)
        rows.append({"cell": j["cell"], "conv": j["conv"], "qid": j["qid"],
                     "category": q.category, "prediction": pred, "judge_correct": jc,
                     "f1": official_score(q.category, pred, q.answer) if pred is not None else None,
                     "error": err or jerr, "kept": j["kept"], "context_sha": sha(j["context"])})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("dry", "mock", "paid"), required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    run_dir = Path(a.run).resolve()
    run_dir.mkdir(parents=True, exist_ok=False if a.mode == "paid" else True)
    convs_by_id = {c.sample_id: c for c in load_locomo(REPO / "data" / "locomo" / "locomo10.json")}

    from sentence_transformers import SentenceTransformer
    import torch
    torch.set_num_threads(4)
    model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

    def encode(texts):
        return model.encode(list(texts), batch_size=128, convert_to_numpy=True,
                            normalize_embeddings=True)

    t0 = time.time()
    jobs1, scen1, prompts = build_cells(convs_by_id, 1, encode)
    est1 = estimate(jobs1, prompts, convs_by_id)
    jobs2, scen2, _ = build_cells(convs_by_id, 2, encode)
    est2 = estimate(jobs2, prompts, convs_by_id)
    draws = 2 if est2["nominal_usd"] <= DRAWS_RULE_USD else 1
    jobs, scen = (jobs2, scen2) if draws == 2 else (jobs1, scen1)
    meta = {"mode": a.mode, "draws": draws, "estimate_draws1": est1, "estimate_draws2": est2,
            "data_sha256": hashlib.sha256((REPO / "data/locomo/locomo10.json").read_bytes()).hexdigest(),
            "build_seconds": round(time.time() - t0)}
    (run_dir / "scenarios.json").write_text(json.dumps(scen, indent=1, default=list))
    print(json.dumps(meta, indent=1), flush=True)
    if a.mode == "dry":
        (run_dir / "meta.json").write_text(json.dumps(meta, indent=1))
        return
    if a.mode == "mock":
        client = MockClient()
        qa = LoCoMoQA(client, "mock", client, "mock", prompts)
    else:
        agent, judge = paid_clients(run_dir)
        qa = LoCoMoQA(agent, MODEL, judge, MODEL, prompts)
    rows = run(jobs, qa, convs_by_id, a.workers)
    with (run_dir / "outcomes.jsonl").open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    meta["seconds"] = round(time.time() - t0)
    meta["errors"] = sum(r["error"] is not None for r in rows)
    if a.mode == "paid":
        from ams.llm.budget import BudgetGuard
        meta["budget_snapshot"] = {k: str(v) for k, v in BudgetGuard(
            run_dir / "budget_guard.sqlite", limit_usd=LIMIT_USD).snapshot().items()}
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps({k: meta[k] for k in ("seconds", "errors")}), flush=True)


if __name__ == "__main__":
    main()
