"""Protocol v2 §8, plan.md step 1.10: the ablation runner, tested OFFLINE on a synthetic
group with mock models. No held-out data, no network, no paid call."""

from __future__ import annotations

import json
import socket
import sqlite3

import pytest

from ams.research.dynamic.ledger import EvidenceSnapshot
from ams.research.dynamic.models import parse_event
from ams.research.dynamic.policies import Policy
from ams.research.protocol_v2 import ablations as AB
from ams.research.protocol_v2 import pipeline as PL
from ams.research.workload import adaptive as AD
from ams.research.workload import design as D
from ams.research.workload import runner as RN
from ams.research.workload.generator import build
from ams.research.workload.integration import LayeredClient, build_states, group_rows
from ams.research.workload.mock import PromptAwareMock
from ams.research.workload.stage2 import ConflictPlaceholderSession
from test_controlled_workload import sources

EXTRA = ("distributed", "sybil_k2", "launder_r2", "random_spread_d0", "random_spread_d0_fu")


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(self, address, *args, **kwargs):
        raise AssertionError("Ablation tests forbid networking")

    monkeypatch.setattr(socket.socket, "connect", deny)


@pytest.fixture(scope="module")
def world():
    rows, _ = build(sources(), dev_groups=1, test_groups=1)
    gid = sorted({r["group_id"] for r in rows["public/contributions.jsonl"]})[0]
    mock = PromptAwareMock()
    store = build_states(
        rows, gid, LayeredClient(None, "openrouter", mock), LayeredClient(None, "local", mock)
    )
    adaptive = [c for c in EXTRA if c not in D.CONDITIONS]
    return rows, group_rows(rows, gid), AD.extend_store(rows, store, adaptive)


def journal(path):
    with sqlite3.connect(path / "queries.sqlite") as db:
        return [json.loads(b) for (b,) in db.execute("SELECT body FROM outcomes ORDER BY rowid")]


def snapshots(store):
    """Every evidence snapshot (with its audits) the ablations touch."""
    for c in ("localized", *EXTRA):
        state = RN.prepare_state(store["snapshots"][c], store["audits"][c], "S")
        yield c, state.evidence


# ----------------------------------------------------------------------------- the grid


def test_grid_is_the_protocol_grid_and_defaults_are_the_frozen_values():
    assert AB.GRID == {"context_gate": (2, 3), "source_gate": (3, 4, 6),
                       "withhold": (0.15, 0.25, 0.35), "tau": (0.7, 0.8, 0.9),
                       "budget": (3, 5, 10)}  # fmt: skip
    assert AB.DEFAULTS == {"context_gate": 2, "source_gate": 4, "withhold": Policy("S").threshold,
                           "tau": PL.TAU, "budget": D.AUDIT_TICKETS}  # fmt: skip
    # one factor at a time; the default value of each knob is the shared default run
    assert AB.variants() == [("context_gate", 3), ("source_gate", 3), ("source_gate", 6),
                             ("withhold", 0.15), ("withhold", 0.35), ("tau", 0.7), ("tau", 0.9),
                             ("budget", 3), ("budget", 10)]  # fmt: skip
    assert AB.METHOD["tau"] == "SL" and AB.METHOD["context_gate"] == "S"
    assert AB.label("source_gate", 6) == "S[source_gate=6]"


# ----------------------------------------------------------------------------- knobs


def test_default_gates_reproduce_the_frozen_scopes_exactly(world):
    _, _, store = world
    default = AB.scopes_with_gates(2, 4)
    n = 0
    for _, ev in snapshots(store):
        for origin in ev.roots.values():
            assert default(ev, origin) == EvidenceSnapshot.active_scopes(ev, origin)
            n += 1
    assert n > 100


def test_gate_variants_only_tighten_or_loosen_their_own_scope(world):
    _, _, store = world
    stricter_ctx, looser_src, stricter_src = (AB.scopes_with_gates(3, 4),
                                              AB.scopes_with_gates(2, 3),
                                              AB.scopes_with_gates(2, 6))  # fmt: skip
    changed = 0
    for _, ev in snapshots(store):
        for origin in ev.roots.values():
            base = set(EvidenceSnapshot.active_scopes(ev, origin))
            assert set(stricter_ctx(ev, origin)) <= base
            assert set(looser_src(ev, origin)) >= base
            assert set(stricter_src(ev, origin)) <= base
            assert set(stricter_ctx(ev, origin)) ^ base <= {"context"}
            assert set(looser_src(ev, origin)) ^ base <= {"source"}
            changed += set(stricter_ctx(ev, origin)) != base
    assert changed > 0  # the distributed placement activates the context gate


def test_variant_overrides_are_scoped_and_always_restored():
    original = EvidenceSnapshot.active_scopes
    for knob, value in AB.variants():
        with AB.variant(knob, value):
            if knob == "withhold":
                assert RN.Policy("S").threshold == value
            if knob == "tau":
                assert value == PL.TAU
            if knob == "budget":
                assert value == D.AUDIT_TICKETS
            if "gate" in knob:
                assert EvidenceSnapshot.active_scopes is not original
    with pytest.raises(RuntimeError), AB.variant("budget", 10):
        raise RuntimeError("boom")
    assert EvidenceSnapshot.active_scopes is original and RN.Policy is Policy
    assert PL.TAU == 0.8 and D.AUDIT_TICKETS == 5
    with pytest.raises(ValueError):
        with AB.variant("unknown", 1):
            pass


def test_default_valued_variant_reproduces_the_pipeline_row_for_row(world, tmp_path):
    rows, _, store = world
    kw = {"conditions": ("localized", "distributed"), "methods": ["S", "SL"], "answer": False}
    PL.evaluate(rows, [store], ConflictPlaceholderSession(), tmp_path / "plain", **kw)
    with AB.variant("withhold", 0.25), AB.variant("context_gate", 2), AB.variant("tau", 0.8):
        PL.evaluate(rows, [store], ConflictPlaceholderSession(), tmp_path / "var", **kw)
    assert journal(tmp_path / "plain") == journal(tmp_path / "var")


# ----------------------------------------------------------------------------- budget


def test_budget_of_five_rebuilds_the_stored_localized_audits(world):
    rows, group, store = world
    built = AB.budget_condition(rows, store, 5, 0)
    assert built["audits"] == store["audits"]["localized"]
    assert built["snapshot"]["evidence"] == store["snapshots"]["localized"]["evidence"]


def test_budget_tickets_subset_and_superset_of_the_oracle(world):
    rows, group, store = world
    gid = store["group_id"]
    oracle = AD._oracle_tickets(group)
    three = AB.budget_tickets(group, gid, 3, 0)
    ten = AB.budget_tickets(group, gid, 10, 0)
    assert len(three) == 3 and set(three) <= set(oracle)
    assert len(ten) == 10 and ten[:5] == oracle
    for _, cid, verdict in ten[5:]:
        role = group["private"][cid]["role"]
        assert role in ("attack_scored", "benign_with_fact")
        assert verdict == ("unsafe" if role == "attack_scored" else "safe_for_use")
    assert AB.budget_tickets(group, gid, 10, 0) == ten  # deterministic per (group, draw)
    assert {tuple(AB.budget_tickets(group, gid, 3, d)) for d in range(6)} != {tuple(three)}
    built = AB.budget_condition(rows, store, 10, 0)
    assert built["snapshot"]["evidence"]["config"]["audit_limit"] == 10
    assert len(built["audits"]) == 10 and all(parse_event(a) for a in built["audits"])


def test_budget_variant_runs_through_the_frozen_runner(world, tmp_path):
    rows, _, store = world
    ext = AB.add_budget(rows, store, draws=2)
    assert {"budget3_d0", "budget3_d1", "budget10_d0", "budget10_d1"} <= set(ext["snapshots"])
    with AB.variant("budget", 10):
        PL.evaluate(rows, [ext], ConflictPlaceholderSession(), tmp_path, methods=["S"],
                    conditions=("budget10_d0",), answer=False)  # fmt: skip
    got = journal(tmp_path)
    assert got and all(r["audit_tickets"] == 10 for r in got)
    assert D.AUDIT_TICKETS == 5


# ----------------------------------------------------------------------------- runner


def test_free_runner_and_summary_end_to_end(world, tmp_path):
    rows, _, store = world
    ext = AB.add_budget(rows, store, draws=2)
    jobs = AB.jobs(draws=2, bv_pairs=[("random_spread", "random_spread_fu")], bv_draws=1)
    out = AB.run_free(rows, [ext], tmp_path / "abl", jobs)
    assert set(out) == {j["name"] for j in jobs}
    res = AB.summarise(rows, tmp_path / "abl", jobs, resamples=200, label="synthetic")
    # every knob value is reported against the shared default, per cell and exposure metric
    s = res["knobs"]["source_gate"]
    assert set(s) == {3, 6} and "localized" in s[3]
    assert set(s[3]["localized"]) <= set(AB.METRICS)
    x = s[3]["localized"]["unaudited_exposure"]
    assert {"default", "variant", "difference", "ci95", "groups"} <= set(x)
    assert res["knobs"]["budget"][10]["localized"]["unaudited_exposure"]["groups"] == 1
    assert "random_spread" in res["boundary_verification"]
    md = AB.render(res)
    assert "synthetic" in md and "retrieval exposure" in md and "descriptive" in md
    assert "S[source_gate=6]" in md and "SL[tau=0.7]" in md
    assert all(r["outcome"] is None for j in jobs for r in journal(tmp_path / "abl" / j["name"]))


def test_cli_refuses_non_dev_groups_before_any_work(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("ab2", "scripts/run_ablations_v2.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    with pytest.raises(Exception, match="dev"):
        cli.check_dev({"G-T00": "test", "G-D00": "dev"})
    cli.check_dev({"G-D00": "dev"})


def test_old_prompt_checkpoints_load_from_a_verified_mirror(world, tmp_path):
    """Stores built before protocol v2 added its generator prompts list fewer prompt files;
    the frozen load check refuses them. The mirror holds exactly the checkpointed files."""
    import copy

    from ams.research.dynamic.models import LedgerError
    from ams.research.sequential.state import RuntimeState

    _, _, store = world
    old = copy.deepcopy({k: store[k] for k in ("snapshots",)})
    body = old["snapshots"]["localized"]["libraries"][0]
    added = next(k for k in body["files"] if k.startswith("v2_generate_attack/"))
    del body["files"][added]  # as if built before that file existed
    with pytest.raises(LedgerError, match="Prompt files changed"):
        RuntimeState.load(old["snapshots"]["localized"])
    fixed = AB.checkpoint_prompts(old, tmp_path / "mirror")
    RuntimeState.load(fixed["snapshots"]["localized"])  # the frozen check passes
    assert not (tmp_path / "mirror" / added).exists()
    assert fixed["snapshots"]["localized"]["libraries"][0]["files"] == body["files"]
    bad = copy.deepcopy(old)
    first = next(iter(bad["snapshots"]["localized"]["libraries"][0]["files"]))
    bad["snapshots"]["localized"]["libraries"][0]["files"][first] = "0" * 64
    with pytest.raises(LedgerError, match="changed since"):
        AB.checkpoint_prompts(bad, tmp_path / "mirror2")


def test_run_script_loads_old_stores_through_the_verified_prompt_mirror(world, tmp_path):
    """Option B runs on the v4 Stage-1 stores (8 Nov), which checkpoint 35 prompt files;
    `run_protocol_v2.prepare_store` must serve them from the verified mirror (step 2.1)."""
    import copy
    import importlib.util
    from pathlib import Path

    from ams.research.sequential.state import RuntimeState

    path = Path(__file__).resolve().parents[1] / "scripts/run_protocol_v2.py"
    spec = importlib.util.spec_from_file_location("run_protocol_v2", path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    rows, _, store = world
    old = copy.deepcopy(store)
    for snap in old["snapshots"].values():
        for body in snap.get("libraries", []):
            for k in [k for k in body["files"] if k.startswith("v2_generat")]:
                del body["files"][k]  # as if built before protocol v2's generator prompts
    out = cli.prepare_store(rows, old, ["localized", "distributed"], tmp_path / "mirror")
    for c in ("localized", "distributed"):
        RuntimeState.load(out["snapshots"][c])  # the frozen load check passes unchanged
        roots = {b["root"] for b in out["snapshots"][c].get("libraries", [])}
        assert roots and all(r.startswith(str((tmp_path / "mirror").resolve())) for r in roots)
