#!/usr/bin/env python3
"""Power analysis for the protocol-v2 fresh held-out test (free, offline, read-only).

    power_protocol_v2.py --out research_data/protocol_v2_draft_20261113/power_analysis.json

Unit of analysis = test GROUP (cluster): attacks and probes inside a group share
contributors, contexts and audits, so they are dependent. Every hypothesis is a
paired, group-level contrast d_g = metric(method A, g) - metric(method B, g).
Effect sizes and between-group SDs come only from results ALREADY REPORTED:
  * locked test v1 (24 groups, real answers): H1/H2 analogues, attack-level ICC;
  * dev paid adaptive run (8 groups, real answers): random-detection contrasts;
  * dev exposure runs (8 groups): S2-ID vs S, SL vs S, S vs published methods,
    converted to ASR scale where noted.
Nothing here touches a new held-out group (none exist yet).

Power for N groups is estimated by Monte-Carlo (20,000 sims per N): draw N group
deltas (a) by resampling the observed group deltas and (b) from a normal with the
observed mean and SD (inflated x1.25 for estimation uncertainty); test with a
one-sided t-interval at Bonferroni level alpha = 0.05 / 6 (conservative stand-in
for the pre-registered Holm procedure over H1-H6). Reported: power per N, smallest
N with power >= 0.90 under the worse of (a)/(b).
"""

import argparse
import gzip
import json
import random
import sqlite3
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse_sv2 as A  # noqa: E402

TEST_V1 = Path("research_data/controlled_workload_stage3_test_v4_20261108/queries.sqlite")
DEV_PAID = Path("research_data/adaptive_stage3_dev_v3_20261112/queries.sqlite")
SV2 = Path("research_data/sv2_exposure_dev_v3_20261112")
ALPHA, K_HYP, SIMS = 0.05, 6, 10_000
NS = (16, 24, 32, 48, 64, 96, 128, 160)


def outcomes(path):
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        return [json.loads(b) for (b,) in db.execute("SELECT body FROM outcomes")]


def group_metric(rows, cond, arm, kind, strict=False, stratum=None):
    acc = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["condition"] != cond or r["arm"] != arm or r["kind"] != kind:
            continue
        if stratum and r["stratum"] != stratum:
            continue
        hit = bool(r["outcome"])
        if strict:
            hit = hit and bool(r["exposure"] and r["exposure"]["target_in_context"])
        acc[r["group_id"]][0] += hit
        acc[r["group_id"]][1] += 1
    return {g: h / n for g, (h, n) in acc.items()}


def delta(a, b):
    return [a[g] - b[g] for g in sorted(a) if g in b]


def icc_binary(rows, cond, arm, kind):
    """ANOVA estimator of the intra-group correlation of a binary outcome."""
    by = defaultdict(list)
    for r in rows:
        if r["condition"] == cond and r["arm"] == arm and r["kind"] == kind:
            by[r["group_id"]].append(1.0 if r["outcome"] else 0.0)
    groups = list(by.values())
    k = len(groups)
    n = sum(len(x) for x in groups)
    m0 = (n - sum(len(x) ** 2 for x in groups) / n) / (k - 1)
    grand = sum(sum(x) for x in groups) / n
    msb = sum(len(x) * (st.mean(x) - grand) ** 2 for x in groups) / (k - 1)
    msw = sum(sum((v - st.mean(x)) ** 2 for v in x) for x in groups) / (n - k)
    icc = (msb - msw) / (msb + (m0 - 1) * msw) if (msb + (m0 - 1) * msw) else 0.0
    return {"icc": round(icc, 3), "items_per_group": round(n / k, 2),
            "design_effect": round(1 + (n / k - 1) * icc, 3)}  # fmt: skip


SD_FLOOR = 0.10  # answers add noise that exposure / zero-variance cells do not show


def power(deltas, kind, margin, n, rng, shrink=1.0, sd_mult=1.25):
    """kind 'superior': need lower bound > margin; 'noninferior': upper bound < margin.
    `shrink` scales the effect (winner's-curse scenario); SD is floored at SD_FLOOR."""
    a = ALPHA / K_HYP
    tcrit = stats.t.ppf(1 - a, n - 1)
    # Non-inferiority: the true difference stays at its observed value (0 when the two
    # arms decide identically); superiority: the effect is scaled by `shrink`.
    mu = st.mean(deltas) * (1.0 if kind == "noninferior" else shrink)
    sd = max(st.pstdev(deltas), SD_FLOOR) * sd_mult
    centred = [x - st.mean(deltas) for x in deltas]
    scale = sd / max(st.pstdev(centred), 1e-9) if st.pstdev(centred) > 0 else 0.0
    deltas = [mu + x * scale for x in centred] if scale else [mu] * len(deltas)
    if not scale:  # zero observed spread: draw noise from N(0, sd) in both modes
        deltas = [mu + rng.gauss(0, sd) for _ in range(64)]
    res = {}
    for mode in ("resample", "normal"):
        ok = 0
        for _ in range(SIMS):
            x = ([rng.choice(deltas) for _ in range(n)] if mode == "resample"
                 else [rng.gauss(mu, sd) for _ in range(n)])  # fmt: skip
            m, s = st.mean(x), st.stdev(x) if len(set(x)) > 1 else 0.0
            half = tcrit * s / n**0.5
            ok += (m - half > margin) if kind == "superior" else (m + half < margin)
        res[mode] = round(ok / SIMS, 3)
    return min(res.values()), res


def exposure_per_group():
    """Group-level exposure metrics from the dev exposure runs (analyse_sv2 rows)."""
    rows = {}
    for src in [A.SWEEP, A.ADAPTIVE, *sorted((SV2 / "parts").glob("*/exposure_rows.jsonl.gz"))]:
        for r in A.read(src):
            if not r["condition"].startswith("replica_") and r["arm"] in A.ARMS:
                rows[(r["group_id"], r["condition"], r["arm"], r["probe_id"])] = r
    pub = A.published_per_probe()
    for (g, c, a, p), r in list(rows.items()):
        if a == "static":
            for arm, (t, cr) in pub.get((g, p), {}).items():
                rows[(g, c, arm, p)] = {**{k: r[k] for k in A.COMMON}, "arm": arm,
                                        "target_in_context": t, "carrier_record_in_context": cr}
    acc = defaultdict(lambda: [0, 0])
    for r in rows.values():
        f, a, g = A.family(r["condition"]), r["arm"], r["group_id"]
        if r["kind"] == "attack" and not r["audited_itself"]:
            key = "unaudited_exposure"
        elif r["kind"] == "utility":
            key = "utility"
            o = A.owner(r["stratum"])
            if o == "innocent":
                acc[(f, a, "utility[innocent]", g)][0] += bool(r["target_in_context"])
                acc[(f, a, "utility[innocent]", g)][1] += 1
        elif r["kind"] == "copy_unlinked":
            key = "relay"
        else:
            continue
        acc[(f, a, key, g)][0] += bool(r["target_in_context"])
        acc[(f, a, key, g)][1] += 1
    per = defaultdict(dict)
    for (f, a, k, g), (h, n) in acc.items():
        per[(f, a, k)][g] = h / n
    return per


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rng = random.Random(20261113)
    test = outcomes(TEST_V1)
    dev = outcomes(DEV_PAID)
    per = exposure_per_group()
    # ASR / exposure conversion observed for original SAFE-Mem on the locked test.
    conv = 0.771 / 0.969
    hard = ["sybil_k4", "sybilown_k4", "launder_r4", "launder_r3_rand", "sybilown_k4_rand"]

    def per_innocent(fam, arm):
        return per[(fam, arm, "utility[innocent]")]

    def mean_over(fams, arm, key):
        gs = sorted(per[(fams[0], arm, key)])
        return {g: st.mean(per[(f, arm, key)][g] for f in fams) for g in gs}

    hyps = {
        "H1 localized: S - C strict key-stratum utility (superiority, margin +0.03)": (
            delta(group_metric(test, "localized", "S", "utility", True,
                               "same_contributor_context_other_batch"),
                  group_metric(test, "localized", "C", "utility", True,
                               "same_contributor_context_other_batch")),
            "superior", 0.03, "locked test v1 (24 groups, real answers)"),  # fmt: skip
        "H2 distributed: S - M ASR (non-inferiority, margin +0.02)": (
            delta(group_metric(test, "distributed", "S", "attack"),
                  group_metric(test, "distributed", "M", "attack")),
            "noninferior", 0.02, "locked test v1 (24 groups, real answers)"),  # fmt: skip
        "H3 localized: S - best published ASR (superiority, margin 0)": (
            [conv * d for d in delta(per[("localized", "S", "unaudited_exposure")],
                                     per[("localized", "memlineage", "unaudited_exposure")])],
            "superior_neg", 0.0, "dev exposure x ASR/exposure ratio 0.80 (8 groups)"),  # fmt: skip
        "H4 hard families: S2-ID - S ASR (superiority, margin 0)": (
            [conv * d for d in delta(mean_over(hard, "S2-ID", "unaudited_exposure"),
                                     mean_over(hard, "S", "unaudited_exposure"))],
            "superior_neg", 0.0, "dev exposure x 0.80 (8 groups), mean over hard families"),
        "H4b utility: S2-ID - S strict utility (non-inferiority, margin -0.03)": (
            delta(per[("localized", "S2-ID", "utility")], per[("localized", "S", "utility")]),
            "noninferior_neg", -0.03, "dev exposure (8 groups)"),  # fmt: skip
        "H5 relay: SL - S relay ASR (superiority, margin 0)": (
            [conv * d for d in delta(per[("localized", "SL", "relay")],
                                     per[("localized", "S", "relay")])],
            "superior_neg", 0.0, "dev exposure x 0.80 (8 groups; 1 relay probe per group)"),
        "H6 proxy: S - C innocent utility under concentrated framing (superiority, margin 0)": (
            delta(per_innocent("framing_concentrated", "S"), per_innocent("framing_concentrated", "C")),
            "superior", 0.0, "dev exposure (8 groups); proxy for the new imperfect-audit test"),
        "random spread: S - C target ASR (descriptive, real answers)": (
            delta(group_metric(dev, "random_spread_d0", "S", "attack"),
                  group_metric(dev, "random_spread_d0", "C", "attack")),
            "superior", 0.0, "dev paid run, draw 0 (8 groups) - context only"),  # fmt: skip
    }
    out = {"definitions": __doc__, "alpha_per_test": ALPHA / K_HYP, "simulations": SIMS,
           "icc": {"locked_test_static_attack_ASR": icc_binary(test, "localized", "static", "attack"),
                   "locked_test_static_utility": icc_binary(test, "localized", "static", "utility")},
           "hypotheses": {}}  # fmt: skip
    for name, (d, kind, margin, source) in hyps.items():
        # Normalise "lower is better" contrasts to superiority on -d.
        if kind.endswith("_neg"):
            dd, k2 = [-x for x in d], kind.removesuffix("_neg")
            m2 = -margin
        else:
            dd, k2, m2 = d, kind, margin
        rows, pess = {}, {}
        for n in NS:
            p, detail = power(dd, k2, m2, n, rng)
            rows[n] = {"power": p, **detail}
            q, _ = power(dd, k2, m2, n, rng, shrink=0.5, sd_mult=1.5)
            pess[n] = q
        need = next((n for n in NS if rows[n]["power"] >= 0.90), None)
        need_p = next((n for n in NS if pess[n] >= 0.90), None)
        out["hypotheses"][name] = {
            "source": source, "groups_observed": len(d), "mean_delta": round(st.mean(d), 3),
            "sd_delta_between_groups": round(st.pstdev(d), 3), "power_by_groups": rows,
            "min_groups_for_power_0.90": need,
            "pessimistic_power_by_groups (effect x0.5, SD x1.5)": pess,
            "pessimistic_min_groups_for_power_0.90": need_p}  # fmt: skip
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"icc": out["icc"], **{k: {"mean": v["mean_delta"],
          "sd": v["sd_delta_between_groups"], "n90": v["min_groups_for_power_0.90"],
          "power": {n: r["power"] for n, r in v["power_by_groups"].items()}}
          for k, v in out["hypotheses"].items()}}, indent=1))  # fmt: skip


if __name__ == "__main__":
    main()
