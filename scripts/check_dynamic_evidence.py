#!/usr/bin/env python3
"""Create an ARTIFICIAL offline ledger/policy example; never loads MPBench or models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ams.research.dynamic.fixture import write_example
from ams.research.dynamic.models import LedgerError
from ams.research.recovery.offline import no_network


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="New output directory; existing output is never overwritten",
    )
    args = parser.parse_args()
    try:
        with no_network():
            result = write_example(args.out)
        print(
            json.dumps(
                {
                    k: result[k]
                    for k in (
                        "status",
                        "records",
                        "independent_roots",
                        "policy_decisions",
                        "final_usage_per_policy",
                    )
                },
                indent=2,
            )
        )
        return 0
    except (LedgerError, OSError) as error:
        print(f"Offline example stopped: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
