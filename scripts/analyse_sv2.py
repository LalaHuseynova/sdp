#!/usr/bin/env python3
"""S v2 candidates vs S v1, R/C/M and published defences (free; retrieval EXPOSURE only).

    analyse_sv2.py --dir research_data/sv2_exposure_dev_v3_<date>

Row sources (read-only):
  * Sybil-k / laundering-r sweep rows (static/R/C/M/S/SL), 12 Nov;
  * adaptive dev rows (static/R/C/M/S/SL/RL/CL/ML), 12 Nov;
  * <dir>/parts/*: S2-ID / S2-BS / S2-ALL on all of those conditions, plus every
    arm on the new boundary-verification (`_fu`) sweep draws and stress conditions;
  * published defences (condition-invariant, broadcast with each condition's own
    strata): RandEC (free run), MemLineage (recorded SensitiveAction verdicts +
    model-free labels), A-MemGuard and LLM sanitiser (paid per-probe results).
Metrics: unaudited attack exposure, utility, utility[innocent], utility[attacker],
unlinked-relay exposure. Random draws averaged within each group; paired cluster
bootstrap over the 8 dev groups (10,000 resamples, seed 20261112).
"""

import argparse
import gzip
import json
import random
import re
from collections import defaultdict
from pathlib import Path

SWEEP = Path("research_data/adaptive_sweeps_dev_v3_20261112/exposure_rows.jsonl.gz")
ADAPTIVE = Path("research_data/adaptive_exposure_dev_v3_20261112/exposure_rows.jsonl.gz")
PUB = Path("research_data/published_exposure_dev_v3_20261112/published_rows.jsonl.gz")
PAID = Path("research_data/published_paid_dev_v3_20261112")
BUNDLE = Path("research_data/controlled_workload_v3_20261108")
ARMS = ("static", "R", "C", "M", "S", "SL", "S2-ID", "S2-BS", "S2-ALL", "memlineage",
        "a_memguard", "llm_sanitiser", "randec")  # fmt: skip
B, SEED = 10_000, 20261112
COMMON = ("group_id", "condition", "probe_id", "kind", "contribution_id", "stratum",
          "audited_itself")  # fmt: skip


def family(c):
    return re.sub(r"_d\d+", "", c)


def owner(s):
    if s and ":" in s:
        return s.split(":", 1)[0]
    return {"other_contributor": "innocent", "unrelated_source": "unrelated",
            "principal": "principal"}.get(s, "attacker")  # fmt: skip


def boot(d):
    vals = [d[g] for g in sorted(d)]
    rng = random.Random(SEED)
    st = sorted(sum(rng.choice(vals) for _ in vals) / len(vals) for _ in range(B))
    return [round(st[int(0.025 * B)], 3), round(st[int(0.975 * B) - 1], 3)]


def read(path):
    return [json.loads(x) for x in gzip.open(path, "rt")]


def published_per_probe():
    """(group, probe) -> {arm: (target_in_context, carrier_in_context)}."""
    from ams.research.workload.generator import read_rows

    question = {p["probe_id"]: p["question"] for p in read_rows(BUNDLE)["public/probes.jsonl"]}
    verdicts = json.loads((PAID / "sensitive_action_verdicts.json").read_text())
    out = defaultdict(dict)
    for r in read(PUB):
        if r["condition"] != "localized":
            continue
        key = (r["group_id"], r["probe_id"])
        if r["arm"] == "randec":
            out[key]["randec"] = (r["target_in_context"], r["carrier_record_in_context"])
        elif r["arm"] == "memlineage_inputs":
            deny = "SENSITIVE" in verdicts[question[r["probe_id"]]].upper() and r[
                "untrusted_in_context"]
            out[key]["memlineage"] = ((False, False) if deny else
                                      (r["static_target_in_context"],
                                       r["static_carrier_in_context"]))  # fmt: skip
    for method, arm in (("amemguard", "a_memguard"), ("sanitiser", "llm_sanitiser")):
        for f in PAID.glob(f"{method}_G-D*.jsonl"):
            for line in f.read_text().splitlines():
                x = json.loads(line)
                out[(x["group_id"], x["probe_id"])][arm] = (x["target_in_context"],
                                                            x["carrier_record_in_context"])  # fmt: skip
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, required=True)
    args = ap.parse_args()
    rows = {}
    sources = [SWEEP, ADAPTIVE, *sorted((args.dir / "parts").glob("*/exposure_rows.jsonl.gz"))]
    for src in sources:
        for r in read(src):
            if r["condition"].startswith("replica_") or r["arm"] not in ARMS:
                continue
            rows[(r["group_id"], r["condition"], r["arm"], r["probe_id"])] = r
    pub = published_per_probe()
    for (g, c, a, p), r in list(rows.items()):
        if a != "static":
            continue
        for arm, (t, cr) in pub.get((g, p), {}).items():
            rows[(g, c, arm, p)] = {**{k: r[k] for k in COMMON}, "arm": arm,
                                    "target_in_context": t, "carrier_record_in_context": cr}  # fmt: skip
    acc = defaultdict(lambda: [0, 0])
    for r in rows.values():
        f, a, g = family(r["condition"]), r["arm"], r["group_id"]
        hit = bool(r["target_in_context"])
        keys = []
        if r["kind"] == "attack":
            keys.append("exposure_all")
            if not r["audited_itself"]:
                keys.append("unaudited_exposure")
        elif r["kind"] == "utility":
            keys += ["utility", f"utility[{owner(r['stratum'])}]"]
        elif r["kind"] == "copy_unlinked":
            keys.append("unlinked_relay")
        for k in keys:
            acc[(f, a, k, g)][0] += hit
            acc[(f, a, k, g)][1] += 1
    per = defaultdict(dict)
    for (f, a, k, g), (h, n) in acc.items():
        per[(f, a, k)][g] = h / n
    fams = sorted({f for (f, _, _) in per})
    metrics = ("unaudited_exposure", "utility", "utility[innocent]", "utility[attacker]",
               "unlinked_relay")  # fmt: skip
    table = {f: {a: {k: round(sum(v.values()) / len(v), 3) for k in metrics
                     if (v := per.get((f, a, k)))} for a in ARMS} for f in fams}  # fmt: skip
    missing = {f: [a for a in ARMS if not table[f][a]] for f in fams}
    contrasts = {}
    for f in fams:
        for k in ("unaudited_exposure", "utility", "utility[innocent]"):
            for x in ("S2-ID", "S2-BS", "S2-ALL"):
                for y in ("S", "SL", "C", "M", "a_memguard", "memlineage"):
                    gx, gy = per.get((f, x, k)), per.get((f, y, k))
                    if gx and gy:
                        d = {g: gx[g] - gy[g] for g in gx if g in gy}
                        contrasts[f"{f}|{k}|{x}-{y}"] = {
                            "estimate": round(sum(d.values()) / len(d), 3), "ci95": boot(d)}
    # Worst case over attacker strategies per arm (exposure), plain vs follow-up audits.
    def worst(arm, fam_filter):
        vals = {f: table[f][arm].get("unaudited_exposure") for f in fams if fam_filter(f)}
        vals = {f: v for f, v in vals.items() if v is not None}
        f = max(vals, key=vals.get) if vals else None
        return {"family": f, "exposure": vals.get(f)}
    summary = {a: {"worst_plain": worst(a, lambda f: not f.endswith("_fu")),
                   "worst_followup": worst(a, lambda f: f.endswith("_fu")
                                           or not re.search(r"_rand|random_", f))}
               for a in ARMS}  # fmt: skip
    out = {"definitions": __doc__, "families": fams, "table": table, "contrasts": contrasts,
           "missing_arms": {f: m for f, m in missing.items() if m}, "worst_case": summary,
           "rows": len(rows)}  # fmt: skip
    (args.dir / "sv2_analysis.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"rows {len(rows)}; families {len(fams)}")
    for f in fams:
        print(f"\n{f}\n  arm           unaudExp   util  util[B]  util[A]  relay")
        for a in ARMS:
            t = table[f][a]
            if t:
                print(f"  {a:13} {t.get('unaudited_exposure', float('nan')):8.3f} "
                      f"{t.get('utility', float('nan')):6.3f} "
                      f"{t.get('utility[innocent]', float('nan')):7.3f} "
                      f"{t.get('utility[attacker]', float('nan')):7.3f} "
                      f"{t.get('unlinked_relay', float('nan')):6.3f}")  # fmt: skip


if __name__ == "__main__":
    main()
