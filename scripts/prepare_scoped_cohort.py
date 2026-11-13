#!/usr/bin/env python3
"""Conditional post-review cohort freeze/analysis; offline and execution disabled."""

import argparse
import json
from pathlib import Path

from ams.research import scoped_cohort
from ams.research.recovery.offline import no_network


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("freeze")
    a.add_argument("--prepared", type=Path, required=True)
    a.add_argument("--readiness", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("verify")
    a.add_argument("--cohort", type=Path, required=True)
    a = sub.add_parser("analysis-plan")
    a.add_argument("--cohort", type=Path, required=True)
    a.add_argument("--case-index", type=Path, required=True)
    a.add_argument("--group-id", required=True)
    a.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    with no_network():
        if args.command == "freeze":
            result = scoped_cohort.freeze(args.prepared, args.readiness, args.out)
        elif args.command == "verify":
            result = scoped_cohort.verify(args.cohort)
        else:
            result = scoped_cohort.prepare_analysis(args.cohort, args.case_index, args.group_id, args.out)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
