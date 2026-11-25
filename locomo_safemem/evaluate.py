"""Contexts for every (store, condition, method, question): SAFE-Mem retrieval under each frozen arm.

Per store (MPBench `protocol_v2.pipeline._group` semantics, LoCoMo answer path):
  static        Original SAFE-Mem: `GovernedRetrieval` with research effects disabled (static parity
                with `TypedStandingMemory.retrieve` is tested), no audits. Audit-independent, so one
                pass per store; its contexts are what the published defences filter (no refill).
  R C M S SL    frozen `Policy(arm)` under each condition's audits; SL = frozen `lineage.apply`.
  S2-ID         frozen `sv2.apply(..., "S2-ID")` semantics: SL retrieval, then the frozen MemLineage
                gate (`sv2._GatedReader`) with the recorded SensitiveAction verdicts.
  S2-BS         appendix: frozen `sv2.apply(..., "S2-BS")`.
  memlineage    frozen MemLineage (coarse, tau 0, Deny) on static's entries, recorded verdicts.
  randec        frozen RandEC (local DistilBERT) on static's entries.
Questions are retrieved in a fixed order (qid) per state, so SAFE-Mem's persistent conflict
downgrades ("contested") evolve exactly as in a sequential deployment, identically for every arm.

Conflict checks (SAFE-Mem's query-time LLM calls) go through `ConflictSession`, whose backend is the
mock, a free recorder (placeholder "compatible"), or the paid guarded client with its response cache.

Output per conversation (LoCoMo v2 job format, answered by the frozen v2 runner unchanged):
  <conv>.jobs.jsonl.gz      {cell, qid, ctx, kept}    cell = family|conv|o|variant|dN|condition|method
  <conv>.contexts.jsonl.gz  {ctx, text}               SAFE-Mem's LoCoMo answer context
  <conv>.stores.json        per store: owner map, roots, construction stats, per-condition audits
"""

from __future__ import annotations

import gzip
import hashlib
import json
import time
from dataclasses import asdict, replace
from pathlib import Path

from locomo_v1 import build as B1
from locomo_v2 import build as V2B

from ams.core.prompts import PromptLibrary
from ams.data.locomo import load_locomo
from ams.llm.types import ChatResponse, Usage
from ams.research.dynamic.models import check, digest
from ams.research.provisional_run.runner import resolve_models
from ams.research.retrieval import RetrievalContext
from ams.research.workload import lineage as LN
from ams.research.workload import published as P
from ams.research.workload import sv2 as SV2
from ams.research.workload.integration import use_id

from locomo_safemem import config as K
from locomo_safemem import governance as G
from locomo_safemem import scenarios as SN
from locomo_safemem import store as ST

EVAL_VERSION = "locomo-safemem-eval-v1"
QLIMIT = None  # smoke tests only (first N questions by qid); never set in a mock/paid study pass


class ConflictSession:
    """`session.dispatch("conflict", request)` for the frozen replay resolver. `backend.complete`
    answers (mock / paid guarded client); backend=None: free placeholder 'compatible' (recording)."""

    def __init__(self, backend=None):
        self.backend, self.requests, self.calls, self.contradictions = backend, {}, 0, 0

    def dispatch(self, stage, request):
        check(stage == "conflict", f"Unexpected paid stage {stage} during retrieval")
        key = request.cache_key("openrouter")
        self.requests.setdefault(key, len(request.messages[-1].content))
        self.calls += 1
        if self.backend is None:
            r = ChatResponse("compatible", request.model, "placeholder", Usage(0, 0, 0.0), raw_finish_reason="stop")
        else:
            r = self.backend.complete(request)
        self.contradictions += "contradict" in r.text.strip().lower()
        return "conflict_" + key[:16], {"response": asdict(r)}


def _context(prompts, conv, entries) -> str:
    body = "\n".join(f"- {e['text']}" for e in entries) or "(nothing)"
    return prompts.get("locomo_memory_start").render(a=conv.speakers[0], b=conv.speakers[1]) + "\n\n" + body


SENTINEL_EVERY = 25  # every 25th retrieval is recomputed through the frozen GovernedRetrieval (fail-closed)
_counter = {"n": 0, "checked": 0}


def _run_state(state, store, qs, session, pre=frozenset(), make_pre=None, sentinel=SENTINEL_EVERY):
    """Retrieve every question in qid order (`governance.fast_retrieve`, exact). Late audits (MPBench
    `pre_reveal_probes`): the pre-reveal questions are answered by a separate state built by
    `make_pre()` AFTER the revealed sweep, so each state starts from the initial memory, exactly as
    MPBench's two independently loaded states. A deterministic sample is re-run through the frozen
    reader (fail-closed)."""
    out = {}
    sweeps = [(state, [q for q in qs if q.qid not in pre])]
    if pre:
        sweeps.append((None, [q for q in qs if q.qid in pre]))
    for st, subset in sweeps:
        st = st if st is not None else make_pre()
        for q in subset:
            use = use_id(store["group_id"], q.question)
            entries, _ = G.fast_retrieve(st, store["session_id"], q.question, use, ST.RETRIEVE_K, store["principal"])
            rows = [{"entry_id": e.entry_id, "text": e.text} for e in entries]
            _counter["n"] += 1
            if sentinel and _counter["n"] % sentinel == 0:
                ctx = RetrievalContext(st.evidence, st.access, use, "user", "read")
                ref = st.reader().retrieve_with_trace(session_id=store["session_id"], query=q.question, context=ctx,
                                                      k=ST.RETRIEVE_K, principal=store["principal"])
                check([(e.entry_id, e.text) for e in ref.retrieval.entries]
                      == [(r["entry_id"], r["text"]) for r in rows],
                      f"Fast path differs from the frozen GovernedRetrieval ({store['store_id']}, {q.qid})")
                _counter["checked"] += 1
            out[q.qid] = rows
    return {q.qid: out[q.qid] for q in qs}


def _state(store, arm, events, tickets, session, revealed=True, verdicts=None):
    base = "S" if arm in ("SL", "S2-ID", "S2-BS") else arm
    st = G.derive_state(store["state"], events, base, tickets, revealed)
    resolve_models(st, session)
    if not store.get("_acl_ok"):
        G.assert_all_allow(st)
        store["_acl_ok"] = True
    if arm == "SL":
        LN.apply(st, store["session_id"], K.TAU)
    elif arm in ("S2-ID", "S2-BS"):
        SV2.apply(st, store, arm, tau=K.TAU, sensitive=verdicts)
    return st


class Defences:
    """Audit-free published defences on static's entries (no refill), `published.apply` semantics."""

    def __init__(self, verdicts, randec=None, paid=None):
        self.ml = P.memlineage(SV2.RecordedVerdicts(verdicts))
        self.randec, self.paid = randec, paid or {}

    def arms(self, family):
        free = ["memlineage", *(["randec"] if self.randec else [])]
        return free + (list(self.paid) if family in K.PAID_PUBLISHED_FAMILIES else [])

    def apply(self, arm, store, group, question, entries):
        if arm == "memlineage":
            return P.apply(self.ml, store, group, question, entries)["kept_entries"]
        if arm == "randec":
            return P.apply(self.randec, store, group, question, entries)["kept_entries"]
        dfn, rewrite = self.paid[arm]
        return P.apply(dfn, store, group, question, entries, text_from_defence=rewrite)["kept_entries"]


def evaluate_store(c, item, chat, embed, prompts, conflict_session, verdicts, defences: Defences,
                   arms=K.INTERNAL_ARMS + K.APPENDIX_ARMS, timing=None, keep_static=False) -> tuple[list, dict, dict]:
    """(jobs, contexts {hash: text}, store metadata) for one store item of `scenarios.plan`."""
    t0 = time.time()
    qs = sorted((q for q in c.qa if q.category in K.QA_CATEGORIES), key=lambda q: q.qid)[:QLIMIT]
    store = ST.build(c, item["mem"], chat, embed, prompts, [q.question for q in qs], store_id=item["store"],
                     embedded=item["embedded"])
    t1 = time.time()
    group = {"public": store["public"]}
    jobs, ctxs = [], {}
    fam, var, pidx = item["family"], item["variant"], item["pidx"]

    def emit(cfam, cvar, draw, label, arm, rows):
        cell = f"{cfam}|{c.sample_id}|o{pidx}|{cvar}|d{draw}|{label}|{arm}"
        for q in qs:
            text = _context(prompts, c, rows[q.qid])
            h = B1.chash(text)
            ctxs.setdefault(h, text)
            jobs.append({"cell": cell, "qid": q.qid, "ctx": h, "kept": [e["entry_id"] for e in rows[q.qid]]})

    static = _run_state(_state(store, "static", [], 0, conflict_session), store, qs, conflict_session)
    draws = sorted({int(n.rsplit("|d", 1)[1]) for n in item["conditions"]}) if item["draw"] is None else [item["draw"]]
    published = {arm: {q.qid: defences.apply(arm, store, group, q.question, static[q.qid]) for q in qs}
                 for arm in defences.arms(fam)}  # audit-free: once per store
    for d in draws:
        emit(fam, var, d, "-", "static", static)
        for arm, rows in published.items():
            emit(fam, var, d, "-", arm, rows)
    meta_conds = {}
    for name, spec in item["conditions"].items():
        cfam, cvar, label = name.split("|")
        if cfam == "frame":
            draw, label = int(label[1:]), "F"
        else:
            draw = item["draw"]
        events = ST.audit_events(store, spec["audits"])
        pre = frozenset(spec["late"])
        rows_s = None
        for arm in arms:
            if arm == "S2-ID":
                continue
            st = _state(store, arm, events, len(events), conflict_session, True, verdicts)
            make_pre = (lambda arm=arm, events=events: _state(store, arm, events, len(events), conflict_session,
                                                              False, verdicts))
            rows = _run_state(st, store, qs, conflict_session, pre, make_pre)
            emit(cfam, cvar, draw, label, arm, rows)
            if arm == "SL":
                rows_s = rows
        if "S2-ID" in arms:  # frozen sv2 gate on SL's retrieval (S2-ID = SL policy + gate, sv2.apply)
            gate = SV2.RecordedVerdicts(verdicts)
            qtext = {q.qid: q.question for q in qs}
            rows = {qid: ([] if any(store["record_owner"][e["entry_id"]]["kind"] != "principal" for e in es)
                          and gate(qtext[qid]) else es)
                    for qid, es in rows_s.items()}
            emit(cfam, cvar, draw, label, "S2-ID", rows)
        meta_conds[name] = {"audits": spec["audits"], "late": sorted(pre),
                            "unsafe_roots": sorted({e["root_id"] for e in events if e["outcome"] == "unsafe"})}
        if fam == "frame":  # v2: the accused speaker's window = the sessions of the accused turns
            mem = item["mem"]
            by_dia = {r["dia_id"]: i for i, r in enumerate(mem["records"]) if r["dia_id"]}
            window = {mem["records"][i]["session"] for i, _, _ in spec["audits"]}
            meta_conds[name]["strata"] = {q.qid: V2B.strata(q, mem, by_dia, window) for q in qs}
    meta = {"store": item["store"], "family": fam, "variant": var, "pidx": pidx, "draw": item["draw"],
            "embedded": item["embedded"], "principal": store["principal"], "hijacked": item["mem"]["hijacked"],
            "hijack_sessions": item["mem"]["hijack_sessions"], "stats": store["stats"],
            "targets": {r["target"]: {"turn": i, "wrong": B1.WRONG.search(r["text"]).group(1),
                                      "session": r["session"], "speaker": r["speaker"]}
                        for i, r in enumerate(item["mem"]["records"]) if r["target"]},
            "relays": {i: r["relay_of"] for i, r in enumerate(item["mem"]["records"]) if r["relay_of"]},
            "owner": {k: [v["contribution_kind"], v["kind"], v["targets"], v["relay_of"], v["session"],
                          v["dia_ids"]] for k, v in store["record_owner"].items()},
            "conditions": meta_conds}
    if keep_static:  # what the paid published defences filter (stage P2): static entries + provenance
        used = {e["entry_id"] for rows in static.values() for e in rows}
        meta["static_export"] = [{"store": item["store"], "family": fam, "variant": var, "pidx": pidx, "draws": draws,
                                  "conv": c.sample_id, "public": store["public"],
                                  "owner": {k: {"contribution_id": v["contribution_id"], "kind": v["kind"]}
                                            for k, v in store["record_owner"].items() if k in used},
                                  "static": {q.qid: static[q.qid] for q in qs},
                                  "questions": {q.qid: q.question for q in qs}}]
    if timing is not None:
        timing.append({"store": item["store"], "build_s": round(t1 - t0, 2), "eval_s": round(time.time() - t1, 2)})
    return jobs, ctxs, meta


def strata(c, item) -> dict:
    """v2's evidence strata (U_out / U_in / U_own / U_mix) for the store's scenario memory."""
    mem = item["mem"]
    by_dia = {r["dia_id"]: i for i, r in enumerate(mem["records"]) if r["dia_id"]}
    window = set(mem["hijack_sessions"])
    targets = {r["target"] for r in mem["records"] if r["target"]}
    return {q.qid: V2B.strata(q, mem, by_dia, window) for q in c.qa
            if q.category in K.QA_CATEGORIES and q.qid not in targets}


def write_build(out: Path, cid: str, jobs: list, ctxs: dict, metas: list) -> None:
    out.mkdir(parents=True, exist_ok=True)

    def gz(path, lines):
        payload = "".join(lines).encode()
        with path.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as fh:
            fh.write(payload)

    gz(out / f"{cid}.jobs.jsonl.gz", (json.dumps(j, sort_keys=True) + "\n" for j in jobs))
    gz(out / f"{cid}.contexts.jsonl.gz", (json.dumps({"ctx": h, "text": ctxs[h]}) + "\n" for h in sorted(ctxs)))
    (out / f"{cid}.stores.json").write_text(json.dumps(metas, sort_keys=True))


def build_conversation(cid, out: Path, chat, embed, conflict_backend, verdicts, defences, *, families=None,
                       draws=None, timing=None) -> dict:
    c = {x.sample_id: x for x in load_locomo(K.DATA)}[cid]
    prompts = PromptLibrary()
    session = ConflictSession(conflict_backend)
    items = SN.plan(c, **({"families": families} if families else {}), **({"draws": draws} if draws else {}))
    jobs, ctxs, metas = [], {}, []
    with G.fast_runtime():  # MPBench's tested runtime optimization (no decision change)
        for item in items:
            j, cx, m = evaluate_store(c, item, chat, embed, prompts, session, verdicts, defences, timing=timing)
            m["strata"] = strata(c, item)
            jobs += j
            ctxs.update(cx)
            metas.append(m)
    write_build(out, cid, jobs, ctxs, metas)
    return {"conv": cid, "stores": len(items), "jobs": len(jobs), "contexts": len(ctxs),
            "conflict_requests": len(session.requests), "conflict_calls": session.calls,
            "distinct_answer_keys": len({(j["qid"], j["ctx"]) for j in jobs})}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
