"""plan.md step 1.12: the dry-run cost and runtime estimate, tested OFFLINE on synthetic
ledgers and journals with exact arithmetic. No network, no paid call."""

from __future__ import annotations

import importlib.util
import json
import os
import socket
import sqlite3
import sys
import types
from pathlib import Path

import pytest

from ams.research.protocol_v2 import cost as CO
from ams.research.protocol_v2 import registry as REG


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(self, address, *args, **kwargs):
        raise AssertionError("Cost tests forbid networking")

    monkeypatch.setattr(socket.socket, "connect", deny)


def ledger(path, calls):
    """calls: (stage, usd, in_tokens, out_tokens, epoch seconds)."""
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE dispatches (call_id TEXT, stage TEXT, status TEXT, result TEXT)")
    for i, (stage, usd, tin, tout, ts) in enumerate(calls):
        md = {"generation_id": f"gen-{ts}-x", "input_tokens": tin, "output_tokens": tout}
        res = {"actual_paid_usd": str(usd), "dispatch": {"receipt": {"metadata": md}}}
        db.execute("INSERT INTO dispatches VALUES (?,?,?,?)",
                   (str(i), stage, "completed", json.dumps(res)))  # fmt: skip
    db.execute("INSERT INTO dispatches VALUES ('f','workload_answer','failed','{}')")
    db.commit()
    db.close()
    return path


def write_journal(path: Path, rows):
    path.mkdir(parents=True)
    db = sqlite3.connect(path / "queries.sqlite")
    db.execute("CREATE TABLE outcomes(key TEXT PRIMARY KEY, body TEXT, hash TEXT)")
    for i, r in enumerate(rows):
        db.execute("INSERT INTO outcomes VALUES (?,?,?)", (str(i), json.dumps(r), ""))
    db.commit()
    db.close()


def row(method, condition, probe, prompt, kind="attack"):
    return {"method": method, "condition": condition, "probe_id": probe, "kind": kind,
            "prompt_hash": prompt}  # fmt: skip


def measured(root: Path, journals: dict, conflicts: dict, seconds=None, conditions=None):
    root.mkdir(parents=True)
    meas = {"methods": {}}
    for m, rows in journals.items():
        write_journal(root / m, rows)
        meas["methods"][m] = {"seconds": (seconds or {}).get(m, 10.0),
                              "conditions": (conditions or {}).get(m, 2),
                              "conflict_distinct": conflicts.get(m, [])}  # fmt: skip
    (root / "measure.json").write_text(json.dumps(meas))
    return root


# ----------------------------------------------------------------------------- per call


def test_ledger_costs_are_means_of_completed_calls_and_pauses_are_not_throughput(tmp_path):
    path = ledger(tmp_path / "d.sqlite", [
        ("workload_answer", 0.0001, 700, 30, 100), ("workload_answer", 0.0003, 900, 50, 102),
        ("workload_answer", 0.0002, 800, 40, 106), ("workload_answer", 0.0002, 800, 40, 900),
        ("workload_judge", 0.00005, 200, 20, 1000)])  # fmt: skip
    c = CO.ledger_costs(path)
    assert c["workload_answer"]["n"] == 4  # the failed dispatch is not counted
    assert c["workload_answer"]["usd"] == pytest.approx(0.0002)
    assert c["workload_answer"]["in_tokens"] == 800 and c["workload_answer"]["out_tokens"] == 40
    # gaps 2, 4 and 794 s: the 794 s pause is excluded, median of (2, 4) = 3
    assert c["workload_answer"]["seconds_per_call"] == 3
    assert c["workload_judge"]["seconds_per_call"] is None


def test_call_seconds_median_and_mean_of_gaps_without_pauses(tmp_path):
    path = ledger(tmp_path / "d.sqlite", [("a", 1e-4, 1, 1, t) for t in (0, 1, 2, 5, 500)])
    # gaps 1, 1, 3 (the 495 s pause is dropped)
    assert CO.call_seconds(path) == pytest.approx({"median": 1.0, "mean": 5 / 3})


def test_published_costs_add_the_sanitiser_resume_session(tmp_path):
    for m, spend, n in (("amemguard", "0.28", 2184), ("sanitiser", "0.01", 278),
                        ("memlineage", "0.0048", 216)):  # fmt: skip
        (tmp_path / f"{m}_summary.json").write_text(
            json.dumps({"task_spend_usd": spend, "calls_this_run": n}))
    calls = {"published_sanitiser": {"usd": 0.0001, "n": 100}}
    p = CO.published_costs(calls, tmp_path)
    assert p["a_memguard_per_context"] == pytest.approx(0.28 / 280)
    assert p["llm_sanitiser_per_context"] == pytest.approx((0.01 + 0.01) / 280)
    assert p["memlineage_per_question"] == pytest.approx(0.0048 / 216)
    assert p["memlineage_questions_per_group"] == 27
    assert p["a_memguard_calls_per_context"] == pytest.approx(2184 / 280)
    assert p["llm_sanitiser_calls_per_context"] == pytest.approx((100 + 278) / 280)


def test_stage1_counts_cached_requests_too(tmp_path):
    (tmp_path / "stage1_summary.json").write_text(json.dumps({"per_group_requests": {
        "G1": {"chat": {"extraction:cache": 10, "extraction:fallback": 30,
                        "classifier:fallback": 5}},
        "G2": {"chat": {"extraction:fallback": 20, "classifier:cache": 15}}}}))  # fmt: skip
    assert CO.stage1_per_group(tmp_path) == {"workload_extraction": 30, "workload_classifier": 10}


def test_price_is_per_token():
    p = CO.price(CO.REPO / "configs/research/pricing_claude_haiku_5_5_20261114.json")
    assert p["in"] == pytest.approx(0.10e-6) and p["out"] == pytest.approx(0.50e-6)


# ----------------------------------------------------------------------------- counts


def test_group_counts_union_internal_methods_and_keep_randec_out(tmp_path):
    d = measured(tmp_path / "g", {
        "static": [row("static", "localized", "p1", "h1"), row("static", "distributed", "p1", "h1"),
                   row("static", "localized", "p2", "h2", "benign")],
        "R": [row("R", "localized", "p1", "h1"), row("R", "distributed", "p1", "h3")],
        "randec": [row("randec", "localized", "p1", "h9")]},
        conflicts={"static": ["c1"], "R": ["c1", "c2"], "randec": ["c9"]})  # fmt: skip
    g = CO.group_counts(d, {"all": {"localized", "distributed"}, "loc": {"localized"}})
    assert g["scopes"]["all"]["answers"] == 3  # h1 h2 h3; randec's h9 not counted
    assert g["scopes"]["all"]["judged"] == 2  # h1 h3 (h2 is a benign probe)
    assert g["scopes"]["loc"]["answers"] == 2
    assert g["scopes"]["all"]["per_method"]["R"] == (2, 2)
    assert g["conflicts"] == 2
    # static is identical across conditions for p1: the published filters see 2 contexts
    assert g["static_invariant"] == {"probes": 2, "varying": 0, "distinct": 2}


def test_invariance_detects_condition_dependent_retrieval():
    rows = [row("static", "a", "p1", "h1"), row("static", "b", "p1", "h2")]
    assert CO.invariance(rows) == {"probes": 1, "varying": 1, "distinct": 2}


def group(answers, judged, static, r, sl, s=0):
    per = {"static": (static, 0), "R": (r, 0), "SL": (sl, 0), "S": (s, 0)}
    return {"answers": answers, "judged": judged, "per_method": per}


def test_unmeasured_methods_are_bounded_by_the_retrieval_they_filter():
    G = [{"scopes": {"all": group(100, 40, 10, 20, 30)}},
         {"scopes": {"all": group(200, 80, 30, 40, 50)}}]  # fmt: skip
    p = CO.per_group(G, "all")
    assert p["answers_low"] == 150 and p["judged_low"] == 60
    extra = 4 * 20 + 4 * 30 + 40  # 4 published <= static, 4 "+R" <= R, S2-ID <= SL
    assert p["unmeasured_high"] == extra
    assert p["answers_high"] == 150 + extra
    assert p["judged_high"] == pytest.approx(60 + extra * 0.4)


C = {"workload_answer": {"usd": 0.0001}, "workload_judge": {"usd": 0.00005},
     "workload_conflict": {"usd": 0.00002}}  # fmt: skip
PUB = {"a_memguard_per_context": 0.001, "llm_sanitiser_per_context": 0.0001,
       "memlineage_per_question": 0.00002, "memlineage_questions_per_group": 27,
       "a_memguard_calls_per_context": 7.8, "llm_sanitiser_calls_per_context": 3.2}  # fmt: skip


def test_evaluation_arithmetic():
    G = [{"scopes": {"all": group(100, 40, 10, 20, 30)}}]
    e = CO.evaluation(G, "all", 10, C, PUB, conflicts=5)
    assert e["answers"]["low"] == pytest.approx(10 * (100 * 1e-4 + 40 * 5e-5 + 5 * 2e-5))
    extra = 4 * 10 + 4 * 20 + 30
    hi = 10 * ((100 + extra) * 1e-4 + (40 + extra * 0.4) * 5e-5 + 10 * 2e-5)
    assert e["answers"]["high"] == pytest.approx(hi)
    assert e["a_memguard"] == pytest.approx({"low": 10 * 10 * 1e-3, "high": 10 * 30 * 1e-3})
    assert e["llm_sanitiser"]["high"] == pytest.approx(10 * 30 * 1e-4)
    assert e["memlineage"]["low"] == e["memlineage"]["high"] == pytest.approx(10 * 27 * 2e-5)
    assert e["total"]["low"] == pytest.approx(
        e["answers"]["low"] + 0.1 + 10 * 10 * 1e-4 + 10 * 27 * 2e-5)


def test_haiku_answers_low_uses_measured_tokens_high_uses_max_tokens():
    c = {"workload_answer": {"in_tokens": 700, "out_tokens": 35}}
    h = {"in": 1e-7, "out": 5e-7}
    p = {"answers_low": 100, "answers_high": 150}
    r = CO.haiku_answers(p, 2, c, h)
    assert r["low"] == pytest.approx(2 * 100 * (700e-7 + 35 * 5e-7))
    assert r["high"] == pytest.approx(2 * 150 * (1.3 * 700e-7 + 200 * 5e-7))


def test_generation_usd_uses_the_prompt_word_ranges():
    s = {"in": 2e-6, "out": 10e-6}
    g = CO.generation_usd(10, 20, 600, 300, s, 4096, 2048)
    tin = 10 * 600 + 20 * 300
    mid = 10 * (315 * 1.4 + 200) + 20 * (250 * 1.4 + 200)
    top = 10 * (450 * 1.4 + 200) + 20 * (380 * 1.4 + 200)
    assert g["low"] == pytest.approx(tin * 2e-6 + mid * 10e-6)
    assert g["high"] == pytest.approx(tin * 2e-6 + top * 10e-6)
    assert g["hard_bound"] == pytest.approx(tin * 2e-6 + (10 * 4096 + 20 * 2048) * 10e-6)


def test_generation_renders_the_frozen_requests():
    g = CO.generation({"in": 2e-6, "out": 10e-6})
    assert (g["attacks"], g["benign"]) == (1440, 1957)  # plan.md rev 4
    assert 100 < g["attack_in_tokens"] < 5000 and 100 < g["benign_in_tokens"] < 5000
    assert g["low"] < g["high"] < g["hard_bound"]


def test_ablation_options(tmp_path):
    root = tmp_path / "abl"
    write_journal(root / "default", [row("S", "localized", "p1", "a"),
                                     row("S", "localized", "p2", "b", "benign")])  # fmt: skip
    write_journal(root / "tau_0.7", [row("SL", "localized", "p1", "a"),
                                     row("SL", "localized", "p1", "c")])  # fmt: skip
    (root / "prompt_mirror").mkdir()  # no journal: ignored
    G = [{"scopes": {"option_b": group(10, 5, 0, 0, 0, s=6)}}]
    c = {**C}
    a = CO.ablations(root, G, c)
    assert (a["dev_answers"], a["dev_judged"]) == (3, 2)
    dev = 3 * 1e-4 + 2 * 5e-5
    assert a["option_a"] == pytest.approx({"low": dev, "high": dev * 4})  # (8 + 24) / 8
    extra = 4 * 6 * 1e-4 + 4 * 6 * 0.5 * 5e-5
    assert a["option_b"]["low"] == pytest.approx(dev + 8 * extra)
    assert a["option_b"]["high"] == pytest.approx((dev + 8 * extra) * 4)


# ----------------------------------------------------------------------------- budget


def test_cap_rounds_up_to_a_readable_figure():
    assert CO.cap(0.012) == 0.05 and CO.cap(0.05) == 0.05
    assert CO.cap(1.01) == 1.5 and CO.cap(9.6) == 10.0
    assert CO.cap(10.2) == 11.0 and CO.cap(30.0) == 30.0


def test_by_purpose_flags_caps_above_the_code_ceiling():
    stages = {"a": {"purpose": "v2_generation", "low": 5.0, "high": 9.0},
              "b": {"purpose": "v2_stage3", "low": 1.0, "high": 2.0},
              "c": {"purpose": "v2_stage3", "low": 1.0, "high": 2.0}}  # fmt: skip
    p = CO.by_purpose(stages)
    assert p["v2_generation"]["proposed_cap"] == 12.0  # 9 x 1.3 = 11.7 -> 12
    assert p["v2_generation"]["fits_ceiling"] is False  # code ceiling USD 10
    assert p["v2_stage3"]["high"] == 4.0 and p["v2_stage3"]["proposed_cap"] == 5.5
    assert p["v2_stage3"]["fits_ceiling"] is True


def test_ceilings_match_the_transport_guard():
    from ams.research.workload.transport import V2_PURPOSES

    assert {k: float(v) for k, v in V2_PURPOSES.items()} == CO.CEILINGS


def test_estimate_end_to_end_on_synthetic_measurements(tmp_path, monkeypatch):
    table = REG.cells()
    loc = table["localized"]["conditions"][0]  # a Table 1 / hypothesis cell
    syb = next(c for v in table.values() if v["family"] in CO.OPTION_B_FAMILIES
               for c in v["conditions"])  # fmt: skip
    dirs = []
    for i in range(2):
        rows = {m: [row(m, loc, "p1", f"{m}{i}"), row(m, syb, "p1", f"{m}{i}s")]
                for m in ("static", "R", "S", "SL")}  # fmt: skip
        rows["randec+R"] = [row("randec+R", loc, "p1", "x")]
        dirs.append(measured(tmp_path / f"g{i}", rows, {"S": ["c1"]},
                             seconds={"randec+R": 66.0}, conditions={"randec+R": 2}))  # fmt: skip
    write_journal(tmp_path / "abl" / "default", [row("S", loc, "p1", "a")])
    calls = {k: {"usd": 1e-4, "n": 10, "in_tokens": 700, "out_tokens": 35,
                 "seconds_per_call": 2.0}
             for k in ("workload_answer", "workload_judge", "workload_conflict",
                       "workload_classifier", "workload_extraction",
                       "workload_retention")}  # fmt: skip
    monkeypatch.setattr(CO, "ledger_costs", lambda: calls)
    monkeypatch.setattr(CO, "published_costs", lambda c: PUB)
    monkeypatch.setattr(CO, "stage1_per_group", lambda: {"workload_extraction": 40,
                                                         "workload_classifier": 35})  # fmt: skip
    monkeypatch.setattr(CO, "generation", lambda s: CO.generation_usd(10, 10, 500, 300, s,
                                                                      4096, 2048))  # fmt: skip
    monkeypatch.setattr(CO, "call_seconds", lambda: {"median": 1.0, "mean": 2.0})
    res = CO.estimate(dirs, tmp_path / "abl", groups=96)
    assert res["per_group"]["all"]["answers_low"] == 8  # 4 methods x 2 conditions
    assert res["per_group"]["core"]["answers_low"] == 4
    assert res["stages"]["3.5 Stage 1 memory, 96 groups"]["low"] == pytest.approx(96 * 75e-4)
    assert res["total"]["low"] == pytest.approx(sum(s["low"] for s in res["stages"].values()))
    assert all(s["low"] <= s["high"] for s in res["stages"].values())
    rt, p = res["runtime"], res["per_group"]["all"]
    assert rt["randec_seconds_per_condition"] == 33.0
    assert rt["precompute_internal_seconds_per_group"] == 40.0  # static, R, S, SL x 10 s
    # the paid process also redoes the published methods' retrieval: A-MemGuard, sanitiser
    # and MemLineage on static, their "+R" on R, S2-ID like SL (10 s each here)
    assert rt["published_retrieval_seconds_per_group"] == 70.0
    # calls: answers + judges + conflicts + published defences' own calls
    calls_low = (p["answers_low"] + p["judged_low"] + 1 + 7.8 * p["distinct_static"]
                 + 3.2 * p["distinct_static"] + 27)  # fmt: skip
    assert rt["calls_per_group"]["low"] == pytest.approx(calls_low)
    # current code: retrieval + RandEC in every condition (2 x 33 s x 2) + calls at 1 s (low)
    assert rt["paid_stage_wall_hours"]["current"][24]["low"] == pytest.approx(
        24 * (40 + 132 + 70 + calls_low * 1.0) / 3600)
    # fix 1: RandEC once per distinct context (static + R)
    randec = 33 / 35 * (p["distinct_static"] + p["distinct_R"])
    assert rt["paid_stage_wall_hours"]["randec_cached"][24]["low"] == pytest.approx(
        24 * (40 + randec + 70 + calls_low * 1.0) / 3600)
    # high: upper-bound calls at the dev mean seconds per call (2 s here)
    calls_high = (p["answers_high"] + p["judged_high"] + 2 + (7.8 + 3.2) * (
        p["distinct_static"] + p["distinct_R"]) + 27)  # fmt: skip
    assert rt["paid_stage_wall_hours"]["randec_cached"][24]["high"] == pytest.approx(
        24 * (40 + randec + 70 + calls_high * 2.0) / 3600)
    assert rt["precompute_cpu_hours"]["randec_cached"] == pytest.approx(96 * (40 + randec) / 3600)
    # both fixes: the paid process recomputes only S2-ID (timed as SL, 10 s here) and runs
    # RandEC on the stored contexts; the free precompute runs twice (steps 1 and 2)
    assert rt["paid_stage_wall_hours"]["both_fixes"][24]["low"] == pytest.approx(
        24 * (10 + randec + calls_low * 1.0) / 3600)
    assert rt["precompute_cpu_hours"]["both_fixes"] == pytest.approx(96 * 2 * 40 / 3600)
    sc = res["scenarios"]
    a, b, c3 = (sc[k] for k in sorted(sc))
    # the full-plan scenario is exactly the sum of the stage table
    assert a == pytest.approx(res["total"])
    assert b["high"] < c3["high"] < a["high"]  # MPBench only < middle option < full plan
    # the full plan's per-purpose caps are the stage table's
    full = res["scenario_caps"][sorted(sc)[0]]
    assert full.keys() == res["by_purpose"].keys()
    for purpose, v in res["by_purpose"].items():
        assert full[purpose]["high"] == pytest.approx(v["high"])
        assert full[purpose]["proposed_cap"] == v["proposed_cap"]
    assert "v2_generation" not in res["scenario_caps"][sorted(sc)[1]]  # MPBench only
    md = CO.render(res)
    for text in ("| **Total** |", "Scope scenarios", "Haiku as generator", "hard bound"):
        assert text in md


# ----------------------------------------------------------------------------- RandEC


def test_randec_loader_forces_the_local_hugging_face_cache(monkeypatch):
    seen = {}

    class Fake:
        def __init__(self, weights):
            seen.update(hub=os.environ.get("HF_HUB_OFFLINE"),
                        tf=os.environ.get("TRANSFORMERS_OFFLINE"))  # fmt: skip

        def harmful(self, text):
            return False

    mod = types.ModuleType("ams.baselines.amemguard_borrowed")
    mod.RandECClassifier = Fake
    monkeypatch.setitem(sys.modules, "ams.baselines.amemguard_borrowed", mod)
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_OFFLINE", raising=False)
    path = Path(__file__).resolve().parents[1] / "scripts/run_protocol_v2.py"
    spec = importlib.util.spec_from_file_location("run_protocol_v2_cost_test", path)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    model = script.randec()
    assert isinstance(model, Fake) and hasattr(model, "randec_cache")  # runtime fix 1
    assert seen == {"hub": "1", "tf": "1"}
