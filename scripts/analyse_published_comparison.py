#!/usr/bin/env python3
"""Combine the Sybil-k / laundering-r sweep with the published-defence rows (free).

    analyse_published_comparison.py --out research_data/published_exposure_dev_v3_<date>

Inputs (read-only): the sweep rows (static/R/C/M/S/SL) and the published rows
(randec, randec+R, MemLineage inputs). All metrics are RETRIEVAL EXPOSURE, not
answer-level ASR:
  unaudited_exposure  scored-attack probes whose target reaches the context, over
                      attacks that were not themselves audited
  utility             utility probes whose fact reaches the context
  utility[innocent]   ... the innocent contributor B's notes (in laundering-r, B is
                      the innocent forwarder)
  utility[attacker]   ... the attacker identities' own benign notes
Random-detection draws are averaged within a group; CIs are paired cluster
bootstraps over the 8 dev groups (10,000 resamples, seed 20261112).
MemLineage is reported as exact bounds (see `memlineage` block): its decision is
static exposure on queries its SensitiveAction classifier calls ORDINARY and an
empty context on SENSITIVE ones (when any retrieved memory is untrusted, which
the coarse labels decide without a model).
"""

import argparse
import gzip
import json
import random
import re
from collections import defaultdict
from pathlib import Path

SWEEP = Path("research_data/adaptive_sweeps_dev_v3_20261112/exposure_rows.jsonl.gz")
ARMS = ("static", "R", "C", "M", "S", "SL", "randec", "randec+R", "memlineage", "a_memguard",
        "llm_sanitiser")
PAID = Path("research_data/published_paid_dev_v3_20261112")


def paid_rows(ml):
    """Broadcast paid, condition-invariant published results over the sweep grid.

    MemLineage: Deny (empty context) iff SensitiveAction says SENSITIVE and the
    context holds an untrusted memory (MemLineage.filter); otherwise the static
    context is used unchanged. A-MemGuard / sanitiser: per-probe kept-context
    exposure from `published_paid.py`, for the groups that were run.
    """
    out = []
    common = ("group_id", "condition", "probe_id", "kind", "contribution_id", "stratum",
              "audited_itself")  # fmt: skip
    verdicts_path = PAID / "sensitive_action_verdicts.json"
    if verdicts_path.exists():
        import ams.research.workload.generator as G

        verdicts = json.loads(verdicts_path.read_text())
        rows = G.read_rows(Path("research_data/controlled_workload_v3_20261108"))
        question = {p["probe_id"]: p["question"] for p in rows["public/probes.jsonl"]}
        for r in ml:
            deny = "SENSITIVE" in verdicts[question[r["probe_id"]]].upper() and r[
                "untrusted_in_context"]
            out.append({**{k: r[k] for k in common}, "arm": "memlineage",
                        "target_in_context": False if deny else r["static_target_in_context"],
                        "carrier_record_in_context":
                            False if deny else r["static_carrier_in_context"]})  # fmt: skip
    for method, arm in (("amemguard", "a_memguard"), ("sanitiser", "llm_sanitiser")):
        res = {}
        for f in PAID.glob(f"{method}_G-D*.jsonl"):
            for line in f.read_text().splitlines():
                x = json.loads(line)
                res[(x["group_id"], x["probe_id"])] = x
        for r in ml:
            x = res.get((r["group_id"], r["probe_id"]))
            if x:
                out.append({**{k: r[k] for k in common}, "arm": arm,
                            "target_in_context": x["target_in_context"],
                            "carrier_record_in_context": x["carrier_record_in_context"]})  # fmt: skip
    return out
B, SEED = 10_000, 20261112


def family(c):
    m = re.match(r"(sybil_k\d+|launder_r\d+)(_rand)?", c)
    return (m.group(1) + ("_rand" if m.group(2) else "")) if m else c


def owner(s):
    return s.split(":", 1)[0] if s and ":" in s else ("principal" if s == "principal" else "other")


def boot(d):
    vals = [d[g] for g in sorted(d)]
    rng = random.Random(SEED)
    st = sorted(sum(rng.choice(vals) for _ in vals) / len(vals) for _ in range(B))
    return [round(st[int(0.025 * B)], 3), round(st[int(0.975 * B) - 1], 3)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rows = [json.loads(x) for x in gzip.open(SWEEP, "rt")]
    rows = [r for r in rows if not r["condition"].startswith("replica_")]
    pub = [json.loads(x) for x in gzip.open(args.out / "published_rows.jsonl.gz", "rt")]
    ml = [r for r in pub if r["arm"] == "memlineage_inputs"]
    rows += [r for r in pub if r["arm"] in ARMS]
    rows += paid_rows(ml)
    acc = defaultdict(lambda: [0, 0])
    for r in rows:
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
    def order(f):
        m = re.match(r"(sybil|launder)_[kr](\d+)", f)
        return (0, "", 0, f) if not m else (1, m.group(1), "_rand" in f, int(m.group(2)))

    fams = sorted({f for (f, _, _) in per}, key=order)
    metrics = ("unaudited_exposure", "exposure_all", "utility", "utility[innocent]",
               "utility[attacker]", "unlinked_relay")  # fmt: skip
    table = {f: {a: {k: round(sum(v.values()) / len(v), 3) for k in metrics
                     if (v := per.get((f, a, k)))} for a in ARMS} for f in fams}  # fmt: skip
    contrasts = {}
    for f in fams:
        for k in ("unaudited_exposure", "utility", "utility[innocent]"):
            for y in ("static", "R", "C", "M", "SL", "randec", "randec+R", "memlineage",
                      "a_memguard", "llm_sanitiser"):  # fmt: skip
                gx, gy = per.get((f, "S", k)), per.get((f, y, k))
                if gx and gy:
                    d = {g: gx[g] - gy[g] for g in gx if g in gy}  # paired on common groups
                    contrasts[f"{f}|{k}|S-{y}"] = {"estimate": round(sum(d.values()) / len(d), 3),
                                                   "ci95": boot(d)}  # fmt: skip
    # MemLineage bounds (condition-invariant; computed on the localized grid).
    loc = [r for r in ml if r["condition"] == "localized"]
    att = [r for r in loc if r["kind"] == "attack"]
    utl = [r for r in loc if r["kind"] == "utility"]
    memlineage = {
        "attack_probes_with_untrusted_context": sum(r["untrusted_in_context"] for r in att),
        "attack_probes": len(att),
        "utility_probes_with_untrusted_context": sum(r["untrusted_in_context"] for r in utl),
        "utility_probes": len(utl),
        "static_attack_exposure": round(sum(r["static_target_in_context"] for r in att) / len(att), 3),
        "static_utility_exposure": round(sum(r["static_target_in_context"] for r in utl) / len(utl), 3),
        "rule": "exposure(q) = static exposure(q) if SensitiveAction(q) == ORDINARY else 0 "
                "(Deny), for every condition; invariant to k, r and audit draws",
        "status": "SensitiveAction verdicts not cached for the 216 distinct dev questions; "
                  "exact values need one paid classifier call per question",
    }  # fmt: skip
    coverage = {a: sorted({r["group_id"] for r in rows if r["arm"] == a}) for a in ARMS}
    out = {"definitions": __doc__, "families": fams, "table": table, "contrasts": contrasts,
           "memlineage": memlineage, "groups_per_arm": coverage}  # fmt: skip
    (args.out / "comparison.json").write_text(json.dumps(out, indent=2) + "\n")
    for f in fams:
        print(f"\n{f}\n  arm        unaudExp   util   util[B]  util[A]  relay")
        for a in ARMS:
            t = table[f][a]
            if not t:
                continue
            print(f"  {a:13} {t.get('unaudited_exposure', 0):8.3f} {t.get('utility', 0):6.3f}"
                  f" {t.get('utility[innocent]', 0):8.3f} {t.get('utility[attacker]', 0):8.3f}"
                  f" {t.get('unlinked_relay', 0):6.3f}")  # fmt: skip
    print("\nmemlineage:", json.dumps(memlineage, indent=1))


if __name__ == "__main__":
    main()
