"""LoCoMo v2 supplementary analysis (reports/LOCOMO_V2_SUPPLEMENTARY_ANALYSIS_NOTE.md).

Written and hashed BEFORE unblinding. It never changes a primary decision of the frozen
`locomo_v2.analysis` (protocol §8-9); it adds, for the same primary contrasts:
  S1  exact confidence intervals by inverting the two-sided sign-flip test (n = 8 conversations);
  S2  per-conversation values, sign counts and a forest plot;
  S3  retrieval-vs-answer agreement (exposure vs ASR, evidence recall vs judge accuracy);
  S4  the all-10-conversation secondary analysis (protocol §8), via the frozen `analyse` function;
  S5  the protocol §10 validity checks the frozen code does not apply itself:
      chance ASR > 0.05 flags a primary cell; a confirmed utility contrast must keep its sign under F1.
Free: reads build + answers/judgements; no model call. Usage (WSL):
  python -m locomo_v2_supp.supplementary --run DIR [--build DIR] [--out DIR]
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np

from locomo_v1.analysis import _jsonl
from locomo_v2 import analysis as A
from locomo_v2 import config as K

RETRIEVAL_OF = {"asr": "exposure", "relay_asr": "relay_exposure", "acc_U_out": "recall_U_out",
                "acc_U_all": "recall_U_all", "acc_U_ext": "recall_U_ext"}
F1_OF = {"acc_U_out": "f1_U_out", "acc_U_all": "f1_U_all", "acc_U_ext": "f1_U_ext"}


def _signs(n):
    return np.array(list(itertools.product((1, -1), repeat=n)))


def signflip_two_sided(d, theta=0.0, signs=None):
    x = np.asarray(d, float) - theta
    signs = _signs(len(x)) if signs is None else signs
    obs = abs(x.mean())
    return float(np.mean(np.abs((signs * x).mean(1)) >= obs - 1e-12))


def exact_ci(d, level=0.95, grid=4001):
    """{theta : two-sided sign-flip p(d - theta) > 1 - level}; reports the achieved coverage."""
    d = [x for x in d if x is not None]
    if len(d) < 2:
        return None
    signs = _signs(len(d))
    lo, hi = min(d), max(d)
    span = max(hi - lo, 1e-9)
    ths = np.linspace(lo - span, hi + span, grid)
    keep = [t for t in ths if signflip_two_sided(d, t, signs) > 1 - level]
    if not keep:
        return None
    return {"ci": [round(float(min(keep)), 4), round(float(max(keep)), 4)], "n": len(d),
            "note": "two-sided exact sign-flip inversion; coverage >= nominal on the 2^n lattice"}


def per_conversation(vals, convs, part):
    metric, fam, variants, auds, a, b, direction, margin = part
    out = {}
    for c in convs:
        xa = A.conv_value(vals, c, fam, variants, auds, a, metric)
        xb = A.conv_value(vals, c, fam, variants, auds, b, metric)
        out[c] = None if xa is None or xb is None else round(xa - xb, 4)
    return out


def supplementary(build: Path, run: Path, out: Path):
    pred = {(r["qid"], r["ctx"]): r["prediction"] for r in _jsonl(run / "answers.jsonl")}
    corr = {(r["qid"], r["prediction"]): r["correct"] for r in _jsonl(run / "judgements.jsonl")}
    vals = A.values(build, K.HELDOUT, pred, corr)
    published = sorted({k[6] for k in vals} & {*K.FREE_PUBLISHED, *K.PAID_PUBLISHED})
    spec = A.hypotheses_spec(published)
    primary = json.loads((run / "analysis.json").read_text())["hypotheses"] if (run / "analysis.json").exists() else {}
    rows = []
    for h, parts in spec.items():
        for part in parts:
            metric, fam, variants, auds, a, b, direction, margin = part
            d = per_conversation(vals, K.HELDOUT, part)
            xs = [v for v in d.values() if v is not None]
            ret = RETRIEVAL_OF.get(metric)
            dr = per_conversation(vals, K.HELDOUT, (ret, *part[1:])) if ret else {}
            agree = [np.sign(d[c]) == np.sign(dr[c]) for c in d if d[c] is not None and dr.get(c) is not None]
            f1 = F1_OF.get(metric)
            df1 = per_conversation(vals, K.HELDOUT, (f1, *part[1:])) if f1 else {}
            f1s = [v for v in df1.values() if v is not None]
            chance = {}
            if metric in ("asr", "relay_asr"):
                for arm in (a, b):
                    cv = [A.conv_value(vals, c, fam, variants, auds, arm, "chance_asr") for c in K.HELDOUT]
                    cv = [x for x in cv if x is not None]
                    chance[arm] = round(float(np.mean(cv)), 4) if cv else None
            rows.append({
                "hypothesis": h, "metric": metric, "family": fam, "variants": list(variants),
                "contrast": f"{a} - {b}", "direction": direction, "margin": margin,
                "primary_decision": (primary.get(h) or {}).get("reject"),
                "per_conversation": d,
                "favourable": sum((v > margin) if direction == "gt" else (v < margin) for v in xs), "n": len(xs),
                "mean": round(float(np.mean(xs)), 4) if xs else None,
                "exact_ci95": exact_ci(xs),
                "retrieval_metric": ret, "retrieval_per_conversation": dr,
                "retrieval_answer_sign_agreement": f"{sum(agree)}/{len(agree)}" if agree else None,
                "f1_mean": round(float(np.mean(f1s)), 4) if f1s else None,
                "f1_same_sign": (None if not f1s or not xs else bool(np.sign(np.mean(f1s)) == np.sign(np.mean(xs)))),
                "chance_asr": chance,
                "chance_flag": any(v is not None and v > 0.05 for v in chance.values()),
            })
    out.mkdir(parents=True, exist_ok=True)
    (out / "supplementary.json").write_text(json.dumps({"label": "SUPPLEMENTARY (pre-registered note); primary decisions unchanged",
                                                        "rows": rows}, indent=1, default=str))
    all10 = A.analyse(build, run, K.CONVS)  # protocol §8 secondary; the frozen function, separate file
    (out / "analysis_all10_secondary.json").write_text(json.dumps(all10, indent=1, default=str))
    forest(rows, out / "forest_primary.png")
    return rows


def forest(rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 0.5 * len(rows) + 1.5))
    for y, r in enumerate(rows):
        xs = [v for v in r["per_conversation"].values() if v is not None]
        ax.scatter(xs, [y] * len(xs), s=14, color="#888888", zorder=2)
        if r["mean"] is not None:
            ax.scatter([r["mean"]], [y], s=40, color="#1f3b73", zorder=3)
        if r["exact_ci95"]:
            ax.plot(r["exact_ci95"]["ci"], [y, y], color="#1f3b73", lw=2, zorder=1)
        ax.axvline(0, color="#cccccc", lw=0.8)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f"{r['hypothesis']}: {r['metric']} {r['contrast']}" for r in rows], fontsize=8)
    ax.set_xlabel("paired difference per held-out conversation (grey), mean and exact 95% CI (blue)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--build", type=Path, default=K.REPO / "research_data" / "locomo_v2" / "build")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    rows = supplementary(a.build, a.run, a.out or a.run / "supplementary")
    for r in rows:
        print(r["hypothesis"], r["metric"], r["contrast"], r["favourable"], "/", r["n"], r["exact_ci95"] and r["exact_ci95"]["ci"],
              "ret-ans", r["retrieval_answer_sign_agreement"], "F1 same sign", r["f1_same_sign"], "chance flag", r["chance_flag"])


if __name__ == "__main__":
    main()
