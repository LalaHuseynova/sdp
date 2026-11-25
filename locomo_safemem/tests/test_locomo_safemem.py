"""Fidelity tests of the LoCoMo + SAFE-Mem study (free; mock LLM, local MiniLM).

    MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash research_data/locomo_v2/run.sh -m pytest -q locomo_safemem/tests
"""

from __future__ import annotations

import copy
import functools
from pathlib import Path

import pytest

from ams.core.prompts import PromptLibrary
from ams.data.locomo import load_locomo
from ams.research.provisional_run.runner import resolve_models
from ams.research.retrieval import RetrievalContext, SourceBinding
from ams.research.workload import lineage as LN
from ams.research.workload import sv2 as SV2
from ams.research.workload.integration import use_id

from locomo_safemem import config as K
from locomo_safemem import evaluate as EV
from locomo_safemem import governance as G
from locomo_safemem import scenarios as SN
from locomo_safemem import store as ST
from locomo_safemem.clients import EmbedCache, MockLLM, Recorder
from locomo_safemem.run import EMBED_CACHE

QN = 25  # questions per check (first by qid)


@functools.lru_cache(maxsize=None)
def conv(cid="conv-48"):
    return {x.sample_id: x for x in load_locomo(K.DATA)}[cid]


@functools.lru_cache(maxsize=None)
def items(cid="conv-48"):
    return SN.plan(conv(cid), draws=[0])


def item(store_suffix, cid="conv-48", pidx=0):
    return next(i for i in items(cid) if i["store"].endswith(store_suffix) and i["pidx"] == pidx)


def questions(c, n=QN):
    return sorted((q for q in c.qa if q.category in K.QA_CATEGORIES), key=lambda q: q.qid)[:n]


def built(it, dump=True):
    c = conv()
    qs = questions(c)
    return ST.build(c, it["mem"], Recorder(MockLLM()), EmbedCache(EMBED_CACHE), PromptLibrary(),
                    [q.question for q in qs], store_id=it["store"], embedded=it["embedded"], dump=dump), qs


def run_frozen(st, store, qs):
    out = []
    for q in qs:
        ctx = RetrievalContext(st.evidence, st.access, use_id(store["group_id"], q.question), "user", "read")
        r = st.reader().retrieve_with_trace(session_id=store["session_id"], query=q.question, context=ctx,
                                            k=ST.RETRIEVE_K, principal=store["principal"])
        out.append([(e.entry_id, e.text) for e in r.retrieval.entries])
    return out


def run_fast(st, store, qs):
    return [[(e.entry_id, e.text) for e in G.fast_retrieve(st, store["session_id"], q.question,
                                                           use_id(store["group_id"], q.question), ST.RETRIEVE_K,
                                                           store["principal"])[0]] for q in qs]


def arm_state(store, arm, events, load=False, revealed=True, verdicts=None):
    base = "S" if arm in ("SL", "S2-ID", "S2-BS") else arm
    if load:
        st = G.prepare_state(store["snapshot"], events, base, len(events), revealed, verify=True)
    else:
        st = G.derive_state(store["state"], events, base, len(events), revealed)
    resolve_models(st, EV.ConflictSession(MockLLM()))
    if arm == "SL":
        LN.apply(st, store["session_id"], K.TAU)
    elif arm in ("S2-ID", "S2-BS"):
        SV2.apply(st, store, arm, tau=K.TAU, sensitive=verdicts)
    return st


# ----------------------------------------------------------------------------- governance
def test_counterpart_role_needs_the_dialogue_binding():
    with pytest.raises(Exception):
        SourceBinding("s", "x1", "a1", "0" * 64, "counterpart_turn", "Caroline")
    G.DialogueSourceBinding("s", "x1", "a1", "0" * 64, "counterpart_turn", "Caroline")


def test_governance_equals_frozen_on_mpbench_store():
    from locomo_safemem import equivalence as EQ

    rep = EQ.compare(("G-T00",), conditions=("localized", "imp_localized_late_d0"), arms=("static", "S", "SL"),
                     mirror=Path("/tmp/locomo_sm_prompt_mirror"))
    assert rep["identical"] and rep["retrievals"] > 0


# ----------------------------------------------------------------------------- SAFE-Mem fidelity
def test_static_equals_original_safemem_retrieve():
    """Original SAFE-Mem's own `TypedStandingMemory.retrieve` == the static (no audit) research arm."""
    store, qs = built(item("loc|1s"))
    a = G.DialogueRuntimeState.load(store["snapshot"])
    b = G.DialogueRuntimeState.load(store["snapshot"])
    a.policy, a.effects_enabled = G.Policy("R"), False
    for st in (a, b):
        resolve_models(st, EV.ConflictSession(MockLLM()))
    gov = run_frozen(a, store, qs)
    orig = [[(e.entry_id, e.text) for e in b.memory.retrieve(session_id=store["session_id"], query=q.question,
                                                             k=ST.RETRIEVE_K, principal=store["principal"]).entries]
            for q in qs]
    assert gov == orig


def test_settings_are_safe_mem_published_locomo_config():
    import yaml

    cfg = yaml.safe_load((K.REPO / "configs/v31_locomo_withhold_a.yaml").read_text())
    t = cfg["typed"]
    assert (ST.SAFE_MEM["mode"], ST.SAFE_MEM["hops"], ST.SAFE_MEM["endorsement"], ST.SAFE_MEM["evidence_slots"],
            ST.SAFE_MEM["external_evidence"], ST.SAFE_MEM["detect_conflicts"], ST.SAFE_MEM["max_claims"],
            ST.RETRIEVE_K, ST.USE_TYPE_VERSION) == (
        t["mode"], t["hops"], t["endorsement"], t["evidence_slots"], t["external_evidence"],
        t["detect_conflicts"], cfg["memory"]["max_facts"], cfg["retrieve_k"], cfg["prompts"]["classify_use_type"])


# ----------------------------------------------------------------------------- provenance
def test_provenance_binding():
    it = item("loc|1s")
    store, _ = built(it, dump=False)
    owner = store["record_owner"]
    poison_turns = [i for i, r in enumerate(it["mem"]["records"]) if r["target"]]
    # every poison turn has its own external root, holding only records of its own contribution
    roots = {store["root_of_turn"][i] for i in poison_turns}
    assert len(roots) == len(poison_turns)
    for r in roots:
        contribs = {store["roots"][r]["contribution"]}
        assert len(contribs) == 1 and store["roots"][r]["kind"] == "external"
    for native, o in owner.items():
        if o["contribution_kind"] == "poison":
            assert o["kind"] == "external" and len(o["targets"]) == 1
        if o["kind"] == "principal":
            assert o["contribution_kind"] in ("session", "embedded")
    # A1 audits implicate exactly the detected poison turns' roots
    ev = ST.audit_events(store, it["conditions"]["loc|1s|A1"]["audits"])
    want = {store["root_of_turn"][i] for i, v, _ in it["conditions"]["loc|1s|A1"]["audits"] if v == "unsafe"}
    assert {e["root_id"] for e in ev if e["outcome"] == "unsafe"} == want


def test_sybil_and_relay_attribution():
    s, _ = built(item("sybil|k4"), dump=False)
    prov = {e.origin.root_id: e.origin for e in s["state"].evidence.events}
    contributors = {prov[s["root_of_turn"][i]].contributor_id
                    for i, r in enumerate(item("sybil|k4")["mem"]["records"]) if r["target"]}
    assert len(contributors) == 4
    r, _ = built(item("relay|r1.0"), dump=False)
    prov = {e.origin.root_id: e.origin for e in r["state"].evidence.events}
    relays = [i for i, x in enumerate(item("relay|r1.0")["mem"]["records"]) if x["relay_of"]]
    assert relays and all(prov[r["root_of_turn"][i]].attribution == "unknown" for i in relays)


# ----------------------------------------------------------------------------- execution equivalences
@pytest.mark.parametrize("suffix,cond", [("loc|1s", "loc|1s|A1"), ("loc|spread", "imp|spread|fp1"),
                                         ("sybil|k2", "sybil|k2|A1"), ("relay|r1.0", "relay|r1.0|A1")])
def test_fast_path_and_derived_states_equal_frozen_loads(suffix, cond):
    it = item(suffix)
    store, qs = built(it)
    ev = ST.audit_events(store, it["conditions"][cond]["audits"])
    verdicts = SV2.RecordedVerdicts({q.question: "ORDINARY" for q in qs})
    for arm in ("static", "R", "C", "M", "S", "SL", "S2-BS"):
        ref = run_frozen(arm_state(store, arm, ev, load=True, verdicts=verdicts), store, qs)
        fast = run_fast(arm_state(store, arm, ev, load=False, verdicts=verdicts), store, qs)
        assert ref == fast, arm


def test_fast_runtime_caches_change_nothing():
    it = item("loc|2s")
    store, qs = built(it)
    ev = ST.audit_events(store, it["conditions"]["loc|2s|A1"]["audits"])
    plain = {arm: run_frozen(arm_state(store, arm, ev, load=True), store, qs) for arm in ("S", "C", "M")}
    with G.fast_runtime() as stats:
        cached = {arm: run_fast(arm_state(store, arm, ev, load=False), store, qs) for arm in ("S", "C", "M")}
    assert plain == cached and stats["hits"] > 0


def test_s2id_shortcut_equals_frozen_sv2_gate():
    it = item("loc|1s")
    store, qs = built(it)
    ev = ST.audit_events(store, it["conditions"]["loc|1s|A1"]["audits"])
    sens = {q.question: ("SENSITIVE" if i % 3 == 0 else "ORDINARY") for i, q in enumerate(qs)}
    verdicts = SV2.RecordedVerdicts(sens)
    full = run_frozen(arm_state(store, "S2-ID", ev, load=True, verdicts=verdicts), store, qs)
    sl = run_fast(arm_state(store, "SL", ev, load=False), store, qs)
    owner = store["record_owner"]
    short = [([] if any(owner[e]["kind"] != "principal" for e, _ in rows)
              and verdicts(q.question) else rows) for rows, q in zip(sl, qs)]
    assert full == short and any(not r for r in full)


# ----------------------------------------------------------------------------- matrix
def test_matrix_is_paired_with_locomo_v2():
    from locomo_v1 import build as B1
    from locomo_v2 import scenarios as V2SC

    c = conv()
    p1, _ = B1.pools(load_locomo(K.DATA))
    base = V2SC.base(c, 0, "1s", 0, p1)
    assert item("loc|1s")["conditions"]["loc|1s|A1"]["audits"] == V2SC.a_audits(c, base, "1s", 0, 0, "A1")
    for k in (2, 4):
        assert item(f"sybil|k{k}")["mem"]["records"] == V2SC.sybil(base, k, c.sample_id, 0, 0)["records"]
    text = " ".join(t.render() for s in c.sessions for t in s.turns)
    for name in K.SYBIL_NAMES:
        assert name not in c.speakers
    kinds = {i["family"] for i in items()}
    assert kinds == {"loc", "sybil", "shift", "relay", "frame", "embed"}
    assert len(text) > 0


def test_late_audits_match_mpbench_two_state_semantics():
    """MPBench runner: two independently loaded states (revealed / not), each question routed by
    `pre_reveal`; ours: two sequential sweeps from the initial state (`evaluate._run_state`)."""
    it = item("loc|1s")
    store, qs = built(it)
    spec = it["conditions"]["imp|1s|late"]
    ev = ST.audit_events(store, spec["audits"])
    pre = frozenset(spec["late"]) & {q.qid for q in qs}
    assert pre and len(pre) < len(qs)
    for arm in ("S", "C"):
        states = {True: arm_state(store, arm, ev, load=True), False: arm_state(store, arm, ev, load=True, revealed=False)}
        ref = {}
        for q in qs:
            ref[q.qid] = run_frozen(states[q.qid not in pre], store, [q])[0]
        st = arm_state(store, arm, ev, load=False)
        got = EV._run_state(st, store, qs, None, pre, lambda: arm_state(store, arm, ev, load=False, revealed=False),
                            sentinel=0)
        assert {k: [(e["entry_id"], e["text"]) for e in v] for k, v in got.items()} == ref
