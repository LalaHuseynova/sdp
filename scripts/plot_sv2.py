#!/usr/bin/env python3
"""Plots for the S v2 dev evaluation (retrieval exposure only). Reads sv2_analysis.json.

    plot_sv2.py --dir research_data/sv2_exposure_dev_v3_<date>
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SERIES = [  # validated 8-slot categorical palette, fixed order
    ("C", "C", "#2a78d6", "s"),
    ("M", "M", "#eb6834", "^"),
    ("S", "S v1", "#1baf7a", "o"),
    ("S2-ID", "S2-ID (S + lineage + ID gate)", "#eda100", "D"),
    ("S2-BS", "S2-BS (S + lineage + batch scope)", "#e87ba4", "P"),
    ("a_memguard", "A-MemGuard", "#008300", "X"),
    ("memlineage", "MemLineage", "#6250d6", "v"),
]
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e6e5df"


def style(ax, title, ylabel, xlabel):
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    ax.set_ylabel(ylabel, fontsize=9, color=MUTED)
    ax.set_xlabel(xlabel, fontsize=9, color=MUTED)
    ax.set_ylim(-0.03, 1.03)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)


def panel(ax, table, fams, xs, metric):
    span = (max(xs) - min(xs)) or 1
    for i, (arm, label, color, marker) in enumerate(SERIES):
        ys = [table[f].get(arm, {}).get(metric) for f in fams]
        ax.plot([x + (i - 3) * 0.01 * span for x in xs], ys, color=color, linewidth=2,
                marker=marker, markersize=8, label=label, markeredgecolor="white",
                markeredgewidth=1.2)  # fmt: skip


def fig3(table, specs, fname, title, out, ylabel="unaudited attack exposure"):
    fig, axes = plt.subplots(1, len(specs), figsize=(4.6 * len(specs), 3.9), sharey=True)
    for ax, (fams, xs, metric, sub, xlabel) in zip(axes, specs, strict=True):
        panel(ax, table, fams, xs, metric)
        style(ax, sub, ylabel if ax is axes[0] else "", xlabel)
        ax.set_xticks(xs)
    axes[-1].legend(fontsize=8, frameon=False, loc="center left", bbox_to_anchor=(1.0, 0.5))
    fig.suptitle(title, fontsize=11, color=INK, x=0.01, ha="left")
    fig.text(0.01, 0.01, "Retrieval exposure on 8 dev groups (random rows: 6 draws per group); "
             "not answer-level ASR.", fontsize=8, color=MUTED)  # fmt: skip
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(out / fname, dpi=160, facecolor="white")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, required=True)
    args = ap.parse_args()
    t = json.loads((args.dir / "sv2_analysis.json").read_text())["table"]
    ks, rs = (1, 2, 4, 8), (0, 1, 2, 3, 4)
    own = lambda k: "sybil_k1" if k == 1 else f"sybilown_k{k}"  # noqa: E731
    fig3(t, [([f"sybil_k{k}" for k in ks], ks, "unaudited_exposure",
              "Sybils in the seeds' batch (oracle)", "Sybil identities k"),
             ([own(k) for k in ks], ks, "unaudited_exposure",
              "Sybils in their own batches (oracle)", "Sybil identities k"),
             ([f"launder_r{n}_rand" for n in rs], [n / 4 for n in rs], "unaudited_exposure",
              "Laundering, random detection", "laundered fraction r")],
         "sv2_exposure.png", "S v2 candidates: attack exposure (lower is better)", args.dir)
    fig3(t, [([f"sybil_k{k}" for k in ks], ks, "utility", "Sybil k (oracle)", "k"),
             ([f"launder_r{n}_rand" for n in rs], [n / 4 for n in rs], "utility",
              "Laundering, random detection", "r")],
         "sv2_utility.png", "S v2 candidates: legitimate utility (higher is better)", args.dir,
         ylabel="utility exposure")  # fmt: skip
    # Innocent contributor's utility in the collateral conditions.
    conds = ["framing_concentrated", "cohabit_x1", "cohabit_x1_rand"]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    w = 0.11
    for i, (arm, label, color, _) in enumerate(SERIES):
        ys = [t[c].get(arm, {}).get("utility[innocent]", 0) for c in conds]
        ax.bar([j + (i - 3) * (w + 0.01) for j in range(len(conds))], ys, width=w, color=color,
               label=label, edgecolor="white", linewidth=2)  # fmt: skip
    ax.set_xticks(range(len(conds)))
    ax.set_xticklabels(["framing (concentrated)", "cohabit (oracle)", "cohabit (random)"])
    style(ax, "Innocent contributor's utility under collateral attacks (higher is better)",
          "innocent utility exposure", "")  # fmt: skip
    ax.legend(fontsize=8, frameon=False, loc="center left", bbox_to_anchor=(1.0, 0.5))
    fig.tight_layout()
    fig.savefig(args.dir / "sv2_innocent.png", dpi=160, facecolor="white")
    print("written")


if __name__ == "__main__":
    main()
