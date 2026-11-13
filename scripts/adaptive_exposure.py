#!/usr/bin/env python3
"""Free exposure evaluation of adaptive-attack conditions (no model call, $0).

    adaptive_exposure.py --bundle research_data/controlled_workload_v3_20261108 \
        --stage1 research_data/controlled_workload_stage1_dev_v3_20261108 \
        --out research_data/adaptive_exposure_dev_v3_<date>

For every (group, condition, arm, probe) it runs the frozen governed retrieval
over the real Stage-1 stores and records whether the probed attack target or
utility fact reaches the supplied context, and why candidates were withheld.
Conflict checks (which cannot change selection) get the logged Stage-2
placeholder. Answers and judges are NOT produced: exposure is the ceiling that
the paid Stage 3 converts into ASR/utility. Sanity: the replica conditions must
reproduce the stored localized/distributed audits and exposure exactly.
Dev split only; refuses the test split.
"""

import argparse
import gzip
import json
import os
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from ams.research.dynamic.models import canonical, check
from ams.research.evidence_memoization import memoized_evidence_revisions
from ams.research.provisional_run.runner import resolve_models
from ams.research.recovery.offline import no_network
from ams.research.retrieval import RetrievalContext
from ams.research.workload import adaptive as AD
from ams.research.workload import lineage as LN
from ams.research.workload import sv2 as SV2
from ams.research.workload.generator import read_rows
from ams.research.workload.integration import group_rows, use_id
from ams.research.workload.runner import MEMORY_ARMS, exposure, prepare_state
from ams.research.workload.stage2 import ConflictPlaceholderSession

REPLICAS = ("replica_localized", "replica_distributed")


def load_store(path):
    with gzip.open(path, "rt") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--stage1", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--draws", type=int, default=AD.DEFAULT_DRAWS)
    ap.add_argument("--groups", nargs="*")
    ap.add_argument("--arms", nargs="*", default=list(MEMORY_ARMS),
                    help="memory arms; lineage arms RL/CL/ML/SL wrap R/C/M/S")
    ap.add_argument("--conditions", nargs="*", help="default: all (incl. replicas)")
    ap.add_argument("--sweeps", action="store_true",
                    help="evaluate only the Sybil-k / laundering-r sweeps (+ localized, replicas)")
    ap.add_argument("--tau", type=float, default=LN.DEFAULT_TAU)
    ap.add_argument("--verdicts", type=Path,
                    default=Path("research_data/published_paid_dev_v3_20261112/"
                                 "sensitive_action_verdicts.json"),
                    help="recorded MemLineage SensitiveAction verdicts (S2-ID, S2-ALL)")
    args = ap.parse_args()
    check(not args.out.exists(), "Output directory exists; never overwritten")
    rows = read_rows(args.bundle)
    paths = sorted((args.stage1 / "stores").glob("*.json.gz"))
    stores = [load_store(p) for p in paths]
    check(all(s["group_id"].startswith("G-D") for s in stores), "Dev split only")
    if args.groups:
        stores = [s for s in stores if s["group_id"] in args.groups]
    conditions = (*REPLICAS, *AD.all_conditions(args.draws))
    evaluated = ("localized", "distributed", "uninformative", *conditions)
    if args.sweeps:
        conditions = (*REPLICAS, *AD.sweep_conditions(args.draws))
        evaluated = ("localized", *conditions)
    if args.conditions:
        evaluated = tuple(args.conditions)
        conditions = tuple(c for c in evaluated if c not in ("localized", "distributed",
                                                             "uninformative"))
    replicas = [r for r in REPLICAS if r in conditions]
    for a in args.arms:
        check(a in MEMORY_ARMS or a in LN.LINEAGE_ARMS or a in SV2.CANDIDATES,
              f"Unknown arm {a}")
    sensitive = None
    if any(SV2.CANDIDATES.get(a, {}).get("id_gate") for a in args.arms):
        sensitive = SV2.RecordedVerdicts(json.loads(args.verdicts.read_text()))
    lineage_info = []
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    session = ConflictPlaceholderSession()
    out_rows, sanity = [], []
    t0 = time.time()
    with no_network(), memoized_evidence_revisions():
        for store in stores:
            gid = store["group_id"]
            group = group_rows(rows, gid)
            ext = AD.extend_store(rows, store, conditions)
            for rep in replicas:
                stored = store["audits"][rep.split("_", 1)[1]]
                same = canonical(ext["audits"][rep]) == canonical(stored)
                sanity.append({"group": gid, "replica": rep, "audits_identical": same})
                check(same, f"{gid} {rep}: replica audits differ from the stored ones")
            for condition in evaluated:
                strata = ext["strata"].get(condition, {})
                for arm in args.arms:
                    base_arm = "S" if arm in SV2.CANDIDATES else LN.LINEAGE_ARMS.get(arm, arm)
                    state = prepare_state(
                        ext["snapshots"][condition], ext["audits"][condition], base_arm
                    )
                    resolve_models(state, session)
                    if arm in SV2.CANDIDATES:
                        info = SV2.apply(state, store, arm, tau=args.tau, sensitive=sensitive)
                        lineage_info.append({"group": gid, "condition": condition,
                                             "arm": arm, **info})
                    if arm in LN.LINEAGE_ARMS:
                        info = LN.apply(state, store["session_id"], args.tau)
                        lineage_info.append({"group": gid, "condition": condition,
                                             "arm": arm, **info})
                    for probe in group["probes"]:
                        pid = probe["probe_id"]
                        priv = group["private_probes"][pid]
                        q = probe["question"]
                        ctx = RetrievalContext(
                            state.evidence, state.access, use_id(gid, q), "user", "read"
                        )
                        res = state.reader().retrieve_with_trace(
                            session_id=store["session_id"], query=q, context=ctx, k=4,
                            principal="user",
                        )  # fmt: skip
                        entries = [asdict(e) for e in res.retrieval.entries]
                        e = exposure(entries, store["record_owner"], priv, priv.get("aliases"))
                        out_rows.append(
                            {
                                "group_id": gid,
                                "condition": condition,
                                "arm": arm,
                                "probe_id": pid,
                                "kind": priv["kind"],
                                "contribution_id": priv["contribution_id"],
                                "stratum": strata.get(pid, priv["strata"].get(condition)),
                                "audited_itself": priv["contribution_id"]
                                in ext["unsafe_audited"].get(condition, ()),
                                **e,
                            }
                        )
            print(f"{gid} done, {len(out_rows)} rows, {time.time() - t0:.0f}s", flush=True)
    # Replica exposure must equal the stored condition's exposure, row by row.
    idx = {(r["group_id"], r["condition"], r["arm"], r["probe_id"]): r for r in out_rows}
    mismatch = 0
    for (g, c, a, p), r in idx.items():
        if c in REPLICAS and (g, c.split("_", 1)[1], a, p) in idx:
            ref = idx[(g, c.split("_", 1)[1], a, p)]
            mismatch += (r["target_in_context"], r["carrier_record_in_context"]) != (
                ref["target_in_context"],
                ref["carrier_record_in_context"],
            )
    check(mismatch == 0, f"{mismatch} replica exposure rows differ")
    args.out.mkdir(parents=True)
    with gzip.open(args.out / "exposure_rows.jsonl.gz", "wt") as f:
        for r in out_rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    summary = {
        "status": "complete",
        "paid_calls": 0,
        "groups": [s["group_id"] for s in stores],
        "conditions": list(evaluated),
        "arms": args.arms,
        "tau": args.tau,
        "lineage": lineage_info,
        "rows": len(out_rows),
        "conflict_checks_answered_by_placeholder": session.conflicts,
        "sanity": {"replica_audits": sanity, "replica_exposure_mismatches": mismatch},
        "seconds": round(time.time() - t0),
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("sanity", "lineage")},
                     indent=2))


if __name__ == "__main__":
    main()
