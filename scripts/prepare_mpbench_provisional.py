#!/usr/bin/env python3
"""Offline unverified Steps 4–6; no scientific pilot, model calls or defense execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ams.research.phase1_common import PreparationError
from ams.research.provisional.pipeline import import_humans, prepare, validate
from ams.research.recovery.offline import no_network


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    b = commands.add_parser("prepare")
    b.add_argument("--phase1", type=Path, default=Path("research_data/mpbench_phase1"))
    b.add_argument(
        "--recovered", type=Path, default=Path("research_data/mpbench_recovery_v1_20261029")
    )
    b.add_argument(
        "--utility", type=Path, default=Path("research_data/mpbench_utility_v2_20261029")
    )
    b.add_argument(
        "--config", type=Path, default=Path("configs/research/mpbench_provisional_v1.json")
    )
    b.add_argument("--out", type=Path, required=True)
    v = commands.add_parser("validate")
    v.add_argument("--prepared", type=Path, required=True)
    r = commands.add_parser("import-reviews")
    r.add_argument("--prepared", type=Path, required=True)
    r.add_argument("--reviews", type=Path, required=True)
    r.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    try:
        with no_network():
            if a.command == "prepare":
                result = prepare(a.phase1, a.recovered, a.utility, a.out, a.config)
            elif a.command == "validate":
                result = validate(a.prepared)
            else:
                result = import_humans(a.prepared, a.reviews, a.out)
            print(
                json.dumps(
                    {
                        k: result[k]
                        for k in (
                            "status",
                            "provisional_groups_generated",
                            "metadata_overlays_generated",
                            "human_verified_labels",
                            "scientific_pilot_ready",
                            "files_checked",
                            "groups_checked",
                            "overlays_checked",
                            "independently_verified_bundles",
                        )
                        if k in result
                    },
                    indent=2,
                )
            )
        return 0
    except (PreparationError, OSError, ValueError, KeyError) as error:
        print(f"Provisional preparation stopped: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
