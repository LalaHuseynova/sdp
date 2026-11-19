"""Analysis, run once on the result pairs (protocol §4).

Estimates per pair, then the mean over pairs. Paired cluster bootstrap over pairs with the
frozen Option B helpers (group_weights, boot_mean, p_value, bound, ci95, holm), one shared
resampling matrix, 10,000 resamples, seed 20261115. G1, G3, G4 and (rev 3) G5 are
intersection-union composites (p = the largest part p); Holm over the m composites of
protocol.HYPOTHESES (rev 3: m = 4). A part with no estimable pair gives p = 1 (still counted).

Rev 3: a condition belongs to one written memory (protocol.CONDITIONS[c]["memory"]); a
reference row compared within a condition is read on that condition's memory, so every
contrast compares rows that read the same memory.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ams.research.protocol_v2.analysis import boot_mean, bound, ci95, group_weights, holm, p_value

from . import protocol as P

LABEL = {"clean": "Clean (no attack)", "undefended": "Undefended agent",
         "safemem_strict": "SAFE-Mem, strict scope", "static": "SAFE-Mem, shared (static)",
         "pub:A-MemGuard": "A-MemGuard", "pub:MemLineage": "MemLineage",
         "pub:LLM-sanitizer": "LLM sanitiser", "pub:RandEC": "RandEC",
         "R": "R", "C": "C", "M": "M", "S": "S (ours)", "SL": "SL (ours)", "S2-ID": "S2-ID (ours)"}
METRIC_LABEL = {
    "asr": "ASR ↓ [generated code]", "asr_gate": "ASR-gate ↓ [code sent to execution]",
    "victim_acc": "victim accuracy ↑", "benign_acc": "benign accuracy ↑",
    "poison_exposure": "poison exposure ↓ [retrieval]",
    "laundered_exposure": "laundered exposure ↓ [retrieval]",
    "innocent_retention": "innocent retention ↑ [retrieval]",
    "benign_retention": "benign retention ↑ [retrieval]",
    "legit_retention": "legit (history) retention ↑ [retrieval]",
}  # fmt: skip
MEMORY_LABEL = {"attack": "MINJA attack memory", "hist": "mixed-history memory"}


def memory_of(condition: str | None, memory: str | None = None) -> str:
    if memory:
        return memory
    return P.CONDITIONS[condition]["memory"] if condition else "attack"


def rows_of(score: dict, memory: str) -> dict:
    if memory == "attack":
        return score["rows"]
    return (score.get(memory) or {}).get("rows", {})


def value(score: dict, row: str, condition: str | None, metric: str,
          memory: str | None = None) -> float:  # fmt: skip
    rows = rows_of(score, memory_of(condition, memory))
    r = rows.get(f"{row}|{condition}") or rows.get(f"{row}|-")
    v = None if r is None else r.get(metric)
    return np.nan if v is None else float(v)


def vector(scores: list[dict], row, condition, metric, memory=None) -> np.ndarray:
    return np.array([value(s, row, condition, metric, memory) for s in scores], dtype=float)


def _mean(v):
    return float(np.nanmean(v)) if np.any(~np.isnan(v)) else None


def hypotheses(scores, seed=P.BOOT_SEED, resamples=P.RESAMPLES, alpha=P.ALPHA) -> dict:
    W = group_weights(len(scores), seed, resamples)
    tests = {}
    for name, parts in P.HYPOTHESES.items():
        out = []
        for metric, cond, a, b, side, margin in parts:
            d = vector(scores, a, cond, metric) - vector(scores, b, cond, metric)
            if np.all(np.isnan(d)):
                out.append(({"metric": metric, "condition": cond, "contrast": f"{a} − {b}",
                             "side": side, "margin": margin, "estimable": False, "p": 1.0},
                            None))  # fmt: skip
                continue
            draws = boot_mean(d, W)
            out.append(({"metric": metric, "condition": cond, "contrast": f"{a} − {b}",
                         "side": side, "margin": margin, "estimable": True,
                         "estimate": _mean(d), "ci95": ci95(draws),
                         "pairs": int(np.sum(~np.isnan(d))),
                         "p": p_value(draws, side, margin)}, draws))  # fmt: skip
        estimable = all(s["estimable"] for s, _ in out)
        tests[name] = (out, estimable, max(s["p"] for s, _ in out) if estimable else 1.0)
    adj = holm({n: t[2] for n, t in tests.items()}, alpha)
    res = {}
    for name, (parts, estimable, p) in tests.items():
        level = adj[name]["level"]
        res[name] = {"estimable": estimable, "p": p, **adj[name],
                     "parts": [{**s, **({"bound": bound(d, s["side"], level)}
                                        if d is not None else {})} for s, d in parts]}  # fmt: skip
    return {"alpha": alpha, "seed": seed, "resamples": resamples, "m": len(res), "tests": res}


def table_rows() -> list[tuple[str, str, str | None]]:
    """(memory, row, condition) in table order: each memory's reference rows, then policies."""
    out = []
    for mem in P.MEMORIES:
        out += [(mem, r, None) for r, _, _ in P.REFERENCE_ROWS]
        out += [(mem, arm, c) for arm, _ in P.POLICY_ROWS for c in P.conditions_of(mem)]
    return out


def summary(scores, seed=P.BOOT_SEED, resamples=P.RESAMPLES) -> dict:
    W = group_weights(len(scores), seed, resamples)
    cells = {}
    for mem, row, cond in table_rows():
        for metric in P.METRICS:
            v = vector(scores, row, cond, metric, mem)
            if np.all(np.isnan(v)):
                continue
            cells[f"{mem}:{row}|{cond or '-'}|{metric}"] = {
                "estimate": _mean(v), "ci95": ci95(boot_mean(v, W)),
                "pairs": int(np.sum(~np.isnan(v)))}  # fmt: skip
    return cells


def pct(x):
    return "—" if x is None else f"{100 * x:.0f}"


def table(cells: dict) -> str:
    cols = P.METRICS
    head = "| Memory | Row | Condition | " + " | ".join(METRIC_LABEL[c] for c in cols) + " |"
    lines = [head, "|" + "---|" * (len(cols) + 3)]
    for mem, row, cond in table_rows():
        vals = []
        for c in cols:
            cell = cells.get(f"{mem}:{row}|{cond or '-'}|{c}")
            vals.append("—" if cell is None else
                        f"{pct(cell['estimate'])} [{pct(cell['ci95'][0])}, {pct(cell['ci95'][1])}]"
                        if cell["ci95"] else pct(cell["estimate"]))  # fmt: skip
        lines.append(f"| {MEMORY_LABEL[mem]} | {LABEL[row]} | {cond or 'all'} | "
                     + " | ".join(vals) + " |")
    return "\n".join(lines)


def analyse(score_files: list[Path], out: Path, label: str) -> dict:
    scores = [json.loads(Path(f).read_text()) for f in score_files]
    roles = {s["pair"]["role"] for s in scores}
    if roles != {"result"}:
        raise ValueError(f"the analysis reads result pairs only, got roles {roles}")
    res = {"label": label, "protocol": P.PROTOCOL_ID, "pairs": len(scores),
           "hypotheses": hypotheses(scores), "cells": summary(scores),
           "isr": [s["isr"] for s in scores],
           "audit_shortfall": {s["pair"]["pair_id"]: s["audit_shortfall"] for s in scores}}  # fmt: skip
    out.mkdir(parents=True, exist_ok=True)
    (out / "analysis.json").write_text(json.dumps(res, indent=1) + "\n")
    lines = [f"# {label}", "", f"Pairs: {len(scores)}. Values: % over pairs [95% CI].", "",
             table(res["cells"]), "",
             f"## Hypotheses (Holm over {res['hypotheses']['m']}; intersection-union parts)", ""]
    for name, h in res["hypotheses"]["tests"].items():
        mark = "✓" if h["reject"] else "✗"
        lines.append(f"- **{name}** {mark} p = {h['p']:.4f}, Holm level {h['level']:.4f}")
        for part in h["parts"]:
            est = "not estimable" if not part["estimable"] else (
                f"{part['estimate']:+.3f} [{part['ci95'][0]:+.3f}, {part['ci95'][1]:+.3f}], "
                f"bound {part.get('bound', float('nan')):+.3f}, p {part['p']:.4f}")
            lines.append(f"  - {part['metric']} {part['contrast']} ({part['condition']}): {est}")
    (out / "tables.md").write_text("\n".join(lines) + "\n")
    return res
