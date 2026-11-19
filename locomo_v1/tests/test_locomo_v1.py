"""Free tests for the LoCoMo second-dataset evaluation (no LLM, no network)."""

from __future__ import annotations

import json
import random

import numpy as np
import pytest

from locomo_v1 import analysis as A
from locomo_v1 import build as B
from locomo_v1 import config as K
from locomo_v1 import execute as E

# ----------------------------------------------------------------------------- statistics


def test_sign_flip_exact():
    assert A.sign_flip_p([0.1] * 8) == pytest.approx(1 / 256)
    assert A.sign_flip_p([-0.1] * 8) == 1.0
    assert A.sign_flip_p([0.1, -0.1] * 4) > 0.5
    assert A.sign_flip_p([]) == 1.0


def test_holm_and_kappa():
    h = A.holm({"a": 0.001, "b": 0.02, "c": 0.04})
    assert h["a"]["reject"] and h["b"]["reject"] and h["c"]["reject"]
    h = A.holm({"a": 0.001, "b": 0.03, "c": 0.04})
    assert h["a"]["reject"] and not h["b"]["reject"] and not h["c"]["reject"]
    assert A.kappa([True, False, True, False], [True, False, True, False]) == 1.0


def test_hypothesis_family_is_fixed():
    assert set(A.HYPOTHESES) == {"H1", "H2", "H3", "H4", "H5", "H6"}
    assert A.HYPOTHESES["H4"][0][5:] == ("lt", K.NI_MARGIN)
    assert set(K.SHAPES) == set(A.ALL4)
    assert K.CONFIRMATORY == tuple(c for c in K.CONVS if c not in ("conv-48", "conv-49"))


# ----------------------------------------------------------------------------- build


@pytest.fixture(scope="module")
def small(tmp_path_factory):
    d = tmp_path_factory.mktemp("build")
    from ams.data.locomo import load_locomo

    conv = {c.sample_id: c for c in load_locomo(K.DATA)}["conv-30"]
    qs = sorted(q.question for q in conv.qa if q.category in K.QA_CATEGORIES)
    # test verdicts: every 3rd question SENSITIVE, to exercise both branches of the gate
    verdicts = {q: ("SENSITIVE" if n % 3 == 0 else "ORDINARY") for n, q in enumerate(qs)}
    info = B.build_conversation("conv-30", d, draws=1, shapes=("1s", "spread"),
                                orientations=(0,), verdicts=verdicts)
    return d, info, verdicts


def test_build_shape(small):
    d, info, _ = small
    jobs = B.load_jobs(d, "conv-30")
    cells = {j["cell"] for j in jobs}
    # clean + per scenario: P1 static + 6 arms x 2 auditors; P2 static + 3 arms x 1 auditor
    assert len(cells) == 1 + 2 * (1 + 12) + 2 * (1 + 3)
    per_cell = {c: sum(j["cell"] == c for j in jobs) for c in cells}
    assert set(per_cell.values()) == {info["questions"]}  # every question in every cell
    ctx = B.load_contexts(d, "conv-30")
    assert all(j["ctx"] in ctx for j in jobs)


def test_audits_and_attacks(small):
    d, _, _ = small
    for s in B.load_scenarios(d, "conv-30"):
        assert len(s["audits"]["A1"]["unsafe"]) == 2 and not s["audits"]["A1"]["safe"]
        if s["attack"] == "P1":
            a2 = s["audits"]["A2"]
            assert len(a2["unsafe"]) + len(a2["safe"]) == 12 and len(a2["unsafe"]) >= 2
        assert len(s["wrong"]) == 8


def test_p2_values_come_from_same_conversation(small):
    from ams.data.locomo import load_locomo

    d, _, _ = small
    conv = {c.sample_id: c for c in load_locomo(K.DATA)}["conv-30"]
    mine = {q.answer for q in conv.qa if q.category in K.QA_CATEGORIES}
    qa = {q.qid: q for q in conv.qa}
    for s in B.load_scenarios(d, "conv-30"):
        if s["attack"] == "P2":
            for t, w in s["wrong"].items():
                assert w in mine and w != qa[t].answer


def test_R_equals_static_except_audited_targets(small):
    d, _, _ = small
    jobs = {}
    for j in B.load_jobs(d, "conv-30"):
        jobs.setdefault(j["cell"], {})[j["qid"]] = j
    for s in B.load_scenarios(d, "conv-30"):
        if s["attack"] != "P1":
            continue
        audited = {q for q, i in s["poison_index"].items() if i in s["audits"]["A1"]["unsafe"]}
        st, r = jobs[f"{s['sid']}|-|static"], jobs[f"{s['sid']}|A1|R"]
        for q in st:
            if q in audited:
                assert s["poison_index"][q] not in r[q]["kept"]
            else:
                assert r[q]["ctx"] == st[q]["ctx"]


def test_audited_poison_never_reaches_its_own_target(small):
    d, _, _ = small
    jobs = {}
    for j in B.load_jobs(d, "conv-30"):
        jobs.setdefault(j["cell"], {})[j["qid"]] = j
    for s in B.load_scenarios(d, "conv-30"):
        for aud, a in s["audits"].items():
            for q, i in s["poison_index"].items():
                if i in a["unsafe"]:
                    for arm in ("C", "M", "S"):
                        cell = jobs.get(f"{s['sid']}|{aud}|{arm}")
                        if cell:
                            assert i not in cell[q]["kept"]


def test_head_is_the_existing_prompt(small):
    from ams.core.prompts import PromptLibrary
    from ams.data.locomo import load_locomo

    conv = {c.sample_id: c for c in load_locomo(K.DATA)}["conv-30"]
    want = PromptLibrary(K.REPO / "prompts").get("locomo_memory_start").render(
        a=conv.speakers[0], b=conv.speakers[1])
    assert B.head(conv) == want


# ----------------------------------------------------------------------------- end to end


def test_mock_end_to_end_and_analysis(small, tmp_path):
    d, _, _ = small
    out = E.run(d, tmp_path, "mock", draws=1, workers=4, convs=("conv-30",))
    assert out["stopped"] is None and out["failed"] == 0
    vals = A.scenario_values(d, tmp_path, 1, convs=("conv-30",))
    assert vals
    static = [v["asr"] for k, v in vals.items() if k[-1] == "static" and v["asr"] is not None]
    assert static and max(static) > 0  # the mock repeats injected values it sees
    # every audited arm withholds the audited poison; S-M identity is a decision property
    one = A.test_part(vals, ("conv-30",), ("asr", ("1s",), ("A1",), "static", "S", "gt", 0.0))
    assert one["n"] == 1


def test_estimate_runs(small):
    d, _, _ = small
    e = E.estimate(d, 1, convs=("conv-30",))
    assert e["unique_answer_prompts"] > 0 and e["calibrated_usd"] > 0


def test_selected_draws():
    assert E.selected({"cell": "P1|conv-26|o0|1s|d4|A1|S"}, 5)
    assert not E.selected({"cell": "P1|conv-26|o0|1s|d4|A1|S"}, 3)
    assert E.selected({"cell": "clean|conv-26|o0"}, 3)


def test_s2id_is_sl_plus_the_frozen_gate(small):
    from ams.data.locomo import load_locomo

    d, _, verdicts = small
    conv = {c.sample_id: c for c in load_locomo(K.DATA)}["conv-30"]
    text = {q.qid: q.question for q in conv.qa}
    ctx = B.load_contexts(d, "conv-30")
    jobs = {}
    for j in B.load_jobs(d, "conv-30"):
        jobs.setdefault(j["cell"], {})[j["qid"]] = j
    owner = conv.speakers[0]
    for s in B.load_scenarios(d, "conv-30"):
        if s["attack"] != "P1":
            continue
        for aud in K.AUDITORS:
            sl, s2 = jobs[f"{s['sid']}|{aud}|SL"], jobs[f"{s['sid']}|{aud}|S2-ID"]
            for q in sl:
                if verdicts[text[q]] == "ORDINARY":
                    assert s2[q]["ctx"] == sl[q]["ctx"]
                else:
                    external = any(f'] {owner} said' not in line
                                   for line in ctx[sl[q]["ctx"]].splitlines()[2:])
                    assert s2[q]["kept"] == ([] if external else sl[q]["kept"])


def test_build_refuses_s2id_without_verdicts(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "load_verdicts", lambda path=None: None)
    with pytest.raises(SystemExit):
        B.build_conversation("conv-30", tmp_path, draws=1, shapes=("1s",), orientations=(0,))
