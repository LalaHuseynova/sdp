#!/usr/bin/env python3
"""One prospectively frozen exact-span reviewer revision; no defense execution."""

import argparse
import json
from pathlib import Path

from ams.research.ai_pilot.span_review import combined_view, prepare, run, verify_plan
from ams.research.recovery.offline import no_network


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["prepare", "verify", "run", "view"])
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--parent", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    if a.command == "run":
        result = run(a.plan)
    else:
        with no_network():
            if a.command == "prepare":
                if a.parent is None:
                    p.error("--parent is required for prepare")
                result = prepare(Path.cwd(), a.parent, a.plan)
            elif a.command == "verify":
                result = {"status": "passed", "planned_requests": len(verify_plan(a.plan)[1])}
            else:
                if a.out is None:
                    p.error("--out is required for view")
                combined_view(a.plan, a.out)
                result = {"status": "AI_only_view_written"}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
