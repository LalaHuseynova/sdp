#!/usr/bin/env python3
"""Figure C check: frozen Policy("S") on three evidence stages of one contributor (offline, read-only).
Run from the repository root:  python output/figures/method_overview_20261123/verify_figure_c.py"""
import hashlib, sys, types
import pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src")); sys.modules.setdefault("fcntl", types.ModuleType("fcntl"))
from ams.research.dynamic.ledger import EvidenceSnapshot, LedgerConfig
from ams.research.dynamic.models import Provenance, Register, StoredRecord, Audit, Finding
from ams.research.dynamic.policies import Policy, Candidate
H = lambda s: hashlib.sha256(s.encode()).hexdigest()
cells = [(c, b) for c in "XYZ" for b in ("b1", "b2")]
stages = {1: {("X","b1")}, 2: {("X","b1"),("X","b2")}, 3: {("X","b1"),("X","b2"),("Y","b1"),("Y","b2")}}
for st, bad in stages.items():
    ev, t = [], 0
    for c, b in cells:
        for kind in (["bad"] if (c, b) in bad else []) + ["u"]:
            r = f"{c}{b}{kind}"; t += 1
            ev.append(Register(f"reg-{r}", t, Provenance(r, c, b, "A", "authenticated_external"),
                               (StoredRecord(f"rec-{r}", H(r), "claim", f"a-{r}"),)))
    for c, b in bad:
        r = f"{c}{b}bad"; t += 1
        ev.append(Audit(f"aud-{r}", t, f"tk-{r}", r, "use", "pv", "unsafe",
                        (Finding(f"rec-{r}", H(r), "unsafe", "ref"),), False, "v", "artificial_fixture", "ref"))
    snap = EvidenceSnapshot(LedgerConfig("toy", "artificial_fixture", 10), tuple(ev), t)
    out = []
    for c, b in cells:
        r = f"{c}{b}u"
        d = Policy("S").decide(Candidate(f"rec-{r}", H(r), "use", "pv", 1.0, True, True), snap)
        out.append(f"{c}{b}:{'W' if not d.eligible else 'K'} D={d.penalty:.3f} {d.active_scopes}")
    print("stage", st, " | ".join(out))
