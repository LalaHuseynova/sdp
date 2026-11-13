#!/usr/bin/env python3
"""Offline-only research preparation. Does not import any model/transport code."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ams.research.phase1 import build_pilot, export_review, prepare, validate_preparation
from ams.research.phase1_common import PreparationError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser(
        "prepare", help="Inventory raw/frozen artifacts and create blank review packets"
    )
    p.add_argument("--data", type=Path, default=Path("data/mpbench"))
    p.add_argument("--journal", type=Path, required=True)
    p.add_argument(
        "--protocol", type=Path, default=Path("reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md")
    )
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--evidence-catalog",
        type=Path,
        help="Actual complete frozen/cached evidence-chunk export, if available",
    )
    p.add_argument(
        "--identifier-key",
        type=Path,
        help="Reuse the private identifier key for exact preparation replay",
    )
    v = sub.add_parser(
        "validate", help="Check preparation hashes, spans, public schemas and corpus"
    )
    v.add_argument("--prepared", type=Path, required=True)
    v.add_argument("--data", type=Path, default=Path("data/mpbench"))
    b = sub.add_parser("build-pilot", help="Require independent reviews; fail closed when missing")
    b.add_argument("--prepared", type=Path, required=True)
    b.add_argument("--annotations", type=Path, required=True)
    b.add_argument("--out", type=Path, required=True)
    e = sub.add_parser("export-review", help="Export only blinded packets and empty review forms")
    e.add_argument("--prepared", type=Path, required=True)
    e.add_argument("--slot", choices=("a", "b"), required=True)
    e.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(
                args.data,
                args.journal,
                args.protocol,
                args.out,
                args.identifier_key,
                args.evidence_catalog,
            )
        elif args.command == "validate":
            result = validate_preparation(args.prepared, args.data)
        elif args.command == "export-review":
            result = export_review(args.prepared, args.out, args.slot)
        else:
            result = build_pilot(args.prepared, args.annotations, args.out)
        # Keep output compact; full artifacts contain counts and exact diagnostics.
        print(
            json.dumps(
                {
                    k: result[k]
                    for k in (
                        "status",
                        "pilot_ready",
                        "review_candidates",
                        "real_episodes_generated",
                        "inputs_checked",
                        "blocking_reason",
                    )
                    if k in result
                },
                indent=2,
            )
        )
        return 2 if result.get("status") == "not_ready" else 0
    except (PreparationError, KeyError, TypeError, ValueError, OSError) as e:
        print(f"Phase 1 preparation stopped: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
