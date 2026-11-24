"""LoCoMo v2 execution readiness (free; no model call; no outcome read).

Checks the freeze, the data, the API-key presence (never printed), a fresh budget-guard state,
and how many v2 answer requests are already in the v1.1 / pilot response caches (cache KEYS only,
opened read-only and immutable; no stored response is read). Writes readiness.json.
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import sqlite3
import sys
from pathlib import Path

from locomo_v1 import build as B1
from locomo_v1 import execute as E
from locomo_v2 import __main__ as CLI
from locomo_v2 import config as K

from ams.core.prompts import PromptLibrary
from ams.data.locomo import load_locomo
from ams.llm import ChatRequest, Message

MAIN = Path("/mnt/c/Users/HP/Documents/sdp")
CACHES = {"v1.1 run": MAIN / "research_data/locomo_v1_run/response_cache.sqlite",
          "pilot": MAIN / "research_data/locomo_pilot_20261119/paid/response_cache.sqlite"}


def cache_keys(path: Path) -> set:
    db = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        return {k for (k,) in db.execute("SELECT key FROM responses")}
    finally:
        db.close()


def main(out: str):
    res = {}
    files = CLI.freeze_files()
    man = json.loads((CLI.FREEZE / "freeze_manifest.json").read_text())
    res["freeze"] = {"digest": man["digest"], "files": len(files),
                     "verified": files == man["files"],
                     "recomputed": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()}
    res["data_sha256_ok"] = hashlib.sha256(K.DATA.read_bytes()).hexdigest() == K.DATA_SHA256
    env = K.REPO / ".env"
    res["api_key_present_in_worktree_env"] = env.exists() and any(
        ln.split("=", 1)[0].strip() == "OPENROUTER_API_KEY" and ln.split("=", 1)[1].strip()
        for ln in env.read_text().splitlines() if "=" in ln)
    run = CLI.OUT / "run"
    live = CLI.STATE / run.name / "budget_guard.sqlite"
    res["guard"] = {"run_dir_exists": run.exists(), "live_ledger_exists": live.exists(),
                    "state_dir": str(CLI.STATE), "cap_usd": K.CAP_USD,
                    "fresh_start": not run.exists() and not live.exists()}
    res["approval_signed"] = (CLI.FREEZE / "owner_approval.json").exists()

    # cache coverage of v2's answer requests (exactly the request LoCoMoQA.answer builds)
    prompts = PromptLibrary(K.REPO / "prompts")
    tpl = prompts.get("locomo_qa")
    qmap = {q.qid: q for c in load_locomo(K.DATA) for q in c.qa}
    keys = {name: cache_keys(p) for name, p in CACHES.items() if p.exists()}
    total = covered = 0
    chars_all = chars_left = 0
    by_conv = {}
    for cid in K.CONVS:
        ctx = B1.load_contexts(CLI.BUILD, cid)
        jobs = {(j["qid"], j["ctx"]) for j in B1.load_jobs(CLI.BUILD, cid) if E.selected(j, K.DRAWS)}
        hit = 0
        for qid, h in jobs:
            qa = qmap[qid]
            q = qa.question + (" Use DATE of CONVERSATION to answer with an approximate date." if qa.category == 2 else "")
            text = tpl.render(context=ctx[h], question=q)
            key = ChatRequest(messages=(Message("user", text),), model=K.MODEL, temperature=0.0,
                              max_tokens=32).cache_key("openrouter")
            ok = any(key in ks for ks in keys.values())
            hit += ok
            chars_all += len(text)
            chars_left += 0 if ok else len(text)
        by_conv[cid] = {"answer_requests": len(jobs), "in_cache": hit}
        total += len(jobs)
        covered += hit

    def usd(chars, n):  # the frozen estimator (locomo_v1.execute.estimate), calibrated
        raw = (chars / 4 * 0.15 + n * 32 * 0.60 + n * 160 * 0.15 + n * 4 * 0.60) / 1e6
        return round(raw, 3), round(raw * E.K.PILOT_CALIBRATION, 3)

    res["cache"] = {"caches": {n: len(k) for n, k in keys.items()}, "answer_requests": total,
                    "answer_requests_in_cache": covered, "per_conversation": by_conv,
                    "note": "keys only; judge requests depend on predictions and are not counted"}
    res["cost_usd"] = {"no_reuse_raw_calibrated": usd(chars_all, total),
                       "with_cache_reuse_raw_calibrated": usd(chars_left, total - covered),
                       "cap": K.CAP_USD}
    res["disk_free_gb"] = round(shutil.disk_usage(K.REPO).free / 1e9, 1)
    import numpy
    import sentence_transformers
    import torch
    res["environment"] = {"python": sys.version.split()[0], "platform": platform.platform(),
                          "numpy": numpy.__version__, "torch": torch.__version__,
                          "sentence_transformers": sentence_transformers.__version__}
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "cache"} | {"cache": {x: res["cache"][x] for x in
                      ("caches", "answer_requests", "answer_requests_in_cache")}}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
