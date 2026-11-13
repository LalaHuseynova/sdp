#!/usr/bin/env python3
"""Offline provisional execution preparation/verification; no run or API option."""

import argparse
import json
from pathlib import Path

from ams.research.provisional_execution import prepare, verify
from ams.research.recovery.offline import no_network


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument(
        "--prepared", type=Path, default=Path("research_data/mpbench_provisional_v1_20261029")
    )
    p.add_argument(
        "--stores", type=Path, default=Path("research_data/dynamic_native_stores_v1_20261031")
    )
    p.add_argument(
        "--session",
        type=Path,
        default=Path("research_data/dynamic_execution_prep_v1_20261031/session"),
    )
    p.add_argument("--pricing", type=Path, required=True)
    p.add_argument("--bag", action="append", dest="bags")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("verify")
    p.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    with no_network():
        result = (
            verify(args.plan)
            if args.command == "verify"
            else prepare(
                Path(__file__).resolve().parents[1],
                args.prepared,
                args.stores,
                args.session,
                args.pricing,
                args.out,
                bag_ids=tuple(args.bags or ["D00"]),
            )
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
