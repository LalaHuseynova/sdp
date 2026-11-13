#!/usr/bin/env python3
"""Explicit AI development preparation. Offline commands never fall back to APIs."""

import argparse
import json
from pathlib import Path

from ams.research.pilot_finish.reviewer import FOLLOWUP, PREPARED, prepare_review, run, verify
from ams.research.pilot_finish.selection import freeze_exploratory, readiness
from ams.research.pilot_finish.utility import prepare_checks, prepare_generation
from ams.research.recovery.offline import no_network


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("review-plan")
    a.add_argument("--bags", nargs="+", required=True)
    a.add_argument("--repair", action="store_true")
    a.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("question-plan")
    a.add_argument("--reviews", type=Path, nargs="+", required=True)
    a.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("check-plan")
    a.add_argument("--generation", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    for name in ["verify", "run"]:
        a = sub.add_parser(name)
        a.add_argument("--plan", type=Path, required=True)
    for name in ["readiness", "freeze"]:
        a = sub.add_parser(name)
        a.add_argument("--reviews", type=Path, nargs="+", required=True)
        a.add_argument("--out", type=Path, required=True)
        if name == "freeze":
            a.add_argument("--readiness", type=Path, required=True)
    args = p.parse_args()
    if args.command == "run":
        result = run(args.plan)
    else:
        with no_network():
            if args.command == "review-plan":
                result = prepare_review(
                    Path.cwd(), PREPARED, FOLLOWUP if args.repair else None, args.out, args.bags
                )
            elif args.command == "question-plan":
                result = prepare_generation(Path.cwd(), PREPARED, args.reviews, args.out)
            elif args.command == "check-plan":
                result = prepare_checks(Path.cwd(), PREPARED, args.generation, args.out)
            elif args.command == "readiness":
                result = readiness(PREPARED, args.reviews, args.out)
            elif args.command == "freeze":
                result = freeze_exploratory(PREPARED, args.reviews, args.readiness, args.out)
            else:
                result = {"status": "passed", "requests": len(verify(args.plan)[1])}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
