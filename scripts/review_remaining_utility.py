#!/usr/bin/env python3
"""Bounded real utility review, preserving the main provenance-transfer protocol."""

import argparse
import json
from pathlib import Path

from ams.research.ai_pilot.utility_review import combined_view, prepare, run, verify_review
from ams.research.recovery.offline import no_network


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["prepare", "verify", "run", "view"])
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--prepared", type=Path)
    p.add_argument("--reviews", type=Path, nargs="+")
    p.add_argument("--checker", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    if a.command == "run":
        result = run(a.plan)
    else:
        with no_network():
            if a.command == "prepare":
                result = prepare(Path.cwd(), a.prepared, a.reviews, a.checker, a.plan)
            elif a.command == "verify":
                result = {"status": "passed", "physical_requests": len(verify_review(a.plan)[1])}
            else:
                combined_view(a.plan, a.out)
                result = {"status": "AI_view_written"}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
