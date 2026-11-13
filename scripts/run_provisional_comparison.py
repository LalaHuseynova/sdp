#!/usr/bin/env python3
"""Prepare or run a scope-bound AI-feedback comparison under the existing USD 30 cap."""

import argparse
import json
from pathlib import Path

from ams.research.provisional_run.preparation import prepare, verify
from ams.research.provisional_run.runner import run
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
    repo = Path(__file__).resolve().parents[1]
    if args.command == "run":
        result = run(args.plan, args.out)
    else:
        with no_network():
            if args.command == "verify":
                cfg, spec = verify(args.plan)
                result = {"status": "passed", "basis": cfg["basis"], "cells": len(spec["cells"])}
            else:
                result = prepare(
                    repo,
                    repo / "research_data/provisional_execution_path_v1_20261101",
                    repo / "research_data/dynamic_native_stores_v1_20261031",
                    repo / "research_data/mpbench_provisional_v1_20261029",
                    repo / "research_data/ai_pilot_post_adjudication_view_v1_20261101",
                    repo / "research_data/dynamic_execution_prep_v1_20261031/session",
                    args.out,
                )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
