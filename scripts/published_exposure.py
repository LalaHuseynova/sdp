#!/usr/bin/env python3
"""Free dev exposure of published defences under the existing Sybil-k / laundering-r sweep.

    published_exposure.py --out research_data/published_exposure_dev_v3_<date> [--groups ...]

Reuses, unchanged: the dev v3 Stage-1 stores, the sweep's 66 conditions, seeds,
audit tickets and per-probe strata (`research_data/adaptive_sweeps_dev_v3_20261112`).

Per group it:
  1. retrieves every probe with original SAFE-Mem (static arm). Static retrieval
     ignores provenance and audits, so it is identical in all 66 conditions; this
     is re-checked here against the sweep's static rows (must match exactly);
  2. runs RandEC (local DistilBERT, free) on those contexts -> arm `randec`;
  3. for every condition, retrieves with R (audited records withheld for their
     own use) and runs RandEC on that -> arm `randec+R` (our labelled composition);
  4. records, for MemLineage, whether any retrieved entry is untrusted under its
     coarse labels (needs no model) -> once the SensitiveAction verdicts exist,
     MemLineage's exposure is fixed exactly (Deny = empty context);
  5. counts (mock, no network) the requests A-MemGuard and the LLM sanitiser would
     send, for a cost estimate.
Each output row copies condition, stratum and audited_itself from the sweep row
of the same (group, condition, probe), so all methods share one experimental grid.
"""

import argparse
import gzip
import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path

from ams.baselines.amemguard_borrowed import RandECClassifier
from ams.baselines.memlineage import Trust, parents_of, propagate
from ams.research.dynamic.models import check
from ams.research.evidence_memoization import memoized_evidence_revisions
from ams.research.provisional_run.runner import resolve_models
from ams.research.recovery.offline import no_network
from ams.research.workload import adaptive as AD
from ams.research.workload import published as P
from ams.research.workload.generator import read_rows
from ams.research.workload.integration import group_rows
from ams.research.workload.runner import prepare_state
from ams.research.workload.stage2 import ConflictPlaceholderSession

BUNDLE = Path("research_data/controlled_workload_v3_20261108")
STAGE1 = Path("research_data/controlled_workload_stage1_dev_v3_20261108")
SWEEP = Path("research_data/adaptive_sweeps_dev_v3_20261112")
RANDEC = Path("third_party/AMemGuard/certified-llm-safety/models/distilbert_suffix.pt")


def load_store(p):
    with gzip.open(p, "rt") as f:
        return json.load(f)


class CountingClient:
    """Mock LLM: records prompt sizes, replies with a fixed placeholder. No network."""

    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def complete(self, request):
        from ams.llm.types import ChatResponse, Usage

        self.calls.append({"chars": sum(len(m.content) for m in request.messages),
                           "max_tokens": request.max_tokens})  # fmt: skip
        return ChatResponse(self.reply, request.model, "mock", Usage(0, 0, 0.0))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--groups", nargs="*")
    args = ap.parse_args()
    check(not args.out.exists(), "Output directory exists; never overwritten")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    rows = read_rows(BUNDLE)
    sweep_meta = json.loads((SWEEP / "summary.json").read_text())
    conditions = [c for c in sweep_meta["conditions"] if not c.startswith("replica_")]
    sweep = defaultdict(dict)  # (g, c, probe) -> {arm: row}
    for line in gzip.open(SWEEP / "exposure_rows.jsonl.gz", "rt"):
        r = json.loads(line)
        if r["condition"] in conditions and r["arm"] in ("static", "R"):
            sweep[(r["group_id"], r["condition"], r["probe_id"])][r["arm"]] = r
    stores = [load_store(p) for p in sorted((STAGE1 / "stores").glob("*.json.gz"))]
    check(all(s["group_id"].startswith("G-D") for s in stores), "Dev split only")
    if args.groups:
        stores = [s for s in stores if s["group_id"] in args.groups]
    out_rows, checks, costs = [], Counter(), Counter()
    session = ConflictPlaceholderSession()
    t0 = time.time()
    with no_network():
        randec = RandECClassifier(weights=RANDEC)
    verdict_cache = {}

    def randec_filter(store, group, q, entries):
        texts = [e["text"] for e in entries]
        for t in texts:
            if t not in verdict_cache:
                verdict_cache[t] = randec.harmful(t + "\n")
        kept = [e for e in entries if not verdict_cache[e["text"]]]
        return kept, [e["entry_id"] for e in entries if verdict_cache[e["text"]]]

    from ams.baselines.amemguard import AMemGuard
    from ams.baselines.amemguard_borrowed import LLMSanitiser
    from ams.research.recovery.offline import CHAT_MODEL

    with no_network(), memoized_evidence_revisions():
        for store in stores:
            gid = store["group_id"]
            group = group_rows(rows, gid)
            static = prepare_state(store["snapshots"]["localized"], [], "static")
            resolve_models(static, session)
            ctx = {}
            for probe in group["probes"]:
                q = probe["question"]
                entries = P.retrieve(static, store, q)
                base = P.exposure_row(store, group, probe, entries)
                ref = sweep[(gid, "localized", probe["probe_id"])]["static"]
                same = (base["target_in_context"], base["carrier_record_in_context"]) == (
                    ref["target_in_context"], ref["carrier_record_in_context"])  # fmt: skip
                checks["static_match"] += same
                checks["static_checked"] += 1
                kept, flagged = randec_filter(store, group, q, entries)
                mems = P.memory_entries(store, group, entries)
                labels = [propagate([(t, 1.0) for _, t in parents_of(m)], 0.0) for m in mems]
                untrusted = any(t >= Trust.DERIVED_UNTRUSTED for t in labels)
                ctx[probe["probe_id"]] = {
                    "randec": P.exposure_row(store, group, probe, kept),
                    "randec_flagged": len(flagged),
                    "untrusted": untrusted,
                    "static": base,
                    "n_entries": len(entries),
                }
                # Cost counting for the paid published methods (mock replies, no network).
                amg_client = CountingClient("[STATUS]: consistent")
                try:
                    AMemGuard(model=CHAT_MODEL, client=amg_client).filter(q, mems)
                except Exception:  # noqa: BLE001 - mock reply may not parse; calls are counted
                    pass
                costs["a_memguard_calls"] += len(amg_client.calls)
                costs["a_memguard_prompt_chars"] += sum(c["chars"] for c in amg_client.calls)
                san_client = CountingClient("[STATUS]: safe")
                LLMSanitiser(san_client, model=CHAT_MODEL).filter(q, mems)
                costs["sanitiser_audit_calls"] += len(san_client.calls)
                costs["sanitiser_prompt_chars"] += sum(c["chars"] for c in san_client.calls)
                costs["memlineage_sensitive_queries"] += 1
            costs["distinct_queries"] += len({p["question"] for p in group["probes"]})
            for condition in conditions:
                ext = AD.extend_store(rows, store, [condition]) if condition != "localized" else store
                audits = ext["audits"][condition]
                rstate = prepare_state(ext["snapshots"][condition], audits, "R")
                resolve_models(rstate, session)
                for probe in group["probes"]:
                    pid = probe["probe_id"]
                    sw = sweep[(gid, condition, pid)]
                    entries = P.retrieve(rstate, store, probe["question"])
                    rexp = P.exposure_row(store, group, probe, entries)
                    checks["R_match"] += (rexp["target_in_context"]
                                          == sw["R"]["target_in_context"])  # fmt: skip
                    checks["R_checked"] += 1
                    kept, _ = randec_filter(store, group, probe["question"], entries)
                    c = ctx[pid]
                    common = {k: sw["static"][k] for k in ("group_id", "condition", "probe_id",
                              "kind", "contribution_id", "stratum", "audited_itself")}  # fmt: skip
                    for arm, e in (("randec", c["randec"]),
                                   ("randec+R", P.exposure_row(store, group, probe, kept))):
                        out_rows.append({**common, "arm": arm, **e})
                    out_rows.append({**common, "arm": "memlineage_inputs",
                                     "static_target_in_context": c["static"]["target_in_context"],
                                     "static_carrier_in_context":
                                         c["static"]["carrier_record_in_context"],
                                     "untrusted_in_context": c["untrusted"]})  # fmt: skip
            print(f"{gid} done, {len(out_rows)} rows, {time.time() - t0:.0f}s", flush=True)
    check(checks["static_match"] == checks["static_checked"], f"Static mismatch {checks}")
    check(checks["R_match"] == checks["R_checked"], f"R mismatch {checks}")
    args.out.mkdir(parents=True)
    with gzip.open(args.out / "published_rows.jsonl.gz", "wt") as f:
        for r in out_rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    summary = {
        "status": "complete", "paid_calls": 0, "groups": [s["group_id"] for s in stores],
        "conditions": conditions, "rows": len(out_rows), "consistency_checks": dict(checks),
        "randec_distinct_texts": len(verdict_cache),
        "randec_flagged_texts": sum(verdict_cache.values()),
        "paid_method_request_counts_mock": dict(costs),
        "seconds": round(time.time() - t0),
    }  # fmt: skip
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
