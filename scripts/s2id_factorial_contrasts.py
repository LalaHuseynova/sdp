#!/usr/bin/env python3
"""S2-ID as a 2x2 factorial (EXPLORATORY; not pre-registered; point estimates already seen).

    {no propagation, S + lineage} x {no gate, MemLineage sensitive-action gate}
        static (Original SAFE-Mem) | memlineage
        SL                         | S2-ID

S2-ID = frozen S + frozen lineage (tau 0.8) + the MemLineage Deny gate with the SAME coarse
attribution and the SAME recorded SensitiveAction verdicts as the `memlineage` baseline
(sv2.py, published.py). This script measures, per registered cell, with the protocol's own
paired cluster bootstrap (frozen `analysis.group_values` / `group_weights`, seed 20261114):

  gate | propagation      S2-ID - SL
  propagation | gate      S2-ID - memlineage
  interaction             (S2-ID - SL) - (memlineage - static)
  beats both components   intersection-union: both upper 95% bounds < 0

for target_asr (lower is better) and strict_utility. Every cell with all four arms is
reported (no selection). Holm is applied over all cells for "beats both", as a conservative
descriptive summary; nothing here changes a pre-registered decision.

    python scripts/s2id_factorial_contrasts.py --journal J [J ...] --bundle B --out OUT.json
        [--mpbench data/mpbench/adversarial_data.jsonl.jsonl] [--resamples 10000]

Read-only on the journals; free (no model call). Run where the Option B journals exist.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse_protocol_v2 import families, journal_rows  # noqa: E402

from ams.research.protocol_v2 import analysis as A  # noqa: E402
from ams.research.workload.generator import read_rows  # noqa: E402

ARMS = ("static", "memlineage", "SL", "S2-ID")
METRICS = ("target_asr", "strict_utility")


def summarise(draws, point):
    lo, hi = np.nanpercentile(draws, [2.5, 97.5])
    return {"estimate": point, "ci95": [float(lo), float(hi)],
            "p_below_0": float(np.mean(draws[~np.isnan(draws)] >= 0))}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--journal", type=Path, nargs="+", required=True)
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mpbench", type=Path)
    ap.add_argument("--resamples", type=int, default=A.RESAMPLES)
    args = ap.parse_args(argv)
    if args.out.exists():
        raise SystemExit("refuse to overwrite")
    rows = [r for j in args.journal for r in journal_rows(j / "queries.sqlite" if j.is_dir() else j)]
    idx = A.index(rows, A.probe_info(read_rows(args.bundle), families(args.mpbench)))
    W = A.group_weights(len(idx.groups), A.SEED, args.resamples)
    cells = sorted({c for (_, c, m) in idx.acc if m == "S2-ID"})
    out, pvals = {}, {}
    for cell in cells:
        res = {}
        for metric in METRICS:
            g = {m: A.group_values(idx, metric, [cell], m) for m in ARMS}
            if any(np.all(np.isnan(v)) for v in g.values()):
                continue
            contrasts = {
                "gate_given_propagation": g["S2-ID"] - g["SL"],
                "propagation_given_gate": g["S2-ID"] - g["memlineage"],
                "interaction": (g["S2-ID"] - g["SL"]) - (g["memlineage"] - g["static"]),
            }
            res[metric] = {"points": {m: A._mean(v) for m, v in g.items()},
                           **{k: summarise(A.boot_mean(d, W), A._mean(d)) for k, d in contrasts.items()}}
            if metric == "target_asr":
                a = res[metric]["gate_given_propagation"]
                b = res[metric]["propagation_given_gate"]
                res[metric]["beats_both_iut_p"] = max(a["p_below_0"], b["p_below_0"])
                pvals[cell] = res[metric]["beats_both_iut_p"]
        out[cell] = res
    holm = A.holm(pvals) if pvals else {}
    for cell, h in holm.items():
        out[cell]["target_asr"]["beats_both_holm"] = h
    args.out.write_text(json.dumps({"label": "EXPLORATORY: S2-ID factorial; not pre-registered",
                                    "groups": len(idx.groups), "seed": A.SEED,
                                    "resamples": args.resamples, "cells": out}, indent=1) + "\n")
    print(json.dumps({c: {"S2-ID-SL": v["target_asr"]["gate_given_propagation"]["estimate"],
                          "S2-ID-ML": v["target_asr"]["propagation_given_gate"]["estimate"],
                          "beats_both_p": v["target_asr"].get("beats_both_iut_p")}
                      for c, v in out.items() if "target_asr" in v}, indent=1))


if __name__ == "__main__":
    main()
