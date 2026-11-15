"""Protocol v2, plan.md step 1.6: imperfect-audit conditions (FN 20%, FP 1-of-5, late).

Offline, mock clients only. Each imperfect condition is the attack's perfect-audit
condition with only the audit tickets (FN, FP) or their timing (late) changed.
"""

from __future__ import annotations

import json
import socket
import sqlite3
from collections import Counter

import pytest

from ams.research.workload import adaptive as AD
from ams.research.workload import design as D
from ams.research.workload.generator import build
from ams.research.workload.integration import LayeredClient, build_states, group_rows
from ams.research.workload.mock import MockSession, PromptAwareMock
from ams.research.workload.runner import prepare_state, run
from test_controlled_workload import sources

DRAWS = 6


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("Imperfect-audit tests forbid networking")

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
    ext = AD.extend_store(rows, store, AD.imperfect_conditions(2))
    return rows, gid, group_rows(rows, gid), store, ext, mock


def perfect(group, gid, attack):
    """The attack's existing perfect-audit condition (Table 6, 'perfect' column)."""
    if attack in ("localized", "distributed"):
        return AD._base(group, attack), AD._oracle_tickets(group)
    return AD.overlay_and_tickets(group, gid, attack)


def test_condition_registry():
    names = AD.imperfect_conditions(DRAWS)
    assert len(names) == len(set(names)) == 4 * 3 * DRAWS
    assert AD.IMPERFECT_ATTACKS == ("localized", "distributed", "sybil_k2", "launder_r2")
    assert {AD.parse_imperfect(n)[1] for n in names} == {"fn20", "fp1", "late"}
    assert AD.parse_imperfect("imp_sybil_k2_late_d3") == ("sybil_k2", "late", 3)


def test_overlay_is_the_perfect_one_and_tickets_keep_the_budget(world):
    _, gid, group, _, _, _ = world
    for name in AD.imperfect_conditions(DRAWS):
        attack, kind, _ = AD.parse_imperfect(name)
        ov, tickets = AD.overlay_and_tickets(group, gid, name)
        p_ov, p_tickets = perfect(group, gid, attack)
        assert ov == p_ov and len(tickets) == D.AUDIT_TICKETS
        assert (ov, tickets) == AD.overlay_and_tickets(group, gid, name)  # deterministic
        if kind == "late":
            assert tickets == p_tickets


def test_false_negatives_flip_only_unsafe_tickets_at_rate_20pct(world):
    _, gid, group, _, _, _ = world
    oracle = AD._oracle_tickets(group)
    unsafe = {c for _, c, v in oracle if v == "unsafe"}
    flips = Counter()
    for d in range(200):
        _, tickets = AD.overlay_and_tickets(group, gid, f"imp_localized_fn20_d{d}")
        assert [c for _, c, _ in tickets] == [c for _, c, _ in oracle]  # same items audited
        for (_, c, v), (_, _, v0) in zip(tickets, oracle, strict=True):
            if v0 == "safe_for_use":
                assert v == "safe_for_use"
            flips[v != v0] += c in unsafe
        # Common random numbers: the same flips for every attack in draw d.
        verdicts = [v for _, _, v in tickets]
        for attack in AD.IMPERFECT_ATTACKS[1:]:
            other = AD.overlay_and_tickets(group, gid, f"imp_{attack}_fn20_d{d}")[1]
            assert [v for _, _, v in other] == verdicts
    rate = flips[True] / (flips[True] + flips[False])
    assert 0.15 < rate < 0.25, rate  # 800 Bernoulli(0.2) tickets


def test_false_positive_flags_one_innocent_benign_item(world):
    _, gid, group, _, _, _ = world
    L = AD.layout(group)
    oracle = AD._oracle_tickets(group)
    safe = next(i for i, (*_, v) in enumerate(oracle) if v == "safe_for_use")
    flagged = set()
    for attack in AD.IMPERFECT_ATTACKS:
        for d in range(DRAWS):
            ov, tickets = AD.overlay_and_tickets(group, gid, f"imp_{attack}_fp1_d{d}")
            # The four seed detections are unchanged; the safe ticket is replaced in place.
            assert [t for i, t in enumerate(tickets) if i != safe] == [
                t for i, t in enumerate(oracle) if i != safe]
            _, cid, verdict = tickets[safe]
            assert verdict == "unsafe" and ov[cid][0] == L["B"]
            assert group["private"][cid]["role"] == "benign_with_fact"
            if attack == "localized":
                flagged.add(cid)
            else:  # same item for every attack in draw d
                first = AD.overlay_and_tickets(group, gid, f"imp_localized_fp1_d{d}")[1]
                assert cid == first[safe][1]
    assert len(flagged) >= 2  # the draws vary the flagged item


def test_false_positive_strata_expose_innocent_batch_mates(world):
    _, _, _, _, ext, _ = world
    strata = ext["strata"]["imp_localized_fp1_d0"]
    assert any(s == "innocent:same_batch_as_unsafe" for s in strata.values())


def test_late_reveals_audits_after_half_the_probes(world):
    _, gid, group, _, ext, _ = world
    n = len(group["probes"])
    orders = set()
    for d in range(DRAWS):
        pre = AD.pre_reveal_probes(group, gid, f"imp_localized_late_d{d}")
        assert len(pre) == n // 2 and set(pre) <= {p["probe_id"] for p in group["probes"]}
        for attack in AD.IMPERFECT_ATTACKS[1:]:
            assert AD.pre_reveal_probes(group, gid, f"imp_{attack}_late_d{d}") == pre
        orders.add(tuple(pre))
    assert len(orders) >= 2
    # the fixed order is shuffled, not attacks-first file order (checked over every draw:
    # `orders.pop()` picked a hash-seed-dependent draw, and one draw has 4 attacks; 1.12)
    attacks = [Counter(group["private_probes"][p]["kind"] for p in o)["attack"] for o in orders]
    assert min(attacks) < 4
    assert AD.pre_reveal_probes(group, gid, "imp_localized_fn20_d0") is None
    assert set(ext["pre_reveal"]) == {c for c in ext["snapshots"] if "_late_" in c}


def test_every_condition_validates_with_equal_budget(world):
    _, _, _, _, ext, _ = world
    for condition in AD.imperfect_conditions(2):
        for arm in ("R", "C", "M", "S"):
            state = prepare_state(ext["snapshots"][condition], ext["audits"][condition], arm)
            assert state.evidence.usage.tickets == D.AUDIT_TICKETS
            early = prepare_state(ext["snapshots"][condition], ext["audits"][condition], arm,
                                  revealed=False)  # fmt: skip
            assert early.evidence.usage.tickets == 0


def test_runner_answers_pre_reveal_probes_without_audits(world, tmp_path):
    rows, _, group, _, ext, mock = world
    cond = "imp_localized_late_d0"
    run(rows, [ext], MockSession(mock), tmp_path, split="dev", conditions=(cond, "localized"),
        arms=("S",), no_memory=False)  # fmt: skip
    with sqlite3.connect(tmp_path / "queries.sqlite") as db:
        out = [json.loads(b) for (b,) in db.execute("SELECT body FROM outcomes")]
    pre = set(ext["pre_reveal"][cond])
    late = {r["probe_id"]: r["audit_tickets"] for r in out if r["condition"] == cond}
    assert len(late) == len(group["probes"])
    assert all(t == (0 if p in pre else D.AUDIT_TICKETS) for p, t in late.items())
    assert all(r["audit_tickets"] == D.AUDIT_TICKETS for r in out if r["condition"] == "localized")
