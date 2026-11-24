"""Paper figures for the SAFE-Mem results PDF (free; reads analysis/*.json only). Run: uv run python make_figures.py"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
A = HERE.parent / "analysis"
G = json.load(open(A / "analysis.json"))
H = json.load(open(A / "backbone_analysis.json"))
NAME = {"static": "Original", "a_memguard": "A-MemGuard", "memlineage": "MemLineage", "llm_sanitiser": "LLM Sanitiser",
        "randec": "RandEC", "R": "R", "C": "C", "M": "M", "S": "S", "SL": "SL", "S2-ID": "S2-ID"}
# Okabe-Ito colour-blind-safe palette; our methods in strong colours, baselines muted
STYLE = {"static": ("#7a7a7a", "o", "--"), "memlineage": ("#009E73", "s", "--"), "C": ("#E69F00", "^", "-"),
         "M": ("#56B4E9", "v", "-"), "S": ("#0072B2", "o", "-"), "S2-ID": ("#D55E00", "D", "-")}
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"], "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e6e6",
                     "grid.linewidth": 0.6, "legend.frameon": False, "savefig.bbox": "tight"})


def v(d, cell, m, k):
    return 100 * d["cells"][cell][m][k]["value"]


# Figure 1: attack success vs usefulness, localized attack, both answer models
PTS = [(["S", "SL", "S2-ID"], "S, SL, S2-ID (ours)", "#0072B2", "o", 70),
       (["C", "M"], "C, M", "#E69F00", "^", 42),
       (["memlineage"], "MemLineage", "#009E73", "s", 38),
       (["a_memguard"], "A-MemGuard", "#CC79A7", "D", 34),
       (["llm_sanitiser"], "LLM Sanitiser", "#7B5EA7", "P", 46),
       (["static", "randec", "R"], "Original SAFE-Mem, RandEC, R", "#7a7a7a", "o", 38)]
fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9), sharey=True)
for ax, (title, d) in zip(axes, (("GPT-4o-mini", G), ("Claude Haiku", H))):
    for ms, lab, c, mk, size in PTS:  # methods with identical values share one marker
        xs = [v(d, "localized", m, "target_asr") for m in ms]
        ys = [v(d, "localized", m, "strict_utility") for m in ms]
        assert max(xs) - min(xs) < 1 and max(ys) - min(ys) < 1, ms
        ax.scatter([xs[0]], [ys[0]], s=size, color=c, marker=mk, zorder=3, edgecolor="white", linewidth=0.6,
                   label=lab)
    ax.set_title(title, fontsize=9.5)
    ax.set_xlim(-6, 70)
    ax.set_ylim(60, 96)
    ax.set_xlabel("Target ASR (%), lower is better")
    ax.annotate("better", xy=(8, 80), xytext=(24, 71), fontsize=7.4, color="#0072B2",
                arrowprops=dict(arrowstyle="->", color="#0072B2", lw=0.8))
axes[0].set_ylabel("Strict utility (%), higher is better")
axes[0].legend(loc="upper center", bbox_to_anchor=(1.05, -0.2), ncol=3, fontsize=7.6)
fig.savefig(HERE / "fig1_tradeoff.svg")
print("figures ok")
