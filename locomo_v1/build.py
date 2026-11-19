"""Build stage (free, deterministic): every scenario, audit, frozen decision and retrieval
context of the full matrix, written once and hashed by the freeze. Paid and mock execution
only read these files.

Reused unchanged: the feasibility generator (`build_memory`, `choose_audits`,
`ledger_events`, `generic_decisions`, seeds) and the frozen `lineage.blocked_records` via
the tested `minja_v2` glue. Per conversation outputs (build/<conv>.*):
  scenarios.json        scenario metadata (targets, injected values, audits, strata)
  jobs.jsonl.gz         one row per (cell, question): context hash and retrieved records
  contexts.jsonl.gz     one row per distinct context: hash and text
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import config as K

_spec = importlib.util.spec_from_file_location("locomo_feas", K.FEASIBILITY)
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)

from ams.data.locomo import load_locomo  # noqa: E402
from ams.research.workload import lineage as LN  # noqa: E402
from minja_v2.adapter import _Index, _LineageState  # noqa: E402
from ams.research.dynamic.models import digest  # noqa: E402

import re  # noqa: E402

WRONG = re.compile(r'it is (.*)\."$', re.S)
def head(conv) -> str:
    """The existing `locomo_memory_start` v1 prompt, rendered as in the pilot."""
    from ams.core.prompts import PromptLibrary

    return PromptLibrary(K.REPO / "prompts").get("locomo_memory_start").render(
        a=conv.speakers[0], b=conv.speakers[1])


def chash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:20]


def pools(convs):
    """P1: same-category answers of other conversations (the feasibility pool, unchanged).
    P2: same-category answers of the same conversation, tagged so that the generator's own
    filter (other conversation, not the target's answer) keeps them."""
    p1 = defaultdict(list)
    p2 = {}
    for c in convs:
        mine = defaultdict(list)
        for q in c.qa:
            if q.category in K.QA_CATEGORIES and q.answer:
                p1[q.category].append((c.sample_id, q.answer))
                mine[q.category].append(("P2", q.answer))
        p2[c.sample_id] = mine
    return p1, p2


def strata_of(q, mem, by_dia):
    hs = set(mem["hijack_sessions"])
    kinds = set()
    for e in q.evidence:
        i = by_dia.get(e.strip())
        if i is None:
            continue
        r = mem["records"][i]
        kinds.add("own" if r["speaker"] == mem["principal"]
                  else "in" if r["session"] in hs else "out")
    if not kinds:
        return None
    return {"out": "U_out", "in": "U_in", "own": "U_own"}[next(iter(kinds))] \
        if len(kinds) == 1 else "U_mix"


def contexts(conv, mem, S, qs, arm, snap, unsafe, poison_of, blocked):
    """Frozen decisions -> ranked top-k contexts (eligible ranked by the adjusted score)."""
    recs = mem["records"]
    if arm in ("static", "clean"):
        elig, pen = np.ones(len(recs), bool), np.zeros(len(recs))
    else:
        elig, pen = F.generic_decisions(arm, snap, mem, conv.sample_id, blocked, 3,
                                        random.Random(f"check|{arm}"))
    score = np.where(elig[None, :], S - 0.5 * pen[None, :], -np.inf)
    if arm not in ("static", "clean"):
        for qi, q in enumerate(qs):  # an audited unsafe turn is withheld for its own use
            i = poison_of.get(q.qid)
            if i is not None and i in unsafe:
                score[qi, i] = -np.inf
    dates = [s.date_time for s in conv.sessions]
    h = head(conv)
    out = []
    for qi in range(len(qs)):
        order = np.argsort(-score[qi], kind="stable")[: K.TOPK]
        kept = [int(i) for i in order if np.isfinite(score[qi, i])]
        body = "\n".join(f"- [{dates[recs[i]['session']]}] {recs[i]['text']}" for i in kept)
        out.append((kept, h + "\n\n" + (body or "(nothing)")))
    return out


class Encoder:
    def __init__(self):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        self.cache = {}

    def __call__(self, texts):
        new = [t for t in dict.fromkeys(texts) if t not in self.cache]
        if new:
            for t, v in zip(new, self.model.encode(new, batch_size=128, convert_to_numpy=True,
                                                   normalize_embeddings=True)):
                self.cache[t] = v
        return np.stack([self.cache[t] for t in texts])


def lineage_blocked(mem, snap, R):
    recs = mem["records"]
    idx = _Index(list(range(len(recs))), [list(map(float, v)) for v in R])

    class _Mem:
        _vectors = {"m": idx}

    keys = {i: (f"rec{i}", digest(r["text"])) for i, r in enumerate(recs)}
    blocked, _ = LN.blocked_records(_LineageState(snap, _Mem(), keys), "m", K.TAU)
    return blocked


def build_conversation(cid: str, out_dir: Path, draws: int = K.DRAWS_MAX,
                       shapes=K.SHAPES, orientations=K.ORIENTATIONS, encode=None) -> dict:
    convs = load_locomo(K.DATA)
    by_id = {c.sample_id: c for c in convs}
    c = by_id[cid]
    p1, p2 = pools(convs)
    encode = encode or Encoder()
    qs = [q for q in c.qa if q.category in K.QA_CATEGORIES]
    Q = encode([q.question for q in qs])
    jobs, ctx_store, scen = [], {}, []

    def emit(cell, ctxs):
        for q, (kept, text) in zip(qs, ctxs):
            h = chash(text)
            ctx_store.setdefault(h, text)
            jobs.append({"cell": cell, "qid": q.qid, "ctx": h, "kept": kept})

    for pidx in orientations:
        clean = {"principal": c.speakers[pidx], "hijacked": c.speakers[1 - pidx],
                 "hijack_sessions": [], "records": [
                     {"text": t.render(), "speaker": t.speaker, "session": si,
                      "dia_id": t.dia_id, "target": None}
                     for si, s in enumerate(c.sessions) for t in s.turns]}
        Rc = encode([r["text"] for r in clean["records"]])
        emit(f"clean|{cid}|o{pidx}", contexts(c, clean, Q @ Rc.T, qs, "clean", None, set(), {},
                                              frozenset()))
        for shape in shapes:
            for draw in range(draws):
                for attack in K.ATTACKS:
                    rng = random.Random(f"{F.SEED}|{cid}|{pidx}|{shape}|{draw}")
                    pool = p1 if attack == "P1" else p2[cid]
                    mem = F.build_memory(c, pidx, shape, rng, pool)
                    recs = mem["records"]
                    R = encode([r["text"] for r in recs])
                    S = Q @ R.T
                    by_dia = {r["dia_id"]: i for i, r in enumerate(recs) if r["dia_id"]}
                    poison_of = {r["target"]: i for i, r in enumerate(recs) if r["target"]}
                    sid = f"{attack}|{cid}|o{pidx}|{shape}|d{draw}"
                    meta = {"sid": sid, "attack": attack, "conv": cid, "orientation": pidx,
                            "shape": shape, "draw": draw, "principal": mem["principal"],
                            "hijacked": mem["hijacked"], "hijack_sessions": mem["hijack_sessions"],
                            "wrong": {r["target"]: WRONG.search(r["text"]).group(1)
                                      for r in recs if r["target"]},
                            "poison_index": poison_of,
                            "strata": {q.qid: strata_of(q, mem, by_dia) for q in qs
                                       if q.qid not in poison_of},
                            "evidence_idx": {q.qid: [by_dia[e.strip()] for e in q.evidence
                                                     if e.strip() in by_dia] for q in qs},
                            "audits": {}}
                    emit(f"{sid}|-|static", contexts(c, mem, S, qs, "static", None, set(),
                                                     poison_of, frozenset()))
                    auditors = K.AUDITORS if attack == "P1" else {a: K.AUDITORS[a]
                                                                  for a in K.P2_AUDITORS}
                    arms = K.POLICY_ARMS if attack == "P1" else [a for a in K.P2_ARMS
                                                                 if a != "static"]
                    for aname, (m, k) in auditors.items():
                        arng = random.Random(f"{F.SEED}|{cid}|{pidx}|{shape}|{draw}|{m}|{k}")
                        audits = F.choose_audits(cid, mem, m, k, arng)
                        snap = F.ledger_events(cid, mem, audits)
                        unsafe = {i for i, v, _ in audits if v == "unsafe"}
                        blocked = lineage_blocked(mem, snap, R) if "SL" in arms else frozenset()
                        meta["audits"][aname] = {"unsafe": sorted(unsafe),
                                                 "safe": sorted(i for i, v, _ in audits
                                                                if v != "unsafe"),
                                                 "lineage_blocked": len(blocked)}
                        for arm in arms:
                            emit(f"{sid}|{aname}|{arm}", contexts(c, mem, S, qs, arm, snap,
                                                                  unsafe, poison_of, blocked))
                    scen.append(meta)
    out_dir.mkdir(parents=True, exist_ok=True)

    def write_gz(path: Path, lines):
        # mtime=0 and no file name in the header: byte-identical output on every rebuild
        payload = "".join(lines).encode("utf-8")
        with path.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw,
                                                   compresslevel=6, mtime=0) as fh:
            fh.write(payload)

    write_gz(out_dir / f"{cid}.jobs.jsonl.gz", (json.dumps(j, sort_keys=True) + "\n" for j in jobs))
    write_gz(out_dir / f"{cid}.contexts.jsonl.gz",
             (json.dumps({"ctx": h, "text": ctx_store[h]}) + "\n" for h in sorted(ctx_store)))
    (out_dir / f"{cid}.scenarios.json").write_text(json.dumps(scen, sort_keys=True))
    return {"conv": cid, "questions": len(qs), "scenarios": len(scen), "jobs": len(jobs),
            "contexts": len(ctx_store)}


def load_jobs(build_dir: Path, cid: str):
    with gzip.open(build_dir / f"{cid}.jobs.jsonl.gz", "rt", encoding="utf-8") as fh:
        return [json.loads(x) for x in fh]


def load_contexts(build_dir: Path, cid: str) -> dict:
    with gzip.open(build_dir / f"{cid}.contexts.jsonl.gz", "rt", encoding="utf-8") as fh:
        return {r["ctx"]: r["text"] for r in map(json.loads, fh)}


def load_scenarios(build_dir: Path, cid: str):
    return json.loads((build_dir / f"{cid}.scenarios.json").read_text())
