#!/usr/bin/env python3
"""Plots for the published-defence comparison (exposure only). Reads comparison.json.

    plot_published_comparison.py --dir research_data/published_exposure_dev_v3_<date>

Writes exposure_vs_k.png, exposure_vs_r.png and utility_vs_k_r.png into --dir.
Small multiples (oracle vs random detection), one y-axis per panel, fixed
categorical order, distinct marker per series (identity never by color alone).
SL equals S on attack exposure in every cell and is omitted; R equals original
SAFE-Mem on unaudited exposure and is omitted; RandEC+R equals R. Published
methods (MemLineage, A-MemGuard, LLM sanitiser) are from the paid runs.
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SERIES = [  # fixed categorical order (validated 8-slot palette, light mode)
    ("static", "Original SAFE-Mem", "#2a78d6", "o"),
    ("C", "C", "#eb6834", "s"),
    ("M", "M", "#1baf7a", "^"),
    ("S", "S (ours)", "#eda100", "D"),
    ("memlineage", "MemLineage", "#e87ba4", "P"),
    ("a_memguard", "A-MemGuard", "#008300", "X"),
    ("llm_sanitiser", "LLM sanitiser", "#6250d6", "v"),
    ("randec", "RandEC", "#e34948", "*"),
]
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e6e5df"


def style(ax, title, ylabel):
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    ax.set_ylabel(ylabel, fontsize=9, color=MUTED)
    ax.set_ylim(-0.03, 1.03)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)


def panel(ax, table, fams, xs, metric, series, offset=True):
    for i, (arm, label, color, marker) in enumerate(series):
        ys = [table[f].get(arm, {}).get(metric) for f in fams]
        if all(y is None for y in ys):
            continue
        jitter = (i - len(series) / 2) * 0.012 if offset else 0
        ax.plot([x + jitter * (max(xs) - min(xs) or 1) for x in xs], ys, color=color,
                linewidth=2, marker=marker, markersize=8, label=label,
                markeredgecolor="white", markeredgewidth=1.2)  # fmt: skip


def figure(table, kind, values, metric, ylabel, fname, out, series, suptitle):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    prefix = "sybil_k" if kind == "k" else "launder_r"
    xs = list(values) if kind == "k" else [n / 4 for n in values]
    for ax, suffix, title in ((axes[0], "", "Oracle detection (4 seeds audited)"),
                              (axes[1], "_rand", "Random detection (6 draws)")):  # fmt: skip
        fams = [f"{prefix}{v}{suffix}" for v in values]
        panel(ax, table, fams, xs, metric, series)
        style(ax, title, ylabel if ax is axes[0] else "")
        ax.set_xticks(xs)
        ax.set_xlabel("Sybil identities k" if kind == "k" else "laundered fraction r",
                      fontsize=9, color=MUTED)  # fmt: skip
    axes[1].legend(fontsize=8, frameon=False, loc="center left", bbox_to_anchor=(1.0, 0.5))
    fig.suptitle(suptitle, fontsize=11, color=INK, x=0.01, ha="left")
    fig.text(0.01, 0.01, "Retrieval exposure on 8 dev groups, not answer-level ASR.",
             fontsize=8, color=MUTED)  # fmt: skip
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(out / fname, dpi=160, facecolor="white")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, required=True)
    args = ap.parse_args()
    table = json.loads((args.dir / "comparison.json").read_text())["table"]
    figure(table, "k", (1, 2, 4, 8), "unaudited_exposure", "unaudited attack exposure",
           "exposure_vs_k.png", args.dir, SERIES,
           "Attack exposure vs number of Sybil identities (lower is better)")  # fmt: skip
    figure(table, "r", (0, 1, 2, 3, 4), "unaudited_exposure", "unaudited attack exposure",
           "exposure_vs_r.png", args.dir, SERIES,
           "Attack exposure vs laundered fraction (lower is better)")  # fmt: skip
    figure(table, "k", (1, 2, 4, 8), "utility", "legitimate utility exposure",
           "utility_vs_k.png", args.dir, SERIES,
           "Legitimate utility vs Sybil identities (higher is better)")  # fmt: skip
    figure(table, "r", (0, 1, 2, 3, 4), "utility[innocent]", "innocent forwarder's utility",
           "innocent_utility_vs_r.png", args.dir, SERIES,
           "Innocent forwarder's utility vs laundered fraction (higher is better)")  # fmt: skip
    print("written")


if __name__ == "__main__":
    main()
