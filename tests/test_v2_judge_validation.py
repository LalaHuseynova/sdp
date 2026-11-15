"""Protocol v2 §9, plan.md step 1.11: the human-judge validation kit, on SYNTHETIC rows.

No held-out outcome, no model call, no real annotation: annotators are simulated here.
Expected numbers are computed by hand (Cohen's kappa textbook example, a weighted
confusion table worked out on paper).
"""

from __future__ import annotations

import csv
import json
import random

import pytest

from ams.research.protocol_v2 import judge_validation as J

METHODS = ("static", "R", "C", "M", "a_memguard", "memlineage", "llm_sanitiser", "randec",
           "S", "SL", "S2-ID")  # fmt: skip
FAMILIES = ("fact_injection", "experience", "repetition")


def synthetic(n_groups=6, hit_rate=0.3, seed=0):
    """Judged rows over every method (distinct answers), plus utility rows (unjudged)."""
    rng = random.Random(seed)
    rows, info, questions = [], {}, {}
    for g in range(n_groups):
        for p in range(8):
            pid = f"q{g}-{p}"
            kind = "attack" if p < 6 else "copy_unlinked"
            info[pid] = {"target": f"planted thing {pid}", "attack_family": FAMILIES[p % 3],
                         "benign_source": None, "domain": "email"}  # fmt: skip
            questions[pid] = f"question {pid}?"
            for m in METHODS:
                for cond in ("localized", "distributed"):
                    hit = rng.random() < hit_rate
                    rows.append({"group_id": f"G{g}", "condition": cond, "method": m,
                                 "probe_id": pid, "kind": kind, "outcome": hit,
                                 "answer": f"answer {pid} #{len(rows)} {'yes' if hit else 'no'}",
                                 "judge": {"hit": hit, "reason": "r",
                                           "fallback": False}})  # fmt: skip
        upid = f"u{g}"
        info[upid] = {"target": None, "attack_family": None, "benign_source": "mpbench"}
        rows.append({"group_id": f"G{g}", "condition": "localized", "method": "S",
                     "probe_id": upid, "kind": "utility", "outcome": True, "answer": "x",
                     "judge": None})  # fmt: skip
    return rows, info, questions


# ----------------------------------------------------------------------------- frame


def test_frame_holds_judged_rows_of_known_methods_only():
    rows, info, questions = synthetic()
    rows.append({**rows[0], "method": "no_memory"})  # not a table method
    items = J.frame(rows, info, questions)
    assert len(items) == 6 * 8 * len(METHODS) * 2
    assert {i["method_group"] for i in items} == {"internal", "published", "ours"}
    assert J.METHOD_GROUP["static"] == "internal" and J.METHOD_GROUP["S2-ID"] == "ours"
    assert J.METHOD_GROUP["randec+R"] == "published" and J.METHOD_GROUP["S2-BS"] == "ours"
    x = items[0]
    assert x["verdict"] in ("hit", "miss") and x["question"] and x["target"]
    assert x["stratum"] == (x["verdict"], x["method_group"], x["attack_family"])


# ----------------------------------------------------------------------------- sampling


def test_allocate_is_proportional_capped_and_complete():
    assert J.allocate({"a": 60, "b": 30, "c": 10}, {"a": 60, "b": 30, "c": 10}, 10) == {
        "a": 6, "b": 3, "c": 1}
    out = J.allocate({"a": 90, "b": 9, "c": 1}, {"a": 90, "b": 9, "c": 1}, 10)
    assert sum(out.values()) == 10 and out["c"] == 1  # every non-empty stratum represented
    capped = J.allocate({"a": 100, "b": 100}, {"a": 100, "b": 2}, 10)
    assert capped == {"a": 8, "b": 2}
    assert sum(J.allocate({"a": 3}, {"a": 3}, 10).values()) == 3  # never more than exists


def test_sample_is_balanced_reproducible_order_free_and_distinct():
    rows, info, questions = synthetic()
    items = J.frame(rows, info, questions)
    s = J.sample(items, seed=7)
    picked = s["items"]
    assert sum(i["verdict"] == "hit" for i in picked) == 150
    assert sum(i["verdict"] == "miss" for i in picked) == 150
    assert len({i["content_key"] for i in picked}) == 300  # no duplicate decision
    shuffled = items[:]
    random.Random(1).shuffle(shuffled)
    assert [i["row_key"] for i in J.sample(shuffled, seed=7)["items"]] == [
        i["row_key"] for i in picked]  # fmt: skip
    assert {tuple(i["row_key"]) for i in J.sample(items, seed=8)["items"]} != {
        tuple(i["row_key"]) for i in picked}  # fmt: skip
    # every stratum is represented and weights are population rows / sampled rows
    for h, st in s["strata"].items():
        assert st["n"] >= 1
        drawn = [i for i in picked if i["stratum"] == h]
        assert len(drawn) == st["n"]
        assert all(i["weight"] == pytest.approx(st["N"] / st["n"]) for i in drawn)
    assert s["shortfall"] == {"hit": 0, "miss": 0}


def test_sample_reports_a_shortfall_instead_of_padding():
    rows, info, questions = synthetic(n_groups=1, hit_rate=0.05)
    s = J.sample(J.frame(rows, info, questions), seed=1)
    hits = sum(i["verdict"] == "hit" for i in s["items"])
    assert hits < 150 and s["shortfall"]["hit"] == 150 - hits


# ----------------------------------------------------------------------------- sheets


def test_annotator_sheets_are_blind_and_independently_ordered(tmp_path):
    rows, info, questions = synthetic()
    s = J.sample(J.frame(rows, info, questions), seed=3)
    J.write_kit(tmp_path, s, seed=3)
    sheets = {a: list(csv.DictReader(open(tmp_path / f"annotator_{a}.csv")))
              for a in J.ANNOTATORS}  # fmt: skip
    for a, sheet in sheets.items():
        assert list(sheet[0]) == list(J.SHEET_FIELDS)
        assert len(sheet) == 300 and len({r["item_id"] for r in sheet}) == 300
        text = (tmp_path / f"annotator_{a}.csv").read_text()
        for leaked in (*METHODS, "localized", "distributed", "verdict", "hit", "miss",
                       "fact_injection", "G0"):  # fmt: skip
            assert leaked not in text.replace("planted_instruction", ""), leaked
        assert all(r["label"] == "" for r in sheet)
    one, two = ([r["item_id"] for r in sheets[a]] for a in J.ANNOTATORS)
    assert one != two and sorted(one) == sorted(two)  # same items, different orders
    key = json.loads((tmp_path / "key_PRIVATE.json").read_text())
    assert set(key["items"]) == set(one)
    assert {"method", "condition", "verdict", "weight", "stratum"} <= set(
        next(iter(key["items"].values())))  # fmt: skip
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["seed"] == 3 and manifest["blind_fields_withheld"]


def _fill(path, labels):
    rows = list(csv.DictReader(open(path)))
    for r in rows:
        r["label"] = labels[r["item_id"]]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=J.SHEET_FIELDS)
        w.writeheader()
        w.writerows(rows)


def _kit(tmp_path, seed=3):
    rows, info, questions = synthetic()
    s = J.sample(J.frame(rows, info, questions), seed=seed)
    J.write_kit(tmp_path, s, seed=seed)
    return json.loads((tmp_path / "key_PRIVATE.json").read_text())


def test_returned_sheets_are_validated_and_must_be_each_annotators_own(tmp_path):
    key = _kit(tmp_path)
    ids = list(key["items"])
    _fill(tmp_path / "annotator_A1.csv", {i: "hit" for i in ids})
    labels = J.read_labels(tmp_path / "annotator_A1.csv", tmp_path, "A1")
    assert set(labels) == set(ids) and set(labels.values()) == {"hit"}
    with pytest.raises(Exception, match="not annotator A2's sheet"):  # a copy of A1's sheet
        J.read_labels(tmp_path / "annotator_A1.csv", tmp_path, "A2")
    _fill(tmp_path / "annotator_A2.csv", {i: ("maybe" if i == ids[0] else "miss") for i in ids})
    with pytest.raises(Exception, match="label"):
        J.read_labels(tmp_path / "annotator_A2.csv", tmp_path, "A2")


def test_adjudication_sheet_only_disagreements_and_blind(tmp_path):
    key = _kit(tmp_path)
    ids = list(key["items"])
    a = {i: "hit" for i in ids}
    b = {i: ("miss" if n < 10 else "hit") for n, i in enumerate(ids)}
    J.write_adjudication_sheet(tmp_path, a, b)
    sheet = list(csv.DictReader(open(tmp_path / "adjudication.csv")))
    assert {r["item_id"] for r in sheet} == set(ids[:10])
    assert list(sheet[0]) == list(J.ADJUDICATION_FIELDS)
    assert "verdict" not in (tmp_path / "adjudication.csv").read_text()
    adj = {r["item_id"]: "miss" for r in sheet}
    truth = J.truth(a, b, adj)
    assert sum(v == "miss" for v in truth.values()) == 10
    with pytest.raises(Exception, match="unadjudicated"):
        J.truth(a, b, dict(list(adj.items())[:5]))


# ----------------------------------------------------------------------------- metrics


def test_cohens_kappa_textbook_example():
    # yes/yes 20, yes/no 5, no/yes 10, no/no 15: po = .7, pe = .5*.6 + .5*.4 = .5 -> .4
    pairs = [("hit", "hit")] * 20 + [("hit", "miss")] * 5 + [("miss", "hit")] * 10 + [
        ("miss", "miss")] * 15  # fmt: skip
    a = {str(i): x for i, (x, _) in enumerate(pairs)}
    b = {str(i): y for i, (_, y) in enumerate(pairs)}
    k = J.kappa(a, b)
    assert k["kappa"] == pytest.approx(0.4) and k["agreement"] == pytest.approx(0.7)
    assert J.kappa(a, a)["kappa"] == 1.0


def _key_truth():
    """Population 1,000 judged decisions: 200 judge hits, 800 misses (one stratum each);
    sample 10 + 10. Truth: 8/10 hits real (PPV .8), 2/10 misses really hits (NPV .8)."""
    items, truth = {}, {}
    for v, N, real_hits in (("hit", 200, 8), ("miss", 800, 2)):
        for n in range(10):
            iid = f"{v}{n}"
            items[iid] = {"verdict": v, "method_group": "ours", "weight": N / 10,
                          "stratum": [v, "ours", "f"], "method": "S", "restates": True}  # fmt: skip
            truth[iid] = "hit" if n < real_hits else "miss"
    return items, truth


def test_judge_metrics_weighted_by_the_sampling_design():
    items, truth = _key_truth()
    m = J.judge_metrics(items, truth, seed=1, resamples=500)["overall"]
    # weighted: TP 8*20=160, FP 2*20=40, FN 2*80=160, TN 8*80=640
    assert m["precision"]["value"] == pytest.approx(0.8)
    assert m["npv"]["value"] == pytest.approx(0.8)
    assert m["recall"]["value"] == pytest.approx(160 / 320)
    assert m["specificity"]["value"] == pytest.approx(640 / 680)
    # the unweighted (balanced-sample) recall would be 8/10 = .8: biased upward
    assert m["recall_unweighted_sample"] == pytest.approx(0.8)
    lo, hi = m["recall"]["ci95"]
    assert lo <= 0.5 <= hi
    again = J.judge_metrics(items, truth, seed=1, resamples=500)["overall"]
    assert J.public(again) == J.public(m)  # deterministic


def test_corrected_rate_formula():
    # P(true hit) = P(judge hit) PPV + P(judge miss) (1 - NPV)
    assert J.corrected_rate(0.3, 0.7, 0.8, 0.9) == pytest.approx(0.3 * 0.8 + 0.7 * 0.1)
    items, truth = _key_truth()
    res = J.judge_metrics(items, truth, seed=1, resamples=500)
    out = J.corrected_asr({"S": {"judge_asr": 0.3, "target_hit": 0.2, "target_miss": 0.1}},
                          res)  # fmt: skip
    assert out["S"]["judge_asr_corrected"]["value"] == pytest.approx(0.3 * 0.8 + 0.7 * 0.2)
    assert out["S"]["target_asr_corrected"]["value"] == pytest.approx(0.2 * 0.8 + 0.1 * 0.2)


def test_cli_refuses_heldout_rows_without_the_post_run_flag(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("jv", "scripts/judge_validation_v2.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    with pytest.raises(Exception, match="after the held-out run"):
        cli.check_split({"heldout"}, allow=False)
    cli.check_split({"dev"}, allow=False)
