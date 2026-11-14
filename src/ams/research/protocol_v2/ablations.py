"""Protocol v2 §8, plan.md step 1.10: the ablation runner (dev only, descriptive).

One knob at a time, every other knob at its frozen value:
  context_gate {2, 3}      unsafe items S needs in >= 2 batches of a context (frozen: 2)
  source_gate  {3, 4, 6}   unsafe items S needs over >= 2 qualifying contexts (frozen: 4)
  withhold     {.15,.25,.35} penalty at which S withholds a record (frozen: 0.25)
  tau          {.7,.8,.9}  content-lineage threshold, on SL (frozen: 0.8)
  budget       {3, 5, 10}  audit tickets, localized placement (frozen: 5); 3 = a random
                           3 of the 5 oracle tickets, 10 = the 5 + 5 random benign or scored
                           items with their true verdict; 6 draws each (paired seeds)
  boundary verification    on vs off: the registered `_fu` cells vs their plain cells

Nothing in the frozen code is edited. Each knob is a SCOPED runtime override (`variant`),
restored on exit, the same pattern as `evidence_memoization`: gates replace
`EvidenceSnapshot.active_scopes` with a parameterised copy that equals the frozen method
at the default values (tested); `withhold` makes the runner's Policy carry the threshold;
`tau` sets the pipeline's lineage threshold; `budget` sets the runner's equal-budget
constant to the variant's ticket count. Runs go through `pipeline.evaluate` unchanged.

Free mode only (retrieval exposure; no answer, no judge, no network). Answer-level
ablations are plan.md step 6.2 (paid, own approval).
"""

from __future__ import annotations

import contextlib
import functools
import json
import random
import re
import sqlite3
from pathlib import Path
from unittest import mock

import numpy as np

from ams.research.dynamic.ledger import EvidenceSnapshot, LedgerConfig
from ams.research.dynamic.models import check, digest, parse_event
from ams.research.dynamic.policies import Policy
from ams.research.protocol_v2 import analysis as A
from ams.research.protocol_v2 import pipeline as PL
from ams.research.protocol_v2 import registry as REG
from ams.research.workload import adaptive as AD
from ams.research.workload import design as D
from ams.research.workload import runner as RN
from ams.research.workload.integration import group_rows

VERSION = "protocol-v2-ablations-v1"
GRID = {"context_gate": (2, 3), "source_gate": (3, 4, 6), "withhold": (0.15, 0.25, 0.35),
        "tau": (0.7, 0.8, 0.9), "budget": (3, 5, 10)}  # fmt: skip
DEFAULTS = {"context_gate": 2, "source_gate": 4, "withhold": Policy("S").threshold,
            "tau": PL.TAU, "budget": D.AUDIT_TICKETS}  # fmt: skip
METHOD = {"context_gate": "S", "source_gate": "S", "withhold": "S", "budget": "S", "tau": "SL"}
CELLS = ("localized", "distributed", "uninformative")  # gates and withhold threshold
METRICS = ("unaudited_exposure", "useful_exposure", "key_exposure", "innocent_useful_exposure",
           "relay_exposure")  # fmt: skip
BV_PAIRS = [(c, c + "_fu") for c in REG.cells() if c + "_fu" in REG.cells()]


def variants() -> list[tuple[str, float]]:
    return [(k, v) for k, values in GRID.items() for v in values if v != DEFAULTS[k]]


def label(knob, value) -> str:
    return f"{METHOD[knob]}[{knob}={value}]"


# ----------------------------------------------------------------------------- knobs


def scopes_with_gates(context_gate: int, source_gate: int):
    """`EvidenceSnapshot.active_scopes` with the two gate counts as parameters. At (2, 4)
    it is the frozen method line for line; only the named count changes (the qualifying-
    context rule of the source gate stays the frozen >= 2 items in >= 2 batches)."""

    def active_scopes(self, origin):
        if origin.attribution != "authenticated_external":
            return ()
        bad = [p for p, v in self.observations()
               if v == "unsafe" and p.contributor_id == origin.contributor_id]  # fmt: skip
        local = [p for p in bad if p.context_id == origin.context_id]
        scopes = []
        if any(p.batch_id == origin.batch_id for p in local):
            scopes.append("batch")
        if len(local) >= context_gate and len({p.batch_id for p in local}) >= 2:
            scopes.append("context")
        qualifying = {
            p.context_id for p in bad
            if len([r for r in bad if r.context_id == p.context_id]) >= 2
            and len({r.batch_id for r in bad if r.context_id == p.context_id}) >= 2
        }  # fmt: skip
        if len(bad) >= source_gate and len(qualifying) >= 2:
            scopes.append("source")
        return tuple(scopes)

    return active_scopes


@contextlib.contextmanager
def variant(knob=None, value=None):
    """Scoped override of one knob; everything is restored on exit (also on error)."""
    with contextlib.ExitStack() as stack:
        if knob in ("context_gate", "source_gate"):
            gates = {"context_gate": DEFAULTS["context_gate"],
                     "source_gate": DEFAULTS["source_gate"], knob: value}  # fmt: skip
            stack.enter_context(mock.patch.object(EvidenceSnapshot, "active_scopes",
                                                  scopes_with_gates(**gates)))  # fmt: skip
        elif knob == "withhold":
            policy = functools.partial(Policy, threshold=value)
            stack.enter_context(mock.patch.object(RN, "Policy", policy))
        elif knob == "tau":
            stack.enter_context(mock.patch.object(PL, "TAU", value))
        elif knob == "budget":
            stack.enter_context(mock.patch.object(D, "AUDIT_TICKETS", value))
        elif knob is not None:
            raise ValueError(f"Unknown ablation knob {knob}")
        yield


# ----------------------------------------------------------------------------- budget


def budget_tickets(group, gid, n, draw) -> list:
    """3: a random 3 of the 5 oracle tickets; 10: the 5 + 5 random benign or scored items
    (true verdict). Copies are never drawn (they have no audit use of their own)."""
    oracle = AD._oracle_tickets(group)
    if n == len(oracle):
        return oracle
    rng = random.Random(int(digest(["ablation-budget-v1", gid, n, draw]), 16))
    if n < len(oracle):
        return [oracle[i] for i in sorted(rng.sample(range(len(oracle)), n))]
    audited = {c for _, c, _ in oracle}
    roles = ("attack_scored", "benign_with_fact")
    pool = sorted(c for c, p in group["private"].items()
                  if c not in audited and p["role"] in roles)  # fmt: skip
    extra = rng.sample(pool, n - len(oracle))
    return oracle + [("t_" + digest([gid, "ablation-budget", cid])[:20], cid,
                      "unsafe" if group["private"][cid]["role"] == "attack_scored"
                      else "safe_for_use") for cid in extra]  # fmt: skip


def budget_condition(rows, store, n, draw) -> dict:
    """The stored localized snapshot with an n-ticket audit set (no model call)."""
    gid = store["group_id"]
    group = group_rows(rows, gid)
    base = store["snapshots"]["localized"]
    ev = base["evidence"]
    config = {**ev["config"], "audit_limit": n}
    events = tuple(parse_event(e) for e in ev["events"])
    evidence = EvidenceSnapshot(LedgerConfig(**config), events, ev["as_of"])
    tickets = budget_tickets(group, gid, n, draw)
    audits = AD._audits(group, gid, evidence, tickets)
    EvidenceSnapshot(evidence.config, (*evidence.events, *audits), n)  # validates
    L = AD.layout(group)
    owners = {L["A"]: "attacker", L["B"]: "innocent", L["U"]: "unrelated"}
    return {"snapshot": {**base, "evidence": {**ev, "config": config}},
            "audits": [AD._plain(a) for a in audits],
            "strata": AD.strata(group, AD._base(group, "localized"), tickets, owners)}  # fmt: skip


def add_budget(rows, store, draws=REG.DRAWS) -> dict:
    out = {**store, "snapshots": dict(store["snapshots"]), "audits": dict(store["audits"]),
           "strata": dict(store.get("strata", {}))}  # fmt: skip
    for n in (v for v in GRID["budget"] if v != DEFAULTS["budget"]):
        for i in range(draws):
            built = budget_condition(rows, store, n, i)
            c = f"budget{n}_d{i}"
            out["snapshots"][c], out["audits"][c], out["strata"][c] = (
                built["snapshot"], built["audits"], built["strata"])  # fmt: skip
    return out


# ----------------------------------------------------------------------------- old stores


def checkpoint_prompts(store, mirror: Path) -> dict:
    """Dev Stage-1 stores (8 Nov) checkpoint every prompt file then present; protocol v2
    later ADDED 4 generator prompts (never used by the memory), so the frozen load check
    refuses them. Copy exactly the checkpointed files, each verified against its stored
    hash, into a mirror and point the store (in memory only) at it. The frozen check then
    still runs unchanged; any changed or missing checkpointed file fails here."""
    out = {**store, "snapshots": {}}
    for cond, snap in store["snapshots"].items():
        libs = []
        for body in snap.get("libraries", []):
            root = Path(mirror) / digest(sorted(body["files"].items()))[:16]
            for rel, h in body["files"].items():
                text = (Path(body["root"]) / rel).read_text()
                check(digest(text) == h, f"Prompt file {rel} changed since the checkpoint")
                dst = root / rel
                if not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_text(text)
                check(dst.read_text() == text, f"Prompt mirror {dst} differs")
            libs.append({**body, "root": str(root.resolve())})
        out["snapshots"][cond] = {**snap, "libraries": libs} if libs else snap
    return out


# ----------------------------------------------------------------------------- runner


def jobs(draws=REG.DRAWS, bv_pairs=None, bv_draws=REG.DRAWS) -> list[dict]:
    cells = REG.cells()
    out = [{"name": "default", "knob": None, "value": None, "conditions": CELLS,
            "methods": ["S", "SL"]}]  # fmt: skip
    for knob, v in variants():
        conditions = (tuple(f"budget{v}_d{i}" for i in range(draws)) if knob == "budget"
                      else ("localized",) if knob == "tau" else CELLS)  # fmt: skip
        out.append({"name": f"{knob}_{v}", "knob": knob, "value": v,
                    "conditions": conditions, "methods": [METHOD[knob]]})  # fmt: skip
    pairs = BV_PAIRS if bv_pairs is None else bv_pairs
    bv = tuple(c for off, on in pairs for cell in (off, on)
               for c in cells[cell]["conditions"][:bv_draws])  # fmt: skip
    out.append({"name": "boundary_verification", "knob": None, "value": None,
                "conditions": bv, "methods": ["S"], "pairs": [list(p) for p in pairs]})  # fmt: skip
    return out


def run_free(rows, stores, root: Path, job_list) -> dict:
    """Retrieval only, the logged Stage-2 conflict placeholder (no answer call possible)."""
    from ams.research.workload.stage2 import ConflictPlaceholderSession

    out = {}
    for j in job_list:
        with variant(j["knob"], j["value"]):
            out[j["name"]] = PL.evaluate(rows, stores, ConflictPlaceholderSession(),
                                         Path(root) / j["name"], conditions=j["conditions"],
                                         methods=j["methods"], answer=False)  # fmt: skip
    return out


def _journal(path: Path):
    db = sqlite3.connect(f"file:{path / 'queries.sqlite'}?mode=ro", uri=True)
    try:
        for text, h in db.execute("SELECT body,hash FROM outcomes ORDER BY rowid"):
            row = json.loads(text)
            check(digest(row) == h, "Saved outcome modified")
            yield row
    finally:
        db.close()


def _rows(root, job_list):
    """Variant rows relabelled as their own method; budget draws as localized draws."""
    for j in job_list:
        for r in _journal(Path(root) / j["name"]):
            if j["knob"]:
                r["method"] = label(j["knob"], j["value"])
            if j["knob"] == "budget":
                r["condition"] = re.sub(r"^budget\d+", "localized", r["condition"])
            yield r


def _compare(idx, metric, a, b, W):
    """a, b = (cell, method). Paired group difference b - a."""
    va = A.group_values(idx, metric, [a[0]], a[1])
    vb = A.group_values(idx, metric, [b[0]], b[1])
    d = vb - va
    if np.all(np.isnan(d)):
        return None
    return {"default": A._mean(va), "variant": A._mean(vb), "difference": A._mean(d),
            "ci95": A.ci95(A.boot_mean(d, W)), "groups": int(np.sum(~np.isnan(d)))}  # fmt: skip


def summarise(rows, root, job_list, *, resamples=A.RESAMPLES, seed=A.SEED, label: str) -> dict:
    idx = A.index(list(_rows(root, job_list)), A.probe_info(rows))
    W = A.group_weights(len(idx.groups), seed, resamples)
    knobs = {}
    for j in job_list:
        if not j["knob"]:
            continue
        base, lab = METHOD[j["knob"]], label_of(j)
        cells = ("localized",) if j["knob"] in ("tau", "budget") else CELLS
        knobs.setdefault(j["knob"], {})[j["value"]] = {
            cell: {m: x for m in METRICS
                   if (x := _compare(idx, m, (cell, base), (cell, lab), W))}
            for cell in cells}  # fmt: skip
    bv = {}
    for j in job_list:
        for off, on in j.get("pairs", []):
            bv[off] = {m: x for m in METRICS if (x := _compare(idx, m, (off, "S"), (on, "S"), W))}
    return {"version": VERSION, "label": label, "groups": len(idx.groups), "seed": seed,
            "resamples": resamples, "grid": GRID, "defaults": DEFAULTS, "knobs": knobs,
            "boundary_verification": bv}  # fmt: skip


def label_of(j):
    return label(j["knob"], j["value"])


# ----------------------------------------------------------------------------- render

_HEAD = {"unaudited_exposure": "unaudited exposure ↓",
         "useful_exposure": "useful-fact exposure ↑", "key_exposure": "key-stratum exposure ↑",
         "innocent_useful_exposure": "innocent exposure ↑",
         "relay_exposure": "relay exposure ↓"}  # fmt: skip


def _fmt(x, key):
    if not x:
        return "–"
    ci = x["ci95"]
    return (f"{A.pct(x[key])} (Δ {A.pct(x['difference'], True)} "
            f"[{A.pct(ci[0], True)}, {A.pct(ci[1], True)}])")  # fmt: skip


def render(res) -> str:
    head = "| Cell | Run | " + " | ".join(_HEAD[m] for m in METRICS) + " |"
    rule = "|" + "---|" * (len(METRICS) + 2)
    out = [f"## Ablations (protocol §8; data: {res['label']}, {res['groups']} groups)", "",
           "All values are **retrieval exposure** (%), **descriptive**, with unadjusted "
           "paired 95% CIs over groups; Δ = variant − default. Ablations never change the "
           "main method. Answer-level ablations: plan.md step 6.2 (paid).", ""]  # fmt: skip
    for knob, values in res["knobs"].items():
        base = METHOD[knob]
        out += [f"### {knob} (frozen: {DEFAULTS[knob]}; method {base})", "", head, rule]
        cells = next(iter(values.values()))
        for cell in cells:
            first = next(iter(values.values()))[cell]
            out.append(f"| {cell} | {base} (default) | " + " | ".join(
                A.pct(first[m]["default"]) if m in first else "–" for m in METRICS) + " |")
            for v, per_cell in values.items():
                x = per_cell[cell]
                out.append(f"| {cell} | {label(knob, v)} | "
                           + " | ".join(_fmt(x.get(m), "variant") for m in METRICS) + " |")
        out.append("")
    out += ["### Boundary verification (method S; off = plain random cell, on = `_fu`)", "",
            head.replace("| Run |", "| Value |"), rule]
    for off, x in res["boundary_verification"].items():
        out.append(f"| {off} | off → on | " + " | ".join(
            (f"{A.pct(x[m]['default'])} → " + _fmt(x[m], "variant")) if m in x else "–"
            for m in METRICS) + " |")  # fmt: skip
    return "\n".join(out) + "\n"
