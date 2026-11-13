#!/usr/bin/env python3
"""Offline Steps 3–5 only: cache recovery and independent annotation preparation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ams.research.phase1_common import PreparationError
from ams.research.recovery.offline import no_network
from ams.research.recovery.pipeline import (
    import_reviews,
    prepare_utility_revision,
    run,
    validate_outputs,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("recover")
    p.add_argument("--phase1", type=Path, default=Path("research_data/mpbench_phase1"))
    p.add_argument("--history", type=Path, required=True)
    p.add_argument("--cache", type=Path, action="append", required=True)
    p.add_argument("--reviews", type=Path)
    p.add_argument("--out", type=Path, required=True)
    v = sub.add_parser("validate")
    v.add_argument("--prepared", type=Path, required=True)
    a = sub.add_parser("import-reviews")
    a.add_argument("--prepared", type=Path, required=True)
    a.add_argument("--reviews", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    a.add_argument("--utility", type=Path, help="Versioned revised QA candidates, if prepared")
    q = sub.add_parser("prepare-utility")
    q.add_argument("--prepared", type=Path, required=True)
    q.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        with no_network():
            if args.command == "recover":
                result = run(args.phase1, args.history, args.cache, args.out, args.reviews)
                print(
                    json.dumps(
                        {
                            "recovery": result["recovery"],
                            "review_packets": result["review_packets"],
                            "qa_candidates": result["qa_candidates"],
                            "pilot_ready": result["pilot_ready"],
                        },
                        indent=2,
                    )
                )
            elif args.command == "validate":
                print(json.dumps(validate_outputs(args.prepared), indent=2))
            elif args.command == "prepare-utility":
                print(json.dumps(prepare_utility_revision(args.prepared, args.out), indent=2))
            else:
                result = import_reviews(args.prepared, args.reviews, args.out, args.utility)
                print(
                    json.dumps(
                        {k: v for k, v in result.items() if k != "approved_reviews"}, indent=2
                    )
                )
    except (PreparationError, OSError, ValueError, KeyError) as error:
        print(f"Offline preparation stopped: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
