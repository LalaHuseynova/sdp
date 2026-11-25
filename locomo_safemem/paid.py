"""Paid stages (refuse to run without `owner_approval.json` naming the frozen manifest digest).

  P1a construct   SAFE-Mem extraction + use-type classifier requests (exact list from the dry pass)
  P1c conflicts   SAFE-Mem query-time conflict checks (exact list from the free precompute pass)
  P2  defences    A-MemGuard + LLM sanitiser on Original SAFE-Mem's static contexts (loc stores)
  P3  answers     answers + judges of every final context (the verified LoCoMo v2 runner, unchanged)

Every stage: GPT-4o-mini via OpenRouter, the frozen strict client (`locomo_v1.execute._strict_client`:
response cache before any reservation, frozen retry policy), its own strict budget guard on WSL
ext4 (`FixedCeilingGuard`; unknown holds never released), the attempt-level circuit breaker and STOP
file of `locomo_v2_supp.runner`, automatic resume through the free OpenRouter probe (at most 5), and
replay of every cached response at $0 on a rerun.
"""

from __future__ import annotations

import gzip
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from locomo_v1 import execute as E
from locomo_v2_supp import runner as RN

from ams.research.dynamic.models import check

from locomo_safemem import config as K
from locomo_safemem import freeze as FZ
from locomo_safemem import run as R

RUN = R.ROOT / "run"
STATE = Path.home() / ".locomo_safemem_state"
APPROVAL = R.ROOT / "owner_approval.json"
STAGES = {"construct": "construction_cache.sqlite", "conflicts": "conflict_cache.sqlite",
          "defences": "defence_cache.sqlite"}


def gate(stage: str) -> dict:
    """The approval must name the verified manifest digest and a cap for the stage."""
    check(APPROVAL.exists(), "refused: no owner approval file")
    a = json.loads(APPROVAL.read_text())
    m = FZ.verify()
    check(m["ok"], f"refused: frozen files changed: {m['changed'][:5]}")
    check(a.get("digest") == m["digest"], "refused: approval does not name the frozen manifest digest")
    check(stage in a.get("caps_usd", {}), f"refused: no approved cap for stage {stage}")
    return a


def log(**rec):
    RUN.mkdir(parents=True, exist_ok=True)
    rec = {"utc": datetime.now(UTC).isoformat(timespec="seconds"), **rec}
    with (RUN / "paid_log.jsonl").open("a") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(json.dumps(rec), flush=True)


def _client(stage, cap, sdk_client=None, state=STATE, run=RUN):
    from ams.llm import ResponseCache
    from ams.llm.budget import BudgetGuard

    if sdk_client is None:
        E._env_key()
    state.mkdir(parents=True, exist_ok=True)
    run.mkdir(parents=True, exist_ok=True)
    guard = E.FixedCeilingGuard(BudgetGuard(state / f"{stage}_guard.sqlite", limit_usd=str(cap)))
    br = RN.Breaker(run / "STOP")
    return br.wrap(E._strict_client(guard, ResponseCache(run / STAGES[stage]), f"lsm_{stage}", sdk_client)), br, guard


def fetch(stage: str, rows: list[dict], cap, workers=16, sdk_client=None, probe_fn=RN.probe, wait_s=60,
          max_auto=RN.MAX_AUTO_RESUMES, state=STATE, run=RUN) -> dict:
    """Send every request once (cache hits are free); pause/resume safe."""
    from ams.llm.pool import map_concurrent

    client, br, guard = _client(stage, cap, sdk_client, state, run)
    stop = run / "STOP"
    stop.unlink(missing_ok=True)
    reqs = [R.req_from(r) for r in rows]
    auto = 0
    while True:
        br.reason = None
        try:
            map_concurrent(client.complete, reqs, workers=workers, progress=f"lsm {stage}")
            log(event="stage_complete", stage=stage, requests=len(reqs))
            return {"status": "complete", "stage": stage, "requests": len(reqs)}
        except Exception as exc:  # noqa: BLE001
            if br.reason == "stop_requested" or stop.exists():
                stop.unlink(missing_ok=True)
                log(event="paused_by_user", stage=stage)
                return {"status": "paused_by_user", "stage": stage}
            auto += 1
            log(event="breaker_tripped", stage=stage, error=type(exc).__name__, attempt=auto)
            if auto > max_auto:
                return {"status": "paused_api_errors", "stage": stage}
            while not probe_fn():
                time.sleep(wait_s)


# ----------------------------------------------------------------------------- P2 defences
def defences(build: Path, cap, which=K.PAID_PUBLISHED, convs=K.CONVS, workers=16, sdk_client=None,
             state=STATE, run=RUN, client=None) -> dict:
    """Frozen A-MemGuard / LLM sanitiser on the exported static contexts (`published.apply`: no
    refill, original order; the sanitiser keeps its rewrites). Appends their jobs to the build."""
    from ams.core.prompts import PromptLibrary
    from ams.data.locomo import load_locomo
    from ams.llm.pool import map_concurrent
    from ams.research.workload import published as P
    from locomo_v1 import build as B1
    from locomo_v2_supp import published_supp as PS

    from locomo_safemem import evaluate as EV

    if client is None:
        client, br, guard = _client("defences", cap, sdk_client, state, run)
    defs = PS.defences(client, which)
    prompts = PromptLibrary()
    data = {c.sample_id: c for c in load_locomo(K.DATA)}
    added = 0
    for cid in convs:
        path = build / f"{cid}.static_loc.json.gz"
        if not path.exists():
            continue
        with gzip.open(path, "rt") as fh:
            exports = json.load(fh)
        c = data[cid]
        jobs, ctxs = [], {}
        for arm, (dfn, rewrite) in defs.items():
            work = [(x, qid) for x in exports for qid in sorted(x["static"])]
            res = map_concurrent(
                lambda w, dfn=dfn, rewrite=rewrite: P.apply(dfn, {"record_owner": w[0]["owner"]}, {"public": w[0]["public"]},
                                                            w[0]["questions"][w[1]], w[0]["static"][w[1]],
                                                            text_from_defence=rewrite)["kept_entries"],
                work, workers=workers, progress=f"{arm} {cid}")
            for (x, qid), kept in zip(work, res):
                text = EV._context(prompts, c, kept)
                h = B1.chash(text)
                ctxs.setdefault(h, text)
                for d in x["draws"]:
                    jobs.append({"cell": f"{x['family']}|{cid}|o{x['pidx']}|{x['variant']}|d{d}|-|{arm}", "qid": qid,
                                 "ctx": h, "kept": [e["entry_id"] for e in kept]})
        _append_build(build, cid, jobs, ctxs)
        added += len(jobs)
    return {"status": "complete", "jobs_added": added}


def _append_build(build: Path, cid: str, jobs: list, ctxs: dict) -> None:
    def rd(name):
        with gzip.open(build / f"{cid}.{name}.jsonl.gz", "rt") as fh:
            return [json.loads(x) for x in fh if x.strip()]

    old = rd("jobs")
    cells = {j["cell"] for j in jobs}
    old = [j for j in old if j["cell"] not in cells]  # idempotent rerun
    allc = {r["ctx"]: r["text"] for r in rd("contexts")}
    allc.update(ctxs)
    from locomo_safemem import evaluate as EV

    metas = json.loads((build / f"{cid}.stores.json").read_text())
    EV.write_build(build, cid, old + jobs, allc, metas)


# ----------------------------------------------------------------------------- P3 answers
def answers(build: Path, cap, convs=RN.ORDER, sdk_client=None, run=None, state=STATE) -> dict:
    """The verified v2 runner (STOP, breaker, S2, journal repair), unchanged, on this study's build."""
    run = run or RUN / "answers"
    return RN.run(run, state, build, gate=False, convs=convs, cap=str(cap), sdk_client=sdk_client)
