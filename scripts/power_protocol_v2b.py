#!/usr/bin/env python3
"""Revised protocol-v2 power analysis (free, offline, read-only). Supersedes v2a.

    power_protocol_v2b.py --out research_data/protocol_v2_draft_20261113/power_analysis_v2b.json

Changes from v2a (owner review, 13 Nov 2026):
1. Testing procedure identical to the protocol: 8 primary contrasts under Holm. Power is
   computed at the Holm worst-case step, alpha = 0.05/8 one-sided (a lower bound on Holm
   power); joint ("and") hypotheses are intersection-union tests, each component at that
   level, power = P(all components pass).
2. No single exposure->ASR factor. ASR is generated from exposure with calibrated
   probabilities measured in our real-answer data (target-specific ASR):
     q  = P(success | target in context):  locked test v1 0.75-0.79, dev paid 0.55-0.65
          -> grid q in {0.55, 0.65, 0.80}
     p0 = P(success | target not in context): 0.00-0.09 -> grid p0 in {0.00, 0.05}
   Relay: q_relay in {0.60, 0.95}.
3. Effect-size sensitivity: every dev-measured difference is scaled by lambda in
   {1.0, 0.75, 0.5, 0.25} (winner's curse: methods were designed on dev); hypotheses
   without dev data (H6) use explicit grids.
4. H2 evaluated at the 5-point non-inferiority margin over a between-group SD grid.
5. Groups are simulated as independent clusters, which the revised protocol makes true
   by construction (no document shared between held-out groups).
6. A percentile cluster-bootstrap check (the protocol's actual CI) is run for key cells.
Data used: per-group dev exposure rows (8 groups) and locked test v1 per-group results
(24 groups), both already reported. No held-out data exists.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import power_protocol_v2 as P  # noqa: E402  (data loaders of v2a)

ALPHA, K = 0.05, 8
A1 = ALPHA / K  # Holm worst-case step, one-sided
SIMS = 4000
NS = (48, 64, 96, 128)
QS, P0S, LAMBDAS = (0.55, 0.65, 0.80), (0.0, 0.05), (1.0, 0.75, 0.5, 0.25)
HARD = ["sybil_k4", "sybilown_k4", "launder_r4", "launder_r3_rand", "sybilown_k4_rand"]
PUBLISHED = ("a_memguard", "memlineage", "llm_sanitiser", "randec")
ATTACKS_PER_GROUP = 4


def tbound(x, side):
    """One-sided t bound at A1 over the group axis (last axis)."""
    n = x.shape[-1]
    m, s = x.mean(-1), x.std(-1, ddof=1)
    h = stats.t.ppf(1 - A1, n - 1) * s / np.sqrt(n)
    return m + h if side == "upper" else m - h


def asr_from_exposure(rng, exp_rate, q, p0, n_items=ATTACKS_PER_GROUP):
    """Group ASR given per-group exposure probability (vectorised over sims x groups)."""
    exposed = rng.binomial(n_items, np.clip(exp_rate, 0, 1))
    hits = rng.binomial(exposed, q) + rng.binomial(n_items - exposed, p0)
    return hits / n_items


def resample_groups(rng, values, n):
    """values: array (G,) or (G, k) of dev groups -> (SIMS, n[, k]) resampled clusters."""
    idx = rng.integers(0, len(values), size=(SIMS, n))
    return values[idx]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rng = np.random.default_rng(20261113)
    per = P.exposure_per_group()
    test = P.outcomes(P.TEST_V1)
    groups = sorted(per[("localized", "S", "unaudited_exposure")])

    def vec(fam, arm, key="unaudited_exposure"):
        return np.array([per[(fam, arm, key)][g] for g in groups])

    def hard(arm):
        return np.array([np.mean([per[(f, arm, "unaudited_exposure")][g] for f in HARD])
                         for g in groups])  # fmt: skip

    out = {"definitions": __doc__, "alpha_one_sided": A1, "sims": SIMS, "results": {}}
    R = out["results"]

    # H1: S - C (and S - M) strict key-stratum utility > +0.03, joint with ASR NI < +0.05.
    key = "same_contributor_context_other_batch"
    d1 = np.array(P.delta(P.group_metric(test, "localized", "S", "utility", True, key),
                          P.group_metric(test, "localized", "C", "utility", True, key)))
    da = np.array(P.delta(P.group_metric(test, "localized", "S", "attack"),
                          P.group_metric(test, "localized", "C", "attack")))  # fmt: skip
    R["H1 (each of 2 contrasts)"] = {}
    for lam in LAMBDAS:
        for n in NS:
            u = resample_groups(rng, d1, n) * lam
            a = resample_groups(rng, da, n) + rng.normal(0, 0.05, size=(SIMS, n))  # answer noise
            ok = (tbound(u, "lower") > 0.03) & (tbound(a, "upper") < 0.05)
            R["H1 (each of 2 contrasts)"][f"lambda={lam},N={n}"] = round(ok.mean(), 3)

    # H2: S - M ASR (distributed) non-inferiority, margin +0.05; true delta and SD grid.
    R["H2 (NI margin 0.05)"] = {}
    for true in (0.0, 0.02):
        for sd in (0.0, 0.05, 0.10, 0.15):
            for n in NS:
                x = true + rng.normal(0, max(sd, 1e-9), size=(SIMS, n))
                ok = tbound(x, "upper") < 0.05
                R["H2 (NI margin 0.05)"][f"true={true},sd={sd},N={n}"] = round(ok.mean(), 3)

    # H3: intersection-union, S - P_j < 0 for every published method (target ASR).
    S_loc = vec("localized", "S")
    pubs = np.stack([vec("localized", p) for p in PUBLISHED], axis=1)  # (G, 4)
    R["H3 (IUT over 4 published)"] = {}
    for q in QS:
        for p0 in P0S:
            for lam in LAMBDAS:
                for n in NS:
                    idx = rng.integers(0, len(groups), size=(SIMS, n))
                    s_exp = S_loc[idx]
                    ok = np.ones(SIMS, bool)
                    for j in range(len(PUBLISHED)):
                        p_exp = s_exp + lam * (pubs[idx, j] - s_exp)
                        d = (asr_from_exposure(rng, s_exp, q, p0)
                             - asr_from_exposure(rng, p_exp, q, p0))  # fmt: skip
                        ok &= tbound(d, "upper") < 0
                    R["H3 (IUT over 4 published)"][f"q={q},p0={p0},lambda={lam},N={n}"] = round(
                        ok.mean(), 3)

    # H4: S2-ID - S target ASR over hard families < 0, joint utility NI > -0.05.
    s_h, id_h = hard("S"), hard("S2-ID")
    u4 = vec("localized", "S2-ID", "utility") - vec("localized", "S", "utility")
    R["H4 (ASR superiority AND utility NI)"] = {}
    for q in QS:
        for p0 in P0S:
            for lam in LAMBDAS:
                for n in NS:
                    idx = rng.integers(0, len(groups), size=(SIMS, n))
                    s_exp = s_h[idx]
                    i_exp = s_exp + lam * (id_h[idx] - s_exp)
                    # 5 families x 4 attacks = 20 attack items per group
                    d = (asr_from_exposure(rng, i_exp, q, p0, 20)
                         - asr_from_exposure(rng, s_exp, q, p0, 20))  # fmt: skip
                    u = u4[idx] + rng.normal(0, 0.05, size=(SIMS, n))
                    ok = (tbound(d, "upper") < 0) & (tbound(u, "lower") > -0.05)
                    R["H4 (ASR superiority AND utility NI)"][
                        f"q={q},p0={p0},lambda={lam},N={n}"] = round(ok.mean(), 3)

    # H5 primary: relay EXPOSURE SL - S < 0 (1 relay probe per group, binary), joint utility
    # NI; secondary (gatekept): relay target ASR.
    s_rel = vec("localized", "S", "relay")
    sl_rel = vec("localized", "SL", "relay")
    u5 = vec("localized", "SL", "utility") - vec("localized", "S", "utility")
    R["H5 primary: relay exposure AND utility NI"] = {}
    R["H5 secondary: relay target ASR (given primary passes)"] = {}
    for p_s in (0.40, 0.625):          # P(relay reaches context under S)
        for resid in (0.0, 0.10, 0.25):  # SL residual leak probability
            for n in NS:
                es = rng.binomial(1, p_s, size=(SIMS, n))
                esl = rng.binomial(1, resid, size=(SIMS, n))
                u = rng.choice(u5, size=(SIMS, n)) + rng.normal(0, 0.05, size=(SIMS, n))
                prim = (tbound((esl - es).astype(float), "upper") < 0) & (
                    tbound(u, "lower") > -0.05)
                R["H5 primary: relay exposure AND utility NI"][
                    f"pS={p_s},SLleak={resid},N={n}"] = round(prim.mean(), 3)
                for qr in (0.60, 0.95):
                    a_s = es * rng.binomial(1, qr, size=(SIMS, n))
                    a_sl = esl * rng.binomial(1, qr, size=(SIMS, n))
                    sec = prim & (tbound((a_sl - a_s).astype(float), "upper") < 0)
                    R["H5 secondary: relay target ASR (given primary passes)"][
                        f"pS={p_s},SLleak={resid},q_relay={qr},N={n}"] = round(sec.mean(), 3)
    _ = sl_rel  # dev: SL relay exposure 0 in every oracle group (recorded for reference)

    # H6: innocent strict utility S - C (and S - M) > 0 under false-positive audits; no data,
    # explicit grid anchored on the dev framing proxy (+0.158, SD 0.141).
    R["H6 (each of 2 contrasts)"] = {}
    for eff in (0.05, 0.10, 0.158):
        for sd in (0.14, 0.20, 0.25):
            for n in NS:
                x = rng.normal(eff, sd, size=(SIMS, n))
                R["H6 (each of 2 contrasts)"][f"effect={eff},sd={sd},N={n}"] = round(
                    (tbound(x, "lower") > 0).mean(), 3)

    # Minimum detectable effect at N=96 (90% power, alpha 0.05/8 one-sided) per SD.
    z = stats.norm.ppf(1 - A1) + stats.norm.ppf(0.90)
    out["MDE_at_N96"] = {f"sd={sd}": round(z * sd / np.sqrt(96), 3)
                         for sd in (0.10, 0.15, 0.20, 0.25, 0.30)}  # fmt: skip

    # Check: percentile cluster bootstrap (the protocol's CI) vs t bound, two key cells.
    def boot_power(make, side, margin, n, sims=500, B=2000):
        ok_b = ok_t = 0
        for _ in range(sims):
            x = make(n)
            bs = x[rng.integers(0, n, size=(B, n))].mean(1)
            if side == "upper":
                ok_b += np.quantile(bs, 1 - A1) < margin
                ok_t += tbound(x[None], "upper")[0] < margin
            else:
                ok_b += np.quantile(bs, A1) > margin
                ok_t += tbound(x[None], "lower")[0] > margin
        return {"bootstrap": round(ok_b / sims, 3), "t": round(ok_t / sims, 3)}

    out["bootstrap_vs_t_check"] = {
        "H6 effect=0.10 sd=0.20 N=96": boot_power(
            lambda n: rng.normal(0.10, 0.20, n), "lower", 0.0, 96),
        "H2 true=0 sd=0.10 N=96": boot_power(
            lambda n: rng.normal(0.0, 0.10, n), "upper", 0.05, 96),
    }
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print("written")


if __name__ == "__main__":
    main()
