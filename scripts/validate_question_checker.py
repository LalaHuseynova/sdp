#!/usr/bin/env python3
"""Freeze a development-only decoder amendment; use locked validation once."""

import argparse
import json
from pathlib import Path

from ams.research.ai_pilot.calibration_v2 import prepare, run, verify_plan
from ams.research.recovery.offline import no_network


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["prepare", "verify", "run"])
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--parent", type=Path)
    a = p.parse_args()
    if a.command == "run":
        result = run(a.plan)
    else:
        with no_network():
            if a.command == "prepare":
                result = prepare(Path.cwd(), a.parent, a.plan)
            else:
                result = {"status": "passed", "requests": len(verify_plan(a.plan)[1])}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
