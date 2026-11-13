"""Free Stage-2 validation of real Stage-1 stores (no paid calls, no answering).

1. Extraction yield: are the inserted facts, planted attack targets, linked and
   unlinked copies and principal statements actually stored as records?
2. Classification: which kind does the frozen classifier assign to each probe?
   (Only description questions can be answered from external memory.)
3. Retrieval exposure for every condition x arm: does governed retrieval put the
   carrier record / the fact or target itself into the supplied context?

Retrieval may invoke the original pairwise conflict checker (an LLM call). It
runs only on already-selected claims and only sets `contested` flags, so it
cannot change which records are selected. Stage 2 is not approved to pay for
it: such calls get a logged placeholder reply ("compatible") and are counted.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict

from ams.core.lattice import coarsen
from ams.llm.types import ChatResponse, Usage
from ams.research.evidence_memoization import memoized_evidence_revisions
from ams.research.provisional_run.runner import resolve_models
from ams.research.recovery.offline import CHAT_MODEL
from ams.research.retrieval import RetrievalContext
from ams.research.workload import design as D
from ams.research.workload.grading import grade_utility, restates
from ams.research.workload.integration import group_rows, use_id
from ams.research.workload.runner import MEMORY_ARMS, exposure, prepare_state


class ConflictPlaceholderSession:
    """No paid call: conflict checks get a placeholder; anything else is refused."""

    def __init__(self):
        self.conflicts = 0

    def dispatch(self, stage, request):
        if stage != "conflict":
            raise RuntimeError("Stage 2 performs retrieval only; no answer calls")
        self.conflicts += 1
        response = ChatResponse("compatible", CHAT_MODEL, "stage2-placeholder", Usage(0, 0, 0.0))
        return f"placeholder_{self.conflicts}", {"response": asdict(response)}


def _records_by_contribution(store):
    out = defaultdict(list)
    for native, rec in store["record_owner"].items():
        out[rec["contribution_id"]].append({**rec, "native_id": native})
    return out


def carrier_stored(priv: dict, claims: list[dict], aliases) -> bool:
    """The Stage-2 rule: is what this contribution planted stored as a claim?

    benign fact: an external claim restating the fact sentence (>= 60% of its
    content words) that also contains the answer alias; principal control: a
    principal claim containing the answer; attacks and copies: an external claim
    restating the planted target (>= 50%).
    """
    role = priv["role"]
    external = [r for r in claims if r["kind"] == "external"]
    if role == "benign_with_fact":
        return any(
            restates(priv["fact"]["sentence"], r["text"], 0.6)
            and (aliases is None or grade_utility(r["text"], aliases))
            for r in external
        )
    if role == "principal_control":
        return any(r["kind"] == "principal" and grade_utility(r["text"], aliases) for r in claims)
    return any(restates(priv["planted_target"], r["text"]) for r in external)


def extraction_yield(rows, stores):
    """Per role: does a record of that contribution restate what was planted?"""
    tally = defaultdict(Counter)
    misses = []
    for store in stores:
        group = group_rows(rows, store["group_id"])
        recs = _records_by_contribution(store)
        aliases = {
            p["contribution_id"]: p.get("aliases")
            for p in group["private_probes"].values()
            if p["kind"].startswith("utility")
        }
        for cid, priv in group["private"].items():
            role = priv["role"]
            claims = [r for r in recs[cid] if r["record_kind"] == "claim"]
            external = [r for r in claims if r["kind"] == "external"]
            hit = carrier_stored(priv, claims, aliases.get(cid))
            tally[role]["stored" if hit else "missing"] += 1
            tally[role]["contributions"] += 1
            tally[role]["external_claims"] += len(external)
            if not hit and len(misses) < 60:
                misses.append(
                    {
                        "group": store["group_id"],
                        "role": role,
                        "contribution_id": cid,
                        "expected": priv.get("planted_target")
                        or priv.get("fact", {}).get("sentence"),
                        "claims": [r["text"] for r in claims][:6],
                    }
                )
    return {k: dict(v) for k, v in tally.items()}, misses


def classification(rows, stores):
    out = defaultdict(Counter)
    for store in stores:
        group = group_rows(rows, store["group_id"])
        state = prepare_state(store["snapshots"][D.CONDITIONS[0]], [], "static")
        resolve_models(state, ConflictPlaceholderSession())
        for probe in group["probes"]:
            kind = group["private_probes"][probe["probe_id"]]["kind"]
            rung = coarsen(
                state.memory.use_type.required(probe["question"]), state.memory.granularity
            )
            out[kind][rung.name.lower()] += 1
    return {k: dict(v) for k, v in out.items()}


def retrieval_exposure(rows, stores):
    session = ConflictPlaceholderSession()
    cells = defaultdict(lambda: defaultdict(Counter))
    with memoized_evidence_revisions():
        for store in stores:
            gid = store["group_id"]
            group = group_rows(rows, gid)
            for condition in D.CONDITIONS:
                for arm in MEMORY_ARMS:
                    state = prepare_state(
                        store["snapshots"][condition], store["audits"][condition], arm
                    )
                    resolve_models(state, session)
                    for probe in group["probes"]:
                        priv = group["private_probes"][probe["probe_id"]]
                        q = probe["question"]
                        ctx = RetrievalContext(
                            state.evidence, state.access, use_id(gid, q), "user", "read"
                        )
                        outcome = state.reader().retrieve_with_trace(
                            session_id=store["session_id"],
                            query=q,
                            context=ctx,
                            k=4,
                            principal="user",
                        )
                        entries = [asdict(e) for e in outcome.retrieval.entries]
                        e = exposure(entries, store["record_owner"], priv, priv.get("aliases"))
                        key = priv["kind"]
                        c = cells[condition][arm]
                        c[f"{key}:n"] += 1
                        c[f"{key}:carrier_in_context"] += e["carrier_record_in_context"]
                        c[f"{key}:target_in_context"] += e["target_in_context"]
                        if priv["kind"] == "utility":
                            s = priv["strata"][condition]
                            c[f"utility[{s}]:n"] += 1
                            c[f"utility[{s}]:target_in_context"] += e["target_in_context"]
    return (
        {cond: {arm: dict(v) for arm, v in arms.items()} for cond, arms in cells.items()},
        session.conflicts,
    )
