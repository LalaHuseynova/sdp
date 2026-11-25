"""Equivalence of the dialogue governance layer with the frozen MPBench layer (free, no API).

On frozen Option B Stage-1 stores (MPBench roles only), every arm's state is prepared twice: with
the frozen `runner.prepare_state` / `RuntimeState` and with `governance.prepare_state` /
`DialogueRuntimeState`. Every probe is retrieved through both, with an identical deterministic
conflict oracle that contradicts about a third of the pairs (so SAFE-Mem's contested path runs).
The selected entries (ids, texts), the required rung and the contested flags must be identical.

    python -m locomo_safemem.equivalence [--groups G-T00 ...] [--out FILE]
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from ams.llm.types import ChatResponse, Usage
from ams.research.dynamic.models import check, digest
from ams.research.provisional_run.runner import resolve_models
from ams.research.retrieval import RetrievalContext
from ams.research.workload import adaptive as AD
from ams.research.workload import design as D
from ams.research.workload import lineage as LN
from ams.research.workload import sv2 as SV2
from ams.research.workload.generator import read_rows
from ams.research.workload.integration import group_rows, use_id
from ams.research.workload.runner import prepare_state as frozen_prepare

from locomo_safemem import governance as G

REPO = Path(__file__).resolve().parents[1]
BUNDLE = REPO / "research_data/controlled_workload_v4_20261108"
STAGE1 = REPO / "research_data/controlled_workload_stage1_test_v4_20261108"
CONDITIONS = ("localized", "distributed", "sybil_k4", "launder_r4", "imp_localized_fp1_d0",
              "imp_localized_late_d0")
ARMS = ("static", "R", "C", "M", "S", "SL", "S2-ID")


class OracleSession:
    """Deterministic conflict replies (hash of the prompt); identical for both paths."""

    def __init__(self):
        self.n = 0

    def dispatch(self, stage, request):
        check(stage == "conflict", f"Unexpected paid stage {stage} in a retrieval-only check")
        self.n += 1
        body = request.messages[-1].content
        word = "contradict" if int(hashlib.sha256(body.encode()).hexdigest(), 16) % 3 == 0 else "compatible"
        r = ChatResponse(word, request.model, "oracle", Usage(0, 0, 0.0), raw_finish_reason="stop")
        return "oracle_" + digest(body)[:16], {"response": asdict(r)}


def local_prompts(store: dict, mirror: Path) -> dict:
    """`ablations.checkpoint_prompts` with the checkpoint root remapped to this checkout's
    `prompts/` (the stored root is the evaluation machine's path); every file hash-verified."""
    out = {**store, "snapshots": {}}
    for cond, snap in store["snapshots"].items():
        libs = []
        for body in snap.get("libraries", []):
            root = mirror / digest(sorted(body["files"].items()))[:16]
            for rel, h in body["files"].items():
                text = (REPO / "prompts" / rel).read_text()
                check(digest(text) == h, f"Prompt file {rel} changed since the checkpoint")
                dst = root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                if not dst.exists():
                    dst.write_text(text)
            libs.append({**body, "root": str(root.resolve())})
        out["snapshots"][cond] = {**snap, "libraries": libs}
    return out


def _state(path: str, store, cond, arm, revealed, verdicts):
    base = "S" if arm in ("SL", "S2-ID") else arm
    if path == "frozen":
        st = frozen_prepare(store["snapshots"][cond], store["audits"][cond], base, revealed)
    else:
        st = G.prepare_state(store["snapshots"][cond], store["audits"][cond], base, D.AUDIT_TICKETS, revealed,
                             verify=True)
    session = OracleSession()
    resolve_models(st, session)
    if arm == "SL":
        LN.apply(st, store["session_id"], LN.DEFAULT_TAU)
    elif arm == "S2-ID":
        SV2.apply(st, store, "S2-ID", tau=LN.DEFAULT_TAU, sensitive=verdicts)
    return st


def compare(groups=("G-T00",), conditions=CONDITIONS, arms=ARMS, mirror: Path | None = None) -> dict:
    rows = read_rows(BUNDLE)
    mirror = mirror or REPO / "research_data/locomo_safemem/equivalence_prompt_mirror"
    report = {"groups": list(groups), "conditions": list(conditions), "arms": list(arms), "retrievals": 0,
              "differences": [], "contested_claims_seen": 0}
    with G.fast_revisions():  # MPBench's tested runtime optimization (no decision change)
        _compare(groups, conditions, arms, mirror, rows, report)
    report["identical"] = not report["differences"]
    return report


def _compare(groups, conditions, arms, mirror, rows, report):
    for gid in groups:
        with gzip.open(STAGE1 / "stores" / f"{gid}.json.gz", "rt") as fh:
            store = json.load(fh)
        store = local_prompts(store, mirror)
        store = AD.extend_store(rows, store, [c for c in conditions if c not in D.CONDITIONS])
        group = group_rows(rows, gid)
        questions = [p["question"] for p in group["probes"]]
        verdicts = SV2.RecordedVerdicts({q: "ORDINARY" for q in questions})
        for cond in conditions:
            pre = set(store.get("pre_reveal", {}).get(cond, ()))
            for arm in arms:
                states = {}
                for path in ("frozen", "dialogue"):
                    states[path] = {rev: _state(path, store, cond, arm, rev, verdicts)
                                    for rev in ((True, False) if pre else (True,))}
                check(type(states["dialogue"][True]).__name__ == "DialogueRuntimeState", "Wrong state type")
                for probe in group["probes"]:
                    rev = probe["probe_id"] not in pre
                    out = {}
                    for path in ("frozen", "dialogue"):
                        st = states[path][rev]
                        ctx = RetrievalContext(st.evidence, st.access, use_id(gid, probe["question"]), "user", "read")
                        res = st.reader().retrieve_with_trace(session_id=store["session_id"], query=probe["question"],
                                                              context=ctx, k=4, principal="user")
                        out[path] = ([(e.entry_id, e.text) for e in res.retrieval.entries], res.retrieval.required,
                                     res.trace.contested_after)
                    report["retrievals"] += 1
                    report["contested_claims_seen"] += sum(1 for _, c in out["frozen"][2] if c)
                    if out["frozen"] != out["dialogue"]:
                        report["differences"].append({"group": gid, "condition": cond, "arm": arm,
                                                      "probe": probe["probe_id"]})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", nargs="*", default=["G-T00"])
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    rep = compare(tuple(a.groups))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != "differences"} | {"n_differences": len(rep["differences"])},
                     indent=1))


if __name__ == "__main__":
    main()
