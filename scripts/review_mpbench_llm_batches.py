#!/usr/bin/env python3
"""Explicit second development review version: small batches, automated labels only."""

import argparse
import json
from pathlib import Path

from ams.research.llm_review.batches import prepare, run, verify
from ams.research.recovery.offline import no_network

parser = argparse.ArgumentParser(description=__doc__)
sub = parser.add_subparsers(dest="command", required=True)
p = sub.add_parser("prepare")
p.add_argument("--parent", type=Path, required=True)
p.add_argument("--out", type=Path, required=True)
for name in ("check", "run"):
    p = sub.add_parser(name)
    p.add_argument("--plan", type=Path, required=True)
args = parser.parse_args()
if args.command == "run":
    result = run(args.plan)
else:
    with no_network():
        result = (
            prepare(args.parent, args.out)
            if args.command == "prepare"
            else {"status": "passed", "jobs": len(verify(args.plan)[1])}
        )
print(json.dumps(result, indent=2))
