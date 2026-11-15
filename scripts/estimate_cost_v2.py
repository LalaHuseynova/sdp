#!/usr/bin/env python3
"""Protocol v2 dry-run cost and runtime estimate (plan.md step 1.12). FREE: no network.

measure  --bundle B --stage1 S --group G --out DIR [--methods ...] [--cells ...]
    Free precompute (pipeline.evaluate, answer=False) for ONE dev group over the
    registered conditions: per method, the answer-prompt hashes (journal), the
    distinct conflict-check requests and the wall time. Run one process per group.
estimate --measured DIR [DIR ...] --ablations DIR --out FILE
    Combine the measurements with per-call costs measured in the existing guarded
    ledgers and the pricing files into a per-stage budget (protocol_v2.cost).
"""

import argparse
import gzip
import json
import time
from pathlib import Path

from ams.research.dynamic.models import check, digest
from ams.research.protocol_v2 import ablations as AB
from ams.research.protocol_v2 import cost as CO
from ams.research.protocol_v2 import hashseed
from ams.research.protocol_v2 import pipeline as PL
from ams.research.protocol_v2 import registry as REG
from ams.research.workload import adaptive as AD
from ams.research.workload import design as D
from ams.research.workload.generator import read_rows
from ams.research.workload.stage2 import ConflictPlaceholderSession

INTERNAL_FREE = ("static", "R", "C", "M", "S", "SL", "S2-BS")


class RecordingPlaceholder(ConflictPlaceholderSession):
    """The Stage-2 placeholder that also records each distinct conflict request."""

    def __init__(self):
        super().__init__()
        self.distinct = set()

    def dispatch(self, stage, request):
        self.distinct.add(digest(repr(request)))
        return super().dispatch(stage, request)


def measure(args):
    from ams.research.recovery.offline import no_network

    check(not args.out.exists(), "Refuse to overwrite an existing directory")
    hashseed.require()
    rows = read_rows(args.bundle)
    split = {p["group_id"]: p["split"] for p in rows["private/probes.jsonl"]}
    check(split.get(args.group) == "dev", "Cost measurement runs on dev groups only")
    table = REG.cells()
    conditions = tuple(c for cell in args.cells for c in table[cell]["conditions"])
    with no_network():
        with gzip.open(args.stage1 / "stores" / f"{args.group}.json.gz", "rt") as f:
            store = json.load(f)
        store = AB.checkpoint_prompts(store, args.out / "prompt_mirror")
        t0 = time.monotonic()
        store = AD.extend_store(rows, store, [c for c in conditions if c not in D.CONDITIONS])
        out = {"group": args.group, "conditions": len(conditions),
               "build_seconds": time.monotonic() - t0, "methods": {}}  # fmt: skip
        for m in args.methods:
            conds = conditions if m in INTERNAL_FREE else tuple(args.invariance_cells)
            session = RecordingPlaceholder()
            defences = {"randec": _randec()} if m.startswith("randec") else {}
            t0 = time.monotonic()
            PL.evaluate(rows, [store], session, args.out / m, conditions=conds, methods=[m],
                        defences=defences, answer=False)  # fmt: skip
            out["methods"][m] = {"conditions": len(conds), "seconds": time.monotonic() - t0,
                                 "conflict_requests": session.conflicts,
                                 "conflict_distinct": sorted(session.distinct)}  # fmt: skip
            (args.out / "measure.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({m: {k: v for k, v in x.items() if k != "conflict_distinct"}
                      for m, x in out["methods"].items()}, indent=1))  # fmt: skip


def _randec():
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from run_protocol_v2 import randec  # local Hugging Face cache only

    return randec()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("--bundle", type=Path, required=True)
    m.add_argument("--stage1", type=Path, required=True)
    m.add_argument("--group", required=True)
    m.add_argument("--out", type=Path, required=True)
    m.add_argument("--methods", nargs="*", default=[*INTERNAL_FREE, "randec", "randec+R"])
    m.add_argument("--cells", nargs="*", default=list(REG.cells()))
    m.add_argument(
        "--invariance-cells",
        nargs="*",
        default=["localized", "distributed", "sybil_k2_rand_d0", "random_spread_d0"],
    )
    e = sub.add_parser("estimate")
    e.add_argument("--measured", type=Path, nargs="+", required=True)
    e.add_argument("--ablations", type=Path, required=True)
    e.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.cmd == "measure":
        measure(args)
    else:
        res = CO.estimate(args.measured, args.ablations)
        args.out.write_text(json.dumps(res, indent=1) + "\n")
        args.out.with_suffix(".md").write_text(CO.render(res))
        print(CO.render(res))


if __name__ == "__main__":
    hashseed.ensure()
    main()
