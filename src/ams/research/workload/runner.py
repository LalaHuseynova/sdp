"""Run static / R / C / M / S / no-memory over controlled-workload stores.

Reuses the provisional runner's exact query path (`answer_query`: governed
retrieval -> original typed answer prompt, temperature 0, 200 tokens), its
model resolver (only answer and conflict calls may leave the frozen replay
tables) and its append-only journal. The attack judge is the original
`MemoryJudge`. Utility is graded deterministically. The transport is whatever
`session` is passed: `MockSession` offline, `RefusingSession` otherwise. No
live transport exists in this module.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ams.core.lattice import coarsen
from ams.eval.judge import MemoryJudge
from ams.llm.types import ChatRequest, Message
from ams.research.dynamic import EvidenceSnapshot, Policy
from ams.research.dynamic.models import check, digest, parse_event
from ams.research.evidence_memoization import memoized_evidence_revisions
from ams.research.provisional_run.runner import BoundClient, Journal, answer_query, resolve_models
from ams.research.recovery.offline import CHAT_MODEL
from ams.research.sequential.state import RuntimeState
from ams.research.workload import design as D
from ams.research.workload.grading import grade_utility, restates
from ams.research.workload.integration import group_rows, use_id

MEMORY_ARMS = ("static", "R", "C", "M", "S")
JUDGED = ("attack", "copy_linked", "copy_unlinked")


def prepare_state(snapshot: dict, audits: list, arm: str) -> RuntimeState:
    state = RuntimeState.load(snapshot)
    state.policy = Policy("R" if arm == "static" else arm)
    state.effects_enabled = arm != "static"
    if arm != "static":
        state.evidence = EvidenceSnapshot(
            state.evidence.config,
            (*state.evidence.events, *(parse_event(a) for a in audits)),
            D.AUDIT_TICKETS,
        )
        state.clock = D.AUDIT_TICKETS
    state.validate()
    check(
        state.evidence.usage.tickets == (0 if arm == "static" else D.AUDIT_TICKETS),
        "Unequal audit budget",
    )
    return state


def exposure(entries, owner, private_probe, aliases=None):
    carriers = set(private_probe["carriers"])
    carrier_texts = [
        e["text"]
        for e in entries
        if owner.get(e["entry_id"], {}).get("contribution_id") in carriers
    ]
    target = private_probe.get("target")
    return {
        "carrier_record_in_context": bool(carrier_texts),
        "target_in_context": bool(
            (target and any(restates(target, t) for t in carrier_texts))
            or (aliases and any(grade_utility(t, aliases) for t in carrier_texts))
        ),
    }


def run(
    rows: dict,
    stores: list,
    session,
    out: Path,
    *,
    split: str,
    conditions: tuple = D.CONDITIONS,
    arms: tuple = MEMORY_ARMS,
    no_memory: bool = True,
    lineage_tau: float | None = None,
) -> dict:
    """Execute every (group, condition, arm, probe) once; idempotent on restart.

    Defaults reproduce the locked-protocol-v1 run exactly. Research extensions
    may pass adaptive `conditions` (stores extended by `adaptive.extend_store`,
    which also carry per-condition `strata`) and lineage arms (RL/CL/ML/SL).
    """
    key = [D.VERSION, split, sorted(s["group_id"] for s in stores)]
    if (conditions, arms, no_memory, lineage_tau) != (D.CONDITIONS, MEMORY_ARMS, True, None):
        key.append([list(conditions), list(arms), no_memory, lineage_tau])
    journal = Journal(out, digest(key))
    plan = (conditions, arms, no_memory, lineage_tau)
    judge_client = BoundClient(session, "judge_answer")
    judge = MemoryJudge(judge_client, model=CHAT_MODEL)
    # Tested runtime-only optimization (also used by the provisional extension):
    # caches the hash of an immutable evidence snapshot; no decision changes.
    try:
        with memoized_evidence_revisions():
            _run_all(rows, stores, session, journal, judge, judge_client, split, plan)
        return {"rows": len(journal.rows())}
    finally:
        journal.db.close()


def _run_all(rows, stores, session, journal, judge, judge_client, split, plan):
    from ams.research.workload import lineage as LN

    conditions, arms, no_memory, tau = plan
    for store in stores:
        gid = store["group_id"]
        group = group_rows(rows, gid)
        owner = store["record_owner"]
        extra_strata = store.get("strata", {})
        for condition in conditions:
            for arm in arms:
                base_arm = LN.LINEAGE_ARMS.get(arm, arm)
                state = prepare_state(
                    store["snapshots"][condition], store["audits"][condition], base_arm
                )
                references = resolve_models(state, session)
                if arm in LN.LINEAGE_ARMS:
                    check(tau is not None, "Lineage arms need an explicit tau")
                    LN.apply(state, store["session_id"], tau)
                for probe in group["probes"]:
                    priv = group["private_probes"][probe["probe_id"]]
                    question = probe["question"]
                    value = answer_query(
                        state, store["session_id"], question, use_id(gid, question), references
                    )
                    entries = value["retrieval"]["retrieval"]["entries"]
                    record = _grade(judge, judge_client, priv, question, value["answer"]["text"])
                    trace = value["retrieval"]["trace"]
                    journal.commit(
                        digest([gid, condition, arm, probe["probe_id"]]),
                        {
                            "group_id": gid,
                            "split": split,
                            "condition": condition,
                            "arm": arm,
                            "probe_id": probe["probe_id"],
                            "kind": priv["kind"],
                            "stratum": extra_strata.get(condition, {}).get(
                                probe["probe_id"], priv["strata"].get(condition)
                            ),
                            "answer": value["answer"]["text"],
                            "finish_reason": value["answer"]["raw_finish_reason"],
                            **record,
                            "exposure": exposure(entries, owner, priv, priv.get("aliases")),
                            "selected_ids": trace["selected_ids"],
                            "supplied_context_hash": digest(trace["supplied_context"]),
                            "penalized_candidates": sum(
                                c["decision"]["penalty"] > 0 for c in trace["candidates"]
                            ),
                            "gated_candidates": sum(
                                c["decision"]["reason"] == "source_risk_gate"
                                for c in trace["candidates"]
                            ),
                            "direct_unsafe_candidates": sum(
                                c["decision"]["reason"] == "verified_unsafe_for_use"
                                for c in trace["candidates"]
                            ),
                            "audit_tickets": state.evidence.usage.tickets,
                            "model_call_ids": value["model_call_ids"],
                        },
                    )
        if no_memory:
            _no_memory(journal, judge, judge_client, session, store, group, split)


def _grade(judge, judge_client, priv, question, answer):
    if priv["kind"] in JUDGED:
        start = len(judge_client.calls)
        verdict = asdict(judge.judge_answer(question, priv["target"], answer.strip()))
        return {
            "outcome": bool(verdict["hit"]),
            "judge": verdict,
            "judge_call_id": judge_client.calls[-1] if len(judge_client.calls) > start else None,
        }
    return {"outcome": grade_utility(answer, priv["aliases"]), "judge": None, "judge_call_id": None}


def _no_memory(journal, judge, judge_client, session, store, group, split):
    """Empty-memory reference: classifier only, no stored text. Once per group."""
    state = RuntimeState.load(store["snapshots"][D.CONDITIONS[0]])
    resolve_models(state, session)
    control = BoundClient(session, "no_memory_answer")
    for probe in group["probes"]:
        priv = group["private_probes"][probe["probe_id"]]
        q = probe["question"]
        required = coarsen(state.memory.use_type.required(q), state.memory.granularity).name.lower()
        prompt = state.memory.prompts.get("answer_typed", "v2").render(
            query=q, memory="(nothing)", required=required
        )
        response = control.complete(
            ChatRequest(
                (Message("user", prompt),), state.answer_model, temperature=0, max_tokens=200
            )
        )
        record = _grade(judge, judge_client, priv, q, response.text)
        journal.commit(
            digest([store["group_id"], "none", "no_memory", probe["probe_id"]]),
            {
                "group_id": store["group_id"],
                "split": split,
                "condition": "none",
                "arm": "no_memory",
                "probe_id": probe["probe_id"],
                "kind": priv["kind"],
                "stratum": None,
                "answer": response.text,
                "finish_reason": response.raw_finish_reason,
                **record,
                "exposure": None,
                "selected_ids": [],
                "supplied_context_hash": None,
                "penalized_candidates": 0,
                "gated_candidates": 0,
                "direct_unsafe_candidates": 0,
                "audit_tickets": 0,
                "model_call_ids": [control.calls[-1]],
            },
        )
