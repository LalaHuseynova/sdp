"""LoCoMo v2 build (free, deterministic). Writes, per conversation, in the v1 job format so that
`locomo_v1.execute.run` answers and judges unchanged:
  build/<conv>.jobs.jsonl.gz      {cell, qid, ctx, kept}
  build/<conv>.contexts.jsonl.gz  {ctx, text}
  build/<conv>.scenarios.json     per-scenario metadata (targets, values, audits, strata, relays)
Cell = "{family}|{conv}|o{o}|{variant}|d{draw}|{auditor}|{arm}"; "clean|{conv}|o{o}" for the
no-attack reference. Frozen code only: Policy.decide, lineage.blocked_records, the MemLineage
gate (sv2._GatedReader with recorded verdicts), RandEC; nothing is tuned.
"""

from __future__ import annotations

import gzip
import json
import random
from pathlib import Path

import numpy as np

from locomo_v1 import build as B1
from locomo_v2 import config as K
from locomo_v2 import scenarios as SC

from ams.data.locomo import load_locomo
from ams.research.dynamic.ledger import EvidenceSnapshot, LedgerConfig
from ams.research.dynamic.models import Audit, Finding, Provenance, Register, StoredRecord, digest
from ams.research.dynamic.policies import Candidate, Policy
from ams.research.workload import lineage as LN
from ams.research.workload.integration import use_id

POLICY_VERSION = "locomo-v2"


# ----------------------------------------------------------------------------- ledger
def ledger(cid: str, mem: dict, audits) -> EvidenceSnapshot:
    regs = []
    for i, r in enumerate(mem["records"]):
        root = f"root{i}"
        if r["attribution"] == "principal":
            prov = Provenance(root, cid, None, None, "principal", None, r["speaker"])
        elif r["attribution"] == "unknown":
            prov = Provenance(root, cid, f"{cid}:s{r['session']}", None, "unknown")
        else:
            prov = Provenance(root, cid, f"{cid}:s{r['session']}", r["contributor"], "authenticated_external")
        regs.append(Register(f"reg{i}", 0, prov, (StoredRecord(f"rec{i}", digest(r["text"]), "claim", f"art{i}"),)))
    evs = []
    for n, (i, verdict, use) in enumerate(audits):
        ref = "oracle_" + digest([cid, i, verdict, use])[:20]
        evs.append(Audit(f"audit{n}", 1, f"ticket{n}", f"root{i}", use, POLICY_VERSION, verdict,
                         (Finding(f"rec{i}", digest(mem["records"][i]["text"]), verdict, ref),),
                         True, "oracle_locomo_v2", "controlled_audit", ref))
    return EvidenceSnapshot(LedgerConfig(f"locomo2-{cid}", "verified_audits", 64), (*regs, *evs), 1)


def policy_for(arm: str, blocked):
    base = Policy("S" if arm in ("SL", "S2-ID") else arm)
    return LN.LineagePolicy(base, blocked, K.TAU) if arm in ("SL", "S2-ID") else base


def generic(arm, snap, mem, cid, blocked, checks=3):
    """(eligible, penalty) per record for a use no audit names; one frozen decision per
    provenance key, SL-blocked records decided individually; `checks` records re-decided."""
    pol = policy_for(arm, blocked)
    use = use_id(cid, "__generic_question__")
    cache, el, pen = {}, [], []
    for i, r in enumerate(mem["records"]):
        cand = Candidate(f"rec{i}", digest(r["text"]), use, POLICY_VERSION, 0.0, True, True)
        if (f"rec{i}", digest(r["text"])) in blocked:
            d = pol.decide(cand, snap)
        else:
            key = (r["attribution"], r["contributor"], r["session"] if r["attribution"] != "principal" else None)
            if key not in cache:
                cache[key] = pol.decide(cand, snap)
            d = cache[key]
        el.append(d.eligible)
        pen.append(d.penalty)
    rng = random.Random(f"check|{arm}|{len(mem['records'])}")
    for i in rng.sample(range(len(mem["records"])), min(checks, len(mem["records"]))):
        r = mem["records"][i]
        d = pol.decide(Candidate(f"rec{i}", digest(r["text"]), use, POLICY_VERSION, 0.0, True, True), snap)
        assert (d.eligible, d.penalty) == (el[i], pen[i]), (arm, i)
    return np.array(el), np.array(pen, dtype=float)


def scores(arm, snap, mem, cid, blocked, S, qs):
    """Adjusted scores [question x record]; audited records are re-decided by the frozen policy
    for the audit's own use (direct findings: unsafe -> withheld, safe_for_use -> served)."""
    recs = mem["records"]
    if arm in ("static", "clean"):
        return S.copy()
    el, pen = generic(arm, snap, mem, cid, blocked)
    sc = np.where(el[None, :], S - 0.5 * pen[None, :], -np.inf)
    pol = policy_for(arm, blocked)
    qi_of = {}  # use -> every question with that text (LoCoMo has duplicate question texts)
    for qi, q in enumerate(qs):
        qi_of.setdefault(use_id(cid, q.question), []).append(qi)
    for ev in snap.events:
        if type(ev) is not Audit or ev.use_id not in qi_of:
            continue
        i = int(ev.root_id.removeprefix("root"))
        for qi in qi_of[ev.use_id]:
            d = pol.decide(Candidate(f"rec{i}", digest(recs[i]["text"]), ev.use_id, POLICY_VERSION,
                                     float(S[qi, i]), True, True), snap)
            sc[qi, i] = d.adjusted_score if d.eligible else -np.inf
    return sc


# ----------------------------------------------------------------------------- contexts
def render(conv, mem, kept) -> str:
    dates = [s.date_time for s in conv.sessions]
    body = "\n".join(f"- [{dates[mem['records'][i]['session']]}] {mem['records'][i]['text']}" for i in kept)
    return B1.head(conv) + "\n\n" + (body or "(nothing)")


def topk(sc_row) -> list[int]:
    order = np.argsort(-sc_row, kind="stable")[: K.TOPK]
    return [int(i) for i in order if np.isfinite(sc_row[i])]


def s2id_gate(kept, mem, question, verdicts):
    recs = [{"speaker": r["speaker"] if r["attribution"] == "principal" else "__external__"} for r in mem["records"]]
    return B1.gate_s2id(kept, recs, mem["principal"], question, verdicts)


class Published:
    """Audit-free published defences on the static top-k (no refill), as on MPBench."""

    def __init__(self, verdicts, randec=None, sanitiser=None):
        from ams.research.workload import published as P
        from ams.research.workload import sv2 as SV2

        self.ml = P.memlineage(SV2.RecordedVerdicts(verdicts))
        self.randec, self.sanitiser = randec, sanitiser
        self._rcache = {}

    def entries(self, mem, kept):
        from ams.memory.base import MemoryEntry

        return [MemoryEntry(entry_id=f"rec{i}", text=mem["records"][i]["text"],
                            metadata={"user_query": "", "contribution_id": f"rec{i}",
                                      "source_context": "" if mem["records"][i]["attribution"] == "principal"
                                      else f"locomo turn by {mem['records'][i]['speaker']}"})
                for i in kept]

    def arms(self):
        return ["memlineage", *(["randec"] if self.randec else []), *(["llm_sanitiser"] if self.sanitiser else [])]

    def apply(self, arm, question, mem, kept) -> list[int]:
        if arm == "memlineage":
            res = self.ml.filter(question, self.entries(mem, kept))
            ok = {m.entry_id for m in res.kept}
            return [i for i in kept if f"rec{i}" in ok]
        if arm == "randec":
            out = []
            for i in kept:
                t = mem["records"][i]["text"]
                if t not in self._rcache:
                    self._rcache[t] = self.randec.harmful(t + "\n")
                if not self._rcache[t]:
                    out.append(i)
            return out
        if arm == "llm_sanitiser":  # recorded audit verdicts per text; "harmful" -> dropped
            return [i for i in kept if self.sanitiser[mem["records"][i]["text"]] != "harmful"]
        raise ValueError(arm)


# ----------------------------------------------------------------------------- strata
def strata(q, mem, by_dia, window):
    kinds = set()
    for e in q.evidence:
        i = by_dia.get(e.strip())
        if i is None:
            continue
        r = mem["records"][i]
        kinds.add("own" if r["attribution"] == "principal" else "in" if r["session"] in window else "out")
    if not kinds:
        return None
    return {"out": "U_out", "in": "U_in", "own": "U_own"}[next(iter(kinds))] if len(kinds) == 1 else "U_mix"


# ----------------------------------------------------------------------------- build
def scenario_plan(c, families):
    """[(family, variant, pidx, draw, memory, {auditor: audits})] for one conversation."""
    p1, _ = B1.pools(load_locomo(K.DATA))
    n = len(c.sessions)
    for name in K.SYBIL_NAMES:
        assert name not in c.speakers
    out = []
    for pidx in K.ORIENTATIONS:
        for draw in range(K.DRAWS):
            bases = {sh: SC.base(c, pidx, sh, draw, p1) for sh in K.SHAPES}
            a = {sh: {aud: SC.a_audits(c, bases[sh], sh, pidx, draw, aud) for aud in K.AUDITORS} for sh in K.SHAPES}
            if "loc" in families:
                for sh in K.SHAPES:
                    out.append(("loc", sh, pidx, draw, bases[sh], a[sh]))
            if "fn20" in families:
                for sh in K.FN_SHAPES:
                    out.append(("fn20", sh, pidx, draw, bases[sh],
                                {"A1": SC.fn20(a[sh]["A1"], c.sample_id, bases[sh], pidx, sh, draw)}))
            if "sybil" in families:
                for k in K.SYBIL_KS:
                    out.append(("sybil", f"k{k}", pidx, draw, SC.sybil(bases["1s"], k, c.sample_id, pidx, draw),
                                {"A1": a["1s"]["A1"]}))
            if "shift" in families:
                m, aud = SC.shift(bases["2s"], c.sample_id)
                out.append(("shift", "2s", pidx, draw, m, {"O": aud}))
            if "relay" in families:
                for rate in K.RELAY_RATES:
                    out.append(("relay", f"r{rate}", pidx, draw,
                                SC.relay(bases["1s"], rate, c.sample_id, pidx, draw, n), {"A1": a["1s"]["A1"]}))
            if "frame" in families:
                cm = SC.clean(c, pidx)
                for kind in K.FRAME_KINDS:
                    out.append(("frame", kind, pidx, draw, cm, {"F": SC.frame(cm, kind, c.sample_id, pidx, draw)}))
    return out


def build_conversation(cid, out_dir: Path, families=("loc", "fn20", "sybil", "shift", "relay", "frame"),
                       encode=None, verdicts=None, published: Published | None = None) -> dict:
    convs = {c.sample_id: c for c in load_locomo(K.DATA)}
    c = convs[cid]
    verdicts = verdicts if verdicts is not None else B1.load_verdicts()
    encode = encode or B1.Encoder()
    published = published or Published(verdicts)
    qs = [q for q in c.qa if q.category in K.QA_CATEGORIES]
    Q = encode([q.question for q in qs])
    jobs, ctx_store, scen = [], {}, []

    def emit(cell, kept_rows, mem):
        for q, kept in zip(qs, kept_rows):
            text = render(c, mem, kept)
            h = B1.chash(text)
            ctx_store.setdefault(h, text)
            jobs.append({"cell": cell, "qid": q.qid, "ctx": h, "kept": kept})

    for pidx in K.ORIENTATIONS:
        cm = SC.clean(c, pidx)
        Sc = Q @ encode([r["text"] for r in cm["records"]]).T
        emit(f"clean|{cid}|o{pidx}", [topk(Sc[qi]) for qi in range(len(qs))], cm)
    for fam, var, pidx, draw, mem, auds in scenario_plan(c, families):
        recs = mem["records"]
        R = encode([r["text"] for r in recs])
        S = Q @ R.T
        by_dia = {r["dia_id"]: i for i, r in enumerate(recs) if r["dia_id"]}
        poison_of = {r["target"]: i for i, r in enumerate(recs) if r["target"]}
        relay_of = {}
        for i, r in enumerate(recs):
            if r["relay_of"]:
                relay_of.setdefault(r["relay_of"], []).append(i)
        sid = f"{fam}|{cid}|o{pidx}|{var}|d{draw}"
        window = set(mem["hijack_sessions"])
        if fam == "frame":
            window = {recs[i]["session"] for i, _, _ in auds["F"]}
        meta = {"sid": sid, "family": fam, "variant": var, "conv": cid, "orientation": pidx, "draw": draw,
                "principal": mem["principal"], "hijacked": mem["hijacked"], "window": sorted(window),
                "wrong": {r["target"]: B1.WRONG.search(r["text"]).group(1) for r in recs if r["target"]},
                "poison_index": poison_of, "relay_index": relay_of,
                "strata": {q.qid: strata(q, mem, by_dia, window) for q in qs if q.qid not in poison_of},
                "evidence_idx": {q.qid: [by_dia[e.strip()] for e in q.evidence if e.strip() in by_dia] for q in qs},
                "audits": {}}
        static_rows = [topk(S[qi]) for qi in range(len(qs))]
        emit(f"{sid}|-|static", static_rows, mem)
        if fam in K.PUBLISHED_FAMILIES:
            for arm in published.arms():
                emit(f"{sid}|-|{arm}", [published.apply(arm, q.question, mem, static_rows[qi])
                                        for qi, q in enumerate(qs)], mem)
        for aud, audits in auds.items():
            snap = ledger(cid, mem, audits)
            blocked = LN_blocked(mem, snap, R)
            meta["audits"][aud] = {"unsafe": sorted(i for i, v, _ in audits if v == "unsafe"),
                                   "safe": sorted(i for i, v, _ in audits if v != "unsafe"),
                                   "lineage_blocked": len(blocked)}
            for arm in K.INTERNAL_ARMS:
                sc = scores(arm, snap, mem, cid, blocked, S, qs)
                rows = [topk(sc[qi]) for qi in range(len(qs))]
                if arm == "S2-ID":
                    rows = [s2id_gate(k, mem, q.question, verdicts) for k, q in zip(rows, qs)]
                emit(f"{sid}|{aud}|{arm}", rows, mem)
        scen.append(meta)
    out_dir.mkdir(parents=True, exist_ok=True)

    def write_gz(path, lines):
        payload = "".join(lines).encode("utf-8")
        with path.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=6, mtime=0) as fh:
            fh.write(payload)

    write_gz(out_dir / f"{cid}.jobs.jsonl.gz", (json.dumps(j, sort_keys=True) + "\n" for j in jobs))
    write_gz(out_dir / f"{cid}.contexts.jsonl.gz",
             (json.dumps({"ctx": h, "text": ctx_store[h]}) + "\n" for h in sorted(ctx_store)))
    (out_dir / f"{cid}.scenarios.json").write_text(json.dumps(scen, sort_keys=True))
    return {"conv": cid, "scenarios": len(scen), "jobs": len(jobs), "contexts": len(ctx_store)}


def LN_blocked(mem, snap, R):
    from minja_v2.adapter import _Index, _LineageState

    idx = _Index(list(range(len(mem["records"]))), [list(map(float, v)) for v in R])

    class _Mem:
        _vectors = {"m": idx}

    keys = {i: (f"rec{i}", digest(r["text"])) for i, r in enumerate(mem["records"])}
    return LN.blocked_records(_LineageState(snap, _Mem(), keys), "m", K.TAU)[0]
