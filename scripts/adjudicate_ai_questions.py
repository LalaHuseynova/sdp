#!/usr/bin/env python3
"""Prepare/run one blinded AI QA round, preserving previous and human materials."""

import argparse
import json
from pathlib import Path

from ams.research.ai_pilot.adjudication import combined_view, prepare, run
from ams.research.pilot_finish.reviewer import PREPARED
from ams.research.recovery.offline import no_network

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("command", choices=["prepare", "run", "view"])
parser.add_argument("--plan", type=Path, required=True)
parser.add_argument("--reviews", type=Path, nargs="+")
parser.add_argument("--out", type=Path)
args = parser.parse_args()
if args.command == "run":
    result = run(args.plan)
else:
    with no_network():
        if args.command == "prepare":
            result = prepare(Path.cwd(), PREPARED, args.reviews, args.plan)
        else:
            combined_view(args.reviews, args.plan, args.out)
            result = {"status": "combined_view_written"}
print(json.dumps(result, indent=2))
