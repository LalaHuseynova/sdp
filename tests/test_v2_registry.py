"""Protocol v2, plan.md step 1.7: condition registry (offline, mock clients only)."""

from __future__ import annotations

import socket
from collections import Counter

import pytest

from ams.research.protocol_v2 import registry as REG
from ams.research.workload import adaptive as AD
from ams.research.workload import design as D
from ams.research.workload.generator import build
from ams.research.workload.integration import LayeredClient, build_states, group_rows
from ams.research.workload.mock import PromptAwareMock
from ams.research.workload.runner import prepare_state
from test_controlled_workload import sources


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("Registry tests forbid networking")

    for key in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, key, deny)
    monkeypatch.setattr(socket, "create_connection", deny)


@pytest.fixture(scope="module")
def world():
    rows, _ = build(sources(), dev_groups=1, test_groups=1)
    gid = sorted({r["group_id"] for r in rows["public/contributions.jsonl"]})[0]
    mock = PromptAwareMock()
    store = build_states(
        rows, gid, LayeredClient(None, "openrouter", mock), LayeredClient(None, "local", mock)
    )
    ext = AD.extend_store(rows, store, REG.adaptive_conditions())
    return gid, group_rows(rows, gid), store, ext


def test_cells_match_protocol_section_4():
    cells = REG.cells()
    fam = Counter(c["family"] for c in cells.values())
    assert fam == {"base": 3, "audit_aware": 2, "framing": 2, "random_detection": 4,
                   "sybil_k": 12, "sybil_own_batch": 9, "laundering_r": 15, "cohabit": 3,
                   "imperfect_audit": 12}  # fmt: skip
    for name, c in cells.items():
        assert len(c["conditions"]) == (1 if c["audits"] == "oracle" else REG.DRAWS), name
    names = [x for c in cells.values() for x in c["conditions"]]
    assert len(names) == len(set(names)) == 272  # every runtime condition, once
    assert set(REG.adaptive_conditions()) == set(names) - set(D.CONDITIONS)
    assert cells["launder_r1"]["params"] == {"r": 0.25}
    assert cells["imp_sybil_k2_late"]["params"] == {"attack": "sybil_k2", "fault": "late"}


def test_worst_case_is_every_attack_cell_without_boundary_verification_or_control():
    worst = REG.WORST_CASE
    # decision 35: uninformative is the "no-signal control", not an attack -> 47 - 1 = 46
    assert len(worst) == len(set(worst)) == 46
    assert REG.CONTROLS == ["uninformative"] and "uninformative" not in worst
    assert "uninformative" in REG.cells()  # still registered and still run
    assert all(REG.cells()[c]["audits"] != "random_bv" for c in worst)
    assert set(REG.cells()) - set(worst) == {*REG.APPENDIX["boundary_verification"],
                                             *REG.CONTROLS}  # fmt: skip


def test_every_table_and_hypothesis_refers_to_registered_cells():
    cells = REG.cells()
    t2 = REG.TABLES["table2"]
    assert t2["no-signal control"] == "uninformative"  # decision 35: a control column
    assert list(t2) == ["localized", "distributed", "no-signal control", "sybil k=2", "sybil k=4",
                        "sybil k=8", "own-batch k=4", "launder r=.25", "launder r=.5",
                        "launder r=1", "audit-aware shift (batch)",
                        "framing (concentrated)"]  # fmt: skip
    assert REG.TABLES["table2b"] == t2
    t6 = REG.TABLES["table6"]
    assert list(t6) == list(AD.IMPERFECT_ATTACKS)
    assert all(list(row) == ["perfect", "fn20", "fp1", "late"] for row in t6.values())
    assert t6["launder_r2"]["perfect"] == "launder_r2"
    assert REG.HYPOTHESES["H4"]["security"] == ["sybil_k4", "sybilown_k4", "launder_r4",
                                           "launder_r3_rand", "sybilown_k4_rand"]  # fmt: skip
    assert REG.HYPOTHESES["H6"]["security"] is None
    assert REG.HYPOTHESES["H6"]["utility"] == ["imp_localized_fp1"]
    for ref in REG.referenced_cells():
        assert ref in cells, ref
    scope = set(REG.SECOND_BACKBONE)
    assert scope == {"localized", "distributed", "imp_localized_fp1",
                     *REG.HYPOTHESES["H4"]["security"]}  # fmt: skip


def test_registry_is_deterministic_with_a_stable_fingerprint():
    assert REG.registry() == REG.registry()
    assert REG.fingerprint() == REG.fingerprint() and len(REG.fingerprint()) == 64


def test_every_condition_builds_with_the_equal_audit_budget(world):
    _, _, _, ext = world
    for condition in REG.adaptive_conditions():
        assert len(ext["audits"][condition]) == D.AUDIT_TICKETS, condition
    for cell in ("sybilown_k4_rand_fu", "cohabit_x1_rand_fu", "imp_launder_r2_fp1"):
        name = REG.cells()[cell]["conditions"][0]
        state = prepare_state(ext["snapshots"][name], ext["audits"][name], "S")
        assert state.evidence.usage.tickets == D.AUDIT_TICKETS


def test_random_cells_have_fixed_distinct_draws(world):
    gid, group, _, _ = world
    for name, cell in REG.cells().items():
        if cell["audits"] == "oracle":
            continue
        draws = []
        for cond in cell["conditions"]:
            once = AD.overlay_and_tickets(group, gid, cond)
            assert once == AD.overlay_and_tickets(group, gid, cond)  # fixed seed
            draws.append(repr((once, AD.pre_reveal_probes(group, gid, cond))))
        assert len(set(draws)) >= 2, name  # the draws differ
