#!/usr/bin/env python3
"""Blinded automated annotation. No human-gold import or defense-execution command."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ams.research.llm_review.design import prepare, verify
from ams.research.llm_review.pipeline import run
from ams.research.recovery.offline import no_network


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--prepared", type=Path, default=Path("research_data/mpbench_provisional_v1_20261029")
    )
    for name in ("check", "run"):
        p = sub.add_parser(name)
        p.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "run":
            result = run(args.plan)
        else:
            with no_network():
                if args.command == "prepare":
                    result = prepare(Path(__file__).resolve().parents[1], args.prepared, args.out)
                else:
                    cfg, jobs = verify(args.plan)
                    result = {
                        "status": "passed",
                        "jobs": len(jobs),
                        "human_verified": False,
                        "task_reservation_usd": cfg["review_task_reservation_ceiling_usd"],
                    }
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError, KeyError) as error:
        print(f"Automated review stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
