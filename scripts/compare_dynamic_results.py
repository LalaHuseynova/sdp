#!/usr/bin/env python3
"""Offline matched-comparison planning and saved-outcome analysis; no run option."""

import argparse
import json
from pathlib import Path

from ams.research.comparison import pending, prepare, write_analysis
from ams.research.recovery.offline import no_network


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("status")
    a.add_argument("--readiness", type=Path, required=True)
    a.add_argument("--historical", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("prepare")
    a.add_argument("--cohort", type=Path, required=True)
    a.add_argument("--case-index", type=Path, required=True)
    a.add_argument("--group-id", required=True)
    a.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("analyse")
    a.add_argument("--plan", type=Path, required=True)
    a.add_argument("--observations", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    a.add_argument("--resamples", type=int, default=10000)
    a.add_argument("--seed", type=int, default=20261028)
    args = p.parse_args()
    with no_network():
        if args.command == "status":
            result = pending(args.readiness, args.historical, args.out)
        elif args.command == "prepare":
            result = prepare(args.cohort, args.case_index, args.group_id, args.out)
        else:
            result = write_analysis(args.plan, args.observations, args.out,
                                    resamples=args.resamples, seed=args.seed)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
