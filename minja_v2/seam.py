"""Combined arms for MINJA's retrieval seam (scripts/minja_patch.py, `audit_filter`).

$MINJA_AUDIT = "<base>+<extra>", base = a ranked SAFE-Mem arm (typed-noscope):

  <base>+pub:<name>   the base selection, then a published defence filters it (no refill),
                      as in protocol v2 ("published methods filter static's retrieval")
  <base>+<arm>        arm in R, C, M, S, SL, S2-ID: the frozen policy decides on MINJA's full
                      similarity ranking first; the base then selects from the eligible
                      records (refill from the eligible ranking); S2-ID's gate acts last

Environment: MINJA_V2_PAIR, MINJA_V2_CONDITION, MINJA_V2_TICKETS (audits file),
MINJA_V2_VERDICTS (SensitiveAction verdicts), MINJA_V2_TRACE (jsonl trace).
"""

from __future__ import annotations

import json
import os

_ADAPTER = None


def _adapter():
    global _ADAPTER
    if _ADAPTER is None:
        from .adapter import Adapter

        _ADAPTER = Adapter.from_files(os.environ["MINJA_V2_PAIR"],
                                      os.environ["MINJA_V2_CONDITION"],
                                      os.environ["MINJA_V2_TICKETS"],
                                      os.environ.get("MINJA_V2_VERDICTS") or None)  # fmt: skip
    return _ADAPTER


def _trace(row: dict) -> None:
    path = os.environ.get("MINJA_V2_TRACE")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")


def combined(name, query, memory, selected, ranked, scores, ranked_fns, methods, principal):
    base, extra = name.split("+", 1)
    if base not in ranked_fns:
        raise ValueError(f"unknown base arm {base!r} in {name!r}")
    ranked = list(ranked or selected)
    if extra.startswith("pub:"):
        pub = extra[4:]
        kept, why = ranked_fns[base](query, memory, selected, ranked)
        if kept:
            k2, why2 = methods[pub](query, memory, kept)
            k2 = [i for i in kept if i in set(k2)]  # keep the base order; no refill
            why = {**why, **why2}
        else:
            k2 = kept
        _trace({"arm": name, "query": query, "principal": principal, "base_kept": kept,
                "kept": k2})  # fmt: skip
        return k2, why
    arm = extra
    if scores is None:
        raise RuntimeError("the policy arms need MINJA's similarity scores (patched seam)")
    scores = {int(k): float(v) for k, v in scores.items()}
    ad = _adapter()
    eligible, detail = ad.rank(arm, query, memory, ranked, scores)
    if eligible:
        kept, why = ranked_fns[base](query, memory, selected, eligible)
    else:  # every candidate withheld: an empty context, never a fallback to the raw top-k
        kept, why = [], {i: "withheld by policy" for i in selected}
    gated = ad.gate(query, memory, kept) if arm == "S2-ID" else kept
    if len(gated) < len(kept):
        why = {**why, **{i: "S2-ID sensitive-action gate" for i in kept if i not in gated}}
    _trace({"arm": name, "condition": ad.condition, "query": query, "principal": principal,
            "top": ranked[:10], "eligible_top": eligible[:10], "base_kept": kept,
            "kept": gated, "decisions": {str(i): v for i, v in detail.items()}})  # fmt: skip
    return gated, why
