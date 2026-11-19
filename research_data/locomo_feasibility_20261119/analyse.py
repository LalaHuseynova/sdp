"""Summarise feasibility.json: means over draws per conversation, then over conversations;
S - C and S - M contrasts with a percentile bootstrap over the 10 conversations (clusters)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent
d = json.loads((OUT / "feasibility.json").read_text())
rows = d["results"]
METRICS = ("poison_exposure", "recall_hijacked_out", "recall_hijacked_in", "recall_principal",
           "avail_hijacked_out", "avail_hijacked_in")


def conv_means(sel, metric):
    by = defaultdict(list)
    for r in sel:
        v = r.get(metric)
        if v is not None:
            by[r["conv"]].append(v)
    return {c: float(np.mean(v)) for c, v in by.items()}


def boot(diff_by_conv, n=10000, seed=1):
    convs = sorted(diff_by_conv)
    x = np.array([diff_by_conv[c] for c in convs])
    if len(x) == 0:
        return None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n, len(x)))
    m = x[idx].mean(axis=1)
    return [round(float(x.mean()), 3), round(float(np.percentile(m, 2.5)), 3),
            round(float(np.percentile(m, 97.5)), 3)]


index = defaultdict(list)
for r in rows:
    index[(r["hijack"], r["m"], r["k_audit"], r["k"], r["arm"])].append(r)

summary = {}
for (h, m, ka, k, arm), sel in sorted(index.items()):
    summary[f"{h}|m{m}|a{ka}|k{k}|{arm}"] = {
        mt: (round(float(np.mean(list(conv_means(sel, mt).values()))), 3)
             if conv_means(sel, mt) else None) for mt in METRICS}

contrasts = {}
for (h, m, ka, k, arm), sel in sorted(index.items()):
    if arm != "S":
        continue
    for other in ("C", "M", "R", "static"):
        o = index[(h, m, ka, k, other)]
        for mt in ("poison_exposure", "recall_hijacked_out", "recall_hijacked_in"):
            a, b = conv_means(sel, mt), conv_means(o, mt)
            common = {c: a[c] - b[c] for c in a if c in b}
            contrasts[f"{h}|m{m}|a{ka}|k{k}|S-{other}|{mt}"] = boot(common)

mech = defaultdict(list)
for x in d["mechanism"]:
    mech[(x["hijack"], x["m"], x["k"])].append(x)
mech_sum = {f"{h}|m{m}|a{k}": {
    "unsafe_found_mean": round(float(np.mean([x["unsafe_found"] for x in v])), 2),
    "safe_found_mean": round(float(np.mean([x["safe_found"] for x in v])), 2),
    "share_S_context_gate_active": round(float(np.mean([x["s_context_active"] for x in v])), 3),
    "mean_sessions_with_S_batch_gate": round(float(np.mean([x["s_batch_sessions"] for x in v])), 2),
    "lineage_blocked_mean": round(float(np.mean([x["lineage_blocked"] for x in v])), 2)}
    for (h, m, k), v in sorted(mech.items())}

(OUT / "summary.json").write_text(json.dumps({"summary": summary, "contrasts": contrasts,
                                              "mechanism": mech_sum}, indent=1))
print(json.dumps(mech_sum, indent=1))
for key in sorted(summary):
    if "|k10|" in key:
        print(key, summary[key])
for key in sorted(contrasts):
    if "|k10|" in key and ("S-C|" in key or "S-M|" in key):
        print(key, contrasts[key])
