#!/usr/bin/env python3
"""Prepare/check/run a frozen constructed-only question-checker calibration."""

import argparse
import json
from pathlib import Path

from ams.research.ai_pilot.calibration import prepare, run, verify_study
from ams.research.recovery.offline import no_network


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["prepare", "verify", "run"])
    p.add_argument("--plan", type=Path, required=True)
    a = p.parse_args()
    if a.command == "run":
        result = run(a.plan)
    else:
        with no_network():
            if a.command == "prepare":
                result = prepare(Path.cwd(), a.plan)
            else:
                cfg, jobs, rows, _ = verify_study(a.plan)
                result = {
                    "status": "passed",
                    "requests": len(jobs),
                    "constructed_cases": len(rows),
                    "uses_MPBench": cfg["uses_MPBench"],
                }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
