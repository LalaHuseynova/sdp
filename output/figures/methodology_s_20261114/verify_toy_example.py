#!/usr/bin/env python3
"""Run the FROZEN Policy.decide on the toy world drawn in figure panel (a). Read-only:
no repository file is modified, no network, no model. fcntl is stubbed only because the
ledger's journal-locking import is POSIX-only; snapshots are built in memory.
Run from the repository root:  python output/figures/methodology_s_20261114/verify_toy_example.py"""
import hashlib, pathlib, sys, types
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))
sys.modules.setdefault("fcntl", types.ModuleType("fcntl"))
from ams.research.dynamic.ledger import EvidenceSnapshot, LedgerConfig
from ams.research.dynamic.models import Provenance, Register, StoredRecord, Audit, Finding
from ams.research.dynamic.policies import Policy, Candidate

H = lambda s: hashlib.sha256(s.encode()).hexdigest()
roots = {  # root: (contributor, context, batch, audit outcome or None)
    "a_payee": ("A", "X", "b1", "unsafe"), "a_escalate": ("A", "X", "b1", "unsafe"),
    "a_zx91": ("A", "X", "b1", None),      "a_larkspur": ("A", "X", "b2", None),
    "a_y1": ("A", "Y", "b1", "unsafe"),    "a_y2": ("A", "Y", "b1", "unsafe"),
    "a_y3": ("A", "Y", "b2", None),        "a_y4": ("A", "Y", "b2", None),
    "b_benign": ("B", "Z", "b1", "safe_for_use"), "u_relay": ("U", "W", "b1", None),
}
ev, t = [], 0
for r, (c, ctx, b, _) in roots.items():
    t += 1
    ev.append(Register(f"reg-{r}", t, Provenance(r, ctx, b, c, "authenticated_external"),
                       (StoredRecord(f"rec-{r}", H(r), "claim", f"art-{r}"),)))
for r, (c, ctx, b, out) in roots.items():
    if out:
        t += 1
        ev.append(Audit(f"aud-{r}", t, f"tk-{r}", r, "use", "pv", out,
                        (Finding(f"rec-{r}", H(r), out, "ref"),), out == "safe_for_use",
                        "verifier", "artificial_fixture", "ref"))
snap = EvidenceSnapshot(LedgerConfig("toy", "artificial_fixture", 5), tuple(ev), t)
print("tickets used:", snap.usage.tickets)
for rec in ("a_zx91", "a_larkspur"):
    print("active S scopes", rec, snap.active_scopes(snap.roots[rec]))
    for arm in "RCMS":
        d = Policy(arm).decide(Candidate(f"rec-{rec}", H(rec), "use", "pv", 1.0, True, True), snap)
        print(f"  {arm}: eligible={d.eligible!s:5} penalty={d.penalty:.4f} reason={d.reason} counts={d.counts}")
