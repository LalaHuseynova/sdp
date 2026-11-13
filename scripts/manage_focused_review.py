#!/usr/bin/env python3
"""Offline two-pass review sealing, scoped import and readiness; never fills votes."""

import argparse
import json
from pathlib import Path

from ams.research import focused_review as review
from ams.research.recovery.offline import no_network


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("prepare")
    a.add_argument("--package", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    for action in ["status", "release", "adjudication-form"]:
        a = sub.add_parser(action); a.add_argument("--workflow", type=Path, required=True)
    a = sub.add_parser("seal")
    a.add_argument("--workflow", type=Path, required=True)
    a.add_argument("--phase", choices=["first", "second", "adjudication"], required=True)
    a.add_argument("--role", type=int, choices=[1, 2, 3], required=True)
    a.add_argument("--submission", type=Path, required=True)
    a = sub.add_parser("accept")
    a.add_argument("--workflow", type=Path, required=True)
    a.add_argument("--coordinator", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("coordinator-form")
    a.add_argument("--workflow", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("readiness")
    a.add_argument("--workflow", type=Path, required=True)
    a.add_argument("--prepared", type=Path, required=True)
    a.add_argument("--reviews", type=Path, nargs="+", required=True)
    a.add_argument("--accepted", type=Path)
    a.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    with no_network():
        if args.command == "prepare":
            result = review.prepare(args.package, args.out)
        elif args.command == "status":
            result = review.status(args.workflow)
        elif args.command == "seal":
            result = review.seal(args.workflow, args.phase, args.role, args.submission)
        elif args.command == "release":
            result = review.release(args.workflow)
        elif args.command == "adjudication-form":
            result = review.adjudication_form(args.workflow)
        elif args.command == "accept":
            result = review.accept(args.workflow, args.coordinator, args.out)
        elif args.command == "coordinator-form":
            result = review.coordinator_form(args.workflow, args.out)
        else:
            result = review.readiness(args.workflow, args.prepared, args.reviews, args.out, args.accepted)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
