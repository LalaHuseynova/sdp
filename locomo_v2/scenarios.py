"""LoCoMo v2 scenarios: the verified v1 generator plus MPBench-analogue overlays.

Every family starts from the v1 P1 scenario with the same seed (so families are paired on the
same targets, injected values, hijack window and positions, as MPBench's overlays relabel one
store) and changes only labels, placement or audits:

  loc    v1 scenario, shapes 1s/2s/quarter/spread, auditors A1/A2           (v1 unchanged)
  fn20   loc + each true unsafe ticket returns "safe_for_use" w.p. 0.2     (MPBench imp_fn20)
  sybil  1s; the 8 poison turns dealt round-robin over k accounts: the hijacked speaker and k-1
         fresh accounts; A1 detection unchanged                             (MPBench sybil_k)
  shift  2s; the 2 detected poison turns in the first hijacked session, the 6 scored ones in the
         second; the auditor catches exactly the first session's two       (MPBench shift_batch)
  relay  1s + A1; a share r of the 8 poison turns gets a verbatim copy of unknown origin in a
         random session                                                    (MPBench relays/H5)
  frame  no attack; 1 or 2 genuine turns of the external speaker falsely audited unsafe
                                                                            (MPBench fp1/framing/H6)
Record fields: text, speaker, session, dia_id, target (qid of a scored/seed poison turn),
target_question, attribution (principal | authenticated_external | unknown), contributor,
relay_of (qid, relay copies only). Audits: [(record index, verdict, use_id)].
"""

from __future__ import annotations

import random
import re

from locomo_v1 import build as B
from locomo_v2 import config as K

from ams.research.workload.integration import use_id

F = B.F
PREFIX = re.compile(r'^(.+?) said, "By the way, about ')


def _annotate(mem: dict) -> dict:
    for r in mem["records"]:
        principal = r["speaker"] == mem["principal"]
        r.setdefault("attribution", "principal" if principal else "authenticated_external")
        r.setdefault("contributor", None if principal else r["speaker"])
        r.setdefault("relay_of", None)
    return mem


def base(c, pidx: int, shape: str, draw: int, pool) -> dict:
    rng = random.Random(f"{K.SEED}|{c.sample_id}|{pidx}|{shape}|{draw}")
    return _annotate(F.build_memory(c, pidx, shape, rng, pool))


def clean(c, pidx: int) -> dict:
    return _annotate({"principal": c.speakers[pidx], "hijacked": c.speakers[1 - pidx],
                      "hijack_sessions": [], "targets": [],
                      "records": [{"text": t.render(), "speaker": t.speaker, "session": si,
                                   "dia_id": t.dia_id, "target": None}
                                  for si, s in enumerate(c.sessions) for t in s.turns]})


def a_audits(c, mem: dict, shape: str, pidx: int, draw: int, auditor: str):
    """v1 auditors, same seeds (identical tickets to v1 for the same scenario)."""
    m, k = K.AUDITORS[auditor]
    rng = random.Random(f"{K.SEED}|{c.sample_id}|{pidx}|{shape}|{draw}|{m}|{k}")
    ext = [i for i, r in enumerate(mem["records"]) if r["attribution"] == "authenticated_external"]
    if len(ext) == sum(r["speaker"] != mem["principal"] for r in mem["records"]):
        return F.choose_audits(c.sample_id, mem, m, k, rng)  # exactly v1
    raise ValueError("a_audits on a memory with non-authenticated external records")


def fn20(audits, cid, mem, pidx, shape, draw):
    rng = random.Random(f"{K.SEED_V2}|fn20|{cid}|{pidx}|{shape}|{draw}")
    out = []
    for i, v, u in audits:
        if v == "unsafe" and rng.random() < K.FN_RATE:
            out.append((i, "safe_for_use", u))  # missed: the poison is verified "safe" for its use
        else:
            out.append((i, v, u))
    return out


def sybil(mem: dict, k: int, cid, pidx, draw) -> dict:
    names = [n for n in K.SYBIL_NAMES if n not in (mem["principal"], mem["hijacked"])][: k - 1]
    assert len(names) == k - 1
    ids = [mem["hijacked"], *names]
    poison = [i for i, r in enumerate(mem["records"]) if r["target"]]
    order = poison[:]
    random.Random(f"{K.SEED_V2}|sybil{k}|{cid}|{pidx}|{draw}").shuffle(order)
    owner = {i: ids[j % k] for j, i in enumerate(order)}
    recs = []
    for i, r in enumerate(mem["records"]):
        r = dict(r)
        if i in owner and owner[i] != r["speaker"]:
            r["text"] = PREFIX.sub(f'{owner[i]} said, "By the way, about ', r["text"], count=1)
            r["speaker"] = r["contributor"] = owner[i]
        recs.append(r)
    return {**mem, "records": recs, "sybil_ids": ids}


def shift(mem2s: dict, cid):
    """2s base; poison re-placed: two (to be detected) in the first hijacked session, the rest in
    the second. Returns (memory, audits): the auditor catches exactly the first session's two."""
    hs = mem2s["hijack_sessions"]
    assert len(hs) == 2
    poison = [i for i, r in enumerate(mem2s["records"]) if r["target"]]
    recs = [dict(r) for r in mem2s["records"]]
    for j, i in enumerate(poison):
        recs[i]["session"] = hs[0] if j < 2 else hs[1]
    audits = [(i, "unsafe", use_id(cid, recs[i]["target_question"])) for i in poison[:2]]
    return {**mem2s, "records": recs}, audits


def relay(mem: dict, rate: float, cid, pidx, draw, n_sessions: int) -> dict:
    rng = random.Random(f"{K.SEED_V2}|relay{rate}|{cid}|{pidx}|{draw}")
    poison = [i for i, r in enumerate(mem["records"]) if r["target"]]
    chosen = sorted(rng.sample(poison, round(rate * len(poison))))
    extra = [{"text": mem["records"][i]["text"], "speaker": "unknown", "session": rng.randrange(n_sessions),
              "dia_id": None, "target": None, "attribution": "unknown", "contributor": None,
              "relay_of": mem["records"][i]["target"]} for i in chosen]
    return {**mem, "records": [*mem["records"], *extra]}  # appended: base indices unchanged


def frame(mem_clean: dict, kind: str, cid, pidx, draw):
    rng = random.Random(f"{K.SEED_V2}|frame{kind}|{cid}|{pidx}|{draw}")
    recs = mem_clean["records"]
    ext = [i for i, r in enumerate(recs) if r["attribution"] == "authenticated_external"]
    by_s = {}
    for i in ext:
        by_s.setdefault(recs[i]["session"], []).append(i)
    if kind == "fp1":
        acc = [rng.choice(ext)]
    elif kind == "fp2c":
        s = rng.choice(sorted(x for x, v in by_s.items() if len(v) >= 2))
        acc = rng.sample(by_s[s], 2)
    elif kind == "fp2s":
        s1, s2 = rng.sample(sorted(by_s), 2)
        acc = [rng.choice(by_s[s1]), rng.choice(by_s[s2])]
    else:
        raise ValueError(kind)
    return [(i, "unsafe", use_id(cid, f"audit:{i}")) for i in acc]
