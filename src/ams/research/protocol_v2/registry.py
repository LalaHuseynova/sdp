"""Protocol v2, plan.md step 1.7: the registry of every pre-registered attack condition.

Nothing here defines a condition. The runtime condition names come from the existing
generators in `workload/adaptive.py` (whose code is hashed at the freeze), and the six
draws of a random condition are grouped into one CELL: the unit a table column or a
hypothesis refers to. Draw seeds are fixed: each draw's random numbers are a hash of
(group id, condition name) inside adaptive.py, identical for every method (paired).

  cells()               cell -> family, audits, params, runtime conditions
  TABLES / HYPOTHESES   protocol §10 and §6, as cell references
  WORST_CASE            every attack cell except boundary verification (47; "≈ 50")
  SECOND_BACKBONE       Table 1 + the hypothesis cells (decision 23)
  adaptive_conditions() what `adaptive.extend_store` must build (all but the stored base)
"""

from __future__ import annotations

import re

from ams.research.dynamic.models import digest
from ams.research.workload import adaptive as AD
from ams.research.workload import design as D

VERSION = "protocol-v2-condition-registry-v1"
DRAWS = AD.DEFAULT_DRAWS  # 6 (decision 12)


def runtime_conditions() -> tuple[str, ...]:
    """Every runtime condition of protocol §4, in a fixed order."""
    stress = AD.stress_conditions(DRAWS)
    return (
        *D.CONDITIONS, "shift_batch", "shift_context", *AD.FRAMING_CONDITIONS,
        *AD.random_conditions(DRAWS), *AD.followup_conditions(DRAWS),
        *AD.sweep_conditions(DRAWS), *AD.sweep_followup_conditions(DRAWS),
        *stress, *(f"{c}_fu" for c in stress if "_rand_" in c),  # own-batch, cohabit ± BV
        *AD.imperfect_conditions(DRAWS),
    )  # fmt: skip


def adaptive_conditions() -> tuple[str, ...]:
    return tuple(c for c in runtime_conditions() if c not in D.CONDITIONS)


def _describe(cell: str) -> dict:
    audits = "random_bv" if cell.endswith("_fu") else "random" if "_rand" in cell else "oracle"
    core = cell.removesuffix("_fu").removesuffix("_rand")
    if cell in D.CONDITIONS:
        return {"family": "base", "audits": "oracle", "params": {}}
    if cell.startswith("shift_"):
        return {"family": "audit_aware", "audits": "oracle", "params": {}}
    if cell.startswith("framing_"):
        return {"family": "framing", "audits": "oracle", "params": {}}
    if cell.startswith("random_"):
        placement = core.split("_")[1]  # random detection is always random (no `_rand` tag)
        return {"family": "random_detection", "audits": "random_bv" if audits == "random_bv"
                else "random", "params": {"placement": placement}}  # fmt: skip
    if cell.startswith("imp_"):
        attack, fault = core.removeprefix("imp_").rsplit("_", 1)
        return {"family": "imperfect_audit", "audits": fault,
                "params": {"attack": attack, "fault": fault}}  # fmt: skip
    sweeps = (("sybilown_k", "sybil_own_batch", "k"), ("sybil_k", "sybil_k", "k"),
              ("launder_r", "laundering_r", "r"), ("cohabit_x", "cohabit", None))
    for prefix, family, key in sweeps:
        if core.startswith(prefix):
            n = int(core.removeprefix(prefix))
            params = {} if key is None else {key: n / 4 if key == "r" else n}  # r = n of 4
            return {"family": family, "audits": audits, "params": params}
    raise ValueError(f"Unregistered condition {cell}")


def cells() -> dict:
    out = {}
    for condition in runtime_conditions():
        cell = re.sub(r"_d\d+", "", condition)
        out.setdefault(cell, {**_describe(cell), "conditions": []})["conditions"].append(condition)
    return out


def _oracle_and_random(prefix, labels):
    return {"oracle": {lab: f"{prefix}{n}" for lab, n in labels},
            "random": {lab: f"{prefix}{n}_rand" for lab, n in labels}}  # fmt: skip


_TABLE2 = {
    "localized": "localized", "distributed": "distributed", "uninformative": "uninformative",
    "sybil k=2": "sybil_k2", "sybil k=4": "sybil_k4", "sybil k=8": "sybil_k8",
    "own-batch k=4": "sybilown_k4", "launder r=.25": "launder_r1", "launder r=.5": "launder_r2",
    "launder r=1": "launder_r4", "audit-aware shift (batch)": "shift_batch",
    "framing (concentrated)": "framing_concentrated",
}  # fmt: skip
_LAUNDER = [("r=0", 0), ("r=.25", 1), ("r=.5", 2), ("r=.75", 3), ("r=1", 4)]

TABLES = {
    "table1": {"localized": "localized"},
    "table2": _TABLE2,  # + worst case over WORST_CASE
    "table2b": _TABLE2,
    "table3": _oracle_and_random("sybil_k", [(f"k={k}", k) for k in AD.SYBIL_KS]),
    "table4": {**_oracle_and_random("launder_r", _LAUNDER),
               "innocent_forwarder_utility": "launder_r3_rand"},  # fmt: skip
    "table5": {"framing concentrated": "framing_concentrated",
               "framing spread": "framing_spread", "cohabit": "cohabit_x1",
               "FP audit": "imp_localized_fp1"},  # fmt: skip
    "table6": {a: {"perfect": a, **{k: f"imp_{a}_{k}" for k in AD.IMPERFECT_KINDS}}
               for a in AD.IMPERFECT_ATTACKS},  # fmt: skip
    "table7": {"localized": "localized"},  # on each dataset / backbone
}

# Populations of protocol §6 (endpoints and margins are defined there): `security` = cells
# of the ASR or exposure endpoint, `utility` = cells of the utility endpoint.
HYPOTHESES = {
    "H1": {"security": ["localized"], "utility": ["localized"]},
    "H2": {"security": ["distributed"], "utility": None},
    "H3": {"security": ["localized"], "utility": None},
    "H4": {"security": ["sybil_k4", "sybilown_k4", "launder_r4", "launder_r3_rand",
                        "sybilown_k4_rand"], "utility": ["localized"]},  # fmt: skip
    "H5": {"security": ["localized"], "utility": ["localized"]},
    "H6": {"security": None, "utility": ["imp_localized_fp1"]},
}

WORST_CASE = [c for c, v in cells().items() if v["audits"] != "random_bv"]
APPENDIX = {"boundary_verification": [c for c, v in cells().items() if v["audits"] == "random_bv"]}


def _unique(names):
    return list(dict.fromkeys(names))


def _flatten(x):
    if isinstance(x, dict):
        return [c for v in x.values() for c in _flatten(v)]
    if isinstance(x, list):
        return [c for v in x for c in _flatten(v)]
    return [] if x is None else [x]


SECOND_BACKBONE = _unique([*_flatten(TABLES["table1"]), *_flatten(HYPOTHESES)])


def referenced_cells() -> list[str]:
    return _unique(_flatten([TABLES, HYPOTHESES, WORST_CASE, SECOND_BACKBONE, APPENDIX]))


def registry() -> dict:
    return {"version": VERSION, "draws": DRAWS, "cells": cells(), "tables": TABLES,
            "hypotheses": HYPOTHESES, "worst_case": WORST_CASE,
            "second_backbone": SECOND_BACKBONE, "appendix": APPENDIX,
            "seed_basis": "per draw: hash of (group id, condition name) in "
                          "workload/adaptive.py, identical for every method"}  # fmt: skip


def fingerprint() -> str:
    return digest(registry())
