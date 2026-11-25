"""LoCoMo + SAFE-Mem study CLI (reports/PROTOCOL_LOCOMO_SAFEMEM.md). Run under WSL:

  R=research_data/locomo_v2/run.sh
  MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash $R -m locomo_safemem <command> [options]

free      plan | equivalence | dry | mock [--convs ...] | estimate | freeze | verify | status | stop
          precompute | final | randec | estimate-final | analyse | tables
paid      paid construct | paid conflicts | paid defences | paid answers   (owner_approval.json)
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from locomo_safemem import config as K
from locomo_safemem import freeze as FZ
from locomo_safemem import run as R

ROOT = R.ROOT
PRICE_IN, PRICE_OUT = 0.15, 0.60  # GPT-4o-mini via OpenRouter, USD per million tokens
V1_CALIBRATION = 0.21898665 / 0.271  # LoCoMo pilot: actual spend / chars-per-4 estimate (locomo_v1.config)
V2_DEFENCE_USD_PER_CALL = 18.50071995 / (60352 + 30980 + 6974)  # realized, LoCoMo v2 supplement


def _usd(tokens_in, tokens_out):
    return (tokens_in * PRICE_IN + tokens_out * PRICE_OUT) / 1e6


def cmd_plan(a):
    from ams.data.locomo import load_locomo

    from locomo_safemem import scenarios as SN

    out = {}
    for c in load_locomo(K.DATA):
        if a.convs and c.sample_id not in a.convs:
            continue
        items = SN.plan(c)
        cond = Counter(n.split("|")[0] + "|" + n.split("|")[2] for i in items for n in i["conditions"])
        out[c.sample_id] = {"stores": len(items), "conditions": sum(len(i["conditions"]) for i in items),
                            "stores_by_family": dict(Counter(i["family"] for i in items)), "condition_kinds": dict(cond)}
    print(json.dumps(out, indent=1))


def cmd_dry(a):
    out = ROOT / "dry"
    s = R.run_pass("dry", out, tuple(a.convs or K.CONVS), workers=a.workers)
    st = R.merge(out, out / "build", tuple(a.convs or K.CONVS))
    reqs = st["construction_requests"]
    FZ.REQUESTS.parent.mkdir(parents=True, exist_ok=True)
    R.write_requests(FZ.REQUESTS, reqs)
    print(json.dumps({"errors": s["errors"], "construction_requests": len(reqs), "file": str(FZ.REQUESTS)}, indent=1))


def construction_estimate() -> dict:
    rows = R.read_requests(FZ.REQUESTS)
    kinds = Counter()
    tin = Counter()
    for r in rows:
        k = "extraction" if r["max_tokens"] == 2400 else "classifier" if r["max_tokens"] == 24 else f"other{r['max_tokens']}"
        kinds[k] += 1
        tin[k] += len(r["content"]) // 4
    def dialogue_lines(content):
        body = content.split("Session:\n", 1)[1].split("\n\nReturn a JSON", 1)[0]
        return sum(1 for ln in body.split("\n") if ln.strip())

    ext_single = sum(1 for r in rows if r["max_tokens"] == 2400 and dialogue_lines(r["content"]) == 1)
    out_low = (kinds["extraction"] - ext_single) * 300 + ext_single * 60 + kinds["classifier"] * 6
    out_high = kinds["extraction"] * 2400 + kinds["classifier"] * 24
    return {"requests": dict(kinds), "input_tokens_chars_over_4": dict(tin), "single_turn_extractions": ext_single,
            "usd_low": round(_usd(sum(tin.values()) * V1_CALIBRATION, out_low), 3),
            "usd_expected": round(_usd(sum(tin.values()), (kinds["extraction"] - ext_single) * 1100 + ext_single * 120
                                       + kinds["classifier"] * 8), 3),
            "usd_cap_bound": round(_usd(sum(tin.values()), out_high), 3)}


def cmd_mock(a):
    from locomo_v1 import execute as E
    from locomo_v2_supp import published_supp as PS

    from locomo_safemem import analysis as AN
    from locomo_safemem import paid as PD

    convs = tuple(a.convs or K.DEV)
    out = ROOT / "mock"
    if a.fresh:
        shutil.rmtree(out, ignore_errors=True)
    s = R.run_pass("mock", out, convs, workers=a.workers)
    st = R.merge(out, out / "build", convs)
    d = PD.defences(out / "build", cap=0, convs=convs, client=PS.MockDefenceLLM())
    rd = R.randec_stage(out / "build", convs, workers=a.workers)
    run = out / "run"
    run.mkdir(parents=True, exist_ok=True)
    res = E.run(out / "build", run, "mock", K.DRAWS, workers=8, convs=convs)
    an = AN.analyse(out / "build", run, convs)
    (out / "analysis_mock.json").write_text(json.dumps(an, indent=1, default=str))
    rep = {"pass": {k: v for k, v in s.items() if k != "errors"}, "errors": s["errors"][:3],
           "retrievals": st["retrievals"], "sentinel_checked_vs_frozen": st["sentinel_checked"],
           "jobs": st["jobs"], "contexts": st["contexts"], "static_loc": st["static_loc"],
           "defence_jobs_added": d["jobs_added"], "randec": rd,
           "answers": {k: v for k, v in res.items() if k != "per_conversation"} if isinstance(res, dict) else res,
           "analysis_hypotheses": {h: v["parts"][0]["estimate"] for h, v in an["hypotheses"].items()},
           "mechanism": an["mechanism"]}
    (out / "mock_report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps(rep, indent=1, default=str)[:6000])


def cmd_estimate(a):
    """Exact construction (dry pass); conflicts, defences and answers projected from the mock pass on
    the dev conversations (real counts are recomputed free, `estimate-final`, before P2/P3)."""
    from locomo_v1 import build as B1

    est = {"P1a_construction": construction_estimate()}
    mock = ROOT / "mock"
    rep = json.loads((mock / "mock_report.json").read_text())
    from ams.data.locomo import load_locomo

    nq = {c.sample_id: sum(q.category in K.QA_CATEGORIES for q in c.qa) for c in load_locomo(K.DATA)}
    scale = sum(nq.values()) / sum(nq[c] for c in K.DEV)  # project dev -> all 10 by question count
    keys, chars = set(), 0
    for cid in K.DEV:
        ctx = {r["ctx"]: r["text"] for r in R_gz(mock / "build" / f"{cid}.contexts.jsonl.gz")}
        for j in R_gz(mock / "build" / f"{cid}.jobs.jsonl.gz"):
            k = (j["qid"], j["ctx"])
            if k not in keys:
                keys.add(k)
                chars += len(ctx[j["ctx"]])
    n = len(keys) * scale
    raw = (chars * scale / 4 * PRICE_IN + n * 32 * PRICE_OUT + n * 160 * PRICE_IN + n * 4 * PRICE_OUT) / 1e6
    est["P3_answers"] = {"answer_keys_projected": int(n), "usd_projected": round(raw * V1_CALIBRATION, 2),
                         "usd_uncalibrated": round(raw, 2)}
    keysc = set()
    for f in (mock / "shards").glob("*.json.gz"):
        with gzip.open(f, "rt") as fh:
            keysc.update(json.load(fh).get("conflict_distinct_keys", []))
    nconf = len(keysc) * scale
    est["P1c_conflicts"] = {"distinct_checks_projected_from_mock": int(nconf),
                            "usd_projected": round(_usd(nconf * 200, nconf * 2), 3),
                            "usd_at_5x": round(_usd(5 * nconf * 200, 5 * nconf * 2), 3),
                            "note": "mock claim relations differ from GPT-4o-mini's: the exact count comes from the free "
                                    "precompute pass after P1a, before P1c is sent"}
    import tempfile

    from locomo_v2_supp import published_supp as PS

    from locomo_safemem import paid as PD

    with tempfile.TemporaryDirectory() as tmp:  # free replay of P2 on a copy of the mock build
        tb = Path(tmp) / "build"
        shutil.copytree(mock / "build", tb)
        rec = PS.Recorder()
        PD.defences(tb, cap=0, convs=K.DEV, client=rec)
    kinds = Counter(v.kind for v in rec.seen.values())
    calls = sum(kinds.values()) * scale
    est["P2_defences"] = {"distinct_requests_dev_mock": dict(kinds), "requests_projected": int(calls),
                          "usd_projected": round(calls * V2_DEFENCE_USD_PER_CALL, 2),
                          "note": "A-MemGuard + LLM sanitiser on the loc stores' static contexts; priced at the LoCoMo v2 "
                                  "supplement's realized USD per call; exact count recomputed after P1 (estimate-final)"}
    est["total_projected_usd"] = round(est["P1a_construction"]["usd_expected"] + est["P3_answers"]["usd_projected"]
                                       + est["P2_defences"]["usd_projected"] + est["P1c_conflicts"]["usd_at_5x"], 2)
    (ROOT / "estimate.json").write_text(json.dumps(est, indent=1))
    print(json.dumps(est, indent=1))


def cmd_estimate_final(a):
    """Exact P2 / P3 counts from the real final build (free), before those stages are sent."""
    import tempfile

    from locomo_v2_supp import published_supp as PS

    from locomo_safemem import paid as PD

    build = ROOT / "build"
    keys, chars = set(), 0
    for cid in K.CONVS:
        ctx = {r["ctx"]: r["text"] for r in R_gz(build / f"{cid}.contexts.jsonl.gz")}
        for j in R_gz(build / f"{cid}.jobs.jsonl.gz"):
            k = (j["qid"], j["ctx"])
            if k not in keys:
                keys.add(k)
                chars += len(ctx[j["ctx"]])
    n = len(keys)
    raw = (chars / 4 * PRICE_IN + n * 32 * PRICE_OUT + n * 160 * PRICE_IN + n * 4 * PRICE_OUT) / 1e6
    with tempfile.TemporaryDirectory() as tmp:
        tb = Path(tmp) / "build"
        shutil.copytree(build, tb)
        rec = PS.Recorder()
        PD.defences(tb, cap=0, client=rec)
    kinds = Counter(v.kind for v in rec.seen.values())
    out = {"P3_answers": {"answer_keys": n, "usd": round(raw * V1_CALIBRATION, 2), "usd_uncalibrated": round(raw, 2)},
           "P2_defences": {"requests": dict(kinds), "usd": round(sum(kinds.values()) * V2_DEFENCE_USD_PER_CALL, 2)}}
    (ROOT / "estimate_final.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


def R_gz(path):
    with gzip.open(path, "rt") as fh:
        return [json.loads(x) for x in fh if x.strip()]


def cmd_precompute(a):
    from locomo_safemem import paid as PD

    out = ROOT / "precompute"
    s = R.run_pass("precompute", out, tuple(a.convs or K.CONVS), workers=a.workers,
                   construction_cache=PD.RUN / PD.STAGES["construct"])
    st = R.merge(out, out / "build", tuple(a.convs or K.CONVS))
    R.write_requests(ROOT / "requests" / "conflicts.jsonl.gz", st["conflict_requests"])
    print(json.dumps({"errors": s["errors"][:3], "conflict_requests": len(st["conflict_requests"]),
                      "retrievals": st["retrievals"], "sentinel_checked": st["sentinel_checked"]}, indent=1))


def cmd_final(a):
    from locomo_safemem import paid as PD

    out = ROOT / "final"
    reuse = R.reuse_precompute(out, ROOT / "precompute", PD.RUN / PD.STAGES["conflicts"])
    print(json.dumps({"reuse": reuse}))
    s = R.run_pass("final", out, tuple(a.convs or K.CONVS), workers=a.workers,
                   construction_cache=PD.RUN / PD.STAGES["construct"], conflict_cache=PD.RUN / PD.STAGES["conflicts"])
    st = R.merge(out, ROOT / "build", tuple(a.convs or K.CONVS))
    print(json.dumps({"errors": s["errors"][:3], "jobs": st["jobs"], "contexts": st["contexts"],
                      "sentinel_checked": st["sentinel_checked"]}, indent=1))


def cmd_paid(a):
    from locomo_safemem import paid as PD

    appr = PD.gate(a.stage)
    cap = appr["caps_usd"][a.stage]
    if a.stage == "construct":
        res = PD.fetch("construct", R.read_requests(FZ.REQUESTS), cap)
    elif a.stage == "conflicts":
        res = PD.fetch("conflicts", R.read_requests(ROOT / "requests" / "conflicts.jsonl.gz"), cap)
    elif a.stage == "defences":
        res = PD.defences(ROOT / "build", cap)
    else:
        res = PD.answers(ROOT / "build", cap)
    print(json.dumps(res, default=str))


def cmd_status(a):
    from locomo_safemem import paid as PD

    out = {"verify": FZ.verify(), "approval": PD.APPROVAL.exists()}
    import sqlite3

    for st in ("construct", "conflicts", "defences"):
        p = PD.STATE / f"{st}_guard.sqlite"
        if p.exists():
            db = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            u, h, b = db.execute("SELECT used_nanodollars,held_nanodollars,blocked FROM budget_config").fetchone()
            out[st] = {"spent_usd": int(u) / 1e9, "held_usd": int(h) / 1e9, "blocked": bool(b)}
    print(json.dumps(out, indent=1, default=str))


def cmd_stop(a):
    from locomo_safemem import paid as PD

    PD.RUN.mkdir(parents=True, exist_ok=True)
    (PD.RUN / "STOP").write_text(datetime.now(UTC).isoformat())
    (PD.RUN / "answers").mkdir(parents=True, exist_ok=True)
    (PD.RUN / "answers" / "STOP").write_text(datetime.now(UTC).isoformat())
    print("STOP requested")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="locomo_safemem")
    ap.add_argument("command")
    ap.add_argument("stage", nargs="?")
    ap.add_argument("--convs", nargs="*")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--fresh", action="store_true")
    a = ap.parse_args(argv)
    if a.command == "plan":
        cmd_plan(a)
    elif a.command == "equivalence":
        from locomo_safemem import equivalence as EQ

        rep = EQ.compare(("G-T00",))
        (ROOT / "equivalence_report.json").write_text(json.dumps(rep, indent=1))
        print(json.dumps({k: v for k, v in rep.items() if k != "differences"}, indent=1))
    elif a.command == "dry":
        cmd_dry(a)
    elif a.command == "mock":
        cmd_mock(a)
    elif a.command == "estimate":
        cmd_estimate(a)
    elif a.command == "freeze":
        print(json.dumps({k: v for k, v in FZ.prepare().items() if k != "files"}, indent=1))
    elif a.command == "verify":
        print(json.dumps(FZ.verify(), indent=1))
    elif a.command == "estimate-final":
        cmd_estimate_final(a)
    elif a.command == "tables":
        from locomo_safemem import tables as TB

        TB.main(["--analysis", str(ROOT / "analysis.json"), "--out", str(ROOT / "tables"),
                 "--mpbench", "/mnt/c/Users/HP/Documents/sdp/research_data/protocol_v2_optionB_run_v1/analysis/analysis.json",
                 "--v2", str(K.REPO / "research_data/locomo_v2/run/analysis.json")])
    elif a.command == "randec":
        print(json.dumps(R.randec_stage(ROOT / "build", tuple(a.convs or K.CONVS), workers=a.workers), indent=1))
    elif a.command == "precompute":
        cmd_precompute(a)
    elif a.command == "final":
        cmd_final(a)
    elif a.command == "paid":
        cmd_paid(a)
    elif a.command == "status":
        cmd_status(a)
    elif a.command == "stop":
        cmd_stop(a)
    elif a.command == "analyse":
        from locomo_safemem import analysis as AN
        from locomo_safemem import paid as PD

        res = AN.analyse(ROOT / "build", PD.RUN / "answers", K.HELDOUT)
        (ROOT / "analysis.json").write_text(json.dumps(res, indent=1, default=str))
        dev = AN.analyse(ROOT / "build", PD.RUN / "answers", K.DEV)
        (ROOT / "analysis_dev.json").write_text(json.dumps(dev, indent=1, default=str))
        print("analysis written")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
