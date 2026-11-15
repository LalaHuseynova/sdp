"""Protocol v2, plan.md step 1.8: the evaluation pipeline for every method (built, not run).

One loop, two modes, both reusing the frozen code paths unchanged:
  answer=False  FREE precompute. Retrieval only, with the logged Stage-2 conflict
                placeholder (conflicts never change selection), so exposure is exact;
                each would-be answer prompt is hashed for the step-1.12 cost estimate.
                Independent per group, so groups can run as parallel shards.
  answer=True   PAID stage, one process. The runner's exact path: the same retrieval
                with real conflict checks, the frozen `answer_typed` v2 prompt
                (temperature 0, 200 tokens) and the original MemoryJudge, through the
                guarded session given (`open_paid`). Identical requests are sent once
                (the guard's exact reuse), and a restart is replayed from the guarded
                ledger at $0 while the journal checks every row is unchanged.

  answer=True, contexts=...  PAID stage, step-1.12 runtime fix 2 (owner-approved, three
                steps, `two_phase`): the internal arms' contexts (and the base contexts
                the published defences filter) are read from a free precompute that
                replayed the REAL conflict replies, instead of being recomputed; each
                stored context is re-verified (hashes, recomputed row, live ledger).
                Rows are identical to answer=True without contexts (tested).

Methods: internal arms come from frozen policies (`runner.prepare_state`, plus the
`lineage` / `sv2` compositions); published defences filter Original SAFE-Mem's
retrieval (or R's, for the labelled "+R" variants) with the existing adapters
(`published.apply`), and their kept memories are answered with the same frozen prompt.
"""

from __future__ import annotations

import contextlib
import os
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from ams.eval.judge import MemoryJudge
from ams.llm.types import ChatRequest, Message
from ams.research.dynamic.models import check, digest
from ams.research.evidence_memoization import memoized_evidence_revisions
from ams.research.provisional_run.runner import BoundClient, Journal, resolve_models
from ams.research.recovery.offline import CHAT_MODEL
from ams.research.retrieval import RetrievalContext
from ams.research.sequential.clients import response_from
from ams.research.workload import lineage as LN
from ams.research.workload import published as P
from ams.research.workload import sv2 as SV2
from ams.research.workload.integration import group_rows, use_id
from ams.research.workload.runner import _grade, exposure, prepare_state

VERSION = "protocol-v2-pipeline-v2"  # v2: Haiku answers built for the backbone model (2.3)
TAU = LN.DEFAULT_TAU  # content-lineage threshold (SL, S2-*), frozen at 0.8

# Table rows in protocol §10 order, then the appendix-only methods (decisions 6-8).
MAIN_METHODS = ("static", "R", "C", "M", "a_memguard", "memlineage", "llm_sanitiser",
                "randec", "S", "SL", "S2-ID")  # fmt: skip
APPENDIX_METHODS = ("S2-BS", "a_memguard+R", "memlineage+R", "llm_sanitiser+R", "randec+R")

# The paid purpose (own owner approval, cap and session) each method needs besides
# v2_stage3 (answers, conflicts, judges). RandEC is a local model and costs nothing.
_EXTRA_PURPOSE = {"memlineage": "v2_published_memlineage", "S2-ID": "v2_published_memlineage",
                  "a_memguard": "v2_published_amemguard",
                  "llm_sanitiser": "v2_published_sanitiser"}  # fmt: skip


def _published(method: str) -> tuple[str, str] | None:
    """('a_memguard', 'R') for 'a_memguard+R'; None for an internal arm."""
    name, _, base = method.partition("+")
    return (name, base or "static") if name in P.PUBLISHED else None


def required_purposes(methods, backbone: str = "gpt") -> set[str]:
    out = {"v2_stage3"}
    for m in methods:
        name = _published(m)[0] if _published(m) else m
        if name in _EXTRA_PURPOSE:
            out.add(_EXTRA_PURPOSE[name])
    if backbone == "haiku":
        out.add("v2_backbone_answer")
    return out


def memlineage(sensitive):
    return P.memlineage(sensitive)


# ----------------------------------------------------------------------------- the loop


def _states(store, condition, method, session, sensitive, revealed_options):
    """{revealed: (state, model-call references)} for one (condition, method)."""
    pub = _published(method)
    arm = pub[1] if pub else LN.LINEAGE_ARMS.get(method, "S" if method in SV2.CANDIDATES
                                                 else method)  # fmt: skip
    out = {}
    for revealed in revealed_options:
        state = prepare_state(store["snapshots"][condition], store["audits"][condition], arm,
                              revealed)  # fmt: skip
        references = resolve_models(state, session)
        if method in LN.LINEAGE_ARMS:
            LN.apply(state, store["session_id"], TAU)
        elif method in SV2.CANDIDATES:
            SV2.apply(state, store, method, tau=TAU, sensitive=sensitive)
        out[revealed] = (state, references)
    return out


def _retrieve(state, store, question):
    gid = store["group_id"]
    ctx = RetrievalContext(state.evidence, state.access, use_id(gid, question), "user", "read")
    res = state.reader().retrieve_with_trace(
        session_id=store["session_id"], query=question, context=ctx, k=4, principal="user"
    )
    return [asdict(e) for e in res.retrieval.entries], res.retrieval.required


def answer_prompt(state, question, entries, required) -> str:
    """The frozen answer prompt, rendered exactly as `provisional_run.runner.answer_query`."""
    return render_answer(state.memory.prompts.get("answer_typed", "v2"), question, entries,
                         required)  # fmt: skip


def render_answer(template, question, entries, required) -> str:
    """`template`: the state's frozen `answer_typed` v2 prompt (or its stored copy)."""
    body = "\n".join(f"- {e['text']}" for e in entries) or "(nothing)"
    return template.render(query=question, memory=body, required=required or "description")


def evaluate(rows, stores, session, out: Path, *, conditions, methods, defences=None,
             sensitive=None, answer: bool = True, contexts=None) -> dict:  # fmt: skip
    """Every (group, condition, method, probe) once; idempotent on restart.

    `contexts` (step-1.12 fix 2, `two_phase`): with answer=False a writer that stores
    each internal arm's context; with answer=True the verified reader of those."""
    defences = defences or {}
    for m in methods:
        pub = _published(m)
        check(pub is None or pub[0] in defences, f"No defence object for {m}")
        check(m not in ("S2-ID",) or sensitive is not None, "S2-ID needs SensitiveAction")
    scope = digest([VERSION, list(conditions), list(methods), answer,
                    sorted(s["group_id"] for s in stores)])  # fmt: skip
    if contexts is not None and answer:  # validated before anything is written or sent
        contexts.check(conditions, [s["group_id"] for s in stores])
        contexts.verify(session)
    journal = Journal(Path(out), scope)
    # Second backbone (decision 22): the router re-addresses answers to Claude Haiku, so the
    # answer request is built for that model and dispatched directly (the frozen replay
    # client would refuse a Haiku reply to a GPT-4o-mini request). Same prompt, temperature
    # and max_tokens; found and fixed at step 2.3 (tests/test_v2_pipeline.py).
    from ams.research.protocol_v2.backbone import BackboneRouter

    backbone = session.model if isinstance(session, BackboneRouter) else None
    judge_client = BoundClient(session, "judge_answer") if answer else None
    judge = MemoryJudge(judge_client, model=CHAT_MODEL) if answer else None
    try:
        with memoized_evidence_revisions():
            for store in stores:
                _group(rows, store, session, journal, judge, judge_client, conditions, methods,
                       defences, sensitive, answer, contexts, backbone)  # fmt: skip
        return {"rows": len(journal.rows()), "scope": scope}
    finally:
        journal.db.close()


def _group(rows, store, session, journal, judge, judge_client, conditions, methods,
           defences, sensitive, answer, contexts=None, backbone=None):  # fmt: skip
    gid = store["group_id"]
    group = group_rows(rows, gid)
    owner = store["record_owner"]
    for condition in conditions:
        pre = set(store.get("pre_reveal", {}).get(condition, ()))  # late audits (step 1.6)
        for method in methods:
            pub = _published(method)
            base = pub[1] if pub else method
            stored = answer and contexts is not None and contexts.has(base)
            states = None if stored else _states(store, condition, method, session, sensitive,
                                                 (True, False) if pre else (True,))  # fmt: skip
            for probe in group["probes"]:
                pid, question = probe["probe_id"], probe["question"]
                priv = group["private_probes"][pid]
                revealed = pid not in pre
                if stored:  # fix 2: the verified context of `base`, real conflict replies
                    ctx = contexts.get(gid, condition, base, pid)
                    check(ctx["row"]["audits_revealed"] == revealed, "Context audit mismatch")
                    entries, required = ctx["entries"], ctx["required"]
                    template, model = ctx["template"], ctx["answer_model"]
                    tickets = ctx["row"]["audit_tickets"]
                else:
                    state, references = states[revealed]
                    start = len(references)
                    entries, required = _retrieve(state, store, question)
                    template, model = state.memory.prompts.get("answer_typed", "v2"), None
                    tickets = state.evidence.usage.tickets
                base_entries = entries
                extra = {}
                if pub:
                    res = P.apply(defences[pub[0]], store, group, question, entries,
                                  text_from_defence=pub[0] == "llm_sanitiser")  # fmt: skip
                    entries = res["kept_entries"]
                    extra = {"kept": res["kept"], "flagged": res["flagged"]}
                prompt = render_answer(template, question, entries, required)
                row = {
                    "group_id": gid, "condition": condition, "method": method,
                    "probe_id": pid, "kind": priv["kind"],
                    "stratum": store.get("strata", {}).get(condition, {}).get(
                        pid, priv["strata"].get(condition)),
                    "audits_revealed": revealed,
                    "audit_tickets": tickets,
                    "context_size": len(entries), "prompt_hash": digest(prompt),
                    "exposure": exposure(entries, owner, priv, priv.get("aliases")),
                    "answer": None, "outcome": None, "judge": None, "finish_reason": None,
                    **extra,
                }  # fmt: skip
                if stored and not pub:  # the stored row must be exactly its recomputation
                    check(row == ctx["row"], "Stored context differs from its recomputation")
                if contexts is not None and not answer and not pub:
                    contexts.put(digest([gid, condition, method, pid]), row=row,
                                 entries=base_entries, required=required, template=template,
                                 answer_model=state.answer_model,
                                 conflict_call_ids=references[start:])  # fmt: skip
                if answer and (stored or backbone):
                    # = state.answer_client.complete through `resolve_models`' resolver
                    request = ChatRequest((Message("user", prompt),), backbone or model,
                                          temperature=0, max_tokens=200)  # fmt: skip
                    call_id, result = session.dispatch("answer", request)
                    response = response_from("chat", result["response"])
                    check(response.model == request.model, "Replay response model mismatch")
                    calls = [*(ctx["conflict_call_ids"] if stored else references[start:]),
                             call_id]  # fmt: skip
                elif answer:
                    response = state.answer_client.complete(ChatRequest(
                        (Message("user", prompt),), state.answer_model, temperature=0,
                        max_tokens=200))  # fmt: skip
                    calls = references[start:]
                if answer:
                    graded = _grade(judge, judge_client, priv, question, response.text)
                    row.update(answer=response.text, finish_reason=response.raw_finish_reason,
                               outcome=graded["outcome"], judge=graded["judge"],
                               model_call_ids=calls)  # fmt: skip
                journal.commit(digest([gid, condition, method, pid]), row)


def distinct_prompts(precomputed_rows) -> int:
    """Distinct answer prompts (each is sent once): the step-1.12 answer-call count."""
    return len({r["prompt_hash"] for r in precomputed_rows})


# ----------------------------------------------------------------------------- paid entry


class _Paid:
    def __init__(self, sessions, stage3, sensitive):
        self.sessions, self.stage3, self.sensitive = sessions, stage3, sensitive

    def client(self, purpose):
        from ams.research.workload.transport import GuardedV2Client

        return GuardedV2Client(self.sessions[purpose])

    def spend(self) -> dict:
        return {p: str(s.task_spend()) for p, s in self.sessions.items()}


@contextlib.contextmanager
def open_paid(root: Path, bundle_hash: str, approval, purposes, *, transport=None,
              confirmed: bool = False):  # fmt: skip
    """Open one guarded session per paid purpose (`root/<purpose>/`), each under the
    owner's approval file (frozen protocol-v2 digest, model and cap per purpose).

    Nothing is opened unless `confirmed` (the CLI's explicit --confirm-paid) and the
    approval covers every requested purpose. `transport`: an httpx mock (tests) or None
    (live: needs OPENROUTER_API_KEY). Each session holds its own exclusive lock, so a
    paid stage always has a single writer."""
    from ams.baselines.memlineage import SensitiveAction
    from ams.core.prompts import PromptLibrary
    from ams.research.execution.session import MODEL, ExecutionSession
    from ams.research.protocol_v2.backbone import BackboneRouter
    from ams.research.workload.transport import (
        V2_MODELS,
        V2_PURPOSES,
        V2_SPLIT,
        ConstructionSession,
        GuardedV2Client,
        check_v2_approval,
    )

    check(confirmed, "Paid stages need the explicit --confirm-paid flag (owner confirmation)")
    caps = {}
    for p in sorted(purposes):  # validate everything before opening anything
        approved = (approval or {}).get("caps_usd", {}).get(p, "0.01") if isinstance(
            approval, dict) else "0.01"  # fmt: skip
        caps[p] = Decimal(str(approved))
        # A cap above the code ceiling is a configuration error: reject it, never lower it.
        check(caps[p] <= V2_PURPOSES[p], f"Approved cap USD {caps[p]} for {p} exceeds the "
              f"code ceiling USD {V2_PURPOSES[p]}; fix the approval file")  # fmt: skip
        check_v2_approval(approval, p, caps[p], V2_MODELS.get(p, MODEL))
    key = None if transport is not None else os.environ.get("OPENROUTER_API_KEY")
    check(transport is not None or bool(key), "Missing OpenRouter credential")
    sessions = {}
    try:
        for p in sorted(purposes):
            path = Path(root) / p
            if not path.exists():
                ExecutionSession.create(path, plan_hash=approval["protocol_v2_digest"],
                                        model=V2_MODELS.get(p, MODEL)).close()  # fmt: skip
            s = ConstructionSession(path)
            sessions[p] = s
            if transport is not None:
                s.arm_construction_mock(bundle_hash, V2_SPLIT, transport, caps[p], purpose=p,
                                        approval=approval)  # fmt: skip
            else:
                s.arm_construction(bundle_hash, V2_SPLIT, key, caps[p], purpose=p,
                                   approval=approval)  # fmt: skip
        stage3 = sessions["v2_stage3"]
        if "v2_backbone_answer" in sessions:
            stage3 = BackboneRouter(stage3, sessions["v2_backbone_answer"])
        sensitive = None
        if "v2_published_memlineage" in sessions:
            sensitive = SensitiveAction(client=GuardedV2Client(sessions["v2_published_memlineage"]),
                                        model=CHAT_MODEL, prompts=PromptLibrary())  # fmt: skip
        yield _Paid(sessions, stage3, sensitive)
    finally:
        for s in sessions.values():
            s.close()
