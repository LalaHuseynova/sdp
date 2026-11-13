#!/usr/bin/env python3
"""Explicitly frozen D01–D07 extension, unchanged policies and shared cumulative cap."""

import argparse
import json
from pathlib import Path

from ams.research.provisional_extension import execute_with_cache, prepare, verify
from ams.research.recovery.offline import no_network


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("verify")
    p.add_argument("--plan", type=Path, required=True)
    p = sub.add_parser("run")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "run":
        result = execute_with_cache(args.plan, args.out)
    else:
        with no_network():
            if args.command == "prepare":
                result = prepare(Path(__file__).resolve().parents[1], args.out)
            else:
                cfg, spec = verify(args.plan)
                result = {"status": "passed", "groups": cfg["groups"], "cells": len(spec["cells"])}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
