"""Experiment matrix: LoCoMo v2's scenario generator (same seeds: identical attack instances) plus the
MPBench Option B cells v2 did not have. One *store* = one scenario memory (texts and placement); one
*condition* = a set of audit tickets (and, for `late`, the questions answered before reveal).

  family   variants                     conditions per store                  MPBench cell
  loc      1s, 2s, quarter, spread      A1, A2; 1s/spread also fp1, late, fu  localized/distributed,
                                                                              random detection, imp_*,
                                                                              boundary verification
  fn20     1s, spread (store = loc)     A1 with missed detections             imp_*_fn20
  sybil    k2, k4, k8                   A1; k2 also fn20, fp1, late, fu       sybil_k{2,4,8}, imp_sybil_k2_*, _fu
  shift    2s                           O (exactly the first session's two)   shift_batch
  relay    r0.5, r1.0                   A1                                    unlinked relays (H5)
  frame    fp1, fp2c, fp2s (no attack)  F (false accusations)                 fp1 / framing harm (H6)
  embed    1s                           A1                                    [ingestion sensitivity]
"""

from __future__ import annotations

import random

from locomo_v1 import build as B1
from locomo_v2 import scenarios as SC

from ams.data.locomo import load_locomo
from ams.research.workload.integration import use_id

from locomo_safemem import config as K

PREFIX = SC.PREFIX


def sybil(mem: dict, k: int, cid, pidx, draw) -> dict:
    """`locomo_v2.scenarios.sybil` with a longer name list (k = 8); identical for k = 2, 4."""
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


def fp1(a1, mem, cid, pidx, shape, draw):
    """MPBench imp_*_fp1: one audit wrongly flags an innocent item. LoCoMo: A1 plus one ticket that
    flags a genuine turn of the external speaker outside the hijack window (seeded)."""
    window = set(mem["hijack_sessions"])
    genuine = [i for i, r in enumerate(mem["records"]) if r["attribution"] == "authenticated_external"
               and not r["target"]]
    # outside the hijack window when one exists; with the all-sessions hijack every session is in it
    cand = [i for i in genuine if mem["records"][i]["session"] not in window] or genuine
    i = random.Random(f"{K.SEED_SM}|fp1|{cid}|{pidx}|{shape}|{draw}").choice(cand)
    return [*a1, (i, "unsafe", use_id(cid, f"audit:{i}"))]


def followup(a1, mem, cid, pidx, shape, draw):
    """MPBench boundary verification (`adaptive._followup_ticket`): if A1's unsafe detections sit in
    one session, one more ticket audits a random genuine turn of the flagged speaker in another
    session, with its true verdict (safe). Otherwise A1 unchanged."""
    recs = mem["records"]
    unsafe = [i for i, v, _ in a1 if v == "unsafe"]
    sessions = {recs[i]["session"] for i in unsafe}
    if len(sessions) != 1:
        return list(a1)
    who = {recs[i]["contributor"] for i in unsafe}
    cand = [i for i, r in enumerate(recs) if r["attribution"] == "authenticated_external" and not r["target"]
            and r["contributor"] in who and r["session"] not in sessions]
    if not cand:
        return list(a1)
    i = random.Random(f"{K.SEED_SM}|fu|{cid}|{pidx}|{shape}|{draw}").choice(sorted(cand))
    return [*a1, (i, "safe_for_use", use_id(cid, f"audit:{i}"))]


def late_questions(qids, cid, pidx, variant, draw):
    """MPBench `pre_reveal_probes`: the questions answered before the audits are revealed."""
    order = sorted(qids)
    random.Random(f"{K.SEED_SM}|late|{cid}|{pidx}|{variant}|{draw}").shuffle(order)
    return sorted(order[: int(len(order) * K.LATE_SHARE)])


def plan(c, families=("loc", "sybil", "shift", "relay", "frame", "embed"), draws=range(K.DRAWS)):
    """[{store, family, variant, pidx, draw, mem, embedded, conditions: {name: {audits, late}}}]."""
    p1, _ = B1.pools(load_locomo(K.DATA))
    for name in K.SYBIL_NAMES:
        assert name not in c.speakers, name
    cid, out = c.sample_id, []
    qids = [q.qid for q in c.qa if q.category in K.QA_CATEGORIES]
    for pidx in K.ORIENTATIONS:
        if "frame" in families:
            cm = SC.clean(c, pidx)
            out.append({"store": f"{cid}|o{pidx}|clean", "family": "frame", "variant": "clean", "pidx": pidx,
                        "draw": None, "mem": cm, "embedded": False,
                        "conditions": {f"frame|{kind}|d{d}": {"audits": SC.frame(cm, kind, cid, pidx, d), "late": []}
                                       for kind in K.FRAME_KINDS for d in draws}})
        for d in draws:
            bases = {sh: SC.base(c, pidx, sh, d, p1) for sh in K.SHAPES}
            a = {sh: {aud: SC.a_audits(c, bases[sh], sh, pidx, d, aud) for aud in ("A1", "A2")} for sh in K.SHAPES}
            if "loc" in families:
                for sh in K.SHAPES:
                    conds = {f"loc|{sh}|A1": {"audits": a[sh]["A1"], "late": []},
                             f"loc|{sh}|A2": {"audits": a[sh]["A2"], "late": []}}
                    if sh in K.IMPERFECT_SHAPES:
                        conds[f"fn20|{sh}|A1"] = {"audits": SC.fn20(a[sh]["A1"], cid, bases[sh], pidx, sh, d), "late": []}
                        conds[f"imp|{sh}|fp1"] = {"audits": fp1(a[sh]["A1"], bases[sh], cid, pidx, sh, d), "late": []}
                        conds[f"imp|{sh}|late"] = {"audits": a[sh]["A1"],
                                                   "late": late_questions(qids, cid, pidx, sh, d)}
                        conds[f"imp|{sh}|fu"] = {"audits": followup(a[sh]["A1"], bases[sh], cid, pidx, sh, d),
                                                 "late": []}
                    out.append({"store": f"{cid}|o{pidx}|d{d}|loc|{sh}", "family": "loc", "variant": sh,
                                "pidx": pidx, "draw": d, "mem": bases[sh], "embedded": False, "conditions": conds})
            if "sybil" in families:
                for k in K.SYBIL_KS:
                    m = sybil(bases["1s"], k, cid, pidx, d)
                    conds = {f"sybil|k{k}|A1": {"audits": a["1s"]["A1"], "late": []}}
                    if k == 2:  # MPBench imp_sybil_k2_{fn20,fp1,late} and boundary verification
                        conds["sybil|k2|fn20"] = {"audits": SC.fn20(a["1s"]["A1"], cid, m, pidx, "1s", d), "late": []}
                        conds["sybil|k2|fp1"] = {"audits": fp1(a["1s"]["A1"], m, cid, pidx, "sybil_k2", d), "late": []}
                        conds["sybil|k2|late"] = {"audits": a["1s"]["A1"],
                                                  "late": late_questions(qids, cid, pidx, "sybil_k2", d)}
                        conds["sybil|k2|fu"] = {"audits": followup(a["1s"]["A1"], m, cid, pidx, "sybil_k2", d),
                                                "late": []}
                    out.append({"store": f"{cid}|o{pidx}|d{d}|sybil|k{k}", "family": "sybil", "variant": f"k{k}",
                                "pidx": pidx, "draw": d, "mem": m, "embedded": False, "conditions": conds})
            if "shift" in families:
                m, aud = SC.shift(bases["2s"], cid)
                out.append({"store": f"{cid}|o{pidx}|d{d}|shift|2s", "family": "shift", "variant": "2s", "pidx": pidx,
                            "draw": d, "mem": m, "embedded": False,
                            "conditions": {"shift|2s|O": {"audits": aud, "late": []}}})
            if "relay" in families:
                for rate in K.RELAY_RATES:
                    m = SC.relay(bases["1s"], rate, cid, pidx, d, len(c.sessions))
                    out.append({"store": f"{cid}|o{pidx}|d{d}|relay|r{rate}", "family": "relay", "variant": f"r{rate}",
                                "pidx": pidx, "draw": d, "mem": m, "embedded": False,
                                "conditions": {f"relay|r{rate}|A1": {"audits": a["1s"]["A1"], "late": []}}})
            if "embed" in families:
                out.append({"store": f"{cid}|o{pidx}|d{d}|embed|1s", "family": "embed", "variant": "1s", "pidx": pidx,
                            "draw": d, "mem": bases["1s"], "embedded": True,
                            "conditions": {"embed|1s|A1": {"audits": a["1s"]["A1"], "late": []}}})
    return out
