#!/usr/bin/env python3
"""Step 11 engineering freeze/cost/readiness tools. No execution or paid API mode."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ams.research.dynamic.models import LedgerError
from ams.research.phase1_common import PreparationError
from ams.research.planning.pipeline import prepare, require_scientific_freeze, verify
from ams.research.recovery.offline import no_network


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("prepare")
    make.add_argument(
        "--prepared", type=Path, default=Path("research_data/mpbench_provisional_v1_20261029")
    )
    make.add_argument("--reviews", type=Path)
    make.add_argument("--config", type=Path, default=Path("configs/research/dynamic_pilot_v1.json"))
    make.add_argument(
        "--pricing", type=Path, default=Path("configs/research/dynamic_pricing_20261030.json")
    )
    make.add_argument("--out", type=Path, required=True)
    for command in ("check", "require-scientific-freeze"):
        sub = commands.add_parser(command)
        sub.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        with no_network():
            if args.command == "prepare":
                report = prepare(
                    args.prepared, args.config, args.pricing, args.out, reviews=args.reviews
                )
                result = {
                    "status": report["status"],
                    "grid_slot_count": report["grid_slot_count"],
                    "review_coverage": report["review_coverage"],
                    "readiness": report["readiness"],
                    "paid_cost_usd": 0,
                }
            elif args.command == "check":
                result = verify(args.bundle)
            else:
                require_scientific_freeze(args.bundle)
                return 0
        print(json.dumps(result, indent=2))
        return 0
    except (LedgerError, PreparationError, OSError, ValueError) as error:
        print(f"Planning stopped: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
