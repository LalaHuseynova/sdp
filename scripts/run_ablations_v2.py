#!/usr/bin/env python3
"""Protocol v2 ablations (plan.md step 1.10), FREE: retrieval exposure only, dev only.

    run_ablations_v2.py --bundle B --stage1 S --out DIR [--groups G ...] [--resamples N]

One knob at a time (gates, withhold threshold, lineage tau, audit budget) plus boundary
verification on/off, each through the unchanged pipeline with a scoped override
(`protocol_v2.ablations`). No network (enforced), no answer, no judge. Refuses any group
whose split is not "dev". Answer-level ablations are step 6.2 (paid, own approval).
"""

import argparse
import gzip
import json
from pathlib import Path

from ams.research.dynamic.models import check
from ams.research.protocol_v2 import ablations as AB
from ams.research.workload import adaptive as AD
from ams.research.workload import design as D
from ams.research.workload.generator import read_rows


def check_dev(splits: dict) -> None:
    bad = sorted(g for g, s in splits.items() if s != "dev")
    check(not bad, f"Ablations run on dev groups only; refused: {bad}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--stage1", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--groups", nargs="*")
    ap.add_argument("--resamples", type=int, default=10_000)
    ap.add_argument("--label", default="dev")
    args = ap.parse_args(argv)
    check(not args.out.exists(), "Refuse to overwrite an existing directory")
    from ams.research.recovery.offline import no_network

    rows = read_rows(args.bundle)
    splits = {p["group_id"]: p["split"] for p in rows["private/probes.jsonl"]}
    job_list = AB.jobs()
    adaptive = sorted({c for j in job_list for c in j["conditions"]
                       if c not in D.CONDITIONS and not c.startswith("budget")})  # fmt: skip
    with no_network():
        stores = []
        for path in sorted((args.stage1 / "stores").glob("*.json.gz")):
            with gzip.open(path, "rt") as f:
                store = json.load(f)
            if args.groups and store["group_id"] not in args.groups:
                continue
            check_dev({store["group_id"]: splits[store["group_id"]]})
            store = AB.checkpoint_prompts(store, args.out / "prompt_mirror")
            stores.append(AB.add_budget(rows, AD.extend_store(rows, store, adaptive)))
        check(bool(stores), "No Stage-1 stores selected")
        AB.run_free(rows, stores, args.out, job_list)
        res = AB.summarise(rows, args.out, job_list, resamples=args.resamples, label=args.label)
    res["inputs"] = {"bundle": str(args.bundle), "stage1": str(args.stage1),
                     "groups": [s["group_id"] for s in stores]}  # fmt: skip
    (args.out / "ablations.json").write_text(json.dumps(res, indent=1) + "\n")
    (args.out / "ablations.md").write_text(AB.render(res))
    print(json.dumps({"groups": res["groups"], "out": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
