#!/usr/bin/env python3
"""Cache-only native memory preparation. No paid or scientific execution option."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ams.research.native.pipeline import prepare, verify
from ams.research.recovery.offline import no_network


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--prepared", type=Path, default=Path("research_data/mpbench_provisional_v1_20261029")
    )
    p.add_argument(
        "--recovered", type=Path, default=Path("research_data/mpbench_recovery_v1_20261029")
    )
    p = commands.add_parser("check")
    p.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    try:
        with no_network():
            result = (
                prepare(
                    Path(__file__).resolve().parents[1], args.prepared, args.recovered, args.out
                )
                if args.command == "prepare"
                else verify(args.bundle)
            )
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        print(f"Native preparation stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
