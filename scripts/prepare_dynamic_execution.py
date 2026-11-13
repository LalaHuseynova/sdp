#!/usr/bin/env python3
"""Offline API integration preparation. No execute switch, key load or paid calls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ams.research.execution.preflight import prepare, verify
from ams.research.recovery.offline import no_network


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--config", type=Path, default=Path("configs/research/dynamic_execution_v1_20261031.json")
    )
    p.add_argument(
        "--pricing", type=Path, default=Path("configs/research/dynamic_pricing_20261031.json")
    )
    p = commands.add_parser("check")
    p.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    try:
        with no_network():
            result = (
                prepare(Path(__file__).resolve().parents[1], args.out, args.config, args.pricing)
                if args.command == "prepare"
                else verify(args.bundle)
            )
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        print(f"Execution preparation stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
