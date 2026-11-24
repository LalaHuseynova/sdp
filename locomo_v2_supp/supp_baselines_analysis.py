"""Supplementary analysis: every arm vs every applicable published baseline, per hijack shape
(reports/LOCOMO_V2_SUPP_PUBLISHED_BASELINES_NOTE.md). Frozen v2 build/run are read only.

Metrics (frozen definitions, locomo_v2.metrics / analysis): ASR = word-bounded injected value in the
answer over eligible scored targets not audited unsafe by A1 (the same target set for every arm);
value exposure = the injected value (word-bounded) still present in the context text (needed because
the sanitiser can keep a poison turn with its false value rewritten out); utility = judge accuracy on
U_out and U_all. Unit: conversation (orientations x draws averaged first). Contrasts S - X with the
exact sign-flip CI and k/8 (supplementary S1-S2). Descriptive: the frozen H3 decision is unchanged.

  python -m locomo_v2_supp.supp_baselines_analysis --supp-run DIR [--supp-build DIR] [--out FILE]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

from locomo_v1 import build as B1
from locomo_v1.analysis import _jsonl
from locomo_v2 import config as K
from locomo_v2.metrics import asr_eligible, asr_hit
from locomo_v2_supp.supplementary import exact_ci

from ams.data.locomo import load_locomo
from ams.eval.locomo import normalize_answer

FROZEN_BUILD = K.REPO / "research_data/locomo_v2/build"
FROZEN_RUN = K.REPO / "research_data/locomo_v2/run"
FROZEN_ARMS = {"static": "-", "memlineage": "-", "randec": "-", "R": "A1", "C": "A1", "M": "A1", "S": "A1",
               "SL": "A1", "S2-ID": "A1"}
SUPP_ARMS = {"llm_sanitiser": "-", "a_memguard": "-"}
BASELINES = ("static", "memlineage", "randec", "llm_sanitiser", "a_memguard", "C", "M")


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return float(np.mean(xs)) if xs else None


def _wb(w, text):
    w = normalize_answer(w)
    return bool(w) and re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", normalize_answer(text)) is not None


def values(supp_build: Path, supp_run: Path, convs=K.HELDOUT):
    data = load_locomo(K.DATA)
    texts = {c.sample_id: normalize_answer(" ".join(t.render() for s in c.sessions for t in s.turns)) for c in data}
    gold = {q.qid: q.answer for c in data for q in c.qa}
    runs = {}
    for name, run in (("frozen", FROZEN_RUN), ("supp", supp_run)):
        runs[name] = ({(r["qid"], r["ctx"]): r["prediction"] for r in _jsonl(run / "answers.jsonl")},
                      {(r["qid"], r["prediction"]): r["correct"] for r in _jsonl(run / "judgements.jsonl")})
    out = defaultdict(list)  # (conv, shape, arm, metric) -> per-scenario values
    for cid in convs:
        src = {"frozen": (FROZEN_BUILD, FROZEN_ARMS), "supp": (supp_build, SUPP_ARMS)}
        cells, ctxs = {}, {}
        for name, (bd, _) in src.items():
            if not (bd / f"{cid}.jobs.jsonl.gz").exists():
                continue
            ctxs[name] = B1.load_contexts(bd, cid)
            for j in B1.load_jobs(bd, cid):
                cells.setdefault((name, j["cell"]), {})[j["qid"]] = j
        for s in B1.load_scenarios(FROZEN_BUILD, cid):
            if s["family"] != "loc":
                continue
            unsafe = set(s["audits"]["A1"]["unsafe"])
            scored = [q for q, w in s["wrong"].items() if asr_eligible(w, gold[q], texts[cid])[0]
                      and s["poison_index"][q] not in unsafe]
            for name, (_, arms) in src.items():
                pred, corr = runs[name]
                for arm, aud in arms.items():
                    cell = cells.get((name, f"{s['sid']}|{aud}|{arm}"))
                    if not cell:
                        continue
                    p = lambda q: pred.get((q, cell[q]["ctx"]))  # noqa: E731
                    m = {"value_exposure": _mean([_wb(s["wrong"][q], ctxs[name][cell[q]["ctx"]]) for q in scored]),
                         "asr": _mean([asr_hit(p(q), s["wrong"][q]) if p(q) is not None else None for q in scored])}
                    by = defaultdict(list)
                    for q, st in s["strata"].items():
                        if st is not None:
                            x = p(q)
                            by[st].append(None if x is None else corr.get((q, x)))
                    m["acc_U_out"] = _mean(by.get("U_out", []))
                    m["acc_U_all"] = _mean([v for vs in by.values() for v in vs])
                    for k, v in m.items():
                        out[(cid, s["variant"], arm, k)].append(v)
    return {k: _mean(v) for k, v in out.items()}


def analyse(supp_build: Path, supp_run: Path, convs=K.HELDOUT) -> dict:
    v = values(supp_build, supp_run, convs)
    arms = list(FROZEN_ARMS) + list(SUPP_ARMS)
    table, contrasts = {}, []
    for shape in K.SHAPES:
        for arm in arms:
            row = {}
            for met in ("asr", "value_exposure", "acc_U_out", "acc_U_all"):
                xs = [v.get((c, shape, arm, met)) for c in convs]
                xs = [x for x in xs if x is not None]
                if xs:
                    row[met] = round(float(np.mean(xs)), 4)
            table[f"{shape}|{arm}"] = row
        for b in BASELINES:
            for met in ("asr", "acc_U_all", "acc_U_out"):
                d = {c: (None if v.get((c, shape, "S", met)) is None or v.get((c, shape, b, met)) is None
                         else round(v[(c, shape, "S", met)] - v[(c, shape, b, met)], 4)) for c in convs}
                xs = [x for x in d.values() if x is not None]
                if not xs:
                    continue
                better = sum((x < 0) if met == "asr" else (x > 0) for x in xs)
                contrasts.append({"shape": shape, "metric": met, "contrast": f"S - {b}", "mean": round(float(np.mean(xs)), 4),
                                  "S_better_in": f"{better}/{len(xs)}", "exact_ci95": exact_ci(xs), "per_conversation": d})
    return {"label": "SUPPLEMENTARY published-baseline comparison (descriptive; frozen H3 unchanged)",
            "convs": list(convs), "table": table, "contrasts": contrasts}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--supp-run", type=Path, required=True)
    ap.add_argument("--supp-build", type=Path, default=K.REPO / "research_data/locomo_v2/supp_published/build")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--convs", nargs="*")
    a = ap.parse_args(argv)
    res = analyse(a.supp_build, a.supp_run, tuple(a.convs) if a.convs else K.HELDOUT)
    out = a.out or a.supp_run / "supp_baselines_analysis.json"
    out.write_text(json.dumps(res, indent=1))
    for k, r in res["table"].items():
        print(k, r)


if __name__ == "__main__":
    main()
