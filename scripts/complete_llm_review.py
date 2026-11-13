#!/usr/bin/env python3
"""Versioned missing-item LLM review and offline readiness analysis."""

import argparse
import json
from pathlib import Path

from ams.research.llm_followup.analysis import analyse
from ams.research.llm_followup.pipeline import run
from ams.research.llm_followup.plan import prepare, verify
from ams.research.recovery.offline import no_network


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--parent", type=Path, required=True)
    prep.add_argument("--out", type=Path, required=True)
    for name in ("check", "run"):
        s = sub.add_parser(name)
        s.add_argument("--plan", type=Path, required=True)
    a = sub.add_parser("analyse")
    a.add_argument("--plan", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    a.add_argument(
        "--prepared", type=Path, default=Path("research_data/mpbench_provisional_v1_20261029")
    )
    args = p.parse_args()
    if args.command == "run":
        result = run(args.plan)
    else:
        with no_network():
            if args.command == "prepare":
                result = prepare(args.parent, args.out)
            elif args.command == "check":
                result = {"status": "passed", "jobs": len(verify(args.plan)[1])}
            else:
                result = analyse(args.plan, args.prepared, args.out)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
