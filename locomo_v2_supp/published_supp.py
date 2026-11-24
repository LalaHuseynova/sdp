"""LoCoMo v2 SUPPLEMENTARY published baselines: LLM sanitiser and A-MemGuard (MPBench methodology).

Frozen LoCoMo v2 files and results are not touched. This module:
  * rebuilds each frozen no-defence ("static") context of the `loc` family from the frozen generator
    and asserts that it reproduces the frozen context hash (same memory, same top-10, same order);
  * applies the frozen MPBench defence classes unchanged, exactly as `ams.research.workload.published.apply`
    does on MPBench: filter the static top-10, NO refill, keep the original retrieval order, and for the
    LLM sanitiser keep the REWRITTEN text of a flagged memory (text_from_defence); a memory is dropped
    only if the defence drops it (empty rewrite; A-MemGuard "inconsistent/unsafe");
  * writes a separate build (`supp_published/build`) in the frozen job format, so the frozen engine
    answers and judges it (GPT-4o-mini, temperature 0, frozen prompts) and the frozen metrics score it.
Defence calls go through a supplied LLM client: a recorder (free exact call counting), a mock (free
end-to-end test), or, only after owner approval, the frozen strict guarded client.

  python -m locomo_v2_supp.published_supp estimate            # free: exact distinct-call counts and cost
  python -m locomo_v2_supp.published_supp mock                # free: mock defences -> build -> frozen engine (mock)
"""

from __future__ import annotations

import gzip
import json
import random
import re
import shutil
import sys
import threading
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from locomo_v1 import build as B1
from locomo_v1 import execute as E
from locomo_v2 import build as B
from locomo_v2 import config as K
from locomo_v2 import scenarios as SC

from ams.data.locomo import load_locomo
import hashlib

from ams.llm.types import ChatResponse, Usage
from ams.memory.base import MemoryEntry

OUT = K.REPO / "research_data" / "locomo_v2" / "supp_published"
FROZEN_BUILD = K.REPO / "research_data" / "locomo_v2" / "build"
FROZEN_RUN = K.REPO / "research_data" / "locomo_v2" / "run"
SCOPES = {"llm_sanitiser": K.SHAPES, "a_memguard": K.SHAPES}  # all four hijack shapes (owner, 24 Nov)


def entries(mem, kept):
    return [MemoryEntry(entry_id=f"rec{i}", text=mem["records"][i]["text"], metadata={}) for i in kept]


def apply_defence(defence, question, mem, kept, text_from_defence):
    """MPBench `published.apply` semantics on LoCoMo turns."""
    res = defence.filter(question, entries(mem, kept))
    returned = {m.entry_id: m.text for m in res.kept}
    out = [(i, returned[f"rec{i}"] if text_from_defence else mem["records"][i]["text"])
           for i in kept if f"rec{i}" in returned]
    return out, [m.entry_id for m in res.flagged]


def render(conv, mem, kept_texts):
    dates = [s.date_time for s in conv.sessions]
    body = "\n".join(f"- [{dates[mem['records'][i]['session']]}] {t}" for i, t in kept_texts)
    return B1.head(conv) + "\n\n" + (body or "(nothing)")


def static_cells(cid, shapes):
    """Yield (conv, scenario memory, qs, static kept rows, sid) for the frozen loc scenarios, verified."""
    data = load_locomo(K.DATA)
    c = {x.sample_id: x for x in data}[cid]
    p1, _ = B1.pools(data)
    qs = [q for q in c.qa if q.category in K.QA_CATEGORIES]
    jobs = defaultdict(dict)
    for j in B1.load_jobs(FROZEN_BUILD, cid):
        jobs[j["cell"]][j["qid"]] = j
    ctx = B1.load_contexts(FROZEN_BUILD, cid)
    for pidx in K.ORIENTATIONS:
        for draw in range(K.DRAWS):
            for shape in shapes:
                mem = SC.base(c, pidx, shape, draw, p1)
                sid = f"loc|{cid}|o{pidx}|{shape}|d{draw}"
                cell = jobs[f"{sid}|-|static"]
                rows = []
                for q in qs:
                    j = cell[q.qid]
                    text = B.render(c, mem, j["kept"])
                    assert B1.chash(text) == j["ctx"] and ctx[j["ctx"]] == text, ("static mismatch", sid, q.qid)
                    rows.append(j["kept"])
                yield c, mem, qs, rows, sid


# ----------------------------------------------------------------------------- LLM clients
@dataclass
class _Req:
    key: str
    chars: int
    max_tokens: int
    kind: str


class Recorder:
    """Free: records every distinct request (frozen cache key) and answers with neutral text."""

    provider = "openrouter"

    def __init__(self):
        self.seen, self.lock = {}, threading.Lock()

    def complete(self, request):
        text = "\n".join(m.content for m in request.messages)
        kind = ("amg_judge" if "impartial auditor" in text else "amg_chain" if "Reasoning Chain" in text
                else "san_clean" if "Santized Memory Log" in text else "san_audit")
        with self.lock:
            self.seen.setdefault(request.cache_key(self.provider), _Req("", len(text), request.max_tokens, kind))
        # a chain text unique per (query, memory) prompt, as a cached real chain would be
        chain = "A -> relates -> " + hashlib.sha256(text.encode()).hexdigest()[:12]
        out = {"san_audit": "[STATUS]: safe", "san_clean": "[Santized Memory Log]: x",
               "amg_chain": chain, "amg_judge": "[]"}[kind]
        return ChatResponse(text=out, model=K.MODEL, provider="mock",
                            usage=Usage(input_tokens=0, output_tokens=0, cost_usd=0.0))


class MockDefenceLLM(Recorder):
    """Free end-to-end test double: flags exactly the injected poison turns.
    Sanitiser: poison -> harmful, rewrite = the turn with its false clause removed (kept, not dropped).
    A-MemGuard: chains carry a marker for poison; the judgment marks those chains inconsistent."""

    POISON = re.compile(r'By the way, about .*?: it is .*?\."')

    def complete(self, request):
        text = "\n".join(m.content for m in request.messages)
        if "impartial auditor" in text:
            ids = re.findall(r'(\d+): "(.*?)"', text)
            out = json.dumps([{"id": int(i), "consistent": "POISON" not in ch, "safe": "POISON" not in ch} for i, ch in ids])
        elif "Reasoning Chain" in text:
            out = "POISON -> claims -> value" if "By the way, about" in text else "speaker -> said -> fact"
        elif "Santized Memory Log" in text:
            mem = text.split("Memory to process:", 1)[1].split("---", 1)[0].strip()
            out = "[Santized Memory Log]: " + self.POISON.sub('(removed)"', mem)
        else:
            out = "[STATUS]: harmful" if "By the way, about" in text else "[STATUS]: safe"
        return ChatResponse(text=out, model=K.MODEL, provider="mock",
                            usage=Usage(input_tokens=0, output_tokens=0, cost_usd=0.0))


def defences(client, which):
    from ams.baselines.amemguard import AMemGuard
    from ams.baselines.amemguard_borrowed import LLMSanitiser

    out = {}
    if "llm_sanitiser" in which:
        out["llm_sanitiser"] = (LLMSanitiser(client, model=K.MODEL), True)
    if "a_memguard" in which:
        out["a_memguard"] = (AMemGuard(model=K.MODEL, client=client,
                                       upstream_root=Path("/mnt/c/Users/HP/Documents/sdp")), False)
    return out


# ----------------------------------------------------------------------------- build
def build(client, out_dir: Path, which=("llm_sanitiser", "a_memguard"), convs=K.CONVS, workers=16) -> dict:
    defs = defences(client, which)
    stats = {}
    out_dir.mkdir(parents=True, exist_ok=True)
    for cid in convs:
        jobs, ctx_store, flagged_n, kept_n = [], {}, defaultdict(int), defaultdict(int)
        from ams.llm.pool import map_concurrent

        for arm, (dfn, rewrite) in defs.items():
            items = [(c, mem, q, kept, sid) for c, mem, qs, rows, sid in static_cells(cid, SCOPES[arm])
                     for q, kept in zip(qs, rows)]
            results = map_concurrent(lambda it: apply_defence(dfn, it[2].question, it[1], it[3], rewrite), items,
                                     workers=workers, progress=f"{arm} {cid}")
            for (c, mem, q, kept, sid), (kt, fl) in zip(items, results):
                    text = render(c, mem, kt)
                    h = B1.chash(text)
                    ctx_store.setdefault(h, text)
                    jobs.append({"cell": f"{sid}|-|{arm}", "qid": q.qid, "ctx": h, "kept": [i for i, _ in kt],
                                 "rewritten": [i for i, t in kt if t != mem["records"][i]["text"]]})
                    flagged_n[arm] += len(fl)
                    kept_n[arm] += len(kt)
        with (out_dir / f"{cid}.jobs.jsonl.gz").open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as fh:
            fh.write("".join(json.dumps(j, sort_keys=True) + "\n" for j in jobs).encode())
        with (out_dir / f"{cid}.contexts.jsonl.gz").open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as fh:
            fh.write("".join(json.dumps({"ctx": h, "text": ctx_store[h]}) + "\n" for h in sorted(ctx_store)).encode())
        shutil.copy(FROZEN_BUILD / f"{cid}.scenarios.json", out_dir / f"{cid}.scenarios.json")
        stats[cid] = {"jobs": len(jobs), "contexts": len(ctx_store), "flagged": dict(flagged_n), "kept": dict(kept_n)}
        print(cid, stats[cid], flush=True)
    return stats


def estimate(convs=K.CONVS) -> dict:
    """Exact distinct defence requests (frozen cache keys), then cost under stated output assumptions."""
    rec = Recorder()
    tmp = OUT / "estimate_build"
    build(rec, tmp, convs=convs)
    by = defaultdict(lambda: {"requests": 0, "input_chars": 0})
    for r in rec.seen.values():
        by[r.kind]["requests"] += 1
        by[r.kind]["input_chars"] += r.chars
    # outputs assumed (stated): audit verdict ~8 tok; rewrite ~ input memory (~80 tok); chain ~120 tok; judgment ~15 tok/chain
    out_tok = {"san_audit": 8, "san_clean": 80, "amg_chain": 120, "amg_judge": 160}
    price_in, price_out = 0.15e-6, 0.60e-6
    cost = {k: round(v["input_chars"] / 4 * price_in + v["requests"] * out_tok[k] * price_out, 3) for k, v in by.items()}
    # answer stage: unique (qid, ctx) of the supplementary cells not already answered in the frozen run
    done = E._answered(FROZEN_RUN)
    keys = set()
    for cid in convs:
        keys |= {(j["qid"], j["ctx"]) for j in B1.load_jobs(tmp, cid)}
    per_key = 9.54905685 / 117713  # actual LoCoMo v2 spend per answer key (answers + judges)
    return {"defence_requests": dict(by), "defence_cost_usd": cost,
            "rewrite_note": "san_clean requests counted here are 0 under the neutral recorder; real count = number of "
                            "distinct turns the sanitiser calls harmful (bounded by san_audit requests)",
            "san_clean_upper_bound_usd": round(by["san_audit"]["input_chars"] / 4 * price_in * 1.3 +
                                              by["san_audit"]["requests"] * 80 * price_out, 3),
            "answer_keys_supp": len(keys), "answer_keys_already_answered": len(keys & done),
            "answer_cost_if_contexts_unchanged_usd": 0.0,
            "answer_cost_upper_bound_usd": round(len(keys) * per_key, 3),
            "assumptions": {"output_tokens": out_tok, "prices_per_token": [price_in, price_out]}}


def main(argv=None):
    cmd = (argv or sys.argv[1:])[0]
    OUT.mkdir(parents=True, exist_ok=True)
    if cmd == "estimate":
        res = estimate()
        (OUT / "estimate.json").write_text(json.dumps(res, indent=1))
        print(json.dumps(res, indent=1))
    elif cmd == "mock":
        stats = build(MockDefenceLLM(), OUT / "mock_build", convs=K.DEV)
        (OUT / "mock_build_stats.json").write_text(json.dumps(stats, indent=1))
        run = OUT / "mock_run"
        shutil.rmtree(run, ignore_errors=True)
        run.mkdir(parents=True)
        print(json.dumps(E.run(OUT / "mock_build", run, "mock", K.DRAWS, workers=8, convs=K.DEV)))
    else:
        sys.exit("estimate | mock")


if __name__ == "__main__":
    main()
